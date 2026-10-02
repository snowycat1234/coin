import hashlib
import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path

root = Path('/mnt/d/codex/coin')
prefix = 'reports/fast_research/'
sha = lambda path: hashlib.sha256(Path(path).read_bytes()).hexdigest()
proofs = {
    'PUBLIC_STRATEGY_CHRONOLOGY_SOURCE_REUSE_20261002_V1.json': '388d3be0611c038df2f955a88c5be822e17d6cbda5f265fdef101f6abe23d8a2',
    'PUBLIC_STRATEGY_CHRONOLOGY_SOURCE_REUSE_EXIT_ARCHIVE_20261002_V1.json': 'b5913a66dd00c14e117ed9a95a8be0173ee8601ca97af631c2b00c909accdae3',
    'PUBLIC_STRATEGY_CONTINUOUS_90D_ACTUAL_20261002_V1.json': '87b3612321539b6fe8c408270efd8c8dee09ccae15489bef94fc5a751a7a6491',
    'PUBLIC_STRATEGY_CONTINUOUS_90D_TINY_20261002_V1.json': '7dab6b867c9e1fb9efbc8b5a11c6bd3c7b1d296819b6de59003072002c13caa6',
    'PUBLIC_STRATEGY_CONTINUOUS_90D_TINY_20261002_V2.json': 'cfba136819ec11f5bec42381d5aedff7c60349148e5031633fdb94946a24d81f',
    'PUBLIC_STRATEGY_CONTINUOUS_90D_ACTUAL_20261002_V2.json': '7e47d20fb71a8c6f87cc5b1adc26a2e031bb9bdbd8cf1a64d61ab6b4ac25642c',
    'PUBLIC_STRATEGY_CONTINUOUS_90D_ACTUAL_EXIT_MONTHS_20261002_V2.json': '86dbe235e2f3cdb96a0e89ab653506aa9f13d14681d6e2905e1be23af20179cc',
    'PUBLIC_STRATEGY_CONTINUOUS_90D_SOURCE_ARCHIVE_BINDING_20261002_V1.json': 'd3d8f8c4468097a609a42355e424170a3516e0f1c63f4783d70c79201b582748',
    'PUBLIC_STRATEGY_CONTINUOUS_90D_INDEPENDENT_ACTUAL_AUDIT_20261002_V2.json': 'd9a5ec7ddc00975992fbd499f5f22afb72200f420056d22f203b934bbf615d44',
    'PUBLIC_STRATEGY_CONTINUOUS_90D_INDEPENDENT_ACTUAL_AUDIT_20261002_V2_R2.json': '32c2d897171beb96aaa97f72f760664f5fa873e6075cbca79d4d7e17cb153ffe',
    'PUBLIC_STRATEGY_90D_AUDIT_ACTUAL_EXIT_AND_CODE_BINDING_20261002_V2_R2.json': 'a45fcefaadd28ccac59302376bdcfb6b79eacea85bf013e8ea5ba612cd820972',
}
proofs = {prefix + key: value for key, value in proofs.items()}
for name, digest in proofs.items():
    assert sha(root / name) == digest, name
