"""Original CS/risk/proxy APIs, explicit daily price-only reference scenario."""
import argparse,importlib.util,json,time
from pathlib import Path
import numpy as np
from source import HERE,ROOT,DAY,CORE5,sha,save
from scripts.research.public_cross_section_momentum import public_targets
from modules.collector_research.pipeline.economics import proxy_step
spec=importlib.util.spec_from_file_location('unchanged_wide_risk_API',ROOT/'research/portfolio-risk-budget-20261012/risk_budget.py');risk=importlib.util.module_from_spec(spec);spec.loader.exec_module(risk)

def targets(t,p,d,names,allowed):
 raw,diag=public_targets(p,t,d,names,allowed);out=np.zeros_like(raw);proof=[]
 for i,at in enumerate(d):
  held=np.flatnonzero(raw[i]!=0);assert len(held)<=4,'Originaltop2/bottom2 rule';w=np.zeros(5);cov=np.zeros((5,5))
  if len(held):
   k=int(np.searchsorted(t,at));assert t[k]==at;kprice=p[k-30:k+1][:,held];assert np.isfinite(kprice).all() and (kprice>0).all();r=np.diff(kprice,axis=0)/kprice[:-1];cov[:len(held),:len(held)]=np.atleast_2d(np.cov(r,rowvar=False,ddof=1))*365;w[:len(held)]=raw[i,held]
  scaled,q=risk.scale(w,cov);out[i,held]=scaled[:len(held)];proof.append(dict(decision_us=int(at),held_symbol_order=[names[j] for j in held],structural_cash_padding=5-len(held),zero_padding_is_unallocated_cash_not_missing_price_estimate=True,controller=q))
 return out,diag,proof

def quantity_proxy(d,w,p0,p1):
 nav=10000.;q=np.zeros(w.shape[1]);rows=[];stop=None;last=None
 for i,at in enumerate(d):
  before=nav
  try:after,nq,cost,_excluded_fund,notional,pnl=proxy_step(nav,q,w[i],p0[i],p1[i],np.zeros(len(q)),np.isfinite(p0[i])&np.isfinite(p1[i]),.00135)
  except ValueError as e:stop=dict(decision_us=int(at),reason=str(e));break
  nav,q=after,nq;last=p1[i].copy();rows.append(dict(signal_available_us=int(at-DAY),execution_open_boundary_us=int(at),next_open_boundary_us=int(at+DAY),conservative_open_label_mature_us=int(at+2*DAY),nav_before=before,nav_after=nav,daily_return=nav/before-1,price_pnl=pnl,trading_cost_proxy=cost,turnover_USDT=notional))
 terminal=0.;closed=False
 if stop is None:
  own=q!=0;assert last is not None and np.isfinite(last[own]).all() and (last[own]>0).all();terminal=float(np.dot(np.abs(q[own]),last[own]))*.00135
  if nav-terminal<=0:stop=dict(decision_us=int(d[-1]),reason='HYPOTHETICAL_TERMINAL_COST_EXHAUSTS_NAV')
  else:nav-=terminal;rows[-1]['nav_after']=nav;rows[-1]['trading_cost_proxy']+=terminal;rows[-1]['daily_return']=nav/rows[-1]['nav_before']-1;q=np.zeros_like(q);closed=True
 return dict(status='COMPLETE_PRICE_ONLY_DAILY_COST_PROXY' if closed else 'STOP_DAILY_OWNED_SOURCE_OR_NAV_GAP',planned_days=len(d),completed_days=len(rows),hypothetical_cost_terminal=closed,terminal_cost_proxy_USDT=terminal,last_marked_NAV=nav,price_only_net_trading_cost_proxy_USDT=nav-10000 if closed else None,positions=q.tolist(),stop=stop,funding_channel='EXCLUDED_BY_DESIGN_NOT_OBSERVED_ZERO',execution='NEXT_DAY_ACTUAL_DAILY_OPEN_LAG1_FULLFILL_PROXY_NOT_MINUTE_NATIVE',margin_and_native_filters='NOT_SIMULATED_NOT_ACCOUNT_QUALIFICATION'),rows

