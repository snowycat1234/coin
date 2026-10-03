"""D046 closed used metadata export; no market payloads or private LOCK body.
Only MARKET/FINANCE/SMOKE plus FINAL_ROOT are completed scientific roles.
The initial metadata failure and genuine compile/freezer tasks stay separate.
Root executes this once after ROOT really completed0. No missing RUN is made.
"""
import argparse,hashlib,json,re
from pathlib import Path
r=Path('/mnt/d/codex/coin');state=Path('/home/xflops/coin-state');tasks=state/'task-progress'
archive='docs/archive/PERPETUAL_RISK_REDUCTION_USED_RECEIPTS_EXPORTER_SOURCE_20261003_V1.py'
root_path='reports/fast_research/PERPETUAL_RISK_REDUCTION_ROOT_ACCEPTANCE_20261003_V1.json'
plan_path='protocols/PERPETUAL_RISK_REDUCTION_ROOT_BINDING_20261003_V1.json'
portable='reports/GITHUB_PERPETUAL_RISK_REDUCTION_SOURCE_BINDING_20261003_V1.json'
pre_registry='docs/archive/OPEN_SOURCE_REGISTRY_PRE_PERPETUAL_RISK_REDUCTION_20261003_V1.md'
folder=r/'docs/archive/PERPETUAL_RISK_REDUCTION_USED_ACTUAL_METADATA_V1'
out=r/'reports/GITHUB_PERPETUAL_RISK_REDUCTION_USED_RECEIPTS_BINDING_20261003_V1.json'
LOCK='state/dataset_lock.json';LOCK_SHA='29d930063842e9b1666869b4e5f9e3c8cd629313e57b9dadc328c6131b92f45d'
STATUS='PASS_ROOT_D046_FOUR_CORRECTNESS_CONTROLS_AND_TWENTY_SAVED_SELECTORS_NOT_NATIVE_OR_LONG_TERM_APR'
OWNERS=dict(MARKET='d046-perpetual-risk-reduction-research-20261003-v2',
    FINANCE='d046-perpetual-risk-reduction-financial-independent-20261003-v1',
    SMOKE='d046-perpetual-risk-reduction-smoke-20261003-v2',
    FINAL_ROOT='d046-perpetual-risk-reduction-root-20261003-v1')
def sha(p):
    with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def small(p):
    p=Path(p);assert p.suffix=='.json' and p.is_file() and not p.is_symlink() and p.stat().st_size<=2_000_000
    return json.loads(p.read_bytes())
def closed(identity,code=0):
    assert isinstance(identity,str) and re.fullmatch('[0-9a-f]{32}',identity)
    path=tasks/('task-'+identity+'.json');value=small(path)
    assert value['id']==identity and type(value['exit_code']) is int and value['exit_code']==code and value['status']==('completed' if code==0 else 'failed')
    return path,value
parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--module-doc',default='docs/PERPETUAL_RISK_REDUCTION_20261003.md');a=parser.parse_args()
assert Path(__file__).read_bytes()==(r/archive).read_bytes() and not folder.exists() and not out.exists()
proof=small(r/root_path);plan=small(r/plan_path)
assert proof['status']==STATUS and set(plan['roles'])=={'MARKET','FINANCE','SMOKE'}
assert proof['local_non_git_hash_guard']=={LOCK:LOCK_SHA} and sha(r/LOCK)==LOCK_SHA
assert proof['completed_selector_references']==20 and proof['new_financial_case_calls']==4 and proof['old_financial_case_calls']==0 and proof['new_complete_calendar_cases']==4 and proof['new_prefix_cases']==0
roles=dict(plan['roles']);roles['FINAL_ROOT']=dict(path=root_path,task_id=proof['binding']['task_id'],sha256=sha(r/root_path),required_status=STATUS)
records={};actual_tasks={}
for label,item in roles.items():
    assert not Path(item['path']).is_absolute() and '..' not in Path(item['path']).parts and item['path'].startswith('reports/fast_research/')
    report=small(r/item['path']);assert sha(r/item['path'])==item['sha256'] and report['status']==item['required_status'] and report['binding']['task_id']==item['task_id']
    records[label]=report;actual_tasks[label]=closed(item['task_id'])
