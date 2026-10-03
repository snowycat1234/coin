"""Small completed-task/source closure for the fixed Turtle experiment only."""
import hashlib,json,os,sys
from datetime import UTC,datetime
from pathlib import Path
ROOT=Path('/mnt/d/codex/coin');STATE=Path('/home/xflops/coin-state')
ARCHIVE='docs/archive/TURTLE_PERPETUAL_ROOT_CLOSE_SOURCE_20261003_V1.py'
def sha(p):
    with Path(p).open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()
def read(p):
    p=Path(p);assert not p.is_symlink() and p.stat().st_size<2_000_000
    return json.loads(p.read_bytes())
def write(p,v):
    with (ROOT/p).open('x') as f:json.dump(v,f,indent=2,ensure_ascii=False,allow_nan=False);f.write('\n')
def closed(task_id,code=0):
    path=STATE/'task-progress'/('task-'+task_id+'.json');v=read(path)
    assert v['id']==task_id and v['status']==('completed' if code==0 else 'failed') and v['exit_code']==code
    return dict(path=str(path),sha256=sha(path),task=v)
assert os.environ.get('COIN_TASK_ID') and sys.prefix==str(STATE/'v8-clean-env-20261002-v2')
assert sha(__file__)==sha(ROOT/ARCHIVE)
assert sha(ROOT/'state/dataset_lock.json')=='29d930063842e9b1666869b4e5f9e3c8cd629313e57b9dadc328c6131b92f45d'
paths={
 'vendor':'reports/fast_research/TURTLE_RULES_OFFICIAL_SOURCE_PROVENANCE_20261003_V2.json',
 'source':'reports/fast_research/TURTLE_4H_WARMUP_SOURCE_ACTUAL_20261003_V1.json',
 'source_QA':'reports/fast_research/TURTLE_4H_WARMUP_SOURCE_INDEPENDENT_20261003_V1.json',
 'synthetic':'reports/fast_research/TURTLE_PERPETUAL_SMOKE_20261003_V2.json',
 'market':'reports/fast_research/TURTLE_PERPETUAL_RESEARCH_ACTUAL_20261003_V2.json',
 'finance':'reports/fast_research/TURTLE_PERPETUAL_FINANCIAL_INDEPENDENT_20261003_V1.json',
 'comparison':'reports/fast_research/TURTLE_PERPETUAL_SAVED_COMPARISON_20261003_V2.json'}
values={role:read(ROOT/path) for role,path in paths.items()}
tasks={role:closed(value['binding']['task_id']) for role,value in values.items()}
market,finance=values['market'],values['finance']
assert market['completed_cases']==market['required_cases']==len(market['cases'])==4
assert finance['financial_case_calls']==finance['completed_cases_verified']==4
assert finance['completed_full_calendar_cases_verified']==market['completed_full_calendar_cases']
assert finance['status'].startswith('PASS_D047_TURTLE_RECORDED_PERPETUAL_ACCOUNTING')
assert values['synthetic']['test_exit_code']==0 and values['synthetic']['source_bytes_unchanged']
assert values['source_QA']['status']=='PASS_D047_OFFICIAL_4H_WARMUP_SOURCE_ONLY'
pins={path:sha(ROOT/path) for path in paths.values()}
for value in values.values():
    for name,digest in value['binding'].get('source_hashes',{}).items():
        assert name!='state/dataset_lock.json'
        p=Path(name) if name.startswith('/') else ROOT/name
        if not p.is_relative_to(ROOT):continue
        rel=p.relative_to(ROOT).as_posix()
        assert rel not in pins or pins[rel]==digest,rel
        assert sha(p)==digest,rel
        pins[rel]=digest
for pattern in ['docs/archive/TURTLE*','protocols/TURTLE*','reports/fast_research/TURTLE*','third_party/jesse_example_turtle_rules/*']:
    for p in ROOT.glob(pattern):
        if p.is_file():pins[p.relative_to(ROOT).as_posix()]=sha(p)
for name in ['docs/OPEN_SOURCE_REGISTRY.md','docs/TURTLE_PERPETUAL_20261003.md',ARCHIVE,
 'reports/GITHUB_PERPETUAL_RISK_REDUCTION_SYNC_VERIFIED_20261003_V1.json']:
    pins[name]=sha(ROOT/name)
failures={
 'vendor_TLS':closed('6bb8e575e7a04b46925c040134c4995b',1),
 'warmup_freezer_metadata':closed('6e3b1a98a42141d8bf7ef845b95f253a',1),
 'warmup_QA_binder_metadata':closed('af34690205324a5ba3b8a8503b44077a',1),
 'synthetic_controller_V1':closed('74d4c497bdea4701b257c55df82ff70f',1),
 'comparison_CASH_optional_field':closed('3101767348a14165afa04b9588d58902',1)}
assert (ROOT/'reports/experiment_registry.jsonl').stat().st_size<4_000_000
root=dict(status='PASS_D047_FIXED_TURTLE_CONDITIONAL_RESEARCH_NOT_NATIVE_OR_APR',
 binding=dict(task_id=os.environ['COIN_TASK_ID'],source_path=ARCHIVE,source_sha256=sha(__file__),source_hashes=pins),
 actual_tasks=tasks,preserved_failed_tasks=failures,completed_cases=4,
 complete_calendar_cases=market['completed_full_calendar_cases'],source_bytes_unchanged=True,
 financial_scope='RECORDED_FINANCE_ONLY_NOT_COMPLETE_STRATEGY_STATE_OR_NATIVE_EXECUTION',
 old_accounts_or_QA_replayed=False,locked_consumed=False,orders_sent=0,GPU=0,
 candidate='NO_QUALIFIED_CANDIDATE',long_term_APR='NOT_EVALUABLE',created_utc=datetime.now(UTC).isoformat())
rootpath='reports/fast_research/TURTLE_PERPETUAL_ROOT_ACCEPTANCE_20261003_V1.json';write(rootpath,root)
source=dict(status='D047_COMPLETED_FIXED_TURTLE_SOURCES_AND_RECEIPTS_BOUND',source_hashes=pins)
sourcepath='reports/GITHUB_TURTLE_PERPETUAL_SOURCE_BINDING_20261003_V1.json';write(sourcepath,source)
old=read(ROOT/'reports/GITHUB_PERPETUAL_RISK_REDUCTION_USED_RECEIPTS_BINDING_20261003_V1.json')
oldhash=old['source_hashes']['docs/OPEN_SOURCE_REGISTRY.md']
alias='docs/archive/OPEN_SOURCE_REGISTRY_PRE_TURTLE_20261003_V1.md';assert sha(ROOT/alias)==oldhash
used=dict(status='D047_ACTUAL_COMPLETED_TASKS_BOUND_AFTER_ROOT_METADATA',source_hashes=dict(pins,**{rootpath:sha(ROOT/rootpath),sourcepath:sha(ROOT/sourcepath)}),
 historical_source_aliases=[dict(original_path='docs/OPEN_SOURCE_REGISTRY.md',original_sha256=oldhash,archive_path=alias)],
 true_completed_tasks=tasks,preserved_failures=failures,root_task_id=os.environ['COIN_TASK_ID'],
 root_true_completion='CALLER_MUST_VERIFY_AFTER_RETURN_NOT_SELF_ATTESTED')
write('reports/GITHUB_TURTLE_PERPETUAL_USED_RECEIPTS_BINDING_20261003_V1.json',used)
print(json.dumps(dict(status=root['status'],root_sha256=sha(ROOT/rootpath),pins=len(pins))))
