"""UNRUN D048 eight recorded-finance checks; no native-filter/strategy proof.

The accepted D047 preparation compiles the original independent finance span
before payload IO. Its HandLedger, reader, cash/ratio tolerances and minute,
event, daily/monthly assertions remain unchanged. Neither strategy target
method nor a producer account/simulation/controller is imported or called.
"""
from __future__ import annotations

import argparse
import gc
import hashlib
import importlib.util
import os
from pathlib import Path
import resource
import sys
import time

import polars as pl
from quant import resources

ROOT = Path('/mnt/d/codex/coin')
STATE = Path('/home/xflops/coin-state')
REUSED = 'scripts/investment/audit_turtle_perpetual.py'
REUSED_SHA = '722e48ca19b924d15f8922c13aebf021db8e11145130a97dca4e930e2f93ae53'
ACCOUNT = 'scripts/investment/perpetual_closing_exempt_account.py'
ACCOUNT_SHA = 'd4c1636be51b067be6b86437cd69f158320f47c258f0d78f0a47f21806c617ac'
VERSION = 'usdt_linear_perpetual_closing_exempt_account_v1'
PROFILE = 'CLOSING_MIN_NOTIONAL_EXEMPT_WITH_UNCERTIFIED_1E8_QUANTITY_V1'
CONTRACT = 'D048_FIXED303D_TURTLE_AND_HOLD_CLOSING_EXEMPT_CONDITIONAL_V1'
ACTUAL_STATUS = 'COMPLETE_D048_EIGHT_CLOSING_EXEMPT_CONDITIONAL_ACCOUNTS_NOT_NATIVE_OR_LONG_TERM_APR'
STATUS = 'PASS_D048_EIGHT_RECORDED_CLOSING_EXEMPT_PERPETUAL_ACCOUNTING_NOT_NATIVE_FILTERS_OR_LONG_TERM_APR'
RECIPES = {'COIN_JESSE_TURTLERULES_4H_USDM_DELAYED_STOP_ADAPTER': 'LONG_SHORT',
           'COIN_PAST30_COVARIANCE_CONSTANT_LONG_USDM_REFERENCE': 'LONG_ONLY'}
SELECTORS = {'COIN_JESSE_TURTLERULES_4H_USDM_DELAYED_STOP_ADAPTER': 'TURTLE_LONG_SHORT',
             'COIN_PAST30_COVARIANCE_CONSTANT_LONG_USDM_REFERENCE': 'HOLD_LONG_ONLY'}


