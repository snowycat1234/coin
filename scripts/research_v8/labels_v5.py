"""V8 V5 canonical column order over frozen V4 per-row missing-policy glue."""
from __future__ import annotations

import polars as pl

if __package__:
    from . import labels_v4 as _v4
else:
    import labels_v4 as _v4

IMPLEMENTATION_VERSION = "V8_LABELS_V5_20261002"
US, EPS, BAR_US, STREAMS = _v4.US, _v4.EPS, _v4.BAR_US, _v4.STREAMS
RETURN_STREAMS, FLOW_COLUMNS, RETURN_COLUMNS = _v4.RETURN_STREAMS, _v4.FLOW_COLUMNS, _v4.RETURN_COLUMNS
BEGIN, END, MATCH_KEYS = _v4.BEGIN, _v4.END, _v4.MATCH_KEYS
contract, require = _v4.contract, _v4.require
past_features = _v4.past_features
fit_train_scaler, fit_conditional_expectation = _v4.fit_train_scaler, _v4.fit_conditional_expectation
OOFPredictionReceipt, flow_surprise = _v4.OOFPredictionReceipt, _v4.flow_surprise
assert_fit_chronology = _v4.assert_fit_chronology


def _as_v4(labels):
    return labels.with_columns(pl.lit(_v4.IMPLEMENTATION_VERSION).alias("implementation_version"))


def _canonical_columns(labels):
    trailing = list(FLOW_COLUMNS)
    for stream in RETURN_STREAMS:
        trailing.append(f"{stream}__subsequent_return_proxy")
        trailing.extend(f"{stream}__{name}" for name in ("entry_price_proxy", "exit_price_proxy", "entry_price_trade_us",
            "exit_price_trade_us", "entry_price_available_us", "exit_price_available_us"))
    trailing.append("label_valid")
    core = [name for name in labels.columns if name not in trailing]
    return labels.select(core + trailing)


def label_table(joint, decisions, variant="LEAD_LAG_5M_5M", *, split="DEVELOPMENT_DIAGNOSTIC",
                signal_kind="PAST_ONLY_PREDICTED_FLOW"):
    result = _canonical_columns(_v4.label_table(joint, decisions, variant, split=split, signal_kind=signal_kind))
    result = result.with_columns(pl.lit(IMPLEMENTATION_VERSION).alias("implementation_version"))
    assert_nonoverlap(result)
    return result


def assert_nonoverlap(labels):
    require(len(labels) > 0 and set(labels["implementation_version"].to_list()) == {IMPLEMENTATION_VERSION}, "Active V5 implementation required")
    return _v4.assert_nonoverlap(_as_v4(labels))


def direct_return_labels(labels):
    assert_nonoverlap(labels)
    return labels.select([name for name in labels.columns if "__future_flow" not in name])


def assert_split_chronology(labels, **kwargs):
    assert_nonoverlap(labels)
    result = _v4.assert_split_chronology(_as_v4(labels), **kwargs)
    result["implementation_version"] = IMPLEMENTATION_VERSION
    return result


def assert_matched_direct_baseline(pipeline_binding, direct_binding):
    require(pipeline_binding.get("label_implementation_version") == direct_binding.get("label_implementation_version") == IMPLEMENTATION_VERSION,
            "Matched comparison must bind active V5 implementation")
    return _v4._v3._v2.assert_matched_direct_baseline(pipeline_binding, direct_binding)


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
        "scripts/research_v8/labels_v3.py", "scripts/research_v8/labels_v4.py", "scripts/research_v8/labels_v5.py", "tests/test_v8_label_contract.py",
        "tests/test_v8_label_contract_v2.py", "tests/test_v8_label_contract_v3.py", "tests/test_v8_label_contract_v4.py", "tests/test_v8_label_contract_v5.py",
        "scripts/research_v8/registry.py", "src/quant/research_fast/dataset.py", "src/quant/paths.py", "src/quant/resources.py",
        "scripts/with_task_progress.sh", "scripts/bounded.sh", "environments/v8/uv.lock")
    hashes = {name: file_sha(ROOT / name) for name in sources}
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT).decode().strip()
    command = [sys.executable, "-m", "pytest", "tests/test_v8_label_contract_v5.py", "-q",
        f"--basetemp={run / 'pytest'}", "-o", f"cache_dir={run / 'pytest-cache'}", f"--junitxml={run / 'junit.xml'}"]
    binding = {"experiment_id": args.experiment_id, "started_utc": datetime.now(UTC).isoformat(),
        "git_commit": head, "source_hashes": hashes, "label_implementation_version": IMPLEMENTATION_VERSION,
        "protocol_sha256": hashes["protocols/LABEL_CONTRACT_V8.json"], "environment_lock_sha256": hashes["environments/v8/uv.lock"],
        "data_scope": "SYNTHETIC_ONLY_NO_MARKET_OR_LOCKED_IO", "synthetic_recipe_sha256": hashlib.sha256(
            (hashes["tests/test_v8_label_contract.py"] + hashes["tests/test_v8_label_contract_v5.py"]).encode()).hexdigest(),
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
        reason_for_next_experiment="Canonicalize per-row missing-policy output schema after preserved first V4 acceptance failed concatenation",
        result_influenced_later_choice=False, source_hashes=hashes, environment_lock_sha256=binding["environment_lock_sha256"],
        run_binding_sha256=file_sha(run / "RUN_BINDING.json"), exact_command=binding["exact_test_command"])
    append_event(ROOT / "reports/experiment_registry.jsonl", event)
    completed = subprocess.run(command, cwd=ROOT, env={**os.environ, "COIN_V8_LABEL_BINDING_FILE": str(run / "RUN_BINDING.json")})
    unchanged = hashes == {name: file_sha(ROOT / name) for name in sources}
    status = "PASS_SYNTHETIC_LABEL_V5_MISSING_POLICY" if completed.returncode == 0 and unchanged else "FAIL_SYNTHETIC_LABEL_V5_ACCEPTANCE"
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


