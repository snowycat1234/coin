"""Saved daily target audit: normal components, manual blend, past-only covariance."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import resource
import time

import numpy as np
import polars as pl

from scripts.investment import donchian_daily_pool_target as donchian
from scripts.investment import hold_donchian_blend_target as blend
from scripts.investment import vol_managed_perpetual_target as hold

DAY = 86_400_000_000
TOL = 1e-12


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def read_frame(artifact):
    if sha(artifact['path']) != artifact['sha256']:
        raise AssertionError('pinned daily/target artifact changed')
    frame = pl.read_parquet(artifact['path'])
    if artifact.get('rows', frame.height) != frame.height:
        raise AssertionError('artifact row count differs')
    return frame


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    began = time.perf_counter()
    payload = json.loads(Path(args.input).read_text(encoding='utf8'))
    bars, saved = read_frame(payload['daily_bars']), read_frame(payload['target_artifact'])
    symbols = payload['symbols'] if 'symbols' in payload else payload['cases'][0]['symbols']
    decisions = np.array(saved['available_us'].unique(maintain_order=True).to_list(), dtype=np.int64)
    if len(symbols) != len(set(symbols)) or not symbols or not np.all(np.diff(decisions) == DAY):
        raise AssertionError('ordered symbols or complete daily decision calendar invalid')
    expected_keys = [(int(t), s) for t in decisions for s in symbols]
    if list(zip(saved['available_us'], saved['symbol'])) != expected_keys:
        raise AssertionError('target rows differ from configured time-major symbol identity')
    h, hm = hold.fixed_targets(bars, decisions, 'LONG_ONLY', symbols=symbols,
        allocation='EQUAL', annual_vol_target=.10)
    d, dm = donchian.fixed_targets(bars, decisions, 'LONG_ONLY', symbols=symbols,
        allocation='ACTIVE_EQUAL', exit_period=10, reentry_period=20)
    for column in ('available_us', 'symbol', 'mode', 'eligibility_reason'):
        if h[column].to_list() != d[column].to_list() or h[column].to_list() != saved[column].to_list():
            raise AssertionError('component calendar or eligibility mismatch ' + column)
    manual = .5 * h['target_weight'].to_numpy() + .5 * d['target_weight'].to_numpy()
    manual_raw = .5 * h['raw_signed_target'].to_numpy() + .5 * d['raw_signed_target'].to_numpy()
    target_gap = float(np.max(np.abs(manual - saved['target_weight'].to_numpy())))
    raw_gap = float(np.max(np.abs(manual_raw - saved['raw_signed_target'].to_numpy())))
    if max(target_gap, raw_gap) > TOL:
        raise AssertionError('manual half/half component mixture differs from saved target')
    contexts = {s: bars.filter(pl.col('symbol') == s).sort('close_us') for s in symbols}
    sigma_max_error = component_target_error = 0.
    covariance_checks = 0
    for i, (hr, dr) in enumerate(zip(hm['risk'], dm['risk'], strict=True)):
        decision = int(decisions[i])
        if (hr['decision_us'] != decision or dr['decision_us'] != decision
                or hr['symbol_order'] != symbols or dr['symbol_order'] != symbols
                or hr['covariance_symbol_order'] != dr['covariance_symbol_order']):
            raise AssertionError('component decision/covariance order differs')
        cov_symbols = hr['covariance_symbol_order']
        if not cov_symbols:
            continue
        returns = []
        for s in cov_symbols:
            available = contexts[s].filter((pl.col('close_us') <= decision)
                & (pl.col('available_us') <= decision)).tail(200)
            if available.height != 200 or available['close_us'][-1] != decision:
                raise AssertionError('incomplete past200 covariance eligibility')
            if not np.all(np.diff(available['close_us'].to_numpy()) == DAY):
                raise AssertionError('noncontinuous past200 warmup')
            past31 = available.tail(31)
            closes = past31['close'].to_numpy()
            returns.append(np.diff(closes) / closes[:-1])
        matrix = np.column_stack(returns)
        # Explicit centered Gram covariance rather than producer np.cov helper.
        centered = matrix - matrix.mean(axis=0)
        covariance = centered.T @ centered / 29 * 365
        for frame, meta in ((h, hr), (d, dr)):
            raw = np.array([float(frame['raw_signed_target'][i * len(symbols) + symbols.index(s)])
                for s in cov_symbols])
            raw = np.clip(raw, -.3, .3)
            if abs(raw).sum() > .6:
                raw *= .6 / abs(raw).sum()
            sigma = float(np.sqrt(max(0., raw @ covariance @ raw)))
            sigma_max_error = max(sigma_max_error,
                abs(sigma - meta['unscaled_signed_covariance_annual_vol']))
            expected = raw * min(1., .10 / sigma) if sigma > 0 else raw
            observed = np.array([float(frame['target_weight'][i * len(symbols) + symbols.index(s)])
                for s in cov_symbols])
            component_target_error = max(component_target_error, float(np.max(abs(expected - observed))))
            if meta['covariance_observations'] != 30 or meta['covariance_assets'] != len(cov_symbols):
                raise AssertionError('covariance observation count differs')
            covariance_checks += 1
    if max(sigma_max_error, component_target_error) > TOL:
        raise AssertionError('explicit centered past-only covariance calculation differs')
    cutoff = int(decisions[len(decisions) * 2 // 3])
    altered = bars.with_columns([
        pl.when(pl.col('available_us') > cutoff).then(pl.col(column) * 1.17)
        .otherwise(pl.col(column)).alias(column)
        for column in ('open', 'high', 'low', 'close')])
    perturbed, _ = blend.fixed_targets(altered, decisions, 'LONG_ONLY', symbols=symbols)
    early = saved.filter(pl.col('available_us') <= cutoff)
    altered_early = perturbed.filter(pl.col('available_us') <= cutoff)
    future_target_gap = float(np.max(abs(early['target_weight'].to_numpy()
        - altered_early['target_weight'].to_numpy())))
    future_raw_gap = float(np.max(abs(early['raw_signed_target'].to_numpy()
        - altered_early['raw_signed_target'].to_numpy())))
    if max(future_target_gap, future_raw_gap) > TOL:
        raise AssertionError('future daily bars changed early targets')
    late_changed = int(np.count_nonzero(abs(saved['target_weight'].to_numpy()
        - perturbed['target_weight'].to_numpy()) > TOL))
    result = {'status': 'PASS_SAVED_COMPONENT_BLEND_PAST_COVARIANCE_AND_FUTURE_BAR_PERTURBATION',
        'input_path': args.input, 'input_sha256': sha(args.input),
        'daily_bars': payload['daily_bars'], 'saved_targets': payload['target_artifact'],
        'symbols': symbols, 'decision_days': len(decisions), 'target_rows': saved.height,
        'manual_component_mix_max_error': target_gap, 'manual_raw_mix_max_error': raw_gap,
        'centered_covariance_checks': covariance_checks,
        'component_sigma_max_error': sigma_max_error, 'component_risk_target_max_error': component_target_error,
        'future_perturbation_cutoff_us': cutoff, 'future_OHLC_multiplier': 1.17,
        'earlier_target_rows_checked': early.height,
        'future_perturbation_early_target_max_error': future_target_gap,
        'future_perturbation_early_raw_max_error': future_raw_gap,
        'later_target_rows_actually_changed': late_changed,
        'absolute_float_tolerance': TOL,
        'elapsed_seconds': time.perf_counter() - began,
        'peak_RSS_bytes': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024,
        'scope': 'Reuses normal HOLD and Donchian signal components; independent manual mixture, centered covariance arithmetic and availability checks. This does not independently reimplement vendor signals, verify source-minute QA, or certify native Bybit, independent alpha or APR.',
        'new_fits': 0, 'new_market_replays': 0, 'new_data_or_API': False,
        'locked_consumed': False, 'orders_sent': False}
    output = Path(args.output)
    if not output.resolve().is_relative_to(Path('/home/xflops/coin-state')):
        raise ValueError('output must be in D-hosted STATE')
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open('x', encoding='utf8') as stream:
        json.dump(result, stream, indent=2, allow_nan=False)
        stream.write('\n')
    print(json.dumps({'status': result['status'], 'output': str(output),
        'decision_days': len(decisions), 'elapsed_seconds': result['elapsed_seconds']}))


if __name__ == '__main__':
    main()
