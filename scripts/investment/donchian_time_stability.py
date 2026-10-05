"""Read saved paired daily wallets; descriptive post-selection evidence only."""
from __future__ import annotations

import argparse
from datetime import UTC, datetime
import hashlib
import json
import math
import os
from pathlib import Path
import resource
import subprocess
import time

import numpy as np
import polars as pl

from quant import resources
from quant.metrics import block_bootstrap_mean_ci
from quant.paths import ROOT, STATE
from scripts.research_v8.registry import FIELDS, append_event

DAY = 86_400_000_000


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def read(receipt):
    path = Path(receipt['path']).resolve()
    if not path.is_relative_to(ROOT/'reports') and not path.is_relative_to(STATE):
        raise ValueError('Saved local reports or owned STATE artifacts only')
    assert sha(path) == receipt['sha256'], str(path)
    return json.loads(path.read_bytes())


def daily(case, expected, capital):
    receipt = case['artifacts']['daily_nav.parquet']
    path = Path(receipt['path']).resolve()
    assert path.is_relative_to(STATE) and sha(path) == receipt['sha256']
    frame = pl.read_parquet(path, columns=['day_end_us', 'nav'])
    assert frame.height == receipt['rows'] == len(expected)
    assert np.array_equal(frame['day_end_us'].to_numpy(), expected)
    nav = frame['nav'].to_numpy().astype(float)
    assert np.isfinite(nav).all() and (nav > 0).all()
    previous = np.r_[capital, nav[:-1]]
    logs = np.log(nav / previous)
    pnl = nav - previous
    summary = case['summary']
    assert summary['completed_minutes'] == summary['required_minutes'] == 436320
    assert summary['terminal_cash_realized'] and summary['terminal_marked_notional'] == 0
    assert abs(nav[-1] - summary['daily_metrics']['final_nav']) < 1e-7
    # Daily endpoints and final liquidation must be the same saved account value.
    assert abs(nav[-1] - capital - summary['net_PnL']) < 1e-7
    assert abs(math.fsum(logs) - math.log(nav[-1]/capital)) < 1e-12
    assert abs(math.fsum(pnl) - summary['net_PnL']) < 1e-7
    return nav, previous, logs, pnl


def summarize_slice(left, right, dates, start, end):
    a, ap, al, au = left
    b, bp, bl, bu = right
    oldlog, newlog = math.fsum(al[start:end]), math.fsum(bl[start:end])
    return dict(start=dates[start], end_inclusive=dates[end-1], days=end-start,
                baseline_start_NAV=float(ap[start]), challenger_start_NAV=float(bp[start]),
                baseline_end_NAV=float(a[end-1]), challenger_end_NAV=float(b[end-1]),
                baseline_net_USDT=math.fsum(au[start:end]),
                challenger_net_USDT=math.fsum(bu[start:end]),
                net_increment_USDT=math.fsum(bu[start:end]-au[start:end]),
                baseline_log_return=oldlog, challenger_log_return=newlog,
                paired_log_return_increment=newlog-oldlog,
                baseline_return=math.expm1(oldlog), challenger_return=math.expm1(newlog),
                scope='ACTUAL_CONTINUOUS_WALLETS_NOT_RESET_ACCOUNTS_NOT_MATCHED_RISK')


