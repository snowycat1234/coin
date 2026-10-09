"""Frozen forward requests and paired full-path daily surrogate controls."""

import json
import os
import shutil
import subprocess
import uuid
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import torch

from modules.temporal_expert_input.checkpoint import load_checkpoint
from modules.temporal_expert_input.gradient import predict_episode, request_gradient
from modules.temporal_prequential_transfer.model import initialize
from modules.temporal_short_expansion.adapter import compress, expand
from modules.temporal_short_expansion.model import E6
from modules.temporal_two_expert.checkpoint import _atomic_json, _sync_directory, model_identity
from modules.temporal_two_expert.exact import sha
from modules.temporal_two_expert.inputs import CORE5

from .protocol import CONTROLS, FOLDS, PROTOCOL, sources
from .stage import SUCCESS, binding_for, load_fold, validate_terminal


def export_fold(state, output, fold, destination, producer_commit):
    final = Path(destination)
    if final.exists():
        raise FileExistsError("Immutable forward artifact required")
    final.parent.mkdir(parents=True, exist_ok=True)
    destination = final.parent / ("." + final.name + ".staging-" + uuid.uuid4().hex)
    train, forward, prototype, scaler, data, receipt = load_fold(state, fold)
    model, optimizer = initialize(scaler)
    binding = binding_for(model, data)
    folder = Path(output) / fold
    terminal = json.loads((folder / "TERMINAL.json").read_text())
    if terminal["status"] != SUCCESS or terminal["completed_updates"] != 512:
        raise ValueError("Only exact512 terminal may generate a forward path")
    saved = load_checkpoint(folder, model, optimizer, binding, sources=sources)
    validate_terminal(terminal, saved)
    repo = Path(__file__).resolve().parents[2]
    for path, expected in sources().items():
        published = subprocess.check_output(["git", "show", producer_commit + ":" + path], cwd=repo)
        if published != (repo / path).read_bytes() or sha(repo / path) != expected:
            raise ValueError("Published immutable producer source required")
    model.eval()
    identity, rng = model_identity(model), torch.get_rng_state().clone()
    with torch.no_grad():
        requests = predict_episode(model, forward, feature_batch_size=32).numpy()
    assert identity == model_identity(model) and torch.equal(rng, torch.get_rng_state())
    destination.mkdir(parents=True)
    feature_clock = np.maximum(
        np.where(forward.windows.valid, forward.windows.available_us, 0).max((1, 2, 3)),
        forward.expert_input_available_us.max(1),
    ).astype(np.int64)
    np.savez_compressed(
        destination / "REQUESTS.npz",
        decision_us=forward.windows.decision_us,
        symbol_order=np.array(CORE5),
        expert_order=np.array(E6),
        desired_expert_budget=requests,
        action_eligible=forward.eligible,
        feature_available_us=feature_clock,
        request_available_us=forward.windows.decision_us,
    )
    np.savez_compressed(
        destination / "SCALER.npz", mean=scaler.mean, scale=scaler.scale, count=scaler.count
    )
    np.savez_compressed(
        destination / "CURRENT_CONTEXT63.npz",
        decision_us=forward.windows.decision_us,
        symbol_order=np.array(CORE5),
        expert_order=np.array(E6),
        expert_targets=forward.expert_targets,
        expert_eligible=forward.eligible,
        target_available_us=forward.target_available_us,
        past_returns30=np.stack([c.past_returns30 for c in forward.contexts]),
        expert_state=forward.expert_state,
        expert_input_available_us=forward.expert_input_available_us,
        surrogate_prices=forward.prices,
        surrogate_funding_coeff=forward.funding_coeff,
        outcome_available_us=forward.label_available_us,
        initial_wallet_cash=np.array(10000.0),
        initial_previous_quote_none=np.array(True),
        initial_quote_capacity_zero=np.array(True),
    )
    _atomic_json(
        destination / "SCALER.json", dict(identity=scaler.identity, provenance=scaler.provenance)
    )
    pointer = json.loads((folder / "latest.json").read_text())
    shutil.copyfile(folder / pointer["file"], destination / "MODEL_ADAM_RNG.pt")
    for name in ("RUN.json", "TERMINAL.json"):
        shutil.copyfile(folder / name, destination / name)
    records, arrays = {}, {}
    for name, request in (
        ("FRESH_GRU", requests),
        *((n, np.tile(v, (63, 1))) for n, v in CONTROLS.items()),
    ):
        # Same forced-availability release, mapper, bankroll, costs and terminal
        # close for every policy. A constant control can request an unavailable
        # action; the frozen mapper performs its documented release to CASH.
        loss, _, report = request_gradient(request, forward, prototype)
        targets, mapped = prototype.mapped_path(compress(request), forward.internal.contexts)
        nav = report["nav"].detach().numpy()
        records[name] = dict(
            capital=10000.0,
            decisions=63,
            active_intervals=62,
            mean_loss=loss,
            utility_sum=float(report["utility_sum"].detach()),
            net_PnL=float(report["net_PnL"].detach()),
            maximum_drawdown=float(np.max(1 - nav / np.maximum.accumulate(nav))),
            fees=float(report["fees"].detach()),
            spread=float(report["spread"].detach()),
            slippage=float(report["slippage"].detach()),
            funding=float(report["funding"].detach()),
            charged_reduction_cost=float(report["charged_reduction_cost"].detach()),
            risk_events=len(report["risk_events"]),
            paid_terminal_cash=report["terminal_cash_realized"],
            request_mean=request.mean(0).tolist(),
            maximum_allocated_gross=max(r["allocated_leg_gross"] for r in mapped),
            maximum_allocated_asset_gross=max(
                float(r["allocated_underlier_gross"].max()) for r in mapped
            ),
            status="APPROXIMATE_DAILY_SURROGATE_NOT_NATIVE",
        )
        arrays[name + "_requests"], arrays[name + "_nav"], arrays[name + "_targets"] = (
            request,
            nav,
            targets,
        )
        arrays[name + "_budget"] = expand(np.stack([r["budget"] for r in mapped]))
    np.savez_compressed(
        destination / "PAIRED_PATHS.npz", decision_us=forward.windows.decision_us, **arrays
    )
    learned, control = records["FRESH_GRU"], records["VOL50_CS50"]
    score = dict(
        fold=fold,
        classification=PROTOCOL["classification"],
        evidence=PROTOCOL["evidence"],
        training=receipt,
        policies=records,
        primary_control="VOL50_CS50",
        primary_utility_excess=learned["utility_sum"] - control["utility_sum"],
        primary_PnL_excess=learned["net_PnL"] - control["net_PnL"],
        model_identity=identity,
        checkpoint_sha256=pointer["SHA256"],
        actual_fit_completed_UTC=datetime.fromtimestamp(
            (folder / "TERMINAL.json").stat().st_mtime, timezone.utc
        ).isoformat(),
        inference_Torch_RNG_unchanged=True,
        terminal_frozen_before_forward_economic_score=True,
        optimizer_updates_during_forward=0,
        native_wallets=0,
        provider_downloads=0,
        native_fresh_startup="CASH10000;previous_quote=None;initial_capacity=0;no_external_previous_quote",
    )
    _atomic_json(destination / "RESULT.json", score)
    _atomic_json(
        destination / "MANIFEST.json",
        dict(
            schema="FROZEN_PREQUENTIAL_FORWARD63_SURROGATE_V1",
            status="COMPLETE",
            fold=fold,
            producer_commit=producer_commit,
            versioned_sources=sources(),
            model_identity=identity,
            completed_updates=512,
            scaler_identity=scaler.identity,
            prediction_role="HISTORICAL_FROZEN_REPLAY_NOT_LIVE",
            files={
                p.name: dict(bytes=p.stat().st_size, SHA256=sha(p))
                for p in sorted(destination.iterdir())
                if p.is_file()
            },
            terminal_close=receipt["forward"],
            native_results=False,
        ),
    )
    os.replace(destination, final)
    _sync_directory(final.parent)
    verify_bundle(final)
    return score


