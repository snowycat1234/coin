import numpy as np
import pytest
from driver import compose,risk,DAY
def test_preexecution_netting_and_caps():
    cs=np.array([[.3,-.3,0,0,0.]])
    hold=np.array([[-.3,.3,0,0,0.]])
    np.testing.assert_array_equal(compose(cs,hold),np.zeros((1,5)))
    with pytest.raises(ValueError):compose(cs,np.array([[.31,0,0,0,0]]))
def test_past_covariance_contraction_and_future_invariance():
    rng=np.random.default_rng(811731);t=np.arange(100)*DAY;p=100*np.exp(np.cumsum(rng.normal(0,.01,(100,5)),axis=0));d=t[30:];cs=np.tile([.1,.1,-.1,-.1,0],(len(d),1));h=np.tile([.03]*5,(len(d),1));m=compose(cs,h);original=risk(t,p,d,cs,h,m);changed=p.copy();changed[70:]*=np.arange(2,7);future=risk(t,changed,d,cs,h,m)
    assert original[:40]==future[:40] and all(r['mix_sigma']<=.5*(r['CS_sigma']+r['HOLD_sigma'])+1e-12 for r in original)
