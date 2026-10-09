"""One fixed four-fit protocol; real fitting is an explicit frozen-packet action."""

from __future__ import annotations

import argparse
import json
import os
import time
from pathlib import Path

import numpy as np
import torch

from .checkpoint import (
    OPTIMIZER,
    _atomic_json,
    load_checkpoint,
    make_optimizer,
    model_identity,
    run_binding,
    run_guard,
    save_checkpoint,
    source_identity,
)
from .exact import memory_bounded_gradients, request_loss_and_gradient, verify_prototype
from .inputs import Standardizer, digest, fit_standardizer
from .model import DEFAULT_FIXED_EXPERT_SET, SEED, Selector, predict_windows

ARMS = (("GRU64", False), ("LATEST_MLP", False), ("GRU64", True), ("LATEST_MLP", True))
PROTOCOL = dict(
    schema="TEMPORAL_MATCHED_FOUR_FIT_V1",
    status="FROZEN_SINGLE_COMPARISON",
    planned_fits=4,
    seed=SEED,
    arm_order=[f + ("_WITH_CASH" if c else "_NO_CASH") for f, c in ARMS],
    fixed_expert_set=list(DEFAULT_FIXED_EXPERT_SET),
    optimizer=OPTIMIZER,
    initialization="zero_w_and_s_readouts;matched_NO_CASH_[0,.5,0,0,.5];WITH_CASH_[.5,.25,0,0,.25]",
    dropout=0.1,
    feature_batch_size=32,
    economic_rollout="complete_chronological_wallet_once_per_step",
    gradient="exact_request_VJP_then_RNG_identical_feature_replay;no_wallet_minibatches",
    shared_normalizer="one_unique_train_window_rows_valid_only_mean_std_ddof0;after_episode_freeze",
    objective="unchanged_recovered_daily_logNAV_minus5_negative_daily_return_squared",
    convergence=dict(
        evaluate_every=16,
        minimum_updates=128,
        stable_evaluations=5,
        loss_abs_tolerance=1e-7,
        loss_relative_tolerance=1e-3,
        request_mean_abs_change_tolerance=1e-3,
        gradient_ratio_to_initial=0.1,
        gradient_absolute_floor=1e-10,
        evaluation="deterministic_training_path_eval_dropout_off;no_development_access",
        interpretation="operational_train_only_criterion;not_global_optimality_or_alpha",
    ),
    limits=dict(
        CPU_threads=1,
        memory_bytes=2_000_000_000,
        GPU=False,
        swap=False,
        maximum_updates_per_fit=1024,
        seconds_per_fit=1200.0,
        total_wall_seconds=5000,
        serial_fits=True,
        checkpoint_every_completed_update=1,
    ),
    capped_status="CAPPED_NOT_CONVERGED;no_negative_feasibility_conclusion",
    checkpoint_selection="terminal_completed_training_step_only;no_dev_selected_epoch",
    development="freeze_all_four_terminal_models_before_scoring;seen_MayJune2024_only",
    architecture_or_LR_search=False,
    model_observed_wallet=False,
    unverified_actions=False,
)


def gradient_norm(model):
    return float(
        torch.sqrt(
            sum(
                (p.grad.square().sum() for p in model.parameters() if p.grad is not None),
                start=torch.tensor(0.0, dtype=torch.float64),
            )
        )
    )


def convergence_met(history, initial_norm, step, rule):
    n = rule["stable_evaluations"]
    if step < rule["minimum_updates"] or len(history) < n:
        return False
    tail = history[-n:]
    losses = [item["loss"] for item in tail]
    tolerance = max(rule["loss_abs_tolerance"], rule["loss_relative_tolerance"] * abs(losses[0]))
    threshold = max(
        rule["gradient_absolute_floor"], rule["gradient_ratio_to_initial"] * initial_norm
    )
    return (
        max(losses) - min(losses) <= tolerance
        and all(item["gradient_norm"] <= threshold for item in tail)
        and all(
            item["request_change"] <= rule["request_mean_abs_change_tolerance"] for item in tail[1:]
        )
    )


def _evaluate_training(model, optimizer, episodes, prototype, batch_size, gradient_function):
    model.eval()
    optimizer.zero_grad(set_to_none=True)
    loss, requests = gradient_function(model, episodes, prototype, feature_batch_size=batch_size)
    norm = gradient_norm(model)
    optimizer.zero_grad(set_to_none=True)
    if not np.isfinite(loss) or not np.isfinite(norm):
        raise ValueError("Nonfinite deterministic training evaluation")
    return loss, norm, requests


