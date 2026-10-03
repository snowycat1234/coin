"""D038 root acceptance over actual closed source/test/three accounts/audit; metadata only."""
import argparse,hashlib,importlib.util,json,os
from datetime import UTC,datetime
from pathlib import Path
ROOT=Path('/mnt/d/codex/coin');STATE=Path('/home/xflops/coin-state')
ARCHIVE='docs/archive/PUBLIC_SMA_DAILY_ROOT_CLOSE_SOURCE_20261003_V3.py'
REUSE='docs/archive/VOL_MANAGED_HOLD_547D_ROOT_CLOSE_SOURCE_20261003_V2.py'
REUSE_SHA='278c9117283b88eb73b50276f37a4cd86449ffd87e747556db301dc146ce905a'
OUT='reports/fast_research/PUBLIC_SMA_DAILY_ROOT_ACCEPTANCE_20261003_V1.json'
GIT='reports/GITHUB_PUBLIC_SMA_DAILY_SOURCE_BINDING_20261003_V1.json'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def check(ok,msg):
    if not ok:raise ValueError(msg)
parser=argparse.ArgumentParser();parser.add_argument('--binding',type=Path,required=True);a=parser.parse_args()
check(os.environ.get('COIN_TASK_ID') and sha(__file__)==sha(ROOT/ARCHIVE),'Actual root task and exact archive')
check(sha(ROOT/REUSE)==REUSE_SHA,'Reuse exact metadata-only validation functions')
m=importlib.util.spec_from_file_location('d037_metadata_only',ROOT/REUSE);r=importlib.util.module_from_spec(m);m.loader.exec_module(r)
REGISTRY='docs/OPEN_SOURCE_REGISTRY.md'
REGISTRY_ARCHIVE='docs/archive/OPEN_SOURCE_REGISTRY_SMACROSSOVER_ACCEPTED_20261003_V1.md'
REGISTRY_SHA='8da5b04187f618759de190260bb7b277bf402c6f31b0480c37a85c8788e06f0e'
original_project=r.project
def project_with_registry(name):
    if name==REGISTRY:
        archived=original_project(REGISTRY_ARCHIVE)
        current=ROOT/REGISTRY
        check(not current.is_symlink() and current.resolve()==current and current.stat().st_size<=2_000_000,'One explicit small ordinary registry source')
        check(sha(current)==REGISTRY_SHA and sha(archived)==REGISTRY_SHA,'Exact current registry and raw archive')
        return archived
    return original_project(name)
r.project=project_with_registry
plan,plan_sha=r.small(a.binding)
check(plan['helper_sha256']==sha(__file__) and len(plan['roles'])==6,'Frozen six-role closure binding')
before=r.resources.status();r.bounded(before);hashes={ARCHIVE:sha(__file__),REUSE:REUSE_SHA,str(a.binding.relative_to(ROOT)):plan_sha}
private={};roles={};snapshots=[]
for role,item in plan['roles'].items():
    value,digest=r.small(r.project(item['report']),item['report_sha256'])
    check(value['status']==item['required_status'],'Exact role status '+role)
    task_id=value['binding']['task_id'];check(task_id==item['task_id'],'Exact actual task '+role)
    task=r.closed(task_id);roles[role]=dict(report=item['report'],report_sha256=digest,actual_closed0_task=task)
    hashes[item['report']]=digest;snapshots.append((Path(task['path']),role+'_CLOSED_TASK.json',task['sha256']))
    binding_path=Path(value['run_dir'])/'RUN_BINDING.json' if 'run_dir' in value else Path(item['run_binding'])
    if role!='VENDOR':
        _,binding_sha=r.small(binding_path,item['run_binding_sha256']);snapshots.append((binding_path,role+'_RUN_BINDING.json',binding_sha))
    for name,h in value['binding'].get('source_hashes',value.get('source_hashes',{})).items():
        if name=='state/dataset_lock.json':private[name]=h;check(sha(ROOT/name)==h,'Frozen private scientific lock');continue
        if name.startswith('.cache/') or Path(name).is_absolute():continue
        r.small(r.project(name),h,False)
        check(name not in hashes or hashes[name]==h,'Consistent shared frozen source '+name);hashes[name]=h
    if role.startswith('MARKET'):
        check(value['all_planned_ledgers_complete'] and value['completed_ledgers']==1 and value['source_bytes_unchanged']
            and value['locked_consumed'] is False and value['orders_sent']==value['market_models_fit']==0,'Complete single no-money account '+role)
        row=value['folds'][0]['results'][0]
        check(row['spread_bps']==8 and row['nominal_roundtrip_bps']==36,'Same fixed Bybit Spot total cost')
        roles[role]['summary']=row['summary'];roles[role]['owned_bytes']=value['owned_bytes']
    if role=='TINY':check(value['test_exit_code']==0 and value['junit_counts']==dict(tests=1,errors=0,failures=0,skipped=0),'Unique new boundary case actually passed')
