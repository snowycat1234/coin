"""Only synthetic minutes/accounts. No real source reader or historical target factory."""
import unittest,json,hashlib,tempfile,sys,inspect
from pathlib import Path
import numpy as np
import pair_launcher as p
ROOTS=json.loads(Path(sys.argv.pop(1)).read_text()) if len(sys.argv)>1 and not sys.argv[1].startswith('-') else {}
PORT,FINE,SIM=p.load_synthetic_engine(ROOTS);D=__import__('decimal').Decimal;S=p.S;M=p.MINUTE;DAY=p.DAY

def fixture(weight=.1,quote=10000.,events=None):
 market={s:{'open':np.full(1440,10.),'close':np.full(1440,10.),'mark':np.full(1440,10.),'quote_volume':np.full(1440,300000.)} for s in S}
 for v in market.values():v['quote_volume'][-61:]=quote
 daily=p.normalize_daily([dict(symbol=s,close_us=0,close=10.) for s in S])
 window=dict(start=0,end=DAY,symbols=S,daily=daily,market=market,events=events or [])
 def targets(_,clocks,mode):
  return PORT.native.pl.DataFrame([dict(available_us=0,symbol=s,target_weight=weight if s=='BTCUSDT' else -weight if s=='DOGEUSDT' else 0.) for s in S]),dict(source='PURE_SYNTHETIC_FIXTURE_NOT_RESEARCH_TARGET')
 return SIM(window,'LONG_SHORT',PORT.native.COSTS[0],PORT.native.UNITS[0],target_factory=targets,account_factory=FINE)

