"""Fresh-output bounded wrapper; no change to the c249 tests or export body."""
from pathlib import Path
import argparse,hashlib,json,os,resource,subprocess,sys,time
HERE=Path(__file__).resolve().parent

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def source_catalog():
 from bind_sources import verify_code_only
 verify_code_only()
 return {str(p.relative_to(HERE)):sha(p) for p in HERE.rglob('*')
  if p.is_file() and '__pycache__' not in p.parts and p.suffix in ('.py','.json','.md','.diff')}

def limits():
 resource.setrlimit(resource.RLIMIT_AS,(4*1024**3,4*1024**3))
 resource.setrlimit(resource.RLIMIT_CPU,(120,120))
 os.sched_setaffinity(0,{min(os.sched_getaffinity(0))})

def run(args):
 from bind_sources import verify_code_only,configure_runtime
 verify_code_only();identities=configure_runtime(args.runtime_site)
 out=Path(args.output_directory).resolve()
 if out.is_relative_to(HERE):raise ValueError('FRESH_OUTPUT_MUST_BE_OUTSIDE_SOURCE_PACKAGE')
 if args.export_only:
  if not out.is_dir():raise ValueError('PARENT_PREPARED_FRESH_OUTPUT_REQUIRED')
  import export_generated
  export_generated.HERE=out  # Destination only; exact original export body.
  export_generated.export();return 0
 if out.exists():raise ValueError('FRESH_OUTPUT_DIRECTORY_REQUIRED_NO_OVERWRITE')
 out.mkdir(parents=True)
 before=source_catalog();env=os.environ.copy()
 env.pop('PYTHONPATH',None);env.pop('PYTHONOPTIMIZE',None)
 env.update(BOT_NATIVE_RUNTIME_SITES=json.dumps(args.runtime_site),PYTHONDONTWRITEBYTECODE='1',OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1',MKL_NUM_THREADS='1',POLARS_MAX_THREADS='1')
 # numpy appears before bind_sources.load in the unchanged adapter; declare
 # consumer runtime paths on the child's startup path, never inherit them.
 env['PYTHONPATH']=os.pathsep.join(str(Path(p).resolve()) for p in args.runtime_site)
 records=[]
 export=[str(HERE/'portable_checks.py'),'--export-only','--output-directory',str(out)]
 for site in args.runtime_site:export+=['--runtime-site',site]
 stages=[('portable_gate',['-m','unittest','-v','test_portable_binding']),
  ('unchanged_generated_tests',['-m','unittest','-v','test_native_adapter']),('unchanged_journal_export',export)]
 for label,argv in stages:
  start=time.monotonic()
  try:
   child=subprocess.run([sys.executable,*argv],cwd=HERE,env=env,preexec_fn=limits,text=True,capture_output=True,timeout=180)
   output=child.stdout+child.stderr;code=child.returncode
  except subprocess.TimeoutExpired as e:output=str(e);code=124
  (out/(label+'.txt')).write_text(output)
  records.append(dict(step=label,returncode=code,wall_seconds=time.monotonic()-start))
  if code:break
 after=source_catalog();usage=resource.getrusage(resource.RUSAGE_CHILDREN)
 receipt=dict(schema='PORTABLE_SYNTHETIC_ONLY_BOUNDED_CHECK_V1',
  status='PASS_SYNTHETIC_MECHANICS_ONLY' if len(records)==3 and all(r['returncode']==0 for r in records) and before==after else 'FAIL',
  steps=records,source_before=before,source_after=after,source_unchanged=before==after,
  runtime=identities,python=sys.version,peak_child_RSS_KiB=usage.ru_maxrss,
  limits=dict(cpu_affinity_count=1,address_space_GiB=4,cpu_seconds_per_child=120,wall_seconds_per_child=180),
  prior_c249_source_changed=False,original26_historical_closure_verified=False,
  history_arrays_loaded=0,historical_target_artifacts_hashed=0,historical_GO=False,
  risk_parity_certified=False,restore_supported=False)
 (out/'PORTABLE_CHECK_RECEIPT.json').write_text(json.dumps(receipt,indent=2,allow_nan=False)+'\n')
 print(json.dumps({k:v for k,v in receipt.items() if k not in ('source_before','source_after','runtime')},indent=2))
 return 0 if receipt['status'].startswith('PASS') else 1

if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('--runtime-site',action='append',required=True)
 parser.add_argument('--output-directory',required=True);parser.add_argument('--export-only',action='store_true')
 args=parser.parse_args();os.environ['BOT_NATIVE_RUNTIME_SITES']=json.dumps(args.runtime_site)
 raise SystemExit(run(args))
