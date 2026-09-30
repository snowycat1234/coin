import copy
import json
from pathlib import Path

import numpy as np
import polars as pl
import pytest

from quant.research import (
    FEATURE_NAMES,
    INTERVAL_US,
    MINUTE_US,
    build_features,
    build_labels,
    calendar_performance,
    date_us,
    development_only,
    evaluate_gates,
    excess_bootstrap,
    export_model,
    fit_model,
    load_protocol,
    make_folds,
    predict_exported_model,
    probability_targets,
    register_protocol,
    split_samples,
)

PROTOCOL = Path(__file__).resolve().parents[1] / "configs/experiments/logistic_v1.json"


def bars(count=400, interval="15m"):
    rng = np.random.default_rng(9)
    close = 100 * np.exp(np.cumsum(rng.normal(0, .004, count)))
    opening = np.concatenate(([100], close[:-1]))
    start = np.arange(count) * INTERVAL_US[interval]
    return pl.DataFrame({
        "open_us": start, "close_us": start + INTERVAL_US[interval],
        "available_us": start + INTERVAL_US[interval],
        "open": opening, "high": np.maximum(opening, close) * 1.001,
        "low": np.minimum(opening, close) * .999, "close": close,
        "volume": rng.uniform(1, 20, count), "taker_buy_base": rng.uniform(.1, .9, count),
        "symbol": ["BTCUSDT"] * count, "interval": [interval] * count,
    })


def test_future_price_change_does_not_rewrite_historical_features():
    original = bars()
    changed = original.with_columns([
        pl.when(pl.col("open_us") >= 250 * INTERVAL_US["15m"])
        .then(pl.col(name) * 20).otherwise(pl.col(name)).alias(name)
        for name in ["open", "high", "low", "close", "volume", "taker_buy_base"]
    ])
    old = build_features(original).head(250).select(FEATURE_NAMES).to_numpy()
    new = build_features(changed).head(250).select(FEATURE_NAMES).to_numpy()
    np.testing.assert_array_equal(old, new)


def test_gap_resets_feature_warmup():
    original = bars().filter(pl.col("open_us") != 200 * INTERVAL_US["15m"])
    features = build_features(original)
    after = features.filter(pl.col("open_us") > 200 * INTERVAL_US["15m"])
    assert after["ema_gap"].head(99).null_count() == 99
    assert after["ema_gap"][99] is not None


def test_label_execution_cost_and_gap_rejection():
    minutes = np.arange(1000) * MINUTE_US
    prices = 100 + np.arange(1000) * .02
    frame = pl.DataFrame({"open_us": minutes, "open": prices, "symbol": ["BTCUSDT"] * 1000})
    features = bars(3)
    labeled = build_labels(features, frame)
    assert labeled["entry_us"][0] == 15 * MINUTE_US + 1
    assert labeled["label_end_us"][0] == 255 * MINUTE_US + 1
    expected = (prices[255] / prices[15]) * .9985 / 1.0015 - 1
    assert labeled["net_return"][0] == pytest.approx(expected)
    missing = frame.filter(pl.col("open_us") != 100 * MINUTE_US)
    assert not build_labels(features, missing)["label_valid"].any()
    missing_entry = frame.filter(pl.col("open_us") != 15 * MINUTE_US)
    assert not build_labels(features, missing_entry)["label_valid"][0]


def test_label_uses_next_minute_if_availability_is_delayed():
    frame = pl.DataFrame({"open_us": np.arange(300) * MINUTE_US,
                          "open": np.ones(300) * 100, "symbol": ["BTCUSDT"] * 300})
    delayed = bars(1).with_columns((pl.col("available_us") + 1).alias("available_us"))
    labels = build_labels(delayed, frame)
    assert labels["entry_us"][0] == 16 * MINUTE_US + 1
    assert labels["net_return"][0] < 0


def test_exact_calendar_folds_never_include_holdout_or_short_final_fold():
    protocol = load_protocol(PROTOCOL)
    folds = make_folds(protocol)
    assert len(folds) == 7
    assert folds[0].train_start_us == date_us("2022-01-01")
    assert folds[0].train_end_us == date_us("2024-01-01")
    assert folds[0].test_start_us == date_us("2024-04-01")
    assert folds[-1].test_end_us == date_us("2026-01-01")
    assert all(fold.test_end_us <= date_us(protocol["holdout_start"]) for fold in folds)


def test_purge_and_embargo_on_both_edges():
    step = INTERVAL_US["15m"]
    frame = pl.DataFrame({"available_us": [0, step, 2 * step, 3 * step],
                          "label_end_us": [2 * step, 2 * step, 3 * step, 4 * step],
                          "label_valid": [True] * 4,
                          **{name: [1.] * 4 for name in FEATURE_NAMES}})
    result = split_samples(frame, 0, 4 * step, "15m")
    assert result["available_us"].to_list() == [step]


def test_locked_data_filtered_before_features():
    protocol = load_protocol(PROTOCOL)
    cutoff = date_us(protocol["holdout_start"])
    frame = bars(3).with_columns(
        pl.Series("open_us", [cutoff - 2, cutoff - 1, cutoff]),
        pl.Series("available_us", [cutoff - 1, cutoff, cutoff + 1]))
    assert development_only(frame, protocol).height == 2


