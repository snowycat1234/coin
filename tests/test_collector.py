import asyncio
import fcntl
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import httpx
import pytest

from quant import collector as module
from quant.collector import MINUTE_MS, Collector, CollectorStopped, status
from quant.paths import STATE

BASE = 1_735_689_600_000


def guard(**kwargs):
    return {"status": "OK"}


@pytest.fixture
def collector(tmp_path):
    # pytest temp directory is configured on D by scripts/env.sh.
    obj = Collector(tmp_path / "live.sqlite3", disk_check=guard)
    yield obj
    obj.close()


def kline(opened=BASE, closed=True, symbol="BTCUSDT"):
    return {
        "stream": f"{symbol.lower()}@kline_1m",
        "data": {
            "e": "kline",
            "E": opened + MINUTE_MS,
            "s": symbol,
            "k": {
                "t": opened,
                "T": opened + MINUTE_MS - 1,
                "s": symbol,
                "i": "1m",
                "o": "100",
                "h": "102",
                "l": "99",
                "c": "101",
                "v": "10",
                "q": "1000",
                "n": 50,
                "x": closed,
            },
        },
    }


def quote(update=1, bid="100", ask="100.1", symbol="BTCUSDT"):
    return {
        "stream": f"{symbol.lower()}@bookTicker",
        "data": {
            "s": symbol,
            "u": update,
            "b": bid,
            "B": "1",
            "a": ask,
            "A": "1",
        },
    }


def test_only_closed_one_minute_bars_are_persisted(collector):
    open_bar = kline(closed=False)
    open_bar["data"]["E"] = BASE + 30_000
    assert not collector.handle_message(open_bar, BASE + 30_000)
    assert collector.db.execute("SELECT COUNT(*) FROM closed_bars").fetchone()[0] == 0
    assert collector.handle_message(kline(), BASE + 60_010)
    row = collector.db.execute("SELECT * FROM closed_bars").fetchone()
    assert row["source"] == "websocket"
    assert row["exchange_event_ms"] == BASE + 60_000
    assert row["received_ms"] == BASE + 60_010
    assert row["websocket_received_ms"] == BASE + 60_010


def test_duplicate_candles_preserve_first_received_evidence(collector):
    assert collector.handle_message(kline(), BASE + 60_010)
    assert not collector.handle_message(kline(), BASE + 60_999)
    row = collector.db.execute("SELECT * FROM closed_bars").fetchone()
    assert row["received_ms"] == row["websocket_received_ms"] == BASE + 60_010
    assert collector.db.execute("SELECT COUNT(*) FROM closed_bars").fetchone()[0] == 1


def test_candle_gap_detection_and_rest_repair_provenance(collector, monkeypatch):
    collector.handle_message(kline(), BASE + 60_010)
    collector.handle_message(kline(BASE + 120_000), BASE + 180_010)
    assert collector.db.execute("SELECT COUNT(*) FROM gaps").fetchone()[0] == 1
    monkeypatch.setattr(module, "now_ms", lambda: BASE + 200_000)

    def request(req):
        assert req.url.host == "data-api.binance.vision"
        assert req.url.path == "/api/v3/klines"
        assert req.url.params["startTime"] == str(BASE + 60_000)
        return httpx.Response(
            200,
            json=[
                [
                    BASE + 60_000,
                    "100",
                    "102",
                    "99",
                    "101",
                    "10",
                    BASE + 119_999,
                    "1000",
                    50,
                    "5",
                    "500",
                    "0",
                ]
            ],
        )

    async def perform():
        async with httpx.AsyncClient(transport=httpx.MockTransport(request)) as client:
            assert await collector.repair(client) == 1
            assert await collector.repair(client) == 0

    asyncio.run(perform())
    repaired = collector.db.execute(
        "SELECT * FROM closed_bars WHERE open_ms=?",
        (BASE + 60_000,),
    ).fetchone()
    assert repaired["source"] == "rest"
    assert repaired["received_ms"] == BASE + 200_000
    assert repaired["exchange_event_ms"] is None
    assert repaired["websocket_received_ms"] is None
    assert collector.db.execute("SELECT repaired_ms FROM gaps").fetchone()[0] == BASE + 200_000
    assert (
        collector.db.execute("SELECT COUNT(*) FROM events WHERE kind='repair'").fetchone()[0] == 1
    )


