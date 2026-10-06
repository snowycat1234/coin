"""CUDA-only frozen walk-forward fits, recoverable each epoch, external artifacts."""
import argparse,hashlib,json,os,random,subprocess,time
from pathlib import Path
import numpy as np
import torch
from torch.utils.data import Dataset,DataLoader
from .data import load_development,chronological_inner,train_scaler
from .model import CrossAssetTransformer,objective

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def atomic(path,value):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True);tmp=path.with_suffix(path.suffix+'.tmp')
    tmp.write_text(json.dumps(value,indent=2,allow_nan=False,default=str)+'\n');tmp.replace(path)
def seed_all(seed):
    random.seed(seed);np.random.seed(seed);torch.manual_seed(seed);torch.cuda.manual_seed_all(seed)
    torch.backends.cudnn.benchmark=False

class Samples(Dataset):
    def __init__(self,d,indices,scale,active,scaler,yscale):
        self.d,self.indices,self.scale,self.active,self.scaler,self.yscale=d,np.asarray(indices),scale,active,scaler,yscale
    def __len__(self):return len(self.indices)
    def __getitem__(self,j):
        d=self.d;i=int(self.indices[j]);mu,sd=self.scaler
        x=(d['x'][i-255:i+1]-mu)/sd;mask=np.isfinite(x)&d['availability'][i-255:i+1,:,None]
        x=np.where(mask,x,0.).astype('float32');avail=d['availability'][i-255:i+1]
        ready=d['ready'][i]&self.active
        y=d['utility'][self.scale][i]/self.yscale[0];ym=np.isfinite(y)&ready[:,None]
        rel=d['relative'][i];rm=np.isfinite(rel)&ready[:,None]
        regime=(d['regime'][i]-self.yscale[1])/self.yscale[2];gm=np.isfinite(regime)
        return tuple(torch.from_numpy(v) for v in (x,mask,avail,np.where(ym,y,0.).astype('float32'),ym,
            np.where(rm,rel,0.).astype('float32'),rm,np.where(gm,regime,0.).astype('float32'),gm))

def target_scale(d,indices,scenario,active):
    y=d['utility'][scenario][indices].copy();y[:,~active]=np.nan
    sd=np.nanstd(y,axis=(0,1));sd=np.where(np.isfinite(sd)&(sd>1e-6),sd,1.)
    reg=d['regime'][indices];mu=np.nanmean(reg,axis=0);rs=np.nanstd(reg,axis=0)
    assert np.isfinite(mu).all() and np.isfinite(rs).all()
    return tuple(v.astype('float32') for v in (sd,mu,np.where(rs>1e-6,rs,1.)))

def predict_forward(network,batch,old):
    x,mask,available,*_=batch
    if not old:return network(x,mask,available)
    b,t,a,f=x.shape
    observed=torch.where(mask,x,0.)
    inputs=torch.cat([observed,mask.to(x.dtype)],-1).permute(0,2,1,3).reshape(b*a,t,f*2)
    output=network(inputs,torch.arange(a,device=x.device).repeat(b)).reshape(b,a,2)
    return dict(utility=output[:,None].expand(b,3,a,2),relative=(-output[...,1])[:,None,:,None].expand(b,3,a,3),
                regime=torch.zeros(b,3,3,device=x.device))

def new_network(d,family):
    if family=='TRANSFORMER_SHARED':
        from pipeline.models import build_model
        return build_model(family,d['x'].shape[-1]*2,len(d['symbols']),256)
    return CrossAssetTransformer(d['x'].shape[-1],patch=8 if family.startswith('PATCH_') else 1)

