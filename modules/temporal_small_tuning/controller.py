"""Bounded two-worker scheduler; fixed six tasks and exact checkpoint resume."""

import argparse
from concurrent.futures import ThreadPoolExecutor
import json
import os
from pathlib import Path
import resource
import subprocess
import threading
import time


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--python", required=True)
    parser.add_argument("--cpus", default="3,4")
    args = parser.parse_args()
    repo = Path(__file__).resolve().parents[2]
    ready = json.loads((args.output / "READY.json").read_text())
    if len(ready["tasks"]) != 6:
        raise ValueError("Exactly six prepared tasks required")
    cpus = [int(c) for c in args.cpus.split(",")]
    if len(cpus) != 2 or len(set(cpus)) != 2 or not set(cpus) <= os.sched_getaffinity(0):
        raise ValueError("Exactly two available worker CPU slots required")
    if len(Path("/proc/swaps").read_text().splitlines()) != 1:
        raise RuntimeError("Swap must be absent")
    # Low-memory parent; hard ceilings permit children to install approved guards.
    resource.setrlimit(resource.RLIMIT_AS, (1000000000, 4000000000))
    resource.setrlimit(resource.RLIMIT_CPU, (300, 1200))
    lock = threading.Lock()
    began = time.monotonic()
    events = []

    def event(record):
        with lock:
            record = dict(record, elapsed=time.monotonic() - began)
            events.append(record)
            with (args.output / "CONTROLLER_EVENTS.jsonl").open("a") as stream:
                stream.write(json.dumps(record) + "\n")
                stream.flush()
                os.fsync(stream.fileno())
            print(json.dumps(record), flush=True)

    tasks = list(ready["tasks"].values())
    # Same candidate on both folds concurrently, then the next candidate.
    order = [
        r["settings"]["task_id"]
        for candidate in ("BASE_DATE_LR1E3", "LOW_LR3E4", "MIXED_WALLET_HALF")
        for r in tasks
        if r["settings"]["candidate"] == candidate
    ]

    def worker_queue(cpu, queue):
        records = []
        for task_id in queue:
            folder = args.output / task_id
            existing = sorted(folder.glob("RESOURCE_SLICE_*.json"))
            elapsed = sum(json.loads(p.read_text())["elapsed_seconds"] for p in existing)
            index = len(existing)
            while not (folder / "TERMINAL.json").exists():
                if time.monotonic() - began > 12000 or elapsed >= 3600:
                    event(dict(stage="REAL_RESOURCE_STOP", task=task_id, elapsed_worker=elapsed))
                    records.append(
                        dict(
                            task=task_id, status="CONTROLLER_RESOURCE_STOP", elapsed_seconds=elapsed
                        )
                    )
                    break
                index += 1
                remaining = min(1100.0, max(0.01, 3600.0 - elapsed - 10.0))
                report = folder / f"RESOURCE_SLICE_{index:02d}.json"
                command = [
                    "taskset",
                    "-c",
                    str(cpu),
                    args.python,
                    str(
                        repo
                        / "research/temporal-april-transfer-20261009/BOUNDED_RESIDENT_RUNTIME.py"
                    ),
                    "--report",
                    str(report),
                    args.python,
                    "-m",
                    "modules.temporal_small_tuning",
                    "worker",
                    "--state",
                    str(args.state),
                    "--output",
                    str(args.output),
                    "--task",
                    task_id,
                    "--seconds",
                    str(remaining),
                ]
                event(dict(stage="WORKER_PROCESS_START", task=task_id, slice=index, cpu=cpu))
                env = dict(
                    os.environ,
                    PYTHONPATH=f"{repo}:{repo / 'src'}",
                    CUDA_VISIBLE_DEVICES="",
                    OMP_NUM_THREADS="1",
                    OPENBLAS_NUM_THREADS="1",
                    MKL_NUM_THREADS="1",
                    POLARS_MAX_THREADS="1",
                )
                with (folder / f"CONSOLE_SLICE_{index:02d}.jsonl").open("x") as stream:
                    process = subprocess.Popen(
                        command, cwd=repo, env=env, stdout=stream, stderr=subprocess.STDOUT
                    )
                    event(
                        dict(
                            stage="WORKER_PID",
                            task=task_id,
                            slice=index,
                            guard_pid=process.pid,
                            cpu=cpu,
                        )
                    )
                    code = process.wait()
                if report.exists():
                    resource_result = json.loads(report.read_text())
                    elapsed += resource_result["elapsed_seconds"]
                else:
                    raise RuntimeError("Resource guard exited without its receipt")
                pointer = json.loads((folder / "latest.json").read_text())
                event(
                    dict(
                        stage="WORKER_SLICE_EXIT",
                        task=task_id,
                        slice=index,
                        code=code,
                        updates=pointer["step"],
                        checkpoint_SHA256=pointer["SHA256"],
                        resource=resource_result,
                    )
                )
                if code and resource_result["stop_reason"] in (
                    "RESIDENT_2GB_CAP",
                    "SHARED_8GB_CAP",
                    "SWAP_NOT_ALLOWED",
                ):
                    records.append(
                        dict(task=task_id, status="REAL_RESOURCE_FAILURE", resource=resource_result)
                    )
                    break
                # Startup/environment interruption keeps the same bound checkpoint.
                # Numeric/path errors are terminal in the worker and never retried.
            if (folder / "TERMINAL.json").exists():
                records.append(json.loads((folder / "TERMINAL.json").read_text()))
        return records

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(worker_queue, cpu, order[i::2]) for i, cpu in enumerate(cpus)]
        results = [f.result() for f in futures]
    receipt = dict(
        status="SIX_FIXED_TASKS_CONTROLLER_FINISHED",
        elapsed_seconds=time.monotonic() - began,
        maximum_actual_concurrent_workers=2,
        cpus=cpus,
        shared_bytes=8000000000,
        swap=False,
        GPU=False,
        tasks=[r for batch in results for r in batch],
        events=events,
        reserve_read=False,
        planned_fits=6,
    )
    with (args.output / "CONTROLLER_RECEIPT.json").open("x") as stream:
        json.dump(receipt, stream, indent=2, sort_keys=True)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    event(dict(stage="CONTROLLER_DONE", completed_tasks=len(receipt["tasks"])))


if __name__ == "__main__":
    main()
