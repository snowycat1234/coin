"""Close finite D071 evidence and verify ordinary Git delivery, without replay."""
import argparse,hashlib,json,os,shutil,subprocess
from datetime import UTC,datetime
from pathlib import Path
from quant.paths import ROOT,STATE
from scripts.research_v8.registry import FIELDS,append_event
PARENT='d82ac37415d099cd8d408424a81505bc85c0ca66'
STEM='HOLD_RISK8_20261005_V1'
parser=argparse.ArgumentParser();parser.add_argument('action',choices=('close','post'));parser.add_argument('--remote-head');args=parser.parse_args()
assert os.environ['COIN_TASK_ID']
def read(p):return json.loads(Path(p).read_bytes())
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def git(*a):return subprocess.check_output(['git',*a],cwd=ROOT,text=True).strip()
def save(p,v):
    with Path(p).open('x') as f:json.dump(v,f,indent=2,ensure_ascii=False);f.write('\n')
proof=ROOT/'reports/GITHUB_HOLD_RISK8_SOURCE_BINDING_20261005_V1.json'
assert sha(ROOT/'state/dataset_lock.json')=='29d930063842e9b1666869b4e5f9e3c8cd629313e57b9dadc328c6131b92f45d'
if args.action=='post':
    binding=read(proof)
    assert git('rev-parse','HEAD')==args.remote_head and git('rev-parse','HEAD~1')==PARENT
    assert not git('status','--porcelain=v1','--untracked-files=no')
    assert sorted(git('ls-files','--others','--exclude-standard').splitlines())==sorted(binding['prior_WIP_preserved'])
    for n,h in binding['source_hashes'].items():assert sha(ROOT/n)==h,n
    gate=ROOT/'reports/GITHUB_HOLD_RISK8_STAGED_GATE_20261005_V1.json'
    assert read(gate)['status']=='STAGED_MODULE_CHECKPOINT_PASS'
    save(ROOT/'reports/GITHUB_HOLD_RISK8_SYNC_VERIFIED_20261005_V1.json',dict(status='GITHUB_MAIN_EXACT_REMOTE_VERIFIED',
        git_commit=args.remote_head,remote_commit=args.remote_head,parent_commit=PARENT,created_utc=datetime.now(UTC).isoformat(),
        task_id=os.environ['COIN_TASK_ID'],source_binding_sha256=sha(proof),gate_sha256=sha(gate),worktree_tracked_clean=True,prior_WIP_preserved=binding['prior_WIP_preserved']))
    print(json.dumps(dict(status='GITHUB_MAIN_EXACT_REMOTE_VERIFIED',head=args.remote_head)));raise SystemExit
assert git('rev-parse','HEAD')==PARENT
prior=ROOT/'reports/GITHUB_DONCHIAN_REENTRY10_SYNC_VERIFIED_20261005_V2.json'
wip=read(prior)['preserved_untracked_paths']
for name in ('','_FINANCIAL','_DIAGNOSTIC','_SYNTHETIC'):
    value=read(ROOT/'reports/fast_research'/(STEM+name+'.json'))
    ident=value.get('binding',{}).get('task_id') or value['task_id']
    task=read(STATE/'task-progress'/('task-'+ident+'.json'))
    assert task['status']=='completed' and task['exit_code']==0 and task['ended_at']
diag=ROOT/'reports/fast_research'/(STEM+'_DIAGNOSTIC.json');d=read(diag)
assert len(d['paired_cases'])==4 and len(d['rows'])==8
assert all(r['terminal_cash_realized'] for r in d['rows'])
review=ROOT/'reports/HOLD_RISK8_INDEPENDENT_REVIEW_20261005_V1.md';assert review.is_file()
dest=ROOT/'docs/archive/HOLD_RISK8_TASK_METADATA_20261005_V1';dest.mkdir()
roles={}
for path in (STATE/'task-progress').glob('task-*.json'):
    t=read(path)
    if not t['title'].startswith('D071') or t['id']==os.environ['COIN_TASK_ID']:continue
    assert t['status']=='completed' and t['exit_code']==0 and t['ended_at']
    shutil.copyfile(path,dest/path.name);roles[t['id']]=dict(title=t['title'],status=t['status'],actual_exit_code=t['exit_code'],sha256=sha(dest/path.name))
