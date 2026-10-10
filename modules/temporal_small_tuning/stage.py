"""Full chronological training paths with the reviewed development selection."""

import json
import time
from pathlib import Path

import numpy as np
import torch

from modules.temporal_april_transfer.data import load_fold as april_data
from modules.temporal_episode_weighting_v2.gradient import (
    episode_diagnostic,
    memory_bounded_gradients,
)
from modules.temporal_episode_weighting_v2.stage import tree_identity
from modules.temporal_expert_input.gradient import predict_episode, request_gradient
from modules.temporal_prequential_transfer.model import initialize, parameter_identity
from modules.temporal_prequential_transfer.stage import load_fold as january_data
from modules.temporal_two_expert.checkpoint import (
    _atomic_json,
    _rng_state,
    model_identity,
    run_guard,
)
from modules.temporal_two_expert.inputs import DAY_US

from .checkpoint import binding_for, load, optimizer_for, retain, save, validate_moments
from .protocol import ROOT, plan, protocol, sources, task

CONTROLS = {
    "FROZEN_VOL": [0.0, 1.0, 0.0, 0.0, 0.0, 0.0],
    "Static50": [0.0, 0.5, 0.0, 0.0, 0.5, 0.0],
    "Cash50": [0.5, 0.25, 0.0, 0.0, 0.25, 0.0],
}
DONE = {
    "EARLY_STOP_RULE",
    "UPDATE_CAP_NOT_CONVERGENCE",
    "CUMULATIVE_RESOURCE_CAP",
    "STOP_NUMERICAL_OR_PATH_FAILURE",
}


def emit(record):
    print(json.dumps(record, allow_nan=False), flush=True)


def inputs(state, fold):
    expected = plan()["folds"].get(fold)
    if expected is None:
        raise ValueError("Only the two approved folds required")
    values = april_data(state) if fold == "FOLD_20240401" else january_data(state, fold)
    train, forward, prototype, scaler, data, receipt = values
    actual = sum(len(e.contexts) - 1 for e in train)
    if (
        actual != expected["actual_distinct_eligible_active_training_dates"]
        or actual < 600
        or [len(e.contexts) for e in train] != expected["wallet_lengths"]
        or scaler.provenance["real_row_count"]
        != expected["unique_prefix_normalization_feature_rows"]
    ):
        raise ValueError("Exact600+active dates, natural wallets and train-only scaler required")
    dates = []
    for e in train:
        d = e.windows.decision_us
        if not np.all(np.diff(d) == DAY_US) or np.any(e.label_available_us >= forward.start_us):
            raise ValueError("True chronology and strict prefix maturity required")
        dates.extend(d[:-1].tolist())
    if len(set(dates)) != actual:
        raise ValueError("Actual distinct eligible dates required")
    manifest = json.loads(
        (
            ROOT / "research/temporal-prefix-static-baseline-20261010/FROZEN_SELECTIONS.json"
        ).read_text()
    )
    match = next(r for r in manifest["folds"] if r["first_forward_decision_us"] == forward.start_us)
    if match["selected_control"] != "VOL":
        raise ValueError("Already-frozen primary VOL control required")
    return values


def score_request(request, forward, prototype):
    loss, gradient, report = request_gradient(request, forward, prototype)
    nav = report["nav"].detach().numpy()
    if (
        not np.isfinite(loss)
        or not np.isfinite(gradient).all()
        or not np.isfinite(nav).all()
        or not report["terminal_cash_realized"]
    ):
        raise ValueError("Finite exact own path and paid closure required")
    return dict(
        mean_loss=loss,
        utility_sum=float(report["utility_sum"].detach()),
        net_PnL=float(report["net_PnL"].detach()),
        maximum_drawdown=float(np.max(1 - nav / np.maximum.accumulate(nav))),
        fees=float(report["fees"].detach()),
        spread=float(report["spread"].detach()),
        slippage=float(report["slippage"].detach()),
        funding=float(report["funding"].detach()),
        risk_events=len(report["risk_events"]),
        paid_terminal_flat=True,
        requests_mean=request.mean(0).tolist(),
    ), nav


