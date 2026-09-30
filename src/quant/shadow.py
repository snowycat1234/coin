"""Append-only B0/B2 paper accounts driven by genuinely received public data.

This module has no exchange order API. Historical repairs can neither generate
paper fills nor qualify as forward evidence. Engineering tests carry synthetic
provenance in their frozen version and every start record.
"""

from __future__ import annotations

import contextlib
import fcntl
import hashlib
import json
import math
import os
import shutil
import sqlite3
import time
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np

from . import disk
from .paths import ROOT, STATE, VHD

SYMBOLS = ("BTCUSDT", "ETHUSDT")
MINUTE_MS = 60_000
HOUR_MS = 3_600_000
DAY_MS = 86_400_000
RESERVE_BYTES = 100_000_000
ZERO_HASH = "0" * 64
IMPLEMENTATION_HASH = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
IMMUTABLE_TRIGGERS = {
    "records_no_update": "BEFORE UPDATE ON records",
    "records_no_delete": "BEFORE DELETE ON records",
}


def _json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def _date(timestamp_ms: int) -> str:
    return datetime.fromtimestamp(timestamp_ms / 1000, UTC).date().isoformat()


@dataclass(frozen=True)
class ShadowConfig:
    version: str = "paper_baselines_v1"
    mode: str = "live_paper"
    initial_cash: float = 10_000.0
    fee_bps: float = 10.0
    half_spread_floor_bps: float = 1.0
    extra_slippage_bps: float = 4.0
    single_asset_max: float = 0.30
    gross_max: float = 0.60
    annual_vol_target: float = 0.10
    participation_rate: float = 0.001
    min_notional: float = 10.0
    max_quote_age_ms: int = 5_000
    order_lifetime_ms: int = 5 * MINUTE_MS
    signal_max_lag_ms: int = 15_000
    require_72h: bool = True

    def __post_init__(self) -> None:
        if self.mode not in {"live_paper", "engineering_simulation"}:
            raise ValueError("unsupported paper-account provenance")
        if not self.version or not math.isfinite(self.initial_cash) or self.initial_cash <= 0:
            raise ValueError("version and finite positive initial cash are required")
        if self.fee_bps < 10 or self.half_spread_floor_bps < 1 or self.extra_slippage_bps < 4:
            raise ValueError("forward costs may only increase the frozen cost contract")
        if self.fee_bps >= 10_000 or self.half_spread_floor_bps + self.extra_slippage_bps >= 10_000:
            raise ValueError("individual cost rates must be below 100%")
        if not (
            0 < self.single_asset_max <= 0.3
            and 0 < self.gross_max <= 0.6
            and 0 < self.annual_vol_target <= 0.1
            and 0 < self.participation_rate <= 0.001
        ):
            raise ValueError("risk or capacity limits exceed the frozen spot contract")
        if self.min_notional < 10 or not self.require_72h:
            raise ValueError("minimum notional and collector qualification cannot be relaxed")
        if not (
            0 < self.max_quote_age_ms <= 5_000
            and MINUTE_MS < self.order_lifetime_ms <= 5 * MINUTE_MS
            and 0 < self.signal_max_lag_ms <= 15_000
        ):
            raise ValueError("invalid quote freshness, signal lag or order lifetime")
        if any(not math.isfinite(v) for v in asdict(self).values() if isinstance(v, float)):
            raise ValueError("configuration must be finite")


@dataclass(frozen=True)
class Quote:
    symbol: str
    bid: float
    ask: float
    received_ms: int
    update_id: int
    source: str = "websocket"

    def __post_init__(self) -> None:
        if self.symbol not in SYMBOLS or self.source != "websocket":
            raise ValueError("quotes must be genuinely received supported WS quotes")
        if (
            not math.isfinite(self.bid)
            or not math.isfinite(self.ask)
            or not 0 < self.bid <= self.ask
        ):
            raise ValueError("invalid bid/ask")
        if self.received_ms < 0 or self.update_id < 0:
            raise ValueError("invalid quote provenance")


def quotes_from_buffers(buffers: dict[str, dict]) -> list[Quote]:
    """Adapt Collector.quote_buffers, never REST or persisted historical aggregates."""
    return [
        Quote(
            s,
            float(b["last_bid"]),
            float(b["last_ask"]),
            int(b["last_received"]),
            int(b["last_id"]),
        )
        for s, b in buffers.items()
        if s in SYMBOLS and b.get("samples", 0) > 0
    ]


def _record_hash(record: dict) -> str:
    return hashlib.sha256(
        _json({k: v for k, v in record.items() if k != "hash"}).encode()
    ).hexdigest()


