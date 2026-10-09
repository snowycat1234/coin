"""Fixed512-update matched weighting with atomic per-update resume and sliced time."""

import copy
import json
import time
from pathlib import Path

import numpy as np
import torch

from modules.temporal_expert_input.checkpoint import load_checkpoint, save_checkpoint
from modules.temporal_expert_input.stage import PROTOCOL as INPUT_PROTOCOL
from modules.temporal_expert_input.stage import emit, input_audit, inputs
from modules.temporal_expert_input.stage import sources as input_sources
from modules.temporal_two_expert.checkpoint import (
    _atomic_json,
    _rng_state,
    model_identity,
    run_binding,
    run_guard,
)
from modules.temporal_two_expert.exact import sha
from modules.temporal_two_expert.inputs import array_digest, digest

from .gradient import episode_diagnostic, memory_bounded_gradients
from .snapshot import SHA256 as INITIAL_SHA256
from .snapshot import initialize, preserve

ARMS = ("GRU64_WEIGHT_DATE", "GRU64_WEIGHT_MIXED")
MIXING = {ARMS[0]: 0.0, ARMS[1]: 0.5}
SUCCESS = "FIXED_512_UPDATES_COMPLETED"
PROTOCOL = copy.deepcopy(INPUT_PROTOCOL)
for obsolete in ("convergence", "convergence_history", "control", "active", "capped_status"):
    PROTOCOL.pop(obsolete, None)
PROTOCOL["limits"].pop("seconds_per_fit")
PROTOCOL["limits"].update(maximum_updates_per_fit=512, seconds_per_slice=1200.0)
PROTOCOL.update(
    schema="TEMPORAL_MATCHED_FIXED_UPDATE_EPISODE_WEIGHTING_V2",
    arm_order=list(ARMS),
    expert_input_enabled_both=True,
    initialization="one_byte_pinned_pre_first_evaluation_expert_input_snapshot_step780;full_model_Adam_all_RNG",
    initial_snapshot_SHA256=INITIAL_SHA256,
    sole_comparison="date_coefficients_n/778_vs_0.5*n/778+0.5/5;identical_expanded_pool_and_expert_inputs",
    arm_mixing=MIXING,
    chronology="same778dates_five_complete54,88,62,144,430_wallets;only_wallet_loss_coefficients_change",
    diagnostics=[0, 128, 256, 512],
    diagnostic_role="train_only_deterministic_supplied_snapshot;per_episode_losses_gradients_and_both_common_objectives",
    diagnostic_contribution="dot(a_i*g_i,G)/squared_norm(G);signed_additive_projection_not_norm_fraction",
    stage_budget="exactly512_new_updates_each;1200second_invocations_resume_same_Adam_RNG_until_complete",
    completion="fixed512_updates_only;no_convergence_stop_or_development_checkpoint_selection",
    time_binding="max_seconds_in_run_binding_is_per_invocation_slice_not_cumulative_training_cap",
    comparison="matched_fixed_update_objective_comparison;one_preserved_initial_snapshot;no_seen_selection",
    checkpoint_selection="512th_completed_update_only",
    weighting_experiment_updates=512,
)


def sources():
    root = Path(__file__).resolve().parents[2]
    return {
        **input_sources(),
        **{str(p.relative_to(root)): sha(p) for p in sorted(Path(__file__).parent.glob("*.py"))},
    }


def tree_identity(value):
    def converted(v):
        if isinstance(v, torch.Tensor):
            return {"tensor": array_digest(v.detach().cpu().numpy())}
        if isinstance(v, np.ndarray):
            return {"array": array_digest(v)}
        if isinstance(v, dict):
            return {str(k): converted(x) for k, x in v.items()}
        if isinstance(v, (tuple, list)):
            return [converted(x) for x in v]
        return v

    return digest(converted(value))


def binding_for(model, parent, births, dataset, arm, protocol=PROTOCOL):
    if arm not in ARMS or not model.input_enabled:
        raise ValueError("Same active-input model in both declared arms required")
    return run_binding(
        model,
        data_split_identity=dataset,
        feature_batch_size=protocol["feature_batch_size"],
        max_steps=parent["step"] + protocol["limits"]["maximum_updates_per_fit"],
        max_seconds=protocol["limits"]["seconds_per_slice"],
        checkpoint_every=1,
        algorithm=dict(
            objective_version=2,
            parent=parent,
            parameter_birth_steps=births,
            protocol=protocol,
            protocol_SHA256=digest(protocol),
            arm=arm,
            mixing=MIXING[arm],
            initial_snapshot_SHA256=INITIAL_SHA256,
            versioned_sources=sources(),
        ),
    )


