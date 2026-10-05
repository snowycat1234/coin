"""Thin existing-evidence checkpoint; no accounting, model or strategy engine."""
import argparse,json,hashlib,os,subprocess
from pathlib import Path
from datetime import UTC,datetime
from quant.paths import ROOT,STATE
from quant import disk,resources
from scripts.research_v8.registry import append_event,FIELDS

def sha(p):
 with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def save(p,v):
 with (ROOT/p).open('x') as f:json.dump(v,f,indent=2,ensure_ascii=False,allow_nan=False);f.write('\n')
ap=argparse.ArgumentParser();ap.add_argument('--config',required=True);a=ap.parse_args();c=json.loads((ROOT/a.config).read_bytes());head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip();assert head==c['parent_commit']
refs={};tasks=[]
for p,status in c['references'].items():
 r=json.loads((ROOT/p).read_bytes());assert r['status']==status;tid=r['task_id'];t=json.loads((STATE/'task-progress'/('task-'+tid+'.json')).read_bytes());assert t['status']=='completed' and t['exit_code']==0
 refs[p]=dict(sha256=sha(ROOT/p),task_id=tid,source_sha256=r['source_sha256']);tasks.append(t)
for item in c['additional_tasks']:
 t=json.loads((STATE/'task-progress'/('task-'+item['id']+'.json')).read_bytes());assert t['exit_code']==item['expected_exit_code'] and t['status']==('completed' if item['expected_exit_code']==0 else 'failed');tasks.append(t)
for p in c['source_paths']:assert (ROOT/p).is_file()
intervals=[]
for t in sorted(tasks,key=lambda t:t['started_at']):
 b,e=t['started_at'],t['ended_at']
 if intervals and b<=intervals[-1][1]:intervals[-1][1]=max(e,intervals[-1][1])
 else:intervals.append([b,e])
event=dict.fromkeys(FIELDS);event.update(experiment_id=c['module'],event_id=c['module']+':DIAGNOSTIC_DECISION',event_type='OPERATIONAL_RESEARCH_DECISION',git_commit=head,model_family=c['family'],hyperparameters=c['recipe'],models_fit=0,all_folds='SEEN_DEVELOPMENT_POST_RESULT_DIAGNOSTIC',success_failure=c['decision'],reason_for_next_experiment=c['next_action'],result_influenced_later_choice=True,artifact_path=c['primary_reference'],artifact_sha256=sha(ROOT/c['primary_reference']));append_event(ROOT/'reports/experiment_registry.jsonl',event)
print('诊断收尾磁盘实扫；总量未知',flush=True);scan=dict(disk.check(),measured_utc=datetime.now(UTC).isoformat())
report=dict(status='COMPLETE_SAVED_EVIDENCE_DIAGNOSTIC_NOT_NEW_ECONOMIC_REPLAY',parent_commit=head,references=refs,decision=c['decision'],next_action=c['next_action'],models_fit=0,new_accounts=0,new_strategy_net_return='NOT_RUN',locked_body_read=False,source_hashes={p:sha(ROOT/p) for p in c['source_paths']},task_intervals_union_seconds=sum(e-b for b,e in intervals),tasks=[{k:t.get(k) for k in ('id','title','started_at','ended_at','exit_code')} for t in tasks],unattributed_intervals='UNKNOWN_NOT_CALLED_MODEL_THINKING_OR_IDLE',disk_scan=scan,resources=resources.status(),runtime_directory_bytes=sum(p.stat().st_size for p in Path(c['runtime_directory']).rglob('*') if p.is_file()))
save(c['closed'],report);p=STATE/'task-progress/last-disk.json';tmp=p.with_suffix('.diagnostic.tmp');tmp.write_text(json.dumps(dict(ledger=scan,measured_at=datetime.fromisoformat(scan['measured_utc']).timestamp(),source=c['closed'])));tmp.replace(p)
paths=c['selected_paths']+[c['closed'],c['binding'],a.config];prior=json.loads((ROOT/c['prior_binding']).read_bytes())['prior_WIP_preserved'];save(c['binding'],dict(status='ACCEPTED_MODULE_SOURCE_BINDING',parent_commit=head,selected_module_paths=paths,source_hashes={p:sha(ROOT/p) for p in set(paths)-{c['binding']}},prior_WIP_preserved=prior,locked_body_read=False))
(ROOT/c['stage_script']).write_text("$ErrorActionPreference = 'Stop'\n$paths = @(\n"+',\n'.join("'"+p+"'" for p in paths)+"\n)\n& git.exe -C 'D:/codex/coin' add -- $paths\nif ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }\n")
print(json.dumps(dict(status=report['status'],actual_task_seconds=report['task_intervals_union_seconds'],disk_bytes=scan['total_bytes'])))