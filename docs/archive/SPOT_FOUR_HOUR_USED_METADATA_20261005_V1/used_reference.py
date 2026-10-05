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
        actual = {'status': 'PASS_SAVED_MANUAL_COMPONENT_TARGET_MIX',
            'input_sha256': sha(args.input), 'target_rows': saved.height,
            'target_max_error': gap, 'raw_target_max_error': raw_gap,
            'scope': 'Normal component reuse, independent manual mixture; no independent vendor signal implementation.'}
    result = {'status': 'PASS_PRIOR_DAILY_MODULE_COMPATIBILITY', 'prior_git_ref': '72e1a8b',
        'prior_source_sha256': sha(old_path), 'current_source_sha256': sha(shared.__file__),
        'daily_default_cases': cases, 'actual_target_reference': actual,
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
