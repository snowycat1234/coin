"""One-case preparation driver. All historical reads/accounts require own GO.

The original resource-controller helpers are reused. This adds no scheduler,
financial kernel, learned strategy, resumability or automatic case sweep.
"""
from pathlib import Path
import argparse,fcntl,json,math,os,resource,select,shutil,signal,stat,subprocess,sys,time
if __name__=='__main__':raise SystemExit('USE_RUN_VERIFIED_COLD_BOOTSTRAP')
from verified_source import require_runtime
require_runtime()
import bindings as B
from project_inputs import source_only

CASE_SECONDS=600

def save(path,obj):
 with Path(path).open('x') as f:json.dump(obj,f,indent=2,sort_keys=True,allow_nan=False);f.write('\n')

def source_check(args):
 source_gates(args)
 roots=B.read(args.roots)
 _,receipt=source_only(roots,args.year,args.source_go,args.source_go_sha)
 receipt['roots_SHA256']=B.sha(args.roots)
 save(args.output,receipt);return receipt

def review_gate(path,expected):
 if path is None or expected is None:raise ValueError('INDEPENDENT_PREPARATION_REVIEW_REQUIRED')
 B.check(path,expected);review=B.read(path)
 if review.get('schema')!='INDEPENDENT_ORIGINAL_CSH_GRID_DRIVER_PREPARATION_REVIEW_V1' or review.get('status')!='PASS_PREPARATION_GENERATED_ONLY' or review.get('preparation_manifest_SHA256')!=B.sha(B.HERE/'PREPARATION_MANIFEST.json'):
  raise ValueError('EXACT_PREPARATION_REVIEW_SCOPE_REQUIRED')

def source_gates(args):
 review_gate(args.review,args.review_sha)
 go=B.require_go(args.source_go,args.source_go_sha,'SOURCE_ONLY_ORIGINAL_PROJECTION',args.year)
 if go.get('output_file')!=str(Path(args.output).resolve()):raise ValueError('SOURCE_GO_FRESH_RECEIPT_DESTINATION_REQUIRED')
 return go

def bounded_worker_guard(args):
 if os.environ.get('_GRID_PREP_PARENT_PID')!=str(os.getppid()) or len(os.sched_getaffinity(0))!=1 or sys.flags.optimize:
  raise ValueError('ORIGINAL_BOUNDED_PARENT_REQUIRED_BEFORE_SOURCE_OR_ACCOUNT')
 for kind,cap in ((resource.RLIMIT_AS,4000000000),(resource.RLIMIT_CPU,600)):
  soft,hard=resource.getrlimit(kind)
  if soft==resource.RLIM_INFINITY or hard==resource.RLIM_INFINITY or soft<=0 or hard<=0 or soft>hard or soft>cap or hard>cap:
   raise ValueError('FINITE_SOFT_AND_HARD_ORIGINAL_RESOURCE_CAPS_REQUIRED')
 for name in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS','POLARS_MAX_THREADS'):
  if os.environ.get(name)!='1':raise ValueError('EXACT_ONE_MATH_THREAD_ENV_REQUIRED')
 remaining=float(args.remaining_seconds)
 if not math.isfinite(remaining) or not 0<remaining<=595:raise ValueError('FINITE_ORIGINAL_REMAINING_SECONDS_REQUIRED')
 require_controller_handoff(args)
 require_runtime().bounded_worker_admitted=True

def controller_packet(args):
 return dict(schema='ORIGINAL_GRID_PREPARATION_CONTROLLER_PIPE_V1',parent_pid=os.getpid(),
  command=args.command,year=args.year,arm=getattr(args,'arm',None),output=str(Path(args.output).resolve()),
  roots_SHA256=B.sha(args.roots),preparation_manifest_SHA256=B.sha(B.HERE/'PREPARATION_MANIFEST.json'),
  review_SHA256=args.review_sha,source_GO_SHA256=args.source_go_sha,
  source_receipt_SHA256=getattr(args,'source_receipt_sha',None),case_GO_SHA256=getattr(args,'case_go_sha',None),
  remaining_seconds=str(args.remaining_seconds))

def require_controller_handoff(args):
 try:
  descriptor=int(os.environ.get('_GRID_PREP_CONTROLLER_FD','-1'))
  if descriptor<3 or not stat.S_ISFIFO(os.fstat(descriptor).st_mode):raise ValueError('INHERITED_CONTROLLER_PIPE_REQUIRED')
  if not select.select([descriptor],[],[],2.)[0]:raise ValueError('CONTROLLER_PIPE_HANDSHAKE_TIMEOUT')
  packet=json.loads(os.read(descriptor,4096))
 except (OSError,TypeError,ValueError) as error:raise ValueError('VERIFIED_CONTROLLER_HANDOFF_REQUIRED') from error
 finally:
  if 'descriptor' in locals() and descriptor>=3:
   try:os.close(descriptor)
   except OSError:pass
 expected=controller_packet(args);expected['parent_pid']=os.getppid()
 if packet!=expected or os.environ.get('_GRID_PREP_PARENT_PID')!=str(os.getppid()):raise ValueError('CONTROLLER_HANDOFF_BINDING_MISMATCH')
 try:os.kill(os.getppid(),0)
 except OSError as error:raise ValueError('CONTROLLER_NOT_LIVE') from error

