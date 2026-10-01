"""Primary engineering acceptance of two actual, unqualified A07 diagnostics."""

from __future__ import annotations

import hashlib
import json
import subprocess
import xml.etree.ElementTree as ET
from datetime import UTC, datetime

from quant.paths import ROOT
from quant.resources import status

SOURCES = {
    "scripts/audit_a07_resource_window.py":
        "b4504f0810206a29599f09e751734c18bf6d82ab185b69e820399d0347287a67",
    "tests/test_a07_resource_window_review.py":
        "3e07161be31eae555c55390b503f14f1704f69e4657fded6af5e000341dad92d",
    "docs/MODULE_A07_RESOURCE_WINDOW_REVIEW.md":
        "0305d750451d37fc93c5078ac6ad15c50964ef9354fbe80f1e8fd457b813c91a",
    "scripts/audit_a07_raw_retention.py":
        "fac11d7b586ffe6ab95dcd49a31692c0c5164f186c3fb73fdd9b5879ef680ffc",
    "tests/test_a07_raw_retention.py":
        "87ac10515568bb2fe38fa37807fa8c5c6d341a25aa620b5691b283284125e74f",
    "docs/MODULE_A07_RAW_RETENTION.md":
        "60e8aad1e19222d6fa6aaa5d53188080c026daf4fea874e224fc75f3c852365e",
}
TESTS = (
    ("reports/A07_RESOURCE_WINDOW_REVIEW_TESTS_20261001_V2.xml", 63,
     "3234e158374473a471a17f41913a76db0af4952f9b11c822ab6ad6b0cef65459"),
    ("reports/A07_RAW_RETENTION_TESTS_20261001_V3.xml", 21,
     "21bc6efee7e729dea3fdedf910b8236e3dc4101fbc9a7d1174a4f149fd2ae669"),
)
PRIOR = {
    "reports/A07_RESOURCE_OBSERVER_ACCEPTANCE_20261001.json":
        "79342daab8e447817a6e0120b1d1d4631ae90b9111ccc863c16af55f67c7a873",
    "reports/A03_GENERIC_INTEGRATION_ACCEPTANCE_20261001.json":
        "13663c92c925b929e72d9a83ae16b86a685fa91dac8212cb09e9af3403be1f9a",
}


def require(ok, reason):
    if not ok:
        raise ValueError(reason)


def artifact(name):
    path = (ROOT / name).resolve()
    require(path.is_relative_to(ROOT) and path.is_file()
            and path.stat().st_size <= 4_000_000, "Artifact path/size bound: " + name)
    payload = path.read_bytes()
    require(len(payload) <= 4_000_000, "Artifact read bound: " + name)
    return {"path": name, "sha256": hashlib.sha256(payload).hexdigest(),
            "bytes": len(payload)}


def read(name):
    artifact(name)
    value = json.loads((ROOT / name).read_text(encoding="utf-8"))
    json.dumps(value, allow_nan=False)
    return value


def frozen():
    expected = SOURCES.copy()
    for name, checksum in PRIOR.items():
        require(artifact(name)["sha256"] == checksum, "Prior acceptance changed")
        prior = read(name)
        expected[name] = checksum
        for key in ("source_hashes", "verified_prior_files"):
            for source, digest in prior.get(key, {}).items():
                require(source not in expected or expected[source] == digest,
                        "Conflicting frozen binding")
                expected[source] = digest
    for name, checksum in expected.items():
        require(artifact(name)["sha256"] == checksum, "Frozen source changed: " + name)
    return expected


def unqualified(value):
    for key in ("actual_24h_capacity_accepted", "actual_24h_quality_accepted",
                "alpha_eligible", "training_authorized"):
        require(value[key] is False, "Engineering cannot grant " + key)
    require(value["collector_writes"] == value["collector_restarts"]
            == value["network_requests"] == 0, "Diagnostic mutated collector/network")


