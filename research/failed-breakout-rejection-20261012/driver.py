"""Fixed causal rejection targets and four independent full-calendar references."""
import argparse,json,subprocess,time
from pathlib import Path
import numpy as np
from core import DAY,SYMBOLS,targets,reference,paired_ci
from source import ROOT,HERE,sha,save
def prepare(state,source):
 assert not state.exists();state.mkdir(parents=True);begin=time.monotonic();src=json.loads((source/'SOURCE_PROJECTION.json').read_text());assert src['status']=='PASS_EXACT_REAL_OHLC_TWO_YEAR_SOURCE' and src['source_protocol_SHA256']==sha((HERE/'PROTOCOL.json').read_bytes());proof={}
 for year in (2023,2025):
  p=source/f'Y{year}_SOURCE.npz';assert sha(p.read_bytes())==src['years'][str(year)]['SOURCE_SHA256']
  with np.load(p,allow_pickle=False) as z:
   assert tuple(z['symbol_order'])==SYMBOLS;d=z['decision_us'];t=z['OHLC_available_us'];h=z['OHLC_high'];l=z['OHLC_low'];c=z['OHLC_close'];r=z['OHLC_ready'];rt=z['close_available_us'];rp=z['close']
   out,rows=targets(t,h,l,c,r,rt,rp,d);cut=d[180]
   for mode in ('FUTURE_OHLC','FUTURE_NAN','FUTURE_RISK','FUTURE_RISK_NAN'):
    ah=h.copy();al=l.copy();ac=c.copy();ar=r.copy();ap=rp.copy()
    if mode=='FUTURE_OHLC':ah[t>cut]*=100;al[t>cut]*=100;ac[t>cut]*=100
    if mode=='FUTURE_NAN':ah[t>cut]=np.nan;al[t>cut]=np.nan;ac[t>cut]=np.nan;ar[t>cut]=False
    if mode=='FUTURE_RISK':ap[rt>cut]*=np.arange(2,7)
    if mode=='FUTURE_RISK_NAN':ap[rt>cut]=np.nan
    # Only the historical prefix is needed in missing-risk probes; no future
    # output is consulted, or used to filter a prior target.
    alt,_=targets(t,ah,al,ac,ar,rt,ap,d[d<=cut])
    for arm in out:np.testing.assert_array_equal(alt[arm],out[arm][d<=cut])
   arrays={k:z[k] for k in ('symbol_order','decision_us','p0','p1','funding_per_unit','owned_interval_valid')};np.savez_compressed(state/f'Y{year}.npz',**arrays,**out)
  reasons={reason:sum(row['reasons'].count(reason) for row in rows) for reason in sorted({x for row in rows for x in row['reasons']})};asset_events=int(np.count_nonzero(out['FADE']));active_days=int(np.any(out['FADE']!=0,axis=1).sum());assert reasons.get('UNKNOWN_SOURCE',0)==0 and sum(reasons.values())==1825
  proof[str(year)]=dict(INPUTS_SHA256=sha((state/f'Y{year}.npz').read_bytes()),SOURCE_SHA256=src['years'][str(year)]['SOURCE_SHA256'],rows=365,active_portfolio_days=active_days,asset_event_days=asset_events,CASH_portfolio_days=365-active_days,event_reason_asset_day_counts=reasons,source_unknown_asset_days=0,exact_opposite_target_same_risk_and_gross='BIT_EXACT',future_OHLC_prices_NaN_and_risk_prices_NaN_prefix='EXACT',risk=rows)
  print('ACTUAL_REJECTED_BREAK_TARGETS',year,365,active_days,asset_events,'CASH',365-active_days,flush=True)
 save(state/'PREPARATION.json',dict(status='PASS_TWO_YEAR_CAUSAL_REJECTED_BREAK_TARGETS',years=proof,SOURCE_PROJECTION_SHA256=sha((source/'SOURCE_PROJECTION.json').read_bytes()),protocol_SHA256=sha((HERE/'PROTOCOL.json').read_bytes()),new_fits=0,new_references=0,provider_GETs=0,seconds=time.monotonic()-begin));assert time.monotonic()-begin<60
