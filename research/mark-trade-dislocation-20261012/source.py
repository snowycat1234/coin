"""Git-first daily pairs; only two necessary boundary days may need official raw ZIPs."""
import argparse,io,json,os,time,zipfile
from functools import lru_cache
from pathlib import Path
import numpy as np
from util import HERE,ROOT,sha,file_sha,git,save,clean,verify,public_packet
from core import DAY,START,FIT,SYMBOLS,features
MARK='c4f44417a665ded2c43e6767221efea004d90dd1';TRADE='0d6db3fd515eea5de421bce6cf7123b3e15ec55f';CUBE='53056adaa3b54f93ef6859269106ac288331dd9c';ECON='53357f33f4e6ccb536af762fbff39b269c24d837'
MP='research/core5-continuous-mark-20261011/result/MARK_DAILY_CONTINUOUS.npz';TP='research/core5-continuous-risk600-20261011/continuous/DAILY_CONTINUOUS.npz'
WARM='d69e9ac94478c5be54cb46c622afec7aaf3c61f7'
@lru_cache(maxsize=3)
def warm_wrapper(name):
 ix=json.loads(git(WARM+':research_artifacts/native_20261008/INDEX.json'));r=next(r for r in ix['files'] if r['file_name']==name);parts=sorted([q for q in ix['published_files'] if q['file_name'].startswith(name+'.bytepart')],key=lambda q:q['index']);assert parts
 bodies=[]
 for p in parts:
  b=git(WARM+':'+p['path']);assert len(b)==p['bytes'] and sha(b)==p['sha256'];bodies.append(b)
 raw=b''.join(bodies);assert len(raw)==r['bytes'] and sha(raw)==r['sha256'];return raw,r
