"""One predeclared continuation, exact optimizer/RNG, no forward evaluation IO."""
from pathlib import Path
import json,time,fcntl,numpy as np,torch
from modules.temporal_supervised_gate import data,initialize,SLOTS,sources
from modules.temporal_balanced_history.train import save
from modules.temporal_short_expansion.checkpoint import _validate_model_state,_validate_saved_optimizer,_validate_rng
from modules.temporal_two_expert.checkpoint import _restore_rng,model_identity,_atomic_json
from modules.temporal_two_expert.exact import sha
S=Path('../coin_single_state');D=S/'supervised-gate';O=D/'continue100';O.mkdir(exist_ok=True);torch.set_num_threads(1);torch.use_deterministic_algorithms(True)
lock=(O/'run.lock').open('a+');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
if (O/'TERMINAL.json').exists():print('ALREADY_COMPLETE');raise SystemExit
pub=json.loads((D/'CONTINUATION_PUBLIC.json').read_text());assert pub['plan_SHA256']==sha(D/'CONTINUATION_PLAN.json') and pub['source_SHA256']==sha(Path(__file__))
a,y,w,sc,receipt=data(S);m,opt=initialize(sc)
if (O/'latest.json').exists():ptr=json.loads((O/'latest.json').read_text());folder=O
else:ptr=json.loads((D/'TERMINAL.json').read_text())['checkpoint'];folder=D
assert sha(folder/ptr['path'])==ptr['SHA256'];x=torch.load(folder/ptr['path'],weights_only=True);assert x['binding']['sources']==sources() and x['binding']['data']==receipt
_validate_model_state(m,x['model'],x['model_identity']);_validate_saved_optimizer(m,opt,x['optimizer'],x['step'],{n:0 for n,_ in m.named_parameters()});_validate_rng(x['rng']);m.load_state_dict(x['model']);opt.load_state_dict(x['optimizer']);_restore_rng(x['rng']);m.train();h=x['history'];step=x['step'];start=time.monotonic();prior=x['elapsed'];cw=torch.tensor(w,dtype=m.mean.dtype)
while h['epoch']<100:
 if not h['permutation']:h['permutation']=np.random.permutation(len(y)).tolist()
 ix=np.asarray(h['permutation'][h['offset']:h['offset']+64]);ts=[torch.tensor(v[ix].copy(),dtype=torch.float64 if j in [0,3] else torch.bool) for j,v in enumerate(a)];yy=torch.tensor(y[ix]);opt.zero_grad(set_to_none=True);q=m(*ts)[:,SLOTS];loss=-(q[torch.arange(len(ix)),yy].clamp_min(1e-12).log()*cw[yy]).mean();assert torch.isfinite(loss);loss.backward();torch.nn.utils.clip_grad_norm_(m.parameters(),1.,error_if_nonfinite=True);opt.step();opt.zero_grad(set_to_none=True);step+=1;h['offset']+=len(ix);h['observations']+=len(ix);h['loss_sum']+=float(loss.detach())*len(ix)
 if h['offset']==len(y):
  record={'epoch':h['epoch']+1,'weighted_cross_entropy':h['loss_sum']/len(y),'presentations':h['observations']};h['epoch_records'].append(record);h['epoch']+=1;h['offset']=0;h['permutation']=[];h['loss_sum']=0.;h['observations']=0;print(json.dumps(record),flush=True)
 elapsed=prior+time.monotonic()-start;ptr=save(O,m,opt,step,x['binding'],elapsed,h)
 if time.monotonic()-start>=1100:print('BUDGET_STOP');raise SystemExit
assert step==2000
_atomic_json(O/'TERMINAL.json',{'status':'FIXED100_EPOCHS_COMPLETE','step':step,'epochs':100,'model_identity':model_identity(m),'checkpoint':ptr,'elapsed_total_training':elapsed,'continuation_publication':pub,'validation_reads':0});print('COMPLETE_FIXED100',flush=True)
