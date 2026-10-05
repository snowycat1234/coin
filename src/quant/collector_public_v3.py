"""Independent public 1m collection; no financial account or order callback."""

from __future__ import annotations

import argparse
import asyncio
import contextlib
import fcntl
import hashlib
import json
import math
import os
import signal
import sqlite3
import sys
from importlib.metadata import version
from pathlib import Path
from typing import Callable

from . import disk, resources
from .collector import INTAKE_RESERVE_BYTES, REST_BASE, STREAM_URL, SYMBOLS, now_ms
from .concurrent_budget import ConcurrentCollector
from .paths import ROOT, STATE

VERSION = "collector_public_v3"
DEFAULT_DB = STATE / "collector_public_v3.sqlite3"
STOP_FILE = ROOT / "state/collector_public_v3.stop"
SOURCE_FILES = (
    "src/quant/collector_public_v3.py",
    "src/quant/collector.py",
    "src/quant/concurrent_budget.py",
    "src/quant/shadow.py",  # import dependency only; never instantiated here
    "src/quant/disk.py",
    "src/quant/resources.py",
    "src/quant/paths.py",
    "scripts/env.sh",
    "scripts/bounded.sh",
    "scripts/collector_public_v3.sh",
    "scripts/collector_public_v3.ps1",
    "pyproject.toml",
    "uv.lock",
)


def canonical(value) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def digest(value) -> str:
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def target_path(path: Path | None = None) -> Path:
    if (
        ROOT.resolve() != Path("/mnt/d/codex/coin")
        or STATE.resolve() != Path("/home/xflops/coin-state")
        or os.environ.get("WSL_DISTRO_NAME") != "hpc_linux"
    ):
        raise RuntimeError("Public v3 requires the fixed D-hosted hpc_linux workspace")
    target = Path(path or DEFAULT_DB).resolve()
    if (
        not target.is_relative_to(STATE.resolve())
        or not target.name.startswith("collector_public_v3")
        or target.suffix != ".sqlite3"
    ):
        raise ValueError("Use an independent native collector_public_v3*.sqlite3 database")
    return target


def source_contract(path: Path, *, engineering: bool = False) -> dict:
    return {
        "version": VERSION,
        "database": str(path),
        "engineering": engineering,
        "scope": "public_market_data_only",
        "symbols": list(SYMBOLS),
        "interval": "1m",
        "stream_url": STREAM_URL,
        "rest_base": REST_BASE,
        "financial_accounts": False,
        "orders": False,
        "credentials": False,
        "gpu": False,
        "disk_hard_bytes": disk.HARD_LIMIT,
        "ram_shared_max_bytes": resources.RAM_LIMIT,
        "swap_bytes": 0,
        "sources": {
            name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in SOURCE_FILES
        },
        "versions": {
            "python": sys.version.split()[0],
            "sqlite": sqlite3.sqlite_version,
            **{name: version(name) for name in ("httpx", "websockets", "numpy")},
        },
    }


def verify_registry(db: sqlite3.Connection) -> tuple[dict, str]:
    triggers = dict(db.execute("SELECT name,sql FROM sqlite_master WHERE type='trigger'"))
    for table in ("public_contract", "public_lifecycle"):
        for action in ("update", "delete"):
            sql = triggers.get(f"{table}_no_{action}", "")
            if f"BEFORE {action.upper()} ON {table}" not in sql or "RAISE(ABORT" not in sql:
                raise RuntimeError("Immutable public registry trigger missing")
    row = db.execute("SELECT payload,sha256 FROM public_contract WHERE id=1").fetchone()
    if not row or digest(json.loads(row[0])) != row[1]:
        raise RuntimeError("Public source binding damaged")
    head, expected = "0" * 64, 1
    for seq, stamp, kind, payload, previous, sha in db.execute(
        "SELECT * FROM public_lifecycle ORDER BY seq"
    ):
        if (
            seq != expected
            or previous != head
            or sha != digest([seq, stamp, kind, json.loads(payload), previous])
        ):
            raise RuntimeError("Public lifecycle audit chain damaged")
        head, expected = sha, expected + 1
    return json.loads(row[0]), head


def append_lifecycle(db: sqlite3.Connection, kind: str, detail: dict) -> None:
    row = db.execute("SELECT seq,sha256 FROM public_lifecycle ORDER BY seq DESC LIMIT 1").fetchone()
    seq, previous = (row[0] + 1, row[1]) if row else (1, "0" * 64)
    stamp = now_ms()
    with db:
        db.execute(
            "INSERT INTO public_lifecycle VALUES(?,?,?,?,?,?)",
            (
                seq,
                stamp,
                kind,
                canonical(detail),
                previous,
                digest([seq, stamp, kind, detail, previous]),
            ),
        )


