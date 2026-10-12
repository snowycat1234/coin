"""Exact public latest-vintage VIX/model/date/loss proof with no new fits."""
import argparse,json,sys,time
from pathlib import Path
import numpy as np
import pandas as pd
from model import HERE,ROOT,git,sha,save,inputs,predict,paired_gain,prior,utc,verify

def restore(state,artifact):
 assert not state.exists() and not git('status','--porcelain');state.mkdir(parents=True);began=time.monotonic();blocked=[]
 def audit(event,args):
  if event=='open' and isinstance(args[0],(str,bytes)):
   p=Path(args[0]).absolute()
   if any(p.is_relative_to(Path('/workspace/vix-advantage-state')/n) for n in ('SOURCE_OBSERVED','TRAIN_OBSERVED','VALIDATION_OBSERVED')) or any(p.is_relative_to(Path('/workspace/rank-persistence-state')/n) for n in ('TRAIN_OBSERVED','VALIDATION_OBSERVED')):blocked.append(str(p));raise RuntimeError('Observed STATE forbidden')
 sys.addaudithook(audit);verify();prefix=str(HERE.relative_to(ROOT))+'/';names=['source/VIXCLS.csv','source/VIX_OBSERVATIONS.npz','source/SOURCE_RESULT.json','model/MODEL.json','model/TRAIN_VECTORS.npz','model/TRAINING_DATES.csv','model/TRAINING_RESULT.json','result/RESULT.json','result/VALIDATION_VECTORS.npz','result/VALIDATION_DATES.csv']
 for name in names:
  raw=git('show',artifact+':'+prefix+name);assert raw==(HERE/name).read_bytes();p=state/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(raw)
 model=json.loads((state/'model/MODEL.json').read_text());source=json.loads((state/'source/SOURCE_RESULT.json').read_text());result=json.loads((state/'result/RESULT.json').read_text());assert sha(state/'source/VIXCLS.csv')==source['raw_SHA256']==model['raw_source_SHA256']
 d,x,raw,w,obs,available,age,proof=inputs();maturity=raw['true_reward_maturity_us'];known=np.isfinite(x);assert np.all(available[known]<=d[known]) and np.all(age[known]<=4*86400000000)
 with np.load(state/'model/TRAIN_VECTORS.npz',allow_pickle=False) as z:
  for name,current in [('decision_us',d),('feature',x),('maturity_us',maturity),('VIX_observation_date_us',obs),('VIX_available_proxy_us',available),('VIX_age_after_proxy_us',age)]:np.testing.assert_array_equal(z[name],current)
  owned=z['training_mask'];y=z['label'];bins=x>=model['threshold'];assert model['training_dates']==d[owned].tolist() and model['training_rows']==int(owned.sum()) and model['maximum_maturity_us']==int(maturity[owned].max())<model['fit_clock_us']
  assert model['threshold']==float(np.median(x[owned])) and model['constant']==float(y[owned].mean()) and model['means']==[float(y[owned&(bins==j)].mean()) for j in (0,1)]
  assert model['distinct_actual_VIX_observation_dates_used']==int(np.unique(obs[owned]).size)
 y,net,reason=prior.labels(d,raw,w,d>=utc('2022-01-01'));candidate,constant=predict(model,x)
 with np.load(state/'result/VALIDATION_VECTORS.npz',allow_pickle=False) as z:
  for name,current in [('decision_us',d),('feature',x),('maturity_us',maturity),('actual_advantage',y),('net_return',net),('candidate',candidate),('constant',constant),('VIX_observation_date_us',obs),('VIX_available_proxy_us',available),('VIX_age_after_proxy_us',age)]:np.testing.assert_array_equal(z[name],current)
 frame=pd.read_csv(state/'result/VALIDATION_DATES.csv');reports=[]
 for f in result['folds']:
  left,right=map(utc,f['calendar']);ids=np.flatnonzero((d>=left)&(d<right));support=np.isfinite(y[ids])&np.isfinite(candidate[ids])&(maturity[ids]<right);lc=(candidate[ids]-y[ids])**2;l0=(constant[ids]-y[ids])**2
  assert f['natural_calendar_dates']==len(ids) and f['actual_mature_common_labels']==int(support.sum());assert f['distinct_VIX_observation_dates_used']==int(np.unique(obs[ids][support]).size)
  assert f['candidate_MSE']==float(lc[support].mean()) and f['global_mean_MSE']==float(l0[support].mean()) and f['paired_14calendar_day_gain95CI']==paired_gain(l0-lc,support,seed=811732)
  saved=frame[frame.fold==f['name']];np.testing.assert_array_equal(saved.decision_us,d[ids]);np.testing.assert_array_equal(saved.support,support);np.testing.assert_array_equal(saved.VIX_observation_date_us,obs[ids]);np.testing.assert_array_equal(saved.VIX_available_proxy_us,available[ids]);np.testing.assert_array_equal(saved.VIX_age_after_proxy_us,age[ids]);assert not f['gates']['paired_14day_CI_lower_positive']
  reports.append(dict(name=f['name'],natural_dates=len(ids),actual_mature_labels=int(support.sum()),distinct_VIX_observation_dates=int(np.unique(obs[ids][support]).size),source_date_proxy_age_model_prediction_label_loss_CI='EXACT'))
 assert result['status']=='STOP_VIX_CONDITIONAL_INFORMATION_GATE' and result['new_native_wallets']==0
 report=dict(status='PASS_PUBLIC_VIX_ZERO_REFIT_RESTORE_LATEST_VINTAGE_CONDITIONAL',artifact_commit=artifact,cases=reports,latest_vintage_source_SHA256=source['raw_SHA256'],source_fetch_UTC=source['fetch_UTC'],historical_PIT_authority='NOT_CERTIFIED_LAG_DOES_NOT_REMOVE_EOD_REVISION_BIAS',new_fits=0,new_provider_GETs=0,account_advances=0,new_wallets=0,observed_STATE_open_attempts=len(blocked),seconds=time.monotonic()-began);save(state/'PUBLIC_RESTORE.json',report);print('ACTUAL_VIX_PUBLIC_ZERO_REFIT',report,flush=True)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--state',type=Path,required=True);p.add_argument('--artifact-commit',required=True);a=p.parse_args();restore(a.state,a.artifact_commit)
