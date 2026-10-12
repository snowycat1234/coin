import numpy as np
DAY=86_400_000_000

def held_complete(own,interval_good,price_good,current_mark,next_mark):
    own=np.asarray(own,bool)
    return bool(own.any() and np.all((np.asarray(interval_good,bool)&np.asarray(price_good,bool)&np.asarray(current_mark,bool)&np.asarray(next_mark,bool))[own]))

def policy_features(decisions,releases,upper,market21):
    d=np.asarray(decisions,np.int64);r=np.asarray(releases,np.int64);u=np.asarray(upper,float)
    if len(r)!=len(u) or np.any(np.diff(r)<=0) or not np.isfinite(u).all():raise ValueError('Ordered actual policy releases')
    a=np.searchsorted(r,d,side='right')-1;b=np.searchsorted(r,d-90*DAY,side='right')-1
    if np.any((a<0)|(b<0)):raise ValueError('Policy warmup cannot use future release')
    change=u[a]-u[b]
    return np.column_stack([u[a],change,change*np.minimum(market21,0.)]),r[a]

def predict(x,models,arm):
    z=(x-models[arm+'_mean'])/models[arm+'_scale']
    return np.einsum('nf,f->n',z,models[arm+'_coef'],optimize=False)+models[arm+'_intercept']

def retention(prediction,scale,known):
    if not np.isfinite(scale) or scale<=0:raise ValueError('Positive frozen training utility scale')
    desired=np.where(known,1/(1+np.exp(-np.clip(np.asarray(prediction)/scale,-30,30))),0.)
    previous=0.;out=np.empty(len(desired))
    for i,g in enumerate(desired):
        previous+=np.clip(g-previous,-.05,.05);out[i]=previous if known[i] else 0.
        if not known[i]:previous=0.
    return out

def bootstrap(difference,mask,seed=811501):
    x=np.where(mask,difference,np.nan);n=len(x);rng=np.random.default_rng(seed)
    starts=rng.integers(0,n,(1000,int(np.ceil(n/14))))
    ix=((starts[:,:,None]+np.arange(14))%n).reshape(1000,-1)[:,:n]
    return np.quantile(np.nanmean(x[ix],axis=1),[.025,.975]).tolist()
