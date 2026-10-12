"""Recover only unavailable2025 H2 original bodies, matching pre-existing SHA receipts."""
import argparse,hashlib,io,json,os,subprocess,time,zipfile
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
COMMIT='be48f5519c23f0e64eb4d75f8b8358915c254f7b';PREFIX='research/core5-2025-consumer-20261010/'
WRAPPER_SHA='848df602c5db2b4da1e1ba4340f1ebc44a1590364cbcfd2c24a3dc20b093beda'
SYMBOLS=('BTCUSDT','ETHUSDT','SOLUSDT','XRPUSDT','DOGEUSDT')
def sha(raw):return hashlib.sha256(raw).hexdigest()
def git(*args):return subprocess.check_output(['git',*args],cwd=ROOT)
def save(path,obj):path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(obj,sort_keys=True,indent=2)+'\n')
def old_records():
 raw=git('show',COMMIT+':'+PREFIX+'CONSUMER.zip');assert len(raw)==2166970 and sha(raw)==WRAPPER_SHA
 manifest=json.loads(git('show',COMMIT+':'+PREFIX+'MANIFEST.json'));expected={r['path']:r for r in manifest['members']}
 with zipfile.ZipFile(io.BytesIO(raw)) as z:
  assert z.testzip() is None and len(z.namelist())==len(set(z.namelist())) and set(z.namelist())==set(expected)
  raw=z.read('MINUTE_ACQUIRED.json');assert len(raw)==expected['MINUTE_ACQUIRED.json']['bytes'] and sha(raw)==expected['MINUTE_ACQUIRED.json']['SHA256'];p=json.loads(raw)
 assert p['complete'] and len(p['records'])==120
 return [r for r in p['records'] if '2025-07'<=r['month']<='2025-12']
def identity(row):
 assert row['symbol'] in SYMBOLS and row['family'] in ('klines','markPriceKlines') and '2025-07'<=row['month']<='2025-12'
 stem=f"{row['symbol']}-1m-{row['month']}.zip";wanted=f"https://data.binance.vision/data/futures/um/monthly/{row['family']}/{row['symbol']}/1m/{stem}"
 assert row['url']==wanted and len(row['SHA256'])==64 and 0<row['bytes']<=4*2**20
 return stem
def recover(state,source):
 assert not state.exists() and not git('status','--porcelain') and git('rev-parse','HEAD').decode().strip()==source
 rows=old_records();assert len(rows)==60 and sum(r['bytes'] for r in rows)==82770519
 assert len({(r['symbol'],r['family'],r['month']) for r in rows})==60
 for r in rows:identity(r)
 os.environ.update(WORK_DIR=str(state/'work'),RAW_CACHE_DIR=str(state/'raw'),SYMBOLS=','.join(SYMBOLS),WARMUP_START='2025-07-01',START_DATE='2025-07-01',END_DATE='2025-12-31',FAMILIES='klines,markPriceKlines,fundingRate',HTTP_RETRIES='0',HTTP_CONNECT_TIMEOUT='10',HTTP_READ_TIMEOUT='20',MAX_ARCHIVE_MIB='4',MAX_UNCOMPRESSED_MIB='64',MAX_WORK_GIB='1',MIN_FREE_GIB='15',REFRESH_CHECKSUMS='0')
 from modules.collector_research.pipeline.download import Job,fetch,session
 from modules.collector_research.pipeline.normalize import numeric_csv,validate_price,month_limits
 import numpy as np
 state.mkdir(parents=True);began=time.monotonic();connection=session();complete=[];total=0
 try:
  for old in rows:
   y,m=map(int,old['month'].split('-'));job=Job(old['symbol'],old['family'],y,m);assert job.url==old['url'];r=fetch(job,connection)
   assert r['status'] in ('DOWNLOADED_VERIFIED','VERIFIED_CACHE','ADOPTED_VERIFIED_CACHE')
   assert r['sha256']==old['SHA256'] and r['bytes']==old['bytes'],'Original pre-existing body identity changed; stop, no replacement'
   lo,hi=month_limits(y,m);frame,duplicates=validate_price(numeric_csv(job.path),old['family'],lo,hi)
   np.testing.assert_array_equal(frame.timestamp_ms.to_numpy(),np.arange(lo,hi,60000,dtype=np.int64));assert duplicates==0
   total+=r['bytes'];assert total<=90000000 and time.monotonic()-began<900
   complete.append(dict(symbol=old['symbol'],family=old['family'],month=old['month'],URL=job.url,original_SHA256=old['SHA256'],bytes=r['bytes'],raw_path=str(job.path.relative_to(state)),status=r['status'],CRC=True,missing_minutes=0,duplicates=0))
   save(state/'PROGRESS.json',dict(verified=len(complete),planned=60,bytes=total,last=complete[-1],seconds=time.monotonic()-began,new_wallets=0));print('EXACT2025_H2_BODY_RECOVERED',len(complete),60,old['symbol'],old['family'],old['month'],total,flush=True)
  save(state/'SOURCE_INDEX.json',dict(status='PASS_EXACT_ORIGINAL2025_H2_MINUTE_BODIES_NOT_NEW_STRATEGY_OR_SOURCE_VALUES',source_commit=source,original_receipt_commit=COMMIT,original_receipt_wrapper_SHA256=WRAPPER_SHA,records=complete,bytes=total,new_wallets=0,new_fits=0,only_previously_unavailable_bodies_reacquired=True,no_H1_or_funding_or_daily_download=True,seconds=time.monotonic()-began))
 except Exception as exc:
  save(state/'FAILED.json',dict(status='STOP_2025_H2_BODY_RECOVERY',error=str(exc),HTTP_status=getattr(getattr(exc,'response',None),'status_code',None),verified=len(complete),bytes=total,no_denial_retry=True,new_wallets=0,new_fits=0));raise
 finally:connection.close()
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--state',type=Path,required=True);p.add_argument('--source-commit',required=True);a=p.parse_args();recover(a.state,a.source_commit)
