"""Restore exact public 2025 source blocks only; no target generation or wallet."""
import importlib.util,io,json,os,sys,time,zipfile
from pathlib import Path
from recover import STATE,get,jsonget,sha,write
S=('BTCUSDT','ETHUSDT','SOLUSDT','XRPUSDT','DOGEUSDT');DAY=86400000000
ART='af6d8e1426c663f3d5afb2da311755487681c232';H1='d69e9ac94478c5be54cb46c622afec7aaf3c61f7'
def enc(x):return (json.dumps(x,sort_keys=True,indent=2,allow_nan=False)+'\n').encode()
def wrap(c,p,index):
 raw=b''.join(get(c,p+r['file_name'],r['sha256']) for r in index['parts']);assert len(raw)==index['original_bytes'] and sha(raw)==index['original_sha256']
 # Read only explicitly selected 2025 price members. ZIP.read validates member CRC.
 return zipfile.ZipFile(io.BytesIO(raw))
def main():
 begun=time.monotonic();out=STATE/'prepared_2025';out.mkdir(exist_ok=True);(out/'months').mkdir(exist_ok=True)
 assert not (out/'RESTORE_RECEIPT.json').exists()
 os.sched_setaffinity(0,{sorted(os.sched_getaffinity(0))[2]})
 root=STATE/'pinned-repo';sys.path[:0]=[str(root),str(root/'src')]
 os.environ.update(CONFIG_FILE='/dev/null',WORK_DIR=str(out/'work'),RAW_CACHE_DIR=str(out/'raw'),MAX_UNCOMPRESSED_MIB='64',MIN_FREE_GIB='15')
 import numpy as np
 from modules.collector_research.pipeline.normalize import numeric_csv,validate_price,month_limits
 index=jsonget(ART,'research/portfolio-risk-2025-native-20261012/input/SOURCE_INDEX.json')
 prefix='research_artifacts/frozen_e5_2025h1_20261008/';frozen=wrap(H1,prefix,jsonget(H1,prefix+'INDEX.json'));print('2025_H1_PUBLIC_WRAPPER_READY',flush=True)
 prefix='research_artifacts/native_20261008/';tailsmeta=jsonget(H1,prefix+'INDEX.json')['market_archives_layout']['original_archives']
 # Fetch only wrapper(s) whose metadata admits the genuine January2025 members.
 tails=[wrap(H1,prefix+'byteparts/',dict(r,parts=r['parts'])) for r in tailsmeta]
 print('2025_JAN_PUBLIC_WRAPPERS_READY',flush=True)
 hp='research/portfolio-risk-2025-admission-20261012/original-H2/';h2=jsonget(ART,hp+'INDEX.json');assert h2['body_bytes']==82770519
 consumer_c='be48f5519c23f0e64eb4d75f8b8358915c254f7b';consumer_p='research/core5-2025-consumer-20261010/';raw=get(consumer_c,consumer_p+'CONSUMER.zip','848df602c5db2b4da1e1ba4340f1ebc44a1590364cbcfd2c24a3dc20b093beda')
 cm=jsonget(consumer_c,consumer_p+'MANIFEST.json');expected={r['path']:r for r in cm['members']}
 with zipfile.ZipFile(io.BytesIO(raw)) as z:
  name='features2025/FEATURES.npz';raw=z.read(name);assert sha(raw)==expected[name]['SHA256']
 with np.load(io.BytesIO(raw),allow_pickle=False) as a:
  clocks=a['completed_day_available_us'];assert clocks.max()<1772323200000000
  prices=a['close'];assert tuple(a['symbol_order'])==S
 daily=[];previous={}
 for month in index['months']:
  stamp=month['month'];m=int(stamp[-2:]);lo,hi=month_limits(2025,m);arrays=dict(times=np.arange(lo*1000,hi*1000,60000000,dtype=np.int64))
  for r in month['sources']:
   s,f=r['symbol'],r['family'];stem=f'{s}-1m-{stamp}.zip'
   if m==1:
    name=f'tail_data/data/raw/{f}/{s}/{stem}';matches=[z for z in tails if name in z.namelist()];assert len(matches)==1;body=matches[0].read(name)
   elif m<=6:body=frozen.read(f'market/data/raw/{f}/{s}/{stem}')
   else:
    row=next(v for v in h2['archives'] if v['raw_path']==f'raw/{f}/{s}/{stem}')
    body=b''.join(get(ART,hp+p['file'],p['SHA256']) for p in row['parts']);assert sha(body)==row['SHA256']
    check=get(ART,hp+row['checksum_file'],row['checksum_SHA256']);assert check.decode().split()[0]==sha(body)
   assert len(body)==r['bytes'] and sha(body)==r['original_SHA256']
   path=out/'raw'/f/s/stem;write(path,body);frame,dup=validate_price(numeric_csv(path),f,lo,hi);assert dup==0
   np.testing.assert_array_equal(frame.timestamp_ms.to_numpy()*1000,arrays['times'])
   if f=='klines':
    for k in ('open','close','quote_volume'):arrays[s+'_'+k]=frame[k].to_numpy()
    j=S.index(s)
    for i,at in enumerate(range(lo*1000,hi*1000,DAY)):
     k=int(np.searchsorted(clocks,at));assert clocks[k]==at
     value=float(prices[k,j]) if at==index['calendar'][0] else (previous[s] if i==0 else float(frame.close.iloc[i*1440-1]))
     assert abs(value-prices[k,j])<=1e-12*abs(value);daily.append(dict(symbol=s,close_us=at,close=value))
    previous[s]=float(frame.close.iloc[-1])
   else:arrays[s+'_mark']=frame.close.to_numpy()
  path=out/'months'/(stamp+'.npz');np.savez_compressed(path,**arrays);assert sha(path.read_bytes())==month['source_NPZ_SHA256'],stamp
  print('SOURCE2025_MONTH',stamp,'EXACT_ORIGINAL_NPZ',flush=True)
 frozen.close()
 for z in tails:z.close()
 body=enc(daily);assert sha(body)==index['files']['DAILY.json']['SHA256'];write(out/'DAILY.json',body)
 # Call the original raw-event reader, with Git transport redirected only to
 # the existing pinned Git byte cache; no model/target routine is invoked.
 base=STATE/'source2025-api';base.mkdir(exist_ok=True);prefix='research/portfolio-risk-2025-admission-20261012/'
 for n in ('source2025.py','recover_h2.py'):write(base/n,get(ART,prefix+n))
 sys.path.insert(0,str(base));spec=importlib.util.spec_from_file_location('original_2025_source_functions',base/'source2025.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
 def public_git(*args):
  assert len(args)==2 and args[0]=='show';c,p=args[1].split(':',1);return get(c,p)
 module.git=public_git
 events,proof=module.funding(out);body=enc(events);assert sha(body)==index['files']['EVENTS.json']['SHA256'];write(out/'EVENTS.json',body)
 write(out/'SOURCE_INDEX.json',get(ART,'research/portfolio-risk-2025-native-20261012/input/SOURCE_INDEX.json'))
 write(out/'RESTORE_RECEIPT.json',enc(dict(status='PASS_EXACT_MONTHS_EVENTS_DAILY',seconds=time.monotonic()-begun,source_commit=ART,financial_constructions=0,account_advances=0,fits=0,new_targets=0,provider_downloads=0)))
 print('SOURCE2025_COMPLETE',time.monotonic()-begun,flush=True)
if __name__=='__main__':main()
