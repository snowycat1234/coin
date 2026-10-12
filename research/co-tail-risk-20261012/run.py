"""Train thresholds and two OLS systems, publish before both mandatory scalar risk scores."""
import argparse,json,time
from pathlib import Path
import numpy as np
from core import DAY,fit,predict,qlike,bootstrap
from source import original,aligned,npz
from util import HERE,sha,save,verify,clean,public_packet
PREFIX='research/co-tail-risk-20261012/public/'
def train(state,commit,inputs_commit):
 clean(commit);verify();assert not state.exists();state.mkdir(parents=True);begin=time.monotonic();packet,index=public_packet(inputs_commit,PREFIX+'INPUTS/');prep=json.loads(packet['PREPARATION.json']);a=npz(packet['TRAIN.npz']);old,oldix=original();derived,Z=aligned(old['TRAIN.npz'])
 for k in a:np.testing.assert_array_equal(a[k],derived[k])
 m=fit(a['decision_us'],a['base_features'],a['causal_sigma5m'],Z,a['target_basket_RV'],a['label_mature_us']);assert len(m['train_indices'])==prep['train_common_dates'];m.update(source_commit=commit,inputs_commit=inputs_commit,inputs_packet_SHA256=index['SHA256'],original_packet_SHA256=oldix['SHA256'],threshold_groups=1,threshold_values=5,OLS_systems=2,normalizer_groups=1,train_smear_values=2,training_seed='NONE',validation_fits=0,new_native_wallets=0,seconds=time.monotonic()-begin);assert m['seconds']<60;save(state/'MODEL.json',m);print('ACTUAL_CO_TAIL_ONE_FROZEN_THRESHOLD_OLS_PAIR',len(m['train_indices']),m['threshold_absZ_q95'],m['seconds'],flush=True)
def score(state,commit,inputs_commit,model_commit):
 clean(commit);verify();assert not state.exists();state.mkdir(parents=True);begin=time.monotonic();packet,ix=public_packet(inputs_commit,PREFIX+'INPUTS/');models,mi=public_packet(model_commit,PREFIX+'MODEL/');m=json.loads(models['MODEL.json']);assert m['inputs_commit']==inputs_commit and m['inputs_packet_SHA256']==ix['SHA256'];old,oi=original();assert oi['SHA256']==m['original_packet_SHA256'];years={}
 for year,seed in ((2023,811754),(2025,811755)):
  a=npz(packet[f'Y{year}.npz']);derived,Z=aligned(old[f'Y{year}.npz'])
  for k in a:np.testing.assert_array_equal(a[k],derived[k])
  d=a['decision_us'];assert len(d)==365 and np.all(np.diff(d)==DAY);pred,x=predict(m,a['base_features'],Z);lc=qlike(a['target_basket_RV'],pred['CO_TAIL']);lb=qlike(a['target_basket_RV'],pred['CONTROL']);delta=lb-lc;gain=float(1-lc.mean()/lb.mean());ci,starts,means=bootstrap(delta,seed);gates=dict(complete365=True,mean_QLIKE_gain_ge2pct=gain>=.02,paired_CI_lower_positive=ci[0]>0);np.savez_compressed(state/f'Y{year}.npz',decision_us=d,full_features=x,candidate_basket_RV=pred['CO_TAIL'],control_basket_RV=pred['CONTROL'],candidate_QLIKE=lc,control_QLIKE=lb,daily_loss_increment=delta,bootstrap_starts=starts,bootstrap_means=means)
  years[str(year)]=dict(days=365,role='OLD_SEEN_DEVELOPMENT',candidate_QLIKE=float(lc.mean()),control_QLIKE=float(lb.mean()),relative_QLIKE_gain=gain,paired14day95CI=ci,seed=seed,gates=gates,information_pass=all(gates.values()),log_RV_MSE_candidate=float(((np.log(a['target_basket_RV'])-np.log(pred['CO_TAIL']))**2).mean()),log_RV_MSE_control=float(((np.log(a['target_basket_RV'])-np.log(pred['CONTROL']))**2).mean()),mean_co_excess=float(x[:,-1].mean()),negative_co_excess_days=int((x[:,-1]<0).sum()),maximum_co_excess=float(x[:,-1].max()));print('ACTUAL_CO_TAIL_FULL_CALENDAR_RISK_GATE',year,gain,ci,gates,flush=True)
 passed=all(q['information_pass'] for q in years.values());r=dict(status='PASS_INFORMATION_REQUIRES_REAL_ECONOMIC_CONTROL' if passed else 'STOP_FIXED_CO_TAIL_RISK_INFORMATION_GATE',project='ACTIVE',source_commit=commit,inputs_commit=inputs_commit,model_commit=model_commit,inputs_packet_SHA256=ix['SHA256'],model_packet_SHA256=mi['SHA256'],years=years,information_pass=passed,prediction_target='FIXED_LINEAR_LOGRETURN_BASKET_RV_PROXY_NOT_NAV_RISK_OR_INCOME',economics='PENDING_REQUIRED_STAGE' if passed else 'NOT_RUN_FAILED_INFORMATION',new_validation_fits=0,new_economic_refs=0,new_native_wallets=0,provider_downloads=0,seconds=time.monotonic()-begin);assert r['seconds']<60;save(state/'RESULTS.json',r)
if __name__=='__main__':
 q=argparse.ArgumentParser();q.add_argument('phase',choices=['fit','score']);q.add_argument('--state',type=Path,required=True);q.add_argument('--source-commit',required=True);q.add_argument('--inputs-commit',required=True);q.add_argument('--model-commit');a=q.parse_args()
 if a.phase=='fit':train(a.state,a.source_commit,a.inputs_commit)
 else:score(a.state,a.source_commit,a.inputs_commit,a.model_commit)
