"""Thin full-year scheduling/reporting adapter around unchanged native wallet APIs."""
import argparse,importlib.util,json,sys,time
from pathlib import Path
import numpy as np
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
def load(name,path):
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
old=load('frozen2025risk_execution_apis',ROOT/'research/portfolio-risk-budget-20261012/driver.py')
native,b,Closing,profile_sha=old.native,old.b,old.Closing,old.profile_sha
checkpoint,restore_snapshot=old.checkpoint,old.restore_snapshot
SYMBOLS=old.SYMBOLS;ARMS=old.ARMS;DAY=old.DAY;sha=old.sha;save=old.save
source=load('exact2025public_source',ROOT/'research/portfolio-risk-2025-admission-20261012/source2025.py')
sys.path.insert(0,str(HERE))
def proto():return json.loads((HERE/'PROTOCOL.json').read_text())
def verify():
 for line in (HERE/'SOURCE_SHA256.txt').read_text().splitlines():s,p=line.split(maxsplit=1);assert sha(ROOT/p)==s,p
def bind_intents(prepared,index):
 for name in ('Y2025.npz','Y2025_RISK.json'):
  r=index['files'][name];path=HERE/'input'/name;assert sha(path)==r['SHA256'] and path.stat().st_size==r['bytes']
  assert path.read_bytes()==(prepared/name).read_bytes(),'Actual consumed target/risk must equal admitted source'
def window(prepared):
 ix=json.loads((prepared/'SOURCE_INDEX.json').read_text());start,end=ix['calendar'];assert ix['status']=='PASS_EXACT_FULL2025_NATIVE_SOURCE_CAUSAL_RISK' and ix['days']==365 and ix['symbol_order']==list(SYMBOLS) and ix['calendar']==[native.utc('2025-01-01'),native.utc('2026-01-01')]
 for name in ('EVENTS.json','DAILY.json','Y2025.npz','Y2025_RISK.json'):r=ix['files'][name];assert sha(prepared/name)==r['SHA256'] and (prepared/name).stat().st_size==r['bytes']
 bind_intents(prepared,ix)
 events=json.loads((prepared/'EVENTS.json').read_text());daily=native.pl.DataFrame(json.loads((prepared/'DAILY.json').read_text()));assert len(events)==ix['funding_events']==5475 and daily.height==1825
 for row in ix['months']:
  path=prepared/'months'/(row['month']+'.npz');assert sha(path)==row['source_NPZ_SHA256'] and path.stat().st_size==row['source_NPZ_bytes']
 def blocks():
  for row in ix['months']:
   path=prepared/'months'/(row['month']+'.npz');assert sha(path)==row['source_NPZ_SHA256'] and path.stat().st_size==row['source_NPZ_bytes']
   with np.load(path,allow_pickle=False) as a:times=a['times'];market={s:{k:a[s+'_'+k] for k in ('open','close','quote_volume','mark')} for s in SYMBOLS}
   for i in range(0,len(times),1440):yield dict(times=times[i:i+1440],market={s:{k:v[i:i+1440] for k,v in fields.items()} for s,fields in market.items()})
 return dict(start=start,end=end,symbols=SYMBOLS,daily=daily,events=events,minute_blocks=blocks)
def intents():
 with np.load(HERE/'input/Y2025.npz',allow_pickle=False) as a:
  d=a['decision_us'];weights={arm:a[arm].copy() for arm in ARMS};assert tuple(a['symbol_order'])==SYMBOLS
 np.testing.assert_array_equal(d,np.arange(native.utc('2025-01-01'),native.utc('2026-01-01'),DAY))
 for w in weights.values():native.targets(d,w,d[0],d[-1]+DAY,d[0],SYMBOLS)
 return d,weights
def forecast(arm):
 rows=[r['arms'][arm] for r in json.loads((HERE/'input/Y2025_RISK.json').read_text())]
 return dict(target_met_days=sum(r['risk_target_met'] for r in rows),cap_bound_days=sum(r['cap_bound'] for r in rows),cash_days=sum(r['reason']=='INTRINSIC_CASH' for r in rows),mean_post_sigma=float(np.mean([r['post_sigma'] for r in rows])),max_shortfall=max(r['shortfall'] for r in rows))
