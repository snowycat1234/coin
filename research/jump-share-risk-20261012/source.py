"""Reuse exact published paths and repair only missing December2022 trade warmup."""
import argparse,io,json,os,time,zipfile
from pathlib import Path
import numpy as np
from core import DAY,STEP,START,FIT,SYMBOLS,measure,features
from util import HERE,ROOT,git,sha,file_sha,save,verify,clean,public_packet
CONT='306b58c4a52035ac9f374de7c25d40dff22fb658';OLD='b4756ec8fb59457cfd8db74a79ca6a859f07f331';TRADE='0d6db3fd515eea5de421bce6cf7123b3e15ec55f';ECON='53357f33f4e6ccb536af762fbff39b269c24d837';WARM='d69e9ac94478c5be54cb46c622afec7aaf3c61f7';PREFIX='research/core5-continuous-risk600-20261011/'
EXPECTED22=('0f4788019cdb29f4db7b03d9efefce099d7adf49c0daf70a144b814b292bf577','1e426fd43bd84ab244e8a47630d7b09084455dc68eee32eb5ccecd9950c68af6','d9319b4016f7cef11f0ec0bfc9bc424d64806405691c01bc6636488171702c44','a33b33fd72aadf7e6b5034fbb5574aa431ddcb5247da00f24a43a309d7e22037','8522853b4787a28a5a32763324118321d1f059d73ca987c8c65633ac0f2615bf')
def npz(b):
 with np.load(io.BytesIO(b),allow_pickle=False) as z:return {k:z[k].copy() for k in z.files}
def configure(state):
 os.environ.update(WORK_DIR=str(state/'work'),RAW_CACHE_DIR=str(state/'raw'),WARMUP_START='2022-12-01',START_DATE='2022-12-01',END_DATE='2022-12-31',SYMBOLS=','.join(SYMBOLS),HTTP_RETRIES='0',HTTP_CONNECT_TIMEOUT='10',HTTP_READ_TIMEOUT='20',MAX_ARCHIVE_MIB='4',MAX_UNCOMPRESSED_MIB='64',MAX_WORK_GIB='1',MIN_FREE_GIB='15',REFRESH_CHECKSUMS='0')
