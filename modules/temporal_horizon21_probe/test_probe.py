import numpy as np
import pytest

from modules.temporal_predictability_probe.probe import targets
from modules.temporal_two_expert.inputs import DAY_US

from .probe import H, forward_rows, horizon_targets, trailing21, wallet_windows


def sample():
    clock = np.arange(100) * DAY_US
    close = 100 * np.power(1.01, np.arange(100))[:, None] * np.ones((1, 5))
    mask = np.ones_like(close, bool)
    daily, _ = targets(close, mask, clock)
    y, available = horizon_targets(close, mask, clock, daily)
    return clock, close, mask, daily, y, available


def test_21day_cumulative_and_average_daily_square_clock():
    clock, _, _, _, y, available = sample()
    np.testing.assert_allclose(y[0], [1.01**21 - 1, 0.01**2], rtol=1e-12)
    assert available[0] == clock[21] and np.isnan(y[-21:]).all()


def test_intermediate_missing_close_prevents_endpoint_only_label():
    clock, close, mask, daily, _, _ = sample()
    close[10, 2] = np.nan
    mask[10, 2] = False
    y, _ = horizon_targets(close, mask, clock, daily)
    assert np.isnan(y[0]).all() and np.isfinite(y[11]).all()


def test_original_wallet_gap_cannot_be_spliced():
    clock, _, _, _, _, _ = sample()
    nominated = np.r_[clock[:30], clock[35:80]]
    valid, spans = wallet_windows(clock, nominated)
    assert len(spans) == 2 and valid[8] and not valid[9] and not valid[29]
    assert valid[35] and not valid[59]


def test_strict_horizon_maturity_at_boundary():
    from modules.temporal_predictability_probe.probe import prefix_rows

    clock, _, _, _, y, available = sample()
    valid, _ = wallet_windows(clock, clock)
    rows = prefix_rows(clock, clock, valid, y, available, clock[50])
    assert rows[-1] == 28 and 29 not in rows


def test_forward43starts_and_three_disjoint21day_outcome_spans():
    clock, _, _, _, y, _ = sample()
    rows = forward_rows(clock, np.ones(100, bool), y, 0)
    assert len(rows) == 43 and rows[-1] == 42
    np.testing.assert_array_equal(rows[::H], [0, 21, 42])
    assert clock[rows[-1]] + H * DAY_US == 63 * DAY_US


def test_trailing21_uses_latest20_matured_targets_not_future_labels():
    clock, _, _, _, y, available = sample()
    valid, _ = wallet_windows(clock, clock)
    mean = np.array([0.0, 0.0])
    a, fallback = trailing21(y, available, clock, [60], mean, valid, clock[50])
    np.testing.assert_allclose(a[0], y[20:40].mean(0))
    assert fallback == 0
    y[40:] *= 1e9
    b, _ = trailing21(y, available, clock, [60], mean, valid, clock[50])
    np.testing.assert_array_equal(a, b)
    available[39] = clock[60] + 1
    with pytest.raises(ValueError, match="mature"):
        trailing21(y, available, clock, [60], mean, valid, clock[50])
