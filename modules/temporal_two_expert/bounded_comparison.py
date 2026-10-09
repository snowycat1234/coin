"""Resource-only one-CPU launcher for the one frozen four-fit comparison."""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import resource
import signal
import subprocess
import time
from pathlib import Path

from .comparison import PROTOCOL
from .exact import sha

LAUNCHER_SHA = "2aca6619668c3a2f78aafd793fc777114b7c5efc6a7075ce848524c3e400e7da"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    if not args.command or args.report.exists():
        raise ValueError("One explicit command and exclusive resource receipt required")
    if len(Path("/proc/swaps").read_text().splitlines()) != 1:
        raise RuntimeError("Swap must be absent")
    source = (
        Path(__file__).resolve().parents[2]
        / "research/two-expert-exact-recovery-20261009/runtime-delta/source/bounded_recovery.py"
    )
    if sha(source) != LAUNCHER_SHA:
        raise ValueError("Unchanged recovered resource monitor required")
    spec = importlib.util.spec_from_file_location("_unchanged_recovery_resource_monitor", source)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    limit = PROTOCOL["limits"]
    memory, seconds = limit["memory_bytes"], limit["total_wall_seconds"]
    cpu = min(os.sched_getaffinity(0))
    env = dict(
        os.environ,
        COIN_CLOUD_BOUNDED="1",
        CUDA_VISIBLE_DEVICES="",
        OPENBLAS_NUM_THREADS="1",
        OMP_NUM_THREADS="1",
        MKL_NUM_THREADS="1",
        POLARS_MAX_THREADS="1",
    )

    def constrain():
        os.sched_setaffinity(0, {cpu})
        resource.setrlimit(resource.RLIMIT_AS, (memory, memory))
        resource.setrlimit(resource.RLIMIT_CPU, (seconds, seconds))

    began, peak, stop = time.monotonic(), 0, None
    child = subprocess.Popen(args.command, env=env, preexec_fn=constrain, start_new_session=True)
    try:
        while child.poll() is None:
            peak = max(peak, module.rss(child.pid))
            if time.monotonic() - began > seconds:
                stop = "TOTAL_WALL_TIME_CAP"
            elif peak > memory:
                stop = "AGGREGATE_RSS_CAP"
            if stop:
                os.killpg(child.pid, signal.SIGTERM)
                try:
                    child.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    os.killpg(child.pid, signal.SIGKILL)
                break
            time.sleep(0.25)
        code = child.wait()
    finally:
        receipt = dict(
            exit_code=child.returncode,
            stop_reason=stop,
            elapsed_seconds=time.monotonic() - began,
            maximum_sampled_descendant_RSS_bytes=peak,
            RSS_sampling_seconds=0.25,
            per_process_address_limit_bytes=memory,
            aggregate_RSS_stop_bytes=memory,
            single_CPU_affinity_enforced=True,
            cpu_index=cpu,
            GPU=False,
            swap=False,
            wall_seconds=seconds,
            resource_only_launcher=True,
            reused_monitor_SHA256=LAUNCHER_SHA,
        )
        args.report.parent.mkdir(parents=True, exist_ok=True)
        with args.report.open("x") as stream:
            json.dump(receipt, stream, indent=2)
            stream.write("\n")
    if code or stop:
        raise SystemExit(code or 1)


if __name__ == "__main__":
    main()
