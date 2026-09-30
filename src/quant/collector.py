"""Public mainnet observation only; REST repairs never become live evidence."""

from __future__ import annotations

import asyncio
import contextlib
import fcntl
import json
import math
import os
import shutil
import signal
import sqlite3
import time
from collections.abc import Callable
from decimal import Decimal
from pathlib import Path
from typing import Any

import httpx
import websockets

from . import disk
from .paths import ROOT, STATE, VHD

SYMBOLS = ("BTCUSDT", "ETHUSDT")
MINUTE_MS = 60_000
REQUIRED_SECONDS = 72 * 3600
REQUIRED_UPTIME = 0.999
HEARTBEAT_SECONDS = 15
ROTATE_SECONDS = 23 * 3600 + 50 * 60
INTAKE_RESERVE_BYTES = 100_000_000
FULL_DISK_REFRESH_SECONDS = 15 * 60
REST_BASE = "https://data-api.binance.vision"
STREAM_URL = "wss://data-stream.binance.vision/stream?streams=" + "/".join(
    stream for s in SYMBOLS for stream in (f"{s.lower()}@kline_1m", f"{s.lower()}@bookTicker")
)


def now_ms() -> int:
    return time.time_ns() // 1_000_000


def default_db() -> Path:
    return STATE / "live.sqlite3"


class CollectorStopped(RuntimeError):
    """A local operational guard stopped observation."""


