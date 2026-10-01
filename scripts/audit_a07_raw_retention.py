"""Read-only, bounded A07 raw filename-age and physical inventory diagnostics."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import sqlite3
import stat
import time
from contextlib import closing
from datetime import UTC, datetime
from pathlib import Path

from quant import disk
from quant.paths import ROOT, STATE
from quant.resources import status

ACCEPTANCE = "reports/A07_MICROSTRUCTURE_ACCEPTANCE.json"
ACCEPTANCE_SHA = "d0acb843b0f616e777ddeb698245a2e5d5cf10b03a0baf1718b295094f894517"
VERSION = "microstructure_l1_v1"
RETENTION_US = 86_400_000_000
RAW_CAP = 4_000_000_000
NAME = re.compile(r"raw-([1-9][0-9]{0,18})-([0-9a-f]{8})\.jsonl\.gz\Z")


class Rejected(ValueError):
    """Metadata does not establish the accepted raw source or inventory."""


def require(ok, message):
    if not ok:
        raise Rejected(message)


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def sha(path):
    result = hashlib.sha256()
    with Path(path).open("rb") as reader:
        for block in iter(lambda: reader.read(1_048_576), b""):
            result.update(block)
    return result.hexdigest()


def utc(stamp):
    return datetime.fromtimestamp(stamp / 1_000_000, UTC).isoformat() if stamp is not None else None


def parse_json(value, bound=64_000):
    require(len(value.encode()) <= bound, "JSON byte bound exceeded")

    def pairs(items):
        result = {}
        for key, item in items:
            require(key not in result, "Duplicate JSON key")
            result[key] = item
        return result

    return json.loads(value, object_pairs_hook=pairs,
                      parse_constant=lambda _: require(False, "Nonfinite JSON value"))


def no_symlink_path(path):
    require(path.is_absolute() and not any(part == ".." for part in path.parts),
            "Absolute path without parent escapes required")
    for candidate in (path, *path.parents):
        require(not candidate.is_symlink(), "Symlink path rejected")
    require(path.resolve() == path, "Path alias rejected")


def frozen_sources():
    path = ROOT / ACCEPTANCE
    require(path.stat().st_size <= 1_000_000 and sha(path) == ACCEPTANCE_SHA,
            "Frozen A07 acceptance changed")
    receipt = parse_json(path.read_text(), 1_000_000)
    require(receipt["status"] == "DATA_ENGINEERING_SHORT_ACCEPTANCE_PASS"
            and receipt["limits"]["raw_bytes"] == RAW_CAP
            and receipt["limits"]["raw_retention_seconds"] == RETENTION_US // 1_000_000,
            "Different accepted raw contract")
    for name, expected in receipt["source_hashes"].items():
        source = ROOT / name
        no_symlink_path(source)
        require(source.is_relative_to(ROOT) and sha(source) == expected,
                "Frozen source changed: " + name)
    return {ACCEPTANCE: ACCEPTANCE_SHA, **receipt["source_hashes"]}


def source_snapshot(database, store):
    """Release a short query_only read before touching the mutable raw inventory."""
    no_symlink_path(database)
    no_symlink_path(store)
    require(database.is_relative_to(STATE.resolve()) and database.is_file(),
            "Native D-hosted STATE database required")
    require(store == ROOT / "data/microstructure_v1" and store.is_dir(),
            "Exact accepted D feature store required")
    marker = store / ".microstructure-store.json"
    no_symlink_path(marker)
    require(marker.stat().st_size <= 4096, "Large ownership marker")
    require(parse_json(marker.read_text()) == {
        "database": str(database), "mode": "live", "version": VERSION,
    }, "Store/database ownership changed")
    started = time.monotonic()
    pruning = {"records": 0, "files": 0, "bytes": 0,
               "oldest_named_received_us": None, "latest_named_received_us": None}
    with closing(sqlite3.connect(database.as_uri() + "?mode=ro", uri=True, timeout=1)) as reader:
        reader.set_progress_handler(lambda: int(time.monotonic() - started > 5), 1000)
        reader.execute("PRAGMA query_only=ON")
        reader.execute("BEGIN")
        values = {}
        for key in ("binding", "checkpoint"):
            row = reader.execute("SELECT value FROM state WHERE key=?", (key,)).fetchone()
            require(row is not None, "Missing source state")
            values[key] = parse_json(row[0])
        head = reader.execute("SELECT seq,sha256 FROM audit ORDER BY seq DESC LIMIT 1").fetchone()
        require(head is not None, "Missing audit head")
        for _, _, payload in reader.execute(
            "SELECT seq,received_us,payload FROM audit WHERE kind='RAW_PRUNED' "
            "ORDER BY seq LIMIT 10001"
        ):
            require(pruning["records"] < 10_000 and time.monotonic() - started <= 5,
                    "Raw pruning snapshot bound exceeded")
            detail = parse_json(payload)
            require(all(type(detail[key]) is int and detail[key] >= 0
                        for key in ("count", "bytes")),
                    "Invalid raw pruning totals")
            oldest, latest = detail["oldest_us"], detail["latest_us"]
            require(type(oldest) is int and type(latest) is int and 0 <= oldest <= latest,
                    "Invalid raw pruning named-time range")
            pruning["records"] += 1
            pruning["files"] += detail["count"]
            pruning["bytes"] += detail["bytes"]
            for key, value, reducer in (("oldest_named_received_us", oldest, min),
                                        ("latest_named_received_us", latest, max)):
                pruning[key] = value if pruning[key] is None else reducer(pruning[key], value)
    elapsed = time.monotonic() - started
    require(elapsed <= 5, "Read snapshot exceeded five seconds")
    binding, checkpoint = values["binding"], values["checkpoint"]
    require(binding["mode"] == checkpoint["mode"] == "live"
            and binding["version"] == VERSION and binding["store"] == str(store)
            and binding["implementation_sha256"] == sha(ROOT / "src/quant/microstructure.py"),
            "Different live source binding")
    require(type(checkpoint["asof_us"]) is int and checkpoint["asof_us"] >= 0,
            "Invalid checkpoint time")
    now_us = time.time_ns() // 1000
    lag = (now_us - checkpoint["asof_us"]) / 1_000_000
    return {"binding": binding, "checkpoint": {key: checkpoint[key] for key in
            ("asof_us", "session", "connected", "accepted_events", "duplicate_events",
             "rejected_events", "observed_monotonic_seconds")},
            "checkpoint_observation_lag_seconds": lag,
            "checkpoint_fresh_at_snapshot": 0 <= lag <= 10,
            "audit_head_seq": head[0], "audit_head_sha256": head[1],
            "sql_read_seconds": elapsed, "sql_released_before_inventory": True,
            "raw_pruned_lifetime_summary": pruning,
            "audit_chain_verified_here": False,
            "audit_policy": "snapshot metadata only; full frozen quality audit remains required"}


def inventory_raw(directory, *, max_entries=20_000, max_seconds=10):
    """Constant-space metadata scan; never open/decompress gzip or recursively walk."""
    require(type(max_entries) is int and 0 < max_entries <= 20_000
            and type(max_seconds) in (int, float) and math.isfinite(max_seconds)
            and 0 < max_seconds <= 10, "Inventory budgets may only be reduced")
    no_symlink_path(directory)
    require(directory.is_dir(), "Raw directory missing")
    started, start_us = time.monotonic(), time.time_ns() // 1000
    seen, files, total, disappeared = 0, 0, 0, 0
    earliest = latest = None
    digest = hashlib.sha256()
    complete, reason = True, None
    with os.scandir(directory) as entries:
        for entry in entries:
            seen += 1
            if seen > max_entries or time.monotonic() - started > max_seconds:
                complete, reason = False, "ENTRY_OR_SCAN_BUDGET_EXCEEDED"
                break
            require(not entry.is_symlink(), "Raw symlink rejected")
            try:
                metadata = entry.stat(follow_symlinks=False)
                require(stat.S_ISREG(metadata.st_mode), "Unexpected raw directory/entry")
                matched = NAME.fullmatch(entry.name)
                require(matched is not None, "Unknown raw filename format")
                stamp = int(matched[1])
                require(stamp <= 253_402_300_799_999_999, "Unrepresentable raw named time")
                size = metadata.st_size
            except FileNotFoundError:
                disappeared += 1
                continue
            files, total = files + 1, total + size
            item = {"name": entry.name, "named_received_us": stamp, "sampled_size_bytes": size}
            if earliest is None or stamp < earliest["named_received_us"]:
                earliest = item
            latest = item if latest is None or stamp > latest["named_received_us"] else latest
            digest.update(canonical(item) + b"\n")
    end_us, elapsed = time.time_ns() // 1000, time.monotonic() - started
    if elapsed > max_seconds:
        complete, reason = False, "ENTRY_OR_SCAN_BUDGET_EXCEEDED"
    require(end_us >= start_us, "Wall time regressed during inventory")
    oldest_age = None if earliest is None else (end_us - earliest["named_received_us"]) / 1_000_000
    newest_age = None if latest is None else (end_us - latest["named_received_us"]) / 1_000_000
    if not complete:
        age, cap = "UNKNOWN_INCOMPLETE_INVENTORY", "UNKNOWN_INCOMPLETE_INVENTORY"
    elif files == 0:
        age, cap = "EMPTY_OBSERVED_NO_RETENTION_COVERAGE", "WITHIN_4GB_SAMPLED_METADATA"
    elif newest_age < 0:
        age, cap = "FUTURE_NAMED_RECEIPT_OBSERVED", "NOT_ESTABLISHED_FUTURE_NAMED_TIME"
    else:
        age = ("WITHIN_24H_NAMED_START_ENVELOPE_OBSERVED" if oldest_age <= 86400
               else "OUTSIDE_24H_NAMED_START_ENVELOPE_OBSERVED")
        cap = "WITHIN_4GB_SAMPLED_METADATA" if total <= RAW_CAP else "EXCEEDS_4GB_SAMPLED_METADATA"
    return {"status": "COMPLETE_NONATOMIC_METADATA_SCAN" if complete else "UNKNOWN_BUDGET_EXCEEDED",
            "reason": reason, "scan_started_utc": utc(start_us), "scan_finished_utc": utc(end_us),
            "scan_seconds": elapsed, "entry_budget": max_entries,
            "scan_budget_seconds": max_seconds,
            "entries_seen": seen, "sampled_files": files if complete else None,
            "sampled_bytes": total if complete else None,
            "partial_known_files_not_a_complete_sample": files if not complete else None,
            "partial_known_bytes_not_a_complete_sample": total if not complete else None,
            "concurrent_retired_or_missing_entries": disappeared,
            "earliest_observed_named_shard": earliest, "latest_observed_named_shard": latest,
            "oldest_named_start_age_seconds_at_scan_end": oldest_age,
            "newest_named_start_age_seconds_at_scan_end": newest_age,
            "age_envelope_observation": age, "raw_byte_cap_observation": cap,
            "enumeration_order_metadata_sha256": digest.hexdigest(),
            "atomic_snapshot": False, "exact_unsampled_peak_known": False,
            "gzip_closure_checked": False, "raw_event_completeness_certified": False,
            "pending_unsealed_tail": "unknown; latest named shard may be open; no gzip reads",
            "named_time_basis": "accepted collector shard-start received_us in filename; "
                                "not mtime, exchange time, latest record or content verification"}


def audit_retention(*, database=None, store=None, max_entries=20_000, max_seconds=10):
    database = STATE / "microstructure.sqlite3" if database is None else Path(database)
    store = ROOT / "data/microstructure_v1" if store is None else Path(store)
    report = {"module": "A07_RAW_RETENTION_METADATA_QA", "created_utc": utc(time.time_ns() // 1000),
              "status": "NOT_ESTABLISHED", "read_only": True,
              "helper_sha256": sha(Path(__file__)), "source_hashes": {}, "source_snapshot": None,
              "inventory": None, "network_requests": 0, "collector_writes": 0,
              "collector_restarts": 0, "alpha_eligible": False, "training_authorized": False,
              "actual_24h_capacity_accepted": False, "actual_24h_quality_accepted": False,
              "actual_14d_accepted": False, "actual_30d_accepted": False,
              "healthy_time_credit_seconds": 0,
              "contract": {"raw_cap_bytes": RAW_CAP, "raw_retention_seconds": 86400,
                  "shard_rotation": "on append when prior shard age>=60s or uncompressed>=4MB",
                  "purge_cadence": "startup; each append via prune_for_reserve; flush after "
                                    "advance to a new second (also recv timeout near1s)",
                  "purge_predicate": "named shard start < current receipt/advance time -24h; "
                                     "closed oldest shards also removed for reserved byte cap",
                  "cadence_limit": "no kernel timer or guaranteed instantaneous wall-clock TTL; "
                                    "IO, stalls, stopped process and scan races can delay it",
                  "pruning_audit": "RAW_PRUNED aggregate count/bytes/oldest/latest starts; "
                                   "not a retired filename ledger or receipt integrity proof"},
              "limitations": "Single non-atomic metadata observation; no exact peak, raw content "
                              "integrity, gzip closure, health, duration or alpha qualification. "
                              "4GB raw comparison does not certify native SQLite/WAL/SHM growth, "
                              "180d features or total project+entire VHD budget."}
    try:
        sources = frozen_sources()
        report["source_hashes"] = sources
        report["source_snapshot"] = source_snapshot(database, store)
        report["inventory"] = inventory_raw(store / "raw", max_entries=max_entries,
                                           max_seconds=max_seconds)
        require(sources == frozen_sources(), "Frozen source changed during diagnosis")
        report["status"] = ("RAW_RETENTION_METADATA_OBSERVATION_COMPLETE"
                            if report["inventory"]["status"] == "COMPLETE_NONATOMIC_METADATA_SCAN"
                            else "RAW_RETENTION_UNKNOWN_BUDGET_EXCEEDED")
    except (Rejected, OSError, KeyError, sqlite3.Error, ValueError) as error:
        report.update(status="RAW_RETENTION_NOT_ESTABLISHED", reason=str(error),
                      failure_type=type(error).__name__)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    output = args.output.absolute()
    no_symlink_path(output)
    require(output.is_relative_to(ROOT / "reports") and output.suffix == ".json"
            and output.parent.is_dir() and not output.exists(), "New exclusive D report required")
    guards = {}
    for label, check in (("aggregate_ram", status),
                         ("whole_project_and_vhd", lambda: disk.check(reserve=2_000_000))):
        try:
            guards[label] = {"status": "OBSERVED", "value": check()}
        except (OSError, RuntimeError) as error:
            guards[label] = {"status": "GUARD_NOT_ESTABLISHED_OR_REJECTED",
                             "error_type": type(error).__name__, "reason": str(error)}
    report = audit_retention()
    report["resource_guards"] = guards
    report["global_resource_constraints_accepted"] = False
    report["guard_boundary"] = (
        "RuntimeError from RAM or whole-disk guard is not evidence of raw expiry/cap failure; "
        "inspect that independent named guard. Native files already belong to entire VHD; "
        "do not add them twice."
    )
    payload = json.dumps(report, indent=2, ensure_ascii=False, allow_nan=False) + "\n"
    require(len(payload.encode()) <= 2_000_000, "Output byte bound exceeded")
    with output.open("x", encoding="utf-8") as writer:
        writer.write(payload)
    print(json.dumps({"status": report["status"], "output": str(output),
                      "actual_24h_capacity_accepted": False, "alpha_eligible": False}))
    if report["status"] == "RAW_RETENTION_NOT_ESTABLISHED":
        raise SystemExit(2)


if __name__ == "__main__":
    main()
