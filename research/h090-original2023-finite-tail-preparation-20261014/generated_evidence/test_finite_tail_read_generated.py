"""Exactly four generated flush tests, statically prepared; no execution authorized."""
import ast,dataclasses,hashlib,importlib.util,json,sys,types,unittest
from copy import deepcopy
from decimal import Decimal as D
from pathlib import Path
REV=Path(__file__).resolve().parent
ACCEPTED=Path('/workspace/coin-cloud/h090-original2023-code-20261014/coin_h090_original2023_finite_prefix_bridge_20261014')
def canonical(value):
 def normal(x):
  if dataclasses.is_dataclass(x):return normal(dataclasses.asdict(x))
  if isinstance(x,D):return str(x)
  if isinstance(x,dict):return {str(k):normal(v) for k,v in x.items()}
  if isinstance(x,(list,tuple)):return [normal(v) for v in x]
  if isinstance(x,set):return sorted(normal(v) for v in x)
  return x
 return json.dumps(normal(value),sort_keys=True,separators=(',',':'),allow_nan=False).encode()
class TestFiniteTailRead(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  assert sys.flags.isolated and sys.flags.no_site and sys.flags.dont_write_bytecode and not sys.flags.optimize
  mf=json.loads((REV/'REVISION_MANIFEST.json').read_text())
  for n,v in mf['files'].items():
   b=(REV/n).read_bytes();assert len(b)==v['bytes'] and hashlib.sha256(b).hexdigest()==v['SHA256']
  # Extract only the accepted fixture bootstrap function; never invoke its
  # broad suite, profiler, calendars or generated runner main.
  fixture=ACCEPTED/'test_finite_prefix_worker.py';b=fixture.read_bytes();assert hashlib.sha256(b).hexdigest()=='27bbafa608663e37af42531b1e7de31cc501dd1637942d95794a907a5186b975'
  t=ast.parse(b);n=next(x for x in t.body if isinstance(x,ast.FunctionDef) and x.name=='bootstrap')
  ns={'BASE':ACCEPTED,'ROOT':ACCEPTED.parent,'PIN':'0d44cc01c0ea09274996ebe886a93536e6376ccbca6ca83f31d35b57354e2efc','sha':lambda b:hashlib.sha256(b).hexdigest(),'json':json,'types':types,'sys':sys,'importlib':__import__('importlib')};__import__('importlib.machinery')
  exec(compile(ast.Module(body=[n],type_ignores=[]),str(fixture),'exec'),ns);ns['bootstrap']();cls.fixture=ns
  spec=importlib.util.spec_from_file_location('finite_tail_read',REV/'finite_tail_read.py');module=importlib.util.module_from_spec(spec);sys.modules['finite_tail_read']=module;spec.loader.exec_module(module)
  spec=importlib.util.spec_from_file_location('tail_read_review_candidate',REV/'original_bridge.py');candidate=importlib.util.module_from_spec(spec);spec.loader.exec_module(candidate);cls.candidate=candidate
  assert candidate.OriginalPrefixFiniteCandidate._flush_account is module.FiniteTailRead._flush_account
 def pair(self):
  f=self.fixture;bundle=f['F'].make_generated(weights=[.05,.05,0,0,0]);admitted=f['T'].admitted(bundle)
  pair=(f['O'].make_sim(admitted,'FINITE',generated=True),self.candidate.make_sim(admitted,'FINITE',generated=True))
  for sim in pair:
   snap=sim.account.engine.snapshot();self.assertEqual(snap['config']['fee_rate'],'0.00055')
   cost=sim.result()['summary']['cost_scenario'];self.assertEqual(cost['id'],'BASE27');self.assertEqual(cost['half_spread_bps'],4);self.assertEqual(cost['slippage_bps'],4)
   # cost_context may be None; it is not a precondition.
  self.same(pair);return pair
 def state(self,s):
  return {'snapshot':s.snapshot(),'account':s.account.snapshot(),'owners':s.owners.snapshot(),'program':deepcopy(vars(s.program)),'budget':deepcopy(vars(s.program_budget)),'pending':deepcopy(s.program_pending),'bindings':deepcopy(s._fill_owner),'authorizations':deepcopy(s._program_order_authorizations),'signal_marks':deepcopy(s._program_signal_mark_evidence),'processed_receipts':deepcopy(s.processed_native_receipts),'trade_cursor':s._trade_cursor,'funding_cursor':s._funding_cursor,'events':deepcopy(s.owner_events),'reservations':deepcopy(vars(s.reservations))}
 def same(self,pair):
  self.assertEqual(canonical(self.state(pair[0])),canonical(self.state(pair[1])))
  for s in pair:self.assertEqual(s._trade_cursor,len(s.account.engine.trades));self.assertEqual(s._funding_cursor,len(s.account.engine.funding))
 def mark(self,s,n,price=100):
  f=self.fixture['F'];stamp=f.START+n*f.MINUTE;s.account.update_marks(stamp,{sym:{'price':D(str(price)) if sym==f.S[0] else D('100'),'close_us':stamp,'available_us':stamp} for sym in f.S});return stamp
 def seed(self,pair):
  f=self.fixture['F'];z=D(0)
  for s in pair:
   s._admit_decision(f.START,None,None,None,None);self.mark(s,0);s.previous_quote=dict.fromkeys(f.S,10000000.);s.schedule({sym:D('10') if sym==f.S[0] else z for sym in f.S},f.START,'DAILY_TARGET');s.attempt(f.START+f.MINUTE,{sym:{'open':100.,'quote_volume':10000000.} for sym in f.S})
  self.same(pair)
 def test_empty_and_new_trade_tail(self):
  pair=self.pair()
  for s in pair:s._flush_account();s._flush_account()
  self.same(pair);self.seed(pair)
  for s in pair:self.assertGreater(len(s.account.engine.trades),0);s._flush_account()
  self.same(pair)
 def test_owner_opening_partial_add_cursors(self):
  pair=self.pair();self.seed(pair);f=self.fixture['F']
  for s in pair:self.mark(s,2,90);s._evaluate_program(f.START+2*f.MINUTE);s.previous_quote=dict.fromkeys(f.S,40500.)
  for n in range(3,8):
   for s in pair:self.mark(s,n,90);s.attempt(f.START+n*f.MINUTE,{sym:{'open':90. if sym==f.S[0] else 100.,'quote_volume':10000000.} for sym in f.S});s._flush_account()
   self.same(pair)
  for s in pair:self.assertEqual(s.program.completed_opening_orders,2)
 def test_funding_tail_accounting(self):
  pair=self.pair();self.seed(pair);f=self.fixture['F']
  for i,rate in enumerate((D('.0001'),D('-.0001'))):
   for s in pair:s.account.apply_funding(f.S[0],'FLUSH_FIXED_FUNDING_'+str(i),f.START+(i+2)*f.MINUTE+1,rate,f.START);s._flush_account();s._flush_account()
   self.same(pair)
 def test_replay_full_serialized_state_and_cursors(self):
  pair=self.pair();self.seed(pair)
  for s in pair:
   before=canonical(self.state(s));row=s.account.engine.trades[0];request=deepcopy(s.account.fill_requests[row['fill_id']]['identity']);s.account.execute_fill(**request,fill_id=row['fill_id']);s._flush_account();self.assertEqual(before,canonical(self.state(s)))
  self.same(pair)
