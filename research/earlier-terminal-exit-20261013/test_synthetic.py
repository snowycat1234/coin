"""Synthetic native-finance tests only. No historical account advance."""
from pathlib import Path
import unittest,json,hashlib,tempfile,shutil,importlib.util,sys,inspect
import numpy as np
H=Path(__file__).resolve().parent;R=H.parent
from freeze_terminal import verify
verify()
p=R/'coin_margin_protective_runner_20261013/run_guard_cases.py'
s=importlib.util.spec_from_file_location('terminal_test_transport',p);guard=importlib.util.module_from_spec(s);s.loader.exec_module(guard)
port,source,_=guard.load_port(2025)
sys.path.insert(0,str(R/'coin_quantity_resolution_20261013'))
from fine_account import FineGridAccount
from terminal_adapter import EarlierTerminalSimulator,NativeDailySimulator,D,ZERO
from preflight_terminal import validate_terminal,bindings
from run_budget import ensure_single_unstarted_batch,stop_on_worker_failure
from worker_bounds import require_worker_bounds
M=60_000_000;DAY=86_400_000_000;SYMS=tuple(source['symbols'])

def make_sim(cls=EarlierTerminalSimulator,weight=.1,terminal_quote=10000.,events=None,mutate=None):
 market={s:{'open':np.full(1440,10.),'close':np.full(1440,10.),'mark':np.full(1440,10.),'quote_volume':np.full(1440,300000.)} for s in SYMS}
 for v in market.values():v['quote_volume'][-61:]=terminal_quote
 if mutate:mutate(market)
 daily=port.native.pl.DataFrame([{'symbol':s,'close_us':0,'close':10.} for s in SYMS])
 w={'start':0,'end':DAY,'symbols':SYMS,'daily':daily,'market':market,'events':events or []}
 def targets(_,clocks,mode):
  return port.native.pl.DataFrame([{'available_us':0,'symbol':s,'target_weight':weight if s=='BTCUSDT' else -weight if s=='DOGEUSDT' else 0.} for s in SYMS]),{'source':'SYNTHETIC'}
 return cls(w,'LONG_SHORT',port.native.COSTS[0],port.native.UNITS[0],target_factory=targets,account_factory=FineGridAccount)

