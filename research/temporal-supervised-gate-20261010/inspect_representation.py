from pathlib import Path
import numpy as np,torch,json
from modules.temporal_supervised_gate import data,initialize,SLOTS
S=Path('../coin_single_state');D=S/'supervised-gate';torch.set_num_threads(1);a,y,w,s,_=data(S);m,_=initialize(s);t=json.loads((D/'TERMINAL.json').read_text());x=torch.load(D/t['checkpoint']['path'],weights_only=True);m.load_state_dict(x['model']);m.eval();joint=[];hook=m.base.w_head.register_forward_pre_hook(lambda mod,args:joint.append(args[0].detach().numpy().copy()))
with torch.no_grad():q=np.concatenate([m(*[torch.tensor(v[i:i+32].copy(),dtype=torch.float64 if j in [0,3] else torch.bool) for j,v in enumerate(a)]).numpy()[:,SLOTS] for i in range(0,len(y),32)])
hook.remove();z=np.concatenate(joint);sv=np.linalg.svd(z-z.mean(0),compute_uv=False);pred=q.argmax(1);cm=np.zeros((4,4),int);np.add.at(cm,(y,pred),1)
r={'scope':'training only, frozen terminal, no fitting','raw_balanced_prediction_counts':np.bincount(pred,minlength=4).tolist(),'raw_balanced_confusion':cm.tolist(),'raw_balanced_SHORT_recall':float((pred[y==3]==3).mean()),'raw_balanced_mean_prob_by_true_class':[q[y==i].mean(0).tolist() for i in range(4)],'joint_abs_gt_099_fraction':float((abs(z)>.99).mean()),'joint_feature_std':z.std(0).tolist(),'joint_singular_values':sv.tolist(),'head_weights':{n:{'L2':float(p.norm()),'min':float(p.min()),'max':float(p.max())} for n,p in m.named_parameters() if 'head' in n},'raw_training_weighted_CE':float((-np.log(q[np.arange(len(y)),y])*w[y]).mean())}
(D/'REPRESENTATION.json').write_text(json.dumps(r,indent=2));print(json.dumps(r,indent=2))
