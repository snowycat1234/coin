"""Ordinary prior default compatibility and scalar macro-filter target audit."""
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
from scripts.investment import donchian_daily_pool_target as current
from scripts.investment import public_sma_perpetual as shared

ROOT = Path('/mnt/d/codex/coin')
DAY = 86_400_000_000
FOUR = DAY // 6


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def compare(a, b):
    if isinstance(a, dict):
        if a.keys() != b.keys():
            raise AssertionError('default metadata keys differ')
        for k in a:
            compare(a[k], b[k])
    elif isinstance(a, (tuple, list)):
        if len(a) != len(b):
            raise AssertionError('default shape differs')
        for x, y in zip(a, b, strict=True):
            compare(x, y)
    elif isinstance(a, float):
        if not np.isfinite(a) or not np.isfinite(b) or abs(a - b) > 1e-12:
            raise AssertionError('default numeric differs')
    elif a != b:
        raise AssertionError('default value differs')


def read_frame(artifact):
    if sha(artifact['path']) != artifact['sha256']:
        raise AssertionError('artifact hash differs')
    return pl.read_parquet(artifact['path'])


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--output-dir', required=True)
    p.add_argument('--input')
    args = p.parse_args()
    started = time.perf_counter()
    output = Path(args.output_dir)
    if not output.resolve().is_relative_to(Path('/home/xflops/coin-state')):
        raise ValueError('D-hosted STATE required')
    output.mkdir(parents=True, exist_ok=False)
    old_sources = {}
    modules = {}
    for filename in ('public_sma_perpetual', 'donchian_daily_pool_target'):
        source = subprocess.check_output(['git', '-C', str(ROOT), 'show',
            '7a239eb:scripts/investment/' + filename + '.py'])
        path = output / ('prior_' + filename + '.py')
        path.write_bytes(source)
        old_sources[filename] = {'path': str(path), 'sha256': sha(path)}
        modules[filename] = load('coin_d081_prior_' + filename, path)
    old = modules['donchian_daily_pool_target']
    old.shared = modules['public_sma_perpetual']
    fixture = load('coin_d081_fixture', ROOT / 'tests/test_four_hour_daily_trend_filter.py')
    common = dict(symbols=('BTCUSDT',), allocation='ACTIVE_EQUAL', exit_period=10, reentry_period=20)
    cases = []
    for interval in (1440, 240):
        if interval == 240:
            signal = fixture.signal(ending=(101., 70., 105.))
            risk = fixture.candles(DAY, [80.] * 200)
            decisions = np.arange(fixture.AT, fixture.AT + 3 * FOUR, FOUR, dtype=np.int64)
            options = dict(signal_interval_minutes=240, risk_bars=risk)
        else:
            signal = fixture.candles(DAY, [80.] * 199 + [101., 70., 105.], end=fixture.AT + 2 * DAY)
            decisions = np.arange(fixture.AT, fixture.AT + 3 * DAY, DAY, dtype=np.int64)
            options = {}
        a, am = old.fixed_targets(signal, decisions, 'LONG_ONLY', **common, **options)
        b, bm = current.fixed_targets(signal, decisions, 'LONG_ONLY', **common, **options)
        if a.schema != b.schema:
            raise AssertionError('default dataframe schema differs')
        compare(a.to_dicts(), b.to_dicts())
        if not am.keys() <= bm.keys():
            raise AssertionError('prior metadata dropped')
        compare(am, {k: bm[k] for k in am})
        cases.append({'signal_interval_minutes': interval, 'rows': a.height, 'status': 'PASS',
            'added_metadata_fields': sorted(bm.keys() - am.keys())})
    actual = None
    if args.input:
        payload = json.loads(Path(args.input).read_text(encoding='utf8'))
        signal = read_frame(payload['four_hour_bars'])
        risk = read_frame(payload['daily_bars'])
        saved = read_frame(payload['target_artifact'])
        symbols = payload.get('symbols', payload['cases'][0]['symbols'])
        times = np.asarray(saved['available_us'].unique(maintain_order=True).to_list(), dtype=np.int64)
        if not np.all(np.diff(times) == FOUR):
            raise AssertionError('saved4h calendar incomplete')
        sc = {s: signal.filter(pl.col('symbol') == s).sort('close_us') for s in symbols}
        dc = {s: risk.filter(pl.col('symbol') == s).sort('close_us') for s in symbols}
        states = dict.fromkeys(symbols, False)
        manual, manual_raw = [], []
        entries, exits = dict.fromkeys(symbols, 0), dict.fromkeys(symbols, 0)
        daily_context_checks = 0
        for t in times:
            day = int(t // DAY * DAY)
            returns = []
            for s in symbols:
                signal_past = sc[s].filter((pl.col('close_us') <= t)
                    & (pl.col('available_us') <= t)).tail(200)
                daily_past = dc[s].filter((pl.col('close_us') <= day)
                    & (pl.col('available_us') <= t)).tail(200)
                if (signal_past.height != 200 or daily_past.height != 200
                        or signal_past['close_us'][-1] != t or daily_past['close_us'][-1] != day
                        or not np.all(np.diff(signal_past['close_us']) == FOUR)
                        or not np.all(np.diff(daily_past['close_us']) == DAY)):
                    raise AssertionError('actual context missing; reference cannot impute')
                close = float(signal_past['close'][-1])
                if states[s]:
                    if close < min(signal_past['low'][-11:-1]):
                        states[s] = False
                        exits[s] += 1
                elif close > max(signal_past['high'][-21:-1]) and close > float(daily_past['close'].mean()):
                    states[s] = True
                    entries[s] += 1
                prices = daily_past.tail(31)['close'].to_numpy()
                returns.append(np.diff(prices) / prices[:-1])
                daily_context_checks += 1
            matrix = np.column_stack(returns)
            centered = matrix - matrix.mean(axis=0)
            covariance = centered.T @ centered / 29 * 365
            hraw = np.full(len(symbols), min(.3, .6 / len(symbols)))
            active = sum(states.values())
            draw = np.array([min(.3, .6 / active) if states[s] else 0. for s in symbols]) if active else np.zeros(len(symbols))
            def scale(raw):
                sigma = float(np.sqrt(max(0., raw @ covariance @ raw)))
                return raw * min(1., .1 / sigma) if sigma else raw
            manual.extend(.5 * scale(hraw) + .5 * scale(draw))
            manual_raw.extend(.5 * hraw + .5 * draw)
        expected_keys = [(int(t), s) for t in times for s in symbols]
        if list(zip(saved['available_us'], saved['symbol'])) != expected_keys:
            raise AssertionError('target order differs')
        gap = float(np.max(abs(np.array(manual) - saved['target_weight'].to_numpy())))
        rawgap = float(np.max(abs(np.array(manual_raw) - saved['raw_signed_target'].to_numpy())))
        if max(gap, rawgap) > 1e-12:
            raise AssertionError(f'independent macro state/covariance target mismatch {gap}/{rawgap}')
        actual = {'status': 'PASS_SCALAR_DAILY_MACRO_ENTRY_EXIT10_AND_DAILY_GRAM_BLEND',
            'input_sha256': sha(args.input), 'target_rows': saved.height,
            'target_max_error': gap, 'raw_target_max_error': rawgap,
            'scalar_signal_entries': entries, 'scalar_signal_exits': exits,
            'actual_completed_daily_context_checks': daily_context_checks,
            'scope': 'Independent prior20/SMA200daily entry, held prior10 exit, daily centered covariance and manual halfHOLDcarry mixture. No source-minute re-QA or native execution proof.'}
    result = {'status': 'PASS_PRIOR_DEFAULT_AND_OPTIONAL_MACRO_REFERENCE',
        'prior_sources': old_sources, 'current_sources': {
            'shared': sha(shared.__file__), 'donchian': sha(current.__file__)},
        'prior_default_cases': cases, 'actual_reference': actual,
        'elapsed_seconds': time.perf_counter() - started,
        'peak_RSS_bytes': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024,
        'absolute_float_tolerance': 1e-12, 'market_replays': 0, 'new_data': False,
        'locked_consumed': False, 'orders_sent': False, 'AST_modified': False}
    with (output / 'RESULT.json').open('x', encoding='utf8') as stream:
        json.dump(result, stream, indent=2, allow_nan=False)
        stream.write('\n')
    print(json.dumps({'status': result['status'], 'result': str(output / 'RESULT.json')}))


if __name__ == '__main__':
    main()
