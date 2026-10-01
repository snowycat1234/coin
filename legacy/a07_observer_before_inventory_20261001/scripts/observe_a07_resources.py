"""Observe a real A07 process and sampled storage/CPU/RSS without changing it."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import signal
import sqlite3
import time
from contextlib import closing
from datetime import UTC, datetime
from pathlib import Path
from threading import Event

from quant import disk
from quant.paths import ROOT, STATE, VHD
from quant.resources import status

COMMAND = [str(ROOT / ".venv/bin/python"), "-u", "-m", "quant.microstructure", "--run"]
DATABASE = STATE / "microstructure.sqlite3"
STORE = ROOT / "data/microstructure_v1"
LIMIT = 10_000_000
BOUND_FILES = (
    "src/quant/microstructure.py", "scripts/microstructure.ps1", "scripts/microstructure.sh",
    "scripts/observe_a07_resources.py", "scripts/observe_a07_resources.ps1",
)


def require(ok, message):
    if not ok:
        raise ValueError(message)


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
                      allow_nan=False).encode()


def sha(path):
    result = hashlib.sha256()
    with Path(path).open("rb") as reader:
        for block in iter(lambda: reader.read(1_048_576), b""):
            result.update(block)
    return result.hexdigest()


def parse_stat(value):
    """Linux comm can include spaces and parentheses; fields start after last ')' ."""
    fields = value.rsplit(")", 1)[1].split()
    require(len(fields) >= 22, "Truncated Linux process stat")
    return {"start_ticks": int(fields[19]),
            "cpu_ticks": int(fields[11]) + int(fields[12])}


def process(pid):
    folder = Path("/proc") / str(pid)
    require(folder.stat().st_uid == os.getuid(), "Different process owner")
    command = folder.joinpath("cmdline").read_bytes().rstrip(b"\0").decode().split("\0")
    require(command == COMMAND, "Not the existing public A07 collector command")
    require("/coin-quant.slice/" in folder.joinpath("cgroup").read_text(),
            "Collector is outside shared RAM budget")
    fields = parse_stat(folder.joinpath("stat").read_text())
    memory = {}
    for line in folder.joinpath("status").read_text().splitlines():
        key, _, value = line.partition(":")
        if key in ("VmRSS", "VmHWM"):
            parts = value.split()
            require(len(parts) == 2 and parts[1] == "kB", "Unknown /proc memory unit")
            memory[key] = int(parts[0]) * 1024
    require(set(memory) == {"VmRSS", "VmHWM"}, "Missing live process RSS counters")
    return {"pid": pid, **fields, "sampled_monotonic_seconds": time.monotonic(),
            "rss_bytes": memory["VmRSS"],
            "lifetime_rss_hwm_bytes": memory["VmHWM"]}


def find_collector():
    matches = []
    for folder in Path("/proc").iterdir():
        if folder.name.isdigit():
            try:
                candidate = process(int(folder.name))
                matches.append(candidate)
            except (OSError, ValueError):
                pass
    require(len(matches) == 1, "Expected exactly one existing owned A07 process")
    return matches[0]["pid"]


def raw_inventory(directory):
    started, count, total, disappeared = time.monotonic(), 0, 0, 0
    for folder, subdirectories, names in os.walk(directory):
        require(not any((Path(folder) / name).is_symlink() for name in subdirectories),
                "Unexpected raw directory symlink")
        for name in names:
            count += 1
            require(count <= 20_000 and time.monotonic() - started <= 10,
                    "Raw inventory budget exceeded")
            try:
                path = Path(folder) / name
                require(not path.is_symlink(), "Unexpected raw symlink")
                total += path.stat().st_size
            except FileNotFoundError:
                disappeared += 1
    return {"sampled_bytes": total, "entries_seen": count,
            "legitimate_concurrent_retirement_or_missing_entries": disappeared,
            "scan_seconds": time.monotonic() - started,
            "atomic_snapshot": False, "exact_unsampled_peak_known": False}


def snapshot(pid, *, database=DATABASE, store=STORE):
    started, before = time.monotonic(), process(pid)
    require(database.is_relative_to(STATE) and database.exists(), "Native D database required")
    require(store.is_relative_to(ROOT / "data") and store.exists(), "D feature store required")
    with closing(sqlite3.connect(f"file:{database}?mode=ro", uri=True, timeout=1)) as reader:
        reader.set_progress_handler(lambda: int(time.monotonic() - started > 5), 1000)
        reader.execute("PRAGMA query_only=ON")
        reader.execute("BEGIN")
        values = {}
        for key in ("binding", "checkpoint"):
            row = reader.execute("SELECT value FROM state WHERE key=?", (key,)).fetchone()
            require(row is not None and len(row[0].encode()) <= 64_000, "Missing/large state")
            values[key] = json.loads(row[0])
        manifests = reader.execute(
            "SELECT COUNT(*),COALESCE(SUM(bytes),0),COALESCE(SUM(rows),0) FROM manifests"
        ).fetchone()
        audit = reader.execute("SELECT seq,sha256 FROM audit ORDER BY seq DESC LIMIT 1").fetchone()
        require(audit is not None, "Missing audit head")
    sql_seconds = time.monotonic() - started
    require(sql_seconds <= 5, "Read transaction exceeded five seconds")
    after = process(pid)
    require(before["start_ticks"] == after["start_ticks"], "PID reused during snapshot")
    binding, checkpoint = values["binding"], values["checkpoint"]
    require(binding["mode"] == checkpoint["mode"] == "live"
            and binding["store"] == str(store.resolve()), "Different collector source")
    selected = {key: checkpoint[key] for key in (
        "asof_us", "session", "connected", "accepted_events", "duplicate_events",
        "rejected_events", "observed_monotonic_seconds",
    )}
    require(0 <= time.time() * 1_000_000 - selected["asof_us"] <= 10_000_000,
            "Stale/future collector checkpoint")
    native = {path.name: path.stat().st_size for path in (
        database, Path(str(database) + "-wal"), Path(str(database) + "-shm")
    ) if path.exists()}
    return {"sampled_utc": datetime.now(UTC).isoformat(), "process": after,
            "checkpoint": selected, "binding": binding,
            "manifest_files": manifests[0], "feature_bytes": manifests[1],
            "feature_rows": manifests[2], "audit_head_seq": audit[0],
            "audit_head_sha256": audit[1], "sql_read_seconds": sql_seconds,
            "sql_released_before_inventory": True, "native_files_sampled_bytes": native,
            "raw_inventory": raw_inventory(store / "raw"),
            "global_vhd_sampled_bytes": VHD.stat().st_size, "aggregate_ram": status()}


def same_window(previous, current):
    require((previous["process"]["pid"], previous["process"]["start_ticks"])
            == (current["process"]["pid"], current["process"]["start_ticks"]),
            "Collector process changed; never splice windows")
    require(previous["checkpoint"]["session"] == current["checkpoint"]["session"]
            and previous["binding"] == current["binding"], "Collector session/source changed")
    for key in ("accepted_events", "duplicate_events", "rejected_events",
                "observed_monotonic_seconds", "asof_us"):
        require(current["checkpoint"][key] >= previous["checkpoint"][key], "Counter reversed")
    for key in ("feature_bytes", "feature_rows", "manifest_files", "audit_head_seq"):
        require(current[key] >= previous[key], "Immutable feature/audit counter reversed")
    require(current["process"]["cpu_ticks"] >= previous["process"]["cpu_ticks"],
            "CPU counter reversed")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--directory", type=Path, required=True)
    parser.add_argument("--seconds", type=float, default=86400)
    parser.add_argument("--period", type=float, default=300)
    args = parser.parse_args()
    require(10 <= args.seconds <= 86400 and 1 <= args.period <= 300
            and args.period <= args.seconds, "Invalid bounded observation schedule")
    folder = args.directory.resolve()
    require(folder.is_relative_to(ROOT / "reports/generated") and not folder.exists(),
            "New exclusive D reports directory required")
    sources = {name: sha(ROOT / name) for name in BOUND_FILES}
    accepted_path = ROOT / "reports/A07_MICROSTRUCTURE_ACCEPTANCE.json"
    accepted = json.loads(accepted_path.read_text())
    require(accepted["status"] == "DATA_ENGINEERING_SHORT_ACCEPTANCE_PASS"
            and accepted["source_hashes"]["src/quant/microstructure.py"]
            == sources["src/quant/microstructure.py"], "Frozen A07 source changed")
    initial_disk = disk.check(reserve=10_000_000)
    pid, stopped = find_collector(), Event()
    for signum in (signal.SIGTERM, signal.SIGINT):
        signal.signal(signum, lambda *_: stopped.set())
    folder.mkdir()
    started, head, count, bytes_written = time.monotonic(), "0" * 64, 0, 0
    first, last, peaks, gaps, state, failure = None, None, {}, [], "OBSERVING", None
    next_at = 0.0
    try:
        with (folder / "samples.jsonl").open("x", encoding="utf-8") as stream:
            while not stopped.is_set():
                elapsed = time.monotonic() - started
                if elapsed < next_at:
                    stopped.wait(min(60, next_at - elapsed))
                    continue
                current = snapshot(pid)
                current["elapsed_monotonic_seconds"] = (
                    current["process"]["sampled_monotonic_seconds"] - started
                )
                require(current["binding"]["implementation_sha256"]
                        == sources["src/quant/microstructure.py"], "Wrong live implementation")
                if last is not None:
                    same_window(last, current)
                    gaps.append(current["elapsed_monotonic_seconds"]
                                - last["elapsed_monotonic_seconds"])
                first = current if first is None else first
                last = current
                for key, value in {
                    "raw_sampled_bytes": current["raw_inventory"]["sampled_bytes"],
                    "native_sampled_bytes": sum(current["native_files_sampled_bytes"].values()),
                    "vhd_sampled_bytes": current["global_vhd_sampled_bytes"],
                    "collector_rss_sampled_bytes": current["process"]["rss_bytes"],
                    "collector_lifetime_rss_hwm_bytes": current["process"][
                        "lifetime_rss_hwm_bytes"],
                    "aggregate_ram_sampled_bytes": current["aggregate_ram"]["ram_current_bytes"],
                }.items():
                    peaks[key] = max(peaks.get(key, 0), value)
                record = {"seq": count + 1, "previous_sha256": head, "sample": current}
                head = hashlib.sha256(canonical(record)).hexdigest()
                line = canonical({**record, "sha256": head}) + b"\n"
                bytes_written += len(line)
                require(bytes_written <= LIMIT and len(line) <= 32_000, "Observation output limit")
                stream.write(line.decode())
                stream.flush()
                os.fsync(stream.fileno())
                count += 1
                print(json.dumps({"sample": count, "elapsed_seconds": round(
                    current["elapsed_monotonic_seconds"], 3), "directory": str(folder)}),
                      flush=True)
                if (current["elapsed_monotonic_seconds"]
                        - first["elapsed_monotonic_seconds"] >= args.seconds):
                    state = "REAL_SHORT_SAMPLED_RESOURCE_WINDOW_COMPLETE"
                    if args.seconds == 86400:
                        state = "REAL_24H_SAMPLED_RESOURCE_WINDOW_COMPLETE"
                    break
                next_at = first["elapsed_monotonic_seconds"] + min(
                    args.seconds, count * args.period
                )
            if stopped.is_set():
                state = "INTERRUPTED_RESOURCE_WINDOW_NOT_ACCEPTED"
    except (OSError, ValueError, KeyError, sqlite3.Error) as error:
        state, failure = "FAILED_RESOURCE_WINDOW_NOT_ACCEPTED", str(error)
    if sources != {name: sha(ROOT / name) for name in BOUND_FILES}:
        state, failure = "FAILED_RESOURCE_WINDOW_NOT_ACCEPTED", "Source changed during observation"
    report = {"status": state, "failure": failure, "source_hashes": sources,
              "created_utc": datetime.now(UTC).isoformat(), "first": first, "last": last,
              "samples": count, "samples_sha256": sha(folder / "samples.jsonl"),
              "head_sha256": head, "sampled_peaks": peaks,
              "maximum_sample_gap_seconds": max(gaps, default=0),
              "requested_seconds": args.seconds, "period_seconds": args.period,
              "clock_ticks_per_second": os.sysconf("SC_CLK_TCK"),
              "initial_disk": initial_disk, "final_disk": disk.check(reserve=0),
              "quality_accepted": False, "actual_24h_capacity_accepted": False,
              "alpha_eligible": False, "training_authorized": False,
              "network_requests": 0, "collector_writes": 0, "collector_restarts": 0,
              "limitations": "Actual existing PID/session CPU delta and lifetime RSS HWM; "
              "sampled raw/native/VHD peaks are not exact unsampled peaks. Raw inventory "
              "is non-atomic and concurrent retirement is reported. No uptime/healthy credit, "
              "24h capacity/quality qualification, profitability or 180d storage guarantee. "
              "Terminal frozen quality audit and separate resource review remain required."}
    if first is not None and last is not None:
        report["measured_elapsed_seconds"] = (last["elapsed_monotonic_seconds"]
                                              - first["elapsed_monotonic_seconds"])
        report["collector_cpu_seconds_in_observed_span"] = (
            last["process"]["cpu_ticks"] - first["process"]["cpu_ticks"]
        ) / report["clock_ticks_per_second"]
        report["committed_feature_growth_bytes"] = last["feature_bytes"] - first["feature_bytes"]
    with (folder / "REPORT.json").open("x", encoding="utf-8") as stream:
        stream.write(json.dumps(report, indent=2, ensure_ascii=False, allow_nan=False) + "\n")
    print(json.dumps({"status": state, "samples": count, "directory": str(folder)}), flush=True)
    if state.startswith(("FAILED", "INTERRUPTED")):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
