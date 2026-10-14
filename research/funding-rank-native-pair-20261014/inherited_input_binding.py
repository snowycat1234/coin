"""Pure input transport. No financial imports, wallets, targets or launch capability."""
import argparse,hashlib,json,re
from pathlib import Path
S=('BTCUSDT','ETHUSDT','SOLUSDT','XRPUSDT','DOGEUSDT')
MINUTE=60000000; DAY=86400000000
SEED_SHA='1c500e9d5b0244a1daaabc597d7cc5ae97a21a156cc42d8a44a1504b821e599f'
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def safe(root,name):
 p=Path(name)
 if p.is_absolute() or '..' in p.parts:raise ValueError('project-relative input name required')
 return Path(root)/p
def check_file(root,name,rec):
 p=safe(root,name)
 if p.stat().st_size!=rec['bytes'] or sha(p)!=rec['SHA256']:raise ValueError('INPUT_BYTES_CHANGED:'+name)
 return p
def schema(z,start,count,full_ohlc=False):
 import numpy as np
 expected={'times',*[s+'_'+k for s in S for k in ('open','close','quote_volume','mark')]}
 if full_ohlc:expected|={'available_us',*[s+'_'+k for s in S for k in ('high','low','volume','mark_open','mark_high','mark_low')]}
 if set(z.files)!=expected:raise ValueError('MONTH_FIELDS_CHANGED')
 t=z['times']
 if t.dtype!=np.dtype('int64') or t.shape!=(count,):raise ValueError('CLOCK_SCHEMA_CHANGED')
 np.testing.assert_array_equal(t,np.arange(start,start+count*MINUTE,MINUTE,dtype=np.int64))
 if full_ohlc:
  np.testing.assert_array_equal(z['available_us'],t+MINUTE)
  if z['available_us'].dtype!=np.dtype('int64'):raise ValueError('AVAILABLE_CLOCK_SCHEMA_CHANGED')
 for k in expected-{'times','available_us'}:
  a=z[k]
  if a.dtype!=np.dtype('float64') or a.shape!=(count,) or not np.isfinite(a).all():raise ValueError('VALUE_SCHEMA_CHANGED:'+k)
def registry(path=None):return json.loads(Path(path or Path(__file__).with_name('INPUT_BINDINGS.json')).read_text())
def verify_source(year,source_root,bindings=None,seed_close_cube=None):
 import numpy as np
 r=(bindings or registry())['years'][str(year)]
 check_file(source_root,'SOURCE_INDEX.json',r['index'])
 j=json.loads(safe(source_root,'SOURCE_INDEX.json').read_text())
 if j.get('calendar',j.get('calendar_us'))!=r['calendar'] or tuple(j.get('symbol_order',j.get('symbols')))!=S:raise ValueError('CALENDAR_OR_ORDER_CHANGED')
 for name,rec in r['required_files'].items():check_file(source_root,name,rec)
 events=json.loads(safe(source_root,'EVENTS.json').read_text())
 if len(events)!=r['funding_events']:raise ValueError('FUNDING_COUNT_CHANGED')
 for e in events:
  if e['symbol'] not in S or not r['calendar'][0]<=e['event_us']<r['calendar'][1]:raise ValueError('FUNDING_BOUNDARY_CHANGED')
 expected=r['calendar'][0]
 for m in r['months']:
  p=check_file(source_root,'months/'+m['month']+'.npz',{'SHA256':m['source_NPZ_SHA256'],'bytes':m['source_NPZ_bytes']})
  with np.load(p,allow_pickle=False) as z:schema(z,expected,m['minutes'],full_ohlc=(year==2021))
  expected+=m['minutes']*MINUTE
 if expected!=r['calendar'][1]:raise ValueError('YEAR_COVERAGE_CHANGED')
 if year==2021:
  if seed_close_cube is None or sha(seed_close_cube)!=SEED_SHA:raise ValueError('ORIGINAL_2021_SEED_CLOSE_REQUIRED')
 if r['identity_status']!='PASS':raise ValueError(r['identity_status'])
 return {'source':'PASS','year':year,'months':12,'funding_events':len(events),'derived_mark_cells':r['derived_mark_cells']}
def source_window(year,source_root,seed_close_cube=None):
 """Native-window-shaped input view; daily is records, wrap externally in original pl.DataFrame.
 No scheduler/account import. Target factory remains external and unbound.
 """
 import numpy as np
 verify_source(year,source_root,seed_close_cube=seed_close_cube)
 r=registry()['years'][str(year)];start,end=r['calendar']
 if year==2021:
  with np.load(seed_close_cube,allow_pickle=False) as z:
   k=int(np.searchsorted(z['close_available_us'],start))
   if int(z['close_available_us'][k])!=start:raise ValueError('SEED_CLOSE_CLOCK_CHANGED')
   first=z['close'][k].copy()
  with np.load(safe(source_root,'DAILY_OHLC.npz'),allow_pickle=False) as z:
   clocks=np.r_[start,z['available_us']];prices=np.vstack([first,z['close']])
  np.testing.assert_array_equal(clocks,np.arange(start,end+DAY,DAY,dtype=np.int64))
  daily=[dict(symbol=s,close_us=int(t),close=float(prices[i,j])) for i,t in enumerate(clocks) for j,s in enumerate(S)]
 else:daily=json.loads(safe(source_root,'DAILY.json').read_text())
 def blocks():
  for m in r['months']:
   p=check_file(source_root,'months/'+m['month']+'.npz',{'SHA256':m['source_NPZ_SHA256'],'bytes':m['source_NPZ_bytes']})
   with np.load(p,allow_pickle=False) as z:
    times=z['times'].copy();market={s:{k:z[s+'_'+k].copy() for k in ('open','close','quote_volume','mark')} for s in S}
   for off in range(0,len(times),1440):yield dict(times=times[off:off+1440],market={s:{k:v[off:off+1440] for k,v in d.items()} for s,d in market.items()})
 return dict(start=start,end=end,symbols=S,daily=daily,events=json.loads(safe(source_root,'EVENTS.json').read_text()),minute_blocks=blocks)
def target_gate(binding=None):
 # Future exact-target contract not supplied: never accept arbitrary old archives.
 if binding is None:return 'WAITING_TARGET_BINDING / NO_GO'
 raise ValueError('FUTURE_TARGET_CONTRACT_NOT_PREREGISTERED / NO_GO')
def verify_engine(root,pins):
 for name,rec in pins.items():check_file(root,name,rec)
 return 'PASS_BYTE_EXACT_NO_IMPORT'
def main():
 p=argparse.ArgumentParser();p.add_argument('--year',type=int,choices=(2021,2023,2024,2025),required=True);p.add_argument('--source-root',required=True);p.add_argument('--seed-close-cube');p.add_argument('--engine-root',required=True);p.add_argument('--check-only',action='store_true',required=True)
 a=p.parse_args();r=registry();verify_engine(a.engine_root,r['engine_files'])
 try:result=verify_source(a.year,a.source_root,seed_close_cube=a.seed_close_cube)
 except Exception as e:result={'source':'BLOCKED','error':str(e)}
 print(json.dumps({'input':result,'targets':target_gate(),'historical_execution':'NO_GO','wallets_constructed':0}));return 3
if __name__=='__main__':raise SystemExit(main())
