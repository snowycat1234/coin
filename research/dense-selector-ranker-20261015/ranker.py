"""One frozen CASH-anchored ordinal pairwise logistic challenger; no wallet."""
import argparse,datetime as dt,json,math,os,platform,signal,time
from pathlib import Path
from collections import Counter
from itertools import combinations
import numpy as np
import scipy
from scipy.optimize import minimize
from scipy.special import expit
OPTIONS=dict(maxiter=500,maxls=40,ftol=1e-12,gtol=1e-8)
LAMBDA=1.0

def dump(path,obj):
 Path(path).write_text(json.dumps(obj,indent=2,allow_nan=False)+'\n')

def scaler_fit(x):
 x=np.asarray(x,dtype=np.float64);mean=x.mean(axis=0);sd=x.std(axis=0,ddof=0)
 return dict(mean=mean.tolist(),scale=np.where(sd==0,1,sd).tolist(),zero=(sd==0).tolist())

def transform(x,scaler):
 z=(np.asarray(x,dtype=np.float64)-scaler['mean'])/scaler['scale'];z[:,scaler['zero']]=0
 return np.column_stack([z,np.ones(len(z))])

def pair_design(x,y,eligible,cash):
 """Weight pairs by 1/(number of dates * that date's unequal pair count)."""
 x=np.asarray(x,float);y=np.asarray(y,float);eligible=np.asarray(eligible,bool)
 n,e=y.shape;noncash=[j for j in range(e) if j!=cash];eye=np.zeros((e,e-1));eye[noncash]=np.eye(e-1)
 design=[];weights=[];counts=[]
 for d in range(n):
  pairs=[(i,j) for i,j in combinations(range(e),2) if eligible[d,i] and eligible[d,j] and y[d,i]!=y[d,j]];counts.append(len(pairs))
  for i,j in pairs:
   sign=1. if y[d,i]>y[d,j] else -1.
   design.append((sign*(eye[i]-eye[j])[:,None]*x[d][None,:]).ravel());weights.append(1./n/len(pairs))
 return np.asarray(design,float).reshape((-1,(e-1)*x.shape[1])),np.asarray(weights,float),counts

def objective(theta,design,weights):
 margin=design@theta;data=float(weights@np.logaddexp(0.,-margin));penalty=.5*LAMBDA*float(theta@theta)
 gradient=design.T@(-weights*expit(-margin))+LAMBDA*theta
 return data+penalty,gradient

def optimize(design,weights):
 return minimize(objective,np.zeros(design.shape[1],dtype=np.float64),args=(design,weights),jac=True,method='L-BFGS-B',bounds=None,options=OPTIONS)

def predict(x,theta,cash,e):
 out=np.zeros((len(x),e),dtype=np.float64);out[:,[j for j in range(e) if j!=cash]]=x@np.asarray(theta).T
 return out

def clocks(row,cutoff=None):
 d=row['decision_us']
 if row['latest_target_available_us']>d or row['latest_state_feedback_available_us']>=d:raise ValueError('Unavailable target or nonpast feedback')
 if row['label_available_us']!=d+7*86400000000+120000001:raise ValueError('Label maturity differs')
 if cutoff is not None and row['label_available_us']>=cutoff:raise ValueError('Training label not strictly mature')

