"""Detached generated73 smoke. Real-preparation positives are not cold tests."""
from pathlib import Path
import argparse,hashlib,json,os,sys,time,unittest
from functools import wraps
ap=argparse.ArgumentParser();ap.add_argument('--receipt',required=True);ap.add_argument('--cpu',type=int);args=ap.parse_args()
ROOT=Path(__file__).resolve().parent.parent;S=ROOT/'causal_forecast_risk_monitor_20261015';R=ROOT/'causal_forecast_risk_monitor_independent_review_20261015'
OUT=Path(args.receipt).resolve();allowed=sorted(os.sched_getaffinity(0));cpu=args.cpu if args.cpu is not None else allowed[0]
if cpu not in allowed:raise SystemExit('Requested CPU is not actually allowed.')
for key in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS','POLARS_MAX_THREADS','VECLIB_MAXIMUM_THREADS'):os.environ[key]='1'
os.environ['PYTHONDONTWRITEBYTECODE']='1';sys.dont_write_bytecode=True
os.sched_setaffinity(0,{cpu});os.chdir(ROOT)
TMP=ROOT/'cold_generated_temporary';TMP.mkdir(exist_ok=False);os.environ['TMPDIR']=str(TMP)
DENIED=[];CONSTRUCTIONS=[];START=time.monotonic();PHASE='IMPORT'
def blocked(label):DENIED.append(label);raise RuntimeError('CAUSAL_COLD_GENERATED_SCOPE_FORBIDDEN:'+label)
def audit(event,a):
 if event in ('socket.connect','socket.connect_ex','socket.getaddrinfo','os.system','os.posix_spawn','subprocess.Popen'):blocked(event)
 if event=='open' and a and isinstance(a[0],(str,bytes,os.PathLike)):
  p=Path(os.fsdecode(a[0]));parts=p.parts
  if any(x.startswith('actual_') or (x.startswith('native_') and '_source_restore_' in x) or x=='EXECUTION_CLAIMS' for x in parts):blocked('ACTUAL_DATA_EVIDENCE_OR_CLAIM_IO')
  if p.suffix in ('.npz','.npy'):blocked('MARKET_OR_TARGET_ARRAY_FILE_IO')
  if p.is_absolute() and 'workspace' in parts:
   q=p.resolve()
   if not(q.is_relative_to(ROOT) or q.is_relative_to(Path(sys.prefix).resolve()) or q==OUT):blocked('PROJECT_IO_OUTSIDE_NEW_EXTRACTION')
sys.addaudithook(audit)
sys.path[:0]=[str(S),str(R),str(ROOT/'traditional_three_tier_freeze_20261015')]
import forecast_monitor as f
import forecast_entry as entry
import forecast_historical as historical
import run_forecast as runner
# Keep exact invalid-scope constructor behavior. Any real historical route
# reaching inherited finance is blocked before genesis. Generated constructors
# and preview forks retain their original code except these outer test guards.
for cls,label in ((f.E.ExpansionAccount,'ExpansionAccount'),(f.E.D.Guard50ExitAccount,'Guard50ExitAccount'),(f.V2.ContinuationAccount,'ContinuationAccount'),(f.V2.P.BoundedContinuationAccount,'BoundedContinuationAccount')):
 original=cls.__init__
 def make_guard(original,label):
  @wraps(original)
  def guarded(self,*a,**kw):
   if kw.get('historical_scope') is not None or kw.get('generated_scope')!=f.GENERATED:blocked('HISTORICAL_FINANCIAL_CONSTRUCTOR:'+label)
   value=original(self,*a,**kw);CONSTRUCTIONS.append(label);return value
  return guarded
 cls.__init__=make_guard(original,label)
def forbid(label):
 def denied(*a,**kw):blocked(label)
 return denied
# Do not overwrite read-only envelope validators or negative historical-entry
# functions: exact tests exercise them before any late finance/source boundary.
for key in ('_year_projection','_load_annual_artifacts','_annual','validate_case_inputs'):
 if key in entry.G:entry.G[key]=forbid('REAL_SOURCE_PROVIDER_OR_INPUT:'+key)
