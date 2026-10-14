"""One frozen generated original-bridge parity worker; no historical dispatch."""
import sys
if not (sys.flags.isolated and sys.flags.no_site and sys.flags.dont_write_bytecode and sys.flags.optimize==0):
 raise RuntimeError('ISOLATED_NO_SITE_NO_BYTECODE_ASSERTIONS_ENABLED_LAUNCH_REQUIRED')
from pathlib import Path
import ast,cProfile,gzip,hashlib,importlib.machinery,json,os,resource,time,traceback,types
from unittest import mock
BASE=Path(__file__).resolve().parent;ROOT=BASE.parent;OUT=BASE/'generated_original_parity_attempt002'
PIN=sys.argv[1];BEGAN=time.monotonic();NPZ_OPENS=[];PARSER_CALLS=[];CASES=[]
KNOWN_NPZ={(ROOT/'coin_h090_finite_native_20261014/dependencies/repo/research/static50-sma-20261013/input'/n).resolve() for n in ('Y2023.npz','Y2025.npz')}
def digest(data):return hashlib.sha256(data).hexdigest()
def canonical(value):return json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
def save(name,value,compressed=False):
 raw=canonical(value)+b'\n';raw=gzip.compress(raw,mtime=0) if compressed else raw
 with (OUT/name).open('xb') as stream:stream.write(raw)
 return dict(file=name,SHA256=digest(raw),bytes=len(raw))
def exact(left,right,label):
 if left!=right or canonical(left)!=canonical(right):
  save('MISMATCH_'+label+'.json.gz',dict(label=label,baseline=left,descendant=right),True)
  raise AssertionError('EXACT_VALUES_OR_JSON_BYTES_MISMATCH:'+label)
def audit(event,args):
 if event in ('socket.connect','subprocess.Popen','os.system'):raise RuntimeError('GENERATED_PARITY_NO_NETWORK_OR_CHILDREN')
 if event!='open' or not isinstance(args[0],(str,bytes,os.PathLike)):return
 path=Path(os.fsdecode(args[0])).resolve()
 if path.suffix.lower() in ('.npz','.npy','.parquet','.csv') and not path.is_relative_to(OUT):
  if path not in KNOWN_NPZ:raise RuntimeError('EXTERNAL_ARRAY_OR_MARKET_READ_REFUSED:'+str(path))
  frame=sys._getframe(1);callers=[]
  while frame is not None and len(callers)<12:
   callers.append((Path(frame.f_code.co_filename).name,frame.f_code.co_name));frame=frame.f_back
  if not any(name in ('sha','file_sha','bytes') for _,name in callers):raise RuntimeError('PUBLIC_NPZ_CHECKSUM_ONLY_REQUIRED')
  NPZ_OPENS.append(dict(file=str(path.relative_to(ROOT)),caller_chain=callers))
sys.addaudithook(audit)
def bootstrap():
 raw=(BASE/'PREPARATION_MANIFEST.json').read_bytes();assert digest(raw)==PIN
 freeze=json.loads(raw)
 for name,want in freeze['files'].items():
  data=(BASE/name).read_bytes();assert digest(data)==want['SHA256'] and len(data)==want['bytes'],name
 assert digest((BASE/'ACCEPTED_ORIGINAL_PREPARATION_MANIFEST.json').read_bytes())=='263cc069a9cae93d3123f47d6218c9445fa17d0f808a0e4fb4186c5d9bba03f9'
 assert digest((BASE/'ACCEPTED_PERFORMANCE_SOURCE_FREEZE.json').read_bytes())=='42a58e1bbf2e83ef06aa8c44c265f9194f6eebc48bf2df584c4c18393142b075'
 old=json.loads((BASE/'ACCEPTED_ORIGINAL_PREPARATION_MANIFEST.json').read_text())
 assert digest((BASE/'accepted_original_bridge.py').read_bytes())==old['files']['original_bridge.py']['SHA256']
 path=BASE/'verified_source.py';module=types.ModuleType('verified_source');module.__file__=str(path)
 module.__spec__=importlib.machinery.ModuleSpec('verified_source',loader=None,origin=str(path));sys.modules['verified_source']=module
 assert digest(path.read_bytes())==old['files']['verified_source.py']['SHA256']
 exec(compile(path.read_bytes(),str(path),'exec'),module.__dict__);runtime=module.install(PIN,'generated')
 import bridge_runtime_locator
 runtime.runtime_packages=bridge_runtime_locator.configure_runtime()
 import original_bridge as O
 import accepted_original_bridge as A
 import preview_prefix as P
 import preview_callers as K
 import native_control as N
 import generated_fixtures as F
 import test_bridge as T
 import numpy as np
 return runtime,O,A,P,K,N,F,T,np
