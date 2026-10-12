"""Exact Git-first year adapter; old normalizer, targets and native window format."""
import argparse,gc,hashlib,importlib.util,io,json,os,sys,time,zipfile
from pathlib import Path
import numpy as np
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
sys.path.insert(0,str(HERE))
from recover_h2 import git,sha,save,SYMBOLS,COMMIT,PREFIX,WRAPPER_SHA
DAY=86400000000
H1='d69e9ac94478c5be54cb46c622afec7aaf3c61f7';FUND='88a77396c7f1e6e0fd5b6249fe0f79dd923fda3b'
def digest(path):return sha(Path(path).read_bytes())
def load(name,path):
 spec=importlib.util.spec_from_file_location(name,path);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module
def wrapper(commit,prefix,index,fields):
 size,checksum,part_name,part_sha=fields;parts=[]
 for row in index['parts']:
  raw=git('show',commit+':'+prefix+row[part_name]);assert len(raw)==row['bytes'] and sha(raw)==row[part_sha];parts.append(raw)
 raw=b''.join(parts);assert len(raw)==index[size] and sha(raw)==index[checksum]
 z=zipfile.ZipFile(io.BytesIO(raw));assert z.testzip() is None and len(z.namelist())==len(set(z.namelist()));return z
def consumer():
 raw=git('show',COMMIT+':'+PREFIX+'CONSUMER.zip');assert len(raw)==2166970 and sha(raw)==WRAPPER_SHA
 z=zipfile.ZipFile(io.BytesIO(raw));m=json.loads(git('show',COMMIT+':'+PREFIX+'MANIFEST.json'));members={r['path']:r for r in m['members']}
 assert z.testzip() is None and set(z.namelist())==set(members) and len(z.namelist())==len(members)
 def read(name):
  raw=z.read(name);r=members[name];assert len(raw)==r['bytes'] and sha(raw)==r['SHA256'];return raw
 return z,read
def causal_inputs():
 z,read=consumer()
 with np.load(io.BytesIO(read('features2025/FEATURES.npz')),allow_pickle=False) as a:t=a['completed_day_available_us'];p=a['close'];assert tuple(a['symbol_order'])==SYMBOLS
 with np.load(io.BytesIO(read('features2025/EXPERTS.npz')),allow_pickle=False) as a:
  d=a['decision_us'];saved=a['expert_targets'];past=a['past_returns30'];assert tuple(a['symbol_order'])==SYMBOLS and tuple(a['expert_order'])==('CASH','VOL_MANAGED_HOLD','CSMOM21','MOMENTUM30_SHORT')
 import polars as pl
 bars=[]
 for s in SYMBOLS:
  f=pl.read_parquet(io.BytesIO(read('features2025/daily_features/'+s+'.parquet')))
  f=f.filter(pl.col('complete_kline')&pl.all_horizontal([pl.col(k).is_finite() for k in ('open','high','low','close','volume')])).with_columns(pl.lit(s).alias('symbol'),pl.col('dt').dt.epoch('us').alias('open_us')).with_columns((pl.col('open_us')+DAY).alias('close_us'),(pl.col('open_us')+DAY).alias('available_us'))
  bars.append(f.select('symbol','open_us','close_us','available_us','open','high','low','close','volume'))
 z.close();return t,p,d,saved,past,pl.concat(bars)
