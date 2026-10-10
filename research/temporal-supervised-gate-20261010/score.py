from pathlib import Path
import json,numpy as np,torch
from modules.temporal_supervised_gate import data,initialize,SLOTS
from modules.temporal_balanced_history.inputs import training,from_arrays
from modules.temporal_expert_input.gradient import predict_episode
from modules.temporal_two_expert.checkpoint import model_identity
from modules.temporal_two_expert.exact import sha
from modules.temporal_two_expert.inputs import digest
S=Path('../coin_single_state');D=S/'supervised-gate';R=S/'data-expansion';torch.set_num_threads(1)
pub=json.loads((D/'FROZEN.json').read_text());t=json.loads((D/'TERMINAL.json').read_text());assert pub['model_identity']==t['model_identity'] and pub['checkpoint_SHA256']==sha(D/t['checkpoint']['path'])
a,y,w,scaler,receipt=data(S);m,_=initialize(scaler);x=torch.load(D/t['checkpoint']['path'],weights_only=True);m.load_state_dict(x['model']);m.eval();assert model_identity(m)==t['model_identity'];before=model_identity(m)
with torch.no_grad():
 q=np.concatenate([m(*[torch.tensor(v[i:i+32].copy()) for v in a]).numpy()[:,SLOTS] for i in range(0,len(y),32)])
trainprior=np.bincount(y,minlength=4)/len(y);labels=json.loads((S/'balanced-history/LABELS.json').read_text());meanutility=np.asarray([r['hindsight_fixed_policy_21day_utility'] for r in labels]).mean(0)
_,p,_,_=training(S)
expected={'features2025/FEATURES.npz':'81550b0443d2c725cdce7950ecc46e676dd12d5aa76185f4bd8d97e4e003ef06','features2025/EXPERTS.npz':'e6c783bb0b6927218afa426c6535485e3336955ecfdcbd17fefba22432b6cf4e','economics2025/ECONOMICS.npz':'0ad850e9ca4549fe1442aeceaa3de5d3abbfb8c0c1e7a3d4c0f812d0ffb8fb4d'}
for n,h in expected.items():assert sha(R/n)==h
f=np.load(R/'features2025/FEATURES.npz');e0=np.load(R/'features2025/EXPERTS.npz');b=np.load(R/'economics2025/ECONOMICS.npz');d=b['decision_us'];e=from_arrays('SEEN_2025_FORWARD',d,b['prices'],b['funding_coeff'],e0['expert_targets'],e0['expert_eligible'],e0['past_returns30'],f,p,digest(expected),role='SEEN_VALIDATION')
with torch.no_grad():q25=predict_episode(m,e,feature_batch_size=32).numpy()[:,SLOTS]
u=np.zeros((365,4))
for j,name in enumerate(['VOL','CS','SHORT'],1):
 z=np.load(R/'controls2025'/f'{name}_PATH.npz');nav=z['nav'];rr=nav[1:]/nav[:-1]-1;assert len(rr)==365;u[:,j]=np.log1p(rr)-5*np.minimum(rr,0)**2
future=np.stack([u[i:i+21].sum(0) for i in range(344)]);y25=future.argmax(1)
def correct(q):
 z=q/w;return z/z.sum(1,keepdims=True)
def metrics(prob,truth,utility):
 pred=prob.argmax(1);conf=np.zeros((4,4),int);np.add.at(conf,(truth,pred),1)
 return {'rows':len(truth),'logloss':float(-np.log(prob[np.arange(len(truth)),truth].clip(1e-12)).mean()),'Brier':float(((prob-np.eye(4)[truth])**2).sum(1).mean()),'accuracy':float((pred==truth).mean()),'SHORT_recall':float((pred[truth==3]==3).mean()) if (truth==3).any() else None,'predicted_counts':np.bincount(pred,minlength=4).tolist(),'true_counts':np.bincount(truth,minlength=4).tolist(),'confusion_true_rows_pred_columns':conf.tolist(),'mean_probability':prob.mean(0).tolist(),'mean_opportunity_regret':float((utility.max(1)-utility[np.arange(len(truth)),pred]).mean())}
res={'status':'CLASSIFICATION_ONLY_NO_NEW_WALLETS','model':before,'training':metrics(correct(q),y,np.asarray([r['hindsight_fixed_policy_21day_utility'] for r in labels])),'2025':{},'train_mean_utility':meanutility.tolist(),'train_prior':trainprior.tolist(),'seen_development':True}
for name,ix in [('overlap',np.arange(344)),('disjoint21',np.arange(0,344,21))]:
 pr=correct(q25[:344]);constant=np.tile(trainprior,(344,1));res['2025'][name]={'model':metrics(pr[ix],y25[ix],future[ix]),'train_prior':metrics(constant[ix],y25[ix],future[ix]),'train_mean_utility_action':int(meanutility.argmax()),'train_mean_utility_regret':float((future[ix].max(1)-future[ix,int(meanutility.argmax())]).mean())}
assert before==model_identity(m);(D/'SCORES.json').write_text(json.dumps(res,indent=2));np.savez_compressed(D/'PREDICTIONS.npz',decision_us=d[:344],q_balanced=q25[:344],p_corrected=correct(q25[:344]),utility=future,y=y25);print(json.dumps(res,indent=2))
