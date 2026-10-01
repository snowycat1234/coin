import asyncio
import gzip
import hashlib
import json
import tempfile
from dataclasses import replace
from pathlib import Path

import pytest

from quant.microstructure import (
    AGG_GAP,
    BASELINE_RESET,
    CARRIED,
    CLOCK,
    DISCONNECTED,
    FEATURES,
    MISSING,
    NO_QUOTE,
    SECOND,
    STALE_QUOTE,
    MicrostructureCollector,
    MicrostructureConfig,
    MicrostructureStopped,
    RawRing,
    aggregate_seconds,
    compact_frame,
    ofi_l1,
    read_microstructure_status,
)
from quant.paths import ROOT, STATE, utc_now_us


def guard(**_):
    return {"status": "OK"}


@pytest.fixture
def folder():
    STATE.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="micro-test-", dir=STATE) as database:
        with tempfile.TemporaryDirectory(prefix="micro-test-", dir=ROOT / ".cache/tmp") as files:
            yield Path(database), Path(files)


def config(folder, **changes):
    return MicrostructureConfig(
        db_path=folder[0] / "micro.sqlite3", store=folder[1], mode="engineering", **changes
    )


def quote(identity, bid="100", ask="102", bq="10", aq="20", symbol="BTCUSDT"):
    return {"u": identity, "s": symbol, "b": bid, "a": ask, "B": bq, "A": aq}


def trade(identity, stamp, *, maker=False, price="100", qty="2"):
    return {
        "e": "aggTrade",
        "E": stamp // 1000,
        "T": stamp // 1000,
        "s": "BTCUSDT",
        "a": identity,
        "p": price,
        "q": qty,
        "m": maker,
        "f": identity,
        "l": identity,
    }


def records(writer, interval=1, symbol="BTCUSDT"):
    return [
        body
        for row in writer.db.execute("SELECT payload FROM outbox WHERE interval_s=?", (interval,))
        if (body := json.loads(row[0]))["symbol"] == symbol
    ]


@pytest.mark.parametrize(
    "bid,ask,bq,aq,expected",
    [
        (100, 102, 13, 18, 5),  # Same prices: +3 bid, -2 ask.
        (101, 102, 13, 20, 13),  # Bid improves: new bid size.
        (99, 102, 13, 20, -10),  # Bid retreats: old bid removed.
        (100, 101, 10, 18, -18),  # Ask improves: new ask size.
        (100, 103, 10, 18, 20),  # Ask retreats: old ask removed.
        (101, 103, 13, 18, 33),  # Both sides change in one received snapshot.
    ],
)
def test_standard_ofi_all_indicator_cases(bid, ask, bq, aq, expected):
    old = {"bid": 100, "ask": 102, "bid_qty": 10, "ask_qty": 20}
    new = {"bid": bid, "ask": ask, "bid_qty": bq, "ask_qty": aq}
    assert ofi_l1(old, new) == expected


def test_seventeen_features_aggressor_and_cross_second_ofi(folder):
    writer = MicrostructureCollector(config(folder), disk_check=guard)
    start = utc_now_us() // (60 * SECOND) * 60 * SECOND
    try:
        writer.set_connected(True, received_us=start + 100)
        writer.ingest(quote(1), start + 200)
        writer.ingest(trade(1, start + 300, maker=False), start + 300)
        writer.ingest(trade(2, start + 400, maker=True, price="102", qty="1"), start + 400)
        writer.ingest(quote(9, bq="13", aq="18"), start + SECOND + 200)
        writer.advance(start + 2 * SECOND)
        first, second = records(writer)
        assert set(FEATURES).issubset(first) and len(FEATURES) == 17
        assert first["aggressive_buy_notional"] == 200
        assert first["aggressive_sell_notional"] == 102
        assert first["trade_flow_imbalance"] == pytest.approx(98 / 302)
        assert first["trade_vwap"] == pytest.approx(302 / 3)
        assert first["event_first_us"] == start
        assert first["received_first_us"] == start + 200
        assert first["available_us"] >= first["close_us"] == start + SECOND
        assert second["available_us"] >= second["close_us"] == start + 2 * SECOND
        assert second["OFI_L1"] == 5 and not second["quality"] & AGG_GAP
        assert second["quote_update_count"] == 1
        assert second["L1_imbalance_last"] == pytest.approx(-5 / 31)
        assert second["microprice_offset_bps_mean"] < 0
    finally:
        writer.close()