def fit_phase(d,indices,valid,scenario,active,family,seed,folder,epochs,select,binding,context):
    folder.mkdir(parents=True,exist_ok=True)
    if (folder/'RESULT.json').exists():
        r=json.loads((folder/'RESULT.json').read_text());assert r['binding']==binding
        assert sha(folder/'weights.pt')==r['weights_sha256'];return r
    old=family=='TRANSFORMER_SHARED';multitask='MULTITASK' in family
    scaler=train_scaler(d['x'],d['availability'],indices);yscale=target_scale(d,indices,scenario,active)
    seed_all(seed);network=new_network(d,family).cuda()
    assert sum(p.numel() for p in network.parameters())<10_000_000
    opt=torch.optim.AdamW(network.parameters(),lr=.0007,weight_decay=.001)
    loader=DataLoader(Samples(d,indices,scenario,active,scaler,yscale),batch_size=64 if old else 16,shuffle=True,num_workers=2,pin_memory=True)
    vl=DataLoader(Samples(d,valid,scenario,active,scaler,yscale),batch_size=32,shuffle=False,num_workers=2,pin_memory=True) if len(valid) else None
    best=float('inf');best_epoch=epochs;best_state=None;stale=0;start=1
    checkpoint=folder/'last.pt'
    if checkpoint.exists():
        saved=torch.load(checkpoint,map_location='cpu',weights_only=False);assert saved['binding']==binding
        network.load_state_dict(saved['model']);opt.load_state_dict(saved['optimizer'])
        best,best_epoch,best_state,stale,start=saved['best'],saved['best_epoch'],saved['best_state'],saved['stale'],saved['epoch']+1
        random.setstate(saved['python_rng']);np.random.set_state(saved['numpy_rng']);torch.set_rng_state(saved['torch_rng']);torch.cuda.set_rng_state_all(saved['cuda_rng'])
    begin=time.monotonic();history=[]
    def batch_loss(values):
        batch=[v.cuda(non_blocking=True) for v in values];o=predict_forward(network,batch,old)
        return objective(o,*batch[3:],multitask)
    for ep in range(start,epochs+1):
        if select and stale>=7:break
        network.train();losses=[]
        for bi,values in enumerate(loader):
            opt.zero_grad(set_to_none=True);loss=batch_loss(values)
            if not torch.isfinite(loss):raise RuntimeError('Nonfinite loss; do not silently clamp')
            loss.backward();norm=torch.nn.utils.clip_grad_norm_(network.parameters(),1.)
            if not torch.isfinite(norm):raise RuntimeError('Nonfinite gradient')
            opt.step();losses.append(float(loss.detach()))
            atomic(context['status'],dict(stage=context['stage'],fold=context['fold'],seed=seed,family=family,funding=1. if scenario==0 else .01,
                epoch=ep,max_epoch=epochs,batch=bi+1,total_batches=len(loader),train_loss=float(np.mean(losses)),
                val_loss=None,GPU_memory_bytes=torch.cuda.memory_allocated(),ETA_seconds=(time.monotonic()-begin)/max(1,(ep-start)*len(loader)+bi+1)*((epochs-ep)*len(loader)+len(loader)-bi-1),
                pid=os.getpid(),updated_at=time.time()))
        network.eval();vloss=[]
        if vl is not None:
            with torch.no_grad():
                for values in vl:vloss.append(float(batch_loss(values)))
        score=float(np.mean(vloss)) if vloss else float(np.mean(losses))
        if not select or score<best-1e-7:
            best,best_epoch,stale=score,ep,0;best_state={k:v.detach().cpu().clone() for k,v in network.state_dict().items()}
        else:stale+=1
        history.append(dict(epoch=ep,train_loss=float(np.mean(losses)),val_loss=score if select else None))
        completed_epoch=dict(stage=context['stage'],fold=context['fold'],seed=seed,family=family,funding=1. if scenario==0 else .01,
                             epoch=ep,max_epoch=epochs,train_loss=history[-1]['train_loss'],val_loss=history[-1]['val_loss'],
                             GPU_memory_bytes=torch.cuda.max_memory_allocated(),elapsed_seconds=time.monotonic()-begin,
                             ETA_seconds=(time.monotonic()-begin)/max(1,ep-start+1)*(epochs-ep),pid=os.getpid(),updated_at=time.time())
        print(json.dumps(completed_epoch),flush=True);atomic(context['status'],completed_epoch)
        tmp=folder/'last.tmp.pt';torch.save(dict(binding=binding,model=network.state_dict(),optimizer=opt.state_dict(),best=best,best_epoch=best_epoch,
             best_state=best_state,stale=stale,epoch=ep,python_rng=random.getstate(),numpy_rng=np.random.get_state(),
             torch_rng=torch.get_rng_state(),cuda_rng=torch.cuda.get_rng_state_all()),tmp);tmp.replace(checkpoint)
        with (folder/'epochs.jsonl').open('a') as stream:stream.write(json.dumps(history[-1])+'\n')
    assert best_state is not None
    tmp=folder/'weights.tmp.pt';torch.save(best_state,tmp);tmp.replace(folder/'weights.pt')
    np.savez(folder/'scaler.npz',mu=scaler[0],sd=scaler[1],utility_sd=yscale[0],regime_mu=yscale[1],regime_sd=yscale[2])
    result=dict(binding=binding,best_epoch=best_epoch,inner_validation_loss=best if select else None,
                weights_sha256=sha(folder/'weights.pt'),scaler_sha256=sha(folder/'scaler.npz'),parameters=sum(p.numel() for p in network.parameters()),
                completed_at=time.time(),elapsed_seconds=time.monotonic()-begin,training_rows=len(indices),validation_rows=len(valid),device='cuda')
    atomic(folder/'RESULT.json',result);del network,opt;torch.cuda.empty_cache();return result