class Collector:
    """Persist bounded aggregates, provenance, gaps and operational evidence.

    Message handling alone cannot accrue online seconds. Only collect() starts a
    real network session and its monotonic heartbeat credits healthy elapsed time.
    A process restart starts a new 72-hour qualification window conservatively.
    Documented connection rotations count as downtime; they do not reset the window.
    """

    def __init__(
        self,
        db_path: Path | None = None,
        *,
        disk_check: Callable[..., dict] = disk.check,
        initial_disk: dict | None = None,
        tick_callback: Callable[[dict[str, Any]], None] | None = None,
    ) -> None:
        self.path = Path(db_path or default_db())
        self.disk_check = disk_check
        self.tick_callback = tick_callback
        self._custom_guard = disk_check is not disk.check
        self._disk_ledger = initial_disk or self.disk_check(reserve=INTAKE_RESERVE_BYTES)
        self._disk_snapshot = {**self._disk_ledger, "asof_ms": now_ms(), "check_kind": "full_start"}
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(self.path, timeout=10)
        self.db.row_factory = sqlite3.Row
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.execute("PRAGMA synchronous=FULL")
        self.db.execute("PRAGMA wal_autocheckpoint=256")
        self.db.execute("PRAGMA journal_size_limit=4194304")
        self.db.executescript("""
            CREATE TABLE IF NOT EXISTS closed_bars (
                symbol TEXT NOT NULL, open_ms INTEGER NOT NULL, close_ms INTEGER NOT NULL,
                open TEXT NOT NULL, high TEXT NOT NULL, low TEXT NOT NULL, close TEXT NOT NULL,
                volume TEXT NOT NULL, quote_volume TEXT NOT NULL, trades INTEGER NOT NULL,
                exchange_event_ms INTEGER, received_ms INTEGER NOT NULL,
                source TEXT NOT NULL CHECK(source IN ('websocket','rest')),
                websocket_received_ms INTEGER, session_id INTEGER,
                PRIMARY KEY(symbol, open_ms)
            );
            CREATE TABLE IF NOT EXISTS quote_minutes (
                symbol TEXT NOT NULL, minute_ms INTEGER NOT NULL,
                samples INTEGER NOT NULL, spread_bps_sum REAL NOT NULL,
                spread_bps_min REAL NOT NULL, spread_bps_max REAL NOT NULL,
                last_bid TEXT NOT NULL, last_ask TEXT NOT NULL,
                first_received_ms INTEGER NOT NULL, last_received_ms INTEGER NOT NULL,
                first_update_id INTEGER NOT NULL, last_update_id INTEGER NOT NULL,
                exchange_event_ms INTEGER, partial INTEGER NOT NULL DEFAULT 0,
                PRIMARY KEY(symbol, minute_ms)
            );
            CREATE TABLE IF NOT EXISTS gaps (
                id INTEGER PRIMARY KEY, symbol TEXT NOT NULL,
                start_ms INTEGER NOT NULL, end_ms INTEGER NOT NULL,
                detected_ms INTEGER NOT NULL, reason TEXT NOT NULL,
                repaired_ms INTEGER, UNIQUE(symbol, start_ms, end_ms)
            );
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY, received_ms INTEGER NOT NULL,
                kind TEXT NOT NULL, symbol TEXT, detail TEXT NOT NULL, session_id INTEGER
            );
            CREATE INDEX IF NOT EXISTS events_time ON events(received_ms);
            CREATE TABLE IF NOT EXISTS sessions (
                id INTEGER PRIMARY KEY, started_ms INTEGER NOT NULL, ended_ms INTEGER,
                state TEXT NOT NULL, heartbeat_ms INTEGER,
                healthy_seconds REAL NOT NULL DEFAULT 0,
                observed_seconds REAL NOT NULL DEFAULT 0,
                healthy_since_ms INTEGER, clock_offset_ms REAL, last_error TEXT,
                endpoint TEXT NOT NULL
            );
        """)
        session_columns = {row[1] for row in self.db.execute("PRAGMA table_info(sessions)")}
        if "observed_seconds" not in session_columns:
            self.db.execute("ALTER TABLE sessions ADD COLUMN observed_seconds REAL DEFAULT 0")
        self.db.commit()
        self.session_id: int | None = None
        self.quote_buffers: dict[str, dict[str, Any]] = {}
        self.last_quote_id: dict[str, int] = {
            row["symbol"]: row["last_update_id"]
            for row in self.db.execute(
                "SELECT symbol,MAX(last_update_id) last_update_id "
                "FROM quote_minutes GROUP BY symbol"
            )
        }
        self.last_quote_received: dict[str, int] = {}
        self.last_kline_received: dict[str, int] = {}
        self.last_closed_received: dict[str, int] = {}
        self._last_guard = time.monotonic()
        self._last_heartbeat = time.monotonic()
        self._last_wall = now_ms()
        self._heartbeat_ms: int | None = None
        self._healthy = False
        self._clock_offset: float | None = None
        self._fatal: str | None = None
        self._fatal_kind: str | None = None
        self._connected = False
        self._interval_fault = False
        self.latest_quotes: dict[str, dict[str, Any]] = {}
        self._pending_gaps = self.db.execute(
            "SELECT COUNT(*) FROM gaps WHERE repaired_ms IS NULL"
        ).fetchone()[0]
        self._qualification_snapshot = {
            "qualified_72h": False,
            "asof_ms": None,
            "observed_seconds": 0.0,
            "healthy_seconds": 0.0,
            "uptime_fraction": 0.0,
        }
        self._budget_vhd = self._disk_ledger.get("wsl_vhd_bytes", 0)
        self._budget_db = self._database_bytes()

    def close(self) -> None:
        self.flush_quotes(partial=True)
        self.db.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        self.db.close()

    def event(self, kind: str, detail: Any = "", symbol: str | None = None) -> None:
        self.db.execute(
            "INSERT INTO events(received_ms,kind,symbol,detail,session_id) VALUES(?,?,?,?,?)",
            (now_ms(), kind, symbol, json.dumps(detail, ensure_ascii=False), self.session_id),
        )
        self.db.commit()

    def guard(self, *, force: bool = False) -> None:
        if self._fatal:
            raise CollectorStopped(self._fatal)
        if not force and time.monotonic() - self._last_guard < HEARTBEAT_SECONDS:
            return
        self._last_guard = time.monotonic()
        try:
            if self._custom_guard:
                result = self.disk_check(reserve=INTAKE_RESERVE_BYTES)
            else:
                # DrvFs directory scans are slow. Bound this writer between full
                # background scans with cheap physical VHD and logical DB deltas.
                growth = max(
                    0,
                    VHD.stat().st_size - self._budget_vhd,
                    self._database_bytes() - self._budget_db,
                )
                if growth >= INTAKE_RESERVE_BYTES:
                    raise RuntimeError("Collector's 100 MB allocation budget is exhausted")
                used = self._disk_ledger["total_bytes"] + growth
                health = disk.enforce(used, INTAKE_RESERVE_BYTES, shutil.disk_usage(ROOT).free)
                result = {
                    "status": health,
                    "conservative_total_bytes": used,
                    "growth_bytes": growth,
                    "reserve_bytes": INTAKE_RESERVE_BYTES,
                }
        except Exception as exc:
            self._disk_stop(exc)
            raise CollectorStopped(self._fatal) from exc
        if result.get("status") == "WARNING":
            self.event("disk_warning", result)
        self._disk_snapshot = {
            **result,
            "asof_ms": now_ms(),
            "check_kind": "cheap_guard" if not self._custom_guard else "injected_guard",
        }

    def _database_bytes(self) -> int:
        total = 0
        for path in (self.path, Path(str(self.path) + "-wal"), Path(str(self.path) + "-shm")):
            with contextlib.suppress(FileNotFoundError):
                total += path.stat().st_size
        return total

    def _disk_stop(self, exc: Exception) -> None:
        self._fatal = f"disk_guard: {exc}"
        self._fatal_kind = "disk"
        self._disk_snapshot = {
            "status": "STOPPED",
            "asof_ms": now_ms(),
            "check_kind": "guard_rejection",
            "reason": self._fatal,
        }
        self.event("disk_stop", self._fatal)
        if self.session_id is not None:
            self.db.execute(
                "UPDATE sessions SET state='DISK_STOP', healthy_seconds=0, last_error=? WHERE id=?",
                (self._fatal, self.session_id),
            )
            self.db.commit()

    async def _refresh_disk_budget(self) -> None:
        try:
            ledger = await asyncio.to_thread(self.disk_check, reserve=INTAKE_RESERVE_BYTES)
        except Exception as exc:
            self._disk_stop(exc)
            raise CollectorStopped(self._fatal) from exc
        self._disk_ledger = ledger
        self._disk_snapshot = {**ledger, "asof_ms": now_ms(), "check_kind": "full_refresh"}
        self._budget_vhd = ledger.get("wsl_vhd_bytes", 0)
        self._budget_db = self._database_bytes()
        self.event("disk_budget_refresh", ledger)

    def _record_gap(self, symbol: str, start: int, end: int, reason: str) -> None:
        if start > end:
            return
        inserted = self.db.execute(
            "INSERT OR IGNORE INTO gaps(symbol,start_ms,end_ms,detected_ms,reason) "
            "VALUES(?,?,?,?,?)",
            (symbol, start, end, now_ms(), reason),
        ).rowcount
        if inserted:
            self._pending_gaps += 1
            self.event("gap", {"start_ms": start, "end_ms": end, "reason": reason}, symbol)

    def detect_gaps(self, at_ms: int | None = None) -> None:
        """Record missing internal and trailing closed minutes, including silent feeds."""
        at_ms = now_ms() if at_ms is None else at_ms
        # Allow final kline publication two seconds; never repair an open candle.
        latest_closed = (at_ms - 2_000) // MINUTE_MS * MINUTE_MS - MINUTE_MS
        for symbol in SYMBOLS:
            rows = self.db.execute(
                "SELECT open_ms FROM closed_bars WHERE symbol=? ORDER BY open_ms",
                (symbol,),
            ).fetchall()
            if not rows:
                continue
            previous = rows[0][0]
            for row in rows[1:]:
                current = row[0]
                if current > previous + MINUTE_MS:
                    self._record_gap(
                        symbol, previous + MINUTE_MS, current - MINUTE_MS, "missing_closed_kline"
                    )
                previous = current
            if latest_closed > previous:
                self._record_gap(
                    symbol, previous + MINUTE_MS, latest_closed, "trailing_closed_kline"
                )
        self.db.commit()

    def _bar(
        self, symbol: str, k: dict, received_ms: int, source: str, exchange_ms: int | None
    ) -> bool:
        start, end = int(k["t"]), int(k["T"])
        if start % MINUTE_MS or end != start + MINUTE_MS - 1:
            raise ValueError("Invalid 1m boundaries")
        if end >= received_ms:
            raise ValueError("A future/open kline cannot be stored as closed")
        values = [Decimal(str(k[x])) for x in ("o", "h", "l", "c", "v", "q")]
        o, h, low, c, v, q = values
        if (
            any(not x.is_finite() for x in values)
            or low <= 0
            or h < max(o, c)
            or low > min(o, c)
            or v < 0
            or q < 0
            or int(k["n"]) < 0
        ):
            raise ValueError("Invalid OHLCV")
        previous = self.db.execute(
            "SELECT MAX(open_ms) FROM closed_bars WHERE symbol=?",
            (symbol,),
        ).fetchone()[0]
        if previous is not None and start > previous + MINUTE_MS:
            self._record_gap(
                symbol, previous + MINUTE_MS, start - MINUTE_MS, "missing_closed_kline"
            )
        ws_received = received_ms if source == "websocket" else None
        inserted = self.db.execute(
            "INSERT OR IGNORE INTO closed_bars VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                symbol,
                start,
                end,
                *(str(k[x]) for x in ("o", "h", "l", "c", "v", "q")),
                int(k["n"]),
                exchange_ms,
                received_ms,
                source,
                ws_received,
                self.session_id,
            ),
        ).rowcount
        new_ws_evidence = 0
        if not inserted and source == "websocket":
            # Preserve first received/source; attach genuine WS evidence if repair came first.
            new_ws_evidence = self.db.execute(
                "UPDATE closed_bars SET websocket_received_ms=?,exchange_event_ms=? "
                "WHERE symbol=? AND open_ms=? AND websocket_received_ms IS NULL",
                (received_ms, exchange_ms, symbol, start),
            ).rowcount
        self.db.commit()
        return bool(inserted or new_ws_evidence)

    def handle_message(self, payload: dict, received_ms: int | None = None) -> bool:
        """Consume one WS message. Tests may supply timestamps; this grants no uptime."""
        self.guard()
        received_ms = now_ms() if received_ms is None else received_ms
        data = payload.get("data", payload)
        if data.get("e") == "serverShutdown":
            self.event("server_shutdown", data)
            raise ConnectionError("Binance serverShutdown")
        symbol = data.get("s")
        if symbol not in SYMBOLS:
            return False
        if data.get("e") == "kline":
            k = data["k"]
            if k.get("i") != "1m" or k.get("s", symbol) != symbol:
                raise ValueError("Unexpected kline stream")
            exchange_ms = int(data["E"])
            if exchange_ms > received_ms + 5_000:
                raise ValueError("Exchange timestamp ahead of local clock")
            if received_ms - exchange_ms > 15_000:
                raise ValueError("Stale exchange kline event exceeds 15 seconds")
            self.last_kline_received[symbol] = received_ms
            if k.get("x") is not True:
                return False
            inserted = self._bar(symbol, k, received_ms, "websocket", exchange_ms)
            self.last_closed_received[symbol] = received_ms
            if inserted:
                self._notify("closed_bar", symbol, received_ms, exchange_ms, k)
            return inserted
        if "u" in data and "b" in data and "a" in data:
            accepted = self._quote(symbol, data, received_ms)
            if accepted:
                self._notify("quote", symbol, received_ms, None)
            return accepted
        return False

    def _quote(self, symbol: str, data: dict, received_ms: int) -> bool:
        update_id = int(data["u"])
        if update_id <= self.last_quote_id.get(symbol, -1):
            return False
        bid, ask = Decimal(data["b"]), Decimal(data["a"])
        bid_qty = Decimal(str(data.get("B", 0)))
        ask_qty = Decimal(str(data.get("A", 0)))
        if not bid.is_finite() or not ask.is_finite() or bid <= 0 or ask < bid:
            raise ValueError("Invalid best bid/ask")
        if not bid_qty.is_finite() or not ask_qty.is_finite() or bid_qty < 0 or ask_qty < 0:
            raise ValueError("Invalid quote quantity")
        spread = float((ask - bid) / ((ask + bid) / 2) * 10_000)
        minute = received_ms // MINUTE_MS * MINUTE_MS
        buffer = self.quote_buffers.get(symbol)
        if buffer is not None and buffer["minute_ms"] != minute:
            self._flush_quote(symbol, buffer)
            buffer = None
        if buffer is None:
            buffer = {
                "minute_ms": minute,
                "samples": 0,
                "sum": 0.0,
                "min": math.inf,
                "max": 0.0,
                "first_received": received_ms,
                "first_id": update_id,
            }
            self.quote_buffers[symbol] = buffer
        buffer["samples"] += 1
        buffer["sum"] += spread
        buffer["min"] = min(buffer["min"], spread)
        buffer["max"] = max(buffer["max"], spread)
        buffer.update(
            last_bid=str(bid), last_ask=str(ask), last_received=received_ms, last_id=update_id
        )
        self.last_quote_id[symbol] = update_id
        self.last_quote_received[symbol] = received_ms
        self.latest_quotes[symbol] = {
            "symbol": symbol,
            "bid": float(bid),
            "ask": float(ask),
            "bid_qty": float(bid_qty),
            "ask_qty": float(ask_qty),
            "update_id": update_id,
            "received_ms": received_ms,
            "received_us": received_ms * 1000,
            "exchange_event_ms": None,
            "exchange_event_us": None,
            "source": "websocket",
        }
        return True

    def health_snapshot(self, received_ms: int | None = None) -> dict[str, Any]:
        """Cheap current operational health; no directory scans or history queries."""
        received_ms = now_ms() if received_ms is None else received_ms
        reasons: list[str] = []
        if self.session_id is None or not self._connected:
            reasons.append("No live connected collection session")
        if self._fatal:
            reasons.append(self._fatal)
        if self._clock_offset is None or abs(self._clock_offset) > 5_000:
            reasons.append("Clock synchronization is unavailable or outside tolerance")
        if self._pending_gaps:
            reasons.append("Unresolved closed candle gaps")
        if self._interval_fault:
            reasons.append("Connection/clock incident awaits next health heartbeat")
        ages = {}
        for symbol in SYMBOLS:
            quote_ms = self.last_quote_received.get(symbol)
            kline_ms = self.last_kline_received.get(symbol)
            closed_ms = self.last_closed_received.get(symbol)
            quote_age = received_ms - quote_ms if quote_ms is not None else None
            kline_age = received_ms - kline_ms if kline_ms is not None else None
            closed_age = received_ms - closed_ms if closed_ms is not None else None
            ages[symbol] = {
                "quote_age_ms": quote_age,
                "kline_age_ms": kline_age,
                "closed_age_ms": closed_age,
            }
            if quote_age is None or not 0 <= quote_age <= 30_000:
                reasons.append(f"{symbol}: quote is absent or stale")
            if kline_age is None or not 0 <= kline_age <= 15_000:
                reasons.append(f"{symbol}: kline is absent or stale")
            if closed_age is None or not 0 <= closed_age <= 90_000:
                reasons.append(f"{symbol}: closed candle is absent or stale")
        qualification = dict(self._qualification_snapshot)
        qualification["qualified_72h"] = qualification["qualified_72h"] and not reasons
        return {
            "healthy": not reasons,
            "reasons": reasons,
            "ages": ages,
            "connected": self._connected,
            "live_session": self.session_id is not None,
            "clock_offset_ms": self._clock_offset,
            "unresolved_gaps": self._pending_gaps,
            "session_id": self.session_id,
            "qualification": qualification,
            "heartbeat_ms": self._heartbeat_ms,
            "disk": dict(self._disk_snapshot),
        }

    def _notify(
        self,
        kind: str,
        symbol: str,
        received_ms: int,
        exchange_ms: int | None,
        bar: dict | None = None,
    ) -> None:
        if self.tick_callback is None:
            return
        quotes = {}
        for item_symbol, quote in self.latest_quotes.items():
            age = received_ms - quote["received_ms"]
            quotes[item_symbol] = {**quote, "age_ms": age, "fresh": 0 <= age <= 2_000}
        closed_bar = None
        if bar is not None:
            closed_bar = {
                "symbol": symbol,
                "open_us": int(bar["t"]) * 1000,
                "close_us": (int(bar["T"]) + 1) * 1000,
                "source_close_us": int(bar["T"]) * 1000,
                "available_us": received_ms * 1000,
                **{
                    name: float(bar[key])
                    for name, key in (
                        ("open", "o"),
                        ("high", "h"),
                        ("low", "l"),
                        ("close", "c"),
                        ("volume", "v"),
                        ("quote_volume", "q"),
                    )
                },
                "trades": int(bar["n"]),
                "source": "websocket",
            }
        tick = {
            "kind": kind,
            "symbol": symbol,
            "received_ms": received_ms,
            "received_us": received_ms * 1000,
            "exchange_event_ms": exchange_ms,
            "exchange_event_us": exchange_ms * 1000 if exchange_ms is not None else None,
            "quotes": quotes,
            "bar": closed_bar,
            "health": self.health_snapshot(received_ms),
        }
        try:
            self.tick_callback(tick)
        except Exception as exc:
            self._fatal = f"tick_callback failed: {type(exc).__name__}: {exc}"
            self._fatal_kind = "callback"
            self._interval_fault = True
            self.event("callback_stop", self._fatal)
            raise CollectorStopped(self._fatal) from exc

    def _flush_quote(self, symbol: str, buffer: dict, partial: bool = False) -> None:
        self.db.execute(
            """
            INSERT INTO quote_minutes VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            ON CONFLICT(symbol,minute_ms) DO UPDATE SET
                samples=quote_minutes.samples+excluded.samples,
                spread_bps_sum=quote_minutes.spread_bps_sum+excluded.spread_bps_sum,
                spread_bps_min=MIN(quote_minutes.spread_bps_min,excluded.spread_bps_min),
                spread_bps_max=MAX(quote_minutes.spread_bps_max,excluded.spread_bps_max),
                last_bid=excluded.last_bid,last_ask=excluded.last_ask,
                last_received_ms=excluded.last_received_ms,last_update_id=excluded.last_update_id,
                partial=MAX(quote_minutes.partial,excluded.partial)
        """,
            (
                symbol,
                buffer["minute_ms"],
                buffer["samples"],
                buffer["sum"],
                buffer["min"],
                buffer["max"],
                buffer["last_bid"],
                buffer["last_ask"],
                buffer["first_received"],
                buffer["last_received"],
                buffer["first_id"],
                buffer["last_id"],
                None,
                int(partial),
            ),
        )
        self.db.commit()

    def flush_quotes(self, at_ms: int | None = None, *, partial: bool = False) -> None:
        at_ms = now_ms() if at_ms is None else at_ms
        for symbol, buffer in list(self.quote_buffers.items()):
            if partial or buffer["minute_ms"] + MINUTE_MS <= at_ms:
                self._flush_quote(symbol, buffer, partial)
                del self.quote_buffers[symbol]

    async def repair(self, client: httpx.AsyncClient) -> int:
        """REST closed bars only; request/receive times and REST provenance preserved."""
        self.guard(force=True)
        repaired = 0
        pending = self.db.execute(
            "SELECT * FROM gaps WHERE repaired_ms IS NULL ORDER BY id LIMIT 16"
        ).fetchall()
        for gap in pending:
            cursor = gap["start_ms"]
            while cursor <= gap["end_ms"]:
                self.guard()
                response = await client.get(
                    REST_BASE + "/api/v3/klines",
                    params={
                        "symbol": gap["symbol"],
                        "interval": "1m",
                        "startTime": cursor,
                        "endTime": gap["end_ms"] + MINUTE_MS - 1,
                        "limit": 1000,
                    },
                )
                response.raise_for_status()
                received = now_ms()
                rows = response.json()
                if not isinstance(rows, list):
                    raise ValueError("Unexpected REST klines response")
                if not rows:
                    break
                advanced = cursor
                for row in rows:
                    opened, closed = int(row[0]), int(row[6])
                    if not cursor <= opened <= gap["end_ms"] or closed >= received:
                        continue
                    k = dict(
                        t=opened,
                        T=closed,
                        o=row[1],
                        h=row[2],
                        l=row[3],
                        c=row[4],
                        v=row[5],
                        q=row[7],
                        n=row[8],
                    )
                    repaired += int(self._bar(gap["symbol"], k, received, "rest", None))
                    advanced = max(advanced, opened + MINUTE_MS)
                if advanced <= cursor:
                    break
                cursor = advanced
                await asyncio.sleep(0.05)
            count = self.db.execute(
                "SELECT COUNT(*) FROM closed_bars WHERE symbol=? AND open_ms BETWEEN ? AND ?",
                (gap["symbol"], gap["start_ms"], gap["end_ms"]),
            ).fetchone()[0]
            expected = (gap["end_ms"] - gap["start_ms"]) // MINUTE_MS + 1
            if count == expected:
                self.db.execute("UPDATE gaps SET repaired_ms=? WHERE id=?", (now_ms(), gap["id"]))
                self.event("repair", {"gap_id": gap["id"], "bars": count}, gap["symbol"])
        self.db.commit()
        self._pending_gaps = self.db.execute(
            "SELECT COUNT(*) FROM gaps WHERE repaired_ms IS NULL"
        ).fetchone()[0]
        return repaired

    async def sync_clock(self, client: httpx.AsyncClient) -> None:
        before = now_ms()
        response = await client.get(REST_BASE + "/api/v3/time")
        response.raise_for_status()
        after = now_ms()
        self._clock_offset = int(response.json()["serverTime"]) - (before + after) / 2
        self.event("clock_sync", {"offset_ms": self._clock_offset, "rtt_ms": after - before})
        if abs(self._clock_offset) > 5_000:
            self.event("clock_unhealthy", {"offset_ms": self._clock_offset})
            self._invalidate_clock_quotes(before, after)

    def _invalidate_clock_quotes(self, start_ms: int, end_ms: int) -> None:
        self.flush_quotes(partial=True)
        self.db.execute(
            "UPDATE quote_minutes SET partial=1 WHERE minute_ms BETWEEN ? AND ?",
            (
                min(start_ms, end_ms) // MINUTE_MS * MINUTE_MS,
                max(start_ms, end_ms) // MINUTE_MS * MINUTE_MS,
            ),
        )
        self.db.commit()
        self._interval_fault = True

    def _heartbeat(self) -> None:
        self.guard(force=True)
        current_mono, current_ms = time.monotonic(), now_ms()
        elapsed = current_mono - self._last_heartbeat
        wall_elapsed = (current_ms - self._last_wall) / 1000
        stable_clock = abs(wall_elapsed - elapsed) <= 5
        healthy = (
            self._connected
            and stable_clock
            and elapsed <= 30
            and self._clock_offset is not None
            and abs(self._clock_offset) <= 5_000
            and self._fatal is None
            and all(
                current_ms - self.last_quote_received.get(s, 0) <= 30_000
                and current_ms - self.last_kline_received.get(s, 0) <= 15_000
                and current_ms - self.last_closed_received.get(s, 0) <= 90_000
                for s in SYMBOLS
            )
            and not self.db.execute(
                "SELECT 1 FROM gaps WHERE repaired_ms IS NULL LIMIT 1"
            ).fetchone()
        )
        if not stable_clock:
            self.event("clock_jump", {"wall_s": wall_elapsed, "monotonic_s": elapsed})
            self._invalidate_clock_quotes(self._last_wall, current_ms)
            self._clock_offset = None
        if healthy != self._healthy:
            self.event("health", {"healthy": healthy})
        if self.session_id is not None:
            # Credit only intervals whose two ends were healthy; process sleep, replay,
            # delayed callbacks and stopped sessions cannot manufacture elapsed time.
            credit = elapsed if healthy and self._healthy and not self._interval_fault else 0
            if healthy:
                self.db.execute(
                    "UPDATE sessions SET heartbeat_ms=?,healthy_seconds=healthy_seconds+?,"
                    "observed_seconds=observed_seconds+?,"
                    "healthy_since_ms=COALESCE(healthy_since_ms,?),clock_offset_ms=? WHERE id=?",
                    (
                        current_ms,
                        credit,
                        max(0, elapsed),
                        current_ms,
                        self._clock_offset,
                        self.session_id,
                    ),
                )
            else:
                self.db.execute(
                    "UPDATE sessions SET heartbeat_ms=?,observed_seconds=observed_seconds+?,"
                    "healthy_since_ms=NULL,clock_offset_ms=? WHERE id=?",
                    (current_ms, max(0, elapsed), self._clock_offset, self.session_id),
                )
            self.db.commit()
            self._heartbeat_ms = current_ms
            self._refresh_qualification_snapshot(current_ms)
        self.event(
            "heartbeat",
            {"healthy": healthy, "elapsed_s": elapsed, "interval_fault": self._interval_fault},
        )
        self._last_heartbeat, self._last_wall, self._healthy = current_mono, current_ms, healthy
        self._interval_fault = False

    def _refresh_qualification_snapshot(self, current_ms: int) -> None:
        """Heartbeat-cached readiness only; instant tick callbacks remain O(symbols)."""
        row = self.db.execute("SELECT * FROM sessions WHERE id=?", (self.session_id,)).fetchone()
        observed, healthy = row["observed_seconds"], row["healthy_seconds"]
        uptime = healthy / observed if observed > 0 else 0.0
        qualified = (
            observed >= REQUIRED_SECONDS
            and uptime >= REQUIRED_UPTIME
            and self._fatal is None
            and self._pending_gaps == 0
            and self._clock_offset is not None
            and abs(self._clock_offset) <= 5000
        )
        if qualified:
            last = current_ms // MINUTE_MS * MINUTE_MS - MINUTE_MS
            first = last - (4320 - 1) * MINUTE_MS
            for symbol in SYMBOLS:
                bars = self.db.execute(
                    "SELECT COUNT(*) FROM closed_bars WHERE symbol=? AND open_ms BETWEEN ? AND ?",
                    (symbol, first, last),
                ).fetchone()[0]
                quotes = self.db.execute(
                    "SELECT COUNT(*) FROM quote_minutes WHERE symbol=? "
                    "AND minute_ms BETWEEN ? AND ? "
                    "AND partial=0",
                    (symbol, first, last),
                ).fetchone()[0]
                qualified = qualified and bars == 4320 and quotes / 4320 >= REQUIRED_UPTIME
        self._qualification_snapshot = {
            "qualified_72h": bool(qualified),
            "asof_ms": current_ms,
            "observed_seconds": observed,
            "healthy_seconds": healthy,
            "uptime_fraction": uptime,
        }

    async def run(
        self, run_seconds: float | None = None, *, stop_event: asyncio.Event | None = None
    ) -> dict:
        if run_seconds is not None and run_seconds <= 0:
            raise ValueError("run_seconds must be positive")
        stop = stop_event if stop_event is not None else asyncio.Event()
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, stop.set)
        self.session_id = self.db.execute(
            "INSERT INTO sessions(started_ms,state,endpoint) VALUES(?,'RUNNING',?)",
            (now_ms(), STREAM_URL),
        ).lastrowid
        self.db.commit()
        self.event("start", {"run_seconds": run_seconds})
        deadline = time.monotonic() + run_seconds if run_seconds is not None else math.inf
        attempts = 0
        last_maintenance = -math.inf
        last_clock_sync = -math.inf
        final_state = "STOPPED"

        async def maintenance(client: httpx.AsyncClient) -> None:
            nonlocal last_maintenance, last_clock_sync
            while not stop.is_set() and time.monotonic() < deadline:
                self.flush_quotes()
                self._heartbeat()
                if (
                    self._clock_offset is None
                    or abs(self._clock_offset) > 5_000
                    or time.monotonic() - last_clock_sync >= 3600
                ):
                    try:
                        await self.sync_clock(client)
                        last_clock_sync = time.monotonic()
                    except httpx.HTTPError as exc:
                        self._clock_offset = None
                        self.event("clock_sync_error", str(exc))
                if (
                    self._clock_offset is not None
                    and abs(self._clock_offset) <= 5_000
                    and time.monotonic() - last_maintenance >= 60
                ):
                    self.detect_gaps()
                    try:
                        await self.repair(client)
                    except (httpx.HTTPError, ValueError) as exc:
                        self.event("repair_error", str(exc))
                    last_maintenance = time.monotonic()
                try:
                    await asyncio.wait_for(
                        stop.wait(), min(HEARTBEAT_SECONDS, max(0.01, deadline - time.monotonic()))
                    )
                except TimeoutError:
                    pass

        async def budgets() -> None:
            while not stop.is_set() and time.monotonic() < deadline:
                try:
                    await asyncio.wait_for(
                        stop.wait(),
                        min(FULL_DISK_REFRESH_SECONDS, max(0.01, deadline - time.monotonic())),
                    )
                except TimeoutError:
                    if time.monotonic() < deadline:
                        await self._refresh_disk_budget()

        try:
            async with httpx.AsyncClient(timeout=10, follow_redirects=False) as client:
                task = asyncio.create_task(maintenance(client))
                budget_task = asyncio.create_task(budgets())
                try:
                    while not stop.is_set() and time.monotonic() < deadline:
                        self.guard()
                        if task.done():
                            task.result()
                            break
                        if budget_task.done():
                            budget_task.result()
                        try:
                            self.event("connect_attempt", {"attempt": attempts + 1})
                            async with websockets.connect(
                                STREAM_URL,
                                open_timeout=10,
                                close_timeout=5,
                                ping_interval=None,
                                max_size=65536,
                                max_queue=1024,
                            ) as ws:
                                self._connected = True
                                self.event("connected", {"endpoint": STREAM_URL})
                                connected_at = time.monotonic()
                                while not stop.is_set() and time.monotonic() < deadline:
                                    if task.done():
                                        task.result()
                                        break
                                    if budget_task.done():
                                        budget_task.result()
                                    if time.monotonic() - connected_at >= ROTATE_SECONDS:
                                        self.event("rotate_24h", "23h50m proactive rotation")
                                        self._interval_fault = True
                                        self.flush_quotes(partial=True)
                                        break
                                    try:
                                        message = await asyncio.wait_for(
                                            ws.recv(),
                                            min(5, max(0.01, deadline - time.monotonic())),
                                        )
                                    except TimeoutError:
                                        if all(
                                            now_ms() - self.last_kline_received.get(s, 0) > 20_000
                                            for s in SYMBOLS
                                        ):
                                            raise ConnectionError(
                                                "No fresh kline for 20s"
                                            ) from None
                                        continue
                                    self.handle_message(json.loads(message), now_ms())
                                    if time.monotonic() - connected_at > 30 and any(
                                        now_ms() - self.last_kline_received.get(s, 0) > 20_000
                                        for s in SYMBOLS
                                    ):
                                        raise ConnectionError("One stale symbol kline for 20s")
                                    if time.monotonic() - connected_at > 60:
                                        attempts = 0
                                self._connected = False
                                self.event("disconnected", "rotation, stop or deadline")
                        except CollectorStopped:
                            raise
                        except (
                            OSError,
                            websockets.WebSocketException,
                            ConnectionError,
                            ValueError,
                            KeyError,
                            TypeError,
                            json.JSONDecodeError,
                        ) as exc:
                            self._connected = False
                            self._interval_fault = True
                            self.flush_quotes(partial=True)
                            self.event(
                                "disconnect_error",
                                {"type": type(exc).__name__, "message": str(exc)},
                            )
                            self.db.execute(
                                "UPDATE sessions SET last_error=? WHERE id=?",
                                (str(exc), self.session_id),
                            )
                            self.db.commit()
                            attempts += 1
                            delay = min(60.0, float(2 ** min(attempts - 1, 6)))
                            try:
                                await asyncio.wait_for(
                                    stop.wait(), min(delay, max(0.01, deadline - time.monotonic()))
                                )
                            except TimeoutError:
                                pass
                finally:
                    task.cancel()
                    budget_task.cancel()
                    with contextlib.suppress(asyncio.CancelledError):
                        await task
                    with contextlib.suppress(asyncio.CancelledError):
                        await budget_task
        except CollectorStopped as exc:
            final_state = {"disk": "DISK_STOP", "callback": "CALLBACK_STOP"}.get(
                self._fatal_kind, "GUARD_STOP"
            )
            self._fatal = str(exc)
            self.event("fatal_stop", str(exc))
        except BaseException as exc:
            final_state = "ERROR"
            self.event("fatal_error", {"type": type(exc).__name__, "message": str(exc)})
            raise
        finally:
            self._connected = False
            self.flush_quotes(partial=True)
            self.db.execute(
                "UPDATE sessions SET state=?,ended_ms=?,"
                "last_error=COALESCE(?,last_error) WHERE id=?",
                (final_state, now_ms(), self._fatal, self.session_id),
            )
            self.db.commit()
            self.event("stop", {"state": final_state})
            for sig in (signal.SIGINT, signal.SIGTERM):
                loop.remove_signal_handler(sig)
        # status has a full accounting check, so keep that scan off the loop too.
        return await asyncio.to_thread(status, self.path)


