import sys
from pathlib import Path
sys.path.insert(0,"/workspace/level-reversion-state/dependencies")

import numpy as np
import pytest
from har import DAY,SYMBOLS,calibrate,feature,forecast,haircut,qlike,bootstrap


def synthetic():
    t=np.arange(450,dtype=np.int64)*DAY
    j=np.arange(450)[:,None]
    rv=np.exp(-6+.3*np.sin(j/13+np.arange(5)[None,:])+.1*np.cos(j/5))
    rv[0]=np.nan
    return t,rv


def test_training_label_maturity_and_normalization_future_invariance():
    t,rv=synthetic()
    model=calibrate(rv,t,t[35],t[200],t[201])
    changed=rv.copy()
    changed[202:]*=1000
    again=calibrate(changed,t,t[35],t[200],t[201])
    assert model==again and model["latest_label_maturity_us"]==t[201]
    with pytest.raises(ValueError,match="Mature"):
        calibrate(rv,t,t[35],t[200],t[200])
    np.testing.assert_array_equal(forecast(rv,230,model),forecast(np.concatenate([rv[:231],rv[231:]*8]),230,model))


def test_identity_missing_and_log_mean_definition():
    t,rv=synthetic()
    model=dict(symbol_order=list(SYMBOLS),coefficients=[[0,0,1,0]]*5,smearing=[1]*5)
    np.testing.assert_allclose(forecast(rv,120,model),rv[114:121].mean(0))
    with pytest.raises(ValueError,match="coordinates"):
        forecast(rv,120,model,symbols=SYMBOLS[::-1])
    assert feature(rv,29) is None
    missing=rv.copy()
    missing[110,2]=np.nan
    assert forecast(missing,120,model) is None
    with pytest.raises(ValueError,match="positive"):
        qlike(np.array([0.]),np.array([.1]))


def test_scalar_preserves_directions_relative_legs_and_joint_bootstrap():
    rng=np.random.default_rng(7)
    returns=rng.normal(0,.01,(30,5))
    base=np.array([-.15,.15,0,-.15,.15])
    scale,receipt=haircut(base,np.full(5,.10),returns)
    assert 0<scale<1 and receipt["forecast_annual_sigma"]*scale<=.1+1e-12
    np.testing.assert_array_equal(np.sign(base*scale),np.sign(base))
    x=np.arange(100)/100-1
    bounds=bootstrap(np.column_stack([x,3*x]))
    np.testing.assert_allclose(bounds[1],3*bounds[0])
    np.testing.assert_array_equal(bounds,bootstrap(np.column_stack([x,3*x])))
