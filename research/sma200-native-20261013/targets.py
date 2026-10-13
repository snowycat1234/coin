"""Exact main signed intent; no alternate trend formula or risk policy."""
import argparse,io,json,time,zipfile
from pathlib import Path
import numpy as np
import pandas as pd
from scripts.research.joint_expert_information import signed_intents
from native_apis import HERE,ROOT,DAY,SYMBOLS,git,sha,file_sha,save,proto,verify,clean,window
SOURCE='53357f33f4e6ccb536af762fbff39b269c24d837';PREFIX='research/settled-funding-direction-20261012/public/INPUTS_FINAL/'
def weights(t,p,d):
 assert p.shape==(len(t),5) and np.all(np.diff(t)==DAY) and d.ndim==1
 mean=pd.DataFrame(p).rolling(200,min_periods=200).mean().to_numpy();signal=np.sign(p-mean);allw=signed_intents(p,signal,t,SYMBOLS);ids=np.searchsorted(t,d);np.testing.assert_array_equal(t[ids],d)
 for k in ids:assert k>=199 and np.isfinite(p[k-199:k+1]).all() and (p[k-199:k+1]>0).all() and np.isfinite(signal[k]).all()
 out=allw[ids,0];assert np.isfinite(out).all() and np.abs(out).max()<=.3+1e-12 and np.abs(out).sum(1).max()<=.6+1e-12
 return out,signal[ids],mean[ids],ids
def prepare(state,commit):
 clean(commit);verify();assert not state.exists();state.mkdir(parents=True);begin=time.monotonic();ix=json.loads(git(SOURCE+':'+PREFIX+'INDEX.json'));raw=git(SOURCE+':'+PREFIX+'PACKET.zip');assert sha(raw)==ix['SHA256']=='0d2cf51769f2c9444c83b1715c5a6fd730d282e96cc4e84d1feaecf482ffdcd2';reports={}
 with zipfile.ZipFile(io.BytesIO(raw)) as z:
  assert z.testzip() is None
  for key in ('Y2023','Y2025'):
   body=z.read(key+'.npz');assert sha(body)==ix['members'][key+'.npz']['SHA256']
   with np.load(io.BytesIO(body),allow_pickle=False) as a:t=a['close_available_us'].copy();p=a['close'].copy();d=a['decision_us'].copy();assert tuple(a['symbol_order'])==SYMBOLS
   w,sma,mean,ids=weights(t,p,d);win=window(key);assert len(d)==365;np.testing.assert_array_equal(d,np.arange(win['start'],win['end'],DAY));diary=win['daily'].sort('close_us','symbol');latest={s:win['daily'].filter(__import__('polars').col('symbol')==s).sort('close_us')['close'].to_numpy() for s in SYMBOLS}
   np.testing.assert_array_equal(p[ids],np.column_stack([latest[s] for s in SYMBOLS]));cut=d[180];pc=p.copy();pc[t>cut]=np.nan;alt,alt_signal,_,_=weights(t[t<=cut],pc[t<=cut],d[d<=cut]);np.testing.assert_array_equal(alt,w[d<=cut]);np.testing.assert_array_equal(alt_signal,sma[d<=cut]);np.savez_compressed(state/(key+'.npz'),decision_us=d,symbol_order=np.array(SYMBOLS),SMA200_10PCT=w,direction=sma,mean200=mean,completed_close=p[ids]);W=proto()['windows'][key];control={}
   for name in ('RESULT.json','BINDING.json'):
    path=ROOT/W['CS_summary_prefix']/name;assert path.read_bytes()==git(W['CS_summary_commit']+':'+str(path.relative_to(ROOT)));control[name]=file_sha(path)
   reports[key]=dict(target_SHA256=file_sha(state/(key+'.npz')),source_member_SHA256=sha(body),source_index_SHA256=file_sha(Path(W['prepared'])/'SOURCE_INDEX.json'),calendar=W['calendar'],days=365,earliest_required_completed_close_available_us=int(t[ids[0]-199]),last_used_completed_close_available_us=int(d[-1]),source_clock_and_native_daily_close_bits='EXACT',future_price_nan_prefix='EXACT',main_function='UNMODIFIED_SIGNED_INTENTS_SMA_COLUMN0',risk='DOWN_SCALE_ONLY',long_asset_days=int((w>0).sum()),short_asset_days=int((w<0).sum()),flat_asset_days=int((w==0).sum()),mean_target_gross=float(np.abs(w).sum(1).mean()),control_SHA256=control);print('ACTUAL_SMA200_NATIVE_TARGETS_READY',key,365,reports[key]['long_asset_days'],reports[key]['short_asset_days'],flush=True)
 out=dict(status='PASS_ORIGINAL_MAIN_SMA200_FULL_YEAR_NATIVE_TARGET_SOURCE',source_commit=commit,protocol_SHA256=file_sha(HERE/'PROTOCOL.json'),main_commit=proto()['main_commit'],input_source_commit=SOURCE,input_packet_SHA256=ix['SHA256'],years=reports,new_fits=0,new_wallets=0,downloads=0,seconds=time.monotonic()-begin);assert out['seconds']<120;save(state/'READINESS.json',out)
if __name__=='__main__':
 q=argparse.ArgumentParser();q.add_argument('--state',type=Path,required=True);q.add_argument('--source-commit',required=True);a=q.parse_args();prepare(a.state,a.source_commit)
