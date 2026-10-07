"""Two small fixed policy families, past-only scales, recoverable CUDA fits.

No fitting entry is released until the full frozen-v2 replay has been analyzed
and a committed v3 protocol names that evidence and the fixed model budget.
"""
import argparse,json,os,platform,random,subprocess,time
from pathlib import Path
import numpy as np
import pandas as pd
import torch
from torch.utils.data import Dataset,DataLoader
from modules.transformer_v2.data import chronological_inner,train_scaler
from modules.transformer_v2.train import atomic,sha,seed_all,target_scale
from .teachers import load_teacher_development,training_teacher_view
from .policy_model import OraclePolicyTransformer,policy_objective

FAMILIES=('ORACLE_POLICY_CROSS_ASSET','ORACLE_POLICY_PATCH_CROSS_ASSET')
SEEDS=(20261006,20261007,20261008)

class InferenceSamples(Dataset):
    """Only past inputs; no label/teacher access, including unmature inference rows."""
    def __init__(self,d,indices,scaler):self.d,self.indices,self.scaler=d,np.asarray(indices),scaler
    def __len__(self):return len(self.indices)
    def __getitem__(self,j):
        d=self.d;i=int(self.indices[j]);mu,sd=self.scaler
        if i<255:raise ValueError('Full past sequence required')
        x=(d['x'][i-255:i+1]-mu)/sd;avail=d['availability'][i-255:i+1]
        mask=np.isfinite(x)&avail[...,None]
        return tuple(torch.from_numpy(v) for v in (np.where(mask,x,0.).astype('float32'),mask,avail))

class TrainingSamples(InferenceSamples):
    def __init__(self,d,indices,scaler,yscale,scenario,active,cutoff):
        super().__init__(d,indices,scaler);self.yscale,self.scenario=yscale,scenario
        self.view=training_teacher_view(d,indices,cutoff,active)
    def __getitem__(self,j):
        inputs=super().__getitem__(j);i=int(self.indices[j]);d=self.d;view=self.view
        u=d['utility'][self.scenario][i]/self.yscale[0];uv=np.isfinite(u)&view['expert_valid'][self.scenario][j,:,None]
        r=view['relative'][j];rv=view['relative_valid'][j]
        g=(d['regime'][i]-self.yscale[1])/self.yscale[2];gv=np.isfinite(g)
        e=view['expert_utilities'][self.scenario][j];ev=view['expert_valid'][self.scenario][j]
        dr=view['direction_return'][j];dv=view['direction_valid'][j]
        targets=(np.where(uv,u,0.).astype('float32'),uv,np.where(rv,r,0.).astype('float32'),rv,
                 np.where(gv,g,0.).astype('float32'),gv,np.where(ev[:,None],e,0.).astype('float32'),ev,
                 np.where(dv,dr,0.).astype('float32'),dv)
        return inputs+tuple(torch.from_numpy(v) for v in targets)

def new_network(d,family):
    if family not in FAMILIES:raise ValueError('Unregistered architecture')
    return OraclePolicyTransformer(d['x'].shape[-1],assets=len(d['symbols']),patch=8 if family==FAMILIES[1] else 1)