def case_gates(args):
 review_gate(args.review,args.review_sha)
 go=B.require_go(args.case_go,args.case_go_sha,'ONE_FRESH_NATIVE_CASE',args.year,args.arm)
 B.check(args.source_receipt,args.source_receipt_sha);r=B.read(args.source_receipt)
 if r.get('schema')!='ORIGINAL_CSH_SOURCE_ONLY_PROJECTION_RECEIPT_V1' or r.get('status')!='PASS_ORIGINAL_TARGET_COVARIANCE_SOURCE_ONLY_NO_WALLET' or r.get('year')!=args.year or r.get('input_manifest_SHA256')!=B.sha(B.HERE/'INPUT_MANIFEST.json') or r.get('parent_source_GO_SHA256')!=args.source_go_sha or r.get('preparation_manifest_SHA256')!=B.sha(B.HERE/'PREPARATION_MANIFEST.json') or r.get('roots_SHA256')!=B.sha(args.roots):
  raise ValueError('EXACT_YEAR_SOURCE_ONLY_RECEIPT_REQUIRED')
 # The unchanged original26 gate hashes both old target artifact bytes. It
 # never selects their market/target values here. Name the extra hash-only
 # scope in case GO instead of silently broadening a single-year read grant.
 if go.get('original26_hash_only_target_artifacts')!=['Y2023.npz','Y2025.npz']:
  raise ValueError('ORIGINAL26_TWO_ARTIFACT_HASH_ONLY_SCOPE_REQUIRED')
 if go.get('output_directory')!=str(Path(args.output).resolve()) or go.get('source_receipt_SHA256')!=args.source_receipt_sha or go.get('preparation_manifest_SHA256')!=B.sha(B.HERE/'PREPARATION_MANIFEST.json'):
  raise ValueError('ONE_CASE_GO_MUST_BIND_FRESH_DESTINATION_SOURCE_REVIEW')
 if args.year==2025 and args.arm=='CSH':
  raise ValueError('DEDUP_EXISTING2025_CSH_REUSE_PENDING_FULL_PACKET_VERIFICATION_NO_NEW_CONTROL')
 if args.arm=='CSH' and go.get('control_dedup_decision')!={2023:'NO_PROVEN_MATCHED_TERMINAL60_CONTROL',2024:'EXISTING_HALT_PREFIX_NOT_BYTE_PROVEN'}[args.year]:
  raise ValueError('EXPLICIT_CONTROL_DEDUP_REASON_REQUIRED')
 return go

def make_sim(admitted,year,arm,*,case_args):
 case_gates(case_args)
 import numpy as np
 A=B.load_runtime(case_args.case_go,case_args.case_go_sha,year,arm);window=dict(admitted['window']);window['daily']=A.PORT.native.pl.DataFrame(window['daily'])
 d=admitted['decision_us'];w=admitted['weights']
 def factory(_daily,clocks,mode):
  if mode!='LONG_SHORT' or not np.array_equal(clocks,d):raise ValueError('EXACT_ORIGINAL_TARGET_FACTORY_CLOCK')
  rows=[dict(available_us=int(t),symbol=s,target_weight=float(w[i,j])) for i,t in enumerate(d) for j,s in enumerate(B.S)]
  frame=A.PORT.native.pl.DataFrame(rows)
  if frame['target_weight'].to_numpy().reshape(w.shape).tobytes()!=w.tobytes():raise ValueError('FACTORY_ORIGINAL_TARGET_BIT_IDENTITY')
  return frame,dict(source='ORIGINAL_UNLAGGED_CS21_HOLD_STATIC50_SAVED_BYTES',year=year,rank_feature_lag_hours=0)
 closes={}
 for i,t in enumerate(d):
  if int(t)//B.DAY%7!=4:continue
  k=int(admitted['source_ids'][i])
  # Original daily close_us is the completed/available native boundary D.
  # Exact DAILY/cube equality was admitted; never add a day of lag.
  closes[int(t)]=[A.H.CompletedClose(int(admitted['clock'][j]),A.D(str(admitted['prices'][j,0])),int(admitted['clock'][j])) for j in range(k-29,k+1)]
 covariance={int(t):admitted['covariance'][i] for i,t in enumerate(d)}
 # No fabricated pre-year minute mark: a Monday year-start is ineligible
 # until the next weekly decision if the original account has no past mark.
 return A.GridNativeAdapter(window,'LONG_SHORT',A.PORT.native.COSTS[0],A.PORT.native.UNITS[0],
  target_factory=factory,account_factory=A.ACCOUNT,arm={'CSH':'CONTROL','CASH':'CASH','GRID':'GRID'}[arm],daily_closes=closes,covariance=covariance,initial_observations={})

