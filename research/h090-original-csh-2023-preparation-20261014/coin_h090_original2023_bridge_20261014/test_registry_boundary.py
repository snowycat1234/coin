"""Exact direct-constructor AST under explicit authorization/account stubs.

Prices are read from the already reviewed proof output. Targets/covariance and
GO/runtime metadata are mocked for boundary coverage only. The native account
constructor is replaced in the extracted AST globals by a sentinel stub; no
source input, native account or financial method runs.
"""
from pathlib import Path
from types import MappingProxyType,SimpleNamespace
from unittest import TestCase,mock
import ast,hashlib,json
import numpy as np
import original_bridge as O
import original200_quality as Q
import bridge_bindings as B

class BoundaryReached(Exception):pass
class ReservationStub:
 def reserve(self,*args):pass

class RegistryBoundary(TestCase):
 @classmethod
 def setUpClass(cls):
  cls.quality=Q.load_original200_proof();cls.source=B.read(B.HERE/'SOURCE_RECEIPT_2023.json')
  cls.window=dict(start=B.CALENDAR[0],end=B.CALENDAR[1],symbols=list(Q.SYMBOLS),market=object(),minute_blocks=object(),daily=[])
  registry=O.OriginalProjectionRegistry.__new__(O.OriginalProjectionRegistry)
  fields=dict(generated=False,decisions=np.arange(*Q.CALENDAR,Q.DAY,dtype=np.int64),clock=np.arange(Q.START,Q.END+Q.DAY,Q.DAY,dtype=np.int64),
   original=np.zeros((365,5),dtype=np.float64),covariance=np.zeros((365,5,5),dtype=np.float64),scope='ROOT_GO_SINGLE2023_PINNED_ORIGINAL_CLOSE_AVAILABLE_US',
   source_index=cls.source['source_index_SHA256'],quality_identity=MappingProxyType(cls.quality.identity()))
  fields['prices']=np.asarray([[cls.quality.packet_row(int(t),s,__import__('struct').unpack('<d',bytes.fromhex(cls.quality._rows[(int(t),s)]['close_float64_hex']))[0])['close'] for s in Q.SYMBOLS] for t in fields['clock']],dtype=np.float64)
  fields['ids']=np.searchsorted(fields['clock'],fields['decisions'])
  fields['window_binding']=(cls.window['start'],cls.window['end'],tuple(cls.window['symbols']),None,id(cls.window['market']),id(cls.window['minute_blocks']))
  for key,value in fields.items():object.__setattr__(registry,key,value)
  cls.window['daily']=[dict(symbol=s,close_us=int(t),close=float(registry.prices[k,col])) for t,k in zip(registry.decisions,registry.ids) for col,s in enumerate(Q.SYMBOLS)]
  packets={int(t):registry._build_packet(int(t),int(k),cls.quality) for t,k in zip(registry.decisions,registry.ids)}
  for key,value in dict(packets=MappingProxyType(packets),approvals=MappingProxyType({t:p.approved_manifest_sha256 for t,p in packets.items()}),
   original_rows=MappingProxyType({int(t):tuple(row) for t,row in zip(registry.decisions,registry.original)}),covariance_bytes=MappingProxyType({int(t):row.tobytes() for t,row in zip(registry.decisions,registry.covariance)})).items():object.__setattr__(registry,key,value)
  for array in (registry.decisions,registry.clock,registry.prices,registry.ids,registry.original,registry.covariance):array.flags.writeable=False
  object.__setattr__(registry,'_validated_state',registry._state_digest());object.__setattr__(registry,'_sealed',True);cls.base=registry
  cls.fixture_receipt={**cls.source,'target_raw_SHA256':O.raw_sha(registry.original),'covariance_raw_SHA256':O.raw_sha(registry.covariance)}
  tree=ast.parse((B.HERE/'original_bridge.py').read_bytes());klass=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='OriginalH090Control')
  constructor=next(n for n in klass.body if isinstance(n,ast.FunctionDef) and n.name=='__init__');constructor.name='exact_constructor_probe'
  module=ast.fix_missing_locations(ast.Module(body=[constructor],type_ignores=[]));cls.constructor_ast_SHA256=hashlib.sha256(ast.dump(constructor,include_attributes=False).encode()).hexdigest()
  cls.namespace=dict(O.__dict__);cls.calls=[]
  def boundary(*args,**kwargs):cls.calls.append('NATIVE_CONSTRUCTOR_STUB_ONLY');raise BoundaryReached()
  cls.namespace.update(NATIVE=SimpleNamespace(__init__=boundary),h090_factory=lambda cost:None,POLICY=SimpleNamespace(ReservationBook=ReservationStub),B=SimpleNamespace(require_original200_source_quality=Q.load_original200_proof,case_gate=lambda args:None))
  exec(compile(module,'EXACT_CONSTRUCTOR_AST_NO_FINANCE','exec'),cls.namespace)
 @classmethod
 def clone(cls):
  registry=O.OriginalProjectionRegistry.__new__(O.OriginalProjectionRegistry)
  for key in O.OriginalProjectionRegistry.__slots__:
   value=getattr(cls.base,key)
   if isinstance(value,np.ndarray):value=value.copy();value.flags.writeable=False
   object.__setattr__(registry,key,value)
  return registry
 def probe(self,registry):
  import verified_source
  # The fake receipt is explicitly a test fixture, not actual source admission.
  with mock.patch.object(B,'read',return_value=self.fixture_receipt),mock.patch.object(verified_source,'require_runtime',return_value=SimpleNamespace(mode='source_case',bounded_worker_admitted=True)):
   return self.namespace['exact_constructor_probe'](SimpleNamespace(),self.window,registry,case_args=SimpleNamespace())
 def test_valid_mocked_boundary_reaches_only_stub_account(self):
  before=len(self.calls)
  with self.assertRaises(BoundaryReached):self.probe(self.clone())
  self.assertEqual(len(self.calls),before+1)
 def test_registry_assignment_and_mutated_warmup_refused_before_account(self):
  registry=self.clone()
  with self.assertRaisesRegex(TypeError,'IMMUTABLE_ORIGINAL_PROJECTION_REGISTRY'):registry.scope='changed'
  registry.prices.flags.writeable=True;registry.prices[0,0]=np.nextafter(registry.prices[0,0],np.inf);registry.prices.flags.writeable=False
  object.__setattr__(registry,'_validated_state',registry._state_digest())
  before=len(self.calls)
  with self.assertRaisesRegex(ValueError,'PROOF_BIT_MISMATCH'):self.probe(registry)
  self.assertEqual(len(self.calls),before)
 def test_new_missing_packets_approval_target_covariance_mutations_refused(self):
  before=len(self.calls)
  for name in ('validate_original_admission','check_window','_build_packet','_state_digest'):
   registry=self.clone()
   with self.assertRaises(AttributeError):object.__setattr__(registry,name,lambda *args:None)
   with self.assertRaises(AttributeError):getattr(registry,'__dict__')
  missing=O.OriginalProjectionRegistry.__new__(O.OriginalProjectionRegistry)
  with self.assertRaisesRegex(ValueError,'SEALED_REVIEWED_ORIGINAL_REGISTRY'):self.probe(missing)
  t=int(self.base.decisions[0]);packet=self.base.packets[t]
  forged=type(packet)(packet.source_bytes+b' ',packet.manifest_bytes,packet.approved_manifest_sha256)
  for field,value in [('packets',MappingProxyType({**dict(self.base.packets),t:forged})),('approvals',MappingProxyType({**dict(self.base.approvals),t:'f'*64})),
    ('original_rows',MappingProxyType({**dict(self.base.original_rows),t:(1.,0.,0.,0.,0.)})),('covariance_bytes',MappingProxyType({**dict(self.base.covariance_bytes),t:b'wrong'}))]:
   registry=self.clone();object.__setattr__(registry,field,value)
   with self.assertRaisesRegex(ValueError,'EXACT_RECONSTRUCTED_ORIGINAL_PACKET_TARGET_COVARIANCE'):self.probe(registry)
  for field in ('original','covariance'):
   registry=self.clone();array=getattr(registry,field);array.flags.writeable=True;array.flat[0]=1.;array.flags.writeable=False
   with self.assertRaisesRegex(ValueError,'EXACT_SEALED_ORIGINAL_PROJECTION'):self.probe(registry)
  self.assertEqual(len(self.calls),before)
