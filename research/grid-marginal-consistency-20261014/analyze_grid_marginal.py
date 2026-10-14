#!/usr/bin/env python3
"""Offline paired-path diagnostics from four pinned public saved-result files.

No network, strategy imports, execution engine, training, or parameter fitting.
Decimal preserves the published decimal number text, not unreported engine precision.
"""
from __future__ import annotations
import argparse
import csv
from datetime import datetime, timedelta, timezone
from decimal import Decimal, getcontext
import hashlib
import json
from pathlib import Path

getcontext().prec = 60
D = Decimal
INITIAL = D('10000')
TOL = D('0.00000001')
ZERO = D(0)
DAY_US = 86400_000000
DAILY_KEYS = {'completed', 'completion', 'end_us', 'net_increment_USDT', 'start_us', 'stop_us'}
SUMMARY_KEYS = {'paid_NAV_decimal', 'complete_calendar', 'completed_minutes', 'required_minutes', 'completion', 'cost_scenario', 'configured_nominal_roundtrip_bps', 'all_observation_max_drawdown', 'maximum_actual_gross_weight', 'risk_parity_certified', 'terminal_cash_realized', 'unpaid_liability', 'decimal_strings'}
DECIMAL_KEYS = {'NAV', 'net_PnL', 'configured_nominal_roundtrip_bps', 'execution_cost_USDT', 'fees_USDT', 'funding_USDT', 'gross_PnL_same_quantities', 'gross_fill_turnover_USDT', 'unpaid_liability'}

def read_json(path):
    return json.loads(path.read_text(), parse_float=D)

def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def git_blob_sha(path):
    body = path.read_bytes()
    return hashlib.sha1(b'blob ' + str(len(body)).encode() + b'\0' + body).hexdigest()

def dump_json(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True, default=str) + '\n')

