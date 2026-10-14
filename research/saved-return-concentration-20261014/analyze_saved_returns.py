#!/usr/bin/env python3
"""Network-free arithmetic on six byte-pinned, public saved-result JSON files."""
from __future__ import annotations
import argparse
import csv
from datetime import datetime, timezone
from decimal import Decimal
import hashlib
import json
import math
from pathlib import Path
import resource
import signal
import time

DAY_US = 86_400_000_000
ROOT = Path(__file__).resolve().parent

def iso(us):
    return datetime.fromtimestamp(us / 1_000_000, timezone.utc).isoformat().replace('+00:00', 'Z')

def sha256(b):
    return hashlib.sha256(b).hexdigest()

def dump(path, obj):
    path.write_text(json.dumps(obj, indent=2, sort_keys=True, allow_nan=False) + '\n')

def return_metrics(daily, initial):
    if not daily:
        raise ValueError('empty input')
    n = len(daily)
    deltas = []
    for i, row in enumerate(daily):
        if not row['completed'] or row['stop_us'] is not None:
            raise ValueError('incomplete day')
        if row['end_us'] - row['start_us'] != DAY_US:
            raise ValueError('non-calendar-day interval')
        if i and daily[i-1]['end_us'] != row['start_us']:
            raise ValueError('gap/duplicate/unsorted interval')
        value = float(row['net_increment_USDT'])
        if not math.isfinite(value):
            raise ValueError('nonfinite increment')
        deltas.append(value)
    # fsum on each short prefix avoids drift and preserves the saved initial capital.
    nav = [initial] + [initial + math.fsum(deltas[:i]) for i in range(1, n+1)]
    if min(nav) <= 0:
        raise ValueError('nonpositive NAV cannot support log-return diagnostics')
    returns = [deltas[i] / nav[i] for i in range(n)]
    logs = [math.log1p(x) for x in returns]
    annual_log = math.fsum(logs)
    annual_return = nav[-1] / initial - 1
    if not math.isclose(math.expm1(annual_log), annual_return, abs_tol=1e-12):
        raise AssertionError('log return reconciliation failed')
    rows = [{
        'date_utc': iso(row['start_us'])[:10], 'start_utc': iso(row['start_us']),
        'end_utc_exclusive': iso(row['end_us']), 'start_NAV_USDT': nav[i],
        'end_NAV_USDT': nav[i+1], 'net_increment_USDT': deltas[i],
        'simple_return': returns[i], 'log_return': logs[i],
    } for i, row in enumerate(daily)]
    month_keys = list(dict.fromkeys(row['date_utc'][:7] for row in rows))
    months = []
    for month in month_keys:
        indexes = [i for i, row in enumerate(rows) if row['date_utc'].startswith(month)]
        first, last = indexes[0], indexes[-1]
        net = math.fsum(deltas[i] for i in indexes)
        logret = math.fsum(logs[i] for i in indexes)
        months.append({
            'month': month, 'days': len(indexes), 'net_increment_USDT': net,
            'initial_capital_return_contribution_pp': 100 * net / initial,
            'compounded_return': nav[last+1] / nav[first] - 1,
            'log_return': logret,
            'share_of_annual_net_log_return': logret / annual_log if annual_log else None,
            'start_NAV_USDT': nav[first], 'end_NAV_USDT': nav[last+1],
        })
    best = max(months, key=lambda x: (x['compounded_return'], -month_keys.index(x['month'])))
    best_removed = {
        'best_month': best['month'], 'best_month_return': best['compounded_return'],
        'return_with_best_month_daily_returns_replaced_by_zero': math.expm1(annual_log - best['log_return']),
        'fixed_dollar_annual_return_minus_best_month_contribution': (nav[-1]-initial-best['net_increment_USDT']) / initial,
        'interpretation': 'Ex post arithmetic deletion; no strategy rerun, rescaling of positions, retuning, or executable counterfactual.',
    }
    rolling = {}
    for window in (30, 90):
        if n < window:
            rolling[str(window)] = None
            continue
        candidates = [(nav[i+window]/nav[i]-1, i) for i in range(n-window+1)]
        worst, start = min(candidates)
        rolling[str(window)] = {
            'calendar_days': window, 'complete_windows_tested': len(candidates),
            'start_utc': rows[start]['start_utc'],
            'last_day_utc': rows[start+window-1]['date_utc'],
            'end_utc_exclusive': rows[start+window-1]['end_utc_exclusive'],
            'return': worst, 'start_NAV_USDT': nav[start], 'end_NAV_USDT': nav[start+window],
        }
    ranked = sorted(range(n), key=lambda i: (-logs[i], i))
    positive_log = math.fsum(x for x in logs if x > 0)
    top = {}
    for k in (5, 10):
        selected = ranked[:k]
        amount = math.fsum(logs[i] for i in selected)
        top[str(k)] = {
            'days': len(selected), 'sum_log_return': amount,
            'share_of_annual_net_log_return': amount / annual_log if annual_log else None,
            'share_of_all_positive_daily_log_returns': amount / positive_log if positive_log else None,
            'return_with_top_days_daily_returns_replaced_by_zero': math.expm1(annual_log-amount),
            'observations': [rows[i] for i in selected],
        }
    peak = nav[0]
    max_dd = 0.0
    for v in nav:
        peak = max(peak, v)
        max_dd = max(max_dd, 1-v/peak)
    return {
        'coverage': {'days': n, 'start_utc': rows[0]['start_utc'],
                     'end_utc_exclusive': rows[-1]['end_utc_exclusive'],
                     'positive_days': sum(x > 0 for x in deltas),
                     'negative_days': sum(x < 0 for x in deltas),
                     'zero_increment_days': sum(x == 0 for x in deltas),
                     'first_nonzero_increment_day': next((r['date_utc'] for r in rows if r['net_increment_USDT'] != 0), None)},
        'initial_NAV_USDT': initial, 'final_NAV_USDT': nav[-1],
        'net_increment_USDT': math.fsum(deltas), 'annual_return': annual_return,
        'annual_log_return': annual_log, 'positive_daily_log_return_sum': positive_log,
        'daily_boundary_max_drawdown': max_dd,
        'positive_months': sum(m['compounded_return'] > 0 for m in months),
        'negative_months': sum(m['compounded_return'] < 0 for m in months),
        'zero_months': sum(m['compounded_return'] == 0 for m in months),
        'months': months, 'leave_best_month_out': best_removed,
        'worst_rolling': rolling, 'top_daily_log_returns': top,
    }, rows

