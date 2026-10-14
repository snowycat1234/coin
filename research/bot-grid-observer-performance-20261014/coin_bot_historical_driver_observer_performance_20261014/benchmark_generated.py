"""Fixed generated1/7/31-day scaling, serial arms and original resource helpers."""
from pathlib import Path
import argparse,fcntl,json,os,resource,subprocess,sys,time
import bindings as B
PORTABLE=B.ROOT/'coin_bot_native_adapter_portable_synthetic_20261014'
PORTABLE_FREEZE='732c04cd365c06b487ccbaff1c5916e23e73bb6d9718c663450d0f1603f0a6f0'

def simulated(days,arm):
 import numpy as np
 B.check(PORTABLE/'PORTABLE_FINAL_MANIFEST.json',PORTABLE_FREEZE)
 sys.path.insert(0,str(PORTABLE))
 from generated_fixtures import make,START
 from native_adapter import GridNativeAdapter,PORT,ACCOUNT,H,D,S,DAY,M
 window,_,closes,cov,_=make('RANGE');end=START+days*DAY;clock=np.arange(START,end,DAY,dtype=np.int64)
 window['end']=end
 window['daily']=PORT.native.pl.DataFrame([dict(symbol=s,close_us=int(t),close=100.) for t in clock for s in S])
 window['market']={s:{k:np.tile(v,days) for k,v in fields.items()} for s,fields in window['market'].items()}
 one_events=window['events'];window['events']=[dict(e,event_us=e['event_us']+i*DAY) for i in range(days) for e in one_events]
 closes={int(t):[H.CompletedClose(int(t)-(29-i)*DAY,D(90 if i%2==0 else 110),int(t)-(29-i)*DAY) for i in range(30)] for t in clock}
 cov={int(t):np.eye(5)*.04 for t in clock};weights=np.tile(np.array([.2,.05,0.,0.,-.1]),(days,1))
 def factory(daily,clocks,mode):
  if mode!='LONG_SHORT' or not np.array_equal(clocks,clock):raise ValueError('FIXED_GENERATED_BENCHMARK_CLOCK')
  return PORT.native.pl.DataFrame([dict(available_us=int(t),symbol=s,target_weight=float(weights[i,j])) for i,t in enumerate(clock) for j,s in enumerate(S)]),dict(source='FIXED_GENERATED_RANGE_SCALING_ONLY',days=days)
 return GridNativeAdapter(window,'LONG_SHORT',PORT.native.COSTS[0],PORT.native.UNITS[0],target_factory=factory,account_factory=ACCOUNT,arm={'CSH':'CONTROL','CASH':'CASH','GRID':'GRID'}[arm],daily_closes=closes,covariance=cov,initial_observations={START:H.CompletedMinute(START,D(100),START)})

