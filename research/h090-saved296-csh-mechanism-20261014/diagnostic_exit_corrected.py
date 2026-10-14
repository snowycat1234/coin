"""Root-authorized six-minute ORIGINAL FINITE diagnostic; read-only admission tracing.
No annual dispatcher; shadow calculations never change actual admission/state.
"""
import os,sys,time,datetime,resource,signal,pathlib,json,hashlib,subprocess,fcntl,types,argparse,traceback,gzip,inspect,itertools,math,shutil
P=pathlib.Path;ROOT=P('/workspace/coin-cloud/h090-original2023-code-20261014');N=ROOT/'coin_h090_original2023_finite_tail_bridge_20261014';B=P('/workspace/coin-cloud/grid-original-source-2023-20261014');OUT=P('/workspace/coin-cloud/h090-finite-initial6min-diagnostic-20261014/attempt001');HORIZON=1672531560000000;PREP='49bc1fb1fc33c7eb6b7d540b9567b16e0d615dfd2979bbb1dd927df44649c819';REVSHA='210f96343a4c4128094e9771190cdfdd775bc7b25a34aad2f55a648907f93abc';REVIEW=P('/workspace/coin-cloud/h090-finite-tail-publication-20261014/attempt001/INDEPENDENT_PREPARATION_REVIEW_49bc.json')
def sha(b):return hashlib.sha256(b).hexdigest()
def saved(p,h):
 b=p.read_bytes();assert sha(b)==h,('PIN',p.name);return b
def jwrite(p,v):
 assert not p.exists();p.write_text(json.dumps(v,sort_keys=True,indent=2,allow_nan=False)+'\n')