def test_scaler_and_model_fit_training_only_and_targets_obey_raw_cap():
    train = build_features(bars()).drop_nulls(list(FEATURE_NAMES)).with_columns(
        pl.Series("label", np.arange(301) % 2),
        (pl.col("available_us") + 4 * 60 * MINUTE_US).alias("label_end_us"))
    config = {"id": "test", "C": 1., "threshold": .55}
    model = fit_model(train, config, minimum_rows=100)
    np.testing.assert_allclose(model.named_steps["scaler"].mean_,
                               train.select(FEATURE_NAMES).to_numpy().mean(axis=0))
    mean_before = model.named_steps["scaler"].mean_.copy()
    future = train.with_columns([(pl.col(name) + 100).alias(name) for name in FEATURE_NAMES])
    targets = probability_targets(model, future, config)
    np.testing.assert_array_equal(model.named_steps["scaler"].mean_, mean_before)
    assert targets["target_weight"].max() <= .30
    exported = export_model(model, train, config)
    assert exported["training_last_label_end_us"] == train["label_end_us"].max()
    portable = predict_exported_model(exported, future)
    np.testing.assert_allclose(portable["probability"].to_numpy(),
                               targets["probability"].to_numpy(), atol=1e-14)


def test_registration_budget_immutability_and_no_repeated_outer_test(tmp_path):
    protocol = load_protocol(PROTOCOL)
    register = tmp_path / "registered.json"
    state = register_protocol(protocol, register)
    assert not state["holdout_revealed"]
    changed = copy.deepcopy(protocol)
    changed["configurations"][0]["C"] = .2
    with pytest.raises(ValueError, match="changed"):
        register_protocol(changed, register)
    state["status"] = "oos_started"
    register.write_text(json.dumps(state))
    with pytest.raises(ValueError, match="already started"):
        register_protocol(protocol, register)
    resumed = register_protocol(protocol, register, "Repair report API integration only")
    assert resumed["audit"][-1]["event"] == "explicit_technical_resume"
    state["status"] = "completed"
    register.write_text(json.dumps(state))
    with pytest.raises(ValueError, match="already started"):
        register_protocol(protocol, register, "Finished evaluations cannot resume")
    excessive = copy.deepcopy(protocol)
    excessive["configurations"] *= 2
    path = tmp_path / "too_many.json"
    path.write_text(json.dumps(excessive))
    with pytest.raises(ValueError, match="budget"):
        load_protocol(path)


def test_gate_failure_stops_and_success_still_requires_locked_holdout():
    protocol = load_protocol(PROTOCOL)
    summary = {"total_return": .10, "sharpe": 1., "max_drawdown": -.08,
               "round_trip_count": 31, "daily_risk_observable": True,
               "exposed_valuation_gap_days": 0}
    baseline = {"total_return": .05}
    stress = {"fee_x2": {"total_return": .02}, "slippage_x2": {"total_return": .03}}
    result = evaluate_gates(summary, baseline, stress, .60, protocol["gates"])
    assert result["status"] == "HOLDOUT_REQUIRED"
    stress["fee_x2"]["total_return"] = -.01
    result = evaluate_gates(summary, baseline, stress, .60, protocol["gates"])
    assert result["status"] == "STOP"
    assert "fee_x2_nonnegative" in result["failed_checks"]


def test_stale_open_exposure_cannot_certify_daily_risk_gate():
    protocol = load_protocol(PROTOCOL)
    summary = {"total_return": .10, "sharpe": 1., "max_drawdown": .08,
               "round_trip_count": 31, "daily_risk_observable": False,
               "valuation_gap_days": 1, "exposed_valuation_gap_days": 1}
    stress = {"fee_x2": {"total_return": .02}, "slippage_x2": {"total_return": .03}}
    result = evaluate_gates(summary, {"total_return": .05}, stress, .60, protocol["gates"])
    assert result["status"] == "STOP"
    assert result["checks"]["drawdown"]
    assert not result["checks"]["daily_risk_observable"]
    del summary["daily_risk_observable"]
    summary["exposed_valuation_gap_days"] = 0
    missing_contract = evaluate_gates(
        summary, {"total_return": .05}, stress, .60, protocol["gates"])
    assert not missing_contract["checks"]["daily_risk_observable"]


def test_block_bootstrap_is_deterministic_and_paired():
    dates = [f"2024-01-{day:02d}" for day in range(1, 29)]
    candidate = pl.DataFrame({"date": dates, "return": [.001] * 28})
    baseline = pl.DataFrame({"date": dates, "return": [.0005] * 28})
    first = excess_bootstrap(candidate, baseline, replicates=20)
    second = excess_bootstrap(candidate, baseline, replicates=20)
    assert first == second
    assert first["ci_95"][0] == pytest.approx(.0005 * 365)
    with pytest.raises(ValueError, match="identical UTC dates"):
        excess_bootstrap(candidate.head(27), baseline, replicates=20)


def test_calendar_returns_chain_from_prior_period_nav():
    frame = pl.DataFrame({"date": ["2024-01-31", "2024-02-01", "2025-01-01"],
                          "nav": [110., 99., 108.9]})
    result = calendar_performance(frame, 100.)
    assert result["monthly"][0]["return"] == pytest.approx(.10)
    assert result["monthly"][1]["return"] == pytest.approx(-.10)
    assert result["yearly"][0]["return"] == pytest.approx(-.01)
    assert result["yearly"][1]["return"] == pytest.approx(.10)
