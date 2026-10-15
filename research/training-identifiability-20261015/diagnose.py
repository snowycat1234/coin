"""Read-only frozen training geometry. No optimizer, holdout or noise simulation."""
import json
from pathlib import Path
import numpy as np

def diagnose(f):
 rows=f['training']; names=f['feature_names']; experts=f['experts']; c=f['coefficients']; sc=c['scaler']
 x=np.asarray([r['x'] for r in rows],float); y=np.asarray([r['utility'] for r in rows],float)
 z=(x-np.asarray(sc['mean']))/np.asarray(sc['scale']); z[:,np.asarray(sc['zero'],bool)]=0
 const=np.ptp(x,axis=0)==0
 u,s,vt=np.linalg.svd(z,full_matrices=False);tol=max(z.shape)*np.finfo(float).eps*s[0];rank=int(sum(s>tol))
 zc=z-z.mean(0);uc,cs,_=np.linalg.svd(zc,full_matrices=False);ctol=max(zc.shape)*np.finfo(float).eps*cs[0];cr=int(sum(cs>ctol));lev=(uc[:,:cr]**2).sum(1)
 active=np.flatnonzero(~const); corr=np.corrcoef(z[:,active],rowvar=False)
 pairs=[{'a':names[active[a]],'b':names[active[b]],'r':float(corr[a,b])} for a in range(len(active)) for b in range(a+1,len(active)) if abs(corr[a,b])>=.95]
 theta=np.zeros((len(experts),z.shape[1]+1));cash=experts.index('CASH')
 for k,n in enumerate(c['noncash_experts']):theta[experts.index(n)]=c['theta'][k]
 pred=np.column_stack([z,np.ones(len(z))])@theta.T
 out=[]
 for i,r in enumerate(rows):
  ids=np.flatnonzero(r['eligible']); order=sorted(ids,key=lambda j:(-pred[i,j],j)); a,b=order[:2]; top=[int(j) for j in ids if pred[i,j]==pred[i,a]]
  margin=float(pred[i,a]-pred[i,b]); delta=theta[a,:-1]-theta[b,:-1]; delta[const]=0; norm=float(np.linalg.norm(delta));distance=margin/norm if norm else (0. if margin==0 else None)
  chosen=float(y[i,top].mean()); oracle=float(y[i,ids].max()); positive=max(0.,oracle-y[i,cash]); captured=max(0.,chosen-y[i,cash]);missed=max(0.,positive-captured)
  out.append({'date':r['date'],'centered_row_leverage':float(lev[i]),'top_choices':[experts[j] for j in top],'runner_up':experts[b],'top_score':float(pred[i,a]),'runner_up_score':float(pred[i,b]),'top_runner_margin':margin,'top_runner_standardized_l2_boundary_distance':distance,'chosen_utility_tie_average':chosen,'cash_utility':float(y[i,cash]),'best_eligible_utility':oracle,'oracle_regret':oracle-chosen,'positive_opportunity_above_cash':positive,'uncaptured_positive_utility_above_cash':missed,'chosen_shortfall_below_cash':max(0.,float(y[i,cash])-chosen)})
 energy=s*s;cum=np.cumsum(energy)/energy.sum();m=np.array([r['top_runner_margin'] for r in out]);ds=np.array([r['top_runner_standardized_l2_boundary_distance'] for r in out if r['top_runner_standardized_l2_boundary_distance'] is not None])
 return {'scope':'Frozen 40-row training baseline only; no model fitting, feature selection, evaluation data or stochastic perturbations.','shape':list(z.shape),'constant_columns':[names[j] for j in np.flatnonzero(const)],'numerical_rank':rank,'rank_tolerance':float(tol),'singular_values':s.tolist(),'effective_participation_rank':float(energy.sum()**2/(energy**2).sum()),'components_for_variance':{str(t):int(np.searchsorted(cum,t)+1) for t in [.5,.8,.95]},'nonzero_singular_condition_number':float(s[0]/s[rank-1]),'centered_rank':cr,'feature_correlation_pairs_abs_ge_095':pairs,'correlation_pair_count':len(pairs),'summary':{'top_tie_dates':sum(len(r['top_choices'])>1 for r in out),'cash_in_top_choices_dates':sum('CASH' in r['top_choices'] for r in out),'positive_opportunity_dates':sum(r['positive_opportunity_above_cash']>0 for r in out),'missed_positive_opportunity_dates':sum(r['uncaptured_positive_utility_above_cash']>0 for r in out),'selected_below_cash_dates':sum(r['chosen_shortfall_below_cash']>0 for r in out),'mean_selected_utility':float(np.mean([r['chosen_utility_tie_average'] for r in out])),'mean_best_eligible_utility':float(np.mean([r['best_eligible_utility'] for r in out])),'mean_uncaptured_positive_utility_above_cash':float(np.mean([r['uncaptured_positive_utility_above_cash'] for r in out])),'margin_min_median_max':np.quantile(m,[0,.5,1]).tolist(),'boundary_distance_min_median_max':np.quantile(ds,[0,.5,1]).tolist(),'leverage_min_median_max':np.quantile(lev,[0,.5,1]).tolist()},'dates':out,'geometry_caveat':'Boundary distance = score margin / norm of frozen top-minus-runner weights, with intercept and constant coordinates fixed. This is unrestricted standardized feature geometry, not a feasible market perturbation or a probability; other rivals can have closer boundaries. Exact score equality is a tie; all tied choices receive equal-weight utility.'}

if __name__=='__main__':
 p=Path(__file__).parent;f=json.loads((p/'training_fixture.json').read_text());result=diagnose(f);(p/'results.json').write_text(json.dumps(result,indent=2,allow_nan=False,default=lambda v:v.item())+'\n'); print(json.dumps({k:result[k] for k in ['shape','numerical_rank','effective_participation_rank','components_for_variance','nonzero_singular_condition_number','correlation_pair_count','summary']},indent=2,default=lambda v:v.item()))
