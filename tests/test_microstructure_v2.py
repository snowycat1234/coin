import ast
import asyncio
import gzip
import hashlib
import importlib.util
import json
import sqlite3
import sys
import tempfile
from dataclasses import replace
from pathlib import Path

import polars as pl
import pytest

from quant.paths import ROOT, STATE, utc_now_us

SPEC = importlib.util.spec_from_file_location(
    "quant._isolated_microstructure_v2_tests", ROOT / "src/quant/microstructure_v2.py"
)
module = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = module
SPEC.loader.exec_module(module)
AGG_GAP, BASELINE_RESET, CARRIED, CLOCK = (
    module.AGG_GAP,
    module.BASELINE_RESET,
    module.CARRIED,
    module.CLOCK,
)
DISCONNECTED, FEATURES, MISSING, NO_QUOTE = (
    module.DISCONNECTED,
    module.FEATURES,
    module.MISSING,
    module.NO_QUOTE,
)
SECOND, STALE_QUOTE = module.SECOND, module.STALE_QUOTE
MicrostructureCollector = module.MicrostructureCollector
MicrostructureConfig, MicrostructureStopped = (
    module.MicrostructureConfig,
    module.MicrostructureStopped,
)
RawRing, aggregate_seconds, compact_frame = (
    module.RawRing,
    module.aggregate_seconds,
    module.compact_frame,
)
ofi_l1, read_microstructure_status = module.ofi_l1, module.read_microstructure_status


def guard(**_):
    return {"status": "OK"}


@pytest.fixture
def folder(monkeypatch):
    STATE.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="micro-test-", dir=STATE) as database:
        with tempfile.TemporaryDirectory(prefix="micro-v2-test-", dir=STATE) as files:
            fixture_root = Path(files)
            monkeypatch.setattr(module, "ROOT", fixture_root)

            def fixture_layout_guard():
                # This hook exists solely in the isolated engineering test module.
                if module.ROOT != fixture_root or not module.STATE.resolve().is_relative_to(STATE):
                    raise MicrostructureStopped("Resource paths must use fixed D ROOT fixture")

            monkeypatch.setattr(module, "_layout_guard", fixture_layout_guard)
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
        assert set(FEATURES).issubset(first) and len(FEATURES) == 19
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
        event = writer.db.execute(
            "SELECT payload FROM audit WHERE kind='RAW_TRADE_ID_GAP'"
        ).fetchone()
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
    monkeypatch.setattr(module.websockets, "connect", forbidden)
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
    monkeypatch.setattr(module, name, Path("/mnt/c/forbidden-project"))
    with pytest.raises(MicrostructureStopped, match="fixed D ROOT"):
        MicrostructureCollector(config(folder), disk_check=guard)


def audit_payloads(writer, kind):
    return [
        json.loads(row[0])
        for row in writer.db.execute("SELECT payload FROM audit WHERE kind=? ORDER BY seq", (kind,))
    ]


def raw_trade(a, stamp, first_raw, last_raw, **kwargs):
    return {**trade(a, stamp, **kwargs), "f": first_raw, "l": last_raw}


