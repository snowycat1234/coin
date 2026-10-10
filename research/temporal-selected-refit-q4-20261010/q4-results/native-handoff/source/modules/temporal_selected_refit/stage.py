"""One fresh full-data fit. No evaluation inputs are loaded here."""

import json
import time
from pathlib import Path

import numpy as np
import torch

from modules.temporal_episode_weighting_v2.gradient import (
    episode_diagnostic,
    memory_bounded_gradients,
)
from modules.temporal_episode_weighting_v2.stage import tree_identity
from modules.temporal_fresh_initialization.stage import load_inputs
from modules.temporal_prequential_transfer.model import initialize, parameter_identity
from modules.temporal_two_expert.checkpoint import (
    _atomic_json,
    _rng_state,
    model_identity,
    run_guard,
)
from modules.temporal_two_expert.inputs import DAY_US

from .checkpoint import binding_for, load, optimizer_for, retain, save
from .protocol import protocol, sources, task

ARM = "FULL773_LOW_LR3E4_DATE_256"


def emit(record):
    print(json.dumps(record, allow_nan=False), flush=True)


def inputs(state):
    train, _, prototype, data, scaler = load_inputs(state, development=False)
    dates = []
    for episode in train:
        if not np.all(np.diff(episode.windows.decision_us) == DAY_US):
            raise ValueError("Original chronological wallets required")
        if np.any(episode.label_available_us >= episode.split_cutoff_us):
            raise ValueError("Strict pre-May maturity required")
        dates.extend(episode.windows.decision_us[:-1].tolist())
    if len(dates) != 773 or len(set(dates)) != 773:
        raise ValueError("Exactly773 distinct active dates required")
    return train, prototype, data, scaler


def prepare(state, output):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    if (output / "READY.json").exists():
        raise FileExistsError("Exclusive one-refit preparation required")
    train, prototype, data, scaler = inputs(state)
    model, _ = initialize(scaler)
    optimizer = optimizer_for(model, task(ARM))
    binding = binding_for(model, data, task(ARM))
    raw, rng = parameter_identity(model), tree_identity(_rng_state())
    with run_guard(output / ARM, binding) as folder:
        if (folder / "latest.json").exists():
            raise FileExistsError("Never overwrite prepared refit")
        diagnostic = episode_diagnostic(
            model, train, prototype, mixing=0.0, feature_batch_size=32, snapshot_step=0
        )
        if (
            optimizer.state
            or raw != parameter_identity(model)
            or rng != tree_identity(_rng_state())
        ):
            raise ValueError("Diagnostic changed fresh model/emptyAdam/allRNG")
        history = dict(status="RUNNING", completed_updates=0, training_diagnostics=[diagnostic])
        p = save(folder, model, optimizer, binding, step=0, elapsed=0.0, history=history)
        _atomic_json(folder / "INITIAL.json", p)
        np.savez_compressed(
            folder / "SCALER.npz", mean=scaler.mean, scale=scaler.scale, count=scaler.count
        )
        _atomic_json(
            folder / "SCALER.json", dict(identity=scaler.identity, provenance=scaler.provenance)
        )
    result = dict(
        status="ONE_REFIT_FROZEN_BEFORE_OPTIMIZATION",
        protocol=protocol(),
        sources=sources(),
        binding=binding,
        initial_parameter_identity=raw,
        initial_all_RNG_identity=rng,
        initial_model_identity=model_identity(model),
        empty_Adam=True,
        optimizer_updates=0,
        reserve_reads=0,
        active_training_dates=773,
        training_decisions=778,
        scaler_rows=907,
        initial_diagnostic=diagnostic,
    )
    _atomic_json(output / "READY.json", result)
    emit(dict(status=result["status"], run_id=binding["run_id"]))
    return result


def frozen_state(state, output):
    train, prototype, data, scaler = inputs(state)
    model, _ = initialize(scaler)
    optimizer = optimizer_for(model, task(ARM))
    binding = binding_for(model, data, task(ARM))
    folder = Path(output) / ARM
    saved, pointer = load(folder, model, optimizer, binding)
    terminal = json.loads((folder / "TERMINAL.json").read_text())
    if (
        saved["step"] != 256
        or terminal["status"] != "FIXED256_COMPLETE"
        or terminal["checkpoint_SHA256"] != pointer["SHA256"]
        or terminal["model_identity"] != model_identity(model)
    ):
        raise ValueError("Exact frozen256 terminal required before evaluation")
    return model, optimizer, scaler, saved, terminal


def train_slice(state, output):
    train, prototype, data, scaler = inputs(state)
    model, _ = initialize(scaler)
    optimizer = optimizer_for(model, task(ARM))
    binding = binding_for(model, data, task(ARM))
    ready = json.loads((Path(output) / "READY.json").read_text())
    if ready["binding"] != binding or ready["sources"] != sources():
        raise ValueError("Published initialization/data/source bytes changed")
    with run_guard(Path(output) / ARM, binding) as folder:
        saved, _ = load(folder, model, optimizer, binding)
        if (folder / "TERMINAL.json").exists():
            return json.loads((folder / "TERMINAL.json").read_text())
        step, prior, history = saved["step"], saved["elapsed_seconds"], saved["trainer_state"]
        began = time.monotonic()
        attempted, phase = step, "restore"
        try:
            while step < 256 and time.monotonic() - began < 1100.0:
                attempted, phase = step + 1, "whole_wallet_stochastic_gradient"
                model.train()
                optimizer.zero_grad(set_to_none=True)
                loss, _ = memory_bounded_gradients(
                    model, train, prototype, feature_batch_size=32, mixing=0.0
                )
                if not np.isfinite(loss):
                    raise ValueError("Nonfinite complete chronological objective")
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
                            stage="selected_full773_refit",
                            step=step,
                            target=256,
                            loss=loss,
                            elapsed_seconds=prior + time.monotonic() - began,
                        )
                    )
            if step == 256:
                phase = "TRAIN_only_terminal_diagnostic"
                history["training_diagnostics"].append(
                    episode_diagnostic(
                        model,
                        train,
                        prototype,
                        mixing=0.0,
                        feature_batch_size=32,
                        snapshot_step=256,
                    )
                )
                history["status"] = "FIXED256_COMPLETE"
        except Exception as error:
            failure = dict(
                type=type(error).__name__,
                message=str(error),
                phase=phase,
                attempted_update=attempted,
            )
            saved, _ = load(folder, model, optimizer, binding)
            step, history = saved["step"], saved["trainer_state"]
            history.update(status="STOP_NUMERICAL_OR_PATH_FAILURE", failure=failure)
            _atomic_json(folder / "FAILURE.json", failure)
        optimizer.zero_grad(set_to_none=True)
        elapsed = prior + time.monotonic() - began
        p = save(folder, model, optimizer, binding, step=step, elapsed=elapsed, history=history)
        retain(folder)
        terminal = dict(
            status=history["status"],
            completed_updates=step,
            fixed_target=256,
            initial_step=0,
            parameters=model.parameter_count,
            model_identity=model_identity(model),
            checkpoint_SHA256=p["SHA256"],
            elapsed_seconds=elapsed,
            training_diagnostics=history["training_diagnostics"],
            failure=history.get("failure"),
            reserve_reads=0,
            optimizer_parameter_ages={
                n: int(optimizer.state[v]["step"]) for n, v in model.named_parameters()
            },
        )
        name = "TERMINAL.json" if history["status"] != "RUNNING" else "SLICE_RECEIPT.json"
        _atomic_json(folder / name, terminal)
        emit(terminal)
        return terminal
