"""Reuse frozen model, objective and checkpoint kernels for one fresh512 fit."""

import json
import time
from pathlib import Path

import numpy as np
import torch

from modules.temporal_episode_weighting_v2.gradient import (
    episode_diagnostic,
    memory_bounded_gradients,
)
from modules.temporal_episode_weighting_v2.stage import sources as warm_sources
from modules.temporal_episode_weighting_v2.stage import tree_identity
from modules.temporal_expert_input.checkpoint import load_checkpoint, save_checkpoint
from modules.temporal_expert_input.stage import emit, inputs
from modules.temporal_prequential_transfer.model import initialize, parameter_identity
from modules.temporal_prequential_transfer.protocol import sources as fresh_sources
from modules.temporal_prequential_transfer.stage import SUCCESS, validate_terminal
from modules.temporal_two_expert.checkpoint import (
    _atomic_json,
    _rng_state,
    model_identity,
    run_binding,
    run_guard,
)
from modules.temporal_two_expert.exact import sha
from modules.temporal_two_expert.inputs import fit_standardizer
from modules.temporal_two_expert.model import SEED

ARM = "FRESH_DATE_512"
COMPARATOR_COMMIT = "d3d57332ca45b7a4443108db21f46abad0e1ac99"
COMPARATOR_MODEL = "7b0f0a6c58fec8efd2aacec5c5abd41ec2aca68fa4c27432a9770b59acb594fd"
COMPARATOR_CHECKPOINT = "7dcf57d6e840e27e8b159046964ab43938a905c3a3cc0f774bafa37e80c55da2"
PROTOCOL = dict(
    schema="ONE_FIXED512_FRESH_INITIALIZATION_ABLATION_V1",
    planned_fits=1,
    arm=ARM,
    comparator_commit=COMPARATOR_COMMIT,
    comparator_model_identity=COMPARATOR_MODEL,
    comparator_checkpoint_SHA256=COMPARATOR_CHECKPOINT,
    architecture="same13699_CORE5_GRU64_hidden32_joint160to32_plus18currentexpertinputs",
    input="24causalvalues24validitymasks_separate_time_masks;no_observed_wallet",
    initialization="same_three_fresh_folds_recipe;seeded_new_model_emptyAdam_PythonNumPyTorchRNG",
    seed=SEED,
    dropout=0.1,
    feature_batch_size=32,
    objective_version=2,
    mixing=0.0,
    objective="unchanged_date_weighted_complete_own_wallet_charged_boundary_v2",
    training_decisions=778,
    natural_wallet_lengths=[54, 88, 62, 144, 430],
    normalization="same_preMay_prefix_only_unique907row_valid_train_window_union;byteequal_old_scaler",
    fixed_updates=512,
    diagnostics=[0, 128, 256, 512],
    diagnostics_role="TRAIN_ONLY_deterministic;no_optimizer_update_or_seen_selection",
    seconds_per_slice=1200.0,
    maximum_slices=4,
    checkpoint_every=1,
    maximum_concurrent_fits=1,
    memory_bytes=2000000000,
    shared_memory_bytes=8000000000,
    swap=0,
    GPU=0,
    chronology="five_original_complete_wallets_and_gaps;no_random_episode_minibatches",
    mapper="unchanged_eligibility_release_L1.1_gross.6_asset.3_risk_covariance_check",
    capital_each=10000.0,
    costs_funding_terminal="unchanged_paid_closure_and_signed_funding",
    data_role="explicit_seen_MayJune_development_initialization_ablation;not_OOS",
    development="terminal512_frozen_before_scoring;actual_native61_requests_export_first",
    limitation="prescribed_initialization_regimes;not_equal_lifetime_optimizer_or_data_exposure",
    lifetime_ages=dict(warm_base=1292, warm_heads=512, fresh_all=512),
    no_seed_sweep=True,
    no_continuation_beyond512=True,
    numerical_failure="save_precise_failure_and_last_completed_checkpoint;stop_no_recipe_retry",
)


def sources():
    root = Path(__file__).resolve().parents[2]
    return {
        **warm_sources(),
        **fresh_sources(),
        **{str(p.relative_to(root)): sha(p) for p in sorted(Path(__file__).parent.glob("*.py"))},
    }


def load_inputs(state, *, development=False):
    train, dev, prototype, dataset, scaler = inputs(state, include_development=development)
    if [len(e.contexts) for e in train] != PROTOCOL["natural_wallet_lengths"]:
        raise ValueError("Exactly the original complete778 training dates required")
    refit = fit_standardizer(
        [e.windows for e in train], training_cutoff_us=train[0].split_cutoff_us
    )
    if refit.identity != scaler.identity or refit.provenance["real_row_count"] != 907:
        raise ValueError("Fresh prefix recomputation must match exact warm907-row scaler")
    for name in ("mean", "scale", "count"):
        np.testing.assert_array_equal(getattr(refit, name), getattr(scaler, name))
    return train, dev, prototype, dataset, scaler


def binding_for(model, dataset):
    return run_binding(
        model,
        data_split_identity=dataset,
        feature_batch_size=32,
        max_steps=512,
        max_seconds=1200.0,
        algorithm=dict(
            objective_version=2,
            parent=dict(step=0, fresh=True),
            parameter_birth_steps={name: 0 for name, _ in model.named_parameters()},
            protocol=PROTOCOL,
            mixing=0.0,
            versioned_sources=sources(),
        ),
    )