@pytest.mark.parametrize(
    "scenario",
    ["continuous", "a_jump", "raw_gap", "duplicate", "overlap", "out_of_order", "reconnect"],
)
def test_a09_seven_required_trade_scenarios_use_raw_ids_without_recounting(folder, scenario):
    writer = MicrostructureCollector(config(folder), disk_check=guard)
    start = utc_now_us() // (60 * SECOND) * 60 * SECOND
    try:
        writer.set_connected(True, received_us=start)
        writer.advance(start + SECOND)
        old = raw_trade(10, start + SECOND + 200, 100, 105)
        writer.ingest(quote(1), start + SECOND + 100)
        assert writer.ingest(old, start + SECOND + 200)
        if scenario == "reconnect":
            writer.set_connected(False, received_us=start + SECOND + 300)
            writer.set_connected(True, received_us=start + SECOND + 400)
        stamp = start + 2 * SECOND + 200
        writer.ingest(quote(2), stamp - 100)
        new = raw_trade(11, stamp, 106, 109)
        if scenario == "a_jump":
            new["a"] = 18
        elif scenario == "raw_gap":
            new.update(a=18, f=108, l=111)
        elif scenario == "duplicate":
            new = old
        elif scenario == "overlap":
            new.update(f=104, l=108)
        elif scenario == "out_of_order":
            new.update(a=9, f=90, l=99)
        accepted = writer.ingest(new, stamp)
        writer.advance(start + 3 * SECOND)
        row = records(writer)[2]
        assert accepted is (scenario not in {"duplicate", "overlap", "out_of_order"})
        assert row["agg_trade_count"] == int(accepted)
        assert row["aggressive_buy_notional"] == (200 if accepted else 0)
        high = writer.ids["BTCUSDT:trade"]
        assert high["last_raw_trade_id"] == (new["l"] if accepted else 105)
        assert high["agg_id_high_water"] >= 10
        if scenario == "raw_gap":
            assert row["quality"] & AGG_GAP and row["valid_seconds"] == 0
            gap = audit_payloads(writer, "RAW_TRADE_ID_GAP")[0]
            assert gap["missing_from_raw_id"] == 106 and gap["missing_to_raw_id"] == 107
            assert gap["from_received_us"] == start + SECOND + 200
        else:
            assert not row["quality"] & AGG_GAP
            assert not audit_payloads(writer, "RAW_TRADE_ID_GAP")
        if scenario == "a_jump":
            assert row["valid_seconds"] == 1
            jump = audit_payloads(writer, "AGG_ID_JUMP_UNCONFIRMED")[0]
            assert jump["raw_ids_contiguous"] and not jump["bucket_invalidated"]
        elif scenario == "duplicate":
            assert len(audit_payloads(writer, "AGG_TRADE_DUPLICATE")) == 1
        elif scenario == "overlap":
            overlap = audit_payloads(writer, "RAW_TRADE_OVERLAP")[0]
            assert (
                overlap["whole_aggregate_rejected"]
                and overlap["unseen_overlap_tail_quantity_unknown"]
            )
            assert row["quality"] & module.LATE
        elif scenario == "out_of_order":
            assert len(audit_payloads(writer, "RAW_TRADE_OUT_OF_ORDER")) == 1
            assert row["quality"] & module.LATE
        elif scenario == "reconnect":
            assert len(audit_payloads(writer, "DISCONNECTED")) == 1
            assert high["f"] == 106 and high["l"] == 109
        assert writer.verify_audit()
    finally:
        writer.close()


@pytest.mark.parametrize(
    "a,first_raw,last_raw,expected_gap", [(11, 109, 111, True), (5, 106, 108, False)]
)
def test_continuous_a_raw_gap_and_decreasing_a_continuous_raw_two_sided_boundary(
    folder, a, first_raw, last_raw, expected_gap
):
    writer = MicrostructureCollector(config(folder), disk_check=guard)
    start = utc_now_us() // SECOND * SECOND
    try:
        writer.set_connected(True, received_us=start)
        writer.ingest(raw_trade(10, start + 100, 100, 105), start + 100)
        writer.advance(start + SECOND)
        writer.ingest(quote(1), start + SECOND + 100)
        assert writer.ingest(
            raw_trade(a, start + SECOND + 200, first_raw, last_raw), start + SECOND + 200
        )
        writer.advance(start + 2 * SECOND)
        row = records(writer)[1]
        assert bool(row["quality"] & AGG_GAP) is expected_gap
        assert row["agg_trade_count"] == 1
        high = writer.ids["BTCUSDT:trade"]
        assert high["last_agg_id"] == a and high["last_raw_trade_id"] == last_raw
        assert high["agg_id_high_water"] == max(10, a)
        if a < 10:
            assert (
                row["valid_seconds"] == 1
                and len(audit_payloads(writer, "AGG_ID_JUMP_UNCONFIRMED")) == 1
            )
    finally:
        writer.close()


@pytest.mark.parametrize("field", ["f", "l", "E", "T"])
@pytest.mark.parametrize("bad", [True, False, -1, 1.5, "2", None])
def test_trade_original_fields_require_strict_nonnegative_integers_even_before_duplicate(
    folder, field, bad
):
    writer = MicrostructureCollector(config(folder), disk_check=guard)
    start = utc_now_us() // SECOND * SECOND
    try:
        writer.set_connected(True, received_us=start)
        value = raw_trade(10, start + 100, 100, 105)
        value[field] = bad
        with pytest.raises(ValueError, match="actual integer"):
            writer.ingest(value, start + 100)
        assert "BTCUSDT:trade" not in writer.ids and writer.accepted == 0
        assert writer.buckets["BTCUSDT"]["base"] == 0
    finally:
        writer.close()


