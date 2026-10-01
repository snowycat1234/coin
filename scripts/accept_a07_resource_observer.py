"""Engineering acceptance of actual short sampled A07 resource observations."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import subprocess
import xml.etree.ElementTree as ET
from datetime import UTC, datetime
from pathlib import Path

from quant import disk
from quant.paths import ROOT
from quant.resources import status


def require(ok, message):
    if not ok:
        raise ValueError(message)


def sha(path):
    result = hashlib.sha256()
    with Path(path).open("rb") as reader:
        for block in iter(lambda: reader.read(1_048_576), b""):
            result.update(block)
    return result.hexdigest()


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
                      allow_nan=False).encode()


def read(path):
    require(path.is_relative_to(ROOT) and path.stat().st_size <= 2_000_000,
            "Evidence path/size outside bound")
    return json.loads(path.read_text(encoding="utf-8"))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--directory", type=Path, required=True)
    parser.add_argument("--tests", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    folder, xml_path, output = (path.resolve() for path in
                                (args.directory, args.tests, args.output))
    require(folder.is_relative_to(ROOT / "reports/generated")
            and xml_path.is_relative_to(ROOT / "reports")
            and output.is_relative_to(ROOT / "reports") and not output.exists(),
            "New exclusive D evidence required")
    report_path = folder / "REPORT.json"
    measured = read(report_path)
    require(measured["status"] == "REAL_SHORT_SAMPLED_RESOURCE_WINDOW_COMPLETE"
            and measured["requested_seconds"] == 60
            and measured["measured_elapsed_seconds"] >= 60
            and measured["period_seconds"] == 10, "Incomplete actual short resource window")
    require(measured["collector_restarts"] == measured["collector_writes"]
            == measured["network_requests"] == 0, "Unexpected collector mutation/network")
    require(all(measured[key] is False for key in
                ("quality_accepted", "actual_24h_capacity_accepted", "alpha_eligible",
                 "training_authorized")), "Short sampler cannot qualify real data")
    require(xml_path.stat().st_size <= 1_000_000, "Oversize XML")
    xml = ET.parse(xml_path).getroot()
    cases = list(xml.iter("testcase"))
    require(len(cases) == 11 and len({(case.get("classname"), case.get("name"))
                                    for case in cases}) == 11,
            "Expected actual eleven observer cases")
    require(not any(list(case.iter(tag)) for case in cases
                    for tag in ("failure", "error", "skipped")), "Observer tests not passed")
    preserved = {}
    for name in ("reports/A07_MICROSTRUCTURE_ACCEPTANCE.json",
                 "reports/PUBLIC_COLLECTOR_V3_ACCEPTANCE.json",
                 "reports/A07_QUALITY_DIAGNOSTIC_ACCEPTANCE.json",
                 "reports/A07_FEATURE_STABILITY_ACCEPTANCE_20261001.json"):
        prior = read(ROOT / name)
        preserved[name] = sha(ROOT / name)
        for source, expected in prior["source_hashes"].items():
            require(sha(ROOT / source) == expected, f"Prior frozen source changed: {source}")
            preserved[source] = expected
    sources = measured["source_hashes"].copy()
    for name in ("tests/test_a07_resource_observer.py", "scripts/accept_a07_resource_observer.py",
                 "docs/MODULE_A07_RESOURCE_OBSERVATION.md"):
        sources[name] = sha(ROOT / name)
    for name, expected in sources.items():
        require(sha(ROOT / name) == expected, f"Observed source changed: {name}")
    sample_path = folder / "samples.jsonl"
    require(sample_path.stat().st_size <= 10_000_000
            and sha(sample_path) == measured["samples_sha256"], "Sample stream changed")
    head, count, first, last, peaks, maximum_gap = "0" * 64, 0, None, None, {}, 0
    raw_unavailable = 0
    with sample_path.open("rb") as reader:
        for line in reader:
            require(len(line) <= 32_000 and count < 5000, "Sample stream bound")
            record = json.loads(line)
            row = record["sample"]
            require(record["seq"] == count + 1 and record["previous_sha256"] == head,
                    "Sample stream sequence/head mismatch")
            head = hashlib.sha256(canonical({key: record[key] for key in
                                             ("seq", "previous_sha256", "sample")})).hexdigest()
            require(head == record["sha256"], "Sample stream hash mismatch")
            require(row["sql_released_before_inventory"] and 0 <= row["sql_read_seconds"] <= 5,
                    "Long live SQL reader")
            require(row["binding"]["mode"] == "live" and row["binding"]["implementation_sha256"]
                    == sources["src/quant/microstructure.py"], "Wrong live source")
            if last is not None:
                require((row["process"]["pid"], row["process"]["start_ticks"],
                         row["checkpoint"]["session"], row["binding"])
                        == (last["process"]["pid"], last["process"]["start_ticks"],
                            last["checkpoint"]["session"], last["binding"]),
                        "Spliced process/session")
                for key in ("cpu_ticks", "sampled_monotonic_seconds"):
                    require(row["process"][key] >= last["process"][key], "Process counter reversed")
                maximum_gap = max(maximum_gap, row["elapsed_monotonic_seconds"]
                                  - last["elapsed_monotonic_seconds"])
            values = {
                "raw_sampled_bytes": row["raw_inventory"]["sampled_bytes"],
                "native_sampled_bytes": sum(row["native_files_sampled_bytes"].values()),
                "vhd_sampled_bytes": row["global_vhd_sampled_bytes"],
                "collector_rss_sampled_bytes": row["process"]["rss_bytes"],
                "collector_lifetime_rss_hwm_bytes": row["process"]["lifetime_rss_hwm_bytes"],
                "aggregate_ram_sampled_bytes": row["aggregate_ram"]["ram_current_bytes"],
            }
            raw_unavailable += values["raw_sampled_bytes"] is None
            for key, value in values.items():
                if value is not None:
                    peaks[key] = max(peaks.get(key, 0), value)
            require(row["raw_inventory"]["atomic_snapshot"] is False
                    and row["raw_inventory"]["exact_unsampled_peak_known"] is False,
                    "Sampled raw inventory cannot be called an exact peak")
            require(row["aggregate_ram"]["swap_bytes"] == 0
                    and row["aggregate_ram"]["ram_limit_bytes"] <= 5_000_000_000,
                    "Shared RAM/swap bound")
            first = row if first is None else first
            last, count = row, count + 1
    require(count == measured["samples"] >= 4 and head == measured["head_sha256"]
            and first == measured["first"] and last == measured["last"]
            and peaks == measured["sampled_peaks"], "Stream/terminal summary mismatch")
    require(raw_unavailable == measured["raw_samples_unavailable"]
            and measured["raw_sampling_complete"] == (raw_unavailable == 0)
            and count - raw_unavailable >= 2, "Unknown raw sample accounting mismatch")
    span = (last["process"]["sampled_monotonic_seconds"]
            - first["process"]["sampled_monotonic_seconds"])
    cpu = (last["process"]["cpu_ticks"] - first["process"]["cpu_ticks"]
           ) / measured["clock_ticks_per_second"]
    require(math.isclose(span, measured["measured_elapsed_seconds"], abs_tol=1e-6)
            and cpu == measured["collector_cpu_seconds_in_observed_span"]
            and maximum_gap == measured["maximum_sample_gap_seconds"] <= 35,
            "CPU/span/gap arithmetic mismatch")
    require(peaks["raw_sampled_bytes"] < 4_000_000_000, "Raw sampled bytes exceed cap")
    lint = subprocess.run([str(ROOT / ".venv/bin/ruff"), "check", *[
        str(ROOT / name) for name in sources if name.endswith(".py")
    ]], capture_output=True, text=True, check=False)
    require(lint.returncode == 0, "Actual Ruff failed: " + lint.stdout + lint.stderr)
    ram, occupancy = status(), disk.check(reserve=10_000_000)
    for name, expected in sources.items():
        require(sha(ROOT / name) == expected, "Source changed during acceptance")
    receipt = {"status": "A07_RESOURCE_OBSERVER_SHORT_ENGINEERING_PASS",
               "created_utc": datetime.now(UTC).isoformat(), "source_hashes": sources,
               "verified_prior_files": preserved, "actual_report": {
                   "path": str(report_path.relative_to(ROOT)), "sha256": sha(report_path)},
               "tests": {"path": str(xml_path.relative_to(ROOT)), "sha256": sha(xml_path),
                         "cases": 11, "failures": 0, "errors": 0, "skipped": 0,
                         "actual_ruff_exit_code": lint.returncode,
                         "actual_ruff_output": lint.stdout},
               "actual_short_span_seconds": span, "actual_collector_cpu_seconds": cpu,
               "actual_samples": count, "sampled_peaks": peaks, "resources": ram, "disk": occupancy,
               "raw_samples_unavailable": raw_unavailable,
               "raw_sampling_complete": measured["raw_sampling_complete"],
               "alpha_eligible": False, "training_authorized": False,
               "actual_24h_capacity_accepted": False, "actual_24h_quality_accepted": False,
               "limitations": "Primary engineering acceptance, not a separate final agent review. "
                              "Real 60s samples; no exact peak or health credit; "
                              "24h data qualification or 180d storage guarantee."}
    with output.open("x", encoding="utf-8") as writer:
        writer.write(json.dumps(receipt, indent=2, ensure_ascii=False, allow_nan=False) + "\n")
    print(json.dumps({"status": receipt["status"], "samples": count, "span_seconds": span}))


if __name__ == "__main__":
    main()
