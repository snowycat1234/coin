import json
import sqlite3
import tempfile
from dataclasses import replace
from pathlib import Path

import pytest

from quant.collector import Collector
from quant.paths import STATE
from quant.shadow import (
    DAY_MS,
    HOUR_MS,
    MINUTE_MS,
    Quote,
    ShadowConfig,
    ShadowEngine,
    quotes_from_buffers,
    read_forward_evidence,
)

BASE = 1_735_689_600_000  # 2025-01-01 UTC; explicitly synthetic
NOW = BASE + 31 * DAY_MS + HOUR_MS + 500


def guard(**kwargs):
    return {"status": "OK"}


def health(now, **changes):
    return {
        "state": "RUNNING",
        "healthy": True,
        "qualified_72h": True,
        "heartbeat_ms": now,
        "clock_offset_ms": 0,
        "unresolved_gaps": 0,
        "disk": {"status": "OK"},
        **changes,
    }


def quotes(now, update=1, spread=0.02):
    return [
        Quote(s, 100 - spread / 2, 100 + spread / 2, now, update) for s in ("BTCUSDT", "ETHUSDT")
    ]


@pytest.fixture
def feed(tmp_path):
    # All test state is D-hosted; no real sessions or network observations are claimed.
    STATE.mkdir(parents=True, exist_ok=True)
    native = tempfile.TemporaryDirectory(prefix="shadow-test-", dir=STATE)
    folder = Path(native.name)
    path = folder / "collector.sqlite3"
    collector = Collector(path, disk_check=guard)
    count = 31 * 1440 + 60
    rows = []
    for symbol in ("BTCUSDT", "ETHUSDT"):
        for i in range(count):
            opened = BASE + i * MINUTE_MS
            price = str(90 + i * 0.0002)
            rows.append(
                (
                    symbol,
                    opened,
                    opened + MINUTE_MS - 1,
                    price,
                    price,
                    price,
                    price,
                    "100000",
                    "10000000",
                    100,
                    opened + MINUTE_MS,
                    opened + MINUTE_MS + 100,
                    "websocket",
                    opened + MINUTE_MS + 100,
                    1,
                )
            )
    collector.db.executemany("INSERT INTO closed_bars VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", rows)
    collector.db.commit()
    yield collector, folder
    collector.close()
    native.cleanup()


def engine(feed, **changes):
    collector, folder = feed
    return ShadowEngine(
        collector.path,
        folder / "shadow.sqlite3",
        config=ShadowConfig(mode="engineering_simulation", **changes),
        started_ms=NOW - HOUR_MS,
        disk_check=guard,
    )


def records(obj, kind):
    return [
        json.loads(r[0])
        for r in obj.db.execute(
            "SELECT payload FROM records WHERE kind=? ORDER BY seq",
            (kind,),
        )
    ]


def add_capacity(feed, opened, volume="10000000", source="websocket"):
    collector, _ = feed
    for symbol in ("BTCUSDT", "ETHUSDT"):
        collector.db.execute(
            "INSERT OR REPLACE INTO closed_bars VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                symbol,
                opened,
                opened + MINUTE_MS - 1,
                "100",
                "100",
                "100",
                "100",
                "100000",
                volume,
                100,
                opened + MINUTE_MS,
                opened + MINUTE_MS + 100,
                source,
                opened + MINUTE_MS + 100 if source == "websocket" else None,
                1,
            ),
        )
    collector.db.commit()


