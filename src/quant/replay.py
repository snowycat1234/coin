"""Historical protocol replay of the frozen paper engine, never forward evidence.

Only isolated laboratory databases receive synthetic WS-shaped events. Original
Parquets and real collector/shadow databases are never changed. OHLC opens are
price proxies; these experiments make no claim about a real order book or fills.
"""

from __future__ import annotations

import hashlib
import json
import math
import resource
import shutil
import sqlite3
import time
from dataclasses import asdict
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Callable

import numpy as np
import polars as pl

from . import disk
from .metrics import daily_metrics
from .paths import ROOT, STATE, VHD
from .shadow import (
    DAY_MS,
    HOUR_MS,
    IMPLEMENTATION_HASH,
    MINUTE_MS,
    SYMBOLS,
    Quote,
    ShadowConfig,
    ShadowEngine,
    read_forward_evidence,
)

RESERVATION = 1_000_000_000
HOLDOUT_START = "2026-03-01"
CRITICAL = {
    "start", "decision", "order", "order_event", "fill", "position", "round_trip", "incident",
    "nav",
}
SOURCE_COLUMNS = [
    "open_us", "close_us", "open", "high", "low", "close", "volume", "quote_volume",
    "trade_count", "valid_day",
]


def _json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def _sha(path: Path) -> str:
    result = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            result.update(chunk)
    return result.hexdigest()


def _ms(value: str) -> int:
    return int(datetime.strptime(value, "%Y-%m-%d").replace(tzinfo=UTC).timestamp() * 1000)


def _date(value: int) -> str:
    return datetime.fromtimestamp(value / 1000, UTC).date().isoformat()


def _months(start: int, end: int):
    current = datetime.fromtimestamp(start / 1000, UTC).replace(day=1)
    while current.timestamp() * 1000 < end:
        following = (current.replace(day=28) + timedelta(days=4)).replace(day=1)
        yield current.strftime("%Y-%m"), max(start, int(current.timestamp() * 1000)), min(
            end, int(following.timestamp() * 1000)
        )
        current = following


class ReplayBudget:
    """One reserved lease for all isolated databases; periodic physical growth checks."""

    def __init__(self, directory: Path, output: Path, ledger: dict):
        self.directory, self.output, self.ledger = directory, output, ledger
        self.calls = 0
        self.initial_native = self.bytes(directory)
        self.initial_report = self.bytes(output)
        self.initial_vhd = VHD.stat().st_size

    @staticmethod
    def bytes(path: Path) -> int:
        return sum(p.stat().st_size for p in path.rglob("*") if p.is_file()) if path.exists() else 0

    def guard(self, *, force: bool = False) -> None:
        self.calls += 1
        # No isolated writer can create >1 GB between checks: each tick appends
        # bounded two-asset state; the full reserved lease is checked before writing.
        if not force and self.calls % 60:
            return
        logical = self.bytes(self.directory) - self.initial_native
        reports = self.bytes(self.output) - self.initial_report
        growth = max(logical, VHD.stat().st_size - self.initial_vhd) + reports
        if logical + reports >= RESERVATION:
            raise RuntimeError("historical replay 1 GB writer reservation exhausted")
        if "total_bytes" in self.ledger:
            disk.enforce(
                self.ledger["total_bytes"] + max(0, growth),
                max(0, RESERVATION - logical - reports),
                shutil.disk_usage(ROOT).free,
            )


