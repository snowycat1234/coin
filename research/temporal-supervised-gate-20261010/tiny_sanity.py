"""Training-only 32-window memorization control, never a deployable strategy."""
from pathlib import Path
import json,time,numpy as np,torch
from modules.temporal_supervised_gate import data,initialize,SLOTS
S=Path('../coin_single_state');D=S/'supervised-gate';torch.set_num_threads(1);torch.use_deterministic_algorithms(True);a,y,w,sc,_=data(S)
# Eight evenly spaced observations per class; entirely pre-May 2024.
ix=np.concatenate([np.flatnonzero(y==c)[np.linspace(0,(y==c).sum()-1,8,dtype=int)] for c in range(4)])
t=[torch.tensor(v[ix].copy(),dtype=torch.float64 if j in [0,3] else torch.bool) for j,v in enumerate(a)];yy=torch.tensor(y[ix]);m,opt=initialize(sc);m.eval() # Disable dropout only for memorization sanity, gradients remain enabled.
plan={'scope':'training-only engineering sanity, not a selector candidate','rows':32,'counts':[8]*4,'updates':200,'lr':.001,'dropout':'disabled for memorization','selection':'8 evenly spaced within each training class','2025_reads':0,'indices':ix.tolist()};(D/'TINY_PLAN.json').write_text(json.dumps(plan,indent=2));hist=[];start=time.monotonic()
for step in range(201):
 q=m(*t)[:,SLOTS];loss=-q[torch.arange(32),yy].clamp_min(1e-12).log().mean()
 if step%20==0:hist.append({'step':step,'cross_entropy':float(loss.detach()),'accuracy':float((q.argmax(1)==yy).double().mean())})
 if step==200:break
 opt.zero_grad(set_to_none=True);loss.backward();torch.nn.utils.clip_grad_norm_(m.parameters(),1.,error_if_nonfinite=True);opt.step()
r={'plan':plan,'history':hist,'elapsed':time.monotonic()-start,'final_confusion':[[int(((yy==i)&(q.argmax(1)==j)).sum()) for j in range(4)] for i in range(4)],'interpretation':'Sanity control only; no out-of-sample or economic evidence'};(D/'TINY_RESULT.json').write_text(json.dumps(r,indent=2));print(json.dumps(r,indent=2))
