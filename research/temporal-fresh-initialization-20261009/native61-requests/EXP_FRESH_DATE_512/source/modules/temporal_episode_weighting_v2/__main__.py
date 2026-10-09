"""Two workers, resumable wall slices, fixed512 terminals and immediate exports."""

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import torch

from modules.temporal_two_expert.checkpoint import _atomic_json, run_guard
from modules.temporal_two_expert.inputs import digest

from .export import export_native, score
from .stage import ARMS, SUCCESS, emit, prepare, train_arm


def run(state, output, producer_commit, request_directory):
    ready = json.loads((output / "READY.json").read_text())
    binding = dict(run_id=digest(ready), specification=ready)
    cpus = sorted(os.sched_getaffinity(0))[:2]
    if len(cpus) != 2 or int(Path("/sys/fs/cgroup/memory.swap.current").read_text()):
        raise ValueError("Two CPU affinities and no swap required")
    active = {}

    def launch(arm, cpu):
        ordinal = 1 + len(list(output.glob(arm + "_SLICE_*_RESOURCES.json")))
        resource = output / f"{arm}_SLICE_{ordinal:02d}_RESOURCES.json"
        if resource.exists():
            raise ValueError("Immutable numbered worker resource receipt required")
        log = (output / f"{arm}_SLICE_{ordinal:02d}.log").open("a")
        command = [
            "taskset",
            "-c",
            str(cpu),
            sys.executable,
            "-m",
            "modules.temporal_two_expert.bounded_comparison",
            "--report",
            str(resource),
            sys.executable,
            "-m",
            "modules.temporal_episode_weighting_v2",
            "arm",
            "--state",
            str(state),
            "--output",
            str(output),
            "--arm",
            arm,
        ]
        child = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT)
        active[arm] = child, log, cpu, ordinal
        emit(
            dict(
                stage="weighting_worker_slice_started",
                arm=arm,
                cpu=cpu,
                slice=ordinal,
                PID=child.pid,
                fixed_update_target=512,
            )
        )

    def export(arm):
        t = json.loads((output / arm / "TERMINAL.json").read_text())
        if t["status"] != SUCCESS or t["completed_stage_updates"] != 512:
            raise RuntimeError(
                f"{arm} failure preserved; inspect FAILURE.json; no objective changes"
            )
        destination = request_directory / ("EXP_" + arm)
        if not destination.exists():
            record = export_native(state, output, arm, destination, producer_commit)
            _atomic_json(output / (arm + "_EXPORT_RECEIPT.json"), record)
            emit(dict(stage="weighting_terminal_immediate_export", **record))

    with run_guard(output, binding):
        for cpu, arm in zip(cpus, ARMS, strict=True):
            if (output / arm / "TERMINAL.json").exists():
                export(arm)
            else:
                launch(arm, cpu)
        while active:
            for arm, (child, log, cpu, ordinal) in list(active.items()):
                code = child.poll()
                if code is None:
                    continue
                log.close()
                del active[arm]
                if code:
                    raise RuntimeError(
                        f"{arm} slice{ordinal} exited{code}; atomic checkpoint retained"
                    )
                if (output / arm / "TERMINAL.json").exists():
                    export(arm)
                else:
                    receipt = json.loads((output / arm / "SLICE_RECEIPT.json").read_text())
                    pointer = json.loads((output / arm / "latest.json").read_text())
                    if (
                        receipt["status"] != "SLICE_EXHAUSTED_RESUME_REQUIRED"
                        or receipt["model_identity"] != pointer["model_identity"]
                        or receipt["cumulative_Adam_step"] != pointer["step"]
                    ):
                        raise ValueError(
                            "Valid last atomic slice checkpoint required before resume"
                        )
                    launch(arm, cpu)
            time.sleep(1)
        score(state, output)
        emit(dict(stage="both_weighting_fixed512_terminals_scored"))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("check", "arm", "run", "score", "export"))
    parser.add_argument("--state", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--arm", choices=ARMS)
    parser.add_argument("--producer-commit")
    parser.add_argument("--request-directory", type=Path)
    args = parser.parse_args()
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
        if (
            args.producer_commit is None
            or args.request_directory is None
            or (args.mode == "export" and args.arm is None)
        ):
            raise ValueError(
                "Published producer, explicit destination and named export arm required"
            )
        if args.mode == "run":
            run(state, output, args.producer_commit, args.request_directory.resolve())
        else:
            emit(
                export_native(state, output, args.arm, args.request_directory, args.producer_commit)
            )


if __name__ == "__main__":
    main()
