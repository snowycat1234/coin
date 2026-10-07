"""Released causal features and strictly read-only inference of protected weights."""
import json
from pathlib import Path
import numpy as np
import pandas as pd
import torch
from torch.utils.data import DataLoader
from modules.transformer_v2.data import load_development
from modules.transformer_v2.train import sha,new_network as v2_network,predict_forward
from .train_policy import InferenceSamples,new_network as policy_network,FAMILIES
from .locked_bridge_data import require_freeze

DAY=86_400_000_000

def build_features(state,input_manifest,collector_root,development_work,source_run):
    require_freeze(state)
    if input_manifest['status']!='IMPUTED184DAY_INPUT_CALENDAR_READY':raise ValueError('Explicit imputed input admission required')
    for e in input_manifest['artifacts']:
        if sha(e['path'])!=e['sha256']:raise ValueError('Frozen admitted source changed')
    past=load_development(collector_root,development_work,source_run)
    from pipeline.make_labels import feature_frame,BASE_FEATURES
    from pipeline.train import market_features
    base=Path(input_manifest['work'])/'data/normalized';frames={}
    for symbol in past['symbols']:
        source=pd.read_parquet(base/(symbol+'_daily.parquet')).reset_index(drop=True)
        f=feature_frame(source,256);f['feature_ready']&=f.dt.ge(pd.Timestamp('2022-09-01',tz='UTC'));frames[symbol]=f
    dates=pd.DatetimeIndex(frames[past['symbols'][0]].dt)
    if dates.max()!=pd.Timestamp('2026-08-31',tz='UTC') or not dates.is_unique or not all(pd.DatetimeIndex(f.dt).equals(dates) for f in frames.values()):raise ValueError('Released causal calendar changed')
    market=market_features(frames).reset_index(drop=True)
    x=np.stack([pd.concat([frames[s][BASE_FEATURES],market],axis=1).to_numpy('float32') for s in past['symbols']],1)
    if not np.allclose(x[:len(past['x'])],past['x'],equal_nan=True,rtol=1e-6,atol=1e-7):raise ValueError('Protected past feature recipe changed')
    d=dict(symbols=past['symbols'],dates=dates,x=x,features=past['features'],
           availability=np.stack([np.isfinite(frames[s].close) for s in past['symbols']],1),
           ready=np.stack([frames[s].feature_ready.to_numpy(bool) for s in past['symbols']],1),
           sma=np.stack([frames[s].sma_signal.to_numpy(float) for s in past['symbols']],1))
    indices=np.flatnonzero((dates>=pd.Timestamp('2026-02-28',tz='UTC'))&(dates<pd.Timestamp('2026-08-31',tz='UTC')))
    if not np.array_equal(dates[indices].as_unit('us').asi8+DAY,np.arange(1772323200000000,1788220800000000,DAY)):raise ValueError('Exactly184 released decision days required')
    # No utility, expert, direction, relative or regime teachers in inference d.
    return d,indices

def immutable_infer(d,indices,family,folder,expected_weights,expected_scaler):
    folder=Path(folder)
    if sha(folder/'weights.pt')!=expected_weights or sha(folder/'scaler.npz')!=expected_scaler:raise ValueError('Frozen weights/scaler changed')
    if not torch.cuda.is_available():raise RuntimeError('Server CUDA required for released inference')
    with np.load(folder/'scaler.npz') as f:scaler=(f['mu'],f['sd']);utility_sd=f['utility_sd']
    policy=family in FAMILIES;network=(policy_network if policy else v2_network)(d,family).cuda()
    network.load_state_dict(torch.load(folder/'weights.pt',map_location='cpu',weights_only=True));network.eval()
    loader=DataLoader(InferenceSamples(d,indices,scaler),batch_size=32,shuffle=False,num_workers=2)
    utility=[];relative=[];probabilities=[]
    with torch.no_grad():
        for values in loader:
            b=[v.cuda() for v in values]
            out=network(*b) if policy else predict_forward(network,b,family=='TRANSFORMER_SHARED')
            utility.append(out['utility'].mean(1).cpu().numpy()*utility_sd)
            relative.append(out['relative'].mean(1).cpu().numpy())
            if policy:probabilities.append(out['policy_logits'].softmax(-1).mean(1).cpu().numpy())
    result=dict(utility=np.concatenate(utility),relative=np.concatenate(relative),indices=np.asarray(indices))
    if family=='TRANSFORMER_SHARED':result['relative']=np.repeat((-result['utility'][...,1])[...,None],3,-1)
    if policy:result['policy_probability']=np.concatenate(probabilities)
    if not all(np.isfinite(v).all() for v in result.values()):raise ValueError('Nonfinite locked prediction')
    del network;torch.cuda.empty_cache()
    # No output or checkpoint is written into the supplied protected folder.
    return result

def immutable_legacy_transformer(d,indices,study):
    from pipeline.models import build_model
    folder=Path(study)/'models/fold5/TRANSFORMER_SHARED';checkpoint=json.loads((folder/'CHECKPOINT.json').read_text())
    for e in checkpoint['models']:
        if sha(folder/e['name'])!=e['sha256']:raise ValueError('Protected stale baseline changed')
    with np.load(folder/'scaler.npz') as f:scaler=(f['mu'],f['sd'])
    network=build_model('TRANSFORMER_SHARED',d['x'].shape[-1]*2,len(d['symbols']),256).cuda()
    network.load_state_dict(torch.load(folder/'weights.pt',map_location='cpu',weights_only=True));network.eval()
    out=[]
    with torch.no_grad():
        for values in DataLoader(InferenceSamples(d,indices,scaler),batch_size=32,shuffle=False,num_workers=2):
            out.append(predict_forward(network,[v.cuda() for v in values],True)['utility'][:,0].cpu().numpy())
    u=np.concatenate(out);del network;torch.cuda.empty_cache()
    return dict(utility=u,relative=np.repeat((-u[...,1])[...,None],3,-1),indices=np.asarray(indices)),dict(checkpoint_sha256=sha(folder/'CHECKPOINT.json'),stale_last_development_fold=True)
