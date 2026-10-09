"""Fixed matched continuation; training-only stops and exact optimizer births."""

import copy
import json
import time
from pathlib import Path

import numpy as np
import torch

from modules.temporal_short_expansion.adapter import SOURCE_COMMIT
from modules.temporal_short_expansion.stage import (
    initialize as short_initialize,
)
from modules.temporal_short_expansion.stage import (
    inputs as short_inputs,
)
from modules.temporal_short_expansion.stage import (
    sources as short_sources,
)
from modules.temporal_surrogate_resume_v2.stage import (
    PROTOCOL_V2,
)
from modules.temporal_two_expert.checkpoint import (
    _atomic_json,
    make_optimizer,
    model_identity,
    run_binding,
    run_guard,
)
from modules.temporal_two_expert.comparison import _evaluate_training, convergence_met
from modules.temporal_two_expert.exact import sha
from modules.temporal_two_expert.inputs import array_digest, digest

from .checkpoint import load_checkpoint, save_checkpoint
from .gradient import memory_bounded_gradients
from .inputs import expose_episode
from .model import ExpertSelector

ARMS = ("GRU64_EXPERT_INPUT_CONTROL", "GRU64_EXPERT_INPUT_ACTIVE")
PROTOCOL = copy.deepcopy(PROTOCOL_V2)
PROTOCOL.update(
    schema="TEMPORAL_MATCHED_EXPERT_INPUT_ABLATION_V1",
    planned_fits=2,
    arm_order=list(ARMS),
    action_pool=["CASH", "VOL_MANAGED_HOLD", "CSMOM21", "MOMENTUM30_SHORT_ONLY"],
    initialization="identical_original_v2_GRU64_WITH_CASH_terminal_model_Adam_RNG_step780;new_r=.01;new_projection0",
    expert_inputs="canonical_slots1,4,5_signed_targets_expertmajor3x5_divided_by_fixed.3_then_expert_eligible3",
    architecture="unchanged_GRU48to32_joint160to32;added18to32_biasFalse_before_tanh;both13699parameters",
    control="identical_projection_parameters;current_expert_block_multiplied_by0",
    active="exact_existing_unramped_causal_expert_targets_and_eligibility;no_new_indicator_recipe",
    clock="saved_target_available<=decision;completed_daily_bar_proxy;execution=decision+60000001us;no_backdating",
    observed_wallet=False,
    future_utility=False,
    chronology="unchanged778dates_five_complete_wallets;unweighted_date_mean;no_oversampling",
    normalization="unchanged907row_train_only_scaler;expert_targets_fixed_unit.3;SOL_outliers_unchanged",
    optimizer_births="base_birth0;r_head_and_expert_projection_birth_parentstep",
    development="both_terminal_before_seen_economic_scoring;terminal_native_requests_export_immediately",
    source_short_context_commit=SOURCE_COMMIT,
    review_commit="96b917f7e728016b6ef17e8983b98e29fcf95a8d",
    weighting_experiment_updates=0,
    comparison="matched_information_ablation;last_completed_training_snapshot;no_seen_architecture_selection",
)


def sources():
    root = Path(__file__).resolve().parents[2]
    return {
        **short_sources(),
        **{str(p.relative_to(root)): sha(p) for p in sorted(Path(__file__).parent.glob("*.py"))},
    }


def emit(record):
    try:
        print(json.dumps(record), flush=True)
    except BrokenPipeError:
        # Disconnecting the progress console must not interrupt an owned fit.
        pass


def initialize(state, scaler, enabled):
    old, old_optimizer, parent, _ = short_initialize(state, scaler, True)
    model = ExpertSelector(old.base, input_enabled=enabled)
    optimizer = make_optimizer(model)
    for parameter in model.base.parameters():
        optimizer.state[parameter] = copy.deepcopy(old_optimizer.state[parameter])
    births = {
        name: 0 if name.startswith("base.") else parent["step"]
        for name, _ in model.named_parameters()
    }
    return model, optimizer, parent, births


