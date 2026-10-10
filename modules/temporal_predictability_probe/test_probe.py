import numpy as np
import pytest

from modules.temporal_two_expert.inputs import DAY_US, FEATURE_NAMES

from .probe import aggregates, fit_ridge, predict, prefix_rows, targets, trailing


def test_true_nextday_target_clock_squared_asset_not_squared_mean():
    close = np.array([[100.0] * 5, [110.0, 90.0, 100.0, 100.0, 100.0], [110.0] * 5])
    clock = np.arange(3) * DAY_US
    y, available = targets(close, np.ones_like(close, bool), clock)
    np.testing.assert_allclose(y[0], [0, 0.004], atol=1e-15)
    assert available[0] == clock[1] and np.isnan(y[-1]).all()


def test_strict_maturity_excludes_boundary_and_knownflat_is_never_a_label():
    clocks = np.arange(6) * DAY_US
    y, available = targets(
        np.arange(100, 106)[:, None] * np.ones((1, 5)), np.ones((6, 5), bool), clocks
    )
    rows = prefix_rows(clocks, clocks, np.ones(6, bool), y, available, 4 * DAY_US)
    np.testing.assert_array_equal(rows, [0, 1, 2])
    assert 3 not in rows and not np.all(y[3] == 0)


def test_missing_close_does_not_become_zero_risk():
    close = np.ones((4, 5)) * 100
    close[1, 2] = np.nan
    y, _ = targets(close, np.isfinite(close), np.arange(4) * DAY_US)
    assert np.isnan(y[:2]).all() and np.all(y[2] == 0)


def test_masks_and_original_broadcast_market_semantics():
    x = np.ones((4, 5, 24))
    valid = np.ones_like(x, bool)
    valid[1, 2, FEATURE_NAMES.index("vol30")] = False
    a, ready = aggregates(x, valid)
    assert a.shape == (4, 8) and ready.tolist() == [True, False, True, True]
    x[0, 2, FEATURE_NAMES.index("breadth20")] = 2
    with pytest.raises(ValueError, match="broadcast"):
        aggregates(x, valid)


def test_ridge_fixed_average_penalty_unpenalized_intercept_and_constant_feature():
    x = np.column_stack([np.arange(11), np.ones(11)])
    y = np.column_stack([x[:, 0], x[:, 0] ** 2])
    fit = fit_ridge(x, y)
    np.testing.assert_allclose(fit["beta"][0, 0], x[:, 0].std() / 2)
    np.testing.assert_array_equal(fit["beta"][1], 0)
    assert fit["scale"][1] == 1
    p, _ = predict(fit, x)
    np.testing.assert_allclose(p.mean(0), y.mean(0))


def test_future_suffix_cannot_change_prefix_scaler_or_coefficients():
    clocks = np.arange(100) * DAY_US
    x = np.column_stack([np.sin(np.arange(100)), np.arange(100)])
    y = np.column_stack([np.cos(np.arange(100)), np.arange(100) ** 2])
    available = clocks + DAY_US
    rows = prefix_rows(clocks, clocks, np.ones(100, bool), y, available, 70 * DAY_US)
    before = fit_ridge(x[rows], y[rows])
    x[69:] *= 1e9
    y[69:] *= 1e9
    after = fit_ridge(x[rows], y[rows])
    for name in before:
        np.testing.assert_array_equal(before[name], after[name])


def test_trailing_only_completed20_days_not_future_or_artificial_episode_join():
    clocks = np.arange(40) * DAY_US
    y = np.column_stack([np.arange(40), np.arange(40) ** 2]).astype(float)
    available = clocks + DAY_US
    a, fallback = trailing(y, available, clocks, [25], np.array([0.0, 0.0]))
    np.testing.assert_array_equal(a[0], y[5:25].mean(0))
    assert fallback == 0
    y[25:] *= 1e9
    b, _ = trailing(y, available, clocks, [25], np.array([0.0, 0.0]))
    np.testing.assert_array_equal(a, b)
    available[24] = clocks[25] + 1
    with pytest.raises(ValueError, match="immature"):
        trailing(y, available, clocks, [25], np.array([0.0, 0.0]))
