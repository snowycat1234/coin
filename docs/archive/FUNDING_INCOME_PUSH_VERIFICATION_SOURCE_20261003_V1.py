"""Verify this module's actual push and remote main with existing Git transport."""
import hashlib
import json
import re
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

root = Path('/mnt/d/codex/coin')
sha = lambda path: hashlib.sha256(Path(path).read_bytes()).hexdigest()
local = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=root, text=True).strip()
assert local == sys.argv[1]
head_helper = 'docs/archive/FUNDING_INCOME_REMOTE_HEAD_SOURCE_20261003_V1.ps1'
assert (root/head_helper).read_bytes() == (root/'.cache/funding_income_remote_head_20261003_v1.ps1').read_bytes()
reply = subprocess.check_output(['powershell.exe', '-NoProfile', '-File',
    'D:/codex/coin/.cache/funding_income_remote_head_20261003_v1.ps1'], cwd=root, timeout=55).decode().strip()
assert re.fullmatch(r'[0-9a-f]{40}\s+refs/heads/main', reply), 'Exact single remote branch reply required'
remote = reply.split()[0]
assert local == remote
tasks = []
for path in Path('/home/xflops/coin-state/task-progress').glob('task-*.json'):
    value = json.loads(path.read_text())
    if value.get('title') == '资金费收入与双腿成本模块 · GitHub同步':
        tasks.append(dict(path=str(path), sha256=sha(path), task=value))
assert len(tasks) == 1 and tasks[0]['task']['status'] == 'completed' and tasks[0]['task']['exit_code'] == 0
acceptance = 'reports/fast_research/FUNDING_INCOME_ROOT_MODULE_ACCEPTANCE_20261003_V1.json'
receipt = dict(status='ACKNOWLEDGED_PUSH_AND_EXACT_REMOTE_MAIN_VERIFIED', created_utc=datetime.now(UTC).isoformat(),
    local_commit=local, remote_main=remote, module='Fixed whole-period funding coupon and Bybit Non-VIP two-leg cost hurdle',
    actual_commit_host_result=sys.argv[2], actual_commit_exit=0, actual_push_host_result=sys.argv[3], actual_host_exit=0,
    actual_git_exit=0, task_bindings=tasks, force=False, root_acceptance_path=acceptance,
    root_acceptance_sha256=sha(root/acceptance), remote_head_transport_path=head_helper,
    remote_head_transport_sha256=sha(root/head_helper),
    existing_push_transport_path='docs/archive/GITHUB_EXISTING_WINDOWS_TRANSPORT_20261002_V1.ps1',
    scientific_runtime='All Python/test/market computation bounded hpc_linux; Windows existing native HTTPS/Git transport only',
    credential_scope='Existing GitHub authorization, no new credentials or credential values',
    preflight='reports/GITHUB_FUNDING_INCOME_MODULE_STAGED_PREFLIGHT_20261003_V1.json',
    no_global_git_or_proxy_settings_changed=True)
out = root/'reports/GITHUB_FUNDING_INCOME_SYNC_VERIFIED_20261003_V1.json'
with out.open('x') as writer:
    json.dump(receipt, writer, indent=2, ensure_ascii=False)
    writer.write('\n')
print(json.dumps(dict(status=receipt['status'], local=local, remote=remote, sha256=sha(out))))
