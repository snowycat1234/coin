import hashlib, json, subprocess
from datetime import UTC, datetime
from pathlib import Path
root = Path('/mnt/d/codex/coin')
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
local = subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip()
remote = json.loads(subprocess.check_output([str(root/'.tools/bin/gh'),'api',
    'repos/snowycat1234/coin/git/ref/heads/main'],cwd=root,timeout=45))['object']['sha']
assert local == remote == '73546402fa45970044e6e091afb58cbde6700bc4'
titles = ['GitHub非重叠诊断模块推送','GitHub机制模块推送第二次尝试','GitHub机制模块 · 网络恢复后推送']
records = []
for title in titles:
    found = [p for p in Path('/home/xflops/coin-state/task-progress').glob('*.json') if json.loads(p.read_text()).get('title') == title]
    assert len(found) == 1
    records.append(dict(path=str(found[0]),sha256=sha(found[0]),task=json.loads(found[0].read_text())))
assert [r['task']['exit_code'] for r in records] == [128,124,0]
receipt = dict(status='ACKNOWLEDGED_PUSH_AND_EXACT_REMOTE_MAIN_VERIFIED',created_utc=datetime.now(UTC).isoformat(),
    module='V8 nonoverlap diagnostic and official input metadata feasibility',local_commit=local,remote_main=remote,
    actual_push_session=84853,actual_host_exit=0,actual_git_exit=0,force=False,
    prior_failure_sessions=[18880,53102],preserved_task_records=records,
    preflight='reports/fast_research/V8_MECHANISM_ROUTE_GIT_PREFLIGHT_20261002_V1.json')
out = root/'reports/GITHUB_V8_MECHANISM_ROUTE_SYNC_VERIFIED_20261002_V1.json'
with out.open('x') as f: json.dump(receipt,f,indent=2,ensure_ascii=False); f.write('\n')
print(json.dumps(dict(status=receipt['status'],local=local,remote=remote,sha256=sha(out))))