for folder in STATE.glob('d071-*'):
    if not folder.is_dir():continue
    for name in ('RUN_BINDING.json','ACTUAL_BINDING.json','junit.xml','result.json','RESULT.json','independent_review.py'):
        path=folder/name
        if path.is_file() and path.stat().st_size<200000:shutil.copyfile(path,dest/(folder.name+'-'+name))
helper=ROOT/'.cache/d071_independent_review.py'
shutil.copyfile(helper,dest/'independent_review.py')
independent=read(STATE/'d071-independent-review-20261005-v1/RESULT.json')
assert independent['status']=='PASS_INDEPENDENT_DECIMAL_JSON_BRIDGES_NOT_MARKET_REPLAY'
assert independent['helper_sha256']==sha(helper)
event=dict.fromkeys(FIELDS)
event.update(event_id='D071-HOLD8:ACCEPTED_DECISION',event_type='OPERATIONAL_RESEARCH_RESULT',experiment_id='D071-HOLD8-TWO-SEPJUN303-20261005',
    git_commit=PARENT,data_manifest_hash=read(ROOT/'protocols'/(STEM+'.json'))['data_manifest']['sha256'],
    protocol_hash=sha(ROOT/'protocols'/(STEM+'.json')),model_family='NONE',fits=0,all_folds='SEEN_DEVELOPMENT_CONTINUOUS303',
    success_failure='RETAIN_HOLD8_RISK_REFERENCE_NOT_INVESTMENT_OR_APR',artifact_path=diag.relative_to(ROOT).as_posix(),artifact_sha256=sha(diag),
    reason_for_next_experiment='Same two-asset EXIT10 contrast to separate pool from timing value; not yet started',
    result_influenced_later_choice=True,independent_task_id=independent['task_id'],closed_actual_roles=roles)
append_event(ROOT/'reports/experiment_registry.jsonl',event)
selected={'scripts/investment/public_sma_perpetual.py','scripts/investment/vol_managed_perpetual_target.py',
    'scripts/investment/multi_asset_portfolio.py','scripts/investment/multi_asset_financial_audit.py','tests/test_hold_risk_budget.py',
    'README.md','AGENTS.md','docs/RESEARCH_STATUS.md','docs/RESEARCH_DECISION_LOG.md','docs/GOALS.md','docs/PROGRESS.md',
    'docs/FAST_RESEARCH_TASK_CHECKLIST.md','docs/MULTI_ASSET_PORTFOLIO_20261004.md','docs/OPEN_SOURCE_REGISTRY.md',
    'reports/experiment_registry.jsonl',prior.relative_to(ROOT).as_posix()}
for folder in ('docs','docs/archive','reports','reports/fast_research','protocols'):
    selected.update(p.relative_to(ROOT).as_posix() for p in (ROOT/folder).glob('HOLD_RISK8_*') if p.is_file())
selected.update(p.relative_to(ROOT).as_posix() for p in dest.iterdir())
assert not set(wip).intersection(selected)
owned=sum(p.stat().st_size for run in STATE.glob('d071-*') if run.is_dir() for p in run.rglob('*') if p.is_file())
assert owned<400000000
save(proof,dict(status='D071_FULL_RISK_BUDGET_PAIRED_ECONOMIC_ACCEPTANCE_NOT_APR',parent_commit=PARENT,task_id=os.environ['COIN_TASK_ID'],
    created_utc=datetime.now(UTC).isoformat(),source_hashes={n:sha(ROOT/n) for n in sorted(selected)},selected_module_paths=sorted(selected),
    prior_WIP_preserved=wip,closed_actual_roles=roles,owned_D071_STATE_bytes=owned,new_market_accounts=4,financial_calls=4,
    saved_control_accounts=4,new_recipes=1,HPO=0,models_fit=0,new_QA=0,new_downloads=0,orders_sent=0,
    private_SHA_only=sha(ROOT/'state/dataset_lock.json'),private_body_read=False,investment='CASH',candidate='NONE',long_term_APR='NOT_EVALUABLE',
    diagnostic_sha256=sha(diag),independent_review_sha256=sha(review)))
print(json.dumps(dict(path=str(proof),selected_paths=len(selected),owned_STATE_bytes=owned)))