def worker():
 start=datetime.datetime.now(datetime.timezone.utc);begin=time.monotonic();print('TINY_FINANCIAL_WORKER',os.getpid(),start.isoformat(),os.environ['DIAG_FIXED_DEADLINE'],flush=True)
 # Exact freeze-first checked-source bootstrap; unchanged gate/constructor code.
 raw=saved(N/'PREPARATION_MANIFEST.json',PREP);mf=json.loads(raw)
 for name,v in mf['files'].items():b=saved(N/name,v['SHA256']);assert len(b)==v['bytes']
 m=types.ModuleType('verified_source');m.__file__=str(N/'verified_source.py');m.__spec__=__import__('importlib').machinery.ModuleSpec('verified_source',None,origin=m.__file__);sys.modules['verified_source']=m;exec(compile((N/'verified_source.py').read_bytes(),m.__file__,'exec'),m.__dict__);rt=m.install(PREP,'source_case')
 import bridge_runtime_locator
 rt.runtime_packages=bridge_runtime_locator.configure_runtime()
 import driver,bridge_bindings as BB
 a=argparse.Namespace(command='case',year=2023,arm='FINITE',roots=str(B/'PRIVATE_ROOTS.json'),source_go=str(B/'SOURCE_GO_2023.json'),source_go_sha=BB.SOURCE_GO_SHA,source_receipt=str(N/'SOURCE_RECEIPT_2023.json'),source_receipt_sha=BB.SOURCE_SHA,case_go=str(OUT/'DIAGNOSTIC_GO_PRIVATE.json'),case_go_sha=os.environ['DIAG_GO_SHA'],review=str(REVIEW),review_sha=REVSHA,output=str(OUT),remaining_seconds=os.environ['DIAG_REMAINING'],completed_control_evidence=str(N/'baseline_control_metadata/EVIDENCE_MANIFEST.json'),completed_control_evidence_sha='7810be2d1e06f88d7a67f2a687e569a2e5e4adc7ae38a13ac471253b6f8da31a')
 driver.bounded_worker_guard(a);BB.case_gate(a)
 from project_inputs import source_only
 from grid_driver import compare_source_receipt
 admitted,computed=source_only(BB.read(a.roots),2023,a.source_go,a.source_go_sha);computed['roots_SHA256']=BB.sha(a.roots);assert compare_source_receipt(computed,a)==BB.read(a.source_receipt)
 import original_bridge as O,finite_preview_callers as F,native_control as NC
 from grid_evidence import safe,json_lines
 import numpy as np
 sim=O.make_sim(admitted,'FINITE',case_args=a)
 charged=[];current={};minute_values=[];capcode=F.PrefixFiniteNativeCandidate._atomic_owner_admission.__code__;advancecode=NC.H090NativeControl.advance_day.__code__
 lines,base=inspect.getsourcelines(F.PrefixFiniteNativeCandidate._atomic_owner_admission);cornerline=base+next(i for i,s in enumerate(lines) if 'for base_point in product' in s)
 daylines,daybase=inspect.getsourcelines(NC.H090NativeControl.advance_day);loopline=daybase+next(i for i,s in enumerate(daylines) if 'for t,market_row in self.tape.day' in s)
 def corners(l,drop_pending):
  answer=[];finite_ends=(l['finite_actual'],) if drop_pending else l['finite_ends'];cov=l['cov'];prices=l['prices'];nav=float(l['nav'])
  for point in itertools.product(*l['endpoints']):
   for fq in finite_ends:
    signed=np.asarray([float(v) for v in point]);signed[0]+=float(fq);gross=np.abs(np.asarray([float(v) for v in point]));gross[0]+=abs(float(fq));weights=gross*prices/nav;w=signed*prices/nav;variance=float(w@cov@w);sigma=math.sqrt(max(variance,0)) if math.isfinite(variance) else None
    vals={'gross':float(weights.sum()),'max_asset':float(weights.max()),'sigma':sigma};fail=[]
    if point[0]*fq<0:fail.append('OPPOSING_OWNER_COLLISION')
    if not math.isfinite(variance) or variance < -1e-15:fail.append('COVARIANCE_INVALID')
    if vals['gross']>.90+1e-12:fail.append('GROSS_090')
    if vals['max_asset']>.30+1e-12:fail.append('ASSET_030')
    if sigma is not None and sigma>.15+1e-12:fail.append('SIGMA_015')
    answer.append({'base_quantities':[str(x) for x in point],'finite_quantity':str(fq),**vals,'thresholds':{'gross':.90+1e-12,'max_asset':.30+1e-12,'sigma':.15+1e-12},'failed_components':fail,'first_failing_component':fail[0] if fail else None})
  return answer
 class EndDiagnostic(Exception):pass
 def trace(frame,event,arg):
  if frame.f_code is capcode:
   l=frame.f_locals
   if event=='call':current[id(frame)]={'owner':None,'actual':None}
   if event=='line' and frame.f_lineno==cornerline:
    rows=corners(l,False);owner=l['owner'];item={'owner':owner,'clock_us':l['event'],'fill_id':l['fill_id'],'NAV_decimal':str(l['nav']),'prices':l['prices'].tolist(),'covariance':l['cov'].tolist(),'corners':rows,'first_actual_failing_corner':next((i for i,v in enumerate(rows) if v['failed_components']),None),'finite_actual_probe_quantity':str(l['finite_actual']),'finite_pending_target':str(l['finite_target'])}
    if owner=='CSH':
     shadow=corners(l,True);item['CSH_shadow_without_unfilled_finite_pending']=shadow;item['CSH_shadow_cap_pass']=not any(v['failed_components'] for v in shadow)
    else:item['finite_hypothetical_filled_position_preserved']=True
    current[id(frame)]=item
   if event=='return':
    item=current.pop(id(frame),{});item.update(owner=l.get('owner'),clock_us=l.get('event'),fill_id=l.get('fill_id'),actual_decision=safe(arg));
    if item.get('owner')=='CSH':item['CSH_shadow_decision_changed']=bool(isinstance(arg,dict) and not arg['allow_increases'] and arg['reason']=='COMBINED_OWNER_ACTUAL_PENDING_090_030_015_CAP' and item.get('CSH_shadow_cap_pass'))
    charged.append(item)
  if frame.f_code is advancecode and event=='line' and frame.f_lineno==loopline and sim.rows_written>=6:
   minute_values.extend(frame.f_locals['values']);raise EndDiagnostic()
  return trace
 sys.settrace(trace)
 try:sim.advance_day()
 except EndDiagnostic:pass
 finally:sys.settrace(None)
 assert sim.rows_written==6 and len(minute_values)==6 and not sim.terminal
 # Prefix saved native journals: exact pinned prior evidence, no normalization.
 prior=ROOT.parent/'h090-original-wallet-2023-20261014/FINITE_ATTEMPT001/final_evidence';em=json.loads(saved(prior/'EVIDENCE_MANIFEST.json','cf296556c26f7b437adfafee1a100bdfb8b1bb656afd68bd42588fca92d13897'));matches={}
 journals={'NATIVE_FILLS':sim.account.trades,'NATIVE_ACCOUNT_FUNDING':sim.account.funding,'NATIVE_SCHEDULER_FUNDING':sim.funding_journal,'REJECTIONS':sim.rejections,'POLICY_EVENTS':sim.policy_events,'TARGET_ROWS':sim.target_rows}
 for name,rows in journals.items():
  fn=name+'.jsonl.gz';p=prior/fn;pin=em['files'][fn];b=saved(p,pin['SHA256']);assert len(b)==pin['bytes'];actual=[(json.dumps(safe(row),sort_keys=True,separators=(',',':'),allow_nan=False)+'\n').encode() for row in rows];old=[]
  with gzip.open(p,'rb') as stream:
   for line in stream:
    row=json.loads(line);clock=row.get('event_us',row.get('signal_us',row.get('available_us',row.get('decision_us'))))
    if clock is None:raise ValueError('UNKNOWN_PREFIX_CLOCK:'+name)
    if clock<=HORIZON:old.append(line)
    else:break
  equal=actual==old;matches[name]={'actual_rows':len(actual),'saved_prefix_rows':len(old),'raw_serialized_bytes_equal':equal,'actual_SHA256':sha(b''.join(actual)),'saved_prefix_SHA256':sha(b''.join(old)),'saved_container_SHA256':pin['SHA256']};json_lines(OUT/(name+'.jsonl.gz'),rows);assert equal,('PREFIX_JOURNAL_MISMATCH',name,matches[name])
 finite=[x for x in charged if x.get('owner')=='MART_FINITE_REPLACE10'];csh=[x for x in charged if x.get('owner')=='CSH'];report={'schema':'ORIGINAL_FINITE_INITIAL_SIX_MINUTE_PENDING_CAP_DIAGNOSTIC_V1','status':'PASS_DIAGNOSTIC_PREFIX_UNCHANGED','horizon_UTC':'2023-01-01T00:06:00Z','horizon_us':HORIZON,'completed_minutes':6,'source_receipt_SHA256':BB.SOURCE_SHA,'preparation_SHA256':PREP,'code_public_commit':'47f44d0b1b3edf45ba542abb69ab2066bdb2ebc2','original_finite_science_SHA256':BB.FINITE_SHA,'annual_gate_unchanged':True,'tiny_resource_protocol_separate_from_annual':True,'actual_finite_admission_attempts':finite,'CSH_admissions':csh,'CSH_shadow_changed_count':sum(bool(x.get('CSH_shadow_decision_changed')) for x in csh),'finite_actual_fills':sum(1 for v in sim._fill_owner.values() if v[0]=='MART_FINITE_REPLACE10'),'prefix_journal_comparisons':matches,'all_charged_corners':charged,'minute_close_values':minute_values,'actual_NAV_decimal':str(sim.account.nav()),'paid_NAV':None,'not_annual_result':True,'shadow_never_routes_or_mutates_actual_state':True,'no_retuning':True,'source_gate_original':True}
 jwrite(OUT/'DIAGNOSTIC_RESULT.json',report);print('DIAGNOSTIC_NUMERIC',json.dumps({'status':report['status'],'finite_attempts':len(finite),'CSH_admissions':len(csh),'CSH_shadow_changed_count':report['CSH_shadow_changed_count'],'first_failures':[x['corners'][x['first_actual_failing_corner']]['first_failing_component'] for x in finite if x.get('first_actual_failing_corner') is not None],'prefix_exact':True}),flush=True)
 return 0

