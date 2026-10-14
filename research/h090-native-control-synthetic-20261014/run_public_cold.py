"""Exact operational transport wrapper; frozen science and closure are unchanged."""
from pathlib import Path
import argparse,gzip,hashlib,io,json,os,platform,re,subprocess,sys,tarfile,time
HERE=Path(__file__).resolve().parent
FREEZE='cf886908cb2a55537c7ddc1d7e5a73a5a09ed48eff110634cbc59242240ea40f'
VERSIONS={'python':'3.12.14','numpy':'2.3.5','polars':'1.44.2','pyarrow':'23.0.1'}
def sha(b):return hashlib.sha256(b).hexdigest()
def safe(name):
 p=Path(name)
 if p.is_absolute() or '..' in p.parts or p.as_posix()!=name:raise ValueError('UNSAFE_PUBLIC_MANIFEST_PATH')
 return p

def checked(name,row):
 p=HERE/safe(name)
 if any(x.is_symlink() for x in (p,*p.parents) if x.is_relative_to(HERE)):raise ValueError('SYMLINKED_PUBLIC_MEMBER')
 body=p.read_bytes()
 if len(body)!=row['bytes'] or sha(body)!=row['SHA256']:raise ValueError('PUBLIC_MEMBER_IDENTITY_MISMATCH:'+name)
 if row.get('GitBlobSHA1') and hashlib.sha1(b'blob '+str(len(body)).encode()+b'\0'+body).hexdigest()!=row['GitBlobSHA1']:raise ValueError('PUBLIC_GIT_BODY_IDENTITY_MISMATCH:'+name)
 return body

def verify(expected):
 if not re.fullmatch('[0-9a-f]{64}',expected):raise ValueError('EXTERNAL_PUBLIC_MANIFEST_SHA_REQUIRED')
 raw=(HERE/'PUBLIC_PAYLOAD_MANIFEST.json').read_bytes()
 if sha(raw)!=expected:raise ValueError('PUBLIC_MANIFEST_HASH_MISMATCH')
 manifest=json.loads(raw)
 for name,row in manifest['files'].items():checked(name,row)
 raw=(HERE/'SOURCE_FREEZE.json').read_bytes()
 if sha(raw)!=FREEZE:raise ValueError('EXTERNAL_FROZEN_SOURCE_IDENTITY_MISMATCH')
 freeze=json.loads(raw);pins=json.loads((HERE/'DEPENDENCY_PINS.json').read_bytes())
 for name,digest in {**freeze['files_SHA256'],**pins['files_SHA256']}.items():
  if sha((HERE/safe(name)).read_bytes())!=digest:raise ValueError('EXACT_FROZEN_CLOSURE_MISMATCH:'+name)
 journal=json.loads((HERE/'saved_generated_journals/JOURNAL_BODY_MANIFEST.json').read_bytes())
 archive=checked('saved_generated_journals/'+journal['archive']['relative_path'],journal['archive'])
 bodies={}
 with tarfile.open(fileobj=io.BytesIO(gzip.decompress(archive)),mode='r:') as source:
  rows={x['archive_member']:x for x in journal['native_files']}
  members=source.getmembers()
  if len(members)!=len(rows):raise ValueError('EXACT_ARCHIVED_JOURNAL_MEMBER_COUNT_REQUIRED')
  for item in members:
   if item.name not in rows or not item.isfile() or item.name in bodies:raise ValueError('UNEXPECTED_ARCHIVED_JOURNAL_MEMBER')
   body=source.extractfile(item).read();row=rows[item.name]
   if len(body)!=row['bytes'] or sha(body)!=row['SHA256']:raise ValueError('SAVED_NATIVE_JOURNAL_BODY_MISMATCH')
   json.loads(body);bodies[item.name]=body
 return {'status':'PASS_EXACT_PUBLIC_AND_ORIGINAL_FROZEN_IDENTITIES','public_manifest_SHA256':expected,'source_freeze_SHA256':FREEZE,'public_members':len(manifest['files']),'exact_source_closure_members':len({**freeze['files_SHA256'],**pins['files_SHA256']}),'existing_public_target_archives_checksum_only':2,'existing_public_target_archive_bytes':50586,'NPZ_arrays_parsed':0,'lossless_native_journal_members':len(bodies)},bodies

