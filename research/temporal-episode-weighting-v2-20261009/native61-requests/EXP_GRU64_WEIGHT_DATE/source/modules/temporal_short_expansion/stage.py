"""Fixed matched continuation; training-only stops and exact optimizer births."""

import copy
import json
import time
from pathlib import Path

import numpy as np
import torch

from modules.temporal_surrogate_resume_v2.stage import (
    PROTOCOL_V2,
    load_inputs,
    original_model,
    stage_sources,
    warm_parent,
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
from modules.temporal_two_expert.inputs import digest

from .adapter import PAYLOADS, SOURCE_COMMIT, load_short_pack
from .checkpoint import load_checkpoint, save_checkpoint
from .gradient import memory_bounded_gradients
from .model import ShortSelector

ARMS = ("GRU64_CASH_CONTROL", "GRU64_CASH_MOM30_SHORT")
PROTOCOL = copy.deepcopy(PROTOCOL_V2)
PROTOCOL.update(
    schema="TEMPORAL_MATCHED_ONE_SHORT_EXPANSION_V1",
    planned_fits=2,
    arm_order=list(ARMS),
    continuation="two_separate_matched_stages;previous_four_v2_runs_immutable",
    action_pools={
        ARMS[0]: ["CASH", "VOL_MANAGED_HOLD", "CSMOM21"],
        ARMS[1]: ["CASH", "VOL_MANAGED_HOLD", "CSMOM21", "MOMENTUM30_SHORT_ONLY"],
    },
    initialization="identical_GRU64_WITH_CASH_v2_terminal_model_Adam_RNG;new_readout_birth0",
    control="same33_added_parameters;new_short_weight_exact0;matching_extra_training_budget",
    expanded="append_MOMENTUM30_SHORT_ONLY_to_canonical_slot5;initial_r=.01",
    parent_choice="pre-May_final_train_loss_GRU_CASH=-.00094994541144_vs_MLP_CASH=-.00091677655390;fixed_primary_temporal_family",
    candidate_choice="public1291857_training_only_complementarity_recommendation;no_dev_outcomes",
    encoder_and_features="unchanged_CORE5_64x24values24masks_GRU32;no_wallet_features",
    optimizer_births="base_parameter_age_cumulative;new_r_head_age_completed_expansion_updates",
    chronology="same778_dates_five_complete_real_wallets_unweighted;no_win_day_oversampling",
    private_mapper_adapter="canonical_active_coordinates[0,1,2,4,5];public2/3zero;unchanged_frozen_mapper_math",
    development="both_terminal_before_seen_economic_scoring;terminal_native_requests_may_export_immediately",
    comparison="two_matched_additional_stages;not_clean_initial_seed_fit_or_OOS_alpha",
    source_short_context_commit=SOURCE_COMMIT,
)


def sources():
    root = Path(__file__).resolve().parents[2]
    return {
        **stage_sources(),
        **{str(p.relative_to(root)): sha(p) for p in sorted(Path(__file__).parent.glob("*.py"))},
    }


def emit(record):
    try:
        print(json.dumps(record), flush=True)
    except BrokenPipeError:
        # Disconnecting the progress console must not interrupt an owned fit.
        pass


def initialize(state, scaler, enabled):
    folder = Path(state) / "surrogate-v2/GRU64_WITH_CASH"
    if not (Path(state) / "surrogate-v2/ALL_FOUR_TERMINAL.json").exists():
        raise ValueError("Previous four-arm terminal freeze required")
    old_binding = json.loads((folder / "RUN.json").read_text())
    if old_binding["specification"]["algorithm"]["versioned_sources"] != stage_sources():
        raise ValueError("Exact frozen objective-v2 source bytes required")
    base = original_model(scaler, "GRU64", True)
    old_optimizer, parent = warm_parent(folder, base)
    model = ShortSelector(base, short_enabled=enabled)
    optimizer = make_optimizer(model)
    for parameter in base.parameters():
        optimizer.state[parameter] = copy.deepcopy(old_optimizer.state[parameter])
    births = {
        name: parent["step"] if name.startswith("r_head.") else 0
        for name, _ in model.named_parameters()
    }
    return model, optimizer, parent, births


def inputs(state, *, include_development=False):
    train, dev, prototype, dataset, scaler = load_inputs(state)
    train = load_short_pack(Path(state) / "short-source", train, prototype, training=True)
    development = (
        load_short_pack(Path(state) / "short-source", dev, prototype, training=False)
        if include_development
        else ()
    )
    data = dict(
        original_dataset=dataset,
        train=[e.identity for e in train],
        source_commit=SOURCE_COMMIT,
        short_payloads=PAYLOADS,
        scaler=scaler.identity,
    )
    return train, development, prototype, data, scaler


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
            optimizer_updates=0,
            RNG_preserved=True,
            parameter_count=model.parameter_count,
            parent_checkpoint_SHA256=parent["pointer"]["SHA256"],
        )
        emit(dict(stage="short_preflight", arm=arm, loss=loss, gradient_norm=norm))
    _atomic_json(
        Path(output) / "READY.json",
        dict(
            status="MATCHED_TWO_ARMS_READY",
            protocol=PROTOCOL,
            sources=sources(),
            arms=records,
            no_development_economic_scoring=True,
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
            load_checkpoint(folder, model, optimizer, binding)
            return json.loads((folder / "TERMINAL.json").read_text())
        if (folder / "latest.json").exists():
            saved = load_checkpoint(folder, model, optimizer, binding)
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
            save_checkpoint(folder, model, optimizer, binding, step=step, trainer_state=history)
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
                )
                emit(
                    dict(
                        stage="short_training",
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
            saved = load_checkpoint(folder, model, optimizer, binding)
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
        emit(dict(stage="short_terminal", arm=arm, **result))
        return result
