import unittest,json
from decimal import Decimal as D
from copy import deepcopy
from candidate import S,FRACTIONS,select_partial,ScheduleAdapter
from native_preview import ChargedPreview
from fine_account import FineGridAccount

class Tests(unittest.TestCase):
 def account(self):
  a=FineGridAccount();a.update_marks(0,{s:{'price':D('100'),'close_us':0,'available_us':0} for s in S});return a
 def vec(self,*values):return dict(zip(S,[D(str(x)) for x in (values or (0,0,0,0,0))]))
 def oracle(self,a,cov=.04,pending=None,quote=100000000):
  return ChargedPreview(a,prices=self.vec(100,100,100,100,100),covariance=[[cov if i==j else 0 for j in range(5)] for i in range(5)],pending=pending or {s:a.positions[s].quantity for s in S},previous_quote=self.vec(quote,quote,quote,quote,quote),event_us=120000001,signal_us=60000000)
 def select(self,o,target):return select_partial(actual=o.actual,raw_target=target,evaluate=o.evaluate)
 def test_full_valid_baseline_exact(self):
  a=self.account();o=self.oracle(a);target=self.vec(5,5,0,0,0);before=a.snapshot();r=self.select(o,target);self.assertEqual(r.fraction,D(1));self.assertEqual(r.target,target);self.assertEqual(len(r.evaluations),1)
  x,_=o.baseline_preview(target);y,_=o.baseline_preview(r.target);self.assertEqual(x.snapshot(),y.snapshot());self.assertEqual(a.snapshot(),before)
 def test_full_invalid_partial_valid_all_gates(self):
  a=self.account();o=self.oracle(a,.25);r=self.select(o,self.vec(30,0,0,0,0));self.assertEqual(r.fraction,D('.5'));self.assertEqual(tuple(v.fraction for v in r.evaluations),FRACTIONS);self.assertTrue(o.evaluate(r.target,r.fraction)['allowed']);self.assertEqual(r.raw_target['BTCUSDT'],D(30))
 def test_all_invalid_no_increase_preserves_inventory(self):
  a=self.account();a.execute_fill(S[0],'BUY',D(5),60000001,0,'SEED',execution_mid_price=D(100),quote_available_us=0);o=self.oracle(a,9);r=self.select(o,self.vec(6,0,0,0,0));self.assertIsNone(r.fraction);self.assertTrue(r.all_invalid);self.assertEqual(r.target['BTCUSDT'],a.positions[S[0]].quantity);self.assertEqual(len(a.trades),1)
 def test_nonmonotonic_enumerates_later_larger_valid(self):
  seen=[]
  def oracle(t,l):seen.append(l);return {'allowed':l in (D('.75'),D('.25'))}
  r=select_partial(actual=self.vec(),raw_target=self.vec(8,0,0,0,0),evaluate=oracle);self.assertEqual(seen,list(FRACTIONS));self.assertEqual(r.fraction,D('.75'))
 def test_long_short_transition_native_reduce_before_increase(self):
  for side,q,target in [('BUY',5,-5),('SELL',5,5)]:
   a=self.account();a.execute_fill(S[0],side,D(q),60000001,0,'SEED',execution_mid_price=D(100),quote_available_us=0);o=self.oracle(a);r=self.select(o,self.vec(target,0,0,0,0));self.assertEqual(r.fraction,D(1));probe,w=o.baseline_preview(r.target);self.assertEqual([x['leg'] for x in w['legs']],['CLOSE','OPEN']);self.assertEqual(probe.positions[S[0]].quantity,D(target))
 def test_fee_charged_asset_boundary(self):
  a=self.account();r=self.select(self.oracle(a,0),self.vec(30,0,0,0,0));self.assertEqual(r.fraction,D('.75'));self.assertFalse(r.evaluations[0].allowed);self.assertEqual(a.free_cash,D(10000))
 def test_cash_failure_from_real_funding_debit(self):
  a=self.account();a.execute_fill(S[0],'BUY',D(5),60000001,0,'SEED',execution_mid_price=D(100),quote_available_us=0);a.apply_funding(S[0],'FUNDING',60000002,D('18'),60000002);o=self.oracle(a,0);r=self.select(o,self.vec(20,20,0,0,0));self.assertTrue(all(not v.allowed for v in r.evaluations));self.assertTrue(r.all_invalid);self.assertGreater(a.funding_cash.copy_abs(),0)
 def test_pending_mixed_corner_fail_closed(self):
  a=self.account();o=self.oracle(a,0,pending=self.vec(25,25,25,0,0));r=self.select(o,self.vec(1,0,0,0,0));self.assertTrue(r.all_invalid);self.assertEqual(r.target,self.vec());self.assertEqual(len(r.evaluations),5)
 def test_shared_capacity_each_candidate(self):
  a=self.account();r=self.select(self.oracle(a,0,quote=100000),self.vec(4,0,0,0,0));self.assertEqual(r.fraction,D('.25'));self.assertEqual(r.target['BTCUSDT'],D(1))
 def test_terminal_protective_delegation_and_paid_close(self):
  calls=[];adapter=ScheduleAdapter(lambda *args:calls.append(args),lambda signal:(_ for _ in ()).throw(AssertionError('NO_ALLOCATION_ON_PRIORITY')));t=self.vec()
  for kind in ['TERMINAL','PROTECTIVE_STOP','RISK_REDUCTION','DATA_GAP_EXIT']:adapter.schedule(t,60000000,kind);self.assertEqual(calls[-1],(t,60000000,kind,None))
  a=self.account();a.execute_fill(S[0],'BUY',D(5),60000001,0,'OPEN',execution_mid_price=D(100),quote_available_us=0);b=deepcopy(a)
  for x in (a,b):x.execute_fill(S[0],'SELL',D(5),60000001,0,'TERMINAL',execution_mid_price=D(100),quote_available_us=0,reduce_only=True)
  self.assertEqual(a.snapshot(),b.snapshot());self.assertEqual(a.positions[S[0]].quantity,0);self.assertEqual(a.unpaid_liability,0);self.assertGreater(a.fees,0)
 def test_invalid_covariance_and_config_rejected(self):
  a=self.account()
  with self.assertRaises(ValueError):self.oracle(a,-1)
if __name__=='__main__':unittest.main()
