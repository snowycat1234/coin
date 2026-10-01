"""Read-only A07 v1 data quality/capacity diagnosis; never collects or fits.

Only committed Parquet rows in one native SQLite read snapshot count as evidence.
Run under scripts/bounded.sh; --output creates a new D report, never replaces one.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import sqlite3
import time
from collections import Counter
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

from quant.paths import ROOT, STATE

VERSION = "microstructure_l1_v1"
SYMBOLS = ("BTCUSDT", "ETHUSDT")
INTERVALS = (1, 5, 30, 60)
SECOND = 1_000_000
DAY = 86_400 * SECOND
FUTURE_START = 1_790_812_800_000_000  # 2026-10-01 00:00:00 UTC
FLAGS = {
    "PARTIAL": 1,
    "DISCONNECTED": 2,
    "NO_QUOTE": 4,
    "STALE_QUOTE": 8,
    "AGG_GAP": 16,
    "LATE": 32,
    "CLOCK": 64,
    "RESTART": 128,
    "MISSING": 256,
    "BASELINE_RESET": 512,
    "CARRIED": 1024,
}
INVALID = 1 | 2 | 8 | 16 | 32 | 64 | 128 | 256
FEATURES = (
    "mid",
    "spread_bps",
    "bid_qty_mean",
    "ask_qty_mean",
    "L1_imbalance_mean",
    "L1_imbalance_last",
    "microprice_offset_bps_mean",
    "quote_update_count",
    "bid_price_change_count",
    "ask_price_change_count",
    "OFI_L1",
    "agg_trade_count",
    "aggressive_buy_notional",
    "aggressive_sell_notional",
    "trade_flow_imbalance",
    "trade_vwap",
    "realized_return_1s",
)
META = {
    "symbol",
    "open_us",
    "close_us",
    "available_us",
    "interval_s",
    "received_first_us",
    "received_last_us",
    "event_first_us",
    "event_last_us",
    "trade_first_us",
    "trade_last_us",
    "quality",
    "known_seconds",
    "valid_seconds",
    "mode",
    "session",
    "version",
}
STATES = FEATURES[:5] + ("microprice_offset_bps_mean",)
SUMS = FEATURES[7:14]
AGG_FEATURES = (
    tuple(f"{name}_{stat}" for name in STATES for stat in ("mean", "std", "min", "max", "last"))
    + SUMS
    + ("trade_flow_imbalance", "trade_vwap", "L1_imbalance_last", "realized_return")
)


class QualityRejected(ValueError):
    """Data integrity, resource bound or frozen provenance was not established."""


@dataclass(frozen=True)
class Limits:
    max_files: int = 200_000
    max_file_bytes: int = 64_000_000
    max_rows_per_file: int = 100_000
    max_row_group_bytes: int = 64_000_000
    max_total_rows: int = 100_000_000
    max_days: int = 4096
    max_audit_records: int = 1_000_000
    max_sessions: int = 10_000
    batch_rows: int = 2048
    max_payload_bytes: int = 65_536
    max_snapshot_bytes: int = 32_000_000
    max_snapshot_seconds: int = 5

    def __post_init__(self):
        ceiling = {
            "max_files": 200_000,
            "max_file_bytes": 64_000_000,
            "max_rows_per_file": 100_000,
            "max_row_group_bytes": 64_000_000,
            "max_total_rows": 100_000_000,
            "max_days": 4096,
            "max_audit_records": 1_000_000,
            "max_sessions": 10_000,
            "batch_rows": 2048,
            "max_payload_bytes": 65_536,
            "max_snapshot_bytes": 32_000_000,
            "max_snapshot_seconds": 5,
        }
        if any(
            not isinstance(getattr(self, key), int)
            or isinstance(getattr(self, key), bool)
            or not 0 < getattr(self, key) <= value
            for key, value in ceiling.items()
        ):
            raise ValueError("Audit bounds may only be reduced")


def require(condition: bool, message: str) -> None:
    if not condition:
        raise QualityRejected(message)


def canonical(value) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def fingerprint(value) -> str:
    return hashlib.sha256(canonical(value)).hexdigest()


def parse_json(value: str, limit: int = 65_536):
    require(len(value.encode()) <= limit, "JSON payload exceeds audit memory bound")

    def pairs(items):
        result = {}
        for key, item in items:
            require(key not in result, "Duplicate JSON key")
            result[key] = item
        return result

    def reject(value):
        raise QualityRejected(f"Nonfinite JSON constant: {value}")

    return json.loads(value, object_pairs_hook=pairs, parse_constant=reject)


def read_json(path: Path, limit: int = 65_536):
    require(path.stat().st_size <= limit, "JSON file exceeds audit memory bound")
    with path.open("rb") as stream:
        data = stream.read(limit + 1)
    require(len(data) <= limit, "JSON file grew beyond audit memory bound")
    return parse_json(data.decode(), limit)


def digest(path: Path, limit: int | None = None) -> str:
    value, read = hashlib.sha256(), 0
    with path.open("rb") as stream:
        while block := stream.read(1_048_576):
            read += len(block)
            require(limit is None or read <= limit, "File exceeds audit byte bound")
            value.update(block)
    return value.hexdigest()


def utc(value: int | None) -> str | None:
    return datetime.fromtimestamp(value / SECOND, UTC).isoformat() if value is not None else None


def day_string(day: int) -> str:
    return datetime.fromtimestamp(day * 86400, UTC).date().isoformat()


def longest_run(days: list[int]) -> int:
    best = current = 0
    previous = None
    for day in sorted(days):
        current = current + 1 if previous == day - 1 else 1
        best, previous = max(best, current), day
    return best


@dataclass
class Bucket:
    symbol: str
    interval: int
    rows: int = 0
    bytes_attributed: float = 0.0
    first: int | None = None
    last: int | None = None
    gap_seconds: int = 0
    gap_count: int = 0
    largest_gap_seconds: int = 0
    valid_seconds: int = 0
    known_seconds: int = 0
    complete_feature_rows: int = 0
    quality: Counter = field(default_factory=Counter)
    nulls: Counter = field(default_factory=Counter)
    expected_nulls: Counter = field(default_factory=Counter)
    unexpected_nulls: Counter = field(default_factory=Counter)
    nonfinite: Counter = field(default_factory=Counter)
    days: dict = field(default_factory=dict)
    previous_valid: bool = False

    def add(self, row: dict, now_us: int, sessions: dict, mode: str, limits: Limits):
        opened, closed, quality = row["open_us"], row["close_us"], row["quality"]
        require(row["version"] == VERSION and row["mode"] == mode, "Feature version/mode pollution")
        require(row["session"] in sessions, "Feature session lacks committed source evidence")
        require(
            row["symbol"] == self.symbol and row["interval_s"] == self.interval,
            "Feature interval or symbol changed",
        )
        require(
            all(
                isinstance(row[key], int) and not isinstance(row[key], bool)
                for key in (
                    "open_us",
                    "close_us",
                    "available_us",
                    "quality",
                    "known_seconds",
                    "valid_seconds",
                )
            ),
            "Invalid metadata integers",
        )
        require(
            opened >= 0
            and opened % (self.interval * SECOND) == 0
            and closed == opened + self.interval * SECOND
            and closed <= row["available_us"] <= now_us,
            "Unaligned or future feature row",
        )
        require(quality >= 0 and not quality & ~sum(FLAGS.values()), "Unknown quality flags")
        require(
            0 < row["known_seconds"] <= self.interval
            and 0 <= row["valid_seconds"] <= row["known_seconds"],
            "Invalid known/valid seconds",
        )
        if self.interval == 1:
            require(
                row["valid_seconds"] == int(not quality & INVALID),
                "1s valid_seconds contradicts quality flags",
            )
        else:
            require(
                not (quality & INVALID) or row["valid_seconds"] < self.interval,
                "Aggregate valid_seconds contradicts invalid flag",
            )
        for prefix in ("received", "event", "trade"):
            first, last = row[f"{prefix}_first_us"], row[f"{prefix}_last_us"]
            require((first is None) == (last is None), "Incomplete event/receipt time pair")
            if first is not None:
                require(
                    isinstance(first, int) and isinstance(last, int) and 0 <= first <= last,
                    "Invalid event/receipt timestamps",
                )
                if prefix == "received":
                    require(opened <= first <= last < closed, "Receipt escaped its closed bucket")
        if self.last is not None:
            require(opened > self.last, "Duplicate or regressed feature primary key")
            missing = (opened - self.last) // SECOND - self.interval
            if missing:
                self.gap_count += 1
                self.gap_seconds += missing
                self.largest_gap_seconds = max(self.largest_gap_seconds, missing)
        return_reset = (
            self.last is None
            or not self.previous_valid
            or opened != self.last + self.interval * SECOND
        )
        self.first = opened if self.first is None else self.first
        self.last, self.rows = opened, self.rows + 1
        self.known_seconds += row["known_seconds"]
        self.valid_seconds += row["valid_seconds"]
        for name, flag in FLAGS.items():
            self.quality[name] += bool(quality & flag)
        complete, unexpected, finite = True, False, True
        for name in FEATURES if self.interval == 1 else AGG_FEATURES:
            value = row[name]
            if value is None:
                complete = False
                self.nulls[name] += 1
                expected = expected_null(row, name, return_reset=return_reset)
                (self.expected_nulls if expected else self.unexpected_nulls)[name] += 1
                unexpected |= not expected
            elif (
                not isinstance(value, (int, float))
                or isinstance(value, bool)
                or not math.isfinite(value)
            ):
                finite = False
                self.nonfinite[name] += 1
        self.complete_feature_rows += complete and finite
        self.previous_valid = not quality & INVALID and row["valid_seconds"] == self.interval
        day = opened // DAY
        require(day in self.days or len(self.days) < limits.max_days, "UTC day bound exceeded")
        stats = self.days.setdefault(
            day,
            {
                "rows": 0,
                "known_seconds": 0,
                "valid_seconds": 0,
                "quality_valid_rows": 0,
                "bad_feature_rows": 0,
                "bytes_attributed": 0.0,
            },
        )
        stats["rows"] += 1
        stats["known_seconds"] += row["known_seconds"]
        stats["valid_seconds"] += row["valid_seconds"]
        stats["quality_valid_rows"] += (
            not quality & INVALID
            and finite
            and not unexpected
            and row["known_seconds"] == self.interval
            and row["valid_seconds"] == self.interval
        )
        stats["bad_feature_rows"] += not finite or unexpected

    def report(self) -> dict:
        return {
            "rows": self.rows,
            "first_open_utc": utc(self.first),
            "last_close_utc": utc(
                None if self.last is None else self.last + self.interval * SECOND
            ),
            "calendar_span_seconds_not_health": (
                0 if self.first is None else (self.last - self.first) // SECOND + self.interval
            ),
            "known_seconds": self.known_seconds,
            "quality_valid_seconds": self.valid_seconds,
            "missing_bucket_seconds": self.gap_seconds,
            "gap_count": self.gap_count,
            "largest_gap_seconds": self.largest_gap_seconds,
            "complete_feature_rows": self.complete_feature_rows,
            "quality_flag_rows": dict(self.quality),
            "feature_nulls": dict(self.nulls),
            "expected_nullable": dict(self.expected_nulls),
            "unexpected_missing": dict(self.unexpected_nulls),
            "nonfinite": dict(self.nonfinite),
            "compressed_bytes_attributed": self.bytes_attributed,
            "byte_allocation": "file bytes divided equally by its rows; not separate encoding",
            "utc_days": {day_string(day): value for day, value in sorted(self.days.items())},
        }


class CommonSeconds:
    """Two pending rows, per-day counters and one cursor into uncertain ranges."""

    def __init__(self, uncertain_ranges, limits):
        self.limits = limits
        merged = []
        for start, end in sorted(uncertain_ranges):
            if merged and start <= merged[-1][1]:
                merged[-1] = (merged[-1][0], max(end, merged[-1][1]))
            else:
                merged.append((start, end))
        self.uncertain = merged
        self.cursor = 0
        self.opened = None
        self.pending = {}
        self.days = {}

    def add(self, row):
        opened = row["open_us"]
        require(self.opened is None or opened >= self.opened, "Paired 1s order regressed")
        if self.opened != opened:
            self.flush()
            self.opened = opened
        require(row["symbol"] not in self.pending, "Duplicate paired 1s symbol")
        mid = row["mid"]
        self.pending[row["symbol"]] = (
            not row["quality"] & INVALID
            and row["known_seconds"] == row["valid_seconds"] == 1
            and isinstance(mid, (int, float))
            and not isinstance(mid, bool)
            and math.isfinite(mid)
            and mid > 0
        )

    def flush(self):
        if self.opened is None or not self.pending:
            return
        day = self.opened // DAY
        require(
            day in self.days or len(self.days) < self.limits.max_days, "Paired day bound exceeded"
        )
        stats = self.days.setdefault(day, Counter())
        if len(self.pending) != 2:
            stats["unpaired_seconds"] += 1
        else:
            stats["matched_seconds"] += 1
            while (
                self.cursor < len(self.uncertain) and self.uncertain[self.cursor][1] <= self.opened
            ):
                self.cursor += 1
            uncertain = (
                self.cursor < len(self.uncertain)
                and self.uncertain[self.cursor][0] < self.opened + SECOND
            )
            if uncertain:
                stats["audit_uncertain_seconds"] += 1
            elif all(self.pending.values()):
                stats["usable_seconds"] += 1
            else:
                stats["invalid_or_no_mid_seconds"] += 1
        self.pending.clear()

    def report(self):
        return {
            "basis": "same open_us BTC/ETH 1s pair, positive finite mid, no INVALID, "
            "excluding exact audit uncertainty overlap; no wall-time or summed-symbol credit",
            "pending_row_limit": 2,
            "uncertainty_ranges": len(self.uncertain),
            "totals": dict(sum(self.days.values(), Counter())),
            "utc_days": {day_string(day): dict(stats) for day, stats in sorted(self.days.items())},
        }


def expected_null(row: dict, name: str, *, return_reset=False) -> bool:
    """Legal nulls describe unavailable statistics; never count them as feature-ready."""
    if name in {"trade_flow_imbalance", "trade_vwap"}:
        return row["agg_trade_count"] == 0
    if name in {"realized_return", "realized_return_1s"}:
        # First return after any invalid predecessor is legitimately unavailable;
        # aggregates propagate any null return, without recording its exact subsecond.
        return return_reset or bool(row["quality"] & (INVALID | FLAGS["BASELINE_RESET"]))
    if name.startswith("mid"):
        return bool(row["quality"] & (FLAGS["STALE_QUOTE"] | INVALID))
    if name == "L1_imbalance_last" or name.endswith("_last"):
        return bool(row["quality"] & (FLAGS["NO_QUOTE"] | INVALID))
    return row["quote_update_count"] == 0 and any(name.startswith(base) for base in STATES[1:])


def audit_sql(
    db: sqlite3.Connection,
    binding: dict,
    source_sha: str,
    limits: Limits,
    deadline: float,
    cutoff: int,
) -> dict:
    triggers = dict(db.execute("SELECT name,sql FROM sqlite_master WHERE type='trigger'"))
    for table in ("audit", "manifests"):
        for action in ("update", "delete"):
            sql = triggers.get(f"{table}_no_{action}", "")
            require(
                f"BEFORE {action.upper()} ON {table}" in sql and "RAISE(ABORT" in sql,
                "Append-only trigger missing",
            )
    schema_sha = fingerprint(
        [
            tuple(row)
            for row in db.execute(
                "SELECT type,name,sql FROM sqlite_master WHERE type IN ('table','trigger') "
                "ORDER BY type,name"
            )
        ]
    )
    sessions, kinds, rejected, exports = {}, Counter(), Counter(), {}
    raw_pruned = {"count": 0, "bytes": 0, "oldest_us": None, "latest_us": None}
    uncertain_days, uncertain_ranges, uncertain_kinds, disconnected = set(), [], Counter(), None

    def uncertain(start, end, kind):
        if start is None:
            return
        require(
            isinstance(start, int) and isinstance(end, int) and 0 <= start <= end,
            "Invalid uncertainty range in audit",
        )
        if end > start:
            require(
                len(uncertain_ranges) < limits.max_audit_records, "Uncertainty count bound exceeded"
            )
            uncertain_ranges.append((start, end))
            first, last = start // DAY, (end - 1) // DAY
            require(last - first + 1 <= limits.max_days, "Uncertainty range exceeds UTC-day bound")
            uncertain_days.update(range(first, last + 1))
            require(len(uncertain_days) <= limits.max_days, "Uncertain UTC-day bound exceeded")
        uncertain_kinds[kind] += 1

    samples, previous, expected, received_last, regressions = [], "0" * 64, 1, None, 0
    for row in db.execute("SELECT * FROM audit ORDER BY seq"):
        require(time.monotonic() <= deadline, "Short SQL snapshot time budget exceeded")
        require(expected <= limits.max_audit_records, "Audit record bound exceeded")
        detail = parse_json(row["payload"], limits.max_payload_bytes)
        require(
            row["seq"] == expected
            and row["previous_sha"] == previous
            and row["sha256"]
            == fingerprint([row["seq"], row["received_us"], row["kind"], detail, previous]),
            "Audit SHA chain damaged",
        )
        if received_last is not None and row["received_us"] < received_last:
            regressions += 1
        received_last = row["received_us"]
        kind = row["kind"]
        kinds[kind] += 1
        if kind == "SESSION":
            require(
                len(sessions) < limits.max_sessions and detail["session"] not in sessions,
                "Session bound or duplicate session",
            )
            require(
                detail["mode"] == binding["mode"]
                and detail["version"] == VERSION
                and detail["source_sha256"] == source_sha
                and detail["schema_sha256"] == schema_sha,
                "Session source/version pollution",
            )
            sessions[detail["session"]] = {"started_us": row["received_us"], "normal_stop": False}
        elif kind == "STOP":
            require(detail["session"] in sessions, "STOP lacks SESSION")
            sessions[detail["session"]]["normal_stop"] = True
        elif kind == "FEATURE_EXPORT":
            require(
                len(exports) < limits.max_files and detail["file"] not in exports,
                "Duplicate exported path or file bound",
            )
            exports[detail["file"]] = {key: detail[key] for key in ("sha256", "rows", "bytes")}
        elif kind == "REJECTED":
            rejected[detail.get("reason", "UNKNOWN")] += 1
        elif kind == "RAW_PRUNED":
            raw_pruned["count"] += detail["count"]
            raw_pruned["bytes"] += detail["bytes"]
            for key, reducer in (("oldest_us", min), ("latest_us", max)):
                if detail[key] is not None:
                    raw_pruned[key] = (
                        detail[key]
                        if raw_pruned[key] is None
                        else reducer(raw_pruned[key], detail[key])
                    )
        if kind == "RESTART_GAP":
            uncertain(detail["start_us"], detail["end_us"], kind)
        elif kind == "OBSERVATION_GAP":
            uncertain(detail["from_us"], detail["to_us"], kind)
        elif kind == "AGG_ID_GAP":
            require(
                detail.get("from_received_us") is not None, "Trade ID gap lacks prior receipt bound"
            )
            uncertain(detail["from_received_us"], detail["to_received_us"], kind)
        elif kind == "DISCONNECTED":
            start = detail.get("uncertain_from_us")
            start = row["received_us"] if start is None else start
            disconnected = start if disconnected is None else min(start, disconnected)
        elif kind == "CONNECTED" and disconnected is not None:
            uncertain(disconnected, row["received_us"], "DISCONNECTED_TO_CONNECTED")
            disconnected = None
        if kind in {
            "DISCONNECTED",
            "RESTART_GAP",
            "OBSERVATION_GAP",
            "CLOCK_GAP",
            "REJECTED",
            "AGG_ID_GAP",
        }:
            if len(samples) < 100:
                samples.append(
                    {
                        "seq": row["seq"],
                        "kind": kind,
                        "received_utc": utc(row["received_us"]),
                        "detail": detail,
                    }
                )
        previous, expected = row["sha256"], expected + 1
    if disconnected is not None:
        uncertain(disconnected, cutoff, "UNRESOLVED_DISCONNECT")
    return {
        "head_sha256": previous,
        "records": expected - 1,
        "schema_sha256": schema_sha,
        "triggers_verified": True,
        "sessions": sessions,
        "kind_counts": dict(kinds),
        "rejected_reason_counts": dict(rejected),
        "timestamp_regressions": regressions,
        "incident_samples": samples,
        "incident_samples_limit": 100,
        "raw_pruned": raw_pruned,
        "exports": exports,
        "uncertain_days": uncertain_days,
        "uncertain_ranges": uncertain_ranges,
        "uncertainty_kind_counts": dict(uncertain_kinds),
    }


def scan_file(
    path: Path,
    manifest: sqlite3.Row,
    buckets: dict,
    sessions: dict,
    mode: str,
    now_us: int,
    limits: Limits,
    common: CommonSeconds | None = None,
) -> dict:
    require(path.is_file(), f"Committed immutable feature file missing: {manifest['path']}")
    size = path.stat().st_size
    require(size == manifest["bytes"], "Feature file size differs from immutable manifest")
    require(0 < size <= limits.max_file_bytes, "Feature file byte bound exceeded")
    require(digest(path, limits.max_file_bytes) == manifest["sha256"], "Feature SHA mismatch")
    parquet = pq.ParquetFile(path)
    interval = manifest["interval_s"]
    require(interval in INTERVALS, "Unknown manifest interval")
    schema = parquet.schema_arrow
    names = set(schema.names)
    features = FEATURES if interval == 1 else AGG_FEATURES
    require(
        len(names) == len(schema.names) and names == META | set(features),
        "Frozen Parquet column schema changed",
    )
    for column in schema:
        name = column.name
        if name in {"symbol", "mode", "session", "version"}:
            matches = pa.types.is_string(column.type) or pa.types.is_large_string(column.type)
        else:
            expected = (
                pa.uint16()
                if name in {"quality", "known_seconds", "valid_seconds", "interval_s"}
                else pa.uint32()
                if name.endswith("_count")
                else pa.int64()
                if name.endswith("_us")
                else pa.float64()
                if name
                in {
                    "mid",
                    "trade_vwap",
                    "OFI_L1",
                    "aggressive_buy_notional",
                    "aggressive_sell_notional",
                }
                or name.startswith("mid_")
                else pa.float32()
            )
            matches = column.type == expected
        require(matches, f"Frozen Arrow dtype changed: {name}")
    require(
        parquet.metadata.num_rows == manifest["rows"], "Feature row count differs from manifest"
    )
    require(0 < manifest["rows"] <= limits.max_rows_per_file, "Feature row bound exceeded")
    for group in range(parquet.metadata.num_row_groups):
        require(
            parquet.metadata.row_group(group).total_byte_size <= limits.max_row_group_bytes,
            "Parquet uncompressed row-group bound exceeded",
        )
    first = last = None
    utc_days_in_file = set()
    count = 0
    for batch in parquet.iter_batches(batch_size=limits.batch_rows, use_threads=False):
        for row in batch.to_pylist():
            require(row["symbol"] in SYMBOLS, "Unexpected feature symbol")
            bucket = buckets[row["symbol"], interval]
            bucket.add(row, now_us, sessions, mode, limits)
            utc_days_in_file.add(row["open_us"] // DAY)
            if common is not None and interval == 1:
                common.add(row)
            per_row = size / manifest["rows"]
            bucket.bytes_attributed += per_row
            bucket.days[row["open_us"] // DAY]["bytes_attributed"] += per_row
            first = row["open_us"] if first is None else min(first, row["open_us"])
            last = row["open_us"] if last is None else max(last, row["open_us"])
            count += 1
    require(
        count == manifest["rows"] and first == manifest["first_us"] and last == manifest["last_us"],
        "Manifest time extent/decoded rows differ",
    )
    require(path.stat().st_size == size, "Immutable feature changed during scan")
    columns = sum(
        parquet.metadata.row_group(group).column(column).total_compressed_size
        for group in range(parquet.metadata.num_row_groups)
        for column in range(parquet.metadata.num_columns)
    )
    return {
        "rows": count,
        "encoded_column_bytes": columns,
        "container_overhead_bytes": size - columns,
        "utc_days_in_file": utc_days_in_file,
    }


def coverage(
    buckets: dict, *, future_only=False, uncertain_days=None, common_valid_by_day=None
) -> dict:
    uncertain_days = uncertain_days or set()
    observed, clean = None, None
    for (_, interval), bucket in buckets.items():
        expected = 86400 // interval
        eligible = {
            day
            for day, row in bucket.days.items()
            if (not future_only or day * DAY >= FUTURE_START)
            and row["rows"] == expected
            and row["known_seconds"] == 86400
        }
        valid = {
            day
            for day in eligible
            if bucket.days[day]["quality_valid_rows"] == expected
            and bucket.days[day]["valid_seconds"] == 86400
            and day not in uncertain_days
        }
        observed = eligible if observed is None else observed & eligible
        clean = valid if clean is None else clean & valid
    observed, clean = sorted(observed or []), sorted(clean or [])
    consecutive = longest_run(observed)
    common_valid_by_day = common_valid_by_day or {}
    valid_volume, run_volume, previous_day = 0, 0, None
    for day in observed:
        usable = common_valid_by_day.get(day, 0)
        require(isinstance(usable, int) and 0 <= usable <= 86400, "Invalid paired daily seconds")
        run_volume = run_volume + usable if previous_day == day - 1 else usable
        valid_volume, previous_day = max(valid_volume, run_volume), day
    stage = (
        "QA_ONLY"
        if consecutive < 14 or valid_volume < 14 * 86400
        else "PREDICTIVE_DIAGNOSTICS_ONLY"
        if consecutive < 30 or valid_volume < 30 * 86400
        else "PREREGISTRATION_REVIEW_ONLY"
    )
    return {
        "fully_observed_common_utc_days": [day_string(day) for day in observed],
        "observed_is_exported_buckets_not_healthy_market_time": True,
        "fully_quality_valid_common_utc_days": [day_string(day) for day in clean],
        "observed_complete_day_count": len(observed),
        "quality_valid_day_count": len(clean),
        "longest_consecutive_quality_valid_days": longest_run(clean),
        "longest_consecutive_observed_days": consecutive,
        "paired_usable_seconds_in_best_continuous_observed_period": valid_volume,
        "paired_usable_data_days_in_that_period": valid_volume / 86400,
        "paired_usable_seconds_including_partial_days": sum(
            value
            for day, value in common_valid_by_day.items()
            if not future_only or day * DAY >= FUTURE_START
        ),
        "earliest_verified_day": day_string(observed[0]) if observed else None,
        "latest_verified_day": day_string(observed[-1]) if observed else None,
        "excluded_audit_uncertain_utc_days": [
            day_string(day)
            for day in sorted(uncertain_days)
            if not future_only or day * DAY >= FUTURE_START
        ],
        "actual_24h_capacity_accepted": bool(observed),
        "actual_24h_quality_accepted": bool(clean),
        "evidence_stage": stage,
        "predictive_diagnostics_data_review_eligible": consecutive >= 14
        and valid_volume >= 14 * 86400,
        "preregistered_research_data_review_eligible": consecutive >= 30
        and valid_volume >= 30 * 86400,
        "alpha_eligible": False,
        "training_authorized": False,
        "quality_review_required": True,
        "criterion": "same full exported UTC day for both symbols and all four intervals; "
        "review additionally needs 14/30 actual matched usable 1s data-days in a continuous "
        "observed period; no invented quality percentage, fitting or health credit; "
        "clean days remain separate diagnostics",
    }


def inventory(store: Path, committed: set, limits: Limits) -> dict:
    counts, sizes, uncommitted, seen = Counter(), Counter(), [], set()
    uncommitted_count = 0
    for section in ("features", "raw"):
        count = 0
        for directory, folders, files in os.walk(store / section, followlinks=False):
            require(
                not any((Path(directory) / name).is_symlink() for name in folders),
                "Managed filesystem contains a directory symlink",
            )
            for name in files:
                path = Path(directory) / name
                require(not path.is_symlink(), "Managed filesystem contains a file symlink")
                count += 1
                require(count <= limits.max_files, "Filesystem inventory bound exceeded")
                relative = str(path.relative_to(store))
                try:
                    size = path.stat().st_size
                except FileNotFoundError:
                    counts[
                        "raw_pruned_during_inventory"
                        if section == "raw"
                        else "feature_disappeared_during_inventory"
                    ] += 1
                    continue
                counts[section] += 1
                sizes[section] += size
                if section == "features":
                    seen.add(relative)
                if section == "features" and relative not in committed:
                    uncommitted_count += 1
                    if len(uncommitted) < 100:
                        uncommitted.append(relative)
    require(committed <= seen, "Committed immutable feature vanished during filesystem inventory")
    return {
        "file_counts": dict(counts),
        "bytes": dict(sizes),
        "unmanifested_feature_count": uncommitted_count,
        "unmanifested_feature_samples": uncommitted,
        "unmanifested_policy": "concurrent or uncommitted export; excluded, never evidence",
        "raw_policy": "mutable debug ring, not an immutable feature manifest; "
        "RAW_PRUNED count/range is legitimate retirement, not feature corruption",
        "raw_complete_or_sha_anchored": False,
        "raw_unsealed_tail": "unknown; no gzip closure/receipt completeness certification",
    }


def audit_quality(
    db_path: Path = STATE / "microstructure.sqlite3",
    store: Path = ROOT / "data/microstructure_v1",
    *,
    limits: Limits | None = None,
    expected_source_sha: str | None = None,
    now_us: int | None = None,
) -> dict:
    """No writes to source SQLite/files. Returns FAIL_CLOSED or diagnostic evidence.

    expected_source_sha is a fixture hook only; production resolves the immutable
    A07 engineering receipt and its original microstructure source SHA.
    """
    limits = limits or Limits()
    fixture = expected_source_sha is not None or now_us is not None
    db_path, store = Path(db_path).resolve(), Path(store).resolve()
    require(
        db_path.is_relative_to(STATE.resolve()) and store.is_relative_to(ROOT.resolve()),
        "Source paths must stay on native D-hosted STATE/D ROOT",
    )
    stamp = time.time_ns() // 1000 if now_us is None else now_us
    report = {
        "module": "A07_QUALITY_DIAGNOSIS",
        "read_only": True,
        "created_utc": utc(stamp),
        "database": str(db_path),
        "store": str(store),
        "version": VERSION,
        "status": "FAIL_CLOSED",
        "alpha_eligible": False,
        "training_authorized": False,
        "actual_24h_capacity_accepted": False,
        "actual_24h_quality_accepted": False,
        "evidence_stage": "QA_ONLY",
        "limits": vars(limits),
        "diagnostic_source_sha256": digest(Path(__file__)),
        "scope": "COMMITTED_MICROSTRUCTURE_FEATURES_ONLY",
    }
    db = None
    try:
        require(db_path.exists() and store.exists(), "Microstructure evidence not started")
        if expected_source_sha is None:
            accepted = read_json(ROOT / "reports/A07_MICROSTRUCTURE_ACCEPTANCE.json", 1_000_000)
            expected_source_sha = accepted["source_hashes"]["src/quant/microstructure.py"]
            require(
                expected_source_sha == digest(ROOT / "src/quant/microstructure.py"),
                "Current collector source differs from original accepted version",
            )
        db = sqlite3.connect(db_path.as_uri() + "?mode=ro", uri=True, timeout=10)
        db.row_factory = sqlite3.Row
        snapshot_started = time.monotonic()
        deadline = snapshot_started + limits.max_snapshot_seconds
        db.set_progress_handler(lambda: int(time.monotonic() > deadline), 1000)
        db.execute("PRAGMA query_only=ON")
        db.execute("PRAGMA temp_store=MEMORY")
        db.execute("BEGIN")
        require(db.execute("PRAGMA quick_check").fetchone()[0] == "ok", "SQLite quick_check failed")
        saved = db.execute("SELECT value FROM state WHERE key='binding'").fetchone()
        stamp = time.time_ns() // 1000 if now_us is None else now_us
        report["created_utc"] = utc(stamp)
        require(saved is not None, "Source binding missing")
        binding = parse_json(saved[0])
        require(
            binding["version"] == VERSION
            and binding["mode"] in {"live", "engineering"}
            and binding["store"] == str(store)
            and binding["implementation_sha256"] == expected_source_sha,
            "Frozen source/mode/version/store binding changed",
        )
        marker = read_json(store / ".microstructure-store.json")
        require(
            marker == {"database": str(db_path), "mode": binding["mode"], "version": VERSION},
            "Store/database ownership mismatch",
        )
        audit = audit_sql(db, binding, expected_source_sha, limits, deadline, stamp)
        saved = db.execute("SELECT value FROM state WHERE key='checkpoint'").fetchone()
        checkpoint = parse_json(saved[0]) if saved else {}
        require(
            not checkpoint
            or checkpoint.get("mode") == binding["mode"]
            and checkpoint.get("session") in audit["sessions"],
            "Checkpoint session/mode changed",
        )
        metadata, snapshot_bytes = [], 0
        for manifest in db.execute("SELECT * FROM manifests ORDER BY interval_s,first_us,path"):
            require(time.monotonic() <= deadline, "Short SQL snapshot time budget exceeded")
            require(len(metadata) < limits.max_files, "Manifest count bound exceeded")
            record = dict(manifest)
            snapshot_bytes += len(canonical(record))
            require(
                snapshot_bytes <= limits.max_snapshot_bytes, "Manifest snapshot byte bound exceeded"
            )
            metadata.append(record)
        outbox = {
            str(row[0]): row[1]
            for row in db.execute("SELECT interval_s,COUNT(*) FROM outbox GROUP BY interval_s")
        }
        db.rollback()
        db.close()
        db = None
        snapshot_seconds = time.monotonic() - snapshot_started
        # No SQLite reader remains while scanning immutable feature files: the
        # live writer can reclaim WAL and continue exporting throughout the scan.
        buckets = {
            (symbol, interval): Bucket(symbol, interval)
            for symbol in SYMBOLS
            for interval in INTERVALS
        }
        common = CommonSeconds(audit["uncertain_ranges"], limits)
        manifests, bytes_read, rows_read, ledger = set(), 0, 0, hashlib.sha256()
        column_bytes = container_bytes = 0
        whole_file_daily_upper = Counter()
        for manifest in metadata:
            relative = manifest["path"]
            require(
                relative not in manifests and relative in audit["exports"],
                "Manifest lacks unique committed FEATURE_EXPORT",
            )
            require(
                audit["exports"][relative]
                == {key: manifest[key] for key in ("sha256", "rows", "bytes")},
                "Manifest/export audit mismatch",
            )
            path = (store / relative).resolve()
            require(
                path.is_relative_to(store / "features") and path.suffix == ".parquet",
                "Manifest path escaped immutable feature folder",
            )
            require(
                rows_read + manifest["rows"] <= limits.max_total_rows,
                "Global decoded-row bound exceeded",
            )
            scanned = scan_file(
                path, manifest, buckets, audit["sessions"], binding["mode"], stamp, limits, common
            )
            rows_read += scanned["rows"]
            column_bytes += scanned["encoded_column_bytes"]
            container_bytes += scanned["container_overhead_bytes"]
            for day in scanned["utc_days_in_file"]:
                whole_file_daily_upper[day] += manifest["bytes"]
            bytes_read += manifest["bytes"]
            manifests.add(relative)
            ledger.update(canonical(dict(manifest)))
        common.flush()
        require(manifests == set(audit["exports"]), "Export audit has no committed manifest")
        report["streams"] = {
            f"{symbol}/{interval}s": bucket.report()
            for (symbol, interval), bucket in buckets.items()
        }
        require(
            not any(bucket.nonfinite or bucket.unexpected_nulls for bucket in buckets.values()),
            "Nonfinite or unexpectedly missing feature values",
        )
        report.update(
            {
                "integrity": "PASS",
                "binding": binding,
                "snapshot": {
                    "sqlite_transaction": "read-only BEGIN",
                    "query_only": True,
                    "audit_head_sha256": audit["head_sha256"],
                    "audit_records": audit["records"],
                    "asof_us": stamp,
                    "asof_utc": utc(stamp),
                    "read_transaction_seconds": snapshot_seconds,
                    "read_transaction_released_before_file_scan": True,
                    "manifest_metadata_bytes": snapshot_bytes,
                    "manifest_ledger_sha256": ledger.hexdigest(),
                    "manifest_files": len(manifests),
                    "rows": rows_read,
                    "bytes": bytes_read,
                    "outbox_unexported_rows": outbox,
                    "outbox_policy": "committed but not exported; no time credit",
                },
                "audit": {
                    key: value
                    for key, value in audit.items()
                    if key not in {"exports", "uncertain_days", "uncertain_ranges"}
                },
                "latest_checkpoint_counters": {
                    key: checkpoint.get(key)
                    for key in (
                        "session",
                        "asof_us",
                        "last_received_us",
                        "accepted_events",
                        "duplicate_events",
                        "rejected_events",
                    )
                },
                "counter_limit": "checkpoint counters cover latest session only; "
                "old duplicate counts were not preserved; "
                "unknown is not zero",
                "inventory": inventory(store, manifests, limits),
            }
        )
        common_valid = {day: stats["usable_seconds"] for day, stats in common.days.items()}
        historical = coverage(
            buckets, uncertain_days=audit["uncertain_days"], common_valid_by_day=common_valid
        )
        future = coverage(
            buckets,
            future_only=True,
            uncertain_days=audit["uncertain_days"],
            common_valid_by_day=common_valid,
        )
        if fixture or binding["mode"] != "live" or audit["timestamp_regressions"]:
            for result in (historical, future):
                result.update(
                    actual_24h_capacity_accepted=False,
                    actual_24h_quality_accepted=False,
                    evidence_stage="QA_ONLY",
                    predictive_diagnostics_data_review_eligible=False,
                    preregistered_research_data_review_eligible=False,
                )
        report.update(
            {
                "common_usable_1s_market_data": common.report(),
                "coverage": historical,
                "future_since_2026_10_01_utc": future,
                "engineering_fixture_hook": fixture,
                "actual_24h_capacity_accepted": historical["actual_24h_capacity_accepted"],
                "actual_24h_quality_accepted": historical["actual_24h_quality_accepted"],
                "evidence_stage": future["evidence_stage"],
                "status": "ACTUAL_24H_DATA_DIAGNOSIS_PASS"
                if historical["actual_24h_quality_accepted"]
                else "ACTUAL_24H_CAPACITY_OBSERVED_QUALITY_REVIEW_REQUIRED"
                if historical["actual_24h_capacity_accepted"]
                else "INSUFFICIENT_EVIDENCE",
            }
        )
        daily_bytes = {
            day: sum(
                bucket.days.get(day, {}).get("bytes_attributed", 0.0) for bucket in buckets.values()
            )
            for day in {day for bucket in buckets.values() for day in bucket.days}
        }
        full = historical["fully_observed_common_utc_days"]
        observed_bytes = [value for day, value in daily_bytes.items() if day_string(day) in full]
        covered = min((bucket.known_seconds for bucket in buckets.values()), default=0)
        report["capacity"] = {
            "verified_feature_bytes": bytes_read,
            "complete_utc_day_feature_bytes_attributed_estimate": {
                day_string(day): value
                for day, value in sorted(daily_bytes.items())
                if day_string(day) in full
            },
            "complete_utc_day_peak_feature_bytes_attributed_estimate": (
                max(observed_bytes) if observed_bytes else None
            ),
            "complete_utc_day_feature_bytes_whole_file_upper_bound": {
                day_string(day): value
                for day, value in sorted(whole_file_daily_upper.items())
                if day_string(day) in full
            },
            "complete_utc_day_peak_feature_bytes_whole_file_upper_bound": max(
                (value for day, value in whole_file_daily_upper.items() if day_string(day) in full),
                default=None,
            ),
            "whole_file_upper_bound_basis": "count every immutable file once for each UTC day "
            "with rows in that file, including its other-day rows and all container overhead",
            "feature_cap_bytes": 8_000_000_000,
            "raw_cap_bytes": 4_000_000_000,
            "diagnostic_projected_feature_bytes_per_day": (
                bytes_read * 86400 / covered if covered else None
            ),
            "projection_is_24h_acceptance": False,
            "projection_basis": "short committed rows / minimum known coverage; "
            "startup/compression overhead and outages can bias this estimate; "
            "not a storage guarantee",
            "raw_peak_24h_not_certified": True,
        }
        projected_day = report["capacity"]["diagnostic_projected_feature_bytes_per_day"]
        report["capacity"].update(
            {
                "encoded_column_bytes_including_page_headers": column_bytes,
                "container_and_footer_overhead_bytes": container_bytes,
                "compression": binding["compression"],
                "native_sqlite_wal_shm_bytes_observed": sum(
                    path.stat().st_size
                    for path in (db_path, Path(str(db_path) + "-wal"), Path(str(db_path) + "-shm"))
                    if path.exists()
                ),
                "native_auxiliary_180d_growth_not_certified": True,
                "diagnostic_180d_features_with_30pct_margin": (
                    projected_day * 180 * 1.3 if projected_day is not None else None
                ),
                "safety_margin": 0.30,
                "projection_excludes_mutable_raw_and_native_auxiliary_growth": True,
                "row_time_denominator": "min known seconds across both symbols and four intervals; "
                "no cross-symbol/cross-frequency time summation",
            }
        )
        report["limitations"] = [
            "Partial rolling 24h and process/calendar wall time do not certify a complete UTC day.",
            "Legal nullable quote/trade/return statistics are not complete feature-ready vectors.",
            "SQL snapshot fixes manifests/audit/outbox; later rename/commit files are excluded.",
            "Local hash chains are integrity bindings, not external signatures.",
            "Raw ring is deliberately retired; no expected SHA or exact retired filename ledger.",
            "No fitting, parameter selection, orders, candidate or future-profit qualification.",
        ]
    except (QualityRejected, OSError, ValueError, KeyError, sqlite3.Error) as error:
        message = str(error)
        over_budget = (
            "bound" in message.lower()
            or "budget" in message.lower()
            or isinstance(error, sqlite3.OperationalError)
            and message == "interrupted"
        )
        report.update(
            status="FAIL_CLOSED",
            integrity="NOT_ESTABLISHED",
            reason=message,
            failure_class="DIAGNOSTIC_BUDGET_EXCEEDED"
            if over_budget
            else "DATA_INTEGRITY_NOT_ESTABLISHED",
            quality_verdict="NOT_EVALUATED",
        )
    finally:
        if db is not None:
            db.rollback()
            db.close()
    return report


def save_report(report: dict, path: Path) -> None:
    path = path.resolve()
    require(
        path.is_relative_to(ROOT / "reports") and path.suffix == ".json",
        "New report must remain in D project reports",
    )
    payload = json.dumps(report, indent=2, ensure_ascii=False, allow_nan=False) + "\n"
    require(len(payload.encode()) <= 10_000_000, "Report exceeds bounded output budget")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x") as stream:
        stream.write(payload)


def main():
    from quant.disk import check
    from quant.resources import status

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    resources = status()
    disk = check(reserve=10_000_000 if args.output else 0)
    report = audit_quality()
    report.update(resources=resources, disk=disk)
    if args.output:
        save_report(report, args.output)
    print(
        json.dumps(
            {
                key: report[key]
                for key in (
                    "status",
                    "created_utc",
                    "actual_24h_capacity_accepted",
                    "actual_24h_quality_accepted",
                    "evidence_stage",
                )
            },
            allow_nan=False,
        )
    )
    if report["status"] == "FAIL_CLOSED":
        raise SystemExit(2)


if __name__ == "__main__":
    main()
