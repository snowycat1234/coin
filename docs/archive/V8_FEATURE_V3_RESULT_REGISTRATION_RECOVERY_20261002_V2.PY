import hashlib,json,sys
from datetime import UTC,datetime
from pathlib import Path
root=Path('/mnt/d/codex/coin');sys.path.insert(0,str(root))
from scripts.research_v8.registry import append_event
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
failed=root/'.cache/v8_feature_v3_result_20261002_v1.py'
archive=root/'docs/archive/V8_FIXED_FEATURE_RESULT_FAILED_SOURCE_20261002_V1.py'
with archive.open('xb') as f:f.write(failed.read_bytes())
failure=dict(status='RECEIPT_WRITTEN_REGISTRY_APPEND_NOT_REACHED',created_utc=datetime.now(UTC).isoformat(),
 actual_exit_code=1,source_path=str(archive.relative_to(root)),source_sha256=sha(archive),
 exact_command='bash scripts/bounded.sh /home/xflops/coin-state/v8-clean-env-20261002-v2/bin/python .cache/v8_feature_v3_result_20261002_v1.py',
 exception="KeyError: 'task_id'",reason='Actual task schema key is id; valid test receipt remains unchanged.',
 market_models_fit=0,locked_consumed=False)
failurepath=root/'reports/fast_research/V8_FIXED_FEATURE_RESULT_REGISTRATION_FAILURE_20261002_V1.json'
with failurepath.open('x') as f:json.dump(failure,f,indent=2);f.write('\n')
start=json.loads((root/'reports/fast_research/V8_FIXED_FEATURE_START_20261002_V3.json').read_text())
out='reports/fast_research/V8_FIXED_FEATURE_CHECK_RECEIPT_20261002_V3.json'
result=json.loads((root/out).read_text())
assert result['actual_task']['status']=='completed' and result['actual_task']['exit_code']==0
assert result['junit_counts']==dict(tests=21,errors=0,failures=0,skipped=0)
for p,h in start['source_hashes'].items():assert sha(root/p)==h
event={k:v for k,v in start.items() if k not in ('created_utc','previous_record_sha256','record_sha256')}
event.update(event_id=start['experiment_id']+':RESULT',event_type='OPERATIONAL_RESULT',success_failure=result['status'],
 artifact_path=out,artifact_sha256=sha(root/out),actual_exit_code=0,actual_task_id=result['actual_task']['id'],
 junit_counts=result['junit_counts'],registration_failure_receipt_sha256=sha(failurepath))
record=append_event(root/'reports/experiment_registry.jsonl',event)
print(json.dumps({'registered':record['event_id'],'result_sha256':sha(root/out)}))
