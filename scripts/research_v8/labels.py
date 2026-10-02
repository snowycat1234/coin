"""V8 nonoverlapping labels and minimal official-model chronology guards.

This is an offline target adapter, not an execution or model framework. Frozen
V7 features and labels are retained unchanged. No file/data discovery occurs.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import polars as pl
from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler

from quant.paths import ROOT
from quant.research_fast.dataset import (
    BAR_US, LOCKED, PAST_BARS, START, STREAMS, day_us, feature_matrix,
)

US = 1_000_000
EPS = 1e-12
RETURN_STREAMS = ("spot_BTCUSDT", "spot_ETHUSDT")
FLOW_COLUMNS = tuple(f"{s}__future_flow" for s in STREAMS)
RETURN_COLUMNS = tuple(f"{s}__subsequent_return_proxy" for s in RETURN_STREAMS)
CONTRACT_PATH = ROOT / "protocols/LABEL_CONTRACT_V8.json"


def require(condition, message):
    if not bool(condition):
        raise ValueError(message)


def contract():
    value = json.loads(CONTRACT_PATH.read_text())
    require(value["version"] == "LABEL_CONTRACT_V8_20261002_V1", "Explicit V8 label version required")
    return value


def _dense(joint):
    times = joint["timestamp"].to_numpy()
    require(len(times) > 0 and np.all(np.diff(times) == BAR_US), "Exact dense 5s source, no interpolation")
    require(times[0] >= day_us(START) and times[-1] + BAR_US <= day_us(LOCKED), "Development dates only; locked access forbidden")
    for stream in STREAMS:
        available = joint[f"{stream}__available_us"].to_numpy()
        require(np.isfinite(available).all() and np.all(available >= times + BAR_US), "Source availability cannot precede close")
    return times


def past_features(joint, decision_us):
    """Unchanged 68 features from the exact closed past256; reject future rows."""
    _dense(joint)
    past = joint.filter(pl.col("timestamp").is_between(
        int(decision_us) - PAST_BARS * BAR_US, int(decision_us), closed="left"))
    require(len(past) == PAST_BARS, "Full past256 is required")
    available = max(past[f"{s}__available_us"].max() for s in STREAMS)
    require(available <= decision_us, "Future row in input features")
    require(all(past[f"{s}__quality"].eq(0).all() for s in STREAMS), "Past source quality invalid")
    return feature_matrix(past), int(available)


def _positions(times, stamps):
    positions = np.searchsorted(times, stamps)
    require(np.all(positions < len(times)) and np.array_equal(times[positions], stamps), "Required label anchor outside explicit source")
    return positions


def _range_max(values, starts, stops):
    return np.asarray([np.max(values[a:b]) for a, b in zip(starts, stops)])


def label_table(joint, decisions, variant="LEAD_LAG_5M_5M", *, split="DEVELOPMENT_DIAGNOSTIC",
                signal_kind="PAST_ONLY_PREDICTED_FLOW"):
    """Four future flow labels and two exact nonoverlapping Spot return proxies.

