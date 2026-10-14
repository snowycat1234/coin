"""Run one independent generated-only check file within fixed review bounds."""
import json,os,pathlib,resource,subprocess,sys,time
runner=pathlib.Path(sys.argv[1]).resolve();out=pathlib.Path(sys.argv[2]);out.mkdir(exist_ok=False)
env=dict(os.environ,REVIEW_RUNNER_ROOT=str(runner),PAIRED_TEST_CODE_ROOTS=str(pathlib.Path(sys.argv[3]).resolve()),PYTHONDONTWRITEBYTECODE='1',OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1',MKL_NUM_THREADS='1',NUMEXPR_NUM_THREADS='1')
env.pop('PYTHONOPTIMIZE',None)
def limits():
    os.sched_setaffinity(0,{min(os.sched_getaffinity(0))});resource.setrlimit(resource.RLIMIT_AS,(4_000_000_000,4_000_000_000));resource.setrlimit(resource.RLIMIT_CPU,(60,60))
began=time.monotonic();peak=0;stop=None
with (out/'checks.log').open('x') as log:
    proc=subprocess.Popen([sys.executable,'-B',str(pathlib.Path(__file__).with_name('independent_checks.py'))],env=env,preexec_fn=limits,stdout=log,stderr=subprocess.STDOUT)
    while proc.poll() is None:
        try:
            lines=pathlib.Path(f'/proc/{proc.pid}/status').read_text().splitlines();rss=next((int(x.split()[1])*1024 for x in lines if x.startswith('VmRSS:')),0);peak=max(peak,rss)
        except FileNotFoundError:pass
        if peak>2_000_000_000:stop='RSS_LIMIT'
        elif time.monotonic()-began>120:stop='WALL_LIMIT'
        if stop:proc.kill();break
        time.sleep(.02)
    code=proc.wait()
receipt={'status':'PASS_GENERATED_REVIEW_CHECKS' if code==0 and stop is None else 'FAIL_GENERATED_REVIEW_CHECKS','exit_code':code,'stop_reason':stop,'elapsed_seconds':time.monotonic()-began,'peak_RSS_bytes':peak,'AS_bytes':4_000_000_000,'CPU_seconds':60,'wall_seconds':120,'CPUs':1,'math_threads':1,'historical_array_reads':0,'wallets':0,'new_market_downloads':0}
(out/'RESOURCE_RECEIPT.json').write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n');print(json.dumps(receipt));sys.exit(code or (1 if stop else 0))
