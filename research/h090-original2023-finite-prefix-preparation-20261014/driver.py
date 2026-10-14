"""Single original2023 arm dispatch; no sweep, source retry or recovery."""
from pathlib import Path
import argparse,fcntl,json,math,os,resource,select,shutil,signal,stat,subprocess,sys,time
if __name__=='__main__':raise SystemExit('USE_ISOLATED_RUN_VERIFIED')
from verified_source import require_runtime
require_runtime()
import bridge_bindings as B
CASE_SECONDS=600

def save(path,obj):
 with Path(path).open('x') as f:json.dump(obj,f,indent=2,sort_keys=True,allow_nan=False);f.write('\n')

def case_gates(args):return B.case_gate(args)
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

def dispatch(args):
 # Same bounded controller for a source-only projection and one financial case.
 if args.command!='case':raise ValueError('ONE_CASE_ONLY_NO_SOURCE_RETRY_OR_SWEEP')
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
   cmd=[sys.executable,'-I','-S','-B',str(B.HERE/'run_verified.py'),'--preparation-manifest-sha',B.sha(B.HERE/'PREPARATION_MANIFEST.json'),args.command,'--worker','--remaining-seconds',args.remaining_seconds]
   keys=['roots','year','output','source_go','source_go_sha','review','review_sha']
   if args.command=='case':keys+=['arm','source_receipt','source_receipt_sha','case_go','case_go_sha']
   if args.arm=='FINITE':keys+=['completed_control_evidence','completed_control_evidence_sha']
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

def worker(args):
 bounded_worker_guard(args);B.require_original200_source_quality();B.case_gate(args)
 from project_inputs import source_only
 from grid_driver import compare_source_receipt
 # A case GO covers one fresh wallet and its revalidation of the exact original
 # source. There is no source-check command or standalone projection retry.
 admitted,computed=source_only(B.read(args.roots),B.YEAR,args.source_go,args.source_go_sha)
 computed['roots_SHA256']=B.sha(args.roots)
 normalized=compare_source_receipt(computed,args)
 if normalized!=B.read(args.source_receipt):raise ValueError('EXACT_SAVED_ORIGINAL_SOURCE_RECEIPT_REQUIRED')
 from original_bridge import make_sim
 from export_evidence import run_calendar
 sim=make_sim(admitted,args.arm,case_args=args)
 binding=dict(schema='H090_ORIGINAL2023_ACTUAL_CASE_BINDING_V1',year=B.YEAR,arm=args.arm,
  preparation_manifest_SHA256=B.sha(B.HERE/'PREPARATION_MANIFEST.json'),finite_source_SHA256=B.FINITE_SHA,
  CONTROL_source_SHA256=B.CONTROL_SHA,finite_public_commit=B.FINITE_COMMIT,CONTROL_public_commit=B.CONTROL_COMMIT,
  source_receipt_SHA256=B.SOURCE_SHA,source_GO_SHA256=B.SOURCE_GO_SHA,roots_SHA256=B.ROOTS_SHA,
  parent_case_GO_SHA256=args.case_go_sha,review_SHA256=args.review_sha,
  source_projection=normalized,source_scope=sim.bridge_source_scope,original200_source_quality=sim.source_registry.identity()['original200_source_quality'],generated=False,
  target_field='STATIC50_UNLAGGED',rank_feature_lag_hours=0,initial_cash='10000',cost='BASE27',funding_unit='RAW_AS_FRACTION',
  financial_account_count=1,owner_cash_wallet_count=0,restore_supported=False,
  runtime_packages=require_runtime().runtime_packages,source_audit=require_runtime().audit())
 return run_calendar(sim,Path(args.output)/'final_evidence',binding,time.monotonic()+float(args.remaining_seconds),
  'PINNED_ORIGINAL2023_SEEN_DEVELOPMENT_ROOT_GO_ONE_ARM')

def main():
 p=argparse.ArgumentParser();sub=p.add_subparsers(dest='command',required=True);sub.add_parser('metadata');q=sub.add_parser('case')
 q.add_argument('--year',type=int,choices=(2023,),required=True);q.add_argument('--arm',choices=B.ARMS,required=True)
 for key in ('roots','source-go','source-go-sha','source-receipt','source-receipt-sha','case-go','case-go-sha','review','review-sha','output'):q.add_argument('--'+key,required=True)
 q.add_argument('--completed-control-evidence');q.add_argument('--completed-control-evidence-sha')
 q.add_argument('--worker',action='store_true');q.add_argument('--remaining-seconds',default='595');a=p.parse_args()
 result=B.metadata() if a.command=='metadata' else worker(a) if a.worker else dispatch(a)
 print(json.dumps(result,sort_keys=True,indent=2,default=str));return int(result.get('status')=='STOPPED_PRESERVED_INCOMPLETE_NO_RETRY')
