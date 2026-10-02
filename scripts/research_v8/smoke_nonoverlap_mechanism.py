"""One prebound synthetic call of the mechanism API; no historical source IO."""
from __future__ import annotations

import argparse
from datetime import UTC, datetime
import json
import os
from pathlib import Path
import shlex
import subprocess
import sys

import numpy as np
import polars as pl

from quant import resources
from quant.paths import ROOT, STATE
from quant.research_fast.dataset import file_sha

sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))
from scripts.research_v8 import nonoverlap_mechanism as mechanism
from scripts.research_v8.registry import FIELDS, append_event
from test_v8_label_contract import joint as synthetic_joint


def single_call():
    joint = synthetic_joint.__wrapped__()
    start = int(joint["timestamp"][0])
    decisions = start + np.asarray([1800, 1860, 1920, 4440], dtype=np.int64) * 1_000_000
    frame = mechanism.labels.label_table(joint, decisions, "LEAD_LAG_5M_5M",
        split="DEVELOPMENT_DIAGNOSTIC", signal_kind="OBSERVED_FUTURE_FLOW_DIAGNOSTIC")
    mechanism.labels.assert_nonoverlap(frame)
    assert frame["label_valid"].to_list() == [True, True, True, False]
    assert frame.schema["label_mature_us"] == pl.Int64 and frame["label_mature_us"][-1] is None
    assert frame["earliest_permissible_order_us"].to_list() == (decisions + 305_000_000).tolist()
    masks = {}
    for name, deadline, expected in (("train", start + 2500_000_000, [True, True, False, False]),
        ("test", start + 5000_000_000, [True, True, True, False])):
        outcomes = frame.with_columns(pl.lit(deadline).alias("split_maturity_deadline_us"),
            (pl.col("label_valid") & (pl.col("label_mature_us") <= deadline)).fill_null(False).alias("diagnostic_outcome_valid"))
        assert outcomes["diagnostic_outcome_valid"].to_list() == expected
        masks[name] = expected
    valid = frame.filter(pl.col("label_valid"))
    metrics = mechanism.correlations(valid[mechanism.labels.FLOW_COLUMNS[0]].to_numpy(),
        valid[mechanism.labels.RETURN_COLUMNS[0]].to_numpy())
    assert metrics["rows"] == 3 and np.isfinite(metrics["pearson"]) and np.isfinite(metrics["spearman"])
    return {"source_scope": "ONE_DETERMINISTIC_SYNTHETIC_BATCH", "calendar_rows": 4,
        "complete_rows": 3, "invalid_tail_rows": 1, "nullable_Int64_maturity": True,
        "chronology_deadline_masks": masks, "official_correlations_import_and_call": "PASS",
        "market_models_fit": 0, "market_or_locked_inputs_read": False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    run, output = args.run_dir.resolve(), args.output.resolve()
    mechanism.require(run.is_relative_to(STATE) and not run.exists(), "Exclusive D-native STATE run required")
    mechanism.require(output.is_relative_to(ROOT / "reports/fast_research") and not output.exists(), "Exclusive small report required")
    mechanism.require(bool(os.environ.get("COIN_TASK_ID")), "Actual bounded progress wrapper required")
    sources = ["scripts/research_v8/smoke_nonoverlap_mechanism.py", "scripts/research_v8/nonoverlap_mechanism.py",
        "protocols/NONOVERLAP_MECHANISM_V8_V1.json", "protocols/P1_GATE_V8.json", "protocols/LABEL_CONTRACT_V8.json",
        "scripts/research_v8/labels.py", "scripts/research_v8/labels_v2.py", "scripts/research_v8/labels_v3.py",
        "scripts/research_v8/labels_v4.py", "scripts/research_v8/labels_v5.py", "tests/test_v8_label_contract.py", "environments/v8/uv.lock"]
    hashes = {name: file_sha(ROOT / name) for name in sources}
    command = [sys.executable, str(Path(__file__).resolve()), "--run-dir", str(run), "--output", str(output)]
    binding = {"git_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "source_hashes": hashes, "environment_lock_sha256": hashes["environments/v8/uv.lock"],
        "exact_command": shlex.join(command), "data_manifest_hash_scope": "Frozen deterministic synthetic generator recipe bytes",
        "synthetic_recipe_sha256": hashes["tests/test_v8_label_contract.py"], "seed": 20261002,
        "task_id": os.environ["COIN_TASK_ID"], "resources": resources.status()}
    run.mkdir()
    (run / "RUN_BINDING.json").write_text(json.dumps(binding, indent=2, allow_nan=False))
    event = dict.fromkeys(FIELDS)
    event.update(experiment_id="v8-nonoverlap-api-smoke-20261002-v1", event_id="v8-nonoverlap-api-smoke-20261002-v1:START",
        event_type="OPERATIONAL_START", git_commit=binding["git_commit"], data_manifest_hash=binding["synthetic_recipe_sha256"],
        protocol_hash=hashes["protocols/NONOVERLAP_MECHANISM_V8_V1.json"], feature_set="SYNTHETIC_PAST256_API_NO_PREDICTOR",
        labels="ONE_LEAD_LAG5M5M_NULLABLE_TAIL_SMOKE", model_family="NONE", hyperparameters={"fits": 0}, seed=20261002,
        thresholds="UNCHANGED_SOURCE_DEADLINE_MASK", cost_assumptions="NO_EXECUTION_OR_ECONOMIC_TEST", all_folds=[],
        success_failure="STARTED", reason_for_next_experiment="Validate only actual API import and one nullable synthetic batch after static review",
        result_influenced_later_choice=False, source_hashes=hashes, exact_command=binding["exact_command"],
        environment_lock_sha256=binding["environment_lock_sha256"], run_binding_sha256=file_sha(run / "RUN_BINDING.json"))
    append_event(ROOT / "reports/experiment_registry.jsonl", event)
    report = {"status": "FAIL_SYNTHETIC_API_SMOKE", "binding": binding, "source_bytes_unchanged": None,
        "market_inputs_read": False, "locked_consumed": False, "market_models_fit": 0, "P1_gate": "NOT_EVALUATED", "candidate": "NONE"}
    try:
        report["checks"] = single_call()
        report["source_bytes_unchanged"] = hashes == {name: file_sha(ROOT / name) for name in sources}
        mechanism.require(report["source_bytes_unchanged"], "Source changed during smoke")
        report["status"] = "PASS_SINGLE_SYNTHETIC_API_SMOKE_NOT_MARKET_DIAGNOSTIC"
    except Exception as error:
        report.update(error_type=type(error).__name__, reason=str(error))
        raise
    finally:
        report.update(created_utc=datetime.now(UTC).isoformat(), resources=resources.status())
        with output.open("x") as stream:
            json.dump(report, stream, indent=2, allow_nan=False)
        append_event(ROOT / "reports/experiment_registry.jsonl", {**event, "event_id": event["experiment_id"] + ":RESULT",
            "event_type": "OPERATIONAL_RESULT", "success_failure": report["status"], "result_path": str(output.relative_to(ROOT)), "result_sha256": file_sha(output)})
        print(json.dumps({"status": report["status"], "output": str(output)}), flush=True)


if __name__ == "__main__":
    main()
