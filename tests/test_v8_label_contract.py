"""Synthetic V8 chronology/interval mutations; no market fitting or OOS reads."""
from dataclasses import replace
from datetime import date
from pathlib import Path
import sys

import numpy as np
import polars as pl
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts/research_v8"))
import labels as v8
from quant.research_fast.dataset import BAR_US, PAST_BARS, STREAMS, day_us


@pytest.fixture
def joint():
    n = 1000
    times = day_us(date(2025, 7, 1)) + np.arange(n, dtype=np.int64) * BAR_US
    rows = {"timestamp": times}
    for index, stream in enumerate(STREAMS):
        price = 100 + index * 10 + np.arange(n) * .01
        rows.update({f"{stream}__available_us": times + BAR_US,
                     f"{stream}__quality": np.zeros(n, np.int32),
                     f"{stream}__aggressive_buy_notional": 100 + np.arange(n) * .1 + index,
                     f"{stream}__aggressive_sell_notional": np.full(n, 80 + index),
                     f"{stream}__close": price, f"{stream}__open": price - .002,
                     f"{stream}__high": price + .01, f"{stream}__low": price - .01,
                     f"{stream}__vwap": price - .001,
                     f"{stream}__last_trade_us": times + BAR_US - 1_000_000,
                     f"{stream}__empty_bin": np.zeros(n, bool),
                     f"{stream}__return_5s": np.full(n, .0001),
                     f"{stream}__flow_imbalance": np.full(n, .1),
                     f"{stream}__large_trade_share": np.full(n, .2),
                     f"{stream}__signed_price_impact": np.full(n, .01),
                     f"{stream}__interarrival_count": np.full(n, 10)})
        for field in ("quote_notional", "base_volume", "trade_count", "agg_count", "mean_trade_size",
                      "max_trade_size", "mean_interarrival", "std_interarrival"):
            rows[f"{stream}__{field}"] = np.full(n, 10. + index)
    return pl.DataFrame(rows)


@pytest.fixture
def decisions(joint):
    return joint["timestamp"][0] + np.asarray([1800, 1860], np.int64) * 1_000_000


@pytest.mark.parametrize("variant,offsets,count", [
    ("LEAD_LAG_5M_5M", (5, 300, 305, 600), 59),
    ("EARLY_LATE_150S_GAP5", (0, 150, 155, 305), 30),
    ("EARLY_LATE_150S_GAP10", (0, 150, 160, 310), 30),
])
def test_exact_nonoverlap_windows_and_availability(joint, decisions, variant, offsets, count):
    labels = v8.label_table(joint, decisions, variant, split="TRAIN")
    assert labels["label_valid"].all()
    for key, offset in zip(("flow_label_start_us", "flow_label_end_us", "return_label_start_us", "return_label_end_us"), offsets):
        assert np.array_equal(labels[key].to_numpy(), decisions + offset * 1_000_000)
    assert np.array_equal(labels["feature_available_us"].to_numpy(), decisions)
    assert np.array_equal(labels["earliest_permissible_order_us"].to_numpy(), decisions + 5_000_000)
    assert np.array_equal(labels["delayed_entry_us"].to_numpy(), decisions + offsets[2] * 1_000_000)
    assert np.array_equal(labels["label_mature_us"].to_numpy(), decisions + offsets[3] * 1_000_000)
    assert labels["split"].to_list() == ["TRAIN"] * 2
    for index, decision in enumerate(decisions):
        flow_rows = joint.filter(pl.col("timestamp").is_between(decision + offsets[0] * 1_000_000,
                                decision + offsets[1] * 1_000_000, closed="left"))
        assert len(flow_rows) == count
        buy, sell = flow_rows[f"{STREAMS[0]}__aggressive_buy_notional"].to_numpy(), flow_rows[f"{STREAMS[0]}__aggressive_sell_notional"].to_numpy()
        expected = np.sum(buy - sell) / (np.sum(buy + sell) + 1e-12)
        assert abs(labels[f"{STREAMS[0]}__future_flow"][index] - expected) < 1e-12
        stream = v8.RETURN_STREAMS[0]
        entry = joint.filter(pl.col("timestamp") == decision + offsets[2] * 1_000_000 - BAR_US)[f"{stream}__close"][0]
        exit_price = joint.filter(pl.col("timestamp") == decision + offsets[3] * 1_000_000 - BAR_US)[f"{stream}__close"][0]
        assert labels[f"{stream}__subsequent_return_proxy"][index] == exit_price / entry - 1
        assert labels[f"{stream}__entry_price_trade_us"][index] < labels["return_label_start_us"][index]
        assert labels[f"{stream}__exit_price_available_us"][index] == labels["return_label_end_us"][index]