def read_forward_evidence(
    db_path: str | Path, version: str | None = None, *, include_records: bool = True
) -> dict:
    """Stream-verify the whole journal; optionally materialize it for offline reporting.

    ``version`` identifies a requested version without filtering the chain: records
    always cover the whole chain for independent re-verification. Recovery passes
    include_records=False, with O(1) journal-record memory. This is no external signature.
    """
    db = sqlite3.connect(f"file:{Path(db_path)}?mode=ro", uri=True)
    db.row_factory = sqlite3.Row
    try:
        triggers = {
            r["name"]: r["sql"]
            for r in db.execute(
                "SELECT name,sql FROM sqlite_master WHERE type='trigger'",
            )
        }
        verified = all(
            name in triggers and clause in triggers[name] and "RAISE(ABORT" in triggers[name]
            for name, clause in IMMUTABLE_TRIGGERS.items()
        )
        if not verified:
            raise RuntimeError("paper journal lacks required immutable triggers")
        records = []
        versions = set()
        start = None
        count = 0
        previous = ZERO_HASH
        for expected, row in enumerate(db.execute("SELECT * FROM records ORDER BY seq"), start=1):
            record = {
                key: row[key]
                for key in (
                    "seq",
                    "received_us",
                    "version",
                    "kind",
                    "prev_hash",
                    "hash",
                )
            }
            record["payload"] = json.loads(row["payload"])
            if record["seq"] != expected or record["prev_hash"] != previous:
                raise RuntimeError("broken paper journal sequence / previous hash")
            if record["hash"] != _record_hash(record):
                raise RuntimeError("paper journal hash mismatch")
            previous = record["hash"]
            versions.add(record["version"])
            count = expected
            if (
                start is None
                and record["kind"] == "start"
                and (version is None or record["version"] == version)
            ):
                start = record
            if include_records:
                records.append(record)
        if version is not None and version not in versions:
            raise ValueError("requested version is absent from the journal")
        return {
            "version": version or (start["version"] if start else None),
            "versions": sorted(versions),
            "records": records,
            "triggers_verified": True,
            "head_hash": previous,
            "seq": count,
            "mode": start["payload"]["mode"] if start else None,
            "provenance": start["payload"]["source"] if start else None,
            "scope": "local_append_only_audit_not_external_signature",
        }
    finally:
        db.close()


