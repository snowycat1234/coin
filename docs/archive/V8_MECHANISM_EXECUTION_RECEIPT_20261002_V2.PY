import hashlib,json,subprocess,sys
from datetime import UTC,datetime
from pathlib import Path
root=Path('/mnt/d/codex/coin');state=Path('/home/xflops/coin-state');sys.path.insert(0,str(root))
from scripts.research_v8.registry import read_verified
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
path=root/'reports/fast_research/V8_NONOVERLAP_MECHANISM_20261002_V2.json';r=json.loads(path.read_text())
assert sha(path)=='39e8b29e99c6bd28667626fca1a22ad050504e0683be6e9734684fdff859faf5'
assert r['status']=='PASS_DIAGNOSTIC_EXECUTION_NOT_P1_GATE' and r['P1_gate']=='NOT_READY'
for p,h in r['source_hashes'].items():assert sha(root/p)==h
for f in r['folds']:assert sha(Path(f['calendar_path']))==f['calendar_sha256']
history=read_verified((root/'reports/experiment_registry.jsonl').read_bytes())
end=next(e for e in history if e['event_id']=='v8-nonoverlap-mechanism-20261002-v2:RESULT')
assert end['artifact_sha256']==sha(path) and end['success_failure']==r['status']
tasks=[json.loads(p.read_text()) for p in (state/'task-progress').glob('task-*.json')]
tasks=[t for t in tasks if t['title']=='V8 非重叠机制四fold诊断' and t['status']=='completed' and t['exit_code']==0]
assert len(tasks)==1
receipt=dict(status='ACTUAL_DIAGNOSTIC_EXECUTION_COMPLETED_PENDING_CALENDAR_SUPPLEMENT',created_utc=datetime.now(UTC).isoformat(),
 git_commit=r['registration_start']['git_commit'],registration_git_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip(),
 data_hash=r['registration_start']['data_manifest_hash'],protocol_hash=r['registration_start']['protocol_hash'],
 environment_hash=r['registration_start']['environment_hash'],seed=r['registration_start']['seed'],
 exact_command=r['registration_start']['exact_command'],source_hashes=r['source_hashes'],
 actual_unified_session_id=98389,actual_unified_exit_code=0,actual_task=tasks[0],output_path=str(path.relative_to(root)),output_sha256=sha(path),
 result_event_sha256=end['record_sha256'],folds=4,variants=3,descriptive_hypotheses=96,scanned_train_OOS_UTC_days=76,
 peak_RSS_bytes=r['peak_RSS_bytes'],elapsed_seconds=r['elapsed_seconds'],
 train_calendar_minutes_per_fold_variant=17260,full_prevalidation_train_minutes=17280,
 omitted_unfitted_guard_minutes_per_fold_variant=20,OOS_calendar_minutes_per_fold_variant=10080,
 calendar_scope_gap_acknowledged=True,complete_calendar_accepted=False,
 candidate='NONE',candidate_status='NO_QUALIFIED_CANDIDATE',P1_gate='NOT_READY',market_models_fit=0,locked_consumed=False,orders_sent=0)
out=root/'reports/fast_research/V8_NONOVERLAP_ACTUAL_EXECUTION_RECEIPT_20261002_V2.json'
with out.open('x') as f:json.dump(receipt,f,indent=2);f.write('\n')
print(json.dumps(dict(status=receipt['status'],receipt_sha256=sha(out),task_id=tasks[0]['id'])))