def fit_phase(d,indices,valid,scenario,active,family,seed,folder,epochs,select,binding,context,cutoff):
    folder.mkdir(parents=True,exist_ok=True)
    if (folder/'RESULT.json').exists():
        r=json.loads((folder/'RESULT.json').read_text())
        if r['binding']!=binding or sha(folder/'weights.pt')!=r['weights_sha256'] or sha(folder/'scaler.npz')!=r['scaler_sha256']:raise ValueError('Protected fit identity changed')
        return r
    scaler=train_scaler(d['x'],d['availability'],indices);yscale=target_scale(d,indices,scenario,active)
    tr=TrainingSamples(d,indices,scaler,yscale,scenario,active,cutoff)
    gap_scale=tr.view['gap_scales'][scenario]
    vl=TrainingSamples(d,valid,scaler,yscale,scenario,active,context['outer_cutoff']) if len(valid) else None
    loader=DataLoader(tr,batch_size=16,shuffle=True,num_workers=2,pin_memory=True)
    validation=DataLoader(vl,batch_size=32,num_workers=2,shuffle=False) if vl else None
    seed_all(seed);network=new_network(d,family).cuda();opt=torch.optim.AdamW(network.parameters(),lr=.0007,weight_decay=.001)
    best=float('inf');best_epoch=epochs;best_state=None;stale=0;start=1;checkpoint=folder/'last.pt'
    if checkpoint.exists():
        c=torch.load(checkpoint,map_location='cpu',weights_only=False)
        if c['binding']!=binding or c['gap_scale']!=gap_scale:raise ValueError('Epoch checkpoint binding changed')
        network.load_state_dict(c['model']);opt.load_state_dict(c['optimizer'])
        best,best_epoch,best_state,stale,start=c['best'],c['best_epoch'],c['best_state'],c['stale'],c['epoch']+1
        random.setstate(c['python_rng']);np.random.set_state(c['numpy_rng']);torch.set_rng_state(c['torch_rng']);torch.cuda.set_rng_state_all(c['cuda_rng'])
    begin=time.monotonic()
    def loss_for(values):
        b=[v.cuda(non_blocking=True) for v in values]
        return policy_objective(network(*b[:3]),*b[3:],gap_scale)
    for epoch in range(start,epochs+1):
        if select and stale>=7:break
        network.train();losses=[]
        for batch,values in enumerate(loader,1):
            opt.zero_grad(set_to_none=True);loss=loss_for(values)
            if not torch.isfinite(loss):raise RuntimeError('Nonfinite policy loss')
            loss.backward();norm=torch.nn.utils.clip_grad_norm_(network.parameters(),1.)
            if not torch.isfinite(norm):raise RuntimeError('Nonfinite policy gradient')
            opt.step();losses.append(float(loss.detach()))
            atomic(context['status'],dict(stage=context['stage'],fold=context['fold'],family=family,seed=seed,funding=1. if scenario==0 else .01,
                epoch=epoch,max_epoch=epochs,batch=batch,total_batches=len(loader),train_loss=float(np.mean(losses)),
                GPU_memory_bytes=torch.cuda.memory_allocated(),pid=os.getpid(),updated_at=time.time()))
        network.eval();scores=[]
        if validation:
            with torch.no_grad():
                for values in validation:scores.append(float(loss_for(values)))
        score=float(np.mean(scores)) if scores else float(np.mean(losses))
        if not select or score<best-1e-7:
            best,best_epoch,stale=score,epoch,0;best_state={k:v.detach().cpu().clone() for k,v in network.state_dict().items()}
        else:stale+=1
        row=dict(epoch=epoch,train_loss=float(np.mean(losses)),val_loss=score if select else None,elapsed_seconds=time.monotonic()-begin)
        with (folder/'epochs.jsonl').open('a') as f:f.write(json.dumps(row)+'\n')
        print(json.dumps(dict(row,family=family,seed=seed,fold=context['fold'],stage=context['stage'])),flush=True)
        tmp=folder/'last.tmp.pt';torch.save(dict(binding=binding,gap_scale=gap_scale,model=network.state_dict(),optimizer=opt.state_dict(),best=best,
             best_epoch=best_epoch,best_state=best_state,stale=stale,epoch=epoch,python_rng=random.getstate(),numpy_rng=np.random.get_state(),
             torch_rng=torch.get_rng_state(),cuda_rng=torch.cuda.get_rng_state_all()),tmp);tmp.replace(checkpoint)
    if best_state is None:raise RuntimeError('No successful policy epoch')
    tmp=folder/'weights.tmp.pt';torch.save(best_state,tmp);tmp.replace(folder/'weights.pt')
    np.savez(folder/'scaler.npz',mu=scaler[0],sd=scaler[1],utility_sd=yscale[0],regime_mu=yscale[1],regime_sd=yscale[2],gap_scale=gap_scale)
    result=dict(binding=binding,best_epoch=best_epoch,inner_validation_loss=best if select else None,gap_scale_training_only=gap_scale,
                weights_sha256=sha(folder/'weights.pt'),scaler_sha256=sha(folder/'scaler.npz'),parameters=sum(p.numel() for p in network.parameters()),
                training_rows=len(indices),validation_rows=len(valid),device='cuda',completed_at=time.time(),elapsed_seconds=time.monotonic()-begin)
    atomic(folder/'RESULT.json',result);del network,opt;torch.cuda.empty_cache();return result

def infer(d,indices,family,folder):
    with np.load(folder/'scaler.npz') as f:scaler=(f['mu'],f['sd']);utility_sd=f['utility_sd']
    network=new_network(d,family).cuda();network.load_state_dict(torch.load(folder/'weights.pt',map_location='cpu',weights_only=True));network.eval()
    loader=DataLoader(InferenceSamples(d,indices,scaler),batch_size=32,shuffle=False,num_workers=2)
    rows={k:[] for k in ('utility_pool','relative_pool','policy_probability_pool','direction_probability_pool')}
    with torch.no_grad():
        for values in loader:
            out=network(*(v.cuda() for v in values))
            rows['utility_pool'].append(out['utility'].cpu().numpy()*utility_sd)
            rows['relative_pool'].append(out['relative'].cpu().numpy())
            rows['policy_probability_pool'].append(out['policy_logits'].softmax(-1).cpu().numpy())
            rows['direction_probability_pool'].append(out['direction30_logits'].sigmoid().cpu().numpy())
    result={k:np.concatenate(v) for k,v in rows.items()};result['indices']=np.asarray(indices)
    for k in ('utility','relative','policy_probability','direction_probability'):result[k]=result[k+'_pool'].mean(1)
    np.savez_compressed(folder/'PREDICTIONS.npz',**result);del network;torch.cuda.empty_cache();return result