def class_nodes(path):
 tree=ast.parse(path.read_text());return {x.name:x for x in tree.body if isinstance(x,(ast.ClassDef,ast.FunctionDef))}
def source_segment(path,cls,method):
 lines=path.read_text().splitlines();node=class_nodes(path)[cls]
 function=next(x for x in node.body if isinstance(x,ast.FunctionDef) and x.name==method)
 return '\n'.join(lines[function.lineno-1:function.end_lineno])
def identity_checks(runtime,O,A,P,K,N,F,T,np):
 accepted=class_nodes(BASE/'accepted_original_bridge.py');actual=class_nodes(BASE/'original_bridge.py')
 for name,node in accepted.items():
  if name!='make_sim':assert ast.dump(node,include_attributes=False)==ast.dump(actual[name],include_attributes=False),name
 assert O.OriginalPrefixH090Control.__mro__==(O.OriginalPrefixH090Control,O.OriginalH090Control,N.H090NativeControl)+N.NATIVE.__mro__
 assert O.OriginalPrefixH090Control._prepare is O.OriginalH090Control._prepare
 assert O.OriginalPrefixH090Control._atomic_risk_admission is K.PrefixH090NativeControl._atomic_risk_admission
 assert O.OriginalPrefixH090Control.VERSION==O.OriginalH090Control.VERSION==A.OriginalH090Control.VERSION
 names=('_prepare','_admit_decision','advance_day','attempt','schedule','funding_through','observe','risk_schedule','snapshot','result')
 for name in names:assert getattr(O.OriginalPrefixH090Control,name) is getattr(O.OriginalH090Control,name),name
 assert O.OriginalFiniteCandidate.__mro__[1].__name__=='FiniteNativeCandidate'
 assert O.OriginalPrefixH090Control not in O.OriginalFiniteCandidate.__mro__
 closure=json.loads((BASE/'EXECUTED_SOURCE_CLOSURE.json').read_text())
 original_closure=(ROOT/'coin_h090_original2023_bridge_20261014/EXECUTED_SOURCE_CLOSURE.json').read_bytes()
 assert (BASE/'EXECUTED_SOURCE_CLOSURE.json').read_bytes()==original_closure
 methods=[]
 for row in json.loads((BASE/'ACCEPTED_PERFORMANCE_CALLER_SINGLE_CHANGE_DIFF.json').read_text()):
  cls,method=row['method'].split('.');path=ROOT/row['source'];old=source_segment(path,cls,method)
  assert digest(path.read_bytes())==row['source_SHA256']
  copied=source_segment(BASE/'preview_callers.py','Prefix'+cls,method)
  assert copied==old.replace(row['single_literal_replacement']['old'],row['single_literal_replacement']['new'])
  assert digest(old.encode())==row['original_method_SHA256'];methods.append(row)
 protected=('bridge_bindings.py','original200_quality.py','verified_source.py','driver.py','export_evidence.py','run_verified.py','ORIGINAL200_SOURCE_QUALITY_PROOF.json.gz','ORIGINAL200_SOURCE_QUALITY_REVIEW.json','SOURCE_RECEIPT_2023.json')
 pins=json.loads((BASE/'ACCEPTED_ORIGINAL_PREPARATION_MANIFEST.json').read_text())['files']
 for name in protected:assert digest((BASE/name).read_bytes())==pins[name]['SHA256']
 body=source_segment(BASE/'original_bridge.py','OriginalPrefixH090Control','__init__')
 assert body.index('super().__init__')<body.index('install_preview_histories')<body.index('PrefixCapitalGuard')<body.index('self.account.risk_admission')
 assert '__class__' not in (BASE/'original_bridge.py').read_text()
 checks=dict(status='PASS_STATIC_IDENTITY',MRO=[f'{c.__module__}.{c.__name__}' for c in O.OriginalPrefixH090Control.__mro__],prepare_exact_inherited_object=True,original_classes_AST_unchanged=True,VERSION_and_meta_unchanged=True,finite_branch_unchanged_and_not_optimized=True,source_closure_byte_identical=True,protected_original_file_hashes={name:pins[name]['SHA256'] for name in protected},two_exact_accepted_clone_points=methods,constructor_order='original gated constructor; fresh history installation; capital guard replacement; risk callback binding',no_class_replacement=True)
 save('MRO_AND_SOURCE_IDENTITIES.json',checks)
 return checks