Flow boundaries refer to close availability, (start,end]. The price labels use
closed-bar boundary prices, never fabricated orders at an unknown BBO.
"""
    spec = contract()["labels"].get(variant)
    require(spec is not None, "Only registered V8 label variants")
    require(split in ("TRAIN", "VALIDATION", "OOS_SCREENING", "DEVELOPMENT_DIAGNOSTIC"), "Explicit research split classification required")
    require(signal_kind in ("PAST_ONLY_PREDICTED_FLOW", "OBSERVED_FUTURE_FLOW_DIAGNOSTIC"), "Explicit signal availability mode required")
    times = _dense(joint)
    decisions = np.asarray(decisions, dtype=np.int64)
    require(decisions.ndim == 1 and len(decisions) > 0 and np.all(np.diff(decisions) > 0), "Unique chronological explicit decision IDs required")
    require(np.all(decisions % (60 * US) == 0), "Frozen minute decision frequency")
    flow_start = decisions + spec["flow_start_offset_seconds"] * US
    flow_end = decisions + spec["flow_end_offset_seconds"] * US
    return_start = decisions + spec["return_start_offset_seconds"] * US
    return_end = decisions + spec["return_end_offset_seconds"] * US
    require(np.all(return_start - flow_end == spec["latency_gap_seconds"] * US), "Flow and return intervals overlap or gap changed")
    require(return_end[-1] <= day_us(LOCKED), "Labels would consume locked dates")
    first_flow = _positions(times, flow_start)
    last_flow = _positions(times, flow_end - BAR_US) + 1
    entry = _positions(times, return_start - BAR_US)
    exit_row = _positions(times, return_end - BAR_US)
    decision_row = _positions(times, decisions - BAR_US)
    first_past = _positions(times, decisions - PAST_BARS * BAR_US)
    require(np.all(last_flow - first_flow == spec["flow_bars"]), "Registered exact flow bar count changed")
    availability = np.column_stack([joint[f"{s}__available_us"].to_numpy() for s in STREAMS]).max(axis=1)
    feature_available = _range_max(availability, first_past, decision_row + 1)
    require(np.all(feature_available <= decisions), "Feature availability after decision")
    flow_mature = _range_max(availability, first_flow, last_flow)
    return_mature = _range_max(availability, entry, exit_row + 1)
    maturity = np.maximum(flow_mature, return_mature)
    signal_available = decisions if signal_kind == "PAST_ONLY_PREDICTED_FLOW" else flow_mature
    earliest_order = signal_available + 5 * US
    require(np.all(earliest_order <= return_start), "Signal plus latency not available before registered delayed entry")
    quality = np.column_stack([joint[f"{s}__quality"].to_numpy() for s in STREAMS])
    require(all(np.all(quality[a:b] == 0) for a, b in zip(first_past, decision_row + 1)), "Past source quality invalid")
    valid = np.asarray([np.all(quality[a:b] == 0) for a, b in zip(first_flow, exit_row + 1)])
    columns = {"decision_us": decisions, "feature_available_us": feature_available,
        "predicted_signal_available_us": decisions, "signal_available_us": signal_available,
        "earliest_order_us": earliest_order, "earliest_permissible_order_us": earliest_order,
        "delayed_entry_us": return_start,
        "flow_label_start_us": flow_start, "flow_label_end_us": flow_end,
        "flow_label_mature_us": flow_mature, "observed_future_flow_available_us": flow_mature,
        "return_label_start_us": return_start, "return_label_end_us": return_end,
        "return_label_mature_us": return_mature, "label_mature_us": maturity,
        "label_variant": [variant] * len(decisions), "flow_return_overlap": [False] * len(decisions),
        "split": [split] * len(decisions), "signal_kind": [signal_kind] * len(decisions),
        "price_proxy_kind": ["CLOSED_BAR_RETURN_PROXY_NOT_EXECUTABLE_FILL"] * len(decisions)}
    for stream in STREAMS:
        buy = joint[f"{stream}__aggressive_buy_notional"].to_numpy()
        sell = joint[f"{stream}__aggressive_sell_notional"].to_numpy()
        require(np.isfinite(buy).all() and np.isfinite(sell).all() and np.all(buy >= 0) and np.all(sell >= 0), "Finite nonnegative aggressive notionals")
        net, total = np.r_[0., np.cumsum(buy - sell)], np.r_[0., np.cumsum(buy + sell)]
        flow = (net[last_flow] - net[first_flow]) / (total[last_flow] - total[first_flow] + EPS)
        columns[f"{stream}__future_flow"] = flow
        valid &= np.isfinite(flow) & (np.abs(flow) <= 1 + 1e-12)
    for stream in RETURN_STREAMS:
        prices = joint[f"{stream}__close"].to_numpy()
        trade_times = joint[f"{stream}__last_trade_us"].to_numpy()
        with np.errstate(invalid="ignore", divide="ignore"):
            returns = prices[exit_row] / prices[entry] - 1
        anchor_valid = (np.isfinite(prices[entry]) & np.isfinite(prices[exit_row]) & (prices[entry] > 0) & (prices[exit_row] > 0)
            & np.isfinite(trade_times[entry]) & np.isfinite(trade_times[exit_row])
            & (trade_times[entry] >= return_start - BAR_US) & (trade_times[entry] < return_start)
            & (trade_times[exit_row] >= return_end - BAR_US) & (trade_times[exit_row] < return_end)
            & (trade_times[entry] < trade_times[exit_row]))
        valid &= anchor_valid & np.isfinite(returns)
        columns[f"{stream}__subsequent_return_proxy"] = returns
        columns[f"{stream}__entry_price_proxy"] = prices[entry]
        columns[f"{stream}__exit_price_proxy"] = prices[exit_row]
        columns[f"{stream}__entry_price_trade_us"] = trade_times[entry]
        columns[f"{stream}__exit_price_trade_us"] = trade_times[exit_row]
        columns[f"{stream}__entry_price_available_us"] = joint[f"{stream}__available_us"].to_numpy()[entry]
        columns[f"{stream}__exit_price_available_us"] = joint[f"{stream}__available_us"].to_numpy()[exit_row]
    columns["label_valid"] = valid
    for name in (*FLOW_COLUMNS, *RETURN_COLUMNS):
        columns[name] = np.where(valid, columns[name], np.nan)
    result = pl.DataFrame(columns)
    assert_nonoverlap(result)
    return result


def assert_nonoverlap(labels):
    require(np.all(labels["feature_available_us"].to_numpy() <= labels["decision_us"].to_numpy()), "Future feature overlap")
    require(np.all(labels["flow_label_start_us"].to_numpy() >= labels["decision_us"].to_numpy()), "Flow before registered decision")
    require(np.all(labels["return_label_start_us"].to_numpy() >= labels["flow_label_end_us"].to_numpy() + 5 * US), "Signal observation and return label overlap")
    require(np.array_equal(labels["delayed_entry_us"].to_numpy(), labels["return_label_start_us"].to_numpy()), "Pre-registered delayed entry changed")
    require(np.array_equal(labels["earliest_order_us"].to_numpy(), labels["signal_available_us"].to_numpy() + 5 * US), "Actual signal availability plus fixed latency changed")
    require(np.array_equal(labels["earliest_order_us"].to_numpy(), labels["earliest_permissible_order_us"].to_numpy()), "Earliest-order timestamp aliases disagree")
    require(np.all(labels["earliest_permissible_order_us"].to_numpy() <= labels["delayed_entry_us"].to_numpy()), "Order becomes available after active delayed entry")
    require(np.all(labels["label_mature_us"].to_numpy() >= labels["return_label_end_us"].to_numpy()), "Label maturity precedes end")


def assert_fit_chronology(*, fit_cutoff_us, validation_start_us, embargo_us, max_label_lag_us, fitting_label_mature_us):
    require(embargo_us >= 0 and max_label_lag_us > 0, "Explicit nonnegative embargo and positive maximum lag")
    require(fit_cutoff_us < validation_start_us - embargo_us - max_label_lag_us, "Fit cutoff must be strictly before validation - embargo - max lag")
    require(np.all(np.asarray(fitting_label_mature_us) <= fit_cutoff_us), "Fitting label not mature at actual cutoff")


def fit_train_scaler(values, row_ids, train_ids, available_us, fit_cutoff_us):
    """Official scaler fits exactly supplied train IDs; future/held-out rows reject."""
    values, ids = np.asarray(values), np.asarray(row_ids)
    train_ids, available = np.asarray(train_ids), np.asarray(available_us)
    require(len(ids) == len(values) == len(available) and len(ids) >= 2, "Aligned scaler rows")
    require(len(set(ids.tolist())) == len(ids) and len(set(train_ids.tolist())) == len(train_ids)
            and set(ids.tolist()) == set(train_ids.tolist()), "Scaler rows must equal declared train IDs")
    require(np.all(available <= fit_cutoff_us) and np.isfinite(values).all(), "Future/nonfinite scaler fitting inputs")
    return StandardScaler().fit(values)


@dataclass(frozen=True)
class OOFPredictionReceipt:
    forecast_row_ids: tuple
    forecast_decision_us: tuple
    forecast_feature_available_us: tuple
    fit_row_ids: tuple
    fit_label_mature_us: tuple
    fit_cutoff_us: int
    embargo_us: int
    model_sha256: str

    def validate(self):
        require(len(self.forecast_row_ids) == len(self.forecast_decision_us) == len(self.forecast_feature_available_us) > 0, "Aligned OOF forecast receipt")
        require(np.all(np.diff(self.forecast_decision_us) > 0), "OOF forecast decisions must be chronological")
        require(len(self.fit_row_ids) == len(self.fit_label_mature_us) > 0, "Aligned OOF fitting receipt")
        require(len(set(self.forecast_row_ids)) == len(self.forecast_row_ids) and len(set(self.fit_row_ids)) == len(self.fit_row_ids), "Duplicate row ID in OOF receipt")
        require(not set(self.forecast_row_ids) & set(self.fit_row_ids), "OOF forecast row was fitted by this model")
        require(len(self.model_sha256) == 64 and all(c in "0123456789abcdef" for c in self.model_sha256), "Saved predictor SHA required")
        require(self.embargo_us >= 0, "Negative OOF embargo")
        require(np.all(np.asarray(self.forecast_feature_available_us) <= self.forecast_decision_us), "OOF prediction uses future features")
        require(max(self.fit_label_mature_us) <= self.fit_cutoff_us, "OOF labels immature at fit")
        require(self.fit_cutoff_us + self.embargo_us < min(self.forecast_decision_us), "OOF fit must precede forecast with embargo")
        require(max(self.fit_label_mature_us) + self.embargo_us < min(self.forecast_decision_us), "OOF matured fitting labels overlap forecast")


def flow_surprise(predicted_flow, conditional_expectation, prediction_receipt, expectation_receipt):
    """Original-unit strictly OOF predictions minus train-only expectation."""
    prediction_receipt.validate()
    expectation_receipt.validate()
    require(prediction_receipt.forecast_row_ids == expectation_receipt.forecast_row_ids
            and prediction_receipt.forecast_decision_us == expectation_receipt.forecast_decision_us, "Prediction components must share exact forecast IDs/timestamps")
    forecast, expected = np.asarray(predicted_flow), np.asarray(conditional_expectation)
    require(forecast.shape == expected.shape == (len(prediction_receipt.forecast_row_ids), 4), "Same four original-unit flow outputs required")
    require(np.isfinite(forecast).all() and np.isfinite(expected).all(), "Finite OOF prediction components")
    return forecast - expected


def fit_conditional_expectation(features, flow_targets, row_ids, train_ids, feature_available_us,
                               label_mature_us, fit_cutoff_us):
    """Thin fixed official Ridge+scaler fit; caller saves model SHA for OOF receipt."""
    targets = np.asarray(flow_targets)
    require(targets.shape == (len(row_ids), 4) and np.isfinite(targets).all(), "Four train-only flow targets")
    require(len(label_mature_us) == len(row_ids), "Aligned expectation label maturity")
    require(np.all(np.asarray(label_mature_us) <= fit_cutoff_us), "Expectation target immature at cutoff")
    scaler = fit_train_scaler(features, row_ids, train_ids, feature_available_us, fit_cutoff_us)
    model = Ridge(alpha=1.0).fit(scaler.transform(np.asarray(features)), targets)
    return model, scaler


def direct_return_labels(labels):
    """Select matched direct targets from the identical frame, never recompute."""
    assert_nonoverlap(labels)
    names = [name for name in labels.columns if "__future_flow" not in name]
    return labels.select(names)


MATCH_KEYS = ("endpoint_ids", "train_ids", "validation_ids", "test_ids", "dataset_sha256",
              "feature_set_sha256", "protocol_sha256", "cost_model_sha256",
              "position_constraints_sha256", "decision_frequency_seconds", "label_variant")


def assert_matched_direct_baseline(pipeline_binding, direct_binding):
    for key in MATCH_KEYS:
        require(key in pipeline_binding and key in direct_binding and pipeline_binding[key] == direct_binding[key], f"Direct baseline mismatch: {key}")
    require(pipeline_binding["decision_frequency_seconds"] == 60, "Frozen decision frequency changed")
    ids = pipeline_binding["endpoint_ids"]
    require(len(ids) == len(set(ids)), "Duplicate matched endpoint")
    splits = [set(pipeline_binding[key]) for key in ("train_ids", "validation_ids", "test_ids")]
    require(all(rows <= set(ids) for rows in splits) and all(not splits[a] & splits[b] for a, b in ((0, 1), (0, 2), (1, 2))), "Matched split IDs invalid or overlapping")
    return hashlib.sha256(json.dumps({k: pipeline_binding[k] for k in MATCH_KEYS}, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
