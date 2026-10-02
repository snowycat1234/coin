"""Synthetic causal target checks; no market input, model training or PnL."""
from datetime import date
from pathlib import Path
import sys

import numpy as np
import polars as pl
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts/research_v8"))
import benchmark_targets as b
from quant.research_fast.dataset import day_us


@pytest.fixture
def inputs():
    start = day_us(date(2025, 7, 20))
    times = start + np.arange(-300, 70, dtype=np.int64) * b.MINUTE_US
    bars = pl.DataFrame([{"symbol": symbol, "close_us": int(stamp), "available_us": int(stamp),
                        "close": 100 + i * .01 + s * 10}
                        for s, symbol in enumerate(b.SYMBOLS) for i, stamp in enumerate(times)])
    calendar = start + np.arange(65, dtype=np.int64) * b.MINUTE_US
    return bars, calendar


def test_cash_and_capped_buy_hold_sparse_schema(inputs):
    bars, calendar = inputs
    cash = b.fixed_targets("CASH", bars, calendar)
    hold = b.fixed_targets("SPOT_BUY_AND_HOLD", bars, calendar)
    assert cash.targets.schema == b.TARGET_SCHEMA and cash.targets["target_weight"].sum() == 0
    assert hold.targets.height == 4  # One entry and one terminal intent per asset.
    assert hold.targets["target_weight"].to_list() == [.3, .3, 0., 0.]
    assert cash.receipt["costs_paid"] is False and hold.receipt["economic_metrics"] is None
    assert not b.assert_paired_comparison([cash, hold])["economic_scoring_allowed"]


def test_trend_future_perturbation_is_causal(inputs):
    bars, calendar = inputs
    original = b.fixed_targets("FIXED_TREND", bars, calendar)
    cutoff = calendar[10]
    altered = bars.with_columns(pl.when(pl.col("close_us") > cutoff).then(pl.col("close") * .1)
        .otherwise(pl.col("close")).alias("close"))
    changed = b.fixed_targets("FIXED_TREND", altered, calendar)
    before = original.calendar_ledger.filter(pl.col("decision_us") <= cutoff)
    after = changed.calendar_ledger.filter(pl.col("decision_us") <= cutoff)
    assert before.equals(after) and before["target_weight"].max() == .3


def test_mean_reversion_preceding_window_and_maximum_intent_hold(inputs):
    bars, calendar = inputs
    modified = bars.with_columns(pl.when(pl.col("close_us") >= calendar[0]).then(80.)
        .otherwise(pl.col("close")).alias("close"))
    plan = b.fixed_targets("FIXED_MEAN_REVERSION", modified, calendar)
    for symbol in b.SYMBOLS:
        rows = plan.calendar_ledger.filter(pl.col("symbol") == symbol)
        assert rows["target_weight"][0] == .3
        assert rows["target_weight"][60] == 0
    assert not plan.receipt["candidate_qualification_allowed"]