def prepare(state, output):
    output = Path(output)
    audit = json.loads((Path(state) / "fresh-initialization/COMPARABILITY.json").read_text())
    if audit["comparator_commit"] != COMPARATOR_COMMIT or not audit["fresh_Adam_empty"]:
        raise ValueError("Completed exact-comparator audit required before any fit")
    train, _, prototype, dataset, scaler = load_inputs(state)
    model, optimizer = initialize(scaler)
    binding = binding_for(model, dataset)
    raw, rng = parameter_identity(model), tree_identity(_rng_state())
    if raw != audit["fresh_parameters_identity"] or rng != audit["fresh_all_RNG_identity"]:
        raise ValueError("Exactly the audited fresh recipe required")
    with run_guard(output / ARM, binding) as folder:
        if (folder / "latest.json").exists():
            raise FileExistsError("Fresh initialization may be prepared only once")
        diagnostic = episode_diagnostic(
            model,
            train,
            prototype,
            mixing=0.0,
            feature_batch_size=32,
            snapshot_step=0,
            check_aggregate=True,
        )
        if (
            optimizer.state
            or raw != parameter_identity(model)
            or rng != tree_identity(_rng_state())
        ):
            raise ValueError("Preflight must preserve new model/emptyAdam/allRNG")
        history = dict(
            status="RUNNING",
            completed_updates=0,
            history=[diagnostic],
            last_stochastic_loss=None,
            last_stochastic_gradient_norm=None,
        )
        save_checkpoint(
            folder, model, optimizer, binding, step=0, trainer_state=history, sources=sources
        )
        np.savez_compressed(
            folder / "SCALER.npz", mean=scaler.mean, scale=scaler.scale, count=scaler.count
        )
        _atomic_json(
            folder / "SCALER.json", dict(identity=scaler.identity, provenance=scaler.provenance)
        )
    ready = dict(
        status="ONE_FRESH_FIT_FROZEN_BEFORE_OPTIMIZATION",
        protocol=PROTOCOL,
        sources=sources(),
        binding=binding,
        comparability=audit,
        initial_parameter_identity=raw,
        initial_all_RNG_identity=rng,
        initial_model_identity=model_identity(model),
        empty_Adam=True,
        initial_diagnostic=diagnostic,
        optimizer_updates=0,
        development_economic_scores=0,
        native_wallets=0,
        provider_downloads=0,
    )
    _atomic_json(output / "READY.json", ready)
    return ready


def frozen_state(state, output):
    train, dev, prototype, dataset, scaler = load_inputs(state, development=True)
    model, optimizer = initialize(scaler)
    binding = binding_for(model, dataset)
    folder = Path(output) / ARM
    saved = load_checkpoint(folder, model, optimizer, binding, sources=sources)
    terminal = json.loads((folder / "TERMINAL.json").read_text())
    validate_terminal(terminal, saved)
    # The frozen loader validates binding but intentionally does not return it.
    saved = {**saved, "binding": binding}
    return train, dev, prototype, model, optimizer, folder, saved, terminal


def train_slice(state, output):
    train, _, prototype, dataset, scaler = load_inputs(state)
    model, optimizer = initialize(scaler)
    binding = binding_for(model, dataset)
    ready = json.loads((Path(output) / "READY.json").read_text())
    if ready["binding"] != binding or ready["sources"] != sources():
        raise ValueError("Immutable published initialization/data/source identity changed")
    with run_guard(Path(output) / ARM, binding) as folder:
        saved = load_checkpoint(folder, model, optimizer, binding, sources=sources)
        if (folder / "TERMINAL.json").exists():
            terminal = json.loads((folder / "TERMINAL.json").read_text())
            if terminal["status"] == SUCCESS:
                validate_terminal(terminal, saved)
            return terminal
        step, prior, history = saved["step"], saved["elapsed_seconds"], saved["trainer_state"]
        if history["completed_updates"] != step:
            raise ValueError("Actual checkpoint and completed optimizer count differ")
        began, phase, attempted = time.monotonic(), "restore", step
        try:

            def diagnostic_if_due():
                if (
                    step in PROTOCOL["diagnostics"]
                    and history["history"][-1]["snapshot_step"] != step
                ):
                    history["history"].append(
                        episode_diagnostic(
                            model,
                            train,
                            prototype,
                            mixing=0.0,
                            feature_batch_size=32,
                            snapshot_step=step,
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
                attempted, phase = step + 1, "whole_wallet_stochastic_gradient"
                model.train()
                optimizer.zero_grad(set_to_none=True)
                loss, _ = memory_bounded_gradients(
                    model, train, prototype, feature_batch_size=32, mixing=0.0
                )
                if not np.isfinite(loss):
                    raise ValueError("Nonfinite full chronological objective")
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
                phase = "TRAIN_diagnostic"
                diagnostic_if_due()
                emit(
                    dict(
                        stage="fresh_initialization_fit",
                        step=step,
                        loss=loss,
                        gradient_norm=float(norm),
                        elapsed_seconds=prior + time.monotonic() - began,
                    )
                )
            if step == 512:
                history["status"] = SUCCESS
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
        optimizer.zero_grad(set_to_none=True)
        elapsed = prior + time.monotonic() - began
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
        terminal = dict(
            status=history["status"],
            arm=ARM,
            completed_updates=step,
            fixed_target=512,
            initial_step=0,
            parameters=13699,
            fresh_initialization=True,
            model_identity=model_identity(model),
            checkpoint_SHA256=pointer["SHA256"],
            elapsed_seconds=elapsed,
            diagnostics=history["history"],
            last_stochastic_loss=history["last_stochastic_loss"],
            last_stochastic_gradient_norm=history["last_stochastic_gradient_norm"],
            failure=history.get("failure"),
            development_scoring_used_for_training=False,
        )
        if history["status"] == "RUNNING":
            terminal["status"] = "SLICE_EXHAUSTED_RESUME_REQUIRED"
            _atomic_json(folder / "SLICE_RECEIPT.json", terminal)
        else:
            _atomic_json(folder / "TERMINAL.json", terminal)
        return terminal
