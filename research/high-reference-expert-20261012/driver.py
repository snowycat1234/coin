"""Two fixed full-year wallets; original risk/financial/source/storage APIs."""
import argparse,gc,hashlib,importlib.util,io,json,sys,time
from pathlib import Path
import numpy as np
from expert import DAY,SYMBOLS,targets,same_match_and_mix
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
def load(name,path):
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
old=load('unchanged_high_reference_native_apis',ROOT/'research/portfolio-risk-budget-20261012/driver.py');native,b,Closing=old.native,old.b,old.Closing
checkpoint,restore_snapshot=old.checkpoint,old.restore_snapshot
risk=load('unchanged_high_reference_risk',ROOT/'research/portfolio-risk-budget-20261012/risk_budget.py')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,x):Path(p).write_text(json.dumps(x,sort_keys=True,indent=2,allow_nan=False)+'\n')
def proto():return json.loads((HERE/'PROTOCOL.json').read_text())
def verify():
 for line in (HERE/'SOURCE_SHA256.txt').read_text().splitlines():h,p=line.split(maxsplit=1);assert sha(ROOT/p)==h,p
def daily_inputs(key):
 W=next(r for r in proto()['windows'] if r['name']==key);start,end=map(native.utc,W['calendar']);d=np.arange(start,end,DAY)
 if key=='Y2023':
  path=ROOT/'research/monetary-policy-information-20261012/input/INPUTS.npz';assert sha(path)=='e33cc15bd53167078252f7d58b406960d543ccb92421f430214e5360971f12f4'
  with np.load(path,allow_pickle=False) as z:t=z['close_available_us'];p=z['close']
  with np.load(ROOT/'research/cs-continuous-economics-20261012/reference-result/TARGETS.npz',allow_pickle=False) as z:
   assert tuple(z['symbol_order'])==SYMBOLS;ix=np.searchsorted(z['decision_us'],d);np.testing.assert_array_equal(z['decision_us'][ix],d);cs=z['CS_ORIGINAL'][ix];hold=z['VOL_ORIGINAL'][ix]
 else:
  sys.path.insert(0,str(ROOT/'research/portfolio-risk-2025-admission-20261012'))
  src=load('unchanged_highref_2025_daily_source',ROOT/'research/portfolio-risk-2025-admission-20261012/source2025.py');z,read=src.consumer()
  with np.load(io.BytesIO(read('features2025/FEATURES.npz')),allow_pickle=False) as a:t=a['completed_day_available_us'];p=a['close'];assert tuple(a['symbol_order'])==SYMBOLS
  with np.load(io.BytesIO(read('features2025/EXPERTS.npz')),allow_pickle=False) as a:
   np.testing.assert_array_equal(a['decision_us'],d);assert tuple(a['symbol_order'])==SYMBOLS;cs=a['expert_targets'][:,2];hold=a['expert_targets'][:,1]
  z.close()
 with np.load(ROOT/W['baseline_targets'],allow_pickle=False) as z:
  assert tuple(z['symbol_order'])==SYMBOLS;np.testing.assert_array_equal(z['decision_us'],d);cov=z['annual_covariance'];base=z['STATIC50']
 keep=t<=end;t=t[keep];p=p[keep]
 regenerated=[]
 for at in d:
  k=int(np.searchsorted(t,at));assert t[k]==at and k>=364;past=np.diff(p[k-30:k+1],axis=0)/p[k-30:k];regenerated.append(np.cov(past,rowvar=False,ddof=1)*365)
 np.testing.assert_array_equal(np.stack(regenerated),cov)
 oldmixed,_=same_match_and_mix(cs,hold,cov,risk.scale);np.testing.assert_array_equal(oldmixed,base)
 return W,t,p,d,hold,cov,base
def prepare(state,science):
 assert not state.exists() and not b.git('status','--porcelain') and b.git('rev-parse','HEAD').decode().strip()==science;verify();state.mkdir(parents=True);began=time.monotonic();reports={}
 for key in ('Y2023','Y2025'):
  W,t,p,d,hold,cov,base=daily_inputs(key);cs,feature=targets(t,p,d);w,proof=same_match_and_mix(cs,hold,cov,risk.scale)
  cut=d[180];alt=p.copy();alt[t>cut]*=np.arange(2,7);future,fproof=targets(t,alt,d);np.testing.assert_array_equal(future[d<=cut],cs[d<=cut])
  assert all(r['current_eligible']==[True]*5 for r in feature),'Actualcomplete365pricehistoryrequiredforallfixedCORE5 dates'
  np.savez_compressed(state/(key+'.npz'),decision_us=d,symbol_order=np.array(SYMBOLS),new_expert=cs,CANDIDATE=w,REUSED_STATIC50=base,annual_covariance=cov)
  save(state/(key+'_RISK.json'),proof);save(state/(key+'_FEATURE.json'),feature)
  reports[key]=dict(calendar=W['calendar'],natural_days=len(d),yearwarmup_all_current_members=True,baseline_complete_target_reconstruction='EXACT',past30covariance='EXACT_OLD_INPUTS',future_suffix_invariance='EXACT',changed_target_days=int(np.any(w!=base,axis=1).sum()),candidate_entire_target_identical_REUSE=bool(np.array_equal(w,base)),intrinsic_expert_cash_days=int((np.abs(cs).sum(1)==0).sum()),joint_cap_bound_days=sum(r['joint']['cap_bound'] for r in proof),joint_forecast_target_met_days=sum(r['joint']['risk_target_met'] for r in proof),npz_SHA256=sha(state/(key+'.npz')),risk_SHA256=sha(state/(key+'_RISK.json')),feature_SHA256=sha(state/(key+'_FEATURE.json')))
  print('HIGH_REFERENCE_ACTUAL_CAUSAL_TARGET_PREPARED',key,reports[key],flush=True)
 save(state/'PREPARATION.json',dict(status='PASS_ONE_FIXED_EXPERT_TARGETS_BEFORE_WALLETS',science_source_commit=science,windows=reports,new_fits=0,new_wallets=0,new_provider_GETs=0,seconds=time.monotonic()-began))
