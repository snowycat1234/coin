"""Two necessary original SMA full-year native wallets, unchanged financial APIs."""
import argparse,json,os,time
from decimal import Decimal
from pathlib import Path
import numpy as np
from native_apis import HERE,ROOT,native,Closing,checkpoint,profile_sha,SYMBOLS,DAY,MINUTE,file_sha,save,proto,verify,clean,window,fingerprint
from scripts.investment.bybit_cost_inputs import execution_components
def intents(key):
 r=json.loads((HERE/'input/READINESS.json').read_text());p=HERE/'input'/(key+'.npz');assert file_sha(p)==r['years'][key]['target_SHA256']
 with np.load(p,allow_pickle=False) as z:d=z['decision_us'].copy();w=z['SMA200_10PCT'].copy();assert tuple(z['symbol_order'])==SYMBOLS
 return d,w
def directional_parts(body):
 result={a:dict(gross=Decimal(0),fees=Decimal(0),execution=Decimal(0),funding=Decimal(0)) for a in ('LONG','SHORT')}
 for r in body['trades']:
  s=r['decimal_strings'];owner=Decimal(s['quantity_before']) if r['leg']=='CLOSE' else Decimal(s['position_delta']);x=result['LONG' if owner>0 else 'SHORT'];x['gross']-=Decimal(s['position_delta'])*Decimal(s['mid_price']);x['fees']+=Decimal(s['fee_USDT_mid']);x['execution']+=Decimal(s['execution_cost'])
 for s,p in body['summary']['positions'].items():
  q=Decimal(str(p['quantity']))
  if q:result['LONG' if q>0 else 'SHORT']['gross']+=q*Decimal(str(body['summary']['terminal_mark_prices'][s]))
 for r in body['funding']:
  if r['quantity']:result['LONG' if r['quantity']>0 else 'SHORT']['funding']+=Decimal(r['decimal_strings']['signed_funding_USDT'])
 for x in result.values():x['net']=x['gross']-x['fees']-x['execution']+x['funding']
 assert abs(sum((x['net'] for x in result.values()),Decimal(0))-Decimal(body['summary']['decimal_strings']['net_PnL']))<Decimal('1e-18')
 return {a:{k:str(v) for k,v in x.items()} for a,x in result.items()}
