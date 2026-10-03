"""Export only accepted D043 task/binding JSON; never copy market payloads."""
import hashlib,json
from pathlib import Path
r=Path('/mnt/d/codex/coin');s=Path('/home/xflops/coin-state/task-progress')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
archive='docs/archive/PERPETUAL_213_USED_RECEIPTS_EXPORTER_SOURCE_20261003_V1.py'
assert Path(__file__).read_bytes()==(r/archive).read_bytes()
root_path='reports/fast_research/PERPETUAL_213_RESEARCH_ROOT_ACCEPTANCE_20261003_V1.json'
proof=json.loads((r/root_path).read_bytes())
assert proof['status']=='PASS_ROOT_D043_213D_CONDITIONAL_DIRECTION_COMPARISON_NOT_NATIVE_OR_LONG_TERM_APR'
plan=json.loads((r/'protocols/PERPETUAL_213_RESEARCH_ROOT_BINDING_20261003_V1.json').read_bytes())
folder=r/'docs/archive/PERPETUAL_213_USED_ACTUAL_METADATA_20261003_V1';assert folder.is_dir()
hashes={}
def export(label,path):
    raw=Path(path).read_bytes();assert len(raw)<2_000_000
    dest=folder/(label+'.json')
    with dest.open('xb') as f:f.write(raw)
    hashes[dest.relative_to(r).as_posix()]=sha(dest)
roles=dict(plan['roles'],ROOT=dict(path=root_path,task_id=proof['binding']['task_id'],exit_code=0))
for label,item in roles.items():
    task_path=s/('task-'+item['task_id']+'.json');task=json.loads(task_path.read_bytes())
    assert task['id']==item['task_id'] and task['exit_code']==item['exit_code']
    assert task['status']==('failed' if item['exit_code']==1 else 'completed')
    export(label+'_TASK',task_path)
    report=json.loads((r/item['path']).read_bytes());run=report.get('run_dir')
    if label=='SOURCE':run='/home/xflops/coin-state/d043-perpetual-213-source-20261003-v1'
    if label=='MARKET':run='/home/xflops/coin-state/d043-perpetual-213-research-20261003-v1'
    if run:export(label+'_RUN_BINDING',Path(run)/'RUN_BINDING.json')
for name in (archive,root_path,'reports/GITHUB_PERPETUAL_213_RESEARCH_SOURCE_BINDING_20261003_V1.json',
    'protocols/PERPETUAL_213_RESEARCH_ROOT_BINDING_20261003_V1.json','docs/PERPETUAL_213_COMPARISON_20261003.md',
    'docs/OPEN_SOURCE_REGISTRY.md','docs/archive/OPEN_SOURCE_REGISTRY_PRE_PERPETUAL_213_20261003_V1.md',
    'docs/archive/PERPETUAL_213_PUSH_VERIFICATION_SOURCE_20261003_V1.py'):
    hashes[name]=sha(r/name)
value=dict(status='D043_ACTUAL_ROOT_CLOSED0_USED_METADATA_ONLY',source_hashes=hashes,
    root_task_id=proof['binding']['task_id'],root_acceptance_sha256=sha(r/root_path),
    candidate='NO_QUALIFIED_CANDIDATE',long_term_APR='NOT_EVALUABLE',market_payloads_exported=False)
out=r/'reports/GITHUB_PERPETUAL_213_USED_RECEIPTS_BINDING_20261003_V1.json'
with out.open('x') as f:json.dump(value,f,indent=2);f.write('\n')
print(json.dumps(dict(status=value['status'],sha256=sha(out))))