def validation(model, forward, prototype, folder, step, controls):
    identity, rng, mode = model_identity(model), tree_identity(_rng_state()), model.training
    path = folder / f"VALIDATION_{step:04d}.json"
    if path.exists():
        result = json.loads(path.read_text())
        if result["model_identity"] != identity or result["step"] != step:
            raise ValueError("Existing validation belongs to another snapshot")
        return result
    try:
        model.eval()
        with torch.no_grad():
            request = predict_episode(model, forward, feature_batch_size=32).numpy()
        metrics, nav = score_request(request, forward, prototype)
        if np.any(request[:, [2, 3]] != 0) or not np.allclose(
            request.sum(1), 1.0, rtol=0.0, atol=1e-12
        ):
            raise ValueError("Canonical output mask/simplex required")
        result = dict(
            step=step,
            model_identity=identity,
            classification="PROJECT_SEEN_DEVELOPMENT_DAILY_SURROGATE_NOT_NATIVE",
            metrics=metrics,
            utility_excess=metrics["utility_sum"] - controls["FROZEN_VOL"]["utility_sum"],
            primary_PnL_excess=metrics["net_PnL"] - controls["FROZEN_VOL"]["net_PnL"],
            controls=controls,
            deterministic_eval=True,
            reserve_read=False,
        )
        np.savez_compressed(
            folder / f"VALIDATION_{step:04d}.npz",
            decision_us=forward.windows.decision_us,
            requests=request,
            nav=nav,
        )
        _atomic_json(path, result)
    finally:
        model.train(mode)
    if identity != model_identity(model) or rng != tree_identity(_rng_state()):
        raise ValueError("Validation changed model or RNG")
    return result


def register_validation(history, result):
    if result["step"] not in plan()["selection"]["checkpoints"]:
        raise ValueError("Only approved scheduled validation checkpoints required")
    if result["step"] in [r["step"] for r in history["validation"]]:
        raise ValueError("Validation updates counted once")
    previous = history.get("best")
    improvement = (
        float("inf") if previous is None else result["utility_excess"] - previous["utility_excess"]
    )
    history["stale_checks"] = 0 if improvement > 1e-5 else history["stale_checks"] + 1
    if previous is None or result["utility_excess"] > previous["utility_excess"]:
        history["best"] = result
    history["validation"].append(result)
    if result["step"] >= 512 and history["stale_checks"] >= 3:
        history["status"] = "EARLY_STOP_RULE"


def prepare(state, output):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    if (output / "READY.json").exists():
        raise FileExistsError("One exclusive six-fit preparation required")
    ready = {}
    cache = {}
    for settings in plan()["actual_fit_tasks"]:
        fold = settings["fold"]
        if fold not in cache:
            loaded = inputs(state, fold)
            train, forward, prototype, scaler, data, receipt = loaded
            controls = {}
            arrays = {}
            for name, vector in CONTROLS.items():
                controls[name], arrays[name] = score_request(
                    np.tile(vector, (len(forward.contexts), 1)), forward, prototype
                )
            cache[fold] = (loaded, controls, arrays)
        (train, forward, prototype, scaler, data, receipt), controls, arrays = cache[fold]
        model, _ = initialize(scaler)
        optimizer = optimizer_for(model, settings)
        binding = binding_for(model, data, settings)
        raw, rng = parameter_identity(model), tree_identity(_rng_state())
        with run_guard(output / settings["task_id"], binding) as folder:
            if (folder / "latest.json").exists():
                raise FileExistsError("Never overwrite an already prepared fit")
            diagnostic = episode_diagnostic(
                model,
                train,
                prototype,
                mixing=settings["wallet_equal_mix"],
                feature_batch_size=32,
                snapshot_step=0,
            )
            if (
                optimizer.state
                or raw != parameter_identity(model)
                or rng != tree_identity(_rng_state())
            ):
                raise ValueError("Preflight changed fresh parameters/empty Adam/RNG")
            history = dict(
                status="RUNNING",
                completed_updates=0,
                training_diagnostics=[diagnostic],
                validation=[],
                best=None,
                stale_checks=0,
                controls=controls,
                last_stochastic_loss=None,
                last_gradient_norm=None,
                slices=[],
            )
            p = save(folder, model, optimizer, binding, step=0, elapsed=0.0, history=history)
            _atomic_json(folder / "INITIAL.json", p)
            np.savez_compressed(
                folder / "SCALER.npz", mean=scaler.mean, scale=scaler.scale, count=scaler.count
            )
            np.savez_compressed(
                folder / "CONTROL_NAV.npz", decision_us=forward.windows.decision_us, **arrays
            )
            _atomic_json(
                folder / "SCALER.json", dict(identity=scaler.identity, provenance=scaler.provenance)
            )
        ready[settings["task_id"]] = dict(
            settings=settings,
            binding=binding,
            training=receipt,
            raw_parameter_identity=raw,
            all_RNG_identity=rng,
            initial_pointer=p,
            empty_Adam=True,
            parameters=model.parameter_count,
        )
        emit(
            dict(
                stage="READY",
                task=settings["task_id"],
                active_dates=settings["eligible_dates"],
                updates=0,
            )
        )
    for fold in cache:
        records = [r for r in ready.values() if r["settings"]["fold"] == fold]
        if (
            len({r["raw_parameter_identity"] for r in records}) != 1
            or len({r["all_RNG_identity"] for r in records}) != 1
        ):
            raise ValueError("Withinfold matched fresh parameters/allRNG required")
    result = dict(
        status="FROZEN_SIX_FITS_BEFORE_OPTIMIZATION",
        protocol=protocol(),
        sources=sources(),
        tasks=ready,
        optimizer_updates=0,
        native_wallets=0,
        provider_downloads=0,
        reserve_results_read=False,
    )
    _atomic_json(output / "READY.json", result)
    return result


