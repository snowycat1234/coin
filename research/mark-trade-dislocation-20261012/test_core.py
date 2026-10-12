"""Causal maturity, paired cohorts and conditional-information counterexamples."""
import numpy as np
import pytest
from core import DAY,START,FIT,features,fit,predict
from source import completed_day
def test_actual_completed_boundary_minute_required():
 import pandas as pd
 start=FIT-DAY;t=np.arange(start,FIT,60000000)//1000;q=pd.DataFrame(dict(timestamp_ms=t,close_time_ms=t+59999));assert len(completed_day(q,start,FIT))==1440
 with pytest.raises(AssertionError):completed_day(q.iloc[:-1],start,FIT)
 bad=q.copy();bad.loc[1439,'close_time_ms']+=1
 with pytest.raises(AssertionError):completed_day(bad,start,FIT)
def test_same_contract_feature_domain_and_unknown_is_not_zero():
 t=np.full((3,5),100.);p=t/np.exp(.01);m=t*np.exp(.002);r=np.ones_like(t,bool);r[1,2]=False;x=features(t,p,m,r)
 np.testing.assert_allclose(x[0,:,0],.01);np.testing.assert_allclose(x[0,:,1],.002);assert np.isnan(x[1,2]).all()
 with pytest.raises(ValueError):features(t,p,m[:,::-1][:,:4],r)
def test_shared_mature_cohort_scaling_and_future_suffix_invariance():
 d=np.arange(START,FIT+10*DAY,DAY);rng=np.random.default_rng(12345);x=rng.normal(size=(len(d),5,2));y=.002+.003*x[:,:,0]-.007*x[:,:,1];m=d+2*DAY;x[10,3]=np.nan;a=fit(d,x,y,m);ix=np.array(a['train_indices']);assert len(ix)==727 and m[ix].max()<FIT and 10 not in ix
 xx=x.copy();yy=y.copy();xx[m>=FIT]*=10000;yy[m>=FIT]=999;b=fit(d,xx,yy,m);assert a==b
 pred,ctrl=predict(a,x[np.isfinite(x).all((1,2))]);np.testing.assert_allclose(pred,y[np.isfinite(x).all((1,2))],atol=1e-14);assert np.mean((pred-y[np.isfinite(x).all((1,2))])**2)<np.mean((ctrl-y[np.isfinite(x).all((1,2))])**2)
def test_degenerate_reference_channel_stops_without_model_substitution():
 d=np.arange(START,FIT,DAY);rng=np.random.default_rng(5);x=rng.normal(size=(len(d),5,2));x[:,:,1]=0;y=rng.normal(size=(len(d),5))
 with pytest.raises(AssertionError):fit(d,x,y,d+2*DAY)
