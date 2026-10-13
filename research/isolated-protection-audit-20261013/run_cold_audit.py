"""Sequential, read-only cold-audit controller with conservative host limits."""
from __future__ import annotations

import json
import os
from pathlib import Path
import resource
import shutil
import subprocess
import sys

HERE = Path(__file__).resolve().parent
WORKSPACE = HERE.parent
STATE = WORKSPACE / "coin_margin_protective_runner_20261013/state_20261013"
MANIFEST = WORKSPACE / "coin_margin_protective_policy_20261013/RUN_MANIFEST.json"
AUDIT_AS_LIMIT = 4_000_000_000
AUDIT_CPU_LIMIT = 240
AUDIT_WALL_LIMIT = 300
HOST_USED_LIMIT = 8_000_000_000
DISK_RESERVE = 16_106_127_360


def resource_gate():
    values = {}
    for line in Path("/proc/meminfo").read_text().splitlines():
        key, _, rest = line.partition(":")
        if key in ("MemTotal", "MemAvailable", "SwapTotal"):
            values[key] = int(rest.split()[0]) * 1024
    if set(values) != {"MemTotal", "MemAvailable", "SwapTotal"}:
        raise RuntimeError("Memory telemetry unavailable")
    if values["SwapTotal"] or len(Path("/proc/swaps").read_text().splitlines()) != 1:
        raise RuntimeError("Cold audit zero-swap requirement violated")
    if values["MemTotal"] - values["MemAvailable"] + 2_000_000_000 > HOST_USED_LIMIT:
        raise RuntimeError("Insufficient host RAM for cold audit")
    if shutil.disk_usage(HERE).free < DISK_RESERVE + 100_000_000:
        raise RuntimeError("Cold audit disk reserve unavailable")
    cpus = sorted(os.sched_getaffinity(0))
    if not cpus:
        raise RuntimeError("No assigned CPU")
    return cpus[0]


def limit(cpu):
    resource.setrlimit(resource.RLIMIT_AS, (AUDIT_AS_LIMIT, AUDIT_AS_LIMIT))
    resource.setrlimit(resource.RLIMIT_CPU, (AUDIT_CPU_LIMIT, AUDIT_CPU_LIMIT))
    os.sched_setaffinity(0, {cpu})


def main():
    manifest = json.loads(MANIFEST.read_text())
    ids = [c["case_id"] for c in manifest["cases"]]
    if len(ids) != 11 or len(set(ids)) != 11:
        raise RuntimeError("Exactly 11 unique preregistered cases required")
    controller = json.loads((STATE / "RESOURCE_RECEIPTS.json").read_text())
    if (controller.get("status") != "ALL_STARTED_CASES_FINISHED" or
            controller.get("unstarted_case_ids") or
            set(controller["per_case"]) != set(ids)):
        raise RuntimeError("All original guard workers must finish before audit")
    if any(controller["per_case"][i].get("exit_code") != 0 for i in ids):
        raise RuntimeError("A financial case failed; audit cannot call all cases complete")
    for case_id in ids:
        if (HERE / "receipts" / f"{case_id}.json").exists():
            raise FileExistsError("Never silently overwrite a cold-audit receipt")
        cpu = resource_gate()
        env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", PYTHONOPTIMIZE="0",
                   OPENBLAS_NUM_THREADS="1", OMP_NUM_THREADS="1", MKL_NUM_THREADS="1",
                   POLARS_MAX_THREADS="1", NUMEXPR_NUM_THREADS="1", RAYON_NUM_THREADS="1",
                   CUDA_VISIBLE_DEVICES="")
        completed = subprocess.run([sys.executable, str(HERE / "cold_audit.py"), case_id],
                                   env=env, preexec_fn=lambda cpu=cpu: limit(cpu),
                                   capture_output=True, text=True, timeout=AUDIT_WALL_LIMIT)
        print(completed.stdout, end="", flush=True)
        if completed.returncode:
            print(completed.stderr, file=sys.stderr, flush=True)
            raise RuntimeError(f"Cold audit failed on {case_id}: {completed.returncode}")
    subprocess.run([sys.executable, str(HERE / "build_report.py")], check=True)


if __name__ == "__main__":
    main()
