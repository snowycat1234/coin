"""Bounded generated-only account tests; explicit dependency pins before import."""
import os,sys,time,datetime,resource,signal,pathlib,json,hashlib,unittest,traceback
P=pathlib.Path;HERE=P(__file__).parent;OUT=HERE/'synthetic_attempt004';assert not OUT.exists();OUT.mkdir();START=datetime.datetime.now(datetime.timezone.utc);BEG=time.monotonic();DEAD=datetime.datetime.fromisoformat('2026-10-14T18:27:13.440429+00:00');REMAIN=(DEAD-START).total_seconds();assert REMAIN>0;os.sched_setaffinity(0,{min(os.sched_getaffinity(0))})
for k,v in [(resource.RLIMIT_CPU,int(REMAIN)),(resource.RLIMIT_AS,4000000000),(resource.RLIMIT_FSIZE,25000000)]:resource.setrlimit(k,(v,v))
def bounds(*a):
 if time.monotonic()-BEG>=REMAIN:raise TimeoutError('WALL120')
 if resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024>2000000000:raise MemoryError('RSS2GB')
 if sum(p.stat().st_size for p in OUT.rglob('*') if p.is_file())>25000000:raise OSError('OUTPUT25MB')
signal.signal(signal.SIGALRM,bounds);signal.setitimer(signal.ITIMER_REAL,.1,.1);r={'PID':os.getpid(),'start_UTC':START.isoformat(),'deadline_UTC':DEAD.isoformat(),'historical_GO':False};print('SYNTHETIC_START',json.dumps(r),flush=True)
def sha(b):return hashlib.sha256(b).hexdigest()
rc=1
try:
 mf=json.loads((HERE/'FREEZE.json').read_bytes())
 for name,v in mf['files'].items():b=(HERE/name).read_bytes();assert len(b)==v['bytes'] and sha(b)==v['SHA256']
 root=P('/workspace/coin-cloud/h090-original2023-code-20261014');deps=json.loads((HERE/'DEPENDENCIES.json').read_bytes())
 for name,v in deps['files'].items():b=(root/name).read_bytes();assert len(b)==v['bytes'] and sha(b)==v['SHA256']
 for k in ['PYTHONOPTIMIZE','PYTHONPATH','PYTHONHOME','PYTHONSTARTUP']:os.environ.pop(k,None)
 for k in ['OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS','POLARS_MAX_THREADS']:os.environ[k]='1'
 sites=json.loads((root.parent/'grid-original-source-2023-20261014/BOT_NATIVE_RUNTIME_SITES.json').read_bytes());sys.path[:0]=[str(HERE),*sites,str(root/'native_pair_replacement_review_20261014/synthetic_dependencies_ca11e94d/fine'),str(root/'native_pair_replacement_review_20261014/synthetic_dependencies_ca11e94d/repo'),str(root/'native_pair_replacement_review_20261014/synthetic_dependencies_ca11e94d/repo/src')]
 import test_synthetic
 names=['test_synthetic.Tests.'+x for x in sorted(n for n in vars(test_synthetic.Tests) if n.startswith('test_'))];suite=unittest.defaultTestLoader.loadTestsFromNames(names)
 with (OUT/'TEST_LOG.txt').open('x') as log:result=unittest.TextTestRunner(stream=log,verbosity=2,failfast=True).run(suite)
 r.update(tests_run=result.testsRun,errors=[{'test':str(t),'traceback':s} for t,s in result.errors],failures=[{'test':str(t),'traceback':s} for t,s in result.failures],fixed_nodes=names,status='PASS_SYNTHETIC_NATIVE_PREVIEW_ONLY' if result.wasSuccessful() else 'FAILED_PRESERVED');rc=0 if result.wasSuccessful() else 1
except BaseException as e:r.update(status='FAILED_PRESERVED',error=repr(e),traceback=traceback.format_exc())
signal.setitimer(signal.ITIMER_REAL,0);u=resource.getrusage(resource.RUSAGE_SELF);r['resource']={'exit':rc,'wall_seconds':time.monotonic()-BEG,'CPU_seconds':u.ru_utime+u.ru_stime,'peak_RSS_bytes':u.ru_maxrss*1024,'end_UTC':datetime.datetime.now(datetime.timezone.utc).isoformat()};r['files']={p.name:{'bytes':p.stat().st_size,'SHA256':sha(p.read_bytes())} for p in OUT.iterdir() if p.is_file()};(OUT/'TEST_RECEIPT.json').write_text(json.dumps(r,indent=2)+'\n');print('SYNTHETIC_TERMINAL',json.dumps(r));sys.exit(rc)
