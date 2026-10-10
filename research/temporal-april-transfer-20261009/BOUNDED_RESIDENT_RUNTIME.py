"""One CPU, resident2GB/shared8GB, virtual4GB; unchanged frozen fit command."""

import argparse
import hashlib
import importlib.util
import json
import os
import resource
import signal
import subprocess
import time
from pathlib import Path

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--report", type=Path, required=True)
parser.add_argument("command", nargs=argparse.REMAINDER)
args = parser.parse_args()
if args.report.exists() or not args.command:
    raise ValueError("Exclusive resource report and command required")
if len(Path("/proc/swaps").read_text().splitlines()) != 1:
    raise RuntimeError("No swap allowed")
source = Path(
    "/workspace/coin-temporal/research/two-expert-exact-recovery-20261009/runtime-delta/source/bounded_recovery.py"
)
expected = "2aca6619668c3a2f78aafd793fc777114b7c5efc6a7075ce848524c3e400e7da"
assert hashlib.sha256(source.read_bytes()).hexdigest() == expected
spec = importlib.util.spec_from_file_location("_unchanged_resident_monitor", source)
monitor = importlib.util.module_from_spec(spec)
spec.loader.exec_module(monitor)
cpu = min(os.sched_getaffinity(0))
env = dict(
    os.environ,
    COIN_CLOUD_BOUNDED="1",
    CUDA_VISIBLE_DEVICES="",
    OPENBLAS_NUM_THREADS="1",
    OMP_NUM_THREADS="1",
    MKL_NUM_THREADS="1",
    POLARS_MAX_THREADS="1",
    NUMEXPR_NUM_THREADS="1",
    ARROW_IO_THREADS="1",
    MALLOC_ARENA_MAX="1",
)


def limits():
    os.sched_setaffinity(0, {cpu})
    resource.setrlimit(resource.RLIMIT_AS, (4000000000, 4000000000))
    resource.setrlimit(resource.RLIMIT_CPU, (1200, 1200))


began = time.monotonic()
process = subprocess.Popen(args.command, env=env, preexec_fn=limits, start_new_session=True)
peak, shared_peak, stop = 0, 0, None
while process.poll() is None:
    peak = max(peak, monitor.rss(process.pid))
    shared_peak = max(shared_peak, int(Path("/sys/fs/cgroup/memory.current").read_text()))
    if peak > 2000000000:
        stop = "RESIDENT_2GB_CAP"
    elif shared_peak > 8000000000:
        stop = "SHARED_8GB_CAP"
    elif int(Path("/sys/fs/cgroup/memory.swap.current").read_text()):
        stop = "SWAP_NOT_ALLOWED"
    elif time.monotonic() - began > 1200:
        stop = "REMAINING_SLICE_WALL_CAP"
    if stop:
        os.killpg(process.pid, signal.SIGTERM)
        break
    time.sleep(0.25)
code = process.wait(timeout=10)
receipt = dict(
    exit_code=code,
    stop_reason=stop,
    elapsed_seconds=time.monotonic() - began,
    maximum_sampled_descendant_RSS_bytes=peak,
    maximum_shared_cgroup_memory_bytes=shared_peak,
    resident_memory_stop_bytes=2000000000,
    virtual_address_limit_bytes=4000000000,
    shared_memory_stop_bytes=8000000000,
    cpu_index=cpu,
    per_arm_CPU_threads=1,
    maximum_actual_concurrent_workers=1,
    swap=False,
    GPU=False,
    reused_monitor_SHA256=expected,
    resource_only_launcher=True,
    economic_or_model_recipe_changed=False,
    RSS_sampling_seconds=0.25,
)
args.report.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
if code or stop:
    raise SystemExit(code or 1)
