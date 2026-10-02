import hashlib
import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path

root = Path('/mnt/d/codex/coin')
prefix = 'reports/fast_research/'
sha = lambda path: hashlib.sha256(Path(path).read_bytes()).hexdigest()
proofs = {
    'PUBLIC_DONCHIAN_2H_122D_ACTUAL_20261002_V1.json': '2c3799fc82858a6bda6ac42767cd6d740a9d532553dfb5607a3043006d5bce57',
    'PUBLIC_DONCHIAN_2H_122D_TINY_20261002_V1.json': 'aadf6d9a7c93201deca02186c16cba306ec09ef46ec2a780a0a7edf5a6831fb4',
    'PUBLIC_DONCHIAN_2H_INDEPENDENT_BOUNDARY_AUDIT_20261002_V1.json': '3ddce1e4858b67c837d64533f45ca6cff77b404c5ff83c28c24af352d4a68114',
    'PUBLIC_DONCHIAN_2H_122D_ACTUAL_EXIT_MONTHS_20261002_V1.json': 'b0904c3bbfb216fce85b77928a1cabe4215d8e38d03937add313c39ffb1524a0',
    'PUBLIC_DONCHIAN_2H_122D_INDEPENDENT_ACTUAL_AUDIT_20261002_V1.json': '5b5409b71fa7c838a6d11fde1d65e288ef4a78e4dc77daaa9571f92d710b506d',
    'PUBLIC_DONCHIAN_2H_AUDIT_ACTUAL_EXIT_AND_CODE_BINDING_20261002_V1.json': '7d64598ef18f367e734cc9d41d5261dfe83c9769ef1716e898792a84a7add4f9',
    'SIMPLE_STRATEGY_CONTINUOUS_122D_ACTUAL_20261002_V1.json': '62cb5604580e3af8de3bcf7d1db5f76343581ef44f656ba89f927ba4bdb24e94',
    'CONTINUOUS_122D_ROOT_MODULE_ACCEPTANCE_20261002_V1.json': '3a2979c9fd5e55b942e00c7340566e0e64db8ca06d49bfcd10195b761ea3df83',
}
proofs = {prefix + key: value for key, value in proofs.items()}
for name, digest in proofs.items():
    assert sha(root / name) == digest, name
read = lambda name: json.loads((root / (prefix + name)).read_text())
actual = read('PUBLIC_DONCHIAN_2H_122D_ACTUAL_20261002_V1.json')
tiny = read('PUBLIC_DONCHIAN_2H_122D_TINY_20261002_V1.json')
audit = read('PUBLIC_DONCHIAN_2H_122D_INDEPENDENT_ACTUAL_AUDIT_20261002_V1.json')
exit_proof = read('PUBLIC_DONCHIAN_2H_AUDIT_ACTUAL_EXIT_AND_CODE_BINDING_20261002_V1.json')
months = read('PUBLIC_DONCHIAN_2H_122D_ACTUAL_EXIT_MONTHS_20261002_V1.json')
reference = read('SIMPLE_STRATEGY_CONTINUOUS_122D_ACTUAL_20261002_V1.json')
assert actual['status'] == 'COMPLETE_ACTUAL_PROXY_STRATEGY_SCREENING'
assert actual['completed_ledgers'] == actual['planned_ledgers'] == 3
assert actual['source_bytes_unchanged'] and actual['all_planned_ledgers_complete']
assert actual['binding']['strategies'] == ['COIN_JESSE_DONCHIAN_2H_SPOT_ADAPTER']
assert len(actual['folds']) == 1 and actual['folds'][0]['days'] == 122
assert tiny['test_exit_code'] == 0 and tiny['source_bytes_unchanged']
assert actual['accepted_smoke_sha256'] == proofs[prefix + 'PUBLIC_DONCHIAN_2H_122D_TINY_20261002_V1.json']
assert audit['status'] == 'PASS_ACTUAL_PROXY_LEDGER_ACCOUNTING_AND_SCOPE'
assert audit['completed_ledgers_verified'] == 3 and audit['common_parameters_unchanged']
assert exit_proof['independent_checker_actual_tool_exit']['exit_code'] == 0
assert exit_proof['host_sessions']['actual_new2h_runner'] == 96916
assert months['actual_outer_exit'] == 0 and months['actual_outer_session'] == 96916
assert months['all_monthly_net_and_gross_PnL_reconcile_period']
operation_archive = 'docs/archive/PUBLIC_DONCHIAN_2H_EXIT_MONTHS_OPERATION_SOURCE_20261002_V1.py'
assert sha(root / operation_archive) == months['operation_source_sha256']
proofs[operation_archive] = months['operation_source_sha256']
sources = actual['binding']['source_hashes']
for name, digest in sources.items():
    assert sha(root / name) == digest, name
