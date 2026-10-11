"""Raw-scale affine identity and explicit invalid-support counterexamples."""
import numpy as np
import pytest
from scipy.integrate import quad
from scipy.stats import norm

from shape_ablation import matched_normal, normal_representation
from verify_shape import clipped_exp_quad


def scalar_moments(q, taus):
    m = quad(lambda u: np.interp(u, taus, q), 0, 1, points=taus)[0]
    s = quad(lambda u: np.interp(u, taus, q)**2, 0, 1, points=taus)[0]
    return m, s-m*m


def test_match_after_raw_return_transform_and_affine_equivariance():
    taus = np.array([.00005, .01, .1, .3, .5, .8, .95, .99995])
    normalized = np.array([[-2, -1, -.6, -.3, 0, .5, 1.2, 4.], [-4, -2, -.7, -.1, .2, .6, 1., 3.]])
    # Different causal sigma*market factors and raw shifts; no normalized-unit match shortcut.
    raw = normalized*np.array([.012, .083])[:, None]+np.array([.007, -.014])[:, None]
    control, mean, var, _, _ = matched_normal(raw, taus)
    for i in range(2):
        ref_mean, ref_var = scalar_moments(raw[i], taus)
        actual_mean, actual_var = scalar_moments(control[i], taus)
        assert actual_mean == pytest.approx(ref_mean, abs=1e-12)
        assert actual_var == pytest.approx(ref_var, abs=1e-12)
        assert mean[i] == pytest.approx(ref_mean)
        assert var[i] == pytest.approx(ref_var)
    before = matched_normal(normalized, taus)[0]
    assert control == pytest.approx(before*np.array([.012, .083])[:, None]+np.array([.007, -.014])[:, None])


def test_invalid_variance_and_order_stop_without_floor_or_sort_repair():
    taus = [.01, .5, .99]
    with pytest.raises(ValueError, match='nonpositive'):
        matched_normal(np.array([[0., 0., 0.]]), taus)
    for bad in [np.array([[0., 1., -.1]]), np.array([[0., np.nan, 1.]])]:
        with pytest.raises(ValueError, match='identity/order'):
            matched_normal(bad, taus)


def test_clipped_normal_reference_is_distinct_from_interpolation_and_numeric_error():
    taus = np.array([.01, .1, .5, .9, .99])
    control, mean, variance, mz, vz = matched_normal(norm.ppf(taus)[None]*.1, taus)
    rep = normal_representation(control, mean, variance, mz, vz, taus)
    assert rep['maximum_raw_log_mean_absolute_error'] < 1e-14
    assert rep['maximum_raw_log_variance_relative_error'] < 1e-12
    assert rep['standard_normal_clipped_variance'] < 1
    assert rep['tail_clipping_expected_exp_change']['max'] < 0
    assert abs(rep['interpolation_expected_exp_change']['mean']) > 1e-8
    assert rep['maximum_Eexp_decomposition_error'] < 1e-14


def test_clipped_exp_verifier_uses_relative_precision_for_near_unit_integral():
    # Historical verifier failure: default quad epsrel permitted1.82e-10 error,
    # despite epsabs1e-11. Keep a fixed low-volatility numeric regression witness.
    taus = np.array([.00005, .00025, .001, .01, .05, .1, .5, .9, .95, .99, .999, .99975, .99995])
    loc, scale = .0001562656270984035, .010510218359215024
    z0, z1 = norm.ppf(taus[[0, -1]])
    exact = (taus[0]*np.exp(loc+scale*z0)+(1-taus[-1])*np.exp(loc+scale*z1)+
             np.exp(loc+.5*scale**2)*(norm.cdf(z1-scale)-norm.cdf(z0-scale)))
    value, estimated_error = clipped_exp_quad(loc, scale, taus)
    assert abs(value-exact) < 1e-12
    assert estimated_error < 1e-12
