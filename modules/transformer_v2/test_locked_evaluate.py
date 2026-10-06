import numpy as np
from .locked_evaluate import baseline_weights

def test_exposure_control_uses_each_past_target_budget_and_missing_mask():
    sma=np.array([[1.,-1.,1.,-1.,np.nan],[1.,1.,-1.,-1.,np.nan]])
    active=np.isfinite(sma);gross=np.array([.12,.4])
    hold=baseline_weights('BASE_HOLD',sma,active,gross)
    assert np.allclose(np.abs(hold).sum(1),gross) and (hold[:,4]==0).all()
    signed=baseline_weights('BASE_SMA200_SIGNED',sma,active,gross)
    assert np.allclose(np.abs(signed).sum(1),gross) and np.allclose(signed.sum(1),0.)
    assert np.isfinite(signed).all() and abs(signed).max()<=.3
    assert not baseline_weights('BASE_CASH',sma,active,gross).any()
    # Changing a later observed budget must not change an earlier decision.
    changed=baseline_weights('BASE_HOLD',sma,active,np.array([.12,.6]))
    assert np.array_equal(hold[0],changed[0])
