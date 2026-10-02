import hashlib,json,subprocess,sys
import xml.etree.ElementTree as ET
from datetime import UTC,datetime
from pathlib import Path
root=Path('/mnt/d/codex/coin');state=Path('/home/xflops/coin-state')
sys.path.insert(0,str(root))
from scripts.research_v8.registry import append_event
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
start_path=root/'reports/fast_research/V8_FIXED_FEATURE_START_20261002_V3.json'
start=json.loads(start_path.read_text())
for p,h in start['source_hashes'].items():assert sha(root/p)==h
xml='reports/fast_research/V8_FIXED_FEATURE_TESTS_20261002_V3.xml'
suites=list(ET.parse(root/xml).iter('testsuite'))
counts={k:sum(int(s.attrib.get(k,0)) for s in suites) for k in ('tests','errors','failures','skipped')}
assert counts==dict(tests=21,errors=0,failures=0,skipped=0)
tasks=[json.loads(p.read_text()) for p in (state/'task-progress').glob('task-*.json')]
tasks=[t for t in tasks if t['title']=='V8 共同特征primitive缺失/单位守卫验收']
assert len(tasks)==1 and tasks[0]['status']=='completed' and tasks[0]['exit_code']==0
head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip()
result=dict(status='PASS_FIXED_FEATURE_SYNTHETIC_CHECKS_PENDING_INDEPENDENT_AUDIT',
 created_utc=datetime.now(UTC).isoformat(),git_commit=start['git_commit'],registration_git_commit=head,
 data_hash=start['data_manifest_hash'],protocol_hash=start['protocol_hash'],environment_hash=start['environment_hash'],
 seed=None,exact_command=start['exact_command'],source_hashes=start['source_hashes'],
 start_receipt_sha256=sha(start_path),junit_path=xml,junit_sha256=sha(root/xml),junit_counts=counts,
 actual_unified_session_id=77221,actual_unified_exit_code=0,actual_task=tasks[0],feature_count=478,
 market_models_fit=0,locked_consumed=False,orders_sent=0,P1_passed=False,
 limitations=['No market input or model fit. All ten model caller routing remains NOT_AUDITED.',
 'Independent V3 audit pending; V1/V2 rejected by the preserved primitive corruption audit.'])
out='reports/fast_research/V8_FIXED_FEATURE_CHECK_RECEIPT_20261002_V3.json'
with (root/out).open('x') as f:json.dump(result,f,indent=2);f.write('\n')
event={k:v for k,v in start.items() if k not in ('created_utc','previous_record_sha256','record_sha256')}
event.update(event_id=start['experiment_id']+':RESULT',event_type='OPERATIONAL_RESULT',
 success_failure=result['status'],artifact_path=out,artifact_sha256=sha(root/out),
 actual_exit_code=0,actual_task_id=tasks[0]['task_id'],junit_counts=counts)
append_event(root/'reports/experiment_registry.jsonl',event)
print(json.dumps(dict(status=result['status'],junit_counts=counts,receipt_sha256=sha(root/out))))
