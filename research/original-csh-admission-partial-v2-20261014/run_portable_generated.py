"""Fresh explicitly authorized synthetic stage; no history or network."""
import os,sys,time,datetime,resource,signal,pathlib,json,hashlib,unittest,traceback
assert os.environ.get('ROOT_GENERATED_TEST_GO')=='REVIEWED_GENERATED_ONLY', 'SEPARATE_GENERATED_TEST_GO_REQUIRED'
import argparse,sysconfig
ap=argparse.ArgumentParser();ap.add_argument('--code-root',required=True);ap.add_argument('--output',required=True);ap.add_argument('--runtime-sites-json');args=ap.parse_args();os.environ['ORIGINAL_CSH_CODE_ROOT']=args.code_root;os.environ['GENERATED_TEST_OUTPUT']=args.output
assert sys.version_info[:3]==(3,12,14) and sys.flags.isolated and sys.flags.no_site and sys.flags.dont_write_bytecode and not sys.flags.optimize
P=pathlib.Path;HERE=P(__file__).parent;OUT=P(os.environ['GENERATED_TEST_OUTPUT']);assert not OUT.exists();OUT.mkdir();START=datetime.datetime.now(datetime.timezone.utc);BEG=time.monotonic();DEAD=START+datetime.timedelta(seconds=120);REMAIN=120;os.sched_setaffinity(0,{min(os.sched_getaffinity(0))})
for k,v in [(resource.RLIMIT_CPU,int(REMAIN)),(resource.RLIMIT_AS,4000000000),(resource.RLIMIT_FSIZE,25000000)]:resource.setrlimit(k,(v,v))
def bounds(*a):
 if time.monotonic()-BEG>=REMAIN:raise TimeoutError('WALL120')
 if resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024>2000000000:raise MemoryError('RSS2GB')
 if sum(p.stat().st_size for p in OUT.rglob('*') if p.is_file())>25000000:raise OSError('OUTPUT25MB')
signal.signal(signal.SIGALRM,bounds);signal.setitimer(signal.ITIMER_REAL,.1,.1);r={'PID':os.getpid(),'start_UTC':START.isoformat(),'deadline_UTC':DEAD.isoformat(),'historical_GO':False};print('V2_SYNTHETIC_START',json.dumps(r),flush=True)
def sha(b):return hashlib.sha256(b).hexdigest()
rc=1
try:
 mf=json.loads((HERE/'FREEZE.json').read_bytes())
 for name,v in mf['files'].items():b=(HERE/name).read_bytes();assert len(b)==v['bytes'] and sha(b)==v['SHA256']
 root=P(os.environ.get('ORIGINAL_CSH_CODE_ROOT','/workspace/coin-cloud/h090-original2023-code-20261014'));deps=json.loads((HERE/'DEPENDENCIES.json').read_bytes())
 for name,v in deps['files'].items():b=(root/name).read_bytes();assert len(b)==v['bytes'] and sha(b)==v['SHA256']
 for k in ['PYTHONOPTIMIZE','PYTHONPATH','PYTHONHOME','PYTHONSTARTUP']:os.environ.pop(k,None)
 for k in ['OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS','POLARS_MAX_THREADS']:os.environ[k]='1'
 sites=json.loads(args.runtime_sites_json) if args.runtime_sites_json else list(dict.fromkeys([sysconfig.get_path('purelib'),sysconfig.get_path('platlib')]));assert sites and all(P(x).is_absolute() and P(x).is_dir() for x in sites);repo=root/'native_pair_replacement_review_20261014/synthetic_dependencies_ca11e94d/repo';fine=root/'native_pair_replacement_review_20261014/synthetic_dependencies_ca11e94d/fine';sys.path[:0]=[str(HERE),*sites,str(fine),str(repo),str(repo/'src')]
 import numpy,polars,pyarrow
 assert (numpy.__version__,polars.__version__,pyarrow.__version__)==('2.3.5','1.44.2','23.0.1')
 # Reuse ONLY the exact accepted generated bootstrap function, not its suite.
 import ast,types,importlib
 base=root/'coin_h090_original2023_finite_prefix_bridge_20261014';PIN='0d44cc01c0ea09274996ebe886a93536e6376ccbca6ca83f31d35b57354e2efc'
 body=(base/'test_finite_prefix_worker.py').read_bytes();assert sha(body)=='27bbafa608663e37af42531b1e7de31cc501dd1637942d95794a907a5186b975'
 node=next(x for x in ast.parse(body).body if isinstance(x,ast.FunctionDef) and x.name=='bootstrap')
 os.environ['BOT_NATIVE_RUNTIME_SITES']=json.dumps(sites)
 ns={'BASE':base,'ROOT':root,'PIN':PIN,'sha':sha,'json':json,'types':types,'sys':sys,'importlib':importlib,'Path':P};exec(compile(ast.Module(body=[node],type_ignores=[]),'accepted_generated_bootstrap','exec'),ns);ns['bootstrap']()
 # Prefer the new candidate module directory after checked dependency install.
 sys.path.insert(0,str(HERE))
 import test_synthetic
 assert test_synthetic.np.__version__=='2.3.5' and test_synthetic.pl.__version__=='1.44.2'
 names=['test_synthetic.Tests.'+n for n in sorted(vars(test_synthetic.Tests)) if n.startswith('test_')];suite=unittest.defaultTestLoader.loadTestsFromNames(names)
 with (OUT/'TEST_LOG.txt').open('x') as log:result=unittest.TextTestRunner(stream=log,verbosity=2,failfast=True).run(suite)
 r.update(tests_run=result.testsRun,fixed_nodes=names,errors=[{'test':str(t),'traceback':s} for t,s in result.errors],failures=[{'test':str(t),'traceback':s} for t,s in result.failures],status='PASS_GENERATED_ORIGINAL_NATIVE_ACCOUNT_SCHEDULER_REGRESSIONS' if result.wasSuccessful() else 'FAILED_PRESERVED');rc=0 if result.wasSuccessful() else 1
except BaseException as e:r.update(status='FAILED_PRESERVED',error=repr(e),traceback=traceback.format_exc())
signal.setitimer(signal.ITIMER_REAL,0);u=resource.getrusage(resource.RUSAGE_SELF);r['resource']={'exit':rc,'end_UTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'wall_seconds':time.monotonic()-BEG,'CPU_seconds':u.ru_utime+u.ru_stime,'peak_RSS_bytes':u.ru_maxrss*1024};r['files']={p.name:{'bytes':p.stat().st_size,'SHA256':sha(p.read_bytes())} for p in OUT.iterdir() if p.is_file()};(OUT/'TEST_RECEIPT.json').write_text(json.dumps(r,indent=2)+'\n');print('V2_SYNTHETIC_TERMINAL',json.dumps(r));sys.exit(rc)
