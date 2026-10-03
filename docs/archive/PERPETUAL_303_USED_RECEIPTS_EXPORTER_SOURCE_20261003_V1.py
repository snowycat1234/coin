"""D045 used closed metadata export; no market payloads or private lock body.
Optional --module-doc selects the root-written module Markdown (default below).
Root executes only after final ROOT is truly completed0; no fabricated run paths.
"""
import argparse,hashlib,json
from pathlib import Path
r=Path('/mnt/d/codex/coin');state=Path('/home/xflops/coin-state');tasks=state/'task-progress'
archive='docs/archive/PERPETUAL_303_USED_RECEIPTS_EXPORTER_SOURCE_20261003_V1.py'
root_path='reports/fast_research/PERPETUAL_303_RESEARCH_ROOT_ACCEPTANCE_20261003_V1.json'
plan_path='protocols/PERPETUAL_303_RESEARCH_ROOT_BINDING_20261003_V1.json'
portable='reports/GITHUB_PERPETUAL_303_RESEARCH_SOURCE_BINDING_20261003_V1.json'
folder=r/'docs/archive/PERPETUAL_303_USED_ACTUAL_METADATA_20261003_V1'
out=r/'reports/GITHUB_PERPETUAL_303_USED_RECEIPTS_BINDING_20261003_V1.json'
LOCK='state/dataset_lock.json';LOCK_SHA='29d930063842e9b1666869b4e5f9e3c8cd629313e57b9dadc328c6131b92f45d'
STATUS='PASS_ROOT_D045_TWENTY_FIXED303D_CONDITIONAL_ACCOUNTS_NOT_NATIVE_OR_LONG_TERM_APR'
def sha(p):
    with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def small(p):
    p=Path(p);assert p.suffix=='.json' and p.is_file() and not p.is_symlink() and p.stat().st_size<=2_000_000
    return json.loads(p.read_bytes())
parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--module-doc',default='docs/PERPETUAL_303_COMPARISON_20261003.md');a=parser.parse_args()
assert Path(__file__).read_bytes()==(r/archive).read_bytes()
assert not folder.exists() and not out.exists()
proof=small(r/root_path);assert proof['status']==STATUS
plan=small(r/plan_path);assert set(plan['roles'])=={'SOURCE','QA','ROOT','SMOKE','MARKET','FINANCE','COMPARISON'}
assert proof['local_non_git_hash_guard']=={LOCK:LOCK_SHA} and sha(r/LOCK)==LOCK_SHA
roles=dict(plan['roles']);assert 'FINAL_ROOT' not in roles
roles['FINAL_ROOT']=dict(path=root_path,task_id=proof['binding']['task_id'],sha256=sha(r/root_path),required_status=STATUS)
records={};actual_tasks={}
for label,item in roles.items():
    assert not Path(item['path']).is_absolute() and '..' not in Path(item['path']).parts and item['path'].startswith('reports/fast_research/')
    report=small(r/item['path']);assert sha(r/item['path'])==item['sha256'] and report['status']==item['required_status'] and report['binding']['task_id']==item['task_id']
    path=tasks/('task-'+item['task_id']+'.json');task=small(path)
    assert task['id']==item['task_id'] and type(task['exit_code']) is int and task['exit_code']==0 and task['status']=='completed'
    records[label]=report;actual_tasks[label]=(path,task)
assert len({t['id'] for _,t in actual_tasks.values()})==8
module=Path(a.module_doc);assert not module.is_absolute() and '..' not in module.parts and a.module_doc.startswith('docs/') and module.suffix=='.md'
folder.mkdir();hashes={};exports={};missing=[];total=0
for label,item in roles.items():hashes[item['path']]=item['sha256']
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
        spec=small(protocol);assert sha(protocol)==report['binding']['protocol_sha256']
        assert spec['run_dir']=='/home/xflops/coin-state/d045-perpetual-303-research-20261003-v1'
        candidates.append(spec['run_dir']);hashes[protocol.relative_to(r).as_posix()]=sha(protocol)
    assert not candidates or len(set(candidates))==1
    owner=candidates[0] if candidates else None
    if label=='MARKET':assert owner=='/home/xflops/coin-state/d045-perpetual-303-research-20261003-v1'
    if owner:
        owned=Path(owner);assert owned.parent==state and not owned.is_symlink();rb=owned/'RUN_BINDING.json'
        if rb.is_file():
            value=small(rb);assert value['task_id']==item['task_id']
            if 'run_binding_sha256' in report:assert sha(rb)==report['run_binding_sha256']
            export(label+'_RUN_BINDING',rb)
        else:
            assert 'run_binding_sha256' not in report;missing.append(dict(role=label,path=str(rb),reason='ACTUAL_RUN_BINDING_NOT_PRESENT_NO_FILE_FABRICATED'))
    else:missing.append(dict(role=label,reason='NO_ACTUAL_RUN_DIR_DECLARED_NO_FILE_FABRICATED'))
for name in (archive,root_path,portable,plan_path,a.module_doc,'docs/OPEN_SOURCE_REGISTRY.md',
    'docs/archive/OPEN_SOURCE_REGISTRY_PRE_PERPETUAL_303_20261003_V1.md',
    'docs/archive/PERPETUAL_303_PUSH_VERIFICATION_SOURCE_20261003_V1.py',
    'reports/fast_research/PERPETUAL_303_SAVED_SCAN_20261003_V1.json',
    'docs/archive/PERPETUAL_303_SAVED_SCAN_SOURCE_20261003_V1.py'):
    path=r/name;assert name!=LOCK and path.is_file() and not path.is_symlink() and path.stat().st_size<=2_000_000;hashes[name]=sha(path)
assert LOCK not in hashes
value=dict(status='D045_ACTUAL_ROOT_CLOSED0_USED_SMALL_METADATA_ONLY',source_hashes=hashes,
    exports=exports,root_task_id=proof['binding']['task_id'],source_root_task_id=roles['ROOT']['task_id'],
    root_acceptance_sha256=sha(r/root_path),local_non_git_hash_guard={LOCK:LOCK_SHA},private_lock_body_read_or_exported=False,
    candidate='NO_QUALIFIED_CANDIDATE',funding_rate_unit='UNCONFIRMED',long_term_APR='NOT_EVALUABLE',market_payloads_exported=False,
    roles_completed0=8,missing_actual_RUN_BINDING_truthfully_not_exported=missing,
    inherited_failed547_provenance_referenced_not_exported_again=True)
payload=(json.dumps(value,indent=2,ensure_ascii=False,allow_nan=False)+'\n').encode();assert len(payload)+total<=4_000_000
with out.open('xb') as f:f.write(payload)
print(json.dumps(dict(status=value['status'],sha256=sha(out),exported_bytes=total,index_bytes=len(payload))))
