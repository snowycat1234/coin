"""One fitted joint correlation scalar; exact native diagonal, no wallet."""
from datetime import datetime, timezone
import numpy as np
from scripts.investment.public_sma_perpetual import signed_risk_weights

DAY = 86_400_000_000
SYMBOLS = ('BTCUSDT','ETHUSDT','SOLUSDT','XRPUSDT','DOGEUSDT')
PAIRS = np.triu_indices(5, 1)


def utc(s):
    return int(datetime.fromisoformat(s).replace(tzinfo=timezone.utc).timestamp())*1_000_000


def correlation(c):
    c=np.asarray(c,dtype=float)
    if c.shape[-2:] != (5,5) or not np.isfinite(c).all():
        raise ValueError('Complete ordered5 covariance required')
    d=np.diagonal(c,axis1=-2,axis2=-1)
    if np.any(d<=0): raise ValueError('Positive diagonal required')
    if not np.allclose(c,np.swapaxes(c,-1,-2),rtol=1e-12,atol=1e-15):
        raise ValueError('Symmetric covariance required')
    if np.min(np.linalg.eigvalsh(c)) < -1e-12:
        raise ValueError('PSD covariance required')
    s=np.sqrt(d)
    return c/s[..., :,None]/s[..., None,:]


def inputs(close, realized, i, symbols=SYMBOLS):
    if tuple(symbols)!=SYMBOLS: raise ValueError('Explicit symbol coordinates required')
    if i<30 or i>=len(close) or len(realized)!=len(close):
        raise ValueError('Thirty mature returns required')
    p=np.asarray(close[i-30:i+1],dtype=float)
    c=np.asarray(realized[i-29:i+1],dtype=float)
    if p.shape!=(31,5) or c.shape!=(30,5,5) or not np.isfinite(p).all() or np.any(p<=0):
        raise ValueError('Complete past price/covariance required')
    simple=np.diff(p,axis=0)/p[:-1]
    native=np.cov(simple,rowvar=False,ddof=1)
    return simple,native,correlation(native),correlation(c.sum(axis=0))


def fit(close,realized,clock,first,last,fit_at,symbols=SYMBOLS):
    if tuple(symbols)!=SYMBOLS: raise ValueError('Explicit symbol coordinates required')
    t=np.asarray(clock)
    if t.dtype.kind not in 'iu' or not np.all(np.diff(t)==DAY):
        raise ValueError('Continuous unique UTC clocks required')
    ids=np.flatnonzero((t>=first)&(t<=last))
    if len(ids)<30 or ids[-1]+1>=len(t) or t[ids[-1]+1]>=fit_at:
        raise ValueError('Mature training labels strictly before fit time required')
    xs=[];ys=[]
    for i in ids:
        _,_,a,b=inputs(close,realized,int(i),symbols)
        y=correlation(realized[i+1])
        xs.append((b-a)[PAIRS]);ys.append((y-a)[PAIRS])
    x=np.asarray(xs);y=np.asarray(ys)
    denominator=float(np.sum(x*x))
    if denominator<=0: raise ValueError('Identifiable scalar required')
    unconstrained=float(np.sum(x*y)/denominator)
    longrun=correlation(realized[ids+1].sum(axis=0))
    return dict(symbol_order=list(SYMBOLS),theta=float(np.clip(unconstrained,0,1)),
        unconstrained_theta=unconstrained,parameters=1,training_joint_dates=len(ids),
        first_decision_us=int(t[ids[0]]),last_decision_us=int(t[ids[-1]]),
        latest_label_maturity_us=int(t[ids[-1]+1]),fit_at_us=int(fit_at),
        train_longrun_correlation=longrun.tolist(),normalization_fits=0,
        LS_denominator=denominator,LS_numerator=float(np.sum(x*y)))


def forecast(close,realized,i,model,symbols=SYMBOLS):
    if tuple(model['symbol_order'])!=tuple(symbols) or tuple(symbols)!=SYMBOLS:
        raise ValueError('Explicit model coordinates required')
    simple,native,a,b=inputs(close,realized,i,symbols)
    theta=model['theta']
    if not 0<=theta<=1: raise ValueError('Convex theta required')
    mix=(1-theta)*a+theta*b
    s=np.sqrt(np.diag(native))
    covariance=mix*s[:,None]*s[None,:]
    return dict(NATIVE30=a,JOINT_BLEND30=mix,PURE_REALIZED30=b,
        LAST_DAY_REALIZED=correlation(realized[i]),
        TRAIN_LONGRUN=np.asarray(model['train_longrun_correlation'])),covariance,simple


def size(base,covariance,past_simple):
    base=np.asarray(base,dtype=float)
    if base.shape!=(5,) or not np.isfinite(base).all(): raise ValueError('Ordered base required')
    correlation(covariance)
    sigma=float(np.sqrt(max(0,float(base@covariance@base)*365)))
    scalar=min(1.,.10/sigma) if sigma else 1.
    w,receipt=signed_risk_weights(base*scalar,past_simple)
    if not np.allclose(w,base*scalar,atol=1e-12,rtol=1e-12):
        raise ValueError('BASE was not already native-risk controlled')
    if np.any(np.abs(w)>np.abs(base)+1e-12): raise ValueError('No relever permitted')
    return w,scalar,sigma,receipt


def losses(predicted,actual):
    p=np.asarray(predicted);a=np.asarray(actual)
    if p.shape!=a.shape or p.shape[1:]!=(5,5): raise ValueError('Joint daily matrices required')
    return np.mean(np.square((p-a)[:,PAIRS[0],PAIRS[1]]),axis=1)


def bootstrap(delta,block=7,seed=811132,draws=1000):
    x=np.asarray(delta,dtype=float)
    if x.ndim!=1 or len(x)<block or not np.isfinite(x).all():
        raise ValueError('Joint-date finite differences required')
    rng=np.random.default_rng(seed);n=len(x)
    starts=rng.integers(0,n,(draws,(n+block-1)//block))
    ids=((starts[:,:,None]+np.arange(block))%n).reshape(draws,-1)[:,:n]
    return np.quantile(x[ids].mean(axis=1),[.025,.975]).tolist()