def completed_day(frame,start,end):
 q=frame[(frame.timestamp_ms>=start//1000)&(frame.timestamp_ms<end//1000)].reset_index(drop=True)
 np.testing.assert_array_equal(q.timestamp_ms.to_numpy()*1000,np.arange(start,end,60000000));assert len(q)==1440 and int(q.close_time_ms.iloc[-1])*1000+1000==end
 return q
def acquire(state,commit,resume=False):
 clean(commit);verify();assert not state.exists() or resume;state.mkdir(parents=True,exist_ok=True);begin=time.monotonic();P=json.loads((HERE/'PROTOCOL.json').read_text());os.environ.update(WORK_DIR=str(state/'work'),RAW_CACHE_DIR=str(state/'raw'),WARMUP_START='2022-12-31',START_DATE='2022-12-31',END_DATE='2024-12-31',SYMBOLS=','.join(SYMBOLS),HTTP_RETRIES='0',HTTP_CONNECT_TIMEOUT='10',HTTP_READ_TIMEOUT='20',MAX_ARCHIVE_MIB='1',MAX_UNCOMPRESSED_MIB='64',MAX_WORK_GIB='1',MIN_FREE_GIB='15',REFRESH_CHECKSUMS='0')
 # Existing public collector config is hash-bound; no account configuration is read.
 assert (ROOT/'modules/collector_research/config.env').read_bytes()==git(commit+':modules/collector_research/config.env')
 from modules.collector_research.pipeline.download import Job,fetch,session,check_zip
 from modules.collector_research.pipeline.normalize import numeric_csv,validate_price
 connection=session();records=[];points={};downloaded=0;reused=0;inventory=json.loads((HERE/'evidence/WARM_BOUNDARY_INVENTORY.json').read_text());assert inventory['commit']==WARM
 try:
  for year in (2022,2024):
   start=int(np.datetime64(f'{year}-12-31','us').astype('int64'));end=start+DAY;point=dict(available_us=end,trade_close=[],mark_close=[])
   for s in SYMBOLS:
    for family,field in (('klines','trade_close'),('markPriceKlines','mark_close')):
     member=f'tail_data/data/raw/{family}/{s}/{s}-1m-{year}-12.zip';found=[q for q in inventory['matching_members'] if q['member']==member];extra={}
     if found:
      assert len(found)==1;raw,wr=warm_wrapper(found[0]['wrapper_file']);path=state/'raw_git'/family/s/f'{s}-1m-{year}-12.zip';path.parent.mkdir(parents=True,exist_ok=True)
      with zipfile.ZipFile(io.BytesIO(raw)) as archive:b=archive.read(member);checksum=archive.read(member+'.CHECKSUM')
      assert sha(b)==checksum.decode().split()[0] and len(b)==found[0]['bytes'];path.write_bytes(b);Path(str(path)+'.CHECKSUM').write_bytes(checksum);check_zip(path);left=int(np.datetime64(f'{year}-12-01','us').astype('int64'));frame,dups=validate_price(numeric_csv(path),family,left//1000,end//1000);assert dups==0;np.testing.assert_array_equal(frame.timestamp_ms.to_numpy()*1000,np.arange(left,end,60000000));status='REUSED_GIT_ORIGINAL';reused+=1;url=f'https://data.binance.vision/data/futures/um/monthly/{family}/{s}/1m/{path.name}';extra=dict(Git_commit=WARM,wrapper_file=wr['file_name'],wrapper_SHA256=wr['sha256'],wrapper_bytes=wr['bytes'],member=member,whole_month_grid_verified=True)
     else:
      job=Job(s,family,year,12,31);assert job.url==f'https://data.binance.vision/data/futures/um/daily/{family}/{s}/1m/{s}-1m-{year}-12-31.zip';r=fetch(job,connection);assert r['status'] in ('DOWNLOADED_VERIFIED','VERIFIED_CACHE','ADOPTED_VERIFIED_CACHE'),r
      downloaded+=int(r['status']=='DOWNLOADED_VERIFIED');reused+=int(r['status']!='DOWNLOADED_VERIFIED');path=job.path;check_zip(path);frame,dups=validate_price(numeric_csv(path),family,start//1000,end//1000);assert dups==0;status=r['status'];url=job.url
     frame=completed_day(frame,start,end);point[field].append(float(frame.close.iloc[-1]));records.append(dict(symbol=s,family=family,date=f'{year}-12-31',URL=url,raw_path=str(path.relative_to(state)),bytes=path.stat().st_size,SHA256=file_sha(path),checksum_SHA256=file_sha(Path(str(path)+'.CHECKSUM')),CRC=True,minutes=1440,last_open_us=end-60000000,inclusive_last_close_ms=int(frame.close_time_ms.iloc[-1]),available_us=end,transport_status=status,**extra))
     save(state/'PROGRESS.json',dict(records=records,source_commit=commit,new_fits=0,new_wallets=0,seconds=time.monotonic()-begin));assert sum(q['bytes'] for q in records if q['transport_status']!='REUSED_GIT_ORIGINAL')<=P['necessary_boundary_repair']['new_body_bytes_max'] and time.monotonic()-begin<600;print('ACTUAL_MARK_TRADE_BOUNDARY_ORIGINAL',year,s,family,len(records),status,flush=True)
   points[str(year+1)]=point
  save(state/'BOUNDARY.json',dict(status='PASS_TWO_REAL_PAIRED_COMPLETED_BOUNDARY_DAYS',points=points,records=records,source_commit=commit,new_provider_ZIPs=downloaded,verified_reused_ZIPs=reused,body_bytes=sum(r['bytes'] for r in records),new_provider_body_bytes=sum(r['bytes'] for r in records if r['transport_status']!='REUSED_GIT_ORIGINAL'),full2022Dec_certified=False,no_protected_records=True,new_fits=0,new_wallets=0,seconds=time.monotonic()-begin))
 except Exception as e:
  save(state/('FAILED_RESUME.json' if resume else 'FAILED.json'),dict(error=str(e),HTTP_status=getattr(getattr(e,'response',None),'status_code',None),verified_archives=len(records),new_ZIPs=downloaded,source_commit=commit,automatic_retry=False,new_fits=0,new_wallets=0));raise
 finally:connection.close()
def raw_npz(commit,path,expected):
 raw=git(commit+':'+path);assert sha(raw)==expected
 with np.load(io.BytesIO(raw),allow_pickle=False) as z:return {k:z[k].copy() for k in z.files},sha(raw)
def at(t,p,d):
 k=int(np.searchsorted(t,d));return p[k] if k<len(t) and int(t[k])==int(d) else np.full(5,np.nan)
def project(state,boundary,commit):
 clean(commit);verify();assert not state.exists();state.mkdir(parents=True);begin=time.monotonic();B=json.loads((boundary/'BOUNDARY.json').read_text());assert B['status']=='PASS_TWO_REAL_PAIRED_COMPLETED_BOUNDARY_DAYS'
 for r in B['records']:assert file_sha(boundary/r['raw_path'])==r['SHA256'] and file_sha(Path(str(boundary/r['raw_path'])+'.CHECKSUM'))==r['checksum_SHA256']
 mt,msha=raw_npz(MARK,MP,'0ec957375b831255920e90b9d9221ca0422731580faae436576b57fb07daeb74');tr,tsha=raw_npz(TRADE,TP,'9a0e63c0b4f93b185310c65892d424e99307a6678930b5d559e421a1145edde9');cube,csha=raw_npz(CUBE,'research/monetary-policy-information-20261012/input/INPUTS.npz','e33cc15bd53167078252f7d58b406960d543ccb92421f430214e5360971f12f4')
 for z in (mt,tr,cube):assert tuple(z['symbol_order'])==SYMBOLS
 np.testing.assert_array_equal(mt['available_us'],tr['available_us']);rt=tr['available_us'];assert len(rt)==699 and np.all(np.diff(rt)==DAY);mask=(mt['observed_minutes']==1440)&(tr['observed_minutes']==1440);assert np.all(mask==(mt['missing_minutes']==0))
 # Rawday closes are exact synchronous finalminute projections, not paid funding marks.
 d=np.arange(START,FIT,DAY);ids=np.searchsorted(cube['decision_us'],d);np.testing.assert_array_equal(cube['decision_us'][ids],d);p0=cube['p0'][ids];p1=cube['p1'][ids];trade=np.stack([at(rt,tr['close'],q) for q in d]);mark=np.stack([at(rt,mt['close'],q) for q in d]);ready=np.stack([at(rt,mask.astype(float),q)==1 for q in d]);previous=[];cube_compared=0;cube_unknown=0
 for i,q in enumerate(d):
  prev=at(rt,tr['close'],q-DAY)
  if not np.isfinite(prev).all():prev=at(cube['close_available_us'],cube['close'],q-DAY)
  previous.append(prev);old=at(cube['close_available_us'],cube['close'],q);valid=np.isfinite(trade[i])&np.isfinite(old);np.testing.assert_array_equal(trade[i,valid],old[valid]);cube_compared+=int(valid.sum());cube_unknown+=int((np.isfinite(trade[i])&~np.isfinite(old)).sum())
 x=features(trade,np.stack(previous),mark,ready);known=np.isfinite(p0)&np.isfinite(p1)&(p0>0)&(p1>0);y=np.full_like(p0,np.nan);np.divide(p1,p0,out=y,where=known);y[known]-=1;mature=d+2*DAY;common=np.isfinite(x).all((1,2))&np.isfinite(y).all(1)&(mature<FIT);assert common.sum()>=600
 np.savez_compressed(state/'TRAIN.npz',decision_us=d,features=x,price_return=y,label_mature_us=mature,trade_close=trade,previous_trade_close=np.stack(previous),mark_close=mark,pair_complete=ready,p0=p0,p1=p1,symbol_order=np.array(SYMBOLS));econ,ep=public_packet(ECON,'research/settled-funding-direction-20261012/public/INPUTS_FINAL/');evals={}
 for year,artifact,prefix,cache in ((2023,'f38617c5a0917490c8b90fba355ecf0d5f1b87f4','research/cs-2023-continuous-economics-20261012/source-result/','/workspace/cs-2023-state/SOURCE_OBSERVED'),(2025,'534a18fbed0ec7a2f7ffbb298526c51b1a2a696c','research/portfolio-risk-2025-native-20261012/input/','/workspace/portfolio-risk-2025-state/PUBLIC_SOURCE_RECOVERED/source')):
  indexraw=git(artifact+':'+prefix+'SOURCE_INDEX.json');ix=json.loads(indexraw);assert (Path(cache)/'SOURCE_INDEX.json').read_bytes()==indexraw;dt=[];pp=[];mm=[];months=[]
  for r in ix['months']:
   path=Path(cache)/'months'/(r['month']+'.npz');assert file_sha(path)==r['source_NPZ_SHA256'] and path.stat().st_size==r['source_NPZ_bytes']
   with np.load(path,allow_pickle=False) as z:
    times=z['times'];assert len(times)%1440==0 and np.all(np.diff(times)==60000000);assert times[0]%DAY==0;dt.extend((times[1439::1440]+60000000).tolist());p=np.column_stack([z[s+'_close'][1439::1440] for s in SYMBOLS]);m=np.column_stack([z[s+'_mark'][1439::1440] for s in SYMBOLS]);assert np.isfinite(p).all() and np.isfinite(m).all() and (p>0).all() and (m>0).all();pp.extend(p.tolist());mm.extend(m.tolist())
   months.append(dict(month=r['month'],SHA256=r['source_NPZ_SHA256'],bytes=r['source_NPZ_bytes']))
  point=B['points'][str(year)];tt=np.array([point['available_us'],*dt],np.int64);pc=np.array([point['trade_close'],*pp]);mc=np.array([point['mark_close'],*mm]);assert len(tt)==366 and np.all(np.diff(tt)==DAY)
  with np.load(io.BytesIO(econ[f'Y{year}.npz']),allow_pickle=False) as z:a={k:z[k].copy() for k in z.files}
  assert tuple(a['symbol_order'])==SYMBOLS and len(a['decision_us'])==365;np.testing.assert_array_equal(tt[:-1],a['decision_us']);old=np.stack([at(a['close_available_us'],a['close'],q) for q in tt[:-1]]);np.testing.assert_array_equal(pc[:-1],old);prev=np.vstack([at(a['close_available_us'],a['close'],tt[0]-DAY),pc[:-2]]);xv=features(pc[:-1],prev,mc[:-1],np.ones((365,5),bool));yv=a['p1']/a['p0']-1;assert np.isfinite(xv).all() and np.isfinite(yv).all()
  np.savez_compressed(state/f'Y{year}.npz',**a,features=xv,price_return=yv,label_mature_us=a['decision_us']+2*DAY,trade_close=pc[:-1],previous_trade_close=prev,mark_close=mc[:-1]);evals[str(year)]=dict(rows=365,known_feature_label_pairs=1825,source_artifact=artifact,source_index_SHA256=sha(indexraw),months=months,raw_paired_daily_points=366,rawtrade_close_cube_identity='BIT_EXACT',first_boundary_year=year-1,INPUTS_SHA256=file_sha(state/f'Y{year}.npz'));print('ACTUAL_MARK_TRADE_VALIDATION_SOURCE',year,365,1825,flush=True)
 prep=dict(status='PASS_REAL_SYNCHRONOUS_MARK_TRADE_SOURCE',source_commit=commit,protocol_SHA256=file_sha(HERE/'PROTOCOL.json'),boundary_SHA256=file_sha(boundary/'BOUNDARY.json'),train=dict(natural_dates=730,source_completed_pair_days=699,all5_complete_pair_dates=int(ready.all(1).sum()),common_mature_dates=int(common.sum()),admitted_decisions=d[common].tolist(),unknown_feature_dates=d[~np.isfinite(x).all((1,2))].tolist(),unknown_label_dates=d[~np.isfinite(y).all(1)].tolist(),purge_dates=d[mature>=FIT].tolist(),maximum_included_maturity_us=int(mature[common].max()),mark_missing_minutes=27,mark_source_SHA256=msha,trade_source_SHA256=tsha,price_cube_SHA256=csha,raw_trade_close_cube_compared_values=cube_compared,cube_unknown_not_used_to_discard_recovered_raw_close=cube_unknown,TRAIN_SHA256=file_sha(state/'TRAIN.npz'),full2022Dec_mark_recovered=False),validation=evals,economics_source_commit=ECON,economics_packet_SHA256=ep['SHA256'],new_fits=0,new_wallets=0,new_economic_references=0,seconds=time.monotonic()-begin);save(state/'PREPARATION.json',prep);assert prep['seconds']<120;print('ACTUAL_MARK_TRADE_TRAIN_SOURCE',int(common.sum()),prep['train']['all5_complete_pair_dates'],flush=True)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('phase',choices=['acquire','project']);p.add_argument('--state',type=Path,required=True);p.add_argument('--boundary',type=Path);p.add_argument('--source-commit',required=True);p.add_argument('--resume',action='store_true');a=p.parse_args()
 if a.phase=='acquire':acquire(a.state,a.source_commit,a.resume)
 else:project(a.state,a.boundary,a.source_commit)