def test_trailing_gap_is_detected_during_silent_stream(collector):
    collector.handle_message(kline(), BASE + 60_010)
    collector.detect_gaps(BASE + 182_001)
    gap = collector.db.execute("SELECT * FROM gaps").fetchone()
    assert gap["start_ms"] == BASE + 60_000
    assert gap["end_ms"] == BASE + 120_000
    assert gap["repaired_ms"] is None


def test_quote_updates_are_aggregated_once_per_received_utc_minute(collector):
    assert collector.handle_message(quote(1), BASE + 100)
    assert not collector.handle_message(quote(1), BASE + 200)
    assert collector.handle_message(quote(2, ask="100.2"), BASE + 300)
    assert collector.db.execute("SELECT COUNT(*) FROM quote_minutes").fetchone()[0] == 0
    assert collector.handle_message(quote(3), BASE + 60_100)
    row = collector.db.execute("SELECT * FROM quote_minutes").fetchone()
    assert row["minute_ms"] == BASE
    assert row["samples"] == 2
    assert row["exchange_event_ms"] is None
    assert row["spread_bps_min"] < row["spread_bps_max"]
    assert row["spread_bps_sum"] / row["samples"] == pytest.approx(
        (row["spread_bps_min"] + row["spread_bps_max"]) / 2
    )
    collector.flush_quotes(BASE + 120_000)
    assert collector.db.execute("SELECT COUNT(*) FROM quote_minutes").fetchone()[0] == 2


def test_disk_rejection_stops_writes_and_invalidates_qualification(collector, monkeypatch):
    def reject(**kwargs):
        raise RuntimeError("18 GB intake limit")

    collector.disk_check = reject
    collector._last_guard = -1e20
    with pytest.raises(CollectorStopped, match="18 GB"):
        collector.handle_message(kline(), BASE + 60_010)
    assert collector.db.execute("SELECT COUNT(*) FROM closed_bars").fetchone()[0] == 0
    assert (
        collector.db.execute("SELECT COUNT(*) FROM events WHERE kind='disk_stop'").fetchone()[0]
        == 1
    )
    monkeypatch.setattr(module.disk, "check", reject)
    result = status(collector.path)
    assert result["qualified_72h"] is False
    assert any("Disk guard" in reason for reason in result["reasons"])


def test_replay_of_historical_events_cannot_create_real_online_session(collector, monkeypatch):
    for minute in range(5):
        opened = BASE + minute * 60_000
        collector.handle_message(kline(opened), opened + 60_010)
    monkeypatch.setattr(module.disk, "check", guard)
    monkeypatch.setattr(module, "now_ms", lambda: BASE + 72 * 3600 * 1000)
    result = status(collector.path)
    assert result["session"] is None
    assert result["qualified_72h"] is False
    assert "No running real collection session" in result["reasons"]


def test_unhealthy_or_delayed_heartbeat_never_credits_elapsed_time(collector, monkeypatch):
    # Private heartbeat is exercised to prove suspension/delayed processing cannot
    # count hours merely because the next wall clock timestamp is much later.
    collector.session_id = collector.db.execute(
        "INSERT INTO sessions(started_ms,state,endpoint,healthy_seconds) VALUES(?,'RUNNING',?,100)",
        (BASE, module.STREAM_URL),
    ).lastrowid
    collector.db.commit()
    collector._connected = True
    collector._clock_offset = 0
    collector._healthy = True
    collector._last_heartbeat = 0
    collector._last_wall = BASE
    for symbol in module.SYMBOLS:
        collector.last_quote_received[symbol] = BASE + 3_600_000
        collector.last_kline_received[symbol] = BASE + 3_600_000
        collector.last_closed_received[symbol] = BASE + 3_600_000
    monkeypatch.setattr(module.time, "monotonic", lambda: 3600)
    monkeypatch.setattr(module, "now_ms", lambda: BASE + 3_600_000)
    collector._heartbeat()
    assert collector.db.execute("SELECT healthy_seconds FROM sessions").fetchone()[0] == 100
    assert collector.db.execute("SELECT observed_seconds FROM sessions").fetchone()[0] == 3600
    collector.last_quote_received.clear()
    monkeypatch.setattr(module.time, "monotonic", lambda: 3615)
    monkeypatch.setattr(module, "now_ms", lambda: BASE + 3_615_000)
    collector._heartbeat()
    assert collector.db.execute("SELECT healthy_seconds FROM sessions").fetchone()[0] == 100
    assert collector.db.execute("SELECT observed_seconds FROM sessions").fetchone()[0] == 3615


