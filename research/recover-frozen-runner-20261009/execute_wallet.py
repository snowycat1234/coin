"""Frozen serial-wallet entry point with cloud CPU/memory/time/disk bounds."""
from __future__ import annotations
import argparse
from datetime import UTC, datetime
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import resource
import shutil
import signal
import subprocess
import time

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]


def sha(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def read(path):
    return json.loads(path.read_bytes())


def require(ok, message):
    if not ok:
        raise ValueError(message)


def proof_check(state, plan):
    for relative, expected in plan["source_sha256"].items():
        require(sha(REPO / relative) == expected, "Frozen source/config identity differs: " + relative)
    require(sha(state / "okx86/RECOVERY.json") == plan["recovery_receipt_sha256"], "Data recovery receipt differs")
    root = state / "okx86"
    selected = {}
    member_count = 0
    for layer, expected in plan["transport_index_sha256"].items():
        directory = root / "transport" / layer
        require(sha(directory / "INDEX.json") == expected, "Pinned transport index differs")
        index = read(directory / "INDEX.json")
        for bundle in index.get("bundles", index.get("delta_bundles")):
            path = directory / bundle["manifest"]
            require(sha(path) == bundle["manifest_sha256"], "Published transport manifest differs")
            manifest = read(path)
            for member in manifest["members"]:
                file = root / "layers" / layer / member["path"]
                require(file.stat().st_size == member["bytes"] and sha(file) == member["sha256"], "Retained source evidence differs")
                selected[member["path"]] = member["sha256"]
                member_count += 1
    receipt = read(root / "RECOVERY.json")
    for file in receipt["direct_files"]:
        selected[file["path"]] = file["sha256"]
    for relative, expected in selected.items():
        require(sha(root / "selected" / relative) == expected, "Selected data bytes differ: " + relative)
    return dict(source_files=len(plan["source_sha256"]), transport_member_records=member_count,
                selected_files=len(selected), provider_downloads=0)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--policy", choices=("FIXED_VOL_HOLD", "FIXED_CSMOM21", "STATIC50"), required=True)
    parser.add_argument("--plan-commit", required=True)
    args = parser.parse_args()
    plan = read(HERE / "EXECUTION_PLAN.json")
    frozen = subprocess.check_output(["git", "-C", str(REPO), "show",
        args.plan_commit + ":research/recover-frozen-runner-20261009/EXECUTION_PLAN.json"])
    require(frozen == (HERE / "EXECUTION_PLAN.json").read_bytes(), "Published execution-plan commit required")
    require(not args.output.exists(), "Fresh independent wallet output required")
    require(shutil.disk_usage(args.state).free >= plan["limits"]["disk_reserve_bytes"], "15 GiB disk reserve required")
    # Set limits before importing native numerical libraries. AS is stricter
    # than an RSS-only 6 GB limit for this single, childless research process.
    for name in ("POLARS_MAX_THREADS", "OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
        os.environ[name] = "1"
    available = os.sched_getaffinity(0)
    os.sched_setaffinity(0, {min(available)})
    require(len(os.sched_getaffinity(0)) == 1, "One CPU affinity required")
    memory = plan["limits"]["memory_bytes"]
    resource.setrlimit(resource.RLIMIT_AS, (memory, memory))
    resource.setrlimit(resource.RLIMIT_CPU, (600, 600))
    proof = proof_check(args.state, plan)
    spec = importlib.util.spec_from_file_location("frozen_baseline", HERE / "baseline.py")
    baseline = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(baseline)
    baseline.source_check()
    started = time.monotonic()
    start_utc = datetime.now(UTC).isoformat()
    status, error = "RUNNING", None
    args.output.parent.mkdir(parents=True, exist_ok=True)
    start_receipt = args.output.parent / (args.policy + ".STARTED.json")
    with start_receipt.open("x") as stream:
        json.dump(dict(policy=args.policy, status=status, actual_started_UTC=start_utc,
            plan_commit=args.plan_commit, plan_sha256=sha(HERE / "EXECUTION_PLAN.json"),
            limits=plan["limits"], source_and_input_proof=proof), stream, indent=2)
    def alarm(signum, frame):
        raise TimeoutError("600-second per-wallet wall-clock cap")
    signal.signal(signal.SIGALRM, alarm)
    signal.setitimer(signal.ITIMER_REAL, 600)
    try:
        saved = baseline.run(args.state, args.policy, args.output, limit_seconds=600,
                             reserve_bytes=plan["limits"]["disk_reserve_bytes"])
        status = "COMPLETE_CONDITIONAL_ACCOUNT"
        summary = saved["summary"]
        print(json.dumps({k: summary[k] for k in ("NAV", "net_PnL", "fees_USDT", "execution_cost_USDT",
                                                  "funding_USDT", "completed_minutes", "terminal_cash_realized", "liquidation_count")}), flush=True)
    except BaseException as exc:
        status, error = "FAILED_PREFIX_RETAINED", dict(type=type(exc).__name__, message=str(exc))
        raise
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        receipt = dict(policy=args.policy, status=status, error=error, actual_started_UTC=start_utc,
            actual_finished_UTC=datetime.now(UTC).isoformat(), elapsed_seconds=time.monotonic()-started,
            peak_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024,
            plan_commit=args.plan_commit, plan_sha256=sha(HERE / "EXECUTION_PLAN.json"),
            limits=plan["limits"], source_and_input_proof=proof, independent_audit="PENDING")
        if args.output.exists():
            with (args.output / "EXECUTION.json").open("x") as stream:
                json.dump(receipt, stream, indent=2)
                stream.write("\n")


if __name__ == "__main__":
    main()
