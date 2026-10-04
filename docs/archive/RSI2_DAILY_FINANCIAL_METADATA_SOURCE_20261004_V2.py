"""Bind one D058 four-case audit from completed small metadata only.

No producer loader, source payload, target calculation or financial call. The
normal checker itself prepares and verifies its reused financial span at run.
"""
import argparse
from datetime import UTC, datetime
import importlib.util
import os
from pathlib import Path
import sys
from types import SimpleNamespace

ROOT = Path('/mnt/d/codex/coin')
STATE = Path('/home/xflops/coin-state')
CHECKER = 'scripts/investment/multi_asset_financial_audit.py'
CHECKER_SHA = '55fd724633f8315e9e6de2d1c52b80379d5c19f7e075dbb4fd84a9c7280eb796'
GUARDS = 'docs/archive/MULTI_ASSET_WINTER_FINANCIAL_METADATA_SOURCE_20261004_V2.py'
GUARDS_SHA = '4c0ec557606eab50ae1ddbc338929fb9148c0827c87e9338ef5da559472792fa'
PRIOR = STATE / 'd054-november-ten-equal-financial-20261004-v1/ACTUAL_BINDING.json'
PRIOR_SHA = 'e402f2d22ec174da1f9ab11da52917d1223c6d5320c9381f746609f6631aa0fc'
ARCHIVE = 'docs/archive/RSI2_DAILY_FINANCIAL_METADATA_SOURCE_20261004_V2.py'
STRATEGY = 'COIN_JESSE_RSI2_1D_USDM_CONFIGURED_POOL_ADAPTER'
RECIPES = {
    'SEPNOV91': ('sep-nov', 91, 131040, 160),
    'DECFEB90': ('dec-feb', 90, 129600, 190),
}