def test_guard_stopped_or_stale_session_never_qualifies(collector, monkeypatch):
    collector.db.execute(
        "INSERT INTO sessions(started_ms,state,heartbeat_ms,healthy_seconds,endpoint) "
        "VALUES(?,'DISK_STOP',?,?,?)",
        (BASE, BASE, 72 * 3600, module.STREAM_URL),
    )
    collector.db.commit()
    monkeypatch.setattr(module.disk, "check", guard)
    monkeypatch.setattr(module, "now_ms", lambda: BASE + 72 * 3600 * 1000)
    result = status(collector.path)
    assert result["qualified_72h"] is False
    assert "No running real collection session" in result["reasons"]
    assert "Collector heartbeat is absent or stale" in result["reasons"]


def test_database_uses_wal_and_quote_table_has_no_raw_message_column(collector):
    assert collector.db.execute("PRAGMA journal_mode").fetchone()[0] == "wal"
    assert collector.db.execute("PRAGMA synchronous").fetchone()[0] == 2
    columns = {row[1] for row in collector.db.execute("PRAGMA table_info(quote_minutes)")}
    assert "raw" not in columns
    assert "samples" in columns


def test_rejects_invalid_candles_and_crossed_quotes(collector):
    malformed = kline()
    malformed["data"]["k"]["h"] = "98"
    with pytest.raises(ValueError, match="OHLCV"):
        collector.handle_message(malformed, BASE + 60_010)
    with pytest.raises(ValueError, match="bid/ask"):
        collector.handle_message(quote(ask="99"), BASE + 100)
    assert collector.db.execute("SELECT COUNT(*) FROM closed_bars").fetchone()[0] == 0


def test_rest_repair_does_not_insert_unclosed_candle(collector, monkeypatch):
    collector._record_gap("BTCUSDT", BASE, BASE, "test")
    monkeypatch.setattr(module, "now_ms", lambda: BASE + 30_000)

    async def perform():
        response = httpx.Response(
            200,
            json=[
                [
                    BASE,
                    "100",
                    "102",
                    "99",
                    "101",
                    "10",
                    BASE + 59_999,
                    "1000",
                    50,
                    "5",
                    "500",
                    "0",
                ]
            ],
        )
        async with httpx.AsyncClient(transport=httpx.MockTransport(lambda r: response)) as client:
            assert await collector.repair(client) == 0

    asyncio.run(perform())
    assert collector.db.execute("SELECT COUNT(*) FROM closed_bars").fetchone()[0] == 0
    assert collector.db.execute("SELECT repaired_ms FROM gaps").fetchone()[0] is None


def test_72h_coverage_is_checked_even_if_session_counter_claims_completion(collector, monkeypatch):
    # A stale/manual counter alone is insufficient: contiguous candle and quote
    # coverage and freshness are checked independently of the elapsed counter.
    collector.db.execute(
        "INSERT INTO sessions(started_ms,state,heartbeat_ms,healthy_seconds,endpoint) "
        "VALUES(?,'RUNNING',?,?,?)",
        (BASE, BASE + 72 * 3600 * 1000, 72 * 3600, module.STREAM_URL),
    )
    collector.db.commit()
    monkeypatch.setattr(module.disk, "check", guard)
    monkeypatch.setattr(module, "now_ms", lambda: BASE + 72 * 3600 * 1000)
    result = status(collector.path)
    assert result["qualified_72h"] is False
    assert result["symbols"]["BTCUSDT"]["bars_in_last_72h"] == 0
    assert any("missing closed candles" in reason for reason in result["reasons"])


