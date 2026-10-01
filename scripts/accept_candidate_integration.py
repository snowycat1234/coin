"""Finalize engineering-only A03 receipt from actual tests and measured capacity."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import xml.etree.ElementTree as ET
from datetime import UTC, datetime
from pathlib import Path

from quant import disk
from quant.paths import ROOT, STATE
from quant.resources import status
from quant.shadow import read_forward_evidence


def require(ok, message):
    if not ok:
        raise ValueError(message)


def local(path):
    path = Path(path).resolve()
    require(path.is_relative_to(ROOT), "Evidence/source outside D project")
    return path


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as reader:
        for block in iter(lambda: reader.read(1_048_576), b""):
            digest.update(block)
    return digest.hexdigest()


def metadata(path):
    path = local(path)
    require(path.stat().st_size <= 2_000_000, "Oversize receipt")
    return json.loads(path.read_text(encoding="utf-8"))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--capacity", type=Path, required=True)
    parser.add_argument("--preservation", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    ram = status()
    capacity, preservation = metadata(args.capacity), metadata(args.preservation)
    require(preservation["status"] == "ANCILLARY_PRESERVATION_PASS", "Preservation not passed")
    for name, expected in preservation["verified_prior_files"].items():
        require(sha(local(ROOT / name)) == expected, f"Prior evidence/source changed: {name}")
    require(len(preservation["verified_prior_files"]) == 38, "Missing preservation scope")
    xml_path = local(ROOT / capacity["native_model_wiring_evidence"]["path"])
    require(xml_path.is_relative_to(ROOT / "reports"), "Actual test receipt outside reports")
    require(xml_path.stat().st_size <= 1_000_000, "Oversize XML")
    node = ET.parse(xml_path).getroot()
    cases = list(node.iter("testcase"))
    original_xml = local(ROOT / "reports/A03_CANDIDATE_NATIVE_RUNTIME_TESTS.xml")
    require(sha(original_xml) ==
            "bf899141ca68ffb0afbb8ab371f9388c1c5f587f9e30fc1b49ab67b77c785cec",
            "Original 50-case regression evidence changed")
    original_cases = list(ET.parse(original_xml).getroot().iter("testcase"))
    def key(case):
        return case.get("classname"), case.get("name")

    original_keys, final_keys = set(map(key, original_cases)), set(map(key, cases))
    require(len(original_cases) == len(original_keys) == 50
            and original_keys.issubset(final_keys) and len(final_keys) == len(cases),
            "Missing or duplicated original integration/legacy cases")
    require(any((case.get("classname") or "").endswith("test_candidate_storage")
                for case in cases), "Missing actual storage codec regression cases")
    codec_xml = local(ROOT / "reports/A03_CANDIDATE_CODEC_COMBINED_TESTS_20261001.xml")
    require(sha(codec_xml) ==
            "60d1dc4b1aa67e53888aa58c1da672ae9010911ab11b8d48885feced0c4adb0d",
            "Original 76-case codec regression evidence changed")
    codec_cases = list(ET.parse(codec_xml).getroot().iter("testcase"))
    require(len(codec_cases) == 76 and set(map(key, codec_cases)).issubset(final_keys),
            "Missing original 26 codec/restore cases")
    require(not any(list(case.iter(tag)) for case in cases
                    for tag in ("failure", "error", "skipped")), "Final tests not passed")
    require(capacity["native_model_wiring_evidence"] == {
        "path": str(xml_path.relative_to(ROOT)), "sha256": sha(xml_path)
    }, "Capacity not bound to final actual tests")
    for name, expected in capacity["source_sha256"].items():
        require(sha(local(ROOT / name)) == expected, f"Measured source changed: {name}")
    snapshot = capacity.get("native_runtime_snapshot")
    if snapshot is not None:
        manifest_path = Path(snapshot["path"]).resolve()
        require(manifest_path.is_relative_to((STATE / "candidate-runtime").resolve()),
                "Native snapshot outside D-hosted STATE")
        require(manifest_path.stat().st_size <= 100_000
                and sha(manifest_path) == snapshot["sha256"], "Native snapshot receipt changed")
        manifest = json.loads(manifest_path.read_text())
        for name, expected in manifest["files"].items():
            require(Path(name).name == name and Path(name).suffix == ".py", "Invalid source member")
            require(sha(local(ROOT / "src/quant" / name)) == expected
                    and sha(manifest_path.parent / "quant" / name) == expected,
                    "Native snapshot differs from measured exact source")
    require(capacity["synthetic_seconds"] == 86400
            and capacity["quote_event_count"] == 172800
            and capacity["paired_closed_minutes"] == 1440, "Incomplete day fixture")
    require(capacity["no_fits"] and capacity["no_network"]
            and capacity["actual_qualification_days"] == 0
            and not capacity["alpha_authorized"]
            and not capacity["actual_24h_live_capacity_certified"],
            "Qualification boundary changed")
    require(capacity["recovery_exact"]
            and all(value > 0 for value in capacity["account_fill_counts"].values()),
            "Missing account fill/recovery evidence")
    normal_info = capacity.get("normal_stage", {})
    normal_path = local(ROOT / normal_info.get("path", ""))
    require(normal_path.is_file() and normal_path.is_relative_to(ROOT / "reports")
            and sha(normal_path) == normal_info.get("sha256"),
            "Missing immutable normal-stage receipt")
    normal = metadata(normal_path)
    require(normal["status"] == "COMPLETE_NORMAL_SYNTHETIC_PATH_ONLY"
            and normal["synthetic_seconds"] == 86400
            and normal["quote_event_count"] == 172800
            and normal["paired_closed_minutes"] == 1440
            and normal["recovery_exact"]
            and normal["source_sha256"] == capacity["source_sha256"]
            and normal["audit_head"] == capacity["audit_head"]
            and normal["record_count"] == capacity["record_count"]
            and normal["seed_files"] == capacity["seed_files"]
            and normal["seed_closed_snapshot_sha256"]
            == capacity["seed_closed_snapshot_sha256"]
            and normal["final_files"] == capacity["final_files"]
            and [sample["synthetic_hour"] for sample in normal["hour_samples"]]
            == list(range(1, 25)), "Normal-stage receipt differs from completed measurement")
    probe = capacity["low_capacity_probe"]
    require(probe["attempts"] >= 1800 and probe["order_window_seconds"] == 300,
            "Missing actual low-capacity attempts")
    require(probe.get("funding_synthetic_seconds") == 3600
            and probe.get("readonly_chain_verified") is True
            and set(probe.get("funded_buy_fills", {}))
            == {"candidate", "B2", "fee_x2", "slippage_x2"}
            and all(set(counts) == {"BTCUSDT", "ETHUSDT"}
                    and all(value > 0 for value in counts.values())
                    for counts in probe["funded_buy_fills"].values())
            and all(row["account"]["positions"][symbol] > 0
                    for row in probe["initial_funded_accounts"].values()
                    for symbol in ("BTCUSDT", "ETHUSDT")),
            "Missing actual four-account/two-asset funding before pressure")
    require(probe["order_status_counts"].get("CAPACITY_OR_RISK") == probe["attempts"]
            and not any(name.startswith("CANCELLED_HEALTH")
                        for name in probe["order_status_counts"]),
            "Pressure fixture substituted health cancellation for capacity attempts")
    require(probe["increment_bytes"] == max(0, sum(probe["files_after_close"].values())
                                            - sum(probe["seed_files"].values())),
            "Probe increment differs from actual file sizes")
    increment = capacity["actual_24h_increment_bytes"]
    require(increment == max(0, sum(capacity["final_files"].values())
                              - sum(capacity["seed_files"].values())), "Day size mismatch")
    payload_scale = capacity["sustained_low_capacity_observed_checkpoint_payload_scale"]
    active = increment + math.ceil(24 * probe["increment_bytes"]
                                  * capacity["sustained_low_capacity_active_order_scale"]
                                  * payload_scale)
    require(active == capacity["sustained_low_capacity_daily_increment_bytes"],
            "Congestion projection arithmetic differs")
    ledger = capacity["final_disk_snapshot"]
    require(ledger["total_bytes"] == ledger["project_bytes"] + ledger["wsl_vhd_bytes"],
            "Wrong full disk scope")
    reserves = sum(capacity["joint_budget_reserves_bytes"].values())
    nominal = ledger["total_bytes"] + reserves + 360 * increment
    congested = ledger["total_bytes"] + reserves + math.ceil(180 * active * 1.25)
    require(nominal == capacity["joint_nominal_180d_projected_total_bytes"]
            and congested == capacity["joint_sustained_low_capacity_180d_projected_total_bytes"],
            "Combined budget arithmetic differs")
    require(nominal < 36_000_000_000 and congested < 36_000_000_000,
            "Measured hourly forecast exceeds intake budget; capacity not accepted")
    journal = Path(capacity["database_paths"]["journal"]).resolve()
    require(journal.is_relative_to(STATE.resolve())
            and journal.parent.name.startswith("a03-capacity-"),
            "Use the independent engineering measurement DB")
    require(set(capacity["seed_closed_snapshot_sha256"])
            == {"source.sqlite3", "journal.sqlite3"}, "Missing committed normal baseline")
    for name, expected in capacity["seed_closed_snapshot_sha256"].items():
        path = journal.parent / "initial-closed-snapshot" / name
        require(sha(path) == expected and path.stat().st_size == capacity["seed_files"][name],
                "Normal committed baseline changed")
    for name, expected in capacity["file_sha256"].items():
        path = (journal.parent / name).resolve()
        require(path.parent == journal.parent and path.suffix == ".sqlite3",
                "Wrong native artifact")
        require(sha(path) == expected, "Measured database changed")
    audit = read_forward_evidence(journal, include_records=False)
    require(audit["head_hash"] == capacity["audit_head"]
            and audit["seq"] == capacity["record_count"]
            and audit["mode"] == "engineering_simulation"
            and audit["provenance"] == "synthetic", "Independent readonly journal audit failed")
    pressure_journal = Path(probe["database_paths"]["journal"]).resolve()
    require(pressure_journal.parent == journal.parent / "attempt_probe",
            "Use the independently measured pressure folder")
    require(set(probe["original_closed_baseline_sha256"])
            == {"source.sqlite3", "journal.sqlite3"}, "Missing committed pressure baseline")
    for name, expected in probe["original_closed_baseline_sha256"].items():
        path = pressure_journal.parent / "initial-closed-snapshot" / name
        require(sha(path) == expected and path.stat().st_size == probe["seed_files"][name],
                "Pressure committed baseline changed")
    for name, expected in probe["final_database_sha256"].items():
        path = (pressure_journal.parent / name).resolve()
        require(path.parent == pressure_journal.parent and path.suffix == ".sqlite3"
                and sha(path) == expected, "Measured pressure database changed")
    pressure_audit = read_forward_evidence(pressure_journal, include_records=False)
    require(pressure_audit["seq"] == probe["pressure_record_count"]
            and pressure_audit["head_hash"] == probe["pressure_head_hash"]
            and pressure_audit["mode"] == "engineering_simulation"
            and pressure_audit["provenance"] == "synthetic",
            "Independent readonly funded-pressure chain audit failed")
    live_disk = disk.check(reserve=10_000_000)
    output = local(args.output)
    require(output.is_relative_to(ROOT / "reports") and output.suffix == ".json",
            "New receipt must remain in reports")
    sources = dict(capacity["source_sha256"])
    for path in (Path(__file__), ROOT / "scripts/audit_candidate_integration.py",
                 ROOT / "scripts/stage_candidate_runtime.py",
                 ROOT / "docs/MODULE_A03_CANDIDATE_INTEGRATION.md"):
        sources[str(path.relative_to(ROOT))] = sha(path)
    report = {
        "status": "CANDIDATE_GENERIC_INTEGRATION_ENGINEERING_PASS",
        "created_at_utc": datetime.now(UTC).isoformat(),
        "scope": "Hourly generic/40-feature wiring, exact recovery, account isolation, "
                 "legacy compatibility and finite measured storage forecasts; "
                 "not alpha or live admission",
        "tests": {"cases": len(cases), "original_cases_preserved": 50,
                  "original_codec_cases_preserved": 26,
                  "failures": 0, "errors": 0, "skipped": 0,
                  "path": str(xml_path.relative_to(ROOT)), "sha256": sha(xml_path)},
        "source_hashes": sources,
        "capacity_report": {"path": str(local(args.capacity).relative_to(ROOT)),
                            "sha256": sha(args.capacity)},
        "preservation_report": {"path": str(local(args.preservation).relative_to(ROOT)),
                                "sha256": sha(args.preservation)},
        "native_runtime_snapshot": snapshot,
        "normal_stage": normal_info,
        "independent_readonly_journal_audit": {key: audit[key] for key in
                                               ("seq", "head_hash", "mode", "provenance")},
        "independent_readonly_pressure_audit": {key: pressure_audit[key] for key in
                                                ("seq", "head_hash", "mode", "provenance")},
        "nominal_180d_combined_forecast_bytes": nominal,
        "congested_180d_combined_forecast_bytes": congested,
        "capacity_limitations": "Synthetic 1Hz hourly fixture and scaled short congestion probe. "
                                "Not legacy15m, live24h, arbitrary fault flapping "
                                "or a universal bound. Existing warning/intake/hard guards "
                                "remain required; production denied.",
        "resources": ram, "disk": live_disk,
        "training_fits_executed": 0, "locked_prices_read": 0, "gpu_used": False,
        "real_forward_days": 0, "alpha_candidate": False, "production_authorized": False,
        "exchange_orders_sent": 0,
        "acceptance_method": "Primary agent readonly code/test/artifact review "
                             "after peer review findings "
                             "were repaired; no claim of separate final peer acceptance",
    }
    with output.open("x", encoding="utf-8") as writer:
        writer.write(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + "\n")
    print(json.dumps({"status": report["status"], "tests": len(cases),
                      "nominal_forecast_bytes": nominal, "congested_forecast_bytes": congested,
                      "disk_bytes": live_disk["total_bytes"]}))


if __name__ == "__main__":
    main()
