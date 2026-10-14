"""Fresh explicitly authorized synthetic stage; no history or network."""
import os,sys,time,datetime,resource,signal,pathlib,json,hashlib,unittest,traceback
assert os.environ.get('ROOT_GENERATED_TEST_GO')=='REVIEWED_GENERATED_ONLY', 'SEPARATE_GENERATED_TEST_GO_REQUIRED'
import argparse,sysconfig
ap=argparse.ArgumentParser();ap.add_argument('--code-root',required=True);ap.add_argument('--output',required=True);ap.add_argument('--runtime-sites-json');ap.add_argument('--synthetic-manifest-sha',required=True);args=ap.parse_args();os.environ['ORIGINAL_CSH_CODE_ROOT']=args.code_root;os.environ['GENERATED_TEST_OUTPUT']=args.output
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
 current=(HERE/'SYNTHETIC_ONLY_MANIFEST.json').read_bytes();assert sha(current)==args.synthetic_manifest_sha
 for name,v in json.loads(current)['files'].items():
  body=(HERE/name).read_bytes();assert len(body)==v['bytes'] and sha(body)==v['SHA256'],name
 mf=json.loads((HERE/'FREEZE.json').read_bytes())
 for name,v in mf['files'].items():b=(HERE/name).read_bytes();assert len(b)==v['bytes'] and sha(b)==v['SHA256']
 root=P(os.environ.get('ORIGINAL_CSH_CODE_ROOT','/workspace/coin-cloud/h090-original2023-code-20261014'));deps=json.loads((HERE/'SYNTHETIC_ONLY_RESTORE_MAP.json').read_bytes())
 for name,v in deps['bodies'].items():b=(root/name).read_bytes();assert len(b)==v['bytes'] and sha(b)==v['SHA256']
 for k in ['PYTHONOPTIMIZE','PYTHONPATH','PYTHONHOME','PYTHONSTARTUP']:os.environ.pop(k,None)
 for k in ['OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS','POLARS_MAX_THREADS']:os.environ[k]='1'
 sites=json.loads(args.runtime_sites_json) if args.runtime_sites_json else list(dict.fromkeys([sysconfig.get_path('purelib'),sysconfig.get_path('platlib')]));assert sites and all(P(x).is_absolute() and P(x).is_dir() for x in sites);repo=root/'native_pair_replacement_review_20261014/synthetic_dependencies_ca11e94d/repo';fine=root/'native_pair_replacement_review_20261014/synthetic_dependencies_ca11e94d/fine';sys.path[:0]=[str(HERE),*sites,str(fine),str(repo),str(repo/'src')]
 import numpy,polars
 assert (numpy.__version__,polars.__version__)==('2.3.5','1.44.2')
 import ast,types,importlib
 # Source-exact generated-only exports avoid importing provider/archive modules.
 # These modules cannot generate targets or dispatch a historical/source case.
 def selected(module,path,names):
  tree=ast.parse(path.read_bytes());nodes=[]
  for node in tree.body:
   if isinstance(node,(ast.FunctionDef,ast.ClassDef)) and node.name in names:nodes.append(node)
   elif isinstance(node,ast.Assign) and any(isinstance(t,ast.Name) and t.id in names for t in node.targets):nodes.append(node)
  assert len(nodes)==len(names),(module,names)
  mod=types.ModuleType(module);mod.__file__=str(path);exec(compile(ast.Module(body=nodes,type_ignores=[]),str(path),'exec'),mod.__dict__);sys.modules[module]=mod
 selected('scripts.investment.perpetual_directional',repo/'scripts/investment/perpetual_directional.py',{'MINUTE','DAY','need'})
 selected('scripts.investment.public_sma_perpetual',repo/'scripts/investment/public_sma_perpetual.py',{'SYMBOLS','require','symbol_order'})
 sys.path.insert(0,str(root/'coin_h090_finite_native_20261014/dependencies'))
 import terminal_adapter
 native=types.ModuleType('native_control');native.NATIVE=terminal_adapter.EarlierTerminalSimulator;sys.modules['native_control']=native
 def forbid(event,args):
  if event in ('socket.connect','subprocess.Popen','os.system'):raise RuntimeError('GENERATED_ONLY_NO_NETWORK_OR_CHILDREN')
  if event=='open' and isinstance(args[0],(str,bytes,os.PathLike)):
   path=P(os.fsdecode(args[0]))
   if path.suffix.lower() in ('.npz','.npy','.parquet','.csv','.zip','.gz'):raise RuntimeError('GENERATED_ONLY_NO_DATA_CONTAINER_READ:'+str(path))
 sys.addaudithook(forbid)
 # Prefer the new candidate module directory after checked dependency install.
 sys.path.insert(0,str(HERE))
 import test_synthetic
 assert test_synthetic.np.__version__=='2.3.5' and test_synthetic.pl.__version__=='1.44.2'
 names=['test_synthetic.Tests.'+n for n in sorted(vars(test_synthetic.Tests)) if n.startswith('test_')];suite=unittest.defaultTestLoader.loadTestsFromNames(names)
 with (OUT/'TEST_LOG.txt').open('x') as log:result=unittest.TextTestRunner(stream=log,verbosity=2,failfast=True).run(suite)
 r.update(tests_run=result.testsRun,fixed_nodes=names,errors=[{'test':str(t),'traceback':s} for t,s in result.errors],failures=[{'test':str(t),'traceback':s} for t,s in result.failures],status='PASS_GENERATED_ORIGINAL_NATIVE_ACCOUNT_SCHEDULER_REGRESSIONS' if result.wasSuccessful() else 'FAILED_PRESERVED');rc=0 if result.wasSuccessful() else 1
except BaseException as e:r.update(status='FAILED_PRESERVED',error=repr(e),traceback=traceback.format_exc())
signal.setitimer(signal.ITIMER_REAL,0);u=resource.getrusage(resource.RUSAGE_SELF);r['resource']={'exit':rc,'end_UTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'wall_seconds':time.monotonic()-BEG,'CPU_seconds':u.ru_utime+u.ru_stime,'peak_RSS_bytes':u.ru_maxrss*1024};r['files']={p.name:{'bytes':p.stat().st_size,'SHA256':sha(p.read_bytes())} for p in OUT.iterdir() if p.is_file()};(OUT/'TEST_RECEIPT.json').write_text(json.dumps(r,indent=2)+'\n');print('V2_SYNTHETIC_TERMINAL',json.dumps(r));sys.exit(rc)
