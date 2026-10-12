"""Completed-path RV/BV risk-information increment; no account engine."""
import numpy as np
DAY=86400000000;STEP=300000000;START=1609459200000000;FIT=1672531200000000
SYMBOLS=('BTCUSDT','ETHUSDT','SOLUSDT','XRPUSDT','DOGEUSDT')
def measure(panel,previous):
 p=np.asarray(panel,float);prev=np.asarray(previous,float);assert p.ndim==3 and p.shape[1:]==(288,5) and prev.shape==(5,)
 assert np.isfinite(p).all() and (p>0).all();flat=p.reshape(-1,5);r=np.diff(np.log(np.vstack([prev,flat])),axis=0).reshape(p.shape);rv=(r*r).sum(1);rs=np.where(r<0,r*r,0).sum(1);bv=(np.pi/2)*(288/287)*(np.abs(r[:,1:])*np.abs(r[:,:-1])).sum(1);price=np.diff(np.log(np.vstack([prev,p[:,-1]])),axis=0);valid=np.isfinite(r).all(1)&(rv>0);share=np.full_like(rv,np.nan);down=np.full_like(rv,np.nan);np.divide(np.maximum(rv-bv,0),rv,out=share,where=valid);np.divide(rs,rv,out=down,where=valid)
 rs[~np.isfinite(r).all(1)]=np.nan
 return dict(RV=rv,RSminus=rs,BV=bv,jump_share=share,down_share=down,price_return=price)
def features(z):
 rv=z['RV'];n=len(rv);x=np.full((n,5,7),np.nan)
 for i in range(29,n):
  past=rv[i-29:i+1];valid=np.isfinite(past).all(0)&(past>0).all(0)&np.isfinite(z['jump_share'][i])&np.isfinite(z['down_share'][i])&np.isfinite(z['price_return'][i])&np.isfinite(z['RV_1m'][i])&(z['RV_1m'][i]>0)
  if valid.any():x[i,valid]=np.column_stack([np.log(past[-1,valid]),np.log(past[-7:,valid].mean(0)),np.log(past[:,valid].mean(0)),z['down_share'][i,valid],z['price_return'][i,valid],np.log(z['RV_1m'][i,valid]/rv[i,valid]),z['jump_share'][i,valid]])
 return x
def fit(d,x,y,mature,minimum=600):
 assert x.shape==(len(d),5,7) and y.shape==(len(d),5);np.testing.assert_array_equal(mature,d+2*DAY);valid=(d>=START)&(d<FIT)&(mature<FIT)&np.isfinite(x).all((1,2))&np.isfinite(y).all(1)&(y>0).all(1);ix=np.flatnonzero(valid);assert len(ix)>=minimum;a=x[ix];log_y=np.log(y[ix]);mean=a.mean(0);std=a.std(0,ddof=1);assert np.isfinite(std).all() and (std>0).all();a=(a-mean)/std;betas={};smears={};ranks={}
 for arm,k in (('CONTROL',6),('JUMP',7)):
  beta=[];smear=[];rank=[]
  for j in range(5):
   design=np.column_stack([np.ones(len(ix)),a[:,j,:k]]);b,_,r,_=np.linalg.lstsq(design,log_y[:,j],rcond=None);assert r==k+1;v=float(np.exp(log_y[:,j]-design@b).mean());assert np.isfinite(v) and v>0;beta.append(b.tolist());smear.append(v);rank.append(int(r))
  betas[arm]=beta;smears[arm]=smear;ranks[arm]=rank
 return dict(train_indices=ix.tolist(),maximum_train_maturity_us=int(mature[ix].max()),feature_mean=mean.tolist(),feature_std=std.tolist(),coefficients=betas,smearing=smears,ranks=ranks,symbol_order=list(SYMBOLS))
def predict(model,x):
 assert x.ndim==3 and x.shape[1:]==(5,7) and np.isfinite(x).all();a=(x-np.array(model['feature_mean']))/np.array(model['feature_std']);out={}
 for arm,k in (('CONTROL',6),('JUMP',7)):
  p=np.empty(x.shape[:2])
  for j in range(5):p[:,j]=np.exp(np.column_stack([np.ones(len(x)),a[:,j,:k]])@np.array(model['coefficients'][arm])[j])*model['smearing'][arm][j]
  assert np.isfinite(p).all() and (p>0).all();out[arm]=p
 return out
def qlike(y,p):
 assert y.shape==p.shape and np.isfinite(y).all() and np.isfinite(p).all() and (y>0).all() and (p>0).all();q=y/p;return q-np.log(q)-1
def bootstrap(delta,seed):
 assert delta.shape==(365,) and np.isfinite(delta).all();rng=np.random.default_rng(seed);starts=rng.integers(0,365,(1000,27));means=[]
 for v in starts:ix=((v[:,None]+np.arange(14))%365).ravel()[:365];means.append(float(delta[ix].mean()))
 means=np.array(means);return [float(q) for q in np.quantile(means,[.025,.975])],starts,means