class HistoricalShadowAdapter(ShadowEngine):
    """Replay-only passive audit compaction, with unchanged financial engine methods.

    Every financial/health record is retained and checkpointed in its transaction.
    Idle heartbeat/checkpoint snapshots are hourly. Minute process_tick calls and
    all frozen source, signal, risk, execution and daily NAV logic remain intact.
    This adapter is forbidden for live_paper; its own SHA is in the replay manifest.
    """

    def __init__(self, *args, budget: ReplayBudget, **kwargs):
        if kwargs["config"].mode != "engineering_simulation":
            raise ValueError("historical adapter cannot operate a live paper account")
        self.replay_budget, self._critical = budget, False
        self._risk_cache = None
        super().__init__(*args, **kwargs)

    def _risk_weights(self, raw: dict, now: int) -> tuple[dict[str, float], str]:
        # Replay inserts yesterday's final minute before the first daily tick.
        # Received previous-day rows cannot change again during this day; only
        # the covariance is cached, never signal weights or current-day prices.
        day = now // DAY_MS
        if self._risk_cache is None or self._risk_cache[0] != day:
            rows = self.source.execute(
                """WITH days AS (
                    SELECT symbol,open_ms/? AS day,COUNT(*) n,MAX(open_ms) last_open
                    FROM closed_bars WHERE open_ms>=? AND open_ms<? AND received_ms<=?
                    AND source='websocket' GROUP BY symbol,day
                ) SELECT d.symbol,d.day,d.n,b.close FROM days d JOIN closed_bars b
                ON b.symbol=d.symbol AND b.open_ms=d.last_open WHERE d.n=1440""",
                (DAY_MS, (day - 31) * DAY_MS, day * DAY_MS, now),
            ).fetchall()
            values = {(r["symbol"], r["day"]): float(r["close"]) for r in rows}
            returns = [[values[s, d] / values[s, d - 1] - 1 for s in SYMBOLS]
                       for d in range(day - 30, day)
                       if all((s, d) in values and (s, d - 1) in values for s in SYMBOLS)]
            cov = np.atleast_2d(np.cov(np.asarray(returns).T, ddof=1)) * 365 \
                if len(returns) >= 20 else None
            self._risk_cache = day, cov
        cov = self._risk_cache[1]
        if cov is None:
            return dict.fromkeys(SYMBOLS, 0.0), "RISK_WARMUP"
        weights = np.array([raw[s] for s in SYMBOLS])
        if weights.sum() > self.config.gross_max:
            weights *= self.config.gross_max / weights.sum()
        vol = math.sqrt(max(0, float(weights @ cov @ weights)))
        if vol > self.config.annual_vol_target:
            weights *= self.config.annual_vol_target / vol
        reserve_rate = (self.config.fee_bps + self.config.half_spread_floor_bps
                        + self.config.extra_slippage_bps) / 10_000
        weights *= max(0.0, 1 - 2 * self.config.gross_max * reserve_rate)
        return dict(zip(SYMBOLS, map(float, weights), strict=True)), "READY"

    def _guard(self) -> None:
        self.replay_budget.guard()

    def _append(self, now: int, kind: str, payload: dict, key: str) -> None:
        if kind == "heartbeat" and now % HOUR_MS != 500:
            return
        if kind in CRITICAL:
            self._critical = True
        super()._append(now, kind, payload, key)

    def _checkpoint(self, now: int) -> None:
        if self._critical or now % HOUR_MS == 500:
            super()._checkpoint(now)
            self._critical = False


def _open_feed(path: Path) -> sqlite3.Connection:
    db = sqlite3.connect(path)
    db.execute("PRAGMA journal_mode=WAL")
    db.execute("PRAGMA synchronous=NORMAL")
    db.executescript("""
        CREATE TABLE metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL);
        INSERT INTO metadata VALUES('provenance','historical_OHLC_synthetic_protocol_only');
        CREATE TABLE closed_bars (
            symbol TEXT NOT NULL,open_ms INTEGER NOT NULL,close_ms INTEGER NOT NULL,
            open TEXT NOT NULL,high TEXT NOT NULL,low TEXT NOT NULL,close TEXT NOT NULL,
            volume TEXT NOT NULL,quote_volume TEXT NOT NULL,trades INTEGER NOT NULL,
            exchange_event_ms INTEGER,received_ms INTEGER NOT NULL,source TEXT NOT NULL,
            websocket_received_ms INTEGER,session_id INTEGER,PRIMARY KEY(symbol,open_ms)
        );
        CREATE INDEX closed_received ON closed_bars(symbol,source,received_ms);
        CREATE INDEX closed_source_open ON closed_bars(source,open_ms);
    """)
    db.commit()
    return db


