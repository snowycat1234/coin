"""Necessary pure observer counterexamples. No real wallet/source/cold restore."""
from pathlib import Path
from tempfile import TemporaryDirectory
from decimal import Decimal as D
from types import SimpleNamespace
import ast,importlib.util,json,sys,unittest
from unittest.mock import patch
from copy import deepcopy
H=Path(__file__).resolve().parent;M=H.parent/'coin_headroom_risk_candidate_postrun_audit_20261013';sys.path.insert(0,str(M))
spec=importlib.util.spec_from_file_location('independent_headroom_observer',M/'cold_audit.py');a=importlib.util.module_from_spec(spec);spec.loader.exec_module(a)
class Minute:
 def __init__(self,x):self.x=x;self.height=len(x)
 def drop(self,name):return self
 def to_numpy(self):return self.x
class ObserverTests(unittest.TestCase):
 def test_prefix_includes_signal_close_and_excludes_later_changed_execution(self):
  import numpy as np
  with TemporaryDirectory(dir=H) as d:
   root=Path(d);(root/'recovery').mkdir();old=np.zeros((2,36),np.float64);old[:,0]=10000;p=root/'recovery/a.npz';np.savez_compressed(p,minute_chunk=old)
   funding=[{'event_us':a.MINUTE,'symbol':'A','owned':True}];(root/'ACCOUNT.json').write_text(json.dumps({'trades':[],'funding':funding,'summary':dict.fromkeys(['gross_PnL_same_quantities','gross_fill_turnover_USDT','fees_USDT','execution_cost_USDT','funding_USDT'],0)}))
   ptr={'completed_minutes':2,'chunks':[{'path':'a.npz','SHA256':a.sha(p),'rows':2,'columns':36}]}
   new=old.copy();new[1,0]=10
   out={'minute':Minute(new),'trades':[{'event_us':2*a.MINUTE+1,'symbol':'A'}],'funding':funding,'protective_policy':{'events':[{'kind':'FULL_EXIT_SIGNAL','event_us':a.MINUTE}]}}
   proof=a.prefix_proof(out,{'calendar':[0,2*a.MINUTE]},root,ptr);self.assertEqual(proof['minute_rows'],1);self.assertTrue(proof['through_first_HEADROOM_signal']);self.assertEqual(proof['funding_rows'],1)
   out['funding']=[{'event_us':a.MINUTE,'symbol':'A','owned':False}]
   with self.assertRaisesRegex(ValueError,'funding exact inclusive'):a.prefix_proof(out,{'calendar':[0,2*a.MINUTE]},root,ptr)
   out['funding']=funding;new[0,0]=1
   with self.assertRaisesRegex(ValueError,'minute prefix bits'):a.prefix_proof(out,{'calendar':[0,2*a.MINUTE]},root,ptr)
 def test_same_clock_funding_sees_only_strictly_earlier_fills(self):
  x={'quantity':'1','mid_price':'100','fill_price':'100.08','fee_amount':'.055044','execution_cost':'.08','realized_PnL':'0','margin_allocated':'100.08','position_delta':'1'}
  raw={'symbol':'A','event_us':a.MINUTE+1,'raw_rate':.001};fund={**raw,'quantity':0.,'owned':False,'mark_price':100.,'mark_close_us':a.MINUTE,'signed_funding_USDT':0.,'conditional_rate_scale':1.,'assumed_fraction_decimal':'.001','decimal_strings':{'quantity':'0','mark_price':'100','signed_funding_USDT':'0'}}
  account=SimpleNamespace(fees=D('.055044'),execution_cost=D('.08'),realized_PnL=D(0),funding_cash=D(0),gross_fill_turnover=D('100.08'),free_cash=D('9899.864956'),unpaid_liability=D(0),positions={'A':SimpleNamespace(quantity=D(1),entry_price=D('100.08'),isolated_balance=D('100.08'))},marks={'A':[{'price':D(100)}]},nav=lambda:D('9999.864956'))
  out={'trades':[{'symbol':'A','side':'BUY','leg':'OPEN','event_us':a.MINUTE+1,'decimal_strings':x}],'funding':[fund]}
  self.assertEqual(a.ledger_proof(account,out,{'symbols':['A'],'events':[raw]})['source_funding_rows_verified'],1)
  fund['owned']=True;fund['decimal_strings']['quantity']='1'
  with self.assertRaisesRegex(ValueError,'pre-funding signed inventory'):a.ledger_proof(account,out,{'symbols':['A'],'events':[raw]})
 def test_all_named_transition_calls_forbidden_even_on_result_inspection(self):
  class Sim:pass
  class Account:pass
  with a.forbid_transitions(Sim,Account):
   for name in ['advance_day','schedule','attempt','funding_through','risk_schedule','observe']:
    with self.assertRaisesRegex(RuntimeError,'financial transition'):getattr(Sim(),name)()
   for name in ['execute_fill','apply_funding','update_marks']:
    with self.assertRaisesRegex(RuntimeError,'financial transition'):getattr(Account(),name)()
  self.assertEqual(Sim.__dict__.keys() & {'advance_day','schedule','attempt','funding_through','risk_schedule','observe'},set())
 def test_paid_classification_requires_full_CORE5_Decimal_flat_and_no_halt(self):
  tree=ast.parse((M/'cold_audit.py').read_text());main=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='main')
  statements=[n for n in main.body if isinstance(n,ast.Assign) and len(n.targets)==1 and isinstance(n.targets[0],ast.Name) and n.targets[0].id in {'full','all_exact_flat','paid'}]
  self.assertEqual(len(statements),3);code=compile(ast.fix_missing_locations(ast.Module(body=statements,type_ignores=[])),'reviewed_paid_assignments','exec')
  symbols=['BTCUSDT','ETHUSDT','SOLUSDT','XRPUSDT','DOGEUSDT']
  def evaluate(rows,status='ACTIVE',residual=None):
   positions={s:SimpleNamespace(quantity=D(0)) for s in symbols}
   if residual is not None:positions['XRPUSDT'].quantity=D(residual)
   env={'sim':SimpleNamespace(rows_written=rows,account=SimpleNamespace(positions=positions)),'required':10,'source':{'symbols':symbols},'summary':{'completion':'COMPLETE_CONDITIONAL_ACCOUNT','account_status':status},'Decimal':D};exec(code,env);return env
  self.assertTrue(evaluate(10)['paid']);self.assertFalse(evaluate(9)['paid']);self.assertFalse(evaluate(10,'BANKRUPT_HALT')['paid']);self.assertFalse(evaluate(10,'LIQUIDATION_REQUIRED_HALT')['paid']);self.assertFalse(evaluate(10,residual='0.00000001')['paid'])
 def test_protective_sixth_open_remains_valid_and_duplicate_same_open_rejected(self):
  class Points:
   def __init__(self,root):pass
   def at(self,symbol,stamp,field):return D(100) if field=='open' else D(100000)
  source={'start':0,'end':24*a.MINUTE};out={'protective_policy':{'events':[{'kind':'FULL_EXIT_SIGNAL','symbol':'A','event_us':a.MINUTE}]}}
  requests={}
  for i in range(6):
   open_us=(i+2)*a.MINUTE
   identity={'symbol':'A','event_us':open_us+1,'signal_us':a.MINUTE,'quote_available_us':open_us,'execution_mid_price':'100','available_quantity':'1','reduce_only':True}
   receipt={'fill_id':f'protection:{i}:REDUCE','fills':[{'leg':'CLOSE','decimal_strings':{'quantity':'.2','quantity_before':'1','quantity_after':'.8','margin_allocated':'0'}}]}
   requests[str(i)]={'identity':identity,'receipt':receipt}
  snapshot={'account':{'fill_requests':requests}}
  with patch.object(a,'SourcePoints',Points):
   proof=a.execution_proof(snapshot,out,source,Path('.'));self.assertEqual(proof['maximum_observed_protective_attempt_number'],6)
   extra=deepcopy(requests['5']);extra['identity']['available_quantity']='.8';extra['receipt']['fill_id']='protection:6:REDUCE';requests['duplicate']=extra
   with self.assertRaisesRegex(ValueError,'one protective reduce'):a.execution_proof(snapshot,out,source,Path('.'))
if __name__=='__main__':unittest.main(verbosity=2)
