"""Close this finite experiment and later verify its actual normal Git push."""
import argparse,hashlib,json,os,shutil,subprocess
from pathlib import Path
from datetime import UTC,datetime
from quant.paths import ROOT,STATE
from scripts.research_v8.registry import FIELDS,append_event
PARENT='c67a06f49aa7af501ea6676019b658edbc601e16';STEM='DONCHIAN_EXIT10_20261004_V1'
parser=argparse.ArgumentParser();parser.add_argument('action',choices=('close','post'));parser.add_argument('--remote-head');args=parser.parse_args()
assert os.environ['COIN_TASK_ID']
def read(p):return json.loads(Path(p).read_bytes())
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def git(*a):return subprocess.check_output(['git',*a],cwd=ROOT,text=True).strip()
def save(p,v):
    with Path(p).open('x') as f:json.dump(v,f,indent=2,ensure_ascii=False);f.write('\n')
source=ROOT/'reports/GITHUB_DONCHIAN_EXIT10_SOURCE_BINDING_20261004_V1.json'
lock=sha(ROOT/'state/dataset_lock.json');assert lock=='29d930063842e9b1666869b4e5f9e3c8cd629313e57b9dadc328c6131b92f45d'
if args.action=='post':
    s=read(source);head=git('rev-parse','HEAD');assert head==args.remote_head and git('rev-parse','HEAD~1')==PARENT
    assert not git('status','--porcelain=v1','--untracked-files=no')
    assert sorted(git('ls-files','--others','--exclude-standard').splitlines())==sorted(s['prior_WIP_preserved'])
    for n,h in s['source_hashes'].items():assert sha(ROOT/n)==h,n
    gate=ROOT/'reports/GITHUB_DONCHIAN_EXIT10_STAGED_GATE_20261004_V1.json';assert read(gate)['status']=='STAGED_MODULE_CHECKPOINT_PASS'
    tasks=[read(t) for t in (STATE/'task-progress').glob('task-*.json')];roles={}
    for role,title in dict(CLOSE='D067退出机制实际验收与来源保存',GATE='D067提交前源码与敏感信息门槛',COMMIT='D067退出机制完整经济对照正常提交',PUSH='D067已验收退出机制模块推送GitHub',REMOTE='D067精确核对远端main提交').items():
        found=[t for t in tasks if t['title']==title];assert len(found)==1
        t=found[0];assert t['status']=='completed' and t['exit_code']==0 and t['ended_at'];roles[role]=t
    out=ROOT/'reports/GITHUB_DONCHIAN_EXIT10_SYNC_VERIFIED_20261004_V1.json'
    save(out,dict(status='PUSHED_AND_EXACT_REMOTE_MAIN_VERIFIED',parent_commit=PARENT,local_HEAD=head,remote_main=args.remote_head,remote='https://github.com/snowycat1234/coin.git',
        closed_actual_roles=roles,created_utc=datetime.now(UTC).isoformat(),source_binding_sha256=sha(source),staged_gate_sha256=sha(gate),preserved_untracked_paths=s['prior_WIP_preserved'],
        tracked_worktree_clean=True,private_SHA_only=lock,private_body_read=False,force_push=False,orders_sent=0,locked_consumed=False,own_artifact_untracked_until_next_normal_module=True))
    print(json.dumps(dict(path=str(out),sha256=sha(out),local_HEAD=head,remote_main=args.remote_head)));raise SystemExit
assert git('rev-parse','HEAD')==PARENT
prior=ROOT/'reports/GITHUB_PUBLIC_COLLECTOR_RESTORE_SYNC_VERIFIED_20261004_V1.json'
assert sha(prior)=='bc6cbb9d48274da20e148ea30e2cd35617685b4906c945c509ab20e7cabdb9a3'
wip=read(prior)['preserved_untracked_paths'];assert len(wip)==36
p=read(ROOT/'protocols'/(STEM+'.json'));a=read(ROOT/'reports/fast_research'/(STEM+'.json'));f=read(ROOT/'reports/fast_research'/(STEM+'_FINANCIAL.json'))
diagpath=ROOT/'reports/fast_research'/(STEM+'_DIAGNOSTIC.json');d=read(diagpath)
assert a['completed_cases']==a['complete_calendar_cases']==f['financial_case_calls']==4 and len(d['paired_cases'])==4
assert f['status'].startswith('PASS_CONFIGURED_N_') and d['status']=='COMPLETE_EXIT10_SAVED_PAIRED_DIAGNOSTIC_NOT_APR'
for n,h in p['source_hashes'].items():assert sha(ROOT/n)==h,n
for case in a['cases']:
    for item in case['artifacts'].values():assert sha(item['path'])==item['sha256']
