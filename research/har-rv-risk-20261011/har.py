"""Fixed causal HAR variance forecasts and scalar-only portfolio risk adapter."""
import numpy as np

DAY = 86_400_000_000
SYMBOLS = ("BTCUSDT","ETHUSDT","SOLUSDT","XRPUSDT","DOGEUSDT")


def feature(rv,index):
    if index<29:
        return None
    past=np.asarray(rv[index-29:index+1],float)
    if past.shape!=(30,5) or not np.isfinite(past).all() or (past<=0).any():
        return None
    return np.column_stack([np.ones(5),np.log(past[-1]),np.log(past[-7:].mean(0)),np.log(past.mean(0))])


def calibrate(rv,available,start,last_decision,label_cutoff):
    from statsmodels.regression.linear_model import OLS
    rv,t=np.asarray(rv,float),np.asarray(available)
    if rv.shape!=(len(t),5) or t.dtype.kind not in "iu" or np.any(np.diff(t)!=DAY):
        raise ValueError("Dense actual dailyRV and availability required")
    indices=np.flatnonzero((t>=start)&(t<=last_decision))
    if len(indices)<100 or indices[-1]+1>=len(t) or np.any(t[indices+1]>label_cutoff):
        raise ValueError("Mature nonoverlapping training labels before frozen cutoff required")
    features=[feature(rv,int(i)) for i in indices]
    if any(x is None for x in features) or not np.isfinite(rv[indices+1]).all():
        raise ValueError("Missing training RV is not silently removed")
    x=np.stack(features)
    coef,smear=[],[]
    for j in range(5):
        fit=OLS(np.log(rv[indices+1,j]),x[:,j,:]).fit()
        coef.append(fit.params.tolist())
        smear.append(float(np.exp(fit.resid).mean()))
    return dict(symbol_order=list(SYMBOLS),coefficients=coef,smearing=smear,
        observations_per_asset=len(indices),latest_input_us=int(t[indices[-1]]),
        latest_label_maturity_us=int(t[indices[-1]+1]),parameter_fits=5)


def forecast(rv,index,model,symbols=SYMBOLS):
    if tuple(symbols)!=SYMBOLS or model["symbol_order"]!=list(SYMBOLS):
        raise ValueError("Exact CORE5 forecast coordinates required")
    x=feature(rv,index)
    if x is None:
        return None
    value=np.exp((x*np.asarray(model["coefficients"])).sum(1))*np.asarray(model["smearing"])
    if not np.isfinite(value).all() or (value<=0).any():
        raise ValueError("Invalid positive HAR variance forecast")
    return value


def haircut(base,variance,past_simple_returns):
    w,v,r=map(lambda x:np.asarray(x,float),(base,variance,past_simple_returns))
    if w.shape!=(5,) or v.shape!=(5,) or r.shape!=(30,5) or not np.isfinite(np.r_[w,v,r.ravel()]).all() or (v<=0).any():
        raise ValueError("Finite ordered base,variance and30past returns required")
    if abs(w).max()>.3+1e-12 or abs(w).sum()>.6+1e-12:
        raise ValueError("Frozen account caps required")
    correlation=np.corrcoef(r,rowvar=False)
    covariance=np.sqrt(v)[:,None]*correlation*np.sqrt(v)[None,:]*365
    variance=float(w@covariance@w)
    if not np.isfinite(variance) or variance<-1e-14:
        raise ValueError("Unknown/invalid signed forecast covariance")
    sigma=float(np.sqrt(max(variance,0.)))
    scale=min(1.,.10/max(sigma,1e-30))
    return scale,dict(forecast_annual_sigma=sigma,scalar=scale,relative_legs_preserved=True,
        correlation_scope="past30daily simple correlation, not predicted correlation")


def qlike(actual,predicted):
    actual,predicted=map(lambda x:np.asarray(x,float),(actual,predicted))
    if actual.shape!=predicted.shape or not np.isfinite(np.r_[actual.ravel(),predicted.ravel()]).all() or (actual<=0).any() or (predicted<=0).any():
        raise ValueError("Common positive finite realised/forecast variance required")
    ratio=actual/predicted
    return ratio-np.log(ratio)-1


def bootstrap(deltas):
    a=np.asarray(deltas,float)
    if a.ndim!=2 or a.shape[1]!=2 or not np.isfinite(a).all():
        raise ValueError("Joint-day two-baseline paired losses required")
    rng=np.random.default_rng(811130)
    values=[]
    for _ in range(1000):
        starts=rng.integers(0,len(a),size=(len(a)+6)//7)
        ix=((starts[:,None]+np.arange(7))%len(a)).ravel()[:len(a)]
        values.append(a[ix].mean(0))
    return np.quantile(values,[.025,.975],axis=0).T