def test_observed_future_flow_is_diagnostic_and_has_later_order(joint, decisions):
    labels = v8.label_table(joint, decisions, signal_kind="OBSERVED_FUTURE_FLOW_DIAGNOSTIC")
    assert np.array_equal(labels["earliest_order_us"].to_numpy(), decisions + 305_000_000)
    assert np.array_equal(labels["signal_available_us"].to_numpy(), decisions + 300_000_000)
    assert labels["signal_kind"][0] == "OBSERVED_FUTURE_FLOW_DIAGNOSTIC"


def test_future_perturbation_leaves_past_features_and_train_scaler_unchanged(joint, decisions):
    decision = decisions[0]
    before, available = v8.past_features(joint, decision)
    altered = joint.with_columns(*[
        pl.when(pl.col("timestamp") >= decision).then(pl.col(column) * 100 + 42).otherwise(pl.col(column)).alias(column)
        for column in joint.columns if column.endswith(("__close", "__return_5s", "__flow_imbalance", "__aggressive_buy_notional"))])
    after, second_available = v8.past_features(altered, decision)
    assert before.shape == (PAST_BARS, 68) and np.array_equal(before, after)
    assert available == second_available == decision
    values = np.vstack((before[:4, :3], after[:2, :3] + 10))
    ids, train = np.arange(6), np.arange(4)
    first = v8.fit_train_scaler(values[train], ids[train], train, np.full(4, decision), decision)
    values[4:] += 1e6  # validation/test mutation must never alter training statistics
    second = v8.fit_train_scaler(values[train], ids[train], train, np.full(4, decision), decision)
    assert np.array_equal(first.mean_, second.mean_) and np.array_equal(first.scale_, second.scale_)
    with pytest.raises(ValueError, match="declared train IDs"):
        v8.fit_train_scaler(values, ids, train, np.full(6, decision), decision)
    with pytest.raises(ValueError, match="Future/nonfinite"):
        v8.fit_train_scaler(values[train], train, train, np.full(4, decision + 1), decision)


def test_interval_mutation_and_future_availability_rejected(joint, decisions):
    labels = v8.label_table(joint, decisions)
    overlap = labels.with_columns((pl.col("flow_label_end_us") - 1).alias("return_label_start_us"))
    with pytest.raises(ValueError, match="overlap"):
        v8.assert_nonoverlap(overlap)
    future = joint.with_columns(pl.when(pl.col("timestamp") == decisions[0] - BAR_US)
        .then(pl.col(f"{STREAMS[0]}__available_us") + 1).otherwise(pl.col(f"{STREAMS[0]}__available_us")).alias(f"{STREAMS[0]}__available_us"))
    with pytest.raises(ValueError, match="Future row"):
        v8.past_features(future, decisions[0])
    with pytest.raises(ValueError, match="Feature availability"):
        v8.label_table(future, decisions)


def test_strict_split_cutoff_and_maturity():
    args = dict(validation_start_us=1000, embargo_us=100, max_label_lag_us=600, fitting_label_mature_us=[298])
    v8.assert_fit_chronology(fit_cutoff_us=299, **args)
    with pytest.raises(ValueError, match="strictly before"):
        v8.assert_fit_chronology(fit_cutoff_us=300, **args)
    with pytest.raises(ValueError, match="not mature"):
        v8.assert_fit_chronology(fit_cutoff_us=297, **args)


