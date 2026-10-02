"""V8 V4: preserve missing future rows over frozen V3 chronology and labels.

No source bars are padded, interpolated or discovered. Complete future windows
use the unchanged V3 computation; incomplete windows retain their nominal grid
with unknown maturity and NaN targets. This is not an economic acceptance gate.
"""
from __future__ import annotations

import numpy as np
import polars as pl

if __package__:
    from . import labels_v3 as _v3
else:
    import labels_v3 as _v3

IMPLEMENTATION_VERSION = "V8_LABELS_V4_20261002"
US, EPS, BAR_US, STREAMS = _v3.US, _v3.EPS, _v3.BAR_US, _v3.STREAMS
RETURN_STREAMS, FLOW_COLUMNS, RETURN_COLUMNS = _v3.RETURN_STREAMS, _v3.FLOW_COLUMNS, _v3.RETURN_COLUMNS
BEGIN, END, MATCH_KEYS = _v3.BEGIN, _v3.END, _v3.MATCH_KEYS
contract, require = _v3.contract, _v3.require
past_features = _v3.past_features
fit_train_scaler, fit_conditional_expectation = _v3.fit_train_scaler, _v3.fit_conditional_expectation
OOFPredictionReceipt, flow_surprise = _v3.OOFPredictionReceipt, _v3.flow_surprise


def _as_v3(labels):
    return labels.with_columns(pl.lit(_v3.IMPLEMENTATION_VERSION).alias("implementation_version"))


def _version(labels):
    return labels.with_columns(pl.lit(IMPLEMENTATION_VERSION).alias("implementation_version"))


def _unknown_source_metadata(joint):
    # V3 first checks every known timestamp's integer/date domain. Infinity is
    # missing metadata, never a legitimate large timestamp or a filled value.
    names = [name for name in joint.columns if name.endswith("_us")]
    return joint.with_columns(*[pl.when(pl.col(name).is_finite()).then(pl.col(name))
        .otherwise(None).alias(name) for name in names])


def _dependencies(times, maximum, valid, starts, stops):
    result = np.full(len(starts), np.nan)
    complete = (starts >= times[0]) & (stops <= times[-1] + BAR_US) & (starts < stops)
    if complete.any():
        first = np.searchsorted(times, starts[complete])
        last = np.searchsorted(times, stops[complete])
        result[complete] = _v3._v2._max_dependencies(maximum, valid, first, last)
    return result


def _anchor(joint, times, requested, name):
    indices = np.searchsorted(times, requested)
    clipped = np.minimum(indices, len(times) - 1)
    known = (indices < len(times)) & (times[clipped] == requested)
    values = joint[name].to_numpy().astype(float)[clipped]
    return np.where(known, values, np.nan)