def inputs(state, *, include_development=False):
    train, dev, prototype, dataset, scaler = short_inputs(
        state, include_development=include_development
    )
    train, dev = tuple(map(expose_episode, train)), tuple(map(expose_episode, dev))
    data = dict(
        original_short_dataset=dataset,
        train=[e.identity for e in train],
        layout="canonical1,4,5_targets3x5/.3_then_eligible3;18",
        scaler=scaler.identity,
    )
    return train, dev, prototype, data, scaler


def binding_for(model, parent, births, dataset, protocol=PROTOCOL):
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
            parameter_birth_steps=births,
            protocol=protocol,
            protocol_SHA256=digest(protocol),
            versioned_sources=sources(),
        ),
    )


def input_audit(episodes):
    return dict(
        schema="EXACT_CURRENT_EXPERT_INPUT_AVAILABILITY_V1",
        dates=sum(len(e.contexts) for e in episodes),
        episodes=[len(e.contexts) for e in episodes],
        input_shape=[sum(len(e.contexts) for e in episodes), 18],
        targets_equal_exact_context=True,
        source_target_clocks_preserved=True,
        available_at_decision=sum(
            int(np.sum(e.expert_input_available_us == e.windows.decision_us[:, None]))
            for e in episodes
        ),
        available_after_decision=sum(
            int(np.sum(e.expert_input_available_us > e.windows.decision_us[:, None]))
            for e in episodes
        ),
        minimum_execution_slack_us=min(
            int(np.min(e.windows.decision_us[:, None] + 60000001 - e.expert_input_available_us))
            for e in episodes
        ),
        completed_bar_clock="UNCERTIFIED_HISTORICAL_COMPLETED_DAILY_CLOSE_PROXY;not_measured_exchange_release",
        input_source_roles="past_market_and_current_expert_state_only;no_prices_funding_outcomes_labels_wallet_state",
        fixed_target_unit=0.3,
        train_scaler_refit_count=0,
        economic_fit_updates=0,
    )


def prepare(state, output):
    train, _, prototype, dataset, scaler = inputs(state)
    records = {}
    for arm in ARMS:
        model, optimizer, parent, births = initialize(state, scaler, arm == ARMS[1])
        binding = binding_for(model, parent, births, dataset)
        rng, identity = torch.get_rng_state().clone(), model_identity(model)
        loss, norm, requests = _evaluate_training(
            model,
            optimizer,
            train,
            prototype,
            PROTOCOL["feature_batch_size"],
            memory_bounded_gradients,
        )
        assert torch.equal(rng, torch.get_rng_state()) and identity == model_identity(model)
        records[arm] = dict(
            binding=binding,
            train_loss=loss,
            gradient_norm=norm,
            request_mean=requests.mean(0).tolist(),
            request_identity=array_digest(requests),
            Torch_RNG_SHA256=array_digest(rng.numpy()),
            optimizer_updates=0,
            RNG_preserved=True,
            parameter_count=model.parameter_count,
            parent_checkpoint_SHA256=parent["pointer"]["SHA256"],
        )
        emit(dict(stage="expert_input_preflight", arm=arm, loss=loss, gradient_norm=norm))
    _atomic_json(
        Path(output) / "READY.json",
        dict(
            status="MATCHED_TWO_ARMS_READY",
            protocol=PROTOCOL,
            sources=sources(),
            arms=records,
            no_development_economic_scoring=True,
            input_audit=input_audit(train),
        ),
    )


