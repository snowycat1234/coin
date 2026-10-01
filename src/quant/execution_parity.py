"""Independent execution V2 acceptance; synthetic checks never confer alpha status."""

from __future__ import annotations

import hashlib
import json
import tempfile
from contextlib import nullcontext
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

import numpy as np
import polars as pl

from .backtest import BacktestConfig, baseline_targets, run_backtest
from .collector import Collector
from .execution_contract import ExecutionContractV2
from .operations import date_us, frame_digest
from .paths import ROOT, STATE
from .shadow import DAY_MS, HOUR_MS, MINUTE_MS, SYMBOLS, Quote, ShadowConfig
from .shadow_v2 import ShadowEngineV2


def _records(engine, kind):
    return [json.loads(row[0]) for row in engine.db.execute(
        "SELECT payload FROM records WHERE kind=? ORDER BY seq", (kind,))]


class _ScriptedSignals(ShadowEngineV2):
    """Inject the *same* raw signal into both executors; risk/fills stay unchanged."""

    def __init__(self, *args, signal_plan, minimum_hold_minutes=0, force_exit=False,
                 risk_zero_hours=(), **kwargs):
        self.signal_plan = signal_plan
        self.minimum_hold_minutes = minimum_hold_minutes
        self.force_exit = force_exit
        self.risk_zero_hours = frozenset(risk_zero_hours)
        super().__init__(*args, **kwargs)

    def _risk_weights(self, raw, now):
        if now // HOUR_MS * HOUR_MS in self.risk_zero_hours:
            return dict.fromkeys(SYMBOLS, 0.0), "RISK_WARMUP"
        return super()._risk_weights(raw, now)

    def _order_policy(self, symbol, raw, weights):
        return {"minimum_hold_minutes": self.minimum_hold_minutes,
                "risk_forced_exit": self.force_exit and raw[symbol] == 0}

    def _hour_weights(self, end, now):
        value = self.signal_plan[end]
        raw = value.copy() if isinstance(value, dict) else dict.fromkeys(SYMBOLS, value)
        return (raw, True,
                {"source": "synthetic_shared_raw_signal", "available_us": end * 1000})


