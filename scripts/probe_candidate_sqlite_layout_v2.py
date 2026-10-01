"""Read-only-input SQLite layout diagnostic on small, closed synthetic journals."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sqlite3
import time
from contextlib import closing
from datetime import UTC, datetime
from pathlib import Path

from quant.paths import ROOT, STATE
from quant.resources import status
from quant.shadow import IMMUTABLE_TRIGGERS, ZERO_HASH, _record_hash

PAGE_SIZES = (4096, 8192, 16384, 32768)
ALLOCATION_LIMIT = 100_000_000


def digest(path):
    result = hashlib.sha256()
    with path.open("rb") as reader:
        for block in iter(lambda: reader.read(1_048_576), b""):
            result.update(block)
    return result.hexdigest()


def json_bytes(value):
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode()


def allocated(folder):
    total = sum(path.stat().st_size for path in folder.rglob("*") if path.is_file())
    if total > ALLOCATION_LIMIT:
        raise RuntimeError("SQLite diagnostic allocation exceeds 100 MB")
    return total


def journal_summary(path):
    """Stream all stored fields exactly; verify the original chain without writes."""
    with closing(sqlite3.connect(path.as_uri() + "?mode=ro&immutable=1", uri=True)) as db:
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA query_only=ON")
        schema = [
            tuple(row)
            for row in db.execute(
                "SELECT type,name,tbl_name,sql FROM sqlite_master ORDER BY type,name"
            )
        ]
        triggers = {
            row["name"]: row["sql"]
            for row in db.execute("SELECT name,sql FROM sqlite_master WHERE type='trigger'")
        }
        if not all(
            name in triggers and clause in triggers[name] and "RAISE(ABORT" in triggers[name]
            for name, clause in IMMUTABLE_TRIGGERS.items()
        ):
            raise RuntimeError("Immutable journal triggers differ")
        whole = hashlib.sha256()
        kinds, previous, count = {}, ZERO_HASH, 0
        fields = [row["name"] for row in db.execute("PRAGMA table_info(records)")]
        for row in db.execute("SELECT * FROM records ORDER BY seq"):
            count += 1
            record = {
                key: row[key]
                for key in ("seq", "received_us", "version", "kind", "prev_hash", "hash")
            }
            record["payload"] = json.loads(row["payload"])
            if (
                row["seq"] != count
                or row["prev_hash"] != previous
                or row["hash"] != _record_hash(record)
            ):
                raise RuntimeError("Full journal hash chain or sequence differs")
            previous = row["hash"]
            # Length framing preserves exact row/field/string boundaries.
            raw = json_bytes({field: row[field] for field in fields})
            framed = len(raw).to_bytes(8, "big") + raw
            whole.update(framed)
            item = kinds.setdefault(row["kind"], {"count": 0, "digest": hashlib.sha256()})
            item["count"] += 1
            item["digest"].update(framed)
        logical = {
            "columns": fields,
            "rows": count,
            "head_hash": previous,
            "all_exact_stored_fields_sha256": whole.hexdigest(),
            "all_record_kind_digests": {
                kind: {
                    "records": item["count"],
                    "all_exact_fields_sha256": item["digest"].hexdigest(),
                }
                for kind, item in kinds.items()
            },
            "schema_definition_sha256": hashlib.sha256(json_bytes(schema)).hexdigest(),
            "complete_chain_verified": True,
        }
        with path.open("rb") as reader:
            header = reader.read(100)
        format_versions = list(header[18:20])
        if format_versions not in ([1, 1], [2, 2]):
            raise RuntimeError("Unexpected SQLite file-header format versions")
        layout = {
            "page_size": db.execute("PRAGMA page_size").fetchone()[0],
            "page_count": db.execute("PRAGMA page_count").fetchone()[0],
            "freelist_count": db.execute("PRAGMA freelist_count").fetchone()[0],
            "journal_mode": "wal" if format_versions == [2, 2] else "delete",
            "sqlite_header_read_write_format": format_versions,
            "immutable_connection_reported_mode": db.execute("PRAGMA journal_mode").fetchone()[0],
            "closed_file_bytes": path.stat().st_size,
            "sha256": digest(path),
        }
        return {"path": str(path), "logical": logical, "layout": layout}


def layout_copy(original, target, page_size, original_mode):
    shutil.copyfile(original, target)
    with closing(sqlite3.connect(target)) as db:
        db.execute("PRAGMA journal_mode=DELETE")
        db.execute(f"PRAGMA page_size={page_size}")
        db.execute("VACUUM")
        if db.execute("PRAGMA page_size").fetchone()[0] != page_size:
            raise RuntimeError("SQLite did not apply requested page size")
        if original_mode == "wal":
            db.execute("PRAGMA journal_mode=WAL")
            db.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    result = journal_summary(target)
    if result["layout"]["journal_mode"] != original_mode:
        raise RuntimeError("Copy header journaling format did not preserve original")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--funded-receipt", type=Path, required=True)
    parser.add_argument("--directory", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    receipt, folder, output = (
        value.resolve() for value in (args.funded_receipt, args.directory, args.output)
    )
    if (
        not receipt.is_relative_to((ROOT / "reports").resolve())
        or not output.is_relative_to((ROOT / "reports").resolve())
        or output.exists()
        or not folder.is_relative_to(STATE.resolve())
        or not folder.name.startswith("a03-layout-")
        or folder.exists()
    ):
        raise ValueError("Fresh native layout folder and exclusive D report required")
    funded = json.loads(receipt.read_text())
    if (
        funded["status"] != "FUNDED_CONGESTION_ENGINEERING_DIAGNOSTIC_ONLY"
        or funded["probe"]["attempts"] < 1800
        or funded["actual_qualification_days"] != 0
    ):
        raise ValueError("Actual synthetic funded pressure receipt required")
    final = Path(funded["probe"]["database_paths"]["journal"]).resolve()
    initial = final.parent / "initial-closed-snapshot/journal.sqlite3"
    if (
        not final.parent.name.startswith("a03-funded-")
        or not final.is_relative_to(STATE.resolve())
        or max(initial.stat().st_size, final.stat().st_size) > 10_000_000
        or digest(final) != funded["probe"]["final_database_sha256"]["journal.sqlite3"]
        or digest(initial) != funded["probe"]["initial_closed_snapshot_sha256"]["journal.sqlite3"]
    ):
        raise RuntimeError("Closed original journals exceed scope or source binding differs")
    started = time.monotonic()
    bound = {
        str(Path(__file__).relative_to(ROOT)): digest(Path(__file__)),
        str(receipt.relative_to(ROOT)): digest(receipt),
    }
    originals = {"initial": journal_summary(initial), "final": journal_summary(final)}
    document = {
        "status": "FINITE_SQLITE_LAYOUT_DIAGNOSTIC_ONLY",
        "created_at_utc": datetime.now(UTC).isoformat(),
        "source_hashes": bound,
        "funded_native_runtime_snapshot": funded["native_runtime_snapshot"],
        "funded_test_receipt": funded["test_receipt"],
        "previous_diagnostic": {
            "path": str(ROOT / "reports/A03_FUNDED_SQLITE_LAYOUT_DIAGNOSTIC_20261001_V1.json"),
            "sha256": digest(ROOT / "reports/A03_FUNDED_SQLITE_LAYOUT_DIAGNOSTIC_20261001_V1.json"),
            "correction": (
                "Immutable PRAGMA mode differs from file-header mode; preserve actual WAL header"
            ),
        },
        "original_journals": originals,
        "page_sizes": list(PAGE_SIZES),
        "layouts": [],
        "allocation_limit_bytes": ALLOCATION_LIMIT,
        "resources_before": status(),
        "capacity_accepted": False,
        "production_authorized": False,
        "actual_qualification_days": 0,
        "network_requests": 0,
        "training_fits": 0,
        "limitations": (
            "Closed-copy VACUUM only. No proof of continuous writer growth or 180d capacity."
        ),
    }
    folder.mkdir()
    failure = None
    peak = 0
    try:
        for page_size in PAGE_SIZES:
            subfolder = folder / str(page_size)
            subfolder.mkdir()
            copies = {}
            for name in ("initial", "final"):
                original = Path(originals[name]["path"])
                copies[name] = layout_copy(
                    original,
                    subfolder / f"{name}.sqlite3",
                    page_size,
                    originals[name]["layout"]["journal_mode"],
                )
                if copies[name]["logical"] != originals[name]["logical"]:
                    raise RuntimeError("VACUUM changed a stored field, financial record or schema")
                peak = max(peak, allocated(folder))
            item = {
                "page_size": page_size,
                "copies": copies,
                "closed_increment_bytes": copies["final"]["layout"]["closed_file_bytes"]
                - copies["initial"]["layout"]["closed_file_bytes"],
                "logical_records_schema_and_chain_identical": True,
            }
            document["layouts"].append(item)
            print(
                json.dumps(
                    {
                        "page_size": page_size,
                        "initial_bytes": copies["initial"]["layout"]["closed_file_bytes"],
                        "final_bytes": copies["final"]["layout"]["closed_file_bytes"],
                        "closed_increment_bytes": item["closed_increment_bytes"],
                    }
                ),
                flush=True,
            )
        if any(digest(Path(row["path"])) != row["layout"]["sha256"] for row in originals.values()):
            raise RuntimeError("Original journal changed during readonly diagnostic")
        if bound != {
            str(Path(__file__).relative_to(ROOT)): digest(Path(__file__)),
            str(receipt.relative_to(ROOT)): digest(receipt),
        }:
            raise RuntimeError("Diagnostic source or funded receipt changed")
        document["original_journals_unchanged"] = True
    except Exception as error:
        failure = error
        document.update(
            status="SQLITE_LAYOUT_DIAGNOSTIC_FAILED_NOT_ACCEPTED",
            error_type=type(error).__name__,
            error=str(error),
        )
    document.update(
        elapsed_seconds=time.monotonic() - started,
        resources_after=status(),
        actual_copy_directory_bytes=allocated(folder),
        sampled_peak_copy_bytes=peak,
        originals_or_financial_rows_rewritten=0,
    )
    with output.open("x", encoding="utf-8") as writer:
        writer.write(json.dumps(document, indent=2, allow_nan=False) + "\n")
    print(
        json.dumps(
            {
                "status": document["status"],
                "output": str(output),
                "actual_copy_bytes": document["actual_copy_directory_bytes"],
            }
        )
    )
    if failure is not None:
        raise failure


if __name__ == "__main__":
    main()
