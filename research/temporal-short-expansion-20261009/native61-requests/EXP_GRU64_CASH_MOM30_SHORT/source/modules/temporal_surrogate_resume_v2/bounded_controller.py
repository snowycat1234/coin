"""Two-CPU controller guard; each arm retains its original one-CPU/2GB guard."""

import argparse
import importlib.util
import json
import os
import resource
import signal
import subprocess
import time
from pathlib import Path


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--report", type=Path, required=True)
    p.add_argument("command", nargs=argparse.REMAINDER)
    a = p.parse_args()
    if not a.command or a.report.exists():
        raise ValueError("Exclusive controller resource receipt required")
    if len(Path("/proc/swaps").read_text().splitlines()) != 1:
        raise ValueError("No swap permitted")
    cpus = sorted(os.sched_getaffinity(0))[:2]
    if len(cpus) != 2:
        raise ValueError("Two CPU affinities required")
    source = (
        Path(__file__).resolve().parents[2]
        / "research/two-expert-exact-recovery-20261009/runtime-delta/source/bounded_recovery.py"
    )
    import hashlib

    if (
        hashlib.sha256(source.read_bytes()).hexdigest()
        != "2aca6619668c3a2f78aafd793fc777114b7c5efc6a7075ce848524c3e400e7da"
    ):
        raise ValueError("Frozen resource monitor required")
    spec = importlib.util.spec_from_file_location("_v2_frozen_resource_monitor", source)
    monitor = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(monitor)
    env = dict(
        os.environ,
        COIN_CLOUD_BOUNDED="1",
        CUDA_VISIBLE_DEVICES="",
        OPENBLAS_NUM_THREADS="1",
        OMP_NUM_THREADS="1",
        MKL_NUM_THREADS="1",
        POLARS_MAX_THREADS="1",
    )

    def limits():
        os.sched_setaffinity(0, set(cpus))
        resource.setrlimit(resource.RLIMIT_AS, (2_000_000_000, 2_000_000_000))

    started = time.monotonic()
    process = subprocess.Popen(a.command, env=env, preexec_fn=limits, start_new_session=True)
    peak, shared_peak, stop = 0, 0, None
    while process.poll() is None:
        peak = max(peak, monitor.rss(process.pid))
        shared_peak = max(shared_peak, int(Path("/sys/fs/cgroup/memory.current").read_text()))
        if time.monotonic() - started > 5000:
            stop = "CONTROLLER_TOTAL_WALL_CAP"
        if shared_peak > 8_000_000_000 or peak > 8_000_000_000:
            stop = "ORIGINAL_SHARED_8GB_RSS_CAP"
        if int(Path("/sys/fs/cgroup/memory.swap.current").read_text()):
            stop = "SWAP_NOT_ALLOWED"
        if stop:
            # All descendants belong to this explicitly launched controller.
            pending = [process.pid]
            descendants = []
            while pending:
                pid = pending.pop()
                descendants.append(pid)
                try:
                    pending.extend(
                        map(int, Path(f"/proc/{pid}/task/{pid}/children").read_text().split())
                    )
                except FileNotFoundError:
                    pass
            for pid in reversed(descendants):
                try:
                    os.kill(pid, signal.SIGTERM)
                except ProcessLookupError:
                    pass
            break
        time.sleep(0.25)
    code = process.wait(timeout=10)
    receipt = dict(
        exit_code=code,
        stop_reason=stop,
        elapsed_seconds=time.monotonic() - started,
        maximum_sampled_descendant_RSS_bytes=peak,
        maximum_shared_cgroup_memory_bytes=shared_peak,
        controller_CPU_affinity=cpus,
        per_arm_CPU_threads=1,
        per_arm_memory_bytes=2_000_000_000,
        maximum_concurrent_arms=2,
        shared_memory_stop_bytes=8_000_000_000,
        swap=False,
        GPU=False,
    )
    a.report.parent.mkdir(parents=True, exist_ok=True)
    a.report.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    if code or stop:
        raise SystemExit(code or 1)


if __name__ == "__main__":
    main()
