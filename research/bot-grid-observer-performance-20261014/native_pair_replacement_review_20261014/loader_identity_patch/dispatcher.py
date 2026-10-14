"""Future full-calendar dispatch; preparation exercises only miniature synthetic data."""
import argparse,json,sys,os,time,subprocess,resource,signal,hashlib,importlib.util,fcntl
from pathlib import Path
import v2_launcher as v
CASE_SECONDS=600;TOTAL_SECONDS=3600
RESOURCE_GUARD_SHA='b5e8a6ebd54e790066861da5c05d0c193175d965ceb75995779d70b2fe8c27a6'

def publication_identity(cache,commit):
 q=subprocess.run(['git','show',commit+':research/funding-rank-native-pair-v2-20261014/V2_FREEZE.json'],cwd=cache,capture_output=True)
 if q.returncode or q.stdout!=(v.HERE/'V2_FREEZE.json').read_bytes():raise v.GateError('EXACT_V2_PUBLICATION_COMMIT_REQUIRED')
 v.verify_publication_files()

def go_identity(path,expected_sha,commit,year,arm,completed):
 if path is None or expected_sha is None:raise v.GateError('PARENT_GO_REQUIRED_PRE_ACCOUNT')
 v.check(path,expected_sha);g=v.read(path)
 if g.get('schema')!='EXPLICIT_PARENT_V2_YEAR_PAIR_GO_V1' or g.get('publication_commit')!=commit or g.get('parent_GO') is not True or g.get('year')!=year or g.get('arms')!=['control','candidate']:raise v.GateError('EXACT_PARENT_GO_YEAR_ARMS')
 if arm=='candidate' and f'{year}_control' not in completed:raise v.GateError('CONTROL_FIRST')
 if f'{year}_{arm}' in completed:raise v.GateError('NO_REPEAT_CASE')
 if year not in (2023,2024,2025):raise v.GateError('FIXED_YEAR_SET')
 # Each later year requires its OWN exactly bound GO; no six-wallet sweep.
 return g

