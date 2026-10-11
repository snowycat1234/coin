"""One frozen funding-channel ablation on training history; no wallet engine.

Price/funding projections are bounded before NumPy conversion. Settled future
funding is an outcome description only, never a model input or earned cash.
"""
import argparse
from datetime import datetime, timezone, timedelta
import hashlib
import io
import json
from pathlib import Path
import subprocess
import time
import zipfile

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq

DAY = 86_400_000_000
SYMBOLS = ('BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'XRPUSDT', 'DOGEUSDT')
HERE = Path(__file__).resolve().parent
SOURCE_COMMIT = 'e0d3400b23842f11f167a63e7d80856d76501de8'
SOURCE_BASE = 'research/temporal-feature-data-20261009/'
ARCHIVE_SHA = 'bdbcdc488fc4245c1fb6b433df1fc4bf806a120433db71e180816119cebbcc30'
SETTLEMENT_JITTER_US = 60_000_000

def sha(raw):
    return hashlib.sha256(raw).hexdigest()

def clock(day):
    return int(datetime.fromisoformat(day).replace(tzinfo=timezone.utc).timestamp() * 1_000_000)

def stamp(us):
    return datetime.fromtimestamp(int(us) / 1_000_000, timezone.utc).isoformat()

def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x') as f:
        json.dump(value, f, indent=2, allow_nan=False)
        f.write('\n')

def git(root, *args):
    return subprocess.check_output(['git', *args], cwd=root)

def source_archive(root, state):
    index = json.loads(git(root, 'show', SOURCE_COMMIT + ':' + SOURCE_BASE + 'INDEX.json'))
    dest = state / 'source/features.zip'
    if dest.exists():
        raw = dest.read_bytes()
    else:
        parts = []
        for part in index['parts']:
            raw = git(root, 'show', SOURCE_COMMIT + ':' + SOURCE_BASE + part['file'])
            if sha(raw) != part['SHA256'] or len(raw) != part['bytes']:
                raise ValueError('Immutable Git part identity differs')
            parts.append(raw)
        raw = b''.join(parts)
        dest.parent.mkdir(parents=True, exist_ok=True)
        with dest.open('xb') as f:
            f.write(raw)
    if sha(raw) != ARCHIVE_SHA or len(raw) != index['bytes']:
        raise ValueError('Immutable source archive differs')
    return raw

def settled_window(events, rates, hours, decision):
    """Strictly < decision-24h; historical seven-day settled-event window."""
    lower, upper = decision - 8 * DAY, decision - DAY
    keep = (events >= lower) & (events < upper)
    t, r, h = events[keep], rates[keep], hours[keep]
    ready = (len(t) >= 2 and np.isfinite(r).all() and np.isfinite(h).all()
             and (h > 0).all() and abs(float(h.sum()) - 168) < 1e-9
             and np.all(np.abs(np.diff(t) - h[1:] * 3_600_000_000) <= SETTLEMENT_JITTER_US))
    return float(r.sum()) if ready else None, len(t), int(t[-1]) if len(t) else None

def mature(decision, start, end):
    return start <= decision and decision + 7 * DAY < end

def short_price_cost(entry, exit_price, fee=.00055, execution=.0008):
    if not np.isfinite(entry + exit_price) or entry <= 0 or exit_price <= 0:
        raise ValueError('Missing eligible future price; never filter by outcome')
    ratio = exit_price / entry
    # Same BASE27 fee-on-actual-fill algebra; no second execution debit.
    return (1 - execution) * (1 - fee) - ratio * (1 + execution) * (1 + fee)

def load_training(raw, protocol, patch):
    start, end = clock('2020-01-01'), clock('2023-01-01')
    dates = np.arange(start + DAY, end, DAY, dtype=np.int64)
    close = np.full((len(dates), 5), np.nan)
    funds = []
    receipts = []
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        if z.testzip() is not None:
            raise ValueError('Source CRC failure')
        members = json.loads(z.read('MEMBERS.json'))['files']
        def member(name):
            b = z.read(name)
            m = members[name]
            if sha(b) != m['SHA256'] or len(b) != m['bytes']:
                raise ValueError('Source member identity differs')
            return b
        for a, symbol in enumerate(SYMBOLS):
            name = 'source_tables_not_model_inputs/daily_features/' + symbol + '.parquet'
            b = member(name)
            dtype = pq.read_schema(io.BytesIO(b)).field('dt').type
            if dtype.tz not in (None, 'UTC'):
                raise ValueError('Unsupported source timezone')
            tz = timezone.utc if dtype.tz else None
            table = pq.read_table(io.BytesIO(b), columns=['dt', 'close', 'complete_kline', 'symbol'],
                filters=[('dt', '>=', pa.scalar(datetime(2020, 1, 1, tzinfo=tz), type=dtype)),
                         ('dt', '<', pa.scalar(datetime(2022, 12, 31, tzinfo=tz), type=dtype))]).sort_by([('dt', 'ascending')])
            dt = table['dt'].to_numpy().astype('datetime64[us]').astype(np.int64)
            available = dt + DAY
            if len(np.unique(dt)) != len(dt) or np.any(dt % DAY) or np.any(available >= end):
                raise ValueError('Training price clock or uniqueness differs')
            if set(table['symbol'].to_pylist()) != {symbol}:
                raise ValueError('Source asset identity differs')
            values = table['close'].to_numpy()
            valid = np.asarray(table['complete_kline'].to_pylist(), dtype=bool)
            close[(available - dates[0]) // DAY, a] = np.where(valid, values, np.nan)
            name = 'source_tables_not_model_inputs/economics/' + symbol + '_funding_events.parquet'
            b = member(name)
            table = pq.read_table(io.BytesIO(b), columns=['calc_time_ms', 'last_funding_rate', 'funding_interval_hours'],
                filters=[('calc_time_ms', '>=', start // 1000 - 8 * DAY // 1000),
                         ('calc_time_ms', '<', end // 1000)]).sort_by([('calc_time_ms', 'ascending')])
            t = table['calc_time_ms'].to_numpy().astype(np.int64) * 1000
            r = table['last_funding_rate'].to_numpy().astype(float)
            h = table['funding_interval_hours'].to_numpy().astype(float)
            if len(np.unique(t)) != len(t) or np.any(t >= end) or not np.isfinite(r).all():
                raise ValueError('Training settled funding identity differs')
            funds.append((t, r, h))
            receipts.append(dict(symbol=symbol, price_rows=len(dt), funding_rows=len(t),
                latest_price_available_us=int(available.max()), latest_funding_event_us=int(t.max())))
    if len(patch['records']) != 10 or patch['original_archive_sha256'] != ARCHIVE_SHA:
        raise ValueError('Accepted observed price patch differs')
    for record in patch['records']:
        t = (clock(record['bar_start']) + DAY - dates[0]) // DAY
        a = SYMBOLS.index(record['symbol'])
        if np.isfinite(close[t, a]) or not np.isfinite(record['close']) or record['close'] <= 0:
            raise ValueError('Patch must fill a previously verified missing observation')
        close[t, a] = record['close']
    return dates, close, funds, receipts

def population(dates, close, funds, protocol, outcomes=True):
    groups = []
    masks = []
    windows = [('fit2021', '2021-01-01', '2022-01-01'),
               ('train_screen2022H1', '2022-01-01', '2022-07-01'),
               ('train_screen2022H2', '2022-07-01', '2023-01-01')]
    anchor = clock('2021-01-04')
    for role, left, right in windows:
        rows = []
        for decision in range(anchor, clock('2023-01-01'), 7 * DAY):
            if not mature(decision, clock(left), clock(right)):
                continue
            k = (decision - dates[0]) // DAY
            for a, symbol in enumerate(SYMBOLS):
                p = close[k - 30:k + 1, a]
                rate, count, latest = settled_window(*funds[a], decision)
                reason = None
                if len(p) != 31 or not np.isfinite(p).all() or np.any(p <= 0):
                    reason = 'PAST_PRICE_NOT_READY'
                elif rate is None:
                    reason = 'PAST_SETTLED_FUNDING_NOT_READY'
                else:
                    vol = float(np.std(np.diff(np.log(p)), ddof=1))
                    if not np.isfinite(vol) or vol <= 0:
                        reason = 'PAST_VOL_NOT_READY'
                if reason:
                    masks.append(dict(role=role, decision_us=decision, symbol=symbol, reason=reason))
                    continue
                x = [np.log(p[-1] / p[-1 - h]) / (vol * np.sqrt(h)) for h in (1, 7, 21)]
                x += [np.log(vol)] + [float(a == s) for s in range(4)] + [rate]
                end_price = close[k + 7, a]
                # Completeness is a fail condition after causal admission, never a mask.
                raw_y = short_price_cost(p[-1], end_price, protocol['fee_rate'], protocol['execution_cost'])
                row = dict(role=role, decision_us=decision, label_end_us=decision + 7 * DAY,
                    symbol=symbol, x=x, risk_scale=vol * np.sqrt(7),
                    latest_funding_input_us=latest, funding_input_events=count)
                if outcomes:
                    row.update(price_cost_unit_return=raw_y, y=raw_y / row['risk_scale'])
                    t, r, h = funds[a]
                    keep = (t > decision) & (t <= decision + 7 * DAY)
                    row.update(future_raw_rate_sum=float(r[keep].sum()), future_event_count=int(keep.sum()),
                        future_nominal_hours=float(h[keep].sum()))
                rows.append(row)
        groups.append(rows)
    if any(not g for g in groups):
        raise ValueError('Empty training role')
    return groups, masks

def fit(rows, funding, alpha):
    raw = np.asarray([r['x'] if funding else r['x'][:-1] for r in rows], dtype=float)
    y = np.asarray([r['y'] for r in rows])
    mean, scale = raw.mean(0), raw.std(0, ddof=0)
    if np.any(scale <= 0) or not np.isfinite(scale).all():
        raise ValueError('Invalid fit-only scaler')
    x = np.column_stack((np.ones(len(raw)), (raw - mean) / scale))
    penalty = np.eye(x.shape[1]) * alpha
    penalty[0, 0] = 0
    beta = np.linalg.solve(x.T @ x + penalty, x.T @ y)
    if not np.isfinite(beta).all():
        raise ValueError('Nonfinite fitted coefficients')
    return dict(funding=funding, alpha=alpha, mean=mean.tolist(), scale=scale.tolist(),
        beta=beta.tolist(), rows=len(rows), latest_label_end_us=max(r['label_end_us'] for r in rows),
        latest_scaler_decision_us=max(r['decision_us'] for r in rows))

def predict(rows, model):
    raw = np.asarray([r['x'] if model['funding'] else r['x'][:-1] for r in rows])
    x = np.column_stack((np.ones(len(raw)), (raw - model['mean']) / model['scale']))
    return x @ model['beta']

def paired(rows, baseline, augmented):
    y = np.asarray([r['y'] for r in rows])
    a, b = predict(rows, baseline), predict(rows, augmented)
    loss_a, loss_b = (a - y) ** 2, (b - y) ** 2
    ratio = float((loss_a.mean() - loss_b.mean()) / loss_a.mean())
    unit = np.asarray([r['price_cost_unit_return'] for r in rows])
    scales = np.asarray([r['risk_scale'] for r in rows])
    dates = sorted({r['decision_us'] for r in rows})
    calendar_a = np.array([.12 * sum(u for r, u, pred in zip(rows, unit, a) if r['decision_us'] == d and pred > 0) for d in dates])
    calendar_b = np.array([.12 * sum(u for r, u, pred in zip(rows, unit, b) if r['decision_us'] == d and pred > 0) for d in dates])
    score = dict(baseline_mse=float(loss_a.mean()), augmented_mse=float(loss_b.mean()), relative_mse_gain=ratio,
        baseline_selected_asset_weeks=int((a > 0).sum()), augmented_selected_asset_weeks=int((b > 0).sum()),
        augmented_active_market_weeks=int(sum(any(pred > 0 and r['decision_us'] == d for r, pred in zip(rows, b)) for d in dates)),
        baseline_mean_calendar_price_cost_proxy=float(calendar_a.mean()), augmented_mean_calendar_price_cost_proxy=float(calendar_b.mean()),
        calendar_price_cost_increment=float((calendar_b - calendar_a).mean()),
        scope='Static reference capital, independent paid entry/exit close-price opportunity proxy; no funding, minute execution, wallet, collateral or risk path')
    vectors = dict(baseline_prediction=a, augmented_prediction=b, baseline_loss=loss_a,
        augmented_loss=loss_b, baseline_calendar_proxy=calendar_a, augmented_calendar_proxy=calendar_b,
        physical_baseline_prediction=a * scales, physical_augmented_prediction=b * scales)
    return score, vectors

def bootstrap(groups, baseline, augmented, protocol):
    rng = np.random.default_rng(protocol['bootstrap_seed'])
    axes = []
    for rows in groups:
        _, v = paired(rows, baseline, augmented)
        dates = sorted({r['decision_us'] for r in rows})
        mask = [[i for i, r in enumerate(rows) if r['decision_us'] == d] for d in dates]
        # Keep all actually admitted assets together; sums retain each date's
        # original mask/count and reproduce the point-estimate weighting.
        axes.append(np.array([[v['baseline_loss'][idx].sum(), v['augmented_loss'][idx].sum()] for idx in mask]))
    gains = []
    for _ in range(protocol['bootstrap_replicates']):
        sampled = []
        for data in axes:
            n = len(data)
            starts = rng.integers(0, n, size=(n + 3) // 4)
            indices = np.concatenate([(s + np.arange(4)) % n for s in starts])[:n]
            sampled.append(data[indices])
        a, b = np.concatenate(sampled).sum(0)
        gains.append(float((a - b) / a))
    return dict(relative_mse_gain_interval=np.quantile(gains, [.025, .975]).tolist(),
        replicates=len(gains), seed=protocol['bootstrap_seed'], block_market_weeks=4,
        resampling='Joint assets, contiguous circular four-week blocks separately within both 2022 halves; conditional descriptive interval')

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--state', type=Path, required=True)
    parser.add_argument('--mode', choices=('preflight', 'run', 'verify'), required=True)
    parser.add_argument('--source-commit')
    parser.add_argument('--protocol-sha256')
    parser.add_argument('--saved-results', type=Path)
    args = parser.parse_args()
    began = time.monotonic()
    root = HERE.parents[1]
    state = args.state.resolve()
    if not state.is_relative_to(Path('/workspace')):
        raise ValueError('Task STATE must be under /workspace')
    def disk_output_check():
        owned = sum(p.stat().st_size for p in state.rglob('*') if p.is_file())
        if owned > 10_485_760:
            raise ValueError('10MiB task-output budget exceeded')
    disk_output_check()
    protocol_raw = (HERE / 'PROTOCOL.json').read_bytes()
    if args.protocol_sha256 and sha(protocol_raw) != args.protocol_sha256:
        raise ValueError('Frozen protocol differs')
    protocol = json.loads(protocol_raw)
    if args.mode == 'run':
        if not args.source_commit or git(root, 'rev-parse', 'HEAD').decode().strip() != args.source_commit:
            raise ValueError('Run from exact published implementation commit')
        if git(root, 'status', '--porcelain').strip():
            raise ValueError('Scientific source worktree must be clean')
        public = json.loads((state / 'SOURCE_PUBLIC_READBACK.json').read_text())
        if public['status'] != 'PASS' or public['source_commit'] != args.source_commit:
            raise ValueError('Exact public source readback required before fitting')
        for record in public['files']:
            if sha((root / record['path']).read_bytes()) != record['sha256']:
                raise ValueError('Public-bound source bytes differ')
        save(state / 'STARTED.json', dict(attempt=1, planned_fits=2, source_commit=args.source_commit,
            protocol_sha256=sha(protocol_raw), development_reads=0, native_wallets=0))
    raw = source_archive(root, state)
    patch_raw = (HERE / 'PRICE_PATCH.json').read_bytes()
    if sha(patch_raw) != protocol['price_patch_sha256']:
        raise ValueError('Observed price patch identity differs')
    dates, close, funds, source = load_training(raw, protocol, json.loads(patch_raw))
    groups, masks = population(dates, close, funds, protocol, outcomes=args.mode != 'preflight')
    preflight = dict(status='PASS', source=source, archive_sha256=sha(raw), price_patch_sha256=sha(patch_raw),
        role_rows={g[0]['role']: len(g) for g in groups},
        role_market_weeks={g[0]['role']: len({r['decision_us'] for r in g}) for g in groups},
        causal_exclusions=masks, latest_returned_price_clock_us=int(dates[-1]),
        training_boundary_us=clock('2023-01-01'), development_rows_returned=0,
        feature_scope='Four price/vol features + four symbol indicators; one lagged settled funding sum in augmented arm only',
        future_funding_used_as_input=False)
    if args.mode == 'preflight':
        save(state / 'DATA_PREFLIGHT.json', preflight)
        print(json.dumps(preflight['role_rows']), flush=True)
        return
    rows = groups[0]
    screen = groups[1] + groups[2]
    if args.mode == 'run':
        models = {'baseline': fit(rows, False, protocol['ridge_alpha']),
                  'funding': fit(rows, True, protocol['ridge_alpha'])}
        save(state / 'MODELS.json', models)
        print('FITS_COMPLETE 2/2; TRAIN2022_SCREEN_ONLY', flush=True)
    else:
        if not args.saved_results:
            raise ValueError('Explicit saved results required')
        models = json.loads((args.saved_results / 'MODELS.json').read_text())
    baseline, augmented = models['baseline'], models['funding']
    overall, vectors = paired(screen, baseline, augmented)
    halves = {g[0]['role']: paired(g, baseline, augmented)[0] for g in groups[1:]}
    ci = bootstrap(groups[1:], baseline, augmented, protocol) if args.mode == 'run' else None
    if args.mode == 'verify':
        saved = json.loads((args.saved_results / 'RESULT.json').read_text())
        expected = json.loads((args.saved_results / 'PREDICTIONS.json').read_text())
        actual = {k: v.tolist() for k, v in vectors.items()}
        if saved['overall'] != overall or saved['halves'] != halves or expected != actual:
            raise ValueError('Saved model/prediction/statistic replay differs')
        save(state / 'MODEL_REPLAY.json', dict(status='PASS', model_loads=2,
            prediction_scalars=2 * len(screen), max_prediction_residual=0, fits=0,
            bootstrap_reruns=0, development_reads=0, native_wallets=0,
            scope='Strict saved-model/prediction replay from same immutable public training sources; no retraining'))
        print('MODEL_REPLAY PASS 2 models; residual0', flush=True)
        return
    gates = dict(
        relative_mse_gain_at_least_1percent=overall['relative_mse_gain'] >= .01,
        conditional_joint_interval_lower_positive=ci['relative_mse_gain_interval'][0] > 0,
        both_training_halves_mse_improve=all(s['relative_mse_gain'] > 0 for s in halves.values()),
        expected_crowding_coefficient_positive=augmented['beta'][-1] > 0,
        active_weeks_at_least20=overall['augmented_active_market_weeks'] >= 20,
        absolute_price_cost_proxy_positive=overall['augmented_mean_calendar_price_cost_proxy'] > 0,
        calendar_price_cost_increment_nonnegative=overall['calendar_price_cost_increment'] >= 0)
    if not all(gates.values()):
        decision = 'STOP_TRAINING_DIAGNOSTIC_NO_DEVELOPMENT_READ'
    else:
        decision = 'TRAINING_GATE_PASS_DEVELOPMENT_NOT_RUN'
    future = np.array([r['future_raw_rate_sum'] for r in screen])
    coverage = [r['future_nominal_hours'] for r in screen]
    result = dict(schema='SETTLED_FUNDING_TRAINING_RESIDUAL_ABLATION_V1', decision=decision,
        source_commit=args.source_commit, protocol_sha256=sha(protocol_raw),
        models_sha256=sha((state / 'MODELS.json').read_bytes()), source_preflight=preflight,
        fits=2, attempt=1, seeds={'bootstrap': protocol['bootstrap_seed'], 'model': 'DETERMINISTIC_CLOSED_FORM'},
        overall=overall, halves=halves, conditional_bootstrap=ci,
        funding_standardized_coefficient=augmented['beta'][-1], gates=gates,
        future_funding_description=dict(raw_rate_sum_mean=float(future.mean()),
            hypothetical_fraction_sum_mean=float(future.mean()), hypothetical_percent_sum_mean=float(future.mean() * .01),
            nominal_hours_min=float(min(coverage)), nominal_hours_max=float(max(coverage)),
            scope='Future settled-rate sums as outcome description only; NOT actual fixed-quantity receipts, no charge marks/venue unit/publication certification, no cash credit'),
        development_reads=0, new_native_wallets=0, provider_downloads=0,
        actual_funding_cash='NOT_BOUND', native_execution_risk='NOT_BOUND',
        paper_replication=False, unseen_OOS=False,
        economic_scope=overall['scope'], elapsed_seconds=time.monotonic() - began)
    save(state / 'PREDICTIONS.json', {k: v.tolist() for k, v in vectors.items()})
    save(state / 'SAMPLE_IDENTITIES.json', [{k: r[k] for k in ('role', 'decision_us', 'label_end_us', 'symbol', 'latest_funding_input_us', 'funding_input_events')} for r in screen])
    save(state / 'RESULT.json', result)
    disk_output_check()
    print(json.dumps(dict(decision=decision, relative_mse_gain=overall['relative_mse_gain'], interval=ci['relative_mse_gain_interval'], gates=gates)), flush=True)

if __name__ == '__main__':
    main()