async def collect(
    run_seconds: float | None = None,
    db_path: Path | None = None,
    *,
    tick_callback: Callable[[dict[str, Any]], None] | None = None,
    stop_event: asyncio.Event | None = None,
) -> dict:
    """Single writer; Linux lock released automatically even after process death."""
    target = Path(db_path or default_db())
    if os.environ.get("WSL_DISTRO_NAME") != "hpc_linux":
        raise RuntimeError("Collection must run in the D-hosted hpc_linux WSL distribution")
    if str(target.resolve()).startswith("/mnt/c/"):
        raise ValueError("Collector storage on C: is forbidden")
    # STATE lives in the Linux filesystem of the D-hosted WSL VHD. WAL has native
    # locking there, unlike DrvFs. Only this known location or a D mount is allowed.
    if not target.resolve().is_relative_to(STATE.resolve()) and not str(
        target.resolve()
    ).startswith("/mnt/d/"):
        raise ValueError("Live collection must use D-hosted STATE or /mnt/d")
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.with_suffix(".lock").open("a+") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise RuntimeError("Another collector already holds the database lock") from exc
        initial_disk = await asyncio.to_thread(disk.check, reserve=INTAKE_RESERVE_BYTES)
        collector = Collector(target, initial_disk=initial_disk, tick_callback=tick_callback)
        try:
            return await collector.run(run_seconds, stop_event=stop_event)
        finally:
            collector.close()


