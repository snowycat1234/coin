"""A09 L1 v2, copied from frozen A07 v1 with raw-ID and terminal BBO fixes.

Buckets use original receipt time: Spot bookTicker has no exchange event time.
No depth snapshot, credentials, order endpoint, REST reconstruction, or signal.
"""

from __future__ import annotations

import asyncio
import contextlib
import fcntl
import gzip
import hashlib
import io
import json
import math
import os
import shutil
import sqlite3
import time
import uuid
from collections import defaultdict, deque
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import polars as pl
import websockets

from . import disk, resources
from .paths import ROOT, STATE, VHD, utc_now_us

VERSION = "microstructure_l1_v2"
SYMBOLS = ("BTCUSDT", "ETHUSDT")
SECOND = 1_000_000
DAY = 86_400 * SECOND
STREAMS = "/".join(
    f"{symbol.lower()}@{stream}" for symbol in SYMBOLS for stream in ("bookTicker", "aggTrade")
)
ENDPOINT = "wss://data-stream.binance.vision/stream?streams=" + STREAMS
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
    "spread_bps_last",
    "l1_total_depth_last",
)
STATES = FEATURES[:5] + ("microprice_offset_bps_mean",)
SUMS = (
    "quote_update_count",
    "bid_price_change_count",
    "ask_price_change_count",
    "OFI_L1",
    "agg_trade_count",
    "aggressive_buy_notional",
    "aggressive_sell_notional",
)
PARTIAL, DISCONNECTED, NO_QUOTE, STALE_QUOTE = 1, 2, 4, 8
AGG_GAP, LATE, CLOCK, RESTART, MISSING, BASELINE_RESET, CARRIED = (16, 32, 64, 128, 256, 512, 1024)
INVALID = PARTIAL | DISCONNECTED | STALE_QUOTE | AGG_GAP | LATE | CLOCK | RESTART | MISSING


class MicrostructureStopped(RuntimeError):
    pass


def _layout_guard():
    if ROOT.resolve() != Path("/mnt/d/codex/coin") or not STATE.resolve().is_relative_to(
        Path("/home/xflops/coin-state")
    ):
        raise MicrostructureStopped(
            "Resource paths must use fixed D ROOT and native D-hosted STATE"
        )


def _json(value) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def _hash(value) -> str:
    return hashlib.sha256(_json(value).encode()).hexdigest()


def _number(value, *, zero=False) -> float:
    if isinstance(value, bool):
        raise ValueError("Boolean is not a numeric market value")
    result = float(value)
    if not math.isfinite(result) or result < 0 or (not zero and result == 0):
        raise ValueError("Nonfinite or invalid market value")
    return result


def _trade_integer(value, name: str) -> int:
    if type(value) is not int or value < 0:
        raise ValueError(f"AggTrade {name} requires a nonnegative actual integer")
    return value


def ofi_l1(previous: dict, current: dict) -> float:
    """Cont/Kukanov/Stoikov event contribution; quantity units, positive buy pressure."""
    bid, ask = current["bid"], current["ask"]
    old_bid, old_ask = previous["bid"], previous["ask"]
    return (
        (current["bid_qty"] if bid >= old_bid else 0)
        - (previous["bid_qty"] if bid <= old_bid else 0)
        - (current["ask_qty"] if ask <= old_ask else 0)
        + (previous["ask_qty"] if ask >= old_ask else 0)
    )


def aggregate_seconds(rows: list[dict], interval: int) -> dict:
    """Unweighted statistics over known 1s states; no synthetic event weighting."""
    if not rows or interval not in (5, 30, 60):
        raise ValueError("Require known 1s rows and a supported interval")
    first, last = rows[0], rows[-1]
    opened = first["open_us"] // (interval * SECOND) * interval * SECOND
    if any(
        row["symbol"] != first["symbol"]
        or row["open_us"] // (interval * SECOND) * interval * SECOND != opened
        for row in rows
    ):
        raise ValueError("Cannot aggregate different symbols or time windows")
    flags = 0
    for row in rows:
        flags |= row["quality"]
    if len({row["session"] for row in rows}) != 1:
        flags |= RESTART
    if len(rows) != interval or len({r["open_us"] for r in rows}) != interval:
        flags |= MISSING
    result = {
        "symbol": first["symbol"],
        "open_us": opened,
        "close_us": opened + interval * SECOND,
        "available_us": max(opened + interval * SECOND, max(row["available_us"] for row in rows)),
        "interval_s": interval,
        "received_first_us": min(
            r["received_first_us"] for r in rows if r["received_first_us"] is not None
        )
        if any(r["received_first_us"] is not None for r in rows)
        else None,
        "received_last_us": max(
            r["received_last_us"] for r in rows if r["received_last_us"] is not None
        )
        if any(r["received_last_us"] is not None for r in rows)
        else None,
        "event_first_us": min(r["event_first_us"] for r in rows if r["event_first_us"] is not None)
        if any(r["event_first_us"] is not None for r in rows)
        else None,
        "event_last_us": max(r["event_last_us"] for r in rows if r["event_last_us"] is not None)
        if any(r["event_last_us"] is not None for r in rows)
        else None,
        "quality": flags,
        "known_seconds": len(rows),
        "valid_seconds": sum(not bool(r["quality"] & INVALID) for r in rows),
        "mode": first["mode"],
        "session": first["session"],
        "version": VERSION,
    }
    for field, reducer in (("trade_first_us", min), ("trade_last_us", max)):
        values = [r.get(field) for r in rows if r.get(field) is not None]
        result[field] = reducer(values) if values else None
    for field in STATES:
        values = [r[field] for r in rows if r[field] is not None]
        mean = math.fsum(values) / len(values) if values else None
        stats = {
            "mean": mean,
            "std": math.sqrt(math.fsum((v - mean) ** 2 for v in values) / len(values))
            if values
            else None,
            "min": min(values) if values else None,
            "max": max(values) if values else None,
            "last": last[field],
        }
        result.update({f"{field}_{key}": value for key, value in stats.items()})
    for field in SUMS:
        result[field] = math.fsum(r[field] for r in rows)
    buys, sells = result["aggressive_buy_notional"], result["aggressive_sell_notional"]
    result["trade_flow_imbalance"] = (buys - sells) / (buys + sells) if buys + sells else None
    base = math.fsum(
        (r["aggressive_buy_notional"] + r["aggressive_sell_notional"]) / r["trade_vwap"]
        for r in rows
        if r["trade_vwap"] is not None
    )
    result["trade_vwap"] = (buys + sells) / base if base else None
    result["L1_imbalance_last"] = last["L1_imbalance_last"]
    result["spread_bps_last"] = last["spread_bps_last"]
    result["l1_total_depth_last"] = last["l1_total_depth_last"]
    result["realized_return"] = math.fsum(
        r["realized_return_1s"] for r in rows if r["realized_return_1s"] is not None
    )
    if any(r["realized_return_1s"] is None for r in rows):
        result["realized_return"] = None
    return result