@pytest.mark.parametrize("field,value", [("f", 106), ("E", 0)])
def test_raw_range_and_original_exchange_time_order_are_validated(folder, field, value):
    writer = MicrostructureCollector(config(folder), disk_check=guard)
    start = utc_now_us() // SECOND * SECOND
    try:
        writer.set_connected(True, received_us=start)
        payload = raw_trade(10, start + 100, 100, 105)
        payload[field] = value
        with pytest.raises(ValueError, match="Malformed"):
            writer.ingest(payload, start + 100)
        assert writer.accepted == 0 and not writer.ids
    finally:
        writer.close()


def test_same_aggregate_id_changed_content_still_stops_without_counting_conflict(folder):
    writer = MicrostructureCollector(config(folder), disk_check=guard)
    start = utc_now_us() // SECOND * SECOND
    try:
        writer.set_connected(True, received_us=start)
        original = raw_trade(10, start + 100, 100, 105)
        writer.ingest(original, start + 100)
        with pytest.raises(MicrostructureStopped, match="changed content"):
            writer.ingest({**original, "q": "3"}, start + 200)
        assert writer.accepted == 1 and writer.buckets["BTCUSDT"]["base"] == 2
        assert writer.status()["fatal"] == "IDENTITY_CONFLICT"
    finally:
        writer.close()


def test_raw_duplicate_with_new_aggregate_and_contained_overlap_are_separately_audited(folder):
    writer = MicrostructureCollector(config(folder), disk_check=guard)
    start = utc_now_us() // SECOND * SECOND
    try:
        writer.set_connected(True, received_us=start)
        writer.ingest(raw_trade(10, start + 100, 100, 110), start + 100)
        before = dict(writer.ids["BTCUSDT:trade"])
        assert not writer.ingest(raw_trade(20, start + 200, 100, 110), start + 200)
        assert not writer.ingest(raw_trade(30, start + 300, 102, 108), start + 300)
        assert writer.ids["BTCUSDT:trade"] == before
        assert writer.buckets["BTCUSDT"]["base"] == 2 and writer.duplicates == 2
        assert len(audit_payloads(writer, "RAW_TRADE_DUPLICATE")) == 1
        assert len(audit_payloads(writer, "RAW_TRADE_OVERLAP")) == 1
    finally:
        writer.close()


def test_checkpoint_preserves_raw_high_water_and_decreasing_aggregate_across_restart(folder):
    cfg = config(folder)
    start = utc_now_us() // SECOND * SECOND
    writer = MicrostructureCollector(cfg, disk_check=guard)
    writer.set_connected(True, received_us=start)
    writer.ingest(raw_trade(100, start + 100, 1000, 1005), start + 100)
    writer.ingest(raw_trade(50, start + 200, 1006, 1010), start + 200)
    writer.advance(start + SECOND)
    saved = dict(writer.ids["BTCUSDT:trade"])
    writer.close()
    writer = MicrostructureCollector(cfg, disk_check=guard)
    try:
        assert writer.ids["BTCUSDT:trade"] == saved
        assert saved["last_agg_id"] == 50 and saved["agg_id_high_water"] == 100
        assert saved["last_raw_trade_id"] == saved["l"] == 1010 and saved["f"] == 1006
        assert saved["received_us"] == start + 200
        writer.set_connected(True, received_us=start + 2 * SECOND)
        assert not writer.ingest(
            raw_trade(60, start + 2 * SECOND + 100, 1006, 1010), start + 2 * SECOND + 100
        )
        assert writer.ids["BTCUSDT:trade"] == saved
        assert writer.ingest(
            raw_trade(51, start + 2 * SECOND + 200, 1011, 1015), start + 2 * SECOND + 200
        )
        writer.advance(start + 3 * SECOND)
        assert not audit_payloads(writer, "RAW_TRADE_ID_GAP")
        assert writer.ids["BTCUSDT:trade"]["last_raw_trade_id"] == 1015
        assert writer.ids["BTCUSDT:trade"]["agg_id_high_water"] == 100
        assert writer.verify_audit()
    finally:
        writer.close()


def reconstruct(row, *, aggregate=False):
    mid = row["mid_last" if aggregate else "mid"]
    spread, depth, imbalance = (
        row["spread_bps_last"],
        row["l1_total_depth_last"],
        row["L1_imbalance_last"],
    )
    if mid is None:
        assert spread is depth is imbalance is None
        return None
    return (
        mid * (1 - spread / 20000),
        mid * (1 + spread / 20000),
        depth * (1 + imbalance) / 2,
        depth * (1 - imbalance) / 2,
    )


