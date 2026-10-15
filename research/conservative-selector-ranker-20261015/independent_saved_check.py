"""Independent saved-coefficient verification. No model fit or optimizer invocation."""
import ast, datetime as dt, hashlib, io, json, math, types, zipfile
from pathlib import Path
from itertools import combinations
from collections import Counter
import numpy as np
P=Path(__file__).resolve().parent
D=json.loads((P/'derived_inputs.json').read_text()); C=json.loads((P/'coefficients.json').read_text()); R=json.loads((P/'RESULTS.json').read_text())
T=D['training']; E=D['evaluation']; names=D['experts']; cash=names.index('CASH'); nc=[i for i in range(6) if i!=cash]
assert len(T)==40 and len(E)==182 and len(D['feature_names'])==60 and len(names)==6
x=np.array([r['x'] for r in T]); mu=x.mean(0); sd=x.std(0,ddof=0); zero=sd==0; scale=np.where(zero,1,sd)
np.testing.assert_array_equal(mu,C['scaler']['mean']); np.testing.assert_array_equal(scale,C['scaler']['scale']); np.testing.assert_array_equal(zero,C['scaler']['zero'])
assert C['feature_names']==D['feature_names'] and C['noncash_experts']==[names[i] for i in nc] and C['cash_score']==0
th=np.array(C['theta']); assert th.shape==(5,61) and np.isfinite(th).all()
def z(rows):
 a=(np.array([r['x'] for r in rows])-mu)/scale; a[:,zero]=0
 return np.column_stack([a,np.ones(len(a))])
xt=z(T); xe=z(E)
def pred(a,t):
 p=np.zeros((len(a),6));p[:,nc]=a@t.T;return p
pairs=[]
for d,r in enumerate(T):
 ps=[(i,j) for i,j in combinations(range(6),2) if r['eligible'][i] and r['eligible'][j] and r['utility'][i]!=r['utility'][j]]
 pairs.append([(i,j,1 if r['utility'][i]>r['utility'][j] else -1) for i,j in ps])
def loss(t,gradient=False):
 p=pred(xt,t); value=0.;g=t.copy()
 for d,ps in enumerate(pairs):
  for i,j,y in ps:
   margin=y*(p[d,i]-p[d,j]); value+=np.logaddexp(0.,-margin)/40/len(ps)
   if gradient:
    factor=-y/(1+np.exp(margin))/40/len(ps)
    if i!=cash:g[nc.index(i)]+=factor*xt[d]
    if j!=cash:g[nc.index(j)]-=factor*xt[d]
 penalty=.5*np.sum(t*t)
 return (value+penalty,g,value,penalty) if gradient else value+penalty
f,g,data,pen=loss(th,True)
step=1e-5; numerical=np.zeros_like(th)
for index in np.ndindex(th.shape):
 plus=th.copy();minus=th.copy();plus[index]+=step;minus[index]-=step;numerical[index]=(loss(plus)-loss(minus))/(2*step)
np.testing.assert_allclose(g,numerical,rtol=0,atol=2e-9)
for k,v in [('total_loss',f),('data_loss',data),('penalty',pen),('gradient_inf_norm',abs(g).max())]:assert abs(v-R['training'][k])<1e-14,(k,v,R['training'][k])
assert abs(g).max()<=1e-6
p=pred(xe,th);np.testing.assert_array_equal(p[:,cash],0)
np.testing.assert_array_equal(p,np.array([r['prediction_challenger_ordinal'] for r in R['all_182_scoring_rows']]))
def scores(p,r):
 ids=[i for i in range(6) if r['eligible'][i]]; best=max(p[i] for i in ids); chosen=[i for i in ids if p[i]==best];u=math.fsum(r['utility'][i] for i in chosen)/len(chosen)
 ps=[(i,j) for i,j in combinations(ids,2) if r['utility'][i]!=r['utility'][j]]
 cor=math.fsum(.5 if p[i]==p[j] else float((p[i]>p[j])==(r['utility'][i]>r['utility'][j])) for i,j in ps)
 return dict(chosen=[names[i] for i in chosen],chosen_utility=u,oracle_regret=max(r['utility'][i] for i in ids)-u,pairwise_correct_equivalent=cor,pairwise_comparisons=len(ps),pairwise_accuracy=cor/len(ps) if ps else None)
selected=[];prior=-1
for r in E:
 assert r['latest_target_available_us']<=r['decision_us'] and r['latest_state_feedback_available_us']<r['decision_us']
 assert r['label_available_us']==r['decision_us']+7*86400000000+120000001
 assert r['decision_us']>=D['simulated_fit_available_us']
 if r['mature']:
  assert r['label_available_us']<=D['evaluation_label_availability_cutoff_us']
  if r['decision_us']>prior:selected.append(r['date']);prior=r['label_available_us']
assert selected==D['preselected_dates'] and len(selected)==22
blocks=[]
for idx,r in enumerate(E):
 if not r['mature']:continue
 saved=R['all_182_scoring_rows'][idx]
 a=scores(p[idx],r);b=scores(r['prediction_state'],r)
 for model,actual in [('challenger',a),('state',b)]:
  for k,v in actual.items():assert saved[model][k]==v,(r['date'],model,k)
 assert saved['cash_train_best']['chosen']==['CASH'] and saved['cash_train_best']['chosen_utility']==0
 if r['date'] in selected:blocks.append((r['date'],a,b))
for key,ix in [('challenger',1),('state',2)]:
 mean=math.fsum(b[ix]['chosen_utility'] for b in blocks)/22;regret=math.fsum(b[ix]['oracle_regret'] for b in blocks)/22;pa=math.fsum(b[ix]['pairwise_correct_equivalent'] for b in blocks)/sum(b[ix]['pairwise_comparisons'] for b in blocks)
 assert mean==R['models'][key]['mean_chosen_utility'] and regret==R['models'][key]['mean_oracle_regret'] and pa==R['models'][key]['pooled_pairwise_accuracy']
assert math.fsum(b[1]['chosen_utility']-b[2]['chosen_utility'] for b in blocks)/22==R['paired']['mean_challenger_minus_state_utility']
for i,r in enumerate(T):
 assert r['label_available_us']<D['training_cutoff_us']
 assert r['latest_target_available_us']<=r['decision_us'] and r['latest_state_feedback_available_us']<r['decision_us']
 if i:assert r['decision_us']>T[i-1]['label_available_us']
assert names[int(np.argmax(np.mean([r['utility'] for r in T],axis=0)))]=='CASH'

print("Independent saved-coefficient checks passed: no fit or optimizer invoked.")
print("Finite-difference max error:", float(abs(g-numerical).max()))