class Tests(unittest.TestCase):
 def test_polars_daily_parity(self):
  records=[dict(symbol=s,close_us=0,close=10.) for s in S]
  self.assertTrue(p.normalize_daily(records).equals(PORT.native.pl.DataFrame(records)))
  with self.assertRaises(p.GateError):p.normalize_daily(records+records[:1])
 def test_missing_economic_review_preaccount(self):
  with self.assertRaisesRegex(p.GateError,'WAITING_LAUNCHER_ECONOMIC_REVIEW'):p.require_economic_review(None)
  with self.assertRaisesRegex(p.GateError,'PARENT_GO'):p.require_parent_go(False,2023,'control',[])
  with self.assertRaisesRegex(p.GateError,'CONTROL_FIRST'):p.require_parent_go(True,2023,'candidate',[])
  with self.assertRaisesRegex(p.GateError,'LATER_YEAR'):p.require_parent_go(True,2024,'control',[])
 def test_wrong_source_code_registry(self):
  with tempfile.TemporaryDirectory() as d:
   f=Path(d)/'SOURCE_INDEX.json';f.write_bytes(b'bad')
   for name in ['SOURCE_INDEX.json','scheduler.py','registry.py','FINE_PROFILE.json']:
    q=Path(d)/name;q.write_bytes(b'bad')
    with self.assertRaises(p.GateError):p.check(q,'0'*64)
  # Real original manifest closure also rejects a relocated wrong registry file.
  bad=dict(ROOTS,repo='/NONEXISTENT_SYNTHETIC_CODE_ROOT')
  with self.assertRaises(p.GateError):p.verify_port_closure(bad)
 def test_target_schema_hash_clock_mask(self):
  # Tiny constant-valued synthetic contract fixture, no saved strategy targets.
  start,end=p.inputs.registry()['years']['2023']['calendar'];n=365
  arrays={'decision_us':np.arange(start,end,DAY,dtype=np.int64),'symbol_order':np.array(S,dtype='<U8'),'PRICE_ONLY_CSH':np.zeros((n,5),np.float64),'FUNDING_ADJUSTED_CSH':np.zeros((n,5),np.float64),'annual_covariance':np.zeros((n,5,5),np.float64),'original_daily_admission':np.ones(n,bool),'required_source_not_ready':np.zeros(n,bool),'owning_rank_us':np.full(n,start-DAY,np.int64),'owning_rank_source_known':np.ones(n,bool)}
  hashes={k:hashlib.sha256(v.tobytes()).hexdigest() for k,v in arrays.items()}
  bound=p.validate_saved_arrays({k:v.copy() for k,v in arrays.items()},2023,hashes);self.assertFalse(bound['candidate'].flags.writeable)
  for key in ('decision_us','PRICE_ONLY_CSH','original_daily_admission'):
   bad={k:v.copy() for k,v in arrays.items()};bad[key].flat[0]=not bad[key].flat[0] if bad[key].dtype==bool else bad[key].flat[0]+1
   with self.assertRaises(p.GateError):p.validate_saved_arrays(bad,2023,hashes)
  with self.assertRaises(p.GateError):p.validate_saved_arrays({},2023)
 def test_funding_before_first_fill_and_owned_quantity(self):
  sim=fixture(events=[dict(event_us=M+1,symbol='BTCUSDT',raw_rate=.001),dict(event_us=2*M+1,symbol='BTCUSDT',raw_rate=.001)])
  sim.advance_day();first,second=sim.funding_journal
  self.assertFalse(first['owned']);self.assertEqual(D(str(first['signed_funding_USDT'])),0)
  self.assertTrue(second['owned']);self.assertEqual(D(str(second['signed_funding_USDT'])),D('-.3'))
  self.assertEqual(sim.account.trades[0]['event_us'],M+1)
 def test_core5_shared_cash_costs(self):
  sim=fixture();self.assertEqual(sim.account.free_cash,D('10000'));self.assertEqual(tuple(sim.account.positions),S)
  sim.advance_day();self.assertEqual(sim.account.config.leverage,D('1'));self.assertEqual(sim.account.config.max_gross_weight,D('.6'));self.assertEqual(sim.account.config.max_asset_weight,D('.3'));self.assertEqual(sim.account.config.maintenance_margin_rate,D('.005'))
  self.assertGreater(sim.account.fees,0);self.assertGreater(sim.account.execution_cost,0)
  for f in sim.account.trades:
   ds=f['decimal_strings'];self.assertEqual(D(ds['fee_amount']),abs(D(ds['quantity'])*D(ds['fill_price']))*D('.00055'))
 def test_shared_capacity_reduce_then_increase(self):
  sim=fixture();sim.account.update_marks(0,{s:dict(price=D('10'),close_us=0,available_us=0) for s in S});sim.previous_quote=dict.fromkeys(S,10000.)
  sim.schedule(dict(BTCUSDT=D('1'),ETHUSDT=D(0),SOLUSDT=D(0),XRPUSDT=D(0),DOGEUSDT=D(0)),0,'DAILY_TARGET');sim.attempt(M,{s:dict(open=10.) for s in S})
  self.assertEqual(sim.account.positions['BTCUSDT'].quantity,D('1'))
  sim.previous_quote=dict.fromkeys(S,30000.);sim.schedule(dict(BTCUSDT=D('-5'),ETHUSDT=D(0),SOLUSDT=D(0),XRPUSDT=D(0),DOGEUSDT=D(0)),M,'DAILY_TARGET');before=len(sim.account.trades);sim.attempt(2*M,{s:dict(open=10.) for s in S})
  fills=sim.account.trades[before:];self.assertEqual(sum(D(f['decimal_strings']['quantity']) for f in fills),D('3'));self.assertEqual(sim.account.positions['BTCUSDT'].quantity,D('-2'))
 def test_terminal60_and_five_nonterminal(self):
  sim=fixture();sim.advance_day();signal=DAY-61*M;fills=[f for f in sim.account.trades if f['signal_us']==signal]
  self.assertEqual(signal,23*60*M-M);self.assertEqual(sorted(set(f['event_us'] for f in fills)),[t+1 for t in range(DAY-60*M,DAY,M)])
  self.assertFalse(any(f['signal_us']==DAY-6*M for f in sim.account.trades));self.assertFalse(sim.final_day_target_zero)
  self.assertFalse(sim.result()['summary']['terminal_cash_realized']);self.assertEqual(p.classify(sim.result()['summary']),'FULL_MARKED_NOT_PAID')
  q=fixture();q.account.update_marks(0,{s:dict(price=D('10'),close_us=0,available_us=0) for s in S});q.previous_quote=dict.fromkeys(S,0.);q.schedule(dict.fromkeys(S,D('10')),0,'DAILY_TARGET')
  for t in range(M,6*M,M):q.attempt(t,{s:dict(open=10.) for s in S})
  self.assertEqual(len(q.pending),0);self.assertEqual(len([r for r in q.rejections if r['reason']=='FIVE_ATTEMPTS_EXPIRED']),5)
 def test_terminal_priority_reduce_only(self):
  sim=fixture(weight=.02,quote=300000.);sim.advance_day();self.assertTrue(sim.result()['summary']['terminal_cash_realized']);self.assertEqual(p.classify(sim.result()['summary']),'PAID_FLAT')
  with self.assertRaises(ValueError):sim.schedule(dict.fromkeys(S,D('1')),sim.terminal_signal_us,'TERMINAL')
  with self.assertRaises(ValueError):sim.schedule(dict.fromkeys(S,D('0')),DAY-2*M,'DAILY_TARGET')
 def test_registry_and_scheduler_real_closure_rejection(self):
  import shutil
  repo=Path(ROOTS['repo']);manifests=['LOCAL_CODE_MANIFEST.json','LOCAL_CODE_MANIFEST_2025.json']
  with tempfile.TemporaryDirectory() as d:
   temp=Path(d);names=set()
   for name in manifests:
    source=repo/'research/static50-sma-20261013'/name;dst=temp/'research/static50-sma-20261013'/name;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,dst);names.update(json.loads(source.read_text())['sha256'])
   for name in names:
    dst=temp/name;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(repo/name,dst)
   for name in ['scripts/research_v8/registry.py','scripts/investment/resumable_perpetual.py']:
    path=temp/name;original=path.read_bytes();path.write_bytes(b'CORRUPT_SYNTHETIC_COPY')
    with self.assertRaisesRegex(p.GateError,Path(name).name):p.verify_port_closure(dict(ROOTS,repo=str(temp)))
    path.write_bytes(original)
 def test_owned_funding_preterminal_fill(self):
  event=DAY-60*M+1;sim=fixture(events=[dict(event_us=event,symbol='BTCUSDT',raw_rate=.001)]);sim.advance_day()
  self.assertTrue(sim.funding_journal[0]['owned']);self.assertEqual(D(str(sim.funding_journal[0]['signed_funding_USDT'])),D('-.99'))
  self.assertEqual(min(f['event_us'] for f in sim.account.trades if f['signal_us']==DAY-61*M),event)
 def test_exact_terminal_attempt_copy(self):
  import terminal_adapter as t
  original=inspect.getsource(t.NativeDailySimulator.attempt)
  expected=original.replace("elif order['attempts']>=5:","elif order['attempts']>=(60 if order['kind']=='TERMINAL' else 5):").replace("reason='FIVE_ATTEMPTS_EXPIRED',","reason='SIXTY_TERMINAL_ATTEMPTS_EXPIRED' if order['kind']=='TERMINAL' else 'FIVE_ATTEMPTS_EXPIRED',")
  self.assertEqual(inspect.getsource(SIM.attempt),expected)
if __name__=='__main__':unittest.main(verbosity=2)
