"""Verify saved predictions and metrics without fitting any model."""
import json,math
from pathlib import Path
import numpy as np
P=Path(__file__).parent
def read(n):return json.loads((P/n).read_text())
d=read('derived_inputs.json');r=read('RESULTS.json');c=read('coefficients.json');oc=read('original40_coefficients.json');old=read('original40_inputs.json')
x=np.asarray([v['x'] for v in d['training']]);mean=x.mean(0);sd=x.std(0)
np.testing.assert_allclose(mean,c['scaler']['mean'],rtol=1e-12,atol=1e-14);np.testing.assert_allclose(np.where(sd==0,1,sd),c['scaler']['scale'],rtol=1e-12,atol=1e-14);np.testing.assert_array_equal(sd==0,c['scaler']['zero'])
assert len(d['training'])==301 and len({v['date'] for v in d['training']})==301
for coeff,key in [(c,'prediction_challenger_ordinal'),(oc,'prediction_original40_ordinal')]:
 ex=np.asarray([v['x'] for v in d['evaluation']]);z=(ex-coeff['scaler']['mean'])/coeff['scaler']['scale'];z[:,coeff['scaler']['zero']]=0
 pred=np.zeros((182,6));pred[:,1:]=np.column_stack((z,np.ones(182)))@np.asarray(coeff['theta']).T
 np.testing.assert_allclose(pred,[v[key] for v in r['all_182_scoring_rows']],rtol=1e-12,atol=1e-14)
 for row,p in zip(r['all_182_scoring_rows'],pred):
  if not row['mature']:continue
  model='challenger' if coeff is c else 'original40';active=[j for j in range(6) if row['eligible'][j]];chosen=[j for j in active if p[j]==max(p[k] for k in active)];utility=math.fsum(row['utility'][j] for j in chosen)/len(chosen)
  assert utility==row[model]['chosen_utility'];assert [d['experts'][j] for j in chosen]==row[model]['chosen']
for scope,rows in [('fixed22',r['blocks']),('all176',[v for v in r['all_182_scoring_rows'] if v['mature']])]:
 ds=[v['challenger']['chosen_utility']-v['original40']['chosen_utility'] for v in rows]
 assert math.fsum(ds)/len(ds)==r['dense_vs_original40'][scope]['mean_utility_difference']
 assert len(rows)==(22 if scope=='fixed22' else 176)
assert d['evaluation']==old['evaluation']
assert all(row['cash_train_best']['chosen']==['CASH'] for row in r['all_182_scoring_rows'] if row['mature'])
receipt=read('FIT_RECEIPT.json');assert receipt['status']=='ACCEPTED' and receipt['actual_fit_attempts']==1
assert receipt['gradient_inf_norm']<=1e-6 and receipt['elapsed_seconds']<=120
assert all(p['num_threads']==1 for p in receipt['threadpools']) and len(receipt['cpu_affinity'])==1
# Direct objective/gradient arithmetic, with no runner import or optimizer.
theta=np.asarray(c['theta']);grad=theta.copy();data_loss=0.;pair_count=0
z=(x-c['scaler']['mean'])/c['scaler']['scale'];z[:,c['scaler']['zero']]=0
for row,features in zip(d['training'],np.column_stack((z,np.ones(len(z))))):
 utility=row['utility'];active=[j for j in range(6) if row['eligible'][j]]
 pairs=[(i,j) for n,i in enumerate(active) for j in active[n+1:] if utility[i]!=utility[j]]
 scores=np.concatenate(([0.],theta@features));pair_count+=len(pairs)
 for i,j in pairs:
  sign=1. if utility[i]>utility[j] else -1.;margin=sign*(scores[i]-scores[j]);weight=1./301/len(pairs)
  data_loss+=weight*float(np.logaddexp(0.,-margin));derivative=-weight*sign*float(np.exp(-np.logaddexp(0.,margin)))
  if i:grad[i-1]+=derivative*features
  if j:grad[j-1]-=derivative*features
loss=data_loss+.5*float(np.sum(theta*theta));gradient_norm=float(np.max(np.abs(grad)))
np.testing.assert_allclose([loss,data_loss,gradient_norm],[receipt['total_loss'],receipt['data_loss'],receipt['gradient_inf_norm']],rtol=1e-10,atol=1e-14)
assert gradient_norm<=1e-6 and pair_count==r['training']['pairs']
print('PASS: direct objective/gradient, saved predictions, train-only scaler, independent decision arithmetic, 22/176 paired metrics, unchanged evaluation and fixed CASH; zero refits.')