read = lambda name: json.loads((root / (prefix + name)).read_text())
actual = read('PUBLIC_STRATEGY_CONTINUOUS_90D_ACTUAL_20261002_V2.json')
tiny = read('PUBLIC_STRATEGY_CONTINUOUS_90D_TINY_20261002_V2.json')
failure = read('PUBLIC_STRATEGY_CONTINUOUS_90D_ACTUAL_20261002_V1.json')
audit = read('PUBLIC_STRATEGY_CONTINUOUS_90D_INDEPENDENT_ACTUAL_AUDIT_20261002_V2_R2.json')
exit_proof = read('PUBLIC_STRATEGY_90D_AUDIT_ACTUAL_EXIT_AND_CODE_BINDING_20261002_V2_R2.json')
months = read('PUBLIC_STRATEGY_CONTINUOUS_90D_ACTUAL_EXIT_MONTHS_20261002_V2.json')
archives = read('PUBLIC_STRATEGY_CONTINUOUS_90D_SOURCE_ARCHIVE_BINDING_20261002_V1.json')
assert actual['status'] == 'COMPLETE_ACTUAL_PROXY_STRATEGY_SCREENING'
assert actual['completed_ledgers'] == actual['planned_ledgers'] == 15
assert actual['source_bytes_unchanged'] and actual['all_planned_ledgers_complete']
assert len(actual['folds']) == 1 and actual['folds'][0]['days'] == 90
assert actual['source_scope'] == 'OCT2025_FEB2026' and actual['source_days_per_symbol'] == 151
assert actual['source_month_files'] == 10
assert actual['binding']['all_folds'] == [{'id': 'CONT90', 'period_end_exclusive': '2026-03-01', 'period_start': '2025-12-01'}]
assert tiny['test_exit_code'] == 0 and tiny['source_bytes_unchanged']
assert actual['accepted_smoke_sha256'] == proofs[prefix + 'PUBLIC_STRATEGY_CONTINUOUS_90D_TINY_20261002_V2.json']
assert failure['status'] == 'FAIL_SIMPLE_STRATEGY_COMPARISON'
assert archives['preserved_failure']['completed_CASH_ledgers'] == 3
assert audit['status'] == 'PASS_ACTUAL_PROXY_LEDGER_ACCOUNTING_AND_SCOPE_WITH_NONPORTABLE_IPC_LIMIT'
assert audit['completed_ledgers_verified'] == 15 and audit['common_parameters_unchanged']
ipc = audit['input_memory_fingerprint']
assert ipc['status'] == 'NOT_REPRODUCED_NONPORTABLE_IPC_BYTES_NO_PASS_CLAIM'
assert ipc['schema_equal'] and ipc['singlefold_equals_whole_source'] and ipc['self_IPC_roundtrip_logical_values_equal']
assert ipc['exact_bound_Parquet_sha256'] == audit['derivative_source']['sha256']
assert sha(audit['derivative_source']['path']) == audit['derivative_source']['sha256']
assert exit_proof['independent_R2_actual_tool_exit']['exit_code'] == 0
assert exit_proof['actual_host_sessions']['actual_V2_runner'] == 4852
assert months['actual_outer_exit'] == 0 and months['actual_outer_session'] == 4852
assert months['all_monthly_net_and_gross_PnL_reconcile_period']
for entry in months['monthly_accounts']:
    assert [x['month'] for x in entry['months']] == ['2025-12', '2026-01', '2026-02']
    assert sum(x['days'] for x in entry['months']) == 90
    assert all(not x['account_reset_at_boundary'] and x['boundary_inventory_is_marked_not_liquidated'] for x in entry['months'])
    assert abs(sum(x['net_cash_PnL'] for x in entry['months']) - entry['period_net_return'] * 10_000) < 1e-6
    assert abs(sum(x['gross_cash_PnL_same_quantities'] for x in entry['months']) - entry['period_gross_cash_PnL_same_quantities']) < 1e-6
assert len(months['monthly_accounts']) == 15
sources = actual['binding']['source_hashes']
for name, digest in sources.items():
    assert sha(root / name) == digest, name
assert sources['scripts/investment/compare_simple_strategies.py'] == '3079ce734610fe1fb479411974d902b0aea4450e22c3a9c1b91e0f3f94c876b1'
assert sources['src/quant/backtest.py'] == 'ee333d4e5cbadb489e5d467619d0872f78ccb2d86d8b5f46eacc69cb63f9829a'
for item in exit_proof['exact_pure_code_archives']:
    assert sha(item['archive_path']) == item['sha256']
    proofs[str(Path(item['archive_path']).relative_to(root))] = item['sha256']
for item in archives['archives']:
    assert sha(root / item['path']) == item['sha256']
    proofs[item['path']] = item['sha256']
for name, key in [
    ('docs/archive/PUBLIC_STRATEGY_90D_SOURCE_ARCHIVE_BINDING_OPERATION_SOURCE_20261002_V1.py', archives['source_sha256']),
    ('docs/archive/PUBLIC_STRATEGY_CHRONOLOGY_SOURCE_REUSE_SOURCE_20261002_V1.py', 'd5293235d9001827f19d053e26cb3ae5a94e42cb865c647286aeddf145e2c0ed'),
]:
    assert sha(root / name) == key
    proofs[name] = key
