"""Real V3 missing-policy regressions; synthetic source, no market IO or fit."""
from pathlib import Path
import os
import json
import sys

import numpy as np
import polars as pl
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts/research_v8"))
import labels_v3 as previous
import labels_v4 as v8
from test_v8_label_contract import joint, decisions


@pytest.fixture(scope="session", autouse=True)
def recorded_preexecution_binding(record_testsuite_property):
    name = os.environ.get("COIN_V8_LABEL_BINDING_FILE")
    if name:
        from quant.research_fast.dataset import file_sha
        binding = json.loads(Path(name).read_text())
        record_testsuite_property("run_binding_sha256", file_sha(Path(name)))
        record_testsuite_property("environment_lock_sha256", binding["environment_lock_sha256"])
        record_testsuite_property("pre_execution_adapter_sha256", binding["source_hashes"]["scripts/research_v8/labels_v4.py"])
        record_testsuite_property("pre_execution_test_sha256", binding["source_hashes"]["tests/test_v8_label_contract_v4.py"])
    else:
        record_testsuite_property("pre_execution_binding", "NOT_PROVIDED_BY_THIS_TEST_LAUNCH")


@pytest.mark.parametrize("variant", ["LEAD_LAG_5M_5M", "EARLY_LATE_150S_GAP5", "EARLY_LATE_150S_GAP10"])
def test_complete_source_matches_frozen_v3_bitexact(joint, decisions, variant):
    actual = v8.label_table(joint, decisions, variant)
    control = previous.label_table(joint, decisions, variant)
    assert actual.drop("implementation_version").equals(control.drop("implementation_version"))
    assert v8.assert_nonoverlap(actual)
    assert all(dtype == pl.Int64 for name, dtype in actual.schema.items() if name.endswith("_us"))


@pytest.mark.parametrize("variant", ["LEAD_LAG_5M_5M", "EARLY_LATE_150S_GAP5", "EARLY_LATE_150S_GAP10"])
@pytest.mark.parametrize("field,side", [("last_trade_us", "entry"), ("available_us", "exit")])
@pytest.mark.parametrize("unknown", [np.inf, -np.inf, np.nan])
def test_nonfinite_anchor_keeps_invalid_row_and_valid_peer(joint, variant, field, side, unknown):
    start = int(joint["timestamp"][0])
    endpoints = start + np.asarray([1320, 1800], np.int64) * v8.US
    spec = v8.contract()["labels"][variant]
    anchor = endpoints[1] + spec[f"return_{'start' if side == 'entry' else 'end'}_offset_seconds"] * v8.US - v8.BAR_US
    column = f"{v8.RETURN_STREAMS[0]}__{field}"
    changed = joint.with_columns(pl.when(pl.col("timestamp") == anchor).then(float(unknown)).otherwise(pl.col(column)).alias(column))
    actual = v8.label_table(changed, endpoints, variant)
    control = v8.label_table(joint, endpoints[:1], variant)
    assert actual.height == 2 and actual["decision_us"].to_list() == endpoints.tolist()
    assert actual["label_valid"].to_list() == [True, False]
    assert actual.head(1).equals(control)
    assert actual["label_mature_us"][1] is None and actual["return_label_mature_us"][1] is None
    assert actual[f"{v8.RETURN_STREAMS[0]}__{side}_price_{'trade' if field == 'last_trade_us' else 'available'}_us"][1] is None
    assert all(np.isnan(actual[name][1]) for name in (*v8.FLOW_COLUMNS, *v8.RETURN_COLUMNS))
    assert v8.direct_return_labels(actual)[v8.RETURN_COLUMNS[0]].equals(actual[v8.RETURN_COLUMNS[0]])


