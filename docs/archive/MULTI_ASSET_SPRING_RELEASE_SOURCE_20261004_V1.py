"""Verify this completed module and archive small runtime bindings, no replay."""
import hashlib,json,os,subprocess
from pathlib import Path
from datetime import UTC,datetime
ROOT=Path('/mnt/d/codex/coin');STATE=Path('/home/xflops/coin-state')
PARENT='a98ceb45178d445b78a2cac113956f0408ac07fe'
DEST=ROOT/'docs/archive/MULTI_ASSET_SPRING_RELEASE_METADATA_20261004_V1'
def sha(p):
    with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def read(p):
    p=Path(p);assert p.is_file() and not p.is_symlink() and p.stat().st_size<=4_000_000
    return json.loads(p.read_bytes())
def archive(p,name):
    read(p)
    with (DEST/name).open('xb') as f:f.write(Path(p).read_bytes())
    assert sha(p)==sha(DEST/name)
assert os.environ['COIN_TASK_ID'] and subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()==PARENT
DEST.mkdir();roles={};maximum=dict(cash=0.,ratio=0.)
receipts=list((ROOT/'reports/fast_research').glob('MULTI_ASSET_SPRING_*.json'))
receipts += [ROOT/'reports/fast_research/MULTI_ASSET_DECIMAL_TAIL_SYNTHETIC_20261004_V1.json',
    ROOT/'reports/fast_research/BYBIT_FEE_AND_D061_COST_REVIEW_20261004_V1.json',
    ROOT/'reports/MULTI_ASSET_SPRING_FINAL_RESOURCE_20261004_V1.json']
for p in receipts:
    r=read(p);ident=r.get('binding',{}).get('task_id') or r.get('task_id')
    assert ident,p
    tpath=STATE/'task-progress'/('task-'+ident+'.json');t=read(tpath)
    failed=r['status']=='FAIL_D062_SOURCE_STAGE'
    assert t['status']==('failed' if failed else 'completed') and t['exit_code']==(1 if failed else 0) and t['ended_at'],p
    archive(tpath,p.stem+'-TASK.json')
    roles[p.relative_to(ROOT).as_posix()]=dict(sha256=sha(p),status=r['status'],task_id=ident,actual_exit_code=t['exit_code'],
        task_archive=(DEST/(p.stem+'-TASK.json')).relative_to(ROOT).as_posix())
    if r.get('run_dir'):
        owner=Path(r['run_dir']);assert owner.parent==STATE
        for n in ('RUN_BINDING.json','ACTUAL_BINDING.json'):
            if (owner/n).exists():archive(owner/n,p.stem+'-'+n)
    if p.name.endswith('_FINANCIAL_20261004_V1.json'):
        assert r['completed_cases_verified']==4 and r['tolerances']==dict(cash_USDT=1e-7,ratio=1e-10)
        for k in maximum:maximum[k]=max(maximum[k],r['maximum_errors'][k])
for recipe in ('HOLD_TWO','HOLD_TEN','MOMENTUM_TEN'):
    stem='MULTI_ASSET_SPRING_'+recipe+'_20261004_V1'
    p=read(ROOT/'protocols'/(stem+'.json'));a=read(ROOT/'reports/fast_research'/(stem+'.json'))
    assert a['completed_cases']==a['complete_calendar_cases']==4 and a['actual_calendar_days']==122
    assert all(c['summary']['completed_minutes']==c['summary']['required_minutes']==175680 for c in a['cases'])
    assert a['binding']['source_hashes']==p['source_hashes']
    for n,h in p['source_hashes'].items():assert sha(ROOT/n)==h,n
    fin=read(ROOT/'reports/fast_research'/('MULTI_ASSET_SPRING_'+recipe+'_FINANCIAL_20261004_V1.json'))
    assert fin['actual_report_sha256']==sha(ROOT/'reports/fast_research'/(stem+'.json'))
