"""One bounded complete-six-wallet fit. No historical evaluation inputs opened."""

import json
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import torch

from modules.temporal_episode_weighting_v2.stage import tree_identity
from modules.temporal_history_expansion.gradient import memory_bounded_gradients
from modules.temporal_prequential_transfer.model import initialize, parameter_identity
from modules.temporal_two_expert.checkpoint import (
    _atomic_json,
    _rng_state,
    model_identity,
    run_guard,
)
from modules.temporal_two_expert.exact import sha

from .checkpoint import binding_for, load, optimizer_for, retain, save
from .data import inputs
from .protocol import ARM, protocol, sources, task


def emit(record):
    print(json.dumps(record, allow_nan=False), flush=True)


def optimizer_ages(model, optimizer):
    return {
        n: int(optimizer.state[p]["step"]) if p in optimizer.state else 0
        for n, p in model.named_parameters()
    }


def finish(folder, model, optimizer, scaler, step, history, pointer, elapsed):
    terminal = dict(
        status=history["status"],
        completed_updates=step,
        fixed_target=256,
        parameters=model.parameter_count,
        model_identity=model_identity(model),
        checkpoint_SHA256=pointer["SHA256"],
        elapsed_seconds=elapsed,
        started_UTC=history["started_UTC"],
        slices=history["slices"],
        failure=history.get("failure"),
        last_stochastic_loss=history["last_stochastic_loss"],
        last_gradient_norm=history["last_gradient_norm"],
        scaler_identity=scaler.identity,
        scaler_rows=907,
        normalization_refitted=False,
        Q4_scores=0,
        optimizer_parameter_ages=optimizer_ages(model, optimizer),
    )
    _atomic_json(
        folder / ("TERMINAL.json" if history["status"] != "RUNNING" else "SLICE_RECEIPT.json"),
        terminal,
    )
    emit(terminal)
    return terminal


def prepare(state, economics, output):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    if (output / "READY.json").exists():
        raise FileExistsError("Exclusive one-fit initialization required")
    train, prototype, data, scaler = inputs(state, economics)
    model, _ = initialize(scaler)
    optimizer = optimizer_for(model, task())
    binding = binding_for(model, data, task())
    with run_guard(output / ARM, binding) as folder:
        if (folder / "latest.json").exists():
            raise FileExistsError("Never overwrite prepared expanded fit")
        history = dict(
            status="RUNNING",
            completed_updates=0,
            slices=0,
            started_UTC=None,
            last_stochastic_loss=None,
            last_gradient_norm=None,
        )
        p = save(folder, model, optimizer, binding, step=0, elapsed=0.0, history=history)
        _atomic_json(folder / "INITIAL.json", p)
        # Verify the real source/data receipt is restricted-loader safe before public freeze.
        load(folder, model, optimizer, binding)
        np.savez_compressed(
            folder / "SCALER.npz", mean=scaler.mean, scale=scaler.scale, count=scaler.count
        )
        _atomic_json(
            folder / "SCALER.json", dict(identity=scaler.identity, provenance=scaler.provenance)
        )
    result = dict(
        status="PREFIT_SOURCE_DATA_MODEL_FROZEN_NOT_STARTED",
        protocol=protocol(),
        sources=sources(),
        binding=binding,
        data=data,
        initial_parameter_identity=parameter_identity(model),
        initial_all_RNG_identity=tree_identity(_rng_state()),
        initial_model_identity=model_identity(model),
        initial_checkpoint_SHA256=p["SHA256"],
        empty_Adam=True,
        optimizer_updates=0,
        historical_scores=0,
        provider_downloads=0,
        normalization_refitted=False,
        completed_date_counts=data["counts"],
    )
    _atomic_json(output / "READY.json", result)
    emit(
        dict(
            status=result["status"],
            run_id=binding["run_id"],
            counts=data["counts"],
            initial_model_identity=result["initial_model_identity"],
        )
    )
    return result


def frozen_state(state, economics, output):
    _, _, data, scaler = inputs(state, economics)
    model, _ = initialize(scaler)
    optimizer = optimizer_for(model, task())
    binding = binding_for(model, data, task())
    folder = Path(output) / ARM
    saved, p = load(folder, model, optimizer, binding)
    terminal = json.loads((folder / "TERMINAL.json").read_text())
    if (
        saved["step"] != 256
        or terminal["status"] != "FIXED256_COMPLETE"
        or terminal["checkpoint_SHA256"] != p["SHA256"]
        or terminal["model_identity"] != model_identity(model)
    ):
        raise ValueError("Exact public frozen256 terminal required before scoring")
    return model, optimizer, scaler, saved, terminal


