"""Normal recorded-finance CLI for one fixed D060 Turtle LONG_ONLY variant.

Reuse accepted independent 303D inputs and Decimal wallet/NAV assertions.
Saved explicit intents certify direction/noADD identity only, not a complete
independent Turtle strategy, order-sizing oracle, native filters or rate units.
"""
from __future__ import annotations
import argparse
import gc
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import resource
import sys
import time

import polars as pl
from quant import resources
from scripts.research_v8.registry import FIELDS, append_event

ROOT = Path('/mnt/d/codex/coin')
STATE = Path('/home/xflops/coin-state')
CONTRACT = 'D060_FIXED303D_TURTLE_NO_ADD_CONDITIONAL_V1'
ACTUAL_STATUS = 'COMPLETE_D060_FOUR_FIXED303D_TURTLE_VARIANT_NOT_NATIVE_OR_APR'
STATUS = 'PASS_D060_FOUR_RECORDED_TURTLE_VARIANT_ACCOUNTING_NOT_NATIVE_OR_APR'
FAIL = 'FAIL_D060_RECORDED_TURTLE_VARIANT_ACCOUNTING'
SID = 'COIN_JESSE_TURTLERULES_4H_USDM_DELAYED_STOP_ADAPTER'
SYMBOLS = ('BTCUSDT', 'ETHUSDT')
VARIANTS = {'PYRAMID4': True, 'SINGLE_LAYER': False}
TOLS = dict(cash_USDT=1e-7, ratio=1e-10)
BUDGETS = dict(new_owned_bytes=100_000, wall_seconds=1800, peak_RSS_bytes=1_500_000_000)
FINANCE = 'scripts/investment/multi_asset_financial_audit.py'
FINANCE_SHA = '4568a8c6f1c7c8c0ff04e6631420210575a791f4d17e482f88a885b14d0e4666'
DATE = 'docs/archive/PERPETUAL_303_INDEPENDENT_ADAPTER_HELPERS_20261003_V1.py'
DATE_SHA = '356086d2534539dba0aecf04b1e716d39ec1f5bb5e1c5817b80affdb38d36b31'
MANIFEST_SHA = '8b665b2829eafd192871fe4a3bc418dac1c202ed54f7d2d5494545fa6636fbfa'
WARMUP_SHA = 'f18b9556288b1a90d1b5ef98e13f6418c7c77ed1de91c9111acb7fa082949d0d'
LOCK = 'state/dataset_lock.json'
LOCK_SHA = '29d930063842e9b1666869b4e5f9e3c8cd629313e57b9dadc328c6131b92f45d'


def need(ok, reason):
    if not bool(ok):
        raise ValueError(reason)


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def source_path(name):
    relative = Path(name)
    need(not relative.is_absolute() and '..' not in relative.parts and name != LOCK,
         'ROOT-relative non-private frozen source only')
    p = ROOT / relative
    need(p.is_file() and p.stat().st_size <= 2_000_000 and
         not any(a.is_symlink() for a in (p, *p.parents)) and
         (p.suffix in {'.py', '.json', '.toml', '.lock', '.md', '.ps1', '.sh', '.rs', '.txt'}
          or p.name.endswith('LICENSE')), 'Bound ordinary source/proof text: ' + name)
    return p


def load(name, digest, identity):
    path = source_path(name)
    need(sha(path) == digest, 'Exact independent dependency: ' + name)
    spec = importlib.util.spec_from_file_location(identity, path)
    value = importlib.util.module_from_spec(spec)
    sys.modules[identity] = value
    spec.loader.exec_module(value)
    return value


def verify(hashes):
    for name, digest in hashes.items():
        need(sha(source_path(name)) == digest, 'Frozen source/proof changed: ' + name)


