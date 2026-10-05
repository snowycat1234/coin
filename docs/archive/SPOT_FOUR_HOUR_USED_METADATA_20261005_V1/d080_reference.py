"""Finite ordinary-module daily compatibility and saved 4h/daily-risk audit."""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import resource
import subprocess
import sys
import time

import numpy as np
import polars as pl

from scripts.investment import public_sma_perpetual as shared
from scripts.investment import vol_managed_perpetual_target as hold
from scripts.investment import donchian_daily_pool_target as donchian

ROOT = Path('/mnt/d/codex/coin')
DAY = 86_400_000_000
FOUR = DAY // 6


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def artifact(value):
    if sha(value['path']) != value['sha256']:
        raise AssertionError('bound artifact changed')
    return pl.read_parquet(value['path'])


def compare(a, b, path='root'):
    if isinstance(a, dict):
        if a.keys() != b.keys():
            raise AssertionError('key mismatch ' + path)
        for k in a:
            compare(a[k], b[k], path + '.' + k)
    elif isinstance(a, (list, tuple)):
        if len(a) != len(b):
            raise AssertionError('length mismatch ' + path)
        for i, (x, y) in enumerate(zip(a, b, strict=True)):
            compare(x, y, path + f'[{i}]')
    elif isinstance(a, float):
        if not np.isfinite(a) or not np.isfinite(b) or abs(a - b) > 1e-12:
            raise AssertionError('float mismatch ' + path)
    elif a != b:
        raise AssertionError('value mismatch ' + path)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output-dir', required=True)
    parser.add_argument('--input')
    args = parser.parse_args()
    began = time.perf_counter()
    destination = Path(args.output_dir)
    if not destination.resolve().is_relative_to(Path('/home/xflops/coin-state')):
        raise ValueError('STATE required')
    destination.mkdir(parents=True, exist_ok=False)
    old_bytes = subprocess.check_output(['git', '-C', str(ROOT), 'show',
        '72e1a8b:scripts/investment/public_sma_perpetual.py'])
    old_path = destination / 'prior_daily_target_72e1a8b.py'
    old_path.write_bytes(old_bytes)
    name = 'coin_d080_prior_daily_reference'
    spec = importlib.util.spec_from_file_location(name, old_path)
    old = importlib.util.module_from_spec(spec)
    sys.modules[name] = old
    spec.loader.exec_module(old)
    test_spec = importlib.util.spec_from_file_location('coin_d080_fixture_source',
        ROOT / 'tests/test_four_hour_signal_daily_risk.py')
    fixture = importlib.util.module_from_spec(test_spec)
    test_spec.loader.exec_module(fixture)
    symbols = ('SOLUSDT', 'ETHUSDT', 'BTCUSDT')
    daily = fixture.bars(DAY, 210, fixture.AT + 5 * DAY, symbols=symbols)
    decisions = np.arange(fixture.AT, fixture.AT + 6 * DAY, DAY, dtype=np.int64)
    cases = []
    for allocation in ('EQUAL', 'ACTIVE_EQUAL', 'INVERSE_VOL_30D'):
        common = dict(symbols=symbols, direction_factory=fixture.AlwaysLong, allocation=allocation)
        a, am = old.fixed_targets(daily, decisions, 'LONG_ONLY', **common)
        b, bm = shared.fixed_targets(daily, decisions, 'LONG_ONLY', **common)
        if a.schema != b.schema:
            raise AssertionError('daily schema differs')
        compare(a.to_dicts(), b.to_dicts(), 'daily_targets')
        # New descriptive metadata can be added, old fields must remain identical.
        if not am.keys() <= bm.keys():
            raise AssertionError('daily prior metadata dropped')
        compare(am, {k: bm[k] for k in am}, 'daily_metadata')
        cases.append({'allocation': allocation, 'rows': a.height, 'status': 'PASS',
            'added_meta_fields': sorted(bm.keys() - am.keys())})
    _, four_meta = shared.fixed_targets(fixture.bars(FOUR, 200),
        np.array([fixture.AT], dtype=np.int64), 'LONG_ONLY',
        direction_factory=fixture.AlwaysLong, signal_interval_minutes=240,
        risk_bars=fixture.bars(DAY, 200))
    if (four_meta['close_then_wait_next_daily_decision_to_reenter'] is not False
            or four_meta['close_then_wait_next_four_hour_decision_to_reenter'] is not True
            or four_meta['covariance_return_interval_minutes'] != 1440):
        raise AssertionError('4h reentry and daily covariance metadata inaccurate')
    actual = None
    if args.input:
        payload = json.loads(Path(args.input).read_text(encoding='utf8'))
        risk = artifact(payload['daily_bars'])
        signal = artifact(payload['four_hour_bars'])
        saved = artifact(payload['target_artifact'])
        symbols = payload.get('symbols', payload['cases'][0]['symbols'])
        times = np.array(saved['available_us'].unique(maintain_order=True).to_list(), dtype=np.int64)
        if not np.all(np.diff(times) == FOUR):
            raise AssertionError('saved4hcalendar incomplete')
        day_times = np.arange(times[0] // DAY * DAY, times[-1] // DAY * DAY + DAY, DAY, dtype=np.int64)
        h, hm = hold.fixed_targets(risk, day_times, 'LONG_ONLY', symbols=symbols,
            allocation='EQUAL', annual_vol_target=.10)
        d, dm = donchian.fixed_targets(signal, times, 'LONG_ONLY', symbols=symbols,
            allocation='ACTIVE_EQUAL', exit_period=10, reentry_period=20,
            signal_interval_minutes=240, risk_bars=risk)
        lookup = {(r['available_us'], r['symbol']): r for r in h.iter_rows(named=True)}
        mix, rawmix = [], []
        for row in d.iter_rows(named=True):
            prior = lookup[(row['available_us'] // DAY * DAY, row['symbol'])]
            mix.append(.5 * prior['target_weight'] + .5 * row['target_weight'])
            rawmix.append(.5 * prior['raw_signed_target'] + .5 * row['raw_signed_target'])
        if list(zip(d['available_us'], d['symbol'])) != list(zip(saved['available_us'], saved['symbol'])):
            raise AssertionError('saved identity order differs')
        gap = float(np.max(abs(np.array(mix) - saved['target_weight'].to_numpy())))
        raw_gap = float(np.max(abs(np.array(rawmix) - saved['raw_signed_target'].to_numpy())))
        if max(gap, raw_gap) > 1e-12:
            raise AssertionError('manual dailyHOLDcarry+4hDonchian mixture mismatch')
        # Scalar original entry + explicit COIN exit10, no producer hooks used.
        signal_context = {s: signal.filter(pl.col('symbol') == s).sort('close_us') for s in symbols}
        risk_context = {s: risk.filter(pl.col('symbol') == s).sort('close_us') for s in symbols}
        states = dict.fromkeys(symbols, False)
        manual_full, manual_full_raw = [], []
        sigma_gap = 0.
        for ti, t in enumerate(times):
            day = int(t // DAY * DAY)
            returns = []
            for s in symbols:
                sc = signal_context[s].filter((pl.col('close_us') <= t)
                    & (pl.col('available_us') <= t)).tail(200)
                rc = risk_context[s].filter((pl.col('close_us') <= day)
                    & (pl.col('available_us') <= t)).tail(200)
                if (sc.height != 200 or rc.height != 200 or sc['close_us'][-1] != t
                        or rc['close_us'][-1] != day or not np.all(np.diff(sc['close_us']) == FOUR)
                        or not np.all(np.diff(rc['close_us']) == DAY)):
                    raise AssertionError('actual independent context incomplete; no implicit imputation')
                price = float(sc['close'][-1])
                if states[s]:
                    if price < min(sc['low'][-11:-1]):
                        states[s] = False
                elif price > max(sc['high'][-21:-1]) and price > float(sc['close'].mean()):
                    states[s] = True
                closes = rc.tail(31)['close'].to_numpy()
                returns.append(np.diff(closes) / closes[:-1])
            matrix = np.column_stack(returns)
            centered = matrix - matrix.mean(axis=0)
            covariance = centered.T @ centered / 29 * 365
            active = sum(states.values())
            raw = np.array([min(.3, .6 / active) if states[s] else 0. for s in symbols]) if active else np.zeros(len(symbols))
            sigma = float(np.sqrt(max(0., raw @ covariance @ raw)))
            weights = raw * min(1., .1 / sigma) if sigma else raw
            sigma_gap = max(sigma_gap, abs(sigma - dm['risk'][ti]['unscaled_signed_covariance_annual_vol']))
            for i, s in enumerate(symbols):
                prior = lookup[(day, s)]
                manual_full.append(.5 * prior['target_weight'] + .5 * weights[i])
                manual_full_raw.append(.5 * prior['raw_signed_target'] + .5 * raw[i])
        full_gap = float(np.max(abs(np.array(manual_full) - saved['target_weight'].to_numpy())))
        full_raw_gap = float(np.max(abs(np.array(manual_full_raw) - saved['raw_signed_target'].to_numpy())))
        if max(full_gap, full_raw_gap, sigma_gap) > 1e-12:
            raise AssertionError('scalar original signal/centered daily risk differs from saved 4h mixture')
        # Minute→4h OHLCV reduction: independent reshape of complete cached blocks.
        minutes = artifact(payload['market_minutes'])
        reduction_rows = 0
        reduction_gap = 0.
        for s in symbols:
            tape = minutes.filter(pl.col('symbol') == s).sort('open_us')
            clock = tape['open_us'].to_numpy()
            start_ix = int(np.searchsorted(clock, ((int(clock[0]) + FOUR - 1) // FOUR) * FOUR))
            tape = tape.slice(start_ix)
            count = tape.height // 240
            tape = tape.head(count * 240)
            times4 = tape['open_us'].to_numpy().reshape(count, 240)
            if not np.all(np.diff(times4, axis=1) == 60_000_000) or not np.all(times4[:, 0] % FOUR == 0):
                raise AssertionError('cached source minute blocks not complete4h')
            original = signal_context[s].filter(pl.col('open_us').is_in(times4[:, 0].tolist())).sort('open_us')
            if original.height != count:
                raise AssertionError('saved4h source clock missing cached block')
            for column, values in {
                    'open': tape['open'].to_numpy().reshape(count, 240)[:, 0],
                    'close': tape['close'].to_numpy().reshape(count, 240)[:, -1],
                    'high': tape['high'].to_numpy().reshape(count, 240).max(axis=1),
                    'low': tape['low'].to_numpy().reshape(count, 240).min(axis=1),
                    'volume': tape['volume'].to_numpy().reshape(count, 240).sum(axis=1)}.items():
                current_gap = float(np.max(abs(values - original[column].to_numpy())))
                reduction_gap = max(reduction_gap, current_gap)
                if not np.allclose(values, original[column].to_numpy(), rtol=1e-12, atol=1e-10):
                    raise AssertionError('independent source-minute reshape OHLCV differs ' + column)
            reduction_rows += count
        actual = {'status': 'PASS_SAVED_MANUAL_COMPONENT_TARGET_MIX',
            'input_sha256': sha(args.input), 'target_rows': saved.height,
            'target_max_error': gap, 'raw_target_max_error': raw_gap,
            'independent_scalar_signal_mix_max_error': full_gap,
            'independent_scalar_raw_mix_max_error': full_raw_gap,
            'centered_daily_risk_sigma_max_error': sigma_gap,
            'cached_minute_to_four_hour_reduction_rows': reduction_rows,
            'cached_minute_reduction_max_absolute_error': reduction_gap,
            'scope': 'Normal-component mixture crosscheck plus scalar original entry/SMA200 and COIN exit10 with centered daily covariance. Cached minute reshape checks overlapping 4h bars only; earlier warmup 4h source integrity remains runner responsibility.'}
    result = {'status': 'PASS_PRIOR_DAILY_MODULE_COMPATIBILITY', 'prior_git_ref': '72e1a8b',
        'prior_source_sha256': sha(old_path), 'current_source_sha256': sha(shared.__file__),
        'daily_default_cases': cases, 'actual_target_reference': actual,
        'current_four_hour_metadata_verified': True,
        'elapsed_seconds': time.perf_counter() - began,
        'peak_RSS_bytes': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024,
        'source_AST_modified': False, 'market_replays': 0, 'new_data': False,
        'orders_sent': False, 'locked_consumed': False}
    with (destination / 'RESULT.json').open('x', encoding='utf8') as stream:
        json.dump(result, stream, indent=2, allow_nan=False)
        stream.write('\n')
    print(json.dumps({'status': result['status'], 'path': str(destination / 'RESULT.json')}))


if __name__ == '__main__':
    main()
