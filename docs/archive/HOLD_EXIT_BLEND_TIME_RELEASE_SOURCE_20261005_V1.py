"""Accept completed D074 evidence and verify ordinary Git delivery."""
import argparse,hashlib,json,os,shutil,subprocess
from datetime import UTC,datetime
from pathlib import Path
from quant.paths import ROOT,STATE
from scripts.research_v8.registry import FIELDS,append_event
PARENT='748b4bc1d80fdba5c2f9b794b91f1ada9ed82810'
STEM='HOLD_EXIT_BLEND_TIME_20261005_V1'
parser=argparse.ArgumentParser();parser.add_argument('action',choices=('close','post'));parser.add_argument('--remote-head');args=parser.parse_args()
assert os.environ['COIN_TASK_ID']
def read(p):return json.loads(Path(p).read_bytes())
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def git(*a):return subprocess.check_output(['git',*a],cwd=ROOT,text=True).strip()
def save(p,v):
 with Path(p).open('x') as f:json.dump(v,f,indent=2,ensure_ascii=False);f.write('\n')
proof=ROOT/'reports/GITHUB_HOLD_EXIT_BLEND_TIME_SOURCE_BINDING_20261005_V1.json'
private=sha(ROOT/'state/dataset_lock.json')
assert private=='29d930063842e9b1666869b4e5f9e3c8cd629313e57b9dadc328c6131b92f45d'
if args.action=='post':
 binding=read(proof)
 assert git('rev-parse','HEAD')==args.remote_head and git('rev-parse','HEAD~1')==PARENT
 assert not git('status','--porcelain=v1','--untracked-files=no')
 assert sorted(git('ls-files','--others','--exclude-standard').splitlines())==sorted(binding['prior_WIP_preserved'])
 for n,h in binding['source_hashes'].items():assert sha(ROOT/n)==h,n
 gate=ROOT/'reports/GITHUB_HOLD_EXIT_BLEND_TIME_STAGED_GATE_20261005_V1.json'
 assert read(gate)['status']=='STAGED_MODULE_CHECKPOINT_PASS'
 save(ROOT/'reports/GITHUB_HOLD_EXIT_BLEND_TIME_SYNC_VERIFIED_20261005_V1.json',dict(status='GITHUB_MAIN_EXACT_REMOTE_VERIFIED',
  git_commit=args.remote_head,remote_commit=args.remote_head,parent_commit=PARENT,created_utc=datetime.now(UTC).isoformat(),
  task_id=os.environ['COIN_TASK_ID'],source_binding_sha256=sha(proof),gate_sha256=sha(gate),worktree_tracked_clean=True,
  prior_WIP_preserved=binding['prior_WIP_preserved'],private_SHA_only=private,private_body_read=False,force_push=False))
 print(json.dumps(dict(status='GITHUB_MAIN_EXACT_REMOTE_VERIFIED',head=args.remote_head)));raise SystemExit
assert git('rev-parse','HEAD')==PARENT
prior=ROOT/'reports/GITHUB_HOLD_EXIT_BLEND_SYNC_VERIFIED_20261005_V1.json'
wip=read(prior)['prior_WIP_preserved'];assert len(wip)==36
protocol=read(ROOT/'protocols'/(STEM+'.json'))
for n,h in protocol['source_hashes'].items():assert sha(ROOT/n)==h,n
main=read(ROOT/'reports/fast_research'/(STEM+'.json'))
independent=read(STATE/'d074-time-independent-20261005-v1/RESULT.json')
assert main['status']=='COMPLETE_SAVED_PAIR_TIME_DIAGNOSTIC_POST_SELECTION_NOT_APR' and len(main['pairs'])==4
assert independent['status']=='PASS_INDEPENDENT_SAVED_DAILY_DECIMAL_TIME_AND_EPISODE_ARITHMETIC_NOT_ALPHA'
assert independent['helper_sha256']==sha(ROOT/'.cache/d074_independent_review.py')
assert independent['main_result_sha256']==sha(ROOT/'reports/fast_research'/(STEM+'.json'))
assert all(i['includes_zero'] for p in main['pairs'] for i in p['block_intervals'])
dest=ROOT/'docs/archive/HOLD_EXIT_BLEND_TIME_USED_METADATA_20261005_V1';dest.mkdir(exist_ok=True)
roles={};failed={}
for path in (STATE/'task-progress').glob('task-*.json'):
 t=read(path)
 if not t['title'].startswith('D074') or t['id']==os.environ['COIN_TASK_ID']:continue
 assert t['ended_at'] and t['status'] in ('completed','failed')
 if t['status']=='completed':assert t['exit_code']==0
 shutil.copyfile(path,dest/path.name)
 (roles if t['exit_code']==0 else failed)[t['id']]=dict(title=t['title'],actual_exit_code=t['exit_code'],sha256=sha(dest/path.name))