assert len({task['id'] for _,task in actual_tasks.values()})==4
module=Path(a.module_doc);assert not module.is_absolute() and '..' not in module.parts and a.module_doc.startswith('docs/') and module.suffix=='.md'
hashes={};exports={};missing=[];total=0
def pin(name,digest=None):
    assert name!=LOCK and not Path(name).is_absolute() and '..' not in Path(name).parts
    p=r/name;assert p.is_file() and not p.is_symlink() and p.stat().st_size<=2_000_000
    assert p.suffix in {'.json','.py','.ps1','.md','.toml','.lock','.sh'}
    value=sha(p);assert digest is None or value==digest
    assert name not in hashes or hashes[name]==value;hashes[name]=value
for name,digest in plan['frozen_sources'].items():
    if name==LOCK:assert digest==LOCK_SHA
    else:pin(name,digest)
for item in roles.values():pin(item['path'],item['sha256'])
folder.mkdir()
def export(label,path):
    global total
    path=Path(path);assert path.is_file() and not path.is_symlink() and path.suffix=='.json' and path.is_relative_to(state)
    raw=path.read_bytes();assert len(raw)<=2_000_000;total+=len(raw);assert total<=4_000_000
    dest=folder/(label+'.json')
    with dest.open('xb') as f:f.write(raw)
    hashes[dest.relative_to(r).as_posix()]=sha(dest);exports[label]=dict(original_path=str(path),exported_path=dest.relative_to(r).as_posix(),sha256=sha(dest),bytes=len(raw))
for label,item in roles.items():
    path,task=actual_tasks[label];export(label+'_TASK',path);report=records[label]
    candidates=[x for x in (report.get('run_dir'),report['binding'].get('run_dir'),report['binding'].get('spec',{}).get('run_dir'),task.get('run_dir')) if x]
    if label=='MARKET':
        protocol=Path(report['binding']['protocol_path']);assert protocol.is_absolute() and protocol.parent==r/'protocols' and not protocol.is_symlink()
        spec=small(protocol);assert sha(protocol)==report['binding']['protocol_sha256'] and spec['run_dir']==str(state/OWNERS[label])
        candidates.append(spec['run_dir']);pin(protocol.relative_to(r).as_posix(),report['binding']['protocol_sha256'])
    assert candidates and set(candidates)=={str(state/OWNERS[label])}
    owned=state/OWNERS[label];assert owned.is_dir() and not owned.is_symlink();rb=owned/'RUN_BINDING.json'
    assert rb.is_file() and small(rb)['task_id']==item['task_id'] and sha(rb)==report['run_binding_sha256']
    export(label+'_RUN_BINDING',rb)
preserved={}
for label,identity in plan['preserved_metadata_failures'].items():
    path,task=closed(identity,1);expected=proof['preserved_metadata_failures'][label]
    assert expected['path']==str(path) and expected['sha256']==sha(path) and expected['task']==task
    export('FAILED_'+label+'_TASK',path);preserved[label]=dict(task_id=identity,status='failed',exit_code=1,run_binding_exported=False,scope='METADATA_INITIALIZATION_FAILED_BEFORE_ARRAYS')
    missing.append(dict(role=label,reason='NO_ACTUAL_RUN_BINDING_DECLARED_FOR_FAILED_INITIALIZATION_NO_FILE_FABRICATED'))
