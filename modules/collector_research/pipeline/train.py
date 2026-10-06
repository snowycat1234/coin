from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
import numpy as np
import pandas as pd
from .common import (DATA, E, REPORTS, WORK, atomic_text, code_digest, dump, funding_scale,
                     log, progress, research_config, sha256, side_cost, symbols)
from .economics import allocate_positions, replay
from .make_labels import BASE_FEATURES
from .models import fit_network, inner_split, scaler_for, transform
from .normalize import verify_dataset
from .storage import read_table, suffix


def market_features(labels: dict[str, pd.DataFrame]) -> pd.DataFrame:
    dates = pd.DatetimeIndex(next(iter(labels.values())).dt)
    close = pd.DataFrame({s: d.close.to_numpy(float) for s, d in labels.items()}, index=dates)
    ret = close.pct_change(fill_method=None)
    market = pd.DataFrame(index=dates)
    for n in (1, 5, 20, 60):
        momentum = close / close.shift(n) - 1
        ready = close.notna().rolling(n + 1, min_periods=n + 1).sum().eq(n + 1)
        momentum = momentum.where(ready)
        market[f'breadth{n}'] = (momentum > 0).where(momentum.notna()).mean(axis=1)
    m20 = (close / close.shift(20) - 1).where(close.notna().rolling(21, min_periods=21).sum().eq(21))
    market['dispersion20'] = m20.std(axis=1)
    market['market_vol20'] = ret.mean(axis=1).rolling(20, min_periods=20).std()
    return market


def folds_for(dates: pd.DatetimeIndex, labels: dict, length: int, min_train: int, embargo: int):
    end = min(pd.Timestamp(E('END_DATE'), tz='UTC') - pd.Timedelta(days=1), dates[-1] - pd.Timedelta(days=1))
    starts = pd.date_range(pd.Timestamp(E('CV_START', '2023-07-01'), tz='UTC'), end, freq='6MS')
    syms = list(labels)
    for a in starts:
        b = min(a + pd.DateOffset(months=6), end)
        calendar = np.flatnonzero((dates >= a) & (dates < b))
        if not len(calendar):
            continue
        cutoff = a - pd.Timedelta(days=embargo)
        train, valid, active = [], [], []
        for sid, s in enumerate(syms):
            d = labels[s]
            seq_ready = d.close.notna().rolling(length, min_periods=length).sum().eq(length).to_numpy()
            causal = d.feature_ready.to_numpy(bool) & seq_ready
            mature = d.label_ready.to_numpy(bool) & (d.label_end_at < cutoff).to_numpy()
            own_train = [(sid, s, int(i)) for i in np.flatnonzero(causal & mature & (dates < a))]
            if len(own_train) >= min_train:
                active.append(s)
                train.extend(own_train)
                valid.extend((sid, s, int(i)) for i in calendar if causal[i])
        if active and train and valid:
            yield dict(start=a, end=b, cutoff=cutoff, calendar=calendar, train=train, valid=valid, active=active)


def targets(mode: str, predictions: np.ndarray | None, fold: dict, labels: dict, syms: list[str]) -> np.ndarray:
    positions = np.zeros((len(fold['calendar']), len(syms)))
    mapping = {int(i): j for j, i in enumerate(fold['calendar'])}
    for k, (sid, s, i) in enumerate(fold['valid']):
        signal = float(labels[s].sma_signal.iloc[i])
        if not np.isfinite(signal):
            # This is observable missing past information, not a future-label gate.
            continue
        if mode == 'MODEL':
            p = predictions[k]
            if not np.isfinite(p).all():
                raise ValueError('Nonfinite prediction')
            scores = np.array([p[0], 0., p[1]])
            scores = (scores - scores.max()) / .02
            mix = np.exp(scores); mix /= mix.sum()
            position = mix[0] * signal + mix[1]
        elif mode == 'HOLD':
            position = 1.
        elif mode == 'SMA200_SIGNED':
            position = signal
        elif mode == 'STATIC_DIRECTION3':
            position = .5 * signal + .25
        elif mode == 'CASH':
            position = 0.
        else:
            raise ValueError(mode)
        positions[mapping[i], sid] = position
    return allocate_positions(positions, len(fold['active']), float(E('ASSET_CAP')), float(E('GROSS_CAP')))


