"""Fixed completed-day rejected breakout; equal-event opposite direction control."""
import importlib.util
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[2];DAY=86_400_000_000
SYMBOLS=('BTCUSDT','ETHUSDT','SOLUSDT','XRPUSDT','DOGEUSDT')
def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
original=load('original_financing_reference',ROOT/'research/settled-funding-direction-20261012/core.py')
risk=original.risk;reference=original.reference;paired_ci=original.paired_ci

def rejection(high,low,close,ready):
    """21 ordered actual candles: prior20 channel, last completed event candle."""
    h,l,c=map(lambda x:np.asarray(x,float),(high,low,close));r=np.asarray(ready,bool)
    if h.shape!=(21,) or l.shape!=(21,) or c.shape!=(21,) or r.shape!=(21,):raise ValueError('Exactly21 past completed candles required')
    valid=r.all() and np.isfinite(h).all() and np.isfinite(l).all() and np.isfinite(c).all() and (l>0).all() and np.all(l<=c) and np.all(c<=h)
    if not valid:return 0,'UNKNOWN_SOURCE'
    upper=float(h[:-1].max());lower=float(l[:-1].min());inside=lower<c[-1]<upper
    up=bool(h[-1]>upper and inside);down=bool(l[-1]<lower and inside)
    if up and down:return 0,'BOTH_SIDES_ORDER_UNKNOWN'
    if up:return -1,'UPPER_BREAK_REJECTED'
    if down:return 1,'LOWER_BREAK_REJECTED'
    return 0,'NO_REJECTED_BREAK'

def targets(available,high,low,close,ready,risk_t,risk_p,decisions):
    t=np.asarray(available,np.int64);d=np.asarray(decisions,np.int64)
    assert np.all(np.diff(t)==DAY) and high.shape==low.shape==close.shape==ready.shape==(len(t),5)
    out={a:np.zeros((len(d),5)) for a in ('FADE','FOLLOW')};proof=[]
    for i,at in enumerate(d):
        k=int(np.searchsorted(t,at));assert k>=20 and k<len(t) and t[k]==at
        direction=np.zeros(5);reasons=[]
        for j in range(5):direction[j],reason=rejection(high[k-20:k+1,j],low[k-20:k+1,j],close[k-20:k+1,j],ready[k-20:k+1,j]);reasons.append(reason)
        q=int(np.searchsorted(risk_t,at));assert q>=30 and q<len(risk_t) and risk_t[q]==at
        p=risk_p[q-30:q+1];assert np.isfinite(p).all() and (p>0).all(),'Unknown risk context never imputed'
        returns=np.diff(p,axis=0)/p[:-1];cov=np.cov(returns,rowvar=False,ddof=1)*365
        out['FADE'][i],a=risk.scale(.12*direction,cov);out['FOLLOW'][i],b=risk.scale(-.12*direction,cov)
        np.testing.assert_array_equal(out['FADE'][i],-out['FOLLOW'][i]);assert a['post_sigma']==b['post_sigma'] and a['gross']==b['gross']
        proof.append(dict(decision_us=int(at),event_bar_available_us=int(t[k]),prior_channel_last_available_us=int(t[k-1]),reasons=reasons,FADE=a,FOLLOW=b))
    return out,proof
