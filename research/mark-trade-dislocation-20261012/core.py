"""One training-only conditional reference-price increment over own-price OLS."""
import numpy as np
DAY=86400000000;START=1609459200000000;FIT=1672531200000000
SYMBOLS=('BTCUSDT','ETHUSDT','SOLUSDT','XRPUSDT','DOGEUSDT')
def features(trade,previous,mark,ready):
 t,p,m=np.asarray(trade,float),np.asarray(previous,float),np.asarray(mark,float);r=np.asarray(ready,bool)
 if t.ndim!=2 or t.shape[1]!=5 or p.shape!=t.shape or m.shape!=t.shape or r.shape!=t.shape:raise ValueError('Exact CORE5 paired source shape')
 valid=r&np.isfinite(t)&np.isfinite(p)&np.isfinite(m)&(t>0)&(p>0)&(m>0);out=np.full((*t.shape,2),np.nan)
 out[:,:,0][valid]=np.log(t[valid]/p[valid]);out[:,:,1][valid]=np.log(m[valid]/t[valid]);return out
def fit(d,x,y,mature,minimum=600):
 d=np.asarray(d,np.int64);x=np.asarray(x,float);y=np.asarray(y,float);mature=np.asarray(mature,np.int64)
 assert x.shape==(len(d),5,2) and y.shape==(len(d),5);np.testing.assert_array_equal(mature,d+2*DAY)
 eligible=(d>=START)&(d<FIT)&(mature<FIT)&np.isfinite(x).all((1,2))&np.isfinite(y).all(1);ix=np.flatnonzero(eligible);assert len(ix)>=minimum
 a=x[ix];z=y[ix];mean=a.mean(0);std=a.std(0,ddof=1);ystd=z.std(0,ddof=1);assert np.isfinite(std).all() and (std>0).all() and (ystd>0).all();a=(a-mean)/std;control=[];candidate=[];ranks=[]
 for j in range(5):
  pc=np.column_stack((np.ones(len(ix)),a[:,j,0]));pa=np.column_stack((pc,a[:,j,1]));bc,_,rc,_=np.linalg.lstsq(pc,z[:,j],rcond=None);ba,_,ra,_=np.linalg.lstsq(pa,z[:,j],rcond=None);assert rc==2 and ra==3;control.append(bc.tolist());candidate.append(ba.tolist());ranks.append([int(rc),int(ra)])
 return dict(train_indices=ix.tolist(),maximum_train_maturity_us=int(mature[ix].max()),feature_mean=mean.tolist(),feature_std=std.tolist(),label_std=ystd.tolist(),control_coefficients=control,candidate_coefficients=candidate,OLS_ranks=ranks,symbol_order=list(SYMBOLS))
def predict(model,x):
 x=np.asarray(x,float);assert x.ndim==3 and x.shape[1:]==(5,2) and np.isfinite(x).all();a=(x-np.array(model['feature_mean']))/np.array(model['feature_std']);candidate=np.empty(x.shape[:2]);control=np.empty_like(candidate)
 for j in range(5):
  pc=np.column_stack((np.ones(len(x)),a[:,j,0]));pa=np.column_stack((pc,a[:,j,1]));control[:,j]=pc@np.array(model['control_coefficients'])[j];candidate[:,j]=pa@np.array(model['candidate_coefficients'])[j]
 return candidate,control
def paired_ci(delta,seed,details=False):
 a=np.asarray(delta,float);assert a.shape==(365,) and np.isfinite(a).all();rng=np.random.default_rng(seed);draws=[];all_starts=[]
 for _ in range(1000):
  starts=rng.integers(0,365,27);ix=np.concatenate([(s+np.arange(14))%365 for s in starts])[:365];draws.append(float(a[ix].mean()));all_starts.append(starts)
 ci=[float(v) for v in np.quantile(draws,[.025,.975])]
 return (ci,np.array(all_starts),np.array(draws)) if details else ci