def test_duplicate_id_does_not_double_count_changed_id_is_fatal(folder):
    writer = MicrostructureCollector(config(folder), disk_check=guard)
    start = utc_now_us() // SECOND * SECOND
    try:
        writer.set_connected(True, received_us=start)
        assert writer.ingest(quote(1), start + 1)
        assert not writer.ingest(quote(1), start + 2)
        assert writer.ingest(trade(1, start + 3), start + 3)
        assert not writer.ingest(trade(1, start + 3), start + 4)
        writer.advance(start + SECOND)
        row = records(writer)[0]
        assert row["quote_update_count"] == row["agg_trade_count"] == 1
        assert writer.status()["duplicate_events"] == 2
        with pytest.raises(MicrostructureStopped, match="changed content"):
            writer.ingest(quote(1, bq="12"), start + SECOND + 1)
        assert writer.status()["state"] == "STOP"
    finally:
        writer.close()


def test_trade_gap_is_audited_and_not_repaired_as_received(folder):
    writer = MicrostructureCollector(config(folder), disk_check=guard)
    start = utc_now_us() // SECOND * SECOND
    try:
        writer.set_connected(True, received_us=start)
        writer.ingest(quote(1), start + 1)
        writer.ingest(trade(10, start + 2), start + 2)
        writer.ingest(trade(12, start + 3), start + 3)
        writer.advance(start + SECOND)
        row = records(writer)[0]
        assert row["agg_trade_count"] == 2 and row["quality"] & AGG_GAP
        assert row["valid_seconds"] == 0
        event = writer.db.execute("SELECT payload FROM audit WHERE kind='AGG_ID_GAP'").fetchone()
        assert json.loads(event[0])["from_received_us"] == start + 2
    finally:
        writer.close()


def test_no_event_seconds_carry_explicitly_then_expire_not_fill_means(folder):
    writer = MicrostructureCollector(config(folder), disk_check=guard)
    start = utc_now_us() // SECOND * SECOND
    try:
        writer.set_connected(True, received_us=start)
        writer.ingest(quote(1), start + 500000)
        writer.advance(start + 4 * SECOND)
        rows = records(writer)
        assert rows[1]["quality"] & NO_QUOTE and rows[1]["quality"] & CARRIED
        assert rows[1]["mid"] == 101 and rows[1]["bid_qty_mean"] is None
        assert rows[2]["mid"] is None and rows[2]["quality"] & STALE_QUOTE
        assert rows[2]["agg_trade_count"] == 0 and rows[2]["trade_vwap"] is None
        assert rows[2]["realized_return_1s"] is None
    finally:
        writer.close()


def test_disconnect_seconds_remain_invalid_and_ofi_restarts(folder):
    writer = MicrostructureCollector(config(folder), disk_check=guard)
    start = utc_now_us() // (60 * SECOND) * 60 * SECOND
    try:
        writer.set_connected(True, received_us=start)
        writer.ingest(quote(1), start + 100)
        writer.set_connected(False, received_us=start + SECOND, reason="synthetic_loss")
        writer.set_connected(True, received_us=start + 4 * SECOND, reason="synthetic_reconnect")
        writer.ingest(quote(2, bid="110", ask="111", bq="50"), start + 4 * SECOND + 100)
        writer.advance(start + 5 * SECOND)
        rows = records(writer)
        assert all(r["quality"] & DISCONNECTED for r in rows[1:4])
        assert rows[4]["OFI_L1"] == 0 and rows[4]["quality"] & BASELINE_RESET
        aggregate = records(writer, 5)[0]
        assert aggregate["quality"] & DISCONNECTED
        assert aggregate["quote_update_count"] == 2 and aggregate["known_seconds"] == 5
    finally:
        writer.close()


