import hashlib, json, subprocess
from datetime import UTC, datetime
from pathlib import Path

root = Path('/mnt/d/codex/coin')
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
proofs = {
 'SIMPLE_STRATEGY_COMPARISON_ACTUAL_20261002_V3.json':'b9825db24c880064af68f3e9280f60d6593e3667742cf053fa8b7b2b13a0177d',
 'SIMPLE_STRATEGY_COMPARISON_ACTUAL_EXIT_20261002_V3.json':'6c210ea6d692c94610049c2777915d74022dac46652ba02568e509b3de3c5049',
 'SIMPLE_STRATEGY_COMPARISON_INDEPENDENT_ACTUAL_AUDIT_20261002_V3_R4.json':'c91825ace2b9a2e5d88089aa58da9c55ea3b2a846aa94ba5bb2b5003d1a2bcd0',
 'V8_EXISTING_FROZEN_SPOT_MINUTE_SOURCE_REUSE_20261002_V1.json':'a8b5389eced2ae4d9742d3e212e88562ca7bcc879990f3fa2b9632ebfdf1552e',
 'SIMPLE_STRATEGY_COMPARISON_TINY_20261002_V3.json':'efef749cc95a71d593ac71eda9bbe1548762893a94389546b9f0d19a3c7e7846',
 'SIMPLE_STRATEGY_AUDIT_EXPORT_RECOVERY_EXIT_RECEIPT_20261002_V1.json':'26e92abafb3f57306eb9d2e1140fa8f1b9411a41591bea3cfd6512e66179399c'}
proofs = {'reports/fast_research/'+k:v for k,v in proofs.items()}
for path, expected in proofs.items(): assert sha(root/path) == expected, path
actual = json.loads((root/'reports/fast_research/SIMPLE_STRATEGY_COMPARISON_ACTUAL_20261002_V3.json').read_text())
execution = json.loads((root/'reports/fast_research/SIMPLE_STRATEGY_COMPARISON_ACTUAL_EXIT_20261002_V3.json').read_text())
audit = json.loads((root/'reports/fast_research/SIMPLE_STRATEGY_COMPARISON_INDEPENDENT_ACTUAL_AUDIT_20261002_V3_R4.json').read_text())
assert actual['completed_ledgers'] == 72 and actual['all_planned_ledgers_complete']
assert actual['source_bytes_unchanged'] and not actual['locked_consumed']
assert actual['market_models_fit'] == 0 and actual['orders_sent'] == 0
assert execution['actual_outer_exit'] == 0 and audit['completed_ledgers_verified'] == 72
assert audit['status'] == 'PASS_ACTUAL_PROXY_LEDGER_ACCOUNTING_AND_SCOPE_EXPORT_RECOVERED'
assert audit['export_recovery']['calculation_task_actual_exit_code'] == 1
assert audit['concentration_ratio_max_absolute_difference'] <= audit['concentration_ratio_absolute_tolerance']
sources = execution['source_hashes']
for path, expected in sources.items(): assert sha(root/path) == expected, path
task = Path('/home/xflops/coin-state/task-progress/task-'+execution['task_id']+'.json')
task_value = json.loads(task.read_text())
assert task_value['status'] == 'completed' and task_value['exit_code'] == 0
recovery_path = audit['export_recovery']['recovery_source']
recovery_exit=json.loads((root/'reports/fast_research/SIMPLE_STRATEGY_AUDIT_EXPORT_RECOVERY_EXIT_RECEIPT_20261002_V1.json').read_text())
assert recovery_exit['actual_recovery_execution']['actual_exit_code']==0
assert sha(recovery_path)==audit['export_recovery']['recovery_source_sha256']
assert sha(audit['export_recovery']['original_partial_report_path']) == audit['export_recovery']['original_partial_report_sha256']
receipt = dict(status='ROOT_ACCEPTED_COMMON_PUBLIC_STRATEGY_PROXY_ECONOMIC_COMPARISON_ONLY',
 created_utc=datetime.now(UTC).isoformat(),git_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip(),
 source_hashes=sources,verified_prior_files=proofs,
 actual_task=dict(path=str(task),sha256=sha(task),task=task_value),
 independent_export_recovery_execution_receipt=recovery_exit,
 independent_calculation_exit=1,independent_calculation_complete_ledgers=72,
 independent_failure='Final numpy counter JSON serialization failed only; original truncated report not PASS evidence; new export-only recovery actual exit0. No market rerun.',
 completed_ledgers=72,original_green_checks_rerun=False,original_market_ledger_rerun=False,
 current_phase_primary='VOL_MANAGED_BUY_AND_HOLD',next_phase_main_research='COIN_JESSE_DONCHIAN_1H_SPOT_ADAPTER',
 screening=True,unseen=False,continuous_CAGR=False,candidate_status='NO_QUALIFIED_CANDIDATE',
 candidate_qualification_allowed=False,real_BBO=False,fees_relaxed=False,GPU_hours=0,locked_consumed=False,orders_sent=0,
 net_economic_aggregates=actual['aggregate'],resources=actual['resources'],latest_actual_disk_scan=actual['disk'],
 owned_bytes=actual['owned_bytes'],next_decision='D011: continuous Aug1..<Dec1 122d, same fixed4 low-turnover strategies/costs/risk, no fits; non-unseen screening')
out=root/'reports/fast_research/INVESTMENT_COMPARISON_ROOT_MODULE_ACCEPTANCE_20261002_V1.json'
with out.open('x') as stream: json.dump(receipt,stream,indent=2,ensure_ascii=False,allow_nan=False);stream.write('\n')
print(json.dumps(dict(status=receipt['status'],sha256=sha(out))))