assert sources['src/quant/backtest.py'] == 'ee333d4e5cbadb489e5d467619d0872f78ccb2d86d8b5f46eacc69cb63f9829a'
for item in exit_proof['exact_pure_code_archives']:
    assert sha(item['archive_path']) == item['sha256']
    proofs[str(Path(item['archive_path']).relative_to(root))] = item['sha256']
tasks = []
for item in exit_proof['tasks'].values():
    path = Path(item['path'])
    value = json.loads(path.read_text())
    assert sha(path) == item['sha256'] and value['status'] == 'completed' and value['exit_code'] == 0
    tasks.append(dict(path=str(path), sha256=sha(path), id=value['id'], exit_code=0))
reuse = actual['reused_reference_binding']
assert reuse['reused_accounts'] == 12 and reuse['new_accounts'] == 3
assert not reuse['existing_reference_accounts_replayed'] and reuse['same_common_config_and_period']
assert reuse['minute_input_sha256'] == actual['minute_source']['sha256'] == reference['minute_source']['sha256']
assert actual['registration_start']['hyperparameters'] == reference['registration_start']['hyperparameters']
assert actual['registration_start']['cost_assumptions'] == reference['registration_start']['cost_assumptions']
assert actual['registration_start']['all_folds'] == reference['registration_start']['all_folds']
assert actual['market_models_fit'] == actual['orders_sent'] == 0 and not actual['locked_consumed']
assert not actual['resources']['gpu_used'] and actual['resources']['swap_bytes'] == 0
assert actual['resources']['ram_peak_bytes'] < actual['resources']['ram_limit_bytes'] <= 5_000_000_000
assert actual['disk']['total_bytes'] < 32_000_000_000
assert actual['owned_bytes'] < 512_000_000
receipt = dict(
    status='ROOT_ACCEPTED_FIXED2H122DAY_PROXY_COMPARISON_ONLY', created_utc=datetime.now(UTC).isoformat(),
    git_commit=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=root, text=True).strip(),
    source_hashes=sources, verified_prior_files=proofs, actual_task_bindings=tasks,
    actual_session=96916, actual_exit=0, independent_session=94014, independent_exit=0,
    completed_new_accounts=3, reused_reference_accounts=12, continuous_days=122,
    main_research_strategy='COIN_JESSE_DONCHIAN_2H_SPOT_ADAPTER', economic_qualification='NO_QUALIFIED_CANDIDATE',
    decision='D014: adopt2h research only; gross83% retained/cost57% reduced but MDD higher and Sep/Nov gross negative. Next fixed Dec-Feb90d chronology robustness, prior project seen, no HPO.',
    period_aggregates=actual['aggregate'], reused_reference_binding=reuse,
    source_bytes_unchanged=True, earlier_green_or_old_ledger_reruns=0,
    monthly_continuity_and_PnL_reconciliation=True, unseen=False, long_term_net_APR_proven=False, real_BBO=False,
    locked_consumed=False, models_fit=0, orders_sent=0, GPU_hours=0,
    peak_orchestrator_RSS_bytes=actual['orchestrator_peak_RSS_bytes'], owned_bytes=actual['owned_bytes'],
    latest_actual_disk_scan=actual['disk'], resources=actual['resources'])
out = root / (prefix + 'PUBLIC_DONCHIAN_2H_ROOT_MODULE_ACCEPTANCE_20261002_V1.json')
with out.open('x') as writer:
    json.dump(receipt, writer, indent=2, ensure_ascii=False, allow_nan=False)
    writer.write('\n')
git_sources = dict(sources)
runtime = {'state/dataset_lock.json': git_sources.pop('state/dataset_lock.json')}
binding = dict(status='GIT_SOURCE_BINDING_EXCLUDES_IGNORED_RUNTIME_LOCK', source_hashes=git_sources,
    verified_prior_files={str(out.relative_to(root)): sha(out), **proofs}, verified_runtime_not_for_upload=runtime,
    scope='Root verifies full runtime lock; Git review excludes ignored runtime, no market rerun.')
with (root / 'reports/GITHUB_PUBLIC_DONCHIAN_2H_SOURCE_BINDING_20261002_V1.json').open('x') as writer:
    json.dump(binding, writer, indent=2)
    writer.write('\n')
print(json.dumps(dict(status=receipt['status'], sha256=sha(out))))
