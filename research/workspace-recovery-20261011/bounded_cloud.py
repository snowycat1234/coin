"""Recovered conservative cloud launcher; execution policy, not financial logic.

Reconstructed 2026-10-11 from the published scripts/research/cloud_bounded.py.
The missing prior launcher has no known byte hash: this is NOT byte-exact recovery.
"""
import argparse
import json
import os
import resource
import signal
import subprocess
import time
from pathlib import Path

ADDRESS = 4_000_000_000
RSS = 2_000_000_000
HOST_USED = 8_000_000_000
SECONDS = 1200


def limits():
    resource.setrlimit(resource.RLIMIT_AS, (ADDRESS, ADDRESS))
    resource.setrlimit(resource.RLIMIT_CPU, (SECONDS, SECONDS))
    os.sched_setaffinity(0, {min(os.sched_getaffinity(0))})


def process_rss(root):
    pending = [root]
    total = 0
    while pending:
        pid = pending.pop()
        try:
            status = Path(f"/proc/{pid}/status").read_text()
            total += next((int(x.split()[1]) * 1024 for x in status.splitlines()
                           if x.startswith("VmRSS:")), 0)
            pending.extend(map(int, Path(f"/proc/{pid}/task/{pid}/children").read_text().split()))
        except (FileNotFoundError, ProcessLookupError):
            pass
    return total


def host_used():
    mem = {line.split(":")[0]: int(line.split()[1]) * 1024
           for line in Path("/proc/meminfo").read_text().splitlines()}
    return mem["MemTotal"] - mem["MemAvailable"]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--seconds", type=int, default=SECONDS)
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    command = args.command[1:] if args.command[:1] == ["--"] else args.command
    if not 1 <= args.seconds <= SECONDS or not command:
        raise ValueError("One explicit sequential job with at most 1200 seconds required")
    if args.report.exists():
        raise FileExistsError("Never overwrite an existing resource receipt")
    if len(Path("/proc/swaps").read_text().splitlines()) != 1:
        raise RuntimeError("Active swap is not permitted")
    if host_used() > HOST_USED:
        raise RuntimeError("Host used memory exceeds budget before launch")
    env = dict(os.environ, COIN_CLOUD_BOUNDED="1", CUDA_VISIBLE_DEVICES="",
               OPENBLAS_NUM_THREADS="1", OMP_NUM_THREADS="1", MKL_NUM_THREADS="1",
               POLARS_MAX_THREADS="1", NUMEXPR_NUM_THREADS="1", RAYON_NUM_THREADS="1",
               PYTHONDONTWRITEBYTECODE="1")
    began = time.monotonic()
    child = subprocess.Popen(command, env=env, preexec_fn=limits, start_new_session=True)
    peak_rss = 0
    peak_host = 0
    reason = None
    try:
        while child.poll() is None:
            peak_rss = max(peak_rss, process_rss(child.pid))
            peak_host = max(peak_host, host_used())
            if peak_rss > RSS or peak_host > HOST_USED or time.monotonic() - began > args.seconds:
                reason = ("AGGREGATE_RSS" if peak_rss > RSS else
                          "HOST_USED" if peak_host > HOST_USED else "WALL_TIME")
                os.killpg(child.pid, signal.SIGTERM)
                try:
                    child.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    os.killpg(child.pid, signal.SIGKILL)
                    child.wait()
                break
            time.sleep(.1)
    finally:
        if child.poll() is None:
            os.killpg(child.pid, signal.SIGTERM)
            try:
                child.wait(timeout=10)
            except subprocess.TimeoutExpired:
                os.killpg(child.pid, signal.SIGKILL)
                child.wait()
    report = dict(exit_code=child.returncode, stop_reason=reason,
                  elapsed_seconds=time.monotonic() - began,
                  maximum_sampled_descendant_RSS_bytes=peak_rss,
                  maximum_host_used_bytes=peak_host,
                  RSS_sampling_seconds=.1, peak_is_sampled_not_kernel_peak=True,
                  per_process_address_limit_bytes=ADDRESS, aggregate_RSS_stop_bytes=RSS,
                  host_used_stop_bytes=HOST_USED, cpu_time_limit_seconds=SECONDS,
                  wall_limit_seconds=args.seconds, affinity_cpu_count=1,
                  thread_limit=1, gpu_enabled=False, swap_active=False,
                  shared_cgroup_enforcement=False, single_wallet_worker_required=True,
                  recovery="RECONSTRUCTED_RESOURCE_GUARD_NOT_BYTE_EXACT_PRIOR")
    args.report.parent.mkdir(parents=True, exist_ok=True)
    with args.report.open("x") as stream:
        stream.write(json.dumps(report, indent=2) + "\n")
    raise SystemExit(child.returncode or (1 if reason else 0))


if __name__ == "__main__":
    main()
