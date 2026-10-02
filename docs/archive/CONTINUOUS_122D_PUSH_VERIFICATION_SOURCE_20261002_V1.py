import hashlib,json,subprocess
from datetime import UTC,datetime
from pathlib import Path
root=Path('/mnt/d/codex/coin')
local=subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip()
remote=json.loads(subprocess.check_output([str(root/'.tools/bin/gh'),'api','repos/snowycat1234/coin/git/ref/heads/main'],cwd=root,timeout=45))['object']['sha']
assert local==remote=='bcd35b0723933b4f3727d19c3fb18b98911290fe'
tasks=[]
for p in Path('/home/xflops/coin-state/task-progress').glob('*.json'):
    value=json.loads(p.read_text())
    if value.get('title')=='连续122日净收益版本 · GitHub推送':
        assert value['status']=='completed' and value['exit_code']==0
        tasks.append(dict(path=str(p),sha256=hashlib.sha256(p.read_bytes()).hexdigest(),task=value))
assert len(tasks)==1
value=dict(status='ACKNOWLEDGED_PUSH_AND_EXACT_REMOTE_MAIN_VERIFIED',created_utc=datetime.now(UTC).isoformat(),
    module='Continuous122day fixed strategy economics; profitable-main assumption rejected',local_commit=local,remote_main=remote,
    actual_push_session=97709,actual_host_exit=0,actual_git_exit=0,force=False,task_bindings=tasks,
    preflight='reports/GITHUB_CONTINUOUS_122D_MODULE_STAGED_PREFLIGHT_20261002_V1.json',no_research_rerun=True)
out=root/'reports/GITHUB_CONTINUOUS_122D_SYNC_VERIFIED_20261002_V1.json'
with out.open('x') as f:json.dump(value,f,indent=2,ensure_ascii=False);f.write('\n')
print(json.dumps(dict(status=value['status'],local=local,remote=remote,sha256=hashlib.sha256(out.read_bytes()).hexdigest())))
