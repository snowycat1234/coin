"""V8 label V3: common integer/development/shape guards over preserved V2.

Preserved V1/V2/contract bytes are not mutated. Thin wrappers validate original
metadata before calling existing official-model/target adapters; no data IO.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import polars as pl
from sklearn.linear_model import Ridge

if __package__:
    from . import labels_v2 as _v2
else:
    import labels_v2 as _v2

from quant.research_fast.dataset import LOCKED, START, day_us

IMPLEMENTATION_VERSION = "V8_LABELS_V3_20261002"
US, EPS, BAR_US, STREAMS = _v2.US, _v2.EPS, _v2.BAR_US, _v2.STREAMS
RETURN_STREAMS, FLOW_COLUMNS, RETURN_COLUMNS = _v2.RETURN_STREAMS, _v2.FLOW_COLUMNS, _v2.RETURN_COLUMNS
MATCH_KEYS, contract, require = _v2.MATCH_KEYS, _v2.contract, _v2.require
BEGIN, END = day_us(START), day_us(LOCKED)


def _integer_array(values, name, *, nonempty=True):
    raw = np.asarray(values)
    require(raw.ndim == 1 and (len(raw) > 0 or not nonempty)
            and np.issubdtype(raw.dtype, np.integer) and raw.dtype != np.bool_,
            f"{name}: one-dimensional original integer metadata required; no float coercion/broadcast")
    # Compare before any int64 cast so an unsigned overflow cannot wrap to valid.
    require(np.all(raw >= np.iinfo(np.int64).min) and np.all(raw <= np.iinfo(np.int64).max), f"{name}: int64 overflow")
    return raw.astype(np.int64, copy=False)


def _timestamps(values, name, *, allow_end=False):
    raw = _integer_array(values, name)
    require(np.all(raw >= BEGIN) and np.all(raw <= END if allow_end else raw < END),
            f"{name}: development dates only; locked timestamps forbidden")
    return raw


def _stamp(value, name, *, allow_end=False):
    require(isinstance(value, (int, np.integer)) and not isinstance(value, (bool, np.bool_)),
            f"{name}: original integer timestamp required")
    return int(_timestamps([value], name, allow_end=allow_end)[0])


def _duration(value, name, *, positive=False):
    require(isinstance(value, (int, np.integer)) and not isinstance(value, (bool, np.bool_))
            and (value > 0 if positive else value >= 0), f"{name}: integer nonnegative duration required")
    return int(value)


def _aligned_timestamps(first, second, names):
    a = _timestamps(first, names[0])
    b = _timestamps(second, names[1], allow_end=True)
    require(a.shape == b.shape, "Timestamp row metadata must have equal shape; broadcasting forbidden")
    return a, b


def _minute_decisions(values, name):
    values = _timestamps(values, name)
    require(np.all(values % (60 * US) == 0), f"{name}: frozen minute decision grid required")
    return values


def _source_timestamps(joint):
    _timestamps(joint["timestamp"].to_numpy(), "source timestamp")
    for name in joint.columns:
        if name.endswith("_us") and name != "timestamp":
            values = joint[name].to_numpy()
            # Unknown source metadata is allowed to invalidate its own label.
            # Every known value still has to be in the exact integer domain.
            finite = np.isfinite(values)
            require(np.all(values[finite] == np.floor(values[finite])), f"{name}: fractional source timestamp")
            require(np.all(values[finite] >= BEGIN) and np.all(values[finite] <= END), f"{name}: locked source metadata")


def _as_v2(labels):
    return labels.with_columns(pl.lit(_v2.IMPLEMENTATION_VERSION).alias("implementation_version"))


def _nullable_integer_output(labels):
    names = [name for name in labels.columns if name.endswith("_us")]
    expressions = []
    for name in names:
        values = labels[name].to_numpy()
        finite = np.isfinite(values)
        require(np.all(values[finite] == np.floor(values[finite])), f"{name}: generated fractional timestamp")
        expressions.append(pl.when(pl.col(name).is_nan()).then(None).otherwise(pl.col(name)).cast(pl.Int64).alias(name))
    return labels.with_columns(*expressions, pl.lit(IMPLEMENTATION_VERSION).alias("implementation_version"))


def label_table(joint, decisions, variant="LEAD_LAG_5M_5M", *, split="DEVELOPMENT_DIAGNOSTIC",
                signal_kind="PAST_ONLY_PREDICTED_FLOW"):
    decisions = _minute_decisions(decisions, "decision")
    _source_timestamps(joint)
    result = _nullable_integer_output(_v2.label_table(joint, decisions, variant, split=split, signal_kind=signal_kind))
    assert_nonoverlap(result)
    return result


def past_features(joint, decision_us):
    decision_us = _stamp(decision_us, "feature decision")
    _minute_decisions([decision_us], "feature decision")
    past = joint.filter(pl.col("timestamp").is_between(decision_us - _v2.PAST_BARS * BAR_US, decision_us, closed="left"))
    _source_timestamps(past)
    return _v2.past_features(past, decision_us)


def assert_nonoverlap(labels):
    require(len(labels) > 0 and set(labels["implementation_version"].to_list()) == {IMPLEMENTATION_VERSION}, "Active V3 implementation required")
    for name in labels.columns:
        if name.endswith("_us"):
            require(labels.schema[name] in (pl.Int64, pl.UInt64), f"{name}: exported integer timestamp schema required")
            # Nullable unknowns remain unknown; neither dropping rows nor zero
            # replacement is allowed, and the complete split guard rejects them.
            known = labels[name].drop_nulls().to_numpy()
            if len(known):
                _timestamps(known, name, allow_end=name not in ("decision_us", "feature_available_us", "predicted_signal_available_us"))
    for name in FLOW_COLUMNS:
        if name in labels.columns:
            values = labels[name].to_numpy()[labels["label_valid"].to_numpy()]
            require(np.isfinite(values).all() and np.all(np.abs(values) <= 1 + 1e-12), "Valid future-flow ratio must stay in [-1,1]; no bps-unit corruption")
    return _v2.assert_nonoverlap(_as_v2(labels))


def direct_return_labels(labels):
    assert_nonoverlap(labels)
    return labels.select([name for name in labels.columns if "__future_flow" not in name])


def assert_fit_chronology(*, fit_cutoff_us, validation_start_us, embargo_us, max_label_lag_us,
                         fitting_label_mature_us, fitting_decision_us):
    decisions, maturity = _aligned_timestamps(fitting_decision_us, fitting_label_mature_us, ("fitting decision", "fitting maturity"))
    _minute_decisions(decisions, "fitting decision")
    fit_cutoff_us = _stamp(fit_cutoff_us, "fit cutoff")
    validation_start_us = _stamp(validation_start_us, "validation start")
    embargo_us, max_label_lag_us = _duration(embargo_us, "embargo"), _duration(max_label_lag_us, "max lag", positive=True)
    return _v2.assert_fit_chronology(fit_cutoff_us=fit_cutoff_us, validation_start_us=validation_start_us,
        embargo_us=embargo_us, max_label_lag_us=max_label_lag_us,
        fitting_label_mature_us=maturity, fitting_decision_us=decisions)


def assert_split_chronology(labels, *, train_ids, validation_ids, test_ids, fit_cutoff_us,
                            validation_start_us, test_start_us, test_end_us, embargo_us,
                            max_label_lag_us, row_id_column="decision_us"):
    assert_nonoverlap(labels)
    scalars = {name: _stamp(value, name, allow_end=name == "test_end_us") for name, value in
        (("fit_cutoff_us", fit_cutoff_us), ("validation_start_us", validation_start_us),
         ("test_start_us", test_start_us), ("test_end_us", test_end_us))}
    embargo_us, max_label_lag_us = _duration(embargo_us, "embargo"), _duration(max_label_lag_us, "max lag", positive=True)
    if row_id_column.endswith("_us"):
        for name, ids in (("train IDs", train_ids), ("validation IDs", validation_ids), ("test IDs", test_ids)):
            _timestamps(ids, name)
    result = _v2.assert_split_chronology(_as_v2(labels), train_ids=train_ids, validation_ids=validation_ids,
        test_ids=test_ids, **scalars, embargo_us=embargo_us, max_label_lag_us=max_label_lag_us,
        row_id_column=row_id_column)
    result["implementation_version"] = IMPLEMENTATION_VERSION
    result["integer_development_domain_and_row_alignment_verified"] = True
    return result


def fit_train_scaler(values, row_ids, train_ids, available_us, fit_cutoff_us):
    values = np.asarray(values)
    available = _timestamps(available_us, "scaler fitting availability")
    require(values.ndim == 2 and len(values) == len(available) and np.asarray(row_ids).ndim == np.asarray(train_ids).ndim == 1,
            "Aligned two-dimensional scaler values and one-dimensional row metadata")
    return _v2.fit_train_scaler(values, row_ids, train_ids, available, _stamp(fit_cutoff_us, "scaler fit cutoff"))


def fit_conditional_expectation(features, flow_targets, row_ids, train_ids, feature_available_us,
                               label_mature_us, fit_cutoff_us):
    available, maturity = _aligned_timestamps(feature_available_us, label_mature_us, ("expectation feature availability", "expectation label maturity"))
    targets = np.asarray(flow_targets)
    require(targets.shape == (len(available), 4) and np.isfinite(targets).all() and np.all(np.abs(targets) <= 1 + 1e-12), "Aligned original-unit expectation flow ratios")
    # Calling the V3 scaler entry point validates all row shapes/date/cutoff.
    scaler = fit_train_scaler(features, row_ids, train_ids, available, fit_cutoff_us)
    require(np.all(maturity <= fit_cutoff_us), "Expectation target immature at cutoff")
    return Ridge(alpha=1.0).fit(scaler.transform(np.asarray(features)), targets), scaler


def _validate_oof(receipt):
    decisions = _minute_decisions(receipt.forecast_decision_us, "OOF forecast decision")
    available = _timestamps(receipt.forecast_feature_available_us, "OOF feature availability")
    maturity = _timestamps(receipt.fit_label_mature_us, "OOF fitting maturity", allow_end=True)
    require(decisions.shape == available.shape and len(decisions) == len(receipt.forecast_row_ids)
            and len(maturity) == len(receipt.fit_row_ids), "Aligned nonbroadcast OOF metadata")
    _stamp(receipt.fit_cutoff_us, "OOF fit cutoff")
    _duration(receipt.embargo_us, "OOF embargo")
    # Invoke the unchanged chronology/disjoint-row checks without changing type.
    _v2.OOFPredictionReceipt.validate(receipt)


@dataclass(frozen=True)
class OOFPredictionReceipt(_v2.OOFPredictionReceipt):
    def validate(self):
        _validate_oof(self)


def flow_surprise(predicted_flow, conditional_expectation, prediction_receipt, expectation_receipt):
    _validate_oof(prediction_receipt)
    _validate_oof(expectation_receipt)
    return _v2.flow_surprise(predicted_flow, conditional_expectation, prediction_receipt, expectation_receipt)


def assert_matched_direct_baseline(pipeline_binding, direct_binding):
    # Bind the matching entry point to this implementation, not only old spec ID.
    require(pipeline_binding.get("label_implementation_version") == direct_binding.get("label_implementation_version") == IMPLEMENTATION_VERSION,
            "Matched comparison must bind active V3 implementation")
    return _v2.assert_matched_direct_baseline(pipeline_binding, direct_binding)
