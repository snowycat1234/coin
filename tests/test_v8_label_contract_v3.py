"""Actual V2 audit regressions across V3 public receipt entry points, synthetic."""
from pathlib import Path
import sys
from dataclasses import replace

import numpy as np
import polars as pl
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts/research_v8"))
import labels_v3 as v8
from test_v8_label_contract import joint, decisions


def split_fixture(joint):
    start = int(joint["timestamp"][0])
    frames = [v8.label_table(joint, np.asarray([start + seconds * 1_000_000]), split=split)
              for seconds, split in ((1320, "TRAIN"), (3000, "VALIDATION"), (4200, "OOS_SCREENING"))]
    labels = pl.concat(frames)
    kwargs = dict(train_ids=[start + 1320_000_000], validation_ids=[start + 3000_000_000], test_ids=[start + 4200_000_000],
        fit_cutoff_us=start + 2100_000_000, validation_start_us=start + 3000_000_000,
        test_start_us=start + 4200_000_000, test_end_us=start + 4900_000_000, embargo_us=100_000_000, max_label_lag_us=600_000_000)
    return labels, kwargs


@pytest.mark.parametrize("variant", ["LEAD_LAG_5M_5M", "EARLY_LATE_150S_GAP5", "EARLY_LATE_150S_GAP10"])
def test_valid_integer_schema_and_exact_registered_windows(joint, decisions, variant):
    labels = v8.label_table(joint, decisions, variant)
    assert labels["label_valid"].all() and v8.assert_nonoverlap(labels)
    assert all(dtype == pl.Int64 for name, dtype in labels.schema.items() if name.endswith("_us"))
    assert v8.direct_return_labels(labels)[v8.RETURN_COLUMNS[0]].equals(labels[v8.RETURN_COLUMNS[0]])


def test_locked_translation_rejected_by_all_export_score_paths(joint):
    labels, kwargs = split_fixture(joint)
    delta = v8.END - int(joint["timestamp"][0])
    shifted = labels.with_columns(*[(pl.col(name) + delta).alias(name) for name in labels.columns if name.endswith("_us")])
    changed = {key: [value + delta for value in values] if key.endswith("_ids") else values + delta if key.endswith("_us") and key not in ("embargo_us", "max_label_lag_us") else values for key, values in kwargs.items()}
    for function in (v8.assert_nonoverlap, v8.direct_return_labels):
        with pytest.raises(ValueError, match="locked"):
            function(shifted)
    with pytest.raises(ValueError, match="locked"):
        v8.assert_split_chronology(shifted, **changed)
    valid = v8.assert_split_chronology(labels, **kwargs)
    assert valid["integer_development_domain_and_row_alignment_verified"]


@pytest.mark.parametrize("values", [[1751329800000000.5], np.asarray([1751329800000000.], float), np.asarray([[1751329800000000]], int)])
def test_original_decisions_reject_fraction_float_and_dimensions(joint, values):
    with pytest.raises(ValueError, match="original integer metadata"):
        v8.label_table(joint, values)


def test_standalone_fit_cannot_broadcast(joint):
    start = int(joint["timestamp"][0])
    args = dict(fit_cutoff_us=start + 2450_000_000, validation_start_us=start + 3500_000_000,
        embargo_us=100_000_000, max_label_lag_us=920_000_000,
        fitting_label_mature_us=[start + 2300_000_000, start + 1980_000_000],
        fitting_decision_us=[start + 1380_000_000])
    with pytest.raises(ValueError, match="equal shape"):
        v8.assert_fit_chronology(**args)
    with pytest.raises(ValueError, match="actual observed label lag"):
        v8.assert_fit_chronology(**{**args, "fitting_decision_us": [start + 1320_000_000, start + 1380_000_000]})


