"""One bounded supervised sequence-skill test; no portfolio optimizer or2025 IO."""
from pathlib import Path
import argparse,json,time,fcntl
import numpy as np
import torch
from modules.temporal_balanced_history.inputs import training,CUTOFF
from modules.temporal_balanced_history.train import save,sources as training_sources
from modules.temporal_neutral_short.model import initialize
from modules.temporal_short_expansion.checkpoint import _validate_model_state,_validate_saved_optimizer,_validate_rng
from modules.temporal_two_expert.checkpoint import _atomic_json,_rng_state,_restore_rng,model_identity,make_optimizer
from modules.temporal_two_expert.exact import sha
from modules.temporal_two_expert.inputs import digest
ROOT=Path(__file__).resolve().parents[1]
SLOTS=[0,1,4,5]

def sources():return dict(training_sources(),**{'modules/temporal_supervised_gate.py':sha(Path(__file__))})
def data(state):
    state=Path(state);es,p,scaler,bindings=training(state);labels=state/'balanced-history/LABELS.json';manifest=json.loads((ROOT/'research/temporal-balanced-history-20261010/MANIFEST.json').read_text());expected=next(x['SHA256'] for x in manifest['members'] if x['path']=='balanced-history/LABELS.json');assert sha(labels)==expected
    rows=json.loads(labels.read_text());values=[];valid=[];step=[];expert=[];ys=[];meta=[]
    for r in rows:
        e=es[r['wallet']];i=int(np.searchsorted(e.windows.decision_us,r['decision_us']));assert e.windows.decision_us[i]==r['decision_us'] and r['label_available_us']<CUTOFF and i+21<=len(e.contexts)-1;u=np.asarray(r['hindsight_fixed_policy_21day_utility']);assert u.shape==(4,) and np.isfinite(u).all() and r['winner']==int(u.argmax())
        values.append(e.windows.values[i]);valid.append(e.windows.valid[i]);step.append(e.windows.step_valid[i]);expert.append(e.expert_state[i]);ys.append(r['winner']);meta.append((r['decision_us'],r['label_available_us']))
    arrays=[np.stack(a) for a in [values,valid,step,expert]];y=np.asarray(ys,np.int64);counts=np.bincount(y,minlength=4);weights=len(y)/(4*counts);assert len(y)==1230 and (counts==[61,541,310,318]).all()
    receipt={'episodes':[e.identity for e in es],'label_SHA256':expected,'cutoff':CUTOFF,'scaler':scaler.identity,'rows':len(y),'class_counts':counts.tolist(),'class_weights':weights.tolist(),'label_clock_max':int(np.asarray(meta)[:,1].max())}
    return arrays,y,weights,scaler,receipt

def ready(state,out):
    out=Path(out);out.mkdir(exist_ok=False);a,y,w,s,receipt=data(state);m,opt=initialize(s);assert opt.param_groups[0]['lr']==.001
    plan={'status':'SUPERVISED_PREFIT_NOT_TRAINED','hypothesis':'Explicitly supervised21day fixed-expert winner may encode timing information that coupled daily utility training failed to learn. Skill and economic usefulness unproven.','epochs':20,'batch_size':64,'updates':400,'training_presentations':24600,'parameters':m.parameter_count,'lr':.001,'optimizer':'sameAdam0.9/0.999 eps1e-8 clip1 dropout0.1','objective':'class-balanced cross entropy on four existing output coordinates; no architecture expansion','sampling':'each epoch visits every training window once in a seeded random order; sequence-internal chronology intact; no financial wallet resets because this stage has no wallet rollout','target':'argmax mature21day cost-aware fixed-policy utility; attention labels reused as explicit supervised labels; not a tradable switching oracle','inference':'p_natural ∝ q_balanced / class_weight, renormalized; this correction is predeclared, never fitted on2025','evaluation':'one2025 seen-development forward classification check; frozen trainclassprior and constanttrainmeanutility baselines; full overlapping dates plus fixed21day nonoverlap grid; report logloss,Brier,accuracy,shortrecall and opportunity regret. No trading replay unless evidence supports incremental skill.','no2025training':True,'data':receipt,'initial_model_identity':model_identity(m),'source_identity':sources(),'budget':'oneCPU,2GBRSS,4GBaddress,1200sec; exact per-minibatch model/Adam/RNG/permutation recovery; no grid'}
    _atomic_json(out/'PLAN.json',plan);binding={'plan_SHA256':sha(out/'PLAN.json'),'sources':sources(),'data':receipt,'torch':str(torch.__version__),'numpy':str(np.__version__)};history={'epoch':0,'offset':0,'permutation':[],'loss_sum':0.,'observations':0,'epoch_records':[]};save(out,m,opt,0,binding,0.,history);_atomic_json(out/'READY.json',{'binding':binding,'initial_model_identity':model_identity(m)});print(json.dumps(plan,indent=2),flush=True)