def main():
 parser=argparse.ArgumentParser(description=__doc__)
 parser.add_argument('--expected-manifest-sha256',required=True)
 parser.add_argument('--receipt-dir',required=True)
 parser.add_argument('--runtime-site',action='append',default=[],help='Explicit site-packages containing the exact pinned official runtime; no download performed.')
 parser.add_argument('--identity-only',action='store_true')
 args=parser.parse_args()
 identity,bodies=verify(args.expected_manifest_sha256)
 if args.identity_only:print(json.dumps(identity,indent=2));return 0
 if platform.python_version()!=VERSIONS['python']:raise ValueError('EXACT_PRODUCER_PYTHON_3_12_14_REQUIRED')
 sites=[]
 for name in args.runtime_site:
  path=Path(name).resolve()
  if not path.is_dir():raise ValueError('EXPLICIT_RUNTIME_SITE_DIRECTORY_REQUIRED')
  sites.append(str(path))
 destination=Path(args.receipt_dir).resolve();destination.mkdir(parents=False,exist_ok=False)
 env={k:v for k,v in os.environ.items() if not k.startswith('PYTHON')}
 env.update(PYTHONDONTWRITEBYTECODE='1',OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1',MKL_NUM_THREADS='1',NUMEXPR_NUM_THREADS='1',POLARS_MAX_THREADS='1',RAYON_NUM_THREADS='1')
 if sites:env['PYTHONPATH']=os.pathsep.join(sites)
 probe="import json,platform,numpy,polars,pyarrow,sys; versions={'python':platform.python_version(),'numpy':numpy.__version__,'polars':polars.__version__,'pyarrow':pyarrow.__version__}; expected="+repr(VERSIONS)+"; print(json.dumps({'versions':versions,'optimization_level':sys.flags.optimize},sort_keys=True)); sys.exit(0 if versions==expected and sys.flags.optimize==0 else 1)"
 commands=[('exact_runtime_identity',[sys.executable,'-B','-c',probe]),('frozen_source_loader_audit',[sys.executable,'-B','run_verified.py','--freeze-sha',FREEZE,'check-loader']),('frozen_bounded_51_tests_and_8_journals',[sys.executable,'-B','run_checks.py','--freeze-sha',FREEZE,'--receipt-dir',str(destination/'bounded')])]
 records=[]
 for stage,command in commands:
  began=time.monotonic()
  result=subprocess.run(command,cwd=HERE,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=300)
  (destination/(stage+'.txt')).write_bytes(result.stdout)
  records.append({'stage':stage,'returncode':result.returncode,'wall_seconds':time.monotonic()-began,'output_SHA256':sha(result.stdout)})
  if result.returncode:break
 passed=len(records)==len(commands) and all(x['returncode']==0 for x in records)
 parity=[]
 if passed:
  receipt=json.loads((destination/'bounded/RECEIPT.json').read_bytes())
  if receipt['status']!='PASS_GENERATED_ONLY':raise ValueError('BOUNDED_GENERATED_RECEIPT_REQUIRED')
  for name,want in bodies.items():
   p=destination/'bounded/generated'/name;actual=p.read_bytes();equal=actual==want
   parity.append({'native_journal_member':name,'bytes':len(actual),'SHA256':sha(actual),'byte_exact_saved_native_body':equal})
   passed=passed and equal
 after,_=verify(args.expected_manifest_sha256)
 passed=passed and after==identity
 report={'schema':'H090_PUBLIC_TRANSPORT_COLD_VERIFICATION_V1','status':'PASS_EXACT_ORIGINAL_FROZEN_GENERATED_COLD_AND_NATIVE_BODY_PARITY' if passed else 'FAIL_PUBLIC_COLD','identity_gate':identity,'runtime':VERSIONS,'runtime_sites_explicitly_supplied':len(sites),'inherited_python_settings_removed':True,'records':records,'distinct_generated_tests':51 if passed else None,'fresh_generated_journals':8 if passed else None,'native_body_parity':parity,'frozen_source_bytes_unchanged':after==identity,'scope':'OFFLINE_GENERATED_ONLY_WITH_CHECKSUM_ACCESS_TO_TWO_ALREADY_PUBLIC_2023_2025_DEVELOPMENT_TARGET_ARCHIVES','target_archive_checksum_access_bytes':50586,'target_archive_np_load_or_member_parsing':0,'new_historical_wallets':0,'new_downloads':0,'historical_GO':False,'restore_GO':False,'finite_program_GO':False,'parent_financial_review_is_separate_agent_review':False,'separate_agent_review_status':'NOT_PERFORMED_FAILED_AND_RETAINED'}
 (destination/'PUBLIC_COLD_RECEIPT.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
 print(json.dumps(report,indent=2));return 0 if passed else 1
if __name__=='__main__':raise SystemExit(main())