for role,item in plan.get('extra_closed_metadata_roles',{}).items():
    value,digest=r.small(r.project(item['report']),item['report_sha256'])
    check(value['status']==item['required_status'] and value['binding']['task_id']==item['task_id'],'Exact metadata comparison status/task')
    task=r.closed(item['task_id']);roles[role]=dict(report=item['report'],report_sha256=digest,actual_closed0_task=task)
    hashes[item['report']]=digest;snapshots.append((Path(task['path']),role+'_CLOSED_TASK.json',task['sha256']))
    check(value['market_arrays_read'] is False and value['old_financial_or_QA_replayed'] is False,'Saved-summary comparison only')
    for name,h in value['source_hashes'].items():
        r.small(r.project(name),h,False);check(name not in hashes or hashes[name]==h,'Comparison frozen source');hashes[name]=h
for name,h in plan['project_sources'].items():
    if name=='state/dataset_lock.json':private[name]=h;check(sha(ROOT/name)==h,'Private lock separately verified');continue
    r.small(r.project(name),h,False);check(name not in hashes or hashes[name]==h,'Exact extra source');hashes[name]=h
check(private=={'state/dataset_lock.json':'29d930063842e9b1666869b4e5f9e3c8cd629313e57b9dadc328c6131b92f45d'},'Only exact private scientific-lock exclusion')
ownership=[]
for item in plan['owned_directories']:
    p=Path(item['path']);check(p.is_relative_to(STATE) and p.resolve()==p and p.is_dir(),'Exclusive known STATE directory')
    files=list(p.rglob('*'));check(not p.is_symlink(),'Owned root must be a real directory')
    for f in files:
        if f.is_symlink():
            allowed=tuple(STATE/f'd038-public-sma-smoke-20261003-v{v}/pytest/test_sma_daily_native_routecurrent' for v in (1,2))
            expected=f if f in allowed else allowed[-1]
            target=expected.with_name('test_sma_daily_native_route0')
            check(f==expected and p==expected.parent.parent and f.resolve(strict=True)==target and target.is_dir()
                and not target.is_symlink() and target.is_relative_to(p),'Only exact same-owned pytest current alias')
    size=sum(f.stat().st_size for f in files if f.is_file());check(size<=item['maximum_bytes'],'Per-role owned budget');ownership.append(dict(path=str(p),bytes=size))
check(sum(v['bytes'] for v in ownership)<=450_000_000,'Combined D038450MB hard working-artifact budget')
failures=[]
for item in plan.get('preserved_failures',[]):
    value,h=r.small(r.project(item['report']),item['report_sha256']);task=r.closed(item['task_id'],1)
    hashes[item['report']]=h;failures.append(dict(report=item['report'],sha256=h,actual_failed1_task=task,economic_result=False))
    snapshots.append((Path(task['path']),'FAILED_'+item['task_id']+'_TASK.json',task['sha256']))
meta=ROOT/'docs/archive/PUBLIC_SMA_DAILY_USED_ACTUAL_METADATA_20261003_V1';meta.mkdir()
for p,name,h in snapshots:
    check(sha(p)==h,'Closed metadata remains exact');target=meta/name
    with target.open('xb') as w:w.write(p.read_bytes())
    hashes[target.relative_to(ROOT).as_posix()]=h
after=r.resources.status();r.bounded(after)
for name,h in hashes.items():r.small(r.project(name),h,False)
value=dict(status='PASS_ROOT_D038_FIXED_SMA_BOUNDARY_THREE_LEDGER_AND_INDEPENDENT_SCOPE_SCREENING_ONLY',
    created_utc=datetime.now(UTC).isoformat(),binding=dict(task_id=os.environ['COIN_TASK_ID'],helper_sha256=sha(__file__),closure_binding_sha256=plan_sha,root_own_completion='LIVE_NOT_YET_CLOSED'),
    source_hashes=hashes,local_non_git_source_hashes=private,roles=roles,ownership=ownership,owned_total_bytes=sum(v['bytes'] for v in ownership),
    preserved_initialization_failures=failures,resources_before=before,resources_after=after,metadata_only=True,
    market_or_ledger_arrays_read_by_root=False,old_accounts_or_QA_replayed=False,locked_consumed=False,orders_sent=0,models_fit=0,
    candidate_status='NO_QUALIFIED_CANDIDATE',long_term_APR='NOT_EVALUABLE',data_venue='Binance',fee_venue='BybitVIP0Spot',native_execution_certified=False)
out_sha,_=r.write(ROOT/OUT,value)
portable=dict(value,status='PASS_D038_PORTABLE_SOURCE_BINDING_PRIVATE_LOCK_EXCLUDED',source_hashes={**hashes,OUT:out_sha},
    root_acceptance_sha256=out_sha,private_lock_body_archived=False,root_task_requires_later_closed0_verification=True)
git_sha,_=r.write(ROOT/GIT,portable)
print(json.dumps(dict(root_report_sha256=out_sha,portable_sha256=git_sha,closed0_roles=len(roles),owned_total_bytes=value['owned_total_bytes'])))