def fit_xgb(X, Y, tr, va, mu, sd, seed, out: Path):
    from xgboost import XGBRegressor
    out.mkdir(parents=True, exist_ok=True)
    prediction = np.full((len(va), 2), np.nan)
    for s in sorted({x[1] for x in tr}):
        own = [i for _, ss, i in tr if ss == s]
        val = [(j, i) for j, (_, ss, i) in enumerate(va) if ss == s]
        xt = transform(X[s][own], mu, sd)
        yt = Y[s][own]
        xv = transform(X[s][[i for _, i in val]], mu, sd) if val else None
        for h in range(2):
            model = XGBRegressor(n_estimators=int(E('XGB_ESTIMATORS', '300')), max_depth=4,
                                 learning_rate=.035, subsample=.8, colsample_bytree=.8,
                                 reg_lambda=4, tree_method='hist', n_jobs=int(E('NUM_THREADS')),
                                 random_state=seed)
            model.fit(xt, yt[:, h])
            model.save_model(out / f'{s}_head{h}.json')
            if val:
                prediction[[j for j, _ in val], h] = model.predict(xv)
    if not np.isfinite(prediction).all():
        raise ValueError('XGB prediction missing; no untrained-asset fallback')
    return prediction


def save_targets(study, fold_number, name, dates, fold, weights, syms):
    """Export past-only targets at the completed day's actual decision boundary."""
    path = study / f'fold{fold_number}_{name}_targets.npz'
    np.savez_compressed(path, decision_us=dates[fold['calendar']].as_unit('us').asi8 + 86_400_000_000,
                        weights=np.asarray(weights, dtype='float64'),
                        symbol_order=np.asarray(syms, dtype='U30'))
    return path


