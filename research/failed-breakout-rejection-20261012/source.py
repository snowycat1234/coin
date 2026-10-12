"""Bounded Git-only real OHLC projections and exact existing economics inputs."""
import argparse,hashlib,importlib.util,io,json,subprocess,time,zipfile
from pathlib import Path
import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
from core import DAY,SYMBOLS,ROOT
HERE=Path(__file__).resolve().parent
def sha(b):return hashlib.sha256(b).hexdigest()
def save(p,o):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(o,sort_keys=True,indent=2,allow_nan=False)+'\n')
def git(s):return subprocess.check_output(['git','show',s],cwd=ROOT)
def load(name,path):
 spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
def feature_archive():
 c='e0d3400b23842f11f167a63e7d80856d76501de8';prefix='research/temporal-feature-data-20261009/';ix=json.loads(git(c+':'+prefix+'INDEX.json'));parts=[]
 for r in ix['parts']:
  b=git(c+':'+prefix+r['file']);assert len(b)==r['bytes'] and sha(b)==r['SHA256'];parts.append(b)
 b=b''.join(parts);assert len(b)==ix['bytes'] and sha(b)==ix['SHA256'];z=zipfile.ZipFile(io.BytesIO(b));assert z.testzip() is None;members=json.loads(z.read('MEMBERS.json'))['files']
 def read(name):
  b=z.read(name);assert len(b)==members[name]['bytes'] and sha(b)==members[name]['SHA256'];return b
 return z,read,dict(commit=c,archive_SHA256=ix['SHA256'])
def economics():
 c='53357f33f4e6ccb536af762fbff39b269c24d837';prefix='research/settled-funding-direction-20261012/public/INPUTS_FINAL/';ix=json.loads(git(c+':'+prefix+'INDEX.json'));b=git(c+':'+prefix+'PACKET.zip');assert len(b)==ix['bytes'] and sha(b)==ix['SHA256'];out={}
 with zipfile.ZipFile(io.BytesIO(b)) as z:
  assert z.testzip() is None
  for year in (2023,2025):
   name=f'Y{year}.npz';b=z.read(name);assert sha(b)==ix['members'][name]['SHA256']
   with np.load(io.BytesIO(b),allow_pickle=False) as a:out[year]={k:a[k] for k in ('symbol_order','decision_us','close_available_us','close','p0','p1','funding_per_unit','owned_interval_valid')};assert tuple(out[year]['symbol_order'])==SYMBOLS
 return out,dict(commit=c,packet_SHA256=ix['SHA256'],member_sha={k:v['SHA256'] for k,v in ix['members'].items() if k.endswith('.npz')})
def project(b,start,end):
 typ=pq.read_schema(io.BytesIO(b)).field('dt').type;tz='UTC' if typ.tz else None
 lo=pd.Timestamp(start,unit='us',tz='UTC').tz_convert(tz) if tz else pd.Timestamp(start,unit='us')
 hi=pd.Timestamp(end,unit='us',tz='UTC').tz_convert(tz) if tz else pd.Timestamp(end,unit='us')
 cols=['dt','symbol','open','high','low','close','volume','complete_kline']
 f=pq.read_table(io.BytesIO(b),columns=cols,filters=[('dt','>=',pa.scalar(lo.to_pydatetime(),type=typ)),('dt','<',pa.scalar(hi.to_pydatetime(),type=typ))]).to_pandas();f['dt']=pd.to_datetime(f.dt,utc=True);return f.sort_values('dt')
def run(state):
 assert not state.exists();state.mkdir(parents=True);begin=time.monotonic();eco,ecoproof=economics();reports={}
 for year in (2023,2025):
  inp=eco[year];d=inp['decision_us'];assert len(d)==365 and np.all(np.diff(d)==DAY);a=np.arange(d[0]-30*DAY,d[-1]+DAY,DAY,dtype=np.int64);arrays={k:np.full((len(a),5),np.nan) for k in ('open','high','low','close','volume')};ready=np.zeros((len(a),5),bool);proof=[];gaps=[];conflicts=[]
  if year==2023:z,read,archive=feature_archive();prefix='source_tables_not_model_inputs/daily_features/'
  else:
   m=load('ohlc_original_consumer',ROOT/'research/portfolio-risk-2025-admission-20261012/source2025.py');z,read=m.consumer();archive=dict(commit='be48f5519c23f0e64eb4d75f8b8358915c254f7b',wrapper_SHA256='848df602c5db2b4da1e1ba4340f1ebc44a1590364cbcfd2c24a3dc20b093beda');prefix='features2025/daily_features/'
  rt=inp['close_available_us'];rp=inp['close'];ri=np.searchsorted(rt,a);assert np.array_equal(rt[ri],a)
  for j,s in enumerate(SYMBOLS):
   name=prefix+s+'.parquet';b=read(name);f=project(b,int(a[0]-DAY),int(a[-1]));assert not f.dt.duplicated().any() and set(f.symbol)=={s};clocks=f.dt.to_numpy(dtype='datetime64[us]').astype(np.int64)+DAY;ix=np.searchsorted(a,clocks);assert np.array_equal(a[ix],clocks)
   for k in arrays:arrays[k][ix,j]=f[k].to_numpy(float)
   ready[ix,j]=f.complete_kline.eq(True).to_numpy()&np.isfinite(f[['open','high','low','close','volume']].to_numpy(float)).all(1)
   known=ready[:,j];bad=known&(~np.isfinite(rp[ri,j])|(arrays['close'][:,j]!=rp[ri,j]));conflicts.extend(dict(symbol=s,bar_available_us=int(a[k]),OHLC_close=float(arrays['close'][k,j]),risk_close=float(rp[ri[k],j])) for k in np.flatnonzero(bad))
   gaps.extend(dict(symbol=s,bar_available_us=int(a[k]),source_day=str(pd.Timestamp(int(a[k]-DAY),unit='us',tz='UTC').date()),reason='MISSING_OR_INCOMPLETE_REAL_OHLC') for k in np.flatnonzero(~known))
   proof.append(dict(symbol=s,parquet_member=name,original_member_SHA256=sha(b),projected_rows=len(f),complete_rows=int(known.sum())))
  z.close();np.savez_compressed(state/f'Y{year}_SOURCE.npz',symbol_order=np.array(SYMBOLS),OHLC_available_us=a,OHLC_ready=ready,**{'OHLC_'+k:v for k,v in arrays.items()},**{k:v for k,v in inp.items() if k!='symbol_order'})
  reports[str(year)]=dict(rows=len(a),actual_complete_asset_bars=int(ready.sum()),source=archive,economics=ecoproof,members=proof,gaps=gaps,close_identity_conflicts=conflicts,SOURCE_SHA256=sha((state/f'Y{year}_SOURCE.npz').read_bytes()));print('ACTUAL_OHLC_SOURCE_PROJECTION',year,len(a),int(ready.sum()),'gaps',len(gaps),'conflicts',len(conflicts),flush=True)
  assert time.monotonic()-begin<180
 save(state/'SOURCE_PROJECTION.json',dict(status='SOURCE_PREFLIGHT_GAPS_REQUIRE_EXACT_EXISTING_RESTORE' if any(r['gaps'] or r['close_identity_conflicts'] for r in reports.values()) else 'PASS_EXACT_REAL_OHLC_TWO_YEAR_SOURCE',years=reports,source_protocol_SHA256=sha((HERE/'PROTOCOL.json').read_bytes()),provider_GETs=0,new_fits=0,new_references=0,new_native_wallets=0,seconds=time.monotonic()-begin))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--state',type=Path,required=True);a=p.parse_args();run(a.state)