assert main['task_id'] in roles and independent['task_id'] in roles and len(failed)==3
for name,path in {'independent_review.py':ROOT/'.cache/d074_independent_review.py',
 'RESULT.json':STATE/'d074-time-independent-20261005-v1/RESULT.json',
 'freeze.ps1':ROOT/'.cache/d074_freeze.ps1','finish.py':ROOT/'.cache/d074_finish.py'}.items():shutil.copyfile(path,dest/name)
owned=sum(p.stat().st_size for run in STATE.glob('d074-*') if run.is_dir() for p in run.rglob('*') if p.is_file());assert owned<2000000
observed=subprocess.run(['ps','-p','890567,890568','-o','pid,stat,etime,args'],text=True,capture_output=True)
ps=observed.stdout
assert observed.returncode in (0,1)
save(dest/'collectors_readonly_presence.json',dict(observed_utc=datetime.now(UTC).isoformat(),ps=ps,
 actual_exit_code=observed.returncode,scope='PROCESS_PRESENCE_ONLY_NOT_HEALTH_DAYS',task_id=os.environ['COIN_TASK_ID'],
 live_original_collectors='quant.microstructure --run' in ps and 'quant.collector_public_v3 --run' in ps,
 original_exit_reason='UNKNOWN',next='PRESERVE_LOG_CHECKPOINT_DB_THEN_FINITE_RESTORE'))
event=dict.fromkeys(FIELDS);event.update(event_id='D074-TIME:ACCEPTED_DECISION',event_type='OPERATIONAL_RESEARCH_RESULT',
 experiment_id=protocol['experiment_id'],git_commit=PARENT,data_manifest_hash='SAVED_ACCEPTED_DAILY_NAV_ONLY',
 protocol_hash=sha(ROOT/'protocols'/(STEM+'.json')),model_family='NONE',fits=0,all_folds='SEEN_POST_SELECTION_303D_NOT_OOS',
 success_failure='DAILY_DRAWDOWN_AND_TIME_REVERSAL_NOT_STABLE_ALPHA',artifact_path='reports/fast_research/'+STEM+'.json',
 artifact_sha256=sha(ROOT/'reports/fast_research'/(STEM+'.json')),independent_task_id=independent['task_id'],
 reason_for_next_experiment='Preserve and restore absent original public collectors, then finite funding unit audit; no restriction retries',result_influenced_later_choice=True)
append_event(ROOT/'reports/experiment_registry.jsonl',event)
selected={'scripts/investment/donchian_time_stability.py','README.md','AGENTS.md','docs/RESEARCH_STATUS.md','docs/RESEARCH_DECISION_LOG.md',
 'docs/GOALS.md','docs/PROGRESS.md','docs/FAST_RESEARCH_TASK_CHECKLIST.md','docs/MULTI_ASSET_PORTFOLIO_20261004.md',
 'reports/experiment_registry.jsonl',prior.relative_to(ROOT).as_posix()}
for folder in ('docs','docs/archive','reports','reports/fast_research','protocols'):
 selected.update(p.relative_to(ROOT).as_posix() for p in (ROOT/folder).glob('HOLD_EXIT_BLEND_TIME_*') if p.is_file())
selected.update(p.relative_to(ROOT).as_posix() for p in dest.iterdir())
assert not set(wip).intersection(selected)
save(proof,dict(status='D074_ACTUAL_SAVED_PAIR_DRAWDOWN_TIME_DIAGNOSTIC_ACCEPTED_NOT_ALPHA',parent_commit=PARENT,
 task_id=os.environ['COIN_TASK_ID'],created_utc=datetime.now(UTC).isoformat(),selected_module_paths=sorted(selected),
 source_hashes={n:sha(ROOT/n) for n in sorted(selected)},prior_WIP_preserved=wip,closed_actual_roles=roles,
 preserved_failed_preparation_tasks=failed,owned_D074_STATE_bytes=owned,actual_pairs=4,actual_days=303,
 actual_empirical_descriptive_draws=24000,independent_toy_draws=111,independent_empirical_endpoints_reestimated=False,
 market_replays=0,models_fit=0,HPO=0,new_downloads=0,new_QA=0,orders_sent=0,
 private_SHA_only=private,private_body_read=False,candidate='NONE',investment='CASH',long_term_APR='NOT_EVALUABLE'))
print(json.dumps(dict(path=str(proof),selected_paths=len(selected),owned_STATE_bytes=owned,failed_preparation_tasks=len(failed))))