def prepare(state,source):
 assert not state.exists();state.mkdir(parents=True);meta=json.loads((source/'SOURCE.json').read_text());assert sha(source/'INPUTS.npz')==meta['INPUTS_SHA256'];began=time.monotonic();pool=json.loads((HERE/'input/POOL.json').read_text())
 assert meta['pool_SHA256']==sha(HERE/'input/POOL.json') and meta['SOURCE_PROTOCOL_SHA256']==sha(HERE/'SOURCE_PROTOCOL.json') and meta['EXECUTION_TIMING_AMENDMENT_SHA256']==sha(HERE/'EXECUTION_TIMING_AMENDMENT.json')
 admitted={'2022-11','2022-12'}|{f'2023-{m:02d}' for m in range(1,13)}
 assert all(r['symbol'] in set(pool['symbols'])-set(CORE5) and (r['period'] in admitted and not r['daily'] or r['period']=='2024-01-01' and r['daily']) for r in meta['source_records'])
 with np.load(source/'INPUTS.npz',allow_pickle=False) as z:t=z['close_available_us'];p=z['close'];opening=z['execution_open'];e=z['execution_us'];d=z['signal_available_us'];names=tuple(z['symbol_order']);wide=z['wide_allowed'];core=z['core_allowed']
 assert names==tuple(CORE5)+tuple(sorted(set(pool['symbols'])-set(CORE5))) and [s for s,v in zip(names,wide) if v] and set(s for s,v in zip(names,wide) if v)==set(pool['symbols']) and tuple(s for s,v in zip(names,core) if v)==CORE5
 assert len(e)==len(d)==365 and np.all(e==d+DAY) and np.all(e>d) and np.all(np.diff(e)==DAY)
 arms={};proof={}
 for name,allowed in [('CORE5',core),('WIDE20',wide)]:
  selected=[s for s,on in zip(names,allowed) if on];w,diag,riskproof=targets(t,p,d,names,selected);cut=d[180]
  for mode in ('PRICES','NAN_AVAILABILITY'):
   future=p.copy()
   if mode=='PRICES':future[t>cut]*=np.arange(2,2+len(names))
   else:future[t>cut]=np.nan
   alt,adiag,_=targets(t,future,d,names,selected);np.testing.assert_array_equal(alt[d<=cut],w[d<=cut]);assert [r for at,r in zip(d,adiag['current_eligible']) if at<=cut]==[r for at,r in zip(d,diag['current_eligible']) if at<=cut]
  assert not w[:,~allowed].any()
  for at,eligible in zip(d,diag['current_eligible']):
   k=int(np.searchsorted(t,at));expected=allowed&np.isfinite(p[k-30:k+1]).all(0)&(p[k-30:k+1]>0).all(0);np.testing.assert_array_equal(eligible,expected)
  arms[name]=w;proof[name]=dict(diag=diag,risk=riskproof,future_price_and_NaN_mask_prefix_invariance='EXACT',cash_days=int((np.abs(w).sum(1)==0).sum()),cap_bound_days=sum(r['controller']['cap_bound'] for r in riskproof),mean_post_sigma=float(np.mean([r['controller']['post_sigma'] for r in riskproof])),mean_risk_shortfall=float(np.mean([r['controller']['shortfall'] for r in riskproof])),maximum_risk_shortfall=max(r['controller']['shortfall'] for r in riskproof),risk_comparison='SAME_POLICY_NOT_EXACT_REALIZED_RISK_MATCH')
 # A sparse portfolio's nonzero-weight submatrix has exactly the same risk
 # as the fullN covariance. PaddingunusedCASH is a legacyshape API adapter.
 with np.load(ROOT/'research/portfolio-risk-budget-20261012/input/P1.npz',allow_pickle=False) as z:k=np.searchsorted(z['decision_us'],d[0]);assert z['decision_us'][k]==d[0];first=z['CS_MATCHED'][k].copy()
 with np.load(ROOT/'research/portfolio-risk-budget-20261012/input/P2.npz',allow_pickle=False) as z:np.testing.assert_array_equal(z['decision_us'][:364],d[1:]);golden=np.vstack([first,z['CS_MATCHED'][:364]]);np.testing.assert_allclose(arms['CORE5'][:,:5],golden,rtol=0,atol=1e-12);golden_error=float(np.max(np.abs(arms['CORE5'][:,:5]-golden)))
 assert not arms['CORE5'][:,5:].any();k=np.searchsorted(t,e);np.testing.assert_array_equal(t[k],e);np.savez_compressed(state/'TARGETS.npz',signal_available_us=d,execution_us=e,symbol_order=np.array(names),p0=opening[k],p1=opening[k+1],**arms);save(state/'PROOF.json',proof)
 checks=dict(frozen_pool_membership=True,source_SHA_and_admitted_periods=True,signal_strictly_before_next_day_actual_open=True,mature_label_after_execution=True,eligible_from_past31_only=True,future_prices_and_NaNs_prefix=True,CORE5_original_controller_golden=True)
 save(state/'PREPARATION.json',dict(status='PASS_FROZEN_CS21_TWO_ARM_CAUSAL_DAILY_TARGETS',SOURCE_SHA256=sha(source/'SOURCE.json'),INPUTS_SHA256=sha(source/'INPUTS.npz'),POOL_SHA256=sha(HERE/'input/POOL.json'),TARGETS_SHA256=sha(state/'TARGETS.npz'),PROOF_SHA256=sha(state/'PROOF.json'),machine_promotion_checks=checks,CORE5_current_native_intents_max_error=golden_error,future_prefix='EXACT_PRICE_AND_NAN_BOTH_ARMS',changed_target_days=int(np.any(arms['WIDE20']!=arms['CORE5'],axis=1).sum()),new_fits=0,new_proxy_scores=0,new_native_wallets=0,seconds=time.monotonic()-began));print('ACTUAL_WIDE_CS_DAILY_TARGETS_PREPARED',len(d),int(np.any(arms['WIDE20']!=arms['CORE5'],axis=1).sum()),flush=True)