def worker(args):
 import numpy as np
 # The reviewed portable code gate already rejects any array carrier. This
 # extra guard also rejects an accidental future numeric archive call.
 np.load=lambda *a,**k: (_ for _ in ()).throw(ValueError('NO_ARRAY_READ_IN_GENERATED_BENCHMARK'))
 from driver import run_calendar
 start=time.monotonic();sim=simulated(args.days,args.arm)
 result=run_calendar(sim,args.output,dict(fixture='FIXED_GENERATED_RANGE_SCALING_ONLY',days=args.days,arm=args.arm,portable_freeze_SHA256=PORTABLE_FREEZE),time.monotonic()+150,'GENERATED_ONLY_NO_MARKET_PERFORMANCE')
 result.update(days=args.days,arm=args.arm,wall_seconds=time.monotonic()-start,peak_RSS_KiB=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
 print(json.dumps(result));return 0

def benchmark(args):
 d=B.load_controller();roots=B.read(args.resource_roots);guard=d.original_resource_guard(roots)
 out=Path(args.output).resolve()
 if out.exists():raise ValueError('FRESH_BENCHMARK_OUTPUT_REQUIRED')
 # The exact historical controller's admission/external reservations, host
 # lock, child limits, process RSS and stop helper are reused for toy scaling.
 admission=d.resource_admission(roots,out)
 out.mkdir(parents=True);runs=[]
 with Path('/tmp/coin_offline_financial_controller.lock').open('a') as lock:
  try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
  except BlockingIOError:raise ValueError('ORIGINAL_FINANCIAL_CONTROLLER_LOCKED')
  for days in (1,7,31):
   for arm in ('CSH','CASH','GRID'):
    admission=d.resource_admission(roots,out)
    target=out/f'GENERATED_{days}D_{arm}';cmd=[sys.executable,'-B',str(B.HERE/'run_verified.py'),'--preparation-manifest-sha',B.sha(B.HERE/'PREPARATION_MANIFEST.json'),'benchmark','--worker','--days',str(days),'--arm',arm,'--output',str(target)]
    cmd+=sum((['--runtime-site',p] for p in args.runtime_site),[])
    def limits():
     guard.child_limits(admission['allowed_cpus'][0]);resource.setrlimit(resource.RLIMIT_CPU,(150,150))
    env=dict(os.environ,BOT_NATIVE_RUNTIME_SITES=json.dumps(args.runtime_site),PYTHONDONTWRITEBYTECODE='1',OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1',POLARS_MAX_THREADS='1')
    env.pop('PYTHONOPTIMIZE',None);env['PYTHONPATH']=os.pathsep.join(args.runtime_site)
    start=time.monotonic();proc=subprocess.Popen(cmd,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,start_new_session=True,preexec_fn=limits,env=env)
    peak=0;stop=None
    while proc.poll() is None:
     peak=max(peak,guard.process_rss(proc.pid))
     if time.monotonic()-start>180:stop='BOUNDED_GENERATED_WALL180'
     elif peak>guard.WORKER_RSS_LIMIT:stop='ORIGINAL_RSS2GB'
     elif target.exists() and sum(p.stat().st_size for p in target.rglob('*') if p.is_file())>guard.CASE_LIMIT:stop='ORIGINAL_OUTPUT250MB'
     if stop:guard.terminate(proc);break
     time.sleep(.1)
    text=proc.communicate()[0];(out/f'{days}D_{arm}.txt').write_text(text)
    record=dict(days=days,arm=arm,exit_code=proc.returncode,stop=stop,wall_seconds=time.monotonic()-start,peak_descendant_RSS_bytes=peak)
    if proc.returncode==0:record['worker_report']=json.loads(text.strip().splitlines()[-1])
    runs.append(record)
    if proc.returncode or stop:break
   if runs[-1]['exit_code'] or runs[-1]['stop']:break
 result=dict(schema='GENERATED_NATIVE_DRIVER_SCALING_V1',status='PASS_GENERATED_SCALING_ONLY' if len(runs)==9 and all(r['exit_code']==0 and r['stop'] is None for r in runs) else 'BLOCKED_OR_FAILED_GENERATED_SCALING',runs=runs,resource_helpers='UNCHANGED_ORIGINAL_RESOURCE_ADMISSION_CHILD_LIMITS_RSS_TERMINATE',historical_arrays_read_by_benchmark=0,historical_wallets=0,risk_parity_certified=False,interpretation='Fixed generated tape measures transport/scaling only. Real source/fill/event complexity may differ; this is not a calendar budget guarantee.')
 (out/'BENCHMARK_RECEIPT.json').write_text(json.dumps(result,indent=2)+'\n')
 print(json.dumps({k:v for k,v in result.items() if k!='runs'},indent=2));return 0 if result['status'].startswith('PASS') else 1

def main():
 p=argparse.ArgumentParser();p.add_argument('--output',required=True);p.add_argument('--runtime-site',action='append',required=True);p.add_argument('--resource-roots');p.add_argument('--worker',action='store_true');p.add_argument('--days',type=int,choices=(1,7,31));p.add_argument('--arm',choices=('CSH','CASH','GRID'));a=p.parse_args()
 os.environ['BOT_NATIVE_RUNTIME_SITES']=json.dumps(a.runtime_site)
 return worker(a) if a.worker else benchmark(a)

if __name__=='__main__':raise SystemExit('USE_RUN_VERIFIED_COLD_BOOTSTRAP')
