"""UNRUN D047 recorded-finance auditor; strategy/state certification is separate.

Reuse the accepted HandLedger, isolated-wallet journal and minute/day/month
assertions. No producer account/simulate/fixed_targets, old account replay,
source QA, API or funding-unit certification is called. The original SMA
target oracle is deliberately removed, never treated as a Turtle oracle.
Root must freeze ACTUAL_BINDING and every producer must close before use.
"""
from __future__ import annotations

import argparse
import ast
import gc
import hashlib
import importlib.util
import json
import os
import resource
import sys
import time
from pathlib import Path

import polars as pl
from quant import resources

ROOT = Path('/mnt/d/codex/coin')
STATE = Path('/home/xflops/coin-state')
BASE = 'docs/archive/PERPETUAL_DIRECTIONAL_INDEPENDENT_AUDITOR_20261003_V1.py'
BASE_SHA = '1c4b0bcb0b4dd954ae4cdb7f12b64426f2244ba554340ee23e7d73ddbac5c7bb'
DATE = 'docs/archive/PERPETUAL_303_INDEPENDENT_ADAPTER_HELPERS_20261003_V1.py'
DATE_SHA = '356086d2534539dba0aecf04b1e716d39ec1f5bb5e1c5817b80affdb38d36b31'
LOADER = 'docs/archive/PERPETUAL_213_INDEPENDENT_ADAPTER_HELPERS_20261003_V1.py'
LOADER_SHA = 'f50223ad5ec0da2be16ae3ac5447bec2d5763260566000893f1697483b7667e4'
STATUS = 'PASS_D047_TURTLE_RECORDED_PERPETUAL_ACCOUNTING_NOT_COMPLETE_STRATEGY_NATIVE_OR_LONG_TERM_APR'
ACTUAL_STATUS = 'COMPLETE_D047_FIXED303D_TURTLE4H_CONDITIONAL_ACCOUNTS_NOT_NATIVE_OR_LONG_TERM_APR'
CONTRACT = 'D047_FIXED303D_TURTLE4H_CALLBACK_CONDITIONAL_V1'
STRATEGY = 'COIN_JESSE_TURTLERULES_4H_USDM_DELAYED_STOP_ADAPTER'


def need(ok, message):
    if not bool(ok):
        raise ValueError(message)


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def base_module():
    path = ROOT / BASE
    need(not path.is_symlink() and sha(path) == BASE_SHA, 'Accepted financial source exact bytes')
    spec = importlib.util.spec_from_file_location('d047_accepted_independent_finances', path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def prepare_financial_only(base):
    """Delete only the saved-SMA-target read and its four oracle statements.

    Compile this entire span before arrays, to avoid late extraction failures.
    The journal finances and all minute/day/month/terminal assertions stay AST
    identical. No saved Turtle target is substituted as its own expectation.
    """
    path = ROOT / BASE
    tree = ast.parse(path.read_bytes())
    found = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == 'audit_case']
    need(len(found) == 1, 'One accepted complete financial function')
    function = found[0]
    original = list(function.body)
    removals = []
    retained = []
    for statement in original:
        text = ast.unparse(statement)
        if isinstance(statement, ast.Assign) and [ast.unparse(t) for t in statement.targets] == ['targets']:
            need(text == "targets = pl.read_parquet(paths['targets.parquet'])", 'Exact SMA artifact read')
            removals.append('READ_SMA_TARGETS')
        elif isinstance(statement, ast.Assign) and [ast.unparse(t) for t in statement.targets] == ['causal_keys']:
            need(text == "causal_keys = ('available_us', 'symbol', 'raw_signed_target', 'mode')", 'Exact SMA key set')
            removals.append('SMA_KEYS')
        elif isinstance(statement, ast.For) and 'STRICT_SMA_TARGET_DISAGREEMENT_NO_EPSILON_REPAIR' in text:
            need('target_expected.select(*causal_keys)' in text, 'Exact old SMA state comparison')
            removals.append('SMA_STATE_COMPARISON')
        elif isinstance(statement, ast.Expr) and text.startswith('need(targets.columns == target_expected.columns'):
            removals.append('SMA_SCHEMA_ASSERTION')
        elif isinstance(statement, ast.Expr) and text.startswith("same(targets['target_weight'], target_expected['target_weight']"):
            need('Independent signed covariance targets' in text, 'Exact old target-weight assertion')
            removals.append('SMA_WEIGHT_ASSERTION')
        else:
            retained.append(statement)
    need(sorted(removals) == sorted(['READ_SMA_TARGETS', 'SMA_KEYS', 'SMA_STATE_COMPARISON',
                                   'SMA_SCHEMA_ASSERTION', 'SMA_WEIGHT_ASSERTION']), 'Only five target-specific deletions')
    function.body = retained
    module_ast = ast.fix_missing_locations(ast.Module(body=[function], type_ignores=[]))
    namespace = dict(vars(base))
    exec(compile(module_ast, '<D047-private-recorded-finance-only>', 'exec'), namespace)
    proof = dict(source_path=BASE, source_sha256=BASE_SHA, removed_target_only_statements=removals,
                 retained_financial_AST_sha256=hashlib.sha256(ast.dump(module_ast, include_attributes=False).encode()).hexdigest(),
                 complete_Turtle_strategy_or_intent_oracle=False,
                 original_cash_tolerance_USDT=base.CASH_TOL, original_ratio_tolerance=base.RATIO_TOL)
    return namespace['audit_case'], proof


