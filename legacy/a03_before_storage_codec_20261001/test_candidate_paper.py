import asyncio
import copy
import json
import math
import tempfile
from dataclasses import replace
from pathlib import Path

import numpy as np
import polars as pl
import pytest

from quant.candidate_paper import (
    SCENARIOS,
    CandidateCollector,
    CandidatePaperEngine,
    _new_features,
    create_candidate_pipeline,
    update_features,
)
from quant.collector import Collector
from quant.forward_report import evaluate_forward_snapshot
from quant.holdout import HoldoutDenied
from quant.paths import ROOT, STATE
from quant.research import FEATURE_NAMES, build_features
from quant.shadow import DAY_MS, HOUR_MS, MINUTE_MS, Quote, ShadowConfig, read_forward_evidence

BASE = 1_735_689_600_000
END = BASE + 32 * DAY_MS + HOUR_MS


def guard(**_):
    return {"status": "OK"}


def model(interval="15m"):
    return {
        "interval": interval,
        "configuration": {"interval": interval, "threshold": 0.55},
        "features": list(FEATURE_NAMES),
        "classes": [0, 1],
        "scaler_mean": [0.0] * 10,
        "scaler_scale": [1.0] * 10,
        "coefficients": [0.0] * 10,
        "intercept": 2.0,
        "provenance": "engineering_simulation",
        "protocol_sha256": "synthetic",
    }


def aggregate(opened, index=0, interval="15m"):
    step = (15 if interval == "15m" else 60) * MINUTE_MS * 1000
    price = 100 + 0.1 * math.sin(index / 5)
    return {
        "symbol": "BTCUSDT",
        "interval": interval,
        "open_us": opened,
        "close_us": opened + step,
        "available_us": opened + step,
        "received_us": opened + step + 100_000,
        "open": price - 0.01,
        "close": price,
        "high": price + 0.02,
        "low": price - 0.03,
        "volume": 1000 + index,
        "quote_volume": 100_000,
        "taker_buy_base": 450,
        "taker_buy_quote": 45_000,
    }


@pytest.mark.parametrize("interval", ["15m", "1h"])
def test_incremental_features_match_research_and_future_never_changes_past(interval):
    step = (15 if interval == "15m" else 60) * MINUTE_MS * 1000
    rows = [aggregate(BASE * 1000 + index * step, index, interval) for index in range(250)]
    reference = build_features(pl.DataFrame(rows))
    state = _new_features()
    outputs = []
    for row in rows:
        result = update_features(state, row, interval)
        if result:
            outputs.append(result.copy())
    actual = pl.DataFrame(outputs).select(FEATURE_NAMES).to_numpy()
    expected = reference.filter(pl.col("ema_gap").is_not_null()).select(FEATURE_NAMES).to_numpy()
    np.testing.assert_allclose(actual, expected, rtol=1e-9, atol=1e-12)
    frozen = outputs[-1].copy()
    later = aggregate(BASE * 1000 + 250 * step, 250, interval)
    later["close"] = 100000
    update_features(state, later, interval)
    assert outputs[-1] == frozen
    assert (
        update_features(state, aggregate(BASE * 1000 + 252 * step, 252, interval), interval) is None
    )
    assert state["count"] == 1


@pytest.fixture
def feed(request):
    STATE.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="candidate-engineering-", dir=STATE) as directory:
        folder = Path(directory)
        collector = Collector(folder / "source.sqlite3", disk_check=guard)
        count = (
            (END - 15 * MINUTE_MS - BASE) // MINUTE_MS
            if "mock_WS_to_features" in request.node.name
            else 60
        )
        for symbol in ("BTCUSDT", "ETHUSDT"):

            def rows(symbol=symbol):
                for index in range(count):
                    opened = END - 15 * MINUTE_MS - (count - index) * MINUTE_MS
                    close = str(90 + index * 0.0002)
                    yield (
                        symbol,
                        opened,
                        opened + MINUTE_MS - 1,
                        close,
                        close,
                        close,
                        close,
                        "100000",
                        "10000000",
                        100,
                        opened + MINUTE_MS,
                        opened + MINUTE_MS + 100,
                        "websocket",
                        opened + MINUTE_MS + 100,
                        1,
                    )

            collector.db.executemany(
                "INSERT INTO closed_bars VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", rows()
            )
        collector.db.commit()
        collector.close()
        yield folder


