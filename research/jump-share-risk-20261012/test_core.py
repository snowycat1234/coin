"""Synthetic path geometry and train-maturity counterexamples, not historical results."""
import numpy as np
from core import DAY,STEP,START,FIT,measure,features,fit,predict,qlike
def prices(r):return np.exp(np.cumsum(r,axis=1))
def test_jump_proxy_new_information_beyond_RV_RS_and_scale():
 r=np.zeros((1,288,5));r[:,30:32]=.01;other=r.copy();other[:,31]=0;other[:,150]=.01;a=measure(prices(r),np.ones(5));b=measure(prices(other),np.ones(5));np.testing.assert_allclose(a['RV'],b['RV'],atol=1e-15);np.testing.assert_allclose(a['RSminus'],b['RSminus']);assert (a['BV']>b['BV']).all() and np.all(b['jump_share']==1);c=measure(prices(2*r),np.ones(5));np.testing.assert_allclose(c['RV'],4*a['RV'],atol=1e-15);np.testing.assert_allclose(c['BV'],4*a['BV'],atol=1e-15);np.testing.assert_allclose(c['jump_share'],a['jump_share'],atol=1e-12)
def test_missing_anchor_zero_RV_and_no_acrossday_pair():
 p=np.ones((2,288,5));p[0,287:]=np.exp(.01);p[1]=np.exp(.02);z=measure(p,np.ones(5));assert np.all(z['BV']==0) and np.all(z['jump_share']==1);u=measure(p,np.full(5,np.nan));assert np.isnan(u['jump_share'][0]).all() and np.isnan(u['RSminus'][0]).all();zero=measure(np.ones_like(p),np.ones(5));zero['RV_1m']=zero['RV'];assert np.isnan(zero['jump_share']).all();assert np.isnan(features(zero)).all()
def test_strong_control_common_maturity_and_training_only_smear():
 rng=np.random.default_rng(831);d=np.arange(START,FIT+10*DAY,DAY);x=rng.normal(size=(len(d),5,7));y=np.exp(-8+.10*x[:,:,0]-.25*x[:,:,6]);x[15,2]=np.nan;m=fit(d,x,y,d+2*DAY);ix=np.array(m['train_indices']);assert len(ix)==727 and 15 not in ix and (d[ix]+2*DAY<FIT).all();xx=x.copy();yy=y.copy();xx[d+2*DAY>=FIT]=999;yy[d+2*DAY>=FIT]=999;assert fit(d,xx,yy,d+2*DAY)==m;valid=np.isfinite(x).all((1,2));p=predict(m,x[valid]);np.testing.assert_allclose(p['JUMP'],y[valid],rtol=1e-12);assert qlike(y[valid],p['JUMP']).mean()<qlike(y[valid],p['CONTROL']).mean()
def test_features_do_not_read_future_suffix():
 rng=np.random.default_rng(74);r=rng.normal(scale=.002,size=(70,288,5));p=np.exp(np.cumsum(r.reshape(-1,5),axis=0)).reshape(r.shape);z=measure(p,np.ones(5));z['RV_1m']=z['RV']*1.1;a=features(z);p[50:]*=100;zz=measure(p,np.ones(5));zz['RV_1m']=zz['RV']*1.1;b=features(zz);np.testing.assert_array_equal(a[:50],b[:50]);assert np.isnan(a[:29]).all()
