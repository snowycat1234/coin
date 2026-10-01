"""Preserve closed artifacts after the v4 report-path failure; never accept capacity."""

from __future__ import annotations

import argparse
import json
import math
import sqlite3
from contextlib import closing
from datetime import UTC, datetime
from pathlib import Path

from measure_candidate_adapter_v4 import digest, load_fixture, runtime_snapshot

from quant import disk
from quant.paths import ROOT, STATE
from quant.resources import status
from quant.shadow import read_forward_evidence


def receipt(path):
    path = path.resolve()
    if not path.is_relative_to(ROOT / "reports") or path.stat().st_size > 1_000_000:
        raise ValueError("Use bounded original D reports")
    reference = {"path": str(path.relative_to(ROOT)), "sha256": digest(path)}
    return json.loads(path.read_text()), reference


def journal(path, after_us=None):
    if not path.is_relative_to(STATE) or path.stat().st_size > 100_000_000:
        raise ValueError("Independent bounded engineering journal required")
    image_sha = digest(path)
    audit = read_forward_evidence(path, include_records=False)
    if audit["mode"] != "engineering_simulation" or audit["provenance"] != "synthetic":
        raise ValueError("Explicit synthetic evidence only")
    with closing(sqlite3.connect(f"file:{path}?mode=ro", uri=True, timeout=2)) as reader:
        reader.row_factory = sqlite3.Row
        reader.execute("PRAGMA query_only=ON")
        where, params = ("", ()) if after_us is None else ("WHERE received_us>?", (after_us,))
        categories = [dict(row) for row in reader.execute(
            "SELECT kind,COUNT(*) records,SUM(LENGTH(CAST(payload AS BLOB))) payload_bytes,"
            "MAX(LENGTH(CAST(payload AS BLOB))) peak_payload_bytes FROM records "
            + where + " GROUP BY kind", params,
        )]
        statuses = dict(reader.execute(
            "SELECT json_extract(payload,'$.status'),COUNT(*) FROM records WHERE kind='order_event'"
            + ("" if after_us is None else " AND received_us>?")
            + " GROUP BY json_extract(payload,'$.status')", params,
        ))
        pages = {key: reader.execute(f"PRAGMA {key}").fetchone()[0]
                 for key in ("page_count", "page_size", "freelist_count")}
    if digest(path) != image_sha:
        raise RuntimeError("Closed source changed during readonly forensic audit")
    return {"path": str(path), "sha256": image_sha, "bytes": path.stat().st_size,
            "chain": {key: audit[key] for key in ("seq", "head_hash", "mode", "provenance")},
            "categories": categories, "order_status_counts": statuses, "pages": pages}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--normal", type=Path, required=True)
    parser.add_argument("--funded", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    normal, normal_ref = receipt(args.normal)
    funded, funded_ref = receipt(args.funded)
    output = args.output.resolve()
    if not output.is_relative_to(ROOT / "reports") or output.exists():
        raise ValueError("Exclusive new D receipt required")
    bound = normal["source_sha256"]
    if any(digest(ROOT / name) != expected for name, expected in bound.items()):
        raise RuntimeError("Measured source no longer current")
    if runtime_snapshot() != normal["native_runtime_snapshot"]:
        raise RuntimeError("Measured native snapshot differs")
    if funded["native_runtime_snapshot"] != normal["native_runtime_snapshot"]:
        raise RuntimeError("Funded measurement used a different source snapshot")
    if funded["test_receipt"]["sha256"] != normal["test_receipt_sha256"]:
        raise RuntimeError("Different actual test receipts")
    if normal["status"] != "COMPLETE_NORMAL_SYNTHETIC_PATH_ONLY" or not normal["recovery_exact"]:
        raise RuntimeError("Complete, independently saved normal path required")
    main_db = Path(normal["database_paths"]["journal"]).resolve()
    if not main_db.parent.name.startswith("a03-capacity-"):
        raise ValueError("Use the original independent capacity folder")
    for name, expected in normal["file_sha256"].items():
        path = main_db.parent / name
        if path.parent != main_db.parent or digest(path) != expected:
            raise RuntimeError("Normal-stage closed image differs from original receipt")
    main_info = journal(main_db)
    if (main_info["chain"]["seq"] != normal["record_count"]
            or main_info["chain"]["head_hash"] != normal["audit_head"]):
        raise RuntimeError("Normal chain does not match the saved receipt")
    fixture = load_fixture()
    pressure_folder = main_db.parent / "attempt_probe"
    pressure = journal(pressure_folder / "journal.sqlite3", (fixture.END + 200) * 1000)
    if pressure["order_status_counts"].get("CAPACITY_OR_RISK", 0) < 1800:
        raise RuntimeError("Closed pressure stage did not exercise the declared attempts")
    pressure["files"] = {p.name: {"bytes": p.stat().st_size, "sha256": digest(p)}
                         for p in pressure_folder.iterdir() if p.suffix == ".sqlite3"}
    probe = funded["probe"]
    if (funded["status"] != "FUNDED_CONGESTION_ENGINEERING_DIAGNOSTIC_ONLY"
            or probe["stage"] != "FINITE_ENGINEERING_TRAJECTORY_COMPLETED"
            or probe["attempts"] < 1800 or not probe["readonly_chain_verified"]):
        raise RuntimeError("Actual completed funded-pressure measurement required")
    for name, expected in probe["final_database_sha256"].items():
        if digest(Path(probe["database_paths"]["journal"]).parent / name) != expected:
            raise RuntimeError("Funded pressure artifact changed")
    normal_increment = max(
        0, sum(normal["final_files"].values()) - sum(normal["seed_files"].values())
    )
    ledger = disk.check(reserve=0)
    micro = ROOT / "data/microstructure_v1"
    reserves = {
        "A07_features_remaining": max(0, 8_000_000_000 - disk.tree_bytes(micro / "features")),
        "A07_raw_remaining": max(0, 4_000_000_000 - disk.tree_bytes(micro / "raw")),
        "public_v3_future": 2_000_000_000,
        "A07_native_audit_future": 1_000_000_000,
    }
    active_scale = max(1, 2400 / probe["attempts"])
    daily = normal_increment + math.ceil(24 * probe["increment_bytes"] * active_scale)
    forecast = ledger["total_bytes"] + sum(reserves.values()) + math.ceil(225 * daily)
    if forecast < 36_000_000_000:
        raise RuntimeError("Do not use this failure-only report to award capacity")
    if (any(digest(ROOT / name) != expected for name, expected in bound.items())
            or runtime_snapshot() != normal["native_runtime_snapshot"]
            or digest(args.normal.resolve()) != normal_ref["sha256"]
            or digest(args.funded.resolve()) != funded_ref["sha256"]):
        raise RuntimeError("Bindings changed during readonly forensics")
    document = {
        "status": "REPORT_PATH_FAILURE_AND_MEASURED_COMBINED_FORECAST_NOT_ACCEPTED",
        "created_at_utc": datetime.now(UTC).isoformat(),
        "runtime_failure": {"exit_code": 1, "file": "scripts/measure_candidate_adapter_v4.py",
                            "line": 527, "error_type": "ValueError",
                            "reason": "relative normal_output passed to relative_to(absolute ROOT)",
                            "terminal_evidence": "Actual unified exec session 67027 exit1"},
        "normal_stage": normal_ref, "funded_pressure_receipt": funded_ref,
        "normal_journal": main_info, "closed_v4_pressure": pressure,
        "normal_increment_bytes": normal_increment,
        "alternate_funded_pressure_increment_bytes": probe["increment_bytes"],
        "active_order_scale": active_scale, "daily_increment_without_payload_scale": daily,
        "forecast_without_additional_payload_scale_bytes": forecast,
        "disk": ledger, "joint_reserves_bytes": reserves, "resources": status(),
        "original_v4_probe_seed_metadata_recovered": False,
        "forensic_scope": "Saved normal stage plus closed original pressure chain. Original v4 "
                          "in-memory probe seed sizes were lost; no invented replacement. "
                          "Combined forecast independently uses the separately saved funded "
                          "measurement, adds normal growth, eight active goals and 25% margin. "
                          "No extra payload scale; still over intake. A finite forecast, "
                          "not an observed physical overflow or universal 180d bound.",
        "source_sha256": bound, "native_runtime_snapshot": normal["native_runtime_snapshot"],
        "forensic_helper_sha256": digest(Path(__file__)),
        "capacity_accepted": False, "production_authorized": False,
        "actual_qualification_days": 0, "training_fits": 0,
        "network_requests": 0, "gpu_used": False,
    }
    with output.open("x", encoding="utf-8") as writer:
        writer.write(json.dumps(document, indent=2, allow_nan=False) + "\n")
    print(json.dumps({"status": document["status"], "normal_increment": normal_increment,
                      "pressure_attempts": pressure["order_status_counts"]["CAPACITY_OR_RISK"],
                      "combined_forecast_without_payload_scale": forecast}))


if __name__ == "__main__":
    main()
