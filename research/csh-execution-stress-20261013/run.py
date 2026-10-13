"""One admitted frozen case per process, exact checkpoint and independent accounting."""
import argparse,datetime,hashlib,json,os,resource,shutil,sys,time,traceback
from pathlib import Path
from recover import STATE,REPO
from runtime import finance,source,target_factory,SYMBOLS,sha
from execution import capacity_half_class
HERE=Path(__file__).resolve().parent

def save(path,value):
 path.parent.mkdir(parents=True,exist_ok=True)
 with path.open('x') as f:json.dump(value,f,indent=2,sort_keys=True,allow_nan=False);f.write('\n')
def verify_freeze():
 p=json.loads((HERE/'FREEZE.json').read_text())
 for name,s in p['code_sha256'].items():assert sha(HERE/name)==s,name
 for row in json.loads((HERE/'PINNED_CODE_AND_TARGETS.json').read_text()):
  assert sha(STATE/row['relative_destination'])==row['sha256'],row
 return p

def guard():
 free=shutil.disk_usage(STATE).free;assert free>=15*2**30,'15GiB reserve'
 m={line.split(':')[0]:int(line.split()[1])*1024 for line in Path('/proc/meminfo').read_text().splitlines() if line.startswith(('MemTotal:','MemAvailable:','SwapTotal:'))}
 assert m['SwapTotal']==0 and m['MemTotal']-m['MemAvailable']<=8_000_000_000,'shared memory/swap budget'
 assert resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024<=2_000_000_000,'2GB worker RSS'
 return dict(free_bytes=free,host_used_bytes=m['MemTotal']-m['MemAvailable'],swap_bytes=m['SwapTotal'])