def expect(function,pattern):
 try:function()
 except (TypeError,ValueError) as error:
  assert pattern in str(error),(pattern,str(error));return str(error)
 raise AssertionError('EXPECTED_SOURCE_ADMISSION_REFUSAL_ABSENT:'+pattern)
def unused_monitoring_tool(label):
 # Select an unused slot without displacing cProfile or any other owner.
 for tool in (4,3,0,1,5,2):
  if sys.monitoring.get_tool(tool) is None:
   sys.monitoring.use_tool_id(tool,label)
   return tool
 raise RuntimeError('NO_UNUSED_MONITORING_SLOT_FAIL_CLOSED')
def source_gates(O,A,P,K,N,F,T,np):
 data=T.admitted(F.make_generated(days=1,original_recipe=True),recipe=True)
 import bridge_bindings as B
 errors=[];native_starts=[];tool=unused_monitoring_tool('source_gate_account_order')
 code=N.NATIVE.__init__.__code__
 def entered(code,offset):native_starts.append('native_constructor')
 sys.monitoring.register_callback(tool,sys.monitoring.events.PY_START,entered)
 sys.monitoring.set_local_events(tool,code,sys.monitoring.events.PY_START)
 try:
  with mock.patch.object(B,'require_original200_source_quality',side_effect=ValueError('EXACT_ORIGINAL200_PROOF_FILE_REQUIRED')):
   errors.append(expect(lambda:O.make_sim({},'CONTROL'),'EXACT_ORIGINAL200_PROOF_FILE_REQUIRED'))
   forged=O.OriginalProjectionRegistry.__new__(O.OriginalProjectionRegistry);forged.generated=False
   errors.append(expect(lambda:O.OriginalPrefixH090Control({},forged),'EXACT_ORIGINAL200_PROOF_FILE_REQUIRED'))
  errors.append(expect(lambda:O.make_sim(data,'CONTROL'),'SEPARATE_ROOT_ONE_CASE_GO_REQUIRED'))
  registry=O.OriginalProjectionRegistry(data,generated=True)
  errors.append(expect(lambda:O.OriginalPrefixH090Control({**data['window'],'start':0},registry),'EXACT_ADMITTED_WINDOW'))
  errors.append(expect(lambda:O.OriginalPrefixH090Control(data['window'],object()),'EXACT_ORIGINAL_REGISTRY_REQUIRED'))
  wrong={**data['window'],'fixture_scope':None}
  errors.append(expect(lambda:O.make_sim({**data,'window':wrong},'CONTROL',generated=True),'BOUNDED_GENERATED_SOURCE'))
 finally:
  sys.monitoring.set_local_events(tool,code,0);sys.monitoring.free_tool_id(tool)
 assert native_starts==[],native_starts
 sim=O.make_sim(data,'CONTROL',generated=True);t=int(data['decision_us'][0]);before=sim.account.snapshot()
 original=dict(zip(F.S,data['weights'][0],strict=True));changed=dict(original);changed[F.S[0]]+=.001
 errors.append(expect(lambda:sim._prepare(t,changed,sim.source_packets[t]),'EXACT_RECEIPT_BOUND_ORIGINAL_TARGET_ROW'))
 exact(before,sim.account.snapshot(),'bad_target_account_nonmutation')
 prepared=sim._prepare(t,original,sim.source_packets[t]);assert prepared['ready']
 assert prepared['covariance'].tobytes()==data['covariance'][0].tobytes()
 altered=T.admitted(F.make_generated(days=1,original_recipe=True),recipe=True);altered['covariance'][0,0,0]+=1.
 wrong=O.make_sim(altered,'CONTROL',generated=True);before=wrong.account.snapshot()
 errors.append(expect(lambda:wrong._prepare(t,dict(zip(F.S,altered['weights'][0],strict=True)),wrong.source_packets[t]),'COV365_BIT_MISMATCH'))
 exact(before,wrong.account.snapshot(),'bad_covariance_account_nonmutation')
 for array in (registry.decisions,registry.original,registry.covariance,registry.clock,registry.prices,registry.ids):assert not array.flags.writeable
 assert all(type(getattr(registry,name)) is types.MappingProxyType for name in ('packets','approvals','original_rows','covariance_bytes'))
 record=dict(status='PASS_FOCUSED_SOURCE_ADMISSION',refusals=errors,proof_and_root_gates_before_native_account=True,wrong_window_and_registry_before_native_account=True,prepare_original_target_and_covariance_checks_preserved=True,generated_recipe_covariance_bytes_equal=True,immutable_matching_original_registry=True,source_cases_launched=0)
 save('SOURCE_GATE_CHECKS.json',record);return record
