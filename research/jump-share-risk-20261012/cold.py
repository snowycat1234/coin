"""Restore exact published paths/models/forecasts; arithmetic only, zero refits or RNG."""
import argparse,io,json,sys,time
from pathlib import Path
import numpy as np
from core import DAY,START,FIT,SYMBOLS,measure,features,predict,qlike
from source import configure,month_prices,one_minute_RV,npz
from util import HERE,git,sha,save,verify,public_packet
PREFIX='research/jump-share-risk-20261012/public/'
def restore(state,commit):
 assert not state.exists();state.mkdir(parents=True);begin=time.monotonic();blocked=[];prefixes=json.loads((HERE/'evidence/ORIGINAL_STATE_PREFIXES.json').read_text())
 def audit(event,args):
  if event=='open' and isinstance(args[0],(str,bytes)) and any(Path(args[0]).absolute().is_relative_to(Path(q)) for q in prefixes):blocked.append(str(args[0]));raise RuntimeError('Original scientific STATE forbidden')
 sys.addaudithook(audit);verify();configure(state);packets={};indices={};total=0
 for kind in ('INPUTS','MODEL','SCORES'):
  packet,index=public_packet(commit,PREFIX+kind+'/');packets[kind]=packet;indices[kind]=index;total+=index['bytes']
  for name,b in packet.items():
   n=Path(name);assert not n.is_absolute() and '..' not in n.parts;p=state/kind/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(b)
 m=json.loads(packets['MODEL']['MODEL.json']);r=json.loads(packets['SCORES']['RESULTS.json']);prep=json.loads(packets['INPUTS']['PREPARATION.json']);a=npz(packets['INPUTS']['TRAIN.npz']);assert sha(packets['INPUTS']['TRAIN.npz'])==prep['TRAIN_SHA256'];assert m['inputs_packet_SHA256']==r['inputs_packet_SHA256']==indices['INPUTS']['SHA256'] and r['model_packet_SHA256']==indices['MODEL']['SHA256'];assert m['inputs_commit']==r['inputs_commit']
 reconstructed=measure(a['five_close'],a['previous_close'])
 for k,v in reconstructed.items():np.testing.assert_array_equal(v,a[k])
 # Existing historical 1m statistics are exact immutable source values, not fitted quantities.
 raw=git(commit+':research/core5-continuous-risk600-20261011/continuous/DAILY_CONTINUOUS.npz');assert sha(raw)=='9a0e63c0b4f93b185310c65892d424e99307a6678930b5d559e421a1145edde9';old=npz(raw);np.testing.assert_array_equal(a['RV_1m'][:699],old['RV_1m']);sources=json.loads(packets['INPUTS']['DECEMBER2022_TRADE_SOURCES.json']);minute=[]
 for q in sources['records']:
  body=packets['INPUTS'][q['raw_path']];check=packets['INPUTS'][q['raw_path']+'.CHECKSUM'];assert sha(body)==q['SHA256']==check.decode().split()[0] and sha(check)==q['CHECKSUM_SHA256'] and len(body)==q['bytes'];minute.append(month_prices(state/'INPUTS'/q['raw_path'],1669852800000000,FIT))
 minute=np.column_stack(minute);np.testing.assert_array_equal(a['five_close'][699:].reshape(-1,5),minute[4::5]);np.testing.assert_array_equal(a['RV_1m'][699:],one_minute_RV(minute,a['five_close'][698,-1]));reconstructed['RV_1m']=a['RV_1m'];xx=features(reconstructed);d=a['decision_us'];available=a['panel_available_us'];ids=np.searchsorted(available,d);x=np.full((730,5,7),np.nan);inside=(ids<len(available))&(d>=available[0]);x[inside]=xx[ids[inside]];np.testing.assert_array_equal(x,a['features']);np.testing.assert_array_equal(a['target_RV'],a['RV'][np.searchsorted(available,d+DAY)]);np.testing.assert_array_equal(a['label_mature_us'],d+2*DAY);ix=np.flatnonzero((d>=START)&(d<FIT)&(a['label_mature_us']<FIT)&np.isfinite(x).all((1,2))&np.isfinite(a['target_RV']).all(1)&(a['target_RV']>0).all(1));np.testing.assert_array_equal(ix,m['train_indices']);assert len(ix)==prep['train_dates']==697
 np.testing.assert_array_equal(x[ix].mean(0),m['feature_mean']);np.testing.assert_array_equal(x[ix].std(0,ddof=1),m['feature_std']);assert int(a['label_mature_us'][ix].max())==m['maximum_train_maturity_us']<FIT;scaled=(x[ix]-np.array(m['feature_mean']))/np.array(m['feature_std']);target=np.log(a['target_RV'][ix]);residual=0.
 for arm,n in (('CONTROL',6),('JUMP',7)):
  for j in range(5):
   design=np.column_stack([np.ones(len(ix)),scaled[:,j,:n]]);beta=np.array(m['coefficients'][arm])[j];error=target[:,j]-design@beta;residual=max(residual,float(np.abs(design.T@error).max()));assert float(np.exp(error).mean())==m['smearing'][arm][j]
 assert residual<1e-8;years={}
 for year in (2023,2025):
  raw=packets['INPUTS'][f'Y{year}.npz'];assert sha(raw)==prep['validation'][str(year)]['INPUTS_SHA256'];v=npz(raw);s=npz(packets['SCORES'][f'Y{year}.npz']);z=measure(v['five_close'],v['previous_close'])
  for k,val in z.items():np.testing.assert_array_equal(val,v[k])
  z['RV_1m']=v['RV_1m'];pos=np.searchsorted(v['panel_available_us'],v['decision_us']);np.testing.assert_array_equal(v['features'],features(z)[pos]);np.testing.assert_array_equal(v['target_RV'],z['RV'][pos+1]);np.testing.assert_array_equal(v['decision_us'],s['decision_us']);assert len(pos)==365 and np.all(np.diff(v['decision_us'])==DAY);pred=predict(m,v['features']);np.testing.assert_array_equal(pred['JUMP'],s['candidate_RV']);np.testing.assert_array_equal(pred['CONTROL'],s['control_RV']);lc=qlike(v['target_RV'],pred['JUMP']);lb=qlike(v['target_RV'],pred['CONTROL']);delta=(lb-lc).mean(1);np.testing.assert_array_equal(lc,s['candidate_QLIKE']);np.testing.assert_array_equal(lb,s['control_QLIKE']);np.testing.assert_array_equal(delta,s['joint_daily_loss_increment']);saved=[];assert s['bootstrap_starts'].shape==(1000,27)
  for start in s['bootstrap_starts']:idx=((start[:,None]+np.arange(14))%365).ravel()[:365];saved.append(float(delta[idx].mean()))
  np.testing.assert_array_equal(saved,s['bootstrap_means']);row=r['years'][str(year)];assert float(lc.mean())==row['candidate_mean_QLIKE'] and float(lb.mean())==row['control_mean_QLIKE'] and float(1-lc.mean()/lb.mean())==row['relative_QLIKE_gain'] and [float(q) for q in np.quantile(saved,[.025,.975])]==row['paired14day95CI'];assert not row['information_pass'];years[str(year)]=dict(days=365,pairs=1825,path_RV_BV_features_forecast_QLIKE_saved_bootstrap_bits='EXACT',validation_1m_RV='STORED_GENUINE_SOURCE_STATISTICS_WITH_MONTH_SHA_REFS_NO_FULL1M_REPARSE')
 assert r['status']=='STOP_FIXED_JUMP_SHARE_RISK_INFORMATION_GATE' and r['new_economic_references']==r['new_native_wallets']==r['new_validation_fits']==0;assert not blocked;proof=dict(status='PASS_EXACT_PUBLIC_JUMP_RISK_ZERO_REFIT',artifact_commit=commit,packet_bytes=total,train_dates=len(ix),OLS_optimum_residual_max=residual,validation=years,restored_source_five_minute_price_points=(730+396+396)*288*5,raw_December_trade_ZIPs_reparsed=5,saved_forecast_scalar_matrix_checks=7300,saved_bootstrap_mean_arithmetic_checks=2000,new_fits=0,new_scientific_prediction_sets=0,new_RNG_draws=0,new_economic_references=0,new_native_wallets=0,provider_GETs=0,original_STATE_open_attempts=len(blocked),seconds=time.monotonic()-begin);save(state/'PUBLIC_RESTORE.json',proof);print('ACTUAL_JUMP_PUBLIC_COLD_ZERO_REFIT_PASS',len(ix),total,residual,proof['seconds'],flush=True)
if __name__=='__main__':
 q=argparse.ArgumentParser();q.add_argument('--state',type=Path,required=True);q.add_argument('--artifact-commit',required=True);a=q.parse_args();restore(a.state,a.artifact_commit)
