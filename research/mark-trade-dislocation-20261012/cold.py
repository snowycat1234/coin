"""Public packets: exact source features, saved OLS optimum, predictions and saved bootstrap arithmetic.

No fit, optimizer, RNG draw, provider request or account transition is executed.
"""
import argparse,io,json,sys,time
from pathlib import Path
import numpy as np
from core import DAY,START,FIT,SYMBOLS,features,predict
from util import HERE,ROOT,sha,file_sha,save,verify,public_packet
PREFIX='research/mark-trade-dislocation-20261012/public/'
def arrays(raw):
 with np.load(io.BytesIO(raw),allow_pickle=False) as z:return {k:z[k].copy() for k in z.files}
def restore(state,commit):
 assert not state.exists();state.mkdir(parents=True);begin=time.monotonic();blocked=[];prefixes=json.loads((HERE/'evidence/ORIGINAL_STATE_PREFIXES.json').read_text())
 def audit(event,args):
  if event=='open' and isinstance(args[0],(str,bytes)):
   p=Path(args[0]).absolute()
   if any(p.is_relative_to(Path(q)) for q in prefixes):blocked.append(str(p));raise RuntimeError('Original scientific STATE forbidden')
 sys.addaudithook(audit);verify();packets={};indices={};total=0
 for kind in ('INPUTS','MODEL','SCORES'):
  packet,index=public_packet(commit,PREFIX+kind+'/');packets[kind]=packet;indices[kind]=index;total+=index['bytes']
  for name,b in packet.items():
   n=Path(name);assert not n.is_absolute() and '..' not in n.parts;p=state/kind/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(b)
 a=arrays(packets['INPUTS']['TRAIN.npz']);prep=json.loads(packets['INPUTS']['PREPARATION.json']);m=json.loads(packets['MODEL']['MODEL.json']);r=json.loads(packets['SCORES']['RESULTS.json']);B=json.loads(packets['INPUTS']['BOUNDARY.json'])
 assert m['inputs_packet_SHA256']==r['inputs_packet_SHA256']==indices['INPUTS']['SHA256'] and r['model_packet_SHA256']==indices['MODEL']['SHA256'];assert m['inputs_commit']==r['inputs_commit'];assert sha(packets['INPUTS']['TRAIN.npz'])==prep['train']['TRAIN_SHA256'] and sha(packets['INPUTS']['BOUNDARY.json'])==prep['boundary_SHA256'] and prep['new_fits']==prep['new_wallets']==0
 np.testing.assert_array_equal(a['features'],features(a['trade_close'],a['previous_trade_close'],a['mark_close'],a['pair_complete']));np.testing.assert_array_equal(a['label_mature_us'],a['decision_us']+2*DAY)
 known=np.isfinite(a['p0'])&np.isfinite(a['p1'])&(a['p0']>0)&(a['p1']>0);y=np.full_like(a['p0'],np.nan);np.divide(a['p1'],a['p0'],out=y,where=known);y[known]-=1;np.testing.assert_array_equal(y,a['price_return']);ix=np.flatnonzero((a['decision_us']>=START)&(a['decision_us']<FIT)&(a['label_mature_us']<FIT)&np.isfinite(a['features']).all((1,2))&np.isfinite(y).all(1));np.testing.assert_array_equal(ix,m['train_indices']);assert len(ix)==prep['train']['common_mature_dates']==690
 x=a['features'][ix];y=y[ix];np.testing.assert_array_equal(x.mean(0),m['feature_mean']);np.testing.assert_array_equal(x.std(0,ddof=1),m['feature_std']);np.testing.assert_array_equal(y.std(0,ddof=1),m['label_std']);assert int(a['label_mature_us'][ix].max())==m['maximum_train_maturity_us']<FIT;scaled=(x-np.array(m['feature_mean']))/np.array(m['feature_std']);residual=0.
 for j in range(5):
  pc=np.column_stack((np.ones(len(ix)),scaled[:,j,0]));pa=np.column_stack((pc,scaled[:,j,1]))
  for design,beta in ((pc,np.array(m['control_coefficients'])[j]),(pa,np.array(m['candidate_coefficients'])[j])):residual=max(residual,float(np.max(np.abs(design.T@(y[:,j]-design@beta)))))
 assert residual<1e-9;years={};sigma=np.array(m['label_std'])
 for year in (2023,2025):
  raw=packets['INPUTS'][f'Y{year}.npz'];assert sha(raw)==prep['validation'][str(year)]['INPUTS_SHA256'];v=arrays(raw);s=arrays(packets['SCORES'][f'Y{year}.npz']);d=v['decision_us'];assert len(d)==365 and np.all(np.diff(d)==DAY) and tuple(v['symbol_order'])==SYMBOLS;np.testing.assert_array_equal(d,s['decision_us']);np.testing.assert_array_equal(v['features'],features(v['trade_close'],v['previous_trade_close'],v['mark_close'],np.ones((365,5),bool)));np.testing.assert_array_equal(v['price_return'],v['p1']/v['p0']-1)
  candidate,control=predict(m,v['features']);np.testing.assert_array_equal(candidate,s['candidate_prediction']);np.testing.assert_array_equal(control,s['control_prediction']);lc=((candidate-v['price_return'])/sigma)**2;lb=((control-v['price_return'])/sigma)**2;delta=(lb-lc).mean(1);np.testing.assert_array_equal(lc,s['candidate_normalized_loss']);np.testing.assert_array_equal(lb,s['control_normalized_loss']);np.testing.assert_array_equal(delta,s['joint_daily_loss_increment']);assert s['bootstrap_starts'].shape==(1000,27);saved_means=[]
  for starts in s['bootstrap_starts']:
   idx=np.concatenate([(t+np.arange(14))%365 for t in starts])[:365];saved_means.append(float(delta[idx].mean()))
  np.testing.assert_array_equal(saved_means,s['bootstrap_means']);ci=[float(q) for q in np.quantile(saved_means,[.025,.975])];row=r['years'][str(year)];assert float(lc.mean())==row['candidate_normalized_MSE'] and float(lb.mean())==row['control_normalized_MSE'] and float(1-lc.mean()/lb.mean())==row['normalized_MSE_gain'] and ci==row['paired14day95CI'];assert not row['all_information_gates'];years[str(year)]=dict(natural_dates=365,asset_pairs=1825,features_predictions_loss_bootstrap_bits='EXACT',new_RNG_draws=0)
 assert r['status']=='STOP_FIXED_MARK_TRADE_CONDITIONAL_INFORMATION_GATE' and r['new_native_wallets']==r['new_economic_references']==r['new_validation_fits']==0 and r['economics']=='NOT_RUN_INFORMATION_GATE_FAILED';assert B['new_provider_ZIPs']==10 and B['verified_reused_ZIPs']==10 and not B['full2022Dec_certified']
 # New raw daily bodies are fully restored; old monthly originals retain exact Git/member refs.
 for q in B['records']:
  if q['transport_status']=='REUSED_GIT_ORIGINAL':assert q['Git_commit']=='d69e9ac94478c5be54cb46c622afec7aaf3c61f7' and q['whole_month_grid_verified'];continue
  b=packets['INPUTS'][q['raw_path']];c=packets['INPUTS'][q['raw_path']+'.CHECKSUM'];assert sha(b)==q['SHA256']==c.decode().split()[0] and sha(c)==q['checksum_SHA256'] and len(b)==q['bytes']
 proof=dict(status='PASS_EXACT_PUBLIC_MARK_TRADE_ZERO_REFIT',artifact_commit=commit,packet_bytes=total,train_dates=len(ix),maximum_OLS_optimum_residual=residual,validation=years,saved_forecast_scalar_matrix_checks=7300,saved_bootstrap_mean_arithmetic_checks=2000,raw_daily_ZIPs_recovered=10,monthly_Git_original_reference_records=10,new_fits=0,new_scientific_prediction_sets=0,new_bootstrap_draws=0,new_economic_references=0,new_native_wallets=0,provider_GETs=0,original_STATE_open_attempts=len(blocked),seconds=time.monotonic()-begin);assert not blocked;save(state/'PUBLIC_RESTORE.json',proof);print('ACTUAL_MARK_TRADE_PUBLIC_ZERO_REFIT_PASS',len(ix),total,residual,proof['seconds'],flush=True)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--state',type=Path,required=True);p.add_argument('--artifact-commit',required=True);a=p.parse_args();restore(a.state,a.artifact_commit)
