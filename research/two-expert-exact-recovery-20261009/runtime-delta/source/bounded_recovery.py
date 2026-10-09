"""One-CPU resource launcher for recovery computations; no financial code."""
from pathlib import Path
import argparse,json,os,resource,signal,subprocess,time

def rss(pid):
    queue=[pid];total=0
    while queue:
        p=queue.pop()
        try:
            status=Path(f'/proc/{p}/status').read_text()
            total+=next((int(x.split()[1])*1024 for x in status.splitlines() if x.startswith('VmRSS:')),0)
            queue.extend(map(int,Path(f'/proc/{p}/task/{p}/children').read_text().split()))
        except (FileNotFoundError,ProcessLookupError):pass
    return total

def main():
    p=argparse.ArgumentParser();p.add_argument('--report',type=Path,required=True)
    p.add_argument('--seconds',type=int,default=120);p.add_argument('--memory',type=int,default=1_000_000_000)
    p.add_argument('command',nargs=argparse.REMAINDER);a=p.parse_args()
    if not a.command or not 1<=a.seconds<=120 or not 1<=a.memory<=1_000_000_000:
        raise ValueError('One fixed bounded recovery computation')
    if a.report.exists():raise FileExistsError('Existing resource report')
    if len(Path('/proc/swaps').read_text().splitlines())!=1:raise RuntimeError('Swap must be absent')
    allowed=os.sched_getaffinity(0);cpu=min(allowed)
    env=dict(os.environ,COIN_CLOUD_BOUNDED='1',CUDA_VISIBLE_DEVICES='',
        OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1',MKL_NUM_THREADS='1',POLARS_MAX_THREADS='1')
    def limits():
        os.sched_setaffinity(0,{cpu})
        resource.setrlimit(resource.RLIMIT_AS,(a.memory,a.memory))
        resource.setrlimit(resource.RLIMIT_CPU,(a.seconds,a.seconds))
    began=time.monotonic();peak=0;stop=None
    child=subprocess.Popen(a.command,env=env,preexec_fn=limits,start_new_session=True)
    try:
        while child.poll() is None:
            peak=max(peak,rss(child.pid))
            if time.monotonic()-began>a.seconds:stop='WALL_TIME_LIMIT'
            elif peak>a.memory:stop='AGGREGATE_RSS_LIMIT'
            if stop:
                os.killpg(child.pid,signal.SIGTERM)
                try:child.wait(timeout=2)
                except subprocess.TimeoutExpired:os.killpg(child.pid,signal.SIGKILL)
                break
            time.sleep(.25)
        code=child.wait()
    finally:
        r=dict(exit_code=child.returncode,stop_reason=stop,elapsed_seconds=time.monotonic()-began,
            maximum_sampled_descendant_RSS_bytes=peak,RSS_sampling_seconds=.25,
            per_process_address_limit_bytes=a.memory,aggregate_RSS_stop_bytes=a.memory,
            single_CPU_affinity_enforced=True,cpu_index=cpu,resource_only_launcher=True)
        a.report.parent.mkdir(parents=True,exist_ok=True)
        with a.report.open('x') as f:json.dump(r,f,indent=2);f.write('\n')
    if code:raise SystemExit(code)
    if stop:raise SystemExit(1)

if __name__=='__main__':main()