def _bucket() -> dict:
    return {
        "quotes": 0,
        "bid_changes": 0,
        "ask_changes": 0,
        "ofi": 0.0,
        "sums": [0.0] * 5,
        "imbalance_last": None,
        "trades": 0,
        "buy": 0.0,
        "sell": 0.0,
        "base": 0.0,
        "flags": 0,
        "first": None,
        "last": None,
        "event_first": None,
        "event_last": None,
        "trade_first": None,
        "trade_last": None,
    }


@dataclass(frozen=True)
class MicrostructureConfig:
    db_path: Path = STATE / "microstructure_v2.sqlite3"
    store: Path = ROOT / "data/microstructure_v2"
    mode: str = "live"
    raw_cap_bytes: int = 4_000_000_000
    raw_retention_us: int = DAY
    feature_cap_bytes: int = 8_000_000_000
    export_seconds: int = 600

    def __post_init__(self):
        if self.mode not in {"live", "engineering"}:
            raise ValueError("Explicit live or engineering provenance required")
        if not 0 < self.raw_cap_bytes <= 4_000_000_000 or not 0 < self.raw_retention_us <= DAY:
            raise ValueError("Raw hard limits cannot be enlarged")
        if not 0 < self.feature_cap_bytes <= 8_000_000_000 or not 1 <= self.export_seconds <= 600:
            raise ValueError("Feature/outbox limits cannot be enlarged")


class RawRing:
    """Compressed debug shards; only this managed raw folder may be pruned."""

    def __init__(self, folder: Path, config: MicrostructureConfig):
        self.folder, self.config = folder, config
        folder.mkdir(parents=True, exist_ok=True)
        self.file = self.handle = None
        self.started = self.uncompressed = 0
        self.closed = deque(
            (path, int(path.name.split("-")[1]), path.stat().st_size)
            for path in sorted(folder.glob("raw-*.jsonl.gz"))
        )
        self.used = sum(item[2] for item in self.closed)
        self.pruned = {"count": 0, "bytes": 0, "oldest_us": None, "latest_us": None}
        self.prune(utc_now_us())

    def close_shard(self):
        if self.handle:
            path = Path(self.file.name)
            self.handle.close()
            self.file.flush()
            os.fsync(self.file.fileno())
            self.file.close()
            size = path.stat().st_size
            self.closed.append((path, self.started, size))
            self.used += size
            self.file = self.handle = None
            self.uncompressed = 0

    def _delete_oldest(self):
        path, stamp, size = self.closed.popleft()
        path.unlink()
        self.used -= size
        self.pruned["count"] += 1
        self.pruned["bytes"] += size
        self.pruned["oldest_us"] = min(stamp, self.pruned["oldest_us"] or stamp)
        self.pruned["latest_us"] = max(stamp, self.pruned["latest_us"] or stamp)

    def take_pruned(self):
        result = self.pruned
        self.pruned = {"count": 0, "bytes": 0, "oldest_us": None, "latest_us": None}
        return result

    @property
    def reserved_bytes(self):
        return self.used + (self.uncompressed + 2048 if self.handle else 0)

    @property
    def physical_bytes(self):
        return self.used + (Path(self.file.name).stat().st_size if self.file else 0)

    def prune(self, now: int):
        if self.handle and self.started < now - self.config.raw_retention_us:
            self.close_shard()
        while self.closed and (
            self.closed[0][1] < now - self.config.raw_retention_us
            or self.reserved_bytes > self.config.raw_cap_bytes
        ):
            self._delete_oldest()
        return self.reserved_bytes

    def append(self, envelope: dict):
        now = envelope["received_us"]
        # Each accepted line is bounded; no single event can overrun the ring allocation.
        encoded = (_json(envelope) + "\n").encode()
        if len(encoded) > 65_536 or len(encoded) + 2048 > self.config.raw_cap_bytes:
            raise MicrostructureStopped("Raw event exceeds bounded debug capacity")
        if self.handle and (now - self.started >= 60 * SECOND or self.uncompressed >= 4_000_000):
            self.close_shard()
        if not self.handle:
            self.started, self.uncompressed = now, 0
            self.file = (self.folder / f"raw-{now}-{uuid.uuid4().hex[:8]}.jsonl.gz").open("xb")
            self.handle = gzip.GzipFile(fileobj=self.file, mode="wb", compresslevel=1)
        # Reserve the uncompressed upper bound before appending. Delete only older raw shards.
        self.prune_for_reserve(now, len(encoded) + 64)
        self.handle.write(encoded)
        self.uncompressed += len(encoded)

    def prune_for_reserve(self, now: int, reserve: int):
        self.prune(now)
        while self.closed and self.reserved_bytes + reserve > self.config.raw_cap_bytes:
            self._delete_oldest()
        if self.reserved_bytes + reserve > self.config.raw_cap_bytes:
            self.close_shard()
            while self.closed and self.used + reserve + 2048 > self.config.raw_cap_bytes:
                self._delete_oldest()
            self.file = (self.folder / f"raw-{now}-{uuid.uuid4().hex[:8]}.jsonl.gz").open("xb")
            self.handle = gzip.GzipFile(fileobj=self.file, mode="wb", compresslevel=1)
            self.started, self.uncompressed = now, 0

    def flush(self, now: int):
        if self.handle:
            self.handle.flush()
            self.file.flush()
            os.fsync(self.file.fileno())
        self.prune(now)


