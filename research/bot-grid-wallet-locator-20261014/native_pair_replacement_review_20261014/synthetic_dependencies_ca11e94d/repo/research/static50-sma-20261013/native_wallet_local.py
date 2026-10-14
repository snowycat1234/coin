"""Location/provenance port of frozen native_wallet.py; financial path unchanged."""
import argparse,importlib.util,json,os,shutil,subprocess,time
from pathlib import Path
import numpy as np
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
spec=importlib.util.spec_from_file_location('mix_verified_sma_native_apis',HERE/'local_native_apis.py')
n=importlib.util.module_from_spec(spec);spec.loader.exec_module(n)
native=n.native;Closing=n.Closing;DAY=n.DAY;SYMBOLS=n.SYMBOLS
def data(key):
 r=json.loads((HERE/'input/READINESS.json').read_text());p=HERE/'input'/(key+'.npz');assert n.file_sha(p)==r['years'][key]['target_SHA256']
 with np.load(p,allow_pickle=False) as z:
  d=z['decision_us'].copy();a=z['STATIC50'].copy();b=z['SMA200_10PCT'].copy();w=z['COMBINED'].copy();assert tuple(z['symbol_order'])==SYMBOLS
 np.testing.assert_array_equal(w,.5*a+.5*b);return d,w
def admission(margin,case_bytes,packet_bytes):return margin>=case_bytes+2*packet_bytes+1048576
def preflight(state):
 assert not state.exists() and state.parent.exists();p=json.loads((HERE/'NATIVE_PLAN_LOCAL.json').read_text());assert p['future_bounded_native_budget_if_admitted']['disk_reserve']==16106127360
 # Original observed state is absent here. Do not let a missing reference count as zero.
 case=150000000;packet=63204609
 margin=shutil.disk_usage(state.parent).free-16106127360
 required=max(209497350,case+2*packet+1048576)
 assert margin>=required,f'RESOURCE_STOP: reserve margin {margin}, need {required}; no state created'
 return p