def run(state,key,commit):
 clean(commit);verify();assert not state.exists();P=proto();ready=json.loads((HERE/'input/READINESS.json').read_text());assert ready['protocol_SHA256']==file_sha(HERE/'PROTOCOL.json');d,w=intents(key);win=window(key);np.testing.assert_array_equal(d,np.arange(win['start'],win['end'],DAY));state.mkdir(parents=True);begin=time.monotonic()
 binding=dict(window=key,arm='SMA200_10PCT',calendar=P['windows'][key]['calendar'],science_source_commit=commit,main_commit=P['main_commit'],protocol_SHA256=file_sha(HERE/'PROTOCOL.json'),readiness_SHA256=file_sha(HERE/'input/READINESS.json'),target_archive_SHA256=file_sha(HERE/'input'/(key+'.npz')),source_index_SHA256=ready['years'][key]['source_index_SHA256'],quantity_profile_SHA256=profile_sha(),account_class=Closing.VERSION,contract_from_initial_capital=True,persist_cash_close=False,final_day_target_zero=False,end_us=win['end'],terminal_signal_us=win['end']-6*MINUTE)
 save(state/'BINDING.json',binding);save(state/'RUN_PROCESS.json',dict(pid=os.getpid(),source_commit=commit,stage='ACTUAL_NATIVE_FULL_YEAR_STARTED',clock_UTC=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime())))
 def factory(_daily,clocks,mode):
  np.testing.assert_array_equal(clocks,d);return native.pl.DataFrame([dict(available_us=int(at),symbol=s,target_weight=float(w[i,j])) for i,at in enumerate(d) for j,s in enumerate(SYMBOLS)]),dict(kind='EXACT_MAIN_SMA200_DOWN_SCALE_ONLY_FULL_YEAR',binding=binding)
 sim=native.NativeDailySimulator(win,'LONG_SHORT',native.COSTS[0],native.UNITS[0],target_factory=factory,account_factory=Closing,persist_cash_close=False,final_day_target_zero=False);assert type(sim.account) is Closing and sim.account.nav()==10000 and not sim.persist_cash_close and not sim.final_day_target_zero;checkpoint(state/'recovery',sim,binding);print('ACTUAL_SMA200_NATIVE_STARTED',key,'PID',os.getpid(),'CAPITAL',float(sim.account.nav()),'SHA',commit,flush=True)
 while sim.cursor<win['end'] and sim.stop is None:
  sim.advance_day();days=len(sim.minute_chunks)
  if days%90==0 or sim.cursor==win['end'] or sim.stop is not None:checkpoint(state/'recovery',sim,binding)
  if days%30==0 or sim.cursor==win['end'] or sim.stop is not None:print('ACTUAL_SMA200_NATIVE_PROGRESS',key,days,365,'NAV',float(sim.account.nav()),'STATUS',sim.account.status,flush=True)
  if time.monotonic()-begin>P['budget']['wallet_seconds_each'] or sum(p.stat().st_size for p in state.rglob('*') if p.is_file())>P['budget']['STATE_case_bytes']:
   checkpoint(state/'recovery',sim,binding);save(state/'BUDGET_STOP.json',dict(cursor=sim.cursor,completed_minutes=sim.rows_written,seconds=time.monotonic()-begin));raise RuntimeError('Frozen budget STOP; true partial state retained')
 case=sim.result();summary=case['summary'];audit='PASS';error=None;bridge=None
 try:
  _,q=native.episodes(case['trades'],SYMBOLS)
  for s in SYMBOLS:assert q[s]==sim.account.positions[s].quantity
  bridge=native.nav_bridge(case['trades'],case['funding'],q,summary['terminal_mark_prices'],sim.account.nav())
 except (AssertionError,ValueError) as exc:audit='FAIL';error=str(exc)
 minute=case['minute'];daily=minute.filter(native.pl.col('close_us')%DAY==0);navs=np.r_[10000.,daily['nav'].to_numpy()];r=np.diff(navs)/navs[:-1];roll=navs[30:]/navs[:-30]-1 if len(navs)>30 else np.array([]);body={k:case[k] for k in ('trades','funding','rejections','breaches','extrema','target_meta')};body.update(summary=summary,targets=case['targets'].to_dicts(),liquidations=case.get('liquidations',[]));save(state/'ACCOUNT.json',body);daily.write_csv(state/'DAILY.csv');save(state/'MINUTE_NUMERIC.json',dict(columns=fingerprint(minute),storage='ALL37_MINUTE_BITS_EXACT_ORIGINAL_NPZ_CODEC'));np.testing.assert_array_equal(case['targets']['target_weight'].to_numpy().reshape(-1,5),w)
 metrics=dict(days=len(r),annual_daily_vol=float(r.std(ddof=1)*np.sqrt(365)) if len(r)>1 else None,worst30=float(roll.min()) if len(roll) else None,mean_actual_gross=float(minute['gross_weight'].mean()),max_actual_gross=float(minute['gross_weight'].max()),mean_signed_net=float(minute['net_signed_weight'].mean()),max_abs_signed_net=float(np.abs(minute['net_signed_weight'].to_numpy()).max()),minute_drawdown=summary['all_observation_max_drawdown']);monthly=[]
 for month in range(1,13):
  lo=native.utc(f'{key[1:]}-{month:02d}-01');hi=native.utc(f'{int(key[1:])+(month==12)}-{1 if month==12 else month+1:02d}-01');ids=(daily['close_us'].to_numpy()>lo)&(daily['close_us'].to_numpy()<=hi)
  if ids.sum()==(hi-lo)//DAY:positions=np.flatnonzero(ids);first,last=positions[0],positions[-1];monthly.append(dict(month=f'{key[1:]}-{month:02d}',days=int(ids.sum()),NAV_change_USDT=float(navs[last+1]-navs[first]),ending_NAV=float(navs[last+1]),no_reset=True))
 spread,slip=execution_components(summary['execution_cost_USDT'],summary['cost_scenario']);pointer=json.loads((state/'recovery/POINTER.json').read_text());full=summary['completed_minutes']==525600;paid=summary['terminal_cash_realized'];report=dict(status='COMPLETE_ORIGINAL_SMA200_NATIVE_BASELINE' if full and audit=='PASS' else 'STOP_INCOMPLETE_ORIGINAL_SMA200_NATIVE_BASELINE',window=key,arm='SMA200_10PCT',calendar=binding['calendar'],science_source_commit=commit,summary=summary,metrics=metrics,monthly_continuous=monthly,direction_contributions=directional_parts(body),spread_cost_USDT=spread,slippage_cost_USDT=slip,cumulative_marked_return=summary['net_PnL']/10000,paid_cash_return=summary['net_PnL']/10000 if paid else None,full_calendar=full,paid_flat=paid,inventory_audit=audit,audit_error=error,independent_decimal_NAV_bridge=bridge,genuine_state_hash=pointer['state_hash'],rejection_counts=native.rejection_counts(case['rejections']),new_wallets=1,new_fits=0,downloads=0,old_wallet_replays=0,scope='ORIGINAL_DOWNSCALE_ONLY_SEEN_FULL_YEAR_CONDITIONAL_NATIVE_NOT_PROXY_OR_NEW_OOS',authority='UNCHANGED_UNCERTIFIED_GRID_FUNDING_UNIT_PIT_MMR',terminal='END_MINUS6MIN_FIVE_TRIES_NO_TAIL_OR_FREE_CLEAR');save(state/'RESULT.json',report);save(state/'TIMING.json',dict(seconds=time.monotonic()-begin));print('ACTUAL_SMA200_NATIVE_RESULT',key,summary['net_PnL'],paid,summary['terminal_marked_notional'],audit,report['status'],flush=True)
if __name__=='__main__':
 q=argparse.ArgumentParser();q.add_argument('--state',type=Path,required=True);q.add_argument('--window',choices=['Y2023','Y2025'],required=True);q.add_argument('--source-commit',required=True);a=q.parse_args();run(a.state,a.window,a.source_commit)