def status(db_path: Path | None = None) -> dict:
    """Qualification is conservative data readiness, never a strategy/champion gate."""
    path = Path(db_path or default_db())
    if not path.exists():
        return {
            "database": str(path),
            "state": "NOT_STARTED",
            "qualified_72h": False,
            "reasons": ["No real public-mainnet collection session"],
            "symbols": {},
        }
    db = sqlite3.connect(f"file:{path}?mode=ro", uri=True, timeout=10)
    db.row_factory = sqlite3.Row
    try:
        session_row = db.execute("SELECT * FROM sessions ORDER BY id DESC LIMIT 1").fetchone()
        session = dict(session_row) if session_row else None
        pending = db.execute("SELECT COUNT(*) FROM gaps WHERE repaired_ms IS NULL").fetchone()[0]
        repaired = db.execute("SELECT COUNT(*) FROM gaps WHERE repaired_ms IS NOT NULL").fetchone()[
            0
        ]
        report: dict[str, Any] = {
            "database": str(path),
            "state": session["state"] if session else "NO_SESSION",
            "qualified_72h": False,
            "scope": "read_only_mainnet_data_readiness",
            "session": session,
            "unresolved_gaps": pending,
            "repaired_gaps": repaired,
            "symbols": {},
            "reasons": [],
        }
        observed = session.get("observed_seconds", 0) if session else 0
        healthy = session["healthy_seconds"] if session else 0
        report["observed_seconds"] = observed
        report["healthy_seconds"] = healthy
        report["downtime_seconds"] = max(0, observed - healthy)
        report["uptime_fraction"] = min(1, healthy / observed) if observed > 0 else 0
        report["required_uptime_fraction"] = REQUIRED_UPTIME
        report["clock_incidents"] = {
            row["kind"]: row["count"]
            for row in db.execute(
                "SELECT kind,COUNT(*) count FROM events WHERE session_id=? "
                "AND kind IN ('clock_jump','clock_unhealthy','clock_sync_error') GROUP BY kind",
                (session["id"] if session else None,),
            )
        }
        report["clock_incident_count"] = sum(report["clock_incidents"].values())
        report["planned_rotations"] = db.execute(
            "SELECT COUNT(*) FROM events WHERE session_id=? AND kind='rotate_24h'",
            (session["id"] if session else None,),
        ).fetchone()[0]
        current = now_ms()
        last_minute = current // MINUTE_MS * MINUTE_MS - MINUTE_MS
        first_minute = last_minute - (4320 - 1) * MINUTE_MS
        reasons = report["reasons"]
        if not session or session["state"] != "RUNNING":
            reasons.append("No running real collection session")
        if not session or (
            session["heartbeat_ms"] is None or current - session["heartbeat_ms"] > 45_000
        ):
            reasons.append("Collector heartbeat is absent or stale")
        if observed < REQUIRED_SECONDS:
            reasons.append("Fewer than 72 real monotonic observation hours")
        if report["uptime_fraction"] < REQUIRED_UPTIME:
            reasons.append("Healthy observed uptime is below 99.9%")
        if not session or (
            session["clock_offset_ms"] is None or abs(session["clock_offset_ms"]) > 5_000
        ):
            reasons.append("Exchange/local clock synchronization is unhealthy")
        if pending:
            reasons.append("Unresolved recorded candle gaps")
        for symbol in SYMBOLS:
            counts = db.execute(
                "SELECT COUNT(*) total,SUM(source='rest') repairs,"
                "MIN(open_ms) first_open_ms,MAX(open_ms) last_open_ms,"
                "MAX(websocket_received_ms) last_websocket_received_ms "
                "FROM closed_bars WHERE symbol=?",
                (symbol,),
            ).fetchone()
            window = db.execute(
                "SELECT COUNT(*) FROM closed_bars WHERE symbol=? AND open_ms BETWEEN ? AND ?",
                (symbol, first_minute, last_minute),
            ).fetchone()[0]
            quote_count = db.execute(
                "SELECT COUNT(*) FROM quote_minutes WHERE symbol=? "
                "AND minute_ms BETWEEN ? AND ? AND partial=0",
                (symbol, first_minute, last_minute),
            ).fetchone()[0]
            all_quotes = db.execute(
                "SELECT COUNT(*) FROM quote_minutes WHERE symbol=? AND minute_ms BETWEEN ? AND ?",
                (symbol, first_minute, last_minute),
            ).fetchone()[0]
            report["symbols"][symbol] = {
                **dict(counts),
                "bars_in_last_72h": window,
                "complete_quote_minutes_in_last_72h": quote_count,
                "partial_quote_minutes_in_last_72h": all_quotes - quote_count,
                "missing_quote_minutes_in_last_72h": 4320 - all_quotes,
                "quote_coverage_fraction": quote_count / 4320,
            }
            if window != 4320:
                reasons.append(f"{symbol}: missing closed candles in the latest 72h window")
            if quote_count / 4320 < REQUIRED_UPTIME:
                reasons.append(f"{symbol}: complete quote minute coverage is below 99.9%")
            if (
                counts["last_websocket_received_ms"] is None
                or current - counts["last_websocket_received_ms"] > 90_000
            ):
                reasons.append(f"{symbol}: no fresh genuinely received closed WS candle")
        try:
            report["disk"] = disk.check(reserve=INTAKE_RESERVE_BYTES)
        except Exception as exc:
            reasons.append(f"Disk guard rejects intake: {exc}")
        report["qualified_72h"] = not reasons
        return report
    finally:
        db.close()
