"""Immutable published paths only; certify essential known warm anchors, zero providers."""
import argparse,io,json,os,time,zipfile
from pathlib import Path
import numpy as np
from core import DAY,START,FIT,geometry,cohort
from util import HERE,ROOT,git,sha,file_sha,save,verify,clean,public_packet
OLD='f46229d072d82ad63553dc163d943d04e7b8f439';OLDPREFIX='research/jump-share-risk-20261012/public/INPUTS/';WARM='d69e9ac94478c5be54cb46c622afec7aaf3c61f7'
def npz(b):
 with np.load(io.BytesIO(b),allow_pickle=False) as z:return {k:z[k].copy() for k in z.files}
def original():
 packet,ix=public_packet(OLD,OLDPREFIX);assert ix['SHA256']=='285528c6c0e204e5d69632a4fdc7dd5ee5f17aeeeaffc2292a5fcea90e10a9ac';return packet,ix
def aligned(raw):
 z=npz(raw);g=geometry(z);d=z['decision_us'];available=z['panel_available_us'];ids=np.searchsorted(available,d);inside=(ids<len(available))&(d>=available[0]);assert np.all(available[ids[inside]]==d[inside]);base=np.full((len(d),22),np.nan);scale=np.full((len(d),5),np.nan);standard=np.full((len(d),288,5),np.nan);base[inside]=g['base'][ids[inside]];scale[inside]=g['scale'][ids[inside]]
 with np.errstate(invalid='ignore',divide='ignore'):standard[inside]=g['returns'][ids[inside]]/scale[inside,None,:]
 target_pos=np.searchsorted(available,d+DAY);np.testing.assert_array_equal(available[target_pos],d+DAY);y=g['basket_RV'][target_pos];return dict(decision_us=d,base_features=base,causal_sigma5m=scale,target_basket_RV=y,label_mature_us=d+2*DAY),standard
