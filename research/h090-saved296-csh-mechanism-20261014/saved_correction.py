"""Saved-only exact receipt correction and mocked wrapper exit regression; no finance imports."""
import os,sys,time,datetime,resource,signal,pathlib,json,gzip,hashlib,ast,types,difflib,re,traceback
from decimal import Decimal as D,localcontext,ROUND_HALF_EVEN
P=pathlib.Path;BASE=P('/workspace/coin-cloud');OLD=BASE/'h090-saved296-csh-mechanism-20261014/attempt001';SIX=BASE/'h090-finite-initial6min-diagnostic-20261014/attempt001';OUT=BASE/'h090-saved296-correction-publication-20261014/attempt001';END=1698105600000000
assert not OUT.exists();OUT.mkdir(parents=True);START=datetime.datetime.now(datetime.timezone.utc);BEG=time.monotonic();os.sched_setaffinity(0,{min(os.sched_getaffinity(0))})
for k,v in [(resource.RLIMIT_CPU,120),(resource.RLIMIT_AS,4000000000),(resource.RLIMIT_FSIZE,25000000)]:resource.setrlimit(k,(v,v))
signal.signal(signal.SIGALRM,lambda *a:(_ for _ in ()).throw(TimeoutError('SAVED_POSTPROCESS120')));signal.alarm(120)
r={'PID':os.getpid(),'start_UTC':START.isoformat(),'deadline_UTC':(START+datetime.timedelta(seconds=120)).isoformat(),'financial_imports':0,'financial_advance':0,'source_loads':0};print('POSTPROCESS_START',json.dumps(r),flush=True)
def sha(b):return hashlib.sha256(b).hexdigest()
def pin(p,h,size=None):
 b=p.read_bytes();assert sha(b)==h and (size is None or len(b)==size),(p.name,'PIN');return b
