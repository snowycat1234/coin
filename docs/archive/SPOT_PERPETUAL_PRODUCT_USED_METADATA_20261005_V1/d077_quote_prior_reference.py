"""Finite ordinary module comparison against exact pre-change Spot source."""
from __future__ import annotations

import hashlib
import importlib.util
import json
import math
from pathlib import Path
import resource
import subprocess
import sys
import time

import numpy as np
import polars as pl

from quant import backtest as current

ROOT = Path('/mnt/d/codex/coin')
STATE = Path('/home/xflops/coin-state/d077-quote-prior-reference-20261005-v1')
PRIOR = '4246975'
EXPECTED_PRIOR_SHA = 'ee333d4e5cbadb489e5d467619d0872f78ccb2d86d8b5f46eacc69cb63f9829a'
START = 1_640_995_200_000_000
MINUTE = 60_000_000
TOL = 1e-10


def sha_bytes(value):
    return hashlib.sha256(value).hexdigest()


def fixture(symbols, volume):
    minute = pl.concat([pl.DataFrame({'symbol': [s] * 90,
        'open_us': np.arange(90, dtype=np.int64) * MINUTE + START,
        'open': [100.0] * 90, 'close': [100.0] * 90,
        'quote_volume': [volume] * 90}) for s in symbols])
    bars = pl.DataFrame([{'symbol': s, 'available_us': START + t * MINUTE,
        'close_us': START + t * MINUTE} for s in symbols for t in (15, 30, 45, 60)])
    return bars, minute


def target(rows):
    return pl.DataFrame([{'symbol': s, 'available_us': START + t * MINUTE,
        'target_weight': w} for t, s, w in rows])


def compare(left, right, key, comparisons):
    if isinstance(left, dict):
        if left.keys() != right.keys():
            raise AssertionError('mapping field mismatch ' + key)
        for name in left:
            compare(left[name], right[name], key + '.' + name, comparisons)
    elif isinstance(left, (list, tuple)):
        if len(left) != len(right):
            raise AssertionError('sequence length mismatch ' + key)
        for i, (a, b) in enumerate(zip(left, right, strict=True)):
            compare(a, b, f'{key}[{i}]', comparisons)
    elif isinstance(left, float):
        if not (math.isfinite(left) and math.isfinite(right)):
            raise AssertionError('nonfinite comparison ' + key)
        gap = abs(left - right)
        comparisons['float_checks'] += 1
        comparisons['max_absolute_float_error'] = max(comparisons['max_absolute_float_error'], gap)
        if gap > TOL:
            raise AssertionError(f'{key}: {left} != {right}')
    else:
        comparisons['exact_checks'] += 1
        if left != right:
            raise AssertionError(f'{key}: {left!r} != {right!r}')


