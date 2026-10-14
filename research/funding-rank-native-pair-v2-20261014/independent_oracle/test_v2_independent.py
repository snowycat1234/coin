"""Independent V2 miniature oracle; no historical source, targets or dispatcher child."""
from pathlib import Path
from decimal import Decimal as D
import argparse,hashlib,importlib,json,sys,tempfile,time,unittest
import numpy as np
ap=argparse.ArgumentParser(add_help=False);ap.add_argument('--module',type=Path,required=True);ap.add_argument('--roots',type=Path,required=True);a,tail=ap.parse_known_args();sys.argv=[sys.argv[0],*tail]
MODULE=a.module.resolve();sys.path.insert(0,str(MODULE));import v2_launcher as v
if Path(v.__file__).resolve()!=MODULE/'v2_launcher.py':raise RuntimeError('Subject shadow')
ROOTS=json.loads(a.roots.read_text());PORT,FINE,SIM=v.load_engine(ROOTS);M=v.M;DAY=v.DAY;S=v.S

def raw(clock,weights):
 n=len(clock)
 return {'decision_us':clock.copy(),'symbol_order':np.array(S,dtype='<U8'),'PRICE_ONLY_CSH':np.asarray(weights,np.float64).copy(),'FUNDING_ADJUSTED_CSH':np.asarray(weights,np.float64).copy(),'annual_covariance':np.zeros((n,5,5),np.float64),'original_daily_admission':np.ones(n,bool),'required_source_not_ready':np.zeros(n,bool),'owning_rank_us':np.full(n,-7*DAY,np.int64),'owning_rank_source_known':np.ones(n,bool)}

def fixture(days=1,weights=None,transport=False,terminal_quote=10000.,events=()):
 if days not in (1,2):raise ValueError('Only miniature days')
 clock=np.arange(0,days*DAY,DAY,dtype=np.int64);weights=weights or [[.1,0,0,0,-.1]]*days
 bound=v.validate_raw(raw(clock,weights),clock)
 market={s:{'open':np.full(days*1440,10.),'close':np.full(days*1440,10.),'mark':np.full(days*1440,10.),'quote_volume':np.full(days*1440,300000.)} for s in S}
 for row in market.values():row['quote_volume'][-61:]=terminal_quote
 records=[dict(symbol=s,close_us=int(t),close=10.) for t in clock for s in S]
 window=dict(start=0,end=days*DAY,symbols=S,daily=v.daily_frame(records) if transport else PORT.native.pl.DataFrame(records),events=list(events))
 if transport:
  def blocks():
   for off in range(0,days*1440,1440):yield dict(times=np.arange(off*M,(off+1440)*M,M,dtype=np.int64),market={s:{k:x[off:off+1440] for k,x in row.items()} for s,row in market.items()})
  window['minute_blocks']=blocks
  factory=v.exact_factory(bound,'control',PORT.native.pl)
 else:
  window['market']=market
  def factory(_daily,clocks,mode):
   np.testing.assert_array_equal(clocks,clock)
   if mode!='LONG_SHORT':raise ValueError('mode')
   return PORT.native.pl.DataFrame([dict(available_us=int(t),symbol=s,target_weight=float(bound['control'][i,j])) for i,t in enumerate(clock) for j,s in enumerate(S)]),{'source':'INDEPENDENT_DIRECT_TOY'}
 return SIM(window,'LONG_SHORT',PORT.native.COSTS[0],PORT.native.UNITS[0],target_factory=factory,account_factory=FINE)

def finish(sim):
 while sim.cursor<sim.end and sim.stop is None:sim.advance_day()
 return sim

