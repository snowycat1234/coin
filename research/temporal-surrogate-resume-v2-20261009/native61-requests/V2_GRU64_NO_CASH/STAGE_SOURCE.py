"""Source-bound warm starts; original Adam/RNG and immutable atomic snapshots."""

import copy
import json
import time
from pathlib import Path

import numpy as np
import torch

from modules.temporal_risk_proxy_v2.proxy import CONTRACT
from modules.temporal_two_expert.checkpoint import (
    _atomic_json,
    load_checkpoint,
    make_optimizer,
    model_identity,
    run_binding,
    run_guard,
    save_checkpoint,
)
from modules.temporal_two_expert.comparison import PROTOCOL, _evaluate_training, convergence_met
from modules.temporal_two_expert.exact import sha
from modules.temporal_two_expert.inputs import Standardizer, digest
from modules.temporal_two_expert.model import Selector
from modules.temporal_two_expert.training_packet import load_packet

from .gradient import memory_bounded_gradients_v2

PROTOCOL_V2 = copy.deepcopy(PROTOCOL)
PROTOCOL_V2.update(
    schema="TEMPORAL_WARM_RESTART_CHARGED_SURROGATE_V2",
    objective_version=2,
    objective=CONTRACT,
    initialization="exact_original_terminal_model_Adam_all_moments_and_saved_RNG;no_reseed",
    gradient="exact_continuous_daily_surrogate_request_VJP_RNG_identical_feature_replay",
    continuation="four_originals_immutable;separate_versioned_stage_not_clean_original_comparison",
    convergence_history="fresh_v2_baseline;unchanged_train_only_rule;stage_update_count",
    capacity="DECLARED_FULL_FILL_DIAGNOSTIC_ONLY;not_historical_liquidity",
    stage_budget="same1024_additional_updates_1200seconds_per_arm;Adam_step_remains_cumulative",
    development="freeze_all4_v2_terminal_heads_then_seen_MayJune;no_checkpoint_selection",
    native_gradient_bridge_required=False,
)
PROTOCOL_V2["limits"].update(serial_fits=False, maximum_concurrent_arms=2)


def stage_sources():
    root = Path(__file__).resolve().parents[2]
    paths = sorted(Path(__file__).parent.glob("*.py"))
    paths += sorted((root / "modules/temporal_risk_proxy_v2").glob("*.py"))
    return {str(p.relative_to(root)): sha(p) for p in paths}


def load_inputs(state):
    state = Path(state).resolve()
    parent = state / "four-fit"
    train, dev, prototype, identity = load_packet(
        state / "FROZEN_PACKET.json",
        sha(state / "FROZEN_PACKET.json"),
        state / "recovery/source/modules/direct_path/prototype.py",
    )
    dataset = json.loads((parent / "RUN.json").read_text())["specification"]["dataset"]
    if dataset != dict(
        packet=identity, train=[e.identity for e in train], development=[e.identity for e in dev]
    ):
        raise ValueError("Exact original features, split and economic inputs required")
    proof = json.loads((parent / "SCALER.json").read_text())
    if sha(parent / "SCALER.npz") != proof["SHA256"]:
        raise ValueError("Original shared scaler bytes required; never refit")
    with np.load(parent / "SCALER.npz", allow_pickle=False) as z:
        scaler = Standardizer(z["mean"], z["scale"], z["count"], proof["provenance"])
    if scaler.identity != proof["identity"]:
        raise ValueError("Original scaler identity required")
    return train, dev, prototype, dataset, scaler


def original_model(scaler, family, cash):
    return Selector(
        scaler,
        family=family,
        cash_enabled=cash,
        seed=PROTOCOL["seed"],
        dropout=PROTOCOL["dropout"],
        zero_readout=True,
    )


