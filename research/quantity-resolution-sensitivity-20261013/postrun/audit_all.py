"""Sequential bounded cold audit of exactly the completed twelve fine wallets."""
from __future__ import annotations

import json
import os
from pathlib import Path
import resource
import shutil
import subprocess
import sys
import time
from provenance import verify_completed_run

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
STATE = ROOT / "coin_quantity_resolution_20261013/state_20261013"
MODULE = ROOT / "coin_quantity_resolution_20261013"
AS_LIMIT = 4_000_000_000
CPU_LIMIT = 300
WALL_LIMIT = 360
RSS_COMMITMENT = 2_000_000_000
HOST_USED_LIMIT = 8_000_000_000
DISK_RESERVE = 16_106_127_360


def resource_gate(guard) -> int:
    mem = guard.memory_observation()
    if mem["SwapTotal"] or mem["active_swaps"] or mem.get("cgroup_swap_current", 0):
        raise RuntimeError("Audit requires zero swap")
    if mem["host_used"] + RSS_COMMITMENT > HOST_USED_LIMIT:
        raise RuntimeError("No 2GB audit commitment under shared 8GB cap")
    if (mem.get("cgroup_limit_verified") and
            mem["cgroup_memory_current"] + RSS_COMMITMENT > mem["cgroup_memory_max"]):
        raise RuntimeError("No 2GB audit commitment under cgroup cap")
    if shutil.disk_usage(HERE).free < DISK_RESERVE + 250_000_000:
        raise RuntimeError("Audit disk reserve unavailable")
    cpus = sorted(os.sched_getaffinity(0))
    if not cpus:
        raise RuntimeError("No assigned audit CPU")
    return 2 if 2 in cpus else cpus[0]


def limit(cpu: int) -> None:
    resource.setrlimit(resource.RLIMIT_AS, (AS_LIMIT, AS_LIMIT))
    resource.setrlimit(resource.RLIMIT_CPU, (CPU_LIMIT, CPU_LIMIT))
    os.sched_setaffinity(0, {cpu})


def main() -> None:
    sys.path.insert(0, str(MODULE))
    from run_cases import guard, preflight
    plan = preflight.bindings()
    ids = verify_completed_run(STATE, MODULE, plan)
    for identity in ids:
        if (HERE / "receipts" / f"{identity}.json").exists():
            raise FileExistsError("Never silently overwrite a fine cold-audit receipt")
        cpu = resource_gate(guard)
        env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", PYTHONOPTIMIZE="0",
                   OPENBLAS_NUM_THREADS="1", OMP_NUM_THREADS="1", MKL_NUM_THREADS="1",
                   POLARS_MAX_THREADS="1", NUMEXPR_NUM_THREADS="1", RAYON_NUM_THREADS="1",
                   CUDA_VISIBLE_DEVICES="")
        proc = subprocess.Popen([sys.executable, str(HERE / "cold_audit.py"), identity],
                                env=env, preexec_fn=lambda chosen=cpu: limit(chosen),
                                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                text=True, start_new_session=True)
        start, peak, stopped = time.monotonic(), 0, None
        try:
            while proc.poll() is None:
                mem = guard.memory_observation()
                peak = max(peak, guard.process_rss(proc.pid))
                stopped = ("WORKER_RSS" if peak > RSS_COMMITMENT else
                           "HOST_USED" if mem["host_used"] > HOST_USED_LIMIT else
                           "SWAP" if mem["SwapTotal"] or mem["active_swaps"] else
                           "CGROUP_SWAP" if mem.get("cgroup_swap_current", 0) else
                           "CGROUP_MEMORY" if mem.get("cgroup_limit_verified") and
                               mem["cgroup_memory_current"] > mem["cgroup_memory_max"] else
                           "DISK_RESERVE" if shutil.disk_usage(HERE).free < DISK_RESERVE else
                           "WALL_SECONDS" if time.monotonic() - start > WALL_LIMIT else None)
                if stopped:
                    guard.terminate(proc)
                    break
                time.sleep(.1)
            output, _ = proc.communicate(timeout=10)
        except BaseException:
            guard.terminate(proc)
            raise
        print(output, end="", flush=True)
        if proc.returncode or stopped:
            raise RuntimeError(f"Fine cold audit failed on {identity}: "
                               f"exit={proc.returncode}, stop={stopped}, peak_RSS={peak}")
        print("FINE_COLD_AUDIT_RESOURCE", identity, "sampled_peak_RSS", peak,
              "elapsed_seconds", time.monotonic() - start, flush=True)
    print("FINE_COLD_AUDIT_ALL_12_PASS", flush=True)


if __name__ == "__main__":
    main()
