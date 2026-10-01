"""Separate each writer's allocation from other jobs' shared VHD growth."""

from __future__ import annotations

import asyncio
import fcntl
import os
import shutil
import time
from pathlib import Path

from . import disk
from .collector import INTAKE_RESERVE_BYTES, Collector, CollectorStopped, default_db, now_ms
from .paths import ROOT, STATE, VHD
from .shadow import RESERVE_BYTES, ShadowEngine


class ConcurrentShadowEngine(ShadowEngine):
    def _guard(self) -> None:
        own_growth = max(0, self._database_bytes() - self._budget_db)
        overall_growth = own_growth
        if "total_bytes" in self.ledger:
            overall_growth = max(overall_growth, VHD.stat().st_size - self._budget_vhd)
            disk.enforce(self.ledger["total_bytes"] + overall_growth, RESERVE_BYTES,
                         shutil.disk_usage(ROOT).free)
        if own_growth >= RESERVE_BYTES:
            raise RuntimeError("shadow local 100 MB writer budget exhausted; refresh disk ledger")


class ConcurrentCollector(Collector):
    def guard(self, *, force: bool = False) -> None:
        if self._fatal is not None:
            raise CollectorStopped(self._fatal)
        if self._custom_guard:
            return super().guard(force=force)
        if not force and time.monotonic() - self._last_guard < 15:
            return
        self._last_guard = time.monotonic()
        try:
            own_growth = max(0, self._database_bytes() - self._budget_db)
            overall_growth = max(own_growth, VHD.stat().st_size - self._budget_vhd)
            if own_growth >= INTAKE_RESERVE_BYTES:
                raise RuntimeError("Collector's local 100 MB allocation budget is exhausted")
            used = self._disk_ledger["total_bytes"] + overall_growth
            health = disk.enforce(used, INTAKE_RESERVE_BYTES, shutil.disk_usage(ROOT).free)
            result = {"status": health, "conservative_total_bytes": used,
                      "growth_bytes": overall_growth, "own_growth_bytes": own_growth,
                      "reserve_bytes": INTAKE_RESERVE_BYTES}
        except Exception as exc:
            self._disk_stop(exc)
            raise CollectorStopped(self._fatal) from exc
        if result["status"] == "WARNING":
            self.event("disk_warning", result)
        self._disk_snapshot = {**result, "asof_ms": now_ms(), "check_kind": "cheap_guard_v2"}


async def collect(run_seconds: float | None = None, db_path: Path | None = None, *,
                  tick_callback=None, stop_event: asyncio.Event | None = None) -> dict:
    target = Path(db_path or default_db()).resolve()
    if os.environ.get("WSL_DISTRO_NAME") != "hpc_linux":
        raise RuntimeError("Collection requires D-hosted hpc_linux WSL")
    if not target.is_relative_to(STATE.resolve()):
        raise ValueError("v2 live SQLite requires native D-hosted STATE")
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.with_suffix(".lock").open("a+") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise RuntimeError("Another collector already holds this database lock") from exc
        initial_disk = await asyncio.to_thread(disk.check, reserve=INTAKE_RESERVE_BYTES)
        collector = ConcurrentCollector(target, initial_disk=initial_disk,
                                        tick_callback=tick_callback)
        try:
            return await collector.run(run_seconds, stop_event=stop_event)
        finally:
            collector.close()
