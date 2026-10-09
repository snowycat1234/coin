"""Run the one frozen pair under the existing bounded resource launchers."""

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import torch

from modules.temporal_two_expert.checkpoint import run_guard
from modules.temporal_two_expert.inputs import digest

from .export import export_native, score
from .stage import ARMS, emit, prepare, train_arm


def run(state, output, producer_commit, request_directory):
    ready = json.loads((output / "READY.json").read_text())
    binding = dict(run_id=digest(ready), specification=ready)
    cpus = sorted(os.sched_getaffinity(0))[:2]
    if len(cpus) != 2:
        raise ValueError("Two CPU affinities required")
    if int(Path("/sys/fs/cgroup/memory.swap.current").read_text()):
        raise ValueError("Swap prohibited")
    active = {}
    with run_guard(output, binding):
        for cpu, arm in zip(cpus, ARMS, strict=True):
            if (output / arm / "TERMINAL.json").exists():
                continue
            log = (output / (arm + ".log")).open("a")
            resources = output / (arm + "_RESOURCES.json")
            if resources.exists():
                raise ValueError("Inspect existing nonterminal resource receipt before resume")
            command = [
                "taskset",
                "-c",
                str(cpu),
                sys.executable,
                "-m",
                "modules.temporal_two_expert.bounded_comparison",
                "--report",
                str(resources),
                sys.executable,
                "-m",
                "modules.temporal_expert_input",
                "arm",
                "--state",
                str(state),
                "--output",
                str(output),
                "--arm",
                arm,
            ]
            p = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT)
            active[arm] = (p, log)
            emit(dict(stage="expert_input_worker_started", arm=arm, cpu=cpu, PID=p.pid))
        while active:
            for arm, (p, log) in list(active.items()):
                code = p.poll()
                if code is None:
                    continue
                log.close()
                del active[arm]
                if code or not (output / arm / "TERMINAL.json").exists():
                    raise RuntimeError(f"{arm} exited{code}; last atomic checkpoint retained")
                destination = request_directory / ("EXP_" + arm)
                if not destination.exists():
                    emit(
                        dict(
                            stage="expert_input_terminal_request_export",
                            **export_native(state, output, arm, destination, producer_commit),
                        )
                    )
            time.sleep(1)
        score(state, output)
        emit(dict(stage="matched_expert_input_all_terminal_and_scored"))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("mode", choices=("check", "arm", "run", "score", "export"))
    p.add_argument("--state", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--arm", choices=ARMS)
    p.add_argument("--producer-commit")
    p.add_argument("--request-directory", type=Path)
    args = p.parse_args()
    if os.environ.get("COIN_CLOUD_BOUNDED") != "1":
        raise ValueError("Bounded launcher required")
    torch.set_num_threads(1)
    torch.use_deterministic_algorithms(True)
    state, output = args.state.resolve(), args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    if args.mode == "check":
        prepare(state, output)
    elif args.mode == "arm":
        if len(os.sched_getaffinity(0)) != 1 or args.arm is None:
            raise ValueError("Named one-CPU arm required")
        train_arm(state, output, args.arm)
    elif args.mode == "score":
        score(state, output)
    else:
        if args.producer_commit is None or args.request_directory is None:
            raise ValueError("Published producer commit and explicit request directory required")
        if args.mode == "run":
            run(state, output, args.producer_commit, args.request_directory.resolve())
        else:
            emit(
                export_native(state, output, args.arm, args.request_directory, args.producer_commit)
            )


if __name__ == "__main__":
    main()