def anchor2024(state,commit):
 os.environ.update(WORK_DIR=str(state/'work'),RAW_CACHE_DIR=str(state/'raw'),WARMUP_START='2024-11-01',START_DATE='2024-11-01',END_DATE='2024-11-30',SYMBOLS='BTCUSDT,ETHUSDT,SOLUSDT,XRPUSDT,DOGEUSDT',HTTP_RETRIES='0',MIN_FREE_GIB='15',MAX_UNCOMPRESSED_MIB='64')
 assert (ROOT/'modules/collector_research/config.env').read_bytes()==git(commit+':modules/collector_research/config.env')
 from modules.collector_research.pipeline.download import check_zip
 from modules.collector_research.pipeline.normalize import numeric_csv,validate_price
 ix=json.loads(git(WARM+':research_artifacts/native_20261008/INDEX.json'));memo={};prices=[];refs=[];left=1730419200000000;right=1733011200000000
 for s in ('BTCUSDT','ETHUSDT','SOLUSDT','XRPUSDT','DOGEUSDT'):
  name='coin_public_tail_archives_20261008_part01.zip' if s in ('BTCUSDT','ETHUSDT','DOGEUSDT') else 'coin_public_tail_archives_20261008_part02.zip'
  if name not in memo:
   wr=next(q for q in ix['files'] if q['file_name']==name);parts=[]
   for q in sorted([q for q in ix['published_files'] if q['file_name'].startswith(name+'.bytepart')],key=lambda q:q['index']):b=git(WARM+':'+q['path']);assert sha(b)==q['sha256'] and len(b)==q['bytes'];parts.append(b)
   body=b''.join(parts);assert sha(body)==wr['sha256'] and len(body)==wr['bytes'];memo[name]=(body,wr)
  body,wr=memo[name];member=f'tail_data/data/raw/klines/{s}/{s}-1m-2024-11.zip'
  with zipfile.ZipFile(io.BytesIO(body)) as archive:b=archive.read(member);check=archive.read(member+'.CHECKSUM')
  assert sha(b)==check.decode().split()[0];p=state/'anchor_raw'/s/(s+'-1m-2024-11.zip');p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(b);check_zip(p);f,dups=validate_price(numeric_csv(p),'klines',left//1000,right//1000);assert dups==0;np.testing.assert_array_equal(f.timestamp_ms.to_numpy()*1000,np.arange(left,right,60000000));assert int(f.close_time_ms.iloc[-1])*1000+1000==right;prices.append(float(f.close.iloc[-1]));refs.append(dict(symbol=s,commit=WARM,wrapper=name,wrapper_SHA256=wr['sha256'],member=member,SHA256=sha(b),CHECKSUM_SHA256=sha(check),minute_grid=43200,final_close=prices[-1],available_us=right,temporary_verified_duplicate_removed=True))
  # Only this newly created, fully verified duplicate is removed; immutable Git original remains.
  p.unlink()
 return np.array(prices),refs
def project(state,commit):
 clean(commit);verify();assert not state.exists();state.mkdir(parents=True);begin=time.monotonic();packet,oldix=original();train_old=npz(packet['TRAIN.npz']);raw25=npz(packet['Y2025.npz']);raw23=npz(packet['Y2023.npz']);np.testing.assert_array_equal(raw23['previous_close'],train_old['five_close'][698,-1]);nov24,refs=anchor2024(state,commit);np.testing.assert_array_equal(nov24,raw25['previous_close']);records={}
 for name in ('TRAIN','Y2023','Y2025'):
  base,Z=aligned(packet[name+'.npz']);assert np.isfinite(Z).all((1,2))[np.isfinite(base['causal_sigma5m']).all(1)].all();np.savez_compressed(state/(name+'.npz'),**base);records[name]=dict(SHA256=file_sha(state/(name+'.npz')),rows=len(base['decision_us']),source_member_SHA256=sha(packet[name+'.npz']))
  if name=='TRAIN':ix=cohort(base['decision_us'],base['base_features'],base['causal_sigma5m'],base['target_basket_RV'],base['label_mature_us']);assert len(ix)>=600;admitted=base['decision_us'][ix].tolist();maximum=int(base['label_mature_us'][ix].max());unknown=base['decision_us'][~np.isfinite(base['base_features']).all(1)|~np.isfinite(base['causal_sigma5m']).all(1)].tolist();purge=base['decision_us'][base['label_mature_us']>=FIT].tolist()
  else:assert len(base['decision_us'])==365 and np.all(np.diff(base['decision_us'])==DAY) and np.isfinite(base['base_features']).all() and np.isfinite(base['causal_sigma5m']).all() and (base['causal_sigma5m']>0).all() and np.isfinite(base['target_basket_RV']).all() and (base['target_basket_RV']>0).all();print('ACTUAL_CO_TAIL_SOURCE_CALENDAR',name,365,flush=True)
 prep=dict(status='PASS_REAL_SOURCE_BASE_COHORT_AND_TRUE_ANCHORS',source_commit=commit,original_source_commit=OLD,original_packet_SHA256=oldix['SHA256'],protocol_SHA256=file_sha(HERE/'PROTOCOL.json'),train_common_dates=len(ix),admitted_decisions=admitted,maximum_train_maturity_us=maximum,unknown_feature_decisions=unknown,purge_decisions=purge,records=records,anchor2023='BIT_EXACT_WITH_ORIGINAL_TRAIN_NOV30_FINALCLOSE',anchor2025=refs,threshold_fits=0,OLS_fits=0,economic_refs=0,native_wallets=0,provider_downloads=0,source_only_original_packet_no_models_or_score_read=True,seconds=time.monotonic()-begin);assert prep['seconds']<120;save(state/'PREPARATION.json',prep);print('ACTUAL_CO_TAIL_COMMON_MATURE_SOURCE',len(ix),prep['seconds'],flush=True)
if __name__=='__main__':
 q=argparse.ArgumentParser();q.add_argument('--state',type=Path,required=True);q.add_argument('--source-commit',required=True);a=q.parse_args();project(a.state,a.source_commit)