def validate(data):
 assert len(data['training'])==301 and len(data['feature_names'])==60 and len(data['experts'])==6
 assert len(data['evaluation'])==182 and sum(r['mature'] for r in data['evaluation'])==176
 assert len(data['preselected_dates'])==22 and len(set(data['preselected_dates']))==22
 previous=-1
 for r in data['training']:
  clocks(r,data['training_cutoff_us']);assert r['decision_us']>previous;previous=r['decision_us']
 original=json.loads((Path(__file__).parent/'original40_inputs.json').read_text())
 assert data['training_cutoff_us']==original['training_cutoff_us']
 assert data['simulated_fit_available_us']==original['simulated_fit_available_us']
 assert data['evaluation_label_availability_cutoff_us']==original['evaluation_label_availability_cutoff_us']
 for key in ['evaluation','preselected_dates','experts','feature_names']:assert data[key]==original[key]
 assert data['train_best']=='CASH_FIXED_ORIGINAL40_BASELINE_NOT_RESELECTED'
 assert data['original_40_training_mean_utility']==original['training_mean_utility']
 assert original['train_best']=='CASH'
 assert len(original['training'])==40
 dense={r['date']:r for r in data['training']};previous=-1
 assert len(dense)==301
 for r in original['training']:
  assert dense[r['date']]==r
  clocks(r,data['training_cutoff_us']);assert r['decision_us']>previous;previous=r['label_available_us']
 assert set(dense).isdisjoint(r['date'] for r in data['evaluation'])
 previous=-1;selected=[]
 for r in data['evaluation']:
  clocks(r);assert r['decision_us']>=data['simulated_fit_available_us']
  if r['mature']:
   assert r['label_available_us']<=data['evaluation_label_availability_cutoff_us']
   if r['decision_us']>previous:selected.append(r['date']);previous=r['label_available_us']
 assert selected==data['preselected_dates']
 for r in data['training']+data['evaluation']:
  assert len(r['x'])==60 and np.isfinite(r['x']).all() and len(r['eligible'])==6 and r['eligible'][data['experts'].index('CASH')]
  if 'utility' in r:assert r['utility'][data['experts'].index('CASH')]==0

def score(pred,y,mask,names):
 ids=[i for i,v in enumerate(mask) if v];chosen=[i for i in ids if pred[i]==max(pred[j] for j in ids)]
 actual=math.fsum(y[i] for i in chosen)/len(chosen);pairs=[(i,j) for i,j in combinations(ids,2) if y[i]!=y[j]]
 correct=math.fsum(.5 if pred[i]==pred[j] else float((pred[i]>pred[j])==(y[i]>y[j])) for i,j in pairs)
 return dict(chosen=[names[i] for i in chosen],chosen_utility=actual,oracle_regret=max(y[i] for i in ids)-actual,pairwise_correct_equivalent=correct,pairwise_comparisons=len(pairs),pairwise_accuracy=correct/len(pairs) if pairs else None,actual_ties_excluded=len(list(combinations(ids,2)))-len(pairs),forecast_ties_half_credit=int(sum(pred[i]==pred[j] for i,j in pairs)))

def summary(rows,key):
 vals=[r[key] for r in rows];n=len(vals);pairs=sum(v['pairwise_comparisons'] for v in vals);mix=Counter()
 for v in vals:
  for name in v['chosen']:mix[name]+=1/len(v['chosen'])
 acc=[v['pairwise_accuracy'] for v in vals if v['pairwise_accuracy'] is not None]
 return dict(mean_chosen_utility=math.fsum(v['chosen_utility'] for v in vals)/n,mean_oracle_regret=math.fsum(v['oracle_regret'] for v in vals)/n,pooled_pairwise_accuracy=math.fsum(v['pairwise_correct_equivalent'] for v in vals)/pairs if pairs else None,mean_date_pairwise_accuracy=math.fsum(acc)/len(acc) if acc else None,pairwise_comparisons=pairs,choice_mix=dict(mix),top_tied_dates=sum(len(v['chosen'])>1 for v in vals),positive_utility_dates=sum(v['chosen_utility']>0 for v in vals),negative_utility_dates=sum(v['chosen_utility']<0 for v in vals),zero_utility_dates=sum(v['chosen_utility']==0 for v in vals))

def paired_comparison(rows,a,b):
 delta=[r[a]['chosen_utility']-r[b]['chosen_utility'] for r in rows]
 return dict(dates=len(rows),mean_utility_difference=math.fsum(delta)/len(delta),a_better=int(sum(v>0 for v in delta)),b_better=int(sum(v<0 for v in delta)),equal=int(sum(v==0 for v in delta)),different_choices=int(sum(r[a]['chosen']!=r[b]['chosen'] for r in rows)))

