"""Exactly one bounded child launch, generated-only; never retries failures."""
from pathlib import Path
from datetime import datetime, timedelta, timezone
import fcntl, hashlib, json, os, resource, signal, subprocess, sys, time, traceback, types
ROOT=Path(__file__).resolve().parent.parent;BASE=Path(__file__).resolve().parent
assert len(sys.argv)==3 and sys.argv[2]=='ROOT_GENERATED_GO_RECORDED'
MODE='finite_prefix_generated';FREEZE_PIN=sys.argv[1]
OUT=BASE/'generated_finite_prefix_attempt001'
LIMITS=dict(wall_seconds=150,CPU_seconds=120,RSS_bytes=2000000000,AS_bytes=4000000000,output_bytes=25000000,CPUs=1,math_threads=1)
INSTRUCTION='Implementation and plan only: execution requires separate root GO after independent frozen-source/lineage review. One targeted generated OriginalFiniteCandidate baseline versus prefix finite parity, complete owner/account/native outputs, same150wall120CPU2GB4GB25MB oneCPU. No history, broad86suite, publication or automatic retry.'
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def save(name,value):
    with (OUT/name).open('x') as stream:json.dump(value,stream,indent=2,sort_keys=True,allow_nan=False);stream.write('\n')
assert sha(BASE/'PREPARATION_MANIFEST.json')==FREEZE_PIN
freeze=json.loads((BASE/'PREPARATION_MANIFEST.json').read_text())
for name,want in freeze['files'].items():assert sha(BASE/name)==want['SHA256'] and (BASE/name).stat().st_size==want['bytes']
OUT.mkdir()
save('ROOT_GO.json',{'root_instruction':INSTRUCTION,'mode':MODE,'preparation_manifest_SHA256':FREEZE_PIN,'limits':LIMITS,'no_automatic_retries':True,'historical_arrays_accounts_allowed':False,'known_public_checksum_only_NPZ_files':2,'known_public_checksum_only_NPZ_bytes':50586})
worker=BASE/'test_finite_prefix_worker.py'
save('EXTERNAL_HARNESS_PINS.json',{'worker_SHA256':sha(worker),'controller_SHA256':sha(Path(__file__)),'preparation_manifest_SHA256':FREEZE_PIN})
guard_path=ROOT/'native_pair_replacement_review_20261014/synthetic_dependencies_ca11e94d/workspace/coin_margin_protective_runner_20261013/run_guard_cases.py'
child=None;stop=None;peak=0;code=None;began=time.monotonic()
try:
    raw=guard_path.read_bytes();assert hashlib.sha256(raw).hexdigest()=='b5e8a6ebd54e790066861da5c05d0c193175d965ceb75995779d70b2fe8c27a6'
    guard=types.ModuleType('original_bounded_guard');guard.__file__=str(guard_path);exec(compile(raw,str(guard_path),'exec'),guard.__dict__)
    with Path('/tmp/coin_grid_generated_test_controller.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        admission=guard.resource_admission(OUT,0);save('RESOURCE_ADMISSION.json',admission)
        def limits():
            guard.child_limits(admission['allowed_cpus'][0])
            for kind,cap in ((resource.RLIMIT_CPU,120),(resource.RLIMIT_AS,4000000000),(resource.RLIMIT_RSS,2000000000),(resource.RLIMIT_FSIZE,25000000)):resource.setrlimit(kind,(cap,cap))
        sites=['/opt/codex/runtimes/codex-primary-runtime/dependencies/python/lib/python3.12/site-packages',str(ROOT/'native_pair_replacement_review_20261014/site'),str(ROOT/'coin_funding_rank_dependencies_20261013/site')]
        env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1',MKL_NUM_THREADS='1',NUMEXPR_NUM_THREADS='1',POLARS_MAX_THREADS='1',VECLIB_MAXIMUM_THREADS='1',BLIS_NUM_THREADS='1',BOT_NATIVE_RUNTIME_SITES=json.dumps(sites))
        for name in ('PYTHONOPTIMIZE','PYTHONPATH','PYTHONHOME','PYTHONSTARTUP'):env.pop(name,None)
        began=time.monotonic()
        with (OUT/'WORKER_LOG.txt').open('x') as log:
            child=subprocess.Popen([sys.executable,'-I','-S','-B',str(worker),FREEZE_PIN],stdout=log,stderr=subprocess.STDOUT,start_new_session=True,preexec_fn=limits,env=env)
            launched=datetime.now(timezone.utc);launch={'PID':child.pid,'start_UTC':launched.isoformat(),'deadline_UTC':(launched+timedelta(seconds=150)).isoformat(),'worker_launch_number':1};save('LAUNCH.json',launch);print(json.dumps(launch),flush=True)
            while child.poll() is None:
                peak=max(peak,guard.process_rss(child.pid));memory=guard.memory_observation();output=sum(p.stat().st_size for p in OUT.rglob('*') if p.is_file())
                if time.monotonic()-began>150:stop='WALL150'
                elif peak>2000000000:stop='RSS2GB'
                elif memory['host_used']>guard.HOST_USED_LIMIT or memory['SwapTotal'] or memory.get('cgroup_swap_current',0):stop='HOST_SWAP'
                elif output>25000000:stop='OUTPUT25MB'
                if stop:break
                time.sleep(.05)
except BaseException as error:
    stop='CONTROLLER_OR_ADMISSION_FAILURE';save('CONTROLLER_FAILURE.json',{'error':repr(error),'traceback':traceback.format_exc(),'automatic_retries':0})
finally:
    if child is not None:
        if child.poll() is None:os.killpg(child.pid,signal.SIGKILL)
        code=child.wait()
    files={str(p.relative_to(OUT)):{'SHA256':sha(p),'bytes':p.stat().st_size} for p in sorted(OUT.rglob('*')) if p.is_file()}
    result=json.loads((OUT/'RESULT.json').read_text()) if (OUT/'RESULT.json').exists() else None
    status='PASS' if code==0 and stop is None and result and result['status']=='PASS' else 'FAILED_NO_RETRY'
    receipt={'schema':'H090_ORIGINAL_FINITE_PREFIX_BOUNDED_PARITY_RECEIPT_V1','status':status,'mode':MODE,'worker_launches':int(child is not None),'automatic_retries':0,'exit_code':code,'resource_stop':stop,'limits':LIMITS,'wall_seconds':time.monotonic()-began,'monitored_peak_RSS_bytes':peak,'worker_peak_RSS_bytes':result['peak_RSS_bytes'] if result else None,'worker_CPU_seconds':result['CPU_seconds'] if result else None,'saved_output_bytes_before_receipt':sum(row['bytes'] for row in files.values()),'preparation_manifest_SHA256':sha(BASE/'PREPARATION_MANIFEST.json'),'preparation_manifest_unchanged':sha(BASE/'PREPARATION_MANIFEST.json')==FREEZE_PIN,'files':files,'historical_arrays_parsed':0,'historical_account_states_imported':0,'known_public_checksum_only_NPZ_distinct_files':2,'known_public_checksum_only_NPZ_distinct_bytes':50586,'financial_methods_changed':False,'economic_policy_changed':False}
    save('BOUNDED_RECEIPT.json',receipt);print(json.dumps({k:v for k,v in receipt.items() if k!='files'},sort_keys=True))
    assert sum(p.stat().st_size for p in OUT.rglob('*') if p.is_file())<=25000000
sys.exit(0 if status=='PASS' else 1)