def run(year,shock):
 freeze=verify_freeze();case=f'Y{year}_{shock}';out=STATE/'wallets'/case
 out.mkdir(parents=True,exist_ok=False) # No overwrite/resume/replay of any case.
 os.sched_setaffinity(0,{min(os.sched_getaffinity(0))})
 resource.setrlimit(resource.RLIMIT_AS,(4_000_000_000,4_000_000_000));resource.setrlimit(resource.RLIMIT_CPU,(1200,1200))
 guard();begun=time.monotonic();start=datetime.datetime.now(datetime.UTC).isoformat();save(out/'STARTED.json',dict(start_UTC=start,case=case,resource=guard(),CPU_affinity=list(os.sched_getaffinity(0))))
 print('WALLET_STARTED',case,start,flush=True)
 sim=None;port=None;binding=None
 try:
  import numpy as np
  port,account=finance();win=source(year,port);factory=target_factory(year,port)
  original=json.loads((HERE/'SOURCE_BINDINGS.json').read_text())[str(year)]
  actual=json.loads((STATE/f'prepared_{year}/SOURCE_INDEX.json').read_text())
  for a,b in zip(actual['months'],original['source_index']['months'],strict=True):
   assert (a['month'],a['source_NPZ_SHA256'],a['source_NPZ_bytes'])==(b['month'],b['source_NPZ_SHA256'],b['source_NPZ_bytes'])
  for name in ('EVENTS.json',):assert sha(STATE/f'prepared_{year}'/name)==original['source_index']['files'][name]['SHA256']
  binding=dict(case=case,calendar=[win['start'],win['end']],arm='STATIC50',capital_USDT=10000,
    original_source_index_sha256=original['source_index_sha256'],actual_source_index_sha256=sha(STATE/f'prepared_{year}/SOURCE_INDEX.json'),
    target_archive_sha256=sha(STATE/'targets'/f'Y{year}.npz'),frozen_recipe_sha256=sha(HERE/'FREEZE.json'),
    source_binding_sha256=sha(HERE/'SOURCE_BINDINGS.json'),shock=shock,capacity_fraction='.0005' if shock=='CAPACITY_HALF' else '.001',
    fee_per_side='.00055',half_spread_bps=8 if shock=='FRICTION_DOUBLE' else 4,slippage_bps=8 if shock=='FRICTION_DOUBLE' else 4,
    protective_enabled=False,terminal_attempts=5,persist_cash_close=False,final_day_target_zero=False)
  save(out/'BINDING.json',binding)
  cls=capacity_half_class(port.native.NativeDailySimulator) if shock=='CAPACITY_HALF' else port.native.NativeDailySimulator
  cost=port.native.COSTS[1 if shock=='FRICTION_DOUBLE' else 0]
  sim=cls(win,'LONG_SHORT',cost,port.native.UNITS[0],target_factory=factory,account_factory=account,persist_cash_close=False,final_day_target_zero=False)
  assert sim.account.nav()==10000 and sim.account.closing_min_notional_exempt
  port.checkpoint(out/'recovery',sim,binding)
  while sim.cursor<win['end'] and sim.stop is None:
   sim.advance_day();days=len(sim.minute_chunks)
   if days%30==0 or sim.cursor==win['end'] or sim.stop is not None:
    port.checkpoint(out/'recovery',sim,binding);elapsed=time.monotonic()-begun
    guard();assert sum(p.stat().st_size for p in out.rglob('*') if p.is_file())<=250_000_000
    assert elapsed<1155,'20-minute worker cap; genuine partial checkpoint retained'
    eta=(sim.end-sim.cursor)/60000000/(sim.rows_written/elapsed) if sim.rows_written else None
    print('PROGRESS',case,days,365,'minutes',sim.rows_written,'elapsed',round(elapsed,2),'ETA_seconds',round(eta,2) if eta is not None else None,'NAV',float(sim.account.nav()),flush=True)
  result=sim.result();s=result['summary'];minute=result['minute']
  _,inventory=port.native.episodes(result['trades'],SYMBOLS)
  assert inventory=={name:sim.account.positions[name].quantity for name in SYMBOLS}
  bridge=port.native.nav_bridge(result['trades'],result['funding'],inventory,s['terminal_mark_prices'],sim.account.nav())
  full=s['completed_minutes']==s['required_minutes'];paid=full and s['completion']=='COMPLETE_CONDITIONAL_ACCOUNT' and s['terminal_cash_realized']
  save(out/'ACCOUNT.json',{k:result[k] for k in ('summary','trades','funding','rejections','breaches','extrema','target_meta')})
  result['targets'].write_csv(out/'TARGETS.csv');minute.filter(port.native.pl.col('close_us')%86400000000==0).write_csv(out/'DAILY.csv')
  save(out/'MINUTE_NUMERIC.json',port.fingerprint(minute))
  compact=dict(case=case,year=year,shock=shock,full_calendar=full,paid_flat=paid,marked_PnL_USDT=s['net_PnL'],paid_PnL_USDT=s['net_PnL'] if paid else None,
   cumulative_net_return=s['net_PnL']/10000,minute_DD=s['all_observation_max_drawdown'],mean_gross=float(minute['gross_weight'].mean()),max_gross=float(minute['gross_weight'].max()),
   mean_net=float(minute['net_signed_weight'].mean()),max_abs_net=float(minute['net_signed_weight'].abs().max()),
   turnover_USDT=s['gross_fill_turnover_USDT'],fees_USDT=s['fees_USDT'],execution_cost_USDT=s['execution_cost_USDT'],funding_USDT=s['funding_USDT'],
   trade_legs=s['trade_legs'],funding_observed=s['funding_observed_events'],rejection_counts=port.native.rejection_counts(result['rejections']),
   terminal_residual_quantity={k:str(v) for k,v in inventory.items()},terminal_residual_gross_USDT=s['terminal_marked_notional'],terminal_signed_marked_notional=s['terminal_signed_marked_notional'],
   account_status=s['account_status'],completion=s['completion'],completed_minutes=s['completed_minutes'],required_minutes=s['required_minutes'],stop_us=s['stop_us'],
   independent_NAV_bridge=bridge,elapsed_seconds=time.monotonic()-begun,sampled_or_process_peak_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,
   fresh_wallets=1,base_replays=0,fits=0,realized_funding_rate_unit_authority='UNCONFIRMED_RAW_AS_FRACTION_PROXY',binding_sha256=sha(out/'BINDING.json'),state_hash=sim.state_hash())
  save(out/'RESULT.json',compact);print('CASE_FINISHED',json.dumps(compact,default=str),flush=True)
 except BaseException as error:
  if sim is not None and port is not None and binding is not None:
   try:port.checkpoint(out/'recovery',sim,binding)
   except Exception:pass
  save(out/'FAILED.json',dict(error=str(error),traceback=traceback.format_exc(),elapsed_seconds=time.monotonic()-begun,historical_wallet_constructed=sim is not None))
  raise

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--year',type=int,choices=(2021,2023,2025),required=True);p.add_argument('--shock',choices=('FRICTION_DOUBLE','CAPACITY_HALF'),required=True);a=p.parse_args();run(a.year,a.shock)
