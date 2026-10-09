"""At most two existing bounded workers; independently export every terminal."""

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

from .export import aggregate, export_fold, verify_bundle
from .protocol import FOLDS
from .stage import SUCCESS, emit, prepare, train_fold


def run(state, output, producer_commit, destination):
    ready = json.loads((output / "READY.json").read_text())
    cpus = sorted(os.sched_getaffinity(0))[:2]
    if len(cpus) != 2 or int(Path("/sys/fs/cgroup/memory.swap.current").read_text()):
        raise ValueError("Two controller CPUs and zero swap required")
    pending, active, failures, completed = list(FOLDS), {}, {}, []
    destination.mkdir(parents=True, exist_ok=True)
    binding = dict(run_id=digest(ready), specification=ready)

    def launch(fold, cpu):
        ordinal = len(list(output.glob(fold + "_SLICE_*_RESOURCES.json"))) + 1
        report = output / f"{fold}_SLICE_{ordinal:02d}_RESOURCES.json"
        log = (output / f"{fold}_SLICE_{ordinal:02d}.log").open("a")
        child = subprocess.Popen(
            [
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
                "modules.temporal_prequential_transfer",
                "fold",
                "--state",
                str(state),
                "--output",
                str(output),
                "--fold",
                fold,
            ],
            stdout=log,
            stderr=subprocess.STDOUT,
        )
        active[fold] = child, log, cpu, ordinal
        emit(
            dict(
                stage="prequential_worker_started", fold=fold, cpu=cpu, slice=ordinal, PID=child.pid
            )
        )

    def finish(fold):
        terminal = json.loads((output / fold / "TERMINAL.json").read_text())
        if terminal["status"] != SUCCESS:
            failures[fold] = terminal
            emit(dict(stage="prequential_independent_fold_blocked", fold=fold, failure=terminal))
            return
        path = destination / fold
        if path.exists():
            score = verify_bundle(path)
        else:
            score = export_fold(state, output, fold, path, producer_commit)
        completed.append(fold)
        _atomic_json(output / (fold + "_EXPORT_RECEIPT.json"), score)
        emit(
            dict(
                stage="prequential_fold_complete",
                fold=fold,
                completed_updates=512,
                train_loss=terminal["diagnostics"][-1]["date_mean_loss"],
                forward_PnL=score["policies"]["FRESH_GRU"]["net_PnL"],
                primary_PnL_excess=score["primary_PnL_excess"],
                model_identity=score["model_identity"],
            )
        )

    def guarded_finish(fold):
        try:
            finish(fold)
        except Exception as error:
            failures[fold] = dict(
                status="FORWARD_EXPORT_OR_PATH_FAILURE",
                type=type(error).__name__,
                message=str(error),
            )
            emit(dict(stage="prequential_export_blocked", fold=fold, **failures[fold]))

    with run_guard(output, binding):
        while pending or active:
            occupied = {x[2] for x in active.values()}
            for cpu in cpus:
                if not pending or cpu in occupied:
                    continue
                fold = pending.pop(0)
                if (output / fold / "TERMINAL.json").exists():
                    guarded_finish(fold)
                else:
                    launch(fold, cpu)
            for fold, (child, log, cpu, ordinal) in list(active.items()):
                code = child.poll()
                if code is None:
                    continue
                log.close()
                del active[fold]
                if code:
                    failures[fold] = dict(
                        status="WORKER_EXIT",
                        exit_code=code,
                        slice=ordinal,
                        atomic_checkpoint_preserved=(output / fold / "latest.json").exists(),
                    )
                    emit(dict(stage="prequential_worker_blocked", fold=fold, **failures[fold]))
                elif (output / fold / "TERMINAL.json").exists():
                    guarded_finish(fold)
                else:
                    try:
                        receipt = json.loads((output / fold / "SLICE_RECEIPT.json").read_text())
                        pointer = json.loads((output / fold / "latest.json").read_text())
                        if (
                            receipt["status"] != "SLICE_EXHAUSTED_RESUME_REQUIRED"
                            or receipt["model_identity"] != pointer["model_identity"]
                            or receipt["completed_updates"] != pointer["step"]
                        ):
                            raise ValueError("Invalid atomic slice checkpoint binding")
                        launch(fold, cpu)
                    except Exception as error:
                        failures[fold] = dict(
                            status="INVALID_SLICE_RESUME_BINDING",
                            type=type(error).__name__,
                            message=str(error),
                        )
                        emit(dict(stage="prequential_resume_blocked", fold=fold, **failures[fold]))
            time.sleep(1)
        result = aggregate(destination)
        _atomic_json(
            output / "CONTROLLER_TERMINAL.json",
            dict(completed=completed, failures=failures, aggregate=result),
        )
        emit(
            dict(
                stage="prequential_all_admissible_folds_finished",
                completed=completed,
                failures=failures,
                screen_pass=result["screen_pass"],
            )
        )


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("mode", choices=("check", "fold", "run", "export", "aggregate"))
    p.add_argument("--state", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--fold", choices=FOLDS)
    p.add_argument("--producer-commit")
    p.add_argument("--destination", type=Path)
    a = p.parse_args()
    if os.environ.get("COIN_CLOUD_BOUNDED") != "1":
        raise ValueError("Existing bounded resource launcher required")
    torch.set_num_threads(1)
    torch.use_deterministic_algorithms(True)
    state, output = a.state.resolve(), a.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    if a.mode == "check":
        prepare(state, output)
    elif a.mode == "fold":
        if len(os.sched_getaffinity(0)) != 1 or a.fold is None:
            raise ValueError("One CPU and named fold required")
        train_fold(state, output, a.fold)
    elif a.mode == "aggregate":
        aggregate(a.destination)
    elif a.mode == "export":
        export_fold(state, output, a.fold, a.destination, a.producer_commit)
    else:
        if a.producer_commit is None or a.destination is None:
            raise ValueError("Published producer and forward destination required")
        run(state, output, a.producer_commit, a.destination.resolve())


if __name__ == "__main__":
    main()