def test_next_minute_received_quote_and_costs_are_required(feed):
    obj = engine(feed)
    try:
        obj.process_tick(NOW, health(NOW), quotes(NOW))
        assert records(obj, "decision")[0]["state"] == "READY"
        assert records(obj, "fill") == []
        early = NOW + 10_000
        obj.process_tick(early, health(early), quotes(early, update=2))
        assert records(obj, "fill") == []
        execute = NOW // MINUTE_MS * MINUTE_MS + MINUTE_MS + 500
        add_capacity(feed, execute // MINUTE_MS * MINUTE_MS - MINUTE_MS)
        obj.process_tick(execute, health(execute), quotes(execute, update=3, spread=0.2))
        fills = records(obj, "fill")
        assert len(fills) == 2
        for fill in fills:
            assert fill["quote_received_ms"] > NOW
            assert fill["price"] == pytest.approx(100.14)  # actual half spread10bp + 4bp
            assert fill["fee"] == pytest.approx(fill["notional"] * 0.001)
            assert fill["notional"] >= 10
            assert fill["notional"] <= fill["capacity_limit"]
        assert obj.status()["cash"]["B2"] >= 0
        assert obj.status()["positions"]["B0"] == {"BTCUSDT": 0, "ETHUSDT": 0}
    finally:
        obj.close()


def test_duplicate_quotes_restart_and_hashchain_cannot_double_fill(feed):
    obj = engine(feed)
    obj.process_tick(NOW, health(NOW), quotes(NOW))
    execute = NOW // MINUTE_MS * MINUTE_MS + MINUTE_MS + 500
    add_capacity(feed, execute // MINUTE_MS * MINUTE_MS - MINUTE_MS)
    obj.process_tick(execute, health(execute), quotes(execute, update=2))
    original_fills = records(obj, "fill")
    original_positions = obj.status()["positions"]
    version = obj.version
    obj.close()
    restored = engine(feed)
    try:
        restored.process_tick(execute, health(execute), quotes(execute, update=2))
        restored.process_tick(execute + 1000, health(execute + 1000), quotes(execute, update=2))
        assert records(restored, "fill") == original_fills
        assert restored.status()["positions"] == original_positions
        evidence = read_forward_evidence(restored.path, version)
        assert evidence["triggers_verified"] is True
        assert evidence["mode"] == "engineering_simulation"
        assert evidence["provenance"] == "synthetic"
        assert evidence["head_hash"] == restored.head
        streamed = read_forward_evidence(restored.path, include_records=False)
        assert streamed["records"] == []
        assert streamed["head_hash"] == evidence["head_hash"]
        assert streamed["seq"] == evidence["seq"]
        with pytest.raises(sqlite3.IntegrityError, match="immutable"):
            restored.db.execute("UPDATE records SET payload='{}' WHERE seq=1")
        with pytest.raises(sqlite3.IntegrityError, match="immutable"):
            restored.db.execute("DELETE FROM records WHERE seq=1")
    finally:
        restored.close()


@pytest.mark.parametrize(
    "fault",
    [
        {"qualified_72h": False},
        {"unresolved_gaps": 1},
        {"clock_offset_ms": 22_000},
        {"disk": {"status": "STOP"}},
        {"healthy": False},
        {"heartbeat_ms": 0},
    ],
)
def test_unqualified_or_faulty_health_freezes_new_decisions(feed, fault):
    obj = engine(feed)
    try:
        result = obj.process_tick(NOW, health(NOW, **fault), quotes(NOW))
        assert result["frozen"] is True
        assert records(obj, "decision") == []
        assert records(obj, "fill") == []
        assert records(obj, "incident")
    finally:
        obj.close()


def test_rest_repair_and_missing_closed_hour_cannot_fabricate_signal(feed):
    collector, _ = feed
    collector.db.execute(
        "UPDATE closed_bars SET source='rest',websocket_received_ms=NULL "
        "WHERE symbol='ETHUSDT' AND open_ms=?",
        (NOW // HOUR_MS * HOUR_MS - MINUTE_MS,),
    )
    collector.db.commit()
    obj = engine(feed)
    try:
        obj.process_tick(NOW, health(NOW), quotes(NOW))
        assert records(obj, "decision") == []
        assert records(obj, "fill") == []
        # Actual late WS evidence can finish the current hour. No REST values are used.
        collector.db.execute(
            "UPDATE closed_bars SET source='websocket',websocket_received_ms=? "
            "WHERE symbol='ETHUSDT' AND open_ms=?",
            (NOW + 100, NOW // HOUR_MS * HOUR_MS - MINUTE_MS),
        )
        collector.db.commit()
        obj.process_tick(NOW + 1000, health(NOW + 1000), quotes(NOW + 1000, update=2))
        assert len(records(obj, "decision")) == 1
        assert records(obj, "fill") == []
    finally:
        obj.close()


def test_capacity_is_cumulative_per_actual_minute_and_rest_capacity_is_rejected(feed):
    obj = engine(feed)
    try:
        obj.process_tick(NOW, health(NOW), quotes(NOW))
        execute = NOW // MINUTE_MS * MINUTE_MS + MINUTE_MS + 500
        prior = execute // MINUTE_MS * MINUTE_MS - MINUTE_MS
        add_capacity(feed, prior, volume="20000")
        obj.process_tick(execute, health(execute), quotes(execute, update=2))
        obj.process_tick(execute + 1000, health(execute + 1000), quotes(execute + 1000, update=3))
        fills = records(obj, "fill")
        assert len(fills) == 2
        assert all(fill["notional"] <= 20 for fill in fills)
        later = execute + MINUTE_MS
        add_capacity(feed, prior + MINUTE_MS, source="rest")
        obj.process_tick(later, health(later), quotes(later, update=4))
        assert records(obj, "fill") == fills
    finally:
        obj.close()


def test_warmup_and_stale_or_old_quotes_do_not_fill(feed):
    collector, _ = feed
    collector.db.execute("DELETE FROM closed_bars WHERE open_ms<?", (NOW - 10 * DAY_MS,))
    collector.db.commit()
    obj = engine(feed)
    try:
        obj.process_tick(NOW, health(NOW), quotes(NOW))
        assert records(obj, "decision")[0]["state"] == "RISK_WARMUP"
        execute = NOW + MINUTE_MS
        add_capacity(feed, execute // MINUTE_MS * MINUTE_MS - MINUTE_MS)
        obj.process_tick(execute, health(execute), quotes(NOW, update=2))
        assert records(obj, "fill") == []
        assert obj.status()["frozen"] is True
    finally:
        obj.close()


def test_daily_nav_is_not_rewritten_after_gap_and_recovery_keeps_position_pnl(feed):
    obj = engine(feed)
    try:
        obj.process_tick(NOW, health(NOW), quotes(NOW))
        execute = NOW // MINUTE_MS * MINUTE_MS + MINUTE_MS + 500
        add_capacity(feed, execute // MINUTE_MS * MINUTE_MS - MINUTE_MS)
        obj.process_tick(execute, health(execute), quotes(execute, update=2))
        quantities = obj.status()["positions"]["B2"].copy()
        day_end = (NOW // DAY_MS + 1) * DAY_MS
        obj.process_tick(day_end + 5000, health(day_end + 5000, healthy=False), [])
        first = [n for n in records(obj, "nav") if n["scenario"] == "B2"][0]
        assert first["stale_exposure"] is True
        assert first["daily_risk_observable"] is False
        # Repair is not allowed to rewrite the already sealed NAV.
        add_capacity(feed, day_end - MINUTE_MS)
        collector, _ = feed
        collector.db.execute(
            "UPDATE closed_bars SET close='50' WHERE open_ms=?", (day_end - MINUTE_MS,)
        )
        collector.db.commit()
        obj.process_tick(day_end + 10_000, health(day_end + 10_000, healthy=False), [])
        assert [n for n in records(obj, "nav") if n["scenario"] == "B2"][0] == first
        next_end = day_end + DAY_MS
        add_capacity(feed, next_end - MINUTE_MS)
        collector.db.execute(
            "UPDATE closed_bars SET close='50' WHERE open_ms=?", (next_end - MINUTE_MS,)
        )
        collector.db.commit()
        obj.process_tick(next_end + 5000, health(next_end + 5000, healthy=False), [])
        last = [n for n in records(obj, "nav") if n["scenario"] == "B2"][-1]
        assert last["nav"] == pytest.approx(
            obj.status()["cash"]["B2"] + sum(quantities.values()) * 50
        )
        assert obj.status()["positions"]["B2"] == quantities
    finally:
        obj.close()


def test_clock_regression_single_writer_and_version_changes_fail_closed(feed):
    obj = engine(feed)
    try:
        obj.process_tick(NOW, health(NOW), quotes(NOW))
        with pytest.raises(RuntimeError, match="another shadow"):
            engine(feed)
        regressed = obj.process_tick(NOW - 1000, health(NOW - 1000), quotes(NOW - 1000))
        assert regressed["frozen"] is True
        assert regressed["clock_regression"] is True
    finally:
        obj.close()
    with pytest.raises(RuntimeError, match="different frozen"):
        engine(feed, fee_bps=20)


def test_health_incident_cancels_pending_so_recovery_cannot_fill_an_old_signal(feed):
    obj = engine(feed)
    try:
        obj.process_tick(NOW, health(NOW), quotes(NOW))
        assert obj.state["accounts"]["B2"]["pending"]
        bad = NOW + 1000
        obj.process_tick(bad, health(bad, unresolved_gaps=1), quotes(bad, update=2))
        assert obj.state["accounts"]["B2"]["pending"] == {}
        execute = NOW // MINUTE_MS * MINUTE_MS + MINUTE_MS + 500
        add_capacity(feed, execute // MINUTE_MS * MINUTE_MS - MINUTE_MS)
        obj.process_tick(execute, health(execute), quotes(execute, update=3))
        assert records(obj, "fill") == []
        assert any(o["status"] == "CANCELLED_HEALTH" for o in records(obj, "order_event"))
    finally:
        obj.close()


def test_transaction_failure_rolls_back_fill_and_cash_before_retry(feed, monkeypatch):
    obj = engine(feed)
    try:
        obj.process_tick(NOW, health(NOW), quotes(NOW))
        execute = NOW // MINUTE_MS * MINUTE_MS + MINUTE_MS + 500
        add_capacity(feed, execute // MINUTE_MS * MINUTE_MS - MINUTE_MS)
        append = obj._append

        def fail_position(now, kind, payload, key):
            if kind == "position":
                raise RuntimeError("injected transaction fault")
            append(now, kind, payload, key)

        with monkeypatch.context() as fault:
            fault.setattr(obj, "_append", fail_position)
            with pytest.raises(RuntimeError, match="injected"):
                obj.process_tick(execute, health(execute), quotes(execute, update=2))
        assert records(obj, "fill") == []
        assert obj.status()["cash"]["B2"] == 10_000
        obj.process_tick(execute, health(execute), quotes(execute, update=2))
        assert len(records(obj, "fill")) == 2
        assert read_forward_evidence(obj.path, include_records=False)["head_hash"] == obj.head
    finally:
        obj.close()


def test_restart_cancels_partly_unfilled_orders_instead_of_replaying_old_targets(feed):
    obj = engine(feed)
    obj.process_tick(NOW, health(NOW), quotes(NOW))
    execute = NOW // MINUTE_MS * MINUTE_MS + MINUTE_MS + 500
    add_capacity(feed, execute // MINUTE_MS * MINUTE_MS - MINUTE_MS, volume="20000")
    obj.process_tick(execute, health(execute), quotes(execute, update=2))
    original_fills = records(obj, "fill")
    assert obj.state["accounts"]["B2"]["pending"]
    obj.close()
    restored = engine(feed)
    try:
        later = execute + MINUTE_MS
        add_capacity(feed, later // MINUTE_MS * MINUTE_MS - MINUTE_MS)
        restored.process_tick(later, health(later), quotes(later, update=3))
        assert records(restored, "fill") == original_fills
        assert restored.state["accounts"]["B2"]["pending"] == {}
        assert any(o.get("reason") == "process_restart" for o in records(restored, "order_event"))
    finally:
        restored.close()


def test_buffer_adapter_and_cost_contract_cannot_be_relaxed():
    adapted = quotes_from_buffers(
        {
            "BTCUSDT": {
                "samples": 2,
                "last_bid": "99",
                "last_ask": "101",
                "last_received": NOW,
                "last_id": 7,
            }
        }
    )
    assert adapted == [Quote("BTCUSDT", 99, 101, NOW, 7)]
    with pytest.raises(ValueError, match="cost"):
        replace(ShadowConfig(), fee_bps=9)
    with pytest.raises(ValueError, match="qualification"):
        ShadowConfig(require_72h=False)
    with pytest.raises(ValueError, match="genuinely received"):
        Quote("BTCUSDT", 99, 101, NOW, 7, source="rest")
