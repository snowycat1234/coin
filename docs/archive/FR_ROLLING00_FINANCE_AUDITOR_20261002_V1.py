"""Independent arithmetic on actual closed diagnostic ledgers; never fit/evaluate models."""
import argparse
from datetime import UTC, datetime
import hashlib
import json
import math
from pathlib import Path
import resource
import time

import polars as pl

ROOT = Path('/mnt/d/codex/coin')
STATE = Path('/home/xflops/coin-state')
IDS = ('RIDGE-1', 'XGB-S', 'XGB-M', 'TCN-S', 'TCN-M', 'MLPLOB-1', 'TLOB-1',
       'TS2VEC-LINEAR-1', 'TS2VEC-LGB-1', 'RIVER-1')
def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()
def close(actual, expected, label, tolerance=1e-6):
    if not math.isfinite(actual) or abs(actual - expected) > tolerance:
        raise ValueError(f'{label}: actual={actual}, expected={expected}')


def scenario(trades, daily, summary, spread):
    cash, quantities = 10000., {'spot_BTCUSDT': 0., 'spot_ETHUSDT': 0.}
    opened, gross, fees, extra, notionals = {}, 0., 0., 0., 0.
    cursor, closed, max_cash_error = 0, 0, 0.
    previous_nav = 10000.
    for day in daily:
        day_fee, day_extra, day_notional = 0., 0., 0.
        while cursor < len(trades) and trades[cursor]['event_us'] < day['valuation_us']:
            row = trades[cursor]
            symbol, key = row['symbol'], (row['sample_id'], row['symbol'])
            if row['event_us'] <= row['decision_us']:
                raise ValueError('Fill must follow the decision')
            notional = row['quantity'] * row['price_proxy']
            fee, cost = notional * .001, notional * (8 + spread) / 20000
            close(row['reference_notional'], notional, 'reference notional')
            close(row['fee'], fee, 'actual fee')
            close(row['execution_cost'], cost, 'spread plus slippage')
            if row['side'] == 'buy':
                if symbol in (k[1] for k in opened) or key in opened:
                    raise ValueError('Overlapping position')
                opened[key] = row
                cash -= notional + fee + cost
                quantities[symbol] += row['quantity']
                if row['gross_weight_after'] > .6 + 1e-9 or row['symbol_weight_after'] > .3 + 1e-9:
                    raise ValueError('Actual new buy exceeds original allocation caps')
            elif row['side'] == 'sell':
                buy = opened.pop(key)
                close(row['quantity'], buy['quantity'], 'paired traded quantity', 1e-10)
                if row['event_us'] <= buy['event_us']:
                    raise ValueError('Exit must follow entry')
                gross += row['quantity'] * (row['price_proxy'] - buy['price_proxy'])
                cash += notional - fee - cost
                quantities[symbol] -= row['quantity']
                closed += 1
            else:
                raise ValueError('Unknown trade side')
            max_cash_error = max(max_cash_error, abs(cash - row['cash_after']))
            close(row['cash_after'], cash, 'trade cash ledger')
            if cash < -1e-7:
                raise ValueError('Negative cash')
            fees += fee
            extra += cost
            notionals += notional
            day_fee += fee
            day_extra += cost
            day_notional += notional
            cursor += 1
        nav = cash
        for asset in ('BTC', 'ETH'):
            quantity = quantities[f'spot_{asset}USDT']
            close(day[f'{asset}_quantity'], quantity, 'daily quantity', 1e-10)
            available, mark = day[f'{asset}_mark_available_us'], day[f'{asset}_mark_price']
            if available is not None and available > day['valuation_us']:
                raise ValueError('Future valuation observation')
            if quantity and mark is None:
                raise ValueError('Missing mark for actual position')
            nav += quantity * (mark or 0.)
        close(day['cash'], cash, 'daily cash')
        close(day['nav'], nav, 'daily independently marked NAV')
        close(day['fees'], day_fee, 'daily fee')
        close(day['execution_costs'], day_extra, 'daily spread/slippage')
        close(day['turnover'], day_notional / previous_nav, 'daily turnover', 1e-10)
        close(day['cumulative_cost'], fees + extra, 'cumulative actual cost')
        close(day['gross_pnl'], nav - 10000. + fees + extra, 'daily gross-cost-net identity')
        previous_nav = nav
    if cursor != len(trades) or opened or any(abs(q) > 1e-10 for q in quantities.values()):
        raise ValueError('All actual fills and positions must be closed within final valuation')
    close(summary['final_nav'], cash, 'final cash NAV')
    close(summary['gross_pnl'], gross, 'closed-pair gross profit')
    close(summary['fees'], fees, 'summary fees')
    close(summary['execution_costs'], extra, 'summary spread/slippage')
    close(summary['cost'], fees + extra, 'summary all costs')
    close(summary['net_pnl'], gross - fees - extra, 'independent gross-cost-net profit')
    close(summary['net_proxy_return'], (cash - 10000.) / 10000., 'net return', 1e-10)
    close(summary['gross_proxy_return'], gross / 10000., 'gross return', 1e-10)
    close(summary['turnover'], sum(row['turnover'] for row in daily), 'turnover sum', 1e-10)
    if summary['trade_count'] != len(trades) or summary['closed_roundtrips'] != closed:
        raise ValueError('Actual trade counts differ')
    return {'fills': len(trades), 'closed_roundtrips': closed,
            'gross_pnl_usdt': gross, 'fee_usdt': fees,
            'spread_usdt': notionals * spread / 20000.,
            'slippage_usdt': notionals * 8 / 20000., 'net_pnl_usdt': cash - 10000.,
            'max_cash_reconstruction_error_usdt': max_cash_error,
            'gross_cost_net_error_usdt': abs(gross - fees - extra - (cash - 10000.)),
            'future_valuation_observations': 0, 'final_open_positions': 0}


