"""One temporal cross-sectional feature; one frozen two-mean predictor."""
import numpy as np
DAY=86400000000
SYMBOLS=('BTCUSDT','ETHUSDT','SOLUSDT','XRPUSDT','DOGEUSDT')

def ranks(x):
 x=np.asarray(x,float);assert x.shape==(5,) and np.isfinite(x).all()
 return np.array([np.sum(x<v)+(np.sum(x==v)-1)/2 for v in x],float)

def persistence(clock,close,decisions):
 t=np.asarray(clock,np.int64);p=np.asarray(close,float);d=np.asarray(decisions,np.int64)
 if p.shape!=(len(t),5) or np.any(np.diff(t)!=DAY) or np.any(np.diff(d)!=DAY):raise ValueError('Dense ordered real daily clocks required')
 out=np.full(len(d),np.nan)
 for i,at in enumerate(d):
  k=int(np.searchsorted(t,at))
  if k<28 or k>=len(t) or t[k]!=at:continue
  history=p[k-28:k+1]
  if not np.isfinite(history).all() or (history<=0).any():continue
  a=ranks(p[k]/p[k-21]-1);b=ranks(p[k-7]/p[k-28]-1);a-=a.mean();b-=b.mean()
  denom=np.linalg.norm(a)*np.linalg.norm(b);out[i]=float(a@b/denom) if denom else 0.
 return out

def fit(decisions,feature,label,maturity,cut,train_start):
 d=np.asarray(decisions,np.int64);x=np.asarray(feature,float);y=np.asarray(label,float);m=np.asarray(maturity,np.int64)
 if any(a.shape!=d.shape for a in (x,y,m)):raise ValueError('Exact date alignment')
 owned=(d>=train_start)&(d<cut)&(m<cut)&np.isfinite(x)&np.isfinite(y)
 if owned.sum()<80:raise ValueError('Insufficient mature training dates')
 threshold=float(np.median(x[owned]));bins=x>=threshold;counts=[int((owned&(bins==j)).sum()) for j in (0,1)]
 if min(counts)<40:raise ValueError('Insufficient mature bin support')
 means=[float(y[owned&(bins==j)].mean()) for j in (0,1)]
 model=dict(threshold=threshold,means=means,counts=counts,constant=float(y[owned].mean()),training_std=float(y[owned].std(ddof=1)),fit_clock_us=int(cut),maximum_maturity_us=int(m[owned].max()),training_dates=[int(v) for v in d[owned]],training_rows=int(owned.sum()))
 return model,owned

def predict(model,feature):
 x=np.asarray(feature,float);known=np.isfinite(x);out=np.full(x.shape,np.nan);out[known]=np.asarray(model['means'])[ (x[known]>=model['threshold']).astype(int)]
 constant=np.full(x.shape,np.nan);constant[known]=model['constant'];return out,constant

def paired_gain(gain,known,seed=811731):
 g=np.asarray(gain,float);support=np.asarray(known,bool)
 if g.shape!=support.shape or support.sum()<90:raise ValueError('Insufficient common natural validation dates')
 rng=np.random.default_rng(seed);start=rng.integers(0,len(g),(1000,int(np.ceil(len(g)/14))));ids=((start[:,:,None]+np.arange(14))%len(g)).reshape(1000,-1)[:,:len(g)]
 draws=np.array([np.mean(g[z][support[z]]) for z in ids]);return [float(v) for v in np.quantile(draws,[.025,.975])]
