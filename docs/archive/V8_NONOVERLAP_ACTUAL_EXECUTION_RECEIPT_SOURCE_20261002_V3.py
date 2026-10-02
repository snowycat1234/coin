import hashlib, json, subprocess, sys
from datetime import UTC, datetime
from pathlib import Path
root=Path('/mnt/d/codex/coin');state=Path('/home/xflops/coin-state');sys.path.insert(0,str(root))
from scripts.research_v8.registry import read_verified
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
path=root/'reports/fast_research/V8_NONOVERLAP_MECHANISM_20261002_V3.json';r=json.loads(path.read_text())
assert sha(path)=='21de88b9f88aed95d3ceda8d56d49ead0d72695ec0873cf36192bd7e6188942a'
assert r['status']=='PASS_CALENDAR_COMPLETENESS_SUPPLEMENT_NOT_P1_GATE' and r['P1_gate']=='NOT_READY'
for p,h in r['source_hashes'].items():assert sha(root/p)==h,p
for f in r['folds']:assert sha(Path(f['calendar_path']))==f['calendar_sha256'],f['fold']
history=read_verified((root/'reports/experiment_registry.jsonl').read_bytes())
end=next(e for e in history if e['event_id']=='v8-nonoverlap-calendar-supplement-20261002-v3:RESULT')
assert end['artifact_sha256']==sha(path) and end['success_failure']==r['status']
task_path=state/'task-progress/task-661405bfeea8411aade407d66bc65fe4.json'
task=json.loads(task_path.read_text());assert task['id']=='661405bfeea8411aade407d66bc65fe4' and task['status']=='completed' and task['exit_code']==0
binding=state/'v8-nonoverlap-calendar-supplement-20261002-v3/RUN_BINDING.json'
assert sha(binding)==r['run_binding_sha256']
archive=root/'docs/archive/V8_NONOVERLAP_ACTUAL_EXECUTION_RECEIPT_SOURCE_20261002_V3.py'
with archive.open('xb') as f:f.write(Path(__file__).read_bytes())
receipt=dict(status='ACTUAL_CALENDAR_SUPPLEMENT_EXECUTION_COMPLETED_PENDING_INDEPENDENT_AUDIT',created_utc=datetime.now(UTC).isoformat(),
 git_commit=r['registration_start']['git_commit'],registration_git_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip(),
 data_hash=r['registration_start']['data_manifest_hash'],protocol_hash=r['registration_start']['protocol_hash'],
 environment_hash=r['registration_start']['binding']['environment_lock_sha256'],seed=r['registration_start']['seed'],
 exact_command=r['registration_start']['binding']['exact_command'],required_outer_wrapper=r['registration_start']['binding']['required_outer_wrapper'],
 source_hashes=r['source_hashes']|{str(archive.relative_to(root)):sha(archive)},
 actual_unified_session_id=95905,actual_unified_exit_code=0,actual_task=task,output_path=str(path.relative_to(root)),output_sha256=sha(path),
 run_binding_path=str(binding),run_binding_sha256=sha(binding),result_event_sha256=end['record_sha256'],
 source_shards_read=32,added_rows=240,scored_added_rows=0,full_train_minutes_per_fold_variant=17280,OOS_minutes_per_fold_variant=10080,
 parent_V2_report_path=r['parent_report_path'],parent_V2_report_sha256=r['parent_report_sha256'],
 peak_RSS_bytes=r['peak_RSS_bytes'],elapsed_seconds=r['elapsed_seconds'],resources=r['resources'],
 candidate='NONE',candidate_status='NO_QUALIFIED_CANDIDATE',P1_gate='NOT_READY',market_models_fit=0,locked_consumed=False,orders_sent=0,
 limitations=['Actual completion binding only; calendar/statistical equality is independently audited.',
 'Original V2 scope failure remains preserved; this supplement adds no new alpha hypothesis or economic evidence.'])
out=root/'reports/fast_research/V8_NONOVERLAP_ACTUAL_EXECUTION_RECEIPT_20261002_V3.json'
with out.open('x') as f:json.dump(receipt,f,indent=2);f.write('\n')
print(json.dumps(dict(status=receipt['status'],receipt_sha256=sha(out),task_id=task['id'])))
