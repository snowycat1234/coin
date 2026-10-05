"""Sequential bounded task stages, actual exits and monotonic timings."""
import argparse,hashlib,json,os,subprocess,time
from datetime import UTC,datetime
from pathlib import Path
from quant.paths import ROOT,STATE
from scripts.task_progress_api import Progress

p=argparse.ArgumentParser();p.add_argument('--config',required=True);p.add_argument('--output',required=True);a=p.parse_args()
config=Path(a.config);steps=json.loads(config.read_bytes())['steps'];out=Path(a.output)
assert steps and not out.exists() and (out.resolve().is_relative_to(STATE) or out.resolve().is_relative_to(ROOT/'reports'))
assert os.environ.get('COIN_TASK_ID');phase=Progress();began=time.monotonic_ns();records=[];code=0
try:
    for i,step in enumerate(steps):
        assert isinstance(step['argv'],list) and step['argv'] and all(isinstance(x,str) for x in step['argv'])
        phase.update(step['title'],i,len(steps),'阶段')
        start=time.monotonic_ns();utc=datetime.now(UTC).isoformat()
        code=subprocess.run(step['argv'],cwd=ROOT,shell=False).returncode
        end=time.monotonic_ns();records.append(dict(title=step['title'],argv=step['argv'],started_utc=utc,
            start_monotonic_ns=start,end_monotonic_ns=end,wall_seconds=(end-start)/1e9,exit_code=code))
        if code:break
    phase.update('完成' if code==0 else '失败，后续阶段未运行',len(records),len(steps),'阶段')
finally:
    phase.stop.set();phase.thread.join(timeout=3)
    with out.open('x') as f:json.dump(dict(status='COMPLETE' if code==0 and len(records)==len(steps) else 'FAILED',
        task_id=os.environ['COIN_TASK_ID'],config_sha256=hashlib.sha256(config.read_bytes()).hexdigest(),
        runner_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),stages=records,
        start_monotonic_ns=began,end_monotonic_ns=time.monotonic_ns(),
        timing_scope='This command only; prior conversation/context/model timing UNKNOWN. Sequential stages are disjoint, no child double count.'),f,indent=2)
raise SystemExit(code)