def bind_owned_database(db: sqlite3.Connection, contract: dict) -> None:
    tables = {r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    if tables and "public_contract" not in tables:
        raise RuntimeError("Unowned database; legacy collection/account evidence cannot be reused")
    if "public_contract" in tables:
        saved, _ = verify_registry(db)
        if saved != contract:
            raise RuntimeError("Frozen public v3 binding changed; register an independent version")
        return
    db.executescript("""
        CREATE TABLE public_contract(id INTEGER PRIMARY KEY CHECK(id=1),
            payload TEXT NOT NULL,sha256 TEXT NOT NULL);
        CREATE TABLE public_lifecycle(seq INTEGER PRIMARY KEY,received_ms INTEGER NOT NULL,
            kind TEXT NOT NULL,payload TEXT NOT NULL,
            previous_sha TEXT NOT NULL,sha256 TEXT NOT NULL);
        CREATE TRIGGER public_contract_no_update BEFORE UPDATE ON public_contract
            BEGIN SELECT RAISE(ABORT,'frozen public source binding'); END;
        CREATE TRIGGER public_contract_no_delete BEFORE DELETE ON public_contract
            BEGIN SELECT RAISE(ABORT,'frozen public source binding'); END;
        CREATE TRIGGER public_lifecycle_no_update BEFORE UPDATE ON public_lifecycle
            BEGIN SELECT RAISE(ABORT,'append only'); END;
        CREATE TRIGGER public_lifecycle_no_delete BEFORE DELETE ON public_lifecycle
            BEGIN SELECT RAISE(ABORT,'append only'); END;
    """)
    with db:
        db.execute(
            "INSERT INTO public_contract VALUES(1,?,?)", (canonical(contract), digest(contract))
        )


async def collect_public_v3(
    seconds: float | None = None,
    db_path: Path | None = None,
    *,
    stop_event: asyncio.Event | None = None,
    engineering: bool = False,
    fixture_factory: Callable | None = None,
    fixture_disk_check: Callable | None = None,
) -> dict:
    """Fixtures require an engineering binding and can never launch the real network loop."""
    target = target_path(db_path)
    if seconds is not None and (not math.isfinite(seconds) or seconds <= 0):
        raise ValueError("Duration must be finite and positive")
    if engineering != (fixture_factory is not None and fixture_disk_check is not None):
        raise ValueError(
            "Offline fixtures require explicit engineering provenance and both fixtures"
        )
    if not engineering and (fixture_factory is not None or fixture_disk_check is not None):
        raise ValueError("Live collection cannot inject a writer or resource guard")
    resources.status()
    contract = source_contract(target, engineering=engineering)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.with_suffix(".lock").open("a+") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as error:
            raise RuntimeError("Another public v3 collector holds this database") from error
        meta = sqlite3.connect(target, timeout=10)
        collector = None
        bound = False
        try:
            bind_owned_database(meta, contract)
            bound = True
            has_sessions = meta.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name='sessions'"
            ).fetchone()
            previous = (
                meta.execute("SELECT * FROM sessions ORDER BY id DESC LIMIT 1").fetchone()
                if has_sessions
                else None
            )
            if previous and previous[2] is None:  # ended_ms; never credit missing time
                append_lifecycle(
                    meta,
                    "UNGRACEFUL_PREVIOUS_SESSION",
                    {
                        "session_id": previous[0],
                        "started_ms": previous[1],
                        "last_heartbeat_ms": previous[4],
                        "detected_ms": now_ms(),
                        "unobserved_time_not_credited": True,
                    },
                )
            append_lifecycle(
                meta,
                "RUN_REQUEST",
                {
                    "engineering": engineering,
                    "seconds": seconds,
                    "contract_sha256": digest(contract),
                },
            )
            check = fixture_disk_check if engineering else disk.check
            ledger = await asyncio.to_thread(check, reserve=INTAKE_RESERVE_BYTES)
            if ledger.get("status") not in {"OK", "WARNING"}:
                raise RuntimeError("Initial disk budget rejected public intake")
            factory = fixture_factory if engineering else ConcurrentCollector
            collector = factory(target, initial_disk=ledger)
            if engineering and type(collector).run is ConcurrentCollector.run:
                raise RuntimeError("Engineering writer must override the real network run loop")
            result = await collector.run(seconds, stop_event=stop_event)
            append_lifecycle(
                meta,
                "RUN_FINISHED",
                {
                    "session_id": collector.session_id,
                    "state": result.get("state"),
                    "engineering": engineering,
                    "data_qualified_72h": bool(result.get("qualified_72h"))
                    if not engineering
                    else False,
                },
            )
            return {
                **result,
                "public_version": VERSION,
                "engineering": engineering,
                "source_contract_sha256": digest(contract),
                "financial_accounts": False,
                "credentials_used": False,
                "orders_sent": 0,
                "alpha_eligible": False,
                "qualified_72h": False if engineering else result.get("qualified_72h", False),
            }
        except BaseException as error:
            if bound:
                with contextlib.suppress(Exception):
                    append_lifecycle(
                        meta,
                        "RUN_ERROR",
                        {"type": type(error).__name__, "detail": str(error)[:512]},
                    )
            raise
        finally:
            try:
                if collector is not None:
                    try:
                        collector.close()
                    finally:
                        collector.db.close()
            finally:
                meta.close()


