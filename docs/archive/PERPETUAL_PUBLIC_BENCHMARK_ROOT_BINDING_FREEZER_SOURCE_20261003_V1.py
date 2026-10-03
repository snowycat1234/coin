"""Freeze actual closed role receipts and small used metadata; never market IO."""
import hashlib,json,os
from datetime import UTC,datetime
from pathlib import Path
R=Path('/mnt/d/codex/coin');S=Path('/home/xflops/coin-state')
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
read=lambda p:json.loads(Path(p).read_bytes())
def copy(source,target):
    assert source.is_file() and source.stat().st_size<2_000_000
    with target.open('xb') as f:f.write(source.read_bytes())
    assert sha(target)==sha(source)
plan=read(R/'.cache/d041_public_benchmark_root_binding_draft_20261003_v1.json')
assert not plan['ready_to_execute']
plan['protocol']=dict(path='protocols/PERPETUAL_PUBLIC_BENCHMARK_20261003_V1.json',sha256=sha(R/'protocols/PERPETUAL_PUBLIC_BENCHMARK_20261003_V1.json'))
plan['roles']['MARKET']['path']='reports/fast_research/PERPETUAL_PUBLIC_BENCHMARK_ACTUAL_20261003_V1.json'
plan['roles']['INDEPENDENT']['path']='reports/fast_research/PERPETUAL_PUBLIC_BENCHMARK_INDEPENDENT_AUDIT_20261003_V1.json'
folder=R/'docs/archive/PERPETUAL_PUBLIC_BENCHMARK_USED_ACTUAL_METADATA_20261003_V1';folder.mkdir()
extra=plan['additional_project_files']
for role,item in plan['roles'].items():
    report=read(R/item['path']);identity=report['binding']['task_id'];digest=sha(R/item['path'])
    assert report['status']==item['required_status']
    if item['sha256']:assert item['sha256']==digest
    if item['task_id']:assert item['task_id']==identity
    task_path=S/'task-progress'/('task-'+identity+'.json');task=read(task_path)
    assert task['id']==identity and task['status']=='completed' and task['exit_code']==0
    item.update(sha256=digest,task_id=identity,actual_status='completed',actual_exit_code=0)
    work=Path(report.get('run_dir',report['binding'].get('spec',{}).get('run_dir','')))
    names=[('TASK.json',task_path),('RUN_BINDING.json',work/'RUN_BINDING.json')]
    if (work/'ACTUAL_BINDING.json').is_file():names.append(('ACTUAL_BINDING.json',work/'ACTUAL_BINDING.json'))
    for name,source in names:
        target=folder/(role+'_'+name);copy(source,target);extra[str(target.relative_to(R))]=sha(target)
test=read(R/plan['roles']['NEW_TESTS']['path']);work=Path(test['run_dir'])
copy(work/'junit.xml',folder/'NEW_TESTS_JUNIT.xml');extra[str((folder/'NEW_TESTS_JUNIT.xml').relative_to(R))]=sha(folder/'NEW_TESTS_JUNIT.xml')
for name in ('donchian_perpetual_target_evidence.json','public_perpetual_controller_evidence.json'):
    matches=list((work/'pytest').rglob(name));assert len(matches)==1
    target=folder/name;copy(matches[0],target);extra[str(target.relative_to(R))]=sha(target)
for source,name in [(Path(__file__),'PERPETUAL_PUBLIC_BENCHMARK_ROOT_BINDING_FREEZER_SOURCE_20261003_V1.py'),
    (R/'.cache/d041_freeze_metadata.py','PERPETUAL_PUBLIC_BENCHMARK_METADATA_FREEZER_SOURCE_20261003_V1.py'),
    (R/'.cache/d041_register_audit.py','PERPETUAL_PUBLIC_BENCHMARK_AUDIT_REGISTRATION_SOURCE_20261003_V1.py')]:
    target=R/'docs/archive'/name;copy(source,target);extra[str(target.relative_to(R))]=sha(target)
for name in ('PERPETUAL_2H_WARMUP_SOURCE_AST_PREFLIGHT_SOURCE_20261003_V1.py','PERPETUAL_2H_WARMUP_SOURCE_AST_PREFLIGHT_TASK_20261003_V1.json',
    'PERPETUAL_2H_WARMUP_SCAN_PUBLISHER_SOURCE_20261003_V1.py','PERPETUAL_PUBLIC_BENCHMARK_PUSH_VERIFICATION_SOURCE_20261003_V1.py'):
    path=R/'docs/archive'/name;extra[str(path.relative_to(R))]=sha(path)
for name in ('reports/GITHUB_PERPETUAL_DIRECTIONAL_SYNC_VERIFIED_20261003_V1.json',
    'protocols/PERPETUAL_2H_WARMUP_INDEPENDENT_BINDING_20261003_V1.json',
    'protocols/PERPETUAL_PUBLIC_BENCHMARK_INDEPENDENT_BINDING_20261003_V1.json',
    'reports/fast_research/PERPETUAL_2H_WARMUP_SOURCE_AST_PREFLIGHT_20261003_V1.json'):
    extra[name]=sha(R/name)
assert sha(R/'scripts/investment/accept_perpetual_public_benchmark.py')==plan['helper_sha256']==sha(R/plan['future_helper_archive'])
plan.update(ready_to_execute=True,created_utc=datetime.now(UTC).isoformat(),freezer_task_id=os.environ['COIN_TASK_ID'],
    qualification='FROZEN_TRUE_CLOSED0_ROLE_BINDINGS_BEFORE_METADATA_ROOT_CLOSURE')
out=R/'protocols/PERPETUAL_PUBLIC_BENCHMARK_ROOT_BINDING_20261003_V1.json'
with out.open('x') as f:json.dump(plan,f,ensure_ascii=False,indent=2);f.write('\n')
print(json.dumps(dict(path=str(out),sha256=sha(out),actual_roles=5,market_arrays_read=False)))