def train_arm(
    model,
    episodes,
    prototype,
    directory,
    dataset_identity,
    *,
    protocol=PROTOCOL,
    gradient_function=memory_bounded_gradients,
):
    """Complete own-path updates; train-only stop state saved with every update."""
    limits, rule = protocol["limits"], protocol["convergence"]
    batch = protocol["feature_batch_size"]
    binding = run_binding(
        model,
        data_split_identity=dataset_identity,
        feature_batch_size=batch,
        max_steps=limits["maximum_updates_per_fit"],
        checkpoint_every=1,
        max_seconds=limits["seconds_per_fit"],
        algorithm=dict(
            protocol_SHA256=digest(protocol),
            convergence=rule,
            gradient=protocol["gradient"],
            limits=limits,
        ),
    )
    optimizer = make_optimizer(model)
    with run_guard(directory, binding) as output:
        if (output / "latest.json").exists():
            loaded = load_checkpoint(output, model, optimizer, binding)
            step, prior_elapsed, state = (
                loaded["step"],
                loaded["elapsed_seconds"],
                loaded["trainer_state"],
            )
            if state.get("status") in ("TRAIN_CONVERGENCE_CRITERION_MET", "CAPPED_NOT_CONVERGED"):
                return dict(
                    status=state["status"],
                    step=step,
                    run_id=binding["run_id"],
                    model_identity=model_identity(model),
                    elapsed_seconds=prior_elapsed,
                )
        else:
            torch.manual_seed(model.seed + 3)
            step, prior_elapsed = 0, 0.0
            state = dict(status="RUNNING", history=[], initial_norm=None, last_requests=None)
        began = time.monotonic()
        if state["initial_norm"] is None:
            loss, norm, requests = _evaluate_training(
                model, optimizer, episodes, prototype, batch, gradient_function
            )
            state.update(
                initial_norm=norm,
                last_requests=torch.tensor(requests),
                history=[dict(step=0, loss=loss, gradient_norm=norm, request_change=0.0)],
            )
            save_checkpoint(
                output,
                model,
                optimizer,
                binding,
                step=0,
                elapsed_seconds=prior_elapsed + time.monotonic() - began,
                trainer_state=state,
            )
        while state["status"] == "RUNNING":
            elapsed = prior_elapsed + time.monotonic() - began
            if step >= limits["maximum_updates_per_fit"] or elapsed >= limits["seconds_per_fit"]:
                state["status"] = "CAPPED_NOT_CONVERGED"
                break
            model.train()
            optimizer.zero_grad(set_to_none=True)
            loss, _ = gradient_function(model, episodes, prototype, feature_batch_size=batch)
            if not np.isfinite(loss):
                raise ValueError("Nonfinite exact path objective; retain last atomic checkpoint")
            norm = torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0, error_if_nonfinite=True)
            optimizer.step()
            optimizer.zero_grad(set_to_none=True)
            step += 1
            if step % rule["evaluate_every"] == 0:
                score, eval_norm, requests = _evaluate_training(
                    model, optimizer, episodes, prototype, batch, gradient_function
                )
                change = float(np.mean(np.abs(requests - state["last_requests"].numpy())))
                state["history"].append(
                    dict(step=step, loss=score, gradient_norm=eval_norm, request_change=change)
                )
                state["last_requests"] = torch.tensor(requests)
                if convergence_met(state["history"], state["initial_norm"], step, rule):
                    state["status"] = "TRAIN_CONVERGENCE_CRITERION_MET"
            elapsed = prior_elapsed + time.monotonic() - began
            if state["status"] == "RUNNING" and (
                step >= limits["maximum_updates_per_fit"] or elapsed >= limits["seconds_per_fit"]
            ):
                state["status"] = "CAPPED_NOT_CONVERGED"
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
                        stage="training",
                        family=model.family,
                        cash=model.cash_enabled,
                        completed_updates=step,
                        training_loss=loss,
                        gradient_norm=float(norm),
                        status=state["status"],
                        elapsed_seconds=elapsed,
                    )
                ),
                flush=True,
            )
        # A time cap reached between updates still gets an atomic terminal state.
        elapsed = prior_elapsed + time.monotonic() - began
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
            step=step,
            run_id=binding["run_id"],
            model_identity=model_identity(model),
            elapsed_seconds=elapsed,
        )
        _atomic_json(output / "TERMINAL.json", result)
        return result


