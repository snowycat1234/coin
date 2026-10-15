"""Bounded unchanged-source-only checks; never executes original V5 financial CLI."""
from pathlib import Path
from hashlib import sha256
import os,sys,tempfile,zipfile,subprocess,json,datetime
ROOT=Path(__file__).resolve().parent.parent
ENV=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1',MKL_NUM_THREADS='1',NUMEXPR_NUM_THREADS='1',POLARS_MAX_THREADS='1',VECLIB_MAXIMUM_THREADS='1',BLIS_NUM_THREADS='1')
GROUPS=[
 ('author_source',['unittest','test_cs_entry','test_cs_source_bridge','test_cs_source','test_cs_funding']),
 ('fresh_zip_positive',['zip']),('fresh_zip_expected_stop',['zip','--expect-cold-stop']),
 ('independent_source',['unittest','review_generated_codecs','review_generated_funding','review_generated_guard','review_generated_metadata','review_generated_signal']),
]

def pin(p):
 raw=p.read_bytes();return {'SHA256':sha256(raw).hexdigest(),'bytes':len(raw)}
def main():
 out=Path(sys.argv[1]) if len(sys.argv)>1 else ROOT/'PACKAGING_EVIDENCE'
 out.mkdir(parents=True,exist_ok=True)
 before={str(p.relative_to(ROOT)):pin(p) for p in ROOT.rglob('*') if p.is_file() and 'PACKAGING_EVIDENCE' not in p.parts}
 results=[]
 with tempfile.TemporaryDirectory(prefix='cs_code_cold_') as td:
  base=Path(td);z=base/'temporary_unsealed_staging.zip';extract=base/'extracted'
  with zipfile.ZipFile(z,'w',compression=zipfile.ZIP_DEFLATED) as archive:
   for name in sorted(before):archive.write(ROOT/name,name)
  with zipfile.ZipFile(z) as archive:archive.extractall(extract)
  for name,args in GROUPS:
   command=[sys.executable,'-B',str(extract/'tools/cold_source_inner.py'),*args]
   p=subprocess.run(command,cwd=extract,env=ENV,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=180)
   raw=p.stdout; (out/(name+'.log')).write_bytes(raw)
   marker=[line for line in raw.decode(errors='replace').splitlines() if line.startswith('COLD_RECEIPT_JSON=')]
   receipt=json.loads(marker[-1].split('=',1)[1]) if marker else None
   results.append({'group':name,'explicit_arguments':args,'exit_code':p.returncode,'receipt':receipt,'log':pin(out/(name+'.log'))})
   if p.returncode:break
 after={name:pin(ROOT/name) for name in before}
 identity_unchanged=before==after
 report={'schema':'BOUNDED_COLD_UNCHANGED_SOURCE21E_ONLY_PACKET_CHECK_V2','created_UTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'status':'PASS' if identity_unchanged and len(results)==len(GROUPS) and all(r['exit_code']==0 for r in results) else 'FAIL','source_code_manifest':pin(ROOT/'original_cs_mom21_D_20261015_v5/CODE_MANIFEST.json'),'original_V5_financial_CLI_cold_status':'NOT_RUN_OMITTED_PRIVATE_RECOVERY_PREREQUISITES','input_code_metadata_unchanged':identity_unchanged,'input_file_count':len(before),'CPU_affinity':sorted(os.sched_getaffinity(0)),'numerical_pools':1,'groups':results,'actual_source_replay':False,'actual_target_construction':False,'historical_financial_runs':0,'valid_GOs_or_claims_created':0,'resource_probe_rerun':False,'publication_actions':0,'universal_sandbox_claim':False}
 (out/'COLD_SOURCE_ONLY_CHECKS.json').write_text(json.dumps(report,indent=2,sort_keys=True)+'\n')
 print(json.dumps({'status':report['status'],'groups':len(results),'tests':sum(r['receipt']['tests'] for r in results if r['receipt'])}))
 return 0 if report['status']=='PASS' else 1
if __name__=='__main__':raise SystemExit(main())