def test_last_bbo_reconstructs_carried_quotes_and_stale_tail_without_backtracking(folder):
    writer = MicrostructureCollector(config(folder), disk_check=guard)
    start = utc_now_us() // (60 * SECOND) * 60 * SECOND
    try:
        writer.set_connected(True, received_us=start)
        writer.ingest(
            quote(1, bid="12345.6789", ask="12345.7001", bq="0.123456789", aq="5.987654321"),
            start + 500_000,
        )
        writer.advance(start + 4 * SECOND)
        frame = compact_frame(records(writer))
        assert frame.schema["spread_bps_last"] == frame.schema["l1_total_depth_last"] == pl.Float64
        assert frame.schema["L1_imbalance_last"] == pl.Float64
        closed = frame.to_dicts()
        expected = (12345.6789, 12345.7001, 0.123456789, 5.987654321)
        for row in closed[:2]:
            assert reconstruct(row) == pytest.approx(expected, abs=1e-12)
        assert closed[1]["quality"] & CARRIED and closed[1]["bid_qty_mean"] is None
        assert closed[1]["L1_imbalance_mean"] is None and closed[1]["L1_imbalance_last"] is not None
        for row in closed[2:]:
            assert reconstruct(row) is None and row["quality"] & STALE_QUOTE
        grouped = aggregate_seconds(closed, 5)
        assert reconstruct(grouped, aggregate=True) is None  # Last stale second never backtracks.
    finally:
        writer.close()


@pytest.mark.parametrize("interval", [5, 30, 60])
def test_all_aggregate_frequencies_use_same_fresh_carried_last_second_bbo(folder, interval):
    writer = MicrostructureCollector(config(folder), disk_check=guard)
    start = utc_now_us() // (60 * SECOND) * 60 * SECOND
    try:
        writer.set_connected(True, received_us=start)
        for second in range(60):
            if (second + 1) % interval == 0:
                continue  # The terminal second is carried from the previous second.
            stamp = start + second * SECOND + 500_000
            writer.ingest(
                quote(
                    second + 1,
                    bid=str(100 + second),
                    ask=str(100.4 + second),
                    bq=str(0.1 + second),
                    aq=str(0.7 + second),
                ),
                stamp,
            )
        writer.advance(start + 60 * SECOND)
        ones = compact_frame(records(writer)).to_dicts()
        aggregates = compact_frame(records(writer, interval)).to_dicts()
        assert len(aggregates) == 60 // interval
        for group in aggregates:
            tail = next(row for row in ones if row["close_us"] == group["close_us"])
            assert tail["quality"] & CARRIED
            assert reconstruct(group, aggregate=True) == pytest.approx(reconstruct(tail), abs=1e-12)
            for field in ("spread_bps_last", "l1_total_depth_last", "L1_imbalance_last"):
                assert group[field] == tail[field]
        writer.export()
        for manifest in writer.db.execute("SELECT path,interval_s FROM manifests"):
            frame = pl.read_parquet(writer.config.store / manifest["path"])
            assert (
                frame.schema["spread_bps_last"] == frame.schema["l1_total_depth_last"] == pl.Float64
            )
    finally:
        writer.close()


def test_old_v1_marker_rejected_without_database_or_marker_mutation(folder):
    cfg = config(folder)
    ownership = {
        "database": str(cfg.db_path.resolve()),
        "mode": "engineering",
        "version": "microstructure_l1_v1",
    }
    marker = cfg.store / ".microstructure-store.json"
    marker.write_text(json.dumps(ownership))
    original = marker.read_bytes()
    with pytest.raises(MicrostructureStopped, match="provenance/schema"):
        MicrostructureCollector(cfg, disk_check=guard)
    assert marker.read_bytes() == original and not cfg.db_path.exists()


def test_foreign_v1_database_is_readonly_rejected_before_sqlite_or_marker_changes(folder):
    cfg = config(folder)
    with sqlite3.connect(cfg.db_path) as writer:
        writer.execute("CREATE TABLE state(key TEXT PRIMARY KEY,value TEXT)")
        writer.execute(
            "INSERT INTO state VALUES('binding',?)",
            (json.dumps({"version": "microstructure_l1_v1"}),),
        )
    original = cfg.db_path.read_bytes()
    with pytest.raises(MicrostructureStopped, match="not this v2"):
        MicrostructureCollector(cfg, disk_check=guard)
    assert cfg.db_path.read_bytes() == original
    assert not (cfg.store / ".microstructure-store.json").exists()
    assert not cfg.db_path.with_name(cfg.db_path.name + "-wal").exists()