def main():
    started = time.perf_counter()
    STATE.mkdir(parents=True, exist_ok=False)
    prior_bytes = subprocess.check_output(['git', '-C', str(ROOT), 'show',
        PRIOR + ':src/quant/backtest.py'])
    prior_sha = sha_bytes(prior_bytes)
    if prior_sha != EXPECTED_PRIOR_SHA:
        raise AssertionError('prior source SHA mismatch')
    source = STATE / 'prior_backtest_4246975.py'
    source.write_bytes(prior_bytes)
    test_bytes = (ROOT / 'tests/test_spot_received_asset_interface.py').read_bytes()
    (STATE / 'accepted_eight_test_source.py').write_bytes(test_bytes)
    # Ordinary separate module load of the exact historical file, no AST patches.
    name = 'coin_d077_prior_backtest_reference'
    spec = importlib.util.spec_from_file_location(name, source)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    cfg_common = {'target_annual_vol': None, 'min_notional': 0,
                  'lot_step_by_symbol': {}, 'latency_minutes': 1}
    experiments = [
        ('PARTIAL_FEES_EXPIRY', ('BTCUSDT',), 10_000.,
         [(15, 'BTCUSDT', .3), (30, 'BTCUSDT', 0)], False),
        ('TWO_SHARED_CAPITAL_TARGET_CHANGE', ('BTCUSDT', 'ETHUSDT'), 10_000_000.,
         [(15, 'BTCUSDT', .3), (15, 'ETHUSDT', .3),
          (30, 'BTCUSDT', .1), (30, 'ETHUSDT', .3),
          (45, 'BTCUSDT', .3), (45, 'ETHUSDT', .1),
          (60, 'BTCUSDT', 0), (60, 'ETHUSDT', 0)], False),
        ('TWO_DEFAULT_TERMINAL_ONE_ATTEMPT', ('BTCUSDT', 'ETHUSDT'), 10_000_000.,
         [(15, 'BTCUSDT', .3), (15, 'ETHUSDT', .3)], True),
    ]
    results = []
    for identity, symbols, volume, rows, liquidate in experiments:
        bars, minutes = fixture(symbols, volume)
        targets = target(rows)
        params = {**cfg_common, 'liquidate_at_end': liquidate}
        old = module.run_backtest(bars, minutes, targets, module.BacktestConfig(**params))
        new = current.run_backtest(bars, minutes, targets, current.BacktestConfig(**params))
        comparisons = {'float_checks': 0, 'exact_checks': 0, 'max_absolute_float_error': 0.0}
        for field in ('orders', 'trades', 'daily_nav', 'round_trips'):
            a, b = getattr(old, field), getattr(new, field)
            if a.schema != b.schema:
                raise AssertionError('default QUOTE schema changed ' + field)
            compare(a.to_dicts(), b.to_dicts(), field, comparisons)
        # Existing summary fields are all required; new explanatory metadata is allowed.
        if not old.summary.keys() <= new.summary.keys():
            raise AssertionError('old summary field removed')
        compare(old.summary, {k: new.summary[k] for k in old.summary}, 'summary', comparisons)
        results.append({'id': identity, 'status': 'PASS', 'trades': new.trades.height,
            'orders': new.orders.height, 'added_summary_fields': sorted(new.summary.keys() - old.summary.keys()),
            **comparisons})
    symbols = ('BTCUSDT', 'ETHUSDT', 'SOLUSDT')
    bars, minutes = fixture(symbols, 10_000_000.)
    multi = current.run_backtest(bars, minutes,
        target([(15, s, .3) for s in symbols] + [(30, s, 0) for s in symbols]),
        current.BacktestConfig(**cfg_common, fee_settlement='RECEIVED_ASSET'))
    cash = 10_000.
    inventory = {s: 0. for s in symbols}
    for row in multi.trades.iter_rows(named=True):
        q, fill = row['gross_quantity'], row['fill_price']
        if row['side'] == 'buy':
            inventory[row['symbol']] += q * .999
            cash -= q * fill
        else:
            if q > inventory[row['symbol']] + 1e-10:
                raise AssertionError('N-asset Spot oversold inventory')
            inventory[row['symbol']] -= q
            cash += q * fill * .999
        if abs(cash - row['cash_after']) > 1e-8 or cash < -1e-8:
            raise AssertionError('N-asset shared capital mismatch')
        if row['asset_weight_after'] > .3 + 1e-9 or row['gross_weight_after'] > .6 + 1e-9:
            raise AssertionError('N-asset postcost cap breached')
    if set(multi.trades['symbol'].to_list()) != set(symbols):
        raise AssertionError('not all three symbols actually traded')
    if abs(multi.summary['final_nav'] - (cash + 100 * sum(inventory.values()))) > 1e-8:
        raise AssertionError('N-asset terminal NAV not conserved')
    n_case = {'id': 'THREE_SYMBOLS_RECEIVED_SHARED_ACCOUNT', 'status': 'PASS',
        'symbols': list(symbols), 'actual_trades': multi.trades.height,
        'shared_cash': cash, 'terminal_inventory': inventory,
        'max_weight': multi.summary['max_observed_weight'],
        'max_gross': multi.summary['max_observed_gross']}
    payload = {'status': 'PASS_EXACT_PRIOR_DEFAULT_QUOTE_AND_CURRENT_N_ASSET_FIXTURES',
        'prior_git_ref': PRIOR, 'prior_source_sha256': prior_sha,
        'current_source_sha256': sha_bytes((ROOT / 'src/quant/backtest.py').read_bytes()),
        'accepted_eight_test_source_sha256': sha_bytes(test_bytes),
        'prior_source_path': str(source), 'absolute_float_tolerance': TOL,
        'prior_quote_cases': results, 'new_N_asset_case': n_case,
        'elapsed_seconds': time.perf_counter() - started,
        'peak_RSS_bytes': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024,
        'scope': 'Small fixtures only; historical source ordinary importlib module, no AST or function-copy adapter. No market replay/old adapter pin tests/locked/new data/orders.'}
    with (STATE / 'RESULT.json').open('x', encoding='utf8') as stream:
        json.dump(payload, stream, indent=2, allow_nan=False)
        stream.write('\n')
    print(json.dumps({'status': payload['status'], 'path': str(STATE / 'RESULT.json'),
        'quote_cases': len(results), 'N_asset_trades': multi.trades.height}))


if __name__ == '__main__':
    main()
