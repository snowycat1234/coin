"""Reference-price expert, original portfolio ranking/risk APIs."""
import numpy as np
from modules.transformer_v2.portfolio import market_neutral
from scripts.investment.public_sma_perpetual import signed_risk_weights
DAY=86400000000;WEEK=7*DAY;ANCHOR=1704067200000000
SYMBOLS=('BTCUSDT','ETHUSDT','SOLUSDT','XRPUSDT','DOGEUSDT')
def targets(clock,price,decisions):
 t=np.asarray(clock,np.int64);p=np.asarray(price,float);d=np.asarray(decisions,np.int64)
 if p.shape!=(len(t),5) or np.any(np.diff(t)!=DAY) or np.any(np.diff(d)!=DAY):raise ValueError('Dense actualdailyclock andexactCORE5 order')
 first=ANCHOR+(int(d[0])-ANCHOR)//WEEK*WEEK;raw=np.zeros(5);out=np.zeros((len(d),5));idx={int(at):i for i,at in enumerate(d)};proof=[]
 for at in range(first,int(d[-1])+DAY,DAY):
  k=int(np.searchsorted(t,at));eligible=np.zeros(5,bool);score=np.full(5,np.nan);returns=None
  if 364<=k<len(t) and t[k]==at:
   history=p[k-364:k+1];eligible=np.isfinite(history).all(0)&(history>0).all(0);score[eligible]=p[k,eligible]/np.max(history[:,eligible],axis=0)
   returns=np.diff(p[k-30:k+1],axis=0)/p[k-30:k]
  if (at-ANCHOR)%WEEK==0:raw=market_neutral(score[None,:],eligible[None,:],k=2,gross=.6)[0]
  raw[~eligible]=0;held=np.flatnonzero(raw!=0);row=np.zeros(5)
  if len(held):row[held],_=signed_risk_weights(raw[held],returns[:,held],annual_vol_target=.10)
  if at in idx:
   out[idx[at]]=row;proof.append(dict(decision_us=at,source_latest_close_available_us=at,current_eligible=eligible.tolist(),reference_score=[float(v) if np.isfinite(v) else None for v in score],reference_completed_closes=365,weekly_rank_event=(at-ANCHOR)%WEEK==0))
 return out,proof
def same_match_and_mix(cs,hold,covariances,scale):
 cs=np.asarray(cs,float);hold=np.asarray(hold,float);cov=np.asarray(covariances,float);assert cs.shape==hold.shape and cov.shape==(len(cs),5,5);out=np.zeros_like(cs);proof=[]
 for i,c in enumerate(cov):
  sc=float(np.sqrt(max(0.,cs[i]@c@cs[i])));sv=float(np.sqrt(max(0.,hold[i]@c@hold[i])));common=min(.10,sc,sv)
  left=cs[i]*(common/sc) if sc>0 else np.zeros(5);right=hold[i]*(common/sv) if sv>0 else np.zeros(5)
  mixed=.5*left+.5*right;out[i],risk=scale(mixed,c);proof.append(dict(CS_sigma=sc,HOLD_sigma=sv,matched_common_sigma=common,joint=risk))
 return out,proof
