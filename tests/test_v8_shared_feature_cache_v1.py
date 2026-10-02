"""Tiny synthetic cache invariants; never opens accepted market shards."""
from datetime import date
from pathlib import Path
import sys

import numpy as np
import polars as pl
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.research_v8 import shared_feature_cache_v1 as cache
from test_v8_label_contract import joint

SOURCE_SHA = "0" * 64


def decisions(joint, offsets=(3840, 3900, 3960, 4020)):
    return int(joint["timestamp"][0]) + np.asarray(offsets, np.int64) * 1_000_000


def matrix(joint, stamps):
    return cache.feature_frame(joint, stamps, fold="SYNTHETIC", split="TRAIN", source_receipt_sha256=SOURCE_SHA)


def views(joint, stamps):
    return cache.label_views(joint, stamps, split="TRAIN",
        maturity_deadline_us=int(joint["timestamp"][0]) + 5000_000_000, deadline_exclusive=False)


def test_future_invalid_labels_do_not_delete_or_change_feature_eligibility(joint):
    stamps = decisions(joint, (4380, 4440, 4500, 4560))
    inputs, targets = matrix(joint, stamps), views(joint, stamps)
    assert inputs.height == 4 and inputs["feature_eligible"].to_list() == [True] * 4
    assert len(inputs.columns) == 478 + 7
    assert inputs["feature_available_us"].to_list() == stamps.tolist()
    assert targets[cache.VARIANTS[0]]["label_valid"].to_list() == [True, False, False, False]
    assert targets[cache.VARIANTS[0]]["label_mature_us"].to_list()[1:] == [None] * 3
    for variant, target in targets.items():
        assert target.height == 4 and target["decision_us"].to_list() == stamps.tolist()
        assert target["earliest_permissible_order_us"].to_list() == (stamps + 5_000_000).tolist()
        direct = cache.labels.direct_return_labels(target)
        assert all("__future_flow" not in name for name in direct.columns)
        for name in cache.labels.RETURN_COLUMNS:
            cache.same_bits(target.select(name), direct.select(name))


def test_past_primitive_abstains_row_without_future_target_filter(joint):
    stamps = decisions(joint)
    before, original = matrix(joint, stamps), views(joint, stamps)
    field = "spot_BTCUSDT__mean_trade_size"
    altered = joint.with_columns(pl.when(pl.col("timestamp") == stamps[1] - cache.BAR_US)
        .then(None).otherwise(pl.col(field)).alias(field))
    after, target = matrix(altered, stamps), views(altered, stamps)
    assert before["feature_eligible"].all()
    assert after["feature_eligible"].to_list() == [True, False, False, False]
    assert after["feature_reason"][0] is None and all(after["feature_reason"][index] for index in (1, 2, 3))
    assert after["feature_available_us"].to_list()[1:] == [None] * 3
    assert np.isnan(after.select(cache.FEATURE_COLUMNS).to_numpy()[1:]).all()
    assert after["endpoint_id"].to_list() == before["endpoint_id"].to_list()
    for variant in cache.VARIANTS:
        assert target[variant]["label_valid"].all()
        cache.same_bits(original[variant], target[variant])


def test_future_mutation_cannot_change_past_features(joint):
    stamps = decisions(joint, (3840, 3900))
    before = matrix(joint, stamps)
    altered = joint.with_columns(pl.when(pl.col("timestamp") >= stamps[-1]).then(1)
        .otherwise(pl.col("spot_ETHUSDT__quality")).alias("spot_ETHUSDT__quality"))
    cache.same_bits(before, matrix(altered, stamps))
    targets = views(altered, stamps)
    assert all(not target["label_valid"].any() for target in targets.values())


def test_atomic_partition_roundtrip_and_original_target_pairing(joint, tmp_path):
    stamps = decisions(joint)
    inputs, targets = matrix(joint, stamps), views(joint, stamps)
    observed = []
    for variant in cache.VARIANTS:
        target = cache.labels.label_table(joint, stamps, variant, split="TRAIN", signal_kind="OBSERVED_FUTURE_FLOW_DIAGNOSTIC")
        target = target.with_columns(pl.lit(int(joint["timestamp"][0]) + 5000_000_000).alias("split_maturity_deadline_us"),
            pl.lit(True).alias("diagnostic_outcome_valid"))
        observed.append(target)
    cache.compare_prior(pl.concat(observed).sort(["decision_us", "label_variant"]), targets)
    saved = cache.commit_day(tmp_path, "synthetic_minute_partition", inputs, targets)
    assert saved["rows"] == 4 and not saved["full_UTC_day"]
    assert not (tmp_path / "pending-synthetic_minute_partition").exists()
    cache.same_bits(inputs, pl.read_parquet(Path(saved["path"]) / "features.parquet"))
    with pytest.raises(ValueError, match="overwrite"):
        cache.commit_day(tmp_path, "synthetic_minute_partition", inputs, targets)
    corrupted = dict(targets)
    corrupted[cache.VARIANTS[0]] = targets[cache.VARIANTS[0]].slice(1)
    with pytest.raises(ValueError, match="shares"):
        cache.commit_day(tmp_path, "incomplete_partition", inputs, corrupted)
    assert not (tmp_path / "incomplete_partition").exists()


def test_exact_four_fold_full_calendar_and_validation_deadlines():
    gates = cache.json_read(cache.ROOT / "protocols/P1_GATE_V8.json")
    days = cache.fold_days(gates["folds"])
    assert len(days) == 84
    for fold in gates["folds"]:
        selected = [day for day in days if day["fold"] == fold["id"]]
        assert {split: sum(day["split"] == split for day in selected) for split in
            ("TRAIN", "VALIDATION", "OOS_SCREENING")} == {"TRAIN": 12, "VALIDATION": 2, "OOS_SCREENING": 7}
        assert selected[0]["start_us"] == cache.day_us(date.fromisoformat(fold["train_start"]))
        assert selected[-1]["end_us"] == cache.day_us(date.fromisoformat(fold["test_end_exclusive"]))
        assert all(day["deadline_exclusive"] for day in selected if day["split"] == "VALIDATION")
        assert sum((day["end_us"] - day["start_us"]) // cache.MINUTE_US for day in selected) == 30240


def test_integer_and_locked_guards_run_before_io_and_old_index_is_never_used(joint):
    class JointOnly:
        def __init__(self):
            self.calls = []
        def joint_rows(self, lower, upper):
            self.calls.append((lower, upper))
            return "SYNTHETIC_STUB"
        def prepare_index(self, *args, **kwargs):
            pytest.fail("Old future-valid index must never be used")
        def __getitem__(self, key):
            pytest.fail("Old past256 sequence path must never be used")
    dataset = JointOnly()
    stamps = decisions(joint, (3840, 3900))
    assert cache.read_joint(dataset, stamps) == "SYNTHETIC_STUB"
    assert dataset.calls == [(int(stamps[0] - 720 * cache.BAR_US), int(stamps[-1] + 600_000_000))]
    before = len(dataset.calls)
    for invalid in (stamps.astype(float), np.asarray([True]), np.asarray([cache.day_us(cache.LOCKED)], np.int64),
                    np.asarray([cache.day_us(cache.LOCKED) - cache.MINUTE_US], np.int64)):
        with pytest.raises(ValueError):
            cache.read_joint(dataset, invalid)
    assert len(dataset.calls) == before