def build_pair(case,O,A,P,K,N,F,T,np):
 days=case['days'];clocks=[F.START+i*F.DAY for i in range(days)]
 events=[dict(event_us=t+m*F.MINUTE+1,symbol=s,raw_rate=.00001) for t in clocks for m in (1,2,4) for s in F.S]
 events.sort(key=lambda row:(row['event_us'],F.S.index(row['symbol'])))
 bundle=F.make_generated(days=days,weights=case.get('weights'),original_recipe=case['recipe'],quote=case['quote'],events=events)
 data=T.admitted(bundle,recipe=case['recipe'])
 baseline=A.make_sim(data,'CONTROL',generated=True)
 timeline=[];tool=unused_monitoring_tool('original_bridge_constructor_order')
 codes={O.OriginalPrefixH090Control.__init__.__code__:'prefix_constructor',O.OriginalH090Control.__init__.__code__:'original_gated_constructor',N.NATIVE.__init__.__code__:'native_constructor',P.install_preview_histories.__code__:'fresh_history_installer'}
 def start(code,offset):timeline.append(dict(event='start',method=codes[code]))
 def end(code,offset,result):timeline.append(dict(event='return',method=codes[code]))
 sys.monitoring.register_callback(tool,sys.monitoring.events.PY_START,start)
 sys.monitoring.register_callback(tool,sys.monitoring.events.PY_RETURN,end)
 for code in codes:sys.monitoring.set_local_events(tool,code,sys.monitoring.events.PY_START|sys.monitoring.events.PY_RETURN)
 try:descendant=O.make_sim(data,'CONTROL',generated=True)
 finally:
  for code in codes:sys.monitoring.set_local_events(tool,code,0)
  sys.monitoring.free_tool_id(tool)
 assert timeline==[dict(event=e,method=m) for e,m in [('start','prefix_constructor'),('start','original_gated_constructor'),('start','native_constructor'),('return','native_constructor'),('return','original_gated_constructor'),('start','fresh_history_installer'),('return','fresh_history_installer'),('return','prefix_constructor')]],timeline
 raw=descendant.account.engine;P.validate_engine(raw)
 assert raw.clock_us==0 and raw.last_fill_us is None and not any(raw.marks.values())
 assert not any(getattr(raw,name) for name in P.HISTORY_FIELDS) and descendant.rows_written==0 and descendant.cursor==F.START
 assert type(descendant.account.capital_guard) is K.PrefixCapitalGuard
 assert descendant.account.risk_admission.__self__ is descendant and descendant.account.risk_admission.__func__ is K.PrefixH090NativeControl._atomic_risk_admission
 exact(baseline.snapshot(),descendant.snapshot(),case['name']+'_fresh_full_snapshot')
 exact(baseline.source_registry.identity(),descendant.source_registry.identity(),case['name']+'_registry')
 assert baseline.source_registry._validated_state==descendant.source_registry._validated_state
 for t in data['decision_us']:
  t=int(t);assert baseline.source_packets[t]==descendant.source_packets[t]
 return baseline,descendant,timeline,data