@pytest.mark.parametrize("variant", ["LEAD_LAG_5M_5M", "EARLY_LATE_150S_GAP5", "EARLY_LATE_150S_GAP10"])
@pytest.mark.parametrize("signal_kind", ["PAST_ONLY_PREDICTED_FLOW", "OBSERVED_FUTURE_FLOW_DIAGNOSTIC"])
def test_finite_source_tail_preserves_common_calendar(joint, variant, signal_kind):
    start = int(joint["timestamp"][0])
    # Source ends at 5000s. Choose the last minute with complete past whose
    # registered return_end exceeds it; no artificial source bars are added.
    end_offset = v8.contract()["labels"][variant]["return_end_offset_seconds"]
    tail_seconds = ((5000 - end_offset) // 60 + 1) * 60
    endpoints = start + np.asarray([1800, tail_seconds], np.int64) * v8.US
    actual = v8.label_table(joint, endpoints, variant, signal_kind=signal_kind)
    control = v8.label_table(joint, endpoints[:1], variant, signal_kind=signal_kind)
    assert actual.height == 2 and actual.head(1).equals(control)
    assert actual["label_valid"].to_list() == [True, False]
    assert actual["return_label_end_us"][1] == endpoints[1] + end_offset * v8.US
    assert actual["label_mature_us"][1] is None and actual["return_label_mature_us"][1] is None
    assert actual[f"{v8.RETURN_STREAMS[0]}__exit_price_trade_us"][1] is None
    assert np.isnan(actual[f"{v8.RETURN_STREAMS[0]}__exit_price_proxy"][1])
    assert all(np.isnan(actual[name][1]) for name in (*v8.FLOW_COLUMNS, *v8.RETURN_COLUMNS))
    only_tail = v8.label_table(joint, endpoints[1:], variant, signal_kind=signal_kind)
    assert only_tail.equals(actual.tail(1))
    assert v8.assert_nonoverlap(actual)


def test_missing_flow_window_and_unknown_past_do_not_become_training_data(joint):
    start = int(joint["timestamp"][0])
    label = v8.label_table(joint, np.asarray([start + 4980 * v8.US], dtype=np.int64))
    assert label["label_valid"].to_list() == [False]
    assert label["flow_label_mature_us"][0] is None and label["label_mature_us"][0] is None
    stream = v8.STREAMS[0]
    changed = joint.with_columns(pl.when(pl.col("timestamp") == start + 1795 * v8.US).then(float("inf"))
        .otherwise(pl.col(f"{stream}__available_us")).alias(f"{stream}__available_us"))
    with pytest.raises(ValueError, match="unknown past source"):
        v8.label_table(changed, np.asarray([start + 1800 * v8.US], dtype=np.int64))


def test_missing_future_row_rejected_by_scored_split_and_domain_guards(joint):
    start = int(joint["timestamp"][0])
    train = v8.label_table(joint, np.asarray([start + 1320 * v8.US], np.int64), split="TRAIN")
    validation = v8.label_table(joint, np.asarray([start + 3000 * v8.US], np.int64), split="VALIDATION")
    tail = v8.label_table(joint, np.asarray([start + 4440 * v8.US], np.int64), split="OOS_SCREENING")
    with pytest.raises(ValueError, match="Unknown or invalid label"):
        v8.assert_split_chronology(pl.concat([train, validation, tail]),
            train_ids=train["decision_us"].to_list(), validation_ids=validation["decision_us"].to_list(), test_ids=tail["decision_us"].to_list(),
            fit_cutoff_us=start + 2100 * v8.US, validation_start_us=start + 3000 * v8.US,
            test_start_us=start + 4440 * v8.US, test_end_us=start + 5100 * v8.US, embargo_us=100 * v8.US, max_label_lag_us=600 * v8.US)
    with pytest.raises(ValueError, match="original integer metadata"):
        v8.label_table(joint, [float(start + 1800 * v8.US)])
    with pytest.raises(ValueError, match="locked"):
        v8.label_table(joint, np.asarray([v8.END], np.int64))
    invalid_flow = train.with_columns(pl.lit(100.).alias(v8.FLOW_COLUMNS[0]))
    with pytest.raises(ValueError, match="future-flow ratio"):
        v8.assert_nonoverlap(invalid_flow)
