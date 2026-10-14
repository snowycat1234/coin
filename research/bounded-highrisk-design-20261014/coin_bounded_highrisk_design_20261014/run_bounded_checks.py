"""Three fixed synthetic commands with unique receipts; never a historical GO."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import resource
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent


def limits():
    os.sched_setaffinity(0, {min(os.sched_getaffinity(0))})
    resource.setrlimit(resource.RLIMIT_AS, (4 * 1024 ** 3, 4 * 1024 ** 3))
    resource.setrlimit(resource.RLIMIT_CPU, (60, 60))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--receipt-dir", default="toy_receipts_new")
    args = parser.parse_args()
    if not args.receipt_dir.startswith("toy_receipts") or "/" in args.receipt_dir or ".." in args.receipt_dir:
        raise SystemExit("Simple local synthetic receipt directory name required")
    out = HERE / args.receipt_dir
    out.mkdir(exist_ok=False)
    environment = dict(os.environ, OPENBLAS_NUM_THREADS="1", OMP_NUM_THREADS="1", MKL_NUM_THREADS="1")
    receipt = dict(status="RUNNING", commands=[], market_reads=0, historical_wallets=0,
                   source_freeze_SHA256=hashlib.sha256((HERE / "SOURCE_FREEZE.json").read_bytes()).hexdigest(),
                   bounds=dict(cpus=1, math_threads=1, address_space_bytes=4 * 1024 ** 3,
                               rss_stop_bytes=2 * 1024 ** 3, cpu_seconds=60, wall_seconds_per_command=120))
    commands = (("source_preflight.txt", [sys.executable, "source_preflight.py"]),
                ("unit_tests.txt", [sys.executable, "-m", "unittest", "-v", "test_bounded_highrisk"]),
                ("toy.json", [sys.executable, "run_toy.py"]))
    try:
        for name, cmd in commands:
            start = time.monotonic()
            max_rss = 0
            stopped = None
            with (out / name).open("w") as output:
                process = subprocess.Popen(cmd, cwd=HERE, env=environment, stdout=output,
                                           stderr=subprocess.STDOUT, preexec_fn=limits)
                while process.poll() is None:
                    elapsed = time.monotonic() - start
                    try:
                        status = Path(f"/proc/{process.pid}/status").read_text()
                        rss = int(next(line.split()[1] for line in status.splitlines()
                                       if line.startswith("VmRSS:"))) * 1024
                        max_rss = max(max_rss, rss)
                    except (FileNotFoundError, StopIteration, ProcessLookupError):
                        pass
                    if elapsed > 120 or max_rss > 2 * 1024 ** 3:
                        stopped = "WALL_LIMIT" if elapsed > 120 else "RSS_LIMIT"
                        process.kill()
                        break
                    time.sleep(.02)
                code = process.wait()
            receipt["commands"].append(dict(command=cmd, returncode=code, stopped=stopped,
                wall_seconds=time.monotonic() - start, sampled_max_rss_bytes=max_rss,
                output=name, output_sha256=hashlib.sha256((out / name).read_bytes()).hexdigest()))
            if code != 0 or stopped:
                raise RuntimeError("Bounded synthetic check failed: " + name)
        receipt["status"] = "PASS_SYNTHETIC_ONLY"
    except BaseException as error:
        receipt["status"] = "FAIL_SYNTHETIC_ONLY"
        receipt["failure"] = str(error)
        raise
    finally:
        (out / "RESOURCE_RECEIPT.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps(receipt, indent=2))


if __name__ == "__main__":
    main()
