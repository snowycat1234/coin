import hashlib,json,os
from pathlib import Path
root=Path('/mnt/d/codex/coin');state=Path('/home/xflops/coin-state')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(Path(p).read_bytes())
archive='docs/archive/PERPETUAL_HISTORY_GAP_USED_RECEIPTS_EXPORTER_SOURCE_20261003_V1.py'
assert Path(__file__).read_bytes()==(root/archive).read_bytes()
proof=read(root/'reports/fast_research/PERPETUAL_HISTORY_GAP_ROOT_ACCEPTANCE_20261003_V1.json')
assert proof['status']=='PASS_ROOT_D042_OFFICIAL_MONTH_AND_DAY_GAP_DIAGNOSIS_SOURCE_REJECTED_NO_ECONOMICS'
task_path=state/'task-progress'/('task-'+proof['binding']['task_id']+'.json');t=read(task_path)
assert t['status']=='completed' and t['exit_code']==0
folder=root/'docs/archive/PERPETUAL_HISTORY_GAP_USED_ACTUAL_METADATA_20261003_V1'
hashes={}
for label,p in {'ROOT_TASK':task_path,'ROOT_RUN_BINDING':Path(proof['run_dir'])/'RUN_BINDING.json'}.items():
    target=folder/(label+'.json');target.write_bytes(p.read_bytes());hashes[target.relative_to(root).as_posix()]=sha(target)
for name in (archive,'docs/OPEN_SOURCE_REGISTRY.md','docs/archive/PERPETUAL_HISTORY_GAP_SCAN_PUBLISHER_SOURCE_20261003_V1.py',
    'reports/fast_research/PERPETUAL_HISTORY_MARK_GAP_DIAGNOSTIC_ACTUAL_EXIT_20261003_V1.json',
    'docs/archive/PERPETUAL_HISTORY_MARK_GAP_DIAGNOSTIC_COMPLETED_TASK_20261003_V1.json',
    'docs/archive/PERPETUAL_HISTORY_MARK_GAP_DIAGNOSTIC_RUN_BINDING_20261003_V1.json',
    'reports/GITHUB_PERPETUAL_PUBLIC_BENCHMARK_SYNC_VERIFIED_20261003_V1.json'):
    hashes[name]=sha(root/name)
out=root/'reports/GITHUB_PERPETUAL_HISTORY_GAP_USED_RECEIPTS_BINDING_20261003_V1.json'
with out.open('x') as f:json.dump(dict(status='D042_ROOT_ACTUAL_CLOSED0_METADATA_ONLY',source_hashes=hashes,root_task=t,
    root_acceptance_sha256=sha(root/'reports/fast_research/PERPETUAL_HISTORY_GAP_ROOT_ACCEPTANCE_20261003_V1.json'),
    market_source_accepted=False,source_failure_preserved=True),f,indent=2);f.write('\n')
print(json.dumps(dict(status='D042_ROOT_ACTUAL_CLOSED0_METADATA_ONLY',sha256=sha(out))))