def run_comparison(
    train,
    development,
    prototype,
    output,
    *,
    packet_identity,
    protocol=PROTOCOL,
    gradient_function=memory_bounded_gradients,
):
    """Caller must supply frozen byte-verified episodes; CLI packet loader enforces it."""
    if (
        not train
        or not development
        or any(e.role != "TRAIN" for e in train)
        or any(e.role != "SEEN_VALIDATION" for e in development)
    ):
        raise ValueError("Frozen TRAIN and separate SEEN_VALIDATION episodes required")
    verify_prototype(prototype)
    cutoff = train[0].split_cutoff_us
    if any(e.split_cutoff_us != cutoff for e in train) or any(
        e.start_us < cutoff for e in development
    ):
        raise ValueError(
            "Common training cutoff and strictly subsequent development roles required"
        )
    dataset = dict(
        packet=packet_identity,
        train=[e.identity for e in train],
        development=[e.identity for e in development],
    )
    common = dict(protocol_SHA256=digest(protocol), dataset=dataset, sources=source_identity())
    group = dict(run_id=digest(common), specification=common)
    with run_guard(output, group) as directory:
        if (directory / "DEVELOPMENT_RESULTS.json").exists():
            return json.loads((directory / "DEVELOPMENT_RESULTS.json").read_text())
        scaler_path, scaler_proof = directory / "SCALER.npz", directory / "SCALER.json"
        if scaler_proof.exists():
            proof = json.loads(scaler_proof.read_text())
            from .exact import sha

            if sha(scaler_path) != proof["SHA256"]:
                raise ValueError("Frozen shared scaler bytes changed")
            with np.load(scaler_path, allow_pickle=False) as z:
                scaler = Standardizer(z["mean"], z["scale"], z["count"], proof["provenance"])
            if scaler.identity != proof["identity"]:
                raise ValueError("Frozen shared scaler identity changed")
        else:
            scaler = fit_standardizer([e.windows for e in train], training_cutoff_us=cutoff)
            # No optimization has started; interrupted pre-pointer creation can
            # rewrite this deterministic scaler, but a frozen run never refits it.
            with scaler_path.open("wb") as stream:
                np.savez(stream, mean=scaler.mean, scale=scaler.scale, count=scaler.count)
            from .exact import sha

            _atomic_json(
                scaler_proof,
                dict(
                    SHA256=sha(scaler_path),
                    identity=scaler.identity,
                    provenance=scaler.provenance,
                    fit_count=1,
                ),
            )
        models, terminal = {}, {}
        for family, cash in ARMS:
            name = family + ("_WITH_CASH" if cash else "_NO_CASH")
            model = Selector(
                scaler,
                family=family,
                cash_enabled=cash,
                dropout=protocol["dropout"],
                seed=protocol["seed"],
                zero_readout=True,
            )
            terminal[name] = train_arm(
                model,
                train,
                prototype,
                directory / name,
                dataset,
                protocol=protocol,
                gradient_function=gradient_function,
            )
            models[name] = model.eval()
        # Four terminal byte-bound snapshots precede any development scoring.
        _atomic_json(
            directory / "ALL_FOUR_TERMINAL.json",
            dict(
                status="ALL_FOUR_FROZEN_BEFORE_DEVELOPMENT",
                terminal=terminal,
                scaler_identity=scaler.identity,
                group_identity=group["run_id"],
            ),
        )
        results = {}
        with torch.no_grad():
            for name, model in models.items():
                reports = []
                for episode in development:
                    request = predict_windows(
                        model, episode.windows, feature_batch_size=protocol["feature_batch_size"]
                    ).numpy()
                    loss, _, report = request_loss_and_gradient(request, episode, prototype)
                    reports.append(
                        dict(
                            wallet_id=episode.wallet_id,
                            loss=loss,
                            **{
                                k: report[k]
                                for k in (
                                    "net_PnL",
                                    "utility_sum",
                                    "fees",
                                    "spread",
                                    "slippage",
                                    "funding",
                                    "terminal_cash_realized",
                                    "status",
                                )
                            },
                        )
                    )
                results[name] = dict(training=terminal[name], development=reports)
        capped = any(r["status"] == "CAPPED_NOT_CONVERGED" for r in terminal.values())
        result = dict(
            status="CAPPED_COMPARISON_NOT_CONVERGED" if capped else "TRAIN_CRITERIA_MET",
            planned_fits=4,
            actual_fits=4,
            refits=0,
            arms=results,
            development_classification="SEEN_PROXY_NOT_UNTOUCHED_OOS",
            data_identity=dataset,
            protocol_SHA256=digest(protocol),
            scaler_identity=scaler.identity,
            native_wallets=0,
            convergence_is_not_economic_qualification=True,
        )
        _atomic_json(directory / "DEVELOPMENT_RESULTS.json", result)
        return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("protocol", "check", "fit"))
    parser.add_argument("--packet")
    parser.add_argument("--packet-sha256")
    parser.add_argument("--prototype")
    parser.add_argument("--output")
    args = parser.parse_args()
    if args.mode == "protocol":
        print(json.dumps(PROTOCOL, indent=2, sort_keys=True))
        return
    from .training_packet import load_packet

    if not args.packet or not args.packet_sha256 or not args.prototype:
        parser.error("check/fit require immutable packet SHA and exact prototype")
    train, development, prototype, identity = load_packet(
        args.packet, args.packet_sha256, args.prototype
    )
    if args.mode == "check":
        print(
            json.dumps(
                dict(
                    status="FROZEN_PACKET_READY_ZERO_FIT",
                    identity=identity,
                    training_rows=sum(len(e.contexts) for e in train),
                    development_rows=sum(len(e.contexts) for e in development),
                )
            )
        )
        return
    if not args.output:
        parser.error("fit requires an exclusive state output directory")
    if os.environ.get("COIN_CLOUD_BOUNDED") != "1" or len(os.sched_getaffinity(0)) != 1:
        parser.error("fit must run through the one-CPU bounded_comparison launcher")
    if len(Path("/proc/swaps").read_text().splitlines()) != 1:
        parser.error("fit requires swap absent")
    torch.set_num_threads(1)
    torch.use_deterministic_algorithms(True)
    print(
        json.dumps(
            run_comparison(train, development, prototype, args.output, packet_identity=identity)
        )
    )


if __name__ == "__main__":
    main()