def test_native_wal_status_reader_does_not_block_open_writer(monkeypatch):
    monkeypatch.setattr(module.disk, "check", guard)
    STATE.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="collector-test-", dir=STATE) as directory:
        obj = Collector(Path(directory) / "live.sqlite3", disk_check=guard)
        try:
            obj.db.execute("BEGIN IMMEDIATE")
            obj.db.execute(
                "INSERT INTO events(received_ms,kind,detail) VALUES(?,'test','uncommitted')",
                (BASE,),
            )
            with ThreadPoolExecutor(max_workers=1) as pool:
                result = pool.submit(status, obj.path).result(timeout=3)
                assert result["state"] == "NO_SESSION"
            obj.db.rollback()
        finally:
            obj.close()


def test_second_live_collector_is_rejected_before_network_open(monkeypatch):
    monkeypatch.setattr(module.disk, "check", guard)
    STATE.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="collector-lock-test-", dir=STATE) as directory:
        target = Path(directory) / "live.sqlite3"
        with target.with_suffix(".lock").open("a+") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            with pytest.raises(RuntimeError, match="already holds"):
                asyncio.run(module.collect(1, target))


def test_stale_websocket_exchange_time_is_rejected_not_credited_as_live(collector):
    with pytest.raises(ValueError, match="Stale exchange"):
        collector.handle_message(kline(), BASE + 90_001)
    assert collector.db.execute("SELECT COUNT(*) FROM closed_bars").fetchone()[0] == 0
    assert not collector.last_closed_received


def test_c_drive_storage_is_rejected_even_if_state_env_was_misconfigured(monkeypatch):
    monkeypatch.setenv("WSL_DISTRO_NAME", "hpc_linux")
    monkeypatch.setattr(module, "STATE", Path("/mnt/c/collector-state"))
    with pytest.raises(ValueError, match="C: is forbidden"):
        asyncio.run(module.collect(1, Path("/mnt/c/collector-state/live.sqlite3")))


def test_clock_sync_uses_request_midpoint_and_records_evidence(collector, monkeypatch):
    times = iter([BASE, BASE + 100, BASE + 100])
    monkeypatch.setattr(module, "now_ms", lambda: next(times))

    async def perform():
        response = httpx.Response(200, json={"serverTime": BASE + 55})
        async with httpx.AsyncClient(transport=httpx.MockTransport(lambda r: response)) as client:
            await collector.sync_clock(client)

    asyncio.run(perform())
    assert collector._clock_offset == 5
    assert (
        collector.db.execute("SELECT COUNT(*) FROM events WHERE kind='clock_sync'").fetchone()[0]
        == 1
    )


@pytest.fixture
def qualified_db(monkeypatch):
    """Synthetic acceptance fixture, deliberately separate from real evidence."""
    monkeypatch.setattr(module.disk, "check", guard)
    current = BASE + module.REQUIRED_SECONDS * 1000 + 1000
    monkeypatch.setattr(module, "now_ms", lambda: current)
    STATE.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="collector-qual-test-", dir=STATE) as directory:
        obj = Collector(Path(directory) / "live.sqlite3", disk_check=guard)
        obj.session_id = obj.db.execute(
            "INSERT INTO sessions(started_ms,state,heartbeat_ms,healthy_seconds,"
            "observed_seconds,clock_offset_ms,endpoint) VALUES(?,'RUNNING',?,?,?,?,?)",
            (
                BASE,
                current,
                module.REQUIRED_SECONDS - 120,
                module.REQUIRED_SECONDS,
                0,
                module.STREAM_URL,
            ),
        ).lastrowid
        for symbol in module.SYMBOLS:
            bars, quotes = [], []
            for minute in range(4320):
                opened = BASE + minute * module.MINUTE_MS
                closed = opened + module.MINUTE_MS - 1
                bars.append(
                    (
                        symbol,
                        opened,
                        closed,
                        "100",
                        "102",
                        "99",
                        "101",
                        "10",
                        "1000",
                        50,
                        closed + 1,
                        closed + 1,
                        "websocket",
                        closed + 1,
                        obj.session_id,
                    )
                )
                quotes.append(
                    (
                        symbol,
                        opened,
                        1,
                        1.0,
                        1.0,
                        1.0,
                        "100",
                        "100.01",
                        opened + 1,
                        closed,
                        minute,
                        minute,
                        None,
                        int(minute in (1430, 2860)),
                    )
                )
            obj.db.executemany(
                "INSERT INTO closed_bars VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", bars
            )
            obj.db.executemany(
                "INSERT INTO quote_minutes VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)", quotes
            )
        obj.db.commit()
        obj.event("rotate_24h", "synthetic test rotation 1")
        obj.event("rotate_24h", "synthetic test rotation 2")
        try:
            yield obj
        finally:
            obj.close()


