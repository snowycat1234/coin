import numpy as np
import pytest

from modules.temporal_predictability_probe.probe import fit_ridge

from .probe import DAY_US, path_windows, predict_signed, prefix_rows, score


def test_full_windows_exclude_paid_terminal_and_keep_it_separate():
    d = np.arange(63, dtype=np.int64) * DAY_US
    av = np.r_[d[1:] + 60000001, d[-1:] + 60000001]
    nav = 10000 * 1.001 ** np.arange(64)
    nav[-1] = nav[-2] - 5
    starts, y, available, partial = path_windows(d, av, nav)
    np.testing.assert_array_equal(starts, np.arange(42))
    np.testing.assert_allclose(y, 1.001**21 - 1)
    np.testing.assert_array_equal(available, d[:42] + 21 * DAY_US + 60000001)
    assert partial["start_index"] == 42 and partial["active_intervals"] == 20
    assert partial["includes_paid_close"] and partial["value"] == nav[-1] / nav[42] - 1


def test_independent_episode_gap_never_becomes_temporal_window():
    d = np.arange(63, dtype=np.int64) * DAY_US
    av = d + DAY_US + 60000001
    d[30:] += 10 * DAY_US
    with pytest.raises(ValueError, match="complete causal"):
        path_windows(d, av, np.full(64, 10000.0))


def test_label_at_fold_and_incomplete_features_cannot_enter_prefix():
    a = dict(
        train_decisions=np.array([0, 1, 2, 3]),
        train_label_available=np.array([9, 10, 8, 7]),
        train_ready=np.array([True, True, False, True]),
        train_y=np.array([[1.0, 1.0], [2.0, 2.0], [3.0, 3.0], [np.nan, 4.0]]),
    )
    np.testing.assert_array_equal(prefix_rows(a, 10), [0])
    assert not len(prefix_rows(a, 9))


def test_both_contrast_outputs_preserve_negative_forecasts():
    x = np.arange(24, dtype=float).reshape(3, 8)
    y = np.column_stack([-np.ones(3), -2 * np.ones(3)])
    fit = fit_ridge(x, y)
    np.testing.assert_array_equal(predict_signed(fit, x), y)


def test_future_labels_and_features_do_not_change_prefix_fit_or_scaler():
    rng = np.random.default_rng(1)
    x, y = rng.normal(size=(40, 8)), rng.normal(size=(40, 2))
    a = dict(
        train_decisions=np.arange(40),
        train_label_available=np.arange(40) + 5,
        train_ready=np.ones(40, bool),
        train_y=y,
    )
    rows = prefix_rows(a, 25)
    before = fit_ridge(x[rows], y[rows])
    x[20:] = 1e6
    y[20:] = -1e6
    after = fit_ridge(x[rows], y[rows])
    for name in before:
        np.testing.assert_array_equal(before[name], after[name])


def test_constant_VOL_is_action_error_not_arbitrary_numeric_forecast():
    record = score(np.array([2.0, -1.0, 0.0]), np.array([1.0, -2.0, 0.0]), -1.0)
    assert record["ridge"]["sign_agreement"] == 1
    assert record["constant_VOL"]["sign_agreement"] == 0.5
    assert record["constant_VOL"]["decision_error_rate"] == 0.5
    assert record["constant_VOL"]["MSE"] is None
    assert record["ridge"]["contrast_ties"] == 1
