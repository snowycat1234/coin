"""Read only existing raw trade sources; create evidence, never targets or wallets."""
import os
for k in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS','POLARS_MAX_THREADS'):
    os.environ[k]='1'
import resource
resource.setrlimit(resource.RLIMIT_AS,(4*1024**3,4*1024**3))
if hasattr(os,'sched_setaffinity'): os.sched_setaffinity(0,{min(os.sched_getaffinity(0))})
import csv,datetime,hashlib,io,json,time,zipfile
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[2]
OUT=Path(__file__).resolve().parent
S=('BTCUSDT','ETHUSDT','SOLUSDT','XRPUSDT','DOGEUSDT')
DAY=86400000000; MINUTE=60000000
START=1704067200000000; END=1735689600000000
SOURCE=ROOT/'coin_expanded_coverage_20261013'
CUBE=ROOT/'coin_cs_sma_recovery_20261013/inputs/Y2025.npz'
INDEX=SOURCE/'prepared_2024_cold/SOURCE_INDEX.json'
WARM_ROOT=ROOT/'coin_native_half_mix_20261013/prepared_2023'
WARM_INDEX=WARM_ROOT/'SOURCE_INDEX.json'
WARM_PACKAGE_INDEX=ROOT/'coin_native_half_mix_20261013/repo/research/core5-binance-native-2023-data/OCTOBER2023/INDEX.json'
WRAPPERS={
 'H1.zip':'a998b786d781a5dd314c6efb44dc55702972977b9bdf2fea315426b7c4362deb',
 'coin_public_tail_archives_20261008_part01.zip':'10de51c5daed8bcc63e9d2cecbd17146ca2e7c0ab488dea221eab44b920a9bbc',
 'coin_public_tail_archives_20261008_part02.zip':'02c1e379231d388bab4c1df1c3342ef0ccf1582ad6c6e58164ca78a239fa7d4e',
 'coin_public_tail_archives_20261008_part03.zip':'104f03ce110de7003c573a3af5c88f0b19e843c956e45e550ab85af8f429a1e1',
}
sha=lambda x:hashlib.sha256(x).hexdigest()
def fsha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for chunk in iter(lambda:f.read(1048576),b''):h.update(chunk)
 return h.hexdigest()
def bind(p,expected):
 actual=fsha(p)
 if actual!=expected:raise ValueError(f'Source bytes changed: {p}: {actual} != {expected}')
 return {'local_path':str(p.relative_to(ROOT)),'bytes':p.stat().st_size,'SHA256':actual}
def save(p,data):
 with p.open('x') as f:json.dump(data,f,indent=2,sort_keys=True,allow_nan=False);f.write('\n')
