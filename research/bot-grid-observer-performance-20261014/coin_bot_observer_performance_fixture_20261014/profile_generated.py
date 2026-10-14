"""Fixed dense generated timing/parity only; no historical archive reads."""
from pathlib import Path
import argparse,cProfile,hashlib,importlib.machinery,json,os,pstats,sys,time,types
ROOT=Path(__file__).resolve().parent.parent
PREP=ROOT/'coin_bot_historical_driver_wallet_locator_20261014'
FREEZE='44d66918dea6183553f54947a4a73b4fb77601065163b21e75b9aded4ddb91b4'

def bootstrap():
 manifest=json.loads((PREP/'PREPARATION_MANIFEST.json').read_text())
 assert hashlib.sha256((PREP/'PREPARATION_MANIFEST.json').read_bytes()).hexdigest()==FREEZE
 for n,r in manifest['files'].items():assert hashlib.sha256((PREP/n).read_bytes()).hexdigest()==r['SHA256']
 path=PREP/'verified_source.py';raw=path.read_bytes();module=types.ModuleType('verified_source');module.__file__=str(path);module.__spec__=importlib.machinery.ModuleSpec('verified_source',loader=None,origin=str(path));sys.modules[module.__name__]=module;exec(compile(raw,str(path),'exec'),module.__dict__);return module.install(FREEZE,'generated')

def dense(days,arm='CONTROL',scenario='DENSE'):
 import numpy as np
 from native_adapter import GridNativeAdapter,PORT,ACCOUNT,H,D,S,DAY,M
 START=207*DAY;end=START+days*DAY;clock=np.arange(START,end,DAY,dtype=np.int64);offset=np.arange(days*1440)
 market={};daily_rows=[]
 for j,s in enumerate(S):
  price=(100+30*j)*(1+.018*np.sin(offset*.013+j)+.004*np.sin(offset*.0007+j));volume=np.full(len(offset),500000.)
  if scenario=='PARTIAL':volume[(offset%1440)<10]=80000.
  if scenario=='TERMINAL_RESIDUAL':volume[-61:]=0.
  market[s]=dict(open=price.copy(),close=price.copy(),mark=price.copy(),quote_volume=volume)
  daily_rows.extend(dict(symbol=s,close_us=int(t),close=float(price[max(0,i*1440-1)])) for i,t in enumerate(clock))
 daily=PORT.native.pl.DataFrame(daily_rows)
 weights=np.array([[.11+.02*np.sin(i*.27),.10+.01*np.sin(i*.4),-.09-.01*np.sin(i*.3),.08+.01*np.sin(i*.5),-.07] for i in range(days)],dtype=np.float64)
 if scenario=='REVERSE':weights[days//2:,0]*=-1
 events=[dict(event_us=START+day*DAY+minute*M,symbol=s,raw_rate=float((1 if (day+j)%2 else -1)*(.00005+.00001*j))) for day in range(days) for minute in (0,480,960) for j,s in enumerate(S)]
 events.sort(key=lambda e:(e['event_us'],S.index(e['symbol'])))
 window=dict(start=START,end=end,symbols=S,daily=daily,events=events,market=market)
 def factory(_daily,clocks,mode):
  if mode!='LONG_SHORT' or not np.array_equal(clock,clocks):raise ValueError('FIXED_DENSE_GENERATED_CLOCK')
  return PORT.native.pl.DataFrame([dict(available_us=int(t),symbol=s,target_weight=float(weights[i,j])) for i,t in enumerate(clock) for j,s in enumerate(S)]),dict(source='FIXED_DENSE_GENERATED_ONLY',days=days,scenario=scenario)
 closes={int(t):[H.CompletedClose(int(t)-(29-i)*DAY,D(90 if i%2==0 else 110),int(t)-(29-i)*DAY) for i in range(30)] for t in clock};cov={int(t):np.eye(5)*.04 for t in clock}
 return GridNativeAdapter(window,'LONG_SHORT',PORT.native.COSTS[0],PORT.native.UNITS[0],target_factory=factory,account_factory=ACCOUNT,arm=arm,daily_closes=closes,covariance=cov,initial_observations={START:H.CompletedMinute(START,D(100),START)})

def main():
 p=argparse.ArgumentParser();p.add_argument('--candidate-sha');p.add_argument('--days',type=int,required=True);p.add_argument('--output',required=True);p.add_argument('--arm',default='CONTROL',choices=('CONTROL','CASH','GRID'));p.add_argument('--scenario',default='DENSE',choices=('DENSE','PARTIAL','REVERSE','TERMINAL_RESIDUAL'));args=p.parse_args();out=Path(args.output);out.mkdir(parents=True,exist_ok=False)
 runtime=bootstrap()
 if args.candidate_sha:
  candidate=ROOT/'coin_bot_native_adapter_observer_performance_20261014/native_adapter.py';runtime.add_path(candidate,args.candidate_sha);runtime.modules['native_adapter']=candidate.resolve();runtime.protected_roots.append(candidate.parent.resolve());candidate_evidence=ROOT/'coin_bot_historical_driver_observer_performance_20261014/evidence.py';runtime.add_path(candidate_evidence,'682c40d797e29e758bafaed316967a15765c1a2dfc610bf3370db8d068b0705e');runtime.modules['evidence']=candidate_evidence.resolve()
 import numpy as np
 np.load=lambda *a,**k:(_ for _ in ()).throw(ValueError('NO_ARRAY_LOAD_IN_GENERATED_PROFILE'))
 sys.path.insert(0,str(ROOT/'coin_bot_native_adapter_portable_synthetic_20261014'))
 sim=dense(args.days,args.arm,args.scenario);profile=cProfile.Profile();began=time.monotonic();daily=[];day_timing=[];profile.enable()
 while sim.cursor<sim.end and sim.stop is None:
  start=time.monotonic();daily.append(sim.advance_day());day_timing.append(time.monotonic()-start)
 profile.disable();elapsed=time.monotonic()-began;profile.dump_stats(out/'CPU_PROFILE.pstats')
 with (out/'PROFILE.txt').open('w') as stream:pstats.Stats(profile,stream=stream).strip_dirs().sort_stats('cumtime').print_stats(35)
 from evidence import export_final
 result=export_final(sim,out/'evidence',dict(fixture='DENSE_GENERATED_PROFILE',days=args.days,arm=args.arm,scenario=args.scenario),daily,[10000.]+[float(chunk[-1,0]) for chunk in sim.minute_chunks],origin='GENERATED_ONLY_NO_MARKET_PERFORMANCE')
 stats=pstats.Stats(profile).stats;selected={str(k):dict(calls=v[1],self_seconds=v[2],cumulative_seconds=v[3]) for k,v in stats.items() if k[2] in ('_reconcile','funding_through','attempt','advance_day')}
 report=dict(candidate_adapter_SHA256=args.candidate_sha,status='PASS_DENSE_GENERATED_PROFILE',days=args.days,completed_minutes=sim.rows_written,arm=args.arm,scenario=args.scenario,loop_seconds=elapsed,first_day_seconds=day_timing[0],last_day_seconds=day_timing[-1],daily_seconds=day_timing,owner_fills=len(sim.allocations),owner_funding_rows=len(sim.funding_allocations),native_funding_events=len(sim.account.funding),profile=selected,export=result,historical_arrays_read=0,historical_wallets=0)
 (out/'PROFILE_RECEIPT.json').write_text(json.dumps(report,indent=2,sort_keys=True)+'\n');runtime.audit();print(json.dumps(report))
if __name__=='__main__':main()
