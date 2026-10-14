"""Bounded source-bound tests + fixed generated scaling + unchanged audit."""
from pathlib import Path
import argparse,json,os,resource,subprocess,sys,time
import bindings as B

def sources():
 return {str(p.relative_to(B.HERE)):B.sha(p) for p in sorted(B.HERE.rglob('*')) if p.is_file() and '__pycache__' not in p.parts and p.suffix in ('.py','.json','.md') and p.name!='PREPARATION_MANIFEST.json'}

def run(args):
 out=Path(args.output).resolve()
 if out.exists():raise ValueError('FRESH_PREPARATION_CHECK_OUTPUT_REQUIRED')
 d=B.load_controller();roots=B.read(args.resource_roots);r=d.resource_admission(roots,out);guard=d.original_resource_guard(roots);guard.require_assertions_enabled()
 out.mkdir(parents=True);before=sources();records=[]
 env=dict(os.environ,BOT_NATIVE_RUNTIME_SITES=json.dumps(args.runtime_site),PYTHONDONTWRITEBYTECODE='1',OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1',POLARS_MAX_THREADS='1')
 env.pop('PYTHONOPTIMIZE',None);env['PYTHONPATH']=os.pathsep.join(args.runtime_site)
 sites=sum((['--runtime-site',p] for p in args.runtime_site),[])
 stages=[('tests',['tests']),
  ('fixed_generated_scaling',['benchmark','--output',str(out/'scaling'),'--resource-roots',args.resource_roots,*sites]),
  ('exact_existing_auditor',['audit','--output',str(out/'scaling')])]
 for name,argv in stages:
  def limits():
   if name=='fixed_generated_scaling':
    # This child is the original-admission controller, not an economic
    # worker. Preserve its verified >=2CPU admission view; benchmark itself
    # then binds every actual wallet worker to exactly one admitted CPU.
    os.sched_setaffinity(0,set(r['allowed_cpus']))
    resource.setrlimit(resource.RLIMIT_AS,(guard.WORKER_AS_LIMIT,guard.WORKER_AS_LIMIT))
    # The exact helper first installs its1200s ceiling before narrowing every
    # generated worker to150s. A lower controller hard limit would make that
    # unchanged child helper fail in preexec; preserve the original ceiling.
    resource.setrlimit(resource.RLIMIT_CPU,(guard.CPU_LIMIT,guard.CPU_LIMIT))
   else:
    guard.child_limits(r['allowed_cpus'][0]);resource.setrlimit(resource.RLIMIT_CPU,(150,150))
  start=time.monotonic();child=subprocess.run([sys.executable,'-B',str(B.HERE/'run_verified.py'),'--preparation-manifest-sha',B.sha(B.HERE/'PREPARATION_MANIFEST.json'),*argv],cwd=B.HERE,env=env,preexec_fn=limits,capture_output=True,text=True,timeout=200)
  (out/(name+'.txt')).write_text(child.stdout+child.stderr);records.append(dict(stage=name,exit_code=child.returncode,wall_seconds=time.monotonic()-start))
  if child.returncode:break
 after=sources();usage=resource.getrusage(resource.RUSAGE_CHILDREN)
 receipt=dict(schema='ORIGINAL_CSH_GRID_PREPARATION_GENERATED_CHECK_V1',status='PASS_GENERATED_PREPARATION_ONLY' if len(records)==3 and all(r['exit_code']==0 for r in records) and before==after else 'FAIL',source_before=before,source_after=after,source_unchanged=before==after,stages=records,peak_child_RSS_KiB=usage.ru_maxrss,
  limits=dict(one_worker_cpu=True,controller_admission_CPU_count=len(r['allowed_cpus']),original_address_space_bytes=4000000000,worker_CPU_seconds=150,controller_original_CPU_ceiling_seconds=guard.CPU_LIMIT,stage_wall_seconds=200),
  preparation_code_historical_array_reads=0,historical_wallets=0,historical_GO=False,risk_parity_certified=False,restore_supported=False,metadata_inspection_exception='METADATA_READ_EXCEPTION.json remains explicit; historical terminal quote values were viewed separately')
 (out/'FINAL_PREPARATION_CHECK_RECEIPT.json').write_text(json.dumps(receipt,indent=2)+'\n')
 print(json.dumps({k:v for k,v in receipt.items() if not k.startswith('source_')},indent=2));return 0 if receipt['status'].startswith('PASS') else 1

def main():
 p=argparse.ArgumentParser();p.add_argument('--output',required=True);p.add_argument('--resource-roots',required=True);p.add_argument('--runtime-site',action='append',required=True);a=p.parse_args();return run(a)

if __name__=='__main__':raise SystemExit('USE_RUN_VERIFIED_COLD_BOOTSTRAP')
