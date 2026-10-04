"""Finite development comparison of configurable pools in one shared account.

Normal target, account and event APIs are used directly. Original two assets
and the historical liquidity-selected pool use the same full capital, costs,
chronology and risk limits. This is neither native Bybit execution nor APR proof.
"""
from __future__ import annotations
import argparse
import gc
import hashlib
import json
import os
from pathlib import Path
import resource
import subprocess
import sys
import time
from datetime import UTC, datetime
from quant import disk, resources
from quant.paths import ROOT, STATE
from scripts.investment import perpetual_directional as engine
from scripts.investment import vol_managed_perpetual_target as hold
from scripts.investment import public_sma_pool_target as sma_pool
from scripts.investment import momentum_cash_pool_target as momentum_cash
from scripts.investment.perpetual_closing_exempt_account import USDTLinearPerpetualAccount
from scripts.research_v8.registry import FIELDS, append_event


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def write(path, value):
    with Path(path).open('x', encoding='utf-8') as stream:
        json.dump(value, stream, indent=2, ensure_ascii=False, allow_nan=False)
        stream.write('\n')


def terminal_evaluation_scope(cases):
    """A complete marked calendar is distinct from a completed cash exit."""
    from decimal import Decimal
    calendar = liquidated = 0
    for case in cases:
        summary = case['summary']
        calendar += summary['completed_minutes'] == summary['required_minutes']
        flat = all(Decimal(summary['positions'][symbol].get('decimal_strings', {}).get(
            'quantity', str(summary['positions'][symbol]['quantity']))) == 0
            for symbol in case['symbols'])
        engine.need(summary['terminal_cash_realized'] == flat,
                    'Cash realization must agree with every configured signed quantity')
        liquidated += flat
    return dict(calendar_complete_cases=calendar, terminal_cash_realized_cases=liquidated,
        liquidated_portfolio_return=('COMPLETE_CONDITIONAL_CASH_RETURN_NOT_NATIVE_OR_APR'
            if cases and liquidated == calendar == len(cases) else 'NOT_EVALUABLE'),
        marked_NAV_includes_unrealized=True)