class MicrostructureCollector:
    """One native writer, bounded 1s memory, durable outbox and atomic Parquet exports."""

    def __init__(
        self,
        config: MicrostructureConfig | None = None,
        *,
        initial_disk=None,
        disk_check: Callable | None = None,
    ):
        self.config = config or MicrostructureConfig()
        _layout_guard()
        if os.environ.get("WSL_DISTRO_NAME") != "hpc_linux":
            raise MicrostructureStopped("D-hosted hpc_linux is required")
        if not self.config.db_path.resolve().is_relative_to(STATE.resolve()):
            raise MicrostructureStopped("SQLite must be inside native D-hosted STATE")
        if not self.config.store.resolve().is_relative_to(ROOT.resolve()):
            raise MicrostructureStopped("All market files must stay inside D ROOT")
        if self.config.db_path.resolve() == (STATE / "microstructure.sqlite3").resolve() or (
            self.config.store.resolve() == (ROOT / "data/microstructure_v1").resolve()
        ):
            raise MicrostructureStopped("v1 database/store is frozen; use separate v2 paths")
        if disk_check and self.config.mode != "engineering":
            raise MicrostructureStopped("Injected guards are engineering only")
        self.disk_check = disk_check or disk.check
        self.ledger = initial_disk or self.disk_check(reserve=20_000_000)
        if self.ledger["status"] not in {"OK", "WARNING"}:
            raise MicrostructureStopped("Unsafe initial disk ledger")
        self.config.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.config.store.mkdir(parents=True, exist_ok=True)
        if any((self.config.store / name).is_symlink() for name in ("raw", "features")):
            raise MicrostructureStopped("Managed raw/features folders cannot be symlinks")
        self.lock = self.config.db_path.with_suffix(".lock").open("a+")
        store_identity = hashlib.sha256(str(self.config.store.resolve()).encode()).hexdigest()
        self.store_lock = (STATE / f"microstore-{store_identity}.lock").open("a+")
        try:
            fcntl.flock(self.lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            fcntl.flock(self.store_lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as error:
            self.lock.close()
            self.store_lock.close()
            raise MicrostructureStopped("Another writer holds this microstructure store") from error
        self.db = None
        try:
            ownership = {
                "database": str(self.config.db_path.resolve()),
                "mode": self.config.mode,
                "version": VERSION,
            }
            marker = self.config.store / ".microstructure-store.json"
            if marker.exists():
                if json.loads(marker.read_text()) != ownership:
                    self.lock.close()
                    self.store_lock.close()
                    raise MicrostructureStopped(
                        "Store provenance/schema belongs to another database"
                    )
            # Reject a v1/foreign database read-only before journal/schema/marker
            # mutations. An existing path cannot silently become a fresh v2 store.
            if self.config.db_path.exists():
                expected_binding = {
                    "version": VERSION,
                    "mode": self.config.mode,
                    "store": str(self.config.store.resolve()),
                    "implementation_sha256": hashlib.sha256(
                        Path(__file__).read_bytes()
                    ).hexdigest(),
                    "compression": {
                        "codec": "zstd",
                        "level": 3,
                        "statistics": False,
                        "polars_version": pl.__version__,
                    },
                }
                try:
                    with contextlib.closing(
                        sqlite3.connect(
                            self.config.db_path.resolve().as_uri() + "?mode=ro", uri=True, timeout=1
                        )
                    ) as reader:
                        reader.execute("PRAGMA query_only=ON")
                        row = reader.execute(
                            "SELECT value FROM state WHERE key='binding'"
                        ).fetchone()
                    if row is None or json.loads(row[0]) != expected_binding:
                        raise MicrostructureStopped(
                            "Existing database provenance/schema is not this v2"
                        )
                except (sqlite3.Error, ValueError, KeyError) as error:
                    raise MicrostructureStopped(
                        "Existing database provenance/schema cannot be v2"
                    ) from error
            if not marker.exists():
                with marker.open("x") as file:
                    file.write(_json(ownership))
                    file.flush()
                    os.fsync(file.fileno())
            self.db = sqlite3.connect(self.config.db_path, timeout=10)
            self.db.row_factory = sqlite3.Row
            self.db.execute("PRAGMA journal_mode=WAL")
            self.db.execute("PRAGMA synchronous=FULL")
            self.db.executescript("""
                CREATE TABLE IF NOT EXISTS state(key TEXT PRIMARY KEY,value TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS outbox(seq INTEGER PRIMARY KEY AUTOINCREMENT,
                    interval_s INTEGER NOT NULL,payload TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS manifests(path TEXT PRIMARY KEY,sha256 TEXT NOT NULL,
                    bytes INTEGER NOT NULL,rows INTEGER NOT NULL,interval_s INTEGER NOT NULL,
                    first_us INTEGER NOT NULL,last_us INTEGER NOT NULL);
                CREATE TABLE IF NOT EXISTS audit(seq INTEGER PRIMARY KEY,
                    received_us INTEGER NOT NULL,
                    kind TEXT NOT NULL,payload TEXT NOT NULL,
                    previous_sha TEXT NOT NULL,sha256 TEXT NOT NULL);
                CREATE TRIGGER IF NOT EXISTS audit_no_update BEFORE UPDATE ON audit
                    BEGIN SELECT RAISE(ABORT,'append only'); END;
                CREATE TRIGGER IF NOT EXISTS audit_no_delete BEFORE DELETE ON audit
                    BEGIN SELECT RAISE(ABORT,'append only'); END;
                CREATE TRIGGER IF NOT EXISTS manifests_no_update BEFORE UPDATE ON manifests
                    BEGIN SELECT RAISE(ABORT,'immutable feature manifest'); END;
                CREATE TRIGGER IF NOT EXISTS manifests_no_delete BEFORE DELETE ON manifests
                    BEGIN SELECT RAISE(ABORT,'immutable feature manifest'); END;
            """)
            self.db.commit()
            self.verify_audit()
            self.schema_sha256 = _hash(
                [
                    tuple(row)
                    for row in self.db.execute(
                        "SELECT type,name,sql FROM sqlite_master WHERE type IN ('table','trigger') "
                        "ORDER BY type,name"
                    )
                ]
            )
            binding = {
                "version": VERSION,
                "mode": self.config.mode,
                "store": str(self.config.store.resolve()),
                "implementation_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                "compression": {
                    "codec": "zstd",
                    "level": 3,
                    "statistics": False,
                    "polars_version": pl.__version__,
                },
            }
            saved = self.db.execute("SELECT value FROM state WHERE key='binding'").fetchone()
            if saved and json.loads(saved[0]) != binding:
                self.db.close()
                self.lock.close()
                self.store_lock.close()
                raise MicrostructureStopped(
                    "Store provenance/schema changed; use a separate database"
                )
            with self.db:
                self.db.execute(
                    "INSERT OR IGNORE INTO state VALUES('binding',?)", (_json(binding),)
                )
            old = self.db.execute("SELECT value FROM state WHERE key='checkpoint'").fetchone()
            self.session = uuid.uuid4().hex
            self.seconds = None
            self.buckets = {s: _bucket() for s in SYMBOLS}
            self.previous = {}
            self.last_mid = {}
            self.ids = json.loads(old[0]).get("ids", {}) if old else {}
            for key, high_water in self.ids.items():
                if key.endswith(":trade"):
                    try:
                        for field in (
                            "id",
                            "f",
                            "l",
                            "last_agg_id",
                            "last_raw_trade_id",
                            "agg_id_high_water",
                            "received_us",
                        ):
                            _trade_integer(high_water[field], field)
                    except (KeyError, ValueError, TypeError) as error:
                        raise MicrostructureStopped(
                            "Recovered v2 trade high water is malformed"
                        ) from error
                    if (
                        high_water["f"] > high_water["l"]
                        or high_water["last_agg_id"] != high_water["id"]
                        or high_water["last_raw_trade_id"] != high_water["l"]
                        or high_water["agg_id_high_water"] < high_water["id"]
                    ):
                        raise MicrostructureStopped(
                            "Recovered v2 raw/aggregate high water is inconsistent"
                        )
            self.windows = {f"{s}:{n}": [] for s in SYMBOLS for n in (5, 30, 60)}
            self.connected = False
            self.last_received_us = self.last_export_us = None
            self.accepted = self.duplicates = self.rejected = 0
            self._last_mono, self._last_wall = time.monotonic(), utc_now_us()
            self._started_mono = time.monotonic()
            self._restarted = bool(old)
            self._last_guard = self._last_full = time.monotonic()
            self._db_at_ledger = self._db_bytes()
            self._fatal = None
            self._disk_task = None
            self.raw = RawRing(self.config.store / "raw", self.config)
            self._feature_bytes = self.db.execute(
                "SELECT COALESCE(SUM(bytes),0) FROM manifests"
            ).fetchone()[0]
            self._store_at_ledger = self._store_bytes()
            with self.db:
                self.audit(
                    "SESSION",
                    {
                        "session": self.session,
                        "mode": self.config.mode,
                        "version": VERSION,
                        "source_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                        "endpoint": ENDPOINT,
                        "schema_sha256": self.schema_sha256,
                        "compression": binding["compression"],
                    },
                )
                if old:
                    checkpoint = json.loads(old[0])
                    self.audit(
                        "RESTART_GAP",
                        {
                            "start_us": checkpoint["asof_us"],
                            "end_us": utc_now_us(),
                            "uncommitted_tail_unknown": True,
                        },
                    )
            pruned = self.raw.take_pruned()
            if pruned["count"]:
                with self.db:
                    self.audit("RAW_PRUNED", pruned)
            self.export()
        except BaseException:
            if hasattr(self, "raw"):
                with contextlib.suppress(Exception):
                    self.raw.close_shard()
            if self.db is not None:
                self.db.close()
            self.lock.close()
            self.store_lock.close()
            raise

    def audit(self, kind: str, detail: dict, received_us: int | None = None):
        last = self.db.execute("SELECT seq,sha256 FROM audit ORDER BY seq DESC LIMIT 1").fetchone()
        seq, previous = (last["seq"] + 1, last["sha256"]) if last else (1, "0" * 64)
        stamp = utc_now_us() if received_us is None else received_us
        digest = _hash([seq, stamp, kind, detail, previous])
        self.db.execute(
            "INSERT INTO audit VALUES(?,?,?,?,?,?)",
            (seq, stamp, kind, _json(detail), previous, digest),
        )

    def verify_audit(self):
        sqls = dict(self.db.execute("SELECT name,sql FROM sqlite_master WHERE type='trigger'"))
        for table in ("audit", "manifests"):
            for action in ("update", "delete"):
                sql = sqls.get(f"{table}_no_{action}", "")
                if f"BEFORE {action.upper()} ON {table}" not in sql or "RAISE(ABORT" not in sql:
                    raise MicrostructureStopped("Immutable store triggers missing")
        previous, expected = "0" * 64, 1
        for row in self.db.execute("SELECT * FROM audit ORDER BY seq"):
            if (
                row["seq"] != expected
                or row["previous_sha"] != previous
                or row["sha256"]
                != _hash(
                    [
                        row["seq"],
                        row["received_us"],
                        row["kind"],
                        json.loads(row["payload"]),
                        previous,
                    ]
                )
            ):
                raise MicrostructureStopped("Microstructure audit chain damaged")
            previous, expected = row["sha256"], expected + 1
        return previous

    def _db_bytes(self):
        return sum(
            p.stat().st_size
            for p in (self.config.db_path, Path(str(self.config.db_path) + "-wal"))
            if p.exists()
        )

    def _store_bytes(self):
        # No recursive DrvFs inventory in the quote hot path, even after 180 days.
        return self._feature_bytes + self.raw.reserved_bytes

    def guard(self):
        if self._fatal:
            raise MicrostructureStopped(self._fatal)
        if time.monotonic() - self._last_guard < 10:
            return
        self._last_guard = time.monotonic()
        try:
            if self.config.mode == "engineering":
                if self.disk_check(reserve=20_000_000)["status"] not in {"OK", "WARNING"}:
                    raise MicrostructureStopped("Engineering guard rejected growth")
            elif "total_bytes" in self.ledger:
                local_growth = max(0, self._db_bytes() - self._db_at_ledger)
                files_growth = max(0, self._store_bytes() - self._store_at_ledger)
                overall_growth = max(
                    local_growth, VHD.stat().st_size - self.ledger["wsl_vhd_bytes"]
                )
                disk.enforce(
                    self.ledger["total_bytes"] + overall_growth + files_growth,
                    20_000_000,
                    shutil.disk_usage(ROOT).free,
                )
        except Exception as error:
            self._fatal = f"DISK: {type(error).__name__}"
            self.connected = False
            raise MicrostructureStopped(self._fatal) from error

    def set_connected(
        self, connected: bool, *, received_us: int | None = None, reason: str = "connection"
    ):
        stamp = received_us if received_us is not None else utc_now_us()
        if not self._fatal:
            self.advance(stamp)
        self.connected = connected
        self.previous.clear()
        self.last_mid.clear()
        for bucket in self.buckets.values():
            bucket["flags"] |= PARTIAL | BASELINE_RESET | (0 if connected else DISCONNECTED)
        with self.db:
            self.audit(
                "CONNECTED" if connected else "DISCONNECTED",
                {
                    "session": self.session,
                    "reason": reason,
                    "uncertain_from_us": self.last_received_us if not connected else None,
                    "detected_us": stamp,
                },
                stamp,
            )

    def ingest(self, message: dict, received_us: int | None = None) -> bool:
        if self.config.mode == "live" and received_us is not None:
            raise MicrostructureStopped("Live receipt timestamps cannot be supplied by callers")
        self.guard()
        received = utc_now_us() if received_us is None else received_us
        data = message.get("data", message)
        self.raw.append(
            {
                "received_us": received,
                "session": self.session,
                "mode": self.config.mode,
                "message": message,
            }
        )
        self.advance(received)
        symbol = data.get("s")
        if symbol not in SYMBOLS:
            raise ValueError("Symbol outside microstructure contract")
        bucket = self.buckets[symbol]
        kind = "trade" if data.get("e") == "aggTrade" else "quote"
        identity = data["a"] if kind == "trade" else data["u"]
        if not isinstance(identity, int) or isinstance(identity, bool) or identity < 0:
            raise ValueError("Invalid stream identity")
        key = f"{symbol}:{kind}"
        digest = _hash(data)
        old = self.ids.get(key)
        if kind == "trade":
            for field in ("f", "l", "E", "T"):
                _trade_integer(data[field], field)
            if data["f"] > data["l"] or data["E"] < data["T"]:
                raise ValueError("Malformed original trade times/ids")
            if not isinstance(data["m"], bool):
                raise ValueError("Aggressor side requires actual m boolean")
            # Validate values even on a replay; malformed raw IDs cannot pass as
            # a duplicate, and rejected overlap must not mutate volume state.
            price, quantity = _number(data["p"]), _number(data["q"])
        if old and (kind == "quote" and identity <= old["id"] or identity == old["id"]):
            if identity == old["id"] and digest != old["hash"]:
                self.reject("IDENTITY_CONFLICT", symbol, received)
                self._fatal = "IDENTITY_CONFLICT"
                raise MicrostructureStopped("Same stream identity has changed content")
            self.duplicates += 1
            if kind == "trade":
                with self.db:
                    self.audit(
                        "AGG_TRADE_DUPLICATE",
                        {
                            "symbol": symbol,
                            "a": identity,
                            "f": data["f"],
                            "l": data["l"],
                            "last_a": old["id"],
                            "last_f": old["f"],
                            "last_l": old["l"],
                            "exact_same_last_aggregate": True,
                        },
                        received,
                    )
            if identity < old["id"]:
                bucket["flags"] |= LATE
                with self.db:
                    self.audit(
                        "OUT_OF_ORDER",
                        {"symbol": symbol, "kind": kind, "id": identity, "last": old["id"]},
                        received,
                    )
            return False
        if kind == "trade" and old and data["f"] <= old["l"]:
            if data["f"] == old["f"] and data["l"] == old["l"]:
                audit_kind = "RAW_TRADE_DUPLICATE"
            elif data["l"] >= old["f"]:
                audit_kind = "RAW_TRADE_OVERLAP"
            else:
                audit_kind = "RAW_TRADE_OUT_OF_ORDER"
            self.duplicates += 1
            if audit_kind != "RAW_TRADE_DUPLICATE":
                bucket["flags"] |= LATE
            with self.db:
                self.audit(
                    audit_kind,
                    {
                        "symbol": symbol,
                        "a": identity,
                        "f": data["f"],
                        "l": data["l"],
                        "last_a": old["id"],
                        "last_f": old["f"],
                        "last_l": old["l"],
                        "last_raw_trade_id": old["l"],
                        "high_water_not_changed": True,
                        "whole_aggregate_rejected": True,
                        "unseen_overlap_tail_quantity_unknown": data["l"] > old["l"],
                    },
                    received,
                )
            return False
        if kind == "quote":
            quote = {
                "bid": _number(data["b"]),
                "ask": _number(data["a"]),
                "bid_qty": _number(data["B"], zero=True),
                "ask_qty": _number(data["A"], zero=True),
                "received_us": received,
            }
            if quote["bid"] > quote["ask"] or quote["bid_qty"] + quote["ask_qty"] <= 0:
                raise ValueError("Crossed or empty L1 quote")
            previous = self.previous.get(symbol)
            if previous:
                bucket["ofi"] += ofi_l1(previous, quote)
                bucket["bid_changes"] += quote["bid"] != previous["bid"]
                bucket["ask_changes"] += quote["ask"] != previous["ask"]
            else:
                bucket["flags"] |= BASELINE_RESET
            mid = (quote["bid"] + quote["ask"]) / 2
            total = quote["bid_qty"] + quote["ask_qty"]
            imbalance = (quote["bid_qty"] - quote["ask_qty"]) / total
            microprice = (quote["ask"] * quote["bid_qty"] + quote["bid"] * quote["ask_qty"]) / total
            values = [
                (quote["ask"] - quote["bid"]) / mid * 10000,
                quote["bid_qty"],
                quote["ask_qty"],
                imbalance,
                (microprice / mid - 1) * 10000,
            ]
            bucket["sums"] = [a + b for a, b in zip(bucket["sums"], values, strict=True)]
            bucket["imbalance_last"] = imbalance
            bucket["quotes"] += 1
            self.previous[symbol] = quote
        else:
            event = data["E"] * 1000
            if event > received + SECOND or received - event > 5 * SECOND:
                bucket["flags"] |= LATE
            if old and data["f"] > old["l"] + 1:
                bucket["flags"] |= AGG_GAP
                with self.db:
                    self.audit(
                        "RAW_TRADE_ID_GAP",
                        {
                            "symbol": symbol,
                            "last_a": old["id"],
                            "a": identity,
                            "last_raw_trade_id": old["l"],
                            "f": data["f"],
                            "l": data["l"],
                            "missing_from_raw_id": old["l"] + 1,
                            "missing_to_raw_id": data["f"] - 1,
                            "from_received_us": old.get("received_us"),
                            "to_received_us": received,
                        },
                        received,
                    )
            elif old and identity != old["id"] + 1:
                with self.db:
                    self.audit(
                        "AGG_ID_JUMP_UNCONFIRMED",
                        {
                            "symbol": symbol,
                            "last_a": old["id"],
                            "a": identity,
                            "last_raw_trade_id": old["l"],
                            "f": data["f"],
                            "l": data["l"],
                            "raw_ids_contiguous": True,
                            "bucket_invalidated": False,
                        },
                        received,
                    )
            bucket["trades"] += 1
            bucket["base"] += quantity
            # m=True: buyer is maker, hence the taker/aggressor sells.
            bucket["sell" if data["m"] else "buy"] += price * quantity
            bucket["event_first"] = min(event, bucket["event_first"] or event)
            bucket["event_last"] = max(event, bucket["event_last"] or event)
            traded = data["T"] * 1000
            bucket["trade_first"] = min(traded, bucket["trade_first"] or traded)
            bucket["trade_last"] = max(traded, bucket["trade_last"] or traded)
        self.ids[key] = {"id": identity, "hash": digest, "received_us": received}
        if kind == "trade":
            self.ids[key].update(
                f=data["f"],
                l=data["l"],
                last_agg_id=identity,
                last_raw_trade_id=data["l"],
                agg_id_high_water=max(identity, old["agg_id_high_water"] if old else identity),
            )
        bucket["first"] = bucket["first"] or received
        bucket["last"] = received
        self.last_received_us = received
        self.accepted += 1
        return True

    def reject(self, reason: str, symbol: str | None, received: int):
        self.rejected += 1
        for bucket in self.buckets.values():
            bucket["flags"] |= LATE
        self.previous.clear()
        with self.db:
            self.audit("REJECTED", {"reason": reason, "symbol": symbol}, received)

    def _seal(self, symbol: str, available_us: int) -> dict:
        bucket, previous = self.buckets[symbol], self.previous.get(symbol)
        flags = bucket["flags"] | (0 if self.connected else DISCONNECTED)
        quote_count = bucket["quotes"]
        if not quote_count:
            flags |= NO_QUOTE
        fresh = (
            previous and 0 <= (self.seconds + 1) * SECOND - previous["received_us"] <= 2 * SECOND
        )
        mid = (previous["bid"] + previous["ask"]) / 2 if fresh else None
        depth_last = previous["bid_qty"] + previous["ask_qty"] if fresh else None
        spread_last = (previous["ask"] - previous["bid"]) / mid * 10000 if fresh else None
        imbalance_last = (previous["bid_qty"] - previous["ask_qty"]) / depth_last if fresh else None
        if not fresh:
            flags |= STALE_QUOTE
        if fresh and not quote_count:
            flags |= CARRIED
        last = self.last_mid.get(symbol)
        log_return = math.log(mid / last) if mid and last and not flags & INVALID else None
        self.last_mid[symbol] = mid if not flags & INVALID else None
        means = [v / quote_count if quote_count else None for v in bucket["sums"]]
        buys, sells = bucket["buy"], bucket["sell"]
        values = (
            mid,
            *means[:4],
            imbalance_last,
            means[4],
            quote_count,
            bucket["bid_changes"],
            bucket["ask_changes"],
            bucket["ofi"],
            bucket["trades"],
            buys,
            sells,
            (buys - sells) / (buys + sells) if buys + sells else None,
            (buys + sells) / bucket["base"] if bucket["base"] else None,
            log_return,
            spread_last,
            depth_last,
        )
        return {
            "symbol": symbol,
            "open_us": self.seconds * SECOND,
            "close_us": (self.seconds + 1) * SECOND,
            "available_us": max((self.seconds + 1) * SECOND, available_us),
            "interval_s": 1,
            "received_first_us": bucket["first"],
            "received_last_us": bucket["last"],
            "event_first_us": bucket["event_first"],
            "event_last_us": bucket["event_last"],
            "trade_first_us": bucket["trade_first"],
            "trade_last_us": bucket["trade_last"],
            "quality": flags,
            "known_seconds": 1,
            "valid_seconds": int(not flags & INVALID),
            "mode": self.config.mode,
            "session": self.session,
            "version": VERSION,
            **dict(zip(FEATURES, values, strict=True)),
        }

    def advance(self, now_us: int):
        target = now_us // SECOND
        if self.seconds is None:
            self.seconds = target
            for bucket in self.buckets.values():
                bucket["flags"] |= PARTIAL | (RESTART if self._restarted else 0)
            return
        if target < self.seconds:
            self.reject("RECEIPT_CLOCK_BACKWARD", None, now_us)
            self._fatal = "RECEIPT_CLOCK_BACKWARD"
            raise MicrostructureStopped("Receipt clock moved behind sealed data")
        if target == self.seconds:
            return
        if target - self.seconds > 120:
            with self.db:
                self.audit(
                    "OBSERVATION_GAP",
                    {"from_us": self.seconds * SECOND, "to_us": target * SECOND},
                    now_us,
                )
            self.seconds = target
            self.previous.clear()
            self.last_mid.clear()
            self.buckets = {s: _bucket() for s in SYMBOLS}
            self.windows = {key: [] for key in self.windows}
            for bucket in self.buckets.values():
                bucket["flags"] |= MISSING | CLOCK | PARTIAL
            return
        with self.db:
            while self.seconds < target:
                for symbol in SYMBOLS:
                    row = self._seal(symbol, now_us)
                    self.db.execute(
                        "INSERT INTO outbox(interval_s,payload) VALUES(1,?)", (_json(row),)
                    )
                    for interval in (5, 30, 60):
                        key = f"{symbol}:{interval}"
                        window = self.windows[key]
                        if window and window[0]["open_us"] // (interval * SECOND) != row[
                            "open_us"
                        ] // (interval * SECOND):
                            aggregated = aggregate_seconds(window, interval)
                            aggregated["available_us"] = max(aggregated["available_us"], now_us)
                            self.db.execute(
                                "INSERT INTO outbox(interval_s,payload) VALUES(?,?)",
                                (interval, _json(aggregated)),
                            )
                            window.clear()
                        window.append(row)
                        if (self.seconds + 1) % interval == 0:
                            aggregated = aggregate_seconds(window, interval)
                            aggregated["available_us"] = max(aggregated["available_us"], now_us)
                            self.db.execute(
                                "INSERT INTO outbox(interval_s,payload) VALUES(?,?)",
                                (interval, _json(aggregated)),
                            )
                            window.clear()
                    self.buckets[symbol] = _bucket()
                self.seconds += 1
            checkpoint = {
                "asof_us": now_us,
                "ids": self.ids,
                "session": self.session,
                "mode": self.config.mode,
                "connected": self.connected,
                "accepted_events": self.accepted,
                "duplicate_events": self.duplicates,
                "rejected_events": self.rejected,
                "last_received_us": self.last_received_us,
                "observed_monotonic_seconds": max(0, time.monotonic() - self._started_mono),
            }
            self.db.execute(
                "INSERT OR REPLACE INTO state VALUES('checkpoint',?)", (_json(checkpoint),)
            )
        self.raw.flush(now_us)
        pruned = self.raw.take_pruned()
        if pruned["count"]:
            with self.db:
                self.audit("RAW_PRUNED", pruned)
        if self.last_export_us is None:
            self.last_export_us = now_us
        elif now_us - self.last_export_us >= self.config.export_seconds * SECOND:
            self.export()
            self.last_export_us = now_us

    def export(self):
        self.guard()
        rows = self.db.execute("SELECT * FROM outbox ORDER BY seq").fetchall()
        if not rows:
            return
        groups = defaultdict(list)
        for row in rows:
            groups[row["interval_s"]].append(row)
        used = self.db.execute("SELECT COALESCE(SUM(bytes),0) FROM manifests").fetchone()[0]
        for interval, batch in groups.items():
            target = (
                self.config.store
                / "features"
                / f"{interval}s"
                / (f"batch-{batch[0]['seq']:013d}-{batch[-1]['seq']:013d}.parquet")
            )
            target.parent.mkdir(parents=True, exist_ok=True)
            temporary = target.with_suffix(".partial")
            data = [json.loads(row["payload"]) for row in batch]
            frame = compact_frame(data)
            buffer = io.BytesIO()
            frame.write_parquet(buffer, compression="zstd", compression_level=3, statistics=False)
            encoded = buffer.getvalue()
            size = len(encoded)
            if used + size >= self.config.feature_cap_bytes:
                self._fatal = "FEATURE_CAP: existing features are never deleted"
                self.connected = False
                with self.db:
                    self.audit(
                        "FEATURE_CAP_STOP",
                        {
                            "existing_bytes": used,
                            "next_bytes": size,
                            "limit": self.config.feature_cap_bytes,
                        },
                    )
                raise MicrostructureStopped(self._fatal)
            digest = hashlib.sha256(encoded).hexdigest()
            with temporary.open("wb") as file:
                file.write(encoded)
                file.flush()
                os.fsync(file.fileno())
            if target.exists():
                if hashlib.sha256(target.read_bytes()).hexdigest() != digest:
                    temporary.unlink()
                    raise MicrostructureStopped("Uncommitted Parquet filename conflicts")
                temporary.unlink()
            else:
                temporary.replace(target)
            with self.db:
                self.db.execute(
                    "INSERT INTO manifests VALUES(?,?,?,?,?,?,?)",
                    (
                        str(target.relative_to(self.config.store)),
                        digest,
                        size,
                        len(data),
                        interval,
                        min(r["open_us"] for r in data),
                        max(r["open_us"] for r in data),
                    ),
                )
                self.db.executemany(
                    "DELETE FROM outbox WHERE seq=?", ((row["seq"],) for row in batch)
                )
                self.audit(
                    "FEATURE_EXPORT",
                    {
                        "file": str(target.relative_to(self.config.store)),
                        "sha256": digest,
                        "rows": len(data),
                        "bytes": size,
                    },
                )
            used += size
            self._feature_bytes = used

    async def refresh_disk(self):
        try:
            ledger = await asyncio.to_thread(self.disk_check, reserve=20_000_000)
        except Exception as error:
            self._fatal = "DISK_LEDGER_FAILED"
            raise MicrostructureStopped(self._fatal) from error
        if ledger["status"] not in {"OK", "WARNING"}:
            self._fatal = "DISK_LEDGER_FAILED"
            raise MicrostructureStopped(self._fatal)
        self.ledger = ledger
        self._store_at_ledger, self._db_at_ledger = self._store_bytes(), self._db_bytes()
        self._last_full = time.monotonic()

    def status(self):
        files = self.db.execute(
            "SELECT COALESCE(SUM(bytes),0),COALESCE(SUM(rows),0) FROM manifests"
        ).fetchone()
        return {
            "module": "A07",
            "version": VERSION,
            "mode": self.config.mode,
            "session": self.session,
            "state": "STOP" if self._fatal else ("CONNECTED" if self.connected else "DISCONNECTED"),
            "accepted_events": self.accepted,
            "schema_sha256": self.schema_sha256,
            "duplicate_events": self.duplicates,
            "rejected_events": self.rejected,
            "last_received_us": self.last_received_us,
            "feature_bytes": files[0],
            "feature_rows": files[1],
            "raw_bytes": self.raw.physical_bytes,
            "pending_rows": self.db.execute("SELECT COUNT(*) FROM outbox").fetchone()[0],
            "alpha_eligible": False,
            "real_time_days_certified": 0,
            "fatal": self._fatal,
            "network": "public_read_only",
            "credentials_used": False,
        }

    async def run(
        self, run_seconds: float | None = None, *, stop_event: asyncio.Event | None = None
    ):
        if self.config.mode != "live":
            raise MicrostructureStopped("Engineering mode cannot request real market data")
        if run_seconds is not None and (not math.isfinite(run_seconds) or run_seconds < 0):
            raise ValueError("Duration must be finite and nonnegative")
        stop = stop_event or asyncio.Event()
        started, delay = time.monotonic(), 1
        while not stop.is_set() and (
            run_seconds is None or time.monotonic() - started < run_seconds
        ):
            try:
                async with websockets.connect(
                    ENDPOINT,
                    max_queue=16,
                    max_size=65_536,
                    ping_interval=20,
                    ping_timeout=20,
                    close_timeout=5,
                ) as socket:
                    self.set_connected(True)
                    connected_at, last_packet = time.monotonic(), time.monotonic()
                    delay = 1
                    while not stop.is_set():
                        if run_seconds is not None and time.monotonic() - started >= run_seconds:
                            break
                        if time.monotonic() - connected_at >= 23 * 3600 + 50 * 60:
                            break
                        now, mono = utc_now_us(), time.monotonic()
                        if abs((now - self._last_wall) / SECOND - (mono - self._last_mono)) > 1:
                            with self.db:
                                self.audit(
                                    "CLOCK_INCIDENT",
                                    {"wall_us": now, "previous_us": self._last_wall},
                                )
                            self._fatal = "CLOCK_INCIDENT"
                            self.set_connected(False, reason="CLOCK_INCIDENT")
                            raise MicrostructureStopped("Receipt clock incident requires restart")
                        self._last_wall, self._last_mono = now, mono
                        if self._disk_task and self._disk_task.done():
                            self._disk_task.result()
                            self._disk_task = None
                        if mono - self._last_full >= 900 and self._disk_task is None:
                            self._disk_task = asyncio.create_task(self.refresh_disk())
                        try:
                            encoded = await asyncio.wait_for(socket.recv(), timeout=1)
                            last_packet = time.monotonic()
                            try:
                                message = json.loads(encoded)
                                if message.get("data", message).get("e") == "serverShutdown":
                                    with self.db:
                                        self.audit("SERVER_SHUTDOWN", {"session": self.session})
                                    break
                                self.ingest(message)
                            except (KeyError, ValueError, TypeError) as error:
                                self.reject(type(error).__name__, None, utc_now_us())
                        except TimeoutError:
                            self.advance(utc_now_us())
                            if time.monotonic() - last_packet > 10:
                                raise TimeoutError("All subscribed streams stalled") from None
            except MicrostructureStopped:
                if self._disk_task:
                    await asyncio.gather(self._disk_task, return_exceptions=True)
                    self._disk_task = None
                raise
            except Exception as error:
                with self.db:
                    self.audit(
                        "NETWORK_ERROR", {"type": type(error).__name__, "detail": str(error)[:512]}
                    )
            finally:
                self.set_connected(False, reason="rotation_or_disconnect")
                if not self._fatal:
                    self.advance(utc_now_us())
            if not stop.is_set():
                remaining = run_seconds - (time.monotonic() - started) if run_seconds else delay
                try:
                    await asyncio.wait_for(stop.wait(), timeout=max(0, min(delay, remaining)))
                except TimeoutError:
                    pass
                delay = min(30, delay * 2)
        if self._disk_task:
            await self._disk_task
            self._disk_task = None
        self.export()
        return self.status()

    def close(self):
        try:
            if not self._fatal:
                self.export()
            self.raw.close_shard()
            with self.db:
                self.audit(
                    "STOP",
                    {
                        "session": self.session,
                        "fatal": self._fatal,
                        "observed_monotonic_seconds": max(0, time.monotonic() - self._started_mono),
                        "unsealed_second_us": self.seconds * SECOND
                        if self.seconds is not None
                        else None,
                        "unsealed_event_counts": {
                            symbol: bucket["quotes"] + bucket["trades"]
                            for symbol, bucket in self.buckets.items()
                        },
                        "partial_aggregate_windows": {
                            key: len(rows) for key, rows in self.windows.items() if rows
                        },
                        "unsealed_or_partial_windows_are_not_complete": True,
                    },
                )
            self.db.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        finally:
            self.db.close()
            self.lock.close()
            self.store_lock.close()


