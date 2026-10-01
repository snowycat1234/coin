import numpy as np
import polars as pl
import pytest

from quant.alpha_rules_v2 import HOUR_US, executable_labels_v2, hysteresis_targets_v2, r2_gates
from quant.decision_policy import holding_period_complete
from quant.execution_contract import MINUTE_US
from quant.execution_parity import cross_engine_parity


def test_labels_use_both_v2_execution_minutes_and_actual_costs():
    features = pl.DataFrame({"symbol": ["BTCUSDT"], "available_us": [HOUR_US]})
    minutes = pl.DataFrame({"symbol": ["BTCUSDT"] * 400,
                            "open_us": np.arange(400) * MINUTE_US,
                            "open": 100 + np.arange(400) * 0.01})
    labels = executable_labels_v2(features, minutes)
    assert labels["entry_us"][0] == 61 * MINUTE_US + 1
    assert labels["label_end_us"][0] == 301 * MINUTE_US + 1
    expected = minutes["open"][301] / minutes["open"][61] - 1
    assert labels["gross_return"][0] == pytest.approx(expected)
    ratio = (1 - .0005) * (1 - .001) / ((1 + .0005) * (1 + .001))
    assert labels["diagnostic_net_return"][0] == pytest.approx((1 + expected) * ratio - 1)
    gap = minutes.filter(pl.col("open_us") != 100 * MINUTE_US)
    assert executable_labels_v2(features, gap)["gross_return"][0] is None
    capacity_gap = minutes.filter(pl.col("open_us") != 60 * MINUTE_US)
    assert not executable_labels_v2(features, capacity_gap)["label_valid"][0]


def test_hysteresis_strict_thresholds_and_hold_then_exit():
    predictions = pl.DataFrame({"symbol": ["BTCUSDT"] * 6,
                               "available_us": np.arange(6) * HOUR_US,
                               "expected_return": [.0045, .0046, -.02, .0014, .0046, None]})
    result = hysteresis_targets_v2(predictions, "A")
    assert result["target_weight"].to_list() == [0, .30, .30, 0, .30, 0]
    assert result["risk_forced_exit"].to_list() == [False] * 5 + [True]
    assert result["minimum_hold_minutes"].unique().to_list() == [120]


def test_missing_decision_resets_to_flat_even_during_hold():
    predictions = pl.DataFrame({"symbol": ["BTCUSDT"] * 3,
                               "available_us": [0, 2 * HOUR_US, 3 * HOUR_US],
                               "expected_return": [.01, .02, .01]})
    assert hysteresis_targets_v2(predictions, "B")["target_weight"].to_list() == [.30, 0, .30]


def test_r2_cannot_accept_profitable_but_inferior_or_cost_fragile_model():
    summary = {"total_return": .10, "sharpe": .8, "max_drawdown": .10,
               "fees": 10, "gross_pnl_before_costs": 200,
               "round_trip_count": 31, "daily_risk_observable": True}
    stress = {name: {"total_return": .01} for name in ("fee_x2", "slippage_x2")}
    active = {name: {"sharpe": value, "total_return": .05}
              for name, value in zip(("B2", "B3", "B4"), (.6, .7, .9), strict=True)}
    assert r2_gates(summary, stress, active)["passed"]
    fragile = r2_gates(summary, {**stress, "fee_x2": {"total_return": -.01}}, active)
    assert not fragile["passed"]
    inferior = r2_gates({**summary, "sharpe": .65}, stress, active)
    assert not inferior["checks"]["exceed_active_median_risk_adjusted"]
    assert not r2_gates({**summary, "gross_pnl_before_costs": 0}, stress, active)["passed"]
    assert not r2_gates({**summary, "daily_risk_observable": False}, stress, active)["passed"]


def test_actual_fill_hold_guard_and_explicit_risk_exception():
    entry = 61 * MINUTE_US + 20_000_000
    assert not holding_period_complete(entry + 120 * MINUTE_US - 1, entry, 120, False)
    assert holding_period_complete(entry + 120 * MINUTE_US, entry, 120, False)
    assert holding_period_complete(entry + MINUTE_US, entry, 120, True)
    with pytest.raises(ValueError):
        holding_period_complete(entry, entry, 90, False)


@pytest.mark.parametrize("forced", [False, True])
def test_both_executors_enforce_actual_holding_or_risk_exit(forced):
    report = cross_engine_parity(minimum_hold_minutes=120, force_exit=forced)
    assert report["pass"]
    assert report["historical_expired"] == report["live_expired"]