parser = argparse.ArgumentParser()
parser.add_argument('--run-dir', type=Path, required=True)
parser.add_argument('--output', type=Path, required=True)
parser.add_argument('--require-ten', action='store_true')
args = parser.parse_args()
started = time.monotonic()
run, output = args.run_dir.resolve(), args.output.resolve()
if not run.is_relative_to(STATE) or not output.parent.is_relative_to(STATE):
    raise ValueError('Independent STATE paths only')
binding = json.loads((run / 'RUN_BINDING.json').read_text())
binding_sha = hashlib.sha256(json.dumps(binding, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()
models, checked_files, missing = {}, {}, []
for model in IDS:
    receipt_path = run / 'rolling_00' / model / 'COMPLETE.json'
    if not receipt_path.is_file():
        missing.append(model)
        continue
    receipt = json.loads(receipt_path.read_text())
    if receipt['status'] != 'COMPLETE' or receipt['binding_sha256'] != binding_sha:
        raise ValueError('Completion provenance changed')
    checked_files[str(receipt_path)] = sha(receipt_path)
    scenarios = {}
    for spread in (2, 4, 8):
        pair = {}
        for kind in ('daily', 'trades'):
            relative = next(p for p in receipt['artifacts'] if p.endswith(f'/{kind}-{spread}.parquet'))
            path = run / relative
            actual_sha = sha(path)
            if actual_sha != receipt['artifacts'][relative]:
                raise ValueError('Actual financial artifact SHA changed')
            checked_files[str(path)] = actual_sha
            pair[kind] = pl.read_parquet(path).to_dicts()
        scenarios[str(spread)] = scenario(pair['trades'], pair['daily'], receipt['evaluation']['economics'][str(spread)], spread)
    models[model] = scenarios
if args.require_ten and missing:
    raise ValueError(f'All ten required; missing {missing}')
result = {'status': 'ACTUAL_CLOSED_DIAGNOSTIC_FINANCE_ARITHMETIC_VERIFIED',
          'created_utc': datetime.now(UTC).isoformat(), 'models_checked': len(models),
          'formal_six_fold_complete': False, 'candidate_qualification': False,
          'remaining_models_not_accepted': missing, 'binding_sha256': binding_sha,
          'models': models, 'actual_financial_file_hashes': checked_files,
          'auditor_sha256': sha(Path(__file__)), 'elapsed_seconds': time.monotonic() - started,
          'auditor_peak_RAM_bytes': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024,
          'scope': 'Independent arithmetic on saved actual fills and observed daily marks; no model fitting, no replacement evaluator, no outcome-based selection.'}
with output.open('x') as writer:
    json.dump(result, writer, indent=2, allow_nan=False)
    writer.write('\n')
print(json.dumps({'status': result['status'], 'models_checked': len(models),
                  'cost_scenarios': len(models) * 3, 'peak_RAM_bytes': result['auditor_peak_RAM_bytes']}))
