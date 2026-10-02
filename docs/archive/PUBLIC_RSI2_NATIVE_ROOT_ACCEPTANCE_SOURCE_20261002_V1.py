"""Metadata-only root acceptance after the six new RSI2 ledgers and audit exit0.

Saved summaries and identities only: no market decoding, old ledger replay,
kernel execution, green retest or model fit. Append one root RESULT when invoked.
"""
from __future__ import annotations

import argparse
from datetime import UTC, datetime
import hashlib
import json
import math
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path('/mnt/d/codex/coin')
STATE = Path('/home/xflops/coin-state')
REPORTS = ROOT / 'reports/fast_research'
STRATEGY = 'COIN_JESSE_RSI2_1H_SPOT_ADAPTER'
CONTROL = 'COIN_JESSE_DONCHIAN_2H_SPOT_ADAPTER'
HYBRID = 'COIN_JESSE_DONCHIAN_2H_ENTRY_1H_EXIT_SPOT_ADAPTER'
OUT = REPORTS / 'PUBLIC_RSI2_NATIVE_ROOT_MODULE_ACCEPTANCE_20261002_V1.json'
GIT_OUT = ROOT / 'reports/GITHUB_RSI2_NATIVE_SOURCE_BINDING_20261002_V1.json'
EVENT_ID = 'PUBLIC-RSI2-NATIVE-MODULE-20261002-V1:RESULT'
TINY = REPORTS / 'PUBLIC_RSI2_NATIVE_PIPELINE_TINY_20261002_V1.json'
PRE_COMMON = 'docs/archive/COMPARE_SIMPLE_STRATEGIES_PRE_RSI2_20261002_V1.py'
PRE_COMMON_SHA = 'bff0fe43a4a46406668a8a7bbe1d298397437a31d6ec623480abff2b2006131e'
AUDIT_STATUS = 'PASS_RSI2_NATIVE_RECEIVED_ASSET_FEE_PROXY_LEDGER_ACCOUNTING_AND_CAUSAL_SCOPE'
SAME_FIELDS = ('common_config', 'costs', 'folds', 'warmup_days', 'reused_minute_input',
               'fee_settlement', 'fee_profile_sha256')
SUMMARY_FIELDS = ('total_return', 'net_cash_PnL', 'gross_cash_PnL_same_quantities',
    'fees', 'spread_cost', 'slippage_cost', 'turnover', 'trade_count', 'round_trip_count',
    'annual_volatility', 'max_observed_minute_MDD', 'max_minute_marked_gross_weight',
    'max_minute_BTC_weight', 'max_minute_ETH_weight', 'terminal_marked_notional',
    'terminal_positions_flat', 'minimum_marked_cash', 'expired_orders', 'dust_orders')


def need(ok, message):
    if not bool(ok):
        raise ValueError(message)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(path):
    return json.loads(Path(path).read_text())


def proof(path, expected=None):
    path = Path(path)
    need(path.resolve().is_relative_to(ROOT) and not path.is_symlink() and path.is_file(),
         'Ordinary local metadata/code proof required: ' + str(path))
    digest = sha(path)
    need(expected is None or digest == expected, 'Frozen proof changed: ' + str(path))
    return str(path.relative_to(ROOT)), digest


def task(identity, host=None):
    need(isinstance(identity, str) and len(identity) == 32 and
         all(c in '0123456789abcdef' for c in identity), 'Actual task identity required')
    path = STATE / 'task-progress' / ('task-' + identity + '.json')
    saved = read(path)
    need(saved['id'] == identity and saved['status'] == 'completed' and saved['exit_code'] == 0,
         'Actual task must have completed with exit0')
    return dict(path=str(path), sha256=sha(path), task_id=identity,
        actual_host_session=host if host is not None else 'UNKNOWN_NOT_IN_RECEIPT',
        host_session_origin='Root observed completion' if host is not None else 'Not invented',
        actual_exit=0, actual_task=saved)


def merge(destination, hashes):
    for name, digest in hashes.items():
        key, checked = proof(ROOT / name, digest)
        need(key not in destination or destination[key] == checked, 'Conflicting CURRENT source: ' + key)
        destination[key] = checked