def receipt():
    return v8.OOFPredictionReceipt((10, 11), (1000, 1100), (1000, 1100), (0, 1, 2),
                                   (500, 600, 650), 700, 100, "a" * 64)


def test_flow_surprise_is_strictly_oof_predicted_minus_train_expectation():
    first, expectation = receipt(), replace(receipt(), model_sha256="b" * 64)
    predicted, expected = np.full((2, 4), .2), np.full((2, 4), .05)
    surprise = v8.flow_surprise(predicted, expected, first, expectation)
    assert np.allclose(surprise, .15)
    for bad in (replace(first, fit_row_ids=(0, 1, 10)),
                replace(first, fit_cutoff_us=950),
                replace(first, forecast_feature_available_us=(1001, 1100)),
                replace(first, fit_label_mature_us=(500, 600, 701))):
        with pytest.raises(ValueError):
            v8.flow_surprise(predicted, expected, bad, expectation)
    with pytest.raises(ValueError, match="OOF forecast row"):
        v8.flow_surprise(predicted, expected, first, replace(expectation, fit_row_ids=(0, 1, 11)))


def test_fixed_official_conditional_expectation_only_train_rows():
    x = np.asarray([[1., 2], [2., 3], [3., 5]])
    y = np.tile(np.asarray([.1, .2, .3])[:, None], (1, 4))
    model, scaler = v8.fit_conditional_expectation(x, y, [0, 1, 2], [0, 1, 2], [100, 200, 300], [500, 600, 650], 700)
    assert model.alpha == 1 and model.predict(scaler.transform(x)).shape == (3, 4)
    assert scaler.n_samples_seen_ == 3
    with pytest.raises(ValueError, match="declared train IDs"):
        v8.fit_conditional_expectation(x, y, [0, 1, 3], [0, 1, 2], [100, 200, 300], [500, 600, 650], 700)


def test_matched_direct_returns_share_all_bindings(joint, decisions):
    labels = v8.label_table(joint, decisions)
    direct = v8.direct_return_labels(labels)
    for name in v8.RETURN_COLUMNS:
        assert direct[name].equals(labels[name])
    assert direct["decision_us"].equals(labels["decision_us"])
    binding = {key: "a" * 64 for key in v8.MATCH_KEYS}
    binding.update(endpoint_ids=[0, 1, 2], train_ids=[0], validation_ids=[1], test_ids=[2],
                   decision_frequency_seconds=60, label_variant="LEAD_LAG_5M_5M")
    assert len(v8.assert_matched_direct_baseline(binding, dict(binding))) == 64
    for field in ("endpoint_ids", "feature_set_sha256", "cost_model_sha256", "position_constraints_sha256"):
        changed = dict(binding)
        changed[field] = [0, 1, 3] if field == "endpoint_ids" else "b" * 64
        with pytest.raises(ValueError, match="mismatch"):
            v8.assert_matched_direct_baseline(binding, changed)


def test_missing_anchor_is_invalid_and_locked_grid_rejected(joint, decisions):
    stream = v8.RETURN_STREAMS[0]
    missing = joint.with_columns(pl.when(pl.col("timestamp") == decisions[0] + 600_000_000 - BAR_US)
        .then(None).otherwise(pl.col(f"{stream}__close")).alias(f"{stream}__close"))
    labels = v8.label_table(missing, decisions)
    assert not labels["label_valid"][0] and np.isnan(labels[f"{stream}__subsequent_return_proxy"][0])
    late = joint.with_columns((pl.col("timestamp") + day_us(date(2026, 3, 1)) - joint["timestamp"][0]).alias("timestamp"))
    with pytest.raises(ValueError, match="locked access forbidden"):
        v8.label_table(late, decisions)
