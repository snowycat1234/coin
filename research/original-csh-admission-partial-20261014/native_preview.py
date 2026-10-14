"""Charged synthetic/native-account oracle. Original account bytes are untouched.
Not a replacement account, source loader, scheduler or historical launcher.
"""
from copy import deepcopy
from decimal import Decimal as D,localcontext
from itertools import product
import math
import numpy as np
from candidate import S,vector

class ChargedPreview:
 def __init__(self,account,*,prices,covariance,pending,previous_quote,event_us,signal_us):
  self.account=account;self.actual={s:account.positions[s].quantity for s in S};self.prices=vector(prices);self.pending=vector(pending);self.quote=vector(previous_quote);self.event_us=event_us;self.signal_us=signal_us
  if tuple(account.symbols)!=S or any(x<=0 for x in self.prices.values()) or any(x<0 for x in self.quote.values()):raise ValueError('BOUND_SHARED_CORE5_INPUTS_REQUIRED')
  if type(event_us) is not int or type(signal_us) is not int or not 0<=signal_us<event_us:raise ValueError('ORIGINAL_CAUSAL_EXECUTION_CLOCK_REQUIRED')
  c=account.config
  if (c.max_gross_weight,c.max_asset_weight,c.leverage,c.fee_rate,c.half_spread_bps,c.slippage_bps)!=(D('.6'),D('.3'),D('1'),D('.00055'),D('4'),D('4')):raise ValueError('ORIGINAL_BASE27_060_030_1X_REQUIRED')
  self.cov=np.asarray(covariance,dtype=np.float64)
  if self.cov.shape!=(5,5) or not np.isfinite(self.cov).all() or not np.allclose(self.cov,self.cov.T,rtol=0,atol=1e-12) or np.linalg.eigvalsh(self.cov).min() < -1e-15:raise ValueError('FINITE_SYMMETRIC_PSD_PAST_COVARIANCE_REQUIRED')
  self.before=account.snapshot()
 def _charged(self,target,tag):
  probe=deepcopy(self.account);legs=[];capacity={s:self.quote[s]*D('.001')/self.prices[s] for s in S}
  # Existing reduction-before-increase precedence; one shared capacity per asset.
  for phase in ('REDUCE','INCREASE'):
   for s in S:
    q=probe.positions[s].quantity;delta=target[s]-q
    if not delta:continue
    reducing=bool(q and q*delta<0)
    if phase=='REDUCE' and not reducing:continue
    if phase=='INCREASE' and reducing:continue
    quantity=min(abs(delta),abs(q)) if phase=='REDUCE' else abs(delta)
    step=probe.instrument_profiles[s].quantity_step;quantity=probe._floor(s,quantity)
    if quantity==0:continue
    if quantity>capacity[s]:return None,{'reason':'SHARED_PRIOR_MINUTE_CAPACITY','phase':phase,'symbol':s}
    before=len(probe.trades)
    receipt=probe.execute_fill(s,'BUY' if delta>0 else 'SELL',quantity,self.event_us,self.signal_us,tag+':'+phase+':'+s,execution_mid_price=self.prices[s],quote_available_us=self.signal_us,reduce_only=phase=='REDUCE')
    if len(probe.trades)==before:return None,{'reason':'NATIVE_CHARGED_FILL_REFUSAL','phase':phase,'symbol':s,'receipt':receipt}
    capacity[s]-=quantity;legs.extend(probe.trades[before:])
  return probe,{'legs':legs,'funding_before_preview_preserved':probe.funding==self.account.funding}
 def evaluate(self,target,lam):
  target=vector(target);assert self.account.snapshot()==self.before,'ACTUAL_STATE_CHANGED_DURING_SELECTION'
  endpoints=[tuple(dict.fromkeys((self.actual[s],self.pending[s],target[s]))) for s in S];witness=[]
  for index,point in enumerate(product(*endpoints)):
   corner=dict(zip(S,point));probe,charge=self._charged(corner,'PREVIEW:'+str(lam)+':'+str(index))
   if probe is None:return {'allowed':False,**charge,'corners_checked':witness}
   nav=probe.nav()
   if nav<=0:return {'allowed':False,'reason':'NONPOSITIVE_CHARGED_NAV'}
   weights=np.asarray([float(corner[s]*self.prices[s]/nav) for s in S]);gross=float(np.abs(weights).sum());asset=float(np.abs(weights).max());variance=float(weights@self.cov@weights);sigma=math.sqrt(max(variance,0))
   row={'gross':gross,'max_asset':asset,'sigma':sigma,'charged_NAV':str(nav),'free_cash':str(probe.free_cash)};witness.append(row)
   if gross>.6+1e-12 or asset>.3+1e-12 or sigma>.1+1e-12:return {'allowed':False,'reason':'CHARGED_ACTUAL_PENDING_060_030_010_CAP','corners_checked':witness}
  assert self.account.snapshot()==self.before
  return {'allowed':True,'reason':'ALL_CHARGED_NATIVE_SHARED_WALLET_AND_PENDING_CORNERS_PASS','corners_checked':witness}
 def baseline_preview(self,target):return self._charged(vector(target),'ACTUAL_BASELINE')