def archive(path, name):
    path, target = Path(path), ROOT / 'docs/archive' / name
    need(path.is_file() and not path.is_symlink(), 'Ordinary small source archive required')
    digest = sha(path)
    if target.exists():
        need(not target.is_symlink() and sha(target) == digest, 'Existing archive differs')
    else:
        with target.open('xb') as writer:
            writer.write(path.read_bytes())
    return dict(source=str(path), source_sha256=digest,
                archive_path=str(target.relative_to(ROOT)), archive_sha256=sha(target))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--audit', type=Path, required=True)
    parser.add_argument('--audit-sha256', required=True)
    parser.add_argument('--audit-host-session', type=int, required=True)
    parser.add_argument('--host-122', type=int, required=True)
    parser.add_argument('--host-90', type=int, required=True)
    parser.add_argument('--host-tiny', type=int, required=True)
    parser.add_argument('--decision', default='NOT_YET_CHOSEN_BY_ROOT')
    parser.add_argument('--next-experiment', default='NOT_YET_CHOSEN_BY_ROOT')
    args = parser.parse_args()
    need(all(value > 0 for value in (args.audit_host_session, args.host_122, args.host_90, args.host_tiny)),
         'Bind real root-observed host sessions')
    need(not OUT.exists() and not GIT_OUT.exists(), 'Do not overwrite root evidence')
    audit_path = args.audit if args.audit.is_absolute() else ROOT / args.audit
    need(audit_path.resolve().is_relative_to(REPORTS), 'Independent small audit report required')
    verified = dict([proof(audit_path, args.audit_sha256), proof(TINY), proof(ROOT / PRE_COMMON, PRE_COMMON_SHA)])
    audit, tiny = read(audit_path), read(TINY)
    need(audit['status'] == AUDIT_STATUS and audit['completed_ledgers_verified'] == 6 and
         len(audit['ledgers']) == 6, 'Actual independent six-ledger PASS required')
    need(not audit['locked_consumed'] and audit['orders_sent'] == audit['models_fit'] == 0,
         'No locked/orders/fits allowed')
    audit_task = task(audit['binding']['task_id'], args.audit_host_session)
    checker = Path(audit['independent_source'])
    need(checker.resolve().is_relative_to(STATE) or checker.resolve().is_relative_to(ROOT), 'Local checker required')
    need(sha(checker) == audit['independent_source_sha256'] == audit['binding']['checker_sha256'],
         'Independent frozen checker changed')
    audit_binding_path = checker.parent / 'ACTUAL_BINDING.json'
    audit_binding = read(audit_binding_path)
    need(tiny['status'] == 'PASS_SIMPLE_COMPARISON_SYNTHETIC_NOT_MARKET_RESULT' and
         tiny['test_exit_code'] == 0 and tiny['source_bytes_unchanged'] and
         tiny['junit_counts'] == dict(tests=1, errors=0, failures=0, skipped=0), 'Unique new integration1PASS required')
    need(not tiny['market_inputs_read'] and not tiny['locked_consumed'] and
         tiny['market_models_fit'] == tiny['orders_sent'] == 0, 'Synthetic-only tiny scope')
    tiny_task = task(tiny['binding']['task_id'], args.host_tiny)
    sources, outputs, accounts, actual_tasks, scans, protocols, kernel_acceptances = {}, [], [], [], [], {}, []
    merge(sources, tiny['binding']['source_hashes'])
    expected = {(fold, STRATEGY, spread) for fold in ('CONT122', 'CONT90') for spread in (2, 4, 8)}
    need({(v['fold'], v['strategy'], v['spread_bps']) for v in audit['ledgers']} == expected,
         'Six unique fixed period/cost/strategy pairs required')
    for period, host in (('122D', args.host_122), ('90D', args.host_90)):
        protocol_path = ROOT / ('protocols/PUBLIC_RSI2_BYBIT_' + period + '_V1.json')
        report_path = REPORTS / ('PUBLIC_RSI2_BYBIT_' + period + '_ACTUAL_20261002_V1.json')
        spec, actual = read(protocol_path), read(report_path)
        protocol_sha = sha(protocol_path)
        protocols[period] = protocol_sha
        verified.update([proof(protocol_path), proof(report_path)])
        need(actual['status'] == 'COMPLETE_ACTUAL_PROXY_STRATEGY_SCREENING' and
             actual['planned_ledgers'] == actual['completed_ledgers'] == 3 and
             actual['all_planned_ledgers_complete'] and actual['source_bytes_unchanged'], 'New actual3/3 complete required')
        need(actual['binding']['protocol_sha256'] == protocol_sha and
             actual['accepted_smoke_sha256'] == sha(TINY), 'Exact actual protocol/tiny binding required')
        need(actual['fee_settlement'] == 'BYBIT_SPOT_RECEIVED_ASSET_V1' and
             not actual['raw_normalized_market_files_read'] and not actual['locked_consumed'] and
             actual['market_models_fit'] == actual['orders_sent'] == 0, 'Proxy native-fee screening only')
        need(any(Path(key).name == report_path.name and digest == sha(report_path)
             for key, digest in audit['binding']['actual_reports'].items()), 'Audit must bind exact completed actual report')
        cases = [v for v in audit_binding['cases'] if v['period'] == period[:-1]]
        need(len(cases) == 1 and cases[0]['report_sha256'] == sha(report_path) and
             cases[0]['protocol_sha256'] == protocol_sha and cases[0]['actual_host_session_id'] == host and
             cases[0]['actual_task_id'] == actual['binding']['task_id'], 'Independent frozen actual prebinding mismatch')
        actual_tasks.append(task(actual['binding']['task_id'], host))
        merge(sources, actual['binding']['source_hashes'])
        reference = spec['paired_control_reference']
        need(reference['strategy_id'] == CONTROL, 'Fixed native2h reference required')
        verified.update([proof(ROOT / reference['protocol_path'], reference['protocol_sha256']),
                         proof(ROOT / reference['report_path'], reference['report_sha256'])])
        control_spec, control = read(ROOT / reference['protocol_path']), read(ROOT / reference['report_path'])
        need(all(spec[k] == control_spec[k] for k in SAME_FIELDS), 'Common cost/capital/risk/calendar/source mismatch')
        extras = spec['additional_reference_receipts']
        hybrid_path = ROOT / ('reports/fast_research/PUBLIC_DONCHIAN_HYBRID_BYBIT_' + period + '_ACTUAL_20261002_V1.json')
        verified.update([proof(hybrid_path, extras[str(hybrid_path.relative_to(ROOT))])])
        hybrid = read(hybrid_path)  # Saved summaries only; old financial arrays stay unread.
        kernel_binding = spec['official_kernel_acceptance']
        kernel_path = ROOT / kernel_binding['path']
        verified.update([proof(kernel_path, kernel_binding['sha256'])])
        kernel = read(kernel_path)
        need(kernel['status'] == 'PASS_OFFICIAL_RSI_KERNEL_SYNTHETIC_SEMANTICS' and
             not kernel['market_inputs_read'] and not kernel['locked_consumed'] and
             kernel['orders_sent'] == kernel['models_fit'] == 0, 'Official synthetic kernel acceptance required')
        kernel_task = task(kernel['binding']['task_id'])
        need(kernel_binding['actual_exit'] == 0 and kernel_binding['task_path'] == kernel_task['path'], 'Kernel actual exit/task binding')
        kernel_acceptances.append(dict(period=period, path=str(kernel_path.relative_to(ROOT)),
            sha256=sha(kernel_path), actual_task_binding=kernel_task, runtime=kernel['supplementary_runtime']))
        need(len(actual['folds']) == 1 and len(actual['folds'][0]['results']) == 3, 'One continuous account, three costs')
        fold = actual['folds'][0]
        physical = [v for v in audit['runtime_inputs'] if v['fold'] == fold['fold']]
        need(len(physical) == 1 and physical[0]['arrow_path'] == fold['minute_input_path'] and
             physical[0]['arrow_sha256'] == fold['minute_input_sha256'] and
             physical[0]['parquet_sha256'] == actual['minute_source']['sha256'] and
             physical[0]['physical_file_hash_checked'] and physical[0]['logical_values_and_schema_equal'],
             'Independent immutable-input metadata acceptance required')
        need(actual['minute_source']['sha256'] == control['minute_source']['sha256'] == hybrid['minute_source']['sha256'] and
             actual['minute_source']['rows'] == control['minute_source']['rows'] == hybrid['minute_source']['rows'] and
             actual['minute_source']['invalid_minutes'] == 0, 'Same accepted saved minute input')
        resource = actual['resources']
        need(resource['ram_limit_bytes'] <= 5_000_000_000 and resource['ram_peak_bytes'] <= resource['ram_limit_bytes'] and
             resource['swap_bytes'] == 0 and not resource['gpu_used'], 'Actual shared resource gate')
        scans.append(actual['disk'])
        outputs.append(dict(period=period, report_path=str(report_path.relative_to(ROOT)), report_sha256=sha(report_path),
            run_dir=actual['run_dir'], elapsed_seconds=actual['elapsed_seconds'], peak_RSS_bytes=actual['orchestrator_peak_RSS_bytes'],
            owned_bytes=actual['owned_bytes'], resources=resource, immutable_input_metadata=physical[0], market_bytes_reread=False))
        for row in fold['results']:
            need(row['strategy'] == STRATEGY and row['spread_bps'] in (2, 4, 8), 'Only fixed publicRSI2 configuration')
            checked = [v for v in audit['ledgers'] if (v['fold'], v['strategy'], v['spread_bps']) ==
                       (fold['fold'], STRATEGY, row['spread_bps'])]
            prior = [v for f in control['folds'] for v in f['results'] if
                     v['strategy'] == CONTROL and v['spread_bps'] == row['spread_bps']]
            peer = [v for f in hybrid['folds'] for v in f['results'] if
                    v['strategy'] == HYBRID and v['spread_bps'] == row['spread_bps']]
            need(len(checked) == len(prior) == len(peer) == 1, 'Unique saved reference and audit summaries')
            new, old, other = row['summary'], prior[0]['summary'], peer[0]['summary']
            need(new['initial_nav'] == old['initial_nav'] == other['initial_nav'] == 10000 and
                 new['period_days'] == old['period_days'] == other['period_days'], 'Same capital and duration')
            need(math.isclose(new['total_return'], checked[0]['net_return'], rel_tol=0, abs_tol=1e-12), 'Actual/audit net mismatch')
            accounts.append(dict(period=period, fold=fold['fold'], nominal_roundtrip_bps=row['nominal_roundtrip_bps'],
                rsi2={k:new[k] for k in SUMMARY_FIELDS}, native2h={k:old[k] for k in SUMMARY_FIELDS},
                hybrid_saved_summary={k:other[k] for k in SUMMARY_FIELDS}, rsi2_months=checked[0]['months'],
                delta_net_USDT_vs_native2h=new['net_cash_PnL']-old['net_cash_PnL'],
                delta_net_percentage_points_vs_native2h=(new['total_return']-old['total_return'])*100,
                delta_gross_shadow_USDT_vs_native2h=new['gross_cash_PnL_same_quantities']-old['gross_cash_PnL_same_quantities'],
                delta_total_cost_USDT_vs_native2h=sum(new[k]-old[k] for k in ('fees','spread_cost','slippage_cost')),
                delta_net_USDT_vs_hybrid=new['net_cash_PnL']-other['net_cash_PnL'],
                common_constraints_not_identical_realized_risk=True, old_financial_arrays_reread_or_reverified=False))
    need(sources.get(PRE_COMMON) == PRE_COMMON_SHA, 'Original bff common archive must be explicitly bound')
    need('state/dataset_lock.json' in sources, 'Actual runtime lock binding required')
    latest = max(scans, key=lambda value: datetime.fromisoformat(value['scan_finished_utc']))
    need(latest['total_bytes'] == latest['project_bytes'] + latest['wsl_vhd_bytes'] < 36_000_000_000,
         'Actual completed disk scan exceeds new-work stop limit')
    archives = [archive(__file__, 'PUBLIC_RSI2_NATIVE_ROOT_ACCEPTANCE_SOURCE_20261002_V1.py'),
        archive(checker, 'PUBLIC_RSI2_NATIVE_SIX_LEDGER_AUDIT_CHECKER_20261002_V1.py')]
    merge(sources, {v['archive_path']:v['archive_sha256'] for v in archives})
    merge(sources, verified)
    primary = [v for v in accounts if v['nominal_roundtrip_bps'] == 30]
    receipt = dict(status='SCREENING_FIXED_PUBLIC_RSI2_NO_QUALIFIED_CANDIDATE', created_utc=datetime.now(UTC).isoformat(),
        git_commit_before_module=subprocess.check_output(['git','rev-parse','HEAD'], cwd=ROOT, text=True).strip(),
        source_hashes=sources, verified_reports_and_protocols=verified, completed_new_ledgers=6, accounts=accounts,
        independent_audit_path=str(audit_path.relative_to(ROOT)), independent_audit_sha256=sha(audit_path),
        independent_audit_actual_exit=audit_task, audit_actual_input_binding_path=str(audit_binding_path),
        audit_actual_input_binding_sha256=sha(audit_binding_path), checker_source_sha256=sha(checker),
        actual_task_bindings=actual_tasks, synthetic_task_binding=tiny_task, official_kernel_acceptances=kernel_acceptances,
        actual_outputs=outputs, source_archives=archives, primary_cost_reference_bps=30, stress_costs_bps=[32,36],
        primary_window_returns={v['period']:v['rsi2']['total_return'] for v in primary},
        all_six_costed_accounts_positive=all(v['rsi2']['total_return'] > 0 for v in accounts),
        acceptance='Fixed publicRSI2 targets and six new proxy ledger/accounting/scope; previously seen historical screening only',
        current_profitable_main='NONE', candidate_status='NO_QUALIFIED_CANDIDATE', pooled_long_term_APR_proven=False,
        independent_period_accounts_not_stitched=True, identical_realized_risk_claimed=False,
        cost_scenario_winner_selected=False, native_Bybit_market_execution_proven=False,
        current_fee_counterfactual_on_Binance_history=True,
        gross_scope='Actual net received inventory same-quantity shadow; not a fee-free order strategy',
        source_reuse='Saved common minute input; old controls only saved summaries; no new market/source QA or old replay',
        locked_consumed=False, real_orders=0, models_fit=0, GPU=0,
        entire_D_disk_latest_completed_scan=latest, scan_is_historical_measurement_not_current=True,
        decision=args.decision, next_experiment=args.next_experiment,
        helper_source_sha256=sha(__file__), helper_operation_task_id=os.environ.get('COIN_TASK_ID','UNKNOWN'))
    gitproof = {**receipt, 'source_hashes':{k:v for k,v in sources.items() if k != 'state/dataset_lock.json'},
        'runtime_excluded_from_git':dict(path='state/dataset_lock.json', sha256=sources['state/dataset_lock.json'],
            verified_actual_runtime=True, reason='D-hosted market manifest; full runtime binding retained in root receipt')}
    sys.path.insert(0, str(ROOT))
    from scripts.research_v8.registry import FIELDS, append_event, read_verified
    registry = ROOT / 'reports/experiment_registry.jsonl'
    need(not any(v['event_id'] == EVENT_ID for v in read_verified(registry.read_bytes())), 'Root RESULT already exists')
    for path, content in ((OUT, receipt), (GIT_OUT, gitproof)):
        with path.open('x') as writer:
            json.dump(content, writer, ensure_ascii=False, indent=2, allow_nan=False); writer.write('\n')
    event = dict.fromkeys(FIELDS)
    event.update(experiment_id='PUBLIC-RSI2-NATIVE-MODULE-20261002-V1', event_id=EVENT_ID,
        event_type='OPERATIONAL_RESULT', git_commit=receipt['git_commit_before_module'],
        data_manifest_hash=sources['state/dataset_lock.json'], protocol_hash=hashlib.sha256(
            json.dumps(protocols,sort_keys=True,separators=(',',':')).encode()).hexdigest(),
        protocol_hash_scope='SHA256_CANONICAL_PERIOD_TO_FROZEN_PROTOCOL_DIGESTS',
        feature_set='FIXED_MIT_PUBLIC_RSI2_1H_TREND_PULLBACK', labels='NONE', model_family='NONE',
        hyperparameters='ONLY_FIXED_RSI2_SMA5_SMA200_THRESHOLD10_SCALAR240_NO_FIT_OR_HPO',
        seed='NOT_APPLICABLE_DETERMINISTIC', thresholds='CLOSE>SMA200_AND_RSI2<=10_ENTRY;HELD_CLOSE>SMA5_EXIT',
        cost_assumptions='Bybit Spot NonVIP10bp+spread2/4/8+slip4bpside; received-asset fees',
        all_folds=['CONT122','CONT90'], success_failure=receipt['status'],
        reason_for_next_experiment=args.next_experiment, result_influenced_later_choice=args.decision != 'NOT_YET_CHOSEN_BY_ROOT',
        artifact_path=str(OUT.relative_to(ROOT)), artifact_sha256=sha(OUT), source_hashes=sources)
    append_event(registry, event)
    print(json.dumps(dict(status=receipt['status'], output=str(OUT), sha256=sha(OUT),
        git_binding=str(GIT_OUT), git_binding_sha256=sha(GIT_OUT), completed_new_ledgers=6)))


if __name__ == '__main__':
    main()