def run_case(case,O,A,P,K,N,F,T,np):
 baseline,descendant,timeline,data=build_pair(case,O,A,P,K,N,F,T,np);outputs=[];measured=[]
 for label,sim in (('baseline',baseline),('descendant',descendant)):
  began=time.monotonic();cpu=time.process_time();daily=[]
  while sim.stop is None and sim.cursor<sim.end:daily.append(sim.advance_day())
  measured.append(dict(arm=label,wall_seconds=time.monotonic()-began,CPU_seconds=time.process_time()-cpu))
  assert sim.stop is None and sim.rows_written==case['days']*1440
  result=sim.result();matrix=result['minute'].to_numpy()
  assert matrix.dtype==np.dtype('float64') and matrix.shape==(case['days']*1440,37)
  np.save(OUT/(case['name']+'_'+label+'_minute37.npy'),matrix,allow_pickle=False)
  snapshot=sim.snapshot();account=sim.account.snapshot()
  events=dict(trades=list(sim.account.trades),account_funding=list(sim.account.funding),scheduler_funding=sim.funding_journal,rejections=sim.rejections,policy_events=sim.policy_events,targets=result['targets'].to_dicts(),target_rows=sim.target_rows,decision_kinds=sim.decision_kinds,pending={s:{**v,'target':str(v['target'])} for s,v in sim.pending.items()},funding_cursor=sim.event_cursor,extrema=sim.extrema,breaches=sim.breaches,day_receipts=daily,processed_native_receipts=sim.processed_native_receipts,summary=result['summary'])
  files=[save(case['name']+'_'+label+'_full_scheduler_snapshot.json.gz',snapshot,True),save(case['name']+'_'+label+'_full_account_snapshot.json.gz',account,True),save(case['name']+'_'+label+'_native_outputs.json.gz',events,True)]
  outputs.append((matrix,snapshot,account,events,files))
 bm,bs,ba,be,bf=outputs[0];pm,ps,pa,pe,pf=outputs[1]
 assert bm.tobytes()==pm.tobytes() and baseline.result()['minute'].columns==descendant.result()['minute'].columns
 exact(bs,ps,case['name']+'_full_scheduler');exact(ba,pa,case['name']+'_full_native_account');exact(be,pe,case['name']+'_all_native_outputs')
 assert [r['SHA256'] for r in bf]==[r['SHA256'] for r in pf]
 expiry=sum(row.get('reason')=='FIVE_ATTEMPTS_EXPIRED' for row in be['rejections'])
 if case['name']=='signed_partial_capacity':
  assert be['trades'] and expiry>0 and be['scheduler_funding'] and be['account_funding']
 if case['name']=='original_recipe_charged':assert be['trades'] and be['account_funding']
 if case['name']=='one_day_unfilled':assert not be['trades'] and expiry>0
 if case['recipe']:
  for i,t in enumerate(data['decision_us']):assert baseline.risk_contexts[int(t)]['covariance'].tobytes()==data['covariance'][i].tobytes()==descendant.risk_contexts[int(t)]['covariance'].tobytes()
 record=dict(case=case['name'],days=case['days'],minutes=case['days']*1440,matrix_shape=list(bm.shape),matrix_dtype=str(bm.dtype),minute_columns=baseline.result()['minute'].columns,minute_bytes_SHA256=digest(bm.tobytes()),full37_column_minute_bytes_equal=True,full_scheduler_and_native_account_snapshot_JSON_bytes_equal=True,native_receipts_targets_decisions_rejections_policy_pending_funding_cursor_extrema_equal=True,native_fill_legs=len(be['trades']),native_account_funding_events=len(be['account_funding']),scheduler_funding_events=len(be['scheduler_funding']),five_attempt_expiry_count=expiry,original_recipe_covariance_bit_identity=case['recipe'],fresh_pre_event_install_timeline=timeline,measured_time_only_no_speedup_claim=measured,full_outputs=bf+pf)
 CASES.append(record);save(case['name']+'_PARITY.json',record);print(json.dumps({k:v for k,v in record.items() if k not in ('full_outputs','minute_columns','fresh_pre_event_install_timeline')},sort_keys=True),flush=True)