tasks = []
for name, item in exit_proof['tasks'].items():
    path = Path(item['path'])
    value = json.loads(path.read_text())
    expected_exit = 1 if name in {'preserved_preledger_IPC_checker_failure', 'preserved_V1_runner_failure'} else 0
    assert sha(path) == item['sha256'] and value['exit_code'] == expected_exit
    assert value['status'] == ('failed' if expected_exit else 'completed')
    tasks.append(dict(name=name, path=str(path), sha256=sha(path), id=value['id'], exit_code=expected_exit))
assert actual['market_models_fit'] == actual['orders_sent'] == 0 and not actual['locked_consumed']
assert not actual['resources']['gpu_used'] and actual['resources']['swap_bytes'] == 0
assert actual['resources']['ram_peak_bytes'] < actual['resources']['ram_limit_bytes'] <= 5_000_000_000
assert actual['disk']['total_bytes'] < 32_000_000_000 and actual['owned_bytes'] < 512_000_000
receipt = dict(
    status='ROOT_ACCEPTED_90DAY_PROXY_ACCOUNTING_WITH_IPC_LIMIT_ONLY', created_utc=datetime.now(UTC).isoformat(),
    git_commit=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=root, text=True).strip(),
    source_hashes=sources, verified_prior_files=proofs, actual_task_bindings=tasks,
    actual_session=4852, actual_exit=0, independent_session=88702, independent_exit=0,
    completed_accounts=15, continuous_days=90, source_days_per_symbol=151,
    main_profitable_strategy='NONE', stable_research_references=['COIN_JESSE_DONCHIAN_1H_SPOT_ADAPTER', 'COIN_JESSE_DONCHIAN_2H_SPOT_ADAPTER'],
    economic_qualification='NO_QUALIFIED_CANDIDATE',
    decision='D015:2h lowered costs but chronology gross became negative; downgrade to defensive reference. Next one fixed2h-entry/1h-exit hypothesis, not HPO or a proved latency cause.',
    period_aggregates=actual['aggregate'], monthly_continuity_and_PnL_reconciliation=True,
    source_bytes_unchanged=True, earlier_green_or_old_ledger_reruns=0, price_rows_read_in_this_root_acceptance=0,
    root_receipt_builder_recovery='First metadata-only call exit1: absent completed_ledgers key in failed report. Preserved actual failure/archive proof supplies three CASH ledgers; no market rerun.',
    derivative_Parquet_sha256=audit['derivative_source']['sha256'], input_memory_fingerprint=ipc,
    unseen=False, accounts_from_different_periods_stitched=False, terminal_inventory_marked_not_assumed_flat=True,
    long_term_net_APR_proven=False, real_BBO=False, locked_consumed=False, models_fit=0, orders_sent=0, GPU_hours=0,
    peak_orchestrator_RSS_bytes=actual['orchestrator_peak_RSS_bytes'], owned_bytes=actual['owned_bytes'],
    latest_actual_disk_scan=actual['disk'], resources=actual['resources'])
out = root / (prefix + 'PUBLIC_STRATEGY_90D_ROOT_MODULE_ACCEPTANCE_20261002_V1.json')
with out.open('x') as writer:
    json.dump(receipt, writer, indent=2, ensure_ascii=False, allow_nan=False)
    writer.write('\n')
git_sources = dict(sources)
runtime = {'state/dataset_lock.json': git_sources.pop('state/dataset_lock.json')}
binding = dict(status='GIT_SOURCE_BINDING_EXCLUDES_IGNORED_RUNTIME_LOCK', source_hashes=git_sources,
    verified_prior_files={str(out.relative_to(root)): sha(out), **proofs}, verified_runtime_not_for_upload=runtime,
    scope='Full lock and actual source receipts checked; physical derivative Parquet and logical source bind accounting. Original memoryIPC not reproduced. No market rerun.')
with (root / 'reports/GITHUB_PUBLIC_STRATEGY_90D_SOURCE_BINDING_20261002_V1.json').open('x') as writer:
    json.dump(binding, writer, indent=2)
    writer.write('\n')
print(json.dumps(dict(status=receipt['status'], sha256=sha(out))))