def targets(t,p,d,saved,past,bars):
 from scripts.investment.vol_managed_perpetual_target import fixed_targets
 from scripts.research.public_cross_section_momentum import public_targets
 frame,_=fixed_targets(bars,d,symbols=SYMBOLS);hold=frame['target_weight'].to_numpy().reshape(len(d),5);assets=(frame['eligibility_reason'].to_numpy().reshape(len(d),5)=='ELIGIBLE')
 cs,_=public_targets(p,t,d,SYMBOLS,SYMBOLS)
 np.testing.assert_array_equal(cs,saved[:,2]);np.testing.assert_array_equal(hold,saved[:,1])
 core=load('unchanged2025component_match',ROOT/'research/cs-continuous-economics-20261012/core.py');base,oldproof,_,_=core.match(t,p,d,hold,assets)
 risk=load('unchanged2025risk_scale',ROOT/'research/portfolio-risk-budget-20261012/risk_budget.py')
 comp={a:base[a] for a in ('CS_MATCHED','VOL_MATCHED')};comp['STATIC50']=.5*comp['CS_MATCHED']+.5*comp['VOL_MATCHED'];out,cov,proof=risk.allocate(t,p,d,comp)
 for i,at in enumerate(d):
  k=int(np.searchsorted(t,at));np.testing.assert_array_equal(np.diff(p[k-30:k+1],axis=0)/p[k-30:k],past[i]);assert oldproof[i]['status']=='READY'
 return out,cov,proof
def funding(state):
 prefix='research/core10-2025-primitives-20261010/';manifest=json.loads(git('show',FUND+':'+prefix+'MANIFEST.json'));raw=git('show',FUND+':'+prefix+'PRIMITIVES.zip');assert len(raw)==manifest['bytes'] and sha(raw)==manifest['SHA256']
 from modules.collector_research.pipeline.normalize import numeric_csv,validate_funding,month_limits
 events=[];proof=[]
 with zipfile.ZipFile(io.BytesIO(raw)) as z:
  assert z.testzip() is None
  for s in SYMBOLS:
   for m in range(1,13):
    stamp=f'2025-{m:02d}';stem=f'{s}-fundingRate-{stamp}.zip';name=f'archives/{s}_fundingRate_{stem}';body=z.read(name);r=manifest['members'][name];assert len(body)==r['bytes'] and sha(body)==r['SHA256']
    path=state/stem;path.write_bytes(body);lo,hi=month_limits(2025,m);f,duplicates=validate_funding(numeric_csv(path),lo,hi);path.unlink();assert duplicates==0
    for row in f.itertuples(index=False):events.append(dict(symbol=s,event_us=int(row.calc_time_ms)*1000,raw_rate=float(row.last_funding_rate),reported_interval_hours=float(row.funding_interval_hours)))
    proof.append(dict(symbol=s,month=stamp,raw_SHA256=sha(body),events=len(f),source_commit=FUND,member=name))
 for s in SYMBOLS:
  at=np.array([r['event_us'] for r in events if r['symbol']==s],dtype=np.int64);assert len(at)==1095 and np.all(np.abs(np.diff(at)-8*3600000000)<=1000000)
 events.sort(key=lambda r:(r['event_us'],r['symbol']));return events,proof