def run(state,prepared,commit):
 assert not state.exists() and not subprocess.check_output(['git','status','--porcelain'],cwd=ROOT);assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT).decode().strip()==commit
 state.mkdir(parents=True);begin=time.monotonic();prep=json.loads((prepared/'PREPARATION.json').read_text());assert prep['protocol_SHA256']==sha((HERE/'PROTOCOL.json').read_bytes());years={}
 for year,seed in ((2023,811744),(2025,811745)):
  proof=prep['years'][str(year)];p=prepared/f'Y{year}.npz';assert sha(p.read_bytes())==proof['INPUTS_SHA256'];arms={};daily={}
  with np.load(p,allow_pickle=False) as z:
   d=z['decision_us'];assert tuple(z['symbol_order'])==SYMBOLS and len(d)==365 and np.all(np.diff(d)==DAY)
   for arm in ('FOLLOW','FADE'):
    arms[arm],daily[arm]=reference(d,z[arm],z['p0'],z['p1'],z['funding_per_unit'],z['owned_interval_valid']);save(state/f'Y{year}_{arm}.json',dict(summary=arms[arm],rows=daily[arm],symbol_order=SYMBOLS,source_commit=commit));print('ACTUAL_REJECTED_BREAK_REFERENCE',year,arm,arms[arm]['status'],arms[arm]['days'],arms[arm]['net_USDT'],flush=True)
  full=all(a['hypothetical_cost_terminal'] and a['days']==365 for a in arms.values());increment=None;ci=None
  if full:
   increment=arms['FADE']['net_USDT']-arms['FOLLOW']['net_USDT'];delta=np.array([r['daily_return'] for r in daily['FADE']])-np.array([r['daily_return'] for r in daily['FOLLOW']]);ci=paired_ci(delta,seed)
  a=arms['FADE'];gates=dict(source_identity_causal_risk_proofs=True,full_pair=full,support=proof['active_portfolio_days']>=50 and proof['asset_event_days']>=100,net_positive=bool(full and a['net_USDT']>0),increment_positive=bool(increment is not None and increment>0),paired95CI_lower_positive=bool(ci is not None and ci[0]>0),risk=bool(full and a['annual_vol']<=.12 and a['drawdown']<=.12 and a['worst30']>=-.10))
  exante={arm:dict(cap_bound_days=sum(r[arm]['cap_bound'] for r in proof['risk']),mean_active_post_sigma=float(np.mean([r[arm]['post_sigma'] for r in proof['risk'] if r[arm]['reason']!='INTRINSIC_CASH'])) if proof['active_portfolio_days'] else None,maximum_shortfall=max(r[arm]['shortfall'] for r in proof['risk'])) for arm in arms}
  years[str(year)]=dict(arms=arms,gates=gates,increment_USDT=increment,paired_daily_increment95CI=ci,bootstrap_seed=seed,active_portfolio_days=proof['active_portfolio_days'],asset_event_days=proof['asset_event_days'],CASH_portfolio_days=proof['CASH_portfolio_days'],event_reasons=proof['event_reason_asset_day_counts'],exante=exante);print('ACTUAL_REJECTED_BREAK_GATE',year,increment,ci,gates,flush=True)
 out=dict(status='PASS_FIXED_REJECTED_BREAK_SCREEN_NATIVE_READINESS_REQUIRED' if all(all(r['gates'].values()) for r in years.values()) else 'STOP_FIXED_REJECTED_BREAK_SCREEN',years=years,source_commit=commit,PREPARATION_SHA256=sha((prepared/'PREPARATION.json').read_bytes()),protocol_SHA256=prep['protocol_SHA256'],scientific_recipes=1,new_conditional_daily_references=4,new_native_wallets=0,new_fits=0,provider_GETs=0,old_financial_replays=0,authority='ACTUAL_HISTORICAL_OPEN_AND_FUNDING_FULLFILL_QUANTITY_PROXY_NOT_NATIVE_NET_INCOME',risk='EXACT_OPPOSITE_EXANTE_WEIGHT_RISK_ACTIVITY_GROSS_REALIZED_RISK_REPORTED_SEPARATELY',calendar_role='2023_AND_2025_SEEN_DEVELOPMENT_NOT_UNSEEN',seconds=time.monotonic()-begin);save(state/'RESULT.json',out);assert time.monotonic()-begin<60;print('ACTUAL_REJECTED_BREAK_RESULT',out['status'],flush=True)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('phase',choices=['prepare','run']);p.add_argument('--state',type=Path,required=True);p.add_argument('--source',type=Path);p.add_argument('--prepared',type=Path);p.add_argument('--source-commit');a=p.parse_args()
 if a.phase=='prepare':prepare(a.state,a.source)
 else:run(a.state,a.prepared,a.source_commit)
