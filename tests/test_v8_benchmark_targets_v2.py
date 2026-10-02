"""V2 integer/calendar regressions and preserved causal fixed benchmark rules."""
from pathlib import Path
import os
import json
import sys

import numpy as np
import polars as pl
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts/research_v8"))
import benchmark_targets as original
import benchmark_targets_v2 as b
from test_v8_benchmark_targets import inputs, daily


@pytest.fixture(scope="session", autouse=True)
def recorded_preexecution_binding(record_testsuite_property):
    name = os.environ.get("COIN_V8_BENCHMARK_BINDING_FILE")
    if name:
        binding = json.loads(Path(name).read_text())
        record_testsuite_property("run_binding_sha256", b.file_sha(Path(name)))
        record_testsuite_property("environment_lock_sha256", binding["environment_lock_sha256"])
        record_testsuite_property("pre_execution_adapter_sha256", binding["dirty_source_hashes"]["scripts/research_v8/benchmark_targets_v2.py"])
        record_testsuite_property("pre_execution_test_sha256", binding["dirty_source_hashes"]["tests/test_v8_benchmark_targets_v2.py"])
    else:
        record_testsuite_property("pre_execution_binding", "NOT_PROVIDED_BY_THIS_TEST_LAUNCH")


@pytest.mark.parametrize("variant", ["CASH", "SPOT_BUY_AND_HOLD", "FIXED_TREND", "FIXED_MEAN_REVERSION"])
def test_preserved_fixed_rules_after_integer_guard(inputs, variant):
    bars, calendar = inputs
    actual = b.fixed_targets(variant, bars, calendar)
    control = original.fixed_targets(variant, bars, calendar)
    assert actual.targets.equals(control.targets) and actual.calendar_ledger.equals(control.calendar_ledger)
    assert actual.receipt["implementation_version"] == b.IMPLEMENTATION_VERSION
    assert not actual.receipt["costs_paid"] and actual.receipt["economic_metrics"] is None


@pytest.mark.parametrize("malformation", ["float", "fractional", "matrix", "locked"])
def test_original_calendar_domain_not_coerced(inputs, malformation):
    bars, calendar = inputs
    malformed = {"float": calendar.astype(float), "fractional": calendar.astype(float) + .5,
                 "matrix": calendar[None, :], "locked": calendar + b._time.END - calendar[0]}[malformation]
    with pytest.raises(ValueError):
        b.fixed_targets("CASH", bars, malformed)


def test_past_only_trend_and_seven_daily_volatility(inputs):
    bars, calendar = inputs
    changed = bars.with_columns(pl.when(pl.col("close_us") > calendar[10]).then(1.)
        .otherwise(pl.col("close")).alias("close"))
    before = b.fixed_targets("FIXED_TREND", bars, calendar).calendar_ledger.filter(pl.col("decision_us") <= calendar[10])
    after = b.fixed_targets("FIXED_TREND", changed, calendar).calendar_ledger.filter(pl.col("decision_us") <= calendar[10])
    assert before.equals(after)
    risk = daily(calendar)
    assert 0 < b.causal_vol_multiplier(risk, int(calendar[0])) < 1
    with pytest.raises(ValueError, match="integer timestamp schema"):
        b.causal_vol_multiplier(risk.with_columns(pl.col("available_us").cast(pl.Float64)), int(calendar[0]))
    with pytest.raises(ValueError, match="integer timestamp schema"):
        b.fixed_targets("VOL_MANAGED_BUY_AND_HOLD", bars, calendar,
            daily_returns=risk.with_columns(pl.col("available_us").cast(pl.Float64)))
    with pytest.raises(ValueError, match="integer timestamp schema"):
        b.fixed_targets("FIXED_TREND", bars.with_columns(pl.col("available_us").cast(pl.Float64)), calendar)


def test_partial_ensemble_cash_and_missing_warmup(inputs):
    bars, calendar = inputs
    trend = b.fixed_targets("FIXED_TREND", bars, calendar)
    missing = ("VOL_MANAGED_BUY_AND_HOLD", "FIXED_MEAN_REVERSION", "FUNDING_BASIS_CARRY", "CURRENT_XGB")
    partial = b.partial_equal_risk_ensemble({"FIXED_TREND": trend}, calendar, preregistered_missing_members=missing)
    assert partial.targets["target_weight"].max() == .3 * .2 and partial.receipt["cash_reserved_sleeve_budget"] == .8
    short = bars.filter(pl.col("close_us") >= calendar[0] - 100 * b.MINUTE_US)
    with pytest.raises(ValueError, match="Entire paired fold"):
        b.assert_paired_comparison([b.fixed_targets("CASH", bars, calendar), b.fixed_targets("FIXED_TREND", short, calendar)])


def test_frozen_fit_timestamp_cannot_be_fractional(inputs, tmp_path):
    bars, calendar = inputs
    artifact = tmp_path / "synthetic-frozen.fixture"
    artifact.write_bytes(b"SYNTHETIC_NO_MODEL_FIT")
    frame = pl.DataFrame([{"decision_us": int(stamp), "available_us": int(stamp), "symbol": symbol, "predicted_return": .004}
                          for stamp in calendar for symbol in b.SYMBOLS])
    proof = {"model_sha256": b.file_sha(artifact), "predictions_sha256": b.frame_sha(frame),
        "labels": "V8_NONOVERLAP_DIRECT_RETURN_BASELINE", "label_contract_sha256": b.file_sha(b.ROOT / "protocols/LABEL_CONTRACT_V8.json"),
        "label_implementation_source_sha256": b.file_sha(b.ROOT / "scripts/research_v8/labels_v3.py"),
        "strategy_source_sha256": "a" * 64, "data_manifest_sha256": "b" * 64,
        "fit_cutoff_us": int(calendar[0] - 2 * b.MINUTE_US), "embargo_us": b.MINUTE_US,
        "max_fitting_label_mature_us": int(calendar[0] - 3 * b.MINUTE_US),
        "forecast_decision_us": calendar.tolist(), "forecast_row_ids": list(range(len(calendar))), "fit_row_ids": [-1]}
    assert b.fixed_targets("CURRENT_XGB", bars, calendar, frozen_predictions=b.FrozenReturnPredictions(frame, proof, artifact)).targets["target_weight"][0] == .3
    with pytest.raises(ValueError, match="original integer timestamp"):
        b.fixed_targets("CURRENT_XGB", bars, calendar,
            frozen_predictions=b.FrozenReturnPredictions(frame, {**proof, "fit_cutoff_us": float(proof["fit_cutoff_us"]) + .5}, artifact))
    with pytest.raises(ValueError, match="original integer metadata"):
        b.fixed_targets("CURRENT_XGB", bars, calendar,
            frozen_predictions=b.FrozenReturnPredictions(frame, {**proof, "forecast_decision_us": calendar.astype(float).tolist()}, artifact))
