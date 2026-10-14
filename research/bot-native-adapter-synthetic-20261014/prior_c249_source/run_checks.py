"""Bounded one-CPU from-start tests/export, pinned source before/after receipt."""
from pathlib import Path
import hashlib,json,os,resource,subprocess,sys,time
HERE=Path(__file__).resolve().parent;ROOT=HERE.parent

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def sources():
 records={str((HERE/n).resolve()):sha(HERE/n) for n in ('native_adapter.py','bind_sources.py','generated_fixtures.py','test_native_adapter.py','export_generated.py','run_checks.py')}
 from bind_sources import PINS,REVIEW,LAUNCHER
 roots=json.loads((REVIEW/'synthetic_dependencies_ca11e94d/SYNTHETIC_ROOTS.json').read_text())
 closure=json.loads((LAUNCHER/'EXECUTABLE_CLOSURE.json').read_text())
 for group,root in (('repo_files',roots['repo']),('fine_files',roots['fine'])):
  for name,r in closure[group].items():
   p=Path(root)/name;records[str(p.resolve())]=sha(p)
 for name,_ in PINS.values():
  p=ROOT/name;records[str(p.resolve())]=sha(p)
 p=LAUNCHER/'terminal_adapter.py';records[str(p.resolve())]=sha(p)
 orig=ROOT/'coin_funding_target_discriminator_20261014/original2021'
 for r in json.loads((orig/'ORIGINAL_REFERENCE.json').read_text()):
  p=orig/r['local_locator'];records[str(p.resolve())]=sha(p)
 return records

def limits():
 resource.setrlimit(resource.RLIMIT_AS,(4*1024**3,4*1024**3))
 resource.setrlimit(resource.RLIMIT_CPU,(120,120))
 os.sched_setaffinity(0,{min(os.sched_getaffinity(0))})

def run():
 before=sources();env=os.environ.copy()
 env.update(PYTHONDONTWRITEBYTECODE='1',OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1',MKL_NUM_THREADS='1',POLARS_MAX_THREADS='1')
 records=[]
 for label,args in [('tests',['-m','unittest','-v','test_native_adapter']),('journal_export',['export_generated.py'])]:
  start=time.monotonic();p=subprocess.run([sys.executable,*args],cwd=HERE,env=env,
   preexec_fn=limits,text=True,capture_output=True,timeout=180)
  (HERE/f'FINAL_{label.upper()}_LOG.txt').write_text(p.stdout+p.stderr)
  records.append(dict(step=label,returncode=p.returncode,wall_seconds=time.monotonic()-start))
  if p.returncode:break
 after=sources();usage=resource.getrusage(resource.RUSAGE_CHILDREN)
 receipt=dict(status='PASS_SYNTHETIC_MECHANICS_ONLY' if all(r['returncode']==0 for r in records) and len(records)==2 and before==after else 'FAIL',
  steps=records,source_before=before,source_after=after,source_unchanged=before==after,
  peak_child_RSS_KiB=usage.ru_maxrss,child_user_seconds=usage.ru_utime,child_system_seconds=usage.ru_stime,
  limits=dict(cpu_affinity_count=1,address_space_GiB=4,cpu_seconds_per_child=120,wall_seconds_per_child=180),
  historical_GO=False,history_arrays_loaded=0,market_downloads=0,risk_parity_certified=False)
 (HERE/'FINAL_CHECK_RECEIPT.json').write_text(json.dumps(receipt,indent=2)+'\n')
 print(json.dumps({k:v for k,v in receipt.items() if not k.startswith('source_')},indent=2))
 return 0 if receipt['status'].startswith('PASS') else 1
if __name__=='__main__':raise SystemExit(run())