def test_daily_connection_rotations_can_still_pass_72h_gate(qualified_db):
    result = status(qualified_db.path)
    assert result["qualified_72h"] is True
    assert result["planned_rotations"] == 2
    assert result["observed_seconds"] == 72 * 3600
    assert result["downtime_seconds"] == 120
    assert result["uptime_fraction"] >= 0.999
    assert result["symbols"]["BTCUSDT"]["partial_quote_minutes_in_last_72h"] == 2
    assert result["symbols"]["BTCUSDT"]["quote_coverage_fraction"] >= 0.999


@pytest.mark.parametrize("downtime,accepted", [(259, True), (260, False)])
def test_uptime_threshold_accepts_259s_but_rejects_260s_per_72h(qualified_db, downtime, accepted):
    qualified_db.db.execute(
        "UPDATE sessions SET healthy_seconds=?",
        (module.REQUIRED_SECONDS - downtime,),
    )
    qualified_db.db.commit()
    result = status(qualified_db.path)
    assert result["qualified_72h"] is accepted
    if not accepted:
        assert "Healthy observed uptime is below 99.9%" in result["reasons"]


def test_quote_coverage_shortfall_is_reported_without_rest_fabrication(qualified_db):
    qualified_db.db.execute(
        "DELETE FROM quote_minutes WHERE symbol='BTCUSDT' AND minute_ms<?",
        (BASE + 5 * module.MINUTE_MS,),
    )
    qualified_db.db.commit()
    result = status(qualified_db.path)
    assert result["qualified_72h"] is False
    assert result["symbols"]["BTCUSDT"]["missing_quote_minutes_in_last_72h"] == 5
    assert result["symbols"]["BTCUSDT"]["partial_quote_minutes_in_last_72h"] == 2
    assert "BTCUSDT: complete quote minute coverage is below 99.9%" in result["reasons"]


def test_large_clock_jump_is_counted_and_forces_new_sync(collector, monkeypatch):
    collector.session_id = collector.db.execute(
        "INSERT INTO sessions(started_ms,state,endpoint,healthy_seconds,observed_seconds) "
        "VALUES(?,'RUNNING',?,100,110)",
        (BASE, module.STREAM_URL),
    ).lastrowid
    collector.db.commit()
    collector._clock_offset = 0
    collector._last_heartbeat = 0
    collector._last_wall = BASE
    monkeypatch.setattr(module.time, "monotonic", lambda: 15)
    monkeypatch.setattr(module, "now_ms", lambda: BASE + 45_000)
    collector._heartbeat()
    assert collector._clock_offset is None
    row = collector.db.execute("SELECT * FROM sessions").fetchone()
    assert row["healthy_seconds"] == 100
    assert row["observed_seconds"] == 125
    monkeypatch.setattr(module.disk, "check", guard)
    result = status(collector.path)
    assert result["clock_incident_count"] == 1
    assert result["clock_incidents"]["clock_jump"] == 1
    assert result["qualified_72h"] is False