def main():
    p=argparse.ArgumentParser();p.add_argument('--state',required=True);p.add_argument('--collector-root',required=True);p.add_argument('--work',required=True);p.add_argument('--source-run',required=True)
    a=p.parse_args();state=Path(a.state).resolve();repo=Path(__file__).resolve().parents[2]
    if platform.system()!='Linux' or os.environ.get('WSL_DISTRO_NAME') or 'microsoft' in platform.release().lower() or state.is_relative_to(repo):raise RuntimeError('Independent Linux server and external STATE required')
    proto=repo/'reports/transformer_v3/TRANSFORMER_V3_PROTOCOL.json';protocol=json.loads(proto.read_text())
    if subprocess.check_output(['git','-C',str(repo),'show','HEAD:'+proto.relative_to(repo).as_posix()])!=proto.read_bytes():raise ValueError('Protocol must be committed before training')
    replay=state/'V2_BYBIT_LIQUIDATION_REPLAY.json';analysis=state/'V2_REPLAY_ANALYSIS.json'
    if sha(replay)!=protocol['replay_results_sha256'] or sha(analysis)!=protocol['replay_analysis_sha256']:raise ValueError('Replay and neutral analysis must precede v3 protocol and fitting')
    if protocol['models']!=list(FAMILIES) or protocol['seeds']!=list(SEEDS):raise ValueError('Fixed two-model/three-seed budget changed')
    if not torch.cuda.is_available():raise RuntimeError('CUDA required; no CPU fallback')
    torch.set_num_threads(len(os.sched_getaffinity(0)));d=load_teacher_development(a.collector_root,a.work,a.source_run)
    sources={str(f.relative_to(repo)):sha(f) for f in [Path(__file__).with_name(n) for n in ('train_policy.py','teachers.py','policy_model.py','policy_portfolio.py')]}
    for module in ('model.py','data.py','train.py'):sources['modules/transformer_v2/'+module]=sha(repo/'modules/transformer_v2'/module)
    for name,digest in sources.items():
        import hashlib
        committed=subprocess.check_output(['git','-C',str(repo),'show','HEAD:'+name])
        if hashlib.sha256(committed).hexdigest()!=digest:raise ValueError('Training source must match committed HEAD: '+name)
    collector=Path(a.collector_root)
    dependencies={name:sha(collector/'pipeline'/name) for name in ('train.py','make_labels.py','common.py')}
    binding=dict(protocol_sha256=sha(proto),sources=sources,collector_sources=dependencies,source_run_binding_sha256=sha(Path(a.source_run)/'BINDING.json'),teacher_sources=d['teacher_receipts'])
    path=state/'POLICY_TRAIN_BINDING.json'
    if path.exists():
        if json.loads(path.read_text())!=binding:raise ValueError('Training source recipe changed; preserve fits')
    else:atomic(path,binding)
    completed=0;total=60;status=state/'policy-train-progress.json'
    for scenario,tag in enumerate(('raw_fraction','raw_percent')):
      for fi,fold in enumerate(d['folds'],1):
        active=np.array([s in fold['active'] for s in d['symbols']]);train=np.array(sorted({i for _,_,i in fold['train']}))
        training_teacher_view(d,train,fold['cutoff'],active)
        inner,valid=chronological_inner(train,d['dates'],d['label_end']);inner_cutoff=d['dates'][valid[0]]-pd.Timedelta(days=60)
        for family in FAMILIES:
          for seed in SEEDS:
            base=state/'policy-fits'/tag/f'fold{fi}'/family/f'seed{seed}';done=base/'FIT_COMPLETE.json'
            if done.exists():
                r=json.loads(done.read_text())
                if r['binding']!=binding or sha(base/'refit/PREDICTIONS.npz')!=r['prediction_sha256']:raise ValueError('Frozen prediction identity changed')
                completed+=1;continue
            context=dict(fold=fi,status=status,stage='POLICY_INNER_SELECTION',outer_cutoff=fold['cutoff'])
            for attempt in range(2):
                try:
                    selected=fit_phase(d,inner,valid,scenario,active,family,seed,base/'inner',40,True,binding,context,inner_cutoff)
                    context['stage']='POLICY_FIXED_EPOCH_REFIT'
                    fit_phase(d,train,[],scenario,active,family,seed,base/'refit',selected['best_epoch'],False,binding,context,fold['cutoff'])
                    infer(d,fold['calendar'],family,base/'refit')
                    atomic(done,dict(binding=binding,fold=fi,family=family,seed=seed,scenario=tag,best_epoch=selected['best_epoch'],
                                    active=fold['active'],prediction_sha256=sha(base/'refit/PREDICTIONS.npz')));break
                except Exception as exc:
                    atomic(base/f'FAILURE_ATTEMPT_{attempt+1}.json',dict(error_type=type(exc).__name__,error=str(exc),time=time.time()))
                    if attempt==1:raise
            completed+=1;print(f'POLICY FIT {completed}/{total}: {tag} fold{fi} {family} seed{seed}',flush=True)
            atomic(state/'POLICY_FIT_PROGRESS.json',dict(status='RUNNING',completed=completed,total=total,pid=os.getpid(),updated_at=time.time()))
    atomic(state/'POLICY_FIT_PROGRESS.json',dict(status='COMPLETE',completed=completed,total=total,pid=os.getpid(),updated_at=time.time()))

if __name__=='__main__':main()