def _incomplete_rows(joint, decisions, variant, split, signal_kind):
    """Build only invalid future rows, retaining actual complete past guards."""
    spec, times = contract()["labels"][variant], joint["timestamp"].to_numpy()
    bounds = [decisions + spec[key] * US for key in
        ("flow_start_offset_seconds", "flow_end_offset_seconds", "return_start_offset_seconds", "return_end_offset_seconds")]
    flow_start, flow_end, return_start, return_end = bounds
    availability = np.column_stack([joint[f"{stream}__available_us"].to_numpy().astype(float) for stream in STREAMS])
    valid_available = np.isfinite(availability) & (availability >= times[:, None] + BAR_US)
    maximum, valid = availability.max(axis=1), valid_available.all(axis=1)
    first_past = _v3._v2._v1._positions(times, decisions - _v3._v2.PAST_BARS * BAR_US)
    decision_row = _v3._v2._v1._positions(times, decisions - BAR_US)
    feature_available = _v3._v2._max_dependencies(maximum, valid, first_past, decision_row + 1)
    require(np.isfinite(feature_available).all() and np.all(feature_available <= decisions),
            "Feature availability after decision or unknown past source")
    quality = np.column_stack([joint[f"{stream}__quality"].to_numpy() for stream in STREAMS])
    require(all(np.all(quality[a:b] == 0) for a, b in zip(first_past, decision_row + 1)), "Past source quality invalid")
    flow_mature = _dependencies(times, maximum, valid, flow_start, flow_end)
    return_mature = _dependencies(times, maximum, valid, return_start - BAR_US, return_end)
    validity_mature = _dependencies(times, maximum, valid, flow_start, return_end)
    signal_available = decisions if signal_kind == "PAST_ONLY_PREDICTED_FLOW" else flow_mature
    earliest = signal_available + contract()["fixed_order_latency_seconds"] * US
    columns = {"decision_us": decisions, "feature_available_us": feature_available,
        "predicted_signal_available_us": decisions, "signal_available_us": signal_available,
        "earliest_order_us": earliest, "earliest_permissible_order_us": earliest,
        "delayed_entry_us": return_start, "flow_label_start_us": flow_start,
        "flow_label_end_us": flow_end, "flow_label_mature_us": flow_mature,
        "observed_future_flow_available_us": flow_mature, "return_label_start_us": return_start,
        "return_label_end_us": return_end, "return_label_mature_us": return_mature,
        "validity_mature_us": validity_mature, "label_mature_us": np.full(len(decisions), np.nan),
        "implementation_version": [_v3._v2.IMPLEMENTATION_VERSION] * len(decisions),
        "label_variant": [variant] * len(decisions), "flow_return_overlap": [False] * len(decisions),
        "split": [split] * len(decisions), "signal_kind": [signal_kind] * len(decisions),
        "price_proxy_kind": ["CLOSED_BAR_RETURN_PROXY_NOT_EXECUTABLE_FILL"] * len(decisions),
        "label_valid": np.zeros(len(decisions), dtype=bool)}
    for name in (*FLOW_COLUMNS, *RETURN_COLUMNS):
        columns[name] = np.full(len(decisions), np.nan)
    for stream in RETURN_STREAMS:
        for side, requested in (("entry", return_start - BAR_US), ("exit", return_end - BAR_US)):
            for suffix, field in (("price_proxy", "close"), ("price_trade_us", "last_trade_us"), ("price_available_us", "available_us")):
                columns[f"{stream}__{side}_{suffix}"] = _anchor(joint, times, requested, f"{stream}__{field}")
    return _v3._nullable_integer_output(pl.DataFrame(columns))


def _unknown_anchor_maturity(labels):
    anchor_fields = [f"{stream}__{side}_price_{field}_us" for stream in RETURN_STREAMS
                     for side in ("entry", "exit") for field in ("trade", "available")]
    unknown = pl.any_horizontal(*[pl.col(name).is_null() for name in anchor_fields])
    # An unknown anchor dependency cannot have a known total maturity even if
    # the available quality records have otherwise known timestamps.
    return labels.with_columns(
        pl.when(unknown).then(None).otherwise(pl.col("return_label_mature_us")).cast(pl.Int64).alias("return_label_mature_us"),
        pl.when(unknown).then(None).otherwise(pl.col("label_mature_us")).cast(pl.Int64).alias("label_mature_us"))


def label_table(joint, decisions, variant="LEAD_LAG_5M_5M", *, split="DEVELOPMENT_DIAGNOSTIC",
                signal_kind="PAST_ONLY_PREDICTED_FLOW"):
    decisions = _v3._minute_decisions(decisions, "decision")
    require(np.all(np.diff(decisions) > 0), "Unique chronological explicit decision IDs required")
    spec = contract()["labels"].get(variant)
    require(spec is not None, "Only registered V8 label variants")
    require(split in ("TRAIN", "VALIDATION", "OOS_SCREENING", "DEVELOPMENT_DIAGNOSTIC"), "Explicit research split classification required")
    require(signal_kind in ("PAST_ONLY_PREDICTED_FLOW", "OBSERVED_FUTURE_FLOW_DIAGNOSTIC"), "Explicit signal availability mode required")
    _v3._source_timestamps(joint)
    times = _v3._v2._grid(joint)
    require(np.all(decisions + spec["return_end_offset_seconds"] * US <= END), "Nominal label endpoints outside development; locked forbidden")
    sanitized = _unknown_source_metadata(joint)
    complete = ((decisions + spec["flow_start_offset_seconds"] * US >= times[0])
                & (decisions + spec["return_end_offset_seconds"] * US <= times[-1] + BAR_US))
    pieces = []
    if complete.any():
        pieces.append(_v3.label_table(sanitized, decisions[complete], variant, split=split, signal_kind=signal_kind))
    if (~complete).any():
        tail = _incomplete_rows(sanitized, decisions[~complete], variant, split, signal_kind)
        if pieces:
            tail = tail.select(pieces[0].columns)
        pieces.append(tail)
    result = _version(_unknown_anchor_maturity(pl.concat(pieces).sort("decision_us")))
    assert_nonoverlap(result)
    return result


