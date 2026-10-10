"""Portable single-process resource guard; no changes to frozen economic code."""
import argparse,json,os,resource,signal,subprocess,time
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--report',required=True);p.add_argument('command',nargs=argparse.REMAINDER);a=p.parse_args()
report=Path(a.report)
assert not report.exists() and a.command
assert len(Path('/proc/swaps').read_text().splitlines())==1
cpu=min(os.sched_getaffinity(0))
env=dict(os.environ,COIN_CLOUD_BOUNDED='1',CUDA_VISIBLE_DEVICES='',OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1',MKL_NUM_THREADS='1',POLARS_MAX_THREADS='1',NUMEXPR_NUM_THREADS='1',ARROW_IO_THREADS='1',MALLOC_ARENA_MAX='1',PYTHONPATH='.:src')
def limits():
 os.sched_setaffinity(0,{cpu});resource.setrlimit(resource.RLIMIT_AS,(4000000000,4000000000));resource.setrlimit(resource.RLIMIT_CPU,(1200,1200))
def memory(pid):
 try:
  rows=Path(f'/proc/{pid}/status').read_text().splitlines()
  return sum(int(x.split()[1])*1024 for x in rows if x.startswith('VmRSS:'))
 except FileNotFoundError:return 0
def shared():
 d={x.split(':')[0]:int(x.split()[1])*1024 for x in Path('/proc/meminfo').read_text().splitlines()}
 return d['MemTotal']-d['MemAvailable']
t=time.monotonic();q=subprocess.Popen(a.command,env=env,preexec_fn=limits,start_new_session=True);peak=global_peak=0;stop=None
while q.poll() is None:
 peak=max(peak,memory(q.pid));global_peak=max(global_peak,shared())
 if peak>2000000000:stop='RSS_2GB'
 elif global_peak>8000000000:stop='HOST_USED_8GB'
 elif time.monotonic()-t>1200:stop='WALL_1200S'
 if stop:os.killpg(q.pid,signal.SIGTERM);break
 time.sleep(.25)
code=q.wait(timeout=10)
report.write_text(json.dumps(dict(exit_code=code,stop_reason=stop,elapsed_seconds=time.monotonic()-t,maximum_process_RSS_bytes=peak,maximum_host_used_bytes=global_peak,host_measure='MemTotal-MemAvailable; cgroup unavailable',cpu=cpu,threads=1,GPU=False,swap=False),indent=2)+'\n')
raise SystemExit(code or bool(stop))