def compact_frame(rows: list[dict]) -> pl.DataFrame:
    frame = pl.DataFrame(rows, infer_schema_length=None)
    exact_columns = {
        "mid",
        "trade_vwap",
        "OFI_L1",
        "aggressive_buy_notional",
        "aggressive_sell_notional",
        "spread_bps_last",
        "l1_total_depth_last",
        "L1_imbalance_last",
    }
    casts = []
    for name in frame.columns:
        if name in {"quality", "known_seconds", "valid_seconds", "interval_s"}:
            casts.append(pl.col(name).cast(pl.UInt16))
        elif name.endswith("_count"):
            casts.append(pl.col(name).cast(pl.UInt32))
        elif name.endswith("_us"):
            casts.append(pl.col(name).cast(pl.Int64))
        elif name in {"symbol", "mode", "session", "version"}:
            casts.append(pl.col(name).cast(pl.String))
        else:
            dtype = pl.Float64 if name in exact_columns or name.startswith("mid_") else pl.Float32
            casts.append(pl.col(name).cast(dtype))
    return frame.with_columns(casts)


async def collect_microstructure(
    config: MicrostructureConfig | None = None, run_seconds: float | None = None, *, stop_event=None
) -> dict:
    resources.status()
    config = config or MicrostructureConfig()
    if config.mode != "live":
        raise MicrostructureStopped("Live entry requires genuine provenance")
    ledger = await asyncio.to_thread(disk.check, reserve=20_000_000)
    writer = MicrostructureCollector(config, initial_disk=ledger)
    try:
        return await writer.run(run_seconds, stop_event=stop_event)
    finally:
        writer.close()