class Oracle(unittest.TestCase):
 def test_actual_financial_import_identity_and_shadow_gate(self):
  dep=json.loads((MODULE/'SYNTHETIC_DEPENDENCIES.json').read_text())['files'];base=Path(ROOTS['repo']).parent
  names=['quant.execution_contract','quant.perpetual_account','quant.disk','quant.metrics','quant.paths','quant.resources','scripts.investment.resumable_perpetual','scripts.investment.perpetual_directional','scripts.investment.bybit_cost_inputs','scripts.investment.perpetual_closing_exempt_account','scripts.research_v8.funding_price_source_v2','scripts.research_v8.registry','fine_account','freeze_bootstrap']
  for name in names:
   module=importlib.import_module(name);path=Path(module.__file__).resolve();relative=str(path.relative_to(base));self.assertIn(relative,dep);self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(),dep[relative]['SHA256'])
  self.assertEqual(Path(importlib.import_module('terminal_adapter').__file__).resolve(),MODULE/'terminal_adapter.py');self.assertIs(SIM.__bases__[0],PORT.native.NativeDailySimulator)
  module=importlib.import_module('quant.perpetual_account');old=module.__file__
  try:
   module.__file__='/UNTRUSTED_SYNTHETIC_SHADOW/perpetual_account.py'
   with self.assertRaises(v.GateError):v.load_engine(ROOTS)
  finally:module.__file__=old

 def test_direct_native_vs_worker_block_transport_finance(self):
  events=[dict(event_us=M+1,symbol='BTCUSDT',raw_rate=.001),dict(event_us=2*M+1,symbol='BTCUSDT',raw_rate=.001),dict(event_us=2*M+1,symbol='DOGEUSDT',raw_rate=.001)]
  direct=finish(fixture(events=events));wrapped=finish(fixture(transport=True,events=events))
  self.assertEqual(direct.account.snapshot(),wrapped.account.snapshot());self.assertEqual(direct.funding_journal,wrapped.funding_journal);self.assertEqual(direct.account.trades,wrapped.account.trades);self.assertEqual(direct.rejections,wrapped.rejections);np.testing.assert_array_equal(direct.minute_chunks[0],wrapped.minute_chunks[0])
  self.assertFalse(wrapped.funding_journal[0]['owned']);self.assertEqual(D(str(wrapped.funding_journal[1]['signed_funding_USDT'])),D('-.3'));self.assertEqual(D(str(wrapped.funding_journal[2]['signed_funding_USDT'])),D('.3'));self.assertEqual(wrapped.account.config.initial_cash,D('10000'));self.assertEqual(tuple(wrapped.account.positions),S)

 def test_reconverged_targets_require_full_independent_replay(self):
  c=fixture(days=2,transport=True,terminal_quote=300000.);f=fixture(days=2,weights=[[.15,0,0,0,-.15],[.1,0,0,0,-.1]],transport=True,terminal_quote=300000.)
  c.advance_day();f.advance_day();self.assertEqual(c.weights[DAY],f.weights[DAY]);self.assertNotEqual(c.account.nav(),f.account.nav());c.advance_day();f.advance_day()
  self.assertEqual(c.rows_written,2880);self.assertEqual(f.rows_written,2880);self.assertTrue(c.result()['summary']['terminal_cash_realized']);self.assertTrue(f.result()['summary']['terminal_cash_realized']);self.assertNotEqual(c.account.nav(),f.account.nav())

 def test_exact_dispatch_loop_snapshot_and_decimal_bridge(self):
  import dispatcher
  direct=finish(fixture(weights=[[.02,0,0,0,-.02]],terminal_quote=300000.));sim=fixture(weights=[[.02,0,0,0,-.02]],transport=True,terminal_quote=300000.)
  with tempfile.TemporaryDirectory() as tmp:
   out=Path(tmp)/'case';binding={'fixture':'INDEPENDENT_TOY_BLOCKS'};result=dispatcher.calendar_loop(sim,PORT,out,binding,time.monotonic()+60)
   self.assertEqual(result['status'],'PAID_FLAT');self.assertEqual(D(result['summary']['paid_NAV_decimal']),direct.account.nav());self.assertEqual(json.loads((out/'FILLS.json').read_text()),direct.account.trades);self.assertEqual(json.loads((out/'FUNDING.json').read_text()),direct.funding_journal)
   snapshot,pointer=PORT.restore_snapshot(out/'checkpoint',binding);restored=SIM.from_snapshot(snapshot,sim.window,account_class=FINE);self.assertEqual(restored.state_hash(),sim.state_hash());self.assertEqual(restored.account.snapshot(),sim.account.snapshot());np.testing.assert_array_equal(restored.minute_chunks[0],sim.minute_chunks[0])
  r=sim.result();_,inventory=PORT.native.episodes(r['trades'],S);self.assertEqual(inventory,{s:sim.account.positions[s].quantity for s in S});bridge=PORT.native.nav_bridge(r['trades'],r['funding'],inventory,r['summary']['terminal_mark_prices'],sim.account.nav());self.assertLessEqual(D(bridge['maximum_error_USDT']),D('1e-8'))

 def test_actual_factory_cap_mask_and_raw_identity(self):
  clocks=np.array([0],np.int64)
  for row in ([.31,0,0,0,0],[.2,.2,.2,.01,0],[float('nan'),0,0,0,0]):
   with self.assertRaises(v.GateError):v.validate_raw(raw(clocks,[row]),clocks)
  bound=v.validate_raw(raw(clocks,[[.1,0,0,0,-.1]]),clocks);frame,_=v.exact_factory(bound,'control',PORT.native.pl)(None,clocks,'LONG_SHORT');self.assertEqual(frame.height,5);self.assertFalse(bound['control'].flags.writeable)
  bad=frame.to_dicts();bad[0]['target_weight']=.11
  with self.assertRaisesRegex(v.GateError,'EXACT_ARM_BYTES'):v.validate_target_frame(PORT.native.pl.DataFrame(bad),clocks,bound,'control')

 def test_dispatch_review_and_go_fail_before_finance(self):
  import dispatcher
  with self.assertRaisesRegex(v.GateError,'WAITING_INDEPENDENT'):v.require_review()
  with self.assertRaises(v.GateError):dispatcher.go_identity(None,None,'0'*40,2023,'control',[])
  with tempfile.TemporaryDirectory() as tmp:
   path=Path(tmp)/'go.json';path.write_text(json.dumps({'schema':'EXPLICIT_PARENT_V2_YEAR_PAIR_GO_V1','publication_commit':'0'*40,'parent_GO':True,'year':2023,'arms':['control','candidate']}));h=v.sha(path)
   self.assertEqual(dispatcher.go_identity(path,h,'0'*40,2023,'control',[])['year'],2023)
   with self.assertRaisesRegex(v.GateError,'CONTROL_FIRST'):dispatcher.go_identity(path,h,'0'*40,2023,'candidate',[])
   with self.assertRaises(v.GateError):dispatcher.go_identity(path,h,'0'*40,2024,'control',[])
   with self.assertRaises(v.GateError):dispatcher.go_identity(path,'0'*64,'0'*40,2023,'control',[])

if __name__=='__main__':unittest.main(verbosity=2)
