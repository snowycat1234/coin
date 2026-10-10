"""Conservative masked daily inputs, without price, model or outcome dependencies."""

from __future__ import annotations

import csv
import importlib.util
import io
import math
import zipfile
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
AUDIT_PATH = HERE.parent / "temporal-oi-feasibility-20261010/audit.py"
if not AUDIT_PATH.exists():
    AUDIT_PATH = HERE / "reused_feasibility/audit.py"
SPEC = importlib.util.spec_from_file_location("reused_oi_audit", AUDIT_PATH)
audit = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(audit)


def normalize(raw: bytes, symbol: str, day: str) -> dict:
    # Reuse archive member/schema/safety checks and OI validity exactly. Only the
    # lossless dedup criterion is tightened to byte identity for the adopted input.
    q = audit.quality(raw, symbol, day)
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        body = archive.read(f"{symbol}-metrics-{day}.csv")
    rows = list(csv.DictReader(io.StringIO(body.decode("utf-8-sig"))))
    lines = body.splitlines(keepends=True)
    assert len(lines) == len(rows) + 1, "Multiline CSV records are outside schema"
    grouped = defaultdict(list)
    for index, row in enumerate(rows):
        stamp = datetime.fromisoformat(row["create_time"])
        assert stamp.tzinfo is None
        grouped[stamp.replace(tzinfo=timezone.utc)].append((index, row, lines[index + 1]))
    origin = datetime.fromisoformat(day).replace(tzinfo=timezone.utc)
    expected = [origin + timedelta(minutes=5 * i) for i in range(288)]
    bad_indices = {r["row"] for r in q["invalid_oi_rows"]}
    conflict = {t for t, group in grouped.items() if len({x[2] for x in group}) > 1}
    identical = {t for t, group in grouped.items() if len(group) > 1 and t not in conflict}
    valid = {
        t
        for t, group in grouped.items()
        if t not in conflict and not any(i in bad_indices for i, _, _ in group)
    }
    terminal = expected[-1]
    reasons = []
    if terminal not in grouped:
        reasons.append("MISSING_EXACT_2355_TERMINAL")
    if terminal in conflict:
        reasons.append("CONFLICTING_TIMESTAMP_BYTES")
    if terminal in grouped and any(i in bad_indices for i, _, _ in grouped[terminal]):
        reasons.append("INVALID_TERMINAL_OI_OR_IDENTITY")
    ok = not reasons
    row = grouped[terminal][0][1] if ok else None
    missing = [t.isoformat() for t in expected if t not in grouped]
    invalid_slots = [t.isoformat() for t in expected if t in grouped and t not in valid]
    return dict(
        symbol=symbol,
        source_day=day,
        status="VERIFIED_CURRENT_ARCHIVE",
        zip_sha256=q["zip_sha256"],
        csv_sha256=q["csv_sha256"],
        csv_bytes=q["csv_bytes"],
        physical_rows=q["rows"],
        unique_timestamps=len(grouped),
        raw_strictly_ordered=q["strictly_increasing"],
        chronological_first_label=min(grouped).isoformat() if grouped else None,
        chronological_last_label=max(grouped).isoformat() if grouped else None,
        identical_duplicate_extra_rows=sum(len(grouped[t]) - 1 for t in identical),
        conflicting_timestamp_count=len(conflict),
        conflicting_timestamps=[t.isoformat() for t in sorted(conflict)],
        missing_5m_slots=missing,
        invalid_5m_slots=invalid_slots,
        invalid_oi_physical_rows=len(bad_indices),
        offgrid_timestamps=q["offgrid_timestamps"],
        valid_5m_slots=sum(t in valid for t in expected),
        complete_positive_288_grid=(
            len(valid) == 288 and set(valid) == set(expected) and not conflict and not bad_indices
        ),
        terminal_valid=ok,
        terminal_mask_reasons=reasons,
        terminal_observation_label_UTC=terminal.isoformat(),
        terminal_original_create_time=row["create_time"] if row else None,
        terminal_oi_quantity=row["sum_open_interest"] if row else None,
        terminal_oi_value=row["sum_open_interest_value"] if row else None,
        assumed_available_UTC=(origin + timedelta(days=2)).isoformat(),
        original_publication_UTC=None,
        availability_status="ASSUMED_D_PLUS_2_MIDNIGHT_UTC_NOT_ASOF_CERTIFIED",
        units_status="NATIVE_HISTORICAL_UNITS_UNCERTIFIED",
        vintage_status="CURRENT_VINTAGE_RETROSPECTIVE_DEVELOPMENT",
    )


