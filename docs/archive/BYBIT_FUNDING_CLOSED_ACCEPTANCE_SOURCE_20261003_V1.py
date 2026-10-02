"""Seal closed root acceptance metadata; no QA, statistics or test replay."""
from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path
from scripts.research_v8.registry import FIELDS, append_event
root=Path('/mnt/d/codex/coin');sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
archive='docs/archive/BYBIT_FUNDING_CLOSED_ACCEPTANCE_SOURCE_20261003_V1.py'
assert Path(__file__).read_bytes()==(root/archive).read_bytes()
name='reports/fast_research/BYBIT_FUNDING_PILOT_ROOT_ACCEPTANCE_20261003_V1.json'
assert sha(root/name)=='b93884989856ae294cc63b4dc30eb8c5561d93c53f5e1104412949a6cb111202'
v=json.loads((root/name).read_bytes());identity=v['root_task_id']
path=Path('/home/xflops/coin-state/task-progress')/('task-'+identity+'.json');task=json.loads(path.read_bytes())
assert identity=='9994290a86b347d7a30f47260058ef9f' and task['status']=='completed' and task['exit_code']==0
hashes={**v['source_hashes'],name:sha(root/name),archive:sha(root/archive)}
for relative,digest in hashes.items():assert sha(root/relative)==digest
actual=dict(path=str(path),sha256=sha(path),task=task,host_result='chunk:e0c282',actual_exit=0)
event=dict.fromkeys(FIELDS)
event.update(experiment_id='BYBIT-PILOT-ROOT-ACCEPTANCE-20261003-V1',event_id='BYBIT-PILOT-ROOT-ACCEPTANCE-20261003-V1:RESULT',
    event_type='IMPORTED_OPERATIONAL_RESULT',git_commit=v['original_receipts'][0]['task'].get('git_commit','UNKNOWN_IN_TASK_USE_PILOT_BINDING'),
    data_manifest_hash=None,protocol_hash=hashes['protocols/BYBIT_FUNDING_HISTORY_PILOT_20261003_V1.json'],
    feature_set='NONE_FAILURE_METADATA_ONLY',labels='NONE',model_family='NONE',hyperparameters='NO_MODEL_OR_MARKET_REPLAY',
    seed='NOT_APPLICABLE',thresholds='FROZEN_SOURCE_AND_TRUE_EXIT_ONLY',cost_assumptions='NOT_EVALUATED',
    all_folds='BTC_ETH_FIXED_2025_08_01_ONLY',success_failure=v['status'],reason_for_next_experiment='D027_EXISTING_BASIS_RISK_SCALE',
    result_influenced_later_choice=True,post_completion_registration=True,preregistered_start_record_created=False,
    artifact_path=name,artifact_sha256=sha(root/name),actual_root_task=actual,actual_exit=0,source_hashes={archive:sha(root/archive)})
event['git_commit']=json.loads((root/'reports/fast_research/BYBIT_FUNDING_HISTORY_PILOT_ACTUAL_20261003_V1.json').read_bytes())['binding']['git_commit']
append_event(root/'reports/experiment_registry.jsonl',event)
out=root/'reports/GITHUB_BYBIT_FUNDING_PILOT_SOURCE_BINDING_20261003_V1.json'
value=dict(status='PASS_EXACT_CLOSED_FAILURE_MODULE_METADATA_BINDING_NOT_NATIVE_GATE',created_utc=datetime.now(UTC).isoformat(),
    source_hashes=hashes,actual_root_closure=actual,pilot_actual_exit=1,native_data_or_unit_gate='NOT_PASSED',
    old_QA_green_tests_or_market_statistics_repeated=False,raw_response_not_in_Git=True)
with out.open('x') as w:json.dump(value,w,indent=2,ensure_ascii=False);w.write('\n')
print(json.dumps({'status':value['status'],'sha256':sha(out),'source_files':len(hashes)}))
