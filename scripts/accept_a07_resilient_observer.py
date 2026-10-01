"""Accept the new exception wrapper's engineering scope, never real duration gates."""

from __future__ import annotations

import hashlib
import json
import subprocess
import xml.etree.ElementTree as ET
from datetime import UTC, datetime

from quant.paths import ROOT
from quant.resources import status

SOURCES = {
    "scripts/observe_a07_resources_resilient.py":
        "c9ae6b2f8ce24d13cd0773fa186c3d9b0c647212c12798549b02f13ff0f3e28d",
    "tests/test_a07_resilient_observer.py":
        "f8cb86fc3fb9234635ac1dd6ba268ba36d17259d356f9abc30682bf262071492",
    "docs/MODULE_A07_RESILIENT_OBSERVER.md":
        "575a29fc6ae93c07ed381c73869ac18ea490816a848f42b84664ed7ed8d0e05e",
}
PRIOR = "reports/A07_DIAGNOSTIC_MODULES_ACCEPTANCE_20261001.json"
PRIOR_SHA = "70ec8e947e0d794b435a261a9a475d41a74f2156f23ed6867c2be4fe7b6e387d"
PREFIX = "reports/generated/A07_RESILIENT_SHORT_20261001_V2/"
WRAPPER = "reports/A07_RESILIENT_SHORT_20261001_V2.json"
REVIEW = "reports/A07_RESILIENT_SHORT_REVIEW_20261001_V2.json"
XML = "reports/A07_RESILIENT_OBSERVER_TESTS_20261001_V3.xml"
XML_SHA = "1f9c4228e7ed9a94c70795f1e687f6cb59adde255c1e21534402b58eedca6a61"


def require(ok, message):
    if not ok:
        raise ValueError(message)


def artifact(name, maximum=4_000_000):
    path = (ROOT / name).resolve()
    require(path.is_relative_to(ROOT) and path.is_file()
            and path.stat().st_size <= maximum, "Artifact bound: " + name)
    value = path.read_bytes()
    require(len(value) <= maximum, "Artifact read bound: " + name)
    return {"path": name, "sha256": hashlib.sha256(value).hexdigest(), "bytes": len(value)}


def read(name):
    artifact(name)
    result = json.loads((ROOT / name).read_text())
    json.dumps(result, allow_nan=False)
    return result


def preserved():
    require(artifact(PRIOR)["sha256"] == PRIOR_SHA, "Prior receipt changed")
    result = {PRIOR: PRIOR_SHA, **SOURCES}
    prior = read(PRIOR)
    for field in ("source_hashes", "verified_prior_files"):
        for name, checksum in prior[field].items():
            require(name not in result or result[name] == checksum, "Binding conflict")
            result[name] = checksum
    for name, checksum in result.items():
        require(artifact(name)["sha256"] == checksum, "Frozen source changed: " + name)
    return result


def test_cases(name):
    artifact(name, 1_000_000)
    cases = list(ET.parse(ROOT / name).getroot().iter("testcase"))
    require(not any(list(case.iter(tag)) for case in cases
                    for tag in ("failure", "error", "skipped")), "Unpassed actual tests")
    names = {(case.get("classname"), case.get("name")) for case in cases}
    require(len(names) == len(cases), "Duplicate testcase")
    return names


