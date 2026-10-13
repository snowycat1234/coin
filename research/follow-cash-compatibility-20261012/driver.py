"""One existing optional execution flag, exact old targets and frozen wallet APIs."""
import argparse,json,time
from pathlib import Path
from report_holding import diagnose_holding
import numpy as np
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
import importlib.util
def load(name,path):
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
follow=load('cash_compat_original_follow',ROOT/'research/rejected-break-follow-native-20261012/driver.py')
native,b,Closing,profile_sha,checkpoint,restore_snapshot=follow.native,follow.b,follow.Closing,follow.profile_sha,follow.checkpoint,follow.restore_snapshot
SYMBOLS,DAY,MINUTE,sha,save=follow.SYMBOLS,follow.DAY,follow.MINUTE,follow.sha,follow.save
targets=follow.targets;OLD=ROOT/'research/rejected-break-follow-native-20261012'
def proto():return json.loads((HERE/'PROTOCOL.json').read_text())
def verify():
 for line in (HERE/'SOURCE_SHA256.txt').read_text().splitlines():s,p=line.split(maxsplit=1);assert sha(ROOT/p)==s,p
def clean(commit):assert not b.git('status','--porcelain') and b.git('rev-parse','HEAD').decode().strip()==commit
def baseline(key):return json.loads((OLD/'summary'/key/'RESULT.json').read_text())
def make(win,d,w,binding,persistent=True):
 assert type(persistent) is bool
 def factory(_daily,clocks,mode):
  np.testing.assert_array_equal(clocks,d)
  return native.pl.DataFrame([dict(available_us=int(at),symbol=s,target_weight=float(w[i,j])) for i,at in enumerate(d) for j,s in enumerate(SYMBOLS)]),dict(kind='SAVED_FOLLOW_KNOWN_CASH_RETRY_COMPATIBILITY',binding=binding)
 return native.NativeDailySimulator(win,'LONG_SHORT',native.COSTS[0],native.UNITS[0],target_factory=factory,account_factory=Closing,persist_cash_close=persistent,final_day_target_zero=False)
def prepare(state,commit):
 clean(commit);verify();assert not state.exists();state.mkdir(parents=True);begin=time.monotonic();rows={};ready=json.loads((OLD/'input/READINESS.json').read_text());assert ready['status']=='PASS_CONDITIONAL_FOLLOW_NATIVE_SOURCE_TARGET_READINESS'
 for key in proto()['fixed_order']:
  prepared=Path(proto()['windows'][key]['prepared']);win=follow.window(key,prepared);d,w=targets(key);old=baseline(key);binding=json.loads((OLD/'summary'/key/'BINDING.json').read_text());index=json.loads((prepared/'SOURCE_INDEX.json').read_text());assert old['summary']['completed_minutes']==525600 and old['summary']['terminal_cash_realized'] and old['inventory_audit']=='PASS';assert binding['source_index_SHA256']==sha(prepared/'SOURCE_INDEX.json')==ready['windows'][key]['source_index_SHA256'];assert binding['quantity_profile_SHA256']==profile_sha() and binding['target_archive_SHA256']==sha(OLD/'input'/(key+'.npz'))==ready['windows'][key]['target_SHA256'];assert binding['terminal_signal_us']==win['end']-6*MINUTE and binding['contract_from_initial_capital'] is True
  for q in index['months']:p=prepared/'months'/(q['month']+'.npz');assert sha(p)==q['source_NPZ_SHA256'] and p.stat().st_size==q['source_NPZ_bytes']
  holding=json.loads((OLD/'summary'/key/'HOLDING_DIAGNOSTIC.json').read_text());assert holding['complete_calendar_days']==365
  rows[key]=dict(calendar=proto()['windows'][key]['calendar'],source_index_SHA256=sha(prepared/'SOURCE_INDEX.json'),target_SHA256=sha(OLD/'input'/(key+'.npz')),baseline_RESULT_SHA256=sha(OLD/'summary'/key/'RESULT.json'),baseline_BINDING_SHA256=sha(OLD/'summary'/key/'BINDING.json'),baseline_state_hash=old['genuine_state_hash'],original_readiness_SHA256=sha(OLD/'input/READINESS.json'),months=12,minute_rows=525600,actual_funding_events=len(win['events']),causal_target_proof='REUSED_ORIGINAL_PUBLIC_PREFIX_CERTIFICATE_NOT_REFIT',original_portfolio_late_minutes=holding['portfolio_CASH_intent_late_inventory_minutes'],original_asset_late_minutes=sum(holding['asset_CASH_intent_late_inventory_minutes'].values()))
  print('ACTUAL_CASH_COMPAT_READINESS',key,len(d),len(win['events']),rows[key]['original_portfolio_late_minutes'],flush=True)
 out=dict(status='PASS_EXACT_SAVED_FOLLOW_CASH_CONTRACT_READINESS',source_commit=commit,protocol_SHA256=sha(HERE/'PROTOCOL.json'),windows=rows,new_fits=0,new_wallets=0,old_wallet_replays=0,provider_downloads=0,seconds=time.monotonic()-begin);assert out['seconds']<120;save(state/'READINESS.json',out)