def worker(state, economics, output, publication):
    output = Path(output)
    train, prototype, data, scaler = inputs(state, economics)
    model, _ = initialize(scaler)
    optimizer = optimizer_for(model, task())
    binding = binding_for(model, data, task())
    ready = json.loads((output / "READY.json").read_text())
    published = json.loads(Path(publication).read_text())
    if (
        ready["binding"] != binding
        or ready["sources"] != sources()
        or published["status"] != "PASS_ALL_PUBLIC_BYTES"
        or published["prefit_ready_SHA256"] != sha(output / "READY.json")
    ):
        raise ValueError("Public verified prefit protocol/model/data required before fitting")
    with run_guard(output / ARM, binding) as folder:
        saved, loaded_pointer = load(folder, model, optimizer, binding)
        if (folder / "TERMINAL.json").exists():
            return json.loads((folder / "TERMINAL.json").read_text())
        step, prior, history = saved["step"], saved["elapsed_seconds"], saved["trainer_state"]
        if step == 256 and history["status"] == "RUNNING":
            history["status"] = "FIXED256_COMPLETE"
            pointer = save(
                folder, model, optimizer, binding, step=step, elapsed=prior, history=history
            )
            retain(folder)
            return finish(folder, model, optimizer, scaler, step, history, pointer, prior)
        if history["status"] != "RUNNING":
            return finish(folder, model, optimizer, scaler, step, history, loaded_pointer, prior)
        if history["slices"] >= 3:
            history["status"] = "STOP_AUTHORIZED_RESOURCE_BUDGET"
            pointer = save(
                folder, model, optimizer, binding, step=step, elapsed=prior, history=history
            )
            retain(folder)
            return finish(folder, model, optimizer, scaler, step, history, pointer, prior)
        history["slices"] += 1
        if history["started_UTC"] is None:
            history["started_UTC"] = datetime.now(timezone.utc).isoformat()
        # Persist attempt consumption before any stochastic gradient or hard interruption.
        save(folder, model, optimizer, binding, step=step, elapsed=prior, history=history)
        retain(folder)
        _atomic_json(
            folder / "STARTED.json",
            dict(
                started_UTC=history["started_UTC"],
                current_slice=history["slices"],
                restored_completed_updates=step,
                target_updates=256,
                active_intervals=1137,
                decisions=1143,
                scaler_rows=907,
                model_parameters=13699,
                public_prefit_commit=published["remote_SHA"],
            ),
        )
        began = time.monotonic()
        attempt_started, attempt_slices = history["started_UTC"], history["slices"]
        attempted, phase = step, "restored_completed_update"
        try:
            while step < 256 and time.monotonic() - began < 1100.0:
                attempted, phase = step + 1, "six_complete_wallet_stochastic_gradient"
                model.train()
                optimizer.zero_grad(set_to_none=True)
                loss, _ = memory_bounded_gradients(model, train, prototype, feature_batch_size=32)
                if not np.isfinite(loss):
                    raise ValueError("Nonfinite complete own-wallet objective")
                norm = torch.nn.utils.clip_grad_norm_(
                    model.parameters(), 1.0, error_if_nonfinite=True
                )
                phase = "Adam_step"
                optimizer.step()
                optimizer.zero_grad(set_to_none=True)
                step += 1
                history.update(
                    completed_updates=step,
                    last_stochastic_loss=loss,
                    last_gradient_norm=float(norm),
                )
                phase = "atomic_completed_update"
                save(
                    folder,
                    model,
                    optimizer,
                    binding,
                    step=step,
                    elapsed=prior + time.monotonic() - began,
                    history=history,
                )
                retain(folder)
                if step % 16 == 0:
                    emit(
                        dict(
                            stage="expanded1137_fixed907_fit",
                            step=step,
                            target=256,
                            loss=loss,
                            elapsed_seconds=prior + time.monotonic() - began,
                        )
                    )
            if step == 256:
                history["status"] = "FIXED256_COMPLETE"
        except Exception as error:
            failure = dict(
                type=type(error).__name__,
                message=str(error),
                phase=phase,
                attempted_update=attempted,
            )
            restored, _ = load(folder, model, optimizer, binding)
            step, history = restored["step"], restored["trainer_state"]
            history.update(
                status="STOP_NUMERICAL_OR_PATH_FAILURE",
                failure=failure,
                started_UTC=attempt_started,
                slices=attempt_slices,
            )
            _atomic_json(folder / "FAILURE.json", failure)
        if step < 256 and history["status"] == "RUNNING" and history["slices"] >= 3:
            history["status"] = "STOP_AUTHORIZED_RESOURCE_BUDGET"
        optimizer.zero_grad(set_to_none=True)
        elapsed = prior + time.monotonic() - began
        pointer = save(
            folder, model, optimizer, binding, step=step, elapsed=elapsed, history=history
        )
        retain(folder)
        return finish(folder, model, optimizer, scaler, step, history, pointer, elapsed)