def build(state,h2,source,expected=None):
 assert not state.exists() and not git('status','--porcelain')
 if expected is None:assert git('rev-parse','HEAD').decode().strip()==source
 state.mkdir(parents=True);(state/'months').mkdir();began=time.monotonic()
 os.environ.update(WORK_DIR=str(state/'work'),RAW_CACHE_DIR=str(state/'raw'),MAX_UNCOMPRESSED_MIB='64',MIN_FREE_GIB='15',MAX_WORK_GIB='1')
 from modules.collector_research.pipeline.normalize import numeric_csv,validate_price,month_limits
 t,p,d,saved,past,bars=causal_inputs();start,end=1767225600000000-365*DAY,1767225600000000;np.testing.assert_array_equal(d,np.arange(start,end,DAY))
 w,cov,risk=targets(t,p,d,saved,past,bars)
 # Prefix is recalculated with future prices/bar rows excluded; no outcome inputs.
 import polars as pl
 cut=start+181*DAY;keep=t<=cut;ids=d<=cut
 alt,altcov,_=targets(t[keep],p[keep],d[ids],saved[ids],past[ids],bars.filter(pl.col('available_us')<=cut))
 np.testing.assert_array_equal(altcov,cov[ids])
 for a in w:np.testing.assert_array_equal(alt[a],w[a][ids])
 np.savez_compressed(state/'Y2025.npz',decision_us=d,symbol_order=np.array(SYMBOLS),annual_covariance=cov,**w);save(state/'Y2025_RISK.json',risk)
 z,read=consumer();receipts=json.loads(read('MINUTE_ACQUIRED.json'))['records'];z.close();rows={(r['symbol'],r['family'],r['month']):r for r in receipts};assert len(rows)==120
 base='research_artifacts/frozen_e5_2025h1_20261008/';ix=json.loads(git('show',H1+':'+base+'INDEX.json'));frozen=wrapper(H1,base,ix,('original_bytes','original_sha256','file_name','sha256'))
 base='research_artifacts/native_20261008/';ix=json.loads(git('show',H1+':'+base+'INDEX.json'));tails=[wrapper(H1,base+'byteparts/',dict(r,parts=r['parts']),('original_bytes','original_sha256','file_name','sha256')) for r in ix['market_archives_layout']['original_archives']]
 recovered=json.loads((h2/'SOURCE_INDEX.json').read_text());assert recovered['bytes']==82770519 and len(recovered['records'])==60
 records=[];daily=[];previous={}
 for m in range(1,13):
  stamp=f'2025-{m:02d}';lo,hi=month_limits(2025,m);times=np.arange(lo*1000,hi*1000,60000000,dtype=np.int64);arrays=dict(times=times);sr=[]
  for j,s in enumerate(SYMBOLS):
   for family in ('klines','markPriceKlines'):
    stem=f'{s}-1m-{stamp}.zip';old=rows[s,family,stamp]
    if m==1:
     name=f'tail_data/data/raw/{family}/{s}/{stem}';matches=[a for a in tails if name in a.namelist()];assert len(matches)==1;body=matches[0].read(name)
    elif m<=6:body=frozen.read(f'market/data/raw/{family}/{s}/{stem}')
    else:body=(h2/'raw'/family/s/stem).read_bytes()
    assert len(body)==old['bytes'] and sha(body)==old['SHA256'];path=state/stem;path.write_bytes(body);f,dups=validate_price(numeric_csv(path),family,lo,hi);path.unlink();assert dups==0;np.testing.assert_array_equal(f.timestamp_ms.to_numpy()*1000,times)
    prior=previous.get((s,family));previous[s,family]=float(f.close.iloc[-1]);sr.append(dict(symbol=s,family=family,original_SHA256=old['SHA256'],bytes=old['bytes'],URL=old['url'],minutes=len(f),CRC=True,exact_grid=True,prior_completed_close=prior,end_completed_close=previous[s,family]))
    if family=='klines':
     for k in ('open','close','quote_volume'):arrays[s+'_'+k]=f[k].to_numpy()
     for i,at in enumerate(range(lo*1000,hi*1000,DAY)):
      k=int(np.searchsorted(t,at));assert t[k]==at;actual=float(p[k,j]) if at==start else (prior if i==0 else float(f.close.iloc[i*1440-1]));assert abs(actual-p[k,j])<=1e-12*abs(actual)
      daily.append(dict(symbol=s,close_us=at,close=actual))
      k=int(np.searchsorted(t,at+DAY));assert t[k]==at+DAY;actual=float(f.close.iloc[(i+1)*1440-1]);assert abs(actual-p[k,j])<=1e-12*abs(actual)
    else:arrays[s+'_mark']=f.close.to_numpy()
  path=state/'months'/(stamp+'.npz');np.savez_compressed(path,**arrays);records.append(dict(month=stamp,minutes=len(times),source_NPZ_SHA256=digest(path),source_NPZ_bytes=path.stat().st_size,sources=sr));del arrays;gc.collect();print('EXACT2025_SOURCE_MONTH_READY',m,12,flush=True);assert time.monotonic()-began<300
 frozen.close()
 for z in tails:z.close()
 events,fund=funding(state);save(state/'EVENTS.json',events);save(state/'DAILY.json',daily)
 report=dict(status='PASS_EXACT_FULL2025_NATIVE_SOURCE_CAUSAL_RISK',calendar=[start,end],days=365,symbol_order=list(SYMBOLS),months=records,funding_events=len(events),funding=fund,source_commit=source,receipt_commit=COMMIT,H1_commit=H1,H2_recovery_source_commit=recovered['source_commit'],original_risk_target_identity='EXACT_REGENERATED_CS_HOLD_AND_PAST30_PREFIX',prefix_days_verified=int(ids.sum()),last365_daily_minute_parity='PASS_ALL_CORE5',initial_trade_boundary='REUSED_ORIGINAL_CAUSAL_PRICE_NOT_NEW_DEC2024_MINUTE_CHECK',initial_mark_boundary='FLAT_UNOWNED_PRIORUNKNOWN_NO_FABRICATION',new_wallets=0,new_fits=0,provider_downloads=0)
 report['files']={n:dict(SHA256=digest(state/n),bytes=(state/n).stat().st_size) for n in ('EVENTS.json','DAILY.json','Y2025.npz','Y2025_RISK.json')}
 if expected:assert report==expected,'Exact original source/target/risk proof restoration'
 save(state/'SOURCE_INDEX.json',report);save(state/'TIMING.json',dict(seconds=time.monotonic()-began));print('EXACT2025_FULL_SOURCE_READY',365,525600,len(events),flush=True)

