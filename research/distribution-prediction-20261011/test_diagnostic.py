"""Meaningful no-fit decomposition/denominator edge cases."""
import numpy as np
import pytest

from diagnose import binomial_interval, cluster_tail_interval, log_moments, mean_price_terms
from experiment import DAY


def test_missing_denominator_is_unknown_and_zero_success_has_nonzero_upper_bound():
    assert binomial_interval(0, 0) is None
    lo, hi = binomial_interval(0, 100)
    assert lo == 0 and 0 < hi < .1
    lo, hi = binomial_interval(100, 100)
    assert .9 < lo < 1 and hi == 1


def test_correlation_keeps_both_assets_in_same_calendar_cluster():
    dates = np.arange(8)*DAY
    hit = np.zeros((8, 2), bool)
    hit[:2] = True
    opp = np.ones_like(hit)
    ci = cluster_tail_interval(hit, opp, dates, 2, 100, 1)
    assert ci['denominators'] == [4, 4, 4, 4]
    assert ci['exceedance_counts'] == [4, 0, 0, 0]
    assert ci['clusters'] == 4
    with pytest.raises(ValueError, match='contiguous'):
        cluster_tail_interval(hit[:4], opp[:4], dates[[0, 1, 3, 4]], 2, 100, 1)


def test_uniform_quantile_moments_with_endpoint_atoms():
    # Q=0 before.25, Q rises linearly to1 by.75, then stays1.
    mean, variance = log_moments(np.array([[0., 1.]]), [.25, .75])
    assert mean[0] == pytest.approx(.5)
    assert variance[0] == pytest.approx(1/6)


def test_convex_rebound_can_erase_zero_log_mean_short_edge():
    q = np.array([[-.2, .2]])
    mean, _, ee, deterministic, convexity = mean_price_terms(q, [.25, .75])
    assert mean[0] == pytest.approx(0.)
    assert deterministic[0] == pytest.approx(0.)
    assert convexity[0] > 0 and 1-ee[0] < 0
    assert 1-ee[0] == pytest.approx(deterministic[0]-convexity[0])