def hold_repair_case(name: str) -> dict:
    """Independent historical/paper proof for actual-fill hold and risk overrides.

    These small artificial paths use no market data or model fitting. Financial
    cash/quantities/cycle accounting must agree; live receipt is 100 ms later and
    can legitimately postpone an exact first-fill holding boundary by a minute.
    """
    if name not in {"ordinary", "late_partial", "dust_reentry", "risk_reduction",
                    "risk_clear_reentry"}:
        raise ValueError("unknown fixed holding repair case")
    start = date_us("2025-02-01T01:00:00") // 1000
    if name == "risk_reduction":
        start = date_us("2025-02-01T23:00:00") // 1000
    first = start // DAY_MS * DAY_MS - 31 * DAY_MS
    duration = 367 if name == "dust_reentry" else 187
    if name == "risk_clear_reentry":
        duration = 247
    opened = np.arange(first, start + (duration + 1) * MINUTE_MS, MINUTE_MS, dtype=np.int64)
    frames = []
    for j, symbol in enumerate(SYMBOLS):
        base = 100. + j * 20
        prices = np.full(len(opened), base)
        for day in range(31):
            mask = (opened >= first + day * DAY_MS) & (opened < first + (day + 1) * DAY_MS)
            prices[mask] *= 1 + .001 * (-1) ** day
        closes = prices.copy()
        volumes = np.full(len(opened), 1e9)
        if name == "risk_reduction":
            prices[opened >= start + HOUR_MS] *= 2
            closes[opened >= start + HOUR_MS - MINUTE_MS] *= 2
        if name in {"late_partial", "dust_reentry"}:
            offset = 0 if name == "late_partial" else 180
            volumes[(opened >= start + offset * MINUTE_MS)
                    & (opened < start + (offset + 4) * MINUTE_MS)] = 0
            if name == "late_partial":
                volumes[opened == start + 4 * MINUTE_MS] = 20_000
        if name == "dust_reentry" and symbol == "BTCUSDT":
            volumes[opened == start + 120 * MINUTE_MS] = 2_990_000
        frames.append(pl.DataFrame({"symbol": [symbol] * len(opened),
                                   "open_us": opened * 1000, "open": prices, "close": closes,
                                   "quote_volume": volumes}))
    minutes = pl.concat(frames)
    hours = (0, 1, 2, 3, 4, 5, 6) if name == "dust_reentry" else (0, 1, 2, 3)
    if name == "risk_clear_reentry":
        hours = (0, 1, 2, 3, 4)
    alpha = (.30, .30, 0., .30, .30, 0., 0.) if name == "dust_reentry" else (
        (.30,) * 4 if name == "risk_reduction" else (.30, .30, 0., 0.)
    )
    if name == "risk_clear_reentry":
        alpha = (.30, .30, .30, 0., 0.)
    plan = {start + h * HOUR_MS: {"BTCUSDT": weight, "ETHUSDT": 0.}
            for h, weight in zip(hours, alpha, strict=True)}
    targets = pl.DataFrame([{"available_us": timestamp * 1000, "symbol": symbol,
                             "target_weight": raw[symbol], "minimum_hold_minutes": 120,
                             "risk_forced_exit": False}
                            for timestamp, raw in plan.items() for symbol in SYMBOLS])
    bars = targets.select("symbol", "available_us").with_columns(
        pl.col("available_us").alias("close_us"))
    # Inject an unavailable covariance for one decision in both engines to test
    # a complete risk liquidation without changing the continuously long intent.
    # This is an explicit fault fixture, not a claim about observed market risk.
    risk_zero_hours = (start + HOUR_MS,) if name == "risk_clear_reentry" else ()
    fault = (patch("quant.backtest._daily_covariances", return_value=(
        np.array([start, start + HOUR_MS, start + 2 * HOUR_MS]) * 1000,
        [np.zeros((2, 2)), None, np.zeros((2, 2))],
    )) if risk_zero_hours else nullcontext())
    with fault:
        historical = run_backtest(bars, minutes, targets, BacktestConfig(
            start_us=start * 1000, end_us=(start + duration * MINUTE_MS) * 1000,
        ))
    with tempfile.TemporaryDirectory(prefix="hold-repair-v2-", dir=STATE) as directory:
        source = Collector(Path(directory) / "source.sqlite3",
                           disk_check=lambda **kwargs: {"status": "OK"})
        engine = None
        try:
            rows = []
            for row in minutes.iter_rows(named=True):
                t, price, close = row["open_us"] // 1000, str(row["open"]), str(row["close"])
                rows.append((row["symbol"], t, t + MINUTE_MS - 1, price, max(price, close),
                             min(price, close), close, "100000", str(row["quote_volume"]),
                             100, t + MINUTE_MS, t + MINUTE_MS + 1, "websocket",
                             t + MINUTE_MS + 1, 1))
            source.db.executemany(
                "INSERT INTO closed_bars VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", rows,
            )
            source.db.commit()
            engine = _ScriptedSignals(
                source.path, Path(directory) / "paper.sqlite3", signal_plan=plan,
                minimum_hold_minutes=120, risk_zero_hours=risk_zero_hours, config=ShadowConfig(
                    version="hold_repair_v2_synthetic", mode="engineering_simulation",
                ), started_ms=start - 1, disk_check=lambda **kwargs: {"status": "OK"},
            )
            restart_verified = False
            index = (start - first) // MINUTE_MS
            for i in range(duration):
                now = start + i * MINUTE_MS + 100
                if i == (240 if name == "dust_reentry" else 60):
                    prior = json.loads(json.dumps(engine.state))
                    engine.close()
                    engine = _ScriptedSignals(
                        source.path, Path(directory) / "paper.sqlite3", signal_plan=plan,
                        minimum_hold_minutes=120, risk_zero_hours=risk_zero_hours,
                        config=ShadowConfig(
                            version="hold_repair_v2_synthetic", mode="engineering_simulation",
                        ), disk_check=lambda **kwargs: {"status": "OK"},
                    )
                    assert engine.state["alpha_holding"] == prior["alpha_holding"]
                    assert engine.state["accounts"] == prior["accounts"]
                    restart_verified = True
                quote_list = []
                for symbol, asset in zip(SYMBOLS, frames, strict=True):
                    price = float(asset["open"][index + i])
                    quote_list.append(Quote(symbol, price * .9999, price * 1.0001, now, i + 1))
                if now // HOUR_MS * HOUR_MS not in plan:
                    engine.state["last_signal_hour"] = now // HOUR_MS * HOUR_MS
                health = {"state": "RUNNING", "healthy": True, "qualified_72h": True,
                          "heartbeat_ms": now, "clock_offset_ms": 0, "unresolved_gaps": 0,
                          "disk": {"status": "OK"}}
                engine.process_tick(now, health, quote_list)
            fills = _records(engine, "fill")
            trades = historical.trades.to_dicts()
            assert len(fills) == len(trades) and fills
            for live, old in zip(fills, trades, strict=True):
                assert live["side"] == old["side"] and live["symbol"] == old["symbol"]
                assert live["quote_received_ms"] // MINUTE_MS == old["execution_us"] // 60_000_000
                for lhs, rhs in (("quantity", "quantity"), ("fee", "fee"), ("price", "fill_price")):
                    assert np.isclose(live[lhs], old[rhs], atol=1e-8, rtol=1e-11)
            account = engine.state["accounts"]["B2"]
            assert np.isclose(account["cash"], historical.daily_nav["cash"][-1], atol=1e-8)
            assert all(np.isclose(account["positions"][s], historical.summary["open_positions"][s],
                                  atol=1e-10) for s in SYMBOLS)
            buys = [fill for fill in fills if fill["side"] == "buy"]
            sells = [fill for fill in fills if fill["side"] == "sell"]
            assert buys and sells
            hold = engine.state["alpha_holding"]["BTCUSDT"]
            first_elapsed = sells[0]["quote_received_ms"] - buys[0]["quote_received_ms"]
            if name == "risk_reduction":
                assert first_elapsed < 120 * MINUTE_MS
                assert sells[0]["quote_received_ms"] == start + 61 * MINUTE_MS + 100
            elif name == "risk_clear_reentry":
                assert sells[0]["quote_received_ms"] == start + 61 * MINUTE_MS + 100
                assert buys[1]["quote_received_ms"] == start + 121 * MINUTE_MS + 100
                assert sells[1]["quote_received_ms"] == start + 241 * MINUTE_MS + 100
                assert hold["first_fill_ms"] == buys[1]["quote_received_ms"]
                assert historical.summary["round_trip_count"] == 2
                assert len(_records(engine, "round_trip")) == 2
            elif name == "dust_reentry":
                second_buy = next(f for f in buys
                                  if f["quote_received_ms"] > start + 180 * MINUTE_MS)
                second_sell = next(f for f in sells
                                   if f["quote_received_ms"] > second_buy["quote_received_ms"])
                assert second_buy["quote_received_ms"] == start + 185 * MINUTE_MS + 100
                assert second_sell["quote_received_ms"] == start + 305 * MINUTE_MS + 100
                assert (second_sell["quote_received_ms"] - second_buy["quote_received_ms"]
                        >= 120 * MINUTE_MS)
                assert account["cycles"]["BTCUSDT"]["entry_ms"] == buys[0]["quote_received_ms"]
                # Dust did not falsely close the first cycle. The final complete
                # sale closes exactly one continuous financial cycle, not two.
                assert historical.summary["round_trip_count"] == 1
                assert len(_records(engine, "round_trip")) == 1
            else:
                assert first_elapsed >= 120 * MINUTE_MS
                assert hold["first_fill_ms"] == buys[0]["quote_received_ms"]
            return {"pass": True, "name": name, "scope": "SYNTHETIC_ENGINEERING_ONLY",
                    "fills": len(fills), "restart_verified": restart_verified,
                    "first_buy_ms": buys[0]["quote_received_ms"],
                    "first_sell_ms": sells[0]["quote_received_ms"],
                    "holding_anchor_ms": hold["first_fill_ms"],
                    "financial_cycle_entry_ms": account["cycles"]["BTCUSDT"]["entry_ms"],
                    "round_trip_count": historical.summary["round_trip_count"],
                    "cash": account["cash"], "positions": account["positions"].copy()}
        finally:
            if engine is not None:
                engine.close()
            source.close()


