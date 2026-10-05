"""Scalar Decimal saved-daily review; no producer imports or empirical rebootstrap."""
import argparse
from datetime import UTC, datetime, timedelta
from decimal import Decimal, localcontext
import hashlib
import json
import math
import os
from pathlib import Path
import resource
import time

import numpy as np
import polars as pl
from quant.metrics import block_bootstrap_mean_ci

STEM = 'HOLD_EXIT_BLEND_TIME_20261005_V1'
DAY = 86_400_000_000
ERRORS = {}


def need(ok, message):
    if not ok:
        raise ValueError(message)


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def read(path, digest=None):
    need(digest is None or sha(path) == digest, 'bound input changed: ' + str(path))
    return json.loads(Path(path).read_text(encoding='utf-8'))


def number(value):
    return Decimal.from_float(value) if isinstance(value, float) else Decimal(str(value))


def same(kind, actual, reported, tolerance):
    error = abs(float(actual) - float(reported))
    ERRORS[kind] = max(ERRORS.get(kind, 0.), error)
    need(error <= tolerance, 'independent mismatch: ' + kind)


def closed(report, state):
    identity = report.get('task_id') or report['binding']['task_id']
    task = read(state / 'task-progress' / ('task-' + identity + '.json'))
    need(task['status'] == 'completed' and task['exit_code'] == 0 and task['ended_at'],
         'task not closed0: ' + identity)
    return identity


def episodes(values, dates, endpoints, capital, initial_date, start_us):
    # Direct running-high/active-episode state with Decimal comparisons. Recovery
    # belongs to the closing endpoint, but is not an underwater observation.
    peak, peak_date, peak_us = capital, initial_date, start_us
    peak_origin, active, output = 'INITIAL_CAPITAL_BEFORE_WINDOW', None, []
    for nav, date, endpoint in zip(values, dates, endpoints, strict=True):
        if nav >= peak:
            if active is not None:
                active.update(recovery_date=date, recovered=True, last_NAV=nav, last_date=date,
                    recovery_endpoint_us=endpoint, last_endpoint_us=endpoint, right_censored=False,
                    duration_days=(endpoint - active['peak_endpoint_us']) / DAY)
                output.append(active)
                active = None
            peak, peak_date, peak_us, peak_origin = nav, date, endpoint, 'DAILY_ENDPOINT'
            continue
        if active is None:
            active = dict(peak_date=peak_date, start_date=date, trough_date=date,
                recovery_date=None, peak_NAV=peak, trough_NAV=nav, last_NAV=nav,
                last_date=date, depth_fraction=(peak - nav) / peak,
                underwater_observations=0, recovered=False,
                scope='DAILY_ENDPOINTS_NOT_MINUTE_DRAWDOWN', peak_endpoint_us=peak_us,
                start_endpoint_us=endpoint, trough_endpoint_us=endpoint, recovery_endpoint_us=None,
                last_endpoint_us=endpoint, peak_origin=peak_origin, right_censored=True,
                duration_days=(endpoint - peak_us) / DAY)
        active['underwater_observations'] += 1
        active.update(last_NAV=nav, last_date=date, last_endpoint_us=endpoint,
                      duration_days=(endpoint - active['peak_endpoint_us']) / DAY)
        if nav < active['trough_NAV']:
            active.update(trough_NAV=nav, trough_date=date, trough_endpoint_us=endpoint,
                          depth_fraction=(peak - nav) / peak)
    if active is not None:
        output.append(active)
    return output


def check_episodes(values, dates, endpoints, reported, capital, initial_date, start_us):
    computed = episodes(values, dates, endpoints, capital, initial_date, start_us)
    need(len(computed) == len(reported), 'all daily episode count')
    for own, record in zip(computed, reported, strict=True):
        for key in ('peak_date', 'start_date', 'trough_date', 'recovery_date', 'last_date',
                    'underwater_observations', 'recovered', 'scope', 'peak_endpoint_us',
                    'start_endpoint_us', 'trough_endpoint_us', 'recovery_endpoint_us',
                    'last_endpoint_us', 'peak_origin', 'right_censored', 'duration_days'):
            need(own[key] == record[key], 'episode identity: ' + key)
        for key in ('peak_NAV', 'trough_NAV', 'last_NAV'):
            same('episode_NAV_USDT', own[key], record[key], 1e-7)
        same('episode_depth_fraction', own['depth_fraction'], record['depth_fraction'], 1e-12)
    return computed


