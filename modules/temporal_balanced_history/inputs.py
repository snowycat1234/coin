"""Explicit new real-terminal episodes; old frozen source contracts stay intact."""
from dataclasses import dataclass,replace
from pathlib import Path
import json
import numpy as np
import pandas as pd
from modules.temporal_two_expert.exact import Episode,load_prototype,sha
from modules.temporal_two_expert.inputs import CORE5,DAY_US,FeatureTimeline,digest,require_sha,fit_standardizer
from modules.temporal_two_expert.training_packet import named_context
from modules.temporal_short_expansion.adapter import append_episode
from modules.temporal_expert_input.inputs import expose_episode
CUTOFF=1714521600000000

@dataclass(frozen=True)
class RealEpisode(Episode):
    real_terminal_ABI=True
    def __post_init__(self):
        d=self.windows.decision_us;n=len(d)
        if self.role not in ('TRAIN','SEEN_VALIDATION') or n<2 or not np.array_equal(d,np.arange(self.start_us,self.end_us,DAY_US)) or len(self.contexts)!=n:
            raise ValueError('Complete explicit daily wallet required')
        if self.prices.shape!=(n,5) or self.funding_coeff.shape!=(n-1,5) or not np.isfinite(self.prices).all() or np.any(self.prices<=0) or not np.isfinite(self.funding_coeff).all():raise ValueError('Real execution and owned funding required')
        if not np.array_equal(self.label_available_us,np.r_[d[1:]+60000001,d[-1]+60000001]) or np.any(self.label_available_us>=self.split_cutoff_us) or self.end_us>self.split_cutoff_us:raise ValueError('Mature explicit labels before split')
        require_sha(self.producer_sha256);cs=[]
        for t,c in zip(d,self.contexts,strict=True):
            c.validate()
            if c.decision_us!=t or c.available_us>t:raise ValueError('Causal matching context')
            a={k:np.array(getattr(c,k),copy=True) for k in ['expert_targets','eligible','past_returns30','market13','target_available_us']}
            for v in a.values():v.flags.writeable=False
            cs.append(replace(c,**a))
        object.__setattr__(self,'contexts',tuple(cs))
        for k in ['prices','funding_coeff','label_available_us']:
            v=np.array(getattr(self,k),copy=True);v.flags.writeable=False;object.__setattr__(self,k,v)

    @property
    def identity(self):return digest(dict(real_terminal_ABI=True,original=super().identity))

def from_arrays(name,d,prices,funding,targets,eligible,past,feature,prototype,source,role='TRAIN'):
    clocks=feature['completed_day_available_us'];values=feature['x'];m=feature['feature_observed_mask'];obs=feature['close_observed_mask']
    selected=(clocks>=d[0]-63*DAY_US)&(clocks<=d[-1]);v=values[selected];t=clocks[selected]
    timeline=FeatureTimeline(v,m[selected],obs[selected],t,np.broadcast_to(t[:,None,None],v.shape).copy(),source)
    c=tuple(named_context(prototype,int(t),targets[i,:3],eligible[i,:3],past[i],np.zeros(13),np.full(3,t,dtype=np.int64)) for i,t in enumerate(d))
    cutoff=CUTOFF if role=='TRAIN' else int(d[-1]+2*DAY_US)
    e=RealEpisode(name,timeline.windows(d),c,prices,funding,np.r_[d[1:]+60000001,d[-1]+60000001],int(d[0]),int(d[-1]+DAY_US),cutoff,role,source)
    return expose_episode(append_episode(e,targets[:,3:4],eligible[:,3:4],d[:,None],prototype,source))

def training(state):
    state=Path(state);r=state/'data-expansion';f=np.load(r/'training1290/FEATURES.npz');a=np.load(r/'training1290/TARGETS.npz');p=load_prototype(state/'recovery/source/modules/direct_path/prototype.py');episodes=[];bindings={}
    for name,folder in [('Y2020',r/'early2020/economics2020'),('Y2021',state/'early2021')]:
        path=folder/'ECONOMICS.npz';b=np.load(path);d=b['decision_us'];ix=np.searchsorted(a['decision_us'],d);np.testing.assert_array_equal(a['decision_us'][ix],d);source=digest({'features':sha(r/'training1290/FEATURES.npz'),'targets':sha(r/'training1290/TARGETS.npz'),'economics':sha(path)})
        episodes.append(from_arrays(name,d,b['prices'],b['funding_coeff'],a['expert_targets'][ix],a['expert_eligible'][ix],a['past_returns30'][ix],f,p,source));bindings[name]=source
    folder=r/'gap-repair/repaired/economics';d=np.arange(1641081600000000,CUTOFF,DAY_US,dtype=np.int64);prices=[];fund=[];hs={}
    for s in CORE5:
        path=folder/f'{s}_daily.parquet';hs[s]=sha(path);b=pd.read_parquet(path).set_index('dt').loc[pd.to_datetime(d,unit='us',utc=True)];assert b.complete_kline.all() and b.funding_interval_complete.iloc[:-1].all();prices.append(b.exec_price.to_numpy(float));fund.append(b.mark_funding_per_unit.to_numpy(float)[:-1])
    source=digest({'features':sha(r/'training1290/FEATURES.npz'),'targets':sha(r/'training1290/TARGETS.npz'),'economics':hs});ix=np.searchsorted(a['decision_us'],d);np.testing.assert_array_equal(a['decision_us'][ix],d)
    episodes.append(from_arrays('Y2022_TO_APR2024',d,np.stack(prices,1),np.stack(fund,1),a['expert_targets'][ix],a['expert_eligible'][ix],a['past_returns30'][ix],f,p,source));bindings['Y2022_TO_APR2024']=source
    assert [len(e.contexts)-1 for e in episodes]==[77,364,849]
    scaler=fit_standardizer([e.windows for e in episodes],training_cutoff_us=CUTOFF)
    return tuple(episodes),p,scaler,bindings