def run(state,arm,prepared,science):
 assert arm in ARMS and not state.exists() and not b.git('status','--porcelain') and b.git('rev-parse','HEAD').decode().strip()==science;verify();P=proto()
 assert (prepared/'SOURCE_INDEX.json').read_bytes()==b.git('show',P['source_artifact']+':research/portfolio-risk-2025-native-20261012/input/SOURCE_INDEX.json')
 state.mkdir(parents=True);began=time.monotonic();win=window(prepared);d,weights=intents();w=weights[arm]
 binding=dict(window='Y2025',arm=arm,calendar=P['calendar'],science_source_commit=science,source_artifact=P['source_artifact'],source_index_SHA256=sha(prepared/'SOURCE_INDEX.json'),target_archive_SHA256=sha(HERE/'input/Y2025.npz'),risk_proof_SHA256=sha(HERE/'input/Y2025_RISK.json'),protocol_SHA256=sha(HERE/'PROTOCOL.json'),account_class=Closing.VERSION,contract_from_initial_capital=True,quantity_profile_SHA256=profile_sha(),annual_risk_budget=.10)
 save(state/'BINDING.json',binding)
 def factory(_daily,clocks,mode):
  np.testing.assert_array_equal(clocks,d);return native.pl.DataFrame([dict(available_us=int(at),symbol=s,target_weight=float(w[i,j])) for i,at in enumerate(d) for j,s in enumerate(SYMBOLS)]),dict(kind='UNCHANGED_FIXED10_FORECAST_BUDGET_FULL2025',binding=binding)
 sim=native.NativeDailySimulator(win,'LONG_SHORT',native.COSTS[0],native.UNITS[0],target_factory=factory,account_factory=Closing)
 assert type(sim.account) is Closing and sim.account.closing_min_notional_exempt and sim.account.nav()==10000;checkpoint(state/'recovery',sim,binding)
 while sim.cursor<win['end'] and sim.stop is None:
  sim.advance_day();days=len(sim.minute_chunks)
  if days%30==0 or sim.cursor==win['end'] or sim.stop is not None:checkpoint(state/'recovery',sim,binding);print('ACTUAL2025_FIXED_RISK_WALLET',arm,days,365,'NAV',float(sim.account.nav()),'status',sim.account.status,flush=True)
  assert time.monotonic()-began<P['budget']['wallet_seconds'] and sum(p.stat().st_size for p in state.rglob('*') if p.is_file())<P['budget']['STATE_case_bytes']
 case=sim.result();summary=case['summary'];audit='PASS';error=None;finance=None
 try:
  _,q=native.episodes(case['trades'],SYMBOLS)
  for s in SYMBOLS:assert q[s]==sim.account.positions[s].quantity
  finance=native.nav_bridge(case['trades'],case['funding'],q,summary['terminal_mark_prices'],sim.account.nav())
 except (AssertionError,ValueError) as exc:audit='FAIL';error=str(exc)
 minute=case['minute'];daily=minute.filter(native.pl.col('close_us')%DAY==0);nav=np.r_[10000.,daily['nav'].to_numpy()];r=np.diff(nav)/nav[:-1];roll=nav[30:]/nav[:-30]-1 if len(nav)>30 else np.array([])
 net=sum(minute[s+'_signed_marked_notional'].to_numpy() for s in SYMBOLS)/minute['nav'].to_numpy()
 metrics=dict(days=len(r),actual_daily_annual_vol=float(r.std(ddof=1)*np.sqrt(365)) if len(r)>1 else None,worst30=float(roll.min()) if len(roll) else None,mean_actual_gross=float(minute['gross_weight'].mean()),maximum_actual_gross=float(minute['gross_weight'].max()),mean_actual_signed_net=float(net.mean()),maximum_absolute_actual_net=float(np.abs(net).max()))
 body={k:case[k] for k in ('trades','funding','rejections','breaches','extrema','target_meta')};body.update(summary=summary,targets=case['targets'].to_dicts(),liquidations=case.get('liquidations',[]));save(state/'ACCOUNT.json',body);daily.write_csv(state/'DAILY.csv')
 f=load('original2025minute_fingerprint',ROOT/'research/cs-continuous-economics-20261012/persistence.py');save(state/'MINUTE_NUMERIC.json',dict(columns=f.minute_fingerprint(minute),Parquet_container='NOT_CREATED_ORIGINAL_ALL37_VALUE_BITS_RETAINED'))
 full=summary['completed_minutes']==525600;paid=bool(summary['terminal_cash_realized']);ci=None
 if full:
  rng=np.random.default_rng(P['bootstrap']['seed']);draws=[]
  for _ in range(P['bootstrap']['draws']):
   starts=rng.integers(0,len(r),int(np.ceil(len(r)/14)));ids=np.concatenate([(s+np.arange(14))%len(r) for s in starts])[:len(r)];draws.append(float(r[ids].mean()))
  ci=[float(x) for x in np.quantile(draws,[.025,.975])]
 gates=dict(full_paid_audited=bool(full and paid and not body['liquidations'] and audit=='PASS'),net_positive=bool(full and paid and summary['net_PnL']>0),daily_paid_path_CI=bool(paid and ci is not None and ci[0]>0),risk=bool(full and metrics['actual_daily_annual_vol']<=.12 and summary['all_observation_max_drawdown']<=.12 and metrics['worst30']>=-.10))
 ptr=json.loads((state/'recovery/POINTER.json').read_text());assert ptr['completed_minutes']==summary['completed_minutes']
 report=dict(status='PASS_CONDITIONAL_SEEN2025_PATH_GATES' if all(gates.values()) else 'STOP_CONDITIONAL_SEEN2025_PATH_GATES',window='Y2025',arm=arm,calendar=P['calendar'],science_source_commit=science,summary=summary,metrics=metrics,gates=gates,bootstrap_marked_path95CI=ci,bootstrap_paid_path95CI=ci if paid else None,inventory_audit=audit,audit_error=error,independent_decimal_NAV_bridge=finance,genuine_state_hash=ptr['state_hash'],forecast_risk=forecast(arm),new_wallets=1,new_fits=0,old_wallet_replays=0,provider_downloads=0,authority='CONDITIONAL_UNCERTIFIED_QUANTITY_FEE_FUNDING_MMR_ARRIVAL',scope='ALREADY_SEEN_FULL2025_FRESH10K_NOT_STITCHED_NOT_NEW_OOS_OR_PREDICTION_ALPHA')
 save(state/'RESULT.json',report);save(state/'TIMING.json',dict(seconds=time.monotonic()-began));print('ACTUAL2025_WALLET_RESULT',arm,summary['net_PnL'],paid,report['status'],flush=True)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--state',type=Path,required=True);p.add_argument('--arm',choices=ARMS,required=True);p.add_argument('--prepared',type=Path,required=True);p.add_argument('--source-commit',required=True);a=p.parse_args();run(a.state,a.arm,a.prepared,a.source_commit)
