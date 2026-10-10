"""Fixed512 updates with whole-prefix gradients and exact atomic resume."""

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
from modules.temporal_expert_input.checkpoint import (
    load_checkpoint,
    save_checkpoint,
    validate_moments,
)
from modules.temporal_prequential_transfer.model import initialize, parameter_identity
from modules.temporal_two_expert.checkpoint import (
    _atomic_json,
    _rng_state,
    model_identity,
    run_binding,
    run_guard,
)
from modules.temporal_two_expert.inputs import array_digest

from .data import load_fold as load_data
from .protocol import FOLDS, PROTOCOL, sources

SUCCESS = "FRESH_FIXED512_COMPLETED"


def validate_terminal(terminal, saved):
    if (
        terminal["status"] != SUCCESS
        or terminal["completed_updates"] != 512
        or terminal["fixed_target"] != 512
        or saved["step"] != 512
        or terminal["model_identity"] != saved["model_identity"]
        or terminal["checkpoint_SHA256"] != saved["checkpoint_SHA256"]
    ):
        raise ValueError("Exact512 terminal record and actual checkpoint identity required")


def emit(record):
    try:
        print(json.dumps(record), flush=True)
    except BrokenPipeError:
        pass


def binding_for(model, data):
    return run_binding(
        model,
        data_split_identity=data,
        feature_batch_size=32,
        max_steps=512,
        max_seconds=1200.0,
        algorithm=dict(
            parent=dict(step=0, fresh=True),
            parameter_birth_steps={n: 0 for n, _ in model.named_parameters()},
            protocol=PROTOCOL,
            versioned_sources=sources(),
        ),
    )


def load_fold(state, fold):
    if fold not in FOLDS:
        raise ValueError("Exactly the authorized April1 fold required")
    return load_data(state)


def prepare(state, output):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    records = {}
    for fold in FOLDS:
        train, _, prototype, scaler, data, receipt = load_fold(state, fold)
        model, optimizer = initialize(scaler)
        binding = binding_for(model, data)
        identity = parameter_identity(model)
        initial_rng = array_digest(torch.get_rng_state().numpy())
        initial_all_rng = tree_identity(_rng_state())
        with run_guard(output / fold, binding) as folder:
            if (folder / "latest.json").exists():
                saved = load_checkpoint(folder, model, optimizer, binding, sources=sources)
                if saved["step"] != 0:
                    raise ValueError("Pre-fit protocol cannot be regenerated after fitting")
                history = saved["trainer_state"]
            else:
                diagnostic = episode_diagnostic(
                    model,
                    train,
                    prototype,
                    snapshot_step=0,
                    feature_batch_size=32,
                    check_aggregate=True,
                )
                if (
                    optimizer.state
                    or identity != parameter_identity(model)
                    or initial_all_rng != tree_identity(_rng_state())
                ):
                    raise ValueError("Preflight must preserve fresh model/emptyAdam/allRNG")
                history = dict(
                    status="RUNNING",
                    completed_updates=0,
                    history=[diagnostic],
                    last_stochastic_loss=None,
                    last_stochastic_gradient_norm=None,
                )
                save_checkpoint(
                    folder,
                    model,
                    optimizer,
                    binding,
                    step=0,
                    trainer_state=history,
                    sources=sources,
                )
            np.savez_compressed(
                folder / "SCALER.npz", mean=scaler.mean, scale=scaler.scale, count=scaler.count
            )
            _atomic_json(
                folder / "SCALER.json", dict(identity=scaler.identity, provenance=scaler.provenance)
            )
        records[fold] = dict(
            fold=receipt,
            binding=binding,
            initial_train_diagnostic=history["history"][0],
            raw_parameter_identity=identity,
            initial_Torch_RNG_identity=initial_rng,
            initial_all_RNG_identity=initial_all_rng,
            empty_Adam=True,
            parameter_count=model.parameter_count,
            model_identity=model_identity(model),
            optimizer_updates=0,
        )
        emit(
            dict(
                stage="fresh_fold_ready",
                fold=fold,
                training_decisions=receipt["training_decisions"],
                scaler_rows=scaler.provenance["real_row_count"],
                train_loss=history["history"][0]["date_mean_loss"],
            )
        )
    if (
        len({v["raw_parameter_identity"] for v in records.values()}) != 1
        or len({v["initial_Torch_RNG_identity"] for v in records.values()}) != 1
    ):
        raise ValueError("Every fold must have identical fresh parameters and initial dropout RNG")
    result = dict(
        status="FROZEN_BEFORE_FITTING",
        protocol=PROTOCOL,
        sources=sources(),
        folds=records,
        optimizer_updates=0,
        native_wallets=0,
        provider_downloads=0,
        original_scaler_or_models_opened=False,
    )
    _atomic_json(output / "READY.json", result)
    return result


