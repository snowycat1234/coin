import numpy as np
import pytest

from VERIFY_SELECT import nav_metrics, rank


def test_reviewed_mean_tolerance_then_exact_worst_and_fixed_order():
    base = dict(candidate="BASE",mean_utility_excess=0.,worst_utility_excess=-.02)
    low = dict(candidate="LOW",mean_utility_excess=-4e-6,worst_utility_excess=-.02+8e-6)
    mixed = dict(candidate="MIXED",mean_utility_excess=-2e-5,worst_utility_excess=0.)
    assert rank([base,low,mixed]) == low
    low["worst_utility_excess"] = base["worst_utility_excess"]
    assert rank([base,low,mixed]) == base


def test_independent_wallet_nav_catches_return_metric_corruption():
    nav = np.array([10000.,10100.,9900.,10200.])
    ret = nav[1:]/nav[:-1]-1
    u = np.log(nav[1:]/nav[:-1]).sum()-5*np.square(np.minimum(ret,0)).sum()
    metrics = dict(net_PnL=200.,maximum_drawdown=1-9900./10100.,utility_sum=u,mean_loss=-u/3,paid_terminal_flat=True,risk_events=0)
    nav_metrics(nav,metrics,3)
    with pytest.raises(ValueError,match="metric mismatch"):
        nav_metrics(nav,dict(metrics,utility_sum=u+1e-6),3)
