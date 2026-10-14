"""Explicit original-source constructor; no generated-scope relabeling.

Financial execution, owner methods, clocks and H090 arithmetic are inherited
unchanged. This seam only admits an already verified original projection.
"""
from finite_tail_read import FiniteTailRead
from copy import deepcopy
from decimal import Decimal as D
from types import MappingProxyType
import hashlib,json
import numpy as np
import bridge_bindings as B
from native_control import H090NativeControl,DESCRIPTOR,POLICY,S,NATIVE,h090_factory
from finite_candidate import FiniteNativeCandidate
from finite_preview_callers import PrefixFiniteNativeCandidate
from calendar_readiness_v2 import SourcePacket,SourceReadinessError
from preview_callers import PrefixH090NativeControl,PrefixCapitalGuard
from preview_prefix import install_preview_histories

def raw_sha(a):return hashlib.sha256(a.tobytes()).hexdigest()

class OriginalProjectionRegistry:
 __slots__=('_sealed','generated','window_binding','decisions','original','covariance','clock','prices','ids','packets','approvals','source_index','scope','quality_identity','original_rows','covariance_bytes','_validated_state')
 def __setattr__(self,name,value):
  if getattr(self,'_sealed',False):raise TypeError('IMMUTABLE_ORIGINAL_PROJECTION_REGISTRY')
  object.__setattr__(self,name,value)
 def __init__(self,admitted,*,generated=False,case_args=None):
  object.__setattr__(self,'_sealed',False)
  if type(generated) is not bool:raise ValueError('EXPLICIT_SOURCE_SCOPE_REQUIRED')
  self.generated=generated
  if not generated:
   quality=B.require_original200_source_quality()
   B.case_gate(case_args)
   from verified_source import require_runtime
   runtime=require_runtime()
   if runtime.mode!='source_case' or not getattr(runtime,'bounded_worker_admitted',False):
    raise ValueError('BOUNDED_ORIGINAL_SOURCE_CONSTRUCTOR_REQUIRED')
  else:
   from verified_source import require_runtime
   if require_runtime().mode!='generated':raise ValueError('GENERATED_REGISTRY_ONLY_IN_GENERATED_TEST_RUNTIME')
  window=admitted['window']
  self.window_binding=(window['start'],window['end'],tuple(window['symbols']),window.get('fixture_scope'),id(window.get('market')),id(window.get('minute_blocks')))
  self.decisions=np.asarray(admitted['decision_us'])
  self.original=np.asarray(admitted['weights']);self.covariance=np.asarray(admitted['covariance'])
  self.clock=np.asarray(admitted['clock']);self.prices=np.asarray(admitted['prices'])
  self.ids=np.asarray(admitted['source_ids']);self.packets={};self.approvals={}
  n=len(self.decisions)
  if (self.decisions.dtype!=np.dtype('int64') or self.original.dtype!=np.dtype('float64')
      or self.original.shape!=(n,5) or self.covariance.shape!=(n,5,5)
      or self.covariance.dtype!=np.dtype('float64') or self.clock.dtype!=np.dtype('int64')
      or self.prices.dtype!=np.dtype('float64') or self.prices.shape!=(len(self.clock),5)
      or self.ids.dtype!=np.dtype('int64') or self.ids.shape!=(n,)
      or np.any(self.ids<0) or np.any(self.ids>=len(self.clock))
      or not np.array_equal(self.decisions,np.arange(window['start'],window['end'],B.DAY,dtype=np.int64))
      or tuple(window['symbols'])!=S or not np.array_equal(self.clock[self.ids],self.decisions)):
   raise ValueError('EXACT_ORIGINAL_PROJECTION_SHAPE_CLOCK_ORDER')
  if not generated:
   # The unchanged source loader copies the entire pinned cube container,
   # including unrelated unavailable prefixes/suffixes. Admit only the exact
   # reviewed original200 union, without filtering/filling any required row.
   first=int(self.ids[0])-199;last=int(self.ids[-1])+1
   required=np.arange(int(self.decisions[0])-199*B.DAY,int(self.decisions[-1])+B.DAY,B.DAY,dtype=np.int64)
   remapped=self.ids-first
   if (first<0 or last>len(self.clock) or len(required)!=564
       or not np.array_equal(self.clock[first:last],required)
       or not np.array_equal(remapped,np.arange(199,564,dtype=np.int64))):
    raise ValueError('EXACT_REVIEWED564_ORIGINAL200_SOURCE_VIEW_REQUIRED')
   self.clock=self.clock[first:last].copy();self.prices=self.prices[first:last].copy();self.ids=remapped.copy()
  if (not np.isfinite(self.original).all() or not np.isfinite(self.covariance).all()
      or not np.isfinite(self.prices).all() or np.any(self.prices<=0)
      or np.any(np.diff(self.clock)!=B.DAY) or np.any(self.clock<0)):
   raise ValueError('FINITE_COMPLETE_ORIGINAL_PROJECTION_REQUIRED')
  if generated:
   if window.get('fixture_scope')!='GENERATED_NATIVE_FINANCE_ONLY' or not 1<=n<=3:raise ValueError('BOUNDED_GENERATED_SOURCE_REQUIRED')
   self.source_index=hashlib.sha256(b'ORIGINAL_BRIDGE_GENERATED_TEST_INDEX').hexdigest()
   self.scope='GENERATED_BRIDGE_PARITY_ONLY'
  else:
   r=B.read(B.HERE/'SOURCE_RECEIPT_2023.json')
   if (window.get('fixture_scope') is not None or (window['start'],window['end'])!=B.CALENDAR or n!=365
       or raw_sha(self.original)!=r['target_raw_SHA256'] or raw_sha(self.covariance)!=r['covariance_raw_SHA256']
       or np.asarray(admitted['original_daily_admission']).dtype!=np.dtype('bool')
       or np.asarray(admitted['original_daily_admission']).shape!=(365,)
       or not np.asarray(admitted['original_daily_admission']).all()):raise ValueError('EXACT_SAVED2023_ORIGINAL_TARGET_COVARIANCE_REQUIRED')
   self.quality_identity=MappingProxyType(quality.validate_projection(self.decisions,self.clock,self.prices,self.ids))
   self.source_index=r['source_index_SHA256'];self.scope='ROOT_GO_SINGLE2023_PINNED_ORIGINAL_CLOSE_AVAILABLE_US'
  for i,t in enumerate(self.decisions):
   t=int(t);k=int(self.ids[i])
   if k<199 or not np.array_equal(self.clock[k-199:k+1],np.arange(t-199*B.DAY,t+B.DAY,B.DAY,dtype=np.int64)):
    raise ValueError('EXACT_COMPLETE200_ORIGINAL_AVAILABLE_CLOCKS_REQUIRED')
   packet=OriginalProjectionRegistry._build_packet(self,t,k,None if generated else quality)
   self.packets[t]=packet;self.approvals[t]=packet.approved_manifest_sha256
  self.packets=MappingProxyType(self.packets);self.approvals=MappingProxyType(self.approvals)
  self.original_rows=MappingProxyType({int(t):tuple(float(v) for v in row) for t,row in zip(self.decisions,self.original)})
  self.covariance_bytes=MappingProxyType({int(t):row.tobytes() for t,row in zip(self.decisions,self.covariance)})
  for a in (self.decisions,self.original,self.covariance,self.clock,self.prices,self.ids):a.flags.writeable=False
  self._validated_state=OriginalProjectionRegistry._state_digest(self)
  object.__setattr__(self,'_sealed',True)
 def _build_packet(self,t,k,quality):
  rows=[]
  for j in range(k-199,k+1):
   end=int(self.clock[j])
   for col,s in enumerate(S):
    if self.generated:
     rows.append(dict(symbol=s,open_us=end-B.DAY,close_us=end,available_us=end,close=float(self.prices[j,col]),
      complete=True,imputed=False,actual_source=True,record_locator=f'original_cube/close_available_us/{end}/{s}'))
    else:rows.append(quality.packet_row(end,s,self.prices[j,col]))
  document=dict(symbol_order=list(S),daily_bars=rows,source_scope=self.scope,
   clock_provenance='PINNED_ORIGINAL_CLOSE_AVAILABLE_US_NOT_NEW_PROVIDER_ARRIVAL_CERTIFICATION')
  source=json.dumps(document,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
  manifest=dict(schema='H090_REVIEWED_SOURCE_BAR_BINDING_V2',status='PINNED_ACTUAL_COMPLETE_SOURCE_BARS',
   source_blob_SHA256=hashlib.sha256(source).hexdigest(),source_index_SHA256=self.source_index,
   symbol_order=list(S),signal_interval_minutes=1440,source_scope=self.scope,
   saved_source_receipt_SHA256=B.SOURCE_SHA if not self.generated else None)
  if not self.generated:manifest['original200_source_quality']=dict(self.quality_identity)
  body=json.dumps(manifest,sort_keys=True,separators=(',',':')).encode();digest=hashlib.sha256(body).hexdigest()
  return SourcePacket(source,body,digest)

 def _state_digest(self):
  h=hashlib.sha256()
  for a in (self.decisions,self.original,self.covariance,self.clock,self.prices,self.ids):
   h.update(str(a.dtype).encode());h.update(str(a.shape).encode());h.update(a.tobytes())
  for t in self.decisions:
   t=int(t);packet=self.packets[t]
   h.update(str(t).encode());h.update(packet.source_bytes);h.update(packet.manifest_bytes);h.update(self.approvals[t].encode())
   h.update(np.asarray(self.original_rows[t],dtype=np.float64).tobytes());h.update(self.covariance_bytes[t])
  h.update(json.dumps(dict(self.quality_identity) if not self.generated else None,sort_keys=True).encode())
  h.update(str((self.generated,self.scope,self.source_index,self.window_binding)).encode())
  return h.hexdigest()

 def validate_original_admission(self):
  # Direct constructors must not trust a registry merely because its type matches.
  # Recheck the exact proof, every warmup price and deterministic packet mapping.
  if getattr(self,'generated',None) is not False or getattr(self,'_sealed',False) is not True:
   raise ValueError('SEALED_REVIEWED_ORIGINAL_REGISTRY_REQUIRED')
  try:
   quality=B.require_original200_source_quality();r=B.read(B.HERE/'SOURCE_RECEIPT_2023.json')
   if (self.clock.shape!=(564,) or self.prices.shape!=(564,5)
       or not np.array_equal(self.clock,np.arange(self.decisions[0]-199*B.DAY,self.decisions[-1]+B.DAY,B.DAY,dtype=np.int64))
       or not np.array_equal(self.ids,np.arange(199,564,dtype=np.int64))):
    raise ValueError('EXACT_REVIEWED564_ORIGINAL200_SOURCE_VIEW_REQUIRED')
   identity=quality.validate_projection(self.decisions,self.clock,self.prices,self.ids)
   expected_scope='ROOT_GO_SINGLE2023_PINNED_ORIGINAL_CLOSE_AVAILABLE_US'
   if (self.scope!=expected_scope or self.source_index!=r['source_index_SHA256']
       or dict(self.quality_identity)!=identity or type(self.quality_identity) is not MappingProxyType
       or self.original.dtype!=np.dtype('float64') or self.original.shape!=(365,5)
       or self.covariance.dtype!=np.dtype('float64') or self.covariance.shape!=(365,5,5)
       or raw_sha(self.original)!=r['target_raw_SHA256'] or raw_sha(self.covariance)!=r['covariance_raw_SHA256']
       or any(a.flags.writeable for a in (self.decisions,self.original,self.covariance,self.clock,self.prices,self.ids))):
    raise ValueError('EXACT_SEALED_ORIGINAL_PROJECTION_BINDING_REQUIRED')
   times={int(t) for t in self.decisions}
   for mapping in (self.packets,self.approvals,self.original_rows,self.covariance_bytes):
    if type(mapping) is not MappingProxyType or set(mapping)!=times:raise ValueError('EXACT_SEALED_ORIGINAL_PACKET_MAP_REQUIRED')
   for i,t in enumerate(self.decisions):
    t=int(t);packet=OriginalProjectionRegistry._build_packet(self,t,int(self.ids[i]),quality)
    if (type(self.packets[t]) is not SourcePacket or self.packets[t]!=packet or self.approvals[t]!=packet.approved_manifest_sha256
        or type(self.original_rows[t]) is not tuple or np.asarray(self.original_rows[t],dtype=np.float64).tobytes()!=self.original[i].tobytes()
        or type(self.covariance_bytes[t]) is not bytes or self.covariance_bytes[t]!=self.covariance[i].tobytes()):
     raise ValueError('EXACT_RECONSTRUCTED_ORIGINAL_PACKET_TARGET_COVARIANCE_REQUIRED')
   if OriginalProjectionRegistry._state_digest(self)!=self._validated_state:raise ValueError('ORIGINAL_REGISTRY_VALIDATED_STATE_CHANGED')
  except (AttributeError,KeyError,TypeError,IndexError) as error:
   raise ValueError('COMPLETE_SEALED_ORIGINAL_REGISTRY_STATE_REQUIRED') from error
  return identity

 def check_window(self,window):
  identity=(window['start'],window['end'],tuple(window['symbols']),window.get('fixture_scope'),id(window.get('market')),id(window.get('minute_blocks')))
  if identity!=self.window_binding:raise ValueError('EXACT_ADMITTED_WINDOW_SOURCE_BACKEND_REQUIRED')
  rows=window['daily'].to_dicts() if hasattr(window['daily'],'to_dicts') else window['daily']
  pairs={(r['symbol'],int(r['close_us'])):float(r['close']) for r in rows}
  if len(pairs)!=len(rows):raise ValueError('EXACT_UNDUPLICATED_DAILY_INPUT_REQUIRED')
  expected=np.asarray([[pairs[(symbol,int(t))] for symbol in S] for t in self.decisions],dtype=np.float64)
  if expected.tobytes()!=self.prices[self.ids].tobytes():raise ValueError('EXACT_CURRENT_AVAILABLE_DAILY_SOURCE_PRICE_REQUIRED')

 def check(self,packet,t):
  if type(packet) is not SourcePacket or t not in self.approvals or packet!=self.packets[t] or packet.approved_manifest_sha256!=self.approvals[t]:
   raise SourceReadinessError('EXACT_RECEIPT_BOUND_ORIGINAL_SOURCE_PACKET_REQUIRED')
 def identity(self):
  return dict(scope=self.scope,source_receipt_SHA256=B.SOURCE_SHA if not self.generated else None,
   source_index_SHA256=self.source_index,target_raw_SHA256=raw_sha(self.original),covariance_raw_SHA256=raw_sha(self.covariance),
   original200_source_quality=None if self.generated else dict(self.quality_identity))

class OriginalH090Control(H090NativeControl):
 VERSION='h090_original2023_one_case_bridge_v1'
 def __init__(self,window,registry,*,case_args=None):
  if type(registry) is not OriginalProjectionRegistry:raise ValueError('EXACT_ORIGINAL_REGISTRY_REQUIRED')
  if getattr(registry,'generated',None) is not True:
   B.require_original200_source_quality();OriginalProjectionRegistry.validate_original_admission(registry)
  OriginalProjectionRegistry.check_window(registry,window)
  from verified_source import require_runtime
  runtime=require_runtime()
  if registry.generated:
   if runtime.mode!='generated' or window.get('fixture_scope')!='GENERATED_NATIVE_FINANCE_ONLY':raise ValueError('GENERATED_REGISTRY_CANNOT_ADMIT_HISTORY')
  else:
   B.case_gate(case_args)
   if runtime.mode!='source_case' or not getattr(runtime,'bounded_worker_admitted',False):raise ValueError('BOUNDED_ORIGINAL_SOURCE_CONSTRUCTOR_REQUIRED')
  self.descriptor=DESCRIPTOR;self.source_registry=registry;self.source_packets=dict(registry.packets)
  self.original_weights={int(t):dict(zip(S,w.tolist(),strict=True)) for t,w in zip(registry.decisions,registry.original)}
  self.risk_contexts={};self.policy_events=[];self.reservations=POLICY.ReservationBook()
  self.reservations.reserve('CSH_H090_CONTROL',D('9000'));self.processed_native_receipts={}
  # Explicit constructor seam replaces only the generated fixture admission.
  # Native account/scheduler constructor and every finance method are exact.
  BASE27={'id':'BASE27','half_spread_bps':4,'slippage_bps':4,'roundtrip_bps':27}
  UNIT={'id':'RAW_AS_FRACTION','scale':1.0}
  NATIVE.__init__(self,window,'LONG_SHORT',BASE27,UNIT,target_factory=None,account_factory=h090_factory(BASE27),
   persist_cash_close=False,final_day_target_zero=False)
  self.account.risk_admission=self._atomic_risk_admission
  if tuple(self.symbols)!=S:raise ValueError('EXACT_CORE5_NATIVE_ORDER_REQUIRED')
  self.meta.update(source=registry.scope,original_target_field='STATIC50_UNLAGGED',rank_feature_lag_hours=0)
 def _prepare(self,t,original,packet):
  if (t not in self.source_registry.original_rows or not isinstance(original,dict) or set(original)!=set(S)
      or np.asarray([original[s] for s in S],dtype=np.float64).tobytes()!=np.asarray(self.source_registry.original_rows[t],dtype=np.float64).tobytes()):
   raise ValueError('EXACT_RECEIPT_BOUND_ORIGINAL_TARGET_ROW_REQUIRED')
  result=H090NativeControl._prepare(self,t,original,packet)
  if result['ready'] and result['covariance'].tobytes()!=self.source_registry.covariance_bytes[t]:
   raise ValueError('H090_COV365_BIT_MISMATCH_WITH_SAVED_ORIGINAL_PROJECTION')
  return result

class OriginalPrefixH090Control(OriginalH090Control):
 # VERSION/meta stay exact for full scheduler/account scientific parity.
 # Descendant performance provenance lives in BRIDGE_SCOPE and the freeze.
 _atomic_risk_admission=PrefixH090NativeControl._atomic_risk_admission
 def __init__(self,window,registry,*,case_args=None):
  # Keep every original source/proof/root gate and native constructor first.
  super().__init__(window,registry,case_args=case_args)
  # The installer refuses all non-fresh accounts; there is no migration.
  install_preview_histories(self.account.engine)
  self.account.capital_guard=PrefixCapitalGuard(self.account.engine)
  self.account.risk_admission=self._atomic_risk_admission

class OriginalFiniteCandidate(FiniteNativeCandidate,OriginalH090Control):
 VERSION='h090_finite_original2023_one_case_bridge_v1'

class OriginalPrefixFiniteCandidate(OriginalFiniteCandidate):
 # The complete original finite constructor owns source gates and economics.
 # VERSION, meta, owner facade and all ordinary owner copies stay unchanged.
 _flush_account=FiniteTailRead._flush_account
 _atomic_owner_admission=PrefixFiniteNativeCandidate._atomic_owner_admission
 def __init__(self,window,registry,*,case_args=None):
  super().__init__(window,registry,case_args=case_args)
  install_preview_histories(self.account.engine)
  self.account.capital_guard=PrefixCapitalGuard(self.account.engine)
  self.account.risk_admission=self._atomic_owner_admission

def make_sim(admitted,arm,*,generated=False,case_args=None):
 if arm not in B.ARMS:raise ValueError('EXACT_CONTROL_OR_FINITE_ARM_REQUIRED')
 if not generated:
  B.require_original200_source_quality()
  B.case_gate(case_args)
 registry=OriginalProjectionRegistry(admitted,generated=generated,case_args=case_args)
 from native_control import PORT
 window=dict(admitted['window'])
 if not isinstance(window['daily'],PORT.native.pl.DataFrame):window['daily']=PORT.native.pl.DataFrame(window['daily'])
 cls=OriginalPrefixH090Control if arm=='CONTROL' else OriginalPrefixFiniteCandidate
 sim=cls(window,registry,case_args=case_args)
 sim.bridge_arm=arm;sim.bridge_source_scope=registry.scope
 return sim
