"""Original .60/.30/.10 charged native preview, independent immutable corners.
Partial/refused native forecasts are invalid, with real executed/residual witnesses.
No live account is modified, no fills are fabricated, no risk cap is raised.
"""
from copy import deepcopy
from decimal import Decimal as D
from itertools import product
import math
import numpy as np
from candidate import S,vector

class ChargedPreview:
 def __init__(self,account,*,prices,covariance,pending,previous_quote,event_us,signal_us,covariance_available_us,quote_available_us):
  self.account=account;self.actual={s:account.positions[s].quantity for s in S};self.prices=vector(prices);self.pending=vector(pending);self.quote=vector(previous_quote);self.event_us=event_us;self.signal_us=signal_us;self.quote_us=quote_available_us
  clocks=(event_us,signal_us,covariance_available_us,quote_available_us)
  if any(type(x) is not int or x<0 for x in clocks) or not covariance_available_us<=signal_us<event_us or quote_available_us>signal_us:raise ValueError('PAST_COVARIANCE_PRIOR_QUOTE_AND_ORIGINAL_CLOCK_REQUIRED')
  if tuple(account.symbols)!=S or any(x<=0 for x in self.prices.values()) or any(x<0 for x in self.quote.values()):raise ValueError('EXACT_SHARED_CORE5_INPUTS')
  c=account.config
  if (c.max_gross_weight,c.max_asset_weight,c.leverage,c.fee_rate,c.half_spread_bps,c.slippage_bps)!=(D('.6'),D('.3'),D('1'),D('.00055'),D('4'),D('4')):raise ValueError('EXACT_ORIGINAL_BASE27_060_030_1X')
  self.cov=np.asarray(covariance,dtype=np.float64)
  if self.cov.shape!=(5,5) or not np.isfinite(self.cov).all() or not np.allclose(self.cov,self.cov.T,atol=1e-12,rtol=0) or np.linalg.eigvalsh(self.cov).min() < -1e-15:raise ValueError('FINITE_PSD_ANNUAL_COVARIANCE_REQUIRED')
  self.before=account.snapshot()
 def _risk(self,probe):
  nav=probe.nav()
  if nav<=0:return {'valid':False,'reason':'NONPOSITIVE_CHARGED_NAV'}
  # ACTUAL executed quantities, never the requested corner vector.
  weights=np.asarray([float(probe.positions[s].quantity*probe._mark(s)/nav) for s in S]);variance=float(weights@self.cov@weights);gross=float(np.abs(weights).sum());asset=float(np.abs(weights).max());sigma=math.sqrt(max(variance,0))
  return {'valid':gross<=.6+1e-12 and asset<=.3+1e-12 and sigma<=.1+1e-12,'gross':gross,'max_asset':asset,'sigma':sigma,'charged_NAV':str(nav),'free_cash':str(probe.free_cash),'actual_executed_positions':{s:str(probe.positions[s].quantity) for s in S}}
 def _charged(self,target,tag):
  callback=getattr(self.account,'liquidation_callback',None);memo={id(self.account.instrument_profiles):self.account.instrument_profiles}
  if callback is not None:memo[id(callback)]=None
  probe=deepcopy(self.account,memo);legs=[];requests=[];capacity={s:self.quote[s]*D('.001')/self.prices[s] for s in S}
  for phase in ('REDUCE','INCREASE'):
   for s in S:
    q=probe.positions[s].quantity;delta=target[s]-q
    if not delta:continue
    reducing=bool(q and q*delta<0)
    if phase=='REDUCE' and not reducing or phase=='INCREASE' and reducing:continue
    requested=min(abs(delta),abs(q)) if phase=='REDUCE' else abs(delta)
    before=len(probe.trades);receipt=probe.execute_fill(s,'BUY' if delta>0 else 'SELL',requested,self.event_us,self.signal_us,tag+':'+phase+':'+s,execution_mid_price=self.prices[s],quote_available_us=self.quote_us,available_quantity=capacity[s],reduce_only=phase=='REDUCE')
    rows=probe.trades[before:];executed=sum((D(row['decimal_strings']['quantity']) for row in rows),D(0));capacity[s]-=executed;legs.extend(rows)
    residual=requested-executed;w={'phase':phase,'symbol':s,'requested_quantity':str(requested),'executed_quantity':str(executed),'remaining_pending_quantity':str(residual),'pending_side':'BUY' if delta>0 else 'SELL','native_receipt':receipt,'actual_after':self._risk(probe)};requests.append(w)
    if residual:
     # Strictly refuse the candidate instead of pretending requested risk was
     # executed or silently dropping the real unfilled residual endpoint.
     return None,{'reason':'NATIVE_REFUSAL_OR_PARTIAL_WITH_RESIDUAL_PENDING','requests':requests,'legs':legs,'actual_executed_risk':w['actual_after']}
  return probe,{'requests':requests,'legs':legs,'funding_before_preview_preserved':probe.funding==self.account.funding}
 def evaluate(self,target,lam):
  target=vector(target);assert self.account.snapshot()==self.before
  endpoints=[tuple(dict.fromkeys((self.actual[s],self.pending[s],target[s]))) for s in S];corners=[]
  for index,point in enumerate(product(*endpoints)):
   probe,charge=self._charged(dict(zip(S,point)),'PREVIEW:'+str(lam)+':'+str(index))
   if probe is None:return {'allowed':False,**charge,'corners_checked':corners}
   risk=self._risk(probe);corners.append({'requested_endpoint':{s:str(q) for s,q in zip(S,point)},'risk':risk,'charge':charge})
   if not risk['valid']:return {'allowed':False,'reason':'CHARGED_ACTUAL_PENDING_060_030_010_CAP','corners_checked':corners}
  assert self.account.snapshot()==self.before
  return {'allowed':True,'reason':'ALL_NATIVE_CHARGED_CORNERS_VALID','corners_checked':corners}
