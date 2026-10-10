"""Offline recomputation and deterministic sample-only normalization diagnostics."""

from __future__ import annotations

import argparse
import csv
import importlib.util
import io
import json
import zipfile
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("oi_audit", HERE / "audit.py")
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)


def normalize_diagnostic(raw: bytes, symbol: str, day: str) -> dict:
    """Never create a feature; inspect sort/dedup feasibility and endpoint validity."""
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        body = archive.read(f"{symbol}-metrics-{day}.csv")
    grouped = defaultdict(list)
    raw_grouped = defaultdict(list)
    all_rows = list(csv.DictReader(io.StringIO(body.decode("utf-8-sig"))))
    raw_lines = body.splitlines()
    assert len(raw_lines) == len(all_rows) + 1
    for i, row in enumerate(all_rows):
        grouped[row["create_time"]].append(row)
        raw_grouped[row["create_time"]].append(raw_lines[i + 1])
    conflict = []
    identical = []
    for timestamp, rows in sorted(grouped.items()):
        if len(rows) == 1:
            continue
        if all(row == rows[0] for row in rows[1:]):
            identical.append(timestamp)
        else:
            conflict.append(timestamp)
    # Unique timestamp stock values are diagnostic evidence only. Original ZIP
    # stays immutable, and any future feature contract must declare this rule.
    canonical = [rows[0] for _, rows in sorted(grouped.items())]
    q = audit.quality(raw, symbol, day)
    terminal_time = f"{day} 23:55:00"
    terminal = grouped.get(terminal_time, [])
    terminal_conflict = bool(terminal) and any(r != terminal[0] for r in terminal[1:])
    bad_times = {r["create_time"] for r in q["invalid_oi_rows"]}
    terminal_valid = bool(terminal) and not terminal_conflict and terminal_time not in bad_times
    canonical_complete = (
        not (conflict or q["missing_5m_slots"] or q["offgrid_timestamps"] or q["invalid_oi_rows"])
        and len(grouped) == 288
    )
    return {
        "symbol": symbol,
        "day": day,
        "physical_rows": q["rows"],
        "unique_timestamps": len(grouped),
        "identical_duplicate_timestamp_count": len(identical),
        "identical_duplicate_extra_rows": sum(len(grouped[t]) - 1 for t in identical),
        "duplicate_csv_line_bytes_identical_timestamp_count": sum(
            len(lines) > 1 and all(line == lines[0] for line in lines[1:])
            for lines in raw_grouped.values()
        ),
        "conflicting_duplicate_timestamp_count": len(conflict),
        "conflicting_duplicate_timestamps": conflict,
        "raw_strictly_ordered": q["strictly_increasing"],
        "canonical_first": canonical[0]["create_time"] if canonical else None,
        "canonical_last": canonical[-1]["create_time"] if canonical else None,
        "missing_5m_slots": len(q["missing_5m_slots"]),
        "invalid_oi_rows": len(q["invalid_oi_rows"]),
        "first_invalid_time": q["invalid_oi_rows"][0]["create_time"]
        if q["invalid_oi_rows"]
        else None,
        "last_invalid_time": q["invalid_oi_rows"][-1]["create_time"]
        if q["invalid_oi_rows"]
        else None,
        "canonical_complete_positive_grid": canonical_complete,
        "terminal_2355_exists_and_positive_after_identical_dedup": terminal_valid,
        "terminal_2355_row": terminal[0] if terminal_valid else None,
        "not_a_feature_or_live_asof_certificate": True,
    }


