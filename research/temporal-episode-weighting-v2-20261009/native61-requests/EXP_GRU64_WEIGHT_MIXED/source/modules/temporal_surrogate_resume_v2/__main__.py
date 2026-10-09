"""Bounded preflight, independent arm worker, or max-two continuation controller."""

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import numpy as np
import torch

from modules.temporal_two_expert.checkpoint import (
    _atomic_json,
    model_identity,
    run_guard,
)
from modules.temporal_two_expert.comparison import ARMS, _evaluate_training
from modules.temporal_two_expert.inputs import digest

from .export import freeze_and_export
from .gradient import memory_bounded_gradients_v2
from .stage import PROTOCOL_V2, load_inputs, original_model, stage_sources, train_stage, warm_parent


def arm_names():
    return [f + ("_WITH_CASH" if c else "_NO_CASH") for f, c in ARMS]


def prepare(state, output, *, check_gradients):
    train, _, prototype, dataset, scaler = load_inputs(state)
    parents, preflight = {}, {}
    for family, cash in ARMS:
        name = family + ("_WITH_CASH" if cash else "_NO_CASH")
        model = original_model(scaler, family, cash)
        optimizer, parent = warm_parent(state / "four-fit" / name, model)
        parents[name] = parent
        if check_gradients:
            rng = torch.get_rng_state().clone()
            before = model_identity(model)
            loss, norm, _ = _evaluate_training(
                model,
                optimizer,
                train,
                prototype,
                PROTOCOL_V2["feature_batch_size"],
                memory_bounded_gradients_v2,
            )
            assert torch.equal(rng, torch.get_rng_state()) and before == model_identity(model)
            assert np.isfinite(loss) and np.isfinite(norm)
            preflight[name] = dict(
                parent_step=parent["step"],
                model_identity=before,
                v2_initial_loss=loss,
                v2_initial_gradient_norm=norm,
                saved_RNG_preserved=True,
                optimizer_updates=0,
            )
            print(
                json.dumps(dict(stage="v2_warm_start_preflight", arm=name, **preflight[name])),
                flush=True,
            )
    specification = dict(
        protocol=PROTOCOL_V2,
        dataset=dataset,
        scaler_identity=scaler.identity,
        parent_snapshots=parents,
        versioned_sources=stage_sources(),
    )
    group = dict(run_id=digest(specification), specification=specification)
    output.mkdir(parents=True, exist_ok=True)
    if check_gradients:
        _atomic_json(
            output / "READY.json",
            dict(
                status="ALL_FOUR_WARM_STARTS_NUMERICALLY_READY",
                group=group,
                preflight=preflight,
                optimizer_updates=0,
            ),
        )
    return group, train, prototype, dataset, scaler


def run_all(state, output):
    ready = json.loads((output / "READY.json").read_text())
    group, _, _, _, _ = prepare(state, output, check_gradients=False)
    if group != ready["group"]:
        raise ValueError("Preflight source/parent/input identity changed")
    cpus = sorted(os.sched_getaffinity(0))[:2]
    if len(cpus) != 2:
        raise ValueError("Two independently available CPU affinities required")
    resources = dict(
        cpu_max=Path("/sys/fs/cgroup/cpu.max").read_text().strip(),
        memory_max=Path("/sys/fs/cgroup/memory.max").read_text().strip(),
        memory_current=int(Path("/sys/fs/cgroup/memory.current").read_text()),
        swap_current=int(Path("/sys/fs/cgroup/memory.swap.current").read_text()),
        max_concurrent_arms=2,
        worker_cpus=cpus,
        per_worker_memory_bytes=2_000_000_000,
        per_worker_threads=1,
    )
    if resources["swap_current"] or len(Path("/proc/swaps").read_text().splitlines()) != 1:
        raise ValueError("No swap permitted")
    _atomic_json(output / "EXECUTION_SCHEDULE.json", resources)
    waiting = arm_names()
    active = {}
    with run_guard(output, group):
        while waiting or active:
            for cpu in cpus:
                if cpu in active or not waiting:
                    continue
                name = waiting.pop(0)
                if (output / name / "TERMINAL.json").exists():
                    continue
                log = (output / (name + ".log")).open("a")
                report = output / (name + "_RESOURCES.json")
                if report.exists():
                    raise ValueError(
                        "Existing nonterminal resource receipt; inspect before resuming"
                    )
                command = [
                    "taskset",
                    "-c",
                    str(cpu),
                    sys.executable,
                    "-m",
                    "modules.temporal_two_expert.bounded_comparison",
                    "--report",
                    str(report),
                    sys.executable,
                    "-m",
                    "modules.temporal_surrogate_resume_v2",
                    "arm",
                    "--state",
                    str(state),
                    "--output",
                    str(output),
                    "--arm",
                    name,
                ]
                process = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT)
                active[cpu] = (name, process, log)
                print(
                    json.dumps(dict(stage="v2_worker_started", arm=name, cpu=cpu, PID=process.pid)),
                    flush=True,
                )
            for cpu, (name, process, log) in list(active.items()):
                code = process.poll()
                if code is None:
                    continue
                log.close()
                del active[cpu]
                if code != 0 or not (output / name / "TERMINAL.json").exists():
                    raise RuntimeError(
                        f"{name} worker exit {code}; last atomic checkpoint retained; inspect log"
                    )
                terminal = json.loads((output / name / "TERMINAL.json").read_text())
                print(
                    json.dumps(dict(stage="v2_worker_finished", arm=name, **terminal)), flush=True
                )
            time.sleep(1)
        freeze_and_export(state, output)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("mode", choices=["check", "arm", "run", "score"])
    p.add_argument("--state", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--arm", choices=arm_names())
    args = p.parse_args()
    if os.environ.get("COIN_CLOUD_BOUNDED") != "1":
        raise ValueError("Bounded resource launcher required")
    torch.set_num_threads(1)
    torch.use_deterministic_algorithms(True)
    state, output = args.state.resolve(), args.output.resolve()
    if args.mode == "check":
        prepare(state, output, check_gradients=True)
    elif args.mode == "arm":
        if len(os.sched_getaffinity(0)) != 1 or args.arm is None:
            raise ValueError("One-CPU named arm required")
        train, _, prototype, dataset, scaler = load_inputs(state)
        family, cash = next(
            (f, c) for f, c in ARMS if f + ("_WITH_CASH" if c else "_NO_CASH") == args.arm
        )
        train_stage(
            original_model(scaler, family, cash),
            train,
            prototype,
            state / "four-fit" / args.arm,
            output / args.arm,
            dataset,
        )
    elif args.mode == "score":
        freeze_and_export(state, output)
    else:
        run_all(state, output)


if __name__ == "__main__":
    main()
