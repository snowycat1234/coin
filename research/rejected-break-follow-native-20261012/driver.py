"""Exact saved FOLLOW targets, two independent unchanged conditional native wallets."""
import argparse,hashlib,importlib.util,io,json,sys,time,zipfile
from pathlib import Path
import numpy as np
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
def load(name,path):
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
old=load('follow_existing2025_execution',ROOT/'research/portfolio-risk-2025-native-20261012/driver.py')
native,b,Closing,profile_sha,checkpoint,restore_snapshot=old.native,old.b,old.Closing,old.profile_sha,old.checkpoint,old.restore_snapshot
SYMBOLS=old.SYMBOLS;DAY=old.DAY;MINUTE=60000000;sha=old.sha;save=old.save
old2023=load('follow_existing2023_source',ROOT/'research/cs-2023-continuous-economics-20261012/native_run.py')
TARGET_COMMIT='16e7784dc77537eab7975bd15cc22cac8de335be'
TARGET_PREFIX='research/failed-breakout-rejection-20261012/public/TARGETS/'
def proto():return json.loads((HERE/'PROTOCOL.json').read_text())
def verify():
 for line in (HERE/'SOURCE_SHA256.txt').read_text().splitlines():s,p=line.split(maxsplit=1);assert sha(ROOT/p)==s,p
def clean(commit):assert not b.git('status','--porcelain') and b.git('rev-parse','HEAD').decode().strip()==commit
def exact_targets(key,path):
 year=int(key[1:]);start,end=map(native.utc,proto()['windows'][key]['calendar'])
 with np.load(path,allow_pickle=False) as z:
  d=z['decision_us'].copy();w=z['FOLLOW'].copy();assert tuple(z['symbol_order'])==SYMBOLS
  np.testing.assert_array_equal(d,np.arange(start,end,DAY));np.testing.assert_array_equal(w,-z['FADE'])
 assert d.shape==(365,) and w.shape==(365,5) and np.isfinite(w).all() and np.abs(w).max()<=.30+1e-12 and np.abs(w).sum(1).max()<=.60+1e-12
 native.targets(d,w,start,end,start,SYMBOLS)
 return d,w
def window(key,prepared):
 W=proto()['windows'][key];assert (prepared/'SOURCE_INDEX.json').read_bytes()==b.git('show',W['source_artifact']+':'+W['source_index_path'])
 return old2023.window(prepared) if key=='Y2023' else old.window(prepared)