def train_slice(state, output, task_id, *, seconds=1100.0):
    if not 0 < seconds <= 1100.0:
        raise ValueError("Bounded approved slice required")
    output = Path(output)
    settings = task(task_id)
    train, forward, prototype, scaler, data, _ = inputs(state, settings["fold"])
    model, _ = initialize(scaler)
    optimizer = optimizer_for(model, settings)
    binding = binding_for(model, data, settings)
    ready = json.loads((output / "READY.json").read_text())
    public = json.loads((output / "PUBLIC_PREFIT_RECEIPT.json").read_text())
    if (
        ready["sources"] != sources()
        or ready["tasks"][task_id]["binding"] != binding
        or public["status"] != "PUBLIC_PREFIT_BYTES_VERIFIED"
        or public["sources"] != sources()
    ):
        raise ValueError("Published immutable prefit source/recipe/run identity required")
    with run_guard(output / task_id, binding) as folder:
        saved, p = load(folder, model, optimizer, binding)
        if (folder / "TERMINAL.json").exists():
            return json.loads((folder / "TERMINAL.json").read_text())
        step, prior, history = saved["step"], saved["elapsed_seconds"], saved["trainer_state"]
        began = time.monotonic()
        phase = "resume"
        attempt = step
        history["slices"].append(
            dict(
                resumed_update=step,
                checkpoint_SHA256=p["SHA256"],
                all_RNG_identity=tree_identity(_rng_state()),
            )
        )
        emit(dict(stage="EXACT_RESUME", task=task_id, step=step, checkpoint=p["SHA256"]))

        def persist():
            return save(
                folder,
                model,
                optimizer,
                binding,
                step=step,
                elapsed=prior + time.monotonic() - began,
                history=history,
            )

        def evaluate_due():
            if step in plan()["selection"]["checkpoints"] and step not in [
                r["step"] for r in history["validation"]
            ]:
                result = validation(model, forward, prototype, folder, step, history["controls"])
                register_validation(history, result)
                diagnostic = episode_diagnostic(
                    model,
                    train,
                    prototype,
                    mixing=settings["wallet_equal_mix"],
                    feature_batch_size=32,
                    snapshot_step=step,
                )
                history["training_diagnostics"].append(diagnostic)
                current = persist()
                if history["best"]["step"] == step:
                    _atomic_json(folder / "BEST.json", current)
                if step == 512:
                    _atomic_json(folder / "MATCHED512.json", current)
                emit(
                    dict(
                        stage="VALIDATION",
                        task=task_id,
                        step=step,
                        utility_excess=result["utility_excess"],
                        PnL=result["metrics"]["net_PnL"],
                        best_step=history["best"]["step"],
                        stale=history["stale_checks"],
                    )
                )
            # Repair a pointer if interrupted immediately after completed metrics.
            elif history["best"] is not None and history["best"]["step"] == step:
                _atomic_json(folder / "BEST.json", json.loads((folder / "latest.json").read_text()))
            if step == 512 and not (folder / "MATCHED512.json").exists():
                _atomic_json(
                    folder / "MATCHED512.json", json.loads((folder / "latest.json").read_text())
                )

        try:
            evaluate_due()
            while (
                step < 1024
                and history["status"] == "RUNNING"
                and time.monotonic() - began < seconds
            ):
                if prior + time.monotonic() - began >= 3600.0:
                    history["status"] = "CUMULATIVE_RESOURCE_CAP"
                    break
                attempt, phase = step + 1, "whole_path_gradient"
                model.train()
                optimizer.zero_grad(set_to_none=True)
                loss, _ = memory_bounded_gradients(
                    model,
                    train,
                    prototype,
                    feature_batch_size=32,
                    mixing=settings["wallet_equal_mix"],
                )
                if not np.isfinite(loss):
                    raise ValueError("Nonfinite own-path objective")
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
                    last_gradient_norm=float(norm),
                )
                phase = "atomic_checkpoint"
                persist()
                phase = "scheduled_development_evaluation"
                evaluate_due()
                retain(folder)
                if step == 1 or step % 32 == 0:
                    emit(
                        dict(
                            stage="TRAIN",
                            task=task_id,
                            step=step,
                            loss=loss,
                            elapsed=prior + time.monotonic() - began,
                        )
                    )
            if step == 1024 and history["status"] == "RUNNING":
                history["status"] = "UPDATE_CAP_NOT_CONVERGENCE"
        except Exception as error:
            failed = dict(
                type=type(error).__name__, message=str(error), phase=phase, attempted_update=attempt
            )
            saved, p = load(folder, model, optimizer, binding)
            step, history = saved["step"], saved["trainer_state"]
            history.update(status="STOP_NUMERICAL_OR_PATH_FAILURE", failure=failed)
            _atomic_json(folder / "FAILURE.json", failed)
        validate_moments(
            model, optimizer, step, binding["specification"]["algorithm"]["parameter_birth_steps"]
        )
        p = persist()
        retain(folder)
        result = dict(
            task_id=task_id,
            status=history["status"],
            completed_updates=step,
            actual_active_training_dates=settings["eligible_dates"],
            settings=settings,
            parameters=13699,
            latest=p,
            best=history["best"],
            validation=history["validation"],
            training_diagnostics=history["training_diagnostics"],
            slices=history["slices"],
            elapsed_seconds=p["elapsed_seconds"],
            failure=history.get("failure"),
            optimizer_all_parameter_ages=step,
            reserve_read=False,
            native_wallets=0,
        )
        _atomic_json(
            folder / ("TERMINAL.json" if history["status"] in DONE else "SLICE_RECEIPT.json"),
            result,
        )
        emit(dict(stage="SLICE_END", task=task_id, status=result["status"], updates=step))
        return result


