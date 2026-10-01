"""Primary A09 correctness acceptance using actual isolated tests and public v2 smoke."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import xml.etree.ElementTree as ET
from datetime import UTC, datetime
from pathlib import Path

from quant.microstructure_v2 import FEATURES, VERSION
from quant.paths import ROOT, STATE
from quant.resources import status

AUDIT = "CODEX_AUDIT_AND_NEXT_PLAN_2026-10-01.md"
AUDIT_SHA = "6845cf09cd21c9258d7e446e42327adc3b3864d699935915fc936f06fb664b91"
PRIOR = "reports/A07_RESILIENT_OBSERVER_ACCEPTANCE_20261001.json"


def require(ok, message):
    if not ok:
        raise ValueError(message)


def artifact(path):
    path = path.resolve()
    require(path.is_relative_to(ROOT) and path.is_file() and path.stat().st_size <= 4_000_000,
            "D artifact path/size bound")
    payload = path.read_bytes()
    require(len(payload) <= 4_000_000, "Artifact read bound")
    return {"path": str(path.relative_to(ROOT)), "sha256": hashlib.sha256(payload).hexdigest(),
            "bytes": len(payload)}


def read(path):
    artifact(path)
    result = json.loads(path.read_text())
    json.dumps(result, allow_nan=False)
    return result


def frozen():
    require(artifact(ROOT / AUDIT)["sha256"] == AUDIT_SHA, "Provided v4 audit changed")
    prior = read(ROOT / PRIOR)
    require(prior["status"] == "A07_RESILIENT_OBSERVER_ENGINEERING_PASS",
            "Prior wrapper receipt not accepted")
    expected = {PRIOR: artifact(ROOT / PRIOR)["sha256"], AUDIT: AUDIT_SHA}
    for field in ("source_hashes", "verified_prior_files"):
        for name, checksum in prior[field].items():
            require(name not in expected or expected[name] == checksum, "Frozen binding conflict")
            expected[name] = checksum
    for name, checksum in expected.items():
        require(artifact(ROOT / name)["sha256"] == checksum, "Prior source changed: " + name)
    return expected


def cases(path):
    artifact(path)
    result = list(ET.parse(path).getroot().iter("testcase"))
    require(not any(list(case.iter(tag)) for case in result
                    for tag in ("failure", "error", "skipped")), "Actual tests not all passed")
    names = {(case.get("classname"), case.get("name")) for case in result}
    require(len(names) == len(result), "Duplicate testcase")
    return names


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tests", type=Path, required=True)
    parser.add_argument("--measurement", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    tests, measured_path, output = (path.resolve() for path in
                                   (args.tests, args.measurement, args.output))
    require(output.is_relative_to(ROOT / "reports") and not output.exists(),
            "New exclusive D acceptance required")
    before = frozen()
    actual_cases = cases(tests)
    first = cases(ROOT / "reports/A09_MICROSTRUCTURE_V2_TESTS_20261001_V1.xml")
    require(len(first) == 72 and len(actual_cases) >= 79 and first <= actual_cases,
            "Original v2 cases not preserved")
    source_names = ("src/quant/microstructure_v2.py", "tests/test_microstructure_v2.py",
                    "docs/MODULE_A09_MICROSTRUCTURE_V2.md", "scripts/microstructure_v2.ps1",
                    "scripts/microstructure_v2.sh", "scripts/measure_a09_microstructure_v2.py",
                    "scripts/accept_a09_microstructure_v2.py")
    sources = {name: artifact(ROOT / name)["sha256"] for name in source_names}
    measured = read(measured_path)
    require(measured["status"] == "A09_REAL_SHORT_AND_STORAGE_OBSERVATION_COMPLETE"
            and measured["source_sha256_before"] == measured["source_sha256_after"]
            == sources["src/quant/microstructure_v2.py"]
            and measured["measurement_source_sha256"]
            == sources["scripts/measure_a09_microstructure_v2.py"],
            "Real measurement binding failed")
    require(VERSION == "microstructure_l1_v2" and len(FEATURES) == 19,
            "A09 v2 schema contract changed")
    smoke, storage = measured["public_smoke"], measured["storage"]
    require(smoke["status"] == "REAL_PUBLIC_V2_SHORT_SMOKE_PASS"
            and smoke["requested_seconds"] >= 90
            and smoke["run_result"]["version"] == VERSION
            and smoke["run_result"]["accepted_events"] > 0
            and smoke["run_result"]["credentials_used"] is False
            and smoke["closed_read_only_status"]["state"] == "STOPPED",
            "Actual public v2 smoke incomplete")
    native = Path(smoke["database"]).resolve()
    store = Path(smoke["store"]).resolve()
    require(native.is_relative_to(STATE) and native != STATE / "microstructure_v2.sqlite3"
            and store.is_relative_to(ROOT / "data") and store != ROOT / "data/microstructure_v2",
            "Smoke must not become default qualification data")
    checkpoint = smoke["closed_read_only_status"]["checkpoint"]
    for key, highwater in checkpoint["ids"].items():
        if key.endswith(":trade"):
            require(all(type(highwater[field]) is int and highwater[field] >= 0 for field in
                        ("f", "l", "last_agg_id", "last_raw_trade_id", "agg_id_high_water"))
                    and highwater["f"] <= highwater["l"] == highwater["last_raw_trade_id"]
                    and highwater["id"] == highwater["last_agg_id"]
                    <= highwater["agg_id_high_water"], "Actual saved raw highwater malformed")
    for interval, information in smoke["intervals"].items():
        require(information["rows"] > 0
                and all(information["schema"][name] == "Float64" for name in
                        ("spread_bps_last", "l1_total_depth_last", "L1_imbalance_last")),
                "Actual v2 last fields/schema incomplete at " + interval)
        if interval in ("1", "5"):
            require(information["reconstructable_valid_rows"] > 0, "No usable BBO")
        for evidence in information["files"]:
            require(artifact(ROOT / evidence["path"])["sha256"] == evidence["sha256"],
                    "Actual closed smoke file changed")
    require(len(storage["chunks"]) == 3 and all(chunk["seconds"] == 600
            for chunk in storage["chunks"]), "Finite storage probe missing")
    for chunk in storage["chunks"]:
        for evidence in chunk["intervals"].values():
            require(artifact(ROOT / evidence["path"])["sha256"] == evidence["sha256"],
                    "Finite storage file changed")
    expected_projection = (max(chunk["total_bytes"] for chunk in storage["chunks"])
                           * 144 * 180 * 13 + 9) // 10
    require(storage["conditional_180d_with_30_percent_margin_bytes"] == expected_projection
            and storage["finite_projection_within_cap"] == (expected_projection <= 8_000_000_000),
            "Finite capacity result must be preserved accurately")
    require(all(measured[key] is False for key in ("actual_24h_capacity_accepted",
                "actual_24h_quality_accepted", "alpha_eligible", "training_authorized"))
            and measured["healthy_credit_seconds"] == measured["orders_sent"] == 0,
            "Short smoke cannot qualify version time or alpha")
    lint = subprocess.run([str(ROOT / ".venv/bin/ruff"), "check",
                           *[name for name in sources if name.endswith(".py")]],
                          capture_output=True, text=True, check=False)
    require(lint.returncode == 0, "Actual Ruff failed: " + lint.stdout + lint.stderr)
    shell = subprocess.run(["bash", "-n", str(ROOT / "scripts/microstructure_v2.sh")],
                           capture_output=True, text=True, check=False)
    require(shell.returncode == 0, "Actual shell launcher parse failed")
    require(before == frozen() and sources == {name: artifact(ROOT / name)["sha256"]
                                               for name in source_names},
            "Sources changed across primary acceptance")
    receipt = {
        "status": "A09_MICROSTRUCTURE_V2_CORRECTNESS_ENGINEERING_PASS",
        "created_utc": datetime.now(UTC).isoformat(), "version": VERSION,
        "source_hashes": sources, "verified_prior_files": before,
        "actual_tests": {**artifact(tests), "cases": len(actual_cases), "failures": 0,
                         "errors": 0, "skipped": 0, "preserved_first_cases": 72},
        "actual_ruff_exit_code": lint.returncode, "actual_ruff_output": lint.stdout,
        "actual_shell_parse_exit_code": shell.returncode,
        "actual_measurement": artifact(measured_path), "actual_public_smoke": smoke,
        "finite_storage_probe": storage, "actual_disk_from_measurement": measured["final_disk"],
        "actual_ram_at_acceptance": status(),
        "actual_24h_capacity_accepted": False, "actual_24h_quality_accepted": False,
        "actual_14d_accepted": False, "actual_30d_accepted": False, "actual_60d_accepted": False,
        "alpha_eligible": False, "training_authorized": False, "healthy_credit_seconds": 0,
        "production_launch_authorized_scope": "V2 public data qualification only, no orders/models",
        "limitations": "Primary correctness/schema/real-short-smoke acceptance, no full UTC-day or "
                       "24h resource/storage acceptance. Finite high-entropy projection and any "
                       "failure retained; native/raw/total combined 180d budget remains separate. "
                       "Short smoke database/store never joins default v2 qualification clock.",
    }
    with output.open("x", encoding="utf-8") as writer:
        writer.write(json.dumps(receipt, indent=2, ensure_ascii=False, allow_nan=False) + "\n")
    print(json.dumps({"status": receipt["status"], "tests": len(actual_cases),
                      "finite_feature_projection_bytes": expected_projection,
                      "finite_projection_within_cap": storage["finite_projection_within_cap"]}))


if __name__ == "__main__":
    main()
