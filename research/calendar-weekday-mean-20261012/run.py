"""One published analytic fit, then two mandatory untouched-history scores."""
import argparse,json,time,subprocess
from pathlib import Path
import numpy as np
from core import fit,predict,losses,FIT,DAY
from prepare import ROOT,HERE,SYMBOLS,sha,save,load
reference=load('calendar_unchanged_reference',ROOT/'research/settled-funding-direction-20261012/core.py')
def frozen(commit):
 assert not subprocess.check_output(['git','status','--porcelain'],cwd=ROOT) and subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT).decode().strip()==commit
def train(state,prepared,commit):
 frozen(commit);assert not state.exists();state.mkdir(parents=True);begin=time.monotonic();prep=json.loads((prepared/'PREPARATION.json').read_text());assert prep['status']=='PASS_REAL_CALENDAR_PRICE_LABEL_SOURCE' and prep['protocol_SHA256']==sha((HERE/'PROTOCOL.json').read_bytes());assert sha((prepared/'TRAIN_INPUTS.npz').read_bytes())==prep['train']['TRAIN_INPUTS_SHA256']
 with np.load(prepared/'TRAIN_INPUTS.npz',allow_pickle=False) as z:
  assert tuple(z['symbol_order'])==SYMBOLS;d=z['decision_us'];y=z['price_return'];mature=z['label_mature_us'];np.testing.assert_array_equal(mature,d+2*DAY);model=fit(d,y,mature)
  # Verification-only direct training prefix arithmetic, zero extra fits.
  ix=np.array(model['train_indices']);known=np.isfinite(y).all(1)&(mature<FIT);np.testing.assert_array_equal(ix,np.flatnonzero(known));assert len(ix)==prep['train']['common_mature_train_dates'];assert model['maximum_train_maturity_us']<FIT
 model.update(symbol_order=list(SYMBOLS),source_commit=commit,PREPARATION_SHA256=sha((prepared/'PREPARATION.json').read_bytes()),protocol_SHA256=prep['protocol_SHA256']);save(state/'MODEL.json',model)
 report=dict(status='PASS_FROZEN_ACTUAL_CALENDAR_TRAINING',actual_mature_training_dates=len(model['train_indices']),weekday_training_counts=model['weekday_train_counts'],candidate_fits=1,constant_control_fits=1,normalizer_fits=1,validation_fits=0,new_references=0,provider_GETs=0,model_SHA256=sha((state/'MODEL.json').read_bytes()),source_commit=commit,seconds=time.monotonic()-begin);save(state/'TRAINING.json',report);assert time.monotonic()-begin<60;print('ACTUAL_CALENDAR_FIT',report['actual_mature_training_dates'],report['weekday_training_counts'],model['maximum_train_maturity_us'],report['model_SHA256'],flush=True)
def score(state,prepared,modelpath,commit):
 frozen(commit);assert not state.exists();state.mkdir(parents=True);begin=time.monotonic();prep=json.loads((prepared/'PREPARATION.json').read_text());model=json.loads(modelpath.read_text());assert sha((prepared/'PREPARATION.json').read_bytes())==model['PREPARATION_SHA256'] and model['protocol_SHA256']==prep['protocol_SHA256']==sha((HERE/'PROTOCOL.json').read_bytes());index=json.loads((HERE/'public/MODEL/INDEX.json').read_text());assert sha(modelpath.read_bytes())==index['members']['MODEL.json']['SHA256'];years={}
 for year,seed in ((2023,811746),(2025,811747)):
  p=prepared/f'Y{year}.npz';assert sha(p.read_bytes())==prep['validation'][str(year)]['INPUTS_SHA256']
  with np.load(p,allow_pickle=False) as z:
   d=z['decision_us'];y=z['price_return'];assert tuple(z['symbol_order'])==SYMBOLS and len(d)==365 and y.shape==(365,5) and np.isfinite(y).all();a,b=predict(model,d);la,lb=losses(model,d,y);delta=(lb-la).mean(1);ci=reference.paired_ci(delta,seed);gain=1-float(la.mean()/lb.mean());np.savez_compressed(state/f'Y{year}_FORECASTS.npz',decision_us=d,label_mature_us=z['label_mature_us'],price_return=y,candidate_prediction=a,constant_prediction=b,candidate_normalized_squared_loss=la,constant_normalized_squared_loss=lb,paired_date_loss_improvement=delta,symbol_order=np.array(SYMBOLS))
  gates=dict(full_common365_labels=True,normalized_MSE_gain_atleast2percent=gain>=.02,paired_date95CI_lower_positive=ci[0]>0)
  years[str(year)]=dict(rows=365,asset_labels=1825,candidate_normalized_MSE=float(la.mean()),constant_normalized_MSE=float(lb.mean()),MSE_gain_fraction=gain,mean_daily_joint_asset_loss_improvement=float(delta.mean()),paired_daily_loss_improvement95CI=ci,gates=gates,bootstrap_seed=seed,FORECASTS_SHA256=sha((state/f'Y{year}_FORECASTS.npz').read_bytes()));print('ACTUAL_CALENDAR_INFORMATION_GATE',year,gain,ci,gates,flush=True)
 passed=all(all(r['gates'].values()) for r in years.values());out=dict(status='PASS_CALENDAR_INFORMATION_NEXT_FIXED_ECONOMICS_REQUIRED' if passed else 'STOP_FIXED_CALENDAR_INFORMATION_GATE',years=years,source_commit=commit,MODEL_SHA256=sha(modelpath.read_bytes()),PREPARATION_SHA256=sha((prepared/'PREPARATION.json').read_bytes()),scientific_recipes=1,candidate_fits=1,constant_control_fits=1,normalizer_fits=1,validation_fits=0,new_reference_calls=0,new_native_wallets=0,provider_GETs=0,old_fits_or_wallet_replays=0,economics='NOT_RUN_INFORMATION_GATE_FAILED' if not passed else 'NOT_YET_RUN',scope='SEEN2023_2025_CALENDAR_CONDITIONAL_PRICE_FORECAST_NOT_NET_INCOME_OR_UNSEEN',seconds=time.monotonic()-begin);save(state/'RESULT.json',out);assert time.monotonic()-begin<60;print('ACTUAL_CALENDAR_RESULT',out['status'],flush=True)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('phase',choices=['fit','score']);p.add_argument('--state',type=Path,required=True);p.add_argument('--prepared',type=Path,required=True);p.add_argument('--model',type=Path);p.add_argument('--source-commit',required=True);a=p.parse_args()
 if a.phase=='fit':train(a.state,a.prepared,a.source_commit)
 else:score(a.state,a.prepared,a.model,a.source_commit)
