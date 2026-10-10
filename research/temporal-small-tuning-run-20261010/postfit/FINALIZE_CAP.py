"""Finalize a controller-stopped fit without any additional optimizer update.

The frozen controller and trainer use different resource clocks. This recovery
requires durable controller/resource evidence and an exited worker. It changes
only trainer terminal metadata, repairing an already-due validation if needed.
"""
import argparse
import json
import shutil
import time
from pathlib import Path

import numpy as np
import torch

from modules.temporal_small_tuning.checkpoint import load, optimizer_for, retain, save
from modules.temporal_small_tuning.protocol import plan, task
from modules.temporal_small_tuning.stage import inputs, register_validation, validation
from modules.temporal_episode_weighting_v2.gradient import episode_diagnostic
from modules.temporal_episode_weighting_v2.stage import tree_identity
from modules.temporal_prequential_transfer.model import initialize
from modules.temporal_two_expert.checkpoint import _atomic_json, _rng_state, model_identity, run_guard
from modules.temporal_two_expert.exact import sha
from modules.temporal_two_expert.inputs import Standardizer


def finalize(state, output, task_id):
    folder = output / task_id
    if (folder / "TERMINAL.json").exists():
        raise ValueError("Never alter an already completed terminal fit")
    controller = json.loads((output / "CONTROLLER_RECEIPT.json").read_text())
    proof = [r for r in controller["tasks"] if r.get("task") == task_id and r["status"] == "CONTROLLER_RESOURCE_STOP"]
    if len(proof) != 1 or controller["status"] != "SIX_FIXED_TASKS_CONTROLLER_FINISHED":
        raise ValueError("Exited controller and specific cumulative resource-stop evidence required")
    resources = [json.loads(q.read_text()) for q in sorted(folder.glob("RESOURCE_SLICE_*.json"))]
    resource_clock = sum(r["elapsed_seconds"] for r in resources)
    extension = output / "RUNTIME_EXTENSION_5400.json"
    cap_seconds = 3600
    if extension.exists():
        runtime = json.loads(extension.read_text())
        if runtime["limits"]["cumulative_seconds"] != 5400 or runtime["permission"]["receipt"]["new_cumulative_wall_seconds"] != 5400:
            raise ValueError("Exact authorized operational5400 limit required")
        cap_seconds = 5400
    if resource_clock < cap_seconds or resource_clock != proof[0]["elapsed_seconds"]:
        raise ValueError("Confirmed cumulative worker resource cap required")
    settings = task(task_id)
    with np.load(folder / "SCALER.npz", allow_pickle=False) as z:
        meta = json.loads((folder / "SCALER.json").read_text())
        scaler = Standardizer(z["mean"], z["scale"], z["count"], meta["provenance"])
    model, _ = initialize(scaler)
    optimizer = optimizer_for(model, settings)
    binding = json.loads((folder / "RUN.json").read_text())
    began = time.monotonic()
    with run_guard(folder, binding):
        saved, old_pointer = load(folder, model, optimizer, binding)
        step, history = saved["step"], saved["trainer_state"]
        if history["status"] != "RUNNING":
            raise ValueError("Only resource-stopped RUNNING state may be finalized")
        before = dict(model=model_identity(model), optimizer=tree_identity(optimizer.state_dict()), RNG=tree_identity(_rng_state()), training=model.training)
        due = step in plan()["selection"]["checkpoints"] and step not in [v["step"] for v in history["validation"]]
        if due:
            train, forward, prototype, _, _, _ = inputs(state, settings["fold"])
            # Input import/setup can touch RNG; restore the exact completed state.
            saved, restored_pointer = load(folder, model, optimizer, binding)
            if restored_pointer != old_pointer:
                raise ValueError("Concurrent fit mutation detected")
            history = saved["trainer_state"]
            v = validation(model, forward, prototype, folder, step, history["controls"])
            register_validation(history, v)
            history["training_diagnostics"].append(episode_diagnostic(model, train, prototype, mixing=settings["wallet_equal_mix"], feature_batch_size=32, snapshot_step=step))
        after = dict(model=model_identity(model), optimizer=tree_identity(optimizer.state_dict()), RNG=tree_identity(_rng_state()), training=model.training)
        if before != after:
            raise ValueError("Zero-update recovery altered model/Adam/RNG/training mode")
        archive = folder / "CAP_ORIGINAL.pt"
        if archive.exists():
            raise ValueError("Never overwrite an existing original cap snapshot")
        shutil.copy2(folder / old_pointer["file"], archive)
        if sha(archive) != old_pointer["SHA256"]:
            raise ValueError("Original capped checkpoint archive differs")
        if history["status"] == "RUNNING":
            history["status"] = "CUMULATIVE_RESOURCE_CAP"
        history["controller_resource_cap"] = dict(guard_elapsed_seconds=resource_clock, cap_seconds=cap_seconds, source=proof[0], additional_optimizer_updates=0)
        p = save(folder, model, optimizer, binding, step=step, elapsed=saved["elapsed_seconds"], history=history)
        if history["best"] is not None and history["best"]["step"] == step:
            _atomic_json(folder / "BEST.json", p)
        if step == 512 and not (folder / "MATCHED512.json").exists():
            _atomic_json(folder / "MATCHED512.json", p)
        result = dict(task_id=task_id, status=history["status"], completed_updates=step, actual_active_training_dates=settings["eligible_dates"], settings=settings, parameters=13699, latest=p, best=history["best"], validation=history["validation"], training_diagnostics=history["training_diagnostics"], slices=history["slices"], elapsed_seconds=p["elapsed_seconds"], failure=history.get("failure"), optimizer_all_parameter_ages=step, reserve_read=False, native_wallets=0)
        _atomic_json(folder / "CAP_FINALIZATION.json", dict(status="ZERO_UPDATE_CAP_FINALIZATION", task_id=task_id, previous_latest=old_pointer, original_body_archive=archive.name, latest=p, preserved_state_identity=before, additional_optimizer_updates=0, completed_due_validation=due, guard_elapsed_seconds=resource_clock, cap_seconds=cap_seconds, recovery_elapsed_seconds=time.monotonic()-began, script_SHA256=sha(Path(__file__)), reserve_read=False))
        _atomic_json(folder / "TERMINAL.json", result)
        retain(folder)
        return dict(task=task_id, status=result["status"], completed_updates=step, additional_optimizer_updates=0)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--state", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    ap.add_argument("--task", required=True)
    args = ap.parse_args()
    torch.set_num_threads(1)
    torch.use_deterministic_algorithms(True)
    print(json.dumps(finalize(args.state,args.output,args.task),allow_nan=False))
