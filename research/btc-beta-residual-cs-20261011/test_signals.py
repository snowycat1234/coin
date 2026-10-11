import importlib.util
from pathlib import Path
import sys

import numpy as np
import pytest
from scripts.research.public_cross_section_momentum import public_targets

sys.path.insert(0, str(Path(__file__).parent))
import signals as signal


def fixture():
    rng = np.random.default_rng(811084)
    count = 310
    clocks = np.arange(1590969600000000, 1590969600000000 + count * signal.DAY, signal.DAY, dtype=np.int64)
    x = rng.normal(.002, .012, count - 1)
    independent = rng.normal(0, .018, (count - 1, 4))
    returns = np.column_stack((x, x[:, None] * [.6, 1., 1.4, 1.8] + independent))
    prices = np.exp(np.vstack((np.zeros(5), np.cumsum(returns, 0)))) * [100, 40, 2, .8, .1]
    decisions = clocks[210:250]
    return clocks, prices, decisions


def test_ols_intercept_beta_and_residuals_match_independent_lstsq():
    t, p, d = fixture()
    profile = signal.context(p, t, int(d[0]))
    k = np.flatnonzero(t == d[0])[0]
    r = np.diff(np.log(p[k - 84:k + 1]), axis=0)
    coefficients = np.linalg.lstsq(np.column_stack((np.ones(84), r[:, 0])), r[:, 1:], rcond=None)[0]
    np.testing.assert_allclose(profile['alpha'][1:], coefficients[0], atol=1e-14)
    np.testing.assert_allclose(profile['beta'][1:], coefficients[1], atol=1e-13)
    expected = (r[-21:, 1:] - coefficients[0] - r[-21:, 0, None] * coefficients[1]).sum(0)
    np.testing.assert_allclose(profile['residual'][1:], expected, atol=1e-13)
    assert profile['fit_observations'] == 84 and profile['latest_input_us'] == d[0]


def test_pure_heterogeneous_market_returns_have_zero_residual_not_common_subtraction():
    t = np.arange(85, dtype=np.int64) * signal.DAY
    x = .003 + .012 * np.sin(np.arange(84))
    r = x[:, None] * [1., .5, 1., 1.5, 2.]
    p = np.exp(np.vstack((np.zeros(5), np.cumsum(r, 0))))
    profile = signal.context(p, t, int(t[-1]))
    assert np.ptp(profile['raw'][1:]) > .01
    assert np.ptp(profile['residual'][1:]) < 1e-12
    assert np.array_equal(np.argsort(profile['raw'][1:]), np.argsort(profile['raw'][1:] - profile['raw'][0]))


def test_common_scale_preserves_large_hedge_neutrality_and_covariance_caps():
    rng = np.random.default_rng(3)
    beta = np.array([1, .2, .3, 5, 6.])
    intent = np.array([0, -.15, -.15, .15, .15])
    result, report = signal.hedge_and_risk(intent, beta, rng.normal(0, .05, (30, 5)))
    assert report['cap_prescale'] < 1
    assert abs(beta @ result) < 1e-12
    assert np.abs(result).max() <= .3 and np.abs(result).sum() <= .6
    assert report['post_target_annual_vol'] <= .10 + 1e-12


def test_future_suffix_cannot_change_prior_beta_ranks_or_weights():
    t, p, d = fixture()
    original = signal.paired_targets(p, t, d)
    future = p.copy(); future[t > d[20]] *= 7
    replay = signal.paired_targets(future, t, d[:21])
    for arm in ('raw', 'residual'):
        np.testing.assert_array_equal(original['weights'][arm][:21], replay['weights'][arm])
    np.testing.assert_array_equal(original['beta'][:21], replay['beta'])


def test_missing_current_input_clears_both_policies_without_forward_fill():
    t, p, d = fixture()
    p[np.flatnonzero(t == d[10])[0], 2] = np.nan
    output = signal.paired_targets(p, t, d)
    assert not output['ready'][10]
    assert all(np.array_equal(output['weights'][arm][10:], np.zeros((len(d) - 10, 5))) for arm in ('raw', 'residual'))


def test_symbol_reordering_transports_every_beta_and_target_coordinate():
    t, p, d = fixture()
    order = np.array([4, 2, 0, 3, 1])
    reference = signal.paired_targets(p, t, d)
    replay = signal.paired_targets(p[:, order], t, d, tuple(signal.SYMBOLS[i] for i in order))
    for arm in ('raw', 'residual'):
        np.testing.assert_allclose(reference['weights'][arm][:, order], replay['weights'][arm], atol=1e-13)
    np.testing.assert_allclose(reference['beta'][:, order], replay['beta'], atol=1e-13)


def test_raw_weekly_intents_match_original_cs_in_the_same_four_asset_pool():
    t, p, d = fixture()
    paired = signal.paired_targets(p, t, d)
    _, old = public_targets(p, t, d, signal.SYMBOLS, signal.SYMBOLS[1:])
    assert len(old['rank_events']) == len(paired['rank_events'])
    for a, b in zip(old['rank_events'], paired['rank_events']):
        assert a['rank_us'] == b['rank_us'] and a['raw_weights'] == b['raw_alt_weights']


def test_ranks_stay_weekly_while_risk_and_hedge_may_move_daily():
    t, p, d = fixture()
    output = signal.paired_targets(p, t, d)
    for arm in ('raw', 'residual'):
        for i in range(1, len(d)):
            if (d[i] - signal.ANCHOR) % signal.WEEK:
                np.testing.assert_array_equal(np.sign(output['weights'][arm][i, 1:]), np.sign(output['weights'][arm][i - 1, 1:]))


def test_noninteger_or_duplicate_clock_and_unknown_asset_rejected():
    t, p, d = fixture()
    with pytest.raises(ValueError):
        signal.paired_targets(p, t.astype(float), d)
    invalid = t.copy(); invalid[230] = invalid[229]
    with pytest.raises(ValueError):
        signal.paired_targets(p, invalid, d)
    with pytest.raises(ValueError):
        signal.paired_targets(p, t, d, ('BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'XRPUSDT', 'UNKNOWNUSDT'))