def drawdown_episodes(nav, dates, capital, start_us):
    """Daily endpoint episodes, including initial capital and censored endings."""
    episodes, pending = [], None
    peak = float(capital)
    peak_us = start_us
    peak_date = datetime.fromtimestamp(start_us/1e6, UTC).date().isoformat()
    peak_origin = 'INITIAL_CAPITAL_BEFORE_WINDOW'
    for i, value in enumerate(nav):
        value = float(value)
        endpoint = start_us+(i+1)*DAY
        if value >= peak:
            if pending is not None:
                pending.update(recovered=True, right_censored=False,
                    recovery_date=dates[i], recovery_endpoint_us=endpoint,
                    last_date=dates[i], last_endpoint_us=endpoint, last_NAV=value,
                    duration_days=(endpoint-pending['peak_endpoint_us'])/DAY)
                episodes.append(pending)
                pending = None
            peak, peak_us, peak_date, peak_origin = value, endpoint, dates[i], 'DAILY_ENDPOINT'
            continue
        if pending is None:
            pending = dict(peak_NAV=peak, peak_date=peak_date, peak_endpoint_us=peak_us,
                peak_origin=peak_origin, start_date=dates[i], start_endpoint_us=endpoint,
                trough_NAV=value, trough_date=dates[i], trough_endpoint_us=endpoint,
                underwater_observations=0, recovered=False, right_censored=True,
                recovery_date=None, recovery_endpoint_us=None,
                scope='DAILY_ENDPOINTS_NOT_MINUTE_DRAWDOWN')
        if value < pending['trough_NAV']:
            pending.update(trough_NAV=value, trough_date=dates[i], trough_endpoint_us=endpoint)
        pending.update(last_NAV=value, last_date=dates[i], last_endpoint_us=endpoint,
            duration_days=(endpoint-pending['peak_endpoint_us'])/DAY,
            depth_fraction=1-pending['trough_NAV']/pending['peak_NAV'],
            underwater_observations=pending['underwater_observations']+1)
    if pending is not None:
        episodes.append(pending)
    return episodes


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--protocol', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    assert args.protocol.resolve().is_relative_to(ROOT/'protocols')
    assert args.output.resolve().is_relative_to(ROOT/'reports') and not args.output.exists()
    protocol = json.loads(args.protocol.read_bytes())
    assert protocol['git_parent'] == subprocess.check_output(
        ['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    assert protocol['blocks_days'] == [7, 30, 60] and protocol['primary_block_days'] == 60
    assert protocol['samples_per_case_per_block'] == 2000 and protocol['seed'] == 20261005
    assert protocol['fixed_tranche_indices'] == [[0,101],[101,202],[202,303]]
    assert protocol['full_capital_USDT'] == 10000
    for name, digest in protocol['source_hashes'].items():
        assert sha(ROOT/name) == digest, name
    began = time.monotonic()
    before = resources.status()
    shared_peak = before['ram_current_bytes']
    event = dict.fromkeys(FIELDS)
    event.update(experiment_id=protocol['experiment_id'], git_commit=protocol['git_parent'],
                 data_manifest_hash='SAVED_ACCEPTED_DAILY_NAV_ONLY', protocol_hash=sha(args.protocol),
                 model_family='NONE', fits=0, all_folds='SEEN_POST_SELECTION_303D_NOT_OOS',
                 reason_for_next_experiment=protocol['question'], result_influenced_later_choice='NONE_BEFORE_RUN')
    append_event(ROOT/'reports/experiment_registry.jsonl', dict(event,
        event_id=protocol['experiment_id']+':START', event_type='OPERATIONAL_RESEARCH_START',
        success_failure='START_SAVED_PAIR_TIME_DIAGNOSTIC'))
    result = dict(status='FAILED_SAVED_PAIR_TIME_DIAGNOSTIC', task_id=os.environ['COIN_TASK_ID'],
                  protocol_sha256=sha(args.protocol), source_sha256=sha(Path(__file__)),
                  pairs=[], independent_market_evidence=False, selection_bias_corrected=False,
                  actual_risk_matched=False, models_fit=0, HPO=0, market_replays=0,
                  candidate='NONE', investment='CASH', long_term_APR='NOT_EVALUABLE')
    try:
        baseline = read(protocol['baseline_report'])
        challenger = read(protocol['challenger_report'])
        for receipt in protocol['accepted_financial_reports']:
            assert read(receipt)['status'].startswith('PASS_CONFIGURED_N_')
        assert read(protocol['accepted_pair_diagnostic'])['status'] in {
            'COMPLETE_EXIT10_SAVED_PAIRED_DIAGNOSTIC_NOT_APR',
            'COMPLETE_FIXED_BLEND_SHARED_WALLET_PAIRED_DIAGNOSTIC_NOT_APR'}
        dates = [datetime.fromtimestamp((protocol['start_us']+i*DAY)/1e6, UTC).date().isoformat()
                 for i in range(303)]
        expected = np.arange(protocol['start_us']+DAY, protocol['end_us']+1, DAY, dtype=np.int64)
        assert len(expected) == 303 and len(baseline['cases']) == len(challenger['cases']) == 4
        for case in challenger['cases']:
            control = next(c for c in baseline['cases'] if c['id'] == case['id'])
            assert control['symbols'] == case['symbols'] and control['cost_id'] == case['cost_id']
            assert control['unit_id'] == case['unit_id']
            left, right = [daily(c, expected, protocol['full_capital_USDT']) for c in (control, case)]
            delta = right[2]-left[2]
            diff = right[3]-left[3]
            months = [summarize_slice(left, right, dates, dates.index(month+'-01'),
                max(i for i, date in enumerate(dates) if date.startswith(month))+1)
                for month in dict.fromkeys(date[:7] for date in dates)]
            tranches = [summarize_slice(left, right, dates, begin, end)
                        for begin, end in protocol['fixed_tranche_indices']]
            total = summarize_slice(left, right, dates, 0, 303)
            assert abs(total['paired_log_return_increment'] - math.log(right[0][-1]/left[0][-1])) < 1e-12
            assert abs(total['net_increment_USDT'] - (case['summary']['net_PnL']-control['summary']['net_PnL'])) < 1e-7
            assert abs(math.fsum(m['net_increment_USDT'] for m in months)-total['net_increment_USDT']) < 1e-7
            assert abs(math.fsum(t['paired_log_return_increment'] for t in tranches)-total['paired_log_return_increment']) < 1e-12
            intervals = []
            for block in protocol['blocks_days']:
                low, high = block_bootstrap_mean_ci(delta, block_days=block,
                    samples=protocol['samples_per_case_per_block'], seed=protocol['seed'])
                intervals.append(dict(block_days=block, mean_daily_log_increment=float(delta.mean()),
                    lower_mean_daily_log_increment=low, upper_mean_daily_log_increment=high,
                    includes_zero=low <= 0 <= high, complete_block_count_scale=303//block,
                    samples=2000, seed=20261005,
                    inference='DESCRIPTIVE_CIRCULAR_BLOCK_PERCENTILES_ASSUMPTION_SENSITIVE_NOT_SELECTION_ADJUSTED'))
            lags = {str(lag): (float(np.corrcoef(delta[:-lag], delta[lag:])[0,1])
                    if np.std(delta[:-lag]) > 0 and np.std(delta[lag:]) > 0 else None)
                    for lag in (1,7,30,60)}
            net = total['net_increment_USDT']
            result['pairs'].append(dict(case_id=case['id'], total=total, months=months,
                fixed_tranches=tranches, block_intervals=intervals, daily_log_increment_autocorrelation=lags,
                positive_increment_days=int((diff>1e-10).sum()), negative_increment_days=int((diff<-1e-10).sum()),
                unchanged_increment_days=int((np.abs(diff)<=1e-10).sum()),
                leave_one_month_out_arithmetic_descriptions=[dict(month=m['start'][:7],
                    net_increment_except_month_USDT=net-m['net_increment_USDT'],
                    scope='ARITHMETIC_CONCENTRATION_ONLY_NOT_A_REPLAY_OR_EXECUTABLE_DATE_SELECTION') for m in months],
                baseline_actual_volatility=control['summary']['daily_metrics']['annual_volatility'],
                challenger_actual_volatility=case['summary']['daily_metrics']['annual_volatility'],
                saved_daily_identities=dict(baseline=control['artifacts']['daily_nav.parquet'],
                                           challenger=case['artifacts']['daily_nav.parquet'])))
            if protocol.get('include_drawdown_episodes', False):
                pair = result['pairs'][-1]
                for name, wallet, original in (('baseline', left, control), ('challenger', right, case)):
                    episodes = drawdown_episodes(wallet[0], dates, protocol['full_capital_USDT'], protocol['start_us'])
                    pair[name+'_drawdown_episodes'] = episodes
                    pair[name+'_daily_max_drawdown'] = max((e['depth_fraction'] for e in episodes), default=0.)
                    pair[name+'_saved_minute_max_drawdown'] = original['summary']['minute_max_drawdown']
                pair['drawdown_clock_scope'] = ('Dates label completed UTC score days; real endpoint_us clocks govern duration. '
                    'Initial capital is at start_us; recovery ends an episode and is not an underwater observation. '
                    'Equality recovers and updates the latest peak; unrecovered endings are right censored.')
            shared_peak = max(shared_peak, resources.status()['ram_current_bytes'])
            assert time.monotonic()-began <= protocol['budget']['wall_seconds']
            assert resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024 <= protocol['budget']['RSS_bytes']
        result['status'] = 'COMPLETE_SAVED_PAIR_TIME_DIAGNOSTIC_POST_SELECTION_NOT_APR'
    except Exception as error:
        result.update(error_type=type(error).__name__, reason=str(error))
        raise
    finally:
        result.update(created_utc=datetime.now(UTC).isoformat(), elapsed_seconds=time.monotonic()-began,
            peak_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,
            shared_RAM_sampled_peak_bytes=shared_peak, resources_before=before, resources_after=resources.status())
        encoded = json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False)+'\n'
        assert len(encoded.encode()) <= protocol['budget']['output_bytes']
        with args.output.open('x') as stream:
            stream.write(encoded)
        append_event(ROOT/'reports/experiment_registry.jsonl', dict(event,
            event_id=protocol['experiment_id']+':RESULT', event_type='OPERATIONAL_RESEARCH_RESULT',
            success_failure=result['status'], artifact_path=args.output.relative_to(ROOT).as_posix(),
            artifact_sha256=sha(args.output)))
    print(json.dumps(dict(status=result['status'], pairs=len(result['pairs']),
        intervals_including_zero=[[i['includes_zero'] for i in p['block_intervals']] for p in result['pairs']])))


if __name__ == '__main__':
    main()