def native_window(key,prepared):
 if key=='Y2023':return old.source_window('P2',prepared)
 year=load('unchanged_high_reference2025_window',ROOT/'research/portfolio-risk-2025-native-20261012/driver.py');return year.window(prepared)
def run(state,key,science):
 assert not state.exists() and not b.git('status','--porcelain') and b.git('rev-parse','HEAD').decode().strip()==science;verify();state.mkdir(parents=True);began=time.monotonic();P=proto();W=next(r for r in P['windows'] if r['name']==key);prep=json.loads((HERE/'input/PREPARATION.json').read_text());assert not prep['windows'][key]['candidate_entire_target_identical_REUSE']
 path=HERE/'input'/(key+'.npz');assert sha(path)==prep['windows'][key]['npz_SHA256']
 with np.load(path,allow_pickle=False) as z:d=z['decision_us'];w=z['CANDIDATE'];assert tuple(z['symbol_order'])==SYMBOLS
 prepared=Path(W['native_source']);win=native_window(key,prepared);start,end=win['start'],win['end'];native.targets(d,w,start,end,start,SYMBOLS)
 baseline=json.loads((ROOT/W['baseline_result']).read_text());basepath=Path('/workspace/portfolio-risk-budget-state/OBSERVED_P2/STATIC50/DAILY.csv' if key=='Y2023' else '/workspace/portfolio-risk-2025-state/OBSERVED_STATIC50/DAILY.csv')
 indexpath=ROOT/('research/portfolio-risk-budget-20261012/result/P2/STATIC50/INDEX.json' if key=='Y2023' else 'research/portfolio-risk-2025-native-20261012/result/Y2025/STATIC50/INDEX.json');ix=json.loads(indexpath.read_text());member=next(r for r in ix['members'] if r['name']=='DAILY.csv');assert sha(basepath)==member['SHA256'] and basepath.stat().st_size==member['bytes'],'Exact public original baseline daily path beforeanywallet'
 binding=dict(science_source_commit=science,year=key,calendar=W['calendar'],target_SHA256=sha(path),source_index_SHA256=sha(prepared/'SOURCE_INDEX.json'),source_artifact=W['source_artifact'],protocol_SHA256=sha(HERE/'PROTOCOL.json'),quantity_profile_SHA256=old.profile_sha(),account_class=Closing.VERSION,capital_USDT=10000,original_baseline_not_replayed=True,baseline_DAILY_SHA256=sha(basepath),baseline_public_INDEX_SHA256=sha(indexpath))
 assert baseline['summary']['contract']['quantity_profile_SHA256']==binding['quantity_profile_SHA256'];save(state/'BINDING.json',binding)
 def factory(_daily,clocks,mode):
  np.testing.assert_array_equal(clocks,d);return native.pl.DataFrame([dict(available_us=int(at),symbol=s,target_weight=float(w[i,j])) for i,at in enumerate(d) for j,s in enumerate(SYMBOLS)]),dict(kind='HIGH365_REFERENCE_EXPERT_FIXED_HALF_WITH_EXISTING_HOLD',binding=binding)
 sim=native.NativeDailySimulator(win,'LONG_SHORT',native.COSTS[0],native.UNITS[0],target_factory=factory,account_factory=Closing);assert type(sim.account) is Closing and sim.account.nav()==10000 and sim.account.closing_min_notional_exempt;checkpoint(state/'recovery',sim,binding)
 print('ACTUAL_HIGH_REFERENCE_WALLET_STARTED',key,'full_days',365,'initial_capital',float(sim.account.nav()),flush=True)
 while sim.cursor<end and sim.stop is None:
  sim.advance_day();days=len(sim.minute_chunks)
  if days%90==0 or sim.cursor==end or sim.stop is not None:checkpoint(state/'recovery',sim,binding)
  if days%30==0 or sim.cursor==end or sim.stop is not None:print('ACTUAL_HIGH_REFERENCE_PROGRESS',key,days,365,'NAV',float(sim.account.nav()),'status',sim.account.status,flush=True)
  assert time.monotonic()-began<P['budget']['wallet_seconds_each'];assert sum(p.stat().st_size for p in state.rglob('*') if p.is_file())<P['budget']['STATE_case_bytes']
 case=sim.result();summary=case['summary'];_,q=native.episodes(case['trades'],SYMBOLS)
 for s in SYMBOLS:assert q[s]==sim.account.positions[s].quantity
 finance=native.nav_bridge(case['trades'],case['funding'],q,summary['terminal_mark_prices'],sim.account.nav());minute=case['minute'];daily=minute.filter(native.pl.col('close_us')%DAY==0);nav=np.r_[10000.,daily['nav'].to_numpy()];r=np.diff(nav)/nav[:-1];roll=nav[30:]/nav[:-30]-1 if len(nav)>30 else np.array([])
 body={k:case[k] for k in ('trades','funding','rejections','breaches','extrema','target_meta')};body.update(summary=summary,targets=case['targets'].to_dicts(),liquidations=case.get('liquidations',[]));save(state/'ACCOUNT.json',body);daily.write_csv(state/'DAILY.csv')
 codec=load('unchanged_highref_minute_fingerprint',ROOT/'research/cs-continuous-economics-20261012/persistence.py');save(state/'MINUTE_NUMERIC.json',dict(columns=codec.minute_fingerprint(minute),Parquet_container='NOT_CREATED_ALL37_ORIGINAL_BITS_RETAINED'))
 full=summary['completed_minutes']==525600;paid=bool(summary['terminal_cash_realized']);metrics=dict(actual_daily_annual_vol=float(r.std(ddof=1)*np.sqrt(365)) if len(r)>1 else None,worst30=float(roll.min()) if len(roll) else None,mean_actual_gross=float(minute['gross_weight'].mean()),maximum_actual_gross=float(minute['gross_weight'].max()),observed_drawdown=summary['all_observation_max_drawdown'])
 base=native.pl.read_csv(basepath);ci=None
 if full:
  np.testing.assert_array_equal(base['close_us'].to_numpy(),daily['close_us'].to_numpy());bn=np.r_[10000.,base['nav'].to_numpy()];br=np.diff(bn)/bn[:-1];delta=r-br;rng=np.random.default_rng(811740);draws=[]
  for _ in range(1000):
   starts=rng.integers(0,len(delta),int(np.ceil(len(delta)/14)));ids=((starts[:,None]+np.arange(14))%len(delta)).ravel()[:len(delta)];draws.append(float(delta[ids].mean()))
  ci=[float(v) for v in np.quantile(draws,[.025,.975])]
 gates=dict(full_paid_audited=bool(full and paid and not body['liquidations']),net_positive=bool(full and paid and summary['net_PnL']>0),paid_point_increment_positive=bool(full and paid and baseline['summary']['terminal_cash_realized'] and summary['net_PnL']>baseline['summary']['net_PnL']),annual_marked_increment_CI_positive=bool(ci is not None and ci[0]>0),risk=bool(full and metrics['actual_daily_annual_vol']<=.12 and metrics['observed_drawdown']<=.12 and metrics['worst30']>=-.10))
 bs=baseline['summary'];ptr=json.loads((state/'recovery/POINTER.json').read_text());report=dict(status='PASS_ANNUAL_EXPERT_SEEN_PATH_GATES' if all(gates.values()) else 'STOP_ANNUAL_EXPERT_SEEN_PATH_GATES',year=key,calendar=W['calendar'],summary=summary,metrics=metrics,original_annual_result=True,new_wallets=1,new_fits=0,provider_downloads=0,old_wallet_replays=0,inventory_NAV_audit='PASS',independent_decimal_NAV_bridge=finance,genuine_state_hash=ptr['state_hash'],forecast=prep['windows'][key],baseline_marked_net=bs['net_PnL'],annual_marked_net_increment=summary['net_PnL']-bs['net_PnL'] if full else None,annual_paid_net_increment=summary['net_PnL']-bs['net_PnL'] if full and paid and bs['terminal_cash_realized'] else None,annual_marked_daily_increment95CI=ci,CI_scope='ORIGINAL_ANNUAL_MARKED_DAILY_PATH_NO_JANUARY_TAIL_REWRITE',gates=gates,science_source_commit=science,baseline_DAILY_SHA256=sha(basepath),seconds=time.monotonic()-began,authority='CONDITIONAL_KNOWN_CORE5_NOT_GLOBAL_UNBIASED_NATIVE_OR_NEW_OOS')
 save(state/'RESULT.json',report);print('ACTUAL_HIGH_REFERENCE_YEAR_RESULT',key,report['status'],'net',summary['net_PnL'],'paid',paid,'increment',report['annual_marked_net_increment'],flush=True)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('phase',choices=['prepare','run']);p.add_argument('--state',type=Path,required=True);p.add_argument('--source-commit',required=True);p.add_argument('--year',choices=['Y2023','Y2025']);a=p.parse_args()
 if a.phase=='prepare':prepare(a.state,a.source_commit)
 else:assert a.year;run(a.state,a.year,a.source_commit)