def publish_h2(h2,destination):
 assert destination.resolve()==(HERE/'original-H2').resolve() and not destination.exists();destination.mkdir()
 index=json.loads((h2/'SOURCE_INDEX.json').read_text());assert len(index['records'])==60 and index['bytes']==82770519
 parts=[]
 for i,row in enumerate(index['records']):
  raw=(h2/row['raw_path']).read_bytes();assert len(raw)==row['bytes'] and sha(raw)==row['original_SHA256'];rp=[]
  for j,off in enumerate(range(0,len(raw),786432)):
   name=f'archive{i:03d}.part{j:02d}';body=raw[off:off+786432];(destination/name).write_bytes(body);rp.append(dict(file=name,bytes=len(body),SHA256=sha(body)))
  check=Path(str(h2/row['raw_path'])+'.CHECKSUM').read_bytes();name=f'archive{i:03d}.CHECKSUM';(destination/name).write_bytes(check);parts.append(dict(raw_path=row['raw_path'],parts=rp,checksum_file=name,checksum_SHA256=sha(check),bytes=row['bytes'],SHA256=row['original_SHA256']))
 save(destination/'INDEX.json',dict(original_source_index=index,original_source_index_SHA256=digest(h2/'SOURCE_INDEX.json'),archives=parts,body_bytes=82770519,new_wallets=0));print('EXACT2025_H2_SOURCE_PUBLISHED_PARTS',len(parts),flush=True)

def restore_h2(state,artifact):
 assert not state.exists();state.mkdir(parents=True);prefix=str(HERE.relative_to(ROOT))+'/original-H2/';index=json.loads(git('show',artifact+':'+prefix+'INDEX.json'));assert index['body_bytes']==82770519 and len(index['archives'])==60
 for r in index['archives']:
  parts=[]
  for p in r['parts']:
   raw=git('show',artifact+':'+prefix+p['file']);assert len(raw)==p['bytes'] and sha(raw)==p['SHA256'];parts.append(raw)
  raw=b''.join(parts);assert len(raw)==r['bytes'] and sha(raw)==r['SHA256'];path=state/r['raw_path'];assert path.resolve().is_relative_to(state.resolve());path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(raw)
  raw=git('show',artifact+':'+prefix+r['checksum_file']);assert sha(raw)==r['checksum_SHA256'];Path(str(path)+'.CHECKSUM').write_bytes(raw)
 save(state/'SOURCE_INDEX.json',index['original_source_index']);assert digest(state/'SOURCE_INDEX.json')==index['original_source_index_SHA256'];return state
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--state',type=Path,required=True);p.add_argument('--h2',type=Path,required=True);p.add_argument('--source-commit',required=True);a=p.parse_args();build(a.state,a.h2,a.source_commit)