def read_public_v3_status(db_path: Path | None = None) -> dict:
    """Cheap, same-snapshot read; qualification needs the separate frozen full checker."""
    target = target_path(db_path)
    base = {
        "database": str(target),
        "public_version": VERSION,
        "read_only": True,
        "financial_accounts": False,
        "credentials_used": False,
        "orders_sent": 0,
        "alpha_eligible": False,
        "qualified_72h": None,
        "qualification_scope": "NOT_CERTIFIED_BY_THIS_SNAPSHOT",
    }
    if not target.exists():
        return {**base, "state": "NOT_STARTED"}
    db = sqlite3.connect(f"file:{target}?mode=ro", uri=True, timeout=10)
    try:
        db.execute("BEGIN")
        contract, head = verify_registry(db)
        tables = {r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        session = None
        symbols = {}
        gaps = None
        if "sessions" in tables:
            db.row_factory = sqlite3.Row
            row = db.execute("SELECT * FROM sessions ORDER BY id DESC LIMIT 1").fetchone()
            session = dict(row) if row else None
            gaps = db.execute("SELECT COUNT(*) FROM gaps WHERE repaired_ms IS NULL").fetchone()[0]
            for symbol in SYMBOLS:
                counts = db.execute(
                    "SELECT COUNT(*) total,SUM(source='websocket') websocket,"
                    "SUM(source='rest') rest,"
                    "MIN(open_ms) first_open_ms,MAX(open_ms) last_open_ms,"
                    "MAX(websocket_received_ms) last_websocket_received_ms "
                    "FROM closed_bars WHERE symbol=?",
                    (symbol,),
                ).fetchone()
                symbols[symbol] = dict(counts)
        stamp = now_ms()
        state = "REGISTERED_NO_SESSION"
        if session:
            state = session["state"]
            if state == "RUNNING" and not (
                session["heartbeat_ms"] and 0 <= stamp - session["heartbeat_ms"] <= 45_000
            ):
                state = "STALE_OR_STARTING"
        current_matches = contract == source_contract(target, engineering=contract["engineering"])
        return {
            **base,
            "state": state if current_matches else "SOURCE_BINDING_MISMATCH",
            "sampled_ms": stamp,
            "stored_source_matches_current": current_matches,
            "contract": contract,
            "contract_sha256": digest(contract),
            "lifecycle_head": head,
            "session": session,
            "symbols": symbols,
            "unresolved_gaps": gaps,
        }
    finally:
        db.close()


async def _entry(arguments) -> dict:
    stop = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, stop.set)

    async def watch_stop():
        while not stop.is_set():
            if STOP_FILE.exists():
                stop.set()
            await asyncio.sleep(1)

    watcher = asyncio.create_task(watch_stop())
    try:
        return await collect_public_v3(arguments.seconds, arguments.db, stop_event=stop)
    finally:
        watcher.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await watcher
        for sig in (signal.SIGTERM, signal.SIGINT):
            loop.remove_signal_handler(sig)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Public 1m market data v3; no keys or accounts")
    parser.add_argument("--run", action="store_true")
    parser.add_argument("--seconds", type=float)
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    args = parser.parse_args()
    print(
        json.dumps(
            asyncio.run(_entry(args)) if args.run else read_public_v3_status(args.db),
            ensure_ascii=False,
            indent=2,
        )
    )
