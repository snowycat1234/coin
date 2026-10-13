"""Lossless project-simulation export; no account import or financial advance."""
from pathlib import Path
import hashlib,json,lzma,shutil
ROOT=Path(__file__).resolve().parent
WORK=ROOT.parent
STATE=WORK/'coin_headroom_process_recovery_20261013/state_recovery_authorized_run'
def sha(b):return hashlib.sha256(b).hexdigest()
def put(raw,path,source=None,transform=None):
 p=ROOT/path;p.parent.mkdir(parents=True,exist_ok=True);p.open('xb').write(raw)
 return {'path':str(path),'size':len(raw),'SHA256':sha(raw),'git_blob_sha':hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest(),'source':source,'transform':transform}
def main():
 rows=[]
 for y in (2021,2023):
  case=f'Y{y}_STATIC50_FINE_HEADROOM';source=STATE/case;target=Path(case)
  for name in ['RESULT.json','BINDING.json','DAILY.csv','MINUTE_NUMERIC.json','TIMING.json']:
   rows.append(put((source/name).read_bytes(),target/name,str((source/name).relative_to(WORK))))
  account=(source/'ACCOUNT.json').read_bytes();compressed=lzma.compress(account,preset=6)
  row=put(compressed,target/'ACCOUNT.json.xz',str((source/'ACCOUNT.json').relative_to(WORK)),'LOSSLESS_XZ_STANDARD_LIBRARY')
  row.update(uncompressed_SHA256=sha(account),uncompressed_size=len(account));rows.append(row)
  for name in ['POINTER.json','STATE_000525600.json.gz','STATE_000518400.json.gz']:
   rows.append(put((source/'recovery'/name).read_bytes(),target/'recovery'/name,str((source/'recovery'/name).relative_to(WORK))))
 report={'status':'PREPARED_LOSSLESS_FINAL_FINANCE_EXPORT_PENDING_INDEPENDENT_POSTRUN_REVIEW','historical_wallets_started_by_export':0,'financial_advances':0,'years':[2021,2023],
 'full_minute_chunk_archive_uploaded':False,'remote_full_minute_cold_supported':False,'scope':'Final and last preterminal day360 complete wallet snapshots and final pointer; compressed original simulation ACCOUNT journals; results/daily/numeric hashes. Referenced DAY chunks are deliberately absent from this package and retained locally.',
 'snapshots_copied_byte_identically':True,'original_account_bytes_recoverable_by_lzma_decompress':True,'files':rows}
 (ROOT/'FINANCE_PACKAGE_MANIFEST.json').open('x').write(json.dumps(report,indent=2)+'\n')
 print(json.dumps({'files':len(rows),'bytes':sum(r['size'] for r in rows),'manifest_SHA256':sha((ROOT/'FINANCE_PACKAGE_MANIFEST.json').read_bytes())}))
if __name__=='__main__':main()
