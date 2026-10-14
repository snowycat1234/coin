"""Synthetic direct-native vs V2 two-arm parity. No historical source reader."""
import unittest,json,sys,inspect,tempfile,hashlib,shutil
from pathlib import Path
import numpy as np
import v2_launcher as v
ROOTS=json.loads(Path(sys.argv.pop(1)).read_text()) if len(sys.argv)>1 else {}
PORT,ACCOUNT,SIM=v.load_engine(ROOTS);D=__import__('decimal').Decimal;S=v.S;M=v.M;DAY=v.DAY

def fixture(weight_control=.1,weight_candidate=.08):
 arrays={'decision_us':np.array([0],np.int64),'symbol_order':np.array(S,dtype='<U8'),'PRICE_ONLY_CSH':np.array([[weight_control,0.,0.,0.,-weight_control]],np.float64),'FUNDING_ADJUSTED_CSH':np.array([[weight_candidate,0.,0.,0.,-weight_candidate]],np.float64),'annual_covariance':np.zeros((1,5,5),np.float64),'original_daily_admission':np.ones(1,bool),'required_source_not_ready':np.zeros(1,bool),'owning_rank_us':np.array([-7*DAY],np.int64),'owning_rank_source_known':np.ones(1,bool)}
 bound=v.validate_raw(arrays,np.array([0],np.int64))
 market={s:{'open':np.full(1440,10.),'close':np.full(1440,10.),'mark':np.full(1440,10.),'quote_volume':np.full(1440,300000.)} for s in S}
 for row in market.values():row['quote_volume'][-61:]=10000.
 w=dict(fixture_identity='PURE_SYNTHETIC_CONSTANT_QUOTES',start=0,end=DAY,symbols=S,daily=[dict(symbol=s,close_us=0,close=10.) for s in S],market=market,events=[dict(event_us=M+1,symbol='BTCUSDT',raw_rate=.001),dict(event_us=2*M+1,symbol='BTCUSDT',raw_rate=.001),dict(event_us=DAY-60*M+1,symbol='BTCUSDT',raw_rate=.001)])
 return w,bound

def reference(w,bound,arm):
 # Direct unchanged API; no V2 factory/frame validator on reference path.
 window={k:x for k,x in w.items() if k!='fixture_identity'};window['daily']=PORT.native.pl.DataFrame(window['daily'])
 def factory(daily,clocks,mode):return PORT.native.pl.DataFrame([dict(available_us=int(t),symbol=s,target_weight=float(bound[arm][i,j])) for i,t in enumerate(clocks) for j,s in enumerate(S)]),dict(source='PURE_SYNTHETIC_DIRECT_API')
 return SIM(window,'LONG_SHORT',PORT.native.COSTS[0],PORT.native.UNITS[0],target_factory=factory,account_factory=ACCOUNT)