def test_semantic_aggregation_vwap_flow_stats_and_missing_quality(folder):
    writer = MicrostructureCollector(config(folder), disk_check=guard)
    start = utc_now_us() // (60 * SECOND) * 60 * SECOND
    try:
        writer.set_connected(True, received_us=start)
        for index in range(5):
            stamp = start + index * SECOND + 200000
            writer.ingest(quote(index + 1, bq=str(index + 10)), stamp)
            writer.ingest(
                trade(
                    index + 1,
                    stamp,
                    maker=index % 2 == 0,
                    price=str(100 + index),
                    qty=str(index + 1),
                ),
                stamp,
            )
        writer.advance(start + 5 * SECOND)
        rows, actual = records(writer), records(writer, 5)[0]
        assert actual["bid_qty_mean_mean"] == 12
        assert actual["bid_qty_mean_std"] == pytest.approx(2**0.5)
        assert actual["bid_qty_mean_min"] == 10 and actual["bid_qty_mean_max"] == 14
        assert actual["bid_qty_mean_last"] == 14
        assert actual["trade_vwap"] == pytest.approx(
            sum((100 + i) * (i + 1) for i in range(5)) / 15
        )
        assert actual["agg_trade_count"] == 5
        assert actual["OFI_L1"] == 4
        assert actual["realized_return"] is None
        assert aggregate_seconds(rows[:3], 5)["quality"] & MISSING
    finally:
        writer.close()


def test_long_observation_gap_is_sparse_audited_and_never_backfilled(folder):
    writer = MicrostructureCollector(config(folder), disk_check=guard)
    start = utc_now_us() // SECOND * SECOND
    try:
        writer.set_connected(True, received_us=start)
        writer.ingest(quote(1), start + 100)
        writer.advance(start + 7000 * SECOND)
        assert not records(writer)
        writer.advance(start + 7001 * SECOND)
        assert len(records(writer)) == 1
        assert records(writer)[0]["quality"] & MISSING
        assert records(writer)[0]["quality"] & CLOCK
        assert (
            writer.db.execute("SELECT COUNT(*) FROM audit WHERE kind='OBSERVATION_GAP'").fetchone()[
                0
            ]
            == 1
        )
    finally:
        writer.close()


def test_restart_native_recovery_export_and_mode_binding(folder):
    cfg = config(folder)
    start = utc_now_us() // SECOND * SECOND
    writer = MicrostructureCollector(cfg, disk_check=guard)
    writer.set_connected(True, received_us=start)
    writer.ingest(quote(1), start + 100)
    writer.advance(start + SECOND)
    writer.close()
    original_files = list((cfg.store / "features").rglob("*.parquet"))
    digests = {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in original_files}
    writer = MicrostructureCollector(cfg, disk_check=guard)
    try:
        writer.set_connected(True, received_us=start + 2 * SECOND)
        assert not writer.ingest(quote(1), start + 2 * SECOND + 100)
        writer.ingest(quote(2, bq="50"), start + 2 * SECOND + 200)
        writer.advance(start + 3 * SECOND)
        assert records(writer)[0]["OFI_L1"] == 0
        assert (
            writer.db.execute("SELECT COUNT(*) FROM audit WHERE kind='RESTART_GAP'").fetchone()[0]
            == 1
        )
        assert writer.verify_audit()
    finally:
        writer.close()
    assert {p: hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in digests} == digests
    with pytest.raises(MicrostructureStopped, match="provenance/schema"):
        MicrostructureCollector(replace(cfg, mode="live"), initial_disk={"status": "OK"})


def test_atomic_orphan_export_retries_without_duplicate_or_overwrite(folder):
    writer = MicrostructureCollector(config(folder), disk_check=guard)
    start = utc_now_us() // (60 * SECOND) * 60 * SECOND
    try:
        writer.set_connected(True, received_us=start)
        writer.ingest(quote(1), start + 100)
        writer.advance(start + SECOND)
        batch = writer.db.execute("SELECT * FROM outbox ORDER BY seq").fetchall()
        target = (
            writer.config.store
            / "features/1s"
            / f"batch-{batch[0]['seq']:013d}-{batch[-1]['seq']:013d}.parquet"
        )
        target.parent.mkdir(parents=True)
        compact_frame([json.loads(r["payload"]) for r in batch]).write_parquet(
            target, compression="zstd", compression_level=3, statistics=False
        )
        digest = hashlib.sha256(target.read_bytes()).hexdigest()
        writer.export()
        assert writer.status()["pending_rows"] == 0
        assert writer.status()["feature_rows"] == 2
        assert hashlib.sha256(target.read_bytes()).hexdigest() == digest
        writer.export()
        assert writer.status()["feature_rows"] == 2
    finally:
        writer.close()


