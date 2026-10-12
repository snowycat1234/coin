"""Public exact coefficient/source/prediction/loss proof, zero model fitting."""
import argparse,io,json,sys,time
from pathlib import Path
import numpy as np
import pandas as pd
from run import HERE,ROOT,git,save,sha,inputs,labels,utc,verify
from core import predict,paired_gain

def restore(state,artifact):
 assert not state.exists() and not git('status','--porcelain');state.mkdir(parents=True);began=time.monotonic();blocked=[]
 def audit(event,args):
  if event=='open' and isinstance(args[0],(str,bytes)):
   p=Path(args[0]).absolute()
   if any(p.is_relative_to(Path('/workspace/rank-persistence-state')/n) for n in ('TRAIN_OBSERVED','VALIDATION_OBSERVED','DIRECTION_DIAGNOSIS')):blocked.append(str(p));raise RuntimeError('Original observed STATE forbidden')
 sys.addaudithook(audit);verify();prefix=str(HERE.relative_to(ROOT))+'/';paths=['model/MODEL.json','model/TRAIN_VECTORS.npz','model/TRAINING_DATES.csv','model/TRAINING_RESULT.json','result/RESULT.json','result/VALIDATION_DATES.csv','result/VALIDATION_VECTORS.npz']
 for name in paths:
  raw=git('show',artifact+':'+prefix+name);assert raw==(HERE/name).read_bytes();p=state/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(raw)
 model=json.loads((state/'model/MODEL.json').read_text());result=json.loads((state/'result/RESULT.json').read_text());d,x,raw,w=inputs();maturity=raw['true_reward_maturity_us']
 with np.load(state/'model/TRAIN_VECTORS.npz',allow_pickle=False) as z:
  for name,current in [('decision_us',d),('feature',x),('maturity_us',maturity)]:np.testing.assert_array_equal(z[name],current)
  owned=z['training_mask'];y=z['training_label'];bins=x>=model['threshold'];assert model['training_dates']==d[owned].tolist() and model['maximum_maturity_us']==int(maturity[owned].max())<model['fit_clock_us']
  assert model['threshold']==float(np.median(x[owned])) and model['constant']==float(y[owned].mean());assert model['means']==[float(y[owned&(bins==j)].mean()) for j in (0,1)]
 actual,net,reason=labels(d,raw,w,d>=utc('2022-01-01'));candidate,constant=predict(model,x)
 with np.load(state/'result/VALIDATION_VECTORS.npz',allow_pickle=False) as z:
  for name,current in [('decision_us',d),('feature',x),('maturity_us',maturity),('actual_advantage',actual),('net_return',net),('candidate',candidate),('constant',constant)]:np.testing.assert_array_equal(z[name],current)
 frame=pd.read_csv(state/'result/VALIDATION_DATES.csv');rows=[]
 for f in result['folds']:
  left,right=map(utc,f['calendar']);ids=np.flatnonzero((d>=left)&(d<right));y=actual[ids];pc=candidate[ids];p0=constant[ids];known=np.isfinite(y)&np.isfinite(pc)&(maturity[ids]<right);lc=(pc-y)**2;l0=(p0-y)**2
  assert f['natural_dates']==len(ids) and f['common_mature_dates']==int(known.sum())
  assert f['candidate_MSE']==float(lc[known].mean()) and f['constant_MSE']==float(l0[known].mean()) and f['paired_calendar_block14_gain95CI']==paired_gain(l0-lc,known)
  saved=frame[frame.fold==f['name']];np.testing.assert_array_equal(saved.decision_us,d[ids]);np.testing.assert_array_equal(saved.support,known);assert not f['gates']['paired_14day_CI_lower_positive']
  rows.append(dict(name=f['name'],natural_dates=len(ids),mature_dates=int(known.sum()),same_model='EXACT',predictions_labels_loss_bootstrap='EXACT'))
 assert result['status']=='STOP_RANK_PERSISTENCE_INFORMATION_GATE' and result['new_native_wallets']==0
 report=dict(status='PASS_PUBLIC_RANK_PERSISTENCE_ZERO_REFIT_RESTORE',artifact_commit=artifact,folds=rows,new_historical_fits=0,account_advances=0,new_wallets=0,provider_downloads=0,observed_STATE_open_attempts=len(blocked),source_risk_target_and_prefix='EXACT',seconds=time.monotonic()-began);save(state/'PUBLIC_RESTORE.json',report);print('RANK_PERSISTENCE_PUBLIC_ZERO_REFIT_PASS',report,flush=True)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--state',type=Path,required=True);p.add_argument('--artifact-commit',required=True);a=p.parse_args();restore(a.state,a.artifact_commit)
