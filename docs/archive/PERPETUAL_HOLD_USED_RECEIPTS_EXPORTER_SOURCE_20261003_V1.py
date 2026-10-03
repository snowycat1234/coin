"""Export actually used closed small task/RUN JSON only, never market payloads."""
import hashlib,json
from pathlib import Path
r=Path('/mnt/d/codex/coin');s=Path('/home/xflops/coin-state/task-progress')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
archive='docs/archive/PERPETUAL_HOLD_USED_RECEIPTS_EXPORTER_SOURCE_20261003_V1.py'
assert Path(__file__).read_bytes()==(r/archive).read_bytes()
root_path='reports/fast_research/PERPETUAL_HOLD_ROOT_ACCEPTANCE_20261003_V2.json'
proof=json.loads((r/root_path).read_bytes());assert proof['status']=='PASS_ROOT_D044_TWELVE_CONSTANT_LONG_CONDITIONAL_ACCOUNTS_NOT_NATIVE_OR_LONG_TERM_APR'
plan=json.loads((r/'protocols/PERPETUAL_HOLD_ROOT_BINDING_20261003_V2.json').read_bytes())
folder=r/'docs/archive/PERPETUAL_HOLD_USED_ACTUAL_METADATA_20261003_V1';folder.mkdir()
hashes={};exports={}
def export(label,path):
    raw=Path(path).read_bytes();assert len(raw)<2_000_000
    dest=folder/(label+'.json')
    with dest.open('xb') as f:f.write(raw)
    hashes[dest.relative_to(r).as_posix()]=sha(dest)
roles=dict(plan['roles'],ROOT=dict(path=root_path,task_id=proof['binding']['task_id'],exit_code=0))
for label,item in roles.items():
    # The original failed547 task is already exported/pinned by the inherited D043 binding.
    if label=='FULL547_FAILURE':continue
    path=s/('task-'+item['task_id']+'.json');task=json.loads(path.read_bytes())
    assert task['id']==item['task_id'] and task['exit_code']==item['exit_code']==0 and task['status']=='completed'
    export(label+'_TASK',path);report=json.loads((r/item['path']).read_bytes());owner=report.get('run_dir')
    if label=='MARKET':owner='/home/xflops/coin-state/d044-perpetual-hold-research-20261003-v1'
    if owner:export(label+'_RUN_BINDING',Path(owner)/'RUN_BINDING.json')
for label,identity in plan['metadata_failed_tasks'].items():
    path=s/('task-'+identity+'.json');task=json.loads(path.read_bytes())
    assert task['id']==identity and task['status']=='failed' and task['exit_code']==1
    export(label+'_TASK',path)
for label,path in {'FINANCIAL_METADATA_V2':'reports/fast_research/PERPETUAL_CONSTANT_LONG_REFERENCE_INDEPENDENT_20261003_V2.json',
    'ROOT_PRIOR_DOCUMENT_GUARD_V1':'reports/fast_research/PERPETUAL_HOLD_ROOT_ACCEPTANCE_20261003_V1.json'}.items():
    row=json.loads((r/path).read_bytes());assert row['status'].startswith('FAIL_')
    export(label+'_RUN_BINDING',Path(row['run_dir'])/'RUN_BINDING.json')
for name in (archive,root_path,'reports/GITHUB_PERPETUAL_HOLD_SOURCE_BINDING_20261003_V2.json',
    'protocols/PERPETUAL_HOLD_ROOT_BINDING_20261003_V2.json','docs/PERPETUAL_HOLD_COMPARISON_20261003.md',
    'docs/OPEN_SOURCE_REGISTRY.md','docs/archive/OPEN_SOURCE_REGISTRY_PRE_PERPETUAL_HOLD_20261003_V1.md',
    'docs/archive/PERPETUAL_HOLD_PUSH_VERIFICATION_SOURCE_20261003_V1.py'):
    hashes[name]=sha(r/name)
value=dict(status='D044_ACTUAL_ROOT_CLOSED0_USED_SMALL_METADATA_ONLY',source_hashes=hashes,
    root_task_id=proof['binding']['task_id'],root_acceptance_sha256=sha(r/root_path),
    candidate='NO_QUALIFIED_CANDIDATE',long_term_APR='NOT_EVALUABLE',market_payloads_exported=False,
    missing_startup_V1_RUN_BINDING_truthfully_not_exported=True,CONTEXT_original_report_has_no_task_id_not_retrofitted=True)
out=r/'reports/GITHUB_PERPETUAL_HOLD_USED_RECEIPTS_BINDING_20261003_V1.json'
with out.open('x') as f:json.dump(value,f,indent=2);f.write('\n')
print(json.dumps(dict(status=value['status'],sha256=sha(out))))