def test_rotation_between_two_healthy_heartbeats_is_still_counted_as_downtime(
    collector, monkeypatch
):
    collector.session_id = collector.db.execute(
        "INSERT INTO sessions(started_ms,state,endpoint,healthy_seconds,observed_seconds) "
        "VALUES(?,'RUNNING',?,100,100)",
        (BASE, module.STREAM_URL),
    ).lastrowid
    collector.db.commit()
    collector._connected = True
    collector._clock_offset = 0
    collector._healthy = True
    collector._interval_fault = True
    collector._last_heartbeat = 0
    collector._last_wall = BASE
    for symbol in module.SYMBOLS:
        collector.last_quote_received[symbol] = BASE + 15_000
        collector.last_kline_received[symbol] = BASE + 15_000
        collector.last_closed_received[symbol] = BASE + 15_000
    monkeypatch.setattr(module.time, "monotonic", lambda: 15)
    monkeypatch.setattr(module, "now_ms", lambda: BASE + 15_000)
    collector._heartbeat()
    row = collector.db.execute("SELECT * FROM sessions").fetchone()
    assert row["observed_seconds"] == 115
    assert row["healthy_seconds"] == 100
    assert collector._healthy is True
    assert collector._interval_fault is False


def test_tick_callback_only_emits_closed_bars_and_new_real_quote_ids(collector):
    ticks = []
    collector.tick_callback = ticks.append
    open_bar = kline(closed=False)
    open_bar["data"]["E"] = BASE + 30_000
    collector.handle_message(open_bar, BASE + 30_000)
    assert not ticks
    collector.handle_message(quote(1), BASE + 59_990)
    collector.handle_message(quote(1), BASE + 59_991)
    collector.handle_message(kline(), BASE + 60_010)
    collector.handle_message(kline(), BASE + 60_011)
    assert [tick["kind"] for tick in ticks] == ["quote", "closed_bar"]
    assert ticks[0]["quotes"]["BTCUSDT"]["update_id"] == 1
    assert ticks[0]["quotes"]["BTCUSDT"]["received_us"] == (BASE + 59_990) * 1000
    assert ticks[0]["quotes"]["BTCUSDT"]["exchange_event_us"] is None
    assert ticks[1]["bar"]["available_us"] == (BASE + 60_010) * 1000
    assert ticks[1]["bar"]["open_us"] == BASE * 1000
    assert ticks[1]["bar"]["close_us"] == (BASE + MINUTE_MS) * 1000
    assert ticks[1]["bar"]["source_close_us"] == (BASE + MINUTE_MS - 1) * 1000
    assert ticks[1]["bar"]["close"] == 101.0
    assert ticks[1]["health"]["live_session"] is False


def test_tick_snapshot_is_detached_and_stale_quote_is_not_marked_fresh(collector):
    ticks = []
    collector.tick_callback = ticks.append
    collector.handle_message(quote(1), BASE + 100)
    ticks[0]["quotes"]["BTCUSDT"]["bid"] = 0
    collector.handle_message(quote(2, symbol="ETHUSDT"), BASE + 3_101)
    assert ticks[1]["quotes"]["BTCUSDT"]["bid"] == 100.0
    assert ticks[1]["quotes"]["BTCUSDT"]["fresh"] is False
    assert ticks[1]["quotes"]["ETHUSDT"]["fresh"] is True
    assert ticks[1]["health"]["healthy"] is False
    assert collector.latest_quotes["BTCUSDT"]["bid"] == 100.0


def test_callback_uses_instant_health_and_never_invokes_full_disk_scan(collector, monkeypatch):
    ticks = []
    collector.tick_callback = ticks.append
    collector.session_id = collector.db.execute(
        "INSERT INTO sessions(started_ms,state,endpoint) VALUES(?,'RUNNING',?)",
        (BASE, module.STREAM_URL),
    ).lastrowid
    collector.db.commit()
    collector._connected = True
    collector._clock_offset = 0
    for symbol in module.SYMBOLS:
        collector.last_quote_received[symbol] = BASE + 60_000
        collector.last_kline_received[symbol] = BASE + 60_000
        collector.last_closed_received[symbol] = BASE + 60_000

    def no_slow_check(**kwargs):
        raise AssertionError("No per-tick full scan")

    monkeypatch.setattr(module.disk, "check", no_slow_check)
    collector.handle_message(quote(1), BASE + 60_001)
    assert ticks[-1]["health"]["healthy"] is True
    assert ticks[-1]["health"]["qualification"]["qualified_72h"] is False
    collector.last_quote_received["ETHUSDT"] = BASE
    collector.handle_message(quote(2), BASE + 60_002)
    assert ticks[-1]["health"]["healthy"] is False
    assert "ETHUSDT: quote is absent or stale" in ticks[-1]["health"]["reasons"]


