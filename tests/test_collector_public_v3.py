import asyncio
import contextlib
import fcntl
import json
import sqlite3
import tempfile
from pathlib import Path

import pytest

from quant import collector as core
from quant import collector_public_v3 as module
from quant.concurrent_budget import ConcurrentCollector, ShadowEngine
from quant.paths import STATE

BASE = 1_790_841_600_000


def ledger(**kwargs):
    return {"status": "OK"}


@pytest.fixture
def native_db():
    with tempfile.TemporaryDirectory(prefix="public-v3-tests-", dir=STATE) as folder:
        yield Path(folder) / "collector_public_v3.sqlite3"


class OfflineCollector(ConcurrentCollector):
    def __init__(self, path, *, initial_disk):
        super().__init__(path, disk_check=ledger, initial_disk=initial_disk)

    async def run(self, seconds=None, *, stop_event=None):
        self.session_id = self.db.execute(
            "INSERT INTO sessions(started_ms,state,endpoint,heartbeat_ms,observed_seconds) "
            "VALUES(?,'STOPPED',?,?,0)",
            (BASE, "engineering_no_network", BASE),
        ).lastrowid
        self.db.execute("UPDATE sessions SET ended_ms=? WHERE id=?", (BASE, self.session_id))
        self.db.commit()
        return {"state": "STOPPED", "qualified_72h": True}  # fixture cannot authorize live


async def offline(path, factory=OfflineCollector, **kwargs):
    return await module.collect_public_v3(
        1, path, engineering=True, fixture_factory=factory, fixture_disk_check=ledger, **kwargs
    )


def query(path, sql):
    with contextlib.closing(sqlite3.connect(path)) as db:
        return db.execute(sql).fetchall()