def daily(calendar, n=7):
    end = int(calendar[0] // b.DAY_US * b.DAY_US)
    return pl.DataFrame({"day_end_us": end + np.arange(-n + 1, 1, dtype=np.int64) * b.DAY_US,
                         "available_us": end + np.arange(-n + 1, 1, dtype=np.int64) * b.DAY_US,
                         "gross_exposure_return": np.linspace(-.03, .03, n)})


def test_seven_complete_days_ewma_cap_and_future_invariance(inputs):
    bars, calendar = inputs
    risk = daily(calendar)
    multiplier = b.causal_vol_multiplier(risk, int(calendar[0]))
    assert 0 < multiplier < 1
    future = pl.DataFrame({"day_end_us": [int(calendar[0] + b.DAY_US)],
                          "available_us": [int(calendar[0] + b.DAY_US)], "gross_exposure_return": [-.9]})
    assert b.causal_vol_multiplier(pl.concat([risk, future]), int(calendar[0])) == multiplier
    managed = b.fixed_targets("VOL_MANAGED_BUY_AND_HOLD", bars, calendar, daily_returns=risk)
    assert managed.targets["target_weight"][0] == .3 * multiplier
    assert managed.targets["target_weight"].max() <= .3


def test_missing_warmup_forbids_different_scoring_windows(inputs):
    bars, calendar = inputs
    short = bars.filter(pl.col("close_us") >= calendar[0] - 100 * b.MINUTE_US)
    trend = b.fixed_targets("FIXED_TREND", short, calendar)
    cash = b.fixed_targets("CASH", bars, calendar)
    assert trend.receipt["warmup_failed"]
    with pytest.raises(ValueError, match="Entire paired fold"):
        b.assert_paired_comparison([cash, trend])
    managed = b.fixed_targets("VOL_MANAGED_BUY_AND_HOLD", bars, calendar, daily_returns=daily(calendar, 6))
    assert managed.receipt["warmup_failed"] and managed.targets["target_weight"].sum() == 0


def test_carry_and_unfrozen_xgb_are_not_evaluable(inputs):
    bars, calendar = inputs
    carry = b.fixed_targets("FUNDING_BASIS_CARRY", bars, calendar)
    xgb = b.fixed_targets("CURRENT_XGB", bars, calendar)
    assert carry.receipt["status"].startswith("NOT_EVALUABLE") and carry.receipt["economic_metrics"] is None
    assert xgb.receipt["status"].startswith("NOT_EVALUABLE") and not xgb.receipt["paired_comparison_allowed"]


def test_partial_ensemble_missing_sleeves_remain_cash(inputs):
    bars, calendar = inputs
    trend = b.fixed_targets("FIXED_TREND", bars, calendar)
    missing = ("VOL_MANAGED_BUY_AND_HOLD", "FIXED_MEAN_REVERSION", "FUNDING_BASIS_CARRY", "CURRENT_XGB")
    plan = b.partial_equal_risk_ensemble({"FIXED_TREND": trend}, calendar, preregistered_missing_members=missing)
    assert plan.strategy_id == "PARTIAL_ENSEMBLE_WITH_CASH_FOR_UNAVAILABLE_SLEEVES"
    assert plan.targets["target_weight"].max() == .3 * .2
    assert plan.receipt["cash_reserved_sleeve_budget"] == .8
    assert not plan.receipt["full_ensemble_evaluable"] and not plan.receipt["paired_comparison_allowed"]
    with pytest.raises(ValueError, match="registered consistently"):
        b.partial_equal_risk_ensemble({"FIXED_TREND": trend}, calendar, preregistered_missing_members=())


def test_frozen_xgb_requires_external_source_mature_cutoff_and_no_fit(inputs, tmp_path):
    bars, calendar = inputs
    artifact = tmp_path / "synthetic-frozen-model.fixture"
    artifact.write_bytes(b"ENGINEERING_SYNTHETIC_FROZEN_ARTIFACT_NO_TRAINING")
    predictions = pl.DataFrame([{"decision_us": int(stamp), "symbol": symbol,
        "available_us": int(stamp), "predicted_return": .004} for stamp in calendar for symbol in b.SYMBOLS])
    proof = {"model_sha256": b.file_sha(artifact), "predictions_sha256": b.frame_sha(predictions),
        "labels": "V8_NONOVERLAP_DIRECT_RETURN_BASELINE", "label_contract_sha256": b.file_sha(b.ROOT / "protocols/LABEL_CONTRACT_V8.json"),
        "label_implementation_source_sha256": b.file_sha(b.ROOT / "scripts/research_v8/labels_v3.py"),
        "strategy_source_sha256": "a" * 64, "data_manifest_sha256": "b" * 64,
        "fit_cutoff_us": int(calendar[0] - 2 * b.MINUTE_US), "embargo_us": b.MINUTE_US,
        "max_fitting_label_mature_us": int(calendar[0] - 3 * b.MINUTE_US),
        "forecast_decision_us": calendar.tolist(), "forecast_row_ids": list(range(len(calendar))), "fit_row_ids": [-1, -2]}
    frozen = b.FrozenReturnPredictions(predictions, proof, artifact)
    plan = b.fixed_targets("CURRENT_XGB", bars, calendar, frozen_predictions=frozen)
    assert plan.targets["target_weight"][0] == .3 and plan.receipt["costs_paid"] is False
    with pytest.raises(ValueError, match="precede mature"):
        b.fixed_targets("CURRENT_XGB", bars, calendar,
            frozen_predictions=b.FrozenReturnPredictions(predictions, {**proof, "fit_cutoff_us": int(calendar[0])}, artifact))
    with pytest.raises(ValueError, match="Legacy overlapping"):
        b.fixed_targets("CURRENT_XGB", bars, calendar,
            frozen_predictions=b.FrozenReturnPredictions(predictions, {**proof, "labels": "V7_SAME_WINDOW"}, artifact))