def evaluate(data,coeff):
 validate(data);names=data['experts'];cash=names.index('CASH');rows=data['evaluation'];x=transform([r['x'] for r in rows],coeff['scaler']);pred=predict(x,coeff['theta'],cash,len(names));output=[]
 original_coeff=json.loads((Path(__file__).parent/'original40_coefficients.json').read_text())
 original_pred=predict(transform([r['x'] for r in rows],original_coeff['scaler']),original_coeff['theta'],cash,len(names))
 for r,p,op in zip(rows,pred,original_pred):
  out={k:r[k] for k in ['date','decision_us','label_available_us','eligible','mature','prediction_state']};out['prediction_challenger_ordinal']=p.tolist();out['prediction_original40_ordinal']=op.tolist();out['selected_block']=r['date'] in data['preselected_dates']
  if r['mature']:
   out['original40']=score(op,r['utility'],r['eligible'],names);out['utility']=r['utility'];out['challenger']=score(p,r['utility'],r['eligible'],names);out['state']=score(r['prediction_state'],r['utility'],r['eligible'],names)
   # CASH/train-best is a fixed selection, not an all-zero forecast argmax tie.
   cash_pred=np.full(len(names),-1.);cash_pred[cash]=0
   out['cash_train_best']=score(cash_pred,r['utility'],r['eligible'],names)
   # A fixed action has no pairwise forecast. Do not interpret the sentinel as scores.
   for k in ['pairwise_correct_equivalent','pairwise_accuracy']:out['cash_train_best'][k]=None
   out['cash_train_best']['pairwise_comparisons']=0
   out['oracle_utility']=max(v for v,m in zip(r['utility'],r['eligible']) if m)
   out['challenger_minus_state_utility']=out['challenger']['chosen_utility']-out['state']['chosen_utility'];out['challenger_minus_cash_utility']=out['challenger']['chosen_utility']
  output.append(out)
 blocks=[r for r in output if r['selected_block']];delta=[r['challenger_minus_state_utility'] for r in blocks]
 train=data['training'];xt=transform([r['x'] for r in train],coeff['scaler']);yp=predict(xt,coeff['theta'],cash,len(names));trainrows=[{'challenger':score(p,r['utility'],r['eligible'],names)} for p,r in zip(yp,train)]
 design,w,counts=pair_design(xt,[r['utility'] for r in train],[r['eligible'] for r in train],cash);theta=np.asarray(coeff['theta']).ravel();loss,g=objective(theta,design,w)
 return dict(role='REPEATEDLY_SEEN_DEV_ORDINAL_DIAGNOSTIC_NOT_PORTFOLIO_RETURN',actual_fit_started_utc=coeff['actual_fit_started_utc'],simulated_historical_fit_availability_us=data['simulated_fit_available_us'],blocks=blocks,all_182_scoring_rows=output,models={m:summary(blocks,m) for m in ['challenger','original40','state','cash_train_best']},all_mature_models={m:summary([r for r in output if r['mature']],m) for m in ['challenger','original40','state','cash_train_best']},dense_vs_original40={scope:paired_comparison(rs,'challenger','original40') for scope,rs in [('fixed22',blocks),('all176',[r for r in output if r['mature']])]},paired=dict(mean_challenger_minus_state_utility=math.fsum(delta)/len(delta),challenger_better_blocks=sum(v>0 for v in delta),state_better_blocks=sum(v<0 for v in delta),equal_blocks=sum(v==0 for v in delta),different_choices=sum(r['challenger']['chosen']!=r['state']['chosen'] for r in blocks)),oracle=dict(mean_unattainable_utility=math.fsum(r['oracle_utility'] for r in blocks)/len(blocks)),training=dict(unique_overlapping_dates=301,original_disjoint_support_dates=40,overlap_is_not_independence=True,pairs=sum(counts),unequal_pairs_by_date=counts,total_loss=loss,data_loss=float(w@np.logaddexp(0,-design@theta)),penalty=.5*float(theta@theta),gradient_inf_norm=float(np.max(np.abs(g))),fit=summary(trainrows,'challenger')),limitations=['305 free parameters, 301 overlapping training dates, and 40 original disjoint support dates; overlaps, six experts and pairs do not create independent evidence.','Ordinal scores are not utility forecasts; no MSE, old softmax, wallet or deployment use.','Lambda 1 and penalized intercepts differ from Ridge alpha 30, not an objective-only causal comparison.','Historical availability is simulated causal cutoff; this model was fitted in 2026, not issued in 2024.','Repeatedly seen development; no fresh OOS, significance, annualization or portfolio-return claim.'])