review=ROOT/'reports/DONCHIAN_EXIT10_INDEPENDENT_REVIEW_20261004_V1.md';assert review.is_file()
dest=ROOT/'docs/archive/DONCHIAN_EXIT10_TASK_METADATA_20261004_V1';dest.mkdir();roles={}
for path in (STATE/'task-progress').glob('task-*.json'):
    t=read(path)
    if not t['title'].startswith('D067') or t['id']==os.environ['COIN_TASK_ID']:continue
    assert t['ended_at'] and t['exit_code'] in (0,1) and t['status']==('completed' if t['exit_code']==0 else 'failed')
    shutil.copyfile(path,dest/path.name);roles[t['id']]=dict(title=t['title'],status=t['status'],actual_exit_code=t['exit_code'],task_archive=(dest/path.name).relative_to(ROOT).as_posix(),sha256=sha(dest/path.name))
assert roles['9a461323f0534c5796cbe3e36cce9636']['actual_exit_code']==1
event=dict.fromkeys(FIELDS);event.update(event_id='D067-EARLY-CLI-PATH:RESULT',event_type='OPERATIONAL_RESULT',experiment_id='D067-EARLY-CLI-20261004',git_commit=PARENT,
    data_manifest_hash='NONE_SYNTHETIC',protocol_hash=sha(ROOT/'protocols'/(STEM+'_SYNTHETIC.json')),model_family='NONE',fits=0,all_folds='TEST_NOT_STARTED',success_failure='FAILED_RELATIVE_PATH_BEFORE_TEST_EXIT1',
    artifact_path='reports/DONCHIAN_EXIT10_EARLY_CLI_FAILURE_20261004_V1.md',artifact_sha256=sha(ROOT/'reports/DONCHIAN_EXIT10_EARLY_CLI_FAILURE_20261004_V1.md'),
    reason_for_next_experiment='Retain actual failure; correct only invocation absolute paths',result_influenced_later_choice='NO_ECONOMIC_RESULT')
append_event(ROOT/'reports/experiment_registry.jsonl',event)
for folder in STATE.glob('d067-*'):
    if not folder.is_dir():continue
    for name in ('RUN_BINDING.json','ACTUAL_BINDING.json','junit.xml'):
        path=folder/name
        if path.is_file():shutil.copyfile(path,dest/(folder.name+'-'+name))
selected={'scripts/investment/donchian_daily_pool_target.py','scripts/investment/multi_asset_portfolio.py','scripts/investment/multi_asset_financial_audit.py','tests/test_donchian_exit_period.py',
    'README.md','AGENTS.md','docs/RESEARCH_STATUS.md','docs/RESEARCH_DECISION_LOG.md','docs/GOALS.md','docs/PROGRESS.md','docs/FAST_RESEARCH_TASK_CHECKLIST.md','docs/MULTI_ASSET_PORTFOLIO_20261004.md','docs/OPEN_SOURCE_REGISTRY.md','reports/experiment_registry.jsonl',prior.relative_to(ROOT).as_posix()}
for folder in ('docs','docs/archive','reports','reports/fast_research','protocols'):
    selected.update(path.relative_to(ROOT).as_posix() for path in (ROOT/folder).glob('DONCHIAN_EXIT10_*') if path.is_file())
selected.update(path.relative_to(ROOT).as_posix() for path in dest.iterdir())
assert not set(wip).intersection(selected)
owned=sum(path.stat().st_size for run in STATE.glob('d067-*') if run.is_dir() for path in run.rglob('*') if path.is_file());assert owned<800000000
save(source,dict(status='D067_FINITE_EXIT_PERIOD_CHANGE_FULL_ECONOMIC_ACCEPTANCE_NOT_APR',task_id=os.environ['COIN_TASK_ID'],parent_commit=PARENT,created_utc=datetime.now(UTC).isoformat(),
    source_hashes={n:sha(ROOT/n) for n in sorted(selected)},selected_module_paths=sorted(selected),prior_WIP_preserved=wip,closed_actual_roles=roles,private_SHA_only=lock,private_body_read=False,
    owned_d067_STATE_bytes=owned,new_market_accounts=4,saved_control_accounts=4,financial_calls=4,paired_cases=4,HPO=0,models_fit=0,new_QA=0,new_downloads=0,
    diagnostic_sha256=sha(diagpath),independent_review_sha256=sha(review),investment='CASH',candidate='NONE',long_term_APR='NOT_EVALUABLE',orders_sent=0))
print(json.dumps(dict(output=str(source),sha256=sha(source),selected_paths=len(selected),owned_STATE_bytes=owned)))
