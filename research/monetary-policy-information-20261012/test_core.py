import importlib.util
from pathlib import Path
import numpy as np
import pytest
s=importlib.util.spec_from_file_location('c',Path(__file__).with_name('core.py'));c=importlib.util.module_from_spec(s);s.loader.exec_module(c)

def test_policy_release_is_available_only_at_actual_announcement_and_prefix_is_invariant():
    r=np.array([0,100*c.DAY,200*c.DAY]);u=np.array([.25,.5,1.]);d=np.array([100*c.DAY-1,100*c.DAY])
    x,clock=c.policy_features(d,r,u,np.array([-.1,-.1]))
    np.testing.assert_array_equal(x[:,0],[.25,.5]);assert (clock<=d).all()
    alt,_=c.policy_features(d,r,np.array([.25,.5,99.]),np.array([-.1,-.1]));np.testing.assert_array_equal(x,alt)
    with pytest.raises(ValueError):c.policy_features(np.array([1]),r,u,np.array([0.]))

def test_retention_preserves_cash_caps_and_unknown_source_without_forcing_directions():
    g=c.retention(np.array([100.,100.,-100.,100.]),1.,np.array([True,True,False,True]))
    np.testing.assert_allclose(g,[.05,.1,0.,.05]);assert ((g>=0)&(g<=1)).all()

def test_checkpoint_uses_train_only_scaling_and_fixed_coefficients():
    m=dict(A_mean=np.array([1.,2.]),A_scale=np.array([2.,4.]),A_coef=np.array([2.,3.]),A_intercept=np.array(.1))
    np.testing.assert_allclose(c.predict(np.array([[3.,6.]]),m,'A'),[5.1])

def test_missing_owned_next_day_mark_rejects_label_even_when_trade_and_funding_complete():
    assert not c.held_complete([True,False],[True,True],[True,True],[True,True],[False,True])
    assert c.held_complete([True,False],[True,True],[True,True],[True,True],[True,False])

def test_uniform_retention_exactly_scales_independent_paid_day_money_not_log_utility():
    import pandas as pd
    from modules.collector_research.pipeline.economics import replay
    from scripts.research.conditional_selector_inputs import reference_utility
    frames={'BTCUSDT':pd.DataFrame(dict(dt=pd.date_range('2021-01-01',periods=3,tz='UTC'),exec_price=[99.,100.,97.],mark_funding_per_unit=[0.,.012,0.],funding_interval_complete=[True]*3,complete_kline=[True]*3))}
    base,_=replay(frames,np.array([0]),np.array([[.12]]),1.,.00135,10000.)
    for g in (0.,.37,1.):
        reduced,_=replay(frames,np.array([0]),np.array([[.12*g]]),1.,.00135,10000.)
        np.testing.assert_allclose(reduced['net'],g*base['net'],rtol=1e-12,atol=1e-9)
        np.testing.assert_allclose(reduced['fees'],g*base['fees'],rtol=1e-12,atol=1e-9)
        expected=np.log1p(g*base['net']/10000.)-.5*max(0.,-g*base['net']/10000.)
        np.testing.assert_allclose(reference_utility(reduced),expected,rtol=1e-11,atol=1e-14)
