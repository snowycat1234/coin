"""Git-first trade reuse; only the ten unavailable official mark/fund originals."""
import argparse,json,os,time
from pathlib import Path
import numpy as np
from common import HERE,ROOT,git,digest,sha,save,SYMBOLS,START,END,MINUTE
TRADE='496bf8d545d6834eda35b0bc9802d52db61d42b5';INDEX='research/workspace-recovery-20261011/PUBLIC_RECOVERY_INDEX.json';INDEX_SHA='8cbacf16f7c4477e4ffe4fef528bbf0e207aee13adadae07383f45c52615634c'
def bounds():
 assert START==1767225600000000 and END==1767229200000000 and END<1772323200000000
 lock=ROOT/'state/dataset_lock.json'
 if lock.exists():assert sha(lock)=='29d930063842e9b1666869b4e5f9e3c8cd629313e57b9dadc328c6131b92f45d','Opaque lock SHA changed; stop without parsing'
def configure(state):
 bounds();os.environ.update(WORK_DIR=str(state/'work'),RAW_CACHE_DIR=str(state/'raw'),SYMBOLS=','.join(SYMBOLS),WARMUP_START='2026-01-01',START_DATE='2026-01-01',END_DATE='2026-01-01',FAMILIES='klines,markPriceKlines,fundingRate',HTTP_RETRIES='0',HTTP_CONNECT_TIMEOUT='10',HTTP_READ_TIMEOUT='20',MAX_ARCHIVE_MIB='1',MAX_UNCOMPRESSED_MIB='64',MAX_WORK_GIB='1',MIN_FREE_GIB='15',REFRESH_CHECKSUMS='0')
def trade_body(s):
 raw=git('show',TRADE+':'+INDEX);assert digest(raw)==INDEX_SHA;ix=json.loads(raw);rows=[r for r in ix['raw_official_trade_archives'] if r['symbol']==s and r['official_url']==f'https://data.binance.vision/data/futures/um/monthly/klines/{s}/1m/{s}-1m-2026-01.zip'];assert len(rows)==1;r=rows[0];parts=[]
 for p in r['parts']:
  raw=git('show',TRADE+':'+p['path']);assert len(raw)==p['bytes'] and digest(raw)==p['sha256'];parts.append(raw)
 raw=b''.join(parts);assert len(raw)==r['bytes'] and digest(raw)==r['sha256'];return raw,dict(commit=TRADE,index_SHA256=INDEX_SHA,original_SHA256=r['sha256'],bytes=r['bytes'],URL=r['official_url'])