def run(state: Path, out: Path) -> None:
    assert not (out / "VERIFY.json").exists()
    samples = json.loads((state / "oi-feasibility-retry/samples.json").read_text())
    assert samples["status"] == "COMPLETE_BOUNDED_SAMPLE" and len(samples["findings"]) == 45
    normalized = []
    raw_manifest = []
    for row in samples["findings"]:
        path = Path(row["raw_zip_path"])
        raw = path.read_bytes()
        checksum = path.with_name(path.name + ".CHECKSUM").read_bytes()
        digest, filename = checksum.decode().strip().split(maxsplit=1)
        assert audit.sha(raw) == digest == row["zip_sha256"]
        assert filename.lstrip("*") == path.name
        assert audit.sha(checksum) == row["checksum_body_sha256"]
        recomputed = json.loads(json.dumps(audit.quality(raw, row["symbol"], row["day"])))
        assert all(recomputed[key] == row[key] for key in recomputed)
        normalized.append(normalize_diagnostic(raw, row["symbol"], row["day"]))
        raw_manifest.append(
            {
                "symbol": row["symbol"],
                "day": row["day"],
                "ZIP": path.name,
                "ZIP_bytes": len(raw),
                "ZIP_SHA256": digest,
                "CSV_SHA256": row["csv_sha256"],
                "CHECKSUM_bytes": len(checksum),
                "CHECKSUM_SHA256": audit.sha(checksum),
                "official_URL": audit.url(row["symbol"], row["day"]),
            }
        )
    heads = []
    for name in ("oi-feasibility-retry", "oi-feasibility-anchors"):
        path = state / name / "heads_requests.jsonl"
        if path.exists():
            for line in path.read_text().splitlines():
                heads.append(json.loads(line))
    assert len(heads) == 28
    assert all(r["http_status"] in (200, 404) for r in heads)
    start = date(2021, 12, 1)
    dates = {
        "common_first_verified_sample": str(start),
        "first_hypothetical_64_level_day_window_at_UTC_midnight_with_Dplus2_proxy": str(
            start + timedelta(days=65)
        ),
        "first_hypothetical_64_one_day_change_window_at_UTC_midnight_with_Dplus2_proxy": str(
            start + timedelta(days=66)
        ),
        "conditional_on_full_daily_coverage_not_yet_downloaded": True,
    }
    train_dates = []
    with (HERE.parent / "temporal-short-input-diagnosis-20261010/ROWS.csv").open() as handle:
        for row in csv.DictReader(handle):
            if row["role"] == "TRAIN":
                epoch_days = int(row["decision_us"]) // 86_400_000_000
                train_dates.append(str(date(1970, 1, 1) + timedelta(days=epoch_days)))
    # Preserve counts only; no outcome/utility fields consumed for analysis.
    assert train_dates and len(train_dates) == 744
    for key, cutoff in (
        ("64_levels", start + timedelta(days=65)),
        ("64_one_day_changes", start + timedelta(days=66)),
    ):
        dates[f"hypothetical_existing_TRAIN_dates_at_or_after_{key}"] = sum(
            date.fromisoformat(d) >= cutoff for d in train_dates
        )
    dates.update(
        original_mature_TRAIN_dates=len(train_dates),
        original_TRAIN_first=train_dates[0],
        original_TRAIN_last=train_dates[-1],
    )
    receipts = [
        "OI_HEAD_RESOURCE_20261010.json",
        "OI_SAMPLE_RESOURCE_20261010.json",
        "OI_ANCHOR_RESOURCE_20261010.json",
    ]
    resource = {p: json.loads((state / p).read_text()) for p in receipts}
    assert resource["OI_SAMPLE_RESOURCE_20261010.json"]["exit_code"] == 0
    assert resource["OI_ANCHOR_RESOURCE_20261010.json"]["exit_code"] == 0
    out.mkdir(parents=True, exist_ok=True)
    for name, value in (
        ("NORMALIZATION_DIAGNOSTIC.json", normalized),
        ("RAW_ARCHIVE_MANIFEST.json", raw_manifest),
        ("HEAD_RECEIPTS.json", heads),
        ("WINDOW_TRADEOFF.json", dates),
        ("RESOURCE_RECEIPTS.json", resource),
    ):
        (out / name).write_text(json.dumps(value, indent=2) + "\n")
    with zipfile.ZipFile(state / "oi-feasibility-raw45.zip", "w", zipfile.ZIP_STORED) as bundle:
        for row in raw_manifest:
            for suffix in ("", ".CHECKSUM"):
                path = state / "oi-feasibility-retry/raw" / (row["ZIP"] + suffix)
                bundle.write(path, "raw/" + path.name)
        for path in (
            state / "oi-feasibility-retry/samples.json",
            state / "oi-feasibility-retry/samples_requests.jsonl",
            state / "oi-feasibility/heads.json",
            state / "oi-feasibility-retry/heads_requests.jsonl",
            state / "oi-feasibility-anchors/heads.json",
            state / "oi-feasibility-anchors/heads_requests.jsonl",
        ):
            bundle.write(path, "receipts/" + path.parent.name + "/" + path.name)
    bundle = state / "oi-feasibility-raw45.zip"
    result = {
        "status": "PASS_OFFLINE_SAMPLE_RECOMPUTATION",
        "archives_checksum_recomputed": 45,
        "HEAD_receipts": len(heads),
        "archive_sample_body_bytes": samples["downloaded_body_bytes"],
        "raw_complete_positive_288_grids": sum(
            r["complete_positive_unique_288_grid"] for r in samples["findings"]
        ),
        "canonical_complete_positive_288_grids": sum(
            r["canonical_complete_positive_grid"] for r in normalized
        ),
        "positive_terminal_2355_days": sum(
            r["terminal_2355_exists_and_positive_after_identical_dedup"] for r in normalized
        ),
        "physical_unordered_samples": sum(not r["raw_strictly_ordered"] for r in normalized),
        "identical_duplicate_extra_rows": sum(
            r["identical_duplicate_extra_rows"] for r in normalized
        ),
        "conflicting_duplicate_timestamps": sum(
            r["conflicting_duplicate_timestamp_count"] for r in normalized
        ),
        "raw_bundle": {
            "path": str(bundle),
            "bytes": bundle.stat().st_size,
            "SHA256": audit.sha(bundle.read_bytes()),
        },
        "full_history_completeness": "NOT_RUN",
        "historical_asof_certificate": "UNAVAILABLE",
        "training_features_models_thresholds_wallets_changed": False,
    }
    (out / "VERIFY.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))
    print(json.dumps(dates, indent=2))


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--state", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    run(args.state, args.output)