def warm_parent(folder, model):
    binding = json.loads((folder / "RUN.json").read_text())
    optimizer = make_optimizer(model)
    loaded = load_checkpoint(folder, model, optimizer, binding)
    pointer = json.loads((folder / "latest.json").read_text())
    parent = dict(
        run_id=binding["run_id"],
        pointer=pointer,
        step=loaded["step"],
        elapsed_seconds=loaded["elapsed_seconds"],
        model_identity=loaded["model_identity"],
        original_status=loaded["trainer_state"]["status"],
        original_history=loaded["trainer_state"]["history"],
    )
    return optimizer, parent


def stage_binding(model, parent, dataset, protocol):
    return run_binding(
        model,
        data_split_identity=dataset,
        feature_batch_size=protocol["feature_batch_size"],
        max_steps=parent["step"] + protocol["limits"]["maximum_updates_per_fit"],
        max_seconds=protocol["limits"]["seconds_per_fit"],
        checkpoint_every=1,
        algorithm=dict(
            objective_version=2,
            parent=parent,
            protocol_SHA256=digest(protocol),
            protocol=protocol,
            versioned_sources=stage_sources(),
        ),
    )


def train_stage(
    model,
    episodes,
    prototype,
    parent_folder,
    directory,
    dataset,
    *,
    protocol=PROTOCOL_V2,
    gradient_function=memory_bounded_gradients_v2,
):
    optimizer, parent = warm_parent(Path(parent_folder), model)
    binding = stage_binding(model, parent, dataset, protocol)
    limits, rule = protocol["limits"], protocol["convergence"]
    baseline_step = parent["step"]
    with run_guard(directory, binding) as output:
        if (output / "TERMINAL.json").exists():
            load_checkpoint(output, model, optimizer, binding)
            return json.loads((output / "TERMINAL.json").read_text())
        if (output / "latest.json").exists():
            loaded = load_checkpoint(output, model, optimizer, binding)
            step, prior, state = loaded["step"], loaded["elapsed_seconds"], loaded["trainer_state"]
        else:
            step, prior = baseline_step, 0.0
            state = dict(
                status="RUNNING",
                history=[],
                initial_norm=None,
                last_requests=None,
                parent=parent,
                objective_version=2,
                completed_stage_updates=0,
                last_stochastic_loss=None,
                last_stochastic_gradient_norm=None,
            )
            optimizer.zero_grad(set_to_none=True)
            save_checkpoint(
                output,
                model,
                optimizer,
                binding,
                step=step,
                elapsed_seconds=0.0,
                trainer_state=state,
            )
        began = time.monotonic()
        phase = "initial_v2_deterministic_train_evaluation"
        attempted_stage = step - baseline_step
        try:
            if state["initial_norm"] is None:
                loss, norm, requests = _evaluate_training(
                    model,
                    optimizer,
                    episodes,
                    prototype,
                    protocol["feature_batch_size"],
                    gradient_function,
                )
                state.update(
                    initial_norm=norm,
                    last_requests=torch.tensor(requests),
                    history=[
                        dict(
                            step=0,
                            cumulative_step=step,
                            loss=loss,
                            gradient_norm=norm,
                            request_change=0.0,
                        )
                    ],
                )
                save_checkpoint(
                    output,
                    model,
                    optimizer,
                    binding,
                    step=step,
                    elapsed_seconds=prior + time.monotonic() - began,
                    trainer_state=state,
                )
            while state["status"] == "RUNNING":
                updates = step - baseline_step
                elapsed = prior + time.monotonic() - began
                if (
                    updates >= limits["maximum_updates_per_fit"]
                    or elapsed >= limits["seconds_per_fit"]
                ):
                    state["status"] = "CAPPED_NOT_CONVERGED"
                    break
                attempted_stage, phase = updates + 1, "stochastic_chronological_gradient"
                model.train()
                optimizer.zero_grad(set_to_none=True)
                loss, _ = gradient_function(
                    model, episodes, prototype, feature_batch_size=protocol["feature_batch_size"]
                )
                if not np.isfinite(loss):
                    raise ValueError("Nonfinite v2 own-path objective")
                norm = torch.nn.utils.clip_grad_norm_(
                    model.parameters(), 1.0, error_if_nonfinite=True
                )
                phase = "Adam_update"
                optimizer.step()
                optimizer.zero_grad(set_to_none=True)
                step += 1
                updates = step - baseline_step
                state.update(
                    completed_stage_updates=updates,
                    last_stochastic_loss=loss,
                    last_stochastic_gradient_norm=float(norm),
                )
                if updates % rule["evaluate_every"] == 0:
                    phase = "deterministic_train_evaluation_after_uncommitted_update"
                    score, eval_norm, requests = _evaluate_training(
                        model,
                        optimizer,
                        episodes,
                        prototype,
                        protocol["feature_batch_size"],
                        gradient_function,
                    )
                    change = float(np.mean(np.abs(requests - state["last_requests"].numpy())))
                    state["history"].append(
                        dict(
                            step=updates,
                            cumulative_step=step,
                            loss=score,
                            gradient_norm=eval_norm,
                            request_change=change,
                        )
                    )
                    state["last_requests"] = torch.tensor(requests)
                    if convergence_met(state["history"], state["initial_norm"], updates, rule):
                        state["status"] = "TRAIN_CONVERGENCE_CRITERION_MET"
                elapsed = prior + time.monotonic() - began
                if state["status"] == "RUNNING" and (
                    updates >= limits["maximum_updates_per_fit"]
                    or elapsed >= limits["seconds_per_fit"]
                ):
                    state["status"] = "CAPPED_NOT_CONVERGED"
                phase = "atomic_checkpoint"
                save_checkpoint(
                    output,
                    model,
                    optimizer,
                    binding,
                    step=step,
                    elapsed_seconds=elapsed,
                    trainer_state=state,
                )
                print(
                    json.dumps(
                        dict(
                            stage="v2_training",
                            family=model.family,
                            cash=model.cash_enabled,
                            completed_stage_updates=updates,
                            cumulative_Adam_step=step,
                            stochastic_loss=loss,
                            preclip_gradient_norm=float(norm),
                            status=state["status"],
                            elapsed_seconds=elapsed,
                        )
                    ),
                    flush=True,
                )
        except Exception as error:
            failure = dict(
                type=type(error).__name__,
                message=str(error),
                phase=phase,
                attempted_stage_update=attempted_stage,
            )
            if hasattr(error, "record"):
                failure.update(error.record)
            consumed = prior + time.monotonic() - began
            loaded = load_checkpoint(output, model, optimizer, binding)
            step, state = loaded["step"], loaded["trainer_state"]
            state.update(status="STOP_V2_NUMERICAL_OR_PATH_FAILURE", failure=failure)
            prior, began = consumed, time.monotonic()
        elapsed = prior + time.monotonic() - began
        optimizer.zero_grad(set_to_none=True)
        save_checkpoint(
            output,
            model,
            optimizer,
            binding,
            step=step,
            elapsed_seconds=elapsed,
            trainer_state=state,
        )
        result = dict(
            status=state["status"],
            objective_version=2,
            parent_step=baseline_step,
            completed_stage_updates=step - baseline_step,
            cumulative_Adam_step=step,
            elapsed_seconds=elapsed,
            run_id=binding["run_id"],
            model_identity=model_identity(model),
            parent_checkpoint_SHA256=parent["pointer"]["SHA256"],
            v2_initial_train=state["history"][0] if state["history"] else None,
            last_deterministic_train=state["history"][-1] if state["history"] else None,
            last_stochastic_loss=state["last_stochastic_loss"],
            last_stochastic_gradient_norm=state["last_stochastic_gradient_norm"],
            failure=state.get("failure"),
            original_runs_unchanged=True,
        )
        _atomic_json(output / "TERMINAL.json", result)
        print(json.dumps(dict(stage="v2_terminal", **result)), flush=True)
        return result
