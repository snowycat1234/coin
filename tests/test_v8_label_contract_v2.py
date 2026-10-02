"""V2 regressions for the actual independent audit counterexamples, synthetic only."""
from pathlib import Path
import sys

import numpy as np
import polars as pl
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts/research_v8"))
import labels_v2 as v8
from test_v8_label_contract import joint, decisions


@pytest.mark.parametrize("variant", ["LEAD_LAG_5M_5M", "EARLY_LATE_150S_GAP5", "EARLY_LATE_150S_GAP10"])
def test_all_registered_variants_and_direct_match(joint, decisions, variant):
    labels = v8.label_table(joint, decisions, variant)
    assert labels["label_valid"].all() and v8.assert_nonoverlap(labels)
    assert labels["implementation_version"][0] == v8.IMPLEMENTATION_VERSION
    direct = v8.direct_return_labels(labels)
    assert all(direct[name].equals(labels[name]) for name in v8.RETURN_COLUMNS)


def test_late_gap_quality_enters_actual_maturity(joint, decisions):
    stamp = decisions[0] + 150_000_000
    late = decisions[0] + 2_000_000_000
    stream = v8.STREAMS[0]
    changed = joint.with_columns(pl.when(pl.col("timestamp") == stamp).then(late)
        .otherwise(pl.col(f"{stream}__available_us")).alias(f"{stream}__available_us"))
    labels = v8.label_table(changed, decisions, "EARLY_LATE_150S_GAP10")
    assert labels["label_valid"].all()
    assert labels["label_mature_us"][0] == labels["validity_mature_us"][0] == late
    assert labels["label_mature_us"][0] > labels["return_label_mature_us"][0]


@pytest.mark.parametrize("field", ["flow_label_start_us", "flow_label_end_us", "return_label_start_us", "return_label_end_us", "delayed_entry_us"])
def test_exact_registered_boundaries_reject_mutation(joint, decisions, field):
    labels = v8.label_table(joint, decisions, "EARLY_LATE_150S_GAP10")
    changed = labels.with_columns((pl.col(field) - 5_000_000).alias(field))
    with pytest.raises(ValueError):
        v8.assert_nonoverlap(changed)
    with pytest.raises(ValueError):
        v8.direct_return_labels(changed)


def test_changed_gap10_to_gap5_with_consistent_orders_still_rejected(joint, decisions):
    labels = v8.label_table(joint, decisions, "EARLY_LATE_150S_GAP10")
    changed = labels.with_columns(*[(pl.col(field) - 5_000_000).alias(field) for field in
        ("return_label_start_us", "return_label_end_us", "delayed_entry_us")])
    with pytest.raises(ValueError, match="Registered variant exact"):
        v8.assert_nonoverlap(changed)


def test_observed_flow_cannot_become_available_at_decision(joint, decisions):
    labels = v8.label_table(joint, decisions, signal_kind="OBSERVED_FUTURE_FLOW_DIAGNOSTIC")
    changed = labels.with_columns(pl.col("decision_us").alias("signal_available_us"),
        (pl.col("decision_us") + 5_000_000).alias("earliest_order_us"),
        (pl.col("decision_us") + 5_000_000).alias("earliest_permissible_order_us"))
    with pytest.raises(ValueError, match="Signal kind"):
        v8.assert_nonoverlap(changed)
    with pytest.raises(ValueError):
        v8.direct_return_labels(changed)


@pytest.mark.parametrize("field", ["observed_future_flow_available_us", "flow_label_mature_us", "return_label_mature_us", "validity_mature_us", "label_mature_us", "predicted_signal_available_us"])
def test_maturity_and_signal_metadata_mutations_rejected(joint, decisions, field):
    labels = v8.label_table(joint, decisions)
    changed = labels.with_columns((pl.col(field) - 1).alias(field))
    with pytest.raises(ValueError):
        v8.assert_nonoverlap(changed)


@pytest.mark.parametrize("side", ["entry", "exit"])
def test_price_anchor_timestamp_mutation_rejected(joint, decisions, side):
    labels = v8.label_table(joint, decisions)
    stream = v8.RETURN_STREAMS[0]
    changed = labels.with_columns(pl.col(f"return_label_{'start' if side == 'entry' else 'end'}_us")
        .alias(f"{stream}__{side}_price_trade_us"))
    with pytest.raises(ValueError, match="Price trade timestamp"):
        v8.assert_nonoverlap(changed)