class Tests(unittest.TestCase):
 def test_dual_arm_direct_api_parity_all_finance(self):
  for weights in [(.1,.08),(.02,.01)]:
   for arm in ('control','candidate'):
    with self.subTest(weights=weights,arm=arm):
     w,b=fixture(*weights);direct=reference(w,b,arm);adapted=v.construct_synthetic(ROOTS,w,b,arm)
     self.assertEqual(direct.account.free_cash,D('10000'));self.assertEqual(adapted.account.free_cash,D('10000'))
     direct.advance_day();adapted.advance_day()
     np.testing.assert_array_equal(direct.minute_chunks[0],adapted.minute_chunks[0])
     self.assertEqual(direct.account.trades,adapted.account.trades);self.assertEqual(direct.funding_journal,adapted.funding_journal);self.assertEqual(direct.rejections,adapted.rejections)
     self.assertEqual(direct.account.snapshot(),adapted.account.snapshot());self.assertEqual(direct.result()['summary'],adapted.result()['summary'])
     self.assertEqual(direct.account.nav(),adapted.account.nav());self.assertEqual(direct.account.fees,adapted.account.fees);self.assertEqual(direct.account.execution_cost,adapted.account.execution_cost);self.assertEqual(direct.account.funding_cash,adapted.account.funding_cash)
     self.assertFalse(adapted.funding_journal[0]['owned']);self.assertTrue(adapted.funding_journal[1]['owned']);self.assertEqual(D(str(adapted.funding_journal[1]['signed_funding_USDT'])),min(D(str(weights[0] if arm=='control' else weights[1]))*D('990'),D('30'))*D('-.01'))
 def test_polars_daily_original_parity(self):
  w,b=fixture();self.assertTrue(v.daily_frame(w['daily']).equals(PORT.native.pl.DataFrame(w['daily'])))
 def test_terminal_original_byte_copy_clock_and_priority(self):
  import terminal_adapter as term
  native=inspect.getsource(term.NativeDailySimulator.attempt);expected=native.replace("elif order['attempts']>=5:","elif order['attempts']>=(60 if order['kind']=='TERMINAL' else 5):").replace("reason='FIVE_ATTEMPTS_EXPIRED',","reason='SIXTY_TERMINAL_ATTEMPTS_EXPIRED' if order['kind']=='TERMINAL' else 'FIVE_ATTEMPTS_EXPIRED',")
  self.assertEqual(inspect.getsource(SIM.attempt),expected)
  w,b=fixture();sim=v.construct_synthetic(ROOTS,w,b,'control');sim.advance_day();self.assertEqual(sim.terminal_signal_us,23*60*M-M);self.assertFalse(sim.final_day_target_zero)
  fills=[f for f in sim.account.trades if f['signal_us']==sim.terminal_signal_us]
  self.assertEqual(sorted(set(f['event_us'] for f in fills)),[t+1 for t in range(DAY-60*M,DAY,M)])
  with self.assertRaises(ValueError):sim.schedule(dict.fromkeys(S,D('1')),sim.terminal_signal_us,'TERMINAL')
  with self.assertRaises(ValueError):sim.schedule(dict.fromkeys(S,D('0')),DAY-M,'DAILY_TARGET')
 def test_shared_cash_capacity_and_five_attempts(self):
  w,b=fixture();sim=v.construct_synthetic(ROOTS,w,b,'control');self.assertEqual(tuple(sim.account.positions),S);sim.account.update_marks(0,{s:dict(price=D('10'),close_us=0,available_us=0) for s in S});sim.previous_quote=dict.fromkeys(S,10000.)
  target=dict.fromkeys(S,D(0));target['BTCUSDT']=D('1');sim.schedule(target,0,'DAILY_TARGET');sim.attempt(M,{s:dict(open=10.) for s in S});self.assertEqual(sim.account.positions['BTCUSDT'].quantity,D('1'))
  sim.previous_quote=dict.fromkeys(S,30000.);target['BTCUSDT']=D('-5');sim.schedule(target,M,'DAILY_TARGET');before=len(sim.account.trades);sim.attempt(2*M,{s:dict(open=10.) for s in S});self.assertEqual(sum(D(f['decimal_strings']['quantity']) for f in sim.account.trades[before:]),D('3'));self.assertEqual(sim.account.positions['BTCUSDT'].quantity,D('-2'))
  q=v.construct_synthetic(ROOTS,w,b,'control');q.account.update_marks(0,{s:dict(price=D('10'),close_us=0,available_us=0) for s in S});q.previous_quote=dict.fromkeys(S,0.);q.schedule(dict.fromkeys(S,D('10')),0,'DAILY_TARGET')
  for t in range(M,6*M,M):q.attempt(t,{s:dict(open=10.) for s in S})
  self.assertEqual(len(q.pending),0);self.assertEqual(len([r for r in q.rejections if r['reason']=='FIVE_ATTEMPTS_EXPIRED']),5)
 def test_factory_tamper_pre_account(self):
  # Native simulator would create account AFTER its factory; spy proves guards reject first.
  w,b=fixture();window={k:x for k,x in w.items() if k!='fixture_identity'};window['daily']=v.daily_frame(window['daily']);calls=[]
  def spy(*args,**kwargs):calls.append(True);raise AssertionError('ACCOUNT_CREATED_TOO_EARLY')
  for kind in ('nan','asset','gross','clock','order','mask','exact'):
   with self.subTest(kind=kind):
    def factory(daily,clocks,mode):
     frame=PORT.native.pl.DataFrame([dict(available_us=0,symbol=s,target_weight=float(b['control'][0,j])) for j,s in enumerate(S)])
     data=frame.to_dicts();current=b
     if kind=='nan':data[0]['target_weight']=float('nan')
     if kind=='asset':data[0]['target_weight']=.31
     if kind=='gross':
      for r in data:r['target_weight']=.2
     if kind=='clock':data[0]['available_us']=M
     if kind=='order':data=data[::-1]
     if kind=='exact':data[0]['target_weight']+=.001
     if kind=='mask':
      current={'control':b['control'],'raw_arrays':dict(b['raw_arrays'])};current['raw_arrays']['original_daily_admission']=np.array([False])
     return v.validate_target_frame(PORT.native.pl.DataFrame(data),clocks,current,'control'),{}
    with self.assertRaises(v.GateError):SIM(window,'LONG_SHORT',PORT.native.COSTS[0],PORT.native.UNITS[0],target_factory=factory,account_factory=spy)
  self.assertEqual(calls,[])
 def test_code_registry_source_target_hash_reject(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d)
   for n in ('registry.py','resumable_perpetual.py','SOURCE_INDEX.json','Y2023_TARGETS.npz'):
    q=root/n;q.write_bytes(b'TAMPER');
    with self.assertRaises(v.GateError):v.check(q,'0'*64)
   # Actual original26-file financial guard rejects a corrupted registry in a private copy.
   repo=Path(ROOTS['repo']);closure=json.loads((v.HERE/'EXECUTABLE_CLOSURE.json').read_text())
   for n in [*closure['repo_files'],closure['financial_port_manifest']['path']]:
    p=root/n;p.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(repo/n,p)
   (root/'scripts/research_v8/registry.py').write_bytes(b'TAMPER')
   with self.assertRaises(ValueError):v.verify_financial(dict(ROOTS,repo=str(root)))
 def test_missing_review_go_and_review_tamper_preaccount(self):
  calls=[]
  with self.assertRaisesRegex(v.GateError,'WAITING_INDEPENDENT'):v.history_admission(ROOTS,2023,'control')
  with self.assertRaisesRegex(v.GateError,'LATER_YEAR'):v.require_parent_go(True,2024,'control')
  with self.assertRaisesRegex(v.GateError,'CONTROL_FIRST'):v.require_parent_go(True,2023,'candidate')
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'review.json';commit='0'*40
   good={'schema':'INDEPENDENT_V2_NATIVE_PAIR_PUBLICATION_REVIEW_V1','status':'PASS_EXACT_V2_PREPARATION_NO_HISTORY','publication_commit':commit,'V2_FREEZE_SHA256':v.sha(v.HERE/'V2_FREEZE.json'),'economic_protocol_SHA256':v.sha(v.HERE/'PROTOCOL.json'),'code_dependency_closure_SHA256':v.sha(v.HERE/'EXECUTABLE_CLOSURE.json'),'source_binding_SHA256':v.sha(v.HERE/'INPUT_BINDINGS.json'),'target_output_manifest_SHA256':json.loads((v.HERE/'TARGET_REMOTE_BINDING.json').read_text())['files']['OUTPUT_MANIFEST.json']['SHA256'],'synthetic_parity_review':'PASS'}
   p.write_text(json.dumps(good));h=v.sha(p)
   # Valid synthetic review does not replace parent GO; source reader is never reached.
   with self.assertRaisesRegex(v.GateError,'PARENT_GO'):v.history_admission(ROOTS,2023,'control',review=p,review_sha=h,publication_commit=commit,parent_go=False)
   for key in ('V2_FREEZE_SHA256','economic_protocol_SHA256','source_binding_SHA256','code_dependency_closure_SHA256','publication_commit'):
    bad=dict(good);bad[key]='TAMPER';p.write_text(json.dumps(bad))
    with self.assertRaisesRegex(v.GateError,'REVIEW_TAMPER'):v.require_review(p,v.sha(p),commit)
   with self.assertRaisesRegex(v.GateError,'EXACT_BYTES'):v.require_review(p,'0'*64,commit)
  self.assertEqual(calls,[])
 def test_no_history_via_synthetic_route(self):
  w,b=fixture();w['start']=1672531200000000
  with self.assertRaisesRegex(v.GateError,'SYNTHETIC_ONLY'):v.construct_synthetic(ROOTS,w,b,'control')
 def test_dispatch_path_miniature_original_parity(self):
  import dispatcher
  for arm in ('control','candidate'):
   w,b=fixture(.02,.01);direct=reference(w,b,arm);direct.advance_day()
   with tempfile.TemporaryDirectory() as d:
    result=dispatcher.dispatch_synthetic(ROOTS,w,b,arm,Path(d)/'case')
    self.assertEqual(result['status'],'PAID_FLAT');self.assertEqual(D(result['summary']['marked_NAV_decimal']),direct.account.nav());self.assertEqual(D(result['summary']['paid_NAV_decimal']),direct.account.nav())
    self.assertEqual(json.loads((Path(d)/'case/FILLS.json').read_text()),direct.account.trades);self.assertEqual(json.loads((Path(d)/'case/FUNDING.json').read_text()),direct.funding_journal)
    from_snapshot,pointer=PORT.restore_snapshot(Path(d)/'case/checkpoint',{'fixture':'PURE_SYNTHETIC_CONSTANT_QUOTES','arm':arm})
    restored=SIM.from_snapshot(from_snapshot,direct.window,account_class=ACCOUNT);self.assertEqual(restored.account.snapshot(),direct.account.snapshot());np.testing.assert_array_equal(restored.minute_chunks[0],direct.minute_chunks[0])
 def test_dispatch_missing_tampered_go_pre_account(self):
  import dispatcher
  with self.assertRaises(v.GateError):dispatcher.go_identity(None,None,'0'*40,2023,'control',[])
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'go.json';p.write_text(json.dumps({'schema':'EXPLICIT_PARENT_V2_YEAR_PAIR_GO_V1','publication_commit':'0'*40,'parent_GO':True,'year':2023,'arms':['control','candidate']}))
   self.assertEqual(dispatcher.go_identity(p,v.sha(p),'0'*40,2023,'control',[])['year'],2023)
   with self.assertRaises(v.GateError):dispatcher.go_identity(p,v.sha(p),'0'*40,2024,'control',[])
   with self.assertRaises(v.GateError):dispatcher.go_identity(p,'0'*64,'0'*40,2023,'control',[])
   with self.assertRaises(v.GateError):dispatcher.go_identity(p,v.sha(p),'0'*40,2023,'candidate',[])
 def test_raw_readonly_hash_dtype_masks(self):
  w,b=fixture();self.assertFalse(b['control'].flags.writeable);self.assertFalse(b['candidate'].flags.writeable)
  with self.assertRaises(ValueError):b['candidate'][0,0]=.2
  raw={k:a.copy() for k,a in b['raw_arrays'].items()};hashes={k:hashlib.sha256(a.tobytes()).hexdigest() for k,a in raw.items()};raw['required_source_not_ready'][0]=True
  with self.assertRaises(v.GateError):v.validate_raw(raw,np.array([0],np.int64),hashes)
if __name__=='__main__':unittest.main(verbosity=2)
