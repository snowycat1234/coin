"""Post-freeze price intake and dense actual-close matrix, no strategy scoring."""
import argparse,concurrent.futures,json,time
from pathlib import Path
import numpy as np
import pandas as pd
from source import HERE,ROOT,CORE5,DAY,Intake,protocol,frame,sha,save

def build(state,selection):
 assert not state.exists();state.mkdir(parents=True);pool=json.loads((selection/'POOL.json').read_text());assert (selection/'POOL.json').read_bytes()==(HERE/'input/POOL.json').read_bytes() and pool['status']=='FROZEN_HISTORICAL_TOP20_WITH_ARCHIVE_COVERAGE_LIMITS' and pool['evaluation_price_payloads_read']==0
 P=protocol();admission=json.loads((HERE/'EVALUATION_WARMUP_ADMISSION.json').read_text());periods=[admission['additional_warmup_month']]+admission['other_evaluation_source_months'];names=list(CORE5)+sorted(set(pool['symbols'])-set(CORE5));t=np.arange(int(pd.Timestamp('2022-08-01',tz='UTC').value//1000),int(pd.Timestamp('2024-01-01',tz='UTC').value//1000)+DAY,DAY);p=np.full((len(t),len(names)),np.nan);intake=Intake(state);intake.count=pool['HTTP_counts'].copy();intake.bytes=pool['HTTP_body_bytes'].copy();records=[]
 old=ROOT/'research/monetary-policy-information-20261012/input/INPUTS.npz';assert sha(old)=='e33cc15bd53167078252f7d58b406960d543ccb92421f430214e5360971f12f4'
 with np.load(old,allow_pickle=False) as z:at=z['close_available_us'];cp=z['close'];assert tuple(z['symbol_order'])==CORE5
 ix=np.searchsorted(at,t);np.testing.assert_array_equal(at[ix],t);p[:,:5]=cp[ix]
 def put(record,root):
  if 'path' not in record:return
  path=root/record['path'];assert sha(path)==record['ZIP_SHA256'];f,complete=frame(path,record['period'],record['daily']);j=names.index(record['symbol']);clocks=f.timestamp_ms.to_numpy(np.int64)*1000+DAY;k=np.searchsorted(t,clocks);np.testing.assert_array_equal(t[k],clocks);values=f.close.to_numpy(float)
  already=np.isfinite(p[k,j]);assert np.array_equal(p[k[already],j],values[already]),'Conflictingactualmonth/daily/reusedCORE5close sources; no keep-last'
  p[k,j]=values
 for r in pool['source_records']:
  if r['symbol'] in names and r['symbol'] not in CORE5:put(r,selection)
 with concurrent.futures.ThreadPoolExecutor(P['source_budget']['network_threads']) as workers:
  jobs={workers.submit(intake.acquire,s,m):(s,m) for s in names if s not in CORE5 for m in periods}
  for n,job in enumerate(concurrent.futures.as_completed(jobs),1):
   r=job.result();records.append(r);put(r,state)
   if n%30==0:print('ACTUAL_FROZEN_WIDE_EVAL_DAILY_SOURCE',n,len(jobs),'unknown',sum('path' not in q for q in records),flush=True)
 decisions=np.arange(int(pd.Timestamp('2023-01-01',tz='UTC').value//1000),int(pd.Timestamp('2024-01-01',tz='UTC').value//1000),DAY);np.savez_compressed(state/'INPUTS.npz',close_available_us=t,close=p,decision_us=decisions,symbol_order=np.array(names),wide_allowed=np.array([s in pool['symbols'] for s in names]),core_allowed=np.array([s in CORE5 for s in names]))
 out=dict(status='PASS_FROZEN_COVERED_ARCHIVE_WIDE_CAUSAL_DAILY_SOURCE',pool_SHA256=sha(selection/'POOL.json'),SOURCE_PROTOCOL_SHA256=sha(HERE/'SOURCE_PROTOCOL.json'),CORE5_exact_cube_SHA256=sha(old),symbol_order=names,wide_pool=pool['symbols'],calendar=['2023-01-01','2024-01-01'],natural_days=365,INPUTS_SHA256=sha(state/'INPUTS.npz'),source_records=sorted(records,key=lambda r:(r['symbol'],r['period'])),cumulative_source_HTTP_counts=intake.count,cumulative_source_HTTP_body_bytes=intake.bytes,source_gap_asset_dates={s:int((~np.isfinite(p[np.searchsorted(t,decisions),j])).sum()) for j,s in enumerate(names)},full_historical_universe_certified=False,unknown_does_not_mean_nontradable=True,price_NaNs_retained=True,CORE5_evaluation_archive_downloads=0,new_fits=0,new_native_wallets=0,strategy_scores=0,seconds=time.monotonic()-intake.started)
 save(state/'SOURCE.json',out);print('ACTUAL_FROZEN_WIDE_EVAL_SOURCE_COMPLETE',out['source_gap_asset_dates'],intake.count,intake.bytes,flush=True)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--state',type=Path,required=True);p.add_argument('--selection',type=Path,required=True);a=p.parse_args();build(a.state,a.selection)
