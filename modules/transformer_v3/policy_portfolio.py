import numpy as np
from modules.transformer_v2.portfolio import market_neutral

def policy_directional(probabilities,sma,active,gross):
    if probabilities.shape!=(*sma.shape,3) or active.shape!=sma.shape:raise ValueError('Policy asset identity mismatch')
    if not np.isfinite(probabilities).all() or (probabilities<0).any() or not np.allclose(probabilities.sum(-1),1.,atol=1e-6):raise ValueError('Policy probabilities invalid')
    if gross not in (.3,.6):raise ValueError('Only preregistered FULL/HALF gross profiles')
    probabilities=probabilities.astype('float64');probabilities=probabilities/probabilities.sum(-1,keepdims=True)
    signal=probabilities[...,0]*np.where(np.isfinite(sma),sma,0.)+probabilities[...,1]
    return signal*active*gross/np.maximum(active.sum(-1,keepdims=True),1)

def policy_targets(pred,sma,active,mapping,profile):
    if profile not in ('FULL','HALF'):raise ValueError('Unregistered risk profile')
    gross=.6 if profile=='FULL' else .3
    direct=policy_directional(pred['policy_probability'],sma,active,gross)
    neutral=market_neutral(pred['relative'][...,1],active,k=2,gross=gross)
    return dict(DIRECTIONAL=direct,NEUTRAL=neutral,COMBINED=.5*(direct+neutral))[mapping]
