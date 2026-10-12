"""Direct causal cross-sectional rank fusion, no labels/selector/budget mixture."""
import numpy as np
from scipy.stats import rankdata
from modules.transformer_v2.portfolio import market_neutral
DAY=86400000000;SYMBOLS=('BTCUSDT','ETHUSDT','SOLUSDT','XRPUSDT','DOGEUSDT');ARMS=('SLOW','DUAL','SKIP')
def targets(clocks,close,decisions):
    t=np.asarray(clocks,np.int64);p=np.asarray(close,float);d=np.asarray(decisions,np.int64)
    if p.shape!=(len(t),5) or np.any(np.diff(t)!=DAY) or np.any(np.diff(d)!=DAY):raise ValueError('ExactCORE5/dailyclock identity')
    out={a:np.zeros((len(d),5)) for a in ARMS};score={a:np.full((len(d),5),np.nan) for a in ARMS};proof=[]
    for i,at in enumerate(d):
        k=int(np.searchsorted(t,at));valid=k>=30 and k<len(t) and t[k]==at and bool(np.isfinite(p[k-30:k+1]).all()) and bool((p[k-30:k+1]>0).all())
        if not valid:proof.append(dict(decision_us=int(at),status='CURRENT_UNREADY',cash=list(ARMS)));continue
        r21=p[k]/p[k-21]-1;r1=p[k]/p[k-1]-1;values=dict(SLOW=r21,DUAL=rankdata(r21,method='average')-rankdata(r1,method='average'),SKIP=p[k-1]/p[k-21]-1)
        raw={a:market_neutral(v[None,:],np.ones((1,5),bool),k=2,gross=.6)[0] for a,v in values.items()};r=np.diff(p[k-30:k+1],axis=0)/p[k-30:k];cov=np.cov(r,rowvar=False,ddof=1)*365
        sigma={a:float(np.sqrt(max(0.,w@cov@w))) for a,w in raw.items()};active=[s for s in sigma.values() if s>0];common=min([.10,*active]) if active else 0.
        for a in ARMS:
            out[a][i]=raw[a]*(common/sigma[a]) if sigma[a]>0 else 0.;score[a][i]=values[a]
        proof.append(dict(decision_us=int(at),status='READY',last_price_available_us=int(t[k]),past_returns=30,raw_sigma=sigma,common_sigma=common,cash=[a for a in ARMS if sigma[a]==0],exact_matched_when_all_active=all(s>0 for s in sigma.values())))
    for a in ARMS:assert np.isfinite(out[a]).all() and np.abs(out[a]).max()<=.3+1e-12 and np.abs(out[a]).sum(1).max()<=.6+1e-12
    return out,score,proof
