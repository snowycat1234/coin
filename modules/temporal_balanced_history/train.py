"""Two fixed sequential fits with atomic per-update recovery; no evaluation IO."""
import argparse,json,time,os,fcntl
from pathlib import Path
import numpy as np,torch
from .inputs import training
from .gradient import gradients
from modules.temporal_neutral_short.model import initialize
from modules.temporal_neutral_short.protocol import sources as inherited_sources
from modules.temporal_two_expert.checkpoint import _atomic_json,_rng_state,_restore_rng,model_identity
from modules.temporal_short_expansion.checkpoint import _validate_model_state,_validate_saved_optimizer,_validate_rng
from modules.temporal_two_expert.exact import sha
from modules.temporal_two_expert.inputs import digest
ROOT=Path(__file__).resolve().parents[2]
def sources():
    return {**inherited_sources(),**{str(Path(__file__).parent.joinpath(n).relative_to(ROOT)):sha(Path(__file__).parent/n) for n in ['__init__.py','inputs.py','gradient.py','prepare.py','train.py']}}
def save(folder,model,opt,step,binding,elapsed,history):
    data={'step':step,'binding':binding,'model':model.state_dict(),'optimizer':opt.state_dict(),'rng':_rng_state(),'model_identity':model_identity(model),'elapsed':elapsed,'history':history}
    p=folder/f'step-{step:08d}.pt';tmp=p.with_suffix('.partial');assert not p.exists() and not tmp.exists();torch.save(data,tmp)
    with tmp.open('rb') as f:os.fsync(f.fileno())
    os.replace(tmp,p);pointer={'path':p.name,'SHA256':sha(p),'step':step};_atomic_json(folder/'latest.json',pointer);return pointer

def ready(state,out):
    out=Path(out);plan=json.loads((out/'PLAN.json').read_text());es,p,scaler,bindings=training(state);assert [e.identity for e in es]==plan['episode_identities'];assert scaler.identity==plan['scaler_identity'];assert sha(out/'WEIGHTS.npz')==plan['weight_SHA256'];_atomic_json(out/'SOURCES.json',sources())
    model,_=initialize(scaler);assert model_identity(model)==plan['initial_model_identity'];opt=torch.optim.Adam(model.parameters(),lr=.0003,betas=(.9,.999),eps=1e-8,weight_decay=0.,foreach=False)
    binding={'plan_SHA256':sha(out/'PLAN.json'),'sources':sources(),'torch':str(torch.__version__),'numpy':str(np.__version__),'scaler':scaler.identity,'episodes':[e.identity for e in es]}
    for arm in plan['arms']:
        f=out/arm;f.mkdir(exist_ok=False);save(f,model,opt,0,dict(binding,arm=arm),0.,[])
    _atomic_json(out/'READY.json',{'status':'PREFIT_FROZEN','binding':binding,'initial_model_identity':model_identity(model),'arms':plan['arms']});print('PREFIT_READY',flush=True)

def run(state,out,arm,publication):
    out=Path(out);folder=out/arm;plan=json.loads((out/'PLAN.json').read_text());assert arm in plan['arms'];assert sources()==json.loads((out/'SOURCES.json').read_text());public=json.loads(Path(publication).read_text());assert public['status']=='PUBLIC_PREFIT_VERIFIED' and public['plan_SHA256']==sha(out/'PLAN.json')
    es,p,scaler,bindings=training(state);ready=json.loads((out/'READY.json').read_text());binding=dict(ready['binding'],arm=arm);assert binding['episodes']==[e.identity for e in es] and binding['scaler']==scaler.identity and binding['sources']==sources()
    lock=(folder/'run.lock').open('a+');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    if (folder/'TERMINAL.json').exists():print('ALREADY_COMPLETE');return
    ptr=json.loads((folder/'latest.json').read_text());assert sha(folder/ptr['path'])==ptr['SHA256'];snap=torch.load(folder/ptr['path'],map_location='cpu',weights_only=True);assert snap['binding']==binding and snap['step']==ptr['step']
    model,_=initialize(scaler);opt=torch.optim.Adam(model.parameters(),lr=.0003,betas=(.9,.999),eps=1e-8,weight_decay=0.,foreach=False);births={n:0 for n,_ in model.named_parameters()};_validate_model_state(model,snap['model'],snap['model_identity']);_validate_saved_optimizer(model,opt,snap['optimizer'],snap['step'],births);_validate_rng(snap['rng']);model.load_state_dict(snap['model']);opt.load_state_dict(snap['optimizer']);_restore_rng(snap['rng']);assert model_identity(model)==snap['model_identity']
    z=np.load(out/'WEIGHTS.npz');weights=[np.ones(len(e.contexts)) if arm=='NATURAL' else z[f'wallet_{i}'] for i,e in enumerate(es)];model.train();start=time.monotonic();history=snap['history'];prior=snap['elapsed'];step=snap['step']
    for step in range(step+1,257):
        opt.zero_grad(set_to_none=True);loss=gradients(model,es,p,weights);norm=torch.nn.utils.clip_grad_norm_(model.parameters(),1.,error_if_nonfinite=True);opt.step();opt.zero_grad(set_to_none=True);elapsed=prior+time.monotonic()-start;history.append({'step':step,'loss':float(loss),'gradient_norm':float(norm)});ptr=save(folder,model,opt,step,binding,elapsed,history)
        if step%16==0:print(json.dumps({'arm':arm,'step':step,'target':256,'elapsed':elapsed,'loss':loss}),flush=True)
        if elapsed>=1150 and step<256:print('SLICE_BUDGET_REACHED_CHECKPOINT_RETAINED',flush=True);return
    _atomic_json(folder/'TERMINAL.json',{'status':'FIXED256_COMPLETE','step':256,'elapsed':elapsed,'checkpoint':ptr,'model_identity':model_identity(model),'binding':binding,'last_loss':loss,'validation_reads':0,'scaler_updates':0});print('FIXED256_COMPLETE',arm,flush=True)
if __name__=='__main__':
    a=argparse.ArgumentParser();a.add_argument('mode',choices=['ready','run']);a.add_argument('--state',required=True);a.add_argument('--out',required=True);a.add_argument('--arm');a.add_argument('--publication');x=a.parse_args();torch.set_num_threads(1);torch.use_deterministic_algorithms(True)
    if x.mode=='ready':ready(x.state,x.out)
    else:run(x.state,x.out,x.arm,x.publication)