def run_calendar(sim,output,binding,deadline,origin):
 from evidence import export_final
 daily=[];nav=[float(sim.account.nav())];reason=None
 while sim.cursor<sim.end and sim.stop is None:
  if time.monotonic()>=deadline-20:reason='RESOURCE_STOP_COMPLETE_DAY_BOUNDARY_NOT_PAID';break
  row=sim.advance_day();daily.append(row)
  if row['completed']:nav.append(float(sim.account.nav()))
 return export_final(sim,output,binding,daily,nav,reason,origin)

def worker(args):
 bounded_worker_guard(args)
 if args.command=='source-check':return source_check(args)
 case_gates(args)
 admitted,receipt=source_only(B.read(args.roots),args.year,args.source_go,args.source_go_sha)
 receipt['roots_SHA256']=B.sha(args.roots)
 if receipt!=B.read(args.source_receipt):raise ValueError('SOURCE_PROJECTION_RECEIPT_CHANGED')
 sim=make_sim(admitted,args.year,args.arm,case_args=args)
 binding=dict(year=args.year,arm=args.arm,source_projection=receipt,source_receipt_SHA256=args.source_receipt_sha,
  case_GO_SHA256=args.case_go_sha,review_SHA256=args.review_sha,native_adapter_SHA256=B.ADAPTER_SHA,
  preparation_manifest_SHA256=B.sha(B.HERE/'PREPARATION_MANIFEST.json'),initial_capital='10000',financial_account_count=1,
  restore_supported=False,original_target_weights_unchanged=True,terminal_opens=60)
 return run_calendar(sim,Path(args.output)/'final_evidence',binding,time.monotonic()+float(args.remaining_seconds),'SEEN_DEVELOPMENT_ORIGINAL_SOURCE')