def main():
    before = preserved()
    require(artifact(XML)["sha256"] == XML_SHA, "Actual V3 XML changed")
    original = test_cases("reports/A07_RESILIENT_OBSERVER_TESTS_20261001_V2.xml")
    repaired = test_cases(XML)
    require(len(original) == 21 and len(repaired) == 26 and original <= repaired,
            "Original 21 cases not preserved")
    wrapper, terminal, review = (read(name) for name in (WRAPPER, PREFIX + "REPORT.json", REVIEW))
    require(wrapper["status"] == "RESILIENT_WRAPPER_ENGINEERING_RETURN_ONLY"
            and wrapper["delegate_started"] and wrapper["delegate_returned"]
            and wrapper["owned_sampler_directory_established"]
            and wrapper["engineering_fixture_hook"] is False, "Actual wrapper incomplete")
    require(wrapper["source_binding_before"] == wrapper["source_binding_after"]
            and wrapper["source_binding_before"]["matches_frozen"]
            and wrapper["wrapper_source_before"] == wrapper["wrapper_source_after"]
            and wrapper["wrapper_source_after"]["sha256"]
            == SOURCES["scripts/observe_a07_resources_resilient.py"], "Wrapper binding mismatch")
    require(wrapper["delegated_argv"][1:] == ["--directory", str(ROOT / PREFIX),
            "--seconds", "60.0", "--period", "10.0"], "Delegated parameters changed")
    require(terminal["status"] == "REAL_SHORT_SAMPLED_RESOURCE_WINDOW_COMPLETE"
            and terminal["requested_seconds"] == 60 and terminal["period_seconds"] == 10
            and terminal["samples"] == 7 and terminal["measured_elapsed_seconds"] >= 60,
            "Actual repaired short window incomplete")
    require(review["status"] == "SHORT_SAMPLED_RESOURCE_EVIDENCE_UNQUALIFIED"
            and review["integrity"] == "PASS" and review["samples"] == 7
            and review["measured_elapsed_seconds"] == terminal["measured_elapsed_seconds"]
            and review["samples_sha256"] == terminal["samples_sha256"],
            "Independent structural review incomplete")
    for name in ("REPORT.json", "samples.jsonl"):
        measured = artifact(PREFIX + name, 10_000_000)
        capture = wrapper["sampler_artifacts"][name]
        require(capture["status"] == "READ_ONLY_HASHED"
                and capture["sha256"] == measured["sha256"]
                and capture["bytes"] == measured["bytes"], "Captured artifacts changed")
    for value in (wrapper, review):
        require(all(value[key] is False for key in ("actual_24h_capacity_accepted",
                    "actual_24h_quality_accepted", "alpha_eligible", "training_authorized"))
                and value["healthy_credit_seconds"] == 0
                and value["collector_writes"] == value["collector_restarts"]
                == value["network_requests"] == 0, "Engineering scope incorrectly elevated")
    archive = read("legacy/a07_resilient_before_io_guard_20261001/INDEX.json")
    require(archive["status"] == "PRE_REPAIR_SOURCE_BYTES_PRESERVED", "Archive missing")
    for item in archive["files"]:
        require(artifact(item["archived"])["sha256"] == item["sha256"], "Archive changed")
    v1 = read("reports/A07_RESILIENT_SHORT_20261001_V1.json")
    require(v1["wrapper_source_before"]["sha256"] == v1["wrapper_source_after"]["sha256"]
            == "b8bac47228c5592275816a76ae1308c2ecc0c8059e492b2a1aeb13725de8b516",
            "Actual initial attempt binding missing")
    lint = subprocess.run([str(ROOT / ".venv/bin/ruff"), "check",
                           *[name for name in SOURCES if name.endswith(".py")],
                           "scripts/accept_a07_resilient_observer.py"],
                          capture_output=True, text=True, check=False)
    require(lint.returncode == 0, "Actual Ruff failure: " + lint.stdout + lint.stderr)
    require(before == preserved(), "Sources changed during primary acceptance")
    self_name = "scripts/accept_a07_resilient_observer.py"
    names = (WRAPPER, PREFIX + "REPORT.json", PREFIX + "samples.jsonl", REVIEW, XML,
             "reports/A07_RESILIENT_SHORT_20261001_V1.json",
             "reports/A07_RESILIENT_OBSERVER_TESTS_20261001_V1.xml",
             "reports/A07_RESILIENT_OBSERVER_TESTS_20261001_V2.xml",
             "legacy/a07_resilient_before_io_guard_20261001/INDEX.json")
    receipt = {
        "status": "A07_RESILIENT_OBSERVER_ENGINEERING_PASS",
        "created_utc": datetime.now(UTC).isoformat(),
        "source_hashes": {**SOURCES, self_name: artifact(self_name)["sha256"]},
        "verified_prior_files": before,
        "actual_evidence": [artifact(name, 10_000_000) for name in names],
        "tests": {"cases": 26, "failures": 0, "errors": 0, "skipped": 0,
                  "preserved_original_cases": 21, "actual_ruff_exit_code": lint.returncode,
                  "actual_ruff_output": lint.stdout},
        "actual_short_samples": 7,
        "actual_short_span_seconds": terminal["measured_elapsed_seconds"],
        "actual_short_sampled_peaks": terminal["sampled_peaks"],
        "actual_disk_endpoint_from_terminal": terminal["final_disk"],
        "actual_ram_at_acceptance": status(),
        "actual_24h_capacity_accepted": False, "actual_24h_quality_accepted": False,
        "alpha_eligible": False, "training_authorized": False, "healthy_credit_seconds": 0,
        "collector_writes": 0, "collector_restarts": 0, "network_requests": 0,
        "limitations": "Primary engineering acceptance with independent defect review and repair, "
                       "isolated synthetic faults and a new real 60s run. No production resource "
                       "fault was injected, current 24h window was not replaced or restarted. "
                       "No complete-day, continuous peak, future profit or 180d storage guarantee.",
    }
    output = ROOT / "reports/A07_RESILIENT_OBSERVER_ACCEPTANCE_20261001.json"
    with output.open("x") as writer:
        json.dump(receipt, writer, indent=2, allow_nan=False)
        writer.write("\n")
    print(json.dumps({"status": receipt["status"], "tests": 26,
                      "span_seconds": receipt["actual_short_span_seconds"]}))


if __name__ == "__main__":
    main()