def recorded_intents(case, base, owner):
    """Explicit submitted id -> notification intent_id -> actual financial leg."""
    trades = json.loads(base.payload(case['artifacts']['trades.json'], owner).read_bytes())
    meta = json.loads(base.payload(case['artifacts']['target_meta.json'], owner).read_bytes())
    need(meta['strategy_id'] == SID and meta['direction_mode'] == 'LONG_ONLY' and
         meta['allow_pyramiding'] is case['allow_pyramiding'] and
         meta['proactive_ADD_permission'] is case['allow_pyramiding'] and isinstance(meta['journal'], list),
         'Recorded direction and proactive ADD permission')
    intents, notices = {}, {}
    duplicates = dict(submissions=0, notifications=0)
    for row in meta['journal']:
        if row.get('event') == 'INTENT_SUBMITTED':
            key = row['id']
            value = {k: row[k] for k in ('symbol', 'side', 'signal_us', 'kind', 'reduce_only')}
            need(value['symbol'] in SYMBOLS and value['side'] in ('BUY', 'SELL') and
                 value['kind'] in ('ENTRY', 'ADD', 'EXIT', 'STOP', 'RISK_REDUCTION', 'TERMINAL'), 'Known intent identity')
            need(key not in intents or intents[key] == value, 'Conflicting submitted intent')
            duplicates['submissions'] += int(key in intents)
            intents[key] = value
        elif row.get('event') == 'ACTUAL_FILL_NOTIFIED':
            key = row['fill_id']
            need(key not in notices or notices[key] == row, 'Conflicting actual notification')
            duplicates['notifications'] += int(key in notices)
            notices[key] = row
    if not case['allow_pyramiding']:
        need(all(r['kind'] != 'ADD' for r in intents.values()), 'Single layer has no submitted proactive ADD')
    seen, fills, used, opens = set(), set(), set(), 0
    for trade in trades:
        key = (trade['fill_id'], trade['leg'])
        need(trade['leg'] in ('OPEN', 'CLOSE') and key not in seen, 'Unique actual financial leg')
        seen.add(key)
        notice = notices.get(trade['fill_id'])
        need(notice is not None and notice['intent_id'] in intents, 'Every financial leg has a reliable explicit intent')
        intent = intents[notice['intent_id']]
        need(all(intent[k] == trade[k] for k in ('symbol', 'side', 'signal_us')), 'Actual leg/intent identity')
        if trade['leg'] == 'OPEN':
            need(trade['side'] == 'BUY' and intent['kind'] in ('ENTRY', 'ADD') and
                 intent['reduce_only'] is False, 'Every real LONG_ONLY OPEN is BUY')
            opens += 1
        else:
            need(intent['kind'] in ('EXIT', 'STOP', 'RISK_REDUCTION', 'TERMINAL') and
                 intent['reduce_only'] is True, 'Every close has an explicit reducing intent')
        fills.add(trade['fill_id']); used.add(notice['intent_id'])
    return dict(recorded_financial_legs=len(trades), recorded_open_BUY_legs=opens,
        distinct_filled_orders=len(fills), distinct_filled_intents=len(used),
        submitted_ADD_intents=sum(r['kind'] == 'ADD' for r in intents.values()),
        no_proactive_ADD_verified=not case['allow_pyramiding'], duplicate_journal_records=duplicates,
        missing_or_guessed_mapping=0, target_meta_sha256=case['artifacts']['target_meta.json']['sha256'],
        complete_strategy_state_or_intent_sizing_independently_rebuilt=False)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('protocol', 'actual', 'plan', 'run-dir', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    need(os.environ.get('COIN_TASK_ID') and sys.prefix == str(STATE / 'v8-clean-env-20261002-v2') and
         pl.thread_pool_size() <= 2, 'Actual bounded clean CPU2 progress task')
    mature = load(FINANCE, FINANCE_SHA, '_d060_normal_finance')
    base, financial, derivation = mature.prepare_financial(SYMBOLS)
    g = base.module(base.GUARD, 'd060_metadata_guards', base.GUARD_SHA)
    plan, plan_sha = g.small(args.plan)
    own = sha(__file__)
    need(plan['ready_to_execute'] is True and plan['checker_sha256'] == own and
         plan['tolerances'] == TOLS and plan['budgets'] == BUDGETS, 'Frozen checker/tolerances/budgets')
    need(args.protocol.parent == ROOT / 'protocols' and args.actual.parent == ROOT / 'reports/fast_research' and
         args.output.parent == ROOT / 'reports/fast_research' and not args.output.exists() and
         plan['protocol_path'] == str(args.protocol.relative_to(ROOT)) and
         plan['actual_report'] == str(args.actual.relative_to(ROOT)), 'Exact frozen CLI invocation')
    run = args.run_dir
    need(run.parent == STATE and not run.is_symlink(), 'Dedicated STATE audit owner')
    if run.exists():
        need(run.is_dir() and {p.name for p in run.iterdir()} == {'ACTUAL_BINDING.json'} and
             sha(run / 'ACTUAL_BINDING.json') == plan_sha, 'Only exact prebound PLAN may precede audit')
    else:
        run.mkdir()
        (run / 'ACTUAL_BINDING.json').write_bytes(g.ordinary(args.plan).read_bytes())
    binding = dict(task_id=os.environ['COIN_TASK_ID'], checker_sha256=own, ACTUAL_BINDING_sha256=plan_sha,
        actual_reports={str(args.actual): plan['actual_report_sha256']}, protocol_sha256=plan['protocol_sha256'],
        source_hashes=dict(plan['source_hashes']), command=[sys.executable, *sys.argv])
    g.write(run / 'RUN_BINDING.json', binding)
    started = time.monotonic(); errors = dict(cash=0., ratio=0.); progress = None; caught = None
    report = dict(status=FAIL, binding=binding, independent_source_sha256=own, run_dir=str(run),
        run_binding_sha256=sha(run / 'RUN_BINDING.json'), cases=[], completed_cases_verified=0,
        tolerances=TOLS, maximum_errors=errors, resources_before=resources.status(),
        financial_scope='RECORDED_LEGS_CONDITIONAL_FUNDING_WALLET_MINUTE_DAY_MONTH_AND_INTENT_IDENTITY',
        complete_strategy_state_or_intent_sizing_independently_rebuilt=False,
        independent_Turtle_target_oracle_called=False, funding_rate_unit='UNCONFIRMED',
        funding_unit_certified=False, native_filters_certified=False, publication_certified=False,
        candidate='NONE', investment='CASH', long_term_APR='NOT_EVALUABLE', locked_consumed=False,
        old_QA_or_accounts_replayed=False, source_QA_calls=0, models_fit=0, orders_sent=0, GPU=0)
    event = dict.fromkeys(FIELDS)
    event.update(experiment_id=run.name, event_id=run.name + ':START', event_type='OPERATIONAL_RESEARCH_START',
        git_commit=None, data_manifest_hash=MANIFEST_SHA, protocol_hash=plan['protocol_sha256'],
        source_hashes={plan['protocol_path']: plan['protocol_sha256']}, feature_set='RECORDED_TURTLE_LONG_ONLY',
        labels='NONE', model_family='NONE', hyperparameters={'plan_sha256': plan_sha, 'variant': plan['required_variant']},
        seed=None, thresholds=TOLS, cost_assumptions='BASE27_STRESS43_RAW_FRACTION_PERCENT',
        all_folds='FIXED_SEEN_303D_FOUR_SCENARIOS', success_failure='START_BEFORE_FINANCIAL_PAYLOAD',
        reason_for_next_experiment='Independent recorded wallet and noADD identity evidence', result_influenced_later_choice=False)

    def bounded():
        g.bounded(resources.status())
        need(time.monotonic() - started <= BUDGETS['wall_seconds'] and
             resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024 <= BUDGETS['peak_RSS_bytes'], 'Finite wall/RSS')
        need(not any(p.is_symlink() for p in run.rglob('*')) and
             sum(p.stat().st_size for p in run.rglob('*') if p.is_file()) <= BUDGETS['new_owned_bytes'], 'Small audit owner, no data copies')

    try:
        bounded(); verify(plan['source_hashes'])
        need(plan['source_hashes'].get(FINANCE) == FINANCE_SHA and plan['source_hashes'].get(DATE) == DATE_SHA,
             'Normal mature finance and accepted 303D reader pinned')
        spec, proto_sha = g.small(args.protocol, plan['protocol_sha256'])
        actual, actual_sha = g.small(args.actual, plan['actual_report_sha256'])
        variant = plan['required_variant']
        need(variant in VARIANTS and type(plan['allow_pyramiding']) is bool and
             plan['allow_pyramiding'] is VARIANTS[variant] and spec['variants'] == VARIANTS and
             spec['contract_id'] == CONTRACT and spec['direction_mode'] == 'LONG_ONLY' and
             spec['strategy_id'] == SID and spec['initial_capital_USDT'] == 10000, 'Common one-factor/full-capital protocol')
        need(spec['cost_scenarios'] == [dict(id=k, half_spread_bps=v[0], slippage_bps=v[1], roundtrip_bps=v[2])
             for k, v in base.COSTS.items()] and spec['unit_scenarios'] == [dict(id=k, scale=float(v))
             for k, v in base.UNITS.items()], 'All predeclared cost and conditional funding unit scenarios')
        need(actual['status'] == ACTUAL_STATUS and actual['binding']['task_id'] == plan['actual_task_id'] and
             actual['binding']['protocol_sha256'] == proto_sha and actual['binding']['source_hashes'] == spec['source_hashes'] and
             actual['variant'] == variant and actual['allow_pyramiding'] is VARIANTS[variant] and
             actual['direction_mode'] == 'LONG_ONLY' and actual['strategy_id'] == SID and
             actual['initial_capital_USDT'] == 10000 and actual['actual_calendar_days'] == 303, 'New actual identity/scope')
        task = g.closed(plan['actual_task_id']); metadata = g.closed(plan['metadata_task_id'])
        caller, _ = g.small(STATE / 'task-progress' / ('task-' + os.environ['COIN_TASK_ID'] + '.json'))
        need(task['task']['ended_at'] <= metadata['task']['started_at'] and
             metadata['task']['ended_at'] <= caller['started_at'], 'Producer and PLAN preparation closed before financial payload')
        producer_run = Path(actual['run_dir'])
        need(producer_run.parent == STATE and not producer_run.is_symlink(), 'Actual exclusive producer owner')
        rb, rb_sha = g.small(producer_run / 'RUN_BINDING.json', plan['producer_run_binding_sha256'])
        need(rb == actual['binding'], 'Actual producer RUN_BINDING exact')
        hashes = dict(plan['source_hashes'])
        for name, digest in spec['source_hashes'].items():
            need(name not in hashes or hashes[name] == digest, 'No conflicting current source pin')
            hashes[name] = digest
        verify(hashes)
        need(sha(ROOT / LOCK) == LOCK_SHA, 'Private streaming SHA-only guard')
        manifest, _ = g.small(g.project(spec['input_manifest']['path']), spec['input_manifest']['sha256'])
        warm, _ = g.small(g.project(spec['warmup_acceptance']['path']), spec['warmup_acceptance']['sha256'])
        smoke, _ = g.small(g.project(spec['required_test']['path']), spec['required_test']['sha256'])
        need(spec['input_manifest']['sha256'] == MANIFEST_SHA and
             manifest['status'] == 'PASS_D045_FIXED_303D_USDM_INPUT_SOURCE_BINDING_NOT_ECONOMICS' and
             manifest['source_only'] is True and manifest['funding_rate_unit'] == 'UNCONFIRMED' and
             manifest['funding_unit_certified'] is False and len(manifest['source_files']) == 94 and
             [w['id'] for w in manifest['windows']] == plan['period_ids'] == ['303D'], 'Accepted 94 inputs, no unit upgrade')
        need(spec['warmup_acceptance']['sha256'] == WARMUP_SHA and
             warm['status'] == 'PASS_D047_OFFICIAL_4H_WARMUP_SOURCE_ONLY' and warm['source_only'] is True and
             len(warm['files']) == 4 and sum(r['rows'] for r in warm['files']) == 744, 'Accepted official 4h warmup scope')
        need(smoke['status'] == spec['required_test']['required_status'] ==
             'PASS_BOUNDED_RESEARCH_TESTS_SYNTHETIC_NOT_MARKET_RESULT' and smoke['test_exit_code'] == 0 and
             smoke['source_bytes_unchanged'] is True and all(smoke['junit_counts'][k] == 0
             for k in ('errors', 'failures', 'skipped')), 'New direct-path synthetic actual PASS')
        report.update(actual_task=task, metadata_task=metadata, synthetic_task=g.closed(smoke['binding']['task_id']),
            source_acceptance_task=g.closed(manifest['binding']['task_id']), warmup_acceptance_task=g.closed(warm['binding']['task_id']),
            actual_report_sha256=actual_sha, protocol_sha256=proto_sha, actual_run_binding_sha256=rb_sha,
            local_non_git_hash_guard={LOCK: LOCK_SHA}, variant=variant, allow_pyramiding=VARIANTS[variant], financial_derivation=derivation)
        warm_proofs = []
        for item in warm['files']:
            p = Path(item['normalized_path'])
            need(p.is_relative_to(STATE) and p.is_file() and not any(a.is_symlink() for a in (p, *p.parents)) and
                 p.stat().st_size == item['normalized_bytes'] and sha(p) == item['normalized_sha256'], 'Warmup byte identity only')
            warm_proofs.append(dict(id=item['source_id'], path=str(p), sha256=item['normalized_sha256'],
                bytes=item['normalized_bytes'], role='OFFICIAL_4H_WARMUP_ONLY'))
        need(len(actual['cases']) == actual['completed_cases'] == actual['required_cases'] == 4 and
             [c['id'] for c in actual['cases']] == plan['case_ids'] and
             {(c['cost_id'], c['unit_id']) for c in actual['cases']} == {(cost, unit) for cost in base.COSTS for unit in base.UNITS},
             'Exactly four new cost/unit selectors, no selective reporting')
        report['registration_start'] = append_event(ROOT / 'reports/experiment_registry.jsonl', event)
        from scripts.research_v7.oracle_flow_ceiling import Progress
        progress = Progress(); progress.value['detail'] = '新变体记录核账；不认证完整Turtle策略或原生执行'
        progress.update('独立读取303日金融必要列；不重源QA', 0, 4, '账户')
        date = load(DATE, DATE_SHA, '_d060_accepted_303_reader')
        _, reader, proof = date.prepare_financial_adapter()
        window = reader(manifest, manifest['windows'][0])
        need(window['days'] == 303 and window['count'] == 436320 and
             actual['input_proofs'] == window['proofs'] + warm_proofs, 'Every producer input bound to independent financial source')
        report.update(reader_derivation=proof, financial_input_bindings=window['proofs'], warmup_metadata_only=warm_proofs)
        hand = base.module(base.REFERENCE, 'd060_independent_decimal_hand', base.REFERENCE_SHA)
        for case in actual['cases']:
            need(case['period'] == '303D' and case['mode'] == case['summary']['mode'] == 'LONG_ONLY' and
                 case['variant'] == variant and case['allow_pyramiding'] is VARIANTS[variant] and
                 case['summary']['allow_pyramiding'] is VARIANTS[variant] and
                 case['strategy_id'] == case['summary']['strategy_id'] == SID, 'Fixed recorded recipe identity')
            contract = case['summary']['contract']
            need(contract['symbols'] == list(SYMBOLS) and contract['closing_min_notional_exempt'] is True and
                 contract['native_filters_certified'] is False and set(contract['instrument_profiles']) == set(SYMBOLS) and
                 all(p['quantity_step'] == '1E-8' and float(p['min_notional']) == 10 for p in
                     contract['instrument_profiles'].values()), 'Current shared account and conditional instrument profile')
            witness = recorded_intents(case, base, producer_run)
            progress.update('独立逐腿与全部分钟核账', len(report['cases']), 4, '账户', variant=variant,
                cost=case['cost_id'], funding_unit=case['unit_id'])
            result = financial(window, case, g, hand, producer_run, None, [], errors)
            report['cases'].append(dict(result, variant=variant, allow_pyramiding=VARIANTS[variant], strategy_id=SID,
                recorded_intent_checks=witness, complete_strategy_state_or_intent_sizing_independently_rebuilt=False,
                signal_reference='RECORDED_INTENT_IDENTITIES_NOT_COMPLETE_INDEPENDENT_TURTLE_ORACLE'))
            report['completed_cases_verified'] = len(report['cases'])
            gc.collect(); bounded()
        verify(hashes); bounded()
        report.update(status=STATUS, required_cases=4, financial_case_calls=4, verified_source_hashes=hashes,
            completed_full_calendar_cases_verified=sum(c['complete_calendar_verified'] for c in report['cases']),
            incomplete_or_halted_cases_verified=sum(not c['complete_calendar_verified'] for c in report['cases']),
            completed_source_files_verified=len(window['proofs']))
    except Exception as error:
        caught = error
        report.update(status=FAIL, error_type=type(error).__name__, reason=str(error))
    finally:
        report.update(actual_exit_code=1 if caught else 0, elapsed_seconds=time.monotonic() - started,
            peak_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024,
            resources_after=resources.status(), owned_bytes=sum(p.stat().st_size for p in run.rglob('*') if p.is_file()))
        g.write(args.output, report)
        append_event(ROOT / 'reports/experiment_registry.jsonl', dict(event, event_id=run.name + ':RESULT',
            event_type='OPERATIONAL_RESEARCH_RESULT', success_failure=report['status'],
            artifact_path=str(args.output.relative_to(ROOT)), artifact_sha256=sha(args.output)))
        if progress is not None:
            progress.update('记录核账退出', len(report['cases']), 4, '账户', actual_exit_code=report['actual_exit_code'])
            progress.stop.set(); progress.thread.join(timeout=3)
    print(json.dumps(dict(status=report['status'], cases=report['completed_cases_verified'], output=str(args.output))))
    return 1 if caught else 0


if __name__ == '__main__':
    raise SystemExit(main())