def run(state,prepared):
 assert not state.exists();state.mkdir(parents=True);began=time.monotonic();prep=json.loads((prepared/'PREPARATION.json').read_text());assert sha(prepared/'TARGETS.npz')==prep['TARGETS_SHA256'] and sha(prepared/'PROOF.json')==prep['PROOF_SHA256'] and sha(HERE/'input/POOL.json')==prep['POOL_SHA256'];reports={};daily={};provenance=all(prep['machine_promotion_checks'].values());assert provenance
 with np.load(prepared/'TARGETS.npz',allow_pickle=False) as z:
  d=z['execution_us'];signals=z['signal_available_us'];assert np.all(signals<d) and np.all(signals+DAY==d);p0=z['p0'];p1=z['p1'];names=tuple(z['symbol_order'])
  for arm in ('CORE5','WIDE20'):
   report,rows=quantity_proxy(d,z[arm],p0,p1);reports[arm]=report;daily[arm]=rows;save(state/(arm+'_ACCOUNT.json'),dict(summary=report,rows=rows,symbol_order=names));print('ACTUAL_WIDE_CS_PRICE_ONLY_PROXY',arm,report['status'],report['completed_days'],report['price_only_net_trading_cost_proxy_USDT'],flush=True)
 full=all(reports[a]['completed_days']==365 and reports[a]['hypothetical_cost_terminal'] for a in reports);ci=None;metrics=None;increment=None
 if full:
  a=np.array([r['daily_return'] for r in daily['WIDE20']]);b=np.array([r['daily_return'] for r in daily['CORE5']]);delta=a-b;rng=np.random.default_rng(811741);draws=[]
  for _ in range(1000):
   starts=rng.integers(0,len(a),int(np.ceil(len(a)/14)));idx=((starts[:,None]+np.arange(14))%len(a)).ravel()[:len(a)];draws.append(float(delta[idx].mean()))
  ci=[float(v) for v in np.quantile(draws,[.025,.975])];metrics={}
  for arm in ('CORE5','WIDE20'):
   returns=np.array([r['daily_return'] for r in daily[arm]]);nav=np.r_[10000.,[r['nav_after'] for r in daily[arm]]];metrics[arm]=dict(daily_reference_annual_vol=float(returns.std(ddof=1)*np.sqrt(365)),drawdown=float(np.max(1-nav/np.maximum.accumulate(nav))),worst30=float(np.min(nav[30:]/nav[:-30]-1)))
  increment=reports['WIDE20']['price_only_net_trading_cost_proxy_USDT']-reports['CORE5']['price_only_net_trading_cost_proxy_USDT']
 gates=dict(causal_identity_membership_mask_proofs=provenance,both_full_no_owned_gap=full,wide_price_only_net_positive=bool(full and reports['WIDE20']['price_only_net_trading_cost_proxy_USDT']>0),paired_price_only_increment_positive=bool(full and increment>0),paired_daily95CI_lower_positive=bool(ci is not None and ci[0]>0),risk=bool(metrics is not None and metrics['WIDE20']['daily_reference_annual_vol']<=.12 and metrics['WIDE20']['drawdown']<=.12 and metrics['WIDE20']['worst30']>=-.10))
 exante=json.loads((prepared/'PROOF.json').read_text());exante={a:{k:v for k,v in exante[a].items() if k not in ('diag','risk')} for a in reports}
 out=dict(status='PASS_PRICE_ONLY_SCREEN_NEXT_NATIVE_SOURCE_READINESS_REQUIRED' if all(gates.values()) else 'STOP_FIXED_ARCHIVE_TOP20_DAILY_SCREEN',arms=reports,gates=gates,paired_price_only_net_increment_USDT=increment,paired_daily_increment95CI=ci,per_arm_reference_metrics=metrics,per_arm_exante_risk=exante,risk_comparison='SAME_RISK_POLICY_NOT_EXACT_REALIZED_RISK_MATCH',machine_promotion_proofs=prep['machine_promotion_checks'],calendar_execution=['2023-01-01','2024-01-01'],signal_first_us=int(signals[0]),signal_last_us=int(signals[-1]),terminal_open_reference_us=int(d[-1]+DAY),conservative_terminal_open_label_maturity_us=int(d[-1]+2*DAY),natural_days=365,bootstrap=dict(block_days=14,draws=1000,seed=811741),new_price_only_reference_calls=2,new_native_wallets=0,old_native_replays=0,new_fits=0,provider_GETs=0,capital_per_independent_shared_reference=10000,authority='COVERED_ARCHIVE_PRESELECTED_KNOWN_HISTORY_NEXT_OPEN_PRICE_ONLY_FULLFILL_NOT_PIT_GLOBAL_UNBIASED_OR_NATIVE_NET_INCOME',seconds=time.monotonic()-began);save(state/'RESULT.json',out);print('ACTUAL_WIDE_CS_SCREEN_RESULT',out['status'],increment,ci,gates,flush=True)

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('phase',choices=['prepare','run']);p.add_argument('--state',type=Path,required=True);p.add_argument('--source',type=Path);p.add_argument('--prepared',type=Path);a=p.parse_args()
 if a.phase=='prepare':prepare(a.state,a.source)
 else:run(a.state,a.prepared)
