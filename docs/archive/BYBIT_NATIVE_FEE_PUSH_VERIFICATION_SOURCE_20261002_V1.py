import hashlib, json, subprocess, sys
from datetime import UTC, datetime
from pathlib import Path
root=Path('/mnt/d/codex/coin')
sha=lambda path:hashlib.sha256(Path(path).read_bytes()).hexdigest()
local=subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip()
assert local == sys.argv[1]
remote=json.loads(subprocess.check_output([str(root/'.tools/bin/gh'),'api',
    'repos/snowycat1234/coin/git/ref/heads/main'],cwd=root,timeout=45))['object']['sha']
assert local == remote
title='Bybit普通现货费用资产模块 · GitHub同步'
tasks=[]
for path in Path('/home/xflops/coin-state/task-progress').glob('task-*.json'):
    v=json.loads(path.read_text())
    if v.get('title') == title:tasks.append(dict(path=str(path),sha256=sha(path),task=v))
assert len(tasks)==1 and tasks[0]['task']['status']=='completed' and tasks[0]['task']['exit_code']==0
receipt=dict(status='ACKNOWLEDGED_PUSH_AND_EXACT_REMOTE_MAIN_VERIFIED',created_utc=datetime.now(UTC).isoformat(),
    local_commit=local,remote_main=remote,module='Bybit ordinarySpot received-asset compatibility and six fixed2h proxy accounts',
    actual_commit_host_result=sys.argv[2],actual_commit_exit=0,actual_push_host_result=sys.argv[3],actual_host_exit=0,actual_git_exit=0,
    task_bindings=tasks,force=False,
    existing_transport_archive='docs/archive/GITHUB_EXISTING_WINDOWS_TRANSPORT_20261002_V1.ps1',
    transport_source_sha256=sha(root/'docs/archive/GITHUB_EXISTING_WINDOWS_TRANSPORT_20261002_V1.ps1'),
    scientific_runtime='All Python/test/market work bounded hpc_linux; existingWindowsGit transport only, no newC caches',
    credential_scope='Existing boundedWSL GitHubCLI authorization only; no new credentials or credential values',
    root_acceptance_path='reports/fast_research/BYBIT_SPOT_NATIVE_FEE_ROOT_MODULE_ACCEPTANCE_20261002_V1.json',
    root_acceptance_sha256=sha(root/'reports/fast_research/BYBIT_SPOT_NATIVE_FEE_ROOT_MODULE_ACCEPTANCE_20261002_V1.json'),
    preflight='reports/GITHUB_BYBIT_NATIVE_FEE_MODULE_STAGED_PREFLIGHT_20261002_V1.json',
    no_global_git_or_proxy_settings_changed=True)
out=root/'reports/GITHUB_BYBIT_NATIVE_FEE_SYNC_VERIFIED_20261002_V1.json'
with out.open('x') as f:json.dump(receipt,f,indent=2,ensure_ascii=False);f.write('\n')
print(json.dumps(dict(status=receipt['status'],local=local,remote=remote,sha256=sha(out))))