def verify_bundle(path):
    path = Path(path)
    manifest = json.loads((path / "MANIFEST.json").read_text())
    terminal = json.loads((path / "TERMINAL.json").read_text())
    score = json.loads((path / "RESULT.json").read_text())
    snapshot = torch.load(path / "MODEL_ADAM_RNG.pt", weights_only=True, map_location="cpu")
    if (
        path.name not in FOLDS
        or manifest["fold"] != path.name
        or terminal["fold"] != path.name
        or score["fold"] != path.name
        or manifest["status"] != "COMPLETE"
        or manifest["versioned_sources"] != sources()
        or terminal["status"] != SUCCESS
        or terminal["completed_updates"] != 512
        or manifest["model_identity"] != terminal["model_identity"]
        or score["model_identity"] != terminal["model_identity"]
        or score["checkpoint_sha256"] != sha(path / "MODEL_ADAM_RNG.pt")
        or snapshot["step"] != 512
        or snapshot["model_identity"] != manifest["model_identity"]
        or len(snapshot["optimizer"]["state"]) != 13
        or any(float(v["step"]) != 512 for v in snapshot["optimizer"]["state"].values())
    ):
        raise ValueError("Complete exact512 source-bound frozen bundle required")
    for name, entry in manifest["files"].items():
        file = (path / name).resolve()
        if not file.is_relative_to(path.resolve()) or sha(file) != entry["SHA256"]:
            raise ValueError("Frozen forward bundle bytes changed")
    return score


def aggregate(destination):
    destination = Path(destination)
    records, failures = [], {}
    for path in sorted(destination.glob("FOLD_*")):
        try:
            records.append(verify_bundle(path))
        except Exception as error:
            failures[path.name] = dict(type=type(error).__name__, message=str(error))
    repo = Path(__file__).resolve().parents[2]
    prior_path = "research/temporal-prequential-transfer-20261009/RESULT.json"
    prior_bytes = subprocess.check_output(
        ["git", "show", PROTOCOL["prior_result_commit"] + ":" + prior_path], cwd=repo
    )
    if prior_bytes != (repo / prior_path).read_bytes():
        raise ValueError("All three original frozen fold results must be retained unchanged")
    prior = json.loads(prior_bytes)
    records = [*prior["folds"], *records]
    excess = [r["primary_utility_excess"] for r in records]
    result = dict(
        status="ALL_FOUR_COMPLETE" if len(records) == 4 else "PARTIAL_FOUR_FOLD_RESEARCH",
        completed_folds=len(records),
        rejected_incomplete_or_changed_bundles=failures,
        folds=records,
        classification=PROTOCOL["classification"],
        evidence=PROTOCOL["evidence"],
        mean_block_utility_excess=float(np.mean(excess)) if excess else None,
        worst_block_utility_excess=min(excess) if excess else None,
        screen_pass=bool(len(records) == 4 and np.mean(excess) > 0 and min(excess) >= 0),
        original_three_screen_pass=prior["screen_pass"],
        original_three_worst_excess=prior["worst_block_utility_excess"],
        all_original_fold_bytes_retained=True,
        new_fold_chosen_by_calendar_and_coverage=True,
        no_pristine_project_OOS_claim=True,
        independent_bankrolls_not_summed=True,
        no_APR_or_unseen_claim=True,
    )
    _atomic_json(destination / "RESULT.json", result)
    return result