def original_resource_guard(roots):
 p=Path(roots['workspace'])/'coin_margin_protective_runner_20261013/run_guard_cases.py';v.check(p,RESOURCE_GUARD_SHA);spec=importlib.util.spec_from_file_location('v2_original_resource_only',p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m

def resource_admission(roots,output):
 guard=original_resource_guard(roots);r=guard.resource_admission(Path(output).parent,0)
 p=v.HERE/'original_resource_gate.py';v.check(p,'e29de5e816620fa86ada83c96fa3f57503f68f282fa4bd56292360d8c132d4ae');spec=importlib.util.spec_from_file_location('v2_exact_external_resource',p);external=importlib.util.module_from_spec(spec);spec.loader.exec_module(external)
 release=Path(roots['workspace'])/'coin_2021_strategy_comparison_20261013/GUARD_PACK_RELEASE.json';v.check(release,'05b51e5419fbf907910eae60ec08c18dd1a1a8e667b6c9b72d2bab3ef913b60b');task=external.task_reservation(release);observation=external.external_observation();observation.update(task);packs=observation['guard_pack_processes'];observation['external_reserved_bytes']=max(task['task_reserved_bytes'],len(packs)*external.PACK_RESERVED_BYTES);observation['external_busy_cpus']=sorted(set(task['task_busy_cpus'])|{cpu for row in packs for cpu in row['allowed_cpus']});r=external.check_external(r,observation,0,guard)
 # Exact original host/swap/cgroup/disk reservation/2CPU rules above remain unchanged.
 for d in Path('/proc').iterdir():
  if not d.name.isdigit() or int(d.name)==os.getpid():continue
  try:args=(d/'cmdline').read_bytes().decode().split('\0')
  except (OSError,UnicodeError):continue
  if any(a.endswith(('run_guard_cases.py','run_cases.py','resume_cases.py','pack_minimal_guard.py','verify_restored_native.py','dispatcher.py')) for a in args):raise v.GateError('OTHER_FINANCIAL_OR_PACK_PROCESS_ACTIVE')
 return r

def save_json(p,obj):
 with Path(p).open('x') as f:json.dump(obj,f,sort_keys=True,indent=2,allow_nan=False);f.write('\n')

def calendar_loop(sim,port,out,binding,deadline):
 """Shared actual dispatch loop. Source may only be real after all caller gates.
 Synthetic tests exercise this exact chronological loop/checkpoint/output path.
 """
 out=Path(out);out.mkdir(parents=True,exist_ok=False);recovery=out/'checkpoint';daily=[];reason=None
 port.checkpoint(recovery,sim,binding)
 while sim.cursor<sim.end and sim.stop is None:
  if time.monotonic()>=deadline-20:reason='RESOURCE_STOP_PARTIAL_NOT_PAID';break
  daily.append(sim.advance_day())
  # Safe complete-day checkpoints; final halt also captured. No replay/automatic resume.
  if len(daily)%7==0 or sim.stop is not None or sim.cursor>=sim.end:port.checkpoint(recovery,sim,binding)
 pointer=port.checkpoint(recovery,sim,binding);result=sim.result();summary=result['summary'];full=summary['completed_minutes']==summary['required_minutes'];flat=summary['terminal_cash_realized'];halt=summary['stop_us'] is not None
 status='PAID_FLAT' if full and flat and not halt else 'HALTED_MARKED' if halt else 'FULL_MARKED_WITH_RESIDUAL' if full else reason or 'PARTIAL_MARKED'
 cash=sim.account.nav() if status=='PAID_FLAT' else None
 summary.update(dispatch_status=status,paid_NAV_decimal=str(cash) if cash is not None else None,marked_NAV_decimal=str(sim.account.nav()),residual_quantities_decimal={s:str(sim.account.positions[s].quantity) for s in sim.symbols},transport_stop_reason=reason)
 save_json(out/'SUMMARY.json',summary);save_json(out/'FILLS.json',result['trades']);save_json(out/'FUNDING.json',result['funding']);save_json(out/'REJECTIONS.json',result['rejections']);save_json(out/'DAILY.json',daily);save_json(out/'BINDING.json',binding)
 # Full original checkpoint retains lossless all-minute chunks and Decimal account state.
 result['targets'].write_parquet(out/'TARGET_ROWS.parquet');result['minute'].write_parquet(out/'MINUTE_FINANCE.parquet');save_json(out/'AUDIT.json',{'breaches':result['breaches'],'extrema':result['extrema']})
 return {'status':status,'summary':summary,'pointer':pointer}

def worker_case(args):
 if os.environ.get('_V2_PARENT_PID')!=str(os.getppid()) or len(os.sched_getaffinity(0))!=1 or resource.getrlimit(resource.RLIMIT_AS)[0]>4000000000 or resource.getrlimit(resource.RLIMIT_CPU)[0]>600:raise v.GateError('BOUNDED_PARENT_CONTROLLER_REQUIRED_PRE_ACCOUNT')
 roots=v.read(args.roots);publication_identity(roots['publication_repo'],args.publication_commit);v.verify_financial(roots);v.require_review(args.review,args.review_sha,args.publication_commit)
 completed=v.read(args.completed)['completed'] if args.completed else []
 go_identity(args.parent_go_receipt,args.parent_go_sha,args.publication_commit,args.year,args.arm,completed)
 bound=v.bind_saved_targets(args.year,roots['targets']);window=v.source_window(args.year,roots['source'+str(args.year)],roots.get('derived_csv'));port,account,cls=v.load_engine(roots)
 # Repeat exact factory validation before original native account creation; unchanged finance.
 sim=cls(window,'LONG_SHORT',port.native.COSTS[0],port.native.UNITS[0],target_factory=v.exact_factory(bound,args.arm,port.native.pl),account_factory=account)
 binding={'publication_commit':args.publication_commit,'V2_FREEZE_SHA256':v.sha(v.HERE/'V2_FREEZE.json'),'year':args.year,'arm':args.arm,'review_SHA256':args.review_sha,'parent_GO_SHA256':args.parent_go_sha,'source_index_SHA256':v.inp.registry()['years'][str(args.year)]['index']['SHA256'],'target_archive_SHA256':v.read(v.HERE/'TARGET_REMOTE_BINDING.json')['files'][f'Y{args.year}_TARGETS.npz']['SHA256']}
 return calendar_loop(sim,port,Path(args.output)/f'{args.year}_{args.arm}',binding,time.monotonic()+max(0,float(args.remaining_seconds)-5))

def dispatch(args):
 start=time.monotonic();roots=v.read(args.roots);publication_identity(roots['publication_repo'],args.publication_commit);v.verify_financial(roots);v.require_review(args.review,args.review_sha,args.publication_commit)
 out=Path(args.output);ledger_path=out/'CASE_LEDGER.json';ledger=v.read(ledger_path) if ledger_path.exists() else {'attempts':{},'completed':[],'elapsed_seconds':0.0,'publication_commit':args.publication_commit}
 if ledger.get('publication_commit')!=args.publication_commit:raise v.GateError('LEDGER_PUBLICATION_IDENTITY')
 if args.year>2023 and not {'2023_control','2023_candidate'}<=set(ledger['completed']):raise v.GateError('FIRST_YEAR2023_PAIR_REQUIRED')
 if args.year>2024 and not {'2024_control','2024_candidate'}<=set(ledger['completed']):raise v.GateError('FIXED2024_PAIR_BEFORE2025')
 go_identity(args.parent_go_receipt,args.parent_go_sha,args.publication_commit,args.year,args.arm,ledger['completed']);key=f'{args.year}_{args.arm}'
 if key in ledger['attempts'] or (out/key).exists():raise v.GateError('NO_SILENT_RERUN_OR_CHECKPOINT_OVERWRITE')
 # Read-only source/target preflight plus original resource safeguards before account child.
 v.bind_saved_targets(args.year,roots['targets']);v.source_window(args.year,roots['source'+str(args.year)],roots.get('derived_csv'));resource_info=resource_admission(roots,out)
 if ledger['elapsed_seconds']+time.monotonic()-start>=TOTAL_SECONDS:raise v.GateError('FIXED_AGGREGATE3600_EXHAUSTED')
 with Path('/tmp/coin_offline_financial_controller.lock').open('a') as lock:
  try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
  except BlockingIOError:raise v.GateError('OTHER_FINANCIAL_CONTROLLER_LOCKED')
  out.mkdir(parents=True,exist_ok=True);ledger['attempts'][key]={'status':'STARTED_NO_RETRY'};ledger_path.write_text(json.dumps(ledger,indent=2));completed_path=out/'COMPLETED_INPUT.json';completed_path.write_text(json.dumps({'completed':ledger['completed']}))
  elapsed=time.monotonic()-start;remaining=min(CASE_SECONDS-elapsed,TOTAL_SECONDS-ledger['elapsed_seconds']-elapsed)
  if remaining<=20:raise v.GateError('CASE600_ADMISSION_BUDGET_EXHAUSTED')
  def limits():
   os.sched_setaffinity(0,{resource_info['allowed_cpus'][0]});resource.setrlimit(resource.RLIMIT_AS,(4000000000,4000000000));resource.setrlimit(resource.RLIMIT_CPU,(int(remaining),int(remaining)))
  cmd=[sys.executable,'-B',str(v.HERE/'dispatcher.py'),'--worker','--roots',args.roots,'--year',str(args.year),'--arm',args.arm,'--output',args.output,'--publication-commit',args.publication_commit,'--review',args.review,'--review-sha',args.review_sha,'--parent-go-receipt',args.parent_go_receipt,'--parent-go-sha',args.parent_go_sha,'--completed',str(completed_path),'--remaining-seconds',str(remaining)]
  log=(out/f'{key}.log').open('x');p=subprocess.Popen(cmd,stdout=log,stderr=subprocess.STDOUT,start_new_session=True,preexec_fn=limits,env=dict(os.environ,_V2_PARENT_PID=str(os.getpid()),PYTHONDONTWRITEBYTECODE='1',OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1',POLARS_MAX_THREADS='1'));guard=original_resource_guard(roots);stop=None
  while p.poll() is None:
   if time.monotonic()-start>=CASE_SECONDS or ledger['elapsed_seconds']+time.monotonic()-start>=TOTAL_SECONDS:stop='HARD_WALL_BUDGET'
   elif guard.process_rss(p.pid)>2000000000:stop='DESCENDANT_RSS2GB'
   elif __import__('shutil').disk_usage(out).free<guard.DISK_RESERVE:stop='DISK15GIB'
   elif sum(q.stat().st_size for q in (out/key).rglob('*') if q.is_file())>guard.CASE_LIMIT:stop='ORIGINAL_CASE250MB_OUTPUT_CAP'
   mem=guard.memory_observation()
   if mem['host_used']>guard.HOST_USED_LIMIT or mem['SwapTotal'] or mem.get('cgroup_swap_current',0):stop='HOST_SWAP_RESOURCE_GATE'
   if mem.get('cgroup_limit_verified') and mem['cgroup_memory_current']>mem['cgroup_memory_max']:stop='CGROUP_MEMORY'
   if stop:os.killpg(p.pid,signal.SIGKILL);p.wait();break
   time.sleep(.05)
  log.close();duration=time.monotonic()-start;ledger['elapsed_seconds']+=duration;ledger['attempts'][key]={'exit_code':p.returncode,'stop':stop,'elapsed_seconds':duration,'status':'PRESERVED_PARTIAL_OR_TERMINAL_NO_RETRY'}
  if p.returncode==0 and (out/key/'SUMMARY.json').exists() and v.read(out/key/'SUMMARY.json').get('transport_stop_reason') is None:ledger['completed'].append(key)
  ledger_path.write_text(json.dumps(ledger,indent=2));return ledger['attempts'][key]

def dispatch_synthetic(roots,window,bound,arm,out):
 # Exercises exactly calendar_loop, checkpoint and complete outputs on tiny fixture only.
 sim=v.construct_synthetic(roots,window,bound,arm);port,_,_=v.load_engine(roots)
 return calendar_loop(sim,port,out,{'fixture':'PURE_SYNTHETIC_CONSTANT_QUOTES','arm':arm},time.monotonic()+60)

def main():
 p=argparse.ArgumentParser();p.add_argument('--roots',required=True);p.add_argument('--year',type=int,choices=(2023,2024,2025),required=True);p.add_argument('--arm',choices=('control','candidate'),required=True);p.add_argument('--output',required=True);p.add_argument('--publication-commit',required=True);p.add_argument('--review');p.add_argument('--review-sha');p.add_argument('--parent-go-receipt');p.add_argument('--parent-go-sha');p.add_argument('--worker',action='store_true');p.add_argument('--completed');p.add_argument('--remaining-seconds',default='600');a=p.parse_args()
 print(json.dumps(worker_case(a) if a.worker else dispatch(a),default=str));return 0
if __name__=='__main__':raise SystemExit(main())
