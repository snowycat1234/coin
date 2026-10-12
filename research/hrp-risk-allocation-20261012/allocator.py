"""One fixed PyPortfolioOpt HRP allocation, preserving direction and past-only risk."""
import numpy as np
import pandas as pd
from scipy.cluster import hierarchy
from scipy.spatial.distance import squareform
from pypfopt.hierarchical_portfolio import HRPOpt
from pypfopt import risk_models
DAY=86_400_000_000
ARMS=('HRP_MATCHED','IVOL_MATCHED','IVAR_MATCHED','IVOL_ORIGINAL')
SYMBOLS=('BTCUSDT','ETHUSDT','SOLUSDT','XRPUSDT','DOGEUSDT')

def allocate(covariance,symbols):
    c=np.asarray(covariance,float);names=list(symbols);n=len(names)
    if c.shape!=(n,n) or not np.isfinite(c).all() or not np.allclose(c,c.T,rtol=0,atol=1e-14) or np.any(np.diag(c)<=0):raise ValueError('Finite ordered positive-variance covariance')
    if n==1:h=np.ones(1);link=np.empty((0,4));corr=np.ones((1,1));order=np.array([0])
    else:
        model=HRPOpt(cov_matrix=pd.DataFrame(c,index=names,columns=names))
        # Same upstream numerical pipeline; omit its obsolete private SciPy
        # method-enumeration guard. No production monkeypatch or optimizer fork.
        corr=risk_models.cov_to_corr(model.cov_matrix).round(6).to_numpy()
        distance=np.sqrt(np.clip((1-corr)/2,0,1))
        link=hierarchy.linkage(squareform(distance,checks=False),'single')
        order=np.asarray(HRPOpt._get_quasi_diag(link),np.int64)
        result=HRPOpt._raw_hrp_allocation(model.cov_matrix,[names[i] for i in order])
        h=np.array([result[s] for s in names])
    ivol=1/np.sqrt(np.diag(c));ivol/=ivol.sum()
    if not np.isfinite(h).all() or np.any(h<=0) or abs(h.sum()-1)>1e-12:raise ValueError('Native HRP positive normalized weights')
    ivar=1/np.diag(c);ivar/=ivar.sum()
    rawh=np.minimum(.6*h,.3);rawi=np.minimum(.6*ivol,.3);rawv=np.minimum(.6*ivar,.3)
    sigma=lambda w:float(np.sqrt(max(0.,w@c@w*365.)))
    sh,si,sv=sigma(rawh),sigma(rawi),sigma(rawv)
    if min(sh,si,sv)<=0:raise ValueError('Nondegenerate risk context')
    common=min(.10,sh,si,sv)
    out=dict(HRP_MATCHED=rawh*(common/sh),IVOL_MATCHED=rawi*(common/si),IVAR_MATCHED=rawv*(common/sv),IVOL_ORIGINAL=rawi*min(1.,.10/si))
    if any(np.abs(v).max()>.3+1e-12 or abs(v).sum()>.6+1e-12 for v in out.values()):raise ValueError('Same caps/no redistribution')
    if any(abs(sigma(out['HRP_MATCHED'])-sigma(out[a]))>1e-12 for a in ('IVOL_MATCHED','IVAR_MATCHED')):raise ValueError('Exact common ex-ante covariance risk')
    return out,dict(covariance=c,correlation_used=corr,distance_used=np.sqrt(np.clip((1-corr)/2,0,1)),linkage=link,leaf_order=order,
      normalized_HRP=h,normalized_IVOL=ivol,normalized_IVAR=ivar,raw_HRP=rawh,raw_IVOL=rawi,raw_IVAR=rawv,common_risk=common,post_risk={arm:sigma(w) for arm,w in out.items()})

def targets(clocks,close,decisions,available_assets):
    t=np.asarray(clocks,np.int64);d=np.asarray(decisions,np.int64);price=np.asarray(close,float);mask=np.asarray(available_assets,bool)
    if price.shape!=(len(t),5) or mask.shape!=(len(d),5) or np.any(np.diff(t)<=0):raise ValueError('Canonical actual price/mask shapes')
    weights={arm:np.zeros((len(d),5)) for arm in ARMS};proof=[];matrix=[]
    for j,at in enumerate(d):
        own=np.flatnonzero(mask[j]);k=int(np.searchsorted(t,at));reason='ELIGIBLE'
        if not len(own):reason='NO_CURRENT_AVAILABLE_ASSET'
        elif k<30 or k>=len(t) or t[k]!=at:reason='MISSING_CURRENT_OR_PAST_RISK_CLOCK'
        elif not np.all(np.diff(t[k-30:k+1])==DAY):reason='NONCONTINUOUS_PAST_RISK_CLOCK'
        elif not np.isfinite(price[k-30:k+1][:,own]).all() or np.any(price[k-30:k+1][:,own]<=0):reason='UNKNOWN_PAST_RISK_PRICE'
        if reason!='ELIGIBLE':proof.append(dict(decision_us=int(at),reason=reason,active_assets=own.tolist()));continue
        past=price[k-30:k+1][:,own];returns=np.diff(past,axis=0)/past[:-1]
        if (returns.std(0,ddof=1)<=0).any():proof.append(dict(decision_us=int(at),reason='ZERO_PAST_VARIANCE',active_assets=own.tolist()));continue
        covariance=np.atleast_2d(np.cov(returns,rowvar=False,ddof=1));out,p=allocate(covariance,[SYMBOLS[i] for i in own])
        for arm in ARMS:weights[arm][j,own]=out[arm]
        matrix.append(dict(decision_index=j,active_assets=own,**p))
        proof.append(dict(decision_us=int(at),reason='ELIGIBLE',active_assets=own.tolist(),first_price_available_us=int(t[k-30]),last_price_available_us=int(t[k]),past_completed_daily_returns=30,
            common_exante_annual_vol=p['common_risk'],post_exante_annual_vol=p['post_risk']))
    return weights,proof,matrix
