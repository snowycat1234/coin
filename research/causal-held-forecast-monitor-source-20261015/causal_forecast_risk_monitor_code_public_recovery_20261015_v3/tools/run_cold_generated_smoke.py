"""Bounded cold generated32 only. Never load the source-entry actual-data suite."""
from pathlib import Path
import argparse,hashlib,json,os,sys,time,unittest
from functools import wraps
p=argparse.ArgumentParser();p.add_argument('--receipt',required=True);p.add_argument('--cpus',nargs=2,type=int);a=p.parse_args()
ROOT=Path(__file__).resolve().parent.parent;EXP=ROOT/'bounded_native_continuation_guard50_exit_expansion_20261015'
OUT=Path(a.receipt).resolve();initial=sorted(os.sched_getaffinity(0));CPUS=a.cpus or initial[:2]
if len(CPUS)!=2 or len(set(CPUS))!=2 or any(c not in initial for c in CPUS):raise SystemExit('Two distinct actually allowed CPUs are required for full generated32 coverage.')
for key in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS','POLARS_MAX_THREADS','VECLIB_MAXIMUM_THREADS'):os.environ[key]='1'
os.environ['PYTHONDONTWRITEBYTECODE']='1';sys.dont_write_bytecode=True
os.sched_setaffinity(0,{CPUS[0]});DENIED=[];CONSTRUCTIONS=[];START=time.monotonic();PHASE='IMPORT';project_paths=set()
def blocked(label):
 DENIED.append(label);raise RuntimeError('GENERATED_ONLY_SCOPE_FORBIDDEN:'+label)
def audit(event,args):
 if event in ('socket.connect','socket.connect_ex','socket.getaddrinfo','os.system','os.posix_spawn'):blocked(event)
 if event=='subprocess.Popen' and PHASE=='IMPORT':blocked('IMPORT_PROCESS_SIDE_EFFECT')
 if event=='open' and args and isinstance(args[0],(str,bytes,os.PathLike)):
  path=Path(os.fsdecode(args[0]))
  forbidden=('native_2023_source_restore_20261015','native_2024_source_restore_20261015')
  if any(x in forbidden or x.startswith('actual_') for x in path.parts):blocked('ACTUAL_SOURCE_OR_OUTPUT_READ')
  if path.is_absolute() and 'workspace' in path.parts:
   resolved=path.resolve()
   if not (resolved.is_relative_to(ROOT) or resolved.is_relative_to(Path(sys.prefix).resolve()) or resolved==OUT):blocked('OUTSIDE_EXTRACTION_PROJECT_IO')
sys.addaudithook(audit)
sys.path[:0]=[str(EXP),str(ROOT/'traditional_three_tier_freeze_20261015')]
import expansion as e
import expansion_entry as entry
import run_expansion as runner

def forbid(label):
 def gate(*args,**kwargs):blocked(label)
 return gate
for cls,label in ((e.ExpansionAccount,'ExpansionAccount'),(e.D.Guard50ExitAccount,'D.Guard50ExitAccount'),(e.V2.ContinuationAccount,'V2.ContinuationAccount'),(e.V2.P.BoundedContinuationAccount,'primitive.BoundedContinuationAccount')):
 original=cls.__init__
 def wrap(original,label):
  @wraps(original)
  def guarded(self,*args,**kw):
   if kw.get('historical_scope') is not None or kw.get('generated_scope')!=e.GENERATED:blocked('HISTORICAL_CONSTRUCTION:'+label)
   result=original(self,*args,**kw);CONSTRUCTIONS.append(label);return result
  return guarded
 cls.__init__=wrap(original,label)
for name in ('prepare_source_only','validate_preparation','preserved_evidence_identity','make_case'):
 if hasattr(entry,name):setattr(entry,name,forbid('historical_entry.'+name))
# Keep runner.case callable for its generated missing-claim negative gate. It is
# patched before any account call; source/current/evidence reads remain blocked.
setattr(runner,'validate_scope',forbid('historical_runner.validate_scope'))
_original_controller=runner.controller
def existing_output_probe_only(args):
 if Path(args.output).exists():return _original_controller(args)
 blocked('historical_runner.controller')
runner.controller=existing_output_probe_only
loader=unittest.TestLoader();suite=unittest.TestSuite()
for name in ('test_expansion','test_saved_native_reconciliation','test_matrix_runner'):suite.addTests(loader.loadTestsFromName(name))
if suite.countTestCases()!=32:raise SystemExit('EXPECTED_EXACT_GENERATED32')
def flatten(suite):
 for item in suite:
  if isinstance(item,unittest.TestSuite):yield from flatten(item)
  else:yield item
cases=list(flatten(suite));PHASE='GENERATED_TESTS'
CONCURRENT=('test_distinct_allowed_cpu_validation_and_serial_preflight','test_generated_concurrent_native_calendars_and_observed_thread_affinity','test_pressure_serial_fallback_before_launch','test_pressure_drop_between_first_and_second_launch_is_honored')
class AffinitySuite(unittest.TestSuite):
 def run(self,result,debug=False):
  for test in self:
   os.sched_setaffinity(0,set(CPUS) if test._testMethodName in CONCURRENT else {CPUS[0]})
   test(result)
  os.sched_setaffinity(0,{CPUS[0]});return result
result=unittest.TextTestRunner(verbosity=2).run(AffinitySuite(cases))
imports={};mismatch=[];manifest_path=ROOT/'FILES.json';manifest=json.loads(manifest_path.read_bytes()) if manifest_path.exists() else None
for name,module in tuple(sys.modules.items()):
 f=getattr(module,'__file__',None)
 if f:
  path=Path(f).resolve()
  if path.is_relative_to(ROOT):
   rel=str(path.relative_to(ROOT));digest=hashlib.sha256(path.read_bytes()).hexdigest();imports[name]={'path':rel,'SHA256':digest}
   if manifest is not None and (rel not in manifest['files'] or digest!=manifest['files'][rel]['SHA256']):mismatch.append(rel)
status='PASS_GENERATED32_ONLY' if result.wasSuccessful() and result.testsRun==32 and not result.skipped and not DENIED and not mismatch else 'BLOCKER'
receipt={'schema':'FROZEN_EXPANSION_COLD_GENERATED32_RECEIPT_V1','status':status,'tests_run':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),'skipped':len(result.skipped),'suite_counts':{'core':9,'checker':6,'runner':17},'source_entry15_run':False,'elapsed_seconds':time.monotonic()-START,'main_CPU':CPUS[0],'generated_concurrency_CPUs':CPUS,'numerical_compute_pool_threads':1,'blocked_events':DENIED,'project_import_mismatches':mismatch,'project_imports':imports,'generated_constructor_returns':len(CONSTRUCTIONS),'historical_accounts_constructed':0,'historical_minutes_advanced':0,'actual_financial_outputs_accessed':0,'approved_GO_bodies_accessed':0,'network_calls':0,'publication_actions':0,'full_historical_recovery_claimed':False,'safety':'Audit blocks actual source/output directories, external project IO, network and process creation during import; historical account constructors and source/current/evidence entries are gated. Runner subprocesses execute generated fixture tests only.'}
OUT.parent.mkdir(parents=True,exist_ok=True)
with OUT.open('x') as stream:json.dump(receipt,stream,indent=2,sort_keys=True);stream.write('\n')
print(json.dumps({key:receipt[key] for key in ('status','tests_run','failures','errors','skipped','elapsed_seconds','blocked_events')},sort_keys=True))
raise SystemExit(0 if status=='PASS_GENERATED32_ONLY' else 1)