def month_prices(path,left,right):
 from modules.collector_research.pipeline.download import check_zip
 from modules.collector_research.pipeline.normalize import numeric_csv,validate_price
 check_zip(path);f,duplicates=validate_price(numeric_csv(path),'klines',left//1000,right//1000);assert duplicates==0;np.testing.assert_array_equal(f.timestamp_ms.to_numpy()*1000,np.arange(left,right,60000000));assert int(f.close_time_ms.iloc[-1])*1000+1000==right;return f.close.to_numpy(float)
def acquire(state,commit,resume=False):
 clean(commit);verify();assert not state.exists() or resume;state.mkdir(parents=True,exist_ok=True);configure(state);assert (ROOT/'modules/collector_research/config.env').read_bytes()==git(commit+':modules/collector_research/config.env');begin=time.monotonic()
 from modules.collector_research.pipeline.download import Job,fetch,session
 connection=session();records=[]
 try:
  for s,expected in zip(SYMBOLS,EXPECTED22):
   job=Job(s,'klines',2022,12);r=fetch(job,connection);assert r['status'] in ('DOWNLOADED_VERIFIED','VERIFIED_CACHE','ADOPTED_VERIFIED_CACHE'),r;assert file_sha(job.path)==expected;month_prices(job.path,1669852800000000,FIT);records.append(dict(symbol=s,URL=job.url,raw_path=str(job.path.relative_to(state)),SHA256=expected,CHECKSUM_SHA256=file_sha(Path(str(job.path)+'.CHECKSUM')),bytes=job.path.stat().st_size,transport_status=r['status'],minutes=44640,CRC=True,complete_grid=True));save(state/'PROGRESS.json',dict(records=records,source_commit=commit,fits=0,wallets=0));assert sum(q['bytes'] for q in records)<=15000000 and time.monotonic()-begin<600;print('ACTUAL_JUMP_DECEMBER_TRADE_ORIGINAL',s,len(records),r['status'],flush=True)
  save(state/'SOURCES.json',dict(status='PASS_REAL_DECEMBER2022_TRADE_ONLY',records=records,source_commit=commit,seconds=time.monotonic()-begin,new_ZIPs=sum(q['transport_status']=='DOWNLOADED_VERIFIED' for q in records),new_body_bytes=sum(q['bytes'] for q in records),December_mark_recovered=False,fits=0,wallets=0))
 except Exception as e:
  save(state/('FAILED_RESUME.json' if resume else 'FAILED.json'),dict(error=str(e),HTTP_status=getattr(getattr(e,'response',None),'status_code',None),verified=len(records),automatic_retry=False,fits=0,wallets=0));raise
 finally:connection.close()
def existing_panel():
 raw=git(OLD+':research/har-rv-risk-20261011/RESULT_BUNDLE.zip');assert sha(raw)=='534cea64e8aa6b27b51bba1b4ffa0ff2305e42843c6022d75a68cc301ec27b17'
 with zipfile.ZipFile(io.BytesIO(raw)) as z:b=z.read('prepared/FIVE_MIN_CLOSES.npz')
 assert sha(b)=='441ae2de4ac38bdc6f0490469a7a1f764f081ac6b6d53a83012b4252a398cb45';a=npz(b);assert tuple(a['symbol_order'])==SYMBOLS;clocks=[np.arange(START+STEP,1640995200000000+STEP,STEP)];panels=[np.column_stack([a[s] for s in SYMBOLS])];refs=[dict(commit=OLD,member='prepared/FIVE_MIN_CLOSES.npz',SHA256=sha(b))]
 for phase in ('Q12022','Q22022','Q32022','OCTNOV2022_REUSE'):
  ixraw=git(CONT+':'+PREFIX+'phases/'+phase+'/SOURCE_INDEX.json');r=json.loads(ixraw)['artifacts']['FIVE_MIN.npz'];parts=[]
  for q in r['parts']:b=git(CONT+':'+q['path']);assert sha(b)==q['SHA256'] and len(b)==q['bytes'];parts.append(b)
  b=b''.join(parts);assert sha(b)==r['SHA256'] and len(b)==r['bytes'];a=npz(b);assert tuple(a['symbol_order'])==SYMBOLS;clocks.append(a['available_us']);panels.append(a['close']);refs.append(dict(commit=CONT,phase=phase,index_SHA256=sha(ixraw),panel_SHA256=sha(b)))
 t=np.concatenate(clocks);p=np.concatenate(panels);assert p.shape==(699*288,5) and len(t)==len(p) and np.all(np.diff(t)==STEP);return t,p,refs
def warm24(state):
 inventory=json.loads(git(WARM+':research_artifacts/native_20261008/INDEX.json'));memo={};prices=[];refs=[];left=1733011200000000;right=1735689600000000
 for s in SYMBOLS:
  wrapper='coin_public_tail_archives_20261008_part01.zip' if s in ('BTCUSDT','ETHUSDT','DOGEUSDT') else 'coin_public_tail_archives_20261008_part02.zip'
  if wrapper not in memo:
   r=next(q for q in inventory['files'] if q['file_name']==wrapper);parts=[]
   for q in sorted([q for q in inventory['published_files'] if q['file_name'].startswith(wrapper+'.bytepart')],key=lambda q:q['index']):b=git(WARM+':'+q['path']);assert sha(b)==q['sha256'] and len(b)==q['bytes'];parts.append(b)
   raw=b''.join(parts);assert sha(raw)==r['sha256'] and len(raw)==r['bytes'];memo[wrapper]=(raw,r)
  raw,r=memo[wrapper];member=f'tail_data/data/raw/klines/{s}/{s}-1m-2024-12.zip'
  with zipfile.ZipFile(io.BytesIO(raw)) as z:b=z.read(member);check=z.read(member+'.CHECKSUM')
  assert sha(b)==check.decode().split()[0];path=state/'warm24'/s/(s+'-1m-2024-12.zip');path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(b);Path(str(path)+'.CHECKSUM').write_bytes(check);prices.append(month_prices(path,left,right));refs.append(dict(commit=WARM,wrapper=wrapper,wrapper_SHA256=r['sha256'],member=member,SHA256=sha(b),CHECKSUM_SHA256=sha(check)))
 return np.column_stack(prices),refs
def value(t,a,d):
 k=int(np.searchsorted(t,d));return a[k] if k<len(t) and t[k]==d else np.full(5,np.nan)
def one_minute_RV(p,prev):return np.square(np.diff(np.log(np.vstack([prev,p])),axis=0)).reshape(-1,1440,5).sum(1)
def project(state,raw22,commit):
 clean(commit);verify();assert not state.exists();state.mkdir(parents=True);configure(state);begin=time.monotonic();source=json.loads((raw22/'SOURCES.json').read_text());assert source['status']=='PASS_REAL_DECEMBER2022_TRADE_ONLY';t,p,refs=existing_panel();rt=t[287::288];stats=measure(p.reshape(699,288,5),np.full(5,np.nan));raw=git(TRADE+':'+PREFIX+'continuous/DAILY_CONTINUOUS.npz');assert sha(raw)=='9a0e63c0b4f93b185310c65892d424e99307a6678930b5d559e421a1145edde9';old=npz(raw);np.testing.assert_array_equal(rt,old['available_us']);np.testing.assert_array_equal(p[287::288],old['close']);np.testing.assert_allclose(stats['RV'],old['RV_5m'],rtol=2e-14,atol=1e-18,equal_nan=True);np.testing.assert_allclose(stats['RSminus'],old['RSminus_5m'],rtol=2e-14,atol=1e-18,equal_nan=True)
 minute22=[]
 for r in source['records']:
  path=raw22/r['raw_path'];assert file_sha(path)==r['SHA256'] and file_sha(Path(str(path)+'.CHECKSUM'))==r['CHECKSUM_SHA256'];minute22.append(month_prices(path,1669852800000000,FIT))
 minute22=np.column_stack(minute22);assert [r['symbol'] for r in source['records']]==list(SYMBOLS);five22=minute22[4::5];full=np.vstack([p,five22]);times=np.r_[t,np.arange(1669852800000000+STEP,FIT+STEP,STEP)];assert full.shape==(730*288,5) and np.all(np.diff(times)==STEP);z=measure(full.reshape(730,288,5),np.full(5,np.nan));z['RV_1m']=np.vstack([old['RV_1m'],one_minute_RV(minute22,p[-1])]);available=times[287::288];xx=features(z);d=np.arange(START,FIT,DAY);x=np.stack([value(available,xx,q) if q>=available[0] else np.full((5,7),np.nan) for q in d]);y=np.stack([value(available,z['RV'],q+DAY) for q in d]);mature=d+2*DAY;common=np.isfinite(x).all((1,2))&np.isfinite(y).all(1)&(y>0).all(1)&(mature<FIT);assert common.sum()>=600
 # New month's final trade closes must match already published genuine daily boundary.
 B,_=public_packet('d0adcbc10e0fe980e3361d3233df44acc7a9888c','research/mark-trade-dislocation-20261012/public/INPUTS/');boundary=json.loads(B['BOUNDARY.json']);np.testing.assert_array_equal(minute22[-1],boundary['points']['2023']['trade_close']);np.savez_compressed(state/'TRAIN.npz',decision_us=d,features=x,target_RV=y,label_mature_us=mature,panel_available_us=available,five_close=full.reshape(730,288,5),previous_close=np.full(5,np.nan),**z,symbol_order=np.array(SYMBOLS));econ,ep=public_packet(ECON,'research/settled-funding-direction-20261012/public/INPUTS_FINAL/');validation={}
 for year,artifact,prefix,cache in ((2023,'f38617c5a0917490c8b90fba355ecf0d5f1b87f4','research/cs-2023-continuous-economics-20261012/source-result/','/workspace/cs-2023-state/SOURCE_OBSERVED'),(2025,'534a18fbed0ec7a2f7ffbb298526c51b1a2a696c','research/portfolio-risk-2025-native-20261012/input/','/workspace/portfolio-risk-2025-state/PUBLIC_SOURCE_RECOVERED/source')):
  a=npz(econ[f'Y{year}.npz']);ixraw=git(artifact+':'+prefix+'SOURCE_INDEX.json');index=json.loads(ixraw);assert (Path(cache)/'SOURCE_INDEX.json').read_bytes()==ixraw;panels=[];clock=[];months=[]
  for r in index['months']:
   path=Path(cache)/'months'/(r['month']+'.npz');assert file_sha(path)==r['source_NPZ_SHA256'] and path.stat().st_size==r['source_NPZ_bytes']
   with np.load(path,allow_pickle=False) as c:tt=c['times'];assert np.all(np.diff(tt)==60000000);price=np.column_stack([c[s+'_close'] for s in SYMBOLS]);assert len(tt)%1440==0 and tt[0]%DAY==0 and np.isfinite(price).all() and (price>0).all();panels.append(price);clock.extend((tt[1439::1440]+60000000).tolist())
   months.append(dict(month=r['month'],SHA256=r['source_NPZ_SHA256'],bytes=r['source_NPZ_bytes']))
  warm,warmrefs=(minute22,source['records']) if year==2023 else warm24(state);yearstart=int(a['decision_us'][0]);prev=value(a['close_available_us'],a['close'],yearstart-31*DAY);minute=np.vstack([warm,*panels]);five=minute[4::5].reshape(396,288,5);zv=measure(five,prev);zv['RV_1m']=one_minute_RV(minute,prev);vt=np.array([*np.arange(yearstart-30*DAY,yearstart+DAY,DAY),*clock]);assert len(vt)==396 and np.all(np.diff(vt)==DAY);xv=features(zv);decisions=a['decision_us'];ids=np.searchsorted(vt,decisions);np.testing.assert_array_equal(vt[ids],decisions);yv=zv['RV'][ids+1];assert len(decisions)==365 and np.isfinite(xv[ids]).all() and np.isfinite(yv).all() and (yv>0).all();np.testing.assert_array_equal(five[30,-1],boundary['points'][str(year)]['trade_close']);np.savez_compressed(state/f'Y{year}.npz',**a,features=xv[ids],target_RV=yv,label_mature_us=decisions+2*DAY,panel_available_us=vt,five_close=five,previous_close=prev,**zv);validation[str(year)]=dict(days=365,pairs=1825,month_records=months,source_commit=artifact,source_index_SHA256=sha(ixraw),warm_refs=warmrefs,warm_previous_endpoint_known=bool(np.isfinite(prev).all()),INPUTS_SHA256=file_sha(state/f'Y{year}.npz'));print('ACTUAL_JUMP_SOURCE_FULL_CALENDAR',year,365,1825,flush=True)
 prep=dict(status='PASS_REAL_PATH_RV_BV_SOURCE_AND_COMMON_MATURITY',source_commit=commit,protocol_SHA256=file_sha(HERE/'PROTOCOL.json'),train_dates=int(common.sum()),admitted_decisions=d[common].tolist(),unknown_feature_decisions=d[~np.isfinite(x).all((1,2))].tolist(),unknown_label_decisions=d[~np.isfinite(y).all(1)].tolist(),purge_decisions=d[mature>=FIT].tolist(),maximum_train_maturity_us=int(mature[common].max()),TRAIN_SHA256=file_sha(state/'TRAIN.npz'),source_refs=refs,source_stats_699_RV_RS_identity='ALLCLOSE2e-14',December2022_trade=source,December2022_mark=False,validation=validation,economic_source_commit=ECON,economic_packet_SHA256=ep['SHA256'],new_fits=0,new_wallets=0,seconds=time.monotonic()-begin);assert prep['seconds']<120;save(state/'PREPARATION.json',prep);print('ACTUAL_JUMP_SOURCE_COMMON_MATURE',int(common.sum()),prep['seconds'],flush=True)
if __name__=='__main__':
 q=argparse.ArgumentParser();q.add_argument('phase',choices=['acquire','project']);q.add_argument('--state',type=Path,required=True);q.add_argument('--raw22',type=Path);q.add_argument('--source-commit',required=True);q.add_argument('--resume',action='store_true');a=q.parse_args()
 if a.phase=='acquire':acquire(a.state,a.source_commit,a.resume)
 else:project(a.state,a.raw22,a.source_commit)