def fit_once(data,out):
 validate(data);out=Path(out);receipt=out/'FIT_RECEIPT.json'
 # An existing receipt blocks accidental actual-fit restarts, even following failure.
 with receipt.open('x') as f:json.dump(dict(status='STARTED',actual_fit_started_utc=dt.datetime.now(dt.timezone.utc).isoformat(),pid=os.getpid()),f)
 rec=json.loads(receipt.read_text());start=time.monotonic()
 def timeout(signum,frame):raise TimeoutError('120-second frozen stage cap reached')
 signal.signal(signal.SIGALRM,timeout);signal.alarm(120)
 try:
  if hasattr(os,'sched_getaffinity'):os.sched_setaffinity(0,{min(os.sched_getaffinity(0))})
  for k in ['OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS']:
   if os.environ.get(k)!='1':raise RuntimeError('Single-thread environment required before imports')
  from threadpoolctl import threadpool_info
  pools=threadpool_info();assert all(p['num_threads']==1 for p in pools)
  rec.update(versions=dict(python=platform.python_version(),numpy=np.__version__,scipy=scipy.__version__),options=OPTIONS,lambda_=1.0,cpu_affinity=sorted(os.sched_getaffinity(0)),threadpools=[{k:p[k] for k in ['internal_api','num_threads','version']} for p in pools],actual_fit_attempts=1,initialization='exactly_zero',free_parameters=305)
  train=data['training'];sc=scaler_fit([r['x'] for r in train]);x=transform([r['x'] for r in train],sc);design,w,counts=pair_design(x,[r['utility'] for r in train],[r['eligible'] for r in train],data['experts'].index('CASH'))
  opt=optimize(design,w);loss,g=objective(opt.x,design,w);accepted=bool(opt.success and np.isfinite(opt.x).all() and np.isfinite(loss) and np.max(np.abs(g))<=1e-6)
  rec.update(status='ACCEPTED' if accepted else 'NONCONVERGENCE',optimizer_success=bool(opt.success),optimizer_status=int(opt.status),message=str(opt.message),iterations=int(opt.nit),function_evaluations=int(opt.nfev),total_loss=loss,data_loss=float(w@np.logaddexp(0,-design@opt.x)),penalty=.5*float(opt.x@opt.x),gradient_inf_norm=float(np.max(np.abs(g))))
  dump(out/'optimizer_output.json',dict(theta=opt.x.reshape(5,61).tolist(),accepted=accepted))
  if accepted:
   coeff=dict(theta=opt.x.reshape(5,61).tolist(),scaler=sc,noncash_experts=[n for n in data['experts'] if n!='CASH'],feature_names=data['feature_names'],cash_score=0.0,actual_fit_started_utc=rec['actual_fit_started_utc']);dump(out/'coefficients.json',coeff);dump(out/'RESULTS.json',evaluate(data,coeff))
 except BaseException as exc:
  rec.update(status='FAILED',exception_type=type(exc).__name__,error=str(exc));raise
 finally:
  signal.alarm(0);rec.update(actual_stage_ended_utc=dt.datetime.now(dt.timezone.utc).isoformat(),elapsed_seconds=time.monotonic()-start);dump(receipt,rec)
 return rec

if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('operation',choices=['fit-once','reproduce']);ap.add_argument('--directory',default='.');a=ap.parse_args();p=Path(a.directory);data=json.loads((p/'derived_inputs.json').read_text())
 if a.operation=='fit-once':print(json.dumps(fit_once(data,p)))
 else:
  result=evaluate(data,json.loads((p/'coefficients.json').read_text()));expected=json.loads((p/'RESULTS.json').read_text());assert result==expected;print('Exact saved-coefficient reproduction passed; no refit.')
