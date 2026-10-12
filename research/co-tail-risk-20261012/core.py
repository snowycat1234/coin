"""One scalar joint-tail information increment with matched second/marginal moments."""
import numpy as np
DAY=86400000000;START=1609459200000000;FIT=1672531200000000;W=np.full(5,.12)
PAIRS=tuple((i,j) for i in range(5) for j in range(i+1,5))
def geometry(source):
 p=source['five_close'];prev=source['previous_close'];r=np.diff(np.log(np.vstack([prev,p.reshape(-1,5)])),axis=0).reshape(p.shape);rv=(r*r).sum(1);np.testing.assert_array_equal(rv,source['RV']);cov=np.einsum('nti,ntj->nij',r,r);basket=np.square(r@W).sum(1);np.testing.assert_allclose(basket,np.einsum('i,nij,j->n',W,cov,W),rtol=5e-14,atol=1e-18,equal_nan=True);n=len(p);base=np.full((n,22),np.nan);scale=np.full((n,5),np.nan)
 for k in range(30,n):
  history=rv[k-30:k]
  if np.isfinite(history).all() and (history>0).all():scale[k]=np.sqrt(history.mean(0)/288)
  past=basket[k-29:k+1];valid=np.isfinite(past).all() and (past>0).all() and np.isfinite(rv[k]).all() and (rv[k]>0).all() and np.isfinite(source['RV_1m'][k]).all() and (source['RV_1m'][k]>0).all()
  if valid:
   corr=[cov[k,i,j]/np.sqrt(rv[k,i]*rv[k,j]) for i,j in PAIRS];base[k]=np.r_[np.log([past[-1],past[-7:].mean(),past.mean()]),np.log(rv[k]),corr,source['jump_share'][k].mean(),source['down_share'][k].mean(),np.log(source['RV_1m'][k]/rv[k]).mean(),W@source['price_return'][k]]
 return dict(returns=r,basket_RV=basket,base=base,scale=scale)
def events(z,q):
 assert z.ndim==3 and z.shape[1]==288 and z.shape[2]>=2 and q.shape==(z.shape[2],) and np.isfinite(q).all() and (q>0).all();good=np.isfinite(z).all((1,2));upper=z>q;lower=z<-q;u=upper.mean(1);l=lower.mean(1);pairs=[(i,j) for i in range(z.shape[2]) for j in range(i+1,z.shape[2])];g=np.mean([u[:,i]*u[:,j]+l[:,i]*l[:,j] for i,j in pairs],0);raw=np.mean([(upper[:,:,i]&upper[:,:,j]).mean(1)+(lower[:,:,i]&lower[:,:,j]).mean(1) for i,j in pairs],0);out=np.column_stack([u,l,g,raw-g]);out[~good]=np.nan;return out
def assemble(base,z,q):
 assert base.shape==(len(z),22) and z.shape==(len(base),288,5);e=events(z,q);return np.column_stack([base,e]) #22+10marginals+G+C =34
def cohort(d,base,scale,y,mature):
 np.testing.assert_array_equal(mature,d+2*DAY);return np.flatnonzero((d>=START)&(d<FIT)&(mature<FIT)&np.isfinite(base).all(1)&np.isfinite(scale).all(1)&(scale>0).all(1)&np.isfinite(y)&(y>0))
def fit(d,base,scale,z,y,mature,minimum=600):
 ix=cohort(d,base,scale,y,mature);assert len(ix)>=minimum and np.isfinite(z[ix]).all();q=np.quantile(np.abs(z[ix]).reshape(-1,5),.95,axis=0,method='linear');x=assemble(base,z,q);assert np.isfinite(x[ix]).all();mean=x[ix].mean(0);std=x[ix].std(0,ddof=1);assert np.isfinite(std).all() and (std>0).all();a=(x[ix]-mean)/std;target=np.log(y[ix]);coeff={};smear={};rank={}
 for arm,k in (('CONTROL',33),('CO_TAIL',34)):
  design=np.column_stack([np.ones(len(ix)),a[:,:k]]);b,_,r,_=np.linalg.lstsq(design,target,rcond=None);assert r==k+1;coeff[arm]=b.tolist();smear[arm]=float(np.exp(target-design@b).mean());assert np.isfinite(smear[arm]) and smear[arm]>0;rank[arm]=int(r)
 return dict(train_indices=ix.tolist(),maximum_train_maturity_us=int(mature[ix].max()),threshold_absZ_q95=q.tolist(),threshold_observations_per_asset=len(ix)*288,feature_mean=mean.tolist(),feature_std=std.tolist(),coefficients=coeff,smearing=smear,ranks=rank)
def predict(model,base,z):
 x=assemble(base,z,np.array(model['threshold_absZ_q95']));assert np.isfinite(x).all();a=(x-np.array(model['feature_mean']))/np.array(model['feature_std']);out={}
 for arm,k in (('CONTROL',33),('CO_TAIL',34)):
  p=np.exp(np.column_stack([np.ones(len(a)),a[:,:k]])@np.array(model['coefficients'][arm]))*model['smearing'][arm];assert np.isfinite(p).all() and (p>0).all();out[arm]=p
 return out,x
def qlike(y,p):
 assert y.shape==p.shape and np.isfinite(y).all() and np.isfinite(p).all() and (y>0).all() and (p>0).all();q=y/p;return q-np.log(q)-1
def bootstrap(delta,seed):
 assert delta.shape==(365,) and np.isfinite(delta).all();rng=np.random.default_rng(seed);starts=rng.integers(0,365,(1000,27));means=np.array([float(delta[((v[:,None]+np.arange(14))%365).ravel()[:365]].mean()) for v in starts]);return [float(q) for q in np.quantile(means,[.025,.975])],starts,means