def train_fold(state, output, fold):
    train, _, prototype, scaler, data, _ = load_fold(state, fold)
    model, optimizer = initialize(scaler)
    binding = binding_for(model, data)
    ready = json.loads((Path(output) / "READY.json").read_text())
    if ready["sources"] != sources() or ready["folds"][fold]["binding"] != binding:
        raise ValueError("Published frozen fold protocol/input/source identity changed")
    with run_guard(Path(output) / fold, binding) as folder:
        if (folder / "TERMINAL.json").exists():
            saved = load_checkpoint(folder, model, optimizer, binding, sources=sources)
            terminal = json.loads((folder / "TERMINAL.json").read_text())
            if terminal["status"] == SUCCESS:
                validate_terminal(terminal, saved)
            return terminal
        saved = load_checkpoint(folder, model, optimizer, binding, sources=sources)
        step, prior, history = saved["step"], saved["elapsed_seconds"], saved["trainer_state"]
        began, phase, attempted = time.monotonic(), "resume", step
        try:

            def diagnostic_if_due():
                if (
                    step in PROTOCOL["diagnostics"]
                    and history["history"][-1]["snapshot_step"] != step
                ):
                    history["history"].append(
                        episode_diagnostic(
                            model, train, prototype, feature_batch_size=32, snapshot_step=step
                        )
                    )
                    save_checkpoint(
                        folder,
                        model,
                        optimizer,
                        binding,
                        step=step,
                        elapsed_seconds=prior + time.monotonic() - began,
                        trainer_state=history,
                        sources=sources,
                    )

            diagnostic_if_due()
            while step < 512 and time.monotonic() - began < 1200.0:
                attempted, phase = step + 1, "whole_prefix_stochastic_gradient"
                model.train()
                optimizer.zero_grad(set_to_none=True)
                loss, _ = memory_bounded_gradients(model, train, prototype, feature_batch_size=32)
                if not np.isfinite(loss):
                    raise ValueError("Nonfinite whole-prefix objective")
                norm = torch.nn.utils.clip_grad_norm_(
                    model.parameters(), 1.0, error_if_nonfinite=True
                )
                phase = "Adam_update"
                optimizer.step()
                optimizer.zero_grad(set_to_none=True)
                step += 1
                history.update(
                    completed_updates=step,
                    last_stochastic_loss=loss,
                    last_stochastic_gradient_norm=float(norm),
                )
                phase = "atomic_completed_update"
                save_checkpoint(
                    folder,
                    model,
                    optimizer,
                    binding,
                    step=step,
                    elapsed_seconds=prior + time.monotonic() - began,
                    trainer_state=history,
                    sources=sources,
                )
                phase = "train_only_snapshot_diagnostic"
                diagnostic_if_due()
                emit(
                    dict(
                        stage="fresh_fold_training",
                        fold=fold,
                        step=step,
                        loss=loss,
                        gradient_norm=float(norm),
                        elapsed_seconds=prior + time.monotonic() - began,
                    )
                )
            if step == 512:
                history["status"] = SUCCESS
                validate_moments(model, optimizer, 512, {n: 0 for n, _ in model.named_parameters()})
        except Exception as error:
            failure = dict(
                type=type(error).__name__,
                message=str(error),
                phase=phase,
                attempted_update=attempted,
            )
            saved = load_checkpoint(folder, model, optimizer, binding, sources=sources)
            step, history = saved["step"], saved["trainer_state"]
            history.update(status="STOP_NUMERICAL_OR_PATH_FAILURE", failure=failure)
            _atomic_json(folder / "FAILURE.json", failure)
        elapsed = prior + time.monotonic() - began
        optimizer.zero_grad(set_to_none=True)
        pointer = save_checkpoint(
            folder,
            model,
            optimizer,
            binding,
            step=step,
            elapsed_seconds=elapsed,
            trainer_state=history,
            sources=sources,
        )
        result = dict(
            status=history["status"],
            fold=fold,
            completed_updates=step,
            model_identity=model_identity(model),
            checkpoint_SHA256=pointer["SHA256"],
            elapsed_seconds=elapsed,
            diagnostics=history["history"],
            failure=history.get("failure"),
            fresh_initialization=True,
            initial_step=0,
            fixed_target=512,
            parameter_count=13699,
            forward_economic_scoring_used_for_training=False,
        )
        if history["status"] == "RUNNING":
            result["status"] = "SLICE_EXHAUSTED_RESUME_REQUIRED"
            _atomic_json(folder / "SLICE_RECEIPT.json", result)
        else:
            _atomic_json(folder / "TERMINAL.json", result)
        emit(dict(stage="fresh_fold_slice_complete", **result))
        return result