def run(state,key,commit):
 clean(commit);verify();assert not state.exists();P=proto();ready=json.loads((HERE/'input/READINESS.json').read_text());assert ready['protocol_SHA256']==sha(HERE/'PROTOCOL.json');prepared=Path(P['windows'][key]['prepared']);win=follow.window(key,prepared);d,w=targets(key);old=baseline(key);assert sha(OLD/'summary'/key/'RESULT.json')==ready['windows'][key]['baseline_RESULT_SHA256'];state.mkdir(parents=True);begin=time.monotonic()
 binding=dict(window=key,arm='FOLLOW_PERSISTENT_CASH',calendar=P['windows'][key]['calendar'],science_source_commit=commit,protocol_SHA256=sha(HERE/'PROTOCOL.json'),readiness_SHA256=sha(HERE/'input/READINESS.json'),target_archive_SHA256=ready['windows'][key]['target_SHA256'],source_index_SHA256=ready['windows'][key]['source_index_SHA256'],baseline_RESULT_SHA256=ready['windows'][key]['baseline_RESULT_SHA256'],baseline_state_hash=old['genuine_state_hash'],quantity_profile_SHA256=profile_sha(),account_class=Closing.VERSION,contract_from_initial_capital=True,persist_cash_close=True,final_day_target_zero=False,end_us=win['end'],terminal_signal_us=win['end']-6*MINUTE)
 save(state/'BINDING.json',binding);sim=make(win,d,w,binding);assert type(sim.account) is Closing and sim.account.nav()==10000 and sim.persist_cash_close and not sim.final_day_target_zero;checkpoint(state/'recovery',sim,binding);print('ACTUAL_CASH_COMPAT_WALLET_STARTED',key,'10K',sim.state_hash(),commit,flush=True)
 while sim.cursor<win['end'] and sim.stop is None:
  sim.advance_day();days=len(sim.minute_chunks)
  if days%30==0 or sim.cursor==win['end'] or sim.stop is not None:checkpoint(state/'recovery',sim,binding);print('ACTUAL_CASH_COMPAT_PROGRESS',key,days,365,float(sim.account.nav()),sim.account.status,flush=True)
  if time.monotonic()-begin>P['budget']['wallet_seconds_each'] or sum(p.stat().st_size for p in state.rglob('*') if p.is_file())>P['budget']['STATE_case_bytes']:
   checkpoint(state/'recovery',sim,binding);save(state/'BUDGET_STOP.json',dict(cursor=sim.cursor,seconds=time.monotonic()-begin));raise RuntimeError('Frozen budget exhausted; genuine partial retained')
 case=sim.result();summary=case['summary'];audit='PASS';error=None;finance=None
 try:
  _,q=native.episodes(case['trades'],SYMBOLS)
  for s in SYMBOLS:assert q[s]==sim.account.positions[s].quantity
  finance=native.nav_bridge(case['trades'],case['funding'],q,summary['terminal_mark_prices'],sim.account.nav())
 except (ValueError,AssertionError) as exc:audit='FAIL';error=str(exc)
 minute=case['minute'];daily=minute.filter(native.pl.col('close_us')%DAY==0);nav=np.r_[10000.,daily['nav'].to_numpy()];r=np.diff(nav)/nav[:-1];roll=nav[30:]/nav[:-30]-1 if len(nav)>30 else np.array([]);gross=minute['gross_weight'].to_numpy();net=sum(minute[s+'_signed_marked_notional'].to_numpy() for s in SYMBOLS)/minute['nav'].to_numpy();metrics=dict(days=len(r),annual_daily_vol=float(r.std(ddof=1)*np.sqrt(365)) if len(r)>1 else None,worst30=float(roll.min()) if len(roll) else None,mean_actual_gross=float(gross.mean()),maximum_actual_gross=float(gross.max()),mean_signed_net=float(net.mean()),maximum_abs_signed_net=float(np.abs(net).max()))
 body={k:case[k] for k in ('trades','funding','rejections','breaches','extrema','target_meta')};body.update(summary=summary,targets=case['targets'].to_dicts(),liquidations=case.get('liquidations',[]));save(state/'ACCOUNT.json',body);daily.write_csv(state/'DAILY.csv');f=load('cash_compat_original_fingerprint',ROOT/'research/cs-continuous-economics-20261012/persistence.py');save(state/'MINUTE_NUMERIC.json',dict(columns=f.minute_fingerprint(minute),storage='GENUINE_ALL37_BITS_ORIGINAL_NPZ_BYTE_SHA_COLUMN_CODEC'));pointer=json.loads((state/'recovery/POINTER.json').read_text());assert pointer['completed_minutes']==summary['completed_minutes'];np.testing.assert_array_equal(np.array([v['target_weight'] for v in body['targets']]).reshape(-1,5),w)
 full=summary['completed_minutes']==525600;paid=bool(summary['terminal_cash_realized']);ci=follow.cash_ci(r,P['bootstrap']['seeds'][key]) if full else None;held=None
 if full:
  diagnose_holding(key,state,state/'HOLDING_DIAGNOSTIC.json');held=json.loads((state/'HOLDING_DIAGNOSTIC.json').read_text())
 delta=float(summary['net_PnL']-old['summary']['net_PnL']) if full and paid else None;portfolio=held['portfolio_CASH_intent_late_inventory_minutes'] if held else None;assets=sum(held['asset_CASH_intent_late_inventory_minutes'].values()) if held else None;base=ready['windows'][key];late_ok=held is not None and ((portfolio<base['original_portfolio_late_minutes'] and assets<base['original_asset_late_minutes']) if key=='Y2023' else (portfolio<=base['original_portfolio_late_minutes'] and assets<=base['original_asset_late_minutes']));gates=dict(full_paid_audited=full and paid and not body['liquidations'] and audit=='PASS',original_risk_bounds=full and metrics['annual_daily_vol']<=.12 and summary['all_observation_max_drawdown']<=.12 and metrics['worst30']>=-.10,paid_net_not_worse=delta is not None and delta>=-1e-8,late_ownership_reduced_or_zero_control=late_ok)
 report=dict(status='PASS_FIXED_FOLLOW_CASH_EXECUTION_COMPATIBILITY' if all(gates.values()) else 'STOP_FIXED_FOLLOW_CASH_EXECUTION_COMPATIBILITY',window=key,arm=binding['arm'],calendar=binding['calendar'],science_source_commit=commit,summary=summary,metrics=metrics,gates=gates,paid_net_delta_USDT=delta,baseline_net_USDT=old['summary']['net_PnL'],portfolio_late_minutes=portfolio,asset_late_minutes=assets,original_portfolio_late_minutes=base['original_portfolio_late_minutes'],original_asset_late_minutes=base['original_asset_late_minutes'],bootstrap_paid_cash_path95CI=ci if paid else None,bootstrap_marked_path95CI=ci,baseline_alpha_STOP='PRESERVED_NOT_RESCUED_BY_EXECUTION_COMPATIBILITY',inventory_audit=audit,audit_error=error,independent_decimal_NAV_bridge=finance,genuine_state_hash=pointer['state_hash'],rejection_counts=native.rejection_counts(case['rejections']),new_wallets=1,new_fits=0,old_wallet_replays=0,provider_downloads=0,scope='POSTHOC_SEEN_EXECUTION_COMPATIBILITY_NOT_NEW_PREDICTION_MECHANISM_OR_INVESTMENT_ADOPTION',authority=old['authority'],ordinary_CASH='PERSIST_UNTIL_FILLED_OR_SUPERSEDED_NOT_60MIN',terminal='ORIGINAL_END_MINUS6MIN_FIVE_TRIES_NO_EXTENSION');save(state/'RESULT.json',report);save(state/'TIMING.json',dict(seconds=time.monotonic()-begin));print('ACTUAL_CASH_COMPAT_RESULT',key,summary['net_PnL'],delta,portfolio,assets,paid,report['status'],flush=True)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('phase',choices=['prepare','run']);p.add_argument('--state',type=Path,required=True);p.add_argument('--window',choices=['Y2023','Y2025']);p.add_argument('--source-commit',required=True);a=p.parse_args();prepare(a.state,a.source_commit) if a.phase=='prepare' else run(a.state,a.window,a.source_commit)
