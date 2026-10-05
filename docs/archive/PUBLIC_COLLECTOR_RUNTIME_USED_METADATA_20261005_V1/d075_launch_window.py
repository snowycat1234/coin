"""Restart only the existing read-only local progress window, under its guard."""
import json,os,subprocess,time
from pathlib import Path
import urllib.request
root=Path('/mnt/d/codex/coin');state=Path('/home/xflops/coin-state')
out=state/'d075-runtime-restoration-20261005-v1';out.mkdir(exist_ok=True)
try:
 with urllib.request.urlopen('http://127.0.0.1:8765/api/status',timeout=2) as r:
  status=json.load(r)
 print(json.dumps(dict(already_live=True,errors=status['errors'])));raise SystemExit
except OSError:pass
cmd=['bash',str(root/'scripts/bounded.sh'),'/usr/bin/python3','-B',str(root/'.cache/serve_task_progress_v2.py')]
with (out/'window.stdout.log').open('xb') as stdout,(out/'window.stderr.log').open('xb') as stderr:
 process=subprocess.Popen(cmd,cwd=root,stdin=subprocess.DEVNULL,stdout=stdout,stderr=stderr,start_new_session=True)
with (out/'WINDOW_LAUNCH.json').open('x') as f:json.dump(dict(task_id=os.environ['COIN_TASK_ID'],command=cmd,wrapper_pid=process.pid,launch_epoch=time.time(),old_source_unmodified=True),f,indent=2)
print(json.dumps(dict(launched=True,wrapper_pid=process.pid,run_dir=str(out))))