def test_v2_defaults_are_new_and_frozen_v1_source_stays_byte_identical():
    assert module.VERSION == "microstructure_l1_v2"
    assert MicrostructureConfig().db_path == STATE / "microstructure_v2.sqlite3"
    assert MicrostructureConfig().store == ROOT / "data/microstructure_v2"
    assert hashlib.sha256((ROOT / "src/quant/microstructure.py").read_bytes()).hexdigest() == (
        "649a69c924cdcfc4e85dca37a2a6c4958993f3f3365e04b3f10372f8875ddbb4"
    )


@pytest.mark.parametrize(
    "bad_field,bad_value", [("last_raw_trade_id", 999), ("agg_id_high_water", 0), ("f", True)]
)
def test_restart_rejects_corrupt_persisted_raw_or_aggregate_highwater(folder, bad_field, bad_value):
    cfg, start = config(folder), utc_now_us() // SECOND * SECOND
    writer = MicrostructureCollector(cfg, disk_check=guard)
    writer.set_connected(True, received_us=start)
    writer.ingest(raw_trade(10, start + 100, 100, 105), start + 100)
    writer.advance(start + SECOND)
    writer.close()
    with sqlite3.connect(cfg.db_path) as fixture_db:
        saved = json.loads(
            fixture_db.execute("SELECT value FROM state WHERE key='checkpoint'").fetchone()[0]
        )
        saved["ids"]["BTCUSDT:trade"][bad_field] = bad_value
        fixture_db.execute("UPDATE state SET value=? WHERE key='checkpoint'", (json.dumps(saved),))
    with pytest.raises(MicrostructureStopped, match="high water"):
        MicrostructureCollector(cfg, disk_check=guard)


@pytest.mark.parametrize("name", ["database", "store"])
def test_reserved_v1_default_locations_are_refused_without_touching_them(folder, name):
    cfg = config(folder)
    cfg = (
        replace(cfg, db_path=STATE / "microstructure.sqlite3")
        if name == "database"
        else (replace(cfg, store=module.ROOT / "data/microstructure_v1"))
    )
    with pytest.raises(MicrostructureStopped, match="v1 database/store is frozen"):
        MicrostructureCollector(cfg, disk_check=guard)


def test_readonly_v2_status_rejects_foreign_binding_without_rewriting_database(folder):
    cfg = config(folder)
    writer = MicrostructureCollector(cfg, disk_check=guard)
    writer.close()
    with sqlite3.connect(cfg.db_path) as fixture_db:
        binding = json.loads(
            fixture_db.execute("SELECT value FROM state WHERE key='binding'").fetchone()[0]
        )
        binding["version"] = "microstructure_l1_v1"
        fixture_db.execute("UPDATE state SET value=? WHERE key='binding'", (json.dumps(binding),))
    original = cfg.db_path.read_bytes()
    with pytest.raises(MicrostructureStopped, match="separate frozen v2"):
        read_microstructure_status(cfg.db_path)
    assert cfg.db_path.read_bytes() == original


def test_resource_retention_and_snapshot_methods_preserve_v1_implementation_ast():
    original = ast.parse((ROOT / "src/quant/microstructure.py").read_text())
    revised = ast.parse((ROOT / "src/quant/microstructure_v2.py").read_text())
    for class_name, methods in (
        ("RawRing", None),
        (
            "MicrostructureCollector",
            {
                "guard",
                "_db_bytes",
                "_store_bytes",
                "advance",
                "export",
                "refresh_disk",
                "run",
                "close",
                "verify_audit",
            },
        ),
    ):
        old = next(
            node
            for node in original.body
            if isinstance(node, ast.ClassDef) and node.name == class_name
        )
        new = next(
            node
            for node in revised.body
            if isinstance(node, ast.ClassDef) and node.name == class_name
        )
        old_methods = {
            node.name: ast.dump(node, include_attributes=False)
            for node in old.body
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        }
        new_methods = {
            node.name: ast.dump(node, include_attributes=False)
            for node in new.body
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        }
        names = old_methods.keys() if methods is None else methods
        assert all(new_methods[name] == old_methods[name] for name in names)