def train_arm(state, output, arm, *, protocol=PROTOCOL):
    train, _, prototype, dataset, scaler = inputs(state)
    model, optimizer, parent, births = initialize(state, scaler, arm == ARMS[1])
    binding = binding_for(model, parent, births, dataset, protocol)
    ready = json.loads((Path(output) / "READY.json").read_text())
    if ready["arms"][arm]["binding"] != binding:
        raise ValueError("Published preflight/protocol/source/parent identity changed")
    limits, rule, baseline = protocol["limits"], protocol["convergence"], parent["step"]
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
                initial_norm=None,
                history=[],
                last_requests=None,
                completed_stage_updates=0,
                last_stochastic_loss=None,
                last_stochastic_gradient_norm=None,
            )
            save_checkpoint(
                folder, model, optimizer, binding, step=step, trainer_state=history, sources=sources
            )
        began, phase, attempted = time.monotonic(), "initial_training_evaluation", step - baseline
        try:
            if history["initial_norm"] is None:
                loss, norm, requests = _evaluate_training(
                    model,
                    optimizer,
                    train,
                    prototype,
                    protocol["feature_batch_size"],
                    memory_bounded_gradients,
                )
                history.update(
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
                    folder,
                    model,
                    optimizer,
                    binding,
                    step=step,
                    elapsed_seconds=prior + time.monotonic() - began,
                    trainer_state=history,
                    sources=sources,
                )
            while history["status"] == "RUNNING":
                updates, elapsed = step - baseline, prior + time.monotonic() - began
                if (
                    updates >= limits["maximum_updates_per_fit"]
                    or elapsed >= limits["seconds_per_fit"]
                ):
                    history["status"] = "CAPPED_NOT_CONVERGED"
                    break
                phase, attempted = "complete_chronological_stochastic_gradient", updates + 1
                model.train()
                optimizer.zero_grad(set_to_none=True)
                loss, _ = memory_bounded_gradients(
                    model, train, prototype, feature_batch_size=protocol["feature_batch_size"]
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
                if updates % rule["evaluate_every"] == 0:
                    phase = "deterministic_train_evaluation"
                    score, eval_norm, requests = _evaluate_training(
                        model,
                        optimizer,
                        train,
                        prototype,
                        protocol["feature_batch_size"],
                        memory_bounded_gradients,
                    )
                    change = float(np.mean(np.abs(requests - history["last_requests"].numpy())))
                    history["history"].append(
                        dict(
                            step=updates,
                            cumulative_step=step,
                            loss=score,
                            gradient_norm=eval_norm,
                            request_change=change,
                        )
                    )
                    history["last_requests"] = torch.tensor(requests)
                    if convergence_met(history["history"], history["initial_norm"], updates, rule):
                        history["status"] = "TRAIN_CONVERGENCE_CRITERION_MET"
                elapsed = prior + time.monotonic() - began
                if history["status"] == "RUNNING" and (
                    updates >= limits["maximum_updates_per_fit"]
                    or elapsed >= limits["seconds_per_fit"]
                ):
                    history["status"] = "CAPPED_NOT_CONVERGED"
                phase = "atomic_checkpoint"
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
                emit(
                    dict(
                        stage="expert_input_training",
                        arm=arm,
                        completed_stage_updates=updates,
                        cumulative_step=step,
                        stochastic_loss=loss,
                        preclip_gradient_norm=float(norm),
                        elapsed_seconds=elapsed,
                        status=history["status"],
                    )
                )
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
            parent_step=baseline,
            completed_stage_updates=step - baseline,
            cumulative_Adam_step=step,
            new_head_Adam_step=step - baseline,
            elapsed_seconds=elapsed,
            run_id=binding["run_id"],
            model_identity=model_identity(model),
            parent_checkpoint_SHA256=parent["pointer"]["SHA256"],
            initial_train=history["history"][0] if history["history"] else None,
            last_deterministic_train=history["history"][-1] if history["history"] else None,
            last_stochastic_loss=history["last_stochastic_loss"],
            last_stochastic_gradient_norm=history["last_stochastic_gradient_norm"],
            failure=history.get("failure"),
            original_and_v2_snapshots_unchanged=True,
        )
        _atomic_json(folder / "TERMINAL.json", result)
        emit(dict(stage="expert_input_terminal", arm=arm, **result))
        return result
