"""Thin causal features and pinball LP adapter; no neural/financial kernel."""
import numpy as np
from scipy.optimize import linprog
from scripts.investment.public_sma_perpetual import signed_risk_weights

SYMBOLS=("BTCUSDT","ETHUSDT","SOLUSDT","XRPUSDT","DOGEUSDT")
DAY=86400000000
Q=.90


def summarize(prices,available,symbols=SYMBOLS):
    p=np.asarray(prices,float);t=np.asarray(available)
    if tuple(symbols)!=SYMBOLS or p.shape!=(len(t),5) or len(t)%288 or t.dtype.kind not in 'iu' or np.any(np.diff(t)!=300000000):
        raise ValueError('Dense5minute clocks and exactordered CORE5 required')
    if not np.isfinite(p).all() or (p<=0).any() or np.any(t[287::288]%DAY):
        raise ValueError('Finite actual prices and completedUTCday clocks required')
    logs=np.log(p)
    r=np.vstack([np.full((1,5),np.nan),np.diff(logs,axis=0)]).reshape(-1,288,5)
    close=p.reshape(-1,288,5)[:,-1]
    previous=np.vstack([np.full((1,5),np.nan),np.log(close[:-1])])
    excursion=np.maximum(0,(logs.reshape(-1,288,5)-previous[:,None,:]).max(1))
    rsplus=np.where(r>=0,np.square(r),0).sum(1)
    rsplus[0]=np.nan
    return dict(available=t[287::288],close=close,RV=np.square(r).sum(1),RSplus=rsplus,excursion=excursion)


def feature(p,i):
    if i<30 or i>=len(p['available']):
        raise ValueError('Causal30day warmup missing')
    rv=p['RV'][i-29:i+1]
    recent=p['excursion'][i-4:i+1]
    if not np.isfinite(rv).all() or (rv<=0).any() or not np.isfinite(recent).all():
        raise ValueError('Unknown completed past risk inputs')
    sigma=np.sqrt(rv.mean(0))
    x=np.column_stack([p['RSplus'][i-4:i+1].sum(0)/p['RV'][i-4:i+1].sum(0),
        recent.mean(0)/sigma,np.log(p['close'][i]/p['close'][i-21])/(np.sqrt(21)*sigma)])
    if not np.isfinite(x).all():
        raise ValueError('Unknown features')
    return x,sigma


def pinball(y,pred,q=Q):
    e=np.asarray(y)-np.asarray(pred)
    return np.maximum(q*e,(q-1)*e)


def fit_quantile(x,y,q=Q):
    x=np.asarray(x,float);y=np.asarray(y,float)
    if x.ndim!=2 or y.shape!=(len(x),) or not 0<q<1 or not np.isfinite(np.r_[x.ravel(),y]).all():
        raise ValueError('Finite training-only LP required')
    n,k=x.shape
    a=np.column_stack([x,np.eye(n),-np.eye(n)])
    cost=np.r_[np.zeros(k),np.full(n,q),np.full(n,1-q)]
    result=linprog(cost,A_eq=a,b_eq=y,bounds=[(None,None)]*k+[(0,None)]*(2*n),method='highs-ds',options={'time_limit':10,'maxiter':10000})
    if not result.success:
        raise RuntimeError('Frozen quantile solver failed: '+str(result.status))
    beta=result.x[:k];dual=result.eqlin.marginals
    primal_error=float(np.max(abs(a@result.x-y)))
    free_dual_error=float(np.max(abs(x.T@dual)))
    objective_error=abs(float(pinball(y,x@beta,q).sum()-result.fun))
    if primal_error>1e-7 or free_dual_error>1e-6 or objective_error>1e-6 or np.min(dual)<q-1-1e-7 or np.max(dual)>q+1e-7:
        raise ValueError('Quantile primal/dual certificate failed')
    return dict(coefficients=beta.tolist(),normalized_pinball_sum=float(result.fun),primal_error=primal_error,
        free_dual_error=free_dual_error,objective_error=objective_error,iterations=int(result.nit),status=int(result.status),
        residual_positive=result.x[k:k+n].tolist(),residual_negative=result.x[k+n:].tolist(),dual=dual.tolist())


def calibrate(p,indices,cutoff):
    ix=np.asarray(indices,dtype=int)
    if len(ix)!=211 or np.any(np.diff(ix)!=1) or np.any(ix+1>=len(p['available'])) or np.any(p['available'][ix+1]>cutoff):
        raise ValueError('All211training labels must be mature before fit')
    features=[];sigma=[]
    for i in ix:
        x,s=feature(p,int(i));features.append(x);sigma.append(s)
    features=np.asarray(features);sigma=np.asarray(sigma)
    actual=p['excursion'][ix+1]
    if not np.isfinite(actual).all():
        raise ValueError('Unknown mature training labels')
    models=[]
    for j,symbol in enumerate(SYMBOLS):
        raw=features[:,j,:];mean=raw.mean(0);std=raw.std(0,ddof=0)
        if (std<=1e-12).any():
            raise ValueError('Degenerate frozen features; no replacement')
        x=np.column_stack([np.ones(len(ix)),(raw-mean)/std])
        y=actual[:,j]/sigma[:,j]
        model=fit_quantile(x,y)
        models.append(dict(symbol=symbol,mean=mean.tolist(),std=std.tolist(),LP=model,
            empirical_scaled=float(np.quantile(y,Q)),empirical_unconditional=float(np.quantile(actual[:,j],Q))))
    return dict(models=models,quantile=Q,training_rows=211,train_indices=ix.tolist(),fit_label_cutoff_us=int(cutoff),
        maximum_training_label_mature_us=int(p['available'][ix+1].max()),historical_fits=5)


def forecast(p,i,model):
    raw,sigma=feature(p,i)
    result=np.zeros(5);vol=np.zeros(5);constant=np.zeros(5)
    if tuple(m['symbol'] for m in model['models'])!=SYMBOLS:
        raise ValueError('Forecast model identity order mismatch')
    for j,m in enumerate(model['models']):
        x=np.r_[1.,(raw[j]-m['mean'])/m['std']]
        result[j]=max(1e-6,float(x@np.asarray(m['LP']['coefficients'])))*sigma[j]
        vol[j]=m['empirical_scaled']*sigma[j]
        constant[j]=m['empirical_unconditional']
    return dict(CONDITIONAL=result,VOL_SCALED=vol,UNCONDITIONAL=constant)


def bootstrap(deltas):
    d=np.asarray(deltas,float)
    if d.ndim!=2 or d.shape[1]!=2 or not np.isfinite(d).all():
        raise ValueError('Common jointdate pairedlosses required')
    rng=np.random.default_rng(811131)
    draws=[]
    for _ in range(1000):
        starts=rng.integers(0,len(d),size=(len(d)+6)//7)
        ix=((starts[:,None]+np.arange(7))%len(d)).ravel()[:len(d)]
        draws.append(d[ix].mean(0))
    return np.quantile(draws,[.025,.975],axis=0).T


def downsize(base,scale,past_returns):
    w=np.asarray(base,float).copy();scale=np.asarray(scale,float)
    if w.shape!=(5,) or scale.shape!=(5,) or not np.isfinite(np.r_[w,scale]).all() or (scale<0).any() or (scale>1).any():
        raise ValueError('Only ordered short-downsize required')
    w[w<0]*=scale[w<0]
    w,risk=signed_risk_weights(w,past_returns,annual_vol_target=.10)
    if np.any(abs(w)>abs(base)+1e-12) or np.any(w*np.asarray(base)<0):
        raise ValueError('No sign flip or upscaling permitted')
    return w,risk
