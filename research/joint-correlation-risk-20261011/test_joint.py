import numpy as np
import pytest
from joint import DAY,SYMBOLS,correlation,inputs,fit,forecast,size,bootstrap


def fixture():
    rng=np.random.default_rng(18)
    x=rng.normal(0,.01,(260,5))
    close=100*np.exp(np.cumsum(x,axis=0))
    z=rng.normal(0,.005,(260,36,5))
    realized=np.einsum('dti,dtj->dij',z,z)
    return close,realized,np.arange(260,dtype=np.int64)*DAY


def test_future_invariance_strict_maturity_and_order():
    p,c,t=fixture();m=fit(p,c,t,t[30],t[180],t[182])
    p2=p.copy();c2=c.copy();p2[182:]*=7;c2[182:]*=100
    assert fit(p2,c2,t,t[30],t[180],t[182])==m
    with pytest.raises(ValueError,match='Mature'):fit(p,c,t,t[30],t[180],t[181])
    a,_,_=forecast(p,c,200,m);p2=p.copy();c2=c.copy();p2[201:]*=7;c2[201:]*=100
    b,_,_=forecast(p2,c2,200,m)
    for name in a:np.testing.assert_array_equal(a[name],b[name])
    with pytest.raises(ValueError,match='coordinates'):forecast(p,c,200,m,SYMBOLS[::-1])
    with pytest.raises(ValueError,match='clocks'):fit(p,c,t[::-1],t[30],t[180],t[182])


def test_native_exact_simple_diagonal_PSD_and_zero_theta():
    p,c,t=fixture();m=fit(p,c,t,t[30],t[180],t[182]);m['theta']=0
    simple,native,a,b=inputs(p,c,100)
    np.testing.assert_array_equal(native,np.cov(np.diff(p[70:101],axis=0)/p[70:100],rowvar=False,ddof=1))
    _,mixed,_=forecast(p,c,100,m)
    np.testing.assert_allclose(mixed,native,rtol=1e-14,atol=1e-18)
    m['theta']=.7;_,mixed,_=forecast(p,c,100,m)
    np.testing.assert_allclose(np.diag(mixed),np.diag(native),rtol=1e-14)
    assert np.min(np.linalg.eigvalsh(mixed))>0
    missing=c.copy();missing[95,0,0]=np.nan
    with pytest.raises(ValueError,match='Complete'):inputs(p,missing,100)


def test_sum_covariance_not_mean_correlation_and_scalar_risk():
    p,c,t=fixture()
    c[71:101]*=np.arange(1,31)[:,None,None]
    simple,native,a,b=inputs(p,c,100)
    assert not np.allclose(b,np.mean(correlation(c[71:101]),axis=0))
    base=np.array([.05,.05,-.05,-.05,0])
    w,s,sigma,_=size(base,native*100,simple)
    assert 0<s<1 and sigma*s<=.1+1e-12
    np.testing.assert_allclose(w,base*s,atol=1e-14)
    assert abs(w).sum()<=.6 and abs(w).max()<=.3
    bad=native.copy();bad[0,0]=-1
    with pytest.raises(ValueError,match='Positive'):correlation(bad)


def test_joint_bootstrap_deterministic_scaling():
    x=np.sin(np.arange(120)/4)-.2
    np.testing.assert_array_equal(bootstrap(x),bootstrap(x))
    np.testing.assert_allclose(bootstrap(x*3),3*np.asarray(bootstrap(x)))
