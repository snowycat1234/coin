"""Root metadata acceptance, run only after the six-ledger audit actually exits0.

Read saved reports/checker/task identities only. No market decoding, old ledger
math, tests, model fits or source QA. One append-only root RESULT on completion.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import subprocess
import sys
from datetime import UTC, datetime

ROOT = Path('/mnt/d/codex/coin')
STATE = Path('/home/xflops/coin-state')
REPORTS = ROOT / 'reports/fast_research'
STRATEGY = 'COIN_JESSE_DONCHIAN_2H_ENTRY_1H_EXIT_SPOT_ADAPTER'
CONTROL = 'COIN_JESSE_DONCHIAN_2H_SPOT_ADAPTER'
OUT = REPORTS / 'PUBLIC_DONCHIAN_HYBRID_NATIVE_ROOT_MODULE_ACCEPTANCE_20261002_V1.json'
GIT_BINDING = ROOT / 'reports/GITHUB_HYBRID_NATIVE_SOURCE_BINDING_20261002_V1.json'
EVENT_ID = 'PUBLIC-DONCHIAN-HYBRID-NATIVE-MODULE-20261002-V1:RESULT'
PROOFS = {
    'PUBLIC_DONCHIAN_HYBRID_TARGET_TINY_20261002_V1.json': '32086aa3f4d1e331da1dc4f3e1f242b433500690a65e53d98f08b6eeb534a808',
    'PUBLIC_DONCHIAN_HYBRID_NATIVE_PIPELINE_TINY_20261002_V1.json': '430e11b95368d5c5fcd1ef476557495aca72e923d48140e8c39d915ca135244b',
    'PUBLIC_DONCHIAN_HYBRID_BYBIT_122D_ACTUAL_20261002_V1.json': '9e7727b41b994db2ab1d3496094e22ef12de98ab841d050cd1c9c7fd31310313',
    'PUBLIC_DONCHIAN_HYBRID_BYBIT_90D_ACTUAL_20261002_V1.json': '3b6e1f58c9f76411a5d8bcddde29fdfc3c7bdb955a9f04013269599199c3bfb6',
    'BYBIT_SPOT_2H_122D_ACTUAL_20261002_V2.json': '53447ac3722829cb5c4db12f5b469b100edb20c05bbb6e9c83f29bce5138bee3',
    'BYBIT_SPOT_2H_90D_ACTUAL_20261002_V2.json': '329f9f923ed4fd8223e2e267a200c2e67036c8ce4f82a7fef0027efdd3b7960a',
    'BYBIT_SPOT_NATIVE_FEE_ROOT_MODULE_ACCEPTANCE_20261002_V1.json': '04b98fbf88f5a3ed06675f0e49299468410153f809d7368987afa82496cdc253',
    'BYBIT_SPOT_NATIVE_FEE_SIX_LEDGER_COMPOSITE_AUDIT_20261002_V1.json': '70fc1568e51019d2c13abb42eb7fd844a58f9c39e77f0ff27278f1b5f7d94c6f',
}
PROTOCOLS = {
    '122D': 'a246e414de3af91521ae0ddb26710cfe15a1fc90e0f764389f782eb91deaf06f',
    '90D': '2d921a889e174cf18f52d1ccba1aa0d7973386dadd7a3a1ceb58e0d234398602',
}
SAME_FIELDS = ('common_config', 'costs', 'folds', 'warmup_days',
               'reused_minute_input', 'fee_settlement', 'fee_profile_sha256')
SUMMARY_FIELDS = ('total_return', 'net_cash_PnL', 'gross_cash_PnL_same_quantities',
    'fees', 'spread_cost', 'slippage_cost', 'turnover', 'trade_count', 'round_trip_count',
    'annual_volatility', 'max_observed_minute_MDD', 'max_minute_marked_gross_weight',
    'max_minute_BTC_weight', 'max_minute_ETH_weight', 'terminal_marked_notional',
    'terminal_positions_flat', 'capacity_limits', 'expired_orders', 'dust_orders',
    'minimum_marked_cash', 'gross_pnl_definition')


def need(ok, message):
    if not bool(ok):
        raise ValueError(message)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(path):
    return json.loads(Path(path).read_text())


def task_binding(identity, host):
    need(isinstance(identity, str) and len(identity) == 32 and
         all(c in '0123456789abcdef' for c in identity), 'Actual task ID required')
    path = STATE / 'task-progress' / ('task-' + identity + '.json')
    task = read(path)
    need(task['id'] == identity and task['status'] == 'completed' and
         task['exit_code'] == 0, 'Actual completed exit0 required; running is not PASS')
    return dict(path=str(path), sha256=sha(path), task_id=identity,
                actual_host_session=host, host_session_origin='Root observed unified-exec completion',
                actual_exit=0, actual_task=task)


def merge_hashes(destination, hashes):
    for name, digest in hashes.items():
        path = ROOT / name
        need(path.resolve().is_relative_to(ROOT) and not path.is_symlink(), 'Local ordinary source required')
        need(sha(path) == digest, 'Actual source bytes changed: ' + name)
        need(name not in destination or destination[name] == digest, 'Conflicting current source: ' + name)
        destination[name] = digest


def archive(source, name):
    source, target = Path(source), ROOT / 'docs/archive' / name
    need(not source.is_symlink() and source.is_file(), 'Ordinary archive source required')
    digest = sha(source)
    reused = target.exists()
    if reused:
        need(not target.is_symlink() and sha(target) == digest, 'Existing archive differs')
    else:
        with target.open('xb') as writer:
            writer.write(source.read_bytes())
    return dict(source=str(source), source_sha256=digest,
                archive_path=str(target.relative_to(ROOT)), archive_sha256=sha(target),
                existing_exact_archive_reused=reused)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--audit', type=Path, required=True)
    parser.add_argument('--audit-host-session', type=int, required=True)
    parser.add_argument('--host-122', type=int, required=True)
    parser.add_argument('--host-90', type=int, required=True)
    args = parser.parse_args()
    need(args.host_122 == 77919 and args.host_90 == 7742 and args.audit_host_session > 0,
         'Bind root-observed actual sessions; never invent exits')
    need(not OUT.exists() and not GIT_BINDING.exists(), 'Refuse to overwrite prior root evidence')
    audit_path = args.audit if args.audit.is_absolute() else ROOT / args.audit
    need(audit_path.resolve().is_relative_to(REPORTS) and not audit_path.is_symlink(),
         'Independent small report within project required')
    audit = read(audit_path)
    need(sha(audit_path) == 'a1af8448c0b44b6e79cbb0123f942bde05b773f90ebb01b0a7b751c4f23f77c9',
         'Root-observed completed audit bytes required')
    need(audit['status'] == 'PASS_HYBRID_NATIVE_RECEIVED_ASSET_FEE_PROXY_LEDGER_ACCOUNTING_AND_CAUSAL_SCOPE'
         and audit['completed_ledgers_verified'] == 6 and len(audit['ledgers']) == 6,
         'Final independent six-account PASS required')
    need(not audit['locked_consumed'] and audit['orders_sent'] == audit['models_fit'] == 0,
         'No locked/orders/model fitting allowed')
    audit_task = task_binding(audit['binding']['task_id'], args.audit_host_session)
    need(audit.get('independent_task_id', audit_task['task_id']) == audit_task['task_id'], 'Audit task mismatch')
    if 'actual_host_session_id' in audit:
        need(audit['actual_host_session_id'] == args.audit_host_session, 'Audit host session mismatch')
    checker = Path(audit['independent_source'])
    need(checker.resolve().is_relative_to(STATE) or checker.resolve().is_relative_to(ROOT), 'Local checker required')
    need(sha(checker) == audit['independent_source_sha256'] == audit['binding']['checker_sha256'], 'Checker source changed')
    need(sha(checker) == 'd79bc8a156987786e190e606d27a1656dc059137e739cbc919780e7b12e77135', 'Frozen checker identity')
    audit_input_binding = checker.parent / 'ACTUAL_BINDING.json'
    need(sha(audit_input_binding) == '596fcd09bd34aa3a19b51b0f3e10537fcc1ae01c47d727b8f1dbfca7acc5786b',
         'Independent actual source/command binding changed')
    verified = {}
    for name, digest in PROOFS.items():
        need(sha(REPORTS / name) == digest, 'Receipt changed: ' + name)
        verified['reports/fast_research/' + name] = digest
    verified[str(audit_path.relative_to(ROOT))] = sha(audit_path)
    tiny = read(REPORTS / 'PUBLIC_DONCHIAN_HYBRID_NATIVE_PIPELINE_TINY_20261002_V1.json')
    need(tiny['status'] == 'PASS_SIMPLE_COMPARISON_SYNTHETIC_NOT_MARKET_RESULT'
         and tiny['test_exit_code'] == 0 and tiny['source_bytes_unchanged'] and
         tiny['junit_counts'] == dict(tests=1, errors=0, failures=0, skipped=0), 'New integration case actual PASS required')
    need(not tiny['market_inputs_read'] and not tiny['locked_consumed'] and
         tiny['market_models_fit'] == tiny['orders_sent'] == 0, 'Synthetic integration scope required')
    tiny_task = task_binding(tiny['binding']['task_id'], 65607)
    old_audit = read(REPORTS / 'BYBIT_SPOT_NATIVE_FEE_SIX_LEDGER_COMPOSITE_AUDIT_20261002_V1.json')
    source_hashes, outputs, actual_tasks, scans, accounts = {}, [], [], [], []
    # Only merge CURRENT actual/tiny source bindings. The old control runner
    # was legitimately changed; old report identities are static receipt hashes.
    merge_hashes(source_hashes, tiny['binding']['source_hashes'])
    expected_ledgers = {('CONT122', STRATEGY, s) for s in (2, 4, 8)} | {
                       ('CONT90', STRATEGY, s) for s in (2, 4, 8)}
    need({(v['fold'], v['strategy'], v['spread_bps']) for v in audit['ledgers']} == expected_ledgers,
         'Six unique fixed strategy/period/cost pairs required')
    for period, host in (('122D', args.host_122), ('90D', args.host_90)):
        protocol_path = ROOT / ('protocols/PUBLIC_DONCHIAN_HYBRID_BYBIT_' + period + '_V1.json')
        need(sha(protocol_path) == PROTOCOLS[period], 'Frozen hybrid protocol changed')
        spec = read(protocol_path)
        reference = spec['paired_control_reference']
        need(reference['strategy_id'] == CONTROL, 'Fixed native2h comparator required')
        need(sha(ROOT / reference['protocol_path']) == reference['protocol_sha256'] and
             sha(ROOT / reference['report_path']) == reference['report_sha256'], 'Control receipt/protocol changed')
        control_spec, control = read(ROOT / reference['protocol_path']), read(ROOT / reference['report_path'])
        need(all(spec[k] == control_spec[k] for k in SAME_FIELDS), 'Common period/cost/capital/risk/source mismatch')
        name = 'PUBLIC_DONCHIAN_HYBRID_BYBIT_' + period + '_ACTUAL_20261002_V1.json'
        actual = read(REPORTS / name)
        need(actual['status'] == 'COMPLETE_ACTUAL_PROXY_STRATEGY_SCREENING' and
             actual['completed_ledgers'] == actual['planned_ledgers'] == 3 and
             actual['all_planned_ledgers_complete'] and actual['source_bytes_unchanged'], 'Actual3/3 complete required')
        need(actual['binding']['protocol_sha256'] == PROTOCOLS[period] and
             actual['accepted_smoke_sha256'] == PROOFS['PUBLIC_DONCHIAN_HYBRID_NATIVE_PIPELINE_TINY_20261002_V1.json'],
             'Actual protocol/tiny binding mismatch')
        need(actual['fee_settlement'] == 'BYBIT_SPOT_RECEIVED_ASSET_V1' and
             not actual['raw_normalized_market_files_read'] and not actual['locked_consumed'] and
             actual['orders_sent'] == actual['market_models_fit'] == 0, 'Native fee screened scope required')
        audit_reports = audit['binding']['actual_reports']
        need(any(Path(key).name == name and value == sha(REPORTS / name)
                 for key, value in audit_reports.items()), 'Audit must bind exact completed actual report')
        actual_tasks.append(task_binding(actual['binding']['task_id'], host))
        merge_hashes(source_hashes, actual['binding']['source_hashes'])
        source_hashes[str(protocol_path.relative_to(ROOT))] = PROTOCOLS[period]
        fold = actual['folds'][0]
        need(len(actual['folds']) == 1 and len(fold['results']) == 3 and
             fold['minute_input_format'] == 'IMMUTABLE_ARROW_IPC_FILE_READ_BEFORE_SIGNALS_AND_EXECUTION', 'One continuous physical-input account fold')
        need(actual['minute_source']['sha256'] == control['minute_source']['sha256'] and
             actual['minute_source']['rows'] == control['minute_source']['rows'] and
             actual['minute_source']['invalid_minutes'] == 0, 'Same saved minute source/calendar required')
        physical = [v for v in audit['runtime_inputs'] if v['fold'] == fold['fold']]
        need(len(physical) == 1 and physical[0]['arrow_path'] == fold['minute_input_path'] and
             physical[0]['arrow_sha256'] == fold['minute_input_sha256'] and
             physical[0]['parquet_sha256'] == actual['minute_source']['sha256'] and
             physical[0]['physical_file_hash_checked'] and physical[0]['logical_values_and_schema_equal'],
             'Independent immutable input metadata binding required; root does not rescan market bytes')
        resource = actual['resources']
        need(resource['ram_limit_bytes'] <= 5000000000 and resource['ram_peak_bytes'] <= resource['ram_limit_bytes']
             and resource['swap_bytes'] == 0 and not resource['gpu_used'], 'Shared resource gate failed')
        scans.append(actual['disk'])
        outputs.append(dict(period=period, report_path='reports/fast_research/' + name,
            report_sha256=sha(REPORTS / name), run_dir=actual['run_dir'], elapsed_seconds=actual['elapsed_seconds'],
            peak_RSS_bytes=actual['orchestrator_peak_RSS_bytes'], owned_bytes=actual['owned_bytes'], resources=resource,
            immutable_input_metadata=physical[0], source_QA_or_market_bytes_rescanned=False))
        for row in fold['results']:
            need(row['strategy'] == STRATEGY and row['spread_bps'] in (2, 4, 8), 'Only fixed hybrid configuration')
            prior = [v for f in control['folds'] for v in f['results']
                     if v['strategy'] == CONTROL and v['spread_bps'] == row['spread_bps']]
            audited = [v for v in audit['ledgers'] if v['fold'] == fold['fold'] and
                       v['strategy'] == STRATEGY and v['spread_bps'] == row['spread_bps']]
            prior_audited = [v for v in old_audit['ledgers'] if v['fold'] == fold['fold'] and
                            v['strategy'] == CONTROL and v['spread_bps'] == row['spread_bps']]
            need(len(prior) == len(audited) == len(prior_audited) == 1, 'Exact saved summary/independent pair required')
            new, old, checked = row['summary'], prior[0]['summary'], audited[0]
            need(new['initial_nav'] == old['initial_nav'] == 10000 and new['period_days'] == old['period_days'], 'Identical capital and duration')
            need(math.isclose(new['total_return'], checked['net_return'], rel_tol=0, abs_tol=1e-12), 'Actual/audit net summary mismatch')
            accounts.append(dict(period=period, fold=fold['fold'], nominal_roundtrip_bps=row['nominal_roundtrip_bps'],
                hybrid={k: new[k] for k in SUMMARY_FIELDS}, native2h={k: old[k] for k in SUMMARY_FIELDS},
                delta_net_USDT=new['net_cash_PnL']-old['net_cash_PnL'],
                delta_net_percentage_points=(new['total_return']-old['total_return'])*100,
                delta_gross_shadow_USDT=new['gross_cash_PnL_same_quantities']-old['gross_cash_PnL_same_quantities'],
                delta_total_cost_USDT=(new['fees']+new['spread_cost']+new['slippage_cost'])-(old['fees']+old['spread_cost']+old['slippage_cost']),
                delta_minute_MDD_percentage_points=(new['max_observed_minute_MDD']-old['max_observed_minute_MDD'])*100,
                delta_actual_vol_percentage_points=(new['annual_volatility']-old['annual_volatility'])*100,
                hybrid_months=checked['months'], native2h_saved_audit_months=prior_audited[0]['months'],
                common_constraints_not_identical_realized_risk=True, old_control_financial_arrays_reread_or_reverified=False))
    need(all(v['delta_net_USDT'] < 0 for v in accounts if v['period'] == '122D') and
         all(v['delta_net_USDT'] > 0 for v in accounts if v['period'] == '90D'), 'Expected root-observed window tradeoff changed')
    latest = max(scans, key=lambda v: datetime.fromisoformat(v['scan_finished_utc']))
    need(latest['total_bytes'] == latest['project_bytes'] + latest['wsl_vhd_bytes'] < 32000000000,
         'Accepted scan exceeds source-add warning budget')
    # Freeze helpers had a metadata-only schema failure before any protocol write.
    # Its actual tool exits were supplied by root; no process/task is invented.
    freezer_records = [dict(path='.cache/freeze_hybrid_bybit_20261002_v1.py', sha256='2f9fc58b34c2a3066f38755a22a5ae8e149a791c0526b8d4dfca5086eb64a33c',
        tool_chunk='c84835', actual_exit=1, error="KeyError: control['results']", protocols_written=0, prices_read=0),
        dict(path='.cache/freeze_hybrid_bybit_20261002_v2.py', sha256='3d080856e74883937572f40e7047f5f42eb2ac54c96b8c77a321de4ebc26e651',
        tool_chunk='c46cfc', actual_exit=0, protocols_written=2, prices_read=0)]
    for item in freezer_records:
        need(sha(ROOT / item['path']) == item['sha256'], 'Frozen protocol helper changed')
    archives = [archive(__file__, 'PUBLIC_DONCHIAN_HYBRID_NATIVE_ROOT_ACCEPTANCE_SOURCE_20261002_V1.py'),
        archive(ROOT / freezer_records[0]['path'], 'PUBLIC_DONCHIAN_HYBRID_BYBIT_FREEZE_FAILED_SOURCE_20261002_V1.py'),
        archive(ROOT / freezer_records[1]['path'], 'PUBLIC_DONCHIAN_HYBRID_BYBIT_FREEZE_CORRECT_SOURCE_20261002_V2.py'),
        archive(ROOT / 'tests/test_hybrid_native_fee_integration.py', 'PUBLIC_DONCHIAN_HYBRID_NATIVE_INTEGRATION_TEST_SOURCE_20261002_V1.py'),
        archive(checker, 'PUBLIC_DONCHIAN_HYBRID_NATIVE_SIX_LEDGER_AUDIT_CHECKER_20261002_V1.py')]
    for item in archives:
        source_hashes[item['archive_path']] = item['archive_sha256']
    receipt = dict(status='SCREENING_MIXED_EXIT_MECHANISM_NO_WINNER',
        created_utc=datetime.now(UTC).isoformat(), git_commit_before_module=subprocess.check_output(
            ['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(), source_hashes=source_hashes,
        verified_prior_files=verified, independent_audit_path=str(audit_path.relative_to(ROOT)),
        independent_audit_sha256=sha(audit_path), independent_audit_actual_exit=audit_task,
        checker_source_path=str(checker), checker_source_sha256=sha(checker),
        audit_actual_input_binding_path=str(audit_input_binding), audit_actual_input_binding_sha256=sha(audit_input_binding),
        actual_task_bindings=actual_tasks, synthetic_task_binding=tiny_task, actual_outputs=outputs,
        completed_new_ledgers=6, accounts=accounts, source_archives=archives,
        protocol_freeze_metadata_failure_and_recovery=freezer_records,
        source_reuse='Same accepted derivative minutes; saved native2h control summaries only, no old financial replay or source QA',
        acceptance='Fixed hybrid and six actual proxy ledgers/accounting/scope accepted; seen historical screening only',
        outcome='WINDOW_DEPENDENT_TRADEOFF_NOT_UNIFIED_WINNER', current_profitable_main='NONE',
        candidate_status='NO_QUALIFIED_CANDIDATE', native_Bybit_market_execution_proven=False,
        current_fee_counterfactual_on_Binance_history=True, identical_realized_risk_claimed=False,
        primary_cost_reference_bps=30, stress_costs_bps=[32,36], cost_scenario_winner_selected=False,
        independent_period_accounts_not_stitched=True, pooled_long_term_APR_proven=False,
        diagnostic_scope='Exit lookback40h-to20h plus frequency; subsequent entry opportunities may differ',
        gross_scope='Same actual net received inventory shadow, not a fee-free gross order strategy',
        locked_consumed=False, real_orders=0, models_fit=0, GPU=0,
        entire_D_disk_latest_completed_scan=latest, scan_is_historical_measurement_not_current=True,
        decision='Pause this fixed hybrid recipe after mixed two-window evidence; preserve exit/breakout capability with new independent-time/information reopen condition',
        next_experiment='One fixed MIT public RSI2 long-only1h trend-pullback; mature official RSI dependency compatibility first, no custom RSI kernel/threshold or timeframe search; returns unknown',
        helper_source_sha256=sha(__file__), helper_operation_task_id=os.environ.get('COIN_TASK_ID', 'UNKNOWN'))
    # Only dataset_lock is excluded from the Git-only identity. It remains fully
    # verified in the actual-runtime receipt, never silently removed from it.
    need('state/dataset_lock.json' in source_hashes, 'Actual runtime data lock binding required')
    gitproof = {**receipt, 'source_hashes': {k:v for k,v in source_hashes.items() if k != 'state/dataset_lock.json'},
        'runtime_excluded_from_git': dict(path='state/dataset_lock.json', sha256=source_hashes['state/dataset_lock.json'],
            verified_actual_runtime=True, reason='Runtime market manifest stays D-hosted; root receipt retains full binding')}
    sys.path.insert(0, str(ROOT))
    from scripts.research_v8.registry import FIELDS, append_event, read_verified
    registry = ROOT / 'reports/experiment_registry.jsonl'
    need(not any(v['event_id'] == EVENT_ID for v in read_verified(registry.read_bytes())), 'Root RESULT already exists')
    with OUT.open('x') as writer:
        json.dump(receipt, writer, ensure_ascii=False, indent=2, allow_nan=False); writer.write('\n')
    with GIT_BINDING.open('x') as writer:
        json.dump(gitproof, writer, ensure_ascii=False, indent=2, allow_nan=False); writer.write('\n')
    event = dict.fromkeys(FIELDS)
    event.update(experiment_id='PUBLIC-DONCHIAN-HYBRID-NATIVE-MODULE-20261002-V1', event_id=EVENT_ID,
        event_type='OPERATIONAL_RESULT', git_commit=receipt['git_commit_before_module'],
        data_manifest_hash=source_hashes['state/dataset_lock.json'],
        protocol_hash=hashlib.sha256(json.dumps(PROTOCOLS, sort_keys=True, separators=(',', ':')).encode()).hexdigest(),
        protocol_hash_scope='SHA256_CANONICAL_PERIOD_TO_FROZEN_PROTOCOL_DIGESTS',
        feature_set='FIXED_MIT_PUBLIC_2H_ENTRY_1H_EXIT', labels='NONE', model_family='NONE',
        hyperparameters='ONLY_FIXED_20_200_RULES_NO_FIT_OR_HPO', seed='NOT_APPLICABLE_DETERMINISTIC',
        thresholds='FIXED_PRIOR20_UPPER_SMA200_ENTRY_PRIOR20_LOWER_EXIT',
        cost_assumptions='Bybit Spot NonVIP10bp+spread2/4/8+slip4bpside; received-asset settlement',
        all_folds=['CONT122','CONT90'], success_failure=receipt['status'],
        reason_for_next_experiment=receipt['next_experiment'], result_influenced_later_choice=True,
        artifact_path=str(OUT.relative_to(ROOT)), artifact_sha256=sha(OUT), source_hashes=source_hashes)
    append_event(registry, event)
    print(json.dumps(dict(status=receipt['status'], output=str(OUT), sha256=sha(OUT),
                         git_binding=str(GIT_BINDING), git_binding_sha256=sha(GIT_BINDING), accounts=6)))


if __name__ == '__main__':
    main()