def controller():
 assert not OUT.exists();OUT.mkdir(parents=True)
 start=datetime.datetime.now(datetime.timezone.utc);begin=time.monotonic();deadline=start+datetime.timedelta(seconds=60);print('DIAGNOSTIC_CONTROLLER_START',os.getpid(),start.isoformat(),deadline.isoformat(),flush=True)
 receipt={'PID':os.getpid(),'start_UTC':start.isoformat(),'deadline_UTC':deadline.isoformat(),'cleanup':False,'annual_dispatch':False,'child_PID':None};child=None;rc=1
 with P('/tmp/coin_offline_financial_controller.lock').open('a') as lock:
  try:
   fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
   # Known completed project controller/child registry only; no global process scan.
   known=[321948,289807,289812]
   for pid in known:
    p=P('/proc')/str(pid)/'cmdline'
    if p.exists():
     argv=p.read_bytes();assert not (b'run_verified.py' in argv or b'--worker' in argv),('KNOWN_ACTIVE_PROJECT_JOB',pid)
   free=shutil.disk_usage(OUT).free;assert free>=25000000+64000000,'TINY_OUTPUT_PLUS_SAFE_MARGIN';receipt['tiny_disk_reservation']={'free_bytes':free,'bound_bytes':25000000,'safe_margin_bytes':64000000,'annual15GiBgate_not_invoked_or_changed':True};receipt['known_job_registry_no_active']=True
   g=json.loads(saved(B/'CASE_GO_H090_FINITE2023_TAIL_ATTEMPT001.json','be1f8be1c1d2e2cf4130915fc663b0bdac94bbe9b1923b87fdddb6956659c1d3'));g['output_directory']=str(OUT);g['scope']='ROOT authorized independent actual ORIGINAL2023 FINITE diagnostic from origin through Jan1 00:06 UTC only. Actual fixed6f915 economics and source/proof/CONTROL gates unchanged. Observational charged-corner and pending-only CSH shadow; no annual run or retuning. Separate60s/oneCPU/2GBRSS/4GBAS/25MB tiny protocol.';jwrite(OUT/'DIAGNOSTIC_GO_PRIVATE.json',g);gsha=sha((OUT/'DIAGNOSTIC_GO_PRIVATE.json').read_bytes());remaining=str(min(55.,60-(time.monotonic()-begin)-2.));rd,wr=os.pipe()
   env=dict(os.environ,BOT_NATIVE_RUNTIME_SITES=saved(B/'BOT_NATIVE_RUNTIME_SITES.json','65c5f0c8290a3cc64c1ecce771fe2b38f6ea59f41e64224ef16a0c36e0baa7c8').decode(),_GRID_PREP_PARENT_PID=str(os.getpid()),_GRID_PREP_CONTROLLER_FD=str(rd),DIAG_GO_SHA=gsha,DIAG_REMAINING=remaining,DIAG_FIXED_DEADLINE=deadline.isoformat())
   for k in ['PYTHONOPTIMIZE','PYTHONPATH','PYTHONHOME','PYTHONSTARTUP']:env.pop(k,None)
   for k in ['OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS','POLARS_MAX_THREADS','VECLIB_MAXIMUM_THREADS','BLIS_NUM_THREADS']:env[k]='1'
   def limits():
    os.sched_setaffinity(0,{min(os.sched_getaffinity(0))});resource.setrlimit(resource.RLIMIT_CPU,(55,55));resource.setrlimit(resource.RLIMIT_AS,(4000000000,4000000000));resource.setrlimit(resource.RLIMIT_FSIZE,(25000000,25000000))
   log=(OUT/'WORKER_PRIVATE.log').open('x');child=subprocess.Popen([sys.executable,'-I','-S','-B',__file__,'--worker'],env=env,stdout=log,stderr=subprocess.STDOUT,start_new_session=True,preexec_fn=limits,pass_fds=(rd,));os.close(rd)
   packet={'schema':'ORIGINAL_GRID_PREPARATION_CONTROLLER_PIPE_V1','parent_pid':os.getpid(),'command':'case','year':2023,'arm':'FINITE','output':str(OUT),'roots_SHA256':'982a532a87825b7f5258c8690bb41ae7c8327ba29c3d7114003a92f5fb017df5','preparation_manifest_SHA256':PREP,'review_SHA256':REVSHA,'source_GO_SHA256':'17e973a99e1835ce2f2acdfa6c3e692a96a3276cc560455bcfc23b631ceb4c27','source_receipt_SHA256':'54f0c27ec160b99f02848ed9ec121a0f38d4a0672358608da51bafbc0a6e80b1','case_GO_SHA256':gsha,'remaining_seconds':remaining};os.write(wr,json.dumps(packet,sort_keys=True).encode());os.close(wr);receipt['child_PID']=child.pid;print('DIAGNOSTIC_CHILD_START',child.pid,datetime.datetime.now(datetime.timezone.utc).isoformat(),deadline.isoformat(),flush=True)
   peak=0
   while child.poll() is None:
    try:rss=int(next(x.split()[1] for x in (P('/proc')/str(child.pid)/'status').read_text().splitlines() if x.startswith('VmRSS:')))*1024
    except (OSError,StopIteration):rss=0
    peak=max(peak,rss);used=sum(p.stat().st_size for p in OUT.rglob('*') if p.is_file())
    if time.monotonic()-begin>=60 or rss>2000000000 or used>25000000:receipt['resource_stop']='TINY_BOUND';os.killpg(child.pid,signal.SIGKILL);break
    time.sleep(.05)
   rc=child.wait();log.close();receipt['peak_child_RSS_bytes']=peak
  except BaseException as e:receipt['error']=repr(e);receipt['traceback']=traceback.format_exc()
  finally:
   if child and child.poll() is None:os.killpg(child.pid,signal.SIGKILL);child.wait()
 receipt.update(exit=rc,end_UTC=datetime.datetime.now(datetime.timezone.utc).isoformat(),wall_seconds=time.monotonic()-begin,output_bytes=sum(p.stat().st_size for p in OUT.rglob('*') if p.is_file()),status='PASS_TINY_DIAGNOSTIC' if rc==0 else 'FAILED_NO_RETRY');jwrite(OUT/'RESOURCE_RECEIPT_PRIVATE.json',receipt);print('DIAGNOSTIC_TERMINAL',json.dumps(receipt));print((OUT/'WORKER_PRIVATE.log').read_text()[-3500:] if (OUT/'WORKER_PRIVATE.log').exists() else 'NO_CHILD');return rc
if __name__=='__main__':
 if '--worker' in sys.argv:
  try:worker_exit_code=worker()
  except BaseException:traceback.print_exc();worker_exit_code=1
  sys.exit(worker_exit_code)
 else:sys.exit(controller())
