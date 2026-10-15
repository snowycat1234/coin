#!/usr/bin/env python3
"""Build a new compact saved-results packet; no financial or source runtime imports."""
from pathlib import Path
import os,json,hashlib,gzip,shutil,zipfile,argparse
from saved_report import *
from verify_packet import AGG,FINAL,EXIT,SOURCE_ARCHIVE
W=Path(__file__).resolve().parent.parent;P=Path(__file__).resolve().parent
NAME='traditional_D_partial2021_nine_compact_saved_results_public_recovery_20261015_v1'
STAGE=P/'staged_candidate';OUT=W/NAME
PUBLIC_NAMES=('ACCOUNT_FINANCIAL_AUDIT.json','ACTUAL_HELD_RISK_REPORT.json','CASE_RECEIPT.json','CAUSAL_MARK_QUALITY.json','GUARD_RECEIPTS.json','LEGACY_PRIMARY_FINANCIAL_RECONCILIATION.json','NATIVE40_RECONSTRUCTION_PROOF.json','NATIVE_RESULT.json','PRIMARY_FINANCIAL_RECONCILIATION.json','TERMINAL_CHECKPOINT.json')
REVIEW_NAMES=tuple(c+'_SAVED_REVIEW.json' for c in CELLS)+('INDEPENDENT_NINE_SAVED_REVIEW.json','FINAL_INDEPENDENT_ACTUAL_PARTIAL2021_NINE_REVIEW.json','STATIC50_H090_POST_HOC_SAVED_EQUALITY.json','review_saved_nine.py','compare_static_h090_saved.py','seal_final_saved_review.py')
PRIVATE_NAMES=('ADMISSION_GO.json','LAUNCH_CLAIM.json','PROCESS_OWNERSHIP.json','BOOTSTRAP_READY.json','ADMISSION_REVIEW.json')
def digest(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for b in iter(lambda:f.read(1<<20),b''):h.update(b)
 return h.hexdigest()
def pin(p):return {'sha256':digest(p),'bytes':Path(p).stat().st_size}
def write(p,value):
 p=Path(p);p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(json_bytes(value))
def seal_local():
 target=P/'LOCAL_FULL_RECOVERY_MANIFEST.json';require(not target.exists(),'LOCAL_PRESERVATION_ALREADY_SEALED')
 originals=set();directories={}
 for rel in (ATT,REV,'traditional_D_partial2021_20261015/source_preparation_final'):
  d=W/rel;files=sorted(p for p in d.rglob('*') if p.is_file() and '__pycache__' not in p.parts);directories[rel]=[str(p.relative_to(d)) for p in files];originals.update(files)
 module=W/'traditional_D_partial2021_20261015'
 originals.update(p for p in module.iterdir() if p.is_file())
 prep=load(module/'source_preparation_final/PREPARATION.json')
 originals.update(W/p for p in prep['code_identity'])
 originals.add(W/OLD)
 files={str(p.relative_to(W)):pin(p) for p in sorted(originals)}
 require(files['traditional_D_partial2021_20261015/ROOT_GO_APPROVED_NINE_20261015_1117.json']['sha256']==GO,'ROOT_GO_ORIGINAL_CHANGED')
 require(files['traditional_D_partial2021_20261015/source_preparation_final/PREPARATION.json']['sha256']==PREP,'FROZEN_PREPARATION_CHANGED')
 require(files[REV+'/INDEPENDENT_NINE_SAVED_REVIEW.json']['sha256']==AGG and files[REV+'/FINAL_INDEPENDENT_ACTUAL_PARTIAL2021_NINE_REVIEW.json']['sha256']==FINAL,'FROZEN_FINAL_REVIEW_CHANGED')
 require(files[ATT+'/ROOT_OBSERVED_EXIT.json']['sha256']==EXIT,'ROOT_EXIT_CHANGED')
 minutes={c:files[ATT+'/'+c+'/MINUTE.npz'] for c in CELLS}
 value=dict(schema='LOCAL_FULL_ORIGINAL_PARTIAL2021_SAVED_FILESET_PRESERVATION_V1',files=files,directory_file_sets=directories,all_nine_full_MINUTE_originals_preserved_in_place=True,MINUTE_outputs=minutes,full_MINUTE_output_bytes=sum(v['bytes'] for v in minutes.values()),local_original_files_preserved_unchanged=True,private_original_authority_process_bodies_preserved_locally=True,local_full_archive_created=False,original_bytes_recoverable_from_manifest_alone=False)
 write(target,value);return value

def manifest(root,source):
 files={str(p.relative_to(root)):pin(p) for p in sorted(root.rglob('*')) if p.is_file() and p.name!='MANIFEST.json' and '__pycache__' not in p.parts}
 write(root/'MANIFEST.json',dict(schema='ORIGINAL_D_PARTIAL2021_NINE_COMPACT_SAVED_RESULTS_V1',packet_kind='PUBLIC_SAFE_SAVED_RESULTS_ONLY',ordered_cells=list(CELLS),files=files,source_verified_commit=source.get('source_commit'),sole_authorized_results_publication_parent=source.get('source_commit'),no_run_authority=True,financial_reruns=0))

def stage():
 require(not STAGE.exists() and not OUT.exists() and not OUT.with_suffix('.zip').exists(),'NEVER_OVERWRITE_PACKET')
 require(digest(P/'saved_native_reconciliation.py')==CHECKER,'EXACT_PURE_NATIVE40_CHECKER_REQUIRED')
 preserve=seal_local();pins=dict(preserve['files']);exact={};gzmap={};STAGE.mkdir()
 def cp(p,dest=None,compress=False):
  p=Path(p);src=str(p.relative_to(W));ref=pin(p)
  if src in pins:require(same(pins[src],ref),'ORIGINAL_CHANGED_DURING_PACKAGING:'+src)
  pins[src]=ref;dest=dest or src
  if compress:dest+='.gz'
  q=STAGE/dest;q.parent.mkdir(parents=True,exist_ok=True)
  if compress:
   with p.open('rb') as i,q.open('xb') as f,gzip.GzipFile(filename='',fileobj=f,mode='wb',mtime=0,compresslevel=9) as z:shutil.copyfileobj(i,z)
   gzmap[dest]=dict(source=src,transformation='LOSSLESS_GZIP_EXACT_ORIGINAL_BYTES',uncompressed_sha256=ref['sha256'],uncompressed_bytes=ref['bytes'])
  else:shutil.copyfile(p,q);exact[dest]=src
 for cell in CELLS:
  for n in PUBLIC_NAMES:cp(W/ATT/cell/n,compress=n in ('ACCOUNT_FINANCIAL_AUDIT.json','NATIVE_RESULT.json','GUARD_RECEIPTS.json'))
 for n in REVIEW_NAMES:cp(W/REV/n)
 cp(W/ATT/'ROOT_OBSERVED_EXIT.json')
 cp(W/'traditional_D_partial2021_20261015/FROZEN_NINE_CELL_MANIFEST.json')
 cp(W/OLD,compress=True)
 for n in ['saved_native_reconciliation.py','saved_report.py','verify_packet.py','test_packet.py','build_packet.py','README.md']:cp(P/n,n)
 original_review=W/'traditional_D_partial2021_independent_review_20261015/INDEPENDENT_ORIGINAL_D_PARTIAL2021_REVIEW.json'
 require(digest(original_review)==SOURCE_REVIEW,'SOURCE_REVIEW_CHANGED')
 source={'schema':'VERIFIED_PARTIAL2021_SOURCE_BEFORE_RESULTS_REFERENCE_V1','status':'PENDING_FULL_REMOTE_VERIFICATION','source_archive_sha256':SOURCE_ARCHIVE,'source_archive_bytes':696892,'source_packet_body_not_duplicated':True,'no_run_or_publication_authority_granted':True}
 write(STAGE/'SOURCE_PUBLICATION_REFERENCE.json',source)
 write(STAGE/'EXACT_COPY_SOURCE_MAP.json',exact);write(STAGE/'LOSSLESS_GZIP_SOURCE_MAP.json',gzmap)
 write(STAGE/'FULL_SAVED_OUTPUT_HASH_PINS.json',dict(schema='EXACT_ORIGINAL_PARTIAL2021_SAVED_FILESET_PINS_V1',files=pins,directory_file_sets=preserve['directory_file_sets'],omitted_bytes_recoverable_from_hashes=False))
 write(STAGE/'EXTERNAL_ADMISSION_HASH_ONLY.json',dict(schema='EXACT_PARTIAL2021_PRIVATE_AUTHORITY_HASH_ONLY_V1',root_GO_sha256=GO,source_generated_review_sha256=SOURCE_REVIEW,preparation_sha256=PREP,private_GO_bodies_included=False,new_run_or_publication_authority_granted=False,omitted_private_bodies={p:v for p,v in pins.items() if Path(p).name in PRIVATE_NAMES or Path(p).suffix=='.log' or Path(p).name.startswith(('CONTROLLER_RECEIPT','ADMISSION_'))}))
 minute={c:{'source':ATT+'/'+c+'/MINUTE.npz',**pins[ATT+'/'+c+'/MINUTE.npz']} for c in CELLS}
 write(STAGE/'OMITTED_ARRAYS_AND_RECOVERY_LIMITS.json',dict(schema='NINE_PARTIAL2021_LOCAL_ARRAY_PINS_AND_LIMITS_V1',MINUTE_outputs=minute,raw_market_source_target_and_covariance_arrays_omitted=True,all_minute_risk_regeneration_self_contained=False,omitted_bytes_recoverable_from_hashes=False,required_for_deep_regeneration='Exact pinned local minute outputs and source/target/covariance arrays, or a separately admitted identical run. Neither bytes nor authority are granted by this packet.',financial_JSON_includes_original_target_decision_and_request_intent_audits_not_raw_input_arrays=True,frozen_input_array_and_source_artifact_pins=load(W/'traditional_D_partial2021_20261015/FROZEN_NINE_CELL_MANIFEST.json')['source_target_artifacts']))
 write(STAGE/'LOCAL_ORIGINAL_PRESERVATION_REFERENCE.json',dict(schema='HASH_ONLY_LOCAL_ORIGINAL_PRESERVATION_PROJECTION_V1',local_manifest_sha256=digest(P/'LOCAL_FULL_RECOVERY_MANIFEST.json'),local_manifest_bytes=(P/'LOCAL_FULL_RECOVERY_MANIFEST.json').stat().st_size,total_original_files=len(preserve['files']),full_MINUTE_output_count=9,full_MINUTE_output_bytes=preserve['full_MINUTE_output_bytes'],all_nine_full_MINUTE_originals_preserved_in_place=True,original_bytes_recoverable_from_manifest_alone=False,private_authority_and_process_bodies_preserved_only_locally=True,full_local_archive_created=False))
 write(STAGE/'INDEPENDENT_REVIEW_HASH_PINS.json',dict(schema='FROZEN_PARTIAL2021_FINAL_SAVED_REVIEW_PINS_V1',financial_aggregate_sha256=AGG,final_independent_review_sha256=FINAL,equality_review_sha256=EQUALITY,root_observed_exit_sha256=EXIT,source_generated_review_sha256=SOURCE_REVIEW,financial_review_original_bodies_preserved_unchanged=True))
 report=build(STAGE);write(STAGE/'summary/REPORT.json',report)
 (STAGE/'summary/REPORT.txt').write_text(render_text(report));(STAGE/'summary/REPORT.csv').write_text(render_csv(report['rows']));(STAGE/'summary/DESCRIPTIVE_PERIOD_TABLE.csv').write_text(render_csv(report['descriptive_period_rows']))
 scan=[];markers=[b'/'+b'workspace/',b'/'+b'tmp/',b'/'+b'home/agent/',b'/'+b'Users/',b'-----BEGIN '+b'PRIVATE KEY',b'github_'+b'pat_',b'gh'+b'p_',b'Bearer'+b' ']
 for p in sorted(STAGE.rglob('*')):
  if not p.is_file():continue
  b=gzip.decompress(p.read_bytes()) if p.suffix=='.gz' else p.read_bytes();require(not any(v in b for v in markers),'PRIVATE_PREFIX_OR_SECRET_MARKER:'+str(p.relative_to(STAGE)));require(p.suffix not in ('.npz','.npy','.log') and p.name not in PRIVATE_NAMES,'PRIVATE_OR_RAW_BODY:'+str(p));scan.append(str(p.relative_to(STAGE)))
 write(STAGE/'PRIVACY_AND_SCOPE_SCAN.json',dict(schema='DECOMPRESSED_PUBLIC_ALLOWLIST_PRIVACY_SCOPE_SCAN_V1',status='PASS',scanned_members=scan,raw_minute_market_source_target_arrays_included=False,private_GO_claim_ownership_and_bootstrap_bodies_included=False,private_absolute_runtime_prefixes_detected=False,accounts_constructed=0,financial_minutes_advanced=0,provider_downloads=0,publication_performed=False))
 manifest(STAGE,source);print(json.dumps({'status':'STAGED_NOT_SEALED','files':len(scan),'stage_directory':str(STAGE.relative_to(W))}),flush=True)

def source_projection(receipt):
 sr=load(receipt)
 require(sr['status']=='PASS' and sr['remote_content_verification']['every_remote_byte_matches_expected_local'] is True,'SOURCE_FULL_REMOTE_BYTES_MUST_BE_VERIFIED')
 require(sr['archive']['SHA256']==SOURCE_ARCHIVE and sr['archive']['bytes']==696892,'EXACT_2021_SOURCE_ARCHIVE_REQUIRED')
 require(sr['parent_commit']=='bf2b1d40df9958033e7d61c38c5b8f343127771b','SOURCE_MUST_BE_CHILD_OF_VERIFIED_MONITOR_RESULTS')
 require(type(sr['commit']) is str and len(sr['commit'])==40 and type(sr['parent_commit']) is str and len(sr['parent_commit'])==40,'FULL_EXACT_COMMITS_REQUIRED')
 return dict(schema='VERIFIED_PARTIAL2021_SOURCE_BEFORE_RESULTS_REFERENCE_V1',status='FULL_REMOTE_BYTES_VERIFIED',source_commit=sr['commit'],source_parent_commit=sr['parent_commit'],source_archive_sha256=SOURCE_ARCHIVE,source_archive_bytes=696892,source_independent_packet_review_sha256='ea701c7ef110aa404301215242b3fcf412df126cb240d173f1f6a3abcb8ca63e',full_private_publication_receipt_sha256=digest(receipt),verified_remote_source_link=sr['packet_readme_url'],every_remote_byte_matches_expected_local=True,results_publication_must_be_additive_child_of_source_commit=True,source_packet_body_not_duplicated=True,no_run_or_publication_authority_granted=True)

def finalize(receipt):
 require(STAGE.exists() and not OUT.exists() and not OUT.with_suffix('.zip').exists(),'STAGE_REQUIRED_AND_FINAL_MUST_NOT_EXIST')
 source=source_projection(receipt)
 # Rehash every original exactly, including omitted arrays, before sealing.
 preserved=load(P/'LOCAL_FULL_RECOVERY_MANIFEST.json')
 for rel,ref in preserved['files'].items():require(same(pin(W/rel),ref),'ORIGINAL_CHANGED_BEFORE_FINAL_SEAL:'+rel)
 for rel,files in preserved['directory_file_sets'].items():require(sorted(str(p.relative_to(W/rel)) for p in (W/rel).rglob('*') if p.is_file() and '__pycache__' not in p.parts)==sorted(files),'ORIGINAL_FILESET_CHANGED:'+rel)
 write(STAGE/'SOURCE_PUBLICATION_REFERENCE.json',source);manifest(STAGE,source)
 from verify_packet import verify
 verification=verify(STAGE)
 # Native generated Python caches are never part of the artifact.
 for p in STAGE.rglob('__pycache__'):shutil.rmtree(p)
 STAGE.rename(OUT)
 archive=OUT.with_suffix('.zip')
 with zipfile.ZipFile(archive,'x',compression=zipfile.ZIP_STORED,allowZip64=True) as z:
  for p in sorted(OUT.rglob('*')):
   if p.is_file():
    info=zipfile.ZipInfo(NAME+'/'+str(p.relative_to(OUT)),date_time=(2026,10,15,0,0,0));info.compress_type=zipfile.ZIP_STORED;info.external_attr=0o100644<<16;z.writestr(info,p.read_bytes())
 size=archive.stat().st_size;parts=[]
 if size>8*1024*1024:
  transport=W/(NAME+'_exact_transport');transport.mkdir()
  with archive.open('rb') as f:
   index=1
   while True:
    b=f.read(8*1024*1024)
    if not b:break
    p=transport/(archive.name+'.part'+str(index).zfill(3));p.write_bytes(b);parts.append(dict(name=p.name,sha256=digest(p),bytes=len(b)));index+=1
  h=hashlib.sha256()
  for rec in parts:
   with (transport/rec['name']).open('rb') as f:
    for b in iter(lambda:f.read(1<<20),b''):h.update(b)
  require(h.hexdigest()==digest(archive),'EXACT_TRANSPORT_CONCAT_SHA_MUST_MATCH')
  write(transport/'TRANSPORT_MANIFEST.json',dict(schema='EXACT_BYTES_SPLIT_ARCHIVE_TRANSPORT_V1',archive=archive.name,archive_sha256=digest(archive),archive_bytes=size,parts=parts,concatenated_ordered_parts_sha256=h.hexdigest(),repacked_or_recompressed_for_transport=False))
 result=dict(schema='NINE_PARTIAL2021_COMPACT_SAVED_RESULTS_ARCHIVE_V1',archive=archive.name,archive_sha256=digest(archive),archive_bytes=size,members=len(load(OUT/'MANIFEST.json')['files'])+1,manifest_sha256=digest(OUT/'MANIFEST.json'),source_verified_commit=source['source_commit'],sole_authorized_results_publication_parent=source['source_commit'],final_financial_review_sha256=FINAL,independent_packet_review='PENDING',transport_parts=parts,originals_rehashed_before_seal=True,publication_performed=False)
 write(OUT.with_suffix('.archive.json'),result);write(P/'AUTHOR_SELF_VERIFICATION.json',verification);print(json.dumps(result),flush=True)
if __name__=='__main__':
 a=argparse.ArgumentParser();a.add_argument('--stage',action='store_true');a.add_argument('--source-receipt');args=a.parse_args()
 for key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS','POLARS_MAX_THREADS','VECLIB_MAXIMUM_THREADS'):os.environ[key]='1'
 os.sched_setaffinity(0,{8})
 if args.stage:stage()
 elif args.source_receipt:finalize(Path(args.source_receipt))
 else:a.error('Use --stage or --source-receipt after exact source publication verification.')