def run(state,key,commit):
 assert commit=='b9c0020ec0ae9c7be991e58544bb5227657ef640'
 P=preflight(state);n.verify();ready=json.loads((HERE/'input/READINESS.json').read_text());assert ready['protocol_SHA256']==n.file_sha(HERE/'PROTOCOL.json')
 d,w=data(key);win=n.window(key);np.testing.assert_array_equal(d,np.arange(win['start'],win['end'],DAY))
 assert ready['years'][key]['source_index_SHA256']==n.file_sha(n.prepared(key)/'SOURCE_INDEX.json')
 state.mkdir(parents=True);begin=time.monotonic();binding=dict(window=key,arm='STATIC50_SMA_HALF',science_source_commit=commit,financial_base_commit='b9c0020ec0ae9c7be991e58544bb5227657ef640',local_code_manifest_SHA256=n.file_sha(HERE/'LOCAL_CODE_MANIFEST.json'),native_wallet_local_SHA256=n.file_sha(HERE/'native_wallet_local.py'),local_native_apis_SHA256=n.file_sha(HERE/'local_native_apis.py'),protocol_SHA256=n.file_sha(HERE/'PROTOCOL.json'),native_plan_SHA256=n.file_sha(HERE/'NATIVE_PLAN_LOCAL.json'),readiness_SHA256=n.file_sha(HERE/'input/READINESS.json'),target_archive_SHA256=n.file_sha(HERE/'input'/(key+'.npz')),source_index_SHA256=ready['years'][key]['source_index_SHA256'],account_class=Closing.VERSION,quantity_profile_SHA256=n.profile_sha(),contract_from_initial_capital=True,persist_cash_close=False,final_day_target_zero=False,end_us=win['end'],terminal_signal_us=win['end']-360000000)
 n.save(state/'BINDING.json',binding);n.save(state/'RUN_PROCESS.json',dict(pid=os.getpid(),source_commit=commit,stage='ACTUAL_ONE_SHARED_NATIVE_WALLET_STARTED',clock_UTC=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime())))
 def factory(_daily,clocks,mode):
  np.testing.assert_array_equal(clocks,d);assert mode=='LONG_SHORT'
  return native.pl.DataFrame([dict(available_us=int(at),symbol=s,target_weight=float(w[i,j])) for i,at in enumerate(d) for j,s in enumerate(SYMBOLS)]),dict(kind='EXACT_SAVED_STATIC50_HALF_PLUS_ORIGINAL_SMA_HALF_NO_REEXPANSION',binding=binding)
 sim=native.NativeDailySimulator(win,'LONG_SHORT',native.COSTS[0],native.UNITS[0],target_factory=factory,account_factory=Closing,persist_cash_close=False,final_day_target_zero=False)
 assert type(sim.account) is Closing and sim.account.nav()==10000 and not sim.persist_cash_close and not sim.final_day_target_zero
 n.checkpoint(state/'recovery',sim,binding);print('ACTUAL_STATIC50_SMA_NATIVE_STARTED',key,os.getpid(),commit,flush=True)
 while sim.cursor<win['end'] and sim.stop is None:
  sim.advance_day();days=len(sim.minute_chunks)
  if days%90==0 or sim.cursor==win['end'] or sim.stop is not None:n.checkpoint(state/'recovery',sim,binding)
  if days%30==0 or sim.cursor==win['end'] or sim.stop is not None:print('ACTUAL_STATIC50_SMA_NATIVE_PROGRESS',key,days,365,'NAV',float(sim.account.nav()),'STATUS',sim.account.status,flush=True)
  if time.monotonic()-begin>P['future_bounded_native_budget_if_admitted']['wallet_seconds_each'] or sum(f.stat().st_size for f in state.rglob('*') if f.is_file())>P['future_bounded_native_budget_if_admitted']['STATE_case_bytes']:
   n.checkpoint(state/'recovery',sim,binding);n.save(state/'BUDGET_STOP.json',dict(cursor=sim.cursor,rows=sim.rows_written,seconds=time.monotonic()-begin));raise RuntimeError('Frozen budget STOP, genuine partial state retained')
 case=sim.result();summary=case['summary'];_,q=native.episodes(case['trades'],SYMBOLS)
 for s in SYMBOLS:assert q[s]==sim.account.positions[s].quantity
 bridge=native.nav_bridge(case['trades'],case['funding'],q,summary['terminal_mark_prices'],sim.account.nav())
 minute=case['minute'];daily=minute.filter(native.pl.col('close_us')%DAY==0)
 body={k:case[k] for k in ('trades','funding','rejections','breaches','extrema','target_meta')};body.update(summary=summary,targets=case['targets'].to_dicts(),liquidations=case.get('liquidations',[]))
 n.save(state/'ACCOUNT.json',body);daily.write_csv(state/'DAILY.csv');n.save(state/'MINUTE_NUMERIC.json',dict(columns=n.fingerprint(minute),storage='ALL37_MINUTE_BITS_EXACT_ORIGINAL_NPZ_CODEC'))
 np.testing.assert_array_equal(case['targets']['target_weight'].to_numpy().reshape(-1,5),w)
 navs=np.r_[10000.,daily['nav'].to_numpy()];returns=np.diff(navs)/navs[:-1];roll=navs[30:]/navs[:-30]-1;ptr=json.loads((state/'recovery/POINTER.json').read_text());full=summary['completed_minutes']==525600
 report=dict(status='COMPLETE_ORIGINAL_SHARED_NATIVE_TARGET' if full else 'STOP_INCOMPLETE_ORIGINAL_SHARED_NATIVE_TARGET',window=key,arm='STATIC50_SMA_HALF',science_source_commit=commit,summary=summary,metrics=dict(days=len(returns),annual_daily_vol=float(returns.std(ddof=1)*np.sqrt(365)),worst30=float(roll.min()),mean_actual_gross=float(minute['gross_weight'].mean()),max_actual_gross=float(minute['gross_weight'].max()),mean_signed_net=float(minute['net_signed_weight'].mean()),max_abs_signed_net=float(np.abs(minute['net_signed_weight'].to_numpy()).max()),minute_drawdown=summary['all_observation_max_drawdown']),full_calendar=full,paid_flat=summary['terminal_cash_realized'],paid_cash_return=summary['net_PnL']/10000 if summary['terminal_cash_realized'] else None,cumulative_marked_return=summary['net_PnL']/10000,independent_decimal_NAV_bridge=bridge,genuine_state_hash=ptr['state_hash'],rejection_counts=native.rejection_counts(case['rejections']),new_wallets=1,new_fits=0,downloads=0,old_wallet_replays=0,scope='HISTORICAL_SHARED_ONE_WALLET_NO_NEW_OOS_OR_NATIVE_VENUE_CERTIFICATION')
 n.save(state/'RESULT.json',report);n.save(state/'TIMING.json',dict(seconds=time.monotonic()-begin));print('ACTUAL_STATIC50_SMA_NATIVE_RESULT',key,summary['net_PnL'],summary['terminal_cash_realized'],summary['terminal_marked_notional'],flush=True)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--state',type=Path,required=True);p.add_argument('--window',choices=['Y2023','Y2025'],required=True);p.add_argument('--source-commit',required=True);a=p.parse_args();run(a.state,a.window,a.source_commit)
