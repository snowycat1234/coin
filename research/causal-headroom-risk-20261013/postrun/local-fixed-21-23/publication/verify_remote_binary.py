"""Verify recovered public simulation bytes and decode only; no financial engine."""
from pathlib import Path
import datetime,decimal,gzip,hashlib,json,lzma
P=Path(__file__).resolve().parent
expected=json.loads((P/'REMOTE_BINARY_EXPECTED.json').read_text());manifest=json.loads((P/'FINANCE_PACKAGE_MANIFEST.json').read_text())
sha=lambda b:hashlib.sha256(b).hexdigest()
rows=[]
for i,f in enumerate(expected['files']):
 b=(P/'remote_binary_downloads'/f"{i}_{f['git_blob_sha']}").read_bytes();local=P/f['local_path']
 assert len(b)==f['size'] and sha(b)==f['SHA256'] and b==local.read_bytes()
 row={k:f[k] for k in ['path','size','SHA256','git_blob_sha']};row['actual_remote_bytes_equal_reviewed_local']=True
 raw=lzma.decompress(b) if f['path'].endswith('.xz') else gzip.decompress(b);j=json.loads(raw)
 row.update(raw_size=len(raw),raw_SHA256=sha(raw),compression_decode_and_JSON_parse='PASS')
 if f['path'].endswith('.xz'):
  m=next(m for m in manifest['files'] if m['path']==f['local_path'])
  assert len(raw)==m['uncompressed_size'] and sha(raw)==m['uncompressed_SHA256']
  row['original_ACCOUNT_raw_SHA256_exact']=True
 else:
  assert raw==gzip.decompress(local.read_bytes())
  row['account_clock_us']=j['account']['clock_us'];row['simulator_cursor_us']=j['state']['cursor']
  row['policy_id']=j['protective_policy']['policy_id'];row['feature_binding']=j['protective_policy']['feature_binding']
  if '000525600' in f['path']:
   q={s:j['account']['positions'][s]['quantity'] for s in ['BTCUSDT','ETHUSDT','SOLUSDT','XRPUSDT','DOGEUSDT']}
   assert all(decimal.Decimal(v)==0 for v in q.values());row['CORE5_final_quantities']=q
 rows.append(row)
r={'status':'PASS_ACTUAL_REMOTE_BINARY_BYTES_AND_LOSSLESS_DECODE','repository':'snowycat1234/coin','commit':expected['commit'],
 'retrieval':'FRESH_BARE_GIT_DEPTH1_FILTER_BLOB_NONE_THEN_SIX_KNOWN_PATH_GIT_SHOW_READS_WITH60S_TIMEOUT_NO_NEW_CREDENTIALS',
 'files_verified':6,'compressed_bytes':sum(f['size'] for f in expected['files']),'files':rows,
 'financial_engine_imports':0,'financial_advances':0,'new_historical_wallets':0,
 'remote_complete_minute_cold_supported':False,'referenced730_DAY_chunks_not_in_public_package':True,
 'remote_source_feature_runtime_full_archive_closure_claimed':False,'final_finance_runtime_restore_repeated':False,
 'scope':'Exact remote final/day360 snapshot bytes equal previously independently cold-verified local snapshots. Original ACCOUNT journals losslessly recovered and rawSHA/size matched. This is byte/decode recovery, not a new full-minute cold run.',
 'Contents_range_limiter_failure_retained':'>1MiB Contents fetch_file returns empty content although SHA is present. Normal Git route recovered exact bytes; no reupload or data repair.',
 'verified_at_UTC':datetime.datetime.now(datetime.timezone.utc).isoformat()}
(P/'REMOTE_BINARY_RECOVERY_RECEIPT.json').open('x').write(json.dumps(r,indent=2)+'\n');print(json.dumps({'status':r['status'],'files':6,'bytes':r['compressed_bytes'],'receipt_SHA256':sha((P/'REMOTE_BINARY_RECOVERY_RECEIPT.json').read_bytes())}))
