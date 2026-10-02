import hashlib
import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path

root = Path('/mnt/d/codex/coin')
sha = lambda path: hashlib.sha256(Path(path).read_bytes()).hexdigest()
local = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=root, text=True).strip()
remote = json.loads(subprocess.check_output([str(root / '.tools/bin/gh'), 'api',
    'repos/snowycat1234/coin/git/ref/heads/main'], cwd=root, timeout=45))['object']['sha']
assert local == remote == '1519a61b1398bba0f6a4f2793f50a39aae4126ac'
titles = {
    '公开2h共同收益模块 · GitHub推送', '公开2h模块 · 网络超时后同步重试',
    '公开2h模块 · 复用本机网络完成同步', '公开2h模块 · 已核Git路径的本机同步',
    '公开2h模块 · 修正凭证路径后的本机同步', '公开2h模块 · 沿用既有认证和本机网络同步',
}
tasks = []
for path in Path('/home/xflops/coin-state/task-progress').glob('*.json'):
    value = json.loads(path.read_text())
    if value.get('title') in titles:
        tasks.append(dict(path=str(path), sha256=sha(path), task=value))
success = [item for item in tasks if item['task']['title'] == '公开2h模块 · 沿用既有认证和本机网络同步']
assert len(success) == 1 and success[0]['task']['status'] == 'completed' and success[0]['task']['exit_code'] == 0
tasks.sort(key=lambda value: value['task']['started_at'])
receipt = dict(status='ACKNOWLEDGED_PUSH_AND_EXACT_REMOTE_MAIN_VERIFIED', created_utc=datetime.now(UTC).isoformat(),
    local_commit=local, remote_main=remote, module='Fixed public2h122day shared economic comparison',
    actual_push_session=91445, actual_host_exit=0, actual_git_exit=0, task_bindings=tasks,
    force=False, credential_scope='Existing GitHub CLI auth via bounded WSL credential helper; no credential values logged or new credentials',
    transport='Existing Windows Git and existing system proxy reused for Git sync; WSL main-domain TCP timed out while API worked',
    transport_source_path='.cache/push_existing_windows_transport_20261002_v1.ps1',
    transport_source_sha256=sha(root / '.cache/push_existing_windows_transport_20261002_v1.ps1'),
    scientific_runtime='All Python/test/market work remains bounded hpc_linux; no model or market reruns for sync',
    prior_failures_preserved=True, no_global_git_or_proxy_settings_changed=True,
    preflight='reports/GITHUB_PUBLIC_DONCHIAN_2H_MODULE_STAGED_PREFLIGHT_20261002_V1.json')
out = root / 'reports/GITHUB_PUBLIC_DONCHIAN_2H_SYNC_VERIFIED_20261002_V1.json'
with out.open('x') as writer:
    json.dump(receipt, writer, indent=2, ensure_ascii=False)
    writer.write('\n')
print(json.dumps(dict(status=receipt['status'], local=local, remote=remote, sha256=sha(out))))