def main():
    started = datetime.now(timezone.utc).isoformat()
    wall = time.monotonic()
    resource.setrlimit(resource.RLIMIT_CPU, (120, 120))
    resource.setrlimit(resource.RLIMIT_AS, (2*1024**3, 2*1024**3))
    signal.alarm(120)
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', default='results')
    args = parser.parse_args()
    output = ROOT / args.output
    output.mkdir(parents=True, exist_ok=True)
    catalog = json.loads((ROOT/'SOURCE_CATALOG.json').read_text())
    verified = []
    for item in catalog:
        b = (ROOT/item['path']).read_bytes()
        git_blob = hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()
        if len(b) != item['expected_bytes'] or git_blob != item['git_blob_sha1']:
            raise AssertionError('public input byte/hash mismatch: '+item['path'])
        verified.append({**item, 'SHA256': sha256(b), 'bytes': len(b), 'git_blob_verified': True})
    results = {'schema': 'PUBLIC_SAVED_2023_RETURN_CONCENTRATION_V1',
               'diagnostic_plan_SHA256': sha256((ROOT/'DIAGNOSTIC_PLAN.md').read_bytes()),
               'script_SHA256': sha256(Path(__file__).read_bytes()), 'runs': {}}
    all_months = []
    for key, label in [('h090', 'H090 CONTROL'), ('csh', 'Ordinary CS/HOLD')]:
        daily = json.loads((ROOT/f'inputs/{key}_DAILY.json').read_text())
        saved = json.loads((ROOT/f'inputs/{key}_SUMMARY.json').read_text())
        risk = json.loads((ROOT/f'inputs/{key}_ACTUAL_RISK_METRICS.json').read_text())
        initial_decimal = Decimal(saved['decimal_strings']['NAV']) - Decimal(saved['decimal_strings']['net_PnL'])
        if initial_decimal != 10000:
            raise AssertionError('unexpected initial NAV')
        metrics, rows = return_metrics(daily, float(initial_decimal))
        gap = metrics['final_NAV_USDT'] - float(saved['paid_NAV_decimal'])
        if not math.isclose(gap, 0, abs_tol=1e-8):
            raise AssertionError('daily endpoint does not reconcile to saved paid NAV')
        if not (len(daily) == 365 and daily[0]['start_us'] == 1672531200000000 and daily[-1]['end_us'] == 1704067200000000):
            raise AssertionError('unexpected year coverage')
        saved_worst30 = -float(risk['worst_complete30d_loss'])
        if not math.isclose(metrics['worst_rolling']['30']['return'], saved_worst30, abs_tol=1e-10):
            raise AssertionError('saved 30-day diagnostic does not reconcile')
        metrics.update({
            'label': label, 'saved_paid_NAV_decimal': saved['paid_NAV_decimal'],
            'daily_reconstruction_endpoint_gap_USDT': gap,
            'saved_all_event_max_drawdown': saved['all_observation_max_drawdown'],
            'saved_30day_return_reconciliation_gap': metrics['worst_rolling']['30']['return'] - saved_worst30,
            'saved_first_entry_utc': iso(saved['first_entry_us']),
            'saved_evidence_origin': saved['evidence_origin'],
            'saved_dispatch_status': saved['dispatch_status'],
            'saved_native_risk_parity_certified': saved['risk_parity_certified'],
            'configured_gross_cap': .9 if key == 'h090' else .6,
            'configured_annual_vol_target': .15 if key == 'h090' else .10,
            'saved_cost_scenario': saved['cost_scenario'],
            'saved_costs_USDT': {x: saved[x] for x in ('fees_USDT','execution_cost_USDT','funding_USDT')},
            'saved_minimum_free_cash_USDT': saved['minimum_actual_free_cash_all_observations_USDT'],
            'saved_maximum_actual_gross_weight': saved['maximum_actual_gross_weight'],
        })
        results['runs'][key] = metrics
        for m in metrics['months']:
            all_months.append({'run': key, **m})
        with (output/f'{key}_DAILY_DERIVED.csv').open('w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=list(rows[0])); writer.writeheader(); writer.writerows(rows)
    with (output/'MONTHLY_CONTRIBUTION.csv').open('w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=list(all_months[0])); writer.writeheader(); writer.writerows(all_months)
    dump(output/'RESULTS.json', results)
    dump(output/'VERIFIED_SOURCES.json', verified)
    receipt = {
        'started_utc': started, 'finished_utc': datetime.now(timezone.utc).isoformat(),
        'wall_seconds': time.monotonic()-wall,
        'max_RSS_bytes_linux': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024,
        'CPU_limit_seconds': 120, 'wall_alarm_seconds': 120, 'address_space_limit_bytes': 2*1024**3,
        'input_files': len(verified), 'input_bytes': sum(x['bytes'] for x in verified),
        'source_hashes_and_endpoint_checks': 'PASS', 'saved_30day_reconciliation': 'PASS',
        'analysis_only_no_network_no_strategy_imports_no_training_no_replay': True,
        'output_SHA256': {p.name: sha256(p.read_bytes()) for p in sorted(output.iterdir()) if p.name != 'RUN_RECEIPT.json'},
    }
    dump(output/'RUN_RECEIPT.json', receipt)
    print(json.dumps({'receipt': receipt, 'runs': {k: {x: v[x] for x in ('annual_return', 'leave_best_month_out', 'worst_rolling', 'coverage')} for k,v in results['runs'].items()}}, indent=2))

if __name__ == '__main__':
    main()