def main():
    from scripts.investment.multi_asset_data import load_portfolio_window, load_accepted_two_asset_control
    # Reuse the established local progress publisher. No second UI/service.
    from scripts.research_v7.oracle_flow_ceiling import Progress
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--protocol', type=Path, required=True)
    parser.add_argument('--run-dir', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--pool-id', help='Run one predeclared pool in a fresh process for resource comparison')
    args = parser.parse_args()
    protocol = json.loads(args.protocol.read_bytes())
    run = args.run_dir.resolve()
    engine.need(run.is_relative_to(STATE) and not run.exists(), 'Exclusive D-hosted run directory')
    engine.need(args.output.resolve().is_relative_to(ROOT/'reports') and not args.output.exists(),
                'New small result artifact required')
    engine.need(os.environ.get('COIN_TASK_ID') and
        sys.prefix == str(STATE/'v8-clean-env-20261002-v2'), 'Bounded accepted WSL runtime required')
    allocation = protocol.get('allocation', 'EQUAL')
    strategies = {hold.STRATEGY_ID: ('EQUAL', hold),
                  hold.INVERSE_STRATEGY_ID: ('INVERSE_VOL_30D', hold),
                  sma_pool.STRATEGY_ID: ('EQUAL', sma_pool),
                  momentum_cash.STRATEGY_ID: ('EQUAL', momentum_cash)}
    identity = protocol['strategy']
    engine.need(identity in strategies and protocol['initial_capital_USDT'] == 10000 and
                allocation == strategies[identity][0],
                'Same full capital and one fixed rule, no search')
    target_module = strategies[identity][1]
    signal = ('CONSTANT_LONG_NOT_SMA_ALPHA' if target_module is hold else
              'PUBLIC_SMA50_200_LONG_OR_FLAT' if target_module is sma_pool else
              'PAST30_POSITIVE_ABSOLUTE_RETURN_LONG_OR_CASH')
    engine.need(bool(protocol['pools']) and
                len({p['id'] for p in protocol['pools']}) == len(protocol['pools']),
                'Nonempty configurable unique pools; saved controls need not be replayed')
    pools=[p for p in protocol['pools'] if args.pool_id is None or p['id']==args.pool_id]
    engine.need(bool(pools) and len({p['id'] for p in pools})==len(pools), 'Unique predeclared pool ID')
    experiment_id=protocol['experiment_id']+(':'+args.pool_id if args.pool_id else '')
    required_cases=4*len(pools)
    start = int(datetime.fromisoformat(protocol['start']).timestamp()*1_000_000)
    end = int(datetime.fromisoformat(protocol['end_exclusive']).timestamp()*1_000_000)
    engine.need(start < end <= int(datetime(2026,3,1,tzinfo=UTC).timestamp()*1_000_000),
                'Development window, locked boundary preserved')
    account_path = protocol.get('account_path', 'FRESH_SINGLE_WINDOW_SHARED_ACCOUNT')
    continuous_windows = {
        'CONTINUOUS_SHARED_ACCOUNT_SEP_NOV_91D': (
            '2024-09-01T00:00:00+00:00', '2024-12-01T00:00:00+00:00',
            'SEEN_DEVELOPMENT_CONTINUOUS_ACCEPTED_THREE_MONTH_MANIFEST'),
        'CONTINUOUS_SHARED_ACCOUNT_DEC_FEB_90D': (
            '2024-12-01T00:00:00+00:00', '2025-03-01T00:00:00+00:00',
            'SEEN_DEVELOPMENT_CONTINUOUS_NEXT_QUARTER_MANIFEST'),
    }
    continuous = account_path in continuous_windows
    engine.need(account_path == 'FRESH_SINGLE_WINDOW_SHARED_ACCOUNT' or continuous,
                'Explicit account capital path')
    if continuous:
        window_start, window_end, data_role = continuous_windows[account_path]
        engine.need((start, end) == (
            int(datetime.fromisoformat(window_start).timestamp()*1_000_000),
            int(datetime.fromisoformat(window_end).timestamp()*1_000_000)) and
            protocol.get('data_role') == data_role,
            'Fixed accepted continuous window; no monthly account reset')
    for path, digest in protocol['source_hashes'].items():
        engine.need(path != 'state/dataset_lock.json' and sha(ROOT/path) == digest, 'Source changed: '+path)
    manifest = Path(protocol['data_manifest']['path'])
    engine.need((manifest.resolve().is_relative_to(STATE) or manifest.resolve().is_relative_to(ROOT/'reports'))
        and sha(manifest) == protocol['data_manifest']['sha256'],
                'Accepted source/pool manifest binding required')
    # Only hash the closed-data policy; no private lock body is read or exported.
    engine.need(sha(ROOT/'state/dataset_lock.json') ==
        '29d930063842e9b1666869b4e5f9e3c8cd629313e57b9dadc328c6131b92f45d', 'Lock guard changed')
    run.mkdir()
    binding = dict(task_id=os.environ['COIN_TASK_ID'], command=[sys.executable,*sys.argv],
        git_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        protocol_sha256=sha(args.protocol), source_hashes=protocol['source_hashes'],
        manifest_sha256=sha(manifest), environment_lock_sha256=sha(ROOT/'environments/v8/uv.lock'))
    write(run/'RUN_BINDING.json', binding)
    event = dict.fromkeys(FIELDS)
    event.update(event_id=experiment_id+':START', event_type='OPERATIONAL_RESEARCH_START',
        experiment_id=experiment_id, git_commit=binding['git_commit'],
        data_manifest_hash=sha(manifest), protocol_hash=sha(args.protocol),
        feature_set='CLOSED_DAILY_' + signal + '_PAST30_SIGNED_COVARIANCE_' + allocation, labels='NONE',
        model_family='NONE', hyperparameters=protocol, seed=None, thresholds='FIXED_NO_SEARCH',
        cost_assumptions=dict(costs=engine.COSTS, funding_units=engine.UNITS),
        all_folds='SEEN_DEVELOPMENT_SAME_FULL_WINDOW', success_failure='START_BEFORE_NEW_ACCOUNTS',
        reason_for_next_experiment=protocol.get('question',
            'Does an ex ante liquidity pool improve net return or diversification?'),
        result_influenced_later_choice='NONE_BEFORE_RESULTS', fits=0)
    append_event(ROOT/'reports/experiment_registry.jsonl', event)
    result = dict(status='FAILED_MULTI_ASSET_DEVELOPMENT_COMPARISON', binding=binding,
        run_dir=str(run), cases=[], completed_cases=0, required_cases=required_cases,
        actual_calendar_days=(end-start)//engine.DAY, initial_capital_per_comparison_account_USDT=10000,
        capital_inside_each_portfolio='ONE_SHARED_ACCOUNT_NOT_SUMMED_ASSET_ACCOUNTS',
        pool_changes_only=target_module is hold and allocation == 'EQUAL',
        strategy_changed_between_pools=False,
        allocation=allocation, strategy_id=identity, directional_signal=signal,
        target_exchange='Bybit_VIP0', price_funding_source='Binance_USDM_CROSS_VENUE_PROXY',
        funding_unit_certified=False, native_filters_certified=False, candidate='NONE', investment='CASH',
        long_term_APR='NOT_EVALUABLE', model_fits=0, orders_sent=0, GPU=0, locked_consumed=False,
        resources_before=resources.status(), resources_by_pool=[])
    result['account_path'] = account_path
    result['capital_path_scope'] = ('ONE_INITIAL_WALLET_ONE_SIMULATE_CALL_PER_SCENARIO_FINAL_EXIT_ONLY'
        if continuous else 'FRESH_SINGLE_WINDOW_SHARED_ACCOUNT')
    progress = Progress()
    progress.value['detail'] = '多币共享资金规则回放；开发筛选，不是长期APR'
    began = time.monotonic()
    sampled_shared_peak = result['resources_before']['ram_current_bytes']
    reserve = int(protocol['budget']['owned_bytes'])

    def guard():
        nonlocal sampled_shared_peak
        status = resources.status()
        sampled_shared_peak = max(sampled_shared_peak,status['ram_current_bytes'])
        owned = sum(p.stat().st_size for p in run.rglob('*') if p.is_file())
        engine.need(owned <= reserve and time.monotonic()-began <= protocol['budget']['wall_seconds'],
                    'Finite output/wall research budget reached')
        engine.need(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024 <=
                    protocol['budget'].get('peak_RSS_bytes', 5_000_000_000),
                    'Finite process RSS research budget reached')

    try:
        progress.update('磁盘容量守卫；总扫描量未知', None, None, '扫描')
        measured = disk.check(reserve)
        measured['measured_utc'] = datetime.now(UTC).isoformat()
        result['disk_before'] = measured
        engine.need(measured['total_bytes']+reserve < 32_000_000_000, 'Expected footprint exceeds warning budget')
        for pool in pools:
            pool_began = time.monotonic()
            before_bytes = sum(p.stat().st_size for p in run.rglob('*') if p.is_file())
            symbols = engine.strategy.symbol_order(pool['symbols'])
            if protocol.get('data_role')=='EXISTING_ACCEPTED_TWO_ASSET_CONTROL':
                engine.need(symbols==('BTCUSDT','ETHUSDT'), 'Control source never substitutes other assets')
                window=load_accepted_two_asset_control(symbols, start, end)
            else:
                window = load_portfolio_window(manifest, symbols, start, end)
            engine.need(window['start'] == start and window['end'] == end,
                        'Reader dates differ from predeclared evaluation window')
            factory = lambda bars, decisions, mode: target_module.fixed_targets(
                bars,decisions,mode,symbols=symbols,allocation=allocation)
            for cost in engine.COSTS:
                for unit in engine.UNITS:
                    case_id = pool['id']+'_'+cost['id']+'_'+unit['id']
                    progress.update('实际同一多币账户',result['completed_cases'],required_cases,'账户',
                                    pool=pool['id'],symbols=len(symbols),cost=cost['id'],funding_unit=unit['id'])
                    case = engine.simulate(window,'LONG_ONLY',cost,unit,progress,guard,
                        target_factory=factory,account_factory=USDTLinearPerpetualAccount)
                    saved = engine.save_case(case,run/case_id)
                    result['cases'].append(dict(id=case_id,pool=pool['id'],symbols=list(symbols),
                        cost_id=cost['id'],unit_id=unit['id'],**saved))
                    result['completed_cases'] = len(result['cases'])
                    del case
                    gc.collect()
                    guard()
            result['resources_by_pool'].append(dict(pool=pool['id'],symbols=len(symbols),
                elapsed_seconds=time.monotonic()-pool_began,
                output_growth_bytes=sum(p.stat().st_size for p in run.rglob('*') if p.is_file())-before_bytes,
                process_RSS_peak_so_far_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,
                shared_RAM_sampled_peak_so_far_bytes=sampled_shared_peak,
                shared_kernel_lifetime_peak_bytes=resources.status()['ram_peak_bytes']))
            del window
            gc.collect()
        result['complete_calendar_cases'] = sum(
            c['summary']['completed_minutes']==c['summary']['required_minutes'] for c in result['cases'])
        engine.need(result['completed_cases']==required_cases and result['complete_calendar_cases']==required_cases,
                    'Incomplete accounts are not investment evidence')
        result.update(terminal_evaluation_scope(result['cases']))
        result['status'] = ('COMPLETE_PREDECLARED_PORTFOLIO_CASES_NOT_CROSS_POOL_COMPARISON_OR_APR'
            if args.pool_id else 'COMPLETE_MULTI_ASSET_SHARED_CAPITAL_DEVELOPMENT_COMPARISON_NOT_APR')
    except Exception as error:
        result.update(error_type=type(error).__name__,reason=str(error))
        raise
    finally:
        result.update(elapsed_seconds=time.monotonic()-began,
            peak_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,
            shared_RAM_sampled_peak_bytes=sampled_shared_peak,
            shared_peak_scope='SAMPLED_PER_RUN_PLUS_SEPARATE_KERNEL_LIFETIME_PEAK_NOT_RESET',
            owned_bytes=sum(p.stat().st_size for p in run.rglob('*') if p.is_file()),
            resources_after=resources.status(),created_utc=datetime.now(UTC).isoformat())
        write(args.output,result)
        append_event(ROOT/'reports/experiment_registry.jsonl',dict(event,
            event_id=experiment_id+':RESULT',event_type='OPERATIONAL_RESEARCH_RESULT',
            success_failure=result['status'], artifact_path=str(args.output.relative_to(ROOT)),artifact_sha256=sha(args.output)))
        progress.stop.set()
        progress.thread.join(timeout=3)
    print(json.dumps(dict(status=result['status'],cases=result['completed_cases'],
        liquidated_portfolio_return=result['liquidated_portfolio_return'],output=str(args.output))))


if __name__ == '__main__':
    main()
