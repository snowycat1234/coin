"""Synthetic only: participation, side reversal, actual cost and unchanged inputs."""
from copy import deepcopy
from decimal import Decimal
import numpy as np
from runtime import finance,SYMBOLS,DAY
from execution import capacity_half_class

def numeric_strings(value):
 if isinstance(value,dict):return {k:numeric_strings(v) for k,v in value.items()}
 if isinstance(value,list):return [numeric_strings(v) for v in value]
 if isinstance(value,str):
  try:return Decimal(value)
  except Exception:return value
 return value

def fixture(port):
 start=1704067200000000;times=np.arange(start,start+2*DAY,60000000,dtype=np.int64)
 market={s:dict(open=np.full(len(times),100.),close=np.full(len(times),100.),mark=np.full(len(times),100.),quote_volume=np.full(len(times),1_000_000.)) for s in SYMBOLS}
 daily=port.native.pl.DataFrame([dict(symbol=s,close_us=int(t),close=100.) for t in (start,start+DAY) for s in SYMBOLS])
 window=dict(start=start,end=start+2*DAY,symbols=SYMBOLS,daily=daily,events=[],market=market)
 def targets(_daily,clocks,mode):
  return port.native.pl.DataFrame([dict(available_us=int(t),symbol=s,target_weight=(.2 if i==0 else -.2) if j==0 else (-.2 if i==0 else .2) if j==1 else 0.) for i,t in enumerate(clocks) for j,s in enumerate(SYMBOLS)]),dict(synthetic=True)
 return window,targets

def finish(sim):
 while sim.cursor<sim.end and sim.stop is None:sim.advance_day()
 return sim.result()

def test_capacity_half_matches_explicit_half_quote_with_reversals():
 p,account=finance();w,t=fixture(p);scaled=deepcopy(w)
 for row in scaled['market'].values():row['quote_volume']*=.5
 cls=capacity_half_class(p.native.NativeDailySimulator)
 a=cls(w,'LONG_SHORT',p.native.COSTS[0],p.native.UNITS[0],target_factory=t,account_factory=account)
 b=p.native.NativeDailySimulator(scaled,'LONG_SHORT',p.native.COSTS[0],p.native.UNITS[0],target_factory=t,account_factory=account)
 ar,br=finish(a),finish(b)
 # Decimal multiplication retains an extra zero exponent; compare exact values,
 # rather than requiring identical textual formatting of the same Decimal.
 assert numeric_strings(ar['trades'])==numeric_strings(br['trades'])
 assert numeric_strings(ar['rejections'])==numeric_strings(br['rejections'])
 assert numeric_strings(ar['summary'])==numeric_strings(br['summary'])
 np.testing.assert_array_equal(ar['minute'].to_numpy(),br['minute'].to_numpy())
 assert all((row['quote_volume']==1_000_000).all() for row in w['market'].values())
 assert a.previous_quote=={s:1_000_000. for s in SYMBOLS}
 assert any(r['side']=='SELL' for r in ar['trades']) and any(r['side']=='BUY' for r in ar['trades'])
 budgets={}
 for r in ar['trades']:
  key=(r['symbol'],r['event_us']);budgets.setdefault(key,[]).append(r)
 assert any(len(v)>1 for v in budgets.values()),'fixture must exercise close+open in one minute'
 assert all(sum((Decimal(r['decimal_strings']['quantity']) for r in rows),Decimal(0))<=Decimal(5) for rows in budgets.values())

def test_exception_restores_raw_prior_quote():
 class Base:
  def attempt(self,*args):
   assert self.previous_quote=={'X':Decimal('5.5')}
   raise RuntimeError('synthetic')
 x=capacity_half_class(Base)();original={'X':11.};x.previous_quote=original
 try:x.attempt(0,{})
 except RuntimeError:pass
 else:raise AssertionError('exception swallowed')
 assert x.previous_quote is original

def test_repeated_minute_cannot_regrant_budget_or_scale_quote_twice():
 class Base:
  def attempt(self,*args):
   self.received.append(self.previous_quote['X'])
 x=capacity_half_class(Base)();x.previous_quote={'X':11.};x.received=[]
 x.attempt(100,{})
 assert x.previous_quote=={'X':11.} and x.received==[Decimal('5.5')]
 try:x.attempt(100,{})
 except RuntimeError as e:assert 'already admitted' in str(e)
 else:raise AssertionError('same-minute capacity was regranted')
 assert x.received==[Decimal('5.5')] and x.previous_quote=={'X':11.}
 x.attempt(101,{})
 assert x.received==[Decimal('5.5'),Decimal('5.5')]

def test_spread_slippage_stress_preserves_fee_and_paid_account_rules():
 p,account=finance();w,t=fixture(p)
 a=p.native.NativeDailySimulator(w,'LONG_SHORT',p.native.COSTS[0],p.native.UNITS[0],target_factory=t,account_factory=account)
 b=p.native.NativeDailySimulator(w,'LONG_SHORT',p.native.COSTS[1],p.native.UNITS[0],target_factory=t,account_factory=account)
 ar,br=finish(a),finish(b)
 assert a.account.config.fee_rate==b.account.config.fee_rate==Decimal('.00055')
 assert b.account.config.half_spread_bps==8 and b.account.config.slippage_bps==8
 assert all(v.quantity_step==Decimal('.00000001') for v in b.account.instrument_profiles.values())
 assert b.account.closing_min_notional_exempt
 assert br['summary']['execution_cost_USDT']>ar['summary']['execution_cost_USDT']
 assert br['summary']['net_PnL']<ar['summary']['net_PnL']
 assert br['summary']['terminal_cash_realized'] and ar['summary']['terminal_cash_realized']
