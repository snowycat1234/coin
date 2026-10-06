import numpy as np
import pandas as pd
from .data import chronological_inner,train_scaler,causal_future_targets

def test_train_scaler_ignores_later_rows_and_unobserved_assets():
    x=np.ones((40,4,3));a=np.ones((40,4),bool);a[:,3]=False;x[:,3]=999
    mu,sd=train_scaler(x,a,[20],length=10);x[21:]=5000
    later_mu,later_sd=train_scaler(x,a,[20],length=10)
    assert np.array_equal(mu,later_mu) and np.array_equal(sd,later_sd) and np.all(mu==1)

def test_inner_maturity_precedes_embargo_boundary():
    dates=pd.date_range('2022-01-01',periods=500,tz='UTC')
    ends=dates+pd.Timedelta(days=61)
    tr,va=chronological_inner(np.arange(400),dates,ends)
    assert (ends[tr]<dates[va[0]]-pd.Timedelta(days=60)).all()
    assert not set(tr)&set(va)

def test_missing_future_day_invalidates_relative_and_regime_labels():
    close=np.exp(np.arange(75)[:,None]*np.array([.001,.002,.003,.004])[None,:])
    available=np.ones_like(close,dtype=bool)
    relative,regime=causal_future_targets(close,available)
    assert np.isfinite(relative[0]).all() and np.isfinite(regime[0]).all()
    close[4,0]=np.nan
    relative,regime=causal_future_targets(close,available)
    assert np.isnan(relative[0]).all() and np.isnan(regime[0]).all()
    available[:10,0]=False
    assert np.isnan(causal_future_targets(close,available)[0][5,0]).all()