def prepare(state,commit):
 clean(commit);verify();assert not state.exists();state.mkdir(parents=True);began=time.monotonic();P=proto()
 ix=json.loads(b.git('show',TARGET_COMMIT+':'+TARGET_PREFIX+'INDEX.json'));raw=b.git('show',TARGET_COMMIT+':'+TARGET_PREFIX+'PACKET.zip');assert hashlib.sha256(raw).hexdigest()==ix['SHA256'] and len(raw)==ix['bytes'];members={}
 with zipfile.ZipFile(io.BytesIO(raw)) as z:
  assert z.testzip() is None and set(z.namelist())==set(ix['members']) and len(z.namelist())==len(ix['members'])
  for name,r in ix['members'].items():
   data=z.read(name);assert hashlib.sha256(data).hexdigest()==r['SHA256'] and len(data)==r['bytes'];(state/name).write_bytes(data);members[name]=r
 prior=json.loads((state/'PREPARATION.json').read_text());assert prior['status']=='PASS_TWO_YEAR_CAUSAL_REJECTED_BREAK_TARGETS';(state/'PREPARATION.json').rename(state/'ORIGINAL_TARGET_PREPARATION.json');reports={}
 for key in P['fixed_order']:
  year=key[1:];W=P['windows'][key];d,w=exact_targets(key,state/(key+'.npz'));proof=prior['years'][year]
  assert sha(state/(key+'.npz'))==proof['INPUTS_SHA256']==members[key+'.npz']['SHA256'] and proof['source_unknown_asset_days']==0 and proof['future_OHLC_prices_NaN_and_risk_prices_NaN_prefix']=='EXACT'
  assert len(proof['risk'])==365 and all(r['event_bar_available_us']<=r['decision_us'] and r['prior_channel_last_available_us']<r['decision_us'] for r in proof['risk']);assert [r['decision_us'] for r in proof['risk']]==d.tolist()
  prepared=Path(W['cache']);win=window(key,prepared);index=json.loads((prepared/'SOURCE_INDEX.json').read_text());monthly=[];cursor=win['start'];mins=0
  for rec in index['months']:
   p=prepared/'months'/(rec['month']+'.npz');assert sha(p)==rec['source_NPZ_SHA256'] and p.stat().st_size==rec['source_NPZ_bytes']
   with np.load(p,allow_pickle=False) as a:
    t=a['times'];np.testing.assert_array_equal(t,np.arange(cursor,cursor+len(t)*MINUTE,MINUTE));assert len(t)%1440==0
    for s in SYMBOLS:
     for f in ('open','close','quote_volume','mark'):
      v=a[s+'_'+f];assert v.shape==t.shape and np.isfinite(v).all() and np.all(v>=0 if f=='quote_volume' else v>0)
   monthly.append(dict(month=rec['month'],SHA256=sha(p),bytes=p.stat().st_size,minutes=len(t)));mins+=len(t);cursor+=len(t)*MINUTE
  assert mins==525600 and cursor==win['end'] and len(monthly)==12
  events=win['events'];assert len(events)==5475 and events==sorted(events,key=lambda x:(x['event_us'],x['symbol'])) and len({(x['event_us'],x['symbol']) for x in events})==5475
  for e in events:assert e['symbol'] in SYMBOLS and win['start']<=e['event_us']<win['end'] and np.isfinite(e['raw_rate']) and np.isfinite(e['reported_interval_hours']) and e['reported_interval_hours']>0
  reports[key]=dict(calendar=W['calendar'],target_SHA256=sha(state/(key+'.npz')),risk_proof_SHA256=sha(state/'ORIGINAL_TARGET_PREPARATION.json'),source_artifact=W['source_artifact'],source_index_SHA256=sha(prepared/'SOURCE_INDEX.json'),months=monthly,minute_rows_per_asset=mins,funding_events=len(events),active_portfolio_days=proof['active_portfolio_days'],CASH_portfolio_days=proof['CASH_portfolio_days'],asset_events=proof['asset_event_days'],target_bytes='ORIGINAL_ALL_FIELDS_UNCHANGED',past_event_clock='PROVEN_SAVED_ORIGINAL_PREFIX',profile_SHA256=profile_sha(),true_minQty='UNKNOWN_FIXED_COARSE_PRESSURE_ONLY',terminal='EXISTING_CALENDAR_END_MINUS6MIN_NATIVE_NOT_PROXY_BOUNDARY')
  print('ACTUAL_FOLLOW_NATIVE_READINESS',key,mins,len(events),proof['active_portfolio_days'],flush=True)
 report=dict(status='PASS_CONDITIONAL_FOLLOW_NATIVE_SOURCE_TARGET_READINESS',source_commit=commit,target_artifact=TARGET_COMMIT,target_packet_SHA256=ix['SHA256'],original_members=members,windows=reports,protocol_SHA256=sha(HERE/'PROTOCOL.json'),new_wallets=0,new_fits=0,provider_downloads=0,seconds=time.monotonic()-began)
 save(state/'READINESS.json',report);assert report['seconds']<120
def targets(key):
 p=HERE/'input'/(key+'.npz');ready=json.loads((HERE/'input/READINESS.json').read_text());assert sha(p)==ready['windows'][key]['target_SHA256'];return exact_targets(key,p)
def cash_ci(r,seed):
 rng=np.random.default_rng(seed);draws=[]
 for _ in range(1000):
  starts=rng.integers(0,len(r),int(np.ceil(len(r)/14)));ids=np.concatenate([(s+np.arange(14))%len(r) for s in starts])[:len(r)];draws.append(float(r[ids].mean()))
 return [float(x) for x in np.quantile(draws,[.025,.975])]
