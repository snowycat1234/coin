"""Original registry source-view contract using saved proof and mocked targets.

The prefix/suffix are generated invalid values. No historical source container,
native account or financial method runs. The reviewed proof supplies only its
already accepted 564-clock price rows.
"""
from types import SimpleNamespace
from unittest import TestCase,mock
import ast,struct
import numpy as np
import bridge_bindings as B
import original_bridge as O
import original200_quality as Q

class SourceView(TestCase):
 @classmethod
 def setUpClass(cls):
  cls.quality=Q.load_original200_proof()
  cls.clock=np.arange(Q.START,Q.END+Q.DAY,Q.DAY,dtype=np.int64)
  cls.prices=np.asarray([[struct.unpack('<d',bytes.fromhex(cls.quality._rows[(int(t),s)]['close_float64_hex']))[0] for s in Q.SYMBOLS] for t in cls.clock],dtype=np.float64)
  cls.decisions=np.arange(*Q.CALENDAR,Q.DAY,dtype=np.int64)
  cls.weights=np.zeros((365,5),dtype=np.float64);cls.covariance=np.zeros((365,5,5),dtype=np.float64)
  cls.receipt={**B.read(B.HERE/'SOURCE_RECEIPT_2023.json'),'target_raw_SHA256':O.raw_sha(cls.weights),'covariance_raw_SHA256':O.raw_sha(cls.covariance)}
 def admitted(self,prefix=0,suffix=0):
  clock=np.arange(Q.START-prefix*Q.DAY,Q.END+(suffix+1)*Q.DAY,Q.DAY,dtype=np.int64)
  prices=np.full((len(clock),5),np.nan,dtype=np.float64);prices[prefix:prefix+564]=self.prices
  return dict(window=dict(start=B.CALENDAR[0],end=B.CALENDAR[1],symbols=list(Q.SYMBOLS),fixture_scope=None,market=object(),minute_blocks=object()),
   decision_us=self.decisions.copy(),clock=clock,prices=prices,source_ids=np.arange(199,564,dtype=np.int64)+prefix,
   weights=self.weights.copy(),covariance=self.covariance.copy(),original_daily_admission=np.ones(365,dtype=bool))
 def construct(self,admitted,old_constructor=None):
  import verified_source
  with mock.patch.object(B,'case_gate',return_value={}),mock.patch.object(B,'read',return_value=self.receipt),mock.patch.object(verified_source,'require_runtime',return_value=SimpleNamespace(mode='source_case',bounded_worker_admitted=True)),mock.patch.object(O.NATIVE,'__init__',side_effect=AssertionError('NATIVE_ACCOUNT_FORBIDDEN')):
   if old_constructor is not None:
    registry=O.OriginalProjectionRegistry.__new__(O.OriginalProjectionRegistry)
    old_constructor(registry,admitted,case_args=SimpleNamespace())
    return registry
   return O.OriginalProjectionRegistry(admitted,case_args=SimpleNamespace())
 def test_old_blanket_failure_new_exact_view_and_packet_identity(self):
  wide=self.admitted(800,7)
  # Reproduce the old line-54 conjunct, without reading unreviewed source rows.
  self.assertFalse(np.isfinite(wide['prices']).all())
  old=B.ROOT/'finite_original2023_bridge_author_review_20261014/rejected_c209_full_container_admission/original_bridge.py'
  klass=next(n for n in ast.parse(old.read_bytes()).body if isinstance(n,ast.ClassDef) and n.name=='OriginalProjectionRegistry')
  constructor=next(n for n in klass.body if isinstance(n,ast.FunctionDef) and n.name=='__init__');constructor.name='old_exact_registry_init'
  namespace=dict(O.__dict__);exec(compile(ast.fix_missing_locations(ast.Module(body=[constructor],type_ignores=[])),'EXACT_C209_REGISTRY_SOURCE_VIEW_REPRO','exec'),namespace)
  with self.assertRaisesRegex(ValueError,'FINITE_COMPLETE_ORIGINAL_PROJECTION_REQUIRED'):
   self.construct(wide,namespace['old_exact_registry_init'])
  before={name:array.tobytes() for name,array in wide.items() if isinstance(array,np.ndarray)}
  registry=self.construct(wide);core=self.construct(self.admitted())
  self.assertEqual(registry.clock.tobytes(),self.clock.tobytes());self.assertEqual(registry.prices.tobytes(),self.prices.tobytes())
  self.assertEqual(registry.ids.tobytes(),np.arange(199,564,dtype=np.int64).tobytes())
  self.assertEqual(registry.original.tobytes(),wide['weights'].tobytes());self.assertEqual(registry.covariance.tobytes(),wide['covariance'].tobytes())
  self.assertEqual(dict(registry.packets),dict(core.packets));self.assertEqual(dict(registry.approvals),dict(core.approvals))
  self.assertEqual(registry.quality_identity['proof_SHA256'],Q.PROOF_SHA)
  for name,bits in before.items():self.assertEqual(wide[name].tobytes(),bits)
  self.assertFalse(np.shares_memory(registry.prices,wide['prices']));self.assertFalse(np.shares_memory(registry.clock,wide['clock']))
  self.assertEqual(len(registry.packets),365)
 def test_invalid_required_price_never_filtered_or_filled(self):
  for value in (np.nan,np.inf,0.,-1.,np.nextafter(self.prices[0,0],np.inf)):
   admitted=self.admitted(8,2);admitted['prices'][8,0]=value
   with self.assertRaisesRegex(ValueError,'FINITE_COMPLETE_ORIGINAL_PROJECTION_REQUIRED|ORIGINAL200_SOURCE_PRICE_PROOF_BIT_MISMATCH'):self.construct(admitted)
 def test_missing_clock_or_wrong_required_source_id_refused(self):
  admitted=self.admitted(8,2);admitted['clock'][8]+=1
  with self.assertRaisesRegex(ValueError,'EXACT_REVIEWED564'):self.construct(admitted)
  admitted=self.admitted(8,2);admitted['source_ids'][0]+=1
  with self.assertRaisesRegex(ValueError,'EXACT_ORIGINAL_PROJECTION_SHAPE_CLOCK_ORDER'):self.construct(admitted)
  admitted=self.admitted(8,2);admitted['clock']=np.delete(admitted['clock'],8);admitted['prices']=np.delete(admitted['prices'],8,axis=0);admitted['source_ids']-=1
  with self.assertRaisesRegex(ValueError,'EXACT_REVIEWED564'):self.construct(admitted)
 def test_target_covariance_and_financial_source_guards_unchanged(self):
  for field in ('weights','covariance'):
   for value in (np.nan,1.):
    admitted=self.admitted(8,2);admitted[field].flat[0]=value
    with self.assertRaisesRegex(ValueError,'FINITE_COMPLETE_ORIGINAL_PROJECTION_REQUIRED|EXACT_SAVED2023_ORIGINAL_TARGET_COVARIANCE_REQUIRED'):self.construct(admitted)
  self.assertEqual(B.sha(B.FINITE/'SOURCE_FREEZE.json'),B.FINITE_SHA);self.assertEqual(B.sha(B.FINITE/'CONTROL_SOURCE_FREEZE.json'),B.CONTROL_SHA)
  old=B.ROOT/'finite_original2023_bridge_author_review_20261014/rejected_c209_full_container_admission'
  self.assertEqual(B.sha(old/'PREPARATION_MANIFEST.json'),'c209bab0cc76cfc265be8fb61d45fbc1246c139c4b10470e4bfbc25a00b3b5ed')
  for name in ('driver.py','export_evidence.py','bridge_bindings.py','original200_quality.py','EXECUTED_SOURCE_CLOSURE.json'):
   self.assertEqual(B.sha(B.HERE/name),B.sha(old/name))
