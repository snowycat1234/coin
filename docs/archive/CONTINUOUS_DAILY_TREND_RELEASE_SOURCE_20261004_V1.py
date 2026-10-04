"""Close actual continuous research, keep original budget failure and unrelated WIP."""
import hashlib,json,os,shutil,subprocess
from pathlib import Path
from datetime import UTC,datetime
from quant.paths import ROOT,STATE
PARENT='29393019aed0e1a3b643877eaf97947f38c25b0c'
assert os.environ['COIN_TASK_ID']
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_bytes())
def git(*args):return subprocess.check_output(['git',*args],cwd=ROOT,text=True).strip()
assert git('rev-parse','HEAD')==PARENT
prior=ROOT/'reports/GITHUB_COST_PROVENANCE_SYNC_VERIFIED_20261004_V1.json'
assert sha(prior)=='f056b50e5424d83fdcb6ac610a62a4eebd8090fe61a2694234b95f716e980a3c'
assert read(prior)['local_HEAD']==read(prior)['remote_main']==PARENT
rp=ROOT/'reports/fast_research/CONTINUOUS_DAILY_TREND_DIAGNOSTIC_20261004_V1.json';r=read(rp)
assert r['status']=='COMPLETE_SAVED_CONTINUOUS303_ECONOMIC_AND_OPPORTUNITY_DIAGNOSTIC_NOT_APR'
assert len(r['rows'])==12 and len(r['paired_saved_accounts'])==8
for recipe,proof in r['recipes'].items():
    ap=ROOT/proof['actual_report'];a=read(ap);fp=ROOT/proof['independent_report'];f=read(fp)
    assert sha(ap)==proof['sha256'] and sha(fp)==proof['independent_sha256']
    p=read(ROOT/'protocols'/('CONTINUOUS_DAILY_TREND_'+recipe+'_20261004_V1.json'))
    assert a['binding']['source_hashes']==p['source_hashes'] and a['actual_calendar_days']==303
    for name,digest in p['source_hashes'].items():assert sha(ROOT/name)==digest,name
    assert len(a['cases'])==4 and all(c['summary']['completed_minutes']==c['summary']['required_minutes']==436320 for c in a['cases'])
    assert f['financial_case_calls']==f['completed_cases_verified']==4 and f['status'].startswith('PASS_CONFIGURED_N_')
    failed=recipe=='HOLD_TEN';t=read(STATE/'task-progress'/('task-'+proof['actual_closed_task']+'.json'))
    assert t['status']==('failed' if failed else 'completed') and t['exit_code']==(1 if failed else 0)
    if failed:assert a['status']=='FAILED_MULTI_ASSET_DEVELOPMENT_COMPARISON' and a['owned_bytes']==505969595>p['budget']['owned_bytes'] and f['producer_budget_passed'] is False
    for c in a['cases']:
        for artifact in c['artifacts'].values():assert sha(Path(artifact['path']))==artifact['sha256']
assert sha(ROOT/'state/dataset_lock.json')=='29d930063842e9b1666869b4e5f9e3c8cd629313e57b9dadc328c6131b92f45d'
dest=ROOT/'docs/archive/CONTINUOUS_DAILY_TREND_TASK_METADATA_20261004_V1';dest.mkdir()
roles={}
for p in (STATE/'task-progress').glob('task-*.json'):
    t=read(p)
    if t['id']==os.environ['COIN_TASK_ID'] or not t['title'].startswith('D064'):continue
    assert t['ended_at'] and t['exit_code'] in (0,1) and t['status']==('completed' if t['exit_code']==0 else 'failed')
    copied=dest/p.name;shutil.copyfile(p,copied)
    roles[t['id']]=dict(title=t['title'],status=t['status'],actual_exit_code=t['exit_code'],task_archive=copied.relative_to(ROOT).as_posix(),task_archive_sha256=sha(copied))
for run in STATE.glob('d064-*'):
    if not run.is_dir():continue
    for name in ['RUN_BINDING.json','ACTUAL_BINDING.json','junit.xml']:
        p=run/name
        if p.is_file():shutil.copyfile(p,dest/(run.name+'-'+name))
selected=set(git('diff','--name-only').splitlines())
for folder in ['protocols','reports/fast_research','reports','docs/archive']:
    for pattern in ['CONTINUOUS_DAILY_TREND_*','DONCHIAN_DAILY_SEMANTICS_*']:
        selected.update(p.relative_to(ROOT).as_posix() for p in (ROOT/folder).glob(pattern) if p.is_file())
selected.update(p.relative_to(ROOT).as_posix() for p in dest.iterdir())
selected.update(['scripts/investment/donchian_daily_pool_target.py','tests/test_donchian_daily_pool.py',prior.relative_to(ROOT).as_posix()])
assert not set(read(prior)['preserved_untracked_paths']).intersection(selected)
owned=sum(p.stat().st_size for d in STATE.glob('d064-*') if d.is_dir() for p in d.rglob('*') if p.is_file())
assert owned<1500000000
report=dict(status='CONTINUOUS303_SAVED_CALENDARS_FINANCE_AND_ECONOMIC_ACCEPTANCE_ORIGINAL_BUDGET_FAILURE_RETAINED',
    parent_commit=PARENT,created_utc=datetime.now(UTC).isoformat(),task_id=os.environ['COIN_TASK_ID'],
    source_hashes={n:sha(ROOT/n) for n in sorted(selected)},selected_module_paths=sorted(selected),
    verified_prior_files={'reports/fast_research/FUNDING_SEMANTICS_PROBE_20261003_V2.json':sha(ROOT/'reports/fast_research/FUNDING_SEMANTICS_PROBE_20261003_V2.json'),'reports/fast_research/BYBIT_PUBLIC_SPEC_PROBE_20261003_V2.json':sha(ROOT/'reports/fast_research/BYBIT_PUBLIC_SPEC_PROBE_20261003_V2.json')},
    closed_actual_roles=roles,owned_d064_STATE_bytes=owned,main_accounts=12,complete_saved_calendar_accounts=12,
    producer_budget_passed_accounts=8,producer_budget_failed_accounts=4,complete_financial_calls=12,paired_cases=8,
    models_fit=0,HPO=0,new_downloads=0,new_QA=0,orders_sent=0,locked_body_read=False,
    private_SHA_only=sha(ROOT/'state/dataset_lock.json'),candidate='NONE',investment='CASH',long_term_APR='NOT_EVALUABLE',
    prior_WIP_preserved=read(prior)['preserved_untracked_paths'],
    diagnostic_report_sha256=sha(rp),independent_static_review_sha256=sha(ROOT/'reports/CONTINUOUS_DAILY_TREND_INDEPENDENT_REVIEW_20261004_V1.md'),
    final_disk_receipt='reports/CONTINUOUS_DAILY_TREND_FINAL_RESOURCE_20261004_V1.json',
    next_handoff='One active-signal allocation contrast with unchanged signals/risk/cost; not currently running')
out=ROOT/'reports/GITHUB_CONTINUOUS_DAILY_TREND_SOURCE_BINDING_20261004_V1.json'
with out.open('x') as f:json.dump(report,f,indent=2);f.write('\n')
print(json.dumps(dict(output=str(out),sha256=sha(out),paths=len(selected),owned_STATE_bytes=owned)))