def select(output):
    output = Path(output)
    rows = []
    for settings in plan()["actual_fit_tasks"]:
        row = json.loads((output / settings["task_id"] / "TERMINAL.json").read_text())
        if row["best"] is None or row["status"] == "STOP_NUMERICAL_OR_PATH_FAILURE":
            raise ValueError("All six completed admissible fit results required for selection")
        rows.append(row)
    candidates = []
    for name in plan()["candidate_settings"]:
        pairs = [r for r in rows if r["settings"]["candidate"] == name]
        scores = [r["best"]["utility_excess"] for r in pairs]
        candidates.append(
            dict(
                candidate=name,
                mean_utility_excess=float(np.mean(scores)),
                worst_utility_excess=min(scores),
                best_updates=[r["best"]["step"] for r in pairs],
                folds={r["settings"]["fold"]: r["best"] for r in pairs},
            )
        )
    top = max(r["mean_utility_excess"] for r in candidates)
    tied = [r for r in candidates if top - r["mean_utility_excess"] <= 1e-5]
    worst = max(r["worst_utility_excess"] for r in tied)
    selected = next(r for r in tied if worst - r["worst_utility_excess"] <= 1e-5)
    result = dict(
        status="SIX_FITS_COMPLETE_SELECTION_FIXED_RESERVE_NOT_READ",
        candidates=candidates,
        selected=selected,
        selected_settings=plan()["candidate_settings"][selected["candidate"]],
        later_full773_refit_steps=max(256, int(np.floor(np.median(selected["best_updates"])))),
        later_full773_refit="NOT_RUN",
        actual_fits=6,
        total_completed_updates=sum(r["completed_updates"] for r in rows),
        all_fit_results=rows,
        reserve_results_read=False,
        no_convergence_claim=True,
        no_promotion=True,
    )
    _atomic_json(output / "RESULT.json", result)
    return result
