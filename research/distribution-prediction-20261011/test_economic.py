"""Independent small cashflow/cost and funding-clock counterexamples."""
from decimal import Decimal

import numpy as np
import pytest
from scipy.integrate import quad

from economic_probe import expected_exp, expected_net, lagged_funding, profit_cutoff, unit_components
from experiment import DAY


def test_expected_exp_matches_independent_quantile_integral():
    taus = [.01, .05, .25, .5, .75, .95, .99]
    q = np.array([-.5, -.2, -.1, 0., .07, .15, .4])
    reference = quad(lambda u: np.exp(np.interp(u, taus, q)), 0., 1., points=taus, epsabs=1e-12)[0]
    assert expected_exp(q[None], taus)[0] == pytest.approx(reference, abs=1e-12)


@pytest.mark.parametrize("ratio,funding", [(.999, 0.), (1.2, .005), (.8, -.05)])
def test_cashflow_reconciles_adverse_fills_with_decimal(ratio, funding):
    p0, p1, fee, execution = Decimal('100'), Decimal(str(100*ratio)), Decimal('.00055'), Decimal('.0008')
    sold = p0*(1-execution)
    bought = p1*(1+execution)
    reference = (sold-bought-fee*(sold+bought))/p0+Decimal(str(funding))
    parts = unit_components(np.log(ratio), funding, float(fee), float(execution))
    assert parts['net'] == pytest.approx(float(reference), abs=1e-14)
    assert parts['net'] == pytest.approx(parts['price']-parts['execution']-parts['fees']+parts['funding'])


def test_profit_cutoff_differs_from_down_and_is_exact_break_even():
    cutoff = profit_cutoff(np.array([0.]), .00055, .0008)[0]
    assert cutoff < 0
    assert unit_components(cutoff, 0., .00055, .0008)['net'] == pytest.approx(0., abs=1e-14)
    assert unit_components(np.log(.999), 0., .00055, .0008)['net'] < 0


def test_origin_day_previous_interval_is_still_future():
    d = np.arange(5)*DAY
    start, end = d[:-1]+60_000_001, d[1:]+60_000_001
    coeff, prices = np.ones((4, 2)), np.full((5, 2), 100.)
    ix, lagged = lagged_funding(coeff, prices, start, end, d, lag=2)
    np.testing.assert_array_equal(ix, [2, 3])
    np.testing.assert_allclose(lagged, .01)
    with pytest.raises(ValueError, match='strictly mature'):
        lagged_funding(coeff, prices, start, end, d, lag=1)


def test_expected_net_degenerate_matches_unit_cashflow():
    q = np.full((1, 3), np.log(1.2))
    expected = expected_net(q, [.1, .5, .9], .001, .00055, .0008)[0]
    actual = unit_components(np.log(1.2), .001, .00055, .0008)['net']
    assert expected == pytest.approx(actual)
