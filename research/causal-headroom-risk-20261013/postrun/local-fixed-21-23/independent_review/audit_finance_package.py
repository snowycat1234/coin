"""Bounded read-only byte/xz closure. No simulator/account imports or execution."""
from pathlib import Path
import hashlib,json,lzma
H=Path(__file__).resolve().parent;W=H.parent;P=W/'coin_headroom_risk_candidate_postrun_package_20261013'
sha=lambda b:hashlib.sha256(b).hexdigest()
manifest_path=P/'FINANCE_PACKAGE_MANIFEST.json';raw_manifest=manifest_path.read_bytes();manifest_sha=sha(raw_manifest)
assert manifest_sha=='6b53fc16ca7387838465adff0fc9bcbcc13a4905d80dd19762c36342def9b4e9'
m=json.loads(raw_manifest);assert m['years']==[2021,2023] and len(m['files'])==18
assert m['financial_advances']==0 and m['historical_wallets_started_by_export']==0
assert m['full_minute_chunk_archive_uploaded'] is False and m['remote_full_minute_cold_supported'] is False
names=set();verified=[];total=0
for r in m['files']:
 name=r['path'];assert name not in names;names.add(name)
 p=P/name;source=W/r['source'];assert not p.is_symlink() and not source.is_symlink()
 b=p.read_bytes();original=source.read_bytes();assert len(b)==r['size'] and sha(b)==r['SHA256']
 assert hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()==r['git_blob_sha']
 if r['transform'] is None:assert b==original;method='EXACT_BYTES'
 else:
  assert r['transform']=='LOSSLESS_XZ_STANDARD_LIBRARY'
  recovered=lzma.decompress(b);assert recovered==original and len(recovered)==r['uncompressed_size'] and sha(recovered)==r['uncompressed_SHA256'];method='XZ_RECOVERS_EXACT_ORIGINAL_BYTES'
 total+=len(b);verified.append({'path':name,'bytes':len(b),'SHA256':sha(b),'verified_method':method})
missing=0;cases=[]
for year in [2021,2023]:
 case=f'Y{year}_STATIC50_FINE_HEADROOM';root=P/case
 pointer=json.loads((root/'recovery/POINTER.json').read_text());result=json.loads((root/'RESULT.json').read_text());binding=json.loads((root/'BINDING.json').read_text())
 assert pointer['binding']==binding and pointer['completed_minutes']==525600
 assert pointer['state_hash']==result['genuine_state_hash'] and len(pointer['chunks'])==365
 assert pointer['snapshot_path']=='STATE_000525600.json.gz'
 assert sha((root/'recovery'/pointer['snapshot_path']).read_bytes())==pointer['snapshot_SHA256']
 absent=[r['path'] for r in pointer['chunks'] if not (root/'recovery'/r['path']).exists()]
 assert len(absent)==365;missing+=len(absent)
 assert (root/'recovery/STATE_000518400.json.gz').is_file()
 cases.append({'case_id':case,'pointer_RESULT_genuine_state_hash_equal':True,'final_snapshot_bytes_and_pointer_SHA_equal':True,'last_preterminal_day360_snapshot_exact_source_bytes':True,'deliberately_missing_DAY_chunk_files':len(absent)})
assert missing==730
out={'status':'PASS_INDEPENDENT_LOSSLESS_COMPACT_FINANCE_PACKAGE_BYTES','package_manifest_SHA256':manifest_sha,'package_export_code_SHA256':sha((P/'prepare_finance_package.py').read_bytes()),'verified_file_count':18,'verified_total_bytes':total,'verified_account_xz_count':2,'samebyte_file_count':16,'case_identity_closure':cases,'files':verified,'full_minute_chunk_archive_uploaded':False,'remote_full_minute_cold_supported':False,'deliberately_missing_SHA_referenced_DAY_chunks':730,'scope':'Exact final/day360 snapshots, pointer and raw ACCOUNT journals plus results/daily/numeric hash manifests. No claim of standalone public runtime/source/feature archive closure or complete minute cold restore; all730 numeric day chunks remain local.','financial_advances':0,'new_historical_wallets_executed':0,'cold_restore_executions':0,'economic_result_validation_by_this_byte_audit':False}
with (H/'FINANCE_PACKAGE_REVIEW_RECEIPT.json').open('x') as f:json.dump(out,f,indent=2,sort_keys=True);f.write('\n')
(P/'FINANCE_PACKAGE_REVIEW_RECEIPT.json').write_bytes((H/'FINANCE_PACKAGE_REVIEW_RECEIPT.json').read_bytes())
print(json.dumps({k:v for k,v in out.items() if k!='files'},indent=2,sort_keys=True));print('RECEIPT_SHA256',sha((H/'FINANCE_PACKAGE_REVIEW_RECEIPT.json').read_bytes()))
