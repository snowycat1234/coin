import unittest,json
from decimal import Decimal as D
from copy import deepcopy
from candidate import S,FRACTIONS,select_partial,ScheduleAdapter
from native_preview import ChargedPreview
from fine_account import FineGridAccount
import numpy as np,polars as pl
from native_control import NATIVE as NativeDailySimulator

class Tests(unittest.TestCase):
 def vec(self,*v):return dict(zip(S,[D(str(x)) for x in (v or (0,0,0,0,0))]))
 def account(self):
  a=FineGridAccount();a.update_marks(0,{s:{'price':D(100),'close_us':0,'available_us':0} for s in S});return a
 def seed(self,a,side='BUY',quantity=D(5)):
  return a.execute_fill(S[0],side,quantity,60000001,0,'SEED',execution_mid_price=D(100),quote_available_us=0)
 def oracle(self,a,cov=.04,pending=None,quote=100000000):
  return ChargedPreview(a,prices=self.vec(100,100,100,100,100),covariance=[[cov if i==j else 0 for j in range(5)] for i in range(5)],pending=pending or {s:a.positions[s].quantity for s in S},previous_quote=self.vec(quote,quote,quote,quote,quote),event_us=180000001,signal_us=120000000,covariance_available_us=0,quote_available_us=60000000,price_available_us=dict.fromkeys(S,0))
 def select(self,o,target):return select_partial(actual=o.actual,raw_target=target,evaluate=o.evaluate)
 def simulator(self):
  window={'start':0,'end':86400000000,'symbols':S,'daily':pl.DataFrame([{'symbol':s,'close_us':0,'close':100.} for s in S]),'events':[],'market':{s:{k:np.full(1440,100000000. if k=='quote_volume' else 100.) for k in ('open','close','mark','quote_volume')} for s in S}}
  sim=NativeDailySimulator(window,'LONG_SHORT',{'id':'BASE27','half_spread_bps':4,'slippage_bps':4,'roundtrip_bps':27},{'id':'RAW_AS_FRACTION','scale':1.},account_factory=FineGridAccount);sim.account.update_marks(0,{s:{'price':D(100),'close_us':0,'available_us':0} for s in S});sim.previous_quote=dict.fromkeys(S,100000000.);return sim
 def market(self):return {s:{'open':100.,'close':100.,'mark':100.,'quote_volume':100000000.} for s in S}
 def test_full_valid_original_scheduler_and_account_exact(self):
  baseline=self.simulator();candidate=self.simulator();raw=self.vec(5,5,0,0,0)
  baseline.schedule(raw,120000000,'DAILY_TARGET')
  adapter=ScheduleAdapter(candidate.schedule,lambda t:self.oracle(candidate.account));adapter.schedule(raw,120000000,'DAILY_TARGET')
  self.assertEqual(adapter.receipts[-1].fraction,D(1));self.assertEqual(adapter.receipts[-1].raw_target,raw);self.assertEqual(candidate.pending,baseline.pending)
  baseline.attempt(180000000,self.market());candidate.attempt(180000000,self.market());self.assertEqual(candidate.snapshot(),baseline.snapshot());self.assertEqual(len(candidate.account.trades),2)
 def test_partial_valid_all_gates_enumerated(self):
  a=self.account();o=self.oracle(a,.25);raw=self.vec(30,0,0,0,0);r=self.select(o,raw);self.assertEqual(r.fraction,D('.5'));self.assertEqual([x.fraction for x in r.evaluations],list(FRACTIONS));self.assertTrue(o.evaluate(r.target,r.fraction)['allowed']);self.assertEqual(r.raw_target,raw);self.assertEqual(len(a.trades),0)
 def test_nonmonotonic_no_shortcut(self):
  seen=[]
  def gate(t,l):seen.append(l);return {'allowed':l in (D('.75'),D('.25'))}
  r=select_partial(actual=self.vec(),raw_target=self.vec(8,0,0,0,0),evaluate=gate);self.assertEqual(seen,list(FRACTIONS));self.assertEqual(r.fraction,D('.75'))
 def test_all_invalid_only_original_paid_reduction(self):
  a=self.account();self.seed(a);o=self.oracle(a,9);r=self.select(o,self.vec(2,0,0,0,0));self.assertTrue(r.all_invalid);self.assertEqual(r.target['BTCUSDT'],D(2));before=a.free_cash
  a.execute_fill(S[0],'SELL',D(3),180000001,120000000,'PAID_REDUCE',execution_mid_price=D(100),quote_available_us=60000000,reduce_only=True);self.assertEqual(a.positions[S[0]].quantity,D(2));self.assertGreater(a.free_cash,before);self.assertGreater(a.fees,0)
 def test_all_invalid_increase_preserves_actual_inventory(self):
  a=self.account();self.seed(a);r=self.select(self.oracle(a,9),self.vec(6,0,0,0,0));self.assertTrue(r.all_invalid);self.assertEqual(r.target['BTCUSDT'],D(5));self.assertEqual(len(a.trades),1)
 def test_long_short_original_reduce_then_increase(self):
  for side,target in [('BUY',-5),('SELL',5)]:
   a=self.account();self.seed(a,side);o=self.oracle(a);r=self.select(o,self.vec(target,0,0,0,0));self.assertEqual(r.fraction,D(1));probe,w=o._charged(r.target,'TRANSITION');self.assertEqual([x['leg'] for x in w['legs']],['CLOSE','OPEN']);self.assertEqual(probe.positions[S[0]].quantity,D(target))
 def test_fee_charged_boundary(self):
  a=self.account();r=self.select(self.oracle(a,0),self.vec(30,0,0,0,0));self.assertEqual(r.fraction,D('.75'));self.assertEqual(a.free_cash,D(10000));self.assertFalse(r.evaluations[0].allowed)
 def test_cash_and_funding_before_fills(self):
  a=self.account();self.seed(a);a.apply_funding(S[0],'FUND',60000002,D(18),60000002);before=a.snapshot();r=self.select(self.oracle(a,0),self.vec(20,20,0,0,0));self.assertTrue(r.all_invalid);self.assertEqual(a.snapshot(),before);self.assertEqual(a.funding_cash,D(-9000))
 def test_pending_mixed_corner_native_cash_risk(self):
  a=self.account();r=self.select(self.oracle(a,0,pending=self.vec(25,25,25,0,0)),self.vec(1,0,0,0,0));self.assertTrue(r.all_invalid);self.assertEqual(r.target,self.vec());self.assertEqual(len(a.trades),0)
 def test_partial_fill_real_residual_and_executed_position(self):
  a=self.account();o=self.oracle(a,0,quote=100000);w=o.evaluate(self.vec(4,0,0,0,0),D(1));self.assertFalse(w['allowed']);request=w['requests'][0];self.assertEqual(D(request['executed_quantity']),D(1));self.assertEqual(D(request['remaining_pending_quantity']),D(3));self.assertEqual(D(request['actual_after']['actual_executed_positions'][S[0]]),D(1));self.assertEqual(a.positions[S[0]].quantity,0)
 def test_shared_capacity_partial_selection(self):
  a=self.account();r=self.select(self.oracle(a,0,quote=100000),self.vec(4,0,0,0,0));self.assertEqual(r.fraction,D('.25'));self.assertEqual(r.target[S[0]],D(1))
 def test_nonrepresentable_dust_not_silently_filled(self):
  a=self.account();w=self.oracle(a,0).evaluate(self.vec('1.000000005',0,0,0,0),D(1));self.assertTrue(w['allowed']);q=w['corners_checked'][-1]['charge']['requests'][0];self.assertEqual(D(q['executed_quantity']),D(1));self.assertEqual(D(q['remaining_pending_quantity']),D('.000000005'));self.assertEqual(a.positions[S[0]].quantity,0)
 def test_below_opening_minimum_native_refusal(self):
  a=self.account();w=self.oracle(a,0).evaluate(self.vec('.01',0,0,0,0),D(1));self.assertFalse(w['allowed']);self.assertEqual(w['requests'][0]['executed_quantity'],'0');self.assertEqual(w['requests'][0]['native_receipt']['reason'],'BELOW_MIN_NOTIONAL_OR_CAPACITY')
 def test_mixed_priority_does_not_bypass_unrelated_increase(self):
  sim=self.simulator();self.seed(sim.account);raw=self.vec(0,40,0,0,0);kinds=dict.fromkeys(S,'DAILY_TARGET');kinds[S[0]]='PROTECTIVE_STOP';adapter=ScheduleAdapter(sim.schedule,lambda t:self.oracle(sim.account,0,pending={s:sim.pending[s]['target'] if s in sim.pending else sim.account.positions[s].quantity for s in S}));adapter.schedule(raw,120000000,kinds)
  self.assertEqual(sim.pending[S[0]]['kind'],'PROTECTIVE_STOP');self.assertNotEqual(adapter.receipts[-1].fraction,D(1));self.assertLess(sim.pending[S[1]]['target'],D(40));sim.attempt(180000000,self.market());self.assertEqual(sim.account.positions[S[0]].quantity,0);self.assertLess(sim.account.positions[S[1]].quantity,D(40))
 def test_terminal_paid_close_original_scheduler_exact(self):
  baseline=self.simulator();candidate=self.simulator()
  for sim in (baseline,candidate):self.seed(sim.account)
  signal=baseline.terminal_signal_us;self.assertEqual(signal,baseline.end-61*60000000);self.assertEqual(candidate.terminal_signal_us,signal)
  raw=self.vec();baseline.schedule(raw,signal,'TERMINAL');adapter=ScheduleAdapter(candidate.schedule,lambda t:(_ for _ in ()).throw(AssertionError('NO_ALLOCATOR_FOR_TERMINAL')));adapter.schedule(raw,signal,'TERMINAL');self.assertEqual(candidate.pending,baseline.pending)
  for sim in (baseline,candidate):sim.attempt(signal+60000000,self.market())
  self.assertEqual(candidate.snapshot(),baseline.snapshot());self.assertEqual(candidate.account.positions[S[0]].quantity,0);self.assertEqual(candidate.account.unpaid_liability,0);self.assertGreater(candidate.account.fees,0)
 def test_actual_marks_not_execution_quote_risk_denominator(self):
  a=self.account();o=ChargedPreview(a,prices=self.vec(101,101,101,101,101),covariance=np.eye(5)*.04,pending=self.vec(),previous_quote=self.vec(100000000,100000000,100000000,100000000,100000000),event_us=180000001,signal_us=120000000,covariance_available_us=0,quote_available_us=60000000,price_available_us=dict.fromkeys(S,0))
  probe,w=o._charged(self.vec(5,0,0,0,0),'QUOTE_MARK');risk=o._risk(probe);self.assertEqual(risk['gross'],float(D(5)*probe._mark(S[0])/probe.nav()));self.assertNotEqual(risk['gross'],float(D(5)*D(101)/probe.nav()))
 def test_invalid_and_future_covariance_fail_closed(self):
  a=self.account()
  with self.assertRaises(ValueError):self.oracle(a,-1)
  with self.assertRaises(ValueError):ChargedPreview(a,prices=self.vec(100,100,100,100,100),covariance=np.eye(5),pending=self.vec(),previous_quote=self.vec(100000000,100000000,100000000,100000000,100000000),event_us=180000001,signal_us=120000000,covariance_available_us=120000001,quote_available_us=0,price_available_us=dict.fromkeys(S,0))
 def test_nontick_original_scheduler_journals_exact(self):
  for side,target in [('BUY','6.123456789'),('SELL','-6.123456789'),('BUY','-3.123456789'),('SELL','3.123456789')]:
   baseline=self.simulator();candidate=self.simulator()
   for sim in (baseline,candidate):self.seed(sim.account,side)
   raw=self.vec(target,0,0,0,0);baseline.schedule(raw,120000000,'DAILY_TARGET')
   adapter=ScheduleAdapter(candidate.schedule,lambda t:self.oracle(candidate.account,0));adapter.schedule(raw,120000000,'DAILY_TARGET')
   self.assertEqual(adapter.receipts[-1].fraction,D(1));self.assertEqual(candidate.pending,baseline.pending)
   for sim in (baseline,candidate):sim.attempt(180000000,self.market())
   self.assertEqual(candidate.snapshot(),baseline.snapshot());self.assertEqual(candidate.account.trades,baseline.account.trades);self.assertEqual(candidate.account.snapshot(),baseline.account.snapshot());self.assertEqual(candidate.pending,baseline.pending);self.assertEqual(candidate.pending[S[0]]['target'],D(target))
 def test_future_signal_price_rejected(self):
  with self.assertRaises(ValueError):ChargedPreview(self.account(),prices=self.vec(100,100,100,100,100),covariance=np.eye(5),pending=self.vec(),previous_quote=self.vec(1000000,1000000,1000000,1000000,1000000),event_us=180000001,signal_us=120000000,covariance_available_us=0,quote_available_us=0,price_available_us=dict.fromkeys(S,120000001))
 def test_dust_distinct_from_liquidity_whole_lot(self):
  o=self.oracle(self.account(),0,quote=100000);w=o.evaluate(self.vec('4.000000005',0,0,0,0),D(1));self.assertFalse(w['allowed']);q=w['requests'][0];self.assertEqual(D(q['unfilled_whole_lot_quantity']),D(3));self.assertEqual(D(q['rounding_dust_quantity']),D('.000000005'));self.assertEqual(D(q['remaining_pending_quantity']),D('3.000000005'))
 def test_original_weight_nav_price_raw_formula_parity(self):
  baseline=self.simulator();candidate=self.simulator();raw=self.vec(D('.05123456789')*D('.99')*baseline.account.nav()/D(100),0,0,0,0)
  self.assertNotEqual(raw[S[0]],baseline.account._floor(S[0],raw[S[0]]));baseline.schedule(raw,120000000,'DAILY_TARGET');adapter=ScheduleAdapter(candidate.schedule,lambda t:self.oracle(candidate.account,0));adapter.schedule(raw,120000000,'DAILY_TARGET');self.assertEqual(adapter.receipts[-1].fraction,D(1));self.assertEqual(candidate.pending,baseline.pending)
  for sim in (baseline,candidate):sim.attempt(180000000,self.market())
  self.assertEqual(candidate.account.trades,baseline.account.trades);self.assertEqual(candidate.account.snapshot(),baseline.account.snapshot());self.assertEqual(candidate.snapshot(),baseline.snapshot());self.assertEqual(candidate.pending,baseline.pending);self.assertEqual(candidate.pending[S[0]]['target'],raw[S[0]])
if __name__=='__main__':unittest.main()