class Tests(unittest.TestCase):
 def test_exact_copy_two_expiry_changes(self):
  old=inspect.getsource(NativeDailySimulator.attempt)
  expected=old.replace("elif order['attempts']>=5:","elif order['attempts']>=(60 if order['kind']=='TERMINAL' else 5):").replace("reason='FIVE_ATTEMPTS_EXPIRED',","reason='SIXTY_TERMINAL_ATTEMPTS_EXPIRED' if order['kind']=='TERMINAL' else 'FIVE_ATTEMPTS_EXPIRED',")
  self.assertEqual(inspect.getsource(EarlierTerminalSimulator.attempt),expected)
 def test_sixty_real_clock_capacity_no_reentry(self):
  sim=make_sim();sim.advance_day();signal=DAY-61*M
  fills=[f for f in sim.account.trades if f['signal_us']==signal]
  self.assertEqual(sorted(set(f['event_us'] for f in fills)),[t+1 for t in range(DAY-60*M,DAY,M)])
  self.assertEqual(len(fills),120)
  for f in fills:
   d=f['decimal_strings'];self.assertEqual(f['leg'],'CLOSE');self.assertLessEqual(D(d['quantity']),D('1'))
   self.assertLessEqual(abs(D(d['quantity_after'])),abs(D(d['quantity_before'])))
   self.assertGreaterEqual(D(d['quantity_after'])*D(d['quantity_before']),ZERO)
   self.assertLess(f['event_us'],DAY)
  self.assertEqual(sim.rows_written,1440);self.assertEqual(sim.cursor,DAY)
  expired=[r for r in sim.rejections if r.get('kind')=='TERMINAL' and r['reason']=='SIXTY_TERMINAL_ATTEMPTS_EXPIRED']
  self.assertEqual(len(expired),2);self.assertEqual([r['event_us'] for r in expired],[DAY-M+1]*2)
  self.assertFalse(sim.result()['summary']['terminal_cash_realized'])
  self.assertFalse(any(f['signal_us']==DAY-6*M for f in sim.account.trades))
  self.assertGreater(abs(sim.account.positions['BTCUSDT'].quantity),0)
 def test_paid_flat_cost_funding(self):
  event={'event_us':DAY-30*M,'symbol':'BTCUSDT','raw_rate':.001}
  sim=make_sim(weight=.05,events=[event]);sim.advance_day();signal=DAY-61*M
  self.assertTrue(sim.result()['summary']['terminal_cash_realized']);self.assertEqual(sim.event_cursor,1)
  funding=sim.funding_journal[0];self.assertTrue(funding['owned']);self.assertNotEqual(D(str(funding['signed_funding_USDT'])),ZERO)
  fills=[f for f in sim.account.trades if f['signal_us']==signal]
  for f in fills:
   d=f['decimal_strings'];self.assertGreater(D(d['fee_amount']),0);self.assertGreater(D(d['execution_cost']),0)
  self.assertGreater(sim.account.fees,0);self.assertGreater(sim.account.execution_cost,0)
 def test_no_future_capacity_and_original_prefix(self):
  left=make_sim();right=make_sim(mutate=lambda m:[v['quote_volume'].__setitem__(-1,1e12) for v in m.values()]);base=make_sim(cls=NativeDailySimulator)
  for sim in (left,right,base):sim.advance_day()
  np.testing.assert_array_equal(left.minute_chunks[0][:1380],base.minute_chunks[0][:1380])
  self.assertEqual(left.account.trades,right.account.trades);np.testing.assert_array_equal(left.minute_chunks[0],right.minute_chunks[0])
  self.assertEqual(left.account.trades,[f for f in left.account.trades if f['event_us']<DAY])
 def test_nonterminal_five_stays_same(self):
  sim=make_sim();sim.advance_day()
  expired=[r for r in sim.rejections if r['reason']=='FIVE_ATTEMPTS_EXPIRED']
  self.assertFalse(any(r.get('kind')=='TERMINAL' for r in expired))
  # Explicit never-filled DAILY_TARGET remains exactly five real attempts.
  q=make_sim(terminal_quote=0);q.account.update_marks(0,{s:dict(price=D('10'),close_us=0,available_us=0) for s in SYMS});q.previous_quote=dict.fromkeys(SYMS,0.);q.schedule(dict.fromkeys(SYMS,D('10')),0,'DAILY_TARGET')
  for t in range(M,6*M,M):q.attempt(t,{s:{'open':10.} for s in SYMS})
  self.assertEqual(len(q.pending),0);self.assertEqual(len([r for r in q.rejections if r['reason']=='FIVE_ATTEMPTS_EXPIRED']),5)
 def test_terminal_cannot_add_or_be_overwritten(self):
  sim=make_sim();sim.advance_day()
  with self.assertRaises(ValueError):sim.schedule(dict.fromkeys(SYMS,D('1')),sim.terminal_signal_us,'TERMINAL')
  with self.assertRaises(ValueError):sim.schedule(dict.fromkeys(SYMS,ZERO),DAY-2*M,'DAILY_TARGET')
 def test_snapshot_zero_advance_halt_preserved(self):
  def crash(m):m['DOGEUSDT']['mark'][20:]=30.
  sim=make_sim(mutate=crash);sim.advance_day();self.assertIsNotNone(sim.stop)
  restored=EarlierTerminalSimulator.from_snapshot(sim.snapshot(),sim.window,account_class=FineGridAccount)
  self.assertEqual(sim.state_hash(),restored.state_hash());self.assertEqual(sim.stop,restored.stop)
  with self.assertRaises(ValueError):restored.advance_day()
  with tempfile.TemporaryDirectory() as d:
   pointer=port.checkpoint(Path(d),sim,{'synthetic':True});self.assertEqual(pointer['stop'],sim.stop)
 def test_snapshot_full_restores_terminal(self):
  sim=make_sim();sim.advance_day();r=EarlierTerminalSimulator.from_snapshot(sim.snapshot(),sim.window,account_class=FineGridAccount)
  self.assertEqual(sim.state_hash(),r.state_hash());self.assertEqual(sim.result()['summary'],r.result()['summary'])
 def test_clock_gate_and_fixed_plan(self):
  end=DAY;t=np.arange(end-61*M,end,M,dtype=np.int64);p=np.ones(61)
  self.assertEqual(validate_terminal(t,t+M,p,p,p,end)['attempt_count'],60)
  with self.assertRaises(ValueError):validate_terminal(t[1:],t[1:]+M,p,p,p,end)
  self.assertEqual({c['arm'] for c in bindings()['cases']},{'STATIC50','COMBINED'})
 def test_budget_bounds_tamper(self):
  self.assertFalse(stop_on_worker_failure(0));self.assertTrue(stop_on_worker_failure(-9))
  require_worker_bounds({0},(4_000_000_000,4_000_000_000),(1200,1200))
  with self.assertRaises(RuntimeError):require_worker_bounds({0},(-1,-1),(1200,1200))
  with tempfile.TemporaryDirectory() as d:
   h=Path(d);ensure_single_unstarted_batch(h,h/'state_first');(h/'state_old').mkdir();(h/'state_old/RUN_BINDING.json').write_text('{}')
   with self.assertRaises(RuntimeError):ensure_single_unstarted_batch(h,h/'state_new')
  with tempfile.TemporaryDirectory() as d:
   h=Path(d);m=json.loads((H/'FROZEN_CODE.json').read_text());m['files_SHA256']={'terminal_adapter.py':m['files_SHA256']['terminal_adapter.py']};m['dependencies_SHA256']={}
   shutil.copy(H/'freeze_terminal.py',h/'freeze_terminal.py');(h/'terminal_adapter.py').write_text('tamper');(h/'FROZEN_CODE.json').write_text(json.dumps(m))
   with self.assertRaises(ValueError):verify(h)
if __name__=='__main__':unittest.main(verbosity=2)