def pinned_source(guard, name, digest):
    path = guard.project(name)
    # Private lock is a hash-only capability; never read or parse its body.
    if name == 'state/dataset_lock.json':
        need(sha(path) == digest, 'Private source identity hash only')
    else:
        guard.small(path, digest, False)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for option in ('protocol', 'actual', 'run-dir', 'output'):
        parser.add_argument('--' + option, type=Path, required=True)
    args = parser.parse_args()
    base = base_module()
    guard = base.module(base.GUARD, 'd047_accepted_guards', base.GUARD_SHA)
    reference = base.module(base.REFERENCE, 'd047_independent_hand', base.REFERENCE_SHA)
    need(os.environ.get('COIN_TASK_ID') and sys.prefix == str(STATE / 'v8-clean-env-20261002-v2')
         and pl.thread_pool_size() <= 2, 'Actual clean bounded progress CPU2 task')
    need(args.run_dir.parent == STATE and args.run_dir.is_dir() and not args.run_dir.is_symlink()
         and {p.name for p in args.run_dir.iterdir()} == {'ACTUAL_BINDING.json'}
         and args.output.parent == ROOT / 'reports/fast_research' and not args.output.exists(),
         'New exclusive prebound audit paths')
    plan, plan_sha = guard.small(args.run_dir / 'ACTUAL_BINDING.json')
    own = sha(__file__)
    need(plan['ready_to_execute'] is True and plan['checker_sha256'] == own
         and plan['protocol_path'] == str(args.protocol.relative_to(ROOT))
         and plan['actual_report'] == str(args.actual.relative_to(ROOT)), 'Exact frozen invocation')
    need(plan['tolerances'] == dict(cash_USDT=base.CASH_TOL, ratio=base.RATIO_TOL), 'Original tolerances, no new epsilon')
    binding = dict(task_id=os.environ['COIN_TASK_ID'], checker_sha256=own, ACTUAL_BINDING_sha256=plan_sha,
                   actual_reports={str(args.actual): plan['actual_report_sha256']}, source_hashes=plan['source_hashes'])
    guard.write(args.run_dir / 'RUN_BINDING.json', binding)
    start = time.monotonic()
    before = resources.status()
    errors = dict(cash=0., ratio=0.)
    results = []
    report = dict(status='FAIL_D047_TURTLE_RECORDED_ACCOUNTING', binding=binding, run_dir=str(args.run_dir),
                  run_binding_sha256=sha(args.run_dir / 'RUN_BINDING.json'), independent_source_sha256=own,
                  tolerances=plan['tolerances'], maximum_errors=errors, cases=results,
                  complete_strategy_state_or_intent_sizing_independently_rebuilt=False,
                  daily_SMA_target_oracle_called=False, financial_scope='RECORDED_LEGS_AND_CONDITIONAL_FUNDING_WALLET_NAV_AND_RISK_ONLY',
                  funding_rate_unit='UNCONFIRMED', unit_certified=False, native_market_certified=False,
                  candidate='NO_QUALIFIED_CANDIDATE', long_term_APR='NOT_EVALUABLE', models_fit=0,
                  orders_sent=0, GPU=0, locked_consumed=False, old_finance_or_QA_replayed=False,
                  registry_scope='ROOT_RUNNER_START_BEFORE_PAYLOAD_AND_RESULT_AFTER_ACTUAL_COMPLETION_REQUIRED')
    caught = None
    try:
        guard.bounded(before)
        function, proof = prepare_financial_only(base)
        report['financial_derivation'] = proof
        need(plan['source_hashes'].get(DATE) == DATE_SHA and plan['source_hashes'].get(LOADER) == LOADER_SHA,
             'Accepted 303D date reader and loader exact pins')
        date = base.module(DATE, 'd047_accepted303_date_reader', DATE_SHA)
        _, reader, date_proof = date.prepare_financial_adapter()
        report['reader_derivation'] = date_proof
        spec, proto_sha = guard.small(args.protocol, plan['protocol_sha256'])
        actual, actual_sha = guard.small(args.actual, plan['actual_report_sha256'])
        need(spec['contract_id'] == CONTRACT and spec['period_ids'] == ['303D']
             and spec['cost_scenarios'] == [dict(id='BASE27', half_spread_bps=4, slippage_bps=4, roundtrip_bps=27),
                                           dict(id='STRESS43', half_spread_bps=8, slippage_bps=8, roundtrip_bps=43)]
             and spec['unit_scenarios'] == [dict(id='RAW_AS_FRACTION', scale=1.), dict(id='RAW_AS_PERCENT', scale=.01)],
             'Exactly four fixed original cost/unit conditions, no alternative policy or period')
        for key, value in dict(initial_capital_USDT=10000., modes=['LONG_SHORT'], annual_vol_target=.10,
                               past_covariance_completed_days=30, asset_abs_cap=.3, gross_cap=.6,
                               leverage=1, margin_mode='ISOLATED', MMR=.005, sizing_buffer=.99,
                               taker_fee_bps_per_side=5.5, timeframe_minutes=240, entry_period=20,
                               exit_period=10, ATR_period=20, ATR_stop_multiple=2,
                               maximum_pyramiding_levels=4, pyramiding_threshold_ATR=.5,
                               planned_selectors=4, planned_trading_account_simulations=4,
                               planned_constant_cash_baselines=0).items():
            need(spec['rules'][key] == value, 'Fixed shared economic/clock rule: ' + key)
        need(actual['status'] == plan['required_actual_status'] == ACTUAL_STATUS
             and actual['binding']['task_id'] == plan['actual_task_id']
             and actual['binding']['protocol_sha256'] == proto_sha
             and actual['binding']['source_hashes'] == spec['frozen_sources'], 'Actual exact complete producer identity')
        report['actual_task'] = guard.closed(plan['actual_task_id'])
        producer_run = Path(spec['run_dir'])
        rb, rb_sha = guard.small(producer_run / 'RUN_BINDING.json', actual['run_binding_sha256'])
        need(rb == actual['binding'], 'Actual producer run bytes')
        hashes = {str(args.protocol.relative_to(ROOT)): proto_sha, str(args.actual.relative_to(ROOT)): actual_sha}
        for name, digest in [*spec['frozen_sources'].items(), *plan['source_hashes'].items()]:
            need(name not in hashes or hashes[name] == digest, 'No conflicting source map')
            pinned_source(guard, name, digest)
            hashes[name] = digest
        need(plan['source_hashes'].get(BASE) == BASE_SHA
             and plan['source_hashes'].get(base.REFERENCE) == base.REFERENCE_SHA, 'Accepted independent math exact pins')
        manifest_ref = spec['input_manifest']
        manifest, _ = guard.small(guard.project(manifest_ref['path']), manifest_ref['sha256'])
        need(manifest['funding_rate_unit'] == 'UNCONFIRMED' and not manifest['funding_unit_certified'], 'No unit upgrade')
        smoke_ref = spec['required_smoke_receipt']
        smoke, _ = guard.small(guard.project(smoke_ref['path']), smoke_ref['sha256'])
        need(smoke['status'] == smoke_ref['required_status'] and smoke['test_exit_code'] == 0
             and smoke['source_bytes_unchanged'] is True, 'Exact sole new bridge/controller compatibility receipt')
        report['synthetic_task'] = guard.closed(smoke['binding']['task_id'])
        warm_ref = spec['warmup_acceptance']
        warm, warm_sha = guard.small(guard.project(warm_ref['path']), warm_ref['sha256'])
        need(warm['status'] == 'PASS_D047_OFFICIAL_4H_WARMUP_SOURCE_ONLY' and warm['source_only'] is True,
             'Warmup only, no investment qualification')
        report['warmup_task'] = guard.closed(warm['binding']['task_id'])
        warm_proofs = []
        for item in warm['files']:
            path = base.payload(item)
            warm_proofs.append(dict(id=item['source_id'], path=str(path), sha256=item['normalized_sha256'],
                                    bytes=item['normalized_bytes'], role='OFFICIAL_4H_WARMUP_ONLY'))
        report['warmup_metadata_only'] = dict(receipt_sha256=warm_sha, files=warm_proofs, rows_or_old_QA_reread=False)
        need([case['id'] for case in actual['cases']] == plan['case_ids']
             and actual['completed_cases'] == actual['required_cases'] == len(plan['case_ids']) == 4,
             'Exact planned four new selectors only')
        need({(c['mode'], c['cost_id'], c['unit_id']) for c in actual['cases']} ==
             {('LONG_SHORT', cost, unit) for cost in base.COSTS for unit in base.UNITS}
             and all(c['strategy_id'] == c['summary']['strategy_id'] == STRATEGY for c in actual['cases']),
             'Only the Turtle recipe; both fixed costs and unconfirmed funding interpretations retained')
        need([w['id'] for w in manifest['windows']] == plan['period_ids']
             and plan['period_ids'] == ['303D'], 'Sole predeclared accepted 303D financial period')
        need(len(actual['input_windows']) == len(manifest['windows']), 'Every original input binding')
        for window_spec, produced in zip(manifest['windows'], actual['input_windows'], strict=True):
            window = reader(manifest, window_spec)
            need(produced['id'] == window_spec['id'] and produced['input_proofs'] == window['proofs'] + warm_proofs,
                 'Exact original financial sources plus metadata-only official signal warmup')
            for case in [c for c in actual['cases'] if c['period'] == window_spec['id']]:
                results.append(function(window, case, guard, reference, producer_run, None, None, errors))
                results[-1]['complete_strategy_state_or_intent_sizing_independently_rebuilt'] = False
                results[-1]['signal_reference'] = 'NOT_AUDITED_BY_OLD_DAILY_TARGET_ORACLE'
                gc.collect()
                need(time.monotonic() - start <= plan['budgets']['wall_seconds']
                     and resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024 <= plan['budgets']['peak_RSS_bytes'], 'Fixed audit process budget')
            del window
            gc.collect()
        for name, digest in hashes.items():
            pinned_source(guard, name, digest)
        need(len(results) == len(plan['case_ids']), 'Every predeclared new case financially checked')
        report.update(status=STATUS, verified_source_hashes=hashes, actual_report_sha256=actual_sha,
                      protocol_sha256=proto_sha, actual_run_binding_sha256=rb_sha, required_cases=len(results),
                      completed_cases_verified=len(results), financial_case_calls=len(results),
                      completed_full_calendar_cases_verified=sum(row['complete_calendar_verified'] for row in results),
                      incomplete_or_halted_cases_verified=sum(not row['complete_calendar_verified'] for row in results))
    except Exception as error:
        caught = error
        report['failure'] = dict(type=type(error).__name__, reason=str(error))
    finally:
        report.update(elapsed_seconds=time.monotonic() - start, peak_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024,
                      resources_before=before, resources_after=resources.status())
        guard.write(args.output, report)
    if caught is not None:
        raise caught


if __name__ == '__main__':
    main()