def train() -> dict:
    verify_dataset()
    scale = funding_scale()
    scenario = 'raw_fraction' if scale == 1 else 'raw_percent'
    labeldir = DATA / 'labels' / scenario
    lm_path = labeldir / 'LABEL_MANIFEST.json'
    lm = json.loads(lm_path.read_text())
    if lm['source_manifest_sha256'] != sha256(REPORTS / 'DATASET_MANIFEST.json'):
        raise ValueError('Labels bind an old dataset; regenerate labels')
    # Bind ALL label knobs as well as file hashes; no stale reuse after fee/H change.
    if lm.get('research_config') != research_config():
        raise ValueError('Label configuration changed; run labels again')
    labels = {}
    for item in lm['files']:
        p = Path(item['path'])
        if sha256(p) != item['sha256']:
            raise ValueError('Label bytes changed')
        labels[item['symbol']] = read_table(p).reset_index(drop=True)
    syms = symbols()
    labels = {s: labels[s] for s in syms}
    dates = pd.DatetimeIndex(next(iter(labels.values())).dt)
    if any(not pd.DatetimeIndex(d.dt).equals(dates) for d in labels.values()):
        raise ValueError('All assets require the same explicit daily calendar')
    frames = {s: read_table(DATA / 'normalized' / (s + '_daily' + suffix())).reset_index(drop=True) for s in syms}
    market = market_features(labels).reset_index(drop=True)
    features = BASE_FEATURES + list(market.columns)
    X = {s: pd.concat([d[BASE_FEATURES], market], axis=1).to_numpy('float32') for s, d in labels.items()}
    Y = {s: d[['y_sma_vs_hold', 'y_cash_vs_hold']].to_numpy('float32') for s, d in labels.items()}
    ends = {s: d.label_end_at.to_numpy() for s, d in labels.items()}
    # Keep Timestamp objects to preserve aware comparisons in inner_split.
    ends = {s: list(d.label_end_at) for s, d in labels.items()}
    length = int(E('LOOKBACK_DAYS')); seed = int(E('SEED'))
    min_rows = int(E('MIN_TRAIN_ASSET_ROWS')); embargo = int(E('EMBARGO_DAYS'))
    families = E('MODEL_FAMILIES').split(',')
    allowed = {'PER_ASSET_XGB', 'TCN_SHARED', 'GRU_SHARED', 'TRANSFORMER_SHARED'}
    if not families or not set(families) <= allowed or len(set(families)) != len(families):
        raise ValueError('Invalid model family selection')
    if set(families) - {'PER_ASSET_XGB'}:
        import torch
        torch.set_num_threads(int(E('NUM_THREADS')))
        if E('DEVICE') not in ('cpu', 'cuda'):
            raise ValueError('DEVICE must be explicitly cpu or cuda')
        if E('DEVICE') == 'cuda' and not torch.cuda.is_available():
            raise ValueError('DEVICE=cuda requested but CUDA cannot initialize; no silent fallback')
    folds = list(folds_for(dates, labels, length, min_rows, embargo))
    if len(folds) < int(E('MIN_FOLDS', '4')):
        raise ValueError(f'Only {len(folds)} folds meet causal training counts; need MIN_FOLDS (default 4)')
    binding = dict(code_sha256=code_digest(), label_manifest_sha256=sha256(lm_path), config=research_config(),
                   extra_knobs={k: E(k, v) for k, v in [('MIN_FOLDS', '4'), ('CV_START', '2023-07-01'), ('XGB_ESTIMATORS', '300')]})
    study_id = hashlib.sha256(json.dumps(binding, sort_keys=True).encode()).hexdigest()[:16]
    study = WORK / 'research' / study_id
    study.mkdir(parents=True, exist_ok=True)
    dump(binding, study / 'BINDING.json')
    foldrows = [{k: str(v) for k, v in f.items() if k in ('start', 'end', 'cutoff')} |
                dict(fold=i, training_rows=len(f['train']), prediction_rows=len(f['valid']),
                     calendar_days=len(f['calendar']), active_assets=','.join(f['active'])) for i, f in enumerate(folds, 1)]
    atomic_text(study / 'fold_plan.csv', pd.DataFrame(foldrows).to_csv(index=False))
    results = []; best_epochs = {name: [] for name in families}
    for fi, fold in enumerate(folds, 1):
        tr, va = fold['train'], fold['valid']
        mu, sd = scaler_for(X, tr, length)
        for name in families:
            progress('TRAIN', (fi - 1) * len(families), len(folds) * len(families), f'fold={fi} {name}')
            out = study / 'models' / f'fold{fi}' / name
            out.mkdir(parents=True, exist_ok=True)
            checkpoint = out / 'CHECKPOINT.json'
            predfile = out / 'predictions.npy'
            cached = json.loads(checkpoint.read_text()) if checkpoint.exists() else None
            reuse = cached is not None and predfile.exists() and cached.get('pred_sha256') == sha256(predfile)
            if reuse:
                reuse = all((out / f['name']).exists() and sha256(out / f['name']) == f['sha256'] for f in cached.get('models', []))
            if reuse:
                pred = np.load(predfile, allow_pickle=False); best_ep = cached['best_epoch']
                log(f'RESUME verified fold={fi} {name}')
            else:
                best_ep = 0
                if name == 'PER_ASSET_XGB':
                    pred = fit_xgb(X, Y, tr, va, mu, sd, seed + fi, out)
                else:
                    itr, iva = inner_split(tr, dates, ends, embargo)
                    inner_assets = {s for s in syms if sum(ss == s for _, ss, _ in itr) >= min_rows}
                    itr = [item for item in itr if item[1] in inner_assets]
                    iva = [item for item in iva if item[1] in inner_assets]
                    if len(itr) >= 100 and len(iva) >= 30:
                        imu, isd = scaler_for(X, itr, length)
                        _, best_ep, _ = fit_network(name, X, Y, itr, [], length, len(syms), imu, isd,
                                                   int(E('EPOCHS')), E('DEVICE'), int(E('BATCH_SIZE')), seed + fi,
                                                   validation_items=iva, patience=int(E('PATIENCE')), logger=log)
                    else:
                        # Small data: fixed preregistered budget, NEVER peek at outer validation.
                        best_ep = min(10, int(E('EPOCHS')))
                        log(f'{name}: inner split too small; fixed {best_ep} epochs, no outer-label selection')
                    pred, _, state = fit_network(name, X, Y, tr, va, length, len(syms), mu, sd,
                                                 best_ep, E('DEVICE'), int(E('BATCH_SIZE')), seed + fi, logger=log)
                    import torch
                    torch.save(state, out / 'weights.pt')
                np.savez_compressed(out / 'scaler.npz', mu=mu, sd=sd)
                with predfile.with_suffix('.tmp').open('wb') as stream:
                    np.save(stream, pred, allow_pickle=False)
                predfile.with_suffix('.tmp').replace(predfile)
                model_files = [p for p in out.iterdir() if p.is_file() and p.name not in ('predictions.npy', 'CHECKPOINT.json')]
                dump(dict(pred_sha256=sha256(predfile), best_epoch=best_ep,
                          models=[dict(name=p.name, sha256=sha256(p)) for p in model_files]), checkpoint)
            if pred.shape != (len(va), 2) or not np.isfinite(pred).all():
                raise ValueError('Invalid cached/generated prediction shape/values')
            best_epochs[name].append(best_ep)
            weights = targets('MODEL', pred, fold, labels, syms)
            save_targets(study, fi, name, dates, fold, weights, syms)
            metrics, trace = replay(frames, fold['calendar'], weights, scale, side_cost(), float(E('INITIAL_CAPITAL')))
            atomic_text(study / f'fold{fi}_{name}_daily.csv', trace.to_csv(index=False))
            results.append(dict(fold=fi, model=name, kind='CANDIDATE', **metrics))
            log(f'FOLD {fi} {name}: net={metrics["net"]:.2f} days={metrics["days"]}')
        for mode in ('HOLD', 'SMA200_SIGNED', 'STATIC_DIRECTION3', 'CASH'):
            weights = targets(mode, None, fold, labels, syms)
            save_targets(study, fi, 'BASE_' + mode, dates, fold, weights, syms)
            metrics, trace = replay(frames, fold['calendar'], weights, scale, side_cost(), float(E('INITIAL_CAPITAL')))
            atomic_text(study / f'fold{fi}_BASE_{mode}_daily.csv', trace.to_csv(index=False))
            results.append(dict(fold=fi, model='BASE_' + mode, kind='BASELINE', **metrics))
        atomic_text(study / 'model_results.csv', pd.DataFrame(results).to_csv(index=False))
    rr = pd.DataFrame(results)
    summary = rr.groupby(['kind', 'model']).agg(folds=('fold', 'count'), net_sum=('net', 'sum'), net_median=('net', 'median'),
                 positive_folds=('net', lambda x: int((x > 0).sum())), mean_sharpe=('sharpe', 'mean'), mean_mdd=('mdd', 'mean')).reset_index()
    rank = ['positive_folds', 'net_median', 'net_sum', 'mean_sharpe']
    summary = summary.sort_values(rank, ascending=False)
    atomic_text(study / 'model_summary.csv', summary.to_csv(index=False))
    winner = summary[summary.kind == 'CANDIDATE'].iloc[0]
    baseline = summary[summary.kind == 'BASELINE'].iloc[0]
    passed = bool(winner.positive_folds >= baseline.positive_folds and winner.net_median > baseline.net_median and winner.net_sum > baseline.net_sum)
    frozen = dict(best_candidate=str(winner.model), best_baseline=str(baseline.model),
                  promotion_gate_pass=passed, deployment_authorized=False, deployment_status='NONE_CASH',
                  exact_minute_wallet_replay='NOT_RUN', funding_scale=scale, funding_unit='CONDITIONAL_UNCONFIRMED',
                  result_scope='SEEN_DEVELOPMENT_CHRONOLOGICAL_SCREENING_NOT_INDEPENDENT_OOS',
                  note='Fold net_sum is a sum of reset-account diagnostics, NOT a continuous portfolio return.')
    dump(frozen, study / 'FROZEN_RESEARCH_WINNER.json')
    final_meta = dict(status='NOT_FIT_CANDIDATE_FAILED_BASELINE_GATE', final_model=None)
    if passed:
        final_items = []
        for sid, s in enumerate(syms):
            d = labels[s]
            items = [(sid, s, int(i)) for i in np.flatnonzero(d.feature_ready.to_numpy(bool) & d.label_ready.to_numpy(bool)) if i >= length - 1]
            if len(items) >= min_rows:
                final_items.extend(items)
        mu, sd = scaler_for(X, final_items, length)
        out = study / 'final_model'; out.mkdir(exist_ok=True)
        if winner.model == 'PER_ASSET_XGB':
            fit_xgb(X, Y, final_items, [], mu, sd, seed, out)
            final_epochs = None
        else:
            final_epochs = max(1, int(round(np.median(best_epochs[str(winner.model)]))))
            _, _, state = fit_network(str(winner.model), X, Y, final_items, [], length, len(syms), mu, sd,
                                      final_epochs, E('DEVICE'), int(E('BATCH_SIZE')), seed, logger=log)
            import torch
            torch.save(state, out / 'weights.pt')
        np.savez_compressed(out / 'scaler.npz', mu=mu, sd=sd)
        final_meta = dict(status='RESEARCH_ONLY_NOT_DEPLOYABLE', family=str(winner.model), final_model=str(out),
                          training_rows=len(final_items), epochs=final_epochs, lookback=length,
                          supported_symbols=sorted({s for _, s, _ in final_items}), symbol_order=syms,
                          features=features, feature_masks='per-feature appended after standardized values',
                          maturity_max=str(max(labels[s].label_end_at.iloc[i] for _, s, i in final_items)),
                          files=[dict(name=p.name, sha256=sha256(p)) for p in out.iterdir() if p.is_file()])
    dump(final_meta, study / 'FINAL_MODEL.json')
    dump(dict(role='PAST_ONLY_CANDIDATE_TARGETS_FOR_SEPARATE_NATIVE_ACCOUNT_VALIDATION',
              decision_clock='Completed UTC day boundary; execution must obey the native account contract',
              symbol_order=syms, files=[dict(name=p.name, sha256=sha256(p))
                                      for p in sorted(study.glob('*_targets.npz'))]),
         study / 'TARGETS_MANIFEST.json')
    report = '\n'.join(['# Conditional selector research', '', json.dumps(frozen, indent=2, ensure_ascii=False), '',
        '## Fold comparison (reset accounts; do not compound/sum as one portfolio)', '', summary.to_string(index=False), '',
        'Neural early stopping uses only an inner purged training split; outer labels never choose epochs.',
        'Inference eligibility uses past features and training counts, not future label availability.',
        'Missing owned execution intervals abort the study. Cash days remain on the full calendar.',
        'Bybit-cost / Binance-price daily proxy only. Margin, capacity, native funding timing and liquidation are NOT certified.',
        'Per-asset XGBoost uses current feature rows; shared neural models use sequences. This is not an isolated test of sharing alone.',
        'No final model is fit when the best candidate fails the baseline gate. No live execution is included.'])
    atomic_text(study / 'FINAL_REPORT.md', report + '\n')
    result = dict(study_id=study_id, study_dir=str(study), report=str(study / 'FINAL_REPORT.md'), **frozen)
    dump(result, REPORTS / 'CURRENT_RESEARCH.json')
    progress('TRAIN', len(folds) * len(families), len(folds) * len(families), 'Completed research-only study')
    return result