# Finance-changing launch functions remain originals for code-identity proofs.
# Per-test negatives patch them; audit denies every actual process and actual
# claim directory. No valid real GO or source/data bodies exist in extraction.
modules=('test_core','test_forecast_boundaries','test_forecast_entry_boundaries','test_forecast_import_conflict','test_reviewer_adversarial','test_reviewer_import_bindings','test_reviewer_saved_policy')
loader=unittest.TestLoader();all_tests=unittest.TestSuite(loader.loadTestsFromName(n) for n in modules)
def flatten(suite):
 for item in suite:
  if isinstance(item,unittest.TestSuite):yield from flatten(item)
  else:yield item
NONCOLD_ID='test_forecast_entry_boundaries.RunnerFailClosedBoundaries.test_complete_new_source_identity_includes_entry_historical_runner_manifest_controls'
excluded=[test.id() for test in flatten(all_tests) if test.id()==NONCOLD_ID]
assert excluded==[NONCOLD_ID]
suite=unittest.TestSuite(test for test in flatten(all_tests) if test.id()!=NONCOLD_ID)
if suite.countTestCases()!=73:raise SystemExit('EXACT_GENERATED73_SUITE_REQUIRED')
PHASE='GENERATED_TESTS';result=unittest.TextTestRunner(verbosity=2).run(suite)
imports={};mismatch=[];manifest=json.loads((ROOT/'FILES.json').read_bytes())
for name,module in tuple(sys.modules.items()):
 filename=getattr(module,'__file__',None)
 if filename:
  path=Path(filename).resolve()
  if path.is_relative_to(ROOT):
   rel=str(path.relative_to(ROOT));digest=hashlib.sha256(path.read_bytes()).hexdigest();imports[name]={'path':rel,'SHA256':digest}
   if rel not in manifest['files'] or manifest['files'][rel]['SHA256']!=digest:mismatch.append(rel)
status='PASS_DETACHED_GENERATED73_ONLY' if result.wasSuccessful() and result.testsRun==73 and not result.skipped and not DENIED and not mismatch else 'BLOCKER'
receipt={'schema':'CAUSAL_FORECAST_DETACHED_COLD_GENERATED73_RECEIPT_V1','status':status,'tests_run':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),'skipped':len(result.skipped),'suite_counts':{'core':5,'controller_boundaries':33,'entry_envelope_runner_and_saved_generated':19,'cached_import_conflict':4,'reviewer_adversarial':7,'reviewer_import_binding':1,'reviewer_saved_generated_policy':4},'real_input_positive_source_callback_tests_not_run':4,'external_annual_preparation_code_identity_tests_not_run':excluded,'original_final_review_tests':78,'elapsed_seconds':time.monotonic()-START,'main_CPU':cpu,'main_affinity':sorted(os.sched_getaffinity(0)),'numerical_compute_pool_threads':1,'resource_profile_rerun':False,'blocked_events':DENIED,'project_import_mismatches':mismatch,'project_imports':imports,'generated_inherited_constructor_returns':len(CONSTRUCTIONS),'historical_accounts_constructed':0,'historical_market_minutes_advanced':0,'real_source_provider_iterations':0,'network_calls':0,'actual_processes_launched':0,'actual_claims_or_leases_created':0,'approved_real_GO_bodies_read':0,'actual_financial_outputs_read':0,'publication_actions':0,'full_self_contained_historical_replay_claimed':False,'coverage_scope':'Exact generated fixture tests only. Temporary missing-claim negative probes are allowed inside extraction; no actual claim directory, real provider, financial historical entry or process is allowed. Existing generated resource evidence is not replayed.'}
OUT.parent.mkdir(parents=True,exist_ok=True)
with OUT.open('x') as stream:json.dump(receipt,stream,indent=2,sort_keys=True);stream.write('\n')
import shutil
shutil.rmtree(TMP)
print(json.dumps({k:receipt[k] for k in ('status','tests_run','failures','errors','skipped','elapsed_seconds','blocked_events','project_import_mismatches')},sort_keys=True))
raise SystemExit(0 if status=='PASS_DETACHED_GENERATED73_ONLY' else 1)