def _read_month(root: Path, month: str, begin: int, end: int) -> dict[str, list[dict]]:
    result = {}
    for symbol in SYMBOLS:
        path = root / f"data/normalized/spot/{symbol}/1m/{month}.parquet"
        frame = pl.read_parquet(path, columns=SOURCE_COLUMNS).filter(
            (pl.col("open_us") >= begin * 1000)
            & (pl.col("open_us") < end * 1000)
            & pl.col("valid_day")
        ).sort("open_us")
        if frame["open_us"].n_unique() != frame.height:
            raise RuntimeError("duplicate normalized minute")
        if frame.filter(pl.col("close_us") != pl.col("open_us") + MINUTE_MS * 1000).height:
            raise RuntimeError("nonstandard minute outside quarantined day")
        result[symbol] = frame.to_dicts()
    return result


def _feed_row(symbol: str, row: dict) -> tuple:
    end = row["close_us"] // 1000
    return (
        symbol, row["open_us"] // 1000, end - 1,
        *[str(row[k]) for k in ("open", "high", "low", "close", "volume", "quote_volume")],
        int(row["trade_count"]), end, end + 100, "websocket", end + 100, 0,
    )


def _health(now: int, *, qualified: bool = True) -> dict:
    return {
        "state": "RUNNING", "healthy": True, "qualified_72h": qualified,
        "heartbeat_ms": now, "clock_offset_ms": 0, "unresolved_gaps": 0,
        "disk": {"status": "OK"}, "source": "engineering_simulation_no_real_qualification",
    }


def _verify_inputs(root: Path, begin: int, end: int) -> dict:
    lock = json.loads((root / "state/dataset_lock.json").read_text())
    selected = {}
    for month, _, _ in _months(begin, end):
        for symbol in SYMBOLS:
            relative = f"data/normalized/spot/{symbol}/1m/{month}.parquet"
            expected = lock["minute_files"].get(relative)
            if not expected or _sha(root / relative) != expected:
                raise RuntimeError(f"replay input does not match frozen dataset: {relative}")
            selected[relative] = expected
    return {"dataset_id": lock["dataset_id"], "selected_files": selected}