def engine(folder, **changes):
    return CandidatePaperEngine(
        folder / "source.sqlite3",
        folder / "candidate.sqlite3",
        model=model(),
        config=ShadowConfig(mode="engineering_simulation", **changes),
        started_ms=END - 15 * MINUTE_MS - 500,
        disk_check=guard,
    )


def health(now):
    return {
        "state": "RUNNING",
        "healthy": True,
        "qualified_72h": True,
        "heartbeat_ms": now,
        "clock_offset_ms": 0,
        "unresolved_gaps": 0,
        "disk": {"status": "OK"},
    }


def seed_features(obj):
    step = 15 * MINUTE_MS * 1000
    for symbol in ("BTCUSDT", "ETHUSDT"):
        for index in range(99):
            row = aggregate(END * 1000 - (100 - index) * step, index)
            row["symbol"] = symbol
            update_features(obj.state["features"][symbol], row, "15m")
    with obj.db:
        obj._append(
            END - 15 * MINUTE_MS - 500,
            "engineering_seed",
            {"source": "synthetic", "historical_feature_bars": 99},
            "engineering_seed",
        )
        for symbol in ("BTCUSDT", "ETHUSDT"):
            obj._snapshot_features(END - 15 * MINUTE_MS - 500, symbol)
        obj._checkpoint(END - 15 * MINUTE_MS - 500)


def kline(symbol, opened, *, missing=False):
    k = {
        "s": symbol,
        "t": opened,
        "T": opened + MINUTE_MS - 1,
        "i": "1m",
        "x": True,
        "o": "100",
        "h": "101",
        "l": "99",
        "c": "100",
        "v": "100000",
        "q": "10000000",
        "n": 100,
        "V": "50000",
        "Q": "5000000",
    }
    if missing:
        del k["V"]
    return {"e": "kline", "E": opened + MINUTE_MS + 100, "s": symbol, "k": k}


def quote_message(symbol, update):
    return {"s": symbol, "u": update, "b": "100", "a": "100.02", "B": "1000", "A": "1000"}


def payloads(obj, kind):
    return [
        json.loads(row[0])
        for row in obj.db.execute("SELECT payload FROM records WHERE kind=? ORDER BY seq", (kind,))
    ]


