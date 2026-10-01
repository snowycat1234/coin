"""Primary A10 acceptance with actual A09 public rows; no fit, label or alpha claim."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import subprocess
import xml.etree.ElementTree as ET
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

import polars as pl

from quant.micro_features_v2 import (
    FEATURE_NAMES_V2,
    HALF_LIFE_SECONDS,
    MODEL_FEATURE_NAMES,
    SCALE_HEAVY_FEATURES,
    MicroFeatureState,
    build_micro_features_v2,
    micro_feature_contract_v2,
)
from quant.paths import ROOT
from quant.resources import status


def require(ok, message):
    if not ok:
        raise ValueError(message)


def artifact(path):
    path = path.resolve()
    require(path.is_relative_to(ROOT) and path.is_file() and path.stat().st_size <= 4_000_000,
            "D artifact bound")
    payload = path.read_bytes()
    require(len(payload) <= 4_000_000, "Artifact read bound")
    return {"path": str(path.relative_to(ROOT)), "sha256": hashlib.sha256(payload).hexdigest(),
            "bytes": len(payload)}


def read(path):
    artifact(path)
    value = json.loads(path.read_text())
    json.dumps(value, allow_nan=False)
    return value


def checksum(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                     allow_nan=False).encode()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tests", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    output, tests = args.output.resolve(), args.tests.resolve()
    require(output.is_relative_to(ROOT / "reports") and not output.exists(),
            "New exclusive D report required")
    contract = micro_feature_contract_v2()
    source_names = ("src/quant/micro_features_v2.py", "tests/test_micro_features_v2.py",
                    "docs/MODULE_A10_MICRO_FEATURES_V2.md",
                    "scripts/accept_a10_micro_features_v2.py")
    sources = {name: artifact(ROOT / name)["sha256"] for name in source_names}
    require(contract["implementation_sha256"] == sources[source_names[0]]
            and HALF_LIFE_SECONDS == 3600 and len(MODEL_FEATURE_NAMES) == 13
            and all(name not in MODEL_FEATURE_NAMES for name in SCALE_HEAVY_FEATURES),
            "Fixed normalized model view mismatch")
    artifact(tests)
    cases = list(ET.parse(tests).getroot().iter("testcase"))
    require(len(cases) == 46 and len({(case.get("classname"), case.get("name"))
                                    for case in cases}) == 46
            and not any(list(case.iter(tag)) for case in cases
                        for tag in ("failure", "error", "skipped")), "Actual A10 tests failed")
    prior_path = ROOT / "reports/A09_MICROSTRUCTURE_V2_ACCEPTANCE_20261001.json"
    prior = read(prior_path)
    require(prior["status"] == "A09_MICROSTRUCTURE_V2_CORRECTNESS_ENGINEERING_PASS",
            "Actual v2 source/smoke acceptance required")
    for name, expected in prior["source_hashes"].items():
        require(artifact(ROOT / name)["sha256"] == expected, "Accepted A09 source changed")
    measured_path = ROOT / prior["actual_measurement"]["path"]
    require(artifact(measured_path)["sha256"] == prior["actual_measurement"]["sha256"],
            "Actual v2 measurement changed")
    measured = read(measured_path)
    smoke = measured["public_smoke"]
    actual_paths = []
    for item in smoke["intervals"]["5"]["files"]:
        path = ROOT / item["path"]
        require(artifact(path)["sha256"] == item["sha256"], "Actual closed source rows changed")
        actual_paths.append(path)
    require(0 < len(actual_paths) <= 20, "Bounded closed short-smoke rows required")
    frame = pl.read_parquet(actual_paths).sort("available_us", "symbol", "close_us")
    require(0 < frame.height <= 200 and frame["mode"].unique().to_list() == ["live"]
            and frame["version"].unique().to_list() == ["microstructure_l1_v2"],
            "Actual v2 live row binding mismatch")
    rows = frame.to_dicts()
    batch = build_micro_features_v2(rows)
    incremental, state = [], MicroFeatureState()
    midpoint = len(rows) // 2
    for index, row in enumerate(rows):
        if index == midpoint:
            snapshot = json.loads(json.dumps(state.export_state(), allow_nan=False))
            state = MicroFeatureState.from_snapshot(snapshot)
        incremental.append(state.ingest(row, asof_us=row["available_us"]))
    require(batch == incremental, "Actual batch/incremental/restart view mismatch")
    counts, ready, finite = Counter(), 0, 0
    for row in batch:
        require(row["mode"] == "live", "View provenance lost")
        counts[(row["symbol"], row["source_status"])] += 1
        ready += row["feature_ready"]
        for name in FEATURE_NAMES_V2:
            if row[name] is not None:
                require(math.isfinite(row[name]), "Nonfinite actual derived feature")
                finite += 1
    lint = subprocess.run([str(ROOT / ".venv/bin/ruff"), "check",
                           *[name for name in sources if name.endswith(".py")]],
                          capture_output=True, text=True, check=False)
    require(lint.returncode == 0, "Actual Ruff failed: " + lint.stdout + lint.stderr)
    require(sources == {name: artifact(ROOT / name)["sha256"] for name in source_names}
            and contract == micro_feature_contract_v2(), "A10 source changed during acceptance")
    receipt = {
        "status": "A10_CAUSAL_MICRO_FEATURE_VIEW_ENGINEERING_PASS",
        "created_utc": datetime.now(UTC).isoformat(), "source_hashes": sources,
        "verified_a09_acceptance": artifact(prior_path), "feature_contract": contract,
        "actual_tests": {**artifact(tests), "cases": 46, "failures": 0, "errors": 0, "skipped": 0},
        "actual_ruff_exit_code": lint.returncode, "actual_ruff_output": lint.stdout,
        "actual_source_measurement": artifact(measured_path),
        "actual_rows": frame.height, "actual_batch_incremental_restart_equal": True,
        "actual_input_rows_sha256": checksum(rows), "actual_feature_rows_sha256": checksum(batch),
        "actual_source_status_counts": [{"symbol": symbol, "status": source_status, "rows": count}
                                       for (symbol, source_status), count
                                       in sorted(counts.items())],
        "actual_ready_model_view_rows": ready, "actual_finite_feature_values": finite,
        "actual_final_state_sha256": checksum(state.export_state()),
        "actual_ram_at_acceptance": status(), "model_feature_names": list(MODEL_FEATURE_NAMES),
        "qa_scale_heavy_raw_only": list(SCALE_HEAVY_FEATURES),
        "actual_24h_capacity_accepted": False, "actual_24h_quality_accepted": False,
        "actual_14d_accepted": False, "actual_30d_accepted": False, "actual_60d_accepted": False,
        "alpha_eligible": False, "training_authorized": False, "healthy_credit_seconds": 0,
        "network_requests": 0, "orders_sent": 0, "collector_writes": 0,
        "limitations": "Primary numerical view acceptance with actual closed v2 public smoke rows; "
                       "no future label, correlation, fit or prediction selection. Short history "
                       "cannot satisfy 720-past-sample warmup; actual ready count retained. "
                       "Synthetic causality/normalization tests do not create real qualification.",
    }
    with output.open("x", encoding="utf-8") as writer:
        writer.write(json.dumps(receipt, indent=2, ensure_ascii=False, allow_nan=False) + "\n")
    print(json.dumps({"status": receipt["status"], "actual_rows": frame.height,
                      "actual_ready_model_view_rows": ready}))


if __name__ == "__main__":
    main()