def build(state,source,public=None):
 assert not state.exists() and not git('status','--porcelain');bounds()
 if public is None:assert git('rev-parse','HEAD').decode().strip()==source
 state.mkdir(parents=True);configure(state)
 from modules.collector_research.pipeline.download import Job,fetch,session,check_zip
 from modules.collector_research.pipeline.normalize import numeric_csv,validate_price,validate_funding,month_limits
 began=time.monotonic();connection=session() if public is None else None;rows=[];events=[];arr=dict(times=np.arange(START,END,MINUTE,dtype=np.int64));newbytes=0
 try:
  for s in SYMBOLS:
   body,proof=trade_body(s);path=state/f'{s}-1m-2026-01.zip';path.write_bytes(body);f,dups=validate_price(numeric_csv(path),'klines',*month_limits(2026,1));path.unlink();f=f[(f.timestamp_ms>=START//1000)&(f.timestamp_ms<END//1000)];assert dups==0;np.testing.assert_array_equal(f.timestamp_ms.to_numpy()*1000,arr['times'])
   for k in ('open','close','quote_volume'):arr[s+'_'+k]=f[k].to_numpy()
   rows.append(dict(symbol=s,family='klines',trade_Git_reused=True,minutes_used=60,**proof));print('TRADE2026JAN1_GIT_REUSED',s,flush=True)
   for family,day in (('markPriceKlines',1),('fundingRate',None)):
    job=Job(s,family,2026,1,day);assert '/2026-01' in job.url and 'data.binance.vision/' in job.url
    if public is None:
     r=fetch(job,connection);assert r['status'] in ('DOWNLOADED_VERIFIED','VERIFIED_CACHE','ADOPTED_VERIFIED_CACHE');newbytes+=r['bytes'];assert newbytes<2000000
    else:
     prior=next(r for r in public['records'] if r['symbol']==s and r['family']==family);parts=[]
     for p in prior['parts']:
      raw=git('show',public['artifact_commit']+':'+p['path']);assert len(raw)==p['bytes'] and digest(raw)==p['SHA256'];parts.append(raw)
     raw=b''.join(parts);assert len(raw)==prior['bytes'] and digest(raw)==prior['SHA256'];job.path.parent.mkdir(parents=True,exist_ok=True);job.path.write_bytes(raw);cp=git('show',public['artifact_commit']+':'+prior['checksum_path']);assert digest(cp)==prior['checksum_SHA256'];Path(str(job.path)+'.CHECKSUM').write_bytes(cp);r=dict(status='PUBLIC_GIT_REUSED',bytes=len(raw),sha256=digest(raw))
    check_zip(job.path);row=dict(symbol=s,family=family,URL=job.url,SHA256=r['sha256'],bytes=r['bytes'],raw_path=str(job.path.relative_to(state)),CRC=True,transport_status=r['status'],checksum_SHA256=sha(Path(str(job.path)+'.CHECKSUM')));rows.append(row)
    if family=='markPriceKlines':
     f,dups=validate_price(numeric_csv(job.path),family,START//1000,(START+1440*MINUTE)//1000);f=f[f.timestamp_ms<END//1000];assert dups==0;np.testing.assert_array_equal(f.timestamp_ms.to_numpy()*1000,arr['times']);arr[s+'_mark']=f.close.to_numpy();row['minutes_used']=60
    else:
     f,dups=validate_funding(numeric_csv(job.path,funding=True),*month_limits(2026,1));f=f[(f.calc_time_ms>=START//1000)&(f.calc_time_ms<=END//1000)];assert dups==0 and len(f)>=1 and int(f.calc_time_ms.iloc[0])*1000==START
     for x in f.itertuples(index=False):events.append(dict(symbol=s,event_us=int(x.calc_time_ms)*1000,raw_rate=float(x.last_funding_rate),reported_interval_hours=float(x.funding_interval_hours)))
     row['actual_events_used']=len(f)
    save(state/'PROGRESS.json',dict(verified_archives=len(rows),new_bytes=newbytes,last=row,new_exit_forks=0,seconds=time.monotonic()-began));assert time.monotonic()-began<300;print('TAIL2026JAN1_SOURCE',s,family,len(rows),flush=True)
  events.sort(key=lambda r:(r['event_us'],r['symbol']));assert len({(r['symbol'],r['event_us']) for r in events})==len(events);np.savez_compressed(state/'INPUTS.npz',symbol_order=np.array(SYMBOLS),**arr);save(state/'EVENTS.json',events)
  report=dict(status='PASS_ACTUAL2026JAN1_FIRST_HOUR_TRADE_MARK_FUND',source_commit=source,calendar=[START,END],records=rows,new_provider_bodies=10 if public is None else 0,new_body_bytes=newbytes,trade_downloads=0,new_exit_forks=0,model_fits=0,INPUTS_SHA256=sha(state/'INPUTS.npz'),EVENTS_SHA256=sha(state/'EVENTS.json'),actual_events=len(events),seconds=time.monotonic()-began,protected_interval_not_opened=True,lock_current_file='NOT_FOUND_PRIOR_SHA_PIN_ONLY')
  save(state/'SOURCE_INDEX.json',report);print('TAIL2026JAN1_SOURCE_READY',60,len(events),newbytes,flush=True)
 except Exception as exc:save(state/'FAILED.json',dict(error=str(exc),HTTP_status=getattr(getattr(exc,'response',None),'status_code',None),verified=len(rows),new_bytes=newbytes,denial_retry=False,new_exit_forks=0));raise
 finally:
  if connection:connection.close()
def publish(state):
 dest=HERE/'source';assert not dest.exists();dest.mkdir();ix=json.loads((state/'SOURCE_INDEX.json').read_text())
 for i,r in enumerate(ix['records']):
  if r['family']=='klines':continue
  raw=(state/r['raw_path']).read_bytes();assert digest(raw)==r['SHA256'];parts=[]
  for j,off in enumerate(range(0,len(raw),786432)):
   p=dest/f'original{i:02d}.part{j:02d}';body=raw[off:off+786432];p.write_bytes(body);parts.append(dict(path=str(p.relative_to(ROOT)),bytes=len(body),SHA256=digest(body)))
  cp=dest/f'original{i:02d}.CHECKSUM';cp.write_bytes(Path(str(state/r['raw_path'])+'.CHECKSUM').read_bytes());r['parts']=parts;r['checksum_path']=str(cp.relative_to(ROOT))
 for n in ('INPUTS.npz','EVENTS.json'):(dest/n).write_bytes((state/n).read_bytes())
 save(dest/'SOURCE_INDEX.json',ix)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--state',type=Path,required=True);p.add_argument('--source-commit',required=True);a=p.parse_args();build(a.state,a.source_commit)