def infer(d,indices,scenario,active,family,folder):
    with np.load(folder/'scaler.npz') as f:scaler=(f['mu'],f['sd']);yscale=(f['utility_sd'],f['regime_mu'],f['regime_sd'])
    network=new_network(d,family).cuda();network.load_state_dict(torch.load(folder/'weights.pt',map_location='cpu',weights_only=True));network.eval()
    loader=DataLoader(Samples(d,indices,scenario,active,scaler,yscale),batch_size=32,num_workers=2,shuffle=False)
    pools=[];relative=[];regime=[]
    with torch.no_grad():
        for values in loader:
            out=predict_forward(network,[v.cuda() for v in values],family=='TRANSFORMER_SHARED')
            pools.append(out['utility'].cpu().numpy()*yscale[0]);relative.append(out['relative'].cpu().numpy());regime.append(out['regime'].cpu().numpy())
    result=dict(utility_pool=np.concatenate(pools),relative_pool=np.concatenate(relative),regime_pool=np.concatenate(regime),indices=np.asarray(indices))
    if family in ('TRANSFORMER_SHARED','CROSS_ASSET_UTILITY'):
        result['relative_pool']=np.repeat((-result['utility_pool'][...,1])[...,None],3,axis=-1)
    result['utility']=result['utility_pool'].mean(1);result['relative']=result['relative_pool'].mean(1)
    np.savez_compressed(folder/'PREDICTIONS.npz',**result);del network;torch.cuda.empty_cache();return result

def main():
    p=argparse.ArgumentParser();p.add_argument('--state',required=True);p.add_argument('--collector-root',required=True);p.add_argument('--work',required=True);p.add_argument('--source-run',required=True)
    a=p.parse_args();state=Path(a.state).resolve();repo=Path(__file__).resolve().parents[2]
    assert not state.is_relative_to(repo)
    proto=repo/'reports/transformer_v2/TRANSFORMER_V2_PROTOCOL.json';protocol=json.loads(proto.read_text())
    assert sha(proto)==(proto.with_suffix('.sha256')).read_text().strip()
    committed=subprocess.check_output(['git','-C',str(repo),'show','HEAD:reports/transformer_v2/TRANSFORMER_V2_PROTOCOL.json'])
    assert committed==proto.read_bytes(),'Protocol must be committed before fitting'
    subprocess.run(['git','-C',str(repo),'diff','--exit-code','--',str(proto)],check=True)
    assert torch.cuda.is_available(),'CUDA unavailable; no CPU fallback';torch.ones(1,device='cuda')
    torch.set_num_threads(len(os.sched_getaffinity(0)))
    d=load_development(a.collector_root,a.work,a.source_run);status=state/'train-progress.json'
    code={f.name:sha(f) for f in [Path(__file__),Path(__file__).with_name('model.py'),Path(__file__).with_name('data.py'),Path(__file__).with_name('portfolio.py')]}
    binding=dict(protocol_sha256=sha(proto),source_sha256=code,dataset_sha256=protocol['data_manifest_sha256'],base_commit=protocol['native_base_commit'])
    if (state/'TRAIN_BINDING.json').exists():assert json.loads((state/'TRAIN_BINDING.json').read_text())==binding,'Source recipe changed; preserve previous fits and review'
    else:atomic(state/'TRAIN_BINDING.json',binding)
    total=5*4*3*2;completed=0
    for scenario,tag in enumerate(('raw_fraction','raw_percent')):
      for fi,fold in enumerate(d['folds'],1):
        active=np.array([s in fold['active'] for s in d['symbols']]);train=np.array(sorted({i for _,_,i in fold['train']}))
        assert (d['label_end'][train]<fold['cutoff']).all()
        inner,valid=chronological_inner(train,d['dates'],d['label_end'])
        predict=fold['calendar'];assert np.min(predict)>=255
        for family in protocol['models']:
          for seed in protocol['seeds']:
            base=state/'fits'/tag/f'fold{fi}'/family/f'seed{seed}'
            result_path=base/'FIT_COMPLETE.json'
            if result_path.exists():
                old=json.loads(result_path.read_text());assert old['binding']==binding and sha(base/'refit/PREDICTIONS.npz')==old['prediction_sha256'];completed+=1;continue
            context=dict(fold=fi,status=status,stage='INNER_EARLY_STOPPING')
            for attempt in range(2):
                try:
                    selection=fit_phase(d,inner,valid,scenario,active,family,seed,base/'inner',40,True,binding,context)
                    context['stage']='FIXED_EPOCH_OUTER_REFIT'
                    fit_phase(d,train,[],scenario,active,family,seed,base/'refit',selection['best_epoch'],False,binding,context)
                    context['stage']='OUTER_PREDICTION_NO_SELECTION';infer(d,predict,scenario,active,family,base/'refit')
                    atomic(result_path,dict(binding=binding,fold=fi,family=family,seed=seed,scenario=tag,best_epoch=selection['best_epoch'],
                           active=fold['active'],prediction_sha256=sha(base/'refit/PREDICTIONS.npz')));break
                except Exception as e:
                    atomic(base/f'FAILURE_ATTEMPT_{attempt+1}.json',dict(error_type=type(e).__name__,error=str(e),time=time.time()))
                    if attempt==1:raise
            completed+=1;print(f'FIT COMPLETE {completed}/{total}: {tag} fold{fi} {family} seed{seed}',flush=True)
            atomic(state/'FIT_PROGRESS.json',dict(status='RUNNING',completed=completed,total=total,pid=os.getpid(),updated_at=time.time()))
    atomic(state/'FIT_PROGRESS.json',dict(status='COMPLETE',completed=completed,total=total,pid=os.getpid(),updated_at=time.time()))

if __name__=='__main__':main()