def run(state,out,publication):
    out=Path(out);plan=json.loads((out/'PLAN.json').read_text());pub=json.loads(Path(publication).read_text());assert pub['status']=='SUPERVISED_PREFIT_PUBLIC_VERIFIED' and pub['plan_SHA256']==sha(out/'PLAN.json');assert plan['source_identity']==sources();lock=(out/'run.lock').open('a+');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    if (out/'TERMINAL.json').exists():print('ALREADY_FINISHED');return
    arrays,y,weights,scaler,receipt=data(state);assert receipt==plan['data'];m,opt=initialize(scaler);ptr=json.loads((out/'latest.json').read_text());assert sha(out/ptr['path'])==ptr['SHA256'];x=torch.load(out/ptr['path'],map_location='cpu',weights_only=True);binding=json.loads((out/'READY.json').read_text())['binding'];assert x['binding']==binding and binding['sources']==sources();_validate_model_state(m,x['model'],x['model_identity']);_validate_saved_optimizer(m,opt,x['optimizer'],x['step'],{n:0 for n,_ in m.named_parameters()});_validate_rng(x['rng']);m.load_state_dict(x['model']);opt.load_state_dict(x['optimizer']);_restore_rng(x['rng']);m.train();h=x['history'];step=x['step'];prior=x['elapsed'];start=time.monotonic();cw=torch.tensor(weights,dtype=m.mean.dtype)
    while h['epoch']<20:
        if not h['permutation']:h['permutation']=np.random.permutation(len(y)).tolist()
        ix=np.asarray(h['permutation'][h['offset']:h['offset']+64]);t=[torch.tensor(a[ix].copy()) for a in arrays];t[0]=t[0].to(m.mean.dtype);t[3]=t[3].to(m.mean.dtype);labels=torch.tensor(y[ix],dtype=torch.int64);opt.zero_grad(set_to_none=True);q=m(*t)[:,SLOTS];loss=-(torch.log(q[torch.arange(len(ix)),labels].clamp_min(1e-12))*cw[labels]).mean();assert torch.isfinite(loss);loss.backward();norm=torch.nn.utils.clip_grad_norm_(m.parameters(),1.,error_if_nonfinite=True);opt.step();opt.zero_grad(set_to_none=True);step+=1;h['offset']+=len(ix);h['observations']+=len(ix);h['loss_sum']+=float(loss.detach())*len(ix)
        if h['offset']==len(y):
            h['epoch_records'].append({'epoch':h['epoch']+1,'weighted_cross_entropy':h['loss_sum']/len(y),'presentations':h['observations']});h['epoch']+=1;h['offset']=0;h['permutation']=[];h['loss_sum']=0.;h['observations']=0;print(json.dumps(h['epoch_records'][-1]),flush=True)
        elapsed=prior+time.monotonic()-start;ptr=save(out,m,opt,step,binding,elapsed,h)
        if elapsed>=1100 and h['epoch']<20:print('BUDGET_STOP_CHECKPOINT_RETAINED');return
    assert step==400;_atomic_json(out/'TERMINAL.json',{'status':'FIXED20_EPOCHS_COMPLETE','step':step,'epochs':20,'presentations':24600,'elapsed':elapsed,'model_identity':model_identity(m),'checkpoint':ptr,'binding':binding,'validation_reads':0,'scaler_updates':0});print('COMPLETE_20_EPOCHS_400_UPDATES',flush=True)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('mode',choices=['ready','run']);p.add_argument('--state',required=True);p.add_argument('--out',required=True);p.add_argument('--publication');a=p.parse_args();torch.set_num_threads(1);torch.use_deterministic_algorithms(True)
    if a.mode=='ready':ready(a.state,a.out)
    else:run(a.state,a.out,a.publication)
