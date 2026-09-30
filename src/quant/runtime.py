"""Public observation plus reference paper accounts; no admitted trading model."""
from __future__ import annotations

import asyncio
import hashlib
import json
import time
from pathlib import Path

from . import disk
from .paths import ROOT, STATE


def seal_execution_contract() -> dict:
    files = [f"src/quant/{name}.py" for name in
             ("runtime", "collector", "shadow", "disk", "resources", "paths")]
    files.append("uv.lock")
    contract = {"version": "paper_baselines_runtime_v1", "sources": {
        relative: hashlib.sha256((ROOT / relative).read_bytes()).hexdigest()
        for relative in files}, "scope": "B0_B2_references_no_champion"}
    path = ROOT / "state/live_contract.json"
    if path.exists():
        if json.loads(path.read_text()) != contract:
            raise RuntimeError("Frozen runtime changed; register a separate execution version")
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(contract, indent=2))
    return contract


def adapt_tick(tick: dict) -> tuple[dict, list]:
    from .shadow import Quote

    now = tick["received_ms"]
    health = dict(tick["health"])
    qualification = health.get("qualification", {})
    age = now - qualification.get("asof_ms", 0)
    health["qualified_72h"] = (qualification.get("qualified_72h") is True
                               and 0 <= age <= 45_000)
    health["state"] = "RUNNING" if health.get("live_session") else "NOT_STARTED"
    quotes = [Quote(symbol=symbol, bid=value["bid"], ask=value["ask"],
                    received_ms=value["received_ms"], update_id=value["update_id"],
                    source=value["source"])
              for symbol, value in tick.get("quotes", {}).items()
              if value.get("fresh") is True]
    return health, quotes


def write_status(report: dict, path: Path = ROOT / "state/live_status.json") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False))
    temporary.replace(path)


async def run_live(seconds: float | None = None) -> dict:
    from .collector import collect
    from .resources import status as resource_status
    from .shadow import ShadowEngine

    resources = resource_status()
    contract = seal_execution_contract()
    stop = asyncio.Event()
    stop_path = ROOT / "state/live.stop"
    stop_path.unlink(missing_ok=True)
    ledger = await asyncio.to_thread(disk.check, reserve=200_000_000)
    engine = None
    last_tick_mono = -float("inf")
    last_status_mono = -float("inf")
    last_report = {"state": "STARTING", "asof_ms": time.time_ns() // 1_000_000,
                   "scope": "B0_B2_references_no_champion", "candidate_status": "NO_ADMITTED_MODEL",
                   "real_money_authorized": False, "resources": resources,
                   "execution_contract": contract["version"]}
    write_status(last_report)

    def tick_callback(tick: dict) -> None:
        nonlocal engine, last_tick_mono, last_status_mono, last_report
        current_mono = time.monotonic()
        if tick["kind"] != "closed_bar" and current_mono - last_tick_mono < 1:
            return
        last_tick_mono = current_mono
        health, quotes = adapt_tick(tick)
        if engine is None:
            engine = ShadowEngine(started_ms=tick["received_ms"], initial_health=health,
                                  initial_disk=ledger)
        paper = engine.process_tick(tick["received_ms"], health, quotes)
        last_report = {"state": "RUNNING", "asof_ms": tick["received_ms"],
                       "scope": "B0_B2_references_no_champion",
                       "candidate_status": "NO_ADMITTED_MODEL",
                       "real_money_authorized": False,
                       "execution_contract": contract["version"],
                       "resources": resource_status(),
                       "collector": health, "paper": paper,
                       "quote_sampling": "at most once per second plus closed candle events"}
        if current_mono - last_status_mono >= 15:
            write_status(last_report)
            last_status_mono = current_mono

    async def watch_stop() -> None:
        while not stop.is_set():
            await asyncio.sleep(1)
            if stop_path.exists():
                stop.set()

    async def refresh_budget() -> None:
        nonlocal ledger
        while not stop.is_set():
            await asyncio.sleep(15 * 60)
            ledger = await asyncio.to_thread(disk.check, reserve=200_000_000)
            if engine is not None:
                engine.refresh_disk_budget(ledger)

    watcher = asyncio.create_task(watch_stop())
    budget = asyncio.create_task(refresh_budget())
    collection = asyncio.create_task(collect(seconds, tick_callback=tick_callback,
                                             stop_event=stop))
    try:
        completed, _ = await asyncio.wait([collection, budget],
                                         return_when=asyncio.FIRST_COMPLETED)
        if budget in completed:
            # A failed guard stops the writer, then the original failure is reported.
            stop.set()
            await collection
            budget.result()
        result = await collection
        last_report.update(state=result["state"], asof_ms=time.time_ns() // 1_000_000,
                           final_collector=result)
        return last_report
    except BaseException as error:
        last_report.update(state="ERROR", asof_ms=time.time_ns() // 1_000_000,
                           error=f"{type(error).__name__}: {error}")
        raise
    finally:
        stop.set()
        for task in (watcher, budget, collection):
            if not task.done():
                task.cancel()
        await asyncio.gather(watcher, budget, collection, return_exceptions=True)
        if engine is not None:
            engine.close()
        write_status(last_report)


def live_status() -> dict:
    path = ROOT / "state/live_status.json"
    if not path.exists():
        return {"state": "NOT_STARTED", "healthy": False}
    report = json.loads(path.read_text())
    age = time.time_ns() // 1_000_000 - report["asof_ms"]
    report["status_age_ms"] = age
    if not 0 <= age <= 45_000 and report["state"] == "RUNNING":
        report.update(state="STALE", healthy=False)
    return report


def forward_report() -> dict:
    from .forward_report import read_forward_report, write_forward_report

    path = STATE / "shadow.sqlite3"
    report = read_forward_report(path)
    write_forward_report(report, ROOT / "reports/generated/P06")
    return report


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Public Binance reference paper runtime")
    parser.add_argument("--seconds", type=float)
    print(json.dumps(asyncio.run(run_live(parser.parse_args().seconds)),
                     ensure_ascii=False, indent=2))