def test_callback_failure_stops_observation_instead_of_silently_dropping_paper_updates(collector):
    def broken(tick):
        raise RuntimeError("paper persistence failed")

    collector.tick_callback = broken
    with pytest.raises(CollectorStopped, match="paper persistence failed"):
        collector.handle_message(quote(1), BASE + 100)
    assert collector._fatal_kind == "callback"
    assert (
        collector.db.execute("SELECT COUNT(*) FROM events WHERE kind='callback_stop'").fetchone()[0]
        == 1
    )
    with pytest.raises(CollectorStopped):
        collector.handle_message(quote(2), BASE + 101)


def test_invalid_quote_depth_cannot_reach_paper_fill_callback(collector):
    ticks = []
    collector.tick_callback = ticks.append
    bad = quote(1)
    bad["data"]["A"] = "NaN"
    with pytest.raises(ValueError, match="quote quantity"):
        collector.handle_message(bad, BASE + 100)
    assert not ticks


def test_tick_health_carries_real_disk_guard_and_heartbeat_evidence(collector, monkeypatch):
    ticks = []
    collector.tick_callback = ticks.append
    collector.session_id = collector.db.execute(
        "INSERT INTO sessions(started_ms,state,endpoint) VALUES(?,'RUNNING',?)",
        (BASE, module.STREAM_URL),
    ).lastrowid
    collector.db.commit()
    monkeypatch.setattr(module, "now_ms", lambda: BASE + 60_010)
    collector.guard(force=True)
    collector._heartbeat()
    collector.handle_message(quote(1), BASE + 60_010)
    health = ticks[-1]["health"]
    assert health["disk"]["status"] == "OK"
    assert health["disk"]["asof_ms"] == BASE + 60_010
    assert health["heartbeat_ms"] == BASE + 60_010
    assert health["qualification"]["asof_ms"] == BASE + 60_010
    assert health["disk"]["check_kind"] == "injected_guard"


def test_pre_set_external_stop_event_finishes_without_network_open(collector, monkeypatch):
    monkeypatch.setattr(module.disk, "check", guard)

    def network_forbidden(*args, **kwargs):
        raise AssertionError("A requested stop must not open the market stream")

    monkeypatch.setattr(module.websockets, "connect", network_forbidden)

    async def perform():
        stop = asyncio.Event()
        stop.set()
        result = await collector.run(stop_event=stop)
        assert result["state"] == "STOPPED"
        assert not result["qualified_72h"]

    asyncio.run(perform())
    assert (
        collector.db.execute("SELECT COUNT(*) FROM events WHERE kind='connect_attempt'").fetchone()[
            0
        ]
        == 0
    )


def test_first_genuine_ws_bar_after_rest_repair_emits_once_preserving_first_source(collector):
    ticks = []
    collector.tick_callback = ticks.append
    bar = kline()["data"]["k"]
    collector._bar("BTCUSDT", bar, BASE + 60_005, "rest", None)
    assert not ticks
    assert collector.handle_message(kline(), BASE + 60_010)
    assert not collector.handle_message(kline(), BASE + 60_011)
    assert len(ticks) == 1
    assert ticks[0]["kind"] == "closed_bar"
    assert ticks[0]["bar"]["available_us"] == (BASE + 60_010) * 1000
    persisted = collector.db.execute("SELECT * FROM closed_bars").fetchone()
    assert persisted["source"] == "rest"
    assert persisted["received_ms"] == BASE + 60_005
    assert persisted["websocket_received_ms"] == BASE + 60_010