@pytest.mark.parametrize("bad_value", [np.nan, -1., np.inf])
def test_missing_future_notional_only_invalidates_affected_window(joint, decisions, bad_value):
    stream = v8.STREAMS[0]
    stamp = decisions[0] + 5_000_000
    changed = joint.with_columns(pl.when(pl.col("timestamp") == stamp).then(bad_value)
        .otherwise(pl.col(f"{stream}__aggressive_buy_notional")).alias(f"{stream}__aggressive_buy_notional"))
    labels = v8.label_table(changed, decisions)
    control = v8.label_table(joint, decisions)
    assert labels["label_valid"].to_list() == [False, True]
    assert all(np.isnan(labels[field][0]) for field in (*v8.FLOW_COLUMNS, *v8.RETURN_COLUMNS))
    assert all(labels[field][1] == control[field][1] for field in (*v8.FLOW_COLUMNS, *v8.RETURN_COLUMNS))


def test_unknown_future_availability_is_invalid_not_imputed(joint, decisions):
    stream = v8.STREAMS[0]
    changed = joint.with_columns(pl.when(pl.col("timestamp") == decisions[0] + 5_000_000).then(float("nan"))
        .otherwise(pl.col(f"{stream}__available_us")).alias(f"{stream}__available_us"))
    # This source row is future to first decision but past to the second. Unknown
    # past feature availability must reject the latter rather than be imputed.
    labels = v8.label_table(changed, decisions[:1])
    assert labels["label_valid"].to_list() == [False]
    assert np.isnan(labels["label_mature_us"][0])


def split_fixture(joint):
    start = joint["timestamp"][0]
    frames = [v8.label_table(joint, np.asarray([start + seconds * 1_000_000]), split=split)
              for seconds, split in ((1320, "TRAIN"), (3000, "VALIDATION"), (4200, "OOS_SCREENING"))]
    labels = pl.concat(frames)
    kwargs = dict(train_ids=[start + 1320_000_000], validation_ids=[start + 3000_000_000],
        test_ids=[start + 4200_000_000], fit_cutoff_us=start + 2100_000_000,
        validation_start_us=start + 3000_000_000, test_start_us=start + 4200_000_000,
        test_end_us=start + 4900_000_000, embargo_us=100_000_000, max_label_lag_us=600_000_000)
    return labels, kwargs


def test_full_split_receipt_and_actual_lag(joint):
    labels, kwargs = split_fixture(joint)
    receipt = v8.assert_split_chronology(labels, **kwargs)
    assert receipt["actual_observed_max_label_lag_us"] == 600_000_000
    assert receipt["counts"] == {"train": 1, "validation": 1, "test": 1}
    with pytest.raises(ValueError, match="actual observed maximum"):
        v8.assert_split_chronology(labels, **{**kwargs, "max_label_lag_us": 599_000_000})
    with pytest.raises(ValueError, match="strictly before"):
        v8.assert_split_chronology(labels, **{**kwargs, "fit_cutoff_us": kwargs["validation_start_us"] - kwargs["embargo_us"] - kwargs["max_label_lag_us"]})


def test_validation_test_maturity_and_row_metadata(joint):
    labels, kwargs = split_fixture(joint)
    with pytest.raises(ValueError, match="Validation label maturity"):
        v8.assert_split_chronology(labels, **{**kwargs, "test_start_us": labels["label_mature_us"][1] + kwargs["embargo_us"]})
    with pytest.raises(ValueError, match="Test label not mature"):
        v8.assert_split_chronology(labels, **{**kwargs, "test_end_us": labels["label_mature_us"][2] - 1})
    with pytest.raises(ValueError, match="split metadata"):
        v8.assert_split_chronology(labels.with_columns(pl.lit("TRAIN").alias("split")), **kwargs)


def test_delayed_observed_lag_cannot_use_nominal_registered_lag(joint):
    labels, kwargs = split_fixture(joint)
    row = labels.row(0, named=True)
    # Internally consistent receipt with genuinely later exit/quality availability.
    columns = ["return_label_mature_us", "validity_mature_us", "label_mature_us"]
    altered = labels.with_columns(*[pl.when(pl.col("decision_us") == row["decision_us"])
        .then(pl.col(field) + 100_000_000).otherwise(pl.col(field)).alias(field) for field in columns])
    with pytest.raises(ValueError, match="actual observed maximum"):
        v8.assert_split_chronology(altered, **kwargs)
    assert v8.assert_split_chronology(altered, **{**kwargs, "max_label_lag_us": 700_000_000})["actual_observed_max_label_lag_us"] == 700_000_000


def test_future_availability_perturbation_cannot_touch_past_features(joint, decisions):
    before, available = v8.past_features(joint, decisions[0])
    stream = v8.STREAMS[0]
    changed = joint.with_columns(pl.when(pl.col("timestamp") >= decisions[0]).then(float("nan"))
        .otherwise(pl.col(f"{stream}__available_us")).alias(f"{stream}__available_us"))
    after, second_available = v8.past_features(changed, decisions[0])
    assert np.array_equal(before, after) and available == second_available