def hold_repair_cases() -> list[dict]:
    """Public acceptance entrypoint, no production data or model fitting."""
    return [hold_repair_case(name) for name in (
        "ordinary", "late_partial", "dust_reentry", "risk_reduction", "risk_clear_reentry",
    )]


def cross_engine_parity(*, partial: bool = False, fee_multiplier: int = 1,
                        slippage_multiplier: int = 1, minimum_hold_minutes: int = 0,
                        force_exit: bool = False) -> dict:
    """Same signals, risk history, prices and capacity; assert actual financial parity."""
    start = date_us("2025-02-01T01:00:00") // 1000
    first = start - 31 * DAY_MS - HOUR_MS
    duration = 185 if minimum_hold_minutes else 125
    count = (start - first) // MINUTE_MS + duration + 1
    opened = first + np.arange(count, dtype=np.int64) * MINUTE_MS
    frames = []
    for j, symbol in enumerate(SYMBOLS):
        prices = 100 + j * 20 + np.arange(count) * (0.00002 + j * 0.00001)
        volume = np.full(count, 15_000.0 if partial else 100_000_000.0)
        frames.append(pl.DataFrame({
            "symbol": [symbol] * count, "open_us": opened * 1000,
            "open": prices, "close": prices, "quote_volume": volume,
        }))
    minutes = pl.concat(frames)
    decision_times = ((start, start + HOUR_MS, start + 2 * HOUR_MS)
                      if minimum_hold_minutes else (start, start + HOUR_MS))
    signal_weights = (0.30, 0.0, 0.0) if minimum_hold_minutes else (0.30, 0.0)
    targets = pl.DataFrame([
        {"available_us": timestamp * 1000, "symbol": symbol,
         "target_weight": weight}
        for timestamp, weight in zip(decision_times, signal_weights, strict=True)
        for symbol in SYMBOLS
    ]).with_columns(pl.lit(minimum_hold_minutes).alias("minimum_hold_minutes"),
                    (pl.col("target_weight").eq(0) & pl.lit(force_exit)).alias("risk_forced_exit"))
    bars = targets.select("symbol", "available_us").with_columns(
        pl.col("available_us").alias("close_us"))
    config = BacktestConfig(
        start_us=start * 1000, end_us=(start + duration * MINUTE_MS) * 1000,
        fee_multiplier=fee_multiplier, slippage_multiplier=slippage_multiplier,
    )
    historical = run_backtest(bars, minutes, targets, config)
    STATE.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="execution-v2-parity-", dir=STATE) as folder:
        source = Collector(Path(folder) / "source.sqlite3",
                           disk_check=lambda **kwargs: {"status": "OK"})
        try:
            def rows():
                for row in minutes.iter_rows(named=True):
                    timestamp = row["open_us"] // 1000
                    price = str(row["open"])
                    yield (row["symbol"], timestamp, timestamp + MINUTE_MS - 1,
                           price, price, price, price, "100000", str(row["quote_volume"]),
                           100, timestamp + MINUTE_MS, timestamp + MINUTE_MS + 1,
                           "websocket", timestamp + MINUTE_MS + 1, 1)
            source.db.executemany("INSERT INTO closed_bars VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                                  rows())
            source.db.commit()
            engine = _ScriptedSignals(
                source.path, Path(folder) / "paper.sqlite3",
                signal_plan=dict(zip(decision_times, signal_weights, strict=True)),
                minimum_hold_minutes=minimum_hold_minutes, force_exit=force_exit,
                config=ShadowConfig(
                    version="execution_v2_synthetic_parity", mode="engineering_simulation",
                    fee_bps=10 * fee_multiplier, extra_slippage_bps=4 * slippage_multiplier,
                ), started_ms=start - 1, disk_check=lambda **kwargs: {"status": "OK"},
            )
            try:
                lookups = dict(zip(SYMBOLS, frames, strict=True))
                for i in range(duration):
                    timestamp = start + i * MINUTE_MS + 100
                    quote_list = []
                    for symbol in SYMBOLS:
                        asset = lookups[symbol]
                        price = float(asset["open"][(start - first) // MINUTE_MS + i])
                        quote_list.append(Quote(symbol, price * (1 - 0.0001),
                                                price * (1 + 0.0001), timestamp, i + 1))
                    health = {"state": "RUNNING", "healthy": True, "qualified_72h": True,
                              "heartbeat_ms": timestamp, "clock_offset_ms": 0,
                              "unresolved_gaps": 0, "disk": {"status": "OK"}}
                    # Stop injecting signals after the prescribed pair; fill pending orders.
                    if timestamp // HOUR_MS * HOUR_MS not in engine.signal_plan:
                        engine.state["last_signal_hour"] = timestamp // HOUR_MS * HOUR_MS
                    engine.process_tick(timestamp, health, quote_list)
                fills, decisions, orders = (_records(engine, name)
                                             for name in ("fill", "decision", "order"))
                trades = historical.trades.to_dicts()
                if len(fills) != len(trades) or not fills:
                    raise AssertionError(
                        f"fill count differs: live={len(fills)}, history={len(trades)}")
                for live, old in zip(fills, trades, strict=True):
                    assert live["symbol"] == old["symbol"] and live["side"] == old["side"]
                    assert live["signal_us"] == old["signal_us"]
                    assert (live["quote_received_ms"] // MINUTE_MS
                            == old["execution_us"] // 60_000_000)
                    assert live["capacity_bar_open_ms"] * 1000 == old["capacity_open_us"]
                    assert live["quote_received_ms"] * 1000 >= live["eligible_us"]
                    for live_key, old_key in (("quantity", "quantity"), ("mid", "mid_price"),
                                              ("price", "fill_price"), ("fee", "fee"),
                                              ("execution_cost", "execution_cost"),
                                              ("capacity_limit", "capacity")):
                        if not np.isclose(live[live_key], old[old_key], rtol=1e-11, atol=1e-8):
                            raise AssertionError(
                                f"{live_key} differs: {live[live_key]} / {old[old_key]}")
                account = engine.state["accounts"]["B2"]
                assert np.isclose(account["cash"], historical.daily_nav["cash"][-1], atol=1e-8)
                for symbol in SYMBOLS:
                    assert np.isclose(account["positions"][symbol],
                                      historical.summary["open_positions"][symbol], atol=1e-10)
                for order in orders:
                    assert (order["not_before_ms"] * 1000
                            == ExecutionContractV2().earliest_execution_us(order["decision_us"]))
                    assert order["expires_ms"] * 1000 == ExecutionContractV2().expiry_us(
                        order["decision_us"])
                first_weights = decisions[0]["target_weights"]
                for trade in trades[:2]:
                    assert np.isclose(first_weights[trade["symbol"]], trade["target_weight"],
                                      atol=1e-12)
                if minimum_hold_minutes and not force_exit:
                    first_fills = {}
                    for fill in fills:
                        if fill["side"] == "buy":
                            first_fills.setdefault(fill["symbol"], fill["quote_received_ms"])
                        else:
                            assert (fill["quote_received_ms"] - first_fills[fill["symbol"]]
                                    >= minimum_hold_minutes * MINUTE_MS)
                return {"pass": True, "scope": "SYNTHETIC_ENGINEERING_ONLY",
                        "minimum_hold_minutes": minimum_hold_minutes, "force_exit": force_exit,
                        "partial_capacity": partial, "fee_multiplier": fee_multiplier,
                        "slippage_multiplier": slippage_multiplier,
                        "fills": len(fills),
                        "historical_expired": historical.summary["expired_orders"],
                        "live_expired": len([r for r in _records(engine, "order_event")
                                             if r["status"] == "EXPIRED"]),
                        "signal_us": trades[0]["signal_us"],
                        "first_execution_minute_us": (
                            trades[0]["execution_us"] // 60_000_000 * 60_000_000),
                        "capacity_source_minute_us": trades[0]["capacity_open_us"],
                        "target_weights": first_weights, "final_cash": account["cash"],
                        "final_positions": account["positions"].copy()}
            finally:
                engine.close()
        finally:
            source.close()


def canonical_baselines(progress=lambda event: None) -> dict:
    """A01 B0..B2 rerun. Loads only the development history, never the locked test."""
    from .data import verify_dataset_lock
    from .disk import check

    lock = verify_dataset_lock()
    start, end = date_us("2022-02-01"), date_us("2026-03-01")
    output = ROOT / "reports/generated/P03_EXECUTION_V2"
    if output.exists() and any(output.iterdir()):
        raise RuntimeError("Canonical A01 evidence exists; refusing to overwrite")
    check(reserve=502_000_000)
    files = [ROOT / relative for relative in lock["minute_files"]
             if Path(relative).stem < "2026-03"]
    minutes = (pl.scan_parquet(files).filter(pl.col("valid_day") & (pl.col("open_us") < end))
               .select("symbol", "open_us", "open", "close", "quote_volume")
               .collect(engine="streaming"))
    bar_files = [ROOT / relative for relative in lock["bar_files"]
                 if Path(relative).name == "1h.parquet"]
    bars = (pl.scan_parquet(bar_files).filter(pl.col("available_us") < end)
            .collect(engine="streaming"))
    config = BacktestConfig(start_us=start, end_us=end)
    scenarios = {"base": config, "fee_x2": replace(config, fee_multiplier=2),
                 "slippage_x2": replace(config, slippage_multiplier=2)}
    summaries = {}
    for name in ("B0", "B1", "B2"):
        targets = baseline_targets(bars, name)
        summaries[name] = {}
        for scenario, settings in scenarios.items():
            result = run_backtest(bars, minutes, targets, settings)
            result.write_report(output, f"{name}_{scenario}", disk_checked=True)
            summaries[name][scenario] = result.summary
            progress({"module": "A01", "baseline": name, "scenario": scenario,
                      "total_return": result.summary["total_return"]})
    # Reproducibility uses actual sealed inputs and complete earlier risk warmup.
    replay_end, replay_start = date_us("2024-01-08"), date_us("2024-01-01")
    small_minutes = minutes.filter((pl.col("open_us") >= date_us("2023-11-01"))
                                   & (pl.col("open_us") < replay_end))
    small_bars = bars.filter((pl.col("available_us") >= date_us("2023-11-01"))
                            & (pl.col("available_us") < replay_end))
    target = baseline_targets(small_bars, "B2")
    hashes = []
    for _ in range(3):
        result = run_backtest(small_bars, small_minutes, target,
                             BacktestConfig(start_us=replay_start, end_us=replay_end))
        hashes.append({label: frame_digest(getattr(result, label))
                       for label in ("daily_nav", "trades", "orders", "round_trips")})
    assert all(item == hashes[0] for item in hashes)
    report = {"status": "PASS", "evidence_scope": "DEVELOPMENT_HISTORY",
              "execution_contract_version": "execution_v2",
              "execution_contract_sha256": ExecutionContractV2().digest(),
              "dataset_id": lock["dataset_id"], "start_us": start, "end_us": end,
              "locked_historical_test_read": False, "true_forward_days": 0,
              "baselines": summaries, "reproducibility_runs": 3,
              "reproducibility_sha256": hashes[0]}
    payload = json.dumps(report, indent=2, ensure_ascii=False, allow_nan=False) + "\n"
    (output / "summary.json").write_text(payload, encoding="utf-8")
    return {"status": "PASS", "path": str(output.relative_to(ROOT)),
            "artifact_sha256": hashlib.sha256(payload.encode()).hexdigest(),
            "start_us": start, "end_us": end, "dataset_id": lock["dataset_id"]}


def run_acceptance(progress=lambda event: None) -> dict:
    path = ROOT / "reports/A01_EXECUTION_PARITY_ACCEPTANCE.json"
    if path.exists():
        raise RuntimeError("A01 receipt already exists; preserve original evidence")
    cases = [cross_engine_parity(), cross_engine_parity(partial=True),
             cross_engine_parity(fee_multiplier=2), cross_engine_parity(slippage_multiplier=2)]
    canonical = canonical_baselines(progress)
    legacy = json.loads((ROOT / "reports/LEGACY_EXECUTION_V1_INDEX.json").read_text())
    # The index is evidence, not permission to rewrite the original source reports.
    for relative, digest in legacy["reports"].items():
        if hashlib.sha256((ROOT / relative).read_bytes()).hexdigest() != digest:
            raise RuntimeError(f"Legacy evidence changed: {relative}")
    report = {"status": "PASS", "execution_contract_version": "execution_v2",
              "execution_contract_sha256": ExecutionContractV2().digest(),
              "cross_engine_parity": {"pass": True, "cases": cases},
              "canonical_baselines": canonical, "new_alpha_training_allowed": True,
              "alpha_candidate": False, "true_forward_days": 0,
              "locked_historical_test_read": False,
              "legacy_index_sha256": hashlib.sha256(
                  (ROOT / "reports/LEGACY_EXECUTION_V1_INDEX.json").read_bytes()).hexdigest(),
              "legacy_report_count": len(legacy["reports"]),
              "source_hashes": {"src/quant/" + name: hashlib.sha256(
                  (ROOT / "src/quant" / name).read_bytes()).hexdigest() for name in (
                  "backtest.py", "execution_contract.py", "shadow_v2.py", "shadow.py",
                  "concurrent_budget.py", "execution_parity.py")}}
    path.write_text(json.dumps(report, indent=2, ensure_ascii=False, allow_nan=False) + "\n",
                    encoding="utf-8")
    return report