def need(ok, message):
    if not ok:
        raise ValueError(message)


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--recipe', required=True, choices=tuple(RECIPES))
    parser.add_argument('--actual-task-id', required=True)
    parser.add_argument('--producer-host', required=True, nargs=3,
                        metavar=('SESSION', 'FINAL_CHUNK', 'EXIT_CODE'))
    for option in ('protocol', 'actual', 'run-dir', 'output', 'binding-protocol'):
        parser.add_argument('--' + option, type=Path, required=True)
    args = parser.parse_args()
    need(os.environ.get('COIN_TASK_ID'), 'Actual bounded metadata task required')
    session, chunk, exit_code = args.producer_host
    need(session.isdigit() and chunk and exit_code == '0', 'Recorded true producer host closure')
    # Standard-library guards are reused; their old main is never called.
    import hashlib
    guard_path = ROOT / GUARDS
    need(guard_path.is_file() and not any(p.is_symlink() for p in (guard_path, *guard_path.parents)),
         'Ordinary exact accepted metadata guard')
    with guard_path.open('rb') as stream:
        need(hashlib.file_digest(stream, 'sha256').hexdigest() == GUARDS_SHA, 'Accepted metadata guard bytes')
    g = load(guard_path, 'd058_reused_metadata_guards')
    protocol_path = g.project(args.protocol)
    actual_path = g.project(args.actual)
    need(protocol_path.parent == ROOT / 'protocols' and actual_path.parent == ROOT / 'reports/fast_research',
         'Public project protocol and small actual report')
    need(args.run_dir.parent == STATE and not args.run_dir.exists() and
         args.output.parent == ROOT / 'reports/fast_research' and not args.output.exists() and
         args.binding_protocol.parent == ROOT / 'protocols' and not args.binding_protocol.exists(),
         'Exclusive new financial directory, report and binding protocol')
    label, days, minutes, source_count = RECIPES[args.recipe]
    need(args.run_dir.name == 'd058-rsi2-daily-' + label + '-financial-20261004-v2',
         'One declared financial directory for this quarter')
    spec, protocol_sha = g.small(protocol_path)
    actual, actual_sha = g.small(actual_path)
    prior, _ = g.small(PRIOR, PRIOR_SHA)
    source_hashes = dict(prior['source_hashes'])
    need(len(source_hashes) == 14 and prior['source_archives'] == {}, 'Exact accepted fourteen-helper map')
    source_hashes[CHECKER] = CHECKER_SHA
    for name, digest in source_hashes.items():
        need(g.sha(g.project(name)) == digest, 'Unchanged independent helper: ' + name)
    pre_market = 'docs/archive/RSI2_DAILY_PRE_MARKET_FINANCIAL_CHECKER_SOURCE_20261004_V1.py'
    pre_sha = 'cefd6bd0051c24756da99a9f6bd52be80472951ef918004b90f92a5552406215'
    need(spec['independent_reference_pre_market_sha256'] == pre_sha and
         g.sha(g.project(pre_market)) == pre_sha, 'Unchanged actual pre-market reference preserved')
    import ast
    before = ast.parse(g.project(pre_market).read_text())
    after = ast.parse(g.project(CHECKER).read_text())
    bodies = ('prepare_financial', 'input_reader', 'rsi2_pool_target_reference', 'target_reference')
    for name in bodies:
        old = next(n for n in before.body if isinstance(n, ast.FunctionDef) and n.name == name)
        new = next(n for n in after.body if isinstance(n, ast.FunctionDef) and n.name == name)
        need(ast.dump(old, include_attributes=False) == ast.dump(new, include_attributes=False),
             'Source-extension guard repair preserves financial/target body: ' + name)
    checker = load(g.project(CHECKER), 'd058_normal_checker_metadata_only')
    scope = checker.calendar_scope(spec)
    need(scope['period_days'] == days and scope['required_minutes'] == minutes and
         actual['status'] in checker.ACTUAL_STATUSES and actual['actual_calendar_days'] == days and
         len(actual['cases']) == actual['completed_cases'] == actual['required_cases'] == 4 and
         actual['complete_calendar_cases'] == actual['calendar_complete_cases'] == 4 and
         actual['account_path'] == spec['account_path'], 'Exactly four completed continuous-quarter calendars')
    run = g.ordinary(Path(actual['run_dir']) / 'RUN_BINDING.json').parent
    need(run == STATE / ('d058-rsi2-daily-' + label + '-20261004-v1'), 'Exact new producer directory')
    rb, rb_sha = g.small(run / 'RUN_BINDING.json')
    task = g.closed(args.actual_task_id)
    need(actual['binding']['task_id'] == args.actual_task_id and actual['binding'] == rb and
         rb['protocol_sha256'] == protocol_sha and rb['source_hashes'] == spec['source_hashes'],
         'Actual report, true closed0 task and RUN_BINDING agree with consumed protocol')
    for name, digest in rb['source_hashes'].items():
        need(g.sha(g.project(name)) == digest, 'Producer consumed unchanged source: ' + name)
    manifest_ref = spec['data_manifest']
    manifest_path = Path(manifest_ref['path'])
    manifest, manifest_sha = g.small(manifest_path if manifest_path.is_absolute()
                                    else g.project(manifest_path), manifest_ref['sha256'])
    need(rb['manifest_sha256'] == manifest_sha, 'Producer consumed the exact accepted source manifest')
    symbols, pool_id = actual['cases'][0]['symbols'], actual['cases'][0]['pool']
    pools = [p for p in spec['pools'] if p['id'] == pool_id]
    need(len(pools) == 1 and symbols == pools[0]['symbols'] == manifest['selected_symbols'] and
         len(symbols) == len(set(symbols)) == 10 and
         spec['allocation'] == actual['allocation'] == 'EQUAL' and
         spec['strategy'] == actual['strategy_id'] == checker.RSI_POOL_STRATEGY == STRATEGY and
         spec['initial_capital_USDT'] == actual['initial_capital_per_comparison_account_USDT'] == 10000,
         'One exact ranked July ten-member momentum recipe and full shared capital')
    need(len({c['id'] for c in actual['cases']}) == 4 and
         {(c['cost_id'], c['unit_id']) for c in actual['cases']} ==
         {(cost, unit) for cost in ('BASE27', 'STRESS43') for unit in ('RAW_AS_FRACTION', 'RAW_AS_PERCENT')},
         'All four fixed cost and conditional funding-unit scenarios')
    for case in actual['cases']:
        summary = case['summary']
        need(case['symbols'] == symbols and case['pool'] == pool_id and
             summary['completion'] == 'COMPLETE_CONDITIONAL_ACCOUNT' and summary['stop_us'] is None and
             summary['completed_minutes'] == summary['required_minutes'] == minutes and
             summary['daily_metrics']['days'] == days, 'Complete calendar without a hidden halted prefix')
    records_function = (checker.continuous_source_records if args.recipe == 'SEPNOV91'
                        else checker.winter_source_records)
    _, certificates = records_function(manifest, tuple(symbols),
        SimpleNamespace(small=g.small, project=g.project, closed=g.closed), scope)
    need(len(manifest['market_records']) == 90 and len(manifest['daily_records']) == 70 and
         len(manifest['normalized_source_hashes']) == source_count and
         (args.recipe == 'SEPNOV91' or len(manifest['warmup_minute_records']) == 30),
         'Exact accepted score/warmup metadata identities, without payload QA')
    own = g.sha(__file__)
    archive = ROOT / ARCHIVE
    if archive.exists():
        need(g.sha(archive) == own, 'Existing metadata-helper archive has identical bytes')
    else:
        with archive.open('xb') as stream:
            stream.write(g.ordinary(__file__).read_bytes())
        need(g.sha(archive) == own, 'Exact used metadata-helper source archive')
    plan = dict(ready_to_execute=True, checker_sha256=CHECKER_SHA, source_hashes=source_hashes,
        preregistered_independent_reference=dict(path=pre_market, sha256=pre_sha),
        source_verification_repair='EXACT_TWO_PINNED_TEXT_SOURCE_SUFFIXES_ONLY',
        preserved_financial_target_function_bodies=list(bodies),
        source_archives={}, tolerances=prior['tolerances'], protocol_path=str(protocol_path.relative_to(ROOT)),
        protocol_sha256=protocol_sha, actual_report=str(actual_path.relative_to(ROOT)), actual_report_sha256=actual_sha,
        actual_task_id=args.actual_task_id, actual_closed_task=task, producer_run_binding_sha256=rb_sha,
        required_scope=scope, strategy=STRATEGY, allocation='EQUAL', required_financial_case_calls=4,
        independent_output_path=str(args.output.relative_to(ROOT)),
        independent_binding_protocol=str(args.binding_protocol.relative_to(ROOT)),
        producer_actual_host=dict(session=int(session), final_chunk=chunk, actual_exit_code=0),
        accepted_source_metadata_capabilities=certificates,
        metadata_helper=dict(path=ARCHIVE, sha256=own, task_id=os.environ['COIN_TASK_ID']),
        reused_metadata_guards=dict(path=GUARDS, sha256=GUARDS_SHA),
        prior_independent_helper_map=dict(path=str(PRIOR), sha256=PRIOR_SHA),
        audit_scope='NEW_RSI2_DAILY_QUARTER_RECORDED_SHARED_WALLET_INDEPENDENT_TARGETS_BOUNDARY_COUPONS_AND_FINAL_INVENTORY',
        metadata_scope='True completed producer and accepted source identities only; zero payload, QA or financial calls.',
        terminal_cash_required=False, full_market_intent_sizing_independently_rebuilt=False,
        investment_qualification_pass=False, old_QA_or_accounts_replayed=False,
        budgets=dict(new_owned_bytes=100000, wall_seconds=1800, peak_RSS_bytes=1500000000),
        created_utc=datetime.now(UTC).isoformat())
    need(plan['tolerances'] == dict(cash_USDT=1e-7, ratio=1e-10), 'Original financial tolerances')
    g.write(args.binding_protocol, plan)
    args.run_dir.mkdir()
    path = args.run_dir / 'ACTUAL_BINDING.json'
    with path.open('xb') as stream:
        stream.write(g.ordinary(args.binding_protocol).read_bytes())
    need(g.sha(path) == g.sha(args.binding_protocol), 'Identical frozen ROOT and STATE binding bytes')
    import json
    print(json.dumps(dict(recipe=args.recipe, plan=str(path), sha256=g.sha(path),
        binding_protocol=str(args.binding_protocol), producer_task_id=args.actual_task_id,
        required_scope=scope, financial_calls=0, source_payloads_read=0)))


if __name__ == '__main__':
    main()
