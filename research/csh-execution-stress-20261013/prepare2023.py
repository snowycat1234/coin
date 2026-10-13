"""Recover admitted 2023 tape bytes and raw events; no targets/fits/wallets."""
import gzip,hashlib,importlib.util,io,json,os,sys,zipfile,time
from pathlib import Path
from recover import STATE,REPO,get,jsonget,sha,write
S=('BTCUSDT','ETHUSDT','SOLUSDT','XRPUSDT','DOGEUSDT');DAY=86400000000
COMMIT='a4dbb6ded845a70d48a7c1d16e9c4a5b18034377';PREFIX='research/cs-2023-continuous-economics-20261012/'

def encoded(x):return (json.dumps(x,sort_keys=True,indent=2,allow_nan=False)+'\n').encode()
def wrapper(c,p,index):
 raw=b''.join(get(c,p+r['name'],r['SHA256']) for r in index['parts']);assert len(raw)==index['package_bytes'] and sha(raw)==index['package_SHA256']
 z=zipfile.ZipFile(io.BytesIO(raw));assert z.testzip() is None
 return z

def main():
 begun=time.monotonic();out=STATE/'prepared_2023';out.mkdir(exist_ok=True);(out/'months').mkdir(exist_ok=True);os.sched_setaffinity(0,{sorted(os.sched_getaffinity(0))[1]})
 assert not (out/'RESTORE_RECEIPT.json').exists(),'Completed source is immutable'
 code=STATE/'pinned-repo';sys.path[:0]=[str(code),str(code/'src')];os.environ.update(CONFIG_FILE='/dev/null',WORK_DIR=str(out/'work'),RAW_CACHE_DIR=str(out/'raw'),MAX_UNCOMPRESSED_MIB='64',MAX_ARCHIVE_MIB='8',MIN_FREE_GIB='15')
 # Reuse the original checksum/CRC/round-trip numeric parser and exact daily union.
 py=STATE/'source2023.py';write(py,get(COMMIT,PREFIX+'source.py'))
 spec=importlib.util.spec_from_file_location('original_2023_source_parser',py);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
 import numpy as np
 index=jsonget(COMMIT,PREFIX+'source-result/SOURCE_INDEX.json');proto=jsonget(COMMIT,PREFIX+'PROTOCOL.json')
 wrappers={}
 for fold in ('JULY2023','OCTOBER2023'):
  c=proto['source']['reused_H2_commit'];p=proto['source']['reused_H2_base']+fold+'/'
  wrappers[fold]=wrapper(c,p,jsonget(c,p+'INDEX.json'))
 def quarter_raw(c,row):
  raw=b''.join(get(c,p['path'],p['SHA256']) for p in row['parts']);assert len(raw)==row['ZIP_bytes'] and sha(raw)==row['ZIP_SHA256']
  check=get(c,row['checksum_path'],row['CHECKSUM_SHA256']);assert check.decode().split()[0]==sha(raw)
  return raw,check
 for month in index['months']:
  stamp=month['month'];arrays={}
  existing=out/'months'/(stamp+'.npz')
  if existing.exists():
   assert sha(existing.read_bytes())==month['source_NPZ_SHA256']
   print('SOURCE2023_MONTH_REUSED',stamp,flush=True)
   continue
  from modules.collector_research.pipeline.normalize import month_limits
  lo,hi=month_limits(*map(int,stamp.split('-')));arrays['times']=np.arange(lo*1000,hi*1000,60000000,dtype=np.int64)
  for r in month['sources']:
   s,f=r['symbol'],r['family'];desc=r['source']
   if 'artifact_commit' in desc:body,check=quarter_raw(desc['artifact_commit'],desc['source'])
   else:
    fold='JULY2023' if int(stamp[-2:])<=9 else 'OCTOBER2023';body=wrappers[fold].read(desc['member']);check=wrappers[fold].read(desc['member']+'.CHECKSUM')
    assert len(body)==desc['ZIP_bytes'] and sha(body)==desc['ZIP_SHA256'] and sha(check)==desc['CHECKSUM_SHA256']
   path=out/'raw'/f/s/(s+'-1m-'+stamp+'.zip');write(path,body);write(Path(str(path)+'.CHECKSUM'),check)
   frame=module.checked_frame(path,f,stamp)
   for repair in desc.get('repairs',[]):
    dr=repair['source'];body,check=quarter_raw(desc['artifact_commit'],dr);rp=out/'raw'/f/s/Path(dr['raw_path']).name;write(rp,body);write(Path(str(rp)+'.CHECKSUM'),check)
    df=module.checked_frame(rp,f,dr['source_period']);frame,e=module.union_exact(frame,df,f,lo,hi);assert e=={k:v for k,v in repair.items() if k!='source'}
   np.testing.assert_array_equal(frame.timestamp_ms.to_numpy()*1000,arrays['times'])
   if f=='klines':
    for k in ('open','close','quote_volume'):arrays[s+'_'+k]=frame[k].to_numpy()
   else:arrays[s+'_mark']=frame.close.to_numpy()
  path=out/'months'/(stamp+'.npz');np.savez_compressed(path,**arrays);assert sha(path.read_bytes())==month['source_NPZ_SHA256'],stamp
  print('SOURCE2023_MONTH',stamp,'EXACT_ORIGINAL_NPZ',flush=True)
 for z in wrappers.values():z.close()
 # Recover raw event records from the genuine published source-bound completed
 # snapshot. Merely decompress JSON: no account construction or advance.
 c='1e8d48cace06519bd090054afffef1eb802e2107';p='research/native-lossless-2023-20261013/'
 ix=jsonget(c,p+'PUBLIC_INDEX.json');row=next(r for r in ix['files'] if r['reconstructed_path']=='STATE_000525600.json.gz')
 raw=b''.join(get(c,p+a['path'],a['SHA256']) for a in row['parts']);assert len(raw)==row['bytes'] and sha(raw)==row['SHA256']
 snapshot=json.loads(gzip.decompress(raw));assert snapshot['market_range']==index['calendar'] and snapshot['state']['rows_written']==525600
 events=[{k:r[k] for k in ('symbol','event_us','raw_rate','reported_interval_hours')} for r in snapshot['state']['funding_journal']];assert len(events)==5475
 body=encoded(events);assert sha(body)==index['files']['EVENTS.json']['SHA256'];write(out/'EVENTS.json',body)
 cube=get(COMMIT,proto['daily_cube'],proto['daily_cube_SHA256']);write(STATE/'inputs/daily_cube2023.npz',cube)
 with np.load(io.BytesIO(cube),allow_pickle=False) as a:
  t=a['close_available_us'];p=a['close'];daily=[];previous={}
  for month in index['months']:
   with np.load(out/'months'/(month['month']+'.npz'),allow_pickle=False) as raw:
    first=int(raw['times'][0]);last=int(raw['times'][-1])+60000000
    for j,s in enumerate(S):
     closes=raw[s+'_close']
     for i,at in enumerate(range(first,last,DAY)):
      k=int(np.searchsorted(t,at));assert t[k]==at
      value=float(p[k,j]) if at==index['calendar'][0] else (previous[s] if i==0 else float(closes[i*1440-1]))
      daily.append(dict(symbol=s,close_us=at,close=value))
     previous[s]=float(closes[-1])
 body=encoded(daily);assert sha(body)==index['files']['DAILY.json']['SHA256'];write(out/'DAILY.json',body)
 write(out/'SOURCE_INDEX.json',get(COMMIT,PREFIX+'source-result/SOURCE_INDEX.json'))
 write(out/'RESTORE_RECEIPT.json',encoded(dict(status='PASS_EXACT_MONTHS_EVENTS_DAILY',seconds=time.monotonic()-begun,source_commit=COMMIT,raw_events_source_snapshot_commit=c,financial_constructions=0,account_advances=0,fits=0,new_targets=0,provider_downloads=0)))
 print('SOURCE2023_COMPLETE',time.monotonic()-begun,flush=True)
if __name__=='__main__':main()