def need(ok, message):
    if not bool(ok):
        raise ValueError(message)


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def recorded_finance():
    path = ROOT / REUSED
    need(not path.is_symlink() and sha(path) == REUSED_SHA, 'Exact accepted recorded-finance preparation')
    spec = importlib.util.spec_from_file_location('d048_accepted_recorded_finance', path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def profile(summary):
    expected = dict(version=VERSION, filter_profile_id=PROFILE,
        closing_min_notional_exempt=True, min_notional_scope='OPENING_LEGS_ONLY',
        opening_min_notional_assumption_USDT=10, min_quantity_assumption='1e-8',
        quantity_step_assumption='1e-8', quantity_profile_status='UNCERTIFIED_PROXY_NOT_API_PROFILE',
        historical_filters_certified=False, native_filters_certified=False,
        instrument_API_profile_available=False, native_liquidation_certified=False,
        mmr_assumption='0.005_NOT_NATIVE_RISK_TIER')
    need(summary['version'] == VERSION and all(summary['contract'][k] == v for k, v in expected.items()),
         'Every consumed account has the distinct closing-exempt uncertified proxy profile')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('protocol', 'actual', 'run-dir', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    reuse = recorded_finance()
    base = reuse.base_module()
    guard = base.module(base.GUARD, 'd048_accepted_guards', base.GUARD_SHA)
    hand = base.module(base.REFERENCE, 'd048_frozen_hand', base.REFERENCE_SHA)
    need(os.environ.get('COIN_TASK_ID') and sys.prefix == str(STATE / 'v8-clean-env-20261002-v2')
         and pl.thread_pool_size() <= 2, 'Clean bounded progress CPU2 caller')
    need(args.run_dir.parent == STATE and args.run_dir.is_dir() and not args.run_dir.is_symlink()
         and {p.name for p in args.run_dir.iterdir()} == {'ACTUAL_BINDING.json'}
         and args.output.parent == ROOT / 'reports/fast_research' and not args.output.exists(),
         'Exclusive new prebound financial attempt')
    plan, plan_sha = guard.small(args.run_dir / 'ACTUAL_BINDING.json')
    own = sha(__file__)
    need(plan['ready_to_execute'] is True and plan['checker_sha256'] == own
         and plan['protocol_path'] == str(args.protocol.relative_to(ROOT))
         and plan['actual_report'] == str(args.actual.relative_to(ROOT)), 'Exact frozen invocation')
    need(plan['tolerances'] == dict(cash_USDT=base.CASH_TOL, ratio=base.RATIO_TOL), 'Original tolerances unchanged')
    binding = dict(task_id=os.environ['COIN_TASK_ID'], checker_sha256=own, ACTUAL_BINDING_sha256=plan_sha,
        actual_reports={str(args.actual): plan['actual_report_sha256']}, source_hashes=plan['source_hashes'])
    guard.write(args.run_dir / 'RUN_BINDING.json', binding)
    started = time.monotonic(); before = resources.status()
    errors = dict(cash=0., ratio=0.); cases = []
    report = dict(status='FAIL_D048_RECORDED_CLOSING_EXEMPT_ACCOUNTING', binding=binding,
        run_dir=str(args.run_dir), run_binding_sha256=sha(args.run_dir / 'RUN_BINDING.json'),
        independent_source_sha256=own, tolerances=plan['tolerances'], maximum_errors=errors, cases=cases,
        financial_scope='RECORDED_LEGS_AND_CONDITIONAL_FUNDING_WALLET_NAV_AND_RISK_ONLY',
        complete_strategy_state_or_intent_sizing_independently_rebuilt=False,
        Turtle_target_oracle_called=False, HOLD_target_oracle_called=False,
        HOLD_change_vs_older_D045_is_pure_account_only_effect=False,
        HOLD_controller_scope='ACCEPTED_D046_TWO_RISK_ORDER_NORMALIZATION_ANCHORS_ALSO_REUSED_NOT_REBUILT',
        filter_profile=PROFILE, quantity_and_historical_filters_certified=False,
        funding_rate_unit='UNCONFIRMED', unit_certified=False, native_market_certified=False,
        candidate='NO_QUALIFIED_CANDIDATE', long_term_APR='NOT_EVALUABLE',
        old_finance_or_QA_replayed=False, models_fit=0, orders_sent=0, GPU=0, locked_consumed=False,
        registry_scope='COMPACT_ROOT_RUNNER_START_BEFORE_PAYLOAD_AND_RESULT_AFTER_COMPLETION_REQUIRED')
    caught = None
    try:
        guard.bounded(before)
        # Failfast preparation is metadata/AST only, before financial payloads.
        function, proof = reuse.prepare_financial_only(base)
        report['financial_derivation'] = proof
        need(plan['source_hashes'].get(REUSED) == REUSED_SHA
             and plan['source_hashes'].get(ACCOUNT) == ACCOUNT_SHA
             and plan['source_hashes'].get(reuse.DATE) == reuse.DATE_SHA
             and plan['source_hashes'].get(reuse.LOADER) == reuse.LOADER_SHA
             and plan['source_hashes'].get(reuse.BASE) == reuse.BASE_SHA
             and plan['source_hashes'].get(base.REFERENCE) == base.REFERENCE_SHA,
             'Exact original finance/reader/hand and distinct new product pins')
        date = base.module(reuse.DATE, 'd048_accepted303_reader', reuse.DATE_SHA)
        _, reader, date_proof = date.prepare_financial_adapter()
        report['reader_derivation'] = date_proof
        spec, proto_sha = guard.small(args.protocol, plan['protocol_sha256'])
        actual, actual_sha = guard.small(args.actual, plan['actual_report_sha256'])
        need(spec['contract_id'] == CONTRACT and spec['period_ids'] == ['303D']
             and spec['cost_scenarios'] == [dict(id='BASE27', half_spread_bps=4, slippage_bps=4, roundtrip_bps=27),
                                           dict(id='STRESS43', half_spread_bps=8, slippage_bps=8, roundtrip_bps=43)]
             and spec['unit_scenarios'] == [dict(id='RAW_AS_FRACTION', scale=1.), dict(id='RAW_AS_PERCENT', scale=.01)],
             'Exactly two recipes and all original cost/unit conditions in the fixed303 days')
        for key, value in dict(initial_capital_USDT=10000., annual_vol_target=.10,
            past_covariance_completed_days=30, asset_abs_cap=.3, gross_cap=.6, leverage=1,
            margin_mode='ISOLATED', MMR=.005, sizing_buffer=.99, taker_fee_bps_per_side=5.5,
            planned_selectors=8, planned_trading_account_simulations=8, planned_constant_cash_baselines=0).items():
            need(spec['rules'][key] == value, 'Fixed shared economic rule: ' + key)
        for key, value in dict(modes=list(SELECTORS.values()), account_version=VERSION,
            filter_profile_id=PROFILE, opening_min_notional_assumption_USDT=10,
            closing_min_notional_exempt=True, min_notional_scope='OPENING_LEGS_ONLY',
            min_quantity_assumption=1e-8, quantity_profile_status='UNCERTIFIED_PROXY_NOT_API_PROFILE',
            native_filters_certified=False, historical_filters_certified=False).items():
            need(spec['rules'][key] == value, 'Explicit proxy and two-recipe protocol rule: ' + key)
        need(spec['rules']['strategy_design'] == [dict(selector=SELECTORS[s], strategy_id=s,
            mode=mode, signal_timeframe_minutes=240 if mode == 'LONG_SHORT' else 1440)
            for s, mode in RECIPES.items()], 'Fixed original signal cadence and direction metadata')
        need(actual['status'] == plan['required_actual_status'] == ACTUAL_STATUS
             and actual['binding']['task_id'] == plan['actual_task_id']
             and actual['binding']['protocol_sha256'] == proto_sha
             and actual['binding']['source_hashes'] == spec['frozen_sources'], 'Exact complete producer processing receipt')
        report['actual_task'] = guard.closed(plan['actual_task_id'])
        producer_run = Path(spec['run_dir'])
        rb, rb_sha = guard.small(producer_run / 'RUN_BINDING.json', actual['run_binding_sha256'])
        need(rb == actual['binding'], 'Producer RUN_BINDING exact bytes')
        hashes = {str(args.protocol.relative_to(ROOT)): proto_sha, str(args.actual.relative_to(ROOT)): actual_sha}
        for name, digest in [*spec['frozen_sources'].items(), *plan['source_hashes'].items()]:
            need(name not in hashes or hashes[name] == digest, 'No conflicting hash-map aliases')
            reuse.pinned_source(guard, name, digest)  # Private lock remains stream-SHA only.
            hashes[name] = digest
        need(spec['frozen_sources'].get(ACCOUNT) == ACCOUNT_SHA, 'Producer consumed exact closing-exempt adapter')
        producer_source = 'scripts/investment/closing_exempt_research.py'
        need(producer_source in spec['frozen_sources']
             and plan['source_hashes'].get(producer_source) == spec['frozen_sources'][producer_source],
             'Frozen consumed producer binding, without importing its simulation or targets')
        manifest_ref = spec['input_manifest']
        manifest, _ = guard.small(guard.project(manifest_ref['path']), manifest_ref['sha256'])
        need(manifest['funding_rate_unit'] == 'UNCONFIRMED' and not manifest['funding_unit_certified'], 'No funding-unit upgrade')
        smoke_ref = spec['required_smoke_receipt']
        smoke, _ = guard.small(guard.project(smoke_ref['path']), smoke_ref['sha256'])
        need(smoke['status'] == smoke_ref['required_status'] and smoke['test_exit_code'] == 0
             and smoke['source_bytes_unchanged'] is True, 'Exact new closing-filter synthetic receipt')
        report['synthetic_task'] = guard.closed(smoke['binding']['task_id'])
        warm_ref = spec['warmup_acceptance']
        warm, warm_sha = guard.small(guard.project(warm_ref['path']), warm_ref['sha256'])
        need(warm['status'] == 'PASS_D047_OFFICIAL_4H_WARMUP_SOURCE_ONLY' and warm['source_only'] is True,
             'Already accepted Turtle signal warmup metadata only')
        report['warmup_task'] = guard.closed(warm['binding']['task_id'])
        warm_proofs = []
        for item in warm['files']:
            path = base.payload(item)
            warm_proofs.append(dict(id=item['source_id'], path=str(path), sha256=item['normalized_sha256'],
                bytes=item['normalized_bytes'], role='OFFICIAL_4H_WARMUP_ONLY'))
        report['warmup_metadata_only'] = dict(receipt_sha256=warm_sha, files=warm_proofs, rows_or_old_QA_reread=False)
        need([case['id'] for case in actual['cases']] == plan['case_ids']
             and len(set(plan['case_ids'])) == actual['completed_cases'] == actual['required_cases'] == 8,
             'Every predeclared new selector exactly once')
        expected = {(strategy, mode, cost, unit) for strategy, mode in RECIPES.items()
                    for cost in base.COSTS for unit in base.UNITS}
        need({(c['strategy_id'], c['mode'], c['cost_id'], c['unit_id']) for c in actual['cases']} == expected
             and all(c['summary']['strategy_id'] == c['strategy_id']
                     and c['selector_mode'] == SELECTORS[c['strategy_id']] for c in actual['cases']), 'Exact two recipe identities')
        for case in actual['cases']:
            profile(case['summary'])
        need([w['id'] for w in manifest['windows']] == plan['period_ids'] == ['303D']
             and len(actual['input_windows']) == 1, 'Sole previously accepted financial period')
        window_spec = manifest['windows'][0]
        window = reader(manifest, window_spec)
        produced = actual['input_windows'][0]
        need(produced['id'] == window_spec['id'] and produced['input_proofs'] == window['proofs'] + warm_proofs,
             'Exact original financial inputs plus distinct warmup metadata')
        for case in actual['cases']:
            need(case['period'] == '303D', 'No alternative period')
            cases.append(function(window, case, guard, hand, producer_run, None, None, errors))
            cases[-1].update(strategy_id=case['strategy_id'], selector_mode=case['selector_mode'], account_filter_profile=PROFILE,
                complete_strategy_state_or_intent_sizing_independently_rebuilt=False,
                signal_reference='NOT_REBUILT_RECORDED_FINANCE_ONLY_NO_TARGET_SELF_COMPARISON')
            gc.collect()
            need(time.monotonic() - started <= plan['budgets']['wall_seconds']
                 and resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024 <= plan['budgets']['peak_RSS_bytes'],
                 'Fixed independent process budget')
        del window; gc.collect()
        for name, digest in hashes.items():
            reuse.pinned_source(guard, name, digest)
        need(len(cases) == 8, 'Every new financial case checked without old-case replay')
        report.update(status=STATUS, verified_source_hashes=hashes, actual_report_sha256=actual_sha,
            protocol_sha256=proto_sha, actual_run_binding_sha256=rb_sha, required_cases=8,
            completed_cases_verified=len(cases), financial_case_calls=len(cases),
            completed_full_calendar_cases_verified=sum(r['complete_calendar_verified'] for r in cases),
            incomplete_or_halted_cases_verified=sum(not r['complete_calendar_verified'] for r in cases))
    except Exception as error:
        caught = error
        report['failure'] = dict(type=type(error).__name__, reason=str(error))
    finally:
        report.update(elapsed_seconds=time.monotonic() - started,
            peak_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024,
            resources_before=before, resources_after=resources.status())
        guard.write(args.output, report)
    if caught is not None:
        raise caught


if __name__ == '__main__':
    main()