class ShadowEngine:
    """One locked writer for B0 cash and B2 reference, sharing a frozen version."""

    def __init__(
        self,
        collector_db: str | Path | None = None,
        db_path: str | Path | None = None,
        *,
        config: ShadowConfig | None = None,
        started_ms: int | None = None,
        initial_health: dict | None = None,
        disk_check=disk.check,
        initial_disk: dict | None = None,
    ) -> None:
        self.config = config or ShadowConfig()
        self.path = Path(db_path or STATE / "shadow.sqlite3").resolve()
        self.collector_path = Path(collector_db or STATE / "live.sqlite3").resolve()
        if str(self.path).startswith("/mnt/c/"):
            raise ValueError("C: storage is forbidden")
        if self.config.mode == "live_paper":
            if os.environ.get("WSL_DISTRO_NAME") != "hpc_linux":
                raise RuntimeError("live paper accounts require D-hosted hpc_linux WSL")
            if not self.path.is_relative_to(STATE.resolve()):
                raise ValueError("live paper SQLite must use native D-hosted STATE")
        elif not self.path.is_relative_to(STATE.resolve()) and not str(self.path).startswith(
            "/mnt/d/"
        ):
            raise ValueError("engineering database must use D-hosted storage")
        frozen = {
            "configuration": asdict(self.config),
            "implementation_sha256": IMPLEMENTATION_HASH,
        }
        self.version = (
            self.config.version
            + ":"
            + hashlib.sha256(
                _json(frozen).encode(),
            ).hexdigest()[:16]
        )
        self.disk_check = disk_check
        self.ledger = initial_disk or disk_check(reserve=RESERVE_BYTES)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.lock = self.path.with_suffix(".lock").open("a+")
        try:
            fcntl.flock(self.lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            self.lock.close()
            raise RuntimeError("another shadow writer holds the account lock") from None
        self.db = sqlite3.connect(self.path, timeout=10)
        self.db.row_factory = sqlite3.Row
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.execute("PRAGMA synchronous=FULL")
        self.db.execute("PRAGMA wal_autocheckpoint=256")
        self.db.execute("PRAGMA journal_size_limit=4194304")
        self.db.executescript("""
            CREATE TABLE IF NOT EXISTS records (
                seq INTEGER PRIMARY KEY, received_us INTEGER NOT NULL,
                version TEXT NOT NULL, kind TEXT NOT NULL, payload TEXT NOT NULL,
                prev_hash TEXT NOT NULL, hash TEXT NOT NULL, event_key TEXT UNIQUE NOT NULL
            );
            CREATE INDEX IF NOT EXISTS records_kind_time ON records(kind,received_us);
            CREATE TRIGGER IF NOT EXISTS records_no_update BEFORE UPDATE ON records
                BEGIN SELECT RAISE(ABORT,'immutable paper journal'); END;
            CREATE TRIGGER IF NOT EXISTS records_no_delete BEFORE DELETE ON records
                BEGIN SELECT RAISE(ABORT,'immutable paper journal'); END;
            CREATE VIEW IF NOT EXISTS decisions AS SELECT * FROM records WHERE kind='decision';
            CREATE VIEW IF NOT EXISTS orders AS SELECT * FROM records WHERE kind='order';
            CREATE VIEW IF NOT EXISTS fills AS SELECT * FROM records WHERE kind='fill';
            CREATE VIEW IF NOT EXISTS positions AS SELECT * FROM records WHERE kind='position';
            CREATE VIEW IF NOT EXISTS daily_nav AS SELECT * FROM records WHERE kind='nav';
        """)
        self.db.commit()
        self.source = sqlite3.connect(f"file:{self.collector_path}?mode=ro", uri=True, timeout=10)
        self.source.row_factory = sqlite3.Row
        self.head = ZERO_HASH
        self.seq = 0
        existing = self.db.execute("SELECT 1 FROM records LIMIT 1").fetchone()
        current = int(time.time() * 1000) if started_ms is None else started_ms
        if existing:
            audit = read_forward_evidence(self.path, include_records=False)
            if set(audit["versions"]) != {self.version}:
                self.close()
                raise RuntimeError("existing account has a different frozen configuration/version")
            self.head, self.seq = audit["head_hash"], audit["seq"]
            checkpoint = self.db.execute(
                "SELECT payload FROM records WHERE kind='checkpoint' ORDER BY seq DESC LIMIT 1",
            ).fetchone()
            self.state = json.loads(checkpoint[0])
            heartbeat = self.db.execute(
                "SELECT payload,received_us FROM records WHERE kind='heartbeat' "
                "ORDER BY seq DESC LIMIT 1",
            ).fetchone()
            if heartbeat and heartbeat["received_us"] // 1000 > self.state["last_tick_ms"]:
                self.state["last_tick_ms"] = heartbeat["received_us"] // 1000
                h = json.loads(heartbeat["payload"])
                self.state["observed_seconds"] = h["observed_seconds"]
                self.state["healthy_seconds"] = h["healthy_seconds"]
            self.state["last_healthy"] = False  # restarting never credits an unobserved interval
        else:
            self.state = {
                "started_ms": current,
                "last_tick_ms": current,
                "last_healthy": False,
                "last_checkpoint_ms": current,
                "last_heartbeat_ms": current,
                "observed_seconds": 0.0,
                "healthy_seconds": 0.0,
                "last_day": current // DAY_MS - 1,
                "last_signal_hour": None,
                "strategy_state": "WAITING_FOR_QUALIFIED_LIVE_HOUR",
                "freeze_reasons": [],
                "capacity_used": {},
                "consumed_quotes": {},
                "trend": {
                    s: {"last_hour": None, "fast": None, "slow": None, "count": 0} for s in SYMBOLS
                },
                "accounts": {
                    name: {
                        "cash": self.config.initial_cash,
                        "positions": dict.fromkeys(SYMBOLS, 0.0),
                        "pending": {},
                        "cycles": {
                            s: {"entry_ms": 0, "cost": 0.0, "proceeds": 0.0, "fees": 0.0}
                            for s in SYMBOLS
                        },
                    }
                    for name in ("B0", "B2")
                },
            }
            with self.db:
                for name in ("B0", "B2"):
                    self._append(
                        current,
                        "start",
                        {
                            "account": name,
                            "scenario": name,
                            "role": "cash" if name == "B0" else "baseline",
                            "mode": self.config.mode,
                            "source": "live" if self.config.mode == "live_paper" else "synthetic",
                            "initial_cash": self.config.initial_cash,
                            "qualified_72h_at_start": bool(
                                (initial_health or {}).get("qualified_72h")
                            ),
                            "configuration": asdict(self.config),
                            "implementation_sha256": IMPLEMENTATION_HASH,
                        },
                        f"start:{name}",
                    )
                self._checkpoint(current)
        self._budget_db = self._database_bytes()
        self._budget_vhd = self.ledger.get("wsl_vhd_bytes", 0)
        self._heartbeat_credit = 0.0
        self._restarted = bool(existing)
        self._last_monotonic = time.monotonic()

    def close(self) -> None:
        with contextlib.suppress(Exception):
            self.source.close()
        with contextlib.suppress(Exception):
            self.db.execute("PRAGMA wal_checkpoint(TRUNCATE)")
            self.db.close()
        with contextlib.suppress(Exception):
            self.lock.close()

    def _append(self, now: int, kind: str, payload: dict, key: str) -> None:
        if self.db.execute("SELECT 1 FROM records WHERE event_key=?", (key,)).fetchone():
            return
        record = {
            "seq": self.seq + 1,
            "received_us": now * 1000,
            "version": self.version,
            "kind": kind,
            "payload": payload,
            "prev_hash": self.head,
        }
        record["hash"] = _record_hash(record)
        self.db.execute(
            "INSERT INTO records VALUES(?,?,?,?,?,?,?,?)",
            (
                record["seq"],
                record["received_us"],
                self.version,
                kind,
                _json(payload),
                self.head,
                record["hash"],
                key,
            ),
        )
        self.seq, self.head = record["seq"], record["hash"]

    def _checkpoint(self, now: int) -> None:
        self.state["last_checkpoint_ms"] = now
        self._append(now, "checkpoint", self.state, f"checkpoint:{now}:{self.seq + 1}")

    def _cancel_pending(self, now: int, reason: str) -> bool:
        pending = self.state["accounts"]["B2"]["pending"]
        for symbol, order in pending.items():
            self._append(
                now,
                "order_event",
                {
                    "order_id": order["order_id"],
                    "account": "B2",
                    "symbol": symbol,
                    "status": "CANCELLED_HEALTH",
                    "reason": reason,
                },
                f"health_cancel:{order['order_id']}:{now}",
            )
        changed = bool(pending)
        pending.clear()
        return changed

    def _database_bytes(self) -> int:
        return sum(
            p.stat().st_size
            for p in (
                self.path,
                Path(str(self.path) + "-wal"),
                Path(str(self.path) + "-shm"),
            )
            if p.exists()
        )

    def refresh_disk_budget(self, ledger: dict) -> None:
        """Caller supplies a fresh full ledger with a 100 MB shadow reservation."""
        if ledger.get("reserved_bytes", 0) < RESERVE_BYTES:
            raise ValueError("disk ledger must reserve the shadow 100 MB writer budget")
        self.ledger = ledger
        self._budget_db = self._database_bytes()
        self._budget_vhd = ledger.get("wsl_vhd_bytes", 0)

    def _guard(self) -> None:
        growth = max(0, self._database_bytes() - self._budget_db)
        if "total_bytes" in self.ledger:
            growth = max(growth, VHD.stat().st_size - self._budget_vhd)
            disk.enforce(
                self.ledger["total_bytes"] + growth, RESERVE_BYTES, shutil.disk_usage(ROOT).free
            )
        if growth >= RESERVE_BYTES:
            raise RuntimeError("shadow 100 MB writer budget exhausted; refresh full disk ledger")

    def _reasons(self, now: int, health: dict, quotes: dict[str, Quote]) -> list[str]:
        reasons = []
        if health.get("state") != "RUNNING" or health.get("healthy") is not True:
            reasons.append("collector_unhealthy")
        if health.get("qualified_72h") is not True:
            reasons.append("collector_72h_unqualified")
        if not isinstance(health.get("heartbeat_ms"), int) or not (
            0 <= now - health["heartbeat_ms"] <= 45_000
        ):
            reasons.append("collector_heartbeat_stale")
        offset = health.get("clock_offset_ms")
        if offset is None or not math.isfinite(offset) or abs(offset) > 5_000:
            reasons.append("clock_unhealthy")
        if health.get("unresolved_gaps") != 0:
            reasons.append("unresolved_gap")
        if health.get("disk", {}).get("status") not in {"OK", "WARNING"}:
            reasons.append("disk_unhealthy")
        for symbol in SYMBOLS:
            quote = quotes.get(symbol)
            if quote is None or not 0 <= now - quote.received_ms <= self.config.max_quote_age_ms:
                reasons.append(f"{symbol}:quote_stale")
            elif (quote.ask - quote.bid) / (quote.ask + quote.bid) + (
                self.config.extra_slippage_bps / 10_000
            ) >= 1:
                reasons.append(f"{symbol}:quote_cost_invalid")
            row = self.source.execute(
                "SELECT MAX(received_ms) FROM closed_bars WHERE symbol=? "
                "AND source='websocket' AND received_ms<=?",
                (symbol, now),
            ).fetchone()
            if row[0] is None or now - row[0] > 90_000:
                reasons.append(f"{symbol}:closed_bar_stale")
        return reasons

    def _hour_weights(self, end: int, now: int) -> tuple[dict[str, float], bool, dict]:
        raw = {}
        evidence = {}
        complete = True
        for symbol in SYMBOLS:
            trend = self.state["trend"][symbol]
            begin = 0 if trend["last_hour"] is None else trend["last_hour"] + HOUR_MS
            rows = self.source.execute(
                "SELECT open_ms,close,received_ms,source FROM closed_bars "
                "WHERE symbol=? AND open_ms>=? AND open_ms<? AND received_ms<=? "
                "ORDER BY open_ms",
                (symbol, begin, end, now),
            ).fetchall()
            hours: dict[int, list] = {}
            for row in rows:
                hours.setdefault(row["open_ms"] // HOUR_MS * HOUR_MS, []).append(row)
            current_complete = trend["last_hour"] == end - HOUR_MS and trend.get(
                "last_valid", False
            )
            if current_complete:
                evidence[symbol] = trend["last_evidence"]
            for hour, group in sorted(hours.items()):
                valid = len(group) == 60 and all(
                    r["open_ms"] == hour + i * MINUTE_MS and r["source"] == "websocket"
                    for i, r in enumerate(group)
                )
                if hour == end - HOUR_MS and not valid:
                    continue  # allow the genuinely received last minute to arrive on a later tick
                if not valid or (
                    trend["last_hour"] is not None and hour != trend["last_hour"] + HOUR_MS
                ):
                    trend.update(fast=None, slow=None, count=0)
                trend["last_hour"] = hour
                trend["last_valid"] = valid
                if not valid:
                    continue
                price = float(group[-1]["close"])
                trend["fast"] = (
                    price
                    if trend["fast"] is None
                    else (trend["fast"] + (price - trend["fast"]) * 2 / 21)
                )
                trend["slow"] = (
                    price
                    if trend["slow"] is None
                    else (trend["slow"] + (price - trend["slow"]) * 2 / 101)
                )
                trend["count"] += 1
                if hour == end - HOUR_MS:
                    current_complete = True
                    evidence[symbol] = {
                        "hour_open_ms": hour,
                        "minutes": 60,
                        "last_received_ms": max(r["received_ms"] for r in group),
                        "source_hash": hashlib.sha256(
                            _json([dict(r) for r in group]).encode()
                        ).hexdigest(),
                        "ema_count": trend["count"],
                    }
                    trend["last_evidence"] = evidence[symbol]
            complete &= current_complete
            raw[symbol] = (
                self.config.single_asset_max
                if (current_complete and trend["count"] >= 100 and trend["fast"] > trend["slow"])
                else 0.0
            )
        return raw, complete, evidence

    def _risk_weights(self, raw: dict, now: int) -> tuple[dict[str, float], str]:
        day = now // DAY_MS
        rows = self.source.execute(
            """
            WITH days AS (
                SELECT symbol,open_ms/? AS day,COUNT(*) n,MAX(open_ms) last_open
                FROM closed_bars WHERE open_ms>=? AND open_ms<? AND received_ms<=?
                AND source='websocket' GROUP BY symbol,day
            ) SELECT d.symbol,d.day,d.n,b.close FROM days d JOIN closed_bars b
            ON b.symbol=d.symbol AND b.open_ms=d.last_open WHERE d.n=1440
        """,
            (DAY_MS, (day - 31) * DAY_MS, day * DAY_MS, now),
        ).fetchall()
        values = {(r["symbol"], r["day"]): float(r["close"]) for r in rows}
        returns = []
        for d in range(day - 30, day):
            if all((s, d) in values and (s, d - 1) in values for s in SYMBOLS):
                returns.append([values[s, d] / values[s, d - 1] - 1 for s in SYMBOLS])
        if len(returns) < 20:
            return dict.fromkeys(SYMBOLS, 0.0), "RISK_WARMUP"
        weights = np.array([raw[s] for s in SYMBOLS])
        if weights.sum() > self.config.gross_max:
            weights *= self.config.gross_max / weights.sum()
        cov = np.atleast_2d(np.cov(np.asarray(returns).T, ddof=1)) * 365
        vol = math.sqrt(max(0, float(weights @ cov @ weights)))
        if vol > self.config.annual_vol_target:
            weights *= self.config.annual_vol_target / vol
        reserve_rate = (
            self.config.fee_bps + self.config.half_spread_floor_bps + self.config.extra_slippage_bps
        ) / 10_000
        weights *= max(0.0, 1 - 2 * self.config.gross_max * reserve_rate)
        return dict(zip(SYMBOLS, map(float, weights), strict=True)), "READY"

    def _decision(self, now: int) -> bool:
        end = now // HOUR_MS * HOUR_MS
        if end <= self.state["started_ms"] or self.state["last_signal_hour"] == end:
            return False
        if now - end > self.config.signal_max_lag_ms:
            return False
        raw, complete, evidence = self._hour_weights(end, now)
        if not complete:
            self.state["strategy_state"] = "HOUR_INCOMPLETE"
            key = f"blocked_hour:{end}"
            if not self.db.execute("SELECT 1 FROM records WHERE event_key=?", (key,)).fetchone():
                self._append(
                    now,
                    "incident",
                    {
                        "kind": "hour_unusable",
                        "hour_end_ms": end,
                        "reason": "incomplete_or_non_websocket_hour",
                    },
                    key,
                )
                return True
            return False  # last minute may still be in flight; retry without fabricating it
        weights, status = self._risk_weights(raw, now)
        self.state["strategy_state"] = status
        self.state["last_signal_hour"] = end
        self._append(
            now,
            "decision",
            {
                "account": "B2",
                "scenario": "B2",
                "hour_end_ms": end,
                "raw_weights": raw,
                "target_weights": weights,
                "state": status,
                "evidence": evidence,
            },
            f"decision:B2:{end}",
        )
        account = self.state["accounts"]["B2"]
        for symbol, old in account["pending"].items():
            self._append(
                now,
                "order_event",
                {
                    "order_id": old["order_id"],
                    "account": "B2",
                    "symbol": symbol,
                    "status": "SUPERSEDED",
                },
                f"superseded:{old['order_id']}:{end}",
            )
        account["pending"] = {}
        for symbol, weight in weights.items():
            order = {
                "order_id": f"B2:{end}:{symbol}",
                "account": "B2",
                "symbol": symbol,
                "target_weight": weight,
                "decision_ms": now,
                "not_before_ms": (now // MINUTE_MS + 1) * MINUTE_MS,
                "expires_ms": now + self.config.order_lifetime_ms,
            }
            account["pending"][symbol] = order
            self._append(now, "order", {**order, "status": "OPEN"}, f"order:{order['order_id']}")
        return True

    def _fill(self, now: int, quotes: dict[str, Quote]) -> bool:
        account = self.state["accounts"]["B2"]
        prices = {s: (quotes[s].bid + quotes[s].ask) / 2 for s in SYMBOLS}
        nav = account["cash"] + sum(account["positions"][s] * prices[s] for s in SYMBOLS)
        changed = False
        sequence = sorted(
            account["pending"],
            key=lambda s: (
                account["pending"][s]["target_weight"] * nav - account["positions"][s] * prices[s]
                >= 0,
                s,
            ),
        )
        for symbol in sequence:
            order = account["pending"][symbol]
            quote = quotes[symbol]
            if now >= order["expires_ms"]:
                self._append(
                    now,
                    "order_event",
                    {
                        "order_id": order["order_id"],
                        "account": "B2",
                        "symbol": symbol,
                        "status": "EXPIRED",
                    },
                    f"expired:{order['order_id']}",
                )
                del account["pending"][symbol]
                changed = True
                continue
            if (
                quote.received_ms < order["not_before_ms"]
                or quote.received_ms <= order["decision_ms"]
            ):
                continue
            if quote.received_ms // MINUTE_MS != now // MINUTE_MS:
                continue
            if quote.update_id <= self.state["consumed_quotes"].get(symbol, -1):
                continue
            prior_open = now // MINUTE_MS * MINUTE_MS - MINUTE_MS
            capacity_bar = self.source.execute(
                "SELECT quote_volume,received_ms FROM closed_bars "
                "WHERE symbol=? AND open_ms=? AND source='websocket' AND received_ms<=?",
                (symbol, prior_open, quote.received_ms),
            ).fetchone()
            if not capacity_bar:
                continue
            mid = prices[symbol]
            nav = account["cash"] + sum(account["positions"][s] * prices[s] for s in SYMBOLS)
            weight = order["target_weight"]
            dollars = weight * nav - account["positions"][symbol] * mid
            if abs(dollars) <= 1e-7:
                del account["pending"][symbol]
                changed = True
                continue
            direction = 1 if dollars > 0 else -1
            half_spread = (quote.ask - quote.bid) / (2 * mid) * 10_000
            execution_rate = (
                max(half_spread, self.config.half_spread_floor_bps) + self.config.extra_slippage_bps
            ) / 10_000
            price = mid * (1 + direction * execution_rate)
            fee_rate = self.config.fee_bps / 10_000
            cost_per_q = abs(price - mid) + price * fee_rate
            desired = abs(dollars) / (mid + direction * weight * cost_per_q)
            capacity_key = f"{symbol}:{now // MINUTE_MS}"
            cap = max(
                0,
                float(capacity_bar["quote_volume"]) * self.config.participation_rate
                - self.state["capacity_used"].get(capacity_key, 0),
            )
            quantity = min(desired, cap / price)
            if direction == -1:
                quantity = min(quantity, account["positions"][symbol])
            else:
                gross = sum(account["positions"][s] * prices[s] for s in SYMBOLS)
                quantity = min(
                    quantity,
                    account["cash"] / (price * (1 + fee_rate)),
                    max(
                        0,
                        (self.config.single_asset_max * nav - account["positions"][symbol] * mid)
                        / (mid + self.config.single_asset_max * cost_per_q),
                    ),
                    max(
                        0,
                        (self.config.gross_max * nav - gross)
                        / (mid + self.config.gross_max * cost_per_q),
                    ),
                )
                for other in SYMBOLS:
                    if other != symbol:
                        quantity = min(
                            quantity,
                            max(
                                0,
                                (
                                    nav
                                    - account["positions"][other]
                                    * prices[other]
                                    / self.config.single_asset_max
                                )
                                / cost_per_q,
                            ),
                        )
            step = 0.00001 if symbol == "BTCUSDT" else 0.0001
            quantity = math.floor(quantity / step + 1e-9) * step
            self.state["consumed_quotes"][symbol] = quote.update_id
            changed = True
            if quantity * price < self.config.min_notional:
                status = (
                    "DUST_UNEXECUTED"
                    if desired * price < self.config.min_notional
                    else "CAPACITY_OR_RISK"
                )
                self._append(
                    now,
                    "order_event",
                    {
                        "order_id": order["order_id"],
                        "account": "B2",
                        "symbol": symbol,
                        "status": status,
                        "quote_id": quote.update_id,
                    },
                    f"attempt:{order['order_id']}:{quote.update_id}",
                )
                if status == "DUST_UNEXECUTED":
                    del account["pending"][symbol]
                continue
            notional, fee = quantity * price, quantity * price * fee_rate
            account["cash"] -= direction * notional + fee
            cycle = account["cycles"][symbol]
            if direction == 1 and account["positions"][symbol] <= 1e-12:
                cycle = {"entry_ms": now, "cost": 0.0, "proceeds": 0.0, "fees": 0.0}
                account["cycles"][symbol] = cycle
            account["positions"][symbol] += direction * quantity
            if abs(account["positions"][symbol]) < 1e-10:
                account["positions"][symbol] = 0.0
            cycle["fees"] += fee
            if direction == 1:
                cycle["cost"] += notional + fee
            else:
                cycle["proceeds"] += notional - fee
            if direction == -1 and account["positions"][symbol] == 0:
                self._append(
                    now,
                    "round_trip",
                    {
                        "scenario": "B2",
                        "account": "B2",
                        "symbol": symbol,
                        "cycle_id": f"{symbol}:{cycle['entry_ms']}",
                        "pnl": cycle["proceeds"] - cycle["cost"],
                    },
                    f"round_trip:{symbol}:{cycle['entry_ms']}",
                )
            nav_after = account["cash"] + sum(account["positions"][s] * prices[s] for s in SYMBOLS)
            if account["cash"] < -1e-7 or min(account["positions"].values()) < -1e-10:
                raise AssertionError("negative paper cash or spot quantity")
            if direction == 1 and (
                max(account["positions"][s] * prices[s] / nav_after for s in SYMBOLS)
                > self.config.single_asset_max + 1e-9
                or sum(account["positions"][s] * prices[s] / nav_after for s in SYMBOLS)
                > self.config.gross_max + 1e-9
            ):
                raise AssertionError("new paper buy exceeds post-cost risk limits")
            self.state["capacity_used"][capacity_key] = (
                self.state["capacity_used"].get(capacity_key, 0) + notional
            )
            fill = {
                "scenario": "B2",
                "account": "B2",
                "order_id": order["order_id"],
                "symbol": symbol,
                "side": "buy" if direction == 1 else "sell",
                "quantity": quantity,
                "price": price,
                "mid": mid,
                "notional": notional,
                "fee": fee,
                "execution_cost": quantity * abs(price - mid),
                "half_spread_bps": half_spread,
                "quote_id": quote.update_id,
                "quote_received_ms": quote.received_ms,
                "capacity_bar_open_ms": prior_open,
                "capacity_bar_received_ms": capacity_bar["received_ms"],
                "capacity_limit": float(capacity_bar["quote_volume"])
                * self.config.participation_rate,
            }
            self._append(now, "fill", fill, f"fill:{order['order_id']}:{quote.update_id}")
            self._append(
                now,
                "position",
                {
                    "account": "B2",
                    "scenario": "B2",
                    "cash": account["cash"],
                    "positions": account["positions"].copy(),
                },
                f"position:{order['order_id']}:{quote.update_id}",
            )
            if quantity >= desired * (1 - 1e-9):
                del account["pending"][symbol]
        self.state["capacity_used"] = {
            k: v
            for k, v in self.state["capacity_used"].items()
            if int(k.rsplit(":", 1)[1]) >= now // MINUTE_MS - 1
        }
        return changed

    def _seal_days(self, now: int) -> bool:
        changed = False
        for day in range(self.state["last_day"] + 1, now // DAY_MS):
            end = (day + 1) * DAY_MS
            if now < end + 2_000:
                break
            for name in ("B0", "B2"):
                position = self.db.execute(
                    "SELECT payload FROM records WHERE kind='position' AND received_us<? "
                    "AND json_extract(payload,'$.account')=? ORDER BY seq DESC LIMIT 1",
                    (end * 1000, name),
                ).fetchone()
                account = (
                    json.loads(position[0])
                    if position
                    else {
                        "cash": self.config.initial_cash,
                        "positions": dict.fromkeys(SYMBOLS, 0.0),
                    }
                )
                marks, stale = {}, False
                for symbol in SYMBOLS:
                    bar = self.source.execute(
                        "SELECT open_ms,close FROM closed_bars WHERE symbol=? AND open_ms<? "
                        "AND received_ms<=? AND source='websocket' ORDER BY open_ms DESC LIMIT 1",
                        (symbol, end, now),
                    ).fetchone()
                    if account["positions"][symbol] > 0 and (
                        not bar or bar["open_ms"] != end - MINUTE_MS
                    ):
                        stale = True
                    marks[symbol] = float(bar["close"]) if bar else 0.0
                nav = account["cash"] + sum(account["positions"][s] * marks[s] for s in SYMBOLS)
                fills = [
                    json.loads(r[0])
                    for r in self.db.execute(
                        "SELECT payload FROM records WHERE kind='fill' AND received_us>=? "
                        "AND received_us<? AND json_extract(payload,'$.account')=?",
                        (day * DAY_MS * 1000, end * 1000, name),
                    )
                ]
                previous = self.db.execute(
                    "SELECT payload FROM records WHERE kind='nav' "
                    "AND json_extract(payload,'$.account')=? ORDER BY seq DESC LIMIT 1",
                    (name,),
                ).fetchone()
                previous_nav = (
                    json.loads(previous[0])["nav"] if previous else self.config.initial_cash
                )
                timely = now - end <= 120_000
                complete_day = day * DAY_MS >= self.state["started_ms"]
                self._append(
                    now,
                    "nav",
                    {
                        "scenario": name,
                        "account": name,
                        "date": _date(day * DAY_MS),
                        "nav": nav,
                        "return": nav / previous_nav - 1,
                        "cash": account["cash"],
                        "positions": account["positions"],
                        "marks": marks,
                        "fees": sum(f["fee"] for f in fills),
                        "execution_costs": sum(f["execution_cost"] for f in fills),
                        "turnover": sum(f["notional"] for f in fills) / previous_nav,
                        "stale_exposure": stale,
                        "daily_risk_observable": not stale and timely and complete_day,
                        "complete_utc_day": complete_day,
                        "timely_recorded": timely,
                        "source": "live" if self.config.mode == "live_paper" else "synthetic",
                        "observation_status": "FORWARD" if timely else "MISSED_WHILE_STOPPED",
                    },
                    f"nav:{name}:{day}",
                )
            self.state["last_day"] = day
            changed = True
        return changed

    def process_tick(self, now_ms: int, health: dict, quotes: list[Quote] | None = None) -> dict:
        """Process current evidence once; callers supply fresh in-memory WS quotes.

        Poll at <=15 second intervals. The function performs no network requests.
        Healthy status alone never replaces the 72-hour qualification or risk warmup.
        """
        now = int(now_ms)
        if self.config.mode == "live_paper" and abs(now - time.time_ns() // 1_000_000) > 5_000:
            raise RuntimeError("tick time differs from actual local wall clock")
        if now <= self.state["last_tick_ms"]:
            regression = now < self.state["last_tick_ms"]
            if regression and "clock_regression" not in self.state["freeze_reasons"]:
                safe = self.state["last_tick_ms"]
                with self.db:
                    self.state["freeze_reasons"] = ["clock_regression"]
                    self.state["last_healthy"] = False
                    self._append(
                        safe,
                        "incident",
                        {"kind": "clock_regression", "reported_ms": now, "last_safe_ms": safe},
                        f"clock_regression:{safe}:{now}",
                    )
                    self._cancel_pending(safe, "clock_regression")
                    self._checkpoint(safe)
            return {**self.status(), "idempotent": not regression, "clock_regression": regression}
        old_state, old_seq, old_head = _json(self.state), self.seq, self.head
        old_credit, old_restarted = self._heartbeat_credit, self._restarted
        current_monotonic = time.monotonic()
        try:
            self._guard()
            by_symbol = {q.symbol: q for q in quotes or []}
            reasons = self._reasons(now, health, by_symbol)
            if (
                self.config.mode == "live_paper"
                and not self._restarted
                and abs(
                    (now - self.state["last_tick_ms"]) / 1000
                    - (current_monotonic - self._last_monotonic)
                )
                > 5
            ):
                reasons.append("clock_jump")
            healthy = not reasons
            elapsed = (now - self.state["last_tick_ms"]) / 1000
            credit = elapsed if elapsed <= 30 and healthy and self.state["last_healthy"] else 0.0
            if self._restarted:
                credit = 0.0
                self._restarted = False
            self.state["observed_seconds"] += elapsed
            self.state["healthy_seconds"] += credit
            self._heartbeat_credit += credit
            changed = reasons != self.state["freeze_reasons"]
            with self.db:
                if old_restarted:
                    changed |= self._cancel_pending(now, "process_restart")
                    self._append(
                        now,
                        "incident",
                        {
                            "kind": "process_restart",
                            "policy": "cancel_unfilled_goals_preserve_cash_and_positions",
                        },
                        f"process_restart:{now}",
                    )
                    changed = True
                if reasons != self.state["freeze_reasons"]:
                    self._append(
                        now,
                        "incident",
                        {
                            "kind": "freeze" if reasons else "recovered",
                            "reasons": reasons,
                            "qualified_72h": health.get("qualified_72h", False),
                        },
                        f"health_transition:{now}",
                    )
                    self.state["freeze_reasons"] = reasons
                changed |= self._seal_days(now)
                if healthy:
                    changed |= self._decision(now)
                    changed |= self._fill(now, by_symbol)
                else:
                    changed |= self._cancel_pending(now, ",".join(reasons))
                if now - self.state["last_heartbeat_ms"] >= 15_000:
                    self._append(
                        now,
                        "heartbeat",
                        {
                            "healthy": healthy,
                            "qualified_72h": health.get("qualified_72h", False),
                            "observed_seconds": self.state["observed_seconds"],
                            "healthy_seconds": self.state["healthy_seconds"],
                            "credited_seconds": self._heartbeat_credit,
                            "max_credit_interval_seconds": 30,
                        },
                        f"heartbeat:{now}",
                    )
                    self.state["last_heartbeat_ms"] = now
                    self._heartbeat_credit = 0.0
                self.state["last_tick_ms"], self.state["last_healthy"] = now, healthy
                if changed or now - self.state["last_checkpoint_ms"] >= MINUTE_MS:
                    self._checkpoint(now)
        except Exception:
            self.state, self.seq, self.head = json.loads(old_state), old_seq, old_head
            self._heartbeat_credit, self._restarted = old_credit, old_restarted
            raise
        self._last_monotonic = current_monotonic
        return self.status()

    def status(self) -> dict:
        return {
            "database": str(self.path),
            "version": self.version,
            "mode": self.config.mode,
            "scope": "B0_B2_engineering_references_no_champion",
            "frozen": bool(self.state["freeze_reasons"]),
            "freeze_reasons": self.state["freeze_reasons"],
            "observed_seconds": self.state["observed_seconds"],
            "healthy_seconds": self.state["healthy_seconds"],
            "cash": {n: a["cash"] for n, a in self.state["accounts"].items()},
            "positions": {n: a["positions"].copy() for n, a in self.state["accounts"].items()},
            "last_signal_hour_ms": self.state["last_signal_hour"],
            "strategy_state": self.state.get("strategy_state", "UNKNOWN"),
            "records": self.seq,
            "head_hash": self.head,
        }
