"""Verify an actual accepted-module push; no market IO or credential output."""
from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

root=Path('/mnt/d/codex/coin')
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
archive='docs/archive/CONDITIONAL_CARRY_PAIR_TRIM_PUSH_VERIFICATION_SOURCE_20261003_V1.py'
assert Path(__file__).read_bytes()==(root/archive).read_bytes()
local=subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip()
assert local==sys.argv[1]
assert subprocess.check_output(['git','remote','get-url','origin'],cwd=root,text=True).strip()=='https://github.com/snowycat1234/coin.git'
helper='docs/archive/FUNDING_INCOME_REMOTE_HEAD_SOURCE_20261003_V1.ps1'
assert (root/helper).read_bytes()==(root/'.cache/funding_income_remote_head_20261003_v1.ps1').read_bytes()
reply=subprocess.check_output(['powershell.exe','-NoProfile','-File','D:/codex/coin/.cache/funding_income_remote_head_20261003_v1.ps1'],cwd=root,timeout=55).decode().strip()
assert re.fullmatch(r'[0-9a-f]{40}\s+refs/heads/main',reply) and reply.split()[0]==local
tasks=[]
for p in Path('/home/xflops/coin-state/task-progress').glob('task-*.json'):
    v=json.loads(p.read_bytes())
    if v.get('title')=='减仓机制对照 · GitHub同步':
        tasks.append({'path':str(p),'sha256':sha(p),'task':v})
assert len(tasks)==1 and tasks[0]['task']['status']=='completed' and tasks[0]['task']['exit_code']==0
acceptance='reports/fast_research/CONDITIONAL_CARRY_PAIR_TRIM_ROOT_ACCEPTANCE_20261003_V1.json'
value=dict(status='ACKNOWLEDGED_PUSH_AND_EXACT_REMOTE_MAIN_VERIFIED',created_utc=datetime.now(UTC).isoformat(),
    local_commit=local,remote_main=reply.split()[0],module='Fixed122d conditional matched-pair reduced-only carry mechanism',
    actual_commit_host_result=sys.argv[2],actual_commit_exit=0,actual_push_host_result=sys.argv[3],actual_git_exit=0,
    task_bindings=tasks,root_acceptance_path=acceptance,root_acceptance_sha256=sha(root/acceptance),
    remote_head_transport_path=helper,remote_head_transport_sha256=sha(root/helper),force=False,
    existing_push_transport_path='docs/archive/GITHUB_EXISTING_WINDOWS_TRANSPORT_20261002_V1.ps1',
    preflight='reports/GITHUB_CONDITIONAL_CARRY_PAIR_TRIM_STAGED_PREFLIGHT_20261003_V1.json',
    no_global_git_or_proxy_settings_changed=True,credential_scope='Existing authorization; no new credentials')
out=root/'reports/GITHUB_CONDITIONAL_CARRY_PAIR_TRIM_SYNC_VERIFIED_20261003_V1.json'
with out.open('x') as w:
    json.dump(value,w,indent=2,ensure_ascii=False);w.write('\n')
print(json.dumps({'status':value['status'],'local':local,'remote':reply.split()[0],'sha256':sha(out)}))