def dump(p,v):assert not p.exists();p.write_text(json.dumps(v,sort_keys=True,indent=2,allow_nan=False)+'\n')
rc=1
try:
 pin(OLD/'TERMINAL_RECEIPT.json','9224ee3f98d9663d347e66306819d4c2353cbe811b512c6663009f5b121604bb');draft=(OLD/'RESULT.json').read_bytes();v=json.loads(draft);exact={};inputs={};recsets={}
 for label,arm,mh in [('CONTROL','CONTROL_ATTEMPT003','7810be2d1e06f88d7a67f2a687e569a2e5e4adc7ae38a13ac471253b6f8da31a'),('FINITE','FINITE_ATTEMPT001','cf296556c26f7b437adfafee1a100bdfb8b1bb656afd68bd42588fca92d13897')]:
  root=BASE/'h090-original-wallet-2023-20261014'/arm/'final_evidence';mf=json.loads(pin(root/'EVIDENCE_MANIFEST.json',mh));rows={}
  for n in ['NATIVE_FILLS','NATIVE_ACCOUNT_FUNDING']:
   fn=n+'.jsonl.gz';p=mf['files'][fn];b=pin(root/fn,p['SHA256'],p['bytes']);inputs[label+'/'+fn]=p;rows[n]=[z for line in gzip.decompress(b).splitlines() if (z:=json.loads(line))['event_us']<=END]
  recsets[label]=rows
  with localcontext() as ctx:
   ctx.prec=40;ctx.rounding=ROUND_HALF_EVEN;fills=rows['NATIVE_FILLS'];fund=rows['NATIVE_ACCOUNT_FUNDING'];z=D(0)
   def fold(key):return sum((D(x['decimal_strings'][key]) for x in fills),z)
   exact[label]={'fees':str(fold('fee_amount')),'execution_cost':str(fold('execution_cost')),'realized_PnL_at_actual_fill_prices':str(fold('realized_PnL')),'fill_price_turnover':str(sum((D(x['decimal_strings']['quantity'])*D(x['decimal_strings']['fill_price']) for x in fills),z)),'funding_cash':str(sum((D(x['decimal_strings']['signed_funding_USDT']) for x in fund),z)),'native_fill_count':len(fills),'funding_record_count':len(fund),'fold':'saved receipt order; decimal_strings only; Decimal precision40 ROUND_HALF_EVEN','half_spread_and_slippage':'Native execution_cost includes both BASE27 half-spread4bp and slippage4bp; no double subtraction from realized fill-price PnL'}
 with localcontext() as ctx:
  ctx.prec=40;ctx.rounding=ROUND_HALF_EVEN;diff={k:str(D(exact['FINITE'][k])-D(exact['CONTROL'][k])) for k in ['fees','execution_cost','realized_PnL_at_actual_fill_prices','fill_price_turnover','funding_cash']}
 v['exact_saved_receipt_totals']=exact;v['exact_receipt_FINITE_minus_CONTROL']=diff;v['corrected_cost_input_hashes']=inputs;v['preserved_failed_draft_SHA256']=sha(draft);v['initial_failed_module_receipt_SHA256']='9224ee3f98d9663d347e66306819d4c2353cbe811b512c6663009f5b121604bb';v['status']='PASS_CORRECTED_SAVED_RECORD_EVIDENCE_NOT_CAUSAL_SEPARATION';v['Decimal_CONTROL_prefix_NAV']='UNAVAILABLE_NO_EXACT_SAVED_PREFIX_ACCOUNT_SNAPSHOT';v['Float64_bridge_remains_distinct']=True
 # First fill difference retains actual native order and exact raw rows; differing IDs alone are not a causal claim.
 a=recsets['CONTROL']['NATIVE_FILLS'];b=recsets['FINITE']['NATIVE_FILLS'];v['first_native_fill_difference']=next(({'native_receipt_index':i,'CONTROL':a[i] if i<len(a) else None,'FINITE':b[i] if i<len(b) else None,'scope':'raw saved row difference; not isolated mechanism attribution'} for i in range(max(len(a),len(b))) if (a[i] if i<len(a) else None)!=(b[i] if i<len(b) else None)),None)
 v['first_rejection_or_admission_evidence_difference']['scope']='Raw saved rejection/order row difference; absence or differing IDs does not prove a different counterfactual admission.'
 v['mechanisms']['causal_separation']='CANNOT_CAUSALLY_SEPARATE_8OVER9_TARGET_SCALING_FROM_8000_NONREFILL_BUDGET_FROM_SAVED_RECORDS';v['mechanisms']['claims_scope']='Observed targets/positions/refusal counts and equity/exposure trajectories only. No controlled counterfactual, tuning, causal or annual-return claim.'
 pub=json.loads((SIX/'publication_attempt001/TERMINAL_RECEIPT.json').read_bytes());prefix='research/h090-finite-initial6min-diagnostic-20261014/';sixpin=pub['published'][prefix+'DIAGNOSTIC_RESULT.json'];sb=pin(SIX/'DIAGNOSTIC_RESULT.json',sixpin['SHA256'],sixpin['bytes']);original=json.loads(sb)
 fp=pub['published'][prefix+'journals/NATIVE_FILLS.jsonl.gz'];fb=pin(SIX/'NATIVE_FILLS.jsonl.gz',fp['SHA256'],fp['bytes']);fills=[json.loads(line) for line in gzip.decompress(fb).splitlines()];assert len(fills)==0
 annotation={'schema':'ADDITIVE_SIX_MINUTE_DIAGNOSTIC_CORRECTION_V1','original_commit':'95c695c5900422a3ce0d926ccf2009aeffb7495a','original_result_SHA256':sha(sb),'original_result_unchanged':True,'original_finite_actual_fills_metadata':original['finite_actual_fills'],'corrected_actual_native_fill_count':len(fills),'corrected_actual_FINITE_fill_count':0,'authority':'actual pinned NATIVE_FILLS journal is empty; rejected pre-execution fill-owner bindings are not fills','NATIVE_FILLS_SHA256':fp['SHA256'],'CSH_admission_checks':25,'CSH_pending_only_shadow_changes':0,'scope':'six-minute only, not full296day causal attribution','worker_original_exit':1,'wrapper_correction_is_code_only_no_financial_rerun':True}
 v['initial6min_reference']['actual_fill_count_corrected']=0;v['initial6min_reference']['original_metadata_count_not_execution_count']=original['finite_actual_fills']
 codepin=pub['published'][prefix+'diagnostic.py'];code=pin(P('/tmp/h090_finite_six_minute_diagnostic.py'),codepin['SHA256'],codepin['bytes']).decode();old="  try:sys.exit(worker())\n  except BaseException:traceback.print_exc();sys.exit(1)";new="  try:worker_exit_code=worker()\n  except BaseException:traceback.print_exc();worker_exit_code=1\n  sys.exit(worker_exit_code)";assert code.count(old)==1;corrected=code.replace(old,new,1);ast.parse(corrected)
 # Execute only AST main guard using mocked worker/controller/traceback; no harness/project imports.
 main=ast.parse(corrected).body[-1];assert isinstance(main,ast.If);mocktests=[]
 for label,failure,expected in [('success_returns_zero',False,0),('worker_error_returns_nonzero',True,1)]:
  calls=[]
  def mockworker():
   calls.append('worker')
   if failure:raise RuntimeError('MOCK_ERROR')
   return 0
  mocksys=types.SimpleNamespace(argv=['diagnostic.py','--worker'],exit=sys.exit);tb=types.SimpleNamespace(print_exc=lambda:calls.append('traceback'))
  try:exec(compile(ast.Module(body=[main],type_ignores=[]),'mocked_main_guard','exec'),{'__name__':'__main__','sys':mocksys,'worker':mockworker,'controller':lambda:(_ for _ in ()).throw(AssertionError('NO_CONTROLLER')),'traceback':tb})
  except SystemExit as e:actual=e.code
  assert actual==expected and calls==(['worker','traceback'] if failure else ['worker']);mocktests.append({'node':label,'expected_exit':expected,'actual_exit':actual,'calls':calls,'PASS':True,'financial_imports':0})
 package=OUT/'public_package';package.mkdir();dump(package/'RESULT.json',v);dump(package/'SIX_MINUTE_ADDITIVE_CORRECTION.json',annotation);dump(package/'MOCK_EXIT_TEST_RECEIPT.json',{'schema':'PURE_MOCK_DIAGNOSTIC_EXIT_REGRESSION_V1','tests':mocktests,'original_source_SHA256':codepin['SHA256'],'corrected_source_SHA256':sha(corrected.encode()),'historical_reruns':0});(package/'diagnostic_original_95c.py').write_bytes(code.encode());(package/'diagnostic_exit_corrected.py').write_bytes(corrected.encode());(package/'WRAPPER_EXIT_ONLY.diff').write_text(''.join(difflib.unified_diff(code.splitlines(True),corrected.splitlines(True),fromfile='immutable95c',tofile='additive_exit_corrected')));(package/'saved_correction.py').write_bytes(P(__file__).read_bytes());(package/'SCOPE.md').write_text('New saved-only correction module; original expired331773 failure/draft and executed95c code/result remain unchanged. Exact receipt costs/funding use decimal_strings. Net/price common-prefix bridge remains Float64 because exact CONTROLprefix NAV snapshot is unavailable. Only raw target/position/admission-row differences, refusal counts and trajectories are established. No8/9-versus8000 causal separation. Six-minute actual fills0 come from the empty native journal, not pre-execution owner bindings. Wrapper success/error exits tested only with two mocks; no historical rerun.\n')
 # Targeted concrete-token scan; source scanner literals are not credentials.
 patt=re.compile(rb'gh[pousr]_[A-Za-z0-9]{25,}|AKIA[A-Z0-9]{16}|-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----')
 for p in package.iterdir():assert not patt.search(p.read_bytes()),('ACTUAL_SECRET_PATTERN',p.name)
 inventory={p.name:{'bytes':p.stat().st_size,'SHA256':sha(p.read_bytes())} for p in package.iterdir()};dump(package/'FILES.json',inventory)
 r.update(status='PASS_SAVED_DECIMAL_CORRECTION_AND_TWO_MOCK_EXIT_TESTS',exact_totals=exact,exact_differences=diff,six_actual_fills=0,six_original_binding_count=original['finite_actual_fills'],mock_tests=mocktests,public_files=len(inventory)+1,public_bytes=sum(p.stat().st_size for p in package.iterdir()),causal_separation='NOT_IDENTIFIED');assert r['public_bytes']<=25000000;rc=0
except BaseException as e:r.update(status='FAILED_STOP_NO_RETRY',error=repr(e),traceback=traceback.format_exc())
signal.alarm(0);u=resource.getrusage(resource.RUSAGE_SELF);r['resource']={'exit':rc,'end_UTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'wall_seconds':time.monotonic()-BEG,'CPU_seconds':u.ru_utime+u.ru_stime,'peak_RSS_bytes':u.ru_maxrss*1024};dump(OUT/'POSTPROCESS_RECEIPT.json',r);print('POSTPROCESS_TERMINAL',json.dumps(r));print('RECEIPT_SHA256',sha((OUT/'POSTPROCESS_RECEIPT.json').read_bytes()));sys.exit(rc)