for kind in ('POOL','SIGNAL'):
    r=read(ROOT/'reports/fast_research'/('MULTI_ASSET_SPRING_'+kind+'_PAIRED_20261004_V1.json'))
    assert r['status']=='COMPLETE_SAVED_MULTI_ASSET_PAIRED_COMPARISON_NOT_APR' and len(r['pairs'])==4
assert maximum['cash']<=1e-7 and maximum['ratio']<=1e-10
old=read(ROOT/'reports/fast_research/MULTI_ASSET_SPRING_PRE_FIX_SOURCE_PRESERVED_20261004_V1.json')
for r in old['archives']:assert sha(ROOT/r['path'])==r['sha256']
failed_launchers={}
for ident in ('eac4f44c29d5495eaff0bbac117b1944','7e50c439d8a8496981bf825dea247636','efbe6b7bbd0d40748f2f55b2d3377869'):
    t=read(STATE/'task-progress'/('task-'+ident+'.json'));assert t['status']=='failed' and t['exit_code']==1
    archive(STATE/'task-progress'/('task-'+ident+'.json'),'BEFORE_SCIENCE_FAILED-'+ident+'-TASK.json')
    failed_launchers[ident]=dict(title=t['title'],actual_exit_code=1,market_accounts=0,source_QA_calls=0,tests_called=0)
assert sha(ROOT/'state/dataset_lock.json')=='29d930063842e9b1666869b4e5f9e3c8cd629313e57b9dadc328c6131b92f45d'
selected=set(subprocess.check_output(['git','diff','--name-only'],cwd=ROOT,text=True).splitlines())
for folder in ('protocols','reports/fast_research','reports','docs/archive'):
    for prefix in ('MULTI_ASSET_SPRING_','MULTI_ASSET_DECIMAL_','BYBIT_FEE_AND_','TRADE_NUMERIC_PRE_FIX_'):
        selected.update(p.relative_to(ROOT).as_posix() for p in (ROOT/folder).glob(prefix+'*') if p.is_file())
selected.update(p.relative_to(ROOT).as_posix() for p in DEST.iterdir())
selected.update(['tests/test_spring_portfolio_causal_calendar.py','tests/test_trade_parser_decimal_tail.py',
    'docs/input_evidence/BYBIT_USER_FEE_SNAPSHOT_20261004.json','docs/input_evidence/COIN_COST_AND_STRATEGY_CORRECTION_20261004.md',
    'reports/GITHUB_TURTLE_EXACT_QUANTITY_SYNC_VERIFIED_20261004_V1.json'])
owned=sum(p.stat().st_size for d in STATE.glob('d062-*') if d.is_dir() for p in d.rglob('*') if p.is_file())
assert owned<=1500000000
report=dict(status='CURRENT_MODULE_EXISTING_ACTUAL_ACCEPTANCE_BINDING_NOT_NEW_MARKET_REPLAY',parent_commit=PARENT,
    source_hashes={n:sha(ROOT/n) for n in sorted(selected)},selected_module_paths=sorted(selected),
    closed_actual_roles=roles,failed_launcher_roles=failed_launchers,complete_new_account_cases=12,
    independent_complete_financial_calls=12,paired_cases=8,calendar_days=122,owned_STATE_bytes=owned,
    maximum_errors=maximum,pre_fix_archives=old['archives'],market_payload_read_or_hashed=False,
    candidate='NONE',investment='CASH',long_term_APR='NOT_EVALUABLE',models_fit=0,orders_sent=0,locked_consumed=False,
    created_utc=datetime.now(UTC).isoformat())
out=ROOT/'reports/GITHUB_MULTI_ASSET_SPRING_SOURCE_BINDING_20261004_V1.json'
with out.open('x') as f:json.dump(report,f,indent=2,allow_nan=False);f.write('\n')
print(json.dumps(dict(output=str(out),sha256=sha(out),selected_paths=len(selected),owned_STATE_bytes=owned)),flush=True)
