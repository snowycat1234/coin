"""Mature training-only teachers; reuse protected cost-aware 60-day expert labels.

Expert utility is the existing continuous daily-expert proxy, not a claim of
minute-wallet equivalence or native Bybit liquidation-certified teacher data.
"""
from pathlib import Path
import json
import numpy as np
import pandas as pd
from modules.transformer_v2.data import load_development
from modules.transformer_v2.train import sha

LOCKED_START=pd.Timestamp('2026-03-01',tz='UTC')
ACTIONS=('SMA','HOLD','CASH')

def future_direction(close,available,horizon=30):
    n,a=close.shape;result=np.full((n,a),np.nan,dtype='float32')
    for i in range(n-horizon):
        section=close[i:i+horizon+1]
        valid=available[i]&np.isfinite(section).all(0)&(section>0).all(0)
        result[i,valid]=section[-1,valid]/section[0,valid]-1
    return result

def robust_gap_scale(utilities,valid):
    ordered=np.sort(utilities[valid],axis=-1)
    gaps=ordered[:,-1]-ordered[:,-2] if len(ordered) else np.array([])
    positive=gaps[np.isfinite(gaps)&(gaps>0)]
    return float(np.median(positive)) if len(positive) else 1.

def training_teacher_view(d,indices,cutoff,active):
    """Purge full 60d labels before a cutoff already carrying the 60d embargo."""
    indices=np.asarray(indices,dtype=int);cutoff=pd.Timestamp(cutoff)
    if cutoff>LOCKED_START:raise ValueError('Training teacher cutoff crosses locked boundary')
    if not (d['label_end'][indices]<cutoff).all():raise ValueError('Unmature expert horizon or missing purge')
    if not ((d['dates'][indices]+pd.Timedelta(days=31))<cutoff).all():raise ValueError('Unmature direction/rank horizon')
    ready=d['ready'][indices]&np.asarray(active)[None,:]
    utilities=[u[indices] for u in d['expert_utilities']]
    masks=[ready&np.isfinite(u).all(-1) for u in utilities]
    return dict(indices=indices,expert_utilities=utilities,expert_valid=masks,
                direction_return=d['direction30'][indices],direction_valid=ready&np.isfinite(d['direction30'][indices]),
                relative=d['relative'][indices],relative_valid=ready[...,None]&np.isfinite(d['relative'][indices]),
                gap_scales=[robust_gap_scale(u,m) for u,m in zip(utilities,masks)],
                teachers_are_training_targets_only=True,cutoff=cutoff.isoformat())

def load_teacher_development(collector_root,work,source_run):
    d=load_development(collector_root,work,source_run)
    d['direction30']=future_direction(d['close'],d['ready'])
    d['expert_utilities']=[];receipts=[]
    for scenario,tag in enumerate(('raw_fraction','raw_percent')):
        base=Path(work)/'data/labels'/tag;manifest=base/'LABEL_MANIFEST.json'
        m=json.loads(manifest.read_text())
        if m['horizon']!=60:raise ValueError('Expert teacher must use exactly 60 complete future days')
        files={r['symbol']:r for r in m['files']};values=[]
        for symbol in d['symbols']:
            p=base/(symbol+'.parquet')
            if sha(p)!=files[symbol]['sha256']:raise ValueError('Protected expert labels changed: '+symbol)
            frame=pd.read_parquet(p)
            if not pd.DatetimeIndex(frame.dt).equals(d['dates']):raise ValueError('Expert teacher calendar mismatch')
            if not pd.DatetimeIndex(frame.label_end_at).equals(d['label_end']):raise ValueError('Expert maturity clock changed')
            u=frame[['u_sma','u_hold','u_cash']].to_numpy('float32')
            # Same input labels used by v2, but now direct action supervision.
            difference=np.stack((u[:,0]-u[:,1],u[:,2]-u[:,1]),-1)
            if not np.allclose(difference,d['utility'][scenario][:,len(values)],equal_nan=True,rtol=1e-5,atol=1e-7):
                raise ValueError('Expert teacher differs from protected v2 utility identity')
            values.append(u)
        d['expert_utilities'].append(np.stack(values,1))
        receipts.append(dict(scenario=tag,manifest_sha256=sha(manifest),files=m['files'],
                             source_manifest_sha256=m['source_manifest_sha256'],horizon=60,
                             semantics=m['label_semantics'],minute_wallet_equivalent=False))
    d['teacher_receipts']=receipts
    return d