def prepare(state, output, *, protocol=PROTOCOL):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    preserve(state, output / "INITIAL")
    train, _, prototype, dataset, scaler = inputs(state)
    records = {}
    common = None
    for arm in ARMS:
        model, optimizer, parent, births = initialize(state, scaler)
        binding = binding_for(model, parent, births, dataset, arm, protocol)
        identity = dict(
            model=model_identity(model),
            optimizer=tree_identity(optimizer.state_dict()),
            RNG=tree_identity(_rng_state()),
            training=model.training,
            initial_snapshot_SHA256=INITIAL_SHA256,
        )
        if common is not None and identity != common:
            raise ValueError("Both arms must have identical full model/Adam/RNG initialization")
        common = identity
        diagnostic = episode_diagnostic(
            model,
            train,
            prototype,
            mixing=MIXING[arm],
            feature_batch_size=protocol["feature_batch_size"],
            snapshot_step=0,
        )
        if identity != dict(
            model=model_identity(model),
            optimizer=tree_identity(optimizer.state_dict()),
            RNG=tree_identity(_rng_state()),
            training=model.training,
            initial_snapshot_SHA256=INITIAL_SHA256,
        ):
            raise ValueError("Preflight must preserve model/Adam/RNG")
        records[arm] = dict(
            binding=binding,
            diagnostic0=diagnostic,
            initial_identity=identity,
            optimizer_updates=0,
            parameter_count=model.parameter_count,
        )
        emit(
            dict(
                stage="weighting_preflight",
                arm=arm,
                train_loss=diagnostic["trained_objective_summary"]["weighted_mean_loss"],
            )
        )
    _atomic_json(
        output / "READY.json",
        dict(
            status="MATCHED_FIXED512_TWO_ARMS_READY",
            protocol=protocol,
            sources=sources(),
            arms=records,
            identical_initialization=True,
            no_development_economic_scoring=True,
            input_audit=input_audit(train),
        ),
    )