def main():
    started = time.monotonic()
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=Path, default=Path('/mnt/d/codex/coin'))
    parser.add_argument('--state', type=Path, default=Path('/home/xflops/coin-state'))
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    need(args.output.resolve().is_relative_to(args.state.resolve()) and not args.output.exists(), 'new STATE output')
    root, state = args.root, args.state
    pp = root / 'protocols' / (STEM + '.json')
    rp = root / 'reports/fast_research' / (STEM + '.json')
    protocol, result = read(pp), read(rp)
    need(result['protocol_sha256'] == sha(pp) and
         result['status'] == 'COMPLETE_SAVED_PAIR_TIME_DIAGNOSTIC_POST_SELECTION_NOT_APR', 'closed main binding')
    need(protocol['full_capital_USDT'] == 10000 and protocol['fixed_tranche_indices'] ==
         [[0, 101], [101, 202], [202, 303]], 'fixed capital and time slices')
    need(protocol['blocks_days'] == [7, 30, 60] and protocol['primary_block_days'] == 60 and
         protocol['samples_per_case_per_block'] == 2000 and protocol['seed'] == 20261005, 'fixed bootstrap budget')
    for name, digest in protocol['source_hashes'].items():
        need(sha(root / name) == digest, 'current bound source')
    roles = {'main': closed(result, state)}
    accounts = []
    for role in ('baseline_report', 'challenger_report'):
        ref = protocol[role]
        report = read(ref['path'], ref['sha256'])
        need(report['complete_calendar_cases'] == 4, 'four saved complete accounts')
        accounts.append(report)
        roles[role] = closed(report, state)
    for i, ref in enumerate(protocol['accepted_financial_reports']):
        financial = read(ref['path'], ref['sha256'])
        need(financial['status'].startswith('PASS_CONFIGURED_N_') and financial['financial_case_calls'] == 4,
             'accepted full financial')
        roles['financial_' + str(i)] = closed(financial, state)
    ref = protocol['accepted_pair_diagnostic']
    accepted = read(ref['path'], ref['sha256'])
    need(accepted['status'] == 'COMPLETE_FIXED_BLEND_SHARED_WALLET_PAIRED_DIAGNOSTIC_NOT_APR', 'D073 saved diagnostic')
    roles['accepted_pair'] = closed(accepted, state)
    origin = datetime(2024, 9, 1, tzinfo=UTC)
    need(protocol['start_us'] == int(origin.timestamp()) * 1_000_000, 'fixed origin')
    dates = [(origin + timedelta(days=i)).date().isoformat() for i in range(303)]
    expected = [int((origin + timedelta(days=i + 1)).timestamp()) * 1_000_000 for i in range(303)]
    need(expected[-1] == protocol['end_us'] and dates[-1] == '2025-06-30', '303 full UTC endpoint calendar')
    month_slices = []
    for i, date in enumerate(dates):
        if not month_slices or month_slices[-1][0] != date[:7]:
            month_slices.append([date[:7], i, i + 1])
        else:
            month_slices[-1][2] = i + 1
    identities, witnesses = [], []
    with localcontext() as context:
        context.prec = 60
        for pair in result['pairs']:
            cases = [next(c for c in report['cases'] if c['id'] == pair['case_id']) for report in accounts]
            need(cases[0]['symbols'] == cases[1]['symbols'] == ['BTCUSDT', 'ETHUSDT'] and
                 cases[0]['cost_id'] == cases[1]['cost_id'] and cases[0]['unit_id'] == cases[1]['unit_id'], 'paired roles')
            series, logs, pnls, risks, all_episodes = [], [], [], [], []
            for side, case in enumerate(cases):
                receipt = case['artifacts']['daily_nav.parquet']
                path = Path(receipt['path'])
                need(path.resolve().is_relative_to(state.resolve()) and not path.is_symlink() and
                     sha(path) == receipt['sha256'], 'saved daily-only source identity')
                frame = pl.read_parquet(path, columns=['day_end_us', 'nav'])
                need(frame.height == receipt['rows'] == 303 and frame['day_end_us'].to_list() == expected,
                     'positive ordered complete daily endpoints')
                score_dates = [datetime.fromtimestamp((int(t) - 1) // 1_000_000, UTC).date().isoformat()
                               for t in frame['day_end_us'].to_list()]
                need(score_dates == dates, 'endpoint-minus1us scoring dates')
                values = [number(v) for v in frame['nav'].to_list()]
                need(all(v.is_finite() and v > 0 for v in values), 'finite positive NAV')
                capital = Decimal(10000)
                previous = [capital] + values[:-1]
                log = [v.ln() - prior.ln() for v, prior in zip(values, previous, strict=True)]
                pnl = [v - prior for v, prior in zip(values, previous, strict=True)]
                summary = case['summary']
                need(summary['completed_minutes'] == summary['required_minutes'] == 436320 and
                     summary['terminal_cash_realized'] is True and summary['terminal_marked_notional'] == 0,
                     'complete saved liquidated wallet')
                same('terminal_NAV_USDT', values[-1], summary['decimal_strings']['NAV'], 1e-7)
                same('net_PnL_USDT', sum(pnl), summary['decimal_strings']['net_PnL'], 1e-7)
                same('log_telescoping', sum(log), (values[-1] / capital).ln(), 1e-12)
                simple = [v / prior - 1 for v, prior in zip(values, previous, strict=True)]
                mean = sum(simple) / Decimal(303)
                variance = sum((x - mean) ** 2 for x in simple) / Decimal(302)
                vol = (variance * Decimal(365)).sqrt()
                own_episodes = check_episodes(values, dates, frame['day_end_us'].to_list(),
                    pair['baseline_drawdown_episodes' if side == 0 else 'challenger_drawdown_episodes'],
                    capital, dates[0], protocol['start_us'])
                daily_dd = max((r['depth_fraction'] for r in own_episodes), default=Decimal(0))
                same('actual_daily_volatility', vol, summary['daily_metrics']['annual_volatility'], 1e-12)
                same('actual_daily_MDD', daily_dd, summary['daily_metrics']['max_drawdown'], 1e-12)
                same('reported_daily_MDD', daily_dd,
                     pair['baseline_daily_max_drawdown' if side == 0 else 'challenger_daily_max_drawdown'], 1e-12)
                same('reported_actual_volatility', vol,
                     pair['baseline_actual_volatility' if side == 0 else 'challenger_actual_volatility'], 1e-12)
                risks.append(dict(actual_daily_volatility=vol, daily_MDD=daily_dd,
                                  minute_MDD_from_saved_summary=summary['minute_max_drawdown']))
                identities.append(dict(path=str(path), sha256=receipt['sha256'], bytes=path.stat().st_size, rows=303))
                series.append(values); logs.append(log); pnls.append(pnl); all_episodes.append(own_episodes)
            cash = [b - a for a, b in zip(pnls[0], pnls[1], strict=True)]
            delta = [b - a for a, b in zip(logs[0], logs[1], strict=True)]
            need(len(pair['months']) == 10 and len(pair['fixed_tranches']) == 3, 'actual month/tranche counts')
            segments = [(0, 303, pair['total'])]
            segments += [(a, b, record) for (a, b), record in zip(protocol['fixed_tranche_indices'], pair['fixed_tranches'], strict=True)]
            segments += [(a, b, record) for (_, a, b), record in zip(month_slices, pair['months'], strict=True)]
            for a, b, record in segments:
                need(record['start'] == dates[a] and record['end_inclusive'] == dates[b - 1] and
                     record['days'] == b - a, 'fixed daily slice identity')
                same('segment_increment_USDT', sum(cash[a:b]), record['net_increment_USDT'], 1e-7)
                same('segment_log_increment', sum(delta[a:b]), record['paired_log_return_increment'], 1e-12)
                for side, prefix in ((0, 'baseline'), (1, 'challenger')):
                    start_nav = Decimal(10000) if a == 0 else series[side][a - 1]
                    same('slice_start_NAV_USDT', start_nav, record[prefix + '_start_NAV'], 1e-7)
                    same('slice_end_NAV_USDT', series[side][b - 1], record[prefix + '_end_NAV'], 1e-7)
                    same('slice_net_USDT', series[side][b - 1] - start_nav, record[prefix + '_net_USDT'], 1e-7)
                    same('slice_account_log', sum(logs[side][a:b]), record[prefix + '_log_return'], 1e-12)
                    same('slice_actual_return', series[side][b - 1] / start_nav - 1, record[prefix + '_return'], 1e-12)
            same('paired_terminal_log', sum(delta), (series[1][-1] / series[0][-1]).ln(), 1e-12)
            for month, omitted in zip(pair['months'], pair['leave_one_month_out_arithmetic_descriptions'], strict=True):
                need(omitted['month'] == month['start'][:7], 'month-out identity')
                same('month_out_USDT', sum(cash) - number(month['net_increment_USDT']), omitted['net_increment_except_month_USDT'], 1e-7)
            need(len(pair['block_intervals']) == 3, 'three dependence assumptions')
            for interval in pair['block_intervals']:
                need(interval['block_days'] in (7, 30, 60) and interval['samples'] == 2000 and
                     interval['seed'] == 20261005, 'real interval configuration')
                same('reported_mean_log', sum(delta) / Decimal(303), interval['mean_daily_log_increment'], 1e-12)
                lo, hi = interval['lower_mean_daily_log_increment'], interval['upper_mean_daily_log_increment']
                need(lo <= hi and interval['includes_zero'] == (lo <= 0 <= hi), 'reported empirical interval identity')
            witnesses.append(dict(case_id=pair['case_id'], total_net_increment=sum(cash), risk=risks,
                daily_episodes=all_episodes, primary60=next(r for r in pair['block_intervals'] if r['block_days'] == 60)))
    # One hand counterexample verifies equality recovery, initial capital peak,
    # actual timestamp duration, and an unrecovered daily endpoint episode.
    toy_dates = ['2024-09-0' + str(i) for i in range(1, 7)]
    toy_start = int(datetime(2024, 9, 1, tzinfo=UTC).timestamp()) * 1_000_000
    toy_episodes = episodes([Decimal(v) for v in (90, 80, 100, 110, 100, 95)], toy_dates,
        [toy_start + DAY * i for i in range(1, 7)], Decimal(100), toy_dates[0], toy_start)
    need(len(toy_episodes) == 2 and toy_episodes[0]['recovered'] and
         toy_episodes[0]['recovery_endpoint_us'] == toy_start + 3 * DAY and toy_episodes[0]['underwater_observations'] == 2 and
         toy_episodes[0]['peak_origin'] == 'INITIAL_CAPITAL_BEFORE_WINDOW' and
         toy_episodes[0]['duration_days'] == 3 and toy_episodes[1]['right_censored'] and
         toy_episodes[1]['duration_days'] == 2 and toy_episodes[1]['peak_origin'] == 'DAILY_ENDPOINT',
         'synthetic equality/censor/clock episode arithmetic')
    # Only 3x37 tiny synthetic draws: empirical 24k draws are not repeated.
    toy = [-.3, .7, -.1, .4, .9, -.8, .2, .5, -.6, .1, .3, -.2]
    for block in (7, 30, 60):
        rng = np.random.default_rng(20261005)
        width = min(block, len(toy)); count = math.ceil(len(toy) / width); means = []
        for _ in range(37):
            indices = []
            for start in rng.integers(0, len(toy), size=count).tolist():
                indices.extend((start + offset) % len(toy) for offset in range(width))
            means.append(math.fsum(toy[j] for j in indices[:len(toy)]) / len(toy))
        ordered = sorted(means)
        def percentile(q):
            position = (len(ordered) - 1) * q
            low, high = math.floor(position), math.ceil(position)
            return ordered[low] + (ordered[high] - ordered[low]) * (position - low)
        lo, hi = block_bootstrap_mean_ci(np.asarray(toy), block_days=block, samples=37, seed=20261005)
        same('toy_circular_percentile', percentile(.025), lo, 1e-14)
        same('toy_circular_percentile', percentile(.975), hi, 1e-14)
    need(time.monotonic() - started <= 120 and resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024 <= 300000000,
         'independent limited time/RSS')
    value = dict(status='PASS_INDEPENDENT_SAVED_DAILY_DECIMAL_TIME_AND_EPISODE_ARITHMETIC_NOT_ALPHA',
        task_id=os.environ.get('COIN_TASK_ID'), helper_sha256=sha(__file__), protocol_sha256=sha(pp),
        main_result_sha256=sha(rp), closed_roles=roles, errors=ERRORS, witnesses=witnesses,
        daily_identities=identities, empirical_interval_endpoints_independently_reestimated=False,
        toy_draws=111, actual_risk_matched=False, selection_bias_corrected=False,
        uncertainty_scope='Descriptive circular block percentiles, dependence/regime sensitive; roughly five60-day blocks, no new history/OOS/selection correction',
        episodes_scope='Daily endpoints with initial10000 prefix, not minute drawdown; no wallet reset',
        market_replays=0, model_fits=0, candidate='NONE', investment='CASH', long_term_APR='NOT_EVALUABLE',
        elapsed_seconds=time.monotonic() - started, peak_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('x', encoding='utf-8') as stream:
        json.dump(value, stream, indent=2, ensure_ascii=False, default=str, allow_nan=False)
        stream.write('\n')
    print(json.dumps(dict(status=value['status'], output=str(args.output), sha256=sha(args.output))))


if __name__ == '__main__':
    main()