def us(y,m,d=1):return int(datetime.datetime(y,m,d,tzinfo=datetime.UTC).timestamp()*1e6)
def limits(y,m):return us(y,m),us(y+(m==12),m%12+1)
def run():
 started=time.monotonic(); records=[]
 cube_record=bind(CUBE,'88a698ceed87603a36ca2bcf4ae76d805aa90085b344bbeee47e58a8c9770add')
 index_record=bind(INDEX,'0b319baf450c8a0f2f89c2a15fdabf2741471bd0ae75aef6f5be1f76cb439c69')
 index=json.loads(INDEX.read_text());warm_index=json.loads(WARM_INDEX.read_text());package_index=json.loads(WARM_PACKAGE_INDEX.read_text())
 if index['symbol_order']!=list(S):raise ValueError('Frozen STATIC50 source order changed')
 wrappers=[bind(SOURCE/n,e) for n,e in WRAPPERS.items()]
 warm_wrapper=bind(WARM_ROOT/'OCTOBER2023.zip','dd466c1dbfdd9bb9d2fb712b40a66f49f4597f1f935b6f81abe483c324acb02a')
 zs={n:zipfile.ZipFile(SOURCE/n) for n in WRAPPERS}
 zdec=zipfile.ZipFile(WARM_ROOT/'OCTOBER2023.zip')
 lookup={n:(label,z) for label,z in zs.items() for n in z.namelist() if n.startswith('tail_data/data/raw/klines/')}
 avail=np.arange(us(2023,12,2),END+DAY,DAY,dtype=np.int64)
 high=np.empty((len(avail),5));low=np.empty_like(high);close=np.empty_like(high);ready=np.zeros_like(high,dtype=bool)
 with np.load(CUBE,allow_pickle=False) as z:
  if tuple(z['symbol_order'])!=S:raise ValueError('STATIC50 cube CORE5 order differs')
  rt=z['close_available_us'];rp=z['close']
  pos=np.searchsorted(rt,avail)
  if np.any(pos==len(rt)) or not np.array_equal(rt[pos],avail):raise ValueError('Risk cube clock coverage absent')
  risk_t=rt[pos].copy();risk_p=rp[pos].copy()
 if not np.isfinite(risk_p).all() or np.any(risk_p<=0):raise ValueError('Original risk cube is invalid')
 bit_parity=0;minute_parity=0;clock_parity=0;full_minute_count=0
 for y,m in [(2023,12)]+[(2024,m) for m in range(1,13)]:
  label=f'{y}-{m:02}';lo,hi=limits(y,m);n=(hi-lo)//MINUTE;days=n//1440
  path=(WARM_ROOT if y==2023 else SOURCE/'prepared_2024_cold')/'months'/f'{label}.npz'
  rec=next(x for x in (warm_index if y==2023 else index)['months'] if x['month']==label)
  prepared_record=bind(path,rec['source_NPZ_SHA256'])
  with np.load(path,allow_pickle=False) as z:
   native_times=z['times'].copy()
   if not np.array_equal(native_times,np.arange(lo,hi,MINUTE,dtype=np.int64)):raise ValueError(f'Native minute clock changed: {label}')
   for j,s in enumerate(S):
    if y==2023:
     member=f'raw/klines/{s}/{s}-1m-{label}.zip';outer=zdec;outer_name='OCTOBER2023.zip'
     expected=next(x for x in package_index['members'] if x['name']==member)['SHA256']
    else:
     member=(f'h1_market/data/raw/klines/{s}/{s}-1m-{label}.zip' if m<=6 else f'tail_data/data/raw/klines/{s}/{s}-1m-{label}.zip')
     if m<=6:outer=zs['H1.zip'];outer_name='H1.zip'
     else:outer_name,outer=lookup[member]
     expected=next(x for x in rec['sources'] if x['symbol']==s and x['family']=='klines')['ZIP_SHA256']
    body=outer.read(member);actual=sha(body);checkbody=outer.read(member+'.CHECKSUM');official=checkbody.decode().split()[0]
    if actual!=expected or actual!=official:raise ValueError(f'Raw trade ZIP SHA mismatch: {label}, {s}')
    with zipfile.ZipFile(io.BytesIO(body)) as inner:
     if len(inner.namelist())!=1:raise ValueError('Unexpected trade ZIP member count')
     csv_name=inner.namelist()[0];csvbody=inner.read(csv_name)
    reader=csv.reader(io.StringIO(csvbody.decode()));header=next(reader)
    expected_header=['open_time','open','high','low','close','volume','close_time','quote_volume','count','taker_buy_volume','taker_buy_quote_volume','ignore']
    if header!=expected_header:raise ValueError(f'Unexpected actual trade schema {label}, {s}: {header}')
    t=np.empty(n,dtype=np.int64);ct=np.empty(n,dtype=np.int64);o=np.empty(n);h=np.empty(n);l=np.empty(n);c=np.empty(n);q=np.empty(n);count=0
    for count,row in enumerate(reader,1):
     if count>n or len(row)!=12:raise ValueError('Unexpected actual row count/schema')
     k=count-1;t[k]=int(row[0])*1000;ct[k]=(int(row[6])+1)*1000
     o[k]=float(row[1]);h[k]=float(row[2]);l[k]=float(row[3]);c[k]=float(row[4]);q[k]=float(row[7])
    if count!=n:raise ValueError(f'Incomplete raw trade minutes: {label}, {s}: {count}/{n}')
    if not np.array_equal(t,native_times) or not np.array_equal(ct,t+MINUTE):raise ValueError(f'Actual raw clock mismatch: {label}, {s}')
    if not np.isfinite(np.column_stack((o,h,l,c,q))).all() or np.any(l<=0) or np.any(q<0) or np.any(l>h) or np.any(l>np.minimum(o,c)) or np.any(h<np.maximum(o,c)):raise ValueError(f'Actual trade HLC invalid: {label}, {s}')
    for kind,a in [('open',o),('close',c),('quote_volume',q)]:
     original=z[s+'_'+kind]
     if original.dtype!=a.dtype or original.tobytes()!=a.tobytes():raise ValueError(f'Actual minute byte parity failed: {label}, {s}, {kind}')
     minute_parity+=n
    clock_parity+=n;full_minute_count+=n
    dt=ct[1439::1440];dh=h.reshape(days,1440).max(axis=1);dl=l.reshape(days,1440).min(axis=1);dc=c[1439::1440]
    ii=np.searchsorted(avail,dt)
    if not np.array_equal(avail[ii],dt):raise ValueError('Actual daily available clock differs')
    if risk_p[ii,j].tobytes()!=dc.tobytes():raise ValueError(f'Daily close bit parity failed: {label}, {s}')
    bit_parity+=days;high[ii,j]=dh;low[ii,j]=dl;close[ii,j]=dc;ready[ii,j]=True
    records.append({'symbol':s,'month':label,'wrapper':outer_name,'member':member,'ZIP_SHA256':actual,'ZIP_bytes':len(body),'CSV_member':csv_name,'CSV_SHA256':sha(csvbody),'CSV_bytes':len(csvbody),'CHECKSUM_SHA256':sha(checkbody),'numeric_rows':n,'daily_bars':days,'schema':header,'first_open_us':int(t[0]),'last_open_us':int(t[-1]),'first_available_us':int(ct[0]),'last_available_us':int(ct[-1]),'true_clock_all_exact':True,'finite_positive_HLC_and_OHLC_bounds':True,'all_close_open_quote_bits_equal_frozen_native':True,'all_completed_daily_close_bits_equal_STATIC50_cube':True,'daily_high_array_SHA256':sha(dh.tobytes()),'daily_low_array_SHA256':sha(dl.tobytes()),'daily_close_array_SHA256':sha(dc.tobytes()),'frozen_prepared_NPZ':prepared_record})
  print('AUDITED_ACTUAL_TRADE_HLC',label,days,'days x5',flush=True)
 if not ready.all() or not np.array_equal(close.view(np.uint64),risk_p.view(np.uint64)):raise ValueError('Daily evidence incomplete or risk close differs')
 decisions=np.arange(START,END,DAY,dtype=np.int64)
 for at in decisions:
  k=int(np.searchsorted(avail,at));r=int(np.searchsorted(risk_t,at))
  if k<20 or r<30 or avail[k]!=at or risk_t[r]!=at:raise ValueError('Original core warmup absent')
  if not ready[k-20:k+1].all() or not np.isfinite(risk_p[r-30:r+1]).all():raise ValueError('Warmup invalid')
 target=OUT/'Y2024_REAL_OHLC.npz'
 if target.exists():raise FileExistsError(target)
 np.savez_compressed(target,symbol_order=np.asarray(S),available_us=avail,high=high,low=low,close=close,ready=ready,risk_t=risk_t,risk_p=risk_p)
 result={'schema':'CORE5_TRUE_TRADE_HLC_SOURCE_GATE_2024_V1','status':'PASS_REAL_CORE5_2024_OHLC_SOURCE_GATE','CORE5':list(S),'evaluation_calendar_us':[START,END],'evaluation_decisions':len(decisions),'evaluation_trade_minutes_per_asset':527040,'warmup_UTC_days':['2023-12-01','2024-01-01'],'warmup_complete_days':31,'all_actual_trade_rows_checked':full_minute_count,'raw_monthly_trade_streams':len(records),'actual_clock_rows_matching_frozen_native':clock_parity,'actual_open_close_quote_cells_bit_matching_frozen_native':minute_parity,'completed_daily_close_cells_bit_matching_STATIC50':bit_parity,'risk_covariance_first_decision_prices':{'count':31,'available_us':[int(risk_t[0]),START],'returns':30},'core_contract_first_decision':{'21_completed_candles_available_us':[int(avail[np.searchsorted(avail,START)-20]),START],'prior20_and_event_days_UTC':['2023-12-11','2023-12-31']},'available_us_semantics':'UTC actual last trade minute close_time_ms+1, times1000; daily max(high),min(low),last(close); never mark or daily-close substitutions','wrappers':wrappers,'warmup_wrapper':warm_wrapper,'STATIC50_source_index':index_record,'STATIC50_risk_close_cube':cube_record,'source_artifact':{'local_path':str(target.relative_to(ROOT)),'SHA256':fsha(target),'bytes':target.stat().st_size,'keys':['symbol_order','available_us','high','low','close','ready','risk_t','risk_p'],'daily_shape':list(high.shape),'first_available_us':int(avail[0]),'last_available_us':int(avail[-1])},'array_SHA256':{k:sha(v.tobytes()) for k,v in {'available_us':avail,'high':high,'low':low,'close':close,'ready':ready,'risk_t':risk_t,'risk_p':risk_p}.items()},'dataset_locator':str(target.relative_to(ROOT)),'dataset_SHA256':fsha(target),'streams':records,'new_historical_wallets':0,'wallets_created':0,'historical_runs':0,'targets_generated':0,'new_market_provider_downloads':0,'Library_calls':0,'uploads':0,'retained_2026_03_09_opened':0,'duration_seconds':time.monotonic()-started,'process_peak_RSS_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,'admission_limits':{'CPU_affinity':list(os.sched_getaffinity(0)),'threads':1,'per_process_AS_bytes':4*1024**3},'caveat':'This passes actual trade HLC and source parity only. Native 2024 mark source retains the exact pre-existing ten derived cells. No market/exchange certification or wallet result is implied.'}
 save(OUT/'SOURCE_GATE.json',result)
 print(json.dumps({k:result[k] for k in ('status','raw_monthly_trade_streams','completed_daily_close_cells_bit_matching_STATIC50','source_artifact','duration_seconds','process_peak_RSS_bytes')}),flush=True)
if __name__=='__main__':
 try:run()
 except Exception as e:
  save(OUT/'SOURCE_STOP.json',{'status':'SOURCE_STOP','error_type':type(e).__name__,'error':str(e),'historical_runs':0,'targets_generated':0,'new_market_provider_downloads':0})
  raise
