"""One bounded generated-only check; no historical admission or public IO."""
from pathlib import Path
import argparse,hashlib,json,os,resource,signal,subprocess,sys,time
HERE=Path(__file__).resolve().parent
ARRAY_SUFFIXES=('.npz','.npy','.parquet','.arrow','.csv')

def pristine_wrappers():
    if any(p.name=='__pycache__' or p.suffix=='.pyc' for p in HERE.rglob('*')):
        raise ValueError('GENERATED_WRAPPER_UNBOUND_CACHE_REFUSED')

def child():
    pristine_wrappers()
    denied=[];opened=[]
    def audit(event,args):
        if event=='open' and args and isinstance(args[0],(str,bytes)):
            path=os.fsdecode(args[0]);opened.append(path)
            if path.lower().endswith(ARRAY_SUFFIXES):
                denied.append(path);raise PermissionError('GENERATED_CHECK_REFUSES_ARRAY_FILE:'+path)
        if event in ('socket.connect','socket.getaddrinfo','subprocess.Popen'):
            raise PermissionError('GENERATED_CHILD_REFUSES_NETWORK_OR_SUBPROCESS')
    sys.addaudithook(audit)
    sys.path.insert(0,str(HERE))
    import unittest
    import test_generated
    suite=unittest.defaultTestLoader.loadTestsFromModule(test_generated)
    result=unittest.TextTestRunner(verbosity=2).run(suite)
    if result.wasSuccessful():
        pristine_wrappers()
        from export_generated_witness import build
        target=Path(os.environ['PAIRED_GENERATED_RECEIPT_DIR'])/'GENERATED_PRIORITY_WITNESS.json'
        if target.exists():raise ValueError('FRESH_WITNESS_REQUIRED')
        target.write_text(json.dumps(build(),sort_keys=True,indent=2,default=str,allow_nan=False)+'\n')
    print(json.dumps(dict(schema='GENERATED_READ_AUDIT_V1',array_open_attempts=len(denied),
        array_files_opened=0,historical_wallets=0,tests=result.testsRun,
        failures=len(result.failures),errors=len(result.errors),
        source_and_runtime_files_opened=len(opened)),sort_keys=True))
    return 0 if result.wasSuccessful() else 1

def limit_child():
    os.sched_setaffinity(0,{min(os.sched_getaffinity(0))})
    resource.setrlimit(resource.RLIMIT_AS,(4_000_000_000,4_000_000_000))
    resource.setrlimit(resource.RLIMIT_CPU,(120,120))

def rss_bytes(pid):
    try:
        status=Path(f'/proc/{pid}/status').read_text()
        return int(next(x.split()[1] for x in status.splitlines() if x.startswith('VmRSS:')))*1024
    except (OSError,StopIteration):return 0

def main():
    p=argparse.ArgumentParser();p.add_argument('--child',action='store_true');p.add_argument('--output',type=Path)
    a=p.parse_args()
    if a.child:return child()
    if a.output is None:raise ValueError('FRESH_LOCAL_RECEIPT_DIRECTORY_REQUIRED')
    pristine_wrappers()
    out=a.output.resolve()
    if not out.is_relative_to(HERE):raise ValueError('ISOLATED_LOCAL_RECEIPTS_ONLY')
    out.mkdir(exist_ok=False)
    env=dict(os.environ,PAIRED_GENERATED_RECEIPT_DIR=str(out),PYTHONDONTWRITEBYTECODE='1',POLARS_MAX_THREADS='1',OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1')
    start=time.monotonic();peak=0;failure=None
    with (out/'unit_tests.txt').open('wb') as log:
        proc=subprocess.Popen([sys.executable,'-B',str(HERE/'run_generated_checks.py'),'--child'],
            env=env,stdout=log,stderr=subprocess.STDOUT,start_new_session=True,preexec_fn=limit_child)
        while proc.poll() is None:
            peak=max(peak,rss_bytes(proc.pid))
            if time.monotonic()-start>120 or peak>2_000_000_000:
                failure='WALL_LIMIT' if time.monotonic()-start>120 else 'RSS_LIMIT'
                os.killpg(proc.pid,signal.SIGKILL);break
            time.sleep(.1)
        code=proc.wait()
    usage=resource.getrusage(resource.RUSAGE_CHILDREN)
    log=(out/'unit_tests.txt').read_text()
    report=dict(schema='PAIRED_HEADROOM_GENERATED_BOUND_RECEIPT_V1',
        status='PASS_GENERATED_ONLY' if code==0 and failure is None else 'FAIL_PRESERVED',
        returncode=code,limit_stop=failure,wall_seconds=time.monotonic()-start,
        child_maxrss_KiB=usage.ru_maxrss,peak_sampled_RSS_bytes=peak,
        child_CPU_seconds=usage.ru_utime+usage.ru_stime,CPU_workers=1,
        resource_limits=dict(wall_seconds=120,CPU_seconds=120,RSS_bytes=2_000_000_000,AS_bytes=4_000_000_000),
        GPU=0,historical_arrays_opened=0,historical_wallets=0,public_writes=0,
        tests_log_SHA256=hashlib.sha256(log.encode()).hexdigest(),
        generated_witness_SHA256=hashlib.sha256((out/'GENERATED_PRIORITY_WITNESS.json').read_bytes()).hexdigest() if (out/'GENERATED_PRIORITY_WITNESS.json').exists() else None)
    (out/'RESOURCE_RECEIPT.json').write_text(json.dumps(report,indent=2)+'\n')
    print(log);print(json.dumps(report,indent=2));return code

if __name__=='__main__':raise SystemExit(main())