def test_mock_WS_to_features_four_cost_accounts_and_P06_still_zero_real_days(feed):
    obj = engine(feed)
    seed_features(obj)
    collector = CandidateCollector(feed / "source.sqlite3", candidate=obj, disk_check=guard)
    collector.health_snapshot = lambda at: {
        **health(at),
        "connected": True,
        "live_session": True,
        "qualification": {"qualified_72h": True},
    }
    update = 1
    for opened in range(END - 15 * MINUTE_MS, END, MINUTE_MS):
        # Both quotes already observed at this synthetic reception instant.
        for symbol in ("BTCUSDT", "ETHUSDT"):
            collector.latest_quotes[symbol] = {
                "symbol": symbol,
                "bid": 100.0,
                "ask": 100.02,
                "received_ms": opened + MINUTE_MS + 50,
                "update_id": update - 1,
            }
        for symbol in ("BTCUSDT", "ETHUSDT"):
            collector.handle_message(quote_message(symbol, update), opened + MINUTE_MS + 50)
        for symbol in ("BTCUSDT", "ETHUSDT"):
            collector.handle_message(kline(symbol, opened), opened + MINUTE_MS + 100)
        update += 1
    obj.process_tick(
        END + 200,
        health(END + 200),
        [Quote(symbol, 100, 100.02, END + 200, update) for symbol in ("BTCUSDT", "ETHUSDT")],
    )
    assert all(obj.state["accounts"][scenario]["pending"] for scenario in SCENARIOS)
    # Actual received mock quote messages continue each second; no stale gap is hidden.
    for offset in range(1000, MINUTE_MS + 2000, 1000):
        update += 1
        for symbol in ("BTCUSDT", "ETHUSDT"):
            collector.handle_message(quote_message(symbol, update), END + offset)
        if offset == MINUTE_MS:
            for symbol in ("BTCUSDT", "ETHUSDT"):
                collector.handle_message(kline(symbol, END), END + MINUTE_MS + 100)
    fills = payloads(obj, "fill")
    assert set(row["scenario"] for row in fills) == set(SCENARIOS), {
        "status": obj.status(),
        "events": payloads(obj, "order_event")[-12:],
        "decisions": payloads(obj, "decision")[-4:],
        "pending": {name: obj.state["accounts"][name]["pending"] for name in SCENARIOS},
    }
    assert all(
        obj.state["accounts"][scenario]["positions"]["BTCUSDT"] > 0 for scenario in SCENARIOS
    )
    base = [row for row in fills if row["scenario"] == "candidate"]
    fee = [row for row in fills if row["scenario"] == "fee_x2"]
    slip = [row for row in fills if row["scenario"] == "slippage_x2"]
    assert sum(row["fee"] for row in fee) > 1.99 * sum(row["fee"] for row in base)
    assert sum(row["execution_cost"] for row in slip) > sum(row["execution_cost"] for row in base)
    for scenario in SCENARIOS:
        actual_cash = 10_000 - sum(
            row["notional"] + row["fee"] for row in fills if row["scenario"] == scenario
        )
        assert obj.state["accounts"][scenario]["cash"] == pytest.approx(actual_cash)
    end = (END // DAY_MS + 1) * DAY_MS
    for symbol in ("BTCUSDT", "ETHUSDT"):
        row = (
            symbol,
            end - MINUTE_MS,
            end - 1,
            "100",
            "100",
            "100",
            "100",
            "100000",
            "10000000",
            100,
            end,
            end + 100,
            "websocket",
            end + 100,
            1,
        )
        collector.db.execute("INSERT INTO closed_bars VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", row)
    collector.db.commit()
    obj.process_tick(
        end + 2100,
        health(end + 2100),
        [Quote(symbol, 100, 100.02, end + 2100, 1000) for symbol in ("BTCUSDT", "ETHUSDT")],
    )
    navs = payloads(obj, "nav")
    assert set(row["scenario"] for row in navs) == set(SCENARIOS)
    assert len({row["date"] for row in navs}) == 1
    report = evaluate_forward_snapshot(read_forward_evidence(obj.path))
    assert report["status"] == "INSUFFICIENT_EVIDENCE"
    assert report.get("actual_elapsed_days", 0) == 0
    assert obj.status()["actual_qualification_days"] == 0
    with pytest.raises(HoldoutDenied):
        asyncio.run(collector.run())
    collector.close()
    obj.close()


def test_duplicate_future_and_frozen_change_recovery_contract(feed):
    obj = engine(feed)
    opened = END - MINUTE_MS
    raw = kline("BTCUSDT", opened)["k"]
    bar = {
        "symbol": "BTCUSDT",
        "open_us": opened * 1000,
        "close_us": (opened + MINUTE_MS) * 1000,
        "open": 100,
        "high": 101,
        "low": 99,
        "close": 100,
        "volume": 100000,
        "quote_volume": 10000000,
        "taker_buy_base": float(raw["V"]),
        "taker_buy_quote": float(raw["Q"]),
        "source": "websocket",
    }
    assert obj.ingest_bar(bar, END + 100)
    seq = obj.seq
    assert not obj.ingest_bar(bar, END + 200)
    assert obj.seq == seq
    with pytest.raises(ValueError, match="未来"):
        obj.ingest_bar({**bar, "open_us": END * 1000, "close_us": (END + MINUTE_MS) * 1000}, END)
    with pytest.raises(ValueError, match="内容改变"):
        obj.ingest_bar({**bar, "close": 100.5}, END + 200)
    obj.close()
    changed = model()
    changed["intercept"] = 3
    with pytest.raises(RuntimeError, match="different frozen"):
        CandidatePaperEngine(
            feed / "source.sqlite3",
            feed / "candidate.sqlite3",
            model=changed,
            config=ShadowConfig(mode="engineering_simulation"),
            disk_check=guard,
        )
    with pytest.raises(RuntimeError, match="different frozen"):
        engine(feed, fee_bps=11)


def test_restart_cannot_create_healthy_credit(feed):
    obj = engine(feed)
    now = END - 15 * MINUTE_MS
    obj.process_tick(
        now, health(now), [Quote(symbol, 100, 100.02, now, 1) for symbol in ("BTCUSDT", "ETHUSDT")]
    )
    prior = obj.state["healthy_seconds"]
    obj.close()
    restored = engine(feed)
    later = now + 8 * HOUR_MS
    restored.process_tick(
        later,
        health(later),
        [Quote(symbol, 100, 100.02, later, 2) for symbol in ("BTCUSDT", "ETHUSDT")],
    )
    assert restored.state["healthy_seconds"] == prior
    assert restored.status()["actual_qualification_days"] == 0
    assert len(payloads(restored, "start")) == 5
    restored.close()


def test_missing_raw_V_freezes_bridge_without_feature_default(feed):
    obj = engine(feed)
    collector = CandidateCollector(feed / "source.sqlite3", candidate=obj, disk_check=guard)
    collector.handle_message(kline("BTCUSDT", END - MINUTE_MS, missing=True), END + 100)
    assert obj.state["candidate_fault"] == "candidate_feature_contract_invalid"
    assert obj.state["features"]["BTCUSDT"]["count"] == 0
    assert obj.status()["frozen"]
    collector.close()
    obj.close()


def test_actual_STOP_pipeline_rejects_before_model_or_source_creation(tmp_path):
    with pytest.raises(HoldoutDenied, match="禁止读取留出"):
        create_candidate_pipeline(
            ROOT / "reports/generated/P04/summary.json",
            tmp_path / "absent-model.json",
            collector_db=tmp_path / "absent.db",
        )
    assert not (tmp_path / "absent.db").exists()


def test_engineering_model_cannot_enter_live_and_nan_rejected(feed):
    with pytest.raises(HoldoutDenied, match="真实单次"):
        CandidatePaperEngine(feed / "source.sqlite3", feed / "never-created.sqlite3", model=model())
    assert not (feed / "never-created.sqlite3").exists()
    invalid = model()
    invalid["scaler_scale"][0] = float("nan")
    with pytest.raises(HoldoutDenied, match="无效"):
        CandidatePaperEngine(
            feed / "source.sqlite3",
            feed / "never-created.sqlite3",
            model=invalid,
            config=replace(ShadowConfig(), mode="engineering_simulation"),
            disk_check=guard,
        )


def test_deferred_start_requires_fresh_dual_quotes_and_real_qualification_snapshot(feed):
    calls = []

    def factory(now, snapshot):
        calls.append((now, snapshot))
        return engine(feed)

    collector = CandidateCollector(
        feed / "source.sqlite3", candidate_factory=factory, disk_check=guard
    )
    now = END + 100
    tick = {
        "received_ms": now,
        "bar": None,
        "health": {
            **health(now),
            "connected": True,
            "live_session": True,
            "qualification": {"qualified_72h": True, "asof_ms": now},
            "disk": {"status": "OK", "asof_ms": now},
        },
        "quotes": {
            symbol: {
                "symbol": symbol,
                "bid": 100.0,
                "ask": 100.02,
                "update_id": 1,
                "received_ms": now,
                "fresh": True,
                "source": "websocket",
            }
            for symbol in ("BTCUSDT", "ETHUSDT")
        },
    }
    tick["quotes"]["ETHUSDT"]["received_ms"] = now - 6000
    collector._candidate_tick(tick)
    assert not calls and collector.stage == "WAITING_FOR_REAL_72H"
    tick["quotes"]["ETHUSDT"]["received_ms"] = now
    tick["health"]["qualification"]["asof_ms"] = now - 45001
    collector._candidate_tick(tick)
    assert not calls
    tick["health"]["qualification"]["asof_ms"] = now
    collector._candidate_tick(tick)
    assert len(calls) == 1 and collector.stage == "CANDIDATE_ACTIVE"
    assert collector.candidate.status()["actual_qualification_days"] == 0
    with pytest.raises(HoldoutDenied):
        asyncio.run(collector.run())
    collector.close()


def test_runtime_model_change_is_denied_before_new_record(feed):
    obj = engine(feed)
    previous = obj.seq
    obj.model["configuration"]["threshold"] = 0.9
    with pytest.raises(HoldoutDenied, match="参数改变"):
        obj.process_tick(END, health(END), [])
    assert obj.seq == previous
    obj.close()


def test_source_single_writer_lock_is_released_by_idempotent_close(feed):
    first = CandidateCollector(
        feed / "source.sqlite3", candidate_factory=lambda *_: None, disk_check=guard
    )
    with pytest.raises(RuntimeError, match="source锁"):
        CandidateCollector(
            feed / "source.sqlite3", candidate_factory=lambda *_: None, disk_check=guard
        )
    first.close()
    first.close()
    replacement = CandidateCollector(
        feed / "source.sqlite3", candidate_factory=lambda *_: None, disk_check=guard
    )
    replacement.close()


def test_wrong_distro_and_protected_source_refuse_before_creation(feed, monkeypatch):
    monkeypatch.setenv("WSL_DISTRO_NAME", "wrong-distro")
    with pytest.raises(HoldoutDenied, match="hpc_linux"):
        CandidateCollector(
            feed / "never-created.sqlite3", candidate_factory=lambda *_: None, disk_check=guard
        )
    assert not (feed / "never-created.sqlite3").exists()
    monkeypatch.setenv("WSL_DISTRO_NAME", "hpc_linux")
    with pytest.raises(HoldoutDenied, match="参考库"):
        CandidateCollector(
            STATE / "shadow_budget_v2.sqlite3", candidate_factory=lambda *_: None, disk_check=guard
        )


@pytest.mark.parametrize("interval", ["15m", "1h"])
def test_compact_checkpoint_recovery_replays_only_features_and_keeps_exact_pending(feed, interval):
    obj = CandidatePaperEngine(
        feed / "source.sqlite3", feed / "compact.sqlite3", model=model(interval),
        config=ShadowConfig(mode="engineering_simulation"), started_ms=END - HOUR_MS,
        disk_check=guard,
    )
    start = END - HOUR_MS
    for index in range(75):
        opened = start + index * MINUTE_MS
        for symbol in ("BTCUSDT", "ETHUSDT"):
            raw = kline(symbol, opened)["k"]
            bar = {
                "symbol": symbol, "open_us": opened * 1000,
                "close_us": (opened + MINUTE_MS) * 1000,
                "open": 100, "high": 101, "low": 99, "close": 100,
                "volume": 100000, "quote_volume": 10000000,
                "taker_buy_base": float(raw["V"]), "taker_buy_quote": float(raw["Q"]),
                "source": "websocket",
            }
            obj.ingest_bar(bar, opened + MINUTE_MS + 100)
        if index == 35:
            with obj.db:
                obj._checkpoint(opened + MINUTE_MS + 100)
    expected = copy.deepcopy(obj.state["features"])
    accounts = copy.deepcopy(obj.state["accounts"])
    seq = obj.seq
    checkpoints = payloads(obj, "checkpoint")
    assert all("features" not in row for row in checkpoints if "candidate_binding" in row)
    assert len(expected["BTCUSDT"]["pending_minutes"]) == (0 if interval == "15m" else 15)
    obj.close()
    restored = CandidatePaperEngine(
        feed / "source.sqlite3", feed / "compact.sqlite3", model=model(interval),
        config=ShadowConfig(mode="engineering_simulation"), disk_check=guard,
    )
    assert restored.state["features"] == expected
    assert restored.state["accounts"] == accounts
    assert restored.seq == seq  # recovery doesn't append financial/health/feature replay
    assert not restored.ingest_bar(bar, opened + MINUTE_MS + 200)
    assert restored.seq == seq
    restored.close()


def test_raw_quote_burst_is_bounded_but_both_closed_bars_and_next_decision_tick_survive(feed):
    obj = engine(feed)
    calls = []
    obj.ingest_tick = lambda tick: calls.append((tick["kind"], tick["received_ms"]))
    collector = CandidateCollector(feed / "source.sqlite3", candidate=obj, disk_check=guard)
    collector.health_snapshot = lambda at: health(at)
    for index in range(10000):
        collector.handle_message(quote_message("BTCUSDT", index + 1), END + index // 100)
    assert len(calls) == 1
    for symbol in ("BTCUSDT", "ETHUSDT"):
        collector.handle_message(kline(symbol, END - MINUTE_MS), END + 100)
    assert [kind for kind, _ in calls].count("closed_bar") == 2
    for symbol in ("BTCUSDT", "ETHUSDT"):
        obj.state["features"][symbol]["latest"] = {"available_us": END * 1000}
    obj.state["last_tick_ms"] = END + 100
    collector.handle_message(quote_message("BTCUSDT", 10001), END + 101)
    collector.handle_message(quote_message("ETHUSDT", 10002), END + 102)
    assert calls[-1] == ("quote", END + 101)
    assert len(calls) == 4  # exactly one boundary escape, not unbounded unhealthy retries
    collector.handle_message(quote_message("BTCUSDT", 10003), END + 1101)
    assert len(calls) == 5
    collector.close()
