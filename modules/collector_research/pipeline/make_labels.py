from __future__ import annotations
import hashlib
import numpy as np
import pandas as pd
from .common import DATA, E, EXEC_OFFSET_US, REPORTS, atomic_text, dump, funding_scale, log, research_config, sha256, side_cost, symbols
from .economics import continuous_expert_returns
from .normalize import verify_dataset
from .storage import read_table, suffix, write_table

BASE_FEATURES = ['mom1', 'mom5', 'mom20', 'mom60', 'mom120', 'mom200', 'vol10', 'vol30', 'vol60', 'vol200',
                 'dist20', 'dist50', 'dist100', 'dist200', 'range', 'vol_z', 'premium', 'funding']


def future_compound(x: pd.Series, horizon: int) -> pd.Series:
    if horizon < 1:
        raise ValueError('Positive horizon required')
    if ((x <= -1) & x.notna()).any():
        raise ValueError('Expert interval return <= -100%')
    # At decision t, the first delayed execution interval is stored on row t.
    return np.expm1(np.log1p(x).iloc[::-1].rolling(horizon, min_periods=horizon).sum().iloc[::-1])


def feature_frame(d: pd.DataFrame, min_history: int) -> pd.DataFrame:
    close = pd.to_numeric(d.close, errors='raise').where(d.complete_kline.astype(bool))
    f = pd.DataFrame({'dt': pd.to_datetime(d.dt, utc=True), 'symbol': d.symbol, 'close': close})
    for n in (1, 5, 20, 60, 120, 200):
        # Require EVERY intermediate observation: no endpoint-only cross-gap momentum.
        good = close.notna().rolling(n + 1, min_periods=n + 1).sum().eq(n + 1)
        f[f'mom{n}'] = close.pct_change(n, fill_method=None).where(good)
    one = close.pct_change(fill_method=None)
    for n in (10, 30, 60, 200):
        f[f'vol{n}'] = one.rolling(n, min_periods=n).std()
    for n in (20, 50, 100, 200):
        f[f'dist{n}'] = close / close.rolling(n, min_periods=n).mean() - 1
    f['range'] = (d.high - d.low) / close
    lv = np.log1p(d.quote_volume.where(d.complete_kline))
    sd = lv.rolling(30, min_periods=30).std().replace(0, np.nan)
    f['vol_z'] = (lv - lv.rolling(30, min_periods=30).mean()) / sd
    f['premium'] = d.premium.where(d.complete_premium.astype(bool))
    f['funding'] = d.funding.where(d.complete_funding.astype(bool))
    mean = close.rolling(200, min_periods=200).mean()
    f['sma_signal'] = np.sign(close - mean)  # equal SMA means CASH, not missing
    f['feature_ready'] = close.notna().rolling(min_history, min_periods=min_history).sum().eq(min_history)
    f['decision_available_at'] = f.dt + pd.Timedelta(days=1)
    return f


def make_labels() -> dict:
    manifest = verify_dataset()
    scale = funding_scale()
    h = int(E('HORIZON_DAYS'))
    history = max(int(E('MIN_HISTORY_DAYS')), int(E('LOOKBACK_DAYS')))
    weight = float(E('LABEL_WEIGHT'))
    if not 0 < weight <= .3:
        raise ValueError('LABEL_WEIGHT must be in (0, .30]')
    source_sha = sha256(REPORTS / 'DATASET_MANIFEST.json')
    scenario = 'raw_fraction' if scale == 1 else 'raw_percent'
    outdir = DATA / 'labels' / scenario
    rows = []
    paths = []
    for symbol in symbols():
        d = read_table(DATA / 'normalized' / (symbol + '_daily' + suffix())).reset_index(drop=True)
        f = feature_frame(d, history)
        signals = {'sma': f.sma_signal.to_numpy(float), 'hold': np.ones(len(f)), 'cash': np.zeros(len(f))}
        for name, signal in signals.items():
            r = continuous_expert_returns(d, signal, weight, scale, side_cost())
            f[name + '_daily_return'] = r
            f['u_' + name] = future_compound(r, h)
        f['y_sma_vs_hold'] = f.u_sma - f.u_hold
        f['y_cash_vs_hold'] = f.u_cash - f.u_hold
        f['label_end_at'] = f.dt + pd.Timedelta(days=h + 1) + pd.Timedelta(microseconds=EXEC_OFFSET_US)
        f['label_ready'] = f[['y_sma_vs_hold', 'y_cash_vs_hold']].notna().all(axis=1)
        # Feature readiness never depends on whether a FUTURE label is complete.
        f['feature_ready'] &= f.dt.ge(pd.Timestamp(E('START_DATE'), tz='UTC'))
        path = write_table(f, outdir / symbol)
        paths.append({'symbol': symbol, 'path': str(path), 'sha256': sha256(path)})
        row = {'symbol': symbol, 'feature_ready_rows': int(f.feature_ready.sum()),
               'mature_training_rows': int((f.feature_ready & f.label_ready).sum()),
               'inference_rows_without_mature_labels': int((f.feature_ready & ~f.label_ready).sum())}
        rows.append(row)
        log(f'LABEL {symbol} {row}')
    result = dict(status='CONDITIONAL_PROXY_LABELS_NOT_REPOSITORY_U', scenario=scenario,
                  funding_rate_scale=scale, rate_unit_certified=False, label_weight=weight,
                  horizon=h, source_manifest_sha256=source_sha, research_config=research_config(), files=paths, audit=rows,
                  label_semantics='H delayed-execution returns of continuous daily-rebalanced expert; entry/turnover paid; no H-boundary liquidation; gaps invalidate label',
                  exact_minute_wallet_equivalent=False)
    dump(result, outdir / 'LABEL_MANIFEST.json')
    atomic_text(REPORTS / f'expert_label_audit_{scenario}.csv', pd.DataFrame(rows).to_csv(index=False))
    return result