def missing(symbol: str, day: str, status: str) -> dict:
    origin = datetime.fromisoformat(day).replace(tzinfo=timezone.utc)
    return dict(
        symbol=symbol,
        source_day=day,
        status=status,
        terminal_valid=False,
        terminal_mask_reasons=[status],
        terminal_oi_quantity=None,
        terminal_oi_value=None,
        terminal_observation_label_UTC=(origin + timedelta(hours=23, minutes=55)).isoformat(),
        assumed_available_UTC=(origin + timedelta(days=2)).isoformat(),
        original_publication_UTC=None,
        physical_rows=0,
        unique_timestamps=0,
        valid_5m_slots=0,
        complete_positive_288_grid=False,
        missing_5m_slots=[(origin + timedelta(minutes=5 * i)).isoformat() for i in range(288)],
        invalid_5m_slots=[],
        invalid_oi_physical_rows=0,
        identical_duplicate_extra_rows=0,
        conflicting_timestamp_count=0,
        availability_status="ASSUMED_D_PLUS_2_MIDNIGHT_UTC_NOT_ASOF_CERTIFIED",
        units_status="NATIVE_HISTORICAL_UNITS_UNCERTIFIED",
        vintage_status="CURRENT_VINTAGE_RETROSPECTIVE_DEVELOPMENT",
    )


def consumer_rows(records: list[dict]) -> list[dict]:
    mapping = {(r["symbol"], r["source_day"]): r for r in records}
    assert len(mapping) == len(records)
    result = []
    for record in records:
        day = datetime.fromisoformat(record["source_day"])
        row = dict(
            symbol=record["symbol"],
            source_day=record["source_day"],
            terminal_observation_label_UTC=record["terminal_observation_label_UTC"],
            assumed_available_UTC=record["assumed_available_UTC"],
            original_publication_UTC=None,
            terminal_oi_quantity=record["terminal_oi_quantity"],
            terminal_oi_value=record["terminal_oi_value"],
            oi_terminal_valid=int(record["terminal_valid"]),
            terminal_mask_reason=";".join(record["terminal_mask_reasons"]),
            complete_positive_288_grid=int(record["complete_positive_288_grid"]),
            physical_rows=record["physical_rows"],
            valid_5m_slots=record["valid_5m_slots"],
            missing_5m_slot_count=len(record["missing_5m_slots"]),
            invalid_5m_slot_count=len(record["invalid_5m_slots"]),
            conflicting_timestamp_count=record["conflicting_timestamp_count"],
            identical_duplicate_extra_rows=record["identical_duplicate_extra_rows"],
            archive_status=record["status"],
            availability_status=record["availability_status"],
            units_status=record["units_status"],
            vintage_status=record["vintage_status"],
        )
        for lag in (1, 7):
            interval = [
                mapping.get((record["symbol"], str((day - timedelta(days=i)).date())))
                for i in range(lag + 1)
            ]
            reason = []
            if any(x is None for x in interval):
                reason.append("CALENDAR_INTERVAL_OUTSIDE_INPUT_RANGE_OR_NOT_ACQUIRED")
            if any(x is not None and not x["terminal_valid"] for x in interval):
                reason.append("INVALID_OR_MISSING_TERMINAL_WITHIN_CALENDAR_INTERVAL")
            value = None
            if not reason:
                value = (
                    float(interval[0]["terminal_oi_quantity"])
                    / float(interval[-1]["terminal_oi_quantity"])
                    - 1
                )
                if not math.isfinite(value):
                    value = None
                    reason.append("NONFINITE_RELATIVE_CHANGE")
            row[f"oi_quantity_relchange_{lag}d"] = value
            row[f"oi_quantity_relchange_{lag}d_valid"] = int(not reason)
            row[f"oi_quantity_relchange_{lag}d_mask_reason"] = ";".join(reason)
        result.append(row)
    return result


def write_csv(path: Path, rows: list[dict]) -> None:
    assert rows
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def summary(records: list[dict], consumer: list[dict]) -> dict:
    return dict(
        asset_days=len(records),
        verified=sum(r["status"] == "VERIFIED_CURRENT_ARCHIVE" for r in records),
        missing_archive_404=sum(r["status"] == "MISSING_ARCHIVE_404" for r in records),
        terminal_valid=sum(r["terminal_valid"] for r in records),
        terminal_masked=sum(not r["terminal_valid"] for r in records),
        complete_positive_288_grid=sum(r["complete_positive_288_grid"] for r in records),
        quantity_relchange_1d_valid=sum(r["oi_quantity_relchange_1d_valid"] for r in consumer),
        quantity_relchange_7d_valid=sum(r["oi_quantity_relchange_7d_valid"] for r in consumer),
        physical_rows=sum(r["physical_rows"] for r in records),
        identical_duplicate_extra_rows=sum(r["identical_duplicate_extra_rows"] for r in records),
        conflicting_timestamp_count=sum(r["conflicting_timestamp_count"] for r in records),
        missing_5m_slots=sum(len(r["missing_5m_slots"]) for r in records),
        invalid_5m_slots=sum(len(r["invalid_5m_slots"]) for r in records),
    )
