"""Bind actual descriptive QA tests, report, frozen sources and resource checks."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import subprocess
import sys
import xml.etree.ElementTree as ET
from datetime import UTC, datetime
from pathlib import Path

from quant import disk
from quant.paths import ROOT
from quant.resources import status

PRIOR_SHA = "737264a53bacd2c78e33c971a6931fb411d54766da0d498f0588f46a7579c926"
SOURCES = (
    "scripts/audit_microstructure_feature_stability.py",
    "tests/test_microstructure_feature_stability.py",
    "docs/MODULE_A07_FEATURE_STABILITY.md",
    "scripts/accept_microstructure_feature_stability.py",
)


def require(ok, message):
    if not ok:
        raise ValueError(message)


def sha(path):
    result = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1_048_576), b""):
            result.update(block)
    return result.hexdigest()


def document(path, ceiling=10_000_000):
    require(path.is_relative_to(ROOT) and path.stat().st_size <= ceiling, "Receipt path/size")
    return json.loads(path.read_text(encoding="utf-8"))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--tests", type=Path, required=True)
    parser.add_argument("--preservation", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    paths = {name: getattr(args, name).resolve() for name in
             ("report", "tests", "preservation", "output")}
    require(all(path.is_relative_to(ROOT / "reports") for path in paths.values()),
            "Evidence must stay in D project reports")
    require(not paths["output"].exists(), "Never overwrite existing evidence")
    initial = {name: sha(ROOT / name) for name in SOURCES}
    prior_path = ROOT / "reports/A07_QUALITY_DIAGNOSTIC_ACCEPTANCE.json"
    require(sha(prior_path) == PRIOR_SHA, "Frozen quality acceptance changed")
    prior = document(prior_path)
    preserve = document(paths["preservation"])
    require(preserve["status"] == "ANCILLARY_PRESERVATION_PASS"
            and len(preserve["verified_prior_files"]) == 38, "Missing frozen source scope")
    frozen = {**preserve["verified_prior_files"], **prior["source_hashes"],
              prior["tests"]["xml"]: prior["tests"]["sha256"],
              prior["actual_report"]["path"]: prior["actual_report"]["sha256"]}
    for name, expected in frozen.items():
        require(sha(ROOT / name) == expected, f"Frozen source/evidence changed: {name}")
    require(paths["tests"].stat().st_size <= 1_000_000, "Oversize test XML")
    xml = ET.parse(paths["tests"]).getroot()
    cases = list(xml.iter("testcase"))
    keys = [(case.get("classname"), case.get("name")) for case in cases]
    require(len(cases) == len(set(keys)) == 9
            and all(key[0] == "tests.test_microstructure_feature_stability" for key in keys),
            "Expected actual nine descriptive QA cases")
    require(not any(list(case.iter(tag)) for case in cases
                    for tag in ("failure", "error", "skipped")), "Tests did not all pass")
    result = document(paths["report"])
    require(result["status"] == "DESCRIPTIVE_FEATURE_QA_ONLY"
            and result["read_only"] and result["evidence_stage"] == "QA_ONLY",
            "Not descriptive read-only QA")
    require(result["prior_quality_acceptance_sha256"] == PRIOR_SHA, "Wrong prior binding")
    for name, expected in result["source_hashes"].items():
        require(sha(ROOT / name) == expected, f"Actual analysis source changed: {name}")
    for flag in ("alpha_eligible", "training_authorized", "actual_24h_capacity_accepted",
                 "actual_24h_quality_accepted", "predictive_diagnostics_authorized"):
        require(result[flag] is False, f"Forbidden qualification: {flag}")
    require(result["fits_executed"] == result["network_requests"] == 0, "Unexpected work")
    require(0 < result["process_max_rss_bytes"] < 512_000_000, "Diagnostic memory bound")
    quality, descriptive = result["quality_snapshot"], result["descriptive"]
    require(quality["integrity"] == "PASS" and quality["status"] == "INSUFFICIENT_EVIDENCE",
            "Real short snapshot quality mismatch")
    require(quality["diagnostic_source_sha256"] == prior["source_hashes"][
        "scripts/audit_microstructure_quality.py"], "Wrong frozen quality auditor")
    snapshot = quality["snapshot"]
    require(snapshot["query_only"] and snapshot["read_transaction_released_before_file_scan"]
            and 0 <= snapshot["read_transaction_seconds"] <= 5, "Long/live SQL read")
    common = quality["common_usable_1s_market_data"]
    pairs = common["totals"]["usable_seconds"]
    require(pairs == descriptive["paired_usable_seconds"] > 0, "Wrong paired denominator")
    require(sum(day.get("usable_seconds", 0) for day in common["utc_days"].values()) == pairs,
            "Common daily counts differ")
    spec = importlib.util.spec_from_file_location(
        "accepted_frozen_quality_constants", ROOT / "scripts/audit_microstructure_quality.py"
    )
    auditor = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = auditor
    spec.loader.exec_module(auditor)
    groups = descriptive["hour_groups"]
    require(0 < len(groups) <= 1440 and descriptive["maximum_pending_feature_rows"] == 2,
            "Descriptive retention limit")
    hours, total = {}, 0
    for key, group in groups.items():
        symbol, timestamp = key.split("/", 1)
        when = datetime.fromisoformat(timestamp)
        require(symbol in auditor.SYMBOLS and when.utcoffset().total_seconds() == 0
                and when.minute == when.second == when.microsecond == 0, "Bad UTC hour")
        n = group["paired_usable_seconds"]
        require(type(n) is int and 0 < n <= 3600, "Bad hourly count")
        hours.setdefault(timestamp, {})[symbol] = n
        total += n
        require(set(group["features"]) == set(auditor.FEATURES), "Missing 17-feature shape")
        for name, moment in group["features"].items():
            count, nulls, nonzero = (moment[field] for field in
                                    ("finite_count", "legal_null_count", "nonzero_count"))
            require(all(type(value) is int and value >= 0 for value in (count, nulls, nonzero))
                    and count + nulls == n and nonzero <= count, f"Wrong count: {key}/{name}")
            for field in ("sum_of_observed_values", "mean", "population_std", "min", "max"):
                value = moment[field]
                require(value is None or (type(value) in (int, float) and math.isfinite(value)),
                        f"Nonfinite moment: {key}/{name}")
            if count:
                require(all(moment[field] is not None for field in
                            ("mean", "population_std", "min", "max")), "Missing moment")
                require(moment["min"] <= moment["mean"] <= moment["max"]
                        and moment["population_std"] >= 0, "Inconsistent moment range")
                require(math.isclose(moment["mean"] * count, moment["sum_of_observed_values"],
                                     rel_tol=1e-9, abs_tol=1e-7), "Mean/sum/count mismatch")
            else:
                require(all(moment[field] is None for field in
                            ("mean", "population_std", "min", "max"))
                        and moment["sum_of_observed_values"] == 0, "Empty moment mismatch")
    require(total == 2 * pairs and all(set(values) == set(auditor.SYMBOLS)
            and len(set(values.values())) == 1 for values in hours.values()),
            "Double-counted, unmatched or missing hourly pair")
    alerts = any(group["range_alert_counts"] for group in groups.values())
    require(alerts == descriptive["range_alerts_present"] and not alerts,
            "Current snapshot range alert needs repair/review")
    lint = subprocess.run([str(ROOT / ".venv/bin/ruff"), "check", *[
        str(ROOT / name) for name in SOURCES if name.endswith(".py")
    ]], capture_output=True, text=True, check=False)
    require(lint.returncode == 0, "Actual Ruff failed: " + lint.stdout + lint.stderr)
    ram, occupancy = status(), disk.check(reserve=10_000_000)
    require(ram["ram_peak_bytes"] <= ram["ram_limit_bytes"], "Shared RAM exceeded bound")
    require(initial == {name: sha(ROOT / name) for name in SOURCES}
            and sha(prior_path) == PRIOR_SHA, "Bound sources changed during acceptance")
    receipt = {
        "module": "A07_FEATURE_STABILITY", "status": "DESCRIPTIVE_DATA_QA_ENGINEERING_PASS",
        "created_utc": datetime.now(UTC).isoformat(), "source_hashes": initial,
        "prior_quality_acceptance_sha256": PRIOR_SHA, "verified_frozen_files": frozen,
        "tests": {"path": str(paths["tests"].relative_to(ROOT)), "sha256": sha(paths["tests"]),
                  "cases": 9, "failures": 0, "errors": 0, "skipped": 0,
                  "seconds": sum(float(case.get("time", 0)) for case in cases),
                  "actual_ruff_exit_code": lint.returncode, "actual_ruff_output": lint.stdout},
        "actual_report": {"path": str(paths["report"].relative_to(ROOT)),
                          "sha256": sha(paths["report"]), "snapshot": snapshot,
                          "paired_usable_seconds": pairs, "hour_groups": len(groups),
                          "symbol_observations": total, "range_alerts_present": alerts},
        "resources": ram, "disk": occupancy, "training_authorized": False,
        "alpha_eligible": False, "actual_calendar_qualification": False,
        "fits_executed": 0, "orders_sent": 0, "network_requests": 0,
        "review_scope": "Primary acceptance checks actual XML, prior hashes, exact paired "
                        "denominators and moment consistency. No separate final agent review.",
        "limitations": "Short descriptive snapshot only; no 24h/14d/30d data admission, "
                       "predictive stability, storage guarantee or trading profitability.",
    }
    with paths["output"].open("x", encoding="utf-8") as stream:
        stream.write(json.dumps(receipt, ensure_ascii=False, indent=2, allow_nan=False) + "\n")
    print(json.dumps({"status": receipt["status"], "tests": 9, "paired_seconds": pairs,
                      "hour_groups": len(groups), "report": str(paths["output"])}))


if __name__ == "__main__":
    main()
