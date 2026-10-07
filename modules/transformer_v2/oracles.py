"""Future-informed diagnostics with each oracle's own registered information horizon."""
import numpy as np
from .portfolio import market_neutral

def weights(name,utility,relative,close,indices,active,sma):
    if name=='EXPERT_ORACLE':
        valid=active&np.isfinite(utility).all(-1)&np.isfinite(sma)
        u=np.where(np.isfinite(utility),utility,0.)
        expert=np.argmax(np.stack([u[...,0],np.zeros_like(u[...,0]),u[...,1]],-1),-1)
        position=np.where(expert==0,np.where(np.isfinite(sma),sma,0.),np.where(expert==1,1.,0.))
    elif name=='CROSS_SECTIONAL_RANK_ORACLE':
        valid=active&np.isfinite(relative[...,1])
        return market_neutral(relative[...,1],valid),valid
    elif name=='DIRECTIONAL_ORACLE':
        valid=np.zeros_like(active);position=np.zeros_like(active,dtype=float)
        for j,i in enumerate(indices):
            if i+30>=len(close):continue
            seen=active[j]&np.isfinite(close[i:i+31]).all(0)&(close[i:i+31]>0).all(0)
            valid[j]=seen;position[j,seen]=np.sign(close[i+30,seen]/close[i,seen]-1)
    else:raise ValueError('Unknown registered oracle')
    # Unknown future information produces explicit cash, never a fabricated return.
    budget=np.minimum(.3,.6/np.maximum(valid.sum(1,keepdims=True),1))
    out=position*valid*budget
    assert abs(out).max(initial=0)<=.3+1e-9 and abs(out).sum(1).max(initial=0)<=.6+1e-9
    return out,valid
