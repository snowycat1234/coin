import json,os,sys
from pathlib import Path
import numpy as np
import pandas as pd

HORIZONS=(7,30,60)

def chronological_inner(indices,dates,label_end,embargo=60):
    indices=np.asarray(sorted(set(indices)),dtype=int)
    cut=indices[int(len(indices)*.8)]
    boundary=dates[cut]-pd.Timedelta(days=embargo)
    train=indices[(indices<cut)&(label_end[indices]<boundary)]
    valid=indices[indices>=cut]
    assert len(train) and len(valid) and (label_end[train]<boundary).all()
    return train,valid

def train_scaler(features,availability,indices,length=256):
    rows=np.zeros(len(features),bool)
    for i in indices:rows[max(0,i-length+1):i+1]=True
    seen=np.isfinite(features)&availability[...,None]&rows[:,None,None]
    count=seen.sum((0,1));assert np.all(count>0),'Feature has no past training observation'
    mu=np.where(seen,features,0.).sum((0,1))/count
    sd=np.sqrt(np.where(seen,(features-mu)**2,0.).sum((0,1))/count)
    sd=np.where(sd>1e-8,sd,1.)
    return mu.astype('float32'),sd.astype('float32')

def causal_future_targets(close,availability,horizons=HORIZONS):
    n,a=close.shape;relative=np.full((n,a,len(horizons)),np.nan);regime=np.full((n,len(horizons)),np.nan)
    for hi,h in enumerate(horizons):
        for i in range(n-h):
            # All intermediate observations are required; no price bridging a gap.
            valid=availability[i]&np.isfinite(close[i:i+h+1]).all(0)&(close[i:i+h+1]>0).all(0)
            if valid.sum()<4:continue
            own=close[i+h,valid]/close[i,valid]-1
            relative[i,valid,hi]=own-own.mean()
            daily=np.diff(np.log(close[i:i+h+1,valid]),axis=0).mean(1)
            regime[i,hi]=np.log(max(float(np.std(daily,ddof=1)),1e-6))
    return relative.astype('float32'),regime.astype('float32')

def load_development(collector_root,work,source_run):
    root=Path(collector_root);work=Path(work);source=Path(source_run)
    binding=json.loads((source/'BINDING.json').read_text());os.environ.update(binding['config']);os.environ.update(binding.get('extra_knobs',{}))
    os.environ.update(WORK_DIR=str(work),CONFIG_FILE=str(root/'config.env'));sys.path.insert(0,str(root))
    from pipeline.train import market_features,folds_for,BASE_FEATURES
    symbols=binding['symbols'];labels={};utility=[]
    for tag in ('raw_fraction','raw_percent'):
        own={s:pd.read_parquet(work/'data/labels'/tag/(s+'.parquet')).reset_index(drop=True) for s in symbols}
        utility.append(np.stack([own[s][['y_sma_vs_hold','y_cash_vs_hold']].to_numpy('float32') for s in symbols],1))
        labels[tag]=own
    primary=labels['raw_fraction'];dates=pd.DatetimeIndex(primary[symbols[0]].dt)
    assert dates.max()<pd.Timestamp('2026-03-01',tz='UTC'),'Development attempted locked read'
    assert all(pd.DatetimeIndex(d.dt).equals(dates) for own in labels.values() for d in own.values())
    market=market_features(primary).reset_index(drop=True)
    x=np.stack([pd.concat([primary[s][BASE_FEATURES],market],axis=1).to_numpy('float32') for s in symbols],1)
    close=np.stack([primary[s].close.to_numpy(float) for s in symbols],1)
    available=np.isfinite(close);ready=np.stack([primary[s].feature_ready.to_numpy(bool) for s in symbols],1)
    relative,regime=causal_future_targets(close,ready)
    label_end=dates+pd.Timedelta(days=61)+pd.Timedelta(microseconds=60_000_001)
    folds=list(folds_for(dates,primary,256,180,60));assert len(folds)==5
    sma=np.stack([primary[s].sma_signal.to_numpy(float) for s in symbols],1)
    return dict(symbols=symbols,dates=dates,x=x,availability=available,ready=ready,close=close,utility=utility,
                relative=relative,regime=regime,label_end=label_end,folds=folds,sma=sma,features=BASE_FEATURES+list(market.columns))