def assert_nonoverlap(labels):
    require(len(labels) > 0 and set(labels["implementation_version"].to_list()) == {IMPLEMENTATION_VERSION}, "Active V4 implementation required")
    return _v3.assert_nonoverlap(_as_v3(labels))


def direct_return_labels(labels):
    assert_nonoverlap(labels)
    return labels.select([name for name in labels.columns if "__future_flow" not in name])


assert_fit_chronology = _v3.assert_fit_chronology


def assert_split_chronology(labels, **kwargs):
    assert_nonoverlap(labels)
    result = _v3.assert_split_chronology(_as_v3(labels), **kwargs)
    result["implementation_version"] = IMPLEMENTATION_VERSION
    return result


def assert_matched_direct_baseline(pipeline_binding, direct_binding):
    require(pipeline_binding.get("label_implementation_version") == direct_binding.get("label_implementation_version") == IMPLEMENTATION_VERSION,
            "Matched comparison must bind active V4 implementation")
    return _v3._v2.assert_matched_direct_baseline(pipeline_binding, direct_binding)


def acceptance_main():
    """Prebind one synthetic acceptance; preserve source and both outcomes."""
    import argparse
    import hashlib
    import json
    import os
    import shlex
    import shutil
    import subprocess
    import sys
    from datetime import UTC, datetime
    from pathlib import Path
    from quant import resources
    from quant.paths import ROOT, STATE
    from quant.research_fast.dataset import file_sha
    if __package__:
        from .registry import FIELDS, append_event
    else:
        from registry import FIELDS, append_event

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--acceptance", required=True, action="store_true")
    parser.add_argument("--experiment-id", required=True)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    run, output = args.run_dir.resolve(), args.output.resolve()
    require(run.is_relative_to(STATE.resolve()) and not run.exists(), "Exclusive D-native synthetic STATE directory required")
    require(output.is_relative_to((ROOT / "reports/fast_research").resolve()) and not output.exists(), "Exclusive small receipt required")
    require(bool(os.environ.get("COIN_TASK_ID")), "Actual long-task progress wrapper required")
    sources = ("protocols/LABEL_CONTRACT_V8.json", "scripts/research_v8/labels.py", "scripts/research_v8/labels_v2.py",
        "scripts/research_v8/labels_v3.py", "scripts/research_v8/labels_v4.py", "tests/test_v8_label_contract.py",
        "tests/test_v8_label_contract_v2.py", "tests/test_v8_label_contract_v3.py", "tests/test_v8_label_contract_v4.py",
        "scripts/research_v8/registry.py", "src/quant/research_fast/dataset.py", "src/quant/paths.py", "src/quant/resources.py",
        "scripts/with_task_progress.sh", "scripts/bounded.sh", "environments/v8/uv.lock")
    hashes = {name: file_sha(ROOT / name) for name in sources}
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT).decode().strip()
    command = [sys.executable, "-m", "pytest", "tests/test_v8_label_contract_v4.py", "-q",
        f"--basetemp={run / 'pytest'}", "-o", f"cache_dir={run / 'pytest-cache'}", f"--junitxml={run / 'junit.xml'}"]
    binding = {"experiment_id": args.experiment_id, "started_utc": datetime.now(UTC).isoformat(),
        "git_commit": head, "source_hashes": hashes, "label_implementation_version": IMPLEMENTATION_VERSION,
        "protocol_sha256": hashes["protocols/LABEL_CONTRACT_V8.json"], "environment_lock_sha256": hashes["environments/v8/uv.lock"],
        "data_scope": "SYNTHETIC_ONLY_NO_MARKET_OR_LOCKED_IO", "synthetic_recipe_sha256": hashlib.sha256(
            (hashes["tests/test_v8_label_contract.py"] + hashes["tests/test_v8_label_contract_v4.py"]).encode()).hexdigest(),
        "seed": 20261002, "python": sys.executable, "exact_test_command": shlex.join(command),
        "actual_adapter_argv": sys.argv, "task_id": os.environ["COIN_TASK_ID"], "required_outer_wrapper": "scripts/with_task_progress.sh (inside bounded.sh)",
        "market_model_fits": 0, "all_folds": [], "resources": resources.status()}
    run.mkdir()
    for name in sources:
        target = run / "source-snapshot" / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / name, target)
    with (run / "RUN_BINDING.json").open("x") as stream:
        json.dump(binding, stream, indent=2, allow_nan=False)
    event = dict.fromkeys(FIELDS)
    event.update(experiment_id=args.experiment_id, event_id=args.experiment_id + ":start", event_type="OPERATIONAL_START",
        git_commit=head, data_manifest_hash=binding["synthetic_recipe_sha256"], protocol_hash=binding["protocol_sha256"],
        feature_set="UNCHANGED_PAST256_SYNTHETIC_SOURCE", labels=IMPLEMENTATION_VERSION, model_family="NONE",
        hyperparameters={"registered_variants": list(contract()["labels"]), "adapter_only": True}, seed=binding["seed"],
        thresholds="UNCHANGED_CONTRACT", cost_assumptions="NO_EXECUTION_OR_COST_RESULT", all_folds=[], success_failure="STARTED",
        reason_for_next_experiment="Repair independently confirmed V8C-01 and V8C-02 without changing prior sources or deleting calendar rows",
        result_influenced_later_choice=False, source_hashes=hashes, environment_lock_sha256=binding["environment_lock_sha256"],
        run_binding_sha256=file_sha(run / "RUN_BINDING.json"), exact_command=binding["exact_test_command"])
    append_event(ROOT / "reports/experiment_registry.jsonl", event)
    completed = subprocess.run(command, cwd=ROOT, env={**os.environ, "COIN_V8_LABEL_BINDING_FILE": str(run / "RUN_BINDING.json")})
    unchanged = hashes == {name: file_sha(ROOT / name) for name in sources}
    status = "PASS_SYNTHETIC_LABEL_V4_MISSING_POLICY" if completed.returncode == 0 and unchanged else "FAIL_SYNTHETIC_LABEL_V4_ACCEPTANCE"
    receipt = {"status": status, "created_utc": datetime.now(UTC).isoformat(), "binding": binding,
        "actual_test_exit_code": completed.returncode, "source_bytes_unchanged": unchanged,
        "run_binding_sha256": file_sha(run / "RUN_BINDING.json"), "junit_path": str(run / "junit.xml"),
        "junit_sha256": file_sha(run / "junit.xml") if (run / "junit.xml").is_file() else None,
        "source_snapshot_preserved": True, "market_inputs_read": False, "locked_consumed": False, "market_model_fits": 0,
        "GPU_hours": 0, "orders_sent": 0, "P1_statistical_economic_gate": "NOT_EVALUATED",
        "qualified_candidate": "NONE", "resources": resources.status()}
    with output.open("x") as stream:
        json.dump(receipt, stream, indent=2, allow_nan=False)
    append_event(ROOT / "reports/experiment_registry.jsonl", {**event, "event_id": args.experiment_id + ":result",
        "event_type": "OPERATIONAL_RESULT", "success_failure": status, "result_path": str(output.relative_to(ROOT)), "result_sha256": file_sha(output)})
    print(json.dumps({"status": status, "output": str(output), "exit_code": completed.returncode}), flush=True)
    raise SystemExit(0 if status.startswith("PASS_") else 1)


if __name__ == "__main__":
    acceptance_main()