compile_path='reports/fast_research/PERPETUAL_RISK_REDUCTION_FINANCIAL_COMPILE_20261003_V1.json'
compile_report=small(r/compile_path);pin(compile_path,plan['frozen_sources'][compile_path])
assert compile_report['status']=='COMPILED_D046_INDEPENDENT_FOUR_ROUTE_METADATA_ONLY_NO_ARRAYS' and compile_report['market_arrays_read'] is False and compile_report['financial_cases_executed']==0
auxiliary=[('FINANCIAL_COMPILE',compile_report['binding']['task_id'])]
for name in ('protocols/PERPETUAL_RISK_REDUCTION_SMOKE_20261003_V2.json','protocols/PERPETUAL_RISK_REDUCTION_RESEARCH_20261003_V2.json'):
    protocol=small(r/name);pin(name,plan['frozen_sources'][name]);auxiliary.append(('FREEZER_'+Path(name).stem,protocol['freezer_task_id']))
    version2_freezer='docs/archive/PERPETUAL_RISK_REDUCTION_RESEARCH_FREEZER_20261003_V2.py'
    if version2_freezer in protocol['frozen_sources']:pin(version2_freezer,protocol['frozen_sources'][version2_freezer])
for label,identity in auxiliary:
    path,task=closed(identity);assert identity not in {item['task_id'] for item in roles.values()};export(label+'_TASK',path)
    missing.append(dict(role=label,reason='ACTUAL_METADATA_TASK_HAS_NO_RUN_BINDING_DECLARATION_NO_FILE_FABRICATED'))
for name in (archive,root_path,portable,plan_path,a.module_doc,'docs/OPEN_SOURCE_REGISTRY.md',pre_registry,
    'docs/archive/PERPETUAL_RISK_REDUCTION_PUSH_VERIFICATION_SOURCE_20261003_V1.py',
    'reports/fast_research/PERPETUAL_RISK_REDUCTION_SAVED_SCAN_20261003_V1.json',
    'docs/archive/PERPETUAL_RISK_REDUCTION_SAVED_SCAN_SOURCE_20261003_V1.py',
    'docs/archive/PERPETUAL_RISK_REDUCTION_RESEARCH_SOURCE_20261003_V1.py',
    'docs/archive/PERPETUAL_RISK_REDUCTION_RESEARCH_FREEZER_20261003_V1.py',
    'docs/archive/PERPETUAL_RISK_REDUCTION_RESEARCH_FREEZER_20261003_V2.py',
    'reports/fast_research/PERPETUAL_303_SOURCE_ROOT_ACCEPTANCE_20261003_V1.json',
    'reports/GITHUB_PERPETUAL_303_USED_RECEIPTS_BINDING_20261003_V1.json',
    'reports/GITHUB_PERPETUAL_303_SYNC_VERIFIED_20261003_V1.json'):pin(name)
assert LOCK not in hashes
value=dict(status='D046_ACTUAL_ROOT_CLOSED0_USED_SMALL_METADATA_ONLY',source_hashes=hashes,exports=exports,
    root_task_id=proof['binding']['task_id'],root_acceptance_sha256=sha(r/root_path),local_non_git_hash_guard={LOCK:LOCK_SHA},
    historical_source_aliases=[dict(original_path='docs/OPEN_SOURCE_REGISTRY.md',original_sha256=sha(r/pre_registry),archive_path=pre_registry)],
    private_lock_body_read_or_exported=False,candidate='NO_QUALIFIED_CANDIDATE',funding_rate_unit='UNCONFIRMED',long_term_APR='NOT_EVALUABLE',
    market_payloads_exported=False,roles_completed0=4,preserved_actual_metadata_failures=preserved,additional_actual_metadata_completed0_tasks=len(auxiliary),
    missing_actual_RUN_BINDING_truthfully_not_exported=missing,prior_D045_capabilities_referenced_without_reexporting_maps=True)
payload=(json.dumps(value,indent=2,ensure_ascii=False,allow_nan=False)+'\n').encode();assert len(payload)+total<=4_000_000
with out.open('xb') as f:f.write(payload)
print(json.dumps(dict(status=value['status'],sha256=sha(out),exported_bytes=total,index_bytes=len(payload))))