def test_ring_retention_hard_cap_does_not_delete_feature_or_audit(folder):
    cfg = config(folder, raw_cap_bytes=8000)
    ring = RawRing(cfg.store / "raw", cfg)
    (cfg.store / "feature.parquet").write_bytes(b"preserve")
    now = utc_now_us()
    for index in range(400):
        ring.append(
            {
                "received_us": now + index * SECOND,
                "random": hashlib.sha256(str(index).encode()).hexdigest() * 5,
            }
        )
        ring.flush(now + index * SECOND)
        assert sum(p.stat().st_size for p in ring.folder.glob("*.gz")) <= cfg.raw_cap_bytes
    ring.close_shard()
    for file in ring.folder.glob("*.gz"):
        with gzip.open(file, "rt") as reader:
            assert all(json.loads(line)["received_us"] >= now for line in reader)
    ring.prune(now + 2 * 86400 * SECOND)
    assert not list(ring.folder.glob("*.gz"))
    assert (cfg.store / "feature.parquet").read_bytes() == b"preserve"


def test_feature_cap_freezes_without_deleting_existing_evidence(folder):
    writer = MicrostructureCollector(config(folder, feature_cap_bytes=1), disk_check=guard)
    start = utc_now_us() // SECOND * SECOND
    try:
        writer.set_connected(True, received_us=start)
        writer.ingest(quote(1), start + 100)
        writer.advance(start + SECOND)
        with pytest.raises(MicrostructureStopped, match="never deleted"):
            writer.export()
        assert writer.status()["state"] == "STOP" and not writer.status()["alpha_eligible"]
        assert writer.status()["pending_rows"] == 2
        assert not list(writer.config.store.rglob("*.partial"))
        assert not list(writer.config.store.rglob("*.parquet"))
        assert (
            writer.db.execute(
                "SELECT COUNT(*) FROM audit WHERE kind='FEATURE_CAP_STOP'"
            ).fetchone()[0]
            == 1
        )
    finally:
        writer.close()


def test_disk_guard_failed_stops_before_ingest(folder):
    failed = []

    def dynamic_guard(**_):
        if failed:
            raise RuntimeError("synthetic disk exhaustion")
        return {"status": "OK"}

    writer = MicrostructureCollector(config(folder), disk_check=dynamic_guard)
    try:
        failed.append(True)
        writer._last_guard = 0
        with pytest.raises(MicrostructureStopped, match="DISK"):
            writer.ingest(quote(1))
        assert writer.accepted == 0 and writer.status()["state"] == "STOP"
    finally:
        writer.close()


def test_store_single_writer_and_audit_immutable(folder):
    writer = MicrostructureCollector(config(folder), disk_check=guard)
    try:
        with pytest.raises(MicrostructureStopped, match="Another writer"):
            MicrostructureCollector(
                replace(config(folder), db_path=folder[0] / "other.sqlite3"), disk_check=guard
            )
        with pytest.raises(Exception, match="append only"):
            writer.db.execute("DELETE FROM audit")
        writer.db.rollback()
        assert writer.verify_audit()
    finally:
        writer.close()


def test_nullable_parquet_schema_is_stable_and_engineering_cannot_go_network(folder):
    writer = MicrostructureCollector(config(folder), disk_check=guard)
    start = utc_now_us() // SECOND * SECOND
    try:
        writer.set_connected(True, received_us=start)
        writer.advance(start + SECOND)
        empty = compact_frame(records(writer))
        writer.ingest(quote(1), start + SECOND + 100)
        writer.ingest(trade(1, start + SECOND + 200), start + SECOND + 200)
        writer.advance(start + 2 * SECOND)
        mixed = compact_frame(records(writer)[1:])
        assert empty.schema == mixed.schema
        with pytest.raises(MicrostructureStopped, match="cannot request real"):
            asyncio.run(writer.run(0))
    finally:
        writer.close()


def test_resource_limits_cannot_be_increased(folder):
    for changes in (
        {"raw_cap_bytes": 4_000_000_001},
        {"raw_retention_us": 86401 * SECOND},
        {"feature_cap_bytes": 8_000_000_001},
        {"export_seconds": 601},
    ):
        with pytest.raises(ValueError):
            config(folder, **changes)


