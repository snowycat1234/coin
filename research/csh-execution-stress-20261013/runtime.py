"""Byte-bound financial imports and exact already-frozen target/source inputs."""
import hashlib,importlib.util,json,os,sys
from pathlib import Path
from recover import STATE,REPO
SYMBOLS=('BTCUSDT','ETHUSDT','SOLUSDT','XRPUSDT','DOGEUSDT');DAY=86400000000

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def load(name,path):
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);sys.modules[name]=m;s.loader.exec_module(m);return m

def finance():
 assert not sys.flags.optimize
 root=STATE/'pinned-repo';sys.path[:0]=[str(root),str(root/'src'),str(STATE/'fine-code')]
 os.environ.update(QUANT_ROOT=str(root),QUANT_STATE=str(STATE),CONFIG_FILE='/dev/null')
 port=load('exact_public_frozen_transport',root/'research/static50-sma-20261013/local_native_apis.py');port.verify()
 fine=load('exact_public_fine_account',STATE/'fine-code/fine_account.py')
 return port,fine.FineGridAccount

def source(year,port):
 import numpy as np
 folder=STATE/f'prepared_{year}';index=json.loads((folder/'SOURCE_INDEX.json').read_text())
 original=json.loads((Path(__file__).parent/'SOURCE_BINDINGS.json').read_text())[str(year)]['source_index']
 for name in ('EVENTS.json','DAILY_OHLC.npz' if year==2021 else 'DAILY.json'):
  assert sha(folder/name)==original['files'][name]['SHA256'],name
 start,end=index.get('calendar',index.get('calendar_us'));assert end<=1772323200000000
 assert start==int(__import__('datetime').datetime(year,1,1,tzinfo=__import__('datetime').UTC).timestamp()*1e6)
 if year==2021:
  assert sha(STATE/'inputs/Y2023.npz')=='1c500e9d5b0244a1daaabc597d7cc5ae97a21a156cc42d8a44a1504b821e599f'
  with np.load(STATE/'inputs/Y2023.npz',allow_pickle=False) as cube:
   k=int(np.searchsorted(cube['close_available_us'],start));assert cube['close_available_us'][k]==start;first=cube['close'][k].copy()
  with np.load(folder/'DAILY_OHLC.npz',allow_pickle=False) as a:
   clocks=np.r_[start,a['available_us']];values=np.vstack([first,a['close']])
  np.testing.assert_array_equal(clocks,np.arange(start,end+DAY,DAY))
  daily=port.native.pl.DataFrame([dict(symbol=s,close_us=int(t),close=float(values[i,j])) for i,t in enumerate(clocks) for j,s in enumerate(SYMBOLS)])
 else:daily=port.native.pl.DataFrame(json.loads((folder/'DAILY.json').read_text()))
 events=json.loads((folder/'EVENTS.json').read_text());assert len(events)==5475
 for e in events:assert start<=e['event_us']<end and e['symbol'] in SYMBOLS
 def blocks():
  for r in index['months']:
   path=folder/'months'/(r['month']+'.npz');assert sha(path)==r['source_NPZ_SHA256'] and path.stat().st_size==r['source_NPZ_bytes']
   with np.load(path,allow_pickle=False) as a:
    times=a['times'].copy();market={s:{k:a[s+'_'+k].copy() for k in ('open','close','quote_volume','mark')} for s in SYMBOLS}
   for off in range(0,len(times),1440):yield dict(times=times[off:off+1440],market={s:{k:v[off:off+1440] for k,v in row.items()} for s,row in market.items()})
 return dict(start=start,end=end,symbols=SYMBOLS,daily=daily,events=events,minute_blocks=blocks)

def target_factory(year,port):
 import numpy as np
 with np.load(STATE/'targets'/f'Y{year}.npz',allow_pickle=False) as a:
  clocks=a['decision_us'].copy();w=a['STATIC50'].copy();assert tuple(a['symbol_order'])==SYMBOLS
 def factory(_daily,decisions,mode):
  np.testing.assert_array_equal(decisions,clocks);assert mode=='LONG_SHORT'
  return port.native.pl.DataFrame([dict(available_us=int(t),symbol=s,target_weight=float(w[i,j])) for i,t in enumerate(clocks) for j,s in enumerate(SYMBOLS)]),dict(kind='EXACT_ARCHIVED_STATIC50_NO_REGENERATION',archive_sha256=sha(STATE/'targets'/f'Y{year}.npz'),target_array_sha256=hashlib.sha256(w.tobytes()).hexdigest())
 return factory
if __name__=='__main__':
 p,f=finance();print('FINANCIAL_CODE_VERIFIED',f.VERSION)