def read_microstructure_status(db_path: Path = STATE / "microstructure_v2.sqlite3") -> dict:
    """One read-only SQLite snapshot; no writer, websocket, keys or resource allocation."""
    _layout_guard()
    path = Path(db_path).resolve()
    if not path.is_relative_to(STATE.resolve()):
        raise MicrostructureStopped("Status requires native D-hosted STATE")
    if not path.exists():
        return {"state": "NOT_STARTED", "alpha_eligible": False, "read_only": True}
    db = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    db.row_factory = sqlite3.Row
    try:
        db.execute("BEGIN")
        reader = object.__new__(MicrostructureCollector)
        reader.db = db
        head = reader.verify_audit()
        binding = json.loads(
            db.execute("SELECT value FROM state WHERE key='binding'").fetchone()[0]
        )
        if (
            binding["version"] != VERSION
            or binding["implementation_sha256"]
            != hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
        ):
            raise MicrostructureStopped("Read status requires the separate frozen v2 binding")
        row = db.execute("SELECT value FROM state WHERE key='checkpoint'").fetchone()
        checkpoint = json.loads(row[0]) if row else {}
        last = db.execute("SELECT kind,payload FROM audit ORDER BY seq DESC LIMIT 1").fetchone()
        fresh = 0 <= utc_now_us() - checkpoint.get("asof_us", 0) <= 5 * SECOND
        state = (
            "STOPPED"
            if last and last[0] == "STOP"
            else ("CONNECTED" if fresh and checkpoint.get("connected") else "STALE_OR_DISCONNECTED")
        )
        sizes = db.execute(
            "SELECT COALESCE(SUM(bytes),0),COALESCE(SUM(rows),0) FROM manifests"
        ).fetchone()
        return {
            "module": "A07",
            "state": state,
            "binding": binding,
            "checkpoint": checkpoint,
            "feature_bytes": sizes[0],
            "feature_rows": sizes[1],
            "audit_head": head,
            "last_audit": {"kind": last[0], "payload": json.loads(last[1])} if last else None,
            "read_only": True,
            "alpha_eligible": False,
            "real_time_days_certified": 0,
        }
    finally:
        db.close()


if __name__ == "__main__":
    import argparse
    import signal

    parser = argparse.ArgumentParser(description="A07 public L1/aggTrade collector; no keys/orders")
    parser.add_argument("--run", action="store_true", help="Explicitly start public collection")
    parser.add_argument("--seconds", type=float, default=None)
    parser.add_argument("--db", type=Path, default=STATE / "microstructure_v2.sqlite3")
    parser.add_argument("--store", type=Path, default=ROOT / "data/microstructure_v2")
    arguments = parser.parse_args()
    if arguments.run:

        async def entry():
            stop = asyncio.Event()
            loop = asyncio.get_running_loop()
            for signum in (signal.SIGTERM, signal.SIGINT):
                loop.add_signal_handler(signum, stop.set)
            return await collect_microstructure(
                MicrostructureConfig(db_path=arguments.db, store=arguments.store),
                run_seconds=arguments.seconds,
                stop_event=stop,
            )

        print(json.dumps(asyncio.run(entry()), indent=2))
    else:
        print(json.dumps(read_microstructure_status(arguments.db), indent=2))
