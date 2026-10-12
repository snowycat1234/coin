"""Strictly chronological one-scalar diagnostic with existing paid labels."""
import argparse,hashlib,importlib.util,json,subprocess,time
from pathlib import Path
import numpy as np
import pandas as pd
from core import DAY,SYMBOLS,persistence,fit,predict,paired_gain
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def git(*args):return subprocess.check_output(['git',*args],cwd=ROOT)
def save(p,x):Path(p).write_text(json.dumps(x,sort_keys=True,indent=2,allow_nan=False)+'\n')
def utc(s):return int(pd.Timestamp(s,tz='UTC').value//1000)
def verify():
 for line in (HERE/'SOURCE_SHA256.txt').read_text().splitlines():h,p=line.split(maxsplit=1);assert sha(ROOT/p)==h,p
def inputs():
 P=json.loads((HERE/'PROTOCOL.json').read_text());r=P['source'];path=ROOT/r['cube_path'];assert sha(path)==r['cube_SHA256'];target=ROOT/r['target_path'];assert sha(target)==r['target_SHA256']
 with np.load(path,allow_pickle=False) as z:
  # Only names used below are decompressed. No teacher/policy/utility is read.
  d=z['decision_us'];t=z['close_available_us'];p=z['close'];idx=np.flatnonzero((d>=utc('2021-04-01'))&(d<utc('2024-01-01')));d=d[idx]
  raw={k:z[k][idx] for k in ('p0','p1','funding_per_unit','owned_interval_valid','label_complete','true_reward_maturity_us')}
 with np.load(target,allow_pickle=False) as z:
  assert tuple(z['symbol_order'])==SYMBOLS;ids=np.searchsorted(z['decision_us'],d);np.testing.assert_array_equal(z['decision_us'][ids],d);base={k:z[k][ids] for k in ('CS_MATCHED','VOL_MATCHED')}
 base['STATIC50']=.5*base['CS_MATCHED']+.5*base['VOL_MATCHED']
 spec=importlib.util.spec_from_file_location('unchanged_past30_risk_budget',ROOT/'research/portfolio-risk-budget-20261012/risk_budget.py');risk=importlib.util.module_from_spec(spec);spec.loader.exec_module(risk);w,_,_=risk.allocate(t,p,d,base)
 for key in ('P1','P2'):
  path=ROOT/'research/portfolio-risk-budget-20261012/input'/(key+'.npz');assert sha(path)==r[key+'_fixed10_SHA256']
  with np.load(path,allow_pickle=False) as z:
   ids=np.searchsorted(d,z['decision_us']);np.testing.assert_array_equal(d[ids],z['decision_us'])
   for a in ('CS_MATCHED','VOL_MATCHED'):np.testing.assert_array_equal(w[a][ids],z[a])
 w={k:w[k] for k in ('CS_MATCHED','VOL_MATCHED')}
 keep=t<=utc('2024-01-01');t=t[keep];p=p[keep];x=persistence(t,p,d)
 # Genuine future-prefix check uses prices after the fit cutoff only.
 alt=p.copy();alt[t>utc('2022-01-01')]*=np.linspace(2,6,5);ax=persistence(t,alt,d);np.testing.assert_array_equal(x[d<=utc('2022-01-01')],ax[d<=utc('2022-01-01')])
 return d,x,raw,w
def labels(d,raw,w,selected):
 spec=importlib.util.spec_from_file_location('unchanged_paid_quantity_reference',ROOT/'research/cs-continuous-economics-20261012/core.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
 y=np.full(len(d),np.nan);net=np.full((len(d),2),np.nan);reasons=np.full(len(d),'NOT_REQUESTED',dtype='U64')
 for i in np.flatnonzero(selected):
  complete=bool(raw['label_complete'][i]);good=raw['owned_interval_valid'][i];required=np.any(np.stack([v[i]!=0 for v in w.values()]),axis=0)
  valid=good&np.isfinite(raw['p0'][i])&np.isfinite(raw['p1'][i])&np.isfinite(raw['funding_per_unit'][i])&(raw['p0'][i]>0)&(raw['p1'][i]>0)
  if not complete or np.any(required&~valid):reasons[i]='MISSING_REAL_OWNED_PRICE_MARK_OR_FUNDING';continue
  for j,a in enumerate(('CS_MATCHED','VOL_MATCHED')):
   report,rows=m.quantity_reference(d[i:i+1],w[a][i:i+1],raw['p0'][i:i+1],raw['p1'][i:i+1],raw['funding_per_unit'][i:i+1],good[None,:],np.array([complete]))
   if report['paid_terminal']:net[i,j]=report['net_USDT']/10000
  if np.isfinite(net[i]).all():y[i]=net[i,0]-net[i,1];reasons[i]='COMPLETE_PAID_CONDITIONAL_ONE_DAY_REFERENCE'
  else:reasons[i]='REFERENCE_STOP_PRESERVED'
 return y,net,reasons
def train(state,science):
 assert not state.exists() and not git('status','--porcelain') and git('rev-parse','HEAD').decode().strip()==science;verify();state.mkdir(parents=True);began=time.monotonic()
 d,x,raw,w=inputs();mature=raw['true_reward_maturity_us'];cut=utc('2022-01-01');training=(d<cut)&(mature<cut)
 y,net,reason=labels(d,raw,w,training);model,owned=fit(d,x,y,mature,cut,utc('2021-04-01'));save(state/'MODEL.json',model)
 pd.DataFrame(dict(decision_us=d,feature=x,label_maturity_us=mature,training_requested=training,training_fit=owned,training_label=y,reason=reason)).to_csv(state/'TRAINING_DATES.csv',index=False)
 np.savez_compressed(state/'TRAIN_VECTORS.npz',decision_us=d,feature=x,maturity_us=mature,training_label=y,training_net=net,training_mask=owned)
 report=dict(status='FROZEN_TRAINING_MODEL_NO_INTERNAL_VALIDATION_SCORES',source_commit=science,training_rows=model['training_rows'],mature_training_bin_rows=model['counts'],feature_threshold_training_median=model['threshold'],conditional_means=model['means'],constant=model['constant'],true_max_label_maturity_us=model['maximum_maturity_us'],fit_clock_us=cut,candidate_conditional_mean_fits=1,analytic_constant_fits=1,new_wallets=0,new_providers=0,hyperparameter_scans=0,source_cube_SHA256=sha(ROOT/json.loads((HERE/'PROTOCOL.json').read_text())['source']['cube_path']),MODEL_SHA256=sha(state/'MODEL.json'),seconds=time.monotonic()-began)
 save(state/'TRAINING_RESULT.json',report);print('ACTUAL_ONE_SCALAR_FIT_COMPLETE',report,flush=True)
def score(state,science):
 assert not state.exists() and not git('status','--porcelain') and git('rev-parse','HEAD').decode().strip()==science;verify();state.mkdir(parents=True);began=time.monotonic()
 model=json.loads((HERE/'model/MODEL.json').read_text());assert model['fit_clock_us']==utc('2022-01-01') and model['maximum_maturity_us']<model['fit_clock_us']
 d,x,raw,w=inputs();selected=d>=utc('2022-01-01');y,net,reason=labels(d,raw,w,selected);candidate,constant=predict(model,x);maturity=raw['true_reward_maturity_us'];P=json.loads((HERE/'PROTOCOL.json').read_text());folds=[];traces=[]
 for fold in P['internal_validation_folds']:
  left,right=map(utc,fold['calendar']);ids=np.flatnonzero((d>=left)&(d<right));fd=d[ids];fx=x[ids];fy=y[ids];fc=candidate[ids];f0=constant[ids];fm=maturity[ids];support=np.isfinite(fy)&np.isfinite(fc)&(fm<right)
  loss_c=(fc-fy)**2;loss_0=(f0-fy)**2;gain=loss_0-loss_c;ci=paired_gain(gain,support) if support.sum()>=90 else None
  corr=float(np.corrcoef(fc[support],fy[support])[0,1]) if support.any() and np.std(fc[support])>0 and np.std(fy[support])>0 else 0.
  gates=dict(common_mature_dates_at_least90=bool(support.sum()>=90),MSE_beats_global_training_mean=bool(support.any() and np.mean(loss_c[support])<np.mean(loss_0[support])),paired_14day_CI_lower_positive=bool(ci is not None and ci[0]>0),positive_frozen_forecast_correlation=bool(corr>0))
  f=dict(name=fold['name'],calendar=fold['calendar'],natural_dates=len(fd),common_mature_dates=int(support.sum()),unavailable_or_purged_dates=[int(v) for v in fd[~support]],candidate_MSE=float(np.mean(loss_c[support])) if support.any() else None,constant_MSE=float(np.mean(loss_0[support])) if support.any() else None,relative_MSE_gain=float(1-np.mean(loss_c[support])/np.mean(loss_0[support])) if support.any() else None,paired_calendar_block14_gain95CI=ci,forecast_advantage_correlation=corr,gates=gates,validation_bin_counts=[int((support&((fx>=model['threshold'])==j)).sum()) for j in (0,1)],actual_advantage_by_bin=[float(np.mean(fy[support&((fx>=model['threshold'])==j)])) if np.any(support&((fx>=model['threshold'])==j)) else None for j in (0,1)])
  folds.append(f);traces.append(pd.DataFrame(dict(fold=fold['name'],decision_us=fd,feature=fx,maturity_us=fm,support=support,actual_advantage=fy,predicted_advantage=fc,constant_advantage=f0,candidate_loss=loss_c,constant_loss=loss_0,reason=reason[ids])));print('ACTUAL_FROZEN_FOLD',f,flush=True)
 report=dict(status='PASS_ONE_SCALAR_INTERNAL_INFORMATION_GATE' if all(all(f['gates'].values()) for f in folds) else 'STOP_RANK_PERSISTENCE_INFORMATION_GATE',science_source_commit=science,frozen_model_SHA256=sha(HERE/'model/MODEL.json'),same_model_all_folds=True,folds=folds,scientific_attempts=1,total_candidate_historical_fits=1,total_analytic_constant_fits=1,new_fits_at_validation=0,new_native_wallets=0,new_providers=0,seconds=time.monotonic()-began,scope='PAID_ONE_DAY_OPPORTUNITY_PREDICTION_ALREADYSEEN_INTERNAL_NOT_CONTINUOUS_INCOME')
 pd.concat(traces,ignore_index=True).to_csv(state/'VALIDATION_DATES.csv',index=False);np.savez_compressed(state/'VALIDATION_VECTORS.npz',decision_us=d,feature=x,maturity_us=maturity,actual_advantage=y,net_return=net,candidate=candidate,constant=constant)
 save(state/'RESULT.json',report);print('ACTUAL_ONE_SCALAR_INTERNAL_RESULT',report['status'],flush=True)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('phase',choices=['train','score']);p.add_argument('--state',type=Path,required=True);p.add_argument('--source-commit',required=True);a=p.parse_args();(train if a.phase=='train' else score)(a.state,a.source_commit)