def train_arm(state, output, arm, *, protocol=PROTOCOL):
    train, _, prototype, dataset, scaler = inputs(state)
    model, optimizer, parent, births = initialize(state, scaler)
    binding = binding_for(model, parent, births, dataset, arm, protocol)
    ready = json.loads((Path(output) / "READY.json").read_text())
    if ready["arms"][arm]["binding"] != binding:
        raise ValueError("Published preflight/protocol/source/initial identity changed")
    baseline = parent["step"]
    target = protocol["limits"]["maximum_updates_per_fit"]
    with run_guard(Path(output) / arm, binding) as folder:
        if (folder / "TERMINAL.json").exists():
            load_checkpoint(folder, model, optimizer, binding, sources=sources)
            return json.loads((folder / "TERMINAL.json").read_text())
        if (folder / "latest.json").exists():
            saved = load_checkpoint(folder, model, optimizer, binding, sources=sources)
            step, prior, history = saved["step"], saved["elapsed_seconds"], saved["trainer_state"]
        else:
            step, prior = baseline, 0.0
            history = dict(
                status="RUNNING",
                history=[ready["arms"][arm]["diagnostic0"]],
                completed_stage_updates=0,
                last_stochastic_loss=None,
                last_stochastic_gradient_norm=None,
            )
            save_checkpoint(
                folder, model, optimizer, binding, step=step, trainer_state=history, sources=sources
            )
        if history["completed_stage_updates"] != step - baseline:
            raise ValueError("Completed update count must match the atomic model/Adam checkpoint")
        began, phase, attempted = time.monotonic(), "slice_start", step - baseline
        try:
            completed = step - baseline
            if (
                completed in protocol["diagnostics"]
                and history["history"][-1]["snapshot_step"] != completed
            ):
                phase = "resumed_predetermined_training_snapshot_diagnostic"
                history["history"].append(
                    episode_diagnostic(
                        model,
                        train,
                        prototype,
                        mixing=MIXING[arm],
                        feature_batch_size=protocol["feature_batch_size"],
                        snapshot_step=completed,
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
            while step - baseline < target:
                if time.monotonic() - began >= protocol["limits"]["seconds_per_slice"]:
                    break
                attempted, phase = step - baseline + 1, "complete_chronological_stochastic_gradient"
                model.train()
                optimizer.zero_grad(set_to_none=True)
                loss, _ = memory_bounded_gradients(
                    model,
                    train,
                    prototype,
                    feature_batch_size=protocol["feature_batch_size"],
                    mixing=MIXING[arm],
                )
                if not np.isfinite(loss):
                    raise ValueError("Nonfinite loss")
                norm = torch.nn.utils.clip_grad_norm_(
                    model.parameters(), 1.0, error_if_nonfinite=True
                )
                phase = "Adam_update"
                optimizer.step()
                optimizer.zero_grad(set_to_none=True)
                step += 1
                updates = step - baseline
                history.update(
                    completed_stage_updates=updates,
                    last_stochastic_loss=loss,
                    last_stochastic_gradient_norm=float(norm),
                )
                # Publish the completed Adam update before optional snapshot diagnostics.
                phase = "atomic_checkpoint"
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
                if updates in protocol["diagnostics"]:
                    phase = "predetermined_training_snapshot_diagnostic"
                    history["history"].append(
                        episode_diagnostic(
                            model,
                            train,
                            prototype,
                            mixing=MIXING[arm],
                            feature_batch_size=protocol["feature_batch_size"],
                            snapshot_step=updates,
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
                emit(
                    dict(
                        stage="weighting_training",
                        arm=arm,
                        completed_stage_updates=updates,
                        cumulative_step=step,
                        stochastic_loss=loss,
                        preclip_gradient_norm=float(norm),
                        elapsed_seconds=prior + time.monotonic() - began,
                        status="RUNNING",
                    )
                )
            # A disconnect after publishing a diagnostic-step update may precede its
            # diagnostic. Complete the missing prescribed snapshot before terminal.
            completed = step - baseline
            if (
                completed in protocol["diagnostics"]
                and history["history"][-1]["snapshot_step"] != completed
            ):
                phase = "resumed_predetermined_training_snapshot_diagnostic"
                history["history"].append(
                    episode_diagnostic(
                        model,
                        train,
                        prototype,
                        mixing=MIXING[arm],
                        feature_batch_size=protocol["feature_batch_size"],
                        snapshot_step=completed,
                    )
                )
            if completed == target:
                history["status"] = SUCCESS
        except Exception as error:
            failure = dict(
                type=type(error).__name__,
                message=str(error),
                phase=phase,
                attempted_stage_update=attempted,
            )
            saved = load_checkpoint(folder, model, optimizer, binding, sources=sources)
            step, history = saved["step"], saved["trainer_state"]
            history.update(status="STOP_NUMERICAL_OR_PATH_FAILURE", failure=failure)
            _atomic_json(folder / "FAILURE.json", failure)
        elapsed = prior + time.monotonic() - began
        optimizer.zero_grad(set_to_none=True)
        save_checkpoint(
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
            objective_version=2,
            mixing=MIXING[arm],
            parent_step=baseline,
            completed_stage_updates=step - baseline,
            cumulative_Adam_step=step,
            new_head_Adam_step=step - baseline,
            elapsed_seconds=elapsed,
            slice_elapsed_seconds=time.monotonic() - began,
            run_id=binding["run_id"],
            model_identity=model_identity(model),
            parent_checkpoint_SHA256=INITIAL_SHA256,
            initial_diagnostic=history["history"][0],
            last_diagnostic=history["history"][-1],
            diagnostics=history["history"],
            last_stochastic_loss=history["last_stochastic_loss"],
            last_stochastic_gradient_norm=history["last_stochastic_gradient_norm"],
            failure=history.get("failure"),
            fixed_update_target=target,
            original_snapshots_unchanged=True,
        )
        if history["status"] == "RUNNING":
            result["status"] = "SLICE_EXHAUSTED_RESUME_REQUIRED"
            _atomic_json(folder / "SLICE_RECEIPT.json", result)
        else:
            _atomic_json(folder / "TERMINAL.json", result)
        emit(dict(stage="weighting_slice_return", arm=arm, **result))
        return result