def test_independent_native_registry_has_no_financial_accounts(native_db, monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("No financial account may be constructed")

    monkeypatch.setattr(ShadowEngine, "__init__", forbidden)
    result = asyncio.run(offline(native_db))
    assert result["orders_sent"] == 0 and result["credentials_used"] is False
    assert result["qualified_72h"] is False and result["alpha_eligible"] is False
    tables = {
        row[0] for row in query(native_db, "SELECT name FROM sqlite_master WHERE type='table'")
    }
    assert tables == {
        "public_contract",
        "public_lifecycle",
        "closed_bars",
        "quote_minutes",
        "gaps",
        "events",
        "sessions",
    }
    snapshot = module.read_public_v3_status(native_db)
    assert snapshot["contract"]["engineering"] is True
    assert snapshot["contract"]["scope"] == "public_market_data_only"
    assert snapshot["state"] == "STOPPED" and snapshot["qualified_72h"] is None


@pytest.mark.parametrize("name", ["live.sqlite3", "shadow.sqlite3", "microstructure.sqlite3"])
def test_old_database_paths_are_rejected_without_opening(native_db, name):
    path = native_db.with_name(name)
    with pytest.raises(ValueError, match="independent"):
        asyncio.run(offline(path))
    assert not path.exists()


def test_prefixed_but_unowned_database_is_not_reused(native_db):
    with contextlib.closing(sqlite3.connect(native_db)) as db:
        db.execute("CREATE TABLE sentinel(value TEXT)")
        db.execute("INSERT INTO sentinel VALUES('original')")
        db.commit()
    with pytest.raises(RuntimeError, match="Unowned"):
        asyncio.run(offline(native_db))
    assert query(native_db, "SELECT * FROM sentinel") == [("original",)]
    assert query(native_db, "SELECT name FROM sqlite_master WHERE type='table'") == [("sentinel",)]


def test_changed_dependency_refuses_before_guard_or_writer_and_preserves_registry(
    native_db, monkeypatch
):
    asyncio.run(offline(native_db))
    original = query(native_db, "SELECT * FROM public_lifecycle")
    saved = module.source_contract

    def changed(path, **kwargs):
        contract = saved(path, **kwargs)
        contract["sources"]["uv.lock"] = "f" * 64
        return contract

    monkeypatch.setattr(module, "source_contract", changed)
    with pytest.raises(RuntimeError, match="binding changed"):
        asyncio.run(offline(native_db))
    assert query(native_db, "SELECT * FROM public_lifecycle") == original
    assert module.read_public_v3_status(native_db)["state"] == "SOURCE_BINDING_MISMATCH"


def test_live_cannot_inject_guard_and_engineering_cannot_enter_real_loop(native_db):
    with pytest.raises(ValueError, match="Live collection cannot inject"):
        asyncio.run(module.collect_public_v3(1, native_db, fixture_factory=OfflineCollector))
    assert not native_db.exists()
    with pytest.raises(ValueError, match="Offline fixtures"):
        asyncio.run(module.collect_public_v3(1, native_db, engineering=True))
    with pytest.raises(RuntimeError, match="override the real network"):
        asyncio.run(
            module.collect_public_v3(
                1,
                native_db,
                engineering=True,
                fixture_factory=ConcurrentCollector,
                fixture_disk_check=ledger,
            )
        )
    assert not query(native_db, "SELECT * FROM sessions")


@pytest.mark.parametrize("duration", [0, -1, float("nan"), float("inf")])
def test_invalid_duration_is_rejected_before_any_storage(native_db, duration):
    with pytest.raises(ValueError, match="finite and positive"):
        asyncio.run(module.collect_public_v3(duration, native_db))
    assert not native_db.exists()


def test_native_single_writer_lock_blocks_concurrent_entry(native_db):
    with native_db.with_suffix(".lock").open("a+") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        with pytest.raises(RuntimeError, match="Another public"):
            asyncio.run(offline(native_db))
        assert not native_db.exists()
    assert asyncio.run(offline(native_db))["state"] == "STOPPED"


def test_actual_two_async_runners_cannot_share_a_native_writer(native_db):
    async def perform():
        active, release = asyncio.Event(), asyncio.Event()

        class BlockingOffline(OfflineCollector):
            async def run(self, seconds=None, *, stop_event=None):
                active.set()
                await release.wait()
                return await super().run(seconds, stop_event=stop_event)

        first = asyncio.create_task(offline(native_db, BlockingOffline))
        await active.wait()
        with pytest.raises(RuntimeError, match="Another public"):
            await offline(native_db)
        release.set()
        assert (await first)["state"] == "STOPPED"

    asyncio.run(perform())
    assert query(native_db, "SELECT COUNT(*) FROM sessions") == [(1,)]


def test_source_and_lifecycle_rows_cannot_be_rewritten(native_db):
    asyncio.run(offline(native_db))
    with contextlib.closing(sqlite3.connect(native_db)) as db:
        for table in ("public_contract", "public_lifecycle"):
            for sql in (f"UPDATE {table} SET payload='changed'", f"DELETE FROM {table}"):
                with pytest.raises(sqlite3.IntegrityError):
                    db.execute(sql)
                db.rollback()
    assert module.read_public_v3_status(native_db)["stored_source_matches_current"] is True


def test_read_only_status_does_not_construct_scan_network_or_change_rows(native_db, monkeypatch):
    asyncio.run(offline(native_db))
    original = query(native_db, "SELECT * FROM public_lifecycle")

    def forbidden(*args, **kwargs):
        raise AssertionError("Read-only status must not perform writer/network/full scan")

    monkeypatch.setattr(ConcurrentCollector, "__init__", forbidden)
    monkeypatch.setattr(module.disk, "check", forbidden)
    monkeypatch.setattr(module.resources, "status", forbidden)
    monkeypatch.setattr(core.httpx.AsyncClient, "__init__", forbidden)
    monkeypatch.setattr(core.websockets, "connect", forbidden)
    snapshot = module.read_public_v3_status(native_db)
    assert snapshot["read_only"] is True and snapshot["qualified_72h"] is None
    assert query(native_db, "SELECT * FROM public_lifecycle") == original


def test_stale_running_session_is_not_live_and_restart_gap_is_not_credited(native_db):
    class CrashedOffline(OfflineCollector):
        async def run(self, seconds=None, *, stop_event=None):
            self.session_id = self.db.execute(
                "INSERT INTO sessions(started_ms,state,endpoint,heartbeat_ms,observed_seconds) "
                "VALUES(?,'RUNNING',?,?,123)",
                (BASE, "engineering", BASE),
            ).lastrowid
            self.db.commit()
            return {"state": "RUNNING", "qualified_72h": True}

    assert asyncio.run(offline(native_db, CrashedOffline))["qualified_72h"] is False
    assert module.read_public_v3_status(native_db)["state"] == "STALE_OR_STARTING"
    asyncio.run(offline(native_db))
    gaps = query(
        native_db, "SELECT payload FROM public_lifecycle WHERE kind='UNGRACEFUL_PREVIOUS_SESSION'"
    )
    assert json.loads(gaps[0][0])["unobserved_time_not_credited"] is True
    assert query(native_db, "SELECT observed_seconds FROM sessions ORDER BY id") == [(123,), (0,)]


def test_failed_initial_disk_check_releases_writer_and_creates_no_session(native_db):
    def failed(**kwargs):
        raise PermissionError("concrete guard failure")

    with pytest.raises(PermissionError, match="guard failure"):
        asyncio.run(
            module.collect_public_v3(
                1,
                native_db,
                engineering=True,
                fixture_factory=OfflineCollector,
                fixture_disk_check=failed,
            )
        )
    assert module.read_public_v3_status(native_db)["state"] == "REGISTERED_NO_SESSION"
    assert asyncio.run(offline(native_db))["state"] == "STOPPED"


def test_missing_immutable_trigger_refuses_both_status_and_restart(native_db):
    asyncio.run(offline(native_db))
    with contextlib.closing(sqlite3.connect(native_db)) as db:
        db.execute("DROP TRIGGER public_contract_no_update")
        db.commit()
    with pytest.raises(RuntimeError, match="trigger missing"):
        module.read_public_v3_status(native_db)
    with pytest.raises(RuntimeError, match="trigger missing"):
        asyncio.run(offline(native_db))


def test_resource_alias_cannot_redirect_target(native_db, monkeypatch):
    monkeypatch.setattr(module, "ROOT", Path("/mnt/c/forbidden"))
    with pytest.raises(RuntimeError, match="D-hosted"):
        module.read_public_v3_status(native_db)


def test_real_frozen_loop_prestopped_performs_no_http_or_websocket(native_db, monkeypatch):
    calls = []

    class NoRequests:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

        async def get(self, *args, **kwargs):
            calls.append("http")
            raise AssertionError("No request after pre-stop")

    def forbidden(*args, **kwargs):
        calls.append("websocket")
        raise AssertionError("No websocket after pre-stop")

    monkeypatch.setattr(module.disk, "check", ledger)
    monkeypatch.setattr(core.httpx, "AsyncClient", NoRequests)
    monkeypatch.setattr(core.websockets, "connect", forbidden)

    async def perform():
        stop = asyncio.Event()
        stop.set()
        return await module.collect_public_v3(1, native_db, stop_event=stop)

    result = asyncio.run(perform())
    assert result["state"] == "STOPPED" and result["qualified_72h"] is False
    assert calls == []
    assert result["engineering"] is False  # real entry stopped before any request, not a live pass
    assert query(native_db, "SELECT COUNT(*) FROM closed_bars") == [(0,)]
