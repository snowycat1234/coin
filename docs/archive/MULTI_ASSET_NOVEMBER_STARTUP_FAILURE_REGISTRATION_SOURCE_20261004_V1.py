"""Record the actual pre-registry startup failure as a later result, never a START."""
import hashlib, json, os, sys
from pathlib import Path
from scripts.research_v8.registry import FIELDS, append_event
ROOT = Path('/mnt/d/codex/coin')
assert os.environ.get('COIN_TASK_ID') and sys.prefix == '/home/xflops/coin-state/v8-clean-env-20261002-v2'
path = ROOT/'reports/fast_research/MULTI_ASSET_NOVEMBER_SOURCE_ACCEPTANCE_STARTUP_FAILURE_20261004_V1.json'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(path) == 'e7054e446b37ee4ca367b72c85d2e46604c03c15044e8cfe70cfef85a9c24036'
failure = json.loads(path.read_bytes())
task = json.loads((ROOT/failure['failed_task']['path']).read_bytes())
assert task['status'] == 'failed' and task['exit_code'] == failure['actual_exit_code'] == 1
assert sha(ROOT/failure['failed_task']['path']) == failure['failed_task']['sha256']
assert sha(ROOT/failure['source_archive']['path']) == failure['source_archive']['sha256']
event = dict.fromkeys(FIELDS)
event.update(event_id='d054-source-QA-98e4-startup-failure:POST_RESULT',
    event_type='OPERATIONAL_STARTUP_FAILURE_RESULT_AFTER_ACTUAL_EXIT',
    experiment_id='d054-november-source-independent-20261004-v1',
    git_commit='354967542958004c59a7f8e4b3d2fececf036b63',
    protocol_hash=failure['binding']['protocol_sha256'],
    feature_set='NO_SOURCE_ARRAYS_READ', labels='NONE', model_family='NONE',
    hyperparameters={'post_result_only': True, 'original_no_registry_START': True},
    thresholds='FROZEN_PROJECT_PATH_CHECK', cost_assumptions='NOT_EVALUATED',
    all_folds='NO_ARRAYS_OR_FINANCIAL_CALLS', success_failure=failure['status'],
    reason_for_next_experiment='Only pinned public sampler path compatibility; original financial/CSV rules unchanged',
    result_influenced_later_choice=True, actual_failed_task_id=task['id'], actual_failed_exit_code=1,
    registration_task_id=os.environ['COIN_TASK_ID'],
    artifact_path=path.relative_to(ROOT).as_posix(), artifact_sha256=sha(path))
record = append_event(ROOT/'reports/experiment_registry.jsonl', event)
out = ROOT/'reports/fast_research/MULTI_ASSET_NOVEMBER_STARTUP_FAILURE_REGISTRATION_20261004_V1.json'
with out.open('x', encoding='utf-8') as f:
    json.dump({'status':'RECORDED_ACTUAL_STARTUP_FAILURE_POST_RESULT_ONLY',
        'task_id':os.environ['COIN_TASK_ID'], 'registry_record_sha256':record['record_sha256'],
        'failed_task_id':task['id'], 'old_no_START_preserved':True,
        'source_arrays_read':False, 'financial_calls':0, 'source_sha256':sha(Path(__file__))}, f, indent=2)
    f.write('\n')
print(json.dumps({'status':'RECORDED_ACTUAL_FAILURE_POST_RESULT_ONLY', 'record_sha256':record['record_sha256']}))