def test_read_only_status_never_constructs_writer_or_touches_network(folder, monkeypatch):
    writer = MicrostructureCollector(config(folder), disk_check=guard)
    start = utc_now_us() // SECOND * SECOND
    writer.set_connected(True, received_us=start)
    writer.ingest(quote(1), start + 100)
    writer.advance(start + SECOND)
    before = writer.db.execute("SELECT COUNT(*) FROM audit").fetchone()[0]

    def forbidden(*_, **__):
        raise AssertionError("Read status invoked a mutable writer/network path")

    monkeypatch.setattr(MicrostructureCollector, "__init__", forbidden)
    monkeypatch.setattr(MicrostructureCollector, "guard", forbidden)
    monkeypatch.setattr("quant.microstructure.websockets.connect", forbidden)
    try:
        result = read_microstructure_status(writer.config.db_path)
        assert result["read_only"] and not result["alpha_eligible"]
        assert result["checkpoint"]["accepted_events"] == 1
        assert writer.db.execute("SELECT COUNT(*) FROM audit").fetchone()[0] == before
    finally:
        monkeypatch.undo()
        writer.close()
    assert read_microstructure_status(writer.config.db_path)["state"] == "STOPPED"


def test_feature_cap_preserves_previously_committed_parquet_bytes(folder):
    writer = MicrostructureCollector(config(folder), disk_check=guard)
    start = utc_now_us() // (60 * SECOND) * 60 * SECOND
    try:
        writer.set_connected(True, received_us=start)
        writer.ingest(quote(1), start + 100)
        writer.advance(start + SECOND)
        writer.export()
        original = {
            p: hashlib.sha256(p.read_bytes()).hexdigest()
            for p in writer.config.store.rglob("*.parquet")
        }
        used = writer.status()["feature_bytes"]
        writer.config = replace(writer.config, feature_cap_bytes=used + 1)
        writer.ingest(quote(2), start + SECOND + 100)
        writer.advance(start + 2 * SECOND)
        with pytest.raises(MicrostructureStopped, match="never deleted"):
            writer.export()
        assert {
            p: hashlib.sha256(p.read_bytes()).hexdigest()
            for p in writer.config.store.rglob("*.parquet")
        } == original
        assert not writer.connected and writer.status()["state"] == "STOP"
    finally:
        writer.close()


def test_all_resampling_frequencies_are_closed_and_partial_restart_is_explicit(folder):
    writer = MicrostructureCollector(config(folder), disk_check=guard)
    start = utc_now_us() // (60 * SECOND) * 60 * SECOND
    try:
        writer.set_connected(True, received_us=start)
        for index in range(60):
            writer.ingest(quote(index + 1), start + index * SECOND + 100)
        writer.advance(start + 60 * SECOND)
        for interval, expected in ((5, 12), (30, 2), (60, 1)):
            grouped = records(writer, interval)
            assert len(grouped) == expected
            assert sum(row["quote_update_count"] for row in grouped) == 60
            assert all(row["known_seconds"] == interval for row in grouped)
        assert records(writer, 60)[0]["received_last_us"] == start + 59 * SECOND + 100
    finally:
        writer.close()


def test_failed_startup_releases_both_native_writer_locks(folder):
    cfg = config(folder)
    writer = MicrostructureCollector(cfg, disk_check=guard)
    writer.close()
    # A mismatched database/source may not claim the existing feature folder.
    with pytest.raises(MicrostructureStopped, match="another database"):
        MicrostructureCollector(replace(cfg, db_path=folder[0] / "wrong.sqlite3"), disk_check=guard)
    writer = MicrostructureCollector(cfg, disk_check=guard)
    writer.close()


@pytest.mark.parametrize("name", ["ROOT", "STATE"])
def test_resource_aliases_cannot_redirect_files_to_C(folder, monkeypatch, name):
    monkeypatch.setattr(f"quant.microstructure.{name}", Path("/mnt/c/forbidden-project"))
    with pytest.raises(MicrostructureStopped, match="fixed D ROOT"):
        MicrostructureCollector(config(folder), disk_check=guard)