def main():
 runtime,O,A,P,K,N,F,T,np=bootstrap();identities=identity_checks(runtime,O,A,P,K,N,F,T,np);gates=source_gates(O,A,P,K,N,F,T,np)
 cases=[dict(name='one_day_unfilled',days=1,recipe=False,weights=[.06,-.08,.08,0,0],quote=0.),dict(name='signed_partial_capacity',days=2,recipe=False,weights=[[.12,-.12,.12,-.12,.12],[-.12,.12,-.12,.12,-.12]],quote=50000.),dict(name='original_recipe_charged',days=3,recipe=True,quote=50000.)]
 for case in cases:run_case(case,O,A,P,K,N,F,T,np)
 distinct=sorted({row['file'] for row in NPZ_OPENS});assert len(distinct)==2 and sum((ROOT/path).stat().st_size for path in distinct)==50586
 return dict(schema='H090_ORIGINAL_PREFIX_BRIDGE_GENERATED_PARITY_V1',status='PASS',preparation_manifest_SHA256=PIN,static_identity_checks=identities,source_gate_checks=gates,cases=CASES,source_audit=runtime.audit(),runtime_packages=runtime.runtime_packages,NPZ_checksum_only_open_log=NPZ_OPENS,historical_arrays_parsed=0,historical_account_states_imported=0,historical_drivers_launched=0,known_public_checksum_only_NPZ_distinct_files=2,known_public_checksum_only_NPZ_distinct_bytes=50586,financial_source_methods_changed=False,economic_policy_changed=False,finite_performance_tested=False,automatic_retries=0,wall_seconds=time.monotonic()-BEGAN,CPU_seconds=time.process_time(),peak_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,CPU_affinity=sorted(os.sched_getaffinity(0)))
profile=cProfile.Profile()
try:
 profile.enable();result=main();profile.disable()
 import pstats
 stats=pstats.Stats(profile)
 for (filename,line,name),(primitive,total,own,cumulative,callers) in stats.stats.items():
  if name in ('load','loadtxt','genfromtxt','read_parquet') and any(x in filename for x in ('/numpy/','/polars/','/pyarrow/')):PARSER_CALLS.append(dict(file=filename,function=name,calls=total))
 assert not PARSER_CALLS;result['external_array_parser_calls']=PARSER_CALLS
 profile.dump_stats(str(OUT/'generated_original_bridge.pstats'));save('RESULT.json',result)
except BaseException as error:
 profile.disable();save('FAILURE.json',dict(status='FAILED_NO_RETRY',error=repr(error),traceback=traceback.format_exc(),completed_cases=CASES,NPZ_checksum_only_opens=NPZ_OPENS,automatic_retries=0));raise
