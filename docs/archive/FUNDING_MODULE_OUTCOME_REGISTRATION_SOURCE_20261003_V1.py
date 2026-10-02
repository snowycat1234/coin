"""Register completed audit/acceptance outcomes honestly after completion."""
import hashlib
import json
from pathlib import Path
from scripts.research_v8.registry import FIELDS, append_event

root = Path('/mnt/d/codex/coin')
state = Path('/home/xflops/coin-state')
archive = 'docs/archive/FUNDING_MODULE_OUTCOME_REGISTRATION_SOURCE_20261003_V1.py'
sha = lambda path: hashlib.sha256(Path(path).read_bytes()).hexdigest()
assert Path(__file__).read_bytes() == (root/archive).read_bytes()
protocol = root/'protocols/FUNDING_INCOME_DIAGNOSTIC_122D_20261003_V1.json'
spec = json.loads(protocol.read_bytes())
for label, name, expected_exit, host in (
    ('AUDIT-V1', 'FUNDING_INCOME_DECIMAL_INDEPENDENT_AUDIT_20261003_V1.json', 1, 'chunk:121be0'),
    ('PREFIX-RECOVERY-V2', 'FUNDING_INCOME_DECIMAL_INDEPENDENT_AUDIT_20261003_V2.json', 0, 'chunk:438966'),
    ('ROOT-ACCEPTANCE', 'FUNDING_INCOME_ROOT_MODULE_ACCEPTANCE_20261003_V1.json', 0, 'chunk:877d0a')):
    path = root/'reports/fast_research'/name
    result = json.loads(path.read_bytes())
    identity = result.get('task_id') or result['binding']['task_id']
    task_path = state/'task-progress'/('task-'+identity+'.json')
    task = json.loads(task_path.read_bytes())
    assert task['id'] == identity and task['exit_code'] == expected_exit
    assert task['status'] == ('failed' if expected_exit else 'completed')
    event = dict.fromkeys(FIELDS)
    event.update(experiment_id='FUNDING-INCOME-'+label+'-20261003', event_id='FUNDING-INCOME-'+label+'-20261003:RESULT',
        event_type='IMPORTED_OPERATIONAL_RESULT', git_commit=spec['git_commit_at_freeze'],
        data_manifest_hash=spec['source_acceptance_sha256'], protocol_hash=sha(protocol),
        feature_set='RAW_FUNDING_COUPON_CONDITIONAL_FRACTION_ONLY', labels='NONE', model_family='NONE',
        hyperparameters='FIXED_732_EVENTS_NO_SEARCH', seed='NONE_DETERMINISTIC', thresholds='31_51_55_63_BP_NOT_INVESTMENT_GATE',
        cost_assumptions=spec['costs'], all_folds='2025-08-01..<2025-12-01_BTC_ETH_SEPARATE',
        success_failure=result['status'], reason_for_next_experiment='D025_NATIVE_BYBIT_FUNDING_INPUT_GAP',
        result_influenced_later_choice=True, artifact_path=str(path.relative_to(root)), artifact_sha256=sha(path),
        actual_task_path=str(task_path), actual_task_sha256=sha(task_path), actual_exit_code=expected_exit,
        actual_host_result=host, post_completion_registration=True, preregistered_start_record_created=False,
        frozen_before_operation_bindings_preserved=True, income_unit_certified=False,
        source_hashes={archive:sha(root/archive), 'scripts/research_v8/registry.py':sha(root/'scripts/research_v8/registry.py')})
    saved = append_event(root/'reports/experiment_registry.jsonl', event)
    print(json.dumps(dict(event_id=saved['event_id'], record_sha256=saved['record_sha256'], actual_exit_code=expected_exit)))