def main():
    before = frozen()
    test_receipts = []
    for name, count, checksum in TESTS:
        evidence = artifact(name)
        require(evidence["sha256"] == checksum, "Actual test XML changed")
        xml = ET.parse(ROOT / name).getroot()
        cases = list(xml.iter("testcase"))
        require(len(cases) == count
                and len({(case.get("classname"), case.get("name")) for case in cases}) == count
                and not any(list(case.iter(tag)) for case in cases
                            for tag in ("failure", "error", "skipped")), "Tests not passed")
        test_receipts.append({**evidence, "cases": count, "failures": 0,
                              "errors": 0, "skipped": 0})
    short_name = "reports/A07_RESOURCE_WINDOW_SHORT_REVIEW_20261001_V1.json"
    pending_name = "reports/A07_RESOURCE_WINDOW_PENDING_REVIEW_20261001_V1.json"
    raw_name = "reports/generated/A07_RAW_RETENTION_20261001_V1.json"
    short, pending, raw = (read(name) for name in (short_name, pending_name, raw_name))
    for value in (short, pending, raw):
        unqualified(value)
        require(value["engineering_fixture_hook"] is False
                if "engineering_fixture_hook" in value else True, "Real evidence required")
    require(short["status"] == "SHORT_SAMPLED_RESOURCE_EVIDENCE_UNQUALIFIED"
            and short["integrity"] == "PASS" and short["samples"] == 7
            and short["measured_elapsed_seconds"] == 60.005372263003665
            and short["collector_cpu_seconds_in_observed_span"] == 2.35
            and short["raw_samples_unavailable"] == 0, "Actual short review mismatch")
    require(pending["status"] == "TERMINAL_REPORT_NOT_AVAILABLE"
            and pending["integrity"] == "NOT_EVALUATED", "Pending review scope mismatch")
    require(raw["status"] == "RAW_RETENTION_METADATA_OBSERVATION_COMPLETE"
            and raw["helper_sha256"] == SOURCES["scripts/audit_a07_raw_retention.py"],
            "Actual raw helper mismatch")
    inventory, snapshot = raw["inventory"], raw["source_snapshot"]
    require(inventory["status"] == "COMPLETE_NONATOMIC_METADATA_SCAN"
            and inventory["entries_seen"] == inventory["sampled_files"] == 909
            and inventory["sampled_bytes"] == 139_990_681
            and 0 <= inventory["scan_seconds"] <= 10
            and inventory["oldest_named_start_age_seconds_at_scan_end"] == 55500.592184
            and inventory["atomic_snapshot"] is False
            and inventory["gzip_closure_checked"] is False, "Raw snapshot scope mismatch")
    require(snapshot["sql_released_before_inventory"] is True
            and 0 <= snapshot["sql_read_seconds"] <= 5
            and snapshot["checkpoint_fresh_at_snapshot"] is True
            and snapshot["checkpoint"]["session"] == "4c51dc675f364596a22237be2397abea"
            and snapshot["raw_pruned_lifetime_summary"]["records"] == 0,
            "Snapshot binding or retirement scope mismatch")
    guards = raw["resource_guards"]
    require(all(guard["status"] == "OBSERVED" for guard in guards.values()),
            "Raw observation resource guards unavailable")
    disk = guards["whole_project_and_vhd"]["value"]
    require(disk["total_bytes"] == disk["project_bytes"] + disk["wsl_vhd_bytes"]
            == 9_056_676_008 and disk["hard_limit_bytes"] == 40_000_000_000
            and disk["status"] == "OK", "Actual disk observation mismatch")
    lint_sources = [name for name in SOURCES if name.endswith(".py")]
    lint_sources.append("scripts/accept_a07_diagnostics.py")
    lint = subprocess.run([str(ROOT / ".venv/bin/ruff"), "check", *lint_sources],
                          capture_output=True, text=True, check=False)
    require(lint.returncode == 0, "Actual Ruff failed: " + lint.stdout + lint.stderr)
    ram = status()
    require(ram["ram_current_bytes"] <= ram["ram_peak_bytes"] <= ram["ram_limit_bytes"]
            <= 5_000_000_000 and ram["swap_bytes"] == 0 and ram["gpu_used"] is False,
            "Actual shared RAM bound")
    require(before == frozen(), "Frozen sources changed during acceptance")
    names = (short_name, pending_name, raw_name,
             "reports/A07_RAW_RETENTION_ENGINEERING_TESTS_20261001_V3.json",
             "docs/A07_DIAGNOSTIC_REVIEW_20261001.md", "scripts/accept_a07_diagnostics.py")
    receipt = {
        "status": "A07_DIAGNOSTIC_MODULES_ENGINEERING_PASS",
        "created_utc": datetime.now(UTC).isoformat(),
        "modules": ["CLOSED_RESOURCE_WINDOW_STRUCTURAL_REVIEW", "RAW_RETENTION_METADATA_QA"],
        "source_hashes": {**SOURCES, **{name: artifact(name)["sha256"] for name in names[-2:]}},
        "verified_prior_files": before,
        "tests": test_receipts, "actual_ruff_exit_code": lint.returncode,
        "actual_ruff_output": lint.stdout,
        "actual_evidence": [artifact(name) for name in names[:-2]],
        "actual_short_samples": short["samples"],
        "actual_short_span_seconds": short["measured_elapsed_seconds"],
        "actual_raw_snapshot": {key: inventory[key] for key in
                                ("sampled_files", "sampled_bytes", "scan_seconds",
                                 "oldest_named_start_age_seconds_at_scan_end")},
        "actual_ram_at_acceptance": ram,
        "disk_observed_in_raw_report": disk,
        "disk_snapshot_utc": raw["created_utc"],
        "actual_24h_capacity_accepted": False, "actual_24h_quality_accepted": False,
        "actual_14d_accepted": False, "actual_30d_accepted": False,
        "alpha_eligible": False, "training_authorized": False, "healthy_credit_seconds": 0,
        "collector_writes": 0, "collector_restarts": 0, "network_requests": 0,
        "limitations": "Primary engineering acceptance after code review, actual focused tests "
                       "and real read-only runs; no additional final independent agent acceptance. "
                       "Disk snapshot belongs to the raw observation, not a new endpoint scan. "
                       "No continuous peaks, TTL retirement, complete UTC day, 24h resource/data, "
                       "14/30d research, profitability or 180d guarantee is established.",
    }
    output = ROOT / "reports/A07_DIAGNOSTIC_MODULES_ACCEPTANCE_20261001.json"
    with output.open("x", encoding="utf-8") as writer:
        writer.write(json.dumps(receipt, ensure_ascii=False, indent=2, allow_nan=False) + "\n")
    print(json.dumps({"status": receipt["status"],
                      "tests": sum(row["cases"] for row in test_receipts),
                      "output": str(output.relative_to(ROOT))}))


if __name__ == "__main__":
    main()