def dispatch(args):
 # Same bounded controller for a source-only projection and one financial case.
 began=time.monotonic()
 (source_gates if args.command=='source-check' else case_gates)(args)
 roots=B.read(args.roots);requested=Path(args.output).resolve()
 out=requested.with_name(requested.name+'.source_attempt') if args.command=='source-check' else requested
 if requested.exists() or out.exists():raise ValueError('FRESH_ONE_ATTEMPT_OUTPUT_REQUIRED_NO_RESUME')
 d=B.load_controller();guard=d.original_resource_guard(roots)
 process=None;stop=None;code=None;error=None;peak=0;read_fd=write_fd=None
 with Path('/tmp/coin_offline_financial_controller.lock').open('a') as lock:
  try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
  except BlockingIOError:raise ValueError('ORIGINAL_FINANCIAL_CONTROLLER_LOCKED')
  out.mkdir(parents=True,exist_ok=False)
  save(out/'ATTEMPT_STARTED.json',dict(command=args.command,year=args.year,arm=getattr(args,'arm',None),status='STARTED_ONE_FRESH_ATTEMPT_NO_RETRY',case_GO_SHA256=getattr(args,'case_go_sha',None),source_GO_SHA256=args.source_go_sha))
  try:
   admission=d.resource_admission(roots,out)
   remaining=min(595.,CASE_SECONDS-(time.monotonic()-began)-5.)
   if remaining<=20:raise ValueError('ORIGINAL_CASE600_ADMISSION_BUDGET_EXHAUSTED')
   args.remaining_seconds=str(remaining)
   cmd=[sys.executable,'-B',str(B.HERE/'run_verified.py'),'--preparation-manifest-sha',B.sha(B.HERE/'PREPARATION_MANIFEST.json'),args.command,'--worker','--remaining-seconds',args.remaining_seconds]
   keys=['roots','year','output','source_go','source_go_sha','review','review_sha']
   if args.command=='case':keys+=['arm','source_receipt','source_receipt_sha','case_go','case_go_sha']
   for key in keys:cmd+=['--'+key.replace('_','-'),str(getattr(args,key))]
   def limits():
    guard.child_limits(admission['allowed_cpus'][0]);resource.setrlimit(resource.RLIMIT_CPU,(int(remaining),int(remaining)))
   env=dict(os.environ,_GRID_PREP_PARENT_PID=str(os.getpid()),PYTHONDONTWRITEBYTECODE='1',OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1',MKL_NUM_THREADS='1',NUMEXPR_NUM_THREADS='1',POLARS_MAX_THREADS='1')
   env.pop('PYTHONOPTIMIZE',None)
   with (out/'CASE_LOG.txt').open('x') as log:
    read_fd,write_fd=os.pipe();env['_GRID_PREP_CONTROLLER_FD']=str(read_fd)
    process=subprocess.Popen(cmd,stdout=log,stderr=subprocess.STDOUT,start_new_session=True,preexec_fn=limits,env=env,pass_fds=(read_fd,))
    os.close(read_fd);read_fd=None
    packet=json.dumps(controller_packet(args),sort_keys=True).encode()
    if len(packet)>=4096 or os.write(write_fd,packet)!=len(packet):raise ValueError('CONTROLLER_HANDOFF_WRITE_INCOMPLETE')
    os.close(write_fd);write_fd=None
    while process.poll() is None:
     rss=guard.process_rss(process.pid);peak=max(peak,rss);mem=guard.memory_observation()
     size=sum(p.stat().st_size for p in out.rglob('*') if p.is_file())+(requested.stat().st_size if args.command=='source-check' and requested.exists() else 0)
     if time.monotonic()-began>=CASE_SECONDS:stop='ORIGINAL_CASE600_WALL'
     elif rss>guard.WORKER_RSS_LIMIT:stop='ORIGINAL_DESCENDANT_RSS2GB'
     elif shutil.disk_usage(out).free<guard.DISK_RESERVE:stop='ORIGINAL_DISK15GIB'
     elif size>guard.CASE_LIMIT:stop='ORIGINAL_CASE250MB_OUTPUT'
     elif mem['host_used']>guard.HOST_USED_LIMIT or mem['SwapTotal'] or mem.get('cgroup_swap_current',0):stop='ORIGINAL_HOST_SWAP_GATE'
     elif mem.get('cgroup_limit_verified') and mem['cgroup_memory_current']>mem['cgroup_memory_max']:stop='ORIGINAL_CGROUP_MEMORY'
     if stop:break
     time.sleep(.1)
  except BaseException as exc:
   stop='LAUNCH_MONITOR_OR_ADMISSION_EXCEPTION';error=dict(type=type(exc).__name__,message=str(exc))
  finally:
   for descriptor in (read_fd,write_fd):
    if descriptor is not None:
     try:os.close(descriptor)
     except OSError:pass
   if process is not None:
    if process.poll() is None:
     try:os.killpg(process.pid,signal.SIGKILL)
     except ProcessLookupError:pass
    code=process.wait()
  try:
   size=sum(p.stat().st_size for p in out.rglob('*') if p.is_file())+(requested.stat().st_size if args.command=='source-check' and requested.exists() else 0)
   if size>guard.CASE_LIMIT:stop='ORIGINAL_CASE250MB_FINAL_OUTPUT'
  except OSError as exc:
   size=None;stop='FINAL_OUTPUT_OBSERVATION_EXCEPTION';error=dict(type=type(exc).__name__,message=str(exc))
  receipt=dict(status='FINISHED_FROM_START' if code==0 and stop is None else 'STOPPED_PRESERVED_INCOMPLETE_NO_RETRY',command=args.command,exit_code=code,resource_stop=stop,controller_error=error,wall_seconds=time.monotonic()-began,peak_descendant_RSS_bytes=peak,output_bytes_before_receipt=size,restore_supported=False,historical_wallets=0 if args.command=='source-check' else None,historical_risk_parity_certified=False)
  save(out/'DISPATCH_RECEIPT.json',receipt)
  return receipt

def main():
 p=argparse.ArgumentParser();sub=p.add_subparsers(dest='command',required=True)
 sub.add_parser('metadata')
 source=sub.add_parser('source-check');case=sub.add_parser('case')
 for q in (source,case):
  q.add_argument('--roots',required=True);q.add_argument('--year',type=int,choices=(2023,2024,2025),required=True);q.add_argument('--output',required=True)
  q.add_argument('--source-go');q.add_argument('--source-go-sha')
 case.add_argument('--arm',choices=('CSH','CASH','GRID'),required=True)
 for n in ('source-receipt','source-receipt-sha','case-go','case-go-sha'):case.add_argument('--'+n)
 for q in (source,case):
  for n in ('review','review-sha'):q.add_argument('--'+n)
  q.add_argument('--worker',action='store_true');q.add_argument('--remaining-seconds',default='595')
 a=p.parse_args()
 if a.command=='metadata':result=dict(status='METADATA_ONLY_NO_ARRAY_OR_WALLET',manifest=B.metadata_manifest(),remaining_gates=['independent_preparation_review','separate_source_only_GO','exact_target_covariance_source_projection','source_receipt','remote_resource_recovery','exact_one_case_GO'],historical_GO=False)
 else:result=worker(a) if a.worker else dispatch(a)
 print(json.dumps(result,indent=2,default=str));return 1 if result.get('status')=='STOPPED_PRESERVED_INCOMPLETE_NO_RETRY' else 0