def _audit_scenario(path: Path, config: ShadowConfig, start: int, end: int) -> dict:
    evidence = read_forward_evidence(path, include_records=False)
    if evidence["mode"] != "engineering_simulation" or evidence["provenance"] != "synthetic":
        raise AssertionError("historical replay acquired live provenance")
    db = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    cash, positions = config.initial_cash, dict.fromkeys(SYMBOLS, 0.0)
    orders, capacity, daily, incidents = {}, {}, {"B0": [], "B2": []}, []
    fees = costs = turnover = 0.0
    fills = trips = decisions = risk_warmup = 0
    first_fill = last_fill = None
    financial_digest = hashlib.sha256()
    last_checkpoint = None
    for received_us, kind, raw in db.execute(
        "SELECT received_us,kind,payload FROM records ORDER BY seq"
    ):
        value = json.loads(raw)
        if kind in CRITICAL:
            financial_digest.update(_json([received_us, kind, value]).encode())
        if kind == "decision":
            decisions += 1
            risk_warmup += value["state"] == "RISK_WARMUP"
            assert received_us > value["hour_end_ms"] * 1000
            assert all(e["last_received_ms"] * 1000 <= received_us
                       for e in value["evidence"].values())
        elif kind == "order":
            orders[value["order_id"]] = value
        elif kind == "fill":
            order = orders[value["order_id"]]
            now = received_us // 1000
            assert value["quote_received_ms"] >= order["not_before_ms"] > order["decision_ms"]
            assert value["quote_received_ms"] <= now
            assert value["capacity_bar_open_ms"] == now // MINUTE_MS * MINUTE_MS - MINUTE_MS
            assert value["capacity_bar_received_ms"] <= value["quote_received_ms"]
            assert math.isclose(value["fee"], value["notional"] * config.fee_bps / 10000)
            assert math.isclose(value["execution_cost"], value["quantity"] * abs(
                value["price"] - value["mid"]
            ))
            step = 0.00001 if value["symbol"] == "BTCUSDT" else 0.0001
            assert abs(value["quantity"] / step - round(value["quantity"] / step)) < 1e-7
            assert value["notional"] >= config.min_notional
            key = (value["symbol"], now // MINUTE_MS)
            capacity[key] = capacity.get(key, 0) + value["notional"]
            assert capacity[key] <= value["capacity_limit"] + 1e-7
            capacity = {k: v for k, v in capacity.items() if k[1] >= key[1] - 1}
            sign = 1 if value["side"] == "buy" else -1
            cash -= sign * value["notional"] + value["fee"]
            positions[value["symbol"]] += sign * value["quantity"]
            assert cash >= -1e-7 and min(positions.values()) >= -1e-10
            fees += value["fee"]
            costs += value["execution_cost"]
            turnover += value["notional"]
            fills += 1
            first_fill = first_fill or now
            last_fill = now
        elif kind == "position":
            assert math.isclose(cash, value["cash"], abs_tol=1e-7)
            assert all(math.isclose(positions[s], value["positions"][s], abs_tol=1e-9)
                       for s in SYMBOLS)
        elif kind == "nav":
            assert math.isclose(value["nav"], value["cash"] + sum(
                value["positions"][s] * value["marks"][s] for s in SYMBOLS
            ), abs_tol=1e-7)
            assert value["source"] == "synthetic"
            daily[value["account"]].append(value)
        elif kind == "round_trip":
            trips += 1
        elif kind == "incident":
            incidents.append({"received_ms": received_us // 1000, **value})
        elif kind == "checkpoint":
            last_checkpoint = value
    db.close()
    assert last_checkpoint is not None
    account = last_checkpoint["accounts"]["B2"]
    assert math.isclose(account["cash"], cash, abs_tol=1e-7)
    assert all(math.isclose(account["positions"][s], positions[s], abs_tol=1e-9) for s in SYMBOLS)
    assert last_checkpoint["healthy_seconds"] == 0, "synthetic minutes gained real healthy credit"
    dates = [_date(d) for d in range(start, end, DAY_MS)]
    for rows in daily.values():
        assert [r["date"] for r in rows] == dates, "UTC day coverage mismatch"
        assert all(r["complete_utc_day"] and r["timely_recorded"] for r in rows)
    assert math.isclose(sum(v["fees"] for v in daily["B2"]), fees, abs_tol=1e-7)
    assert math.isclose(sum(v["execution_costs"] for v in daily["B2"]), costs, abs_tol=1e-7)
    metrics = {
        name: daily_metrics(pl.DataFrame(rows), config.initial_cash) for name, rows in daily.items()
    }
    return {
        "version": evidence["version"], "head_hash": evidence["head_hash"],
        "journal_records": evidence["seq"], "hash_chain_verified": True,
        "triggers_verified": evidence["triggers_verified"],
        "financial_sha256": financial_digest.hexdigest(),
        "fill_count": fills, "round_trip_count": trips, "decision_count": decisions,
        "risk_warmup_decisions": risk_warmup, "first_fill_ms": first_fill,
        "last_fill_ms": last_fill, "cash": cash, "positions": positions,
        "fees": fees, "execution_costs": costs, "notional_turnover": turnover,
        "real_healthy_seconds": 0, "daily_nav": daily, "metrics": metrics, "incidents": incidents,
        "all_days_observable": all(r["daily_risk_observable"] for r in daily["B2"]),
    }


def _run_scenario(
    *, root: Path, directory: Path, name: str, start: int, end: int, warmup: int,
    config: ShadowConfig, budget: ReplayBudget, progress: Callable[[dict], None] | None = None,
    restart_ms: int | None = None, fault: str | None = None,
) -> dict:
    directory.mkdir(parents=True, exist_ok=False)
    feed_path, journal = directory / "feed.sqlite3", directory / "account.sqlite3"
    feed = _open_feed(feed_path)
    engine = None
    wall = time.monotonic()
    prior = {}
    counters = dict.fromkeys(SYMBOLS, 0)
    fault_recorded = False
    restart_verified = False
    try:
        for month, begin, finish in _months(warmup, end):
            rows = _read_month(root, month, begin, finish)
            indexed = {s: {r["open_us"] // 1000: r for r in rows[s]} for s in SYMBOLS}
            # Monthly files are the largest materialized data chunk. Calendar ticks
            # continue through missing/quarantined minutes without forward filling.
            for minute in range(begin, finish, MINUTE_MS):
                for symbol, row in prior.items():
                    feed.execute("INSERT INTO closed_bars VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                                 _feed_row(symbol, row))
                feed.commit()
                current = {s: indexed[s][minute] for s in SYMBOLS if minute in indexed[s]}
                for symbol in current:
                    counters[symbol] += 1
                prior = current
                if minute < start:
                    continue
                now = minute + 500
                if engine is None:
                    engine = HistoricalShadowAdapter(
                        feed_path, journal, config=config, started_ms=start,
                        initial_health=_health(start, qualified=False), initial_disk=budget.ledger,
                        budget=budget,
                    )
                if restart_ms == minute:
                    before = engine.status()
                    engine.close()
                    engine = HistoricalShadowAdapter(
                        feed_path, journal, config=config, started_ms=start,
                        initial_disk=budget.ledger, budget=budget,
                    )
                    restored = engine.status()
                    assert before["cash"] == restored["cash"]
                    assert before["positions"] == restored["positions"]
                    restart_verified = True
                quotes = [
                    Quote(s, float(row["open"]) * .9999, float(row["open"]) * 1.0001,
                          now, minute // MINUTE_MS)
                    for s, row in current.items()
                ]
                health = _health(now)
                if len(current) != len(SYMBOLS):
                    health.update(healthy=False, unresolved_gaps=1)
                injection = start + DAY_MS + HOUR_MS + MINUTE_MS
                if fault and injection <= minute < injection + 2 * MINUTE_MS:
                    fault_recorded = True
                    if fault == "clock":
                        health["clock_offset_ms"] = 22_000
                    elif fault == "stale_quote":
                        quotes = [Quote(q.symbol, q.bid, q.ask, now - 6000, q.update_id)
                                  for q in quotes]
                    elif fault == "gap":
                        health.update(healthy=False, unresolved_gaps=1)
                    else:
                        raise ValueError("unknown replay fault")
                engine.process_tick(now, health, quotes)
                if minute % DAY_MS == 0:
                    feed.execute("DELETE FROM closed_bars WHERE open_ms<?", (minute - 32 * DAY_MS,))
                    feed.commit()
            if progress:
                progress({"scenario": name, "month": month, "through": _date(finish - MINUTE_MS),
                          "seconds": round(time.monotonic() - wall, 1),
                          "records": engine.seq if engine else 0})
            budget.guard(force=True)
            # Release month allocations before opening the next chunk.
            del indexed, rows
        assert engine is not None
        for symbol, row in prior.items():
            feed.execute("INSERT INTO closed_bars VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                         _feed_row(symbol, row))
        feed.commit()
        # Seal the final UTC day without reading any end-date price or generating
        # an extra hour signal. Unfilled goals are explicitly cancelled.
        health = _health(end + 5000)
        health["healthy"] = False
        engine.process_tick(end + 5000, health, [])
        engine.close()
        engine = None
        feed.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        result = _audit_scenario(journal, config, start, end)
        result.update(
            scenario=name, configuration=asdict(config), journal=str(journal),
            feed=str(feed_path), source_minutes_including_warmup=counters,
            elapsed_seconds=time.monotonic() - wall, restart_verified=restart_verified,
            fault_injected=fault_recorded, lab_directory_bytes=budget.bytes(directory),
        )
        if fault:
            assert fault_recorded
            assert any(r["kind"] == "freeze" and r["received_ms"] < end
                       for r in result["incidents"])
            with sqlite3.connect(journal) as db:
                cancelled = db.execute(
                    "SELECT COUNT(*) FROM records WHERE kind='order_event' "
                    "AND json_extract(payload,'$.status')='CANCELLED_HEALTH' "
                    "AND received_us<?", (end * 1000,)
                ).fetchone()[0]
            assert cancelled >= 1, "fault did not cancel the previous minute's goals"
            result["fault_cancelled_orders"] = cancelled
        return result
    finally:
        if engine is not None:
            engine.close()
        feed.close()


def run_historical_replay(
    start: str = "2024-01-01", end: str = "2024-07-01", *, source_root: Path = ROOT,
    output_dir: Path | None = None, state_dir: Path | None = None,
    progress: Callable[[dict], None] | None = None,
) -> dict:
    """Run two identical base replays, cost stresses and isolated fault exercises.

    Dates are full UTC days, end exclusive, >=180 days, before the sealed holdout.
    Returns a JSON-safe report and writes report.json + README.md + scenario NAVs.
    Destinations must be new/empty. Only native D-hosted STATE is accepted for SQL.
    """
    first, last = _ms(start), _ms(end)
    if (last - first) // DAY_MS < 180 or last > _ms(HOLDOUT_START):
        raise ValueError("need >=180 UTC days entirely before the sealed 2026-03 holdout")
    if first < _ms("2022-02-01") or last <= first:
        raise ValueError("need 31 prior complete development days")
    source_root = Path(source_root).resolve()
    output = Path(output_dir or ROOT / f"reports/replay_{start}_{end}").resolve()
    native = Path(state_dir or STATE / f"replay_{start}_{end}").resolve()
    if not str(source_root).startswith("/mnt/d/") or not str(output).startswith("/mnt/d/"):
        raise ValueError("historical source/report storage must stay on D:")
    if not native.is_relative_to(STATE.resolve()) or native == STATE.resolve():
        raise ValueError("isolated replay databases must be a new native STATE subdirectory")
    for destination in (output, native):
        if destination.exists() and any(destination.iterdir()):
            raise FileExistsError(f"replay destination already contains files: {destination}")
    warmup = first - 31 * DAY_MS
    inputs = _verify_inputs(source_root, warmup, last)
    ledger = disk.check(reserve=RESERVATION)
    output.mkdir(parents=True, exist_ok=True)
    native.mkdir(parents=True, exist_ok=True)
    budget = ReplayBudget(native, output, ledger)
    started = time.monotonic()
    scenarios = {}
    restart = first + (last - first) // DAY_MS // 2 * DAY_MS + 14 * HOUR_MS + 30 * MINUTE_MS
    for name, fee, slip in (("base", 10., 4.), ("base_repeat", 10., 4.),
                            ("fee_x2", 20., 4.), ("slippage_x2", 10., 8.)):
        config = ShadowConfig(version="historical_reference_v1", mode="engineering_simulation",
                              fee_bps=fee, extra_slippage_bps=slip)
        scenarios[name] = _run_scenario(
            root=source_root, directory=native / name, name=name, start=first, end=last,
            warmup=warmup, config=config, budget=budget, progress=progress, restart_ms=restart,
        )
        assert scenarios[name]["fill_count"] > 0, "complete replay produced no simulated fills"
    base, repeat = scenarios["base"], scenarios["base_repeat"]
    assert base["head_hash"] == repeat["head_hash"], "deterministic replay journal mismatch"
    assert base["financial_sha256"] == repeat["financial_sha256"]
    assert base["cash"] == repeat["cash"] and base["positions"] == repeat["positions"]
    faults = {}
    for fault in ("clock", "stale_quote", "gap"):
        faults[fault] = _run_scenario(
            root=source_root, directory=native / f"fault_{fault}", name=f"fault_{fault}",
            start=first, end=first + 3 * DAY_MS, warmup=warmup,
            config=ShadowConfig(version="historical_fault_v1", mode="engineering_simulation"),
            budget=budget, progress=progress, fault=fault,
            restart_ms=first + 2 * DAY_MS + 14 * HOUR_MS + 30 * MINUTE_MS,
        )
    budget.guard(force=True)
    for name, result in {**scenarios, **{f"fault_{k}": v for k, v in faults.items()}}.items():
        for account, rows in result["daily_nav"].items():
            pl.DataFrame(rows).write_parquet(output / f"{name}_{account}_daily_nav.parquet")
        result.pop("daily_nav")
    final_disk = disk.check()
    report = {
        "acceptance": "ENGINEERING_REPLAY_PASS", "provenance": "historical_simulation",
        "live_evidence_days": 0, "real_healthy_seconds": 0, "candidate_qualification": False,
        "strategy_role": "B0_cash_B2_reference_only_no_champion", "start_utc": start,
        "end_exclusive_utc": end, "complete_utc_days": (last - first) // DAY_MS,
        "first_nav_date": start, "last_nav_date": _date(last - DAY_MS),
        "warmup_start": _date(warmup), "warmup_in_performance": False,
        "source": inputs, "shadow_implementation_sha256": IMPLEMENTATION_HASH,
        "replay_implementation_sha256": _sha(Path(__file__)),
        "event_order": ("previous close received t+100ms; decision/open proxy t+500ms; "
                        "fill >=next minute"),
        "quotes": "historical 1m open +/-1bp proxy, not observed book or guaranteed execution",
        "audit_adapter": "all financial/health records; hourly passive heartbeats/checkpoints",
        "source_storage": "monthly two-asset Parquet chunks; isolated feed retains 32 days",
        "deterministic_replays": 2, "determinism_verified": True, "restart_ms": restart,
        "scenarios": scenarios, "faults": faults, "elapsed_seconds": time.monotonic() - started,
        "process_peak_rss_bytes": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024,
        "native_output_bytes": budget.bytes(native), "report_output_bytes": budget.bytes(output),
        "disk_before": ledger, "disk_after": final_disk,
        "limitations": ["Historical OHLC cannot establish live liquidity or queue position.",
                        "Synthetic protocol eligibility is not mainnet 72h qualification.",
                        "UTC daily observed NAV drawdown misses intraday adverse excursions.",
                        "Current lot/min-notional snapshot is not historical reconstruction.",
                        "Engineering success does not certify B2 profit or candidate readiness."],
    }
    (output / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    table = "\n".join(
        f"| {name} | {r['fill_count']} | {r['metrics']['B2']['total_return']:.2%} | "
        f"{r['fees']:.4f} | {r['execution_costs']:.4f} |"
        for name, r in scenarios.items() if name != "base_repeat"
    )
    (output / "README.md").write_text(
        f"# 历史完整系统工程演练\n\n工程验收：通过。{start} 至 {end}（不含），"
        f"{report['complete_utc_days']} 个完整 UTC 日。真实前向实测证据：0 天。\n\n"
        "| 场景 | 模拟成交笔数 | B2 期间收益 | 手续费 USDT | 执行成本 USDT |\n"
        "|---|---:|---:|---:|---:|\n" + table + "\n\n"
        "B0 全现金。B2 仅作工程参考；上述收益不构成候选晋级或盈利保障。"
        "报价由分钟开盘价加减 1bp 生成，不能证明真实盘口可成交。\n\n"
        "两次基础回放的完整审计链、费用、现金和数量完全一致；中途重启恢复验收通过。"
        "时钟异常、陈旧报价、未解决缺口在三个独立数据库冻结并撤销未成交目标。"
        "最后六个月封存区间未读取。详细费用、逐日账户和资源证据见 report.json 与逐日 Parquet。\n"
    )
    budget.guard(force=True)
    return report
