import numpy as np

def directional(utility,sma,active,gross=.6):
    assert utility.shape==(*sma.shape,2) and active.shape==sma.shape
    scores=np.stack([utility[...,0],np.zeros_like(sma),utility[...,1]],-1)
    scores=(scores-scores.max(-1,keepdims=True))/.02
    mix=np.exp(scores);mix/=mix.sum(-1,keepdims=True)
    position=(mix[...,0]*np.where(np.isfinite(sma),sma,0.)+mix[...,1])*active
    return position*(gross/np.maximum(active.sum(-1,keepdims=True),1))

def market_neutral(score,active,k=2,gross=.6):
    assert score.shape==active.shape and k==2
    weights=np.zeros_like(score,dtype=float)
    for j in range(len(score)):
        indices=np.flatnonzero(active[j]&np.isfinite(score[j]))
        if len(indices)<2*k:continue
        ranked=indices[np.argsort(score[j,indices],kind='stable')]
        # A fully tied score has no relative-strength signal: retain cash.
        if np.ptp(score[j,indices])<=1e-12:continue
        weights[j,ranked[-k:]]=gross/(2*k);weights[j,ranked[:k]]=-gross/(2*k)
    assert np.max(abs(weights),initial=0)<=.30+1e-12
    assert np.max(abs(weights.sum(1)),initial=0)<1e-12
    assert np.max(abs(weights).sum(1),initial=0)<=.60+1e-12
    return weights