def date_from_us(ts):
    return datetime.fromtimestamp(ts // 1_000_000, timezone.utc).date().isoformat()

def validate_days(rows, year):
    start = int(datetime(year, 1, 1, tzinfo=timezone.utc).timestamp()) * 1_000_000
    end = int(datetime(year + 1, 1, 1, tzinfo=timezone.utc).timestamp()) * 1_000_000
    if len(rows) != (end - start) // DAY_US:
        raise ValueError('Incomplete calendar length')
    for i, row in enumerate(rows):
        if set(row) != DAILY_KEYS:
            raise ValueError('Unexpected daily schema')
        if row['start_us'] != start + i * DAY_US or row['end_us'] != start + (i + 1) * DAY_US:
            raise ValueError('Calendar is not ordered and contiguous')
        if row['completed'] is not True or row['completion'] != 'COMPLETE_CONDITIONAL_ACCOUNT' or row['stop_us'] is not None:
            raise ValueError('Incomplete daily result')
        value = D(str(row['net_increment_USDT']))
        if not value.is_finite():
            raise ValueError('Nonfinite daily increment')

def validate_summary(summary):
    if set(summary) != SUMMARY_KEYS or set(summary['decimal_strings']) != DECIMAL_KEYS:
        raise ValueError('Financial summary allowlist mismatch')
    if summary['complete_calendar'] is not True or summary['completed_minutes'] != 525600 or summary['required_minutes'] != 525600:
        raise ValueError('Incomplete summary')
    if summary['terminal_cash_realized'] is not True or D(str(summary['unpaid_liability'])) != 0:
        raise ValueError('Non-flat paid terminal result')
    inferred_initial = D(summary['paid_NAV_decimal']) - D(summary['decimal_strings']['net_PnL'])
    if abs(inferred_initial - INITIAL) > TOL:
        raise ValueError('Initial capital mismatch')
    return inferred_initial

def signs(values):
    vals = list(values)
    n = len(vals)
    positive = sum(x > 0 for x in vals)
    negative = sum(x < 0 for x in vals)
    zero = sum(x == 0 for x in vals)
    return {'count': n, 'positive': positive, 'negative': negative, 'zero': zero,
            'positive_fraction_all': D(positive) / n if n else None,
            'positive_fraction_nonzero': D(positive) / (positive + negative) if positive + negative else None}

def pearson(x, y):
    if len(x) != len(y) or len(x) < 2:
        raise ValueError('Invalid paired correlation length')
    mx, my = sum(x, ZERO) / len(x), sum(y, ZERO) / len(y)
    dx, dy = [v - mx for v in x], [v - my for v in y]
    vx, vy = sum((v * v for v in dx), ZERO), sum((v * v for v in dy), ZERO)
    if vx == 0 or vy == 0:
        return None
    return sum((a * b for a, b in zip(dx, dy)), ZERO) / (vx * vy).sqrt()

def difference_path_stats(dates, increments):
    value = peak = minimum = maximum = worst = ZERO
    initial_date = 'INITIAL_ZERO'
    peak_date = min_date = max_date = worst_peak_date = worst_trough_date = initial_date
    worst_peak_value = worst_trough_value = ZERO
    for date, inc in zip(dates, increments):
        value += inc
        if value > maximum:
            maximum, max_date = value, date
        if value < minimum:
            minimum, min_date = value, date
        if value > peak:
            peak, peak_date = value, date
        dd = peak - value
        if dd > worst:
            worst = dd
            worst_peak_date, worst_trough_date = peak_date, date
            worst_peak_value, worst_trough_value = peak, value
    return {'final_difference_USDT': value, 'minimum_difference_USDT': minimum,
            'minimum_date': min_date, 'maximum_difference_USDT': maximum, 'maximum_date': max_date,
            'maximum_drawdown_USDT': worst, 'drawdown_peak_date': worst_peak_date,
            'drawdown_trough_date': worst_trough_date, 'drawdown_peak_difference_USDT': worst_peak_value,
            'drawdown_trough_difference_USDT': worst_trough_value,
            'date_convention': 'UTC calendar day whose end NAV is sampled; INITIAL_ZERO precedes day one'}

def analyze_pair(year, cash, grid, cash_summary, grid_summary):
    validate_days(cash, year)
    validate_days(grid, year)
    for summary in (cash_summary, grid_summary):
        validate_summary(summary)
    if cash_summary['cost_scenario'] != grid_summary['cost_scenario']:
        raise ValueError('Cost scenarios differ')
    cash_nav = grid_nav = INITIAL
    daily = []
    monthly = {}
    cash_returns, grid_returns, increments, dates = [], [], [], []
    for c, g in zip(cash, grid):
        if c['start_us'] != g['start_us'] or c['end_us'] != g['end_us']:
            raise ValueError('Pair is misaligned')
        date = date_from_us(c['start_us'])
        ci, gi = D(str(c['net_increment_USDT'])), D(str(g['net_increment_USDT']))
        cr, gr = ci / cash_nav, gi / grid_nav
        cash_nav, grid_nav = cash_nav + ci, grid_nav + gi
        if cash_nav <= 0 or grid_nav <= 0:
            raise ValueError('Nonpositive portfolio NAV')
        inc = gi - ci
        row = {'date': date, 'cash_increment_USDT': ci, 'grid_increment_USDT': gi,
               'paired_increment_USDT': inc, 'cash_NAV_USDT': cash_nav, 'grid_NAV_USDT': grid_nav,
               'cumulative_difference_USDT': grid_nav - cash_nav,
               'cash_simple_return': cr, 'grid_simple_return': gr}
        daily.append(row)
        cash_returns.append(cr); grid_returns.append(gr); increments.append(inc); dates.append(date)
        month = date[:7]
        m = monthly.setdefault(month, {'month': month, 'days': 0, 'cash_increment_USDT': ZERO,
                                      'grid_increment_USDT': ZERO, 'paired_increment_USDT': ZERO})
        m['days'] += 1
        m['cash_increment_USDT'] += ci; m['grid_increment_USDT'] += gi; m['paired_increment_USDT'] += inc
    checks = {}
    for name, nav, summary in [('cash', cash_nav, cash_summary), ('grid', grid_nav, grid_summary)]:
        residual = nav - D(summary['paid_NAV_decimal'])
        if abs(residual) > TOL:
            raise ValueError('Daily reconstruction disagrees with paid terminal NAV')
        checks[name + '_daily_minus_summary_NAV_USDT'] = residual
    annual = sum(increments, ZERO)
    summary_delta = D(grid_summary['paid_NAV_decimal']) - D(cash_summary['paid_NAV_decimal'])
    months = list(monthly.values())
    best = max(months, key=lambda m: m['paired_increment_USDT'])
    monthly_sum = sum((m['paired_increment_USDT'] for m in months), ZERO)
    if monthly_sum != annual or annual != grid_nav - cash_nav:
        raise ValueError('Monthly/daily/terminal telescoping failed')
    checks.update({'monthly_sum_minus_daily_sum_USDT': monthly_sum - annual,
                   'daily_sum_minus_summary_difference_USDT': annual - summary_delta,
                   'reconciliation_tolerance_USDT': TOL, 'passed': True})
    result = {'year': year, 'days': len(daily), 'annual_increment_USDT': annual,
              'summary_terminal_increment_USDT': summary_delta,
              'daily_increment_signs': signs(increments),
              'monthly_increment_signs': signs(m['paired_increment_USDT'] for m in months),
              'months': months, 'difference_path': difference_path_stats(dates, increments),
              'lag_zero_daily_simple_return_correlation': pearson(cash_returns, grid_returns),
              'remove_best_month_sensitivity': {'month': best['month'],
                'removed_contribution_USDT': best['paired_increment_USDT'],
                'remaining_dollar_contribution_USDT': annual - best['paired_increment_USDT'],
                'interpretation': 'Mechanical dollar-contribution subtraction; not a new wallet or trading rule'},
              'summary_context': {name: {'cost_scenario': s['cost_scenario'],
                'all_observation_max_drawdown': s['all_observation_max_drawdown'],
                'maximum_actual_gross_weight': s['maximum_actual_gross_weight'],
                'risk_parity_certified': s['risk_parity_certified']}
                for name, s in [('cash', cash_summary), ('grid', grid_summary)]},
              'checks': checks}
    return result, daily

def write_csv(path, rows):
    with path.open('w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader(); writer.writerows(rows)

def run(base, out):
    catalog = read_json(base / 'SOURCE_CATALOG.json')
    loaded, verified = {}, []
    for source in catalog['sources']:
        dp, sp = base / source['daily_file'], base / source['summary_financial_file']
        if git_blob_sha(dp) != source['daily_git_blob_sha'] or sha256(dp) != source['daily_sha256'] or sha256(sp) != source['summary_financial_sha256']:
            raise ValueError('Input integrity check failed')
        loaded[source['id']] = (read_json(dp), read_json(sp))
        verified.append({'id': source['id'], 'daily_sha256': sha256(dp),
                         'daily_git_blob_sha': git_blob_sha(dp), 'summary_financial_sha256': sha256(sp)})
    out.mkdir(parents=True, exist_ok=True)
    results, months = [], []
    for year in (2023, 2025):
        c, cs = loaded[f'{year}_cash']; g, gs = loaded[f'{year}_grid']
        result, daily = analyze_pair(year, c, g, cs, gs)
        results.append(result); months.extend(result['months'])
        write_csv(out / f'{year}_PAIRED_DAILY.csv', daily)
    write_csv(out / 'MONTHLY_INCREMENT.csv', months)
    full = {'version': 1, 'method': 'Predeclared paired calendar daily increment consistency',
            'initial_NAV_per_arm_USDT': INITIAL, 'years': results,
            'inference': 'Descriptive only. No sampling confidence, same-actual-risk dominance, or learnable grid alpha claim.'}
    dump_json(out / 'RESULTS.json', full)
    dump_json(out / 'VERIFIED_SOURCES.json', verified)
    return full

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base', type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument('--out', type=Path)
    args = parser.parse_args()
    result = run(args.base, args.out or args.base / 'results')
    for year in result['years']:
        print(year['year'], 'annual USDT', year['annual_increment_USDT'],
              'positive months', year['monthly_increment_signs']['positive'],
              'positive days', year['daily_increment_signs']['positive'],
              'zero days', year['daily_increment_signs']['zero'],
              'difference drawdown USDT', year['difference_path']['maximum_drawdown_USDT'],
              'without best month USDT', year['remove_best_month_sensitivity']['remaining_dollar_contribution_USDT'],
              'daily return correlation', year['lag_zero_daily_simple_return_correlation'])