@pytest.mark.parametrize("field", ["fit_cutoff_us", "validation_start_us", "test_start_us", "test_end_us"])
def test_split_boundaries_cannot_cross_development_or_use_floats(joint, field):
    labels, kwargs = split_fixture(joint)
    with pytest.raises(ValueError):
        v8.assert_split_chronology(labels, **{**kwargs, field: v8.END + 1})
    with pytest.raises(ValueError, match="original integer timestamp"):
        v8.assert_split_chronology(labels, **{**kwargs, field: float(kwargs[field])})


def test_valid_future_flow_units_checked_export_and_split(joint):
    labels, kwargs = split_fixture(joint)
    changed = labels.with_columns(pl.lit(100.).alias(v8.FLOW_COLUMNS[0]))
    with pytest.raises(ValueError, match="future-flow ratio"):
        v8.assert_nonoverlap(changed)
    with pytest.raises(ValueError, match="future-flow ratio"):
        v8.assert_split_chronology(changed, **kwargs)


def test_exported_fractional_timestamp_schema_rejected(joint, decisions):
    labels = v8.label_table(joint, decisions)
    changed = labels.with_columns((pl.col("flow_label_mature_us").cast(pl.Float64) + .5).alias("flow_label_mature_us"))
    with pytest.raises(ValueError, match="integer timestamp schema"):
        v8.assert_nonoverlap(changed)


def test_source_known_fractional_metadata_rejected(joint, decisions):
    stream = v8.STREAMS[0]
    changed = joint.with_columns((pl.col(f"{stream}__available_us").cast(pl.Float64) + .5).alias(f"{stream}__available_us"))
    with pytest.raises(ValueError, match="fractional source timestamp"):
        v8.label_table(changed, decisions)


def test_unknown_future_metadata_stays_nullable_and_unfit(joint, decisions):
    stream = v8.STREAMS[0]
    changed = joint.with_columns(pl.when(pl.col("timestamp") == decisions[0] + 5_000_000).then(float("nan"))
        .otherwise(pl.col(f"{stream}__available_us")).alias(f"{stream}__available_us"))
    labels = v8.label_table(changed, decisions[:1])
    assert labels.schema["label_mature_us"] == pl.Int64 and labels["label_mature_us"][0] is None
    assert not labels["label_valid"][0] and np.isnan(labels[v8.FLOW_COLUMNS[0]][0])


def test_scaler_and_expectation_guard_dates_alignment(joint):
    start = int(joint["timestamp"][0])
    x = np.asarray([[1., 2], [2., 3], [3., 4]])
    available = [start + 100, start + 200, start + 300]
    scaler = v8.fit_train_scaler(x, [0, 1, 2], [0, 1, 2], available, start + 700)
    assert scaler.n_samples_seen_ == 3
    with pytest.raises(ValueError, match="locked"):
        v8.fit_train_scaler(x, [0, 1, 2], [0, 1, 2], [v8.END] * 3, v8.END + 700)
    with pytest.raises(ValueError, match="equal shape"):
        v8.fit_conditional_expectation(x, np.full((3, 4), .2), [0, 1, 2], [0, 1, 2], available, [start + 650], start + 700)


def test_oof_all_timestamp_entries_are_integer_development(joint):
    start = int(joint["timestamp"][0])
    good = v8.OOFPredictionReceipt((10, 11), (start + 1800_000_000, start + 1860_000_000), (start + 1800_000_000, start + 1860_000_000),
                                 (0, 1, 2), (start + 500_000_000, start + 600_000_000, start + 650_000_000), start + 700_000_000, 100_000_000, "a" * 64)
    assert np.allclose(v8.flow_surprise(np.full((2, 4), .2), np.full((2, 4), .05), good, good), .15)
    for bad in (replace(good, forecast_decision_us=(v8.END + 1000, v8.END + 1100)),
                replace(good, fit_label_mature_us=(v8.END, v8.END, v8.END)),
                replace(good, forecast_feature_available_us=(float(start + 1000), float(start + 1100))),
                replace(good, fit_cutoff_us=float(start + 700))):
        with pytest.raises(ValueError):
            v8.flow_surprise(np.full((2, 4), .2), np.full((2, 4), .05), bad, good)
