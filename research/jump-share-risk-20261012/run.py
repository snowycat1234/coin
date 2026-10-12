"""One published-cohort OLS pair then both full-calendar QLIKE gates."""
import argparse,io,json,time
from pathlib import Path
import numpy as np
from core import DAY,SYMBOLS,fit,predict,qlike,bootstrap
from util import HERE,sha,save,clean,verify,public_packet
PREFIX='research/jump-share-risk-20261012/public/'
def arrays(raw):
 with np.load(io.BytesIO(raw),allow_pickle=False) as z:return {k:z[k].copy() for k in z.files}
def train(state,commit,inputs_commit):
 clean(commit);verify();assert not state.exists();state.mkdir(parents=True);begin=time.monotonic();packet,ix=public_packet(inputs_commit,PREFIX+'INPUTS/');a=arrays(packet['TRAIN.npz']);prep=json.loads(packet['PREPARATION.json']);assert prep['new_fits']==0 and tuple(a['symbol_order'])==SYMBOLS;m=fit(a['decision_us'],a['features'],a['target_RV'],a['label_mature_us']);assert len(m['train_indices'])==prep['train_dates'];m.update(source_commit=commit,inputs_commit=inputs_commit,inputs_packet_SHA256=ix['SHA256'],fit_groups=2,OLS_asset_systems=10,training_seed='NONE',validation_fits=0,smearing_train_only=True,new_wallets=0,seconds=time.monotonic()-begin);assert m['seconds']<60;save(state/'MODEL.json',m);print('ACTUAL_JUMP_RISK_ONE_PAIR_FIT',len(m['train_indices']),m['maximum_train_maturity_us'],m['seconds'],flush=True)
def score(state,commit,inputs_commit,model_commit):
 clean(commit);verify();assert not state.exists();state.mkdir(parents=True);begin=time.monotonic();packet,ix=public_packet(inputs_commit,PREFIX+'INPUTS/');models,mi=public_packet(model_commit,PREFIX+'MODEL/');m=json.loads(models['MODEL.json']);assert m['inputs_commit']==inputs_commit and m['inputs_packet_SHA256']==ix['SHA256'];years={}
 for year,seed in ((2023,811752),(2025,811753)):
  a=arrays(packet[f'Y{year}.npz']);d=a['decision_us'];assert len(d)==365 and np.all(np.diff(d)==DAY) and tuple(a['symbol_order'])==SYMBOLS;p=predict(m,a['features']);lc=qlike(a['target_RV'],p['JUMP']);lb=qlike(a['target_RV'],p['CONTROL']);delta=(lb-lc).mean(1);gain=float(1-lc.mean()/lb.mean());ci,starts,means=bootstrap(delta,seed);asset_improved=int((lc.mean(0)<lb.mean(0)).sum());gates=dict(complete365x5=True,mean_QLIKE_gain_ge2pct=gain>=.02,paired95CI_lower_positive=ci[0]>0,atleast3of5asset_QLIKE=asset_improved>=3);np.savez_compressed(state/f'Y{year}.npz',decision_us=d,candidate_RV=p['JUMP'],control_RV=p['CONTROL'],candidate_QLIKE=lc,control_QLIKE=lb,joint_daily_loss_increment=delta,bootstrap_starts=starts,bootstrap_means=means)
  years[str(year)]=dict(days=365,pairs=1825,role='OLD_SEEN_DEVELOPMENT',candidate_mean_QLIKE=float(lc.mean()),control_mean_QLIKE=float(lb.mean()),relative_QLIKE_gain=gain,asset_QLIKE_improvements=asset_improved,paired14day95CI=ci,seed=seed,gates=gates,information_pass=all(gates.values()),log_RV_MSE_candidate=float(((np.log(a['target_RV'])-np.log(p['JUMP']))**2).mean()),log_RV_MSE_control=float(((np.log(a['target_RV'])-np.log(p['CONTROL']))**2).mean()));print('ACTUAL_JUMP_FULL_CALENDAR_RISK_INFORMATION',year,gain,ci,asset_improved,gates,flush=True)
 passed=all(r['information_pass'] for r in years.values());result=dict(status='PASS_INFORMATION_REQUIRES_COST_FUND_RISK_WALLETS' if passed else 'STOP_FIXED_JUMP_SHARE_RISK_INFORMATION_GATE',project='ACTIVE',source_commit=commit,inputs_commit=inputs_commit,model_commit=model_commit,inputs_packet_SHA256=ix['SHA256'],model_packet_SHA256=mi['SHA256'],years=years,information_pass=passed,economics='PENDING_FROZEN_STAGE' if passed else 'NOT_RUN_FAILED_INFORMATION',prediction_target='NEXT_UTC_DAY_REALISED_VARIANCE_NOT_TRADING_INCOME',new_validation_fits=0,new_economic_references=0,new_native_wallets=0,new_provider_ZIPs=0,seconds=time.monotonic()-begin);assert result['seconds']<60;save(state/'RESULTS.json',result)
if __name__=='__main__':
 q=argparse.ArgumentParser();q.add_argument('phase',choices=['fit','score']);q.add_argument('--state',type=Path,required=True);q.add_argument('--source-commit',required=True);q.add_argument('--inputs-commit',required=True);q.add_argument('--model-commit');a=q.parse_args()
 if a.phase=='fit':train(a.state,a.source_commit,a.inputs_commit)
 else:score(a.state,a.source_commit,a.inputs_commit,a.model_commit)
