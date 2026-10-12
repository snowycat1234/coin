"""One fit pair, then both full old-calendar scores from already published coefficients."""
import argparse,io,json,time
from pathlib import Path
import numpy as np
from util import HERE,sha,save,clean,verify,public_packet
from core import DAY,FIT,SYMBOLS,fit,predict,paired_ci
PREFIX='research/mark-trade-dislocation-20261012/public/'
def arrays(raw):
 with np.load(io.BytesIO(raw),allow_pickle=False) as z:return {k:z[k].copy() for k in z.files}
def train(state,commit,inputs_commit):
 clean(commit);verify();assert not state.exists();state.mkdir(parents=True);start=time.monotonic();packet,index=public_packet(inputs_commit,PREFIX+'INPUTS/');a=arrays(packet['TRAIN.npz']);prep=json.loads(packet['PREPARATION.json']);assert prep['new_fits']==0 and tuple(a['symbol_order'])==SYMBOLS;m=fit(a['decision_us'],a['features'],a['price_return'],a['label_mature_us']);assert len(m['train_indices'])==prep['train']['common_mature_dates']
 m.update(status='FROZEN_ONE_PAIR_TRAIN_ONLY_DETERMINISTIC_OLS',source_commit=commit,inputs_commit=inputs_commit,inputs_packet_SHA256=index['SHA256'],training_seed='NONE',fit_groups=2,OLS_asset_systems=10,feature_scaler_groups=1,label_normalizer_groups=1,validation_fits=0,new_economic_references=0,new_wallets=0,seconds=time.monotonic()-start);assert m['seconds']<60;save(state/'MODEL.json',m);print('ACTUAL_MARK_TRADE_ONE_PAIR_FIT',len(m['train_indices']),m['maximum_train_maturity_us'],m['seconds'],flush=True)
def score(state,commit,inputs_commit,model_commit):
 clean(commit);verify();assert not state.exists();state.mkdir(parents=True);start=time.monotonic();inputs,ix=public_packet(inputs_commit,PREFIX+'INPUTS/');models,mi=public_packet(model_commit,PREFIX+'MODEL/');m=json.loads(models['MODEL.json']);assert m['inputs_commit']==inputs_commit and m['inputs_packet_SHA256']==ix['SHA256'];years={};ystd=np.array(m['label_std'])
 for year,seed in ((2023,811750),(2025,811751)):
  a=arrays(inputs[f'Y{year}.npz']);d=a['decision_us'];assert len(d)==365 and np.all(np.diff(d)==DAY) and tuple(a['symbol_order'])==SYMBOLS;candidate,control=predict(m,a['features']);lc=((candidate-a['price_return'])/ystd)**2;lb=((control-a['price_return'])/ystd)**2;delta=(lb-lc).mean(1);gain=1-lc.mean()/lb.mean();ci,starts,draws=paired_ci(delta,seed,True);gates=dict(complete_365x5=bool(np.isfinite(lc).all() and np.isfinite(lb).all()),normalized_MSE_gain_ge_2pct=bool(gain>=.02),paired_CI_lower_positive=bool(ci[0]>0));np.savez_compressed(state/f'Y{year}.npz',decision_us=d,candidate_prediction=candidate,control_prediction=control,candidate_normalized_loss=lc,control_normalized_loss=lb,joint_daily_loss_increment=delta,bootstrap_starts=starts,bootstrap_means=draws)
  years[str(year)]=dict(calendar_days=365,asset_pairs=1825,role='OLD_SEEN_DEVELOPMENT_NOT_NEW_OOS',candidate_normalized_MSE=float(lc.mean()),control_normalized_MSE=float(lb.mean()),normalized_MSE_gain=float(gain),daily_loss_increment_mean=float(delta.mean()),paired14day95CI=ci,bootstrap_seed=seed,gates=gates,all_information_gates=all(gates.values()));print('ACTUAL_MARK_TRADE_FULL_YEAR_INFORMATION',year,gain,ci,gates,flush=True)
 passed=all(r['all_information_gates'] for r in years.values());result=dict(status='PASS_INFORMATION_NEXT_FROZEN_ECONOMICS_REQUIRED' if passed else 'STOP_FIXED_MARK_TRADE_CONDITIONAL_INFORMATION_GATE',project='ACTIVE',source_commit=commit,inputs_commit=inputs_commit,inputs_packet_SHA256=ix['SHA256'],model_commit=model_commit,model_packet_SHA256=mi['SHA256'],years=years,all_information_gates=passed,economics='PENDING_FROZEN_STAGE' if passed else 'NOT_RUN_INFORMATION_GATE_FAILED',new_validation_fits=0,new_economic_references=0,new_native_wallets=0,new_provider_ZIPs=0,seconds=time.monotonic()-start);assert result['seconds']<60;save(state/'RESULTS.json',result)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('phase',choices=['fit','score']);p.add_argument('--state',type=Path,required=True);p.add_argument('--source-commit',required=True);p.add_argument('--inputs-commit',required=True);p.add_argument('--model-commit');a=p.parse_args()
 if a.phase=='fit':train(a.state,a.source_commit,a.inputs_commit)
 else:score(a.state,a.source_commit,a.inputs_commit,a.model_commit)