def run(state,key,prepared,commit):
 clean(commit);verify();assert not state.exists();P=proto();W=P['windows'][key];ready=json.loads((HERE/'input/READINESS.json').read_text());assert ready['protocol_SHA256']==sha(HERE/'PROTOCOL.json') and ready['status']=='PASS_CONDITIONAL_FOLLOW_NATIVE_SOURCE_TARGET_READINESS';win=window(key,prepared);d,w=targets(key);state.mkdir(parents=True);began=time.monotonic()
 binding=dict(window=key,arm='FOLLOW',calendar=W['calendar'],science_source_commit=commit,source_artifact=W['source_artifact'],source_index_SHA256=sha(prepared/'SOURCE_INDEX.json'),target_artifact=TARGET_COMMIT,target_archive_SHA256=sha(HERE/'input'/(key+'.npz')),risk_proof_SHA256=sha(HERE/'input/ORIGINAL_TARGET_PREPARATION.json'),readiness_SHA256=sha(HERE/'input/READINESS.json'),protocol_SHA256=sha(HERE/'PROTOCOL.json'),account_class=Closing.VERSION,contract_from_initial_capital=True,quantity_profile_SHA256=profile_sha(),risk_targets='EXACT_ORIGINAL_FOLLOW_NO_RESCALE',end_us=win['end'],terminal_signal_us=win['end']-6*MINUTE)
 save(state/'BINDING.json',binding)
 def factory(_daily,clocks,mode):
  np.testing.assert_array_equal(clocks,d)
  return native.pl.DataFrame([dict(available_us=int(at),symbol=s,target_weight=float(w[i,j])) for i,at in enumerate(d) for j,s in enumerate(SYMBOLS)]),dict(kind='POSTHOC_SEEN_REJECTED20_EVENT_FOLLOW_EXACT_SAVED_TARGET',binding=binding)
 sim=native.NativeDailySimulator(win,'LONG_SHORT',native.COSTS[0],native.UNITS[0],target_factory=factory,account_factory=Closing)
 assert type(sim.account) is Closing and sim.account.nav()==10000 and not sim.persist_cash_close and not sim.final_day_target_zero
 checkpoint(state/'recovery',sim,binding);print('ACTUAL_FOLLOW_NATIVE_WALLET_STARTED',key,'capital',float(sim.account.nav()),'initial_state_hash',sim.state_hash(),'source',commit,flush=True)
 while sim.cursor<win['end'] and sim.stop is None:
  sim.advance_day();days=len(sim.minute_chunks)
  if days%30==0 or sim.cursor==win['end'] or sim.stop is not None:checkpoint(state/'recovery',sim,binding);print('ACTUAL_FOLLOW_NATIVE_PROGRESS',key,days,365,'NAV',float(sim.account.nav()),'status',sim.account.status,flush=True)
  if time.monotonic()-began>P['budget']['wallet_seconds_each'] or sum(p.stat().st_size for p in state.rglob('*') if p.is_file())>P['budget']['STATE_case_bytes']:
   checkpoint(state/'recovery',sim,binding);save(state/'BUDGET_STOP.json',dict(cursor=sim.cursor,rows=sim.rows_written,seconds=time.monotonic()-began));raise RuntimeError('Frozen wallet budget exhausted; genuine partial state retained')
 case=sim.result();summary=case['summary'];audit='PASS';error=None;finance=None
 try:
  _,q=native.episodes(case['trades'],SYMBOLS)
  for s in SYMBOLS:assert q[s]==sim.account.positions[s].quantity
  finance=native.nav_bridge(case['trades'],case['funding'],q,summary['terminal_mark_prices'],sim.account.nav())
 except (ValueError,AssertionError) as exc:audit='FAIL';error=str(exc)
 minute=case['minute'];daily=minute.filter(native.pl.col('close_us')%DAY==0);nav=np.r_[10000.,daily['nav'].to_numpy()];r=np.diff(nav)/nav[:-1];roll=nav[30:]/nav[:-30]-1 if len(nav)>30 else np.array([]);gross=minute['gross_weight'].to_numpy();net=sum(minute[s+'_signed_marked_notional'].to_numpy() for s in SYMBOLS)/minute['nav'].to_numpy()
 metrics=dict(days=len(r),annual_daily_vol=float(r.std(ddof=1)*np.sqrt(365)) if len(r)>1 else None,worst30=float(roll.min()) if len(roll) else None,mean_actual_gross=float(gross.mean()),maximum_actual_gross=float(gross.max()),mean_signed_net=float(net.mean()),maximum_abs_signed_net=float(np.abs(net).max()))
 body={k:case[k] for k in ('trades','funding','rejections','breaches','extrema','target_meta')};body.update(summary=summary,targets=case['targets'].to_dicts(),liquidations=case.get('liquidations',[]));save(state/'ACCOUNT.json',body);daily.write_csv(state/'DAILY.csv')
 f=load('follow_original_minute_fingerprint',ROOT/'research/cs-continuous-economics-20261012/persistence.py');save(state/'MINUTE_NUMERIC.json',dict(columns=f.minute_fingerprint(minute),storage='ORIGINAL_ALL37_BITS_COLUMN_CODEC_NO_REDUNDANT_PARQUET'))
 full=summary['completed_minutes']==525600;paid=bool(summary['terminal_cash_realized']);ci=cash_ci(r,P['bootstrap']['seeds'][key]) if full else None
 gates=dict(full_paid_audited=full and paid and not body['liquidations'] and audit=='PASS',net_positive=full and paid and summary['net_PnL']>0,cash_path_CI=paid and ci is not None and ci[0]>0,risk=full and metrics['annual_daily_vol']<=.12 and summary['all_observation_max_drawdown']<=.12 and metrics['worst30']>=-.10)
 ptr=json.loads((state/'recovery/POINTER.json').read_text());assert ptr['completed_minutes']==summary['completed_minutes'];nt=len(body['targets'])//5;assert len(body['targets'])==nt*5;np.testing.assert_array_equal(np.array([[row['target_weight'] for row in body['targets'][i*5:i*5+5]] for i in range(nt)]),w[:nt])
 report=dict(status='PASS_CONDITIONAL_POSTHOC_FOLLOW_PATH_GATES' if all(gates.values()) else 'STOP_CONDITIONAL_POSTHOC_FOLLOW_PATH_GATES',window=key,arm='FOLLOW',calendar=W['calendar'],science_source_commit=commit,summary=summary,metrics=metrics,gates=gates,bootstrap_marked_path95CI=ci,bootstrap_paid_cash_path95CI=ci if paid else None,inventory_audit=audit,audit_error=error,independent_decimal_NAV_bridge=finance,genuine_state_hash=ptr['state_hash'],rejection_counts=native.rejection_counts(case['rejections']),new_wallets=1,new_fits=0,old_wallet_replays=0,provider_downloads=0,authority='UNCHANGED_CONDITIONAL_NATIVE_SOFTWARE_NOT_AUTHORITATIVE_VENUE_MINQTY_FUNDING_ARRIVAL_MMR',scope='POSTHOC_POSITIVE_CONTROL_FULL_SEEN_YEAR_FRESH10K_NOT_NEW_OOS_NOT_FADE_RESCUE',target_hold='DAILY24H_INTENT_ACTUAL_CLOSE_CAPACITY_LIMITED_FIVE_TRIES_RESIDUALS_RETAINED',terminal='CALENDAR_END_MINUS6MIN_NATIVE_DIFFERS_FROM_PROXY_OWNED_ENDPOINT')
 save(state/'RESULT.json',report);save(state/'TIMING.json',dict(seconds=time.monotonic()-began));print('ACTUAL_FOLLOW_NATIVE_RESULT',key,summary['net_PnL'],paid,report['status'],flush=True)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('phase',choices=['prepare','run']);p.add_argument('--state',type=Path,required=True);p.add_argument('--window',choices=['Y2023','Y2025']);p.add_argument('--prepared',type=Path);p.add_argument('--source-commit',required=True);a=p.parse_args()
 if a.phase=='prepare':prepare(a.state,a.source_commit)
 else:run(a.state,a.window,a.prepared,a.source_commit)
