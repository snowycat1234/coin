"""All-terminal barrier, seen surrogate scoring and frozen native handoff paths."""

import json
import shutil
import zipfile
from pathlib import Path

import numpy as np
import torch

from modules.temporal_risk_proxy_v2.proxy import (
    BoundaryPlan,
    BoundaryStop,
    request_loss_and_gradient_v2,
)
from modules.temporal_two_expert.checkpoint import (
    _atomic_json,
    load_checkpoint,
    make_optimizer,
    model_identity,
)
from modules.temporal_two_expert.comparison import ARMS, PROTOCOL
from modules.temporal_two_expert.exact import sha
from modules.temporal_two_expert.inputs import array_digest
from modules.temporal_two_expert.model import E5_EXPERT_ORDER, predict_windows

from .stage import PROTOCOL_V2, load_inputs, original_model, stage_sources


def freeze_and_export(state, output):
    output = Path(output)
    if (output / "RESULT.json").exists():
        return json.loads((output / "RESULT.json").read_text())
    train, dev, prototype, dataset, scaler = load_inputs(state)
    terminal, pointers = {}, {}
    for family, cash in ARMS:
        name = family + ("_WITH_CASH" if cash else "_NO_CASH")
        folder = output / name
        terminal[name] = json.loads((folder / "TERMINAL.json").read_text())
        pointers[name] = json.loads((folder / "latest.json").read_text())
        assert terminal[name]["model_identity"] == pointers[name]["model_identity"]
        assert pointers[name]["step"] == terminal[name]["cumulative_Adam_step"]
    barrier = dict(
        status="ALL_FOUR_V2_TERMINAL_BEFORE_SEEN_SCORING",
        objective_version=2,
        terminal=terminal,
        terminal_pointers=pointers,
        scaler_identity=scaler.identity,
    )
    _atomic_json(output / "ALL_FOUR_TERMINAL.json", barrier)
    arrays, arms, handoff = {}, {}, []
    pack = output / "terminal-pack"
    pack.mkdir(exist_ok=True)
    for family, cash in ARMS:
        name = family + ("_WITH_CASH" if cash else "_NO_CASH")
        folder = output / name
        model = original_model(scaler, family, cash)
        binding = json.loads((folder / "RUN.json").read_text())
        if binding["specification"]["algorithm"]["versioned_sources"] != stage_sources():
            raise ValueError("Versioned objective/runtime source changed after fitting")
        loaded = load_checkpoint(folder, model, make_optimizer(model), binding)
        model.eval()
        identity = model_identity(model)
        assert identity == terminal[name]["model_identity"]
        wallets = []
        for episode in (*train, *dev):
            with torch.no_grad():
                request = predict_windows(
                    model, episode.windows, feature_batch_size=PROTOCOL["feature_batch_size"]
                ).numpy()
            targets, records = prototype.mapped_path(request, episode.contexts)
            key = name + "__" + episode.wallet_id
            for field, value in dict(
                decision_us=episode.windows.decision_us,
                requests_E5=request,
                net_targets=targets,
                mapped_budget_E5=np.array([r["budget"] for r in records]),
            ).items():
                arrays[key + "__" + field] = value
            handoff.append(
                dict(
                    key=key,
                    arm=name,
                    model_identity=identity,
                    terminal_checkpoint_SHA256=pointers[name]["SHA256"],
                    parent_checkpoint_SHA256=terminal[name]["parent_checkpoint_SHA256"],
                    wallet_id=episode.wallet_id,
                    role=episode.role,
                    decisions=len(episode.contexts),
                    start_us=episode.start_us,
                    end_us=episode.end_us,
                    split_cutoff_us=episode.split_cutoff_us,
                    request_array_digest=array_digest(request),
                    target_array_digest=array_digest(targets),
                    context_identity=episode.identity,
                    forced_terminal_decision_us=int(episode.windows.decision_us[-1]),
                    expert_order=list(E5_EXPERT_ORDER),
                    inactive_slots=[2, 3],
                    symbol_order=list(model.contract["symbols"]),
                )
            )
            detail = dict(
                wallet_id=episode.wallet_id,
                role=episode.role,
                decisions=len(episode.contexts),
                initial_capital=10000.0,
                request_mean=request.mean(0).tolist(),
                maximum_allocated_leg_gross=max(r["allocated_leg_gross"] for r in records),
                maximum_allocated_asset_gross=max(
                    float(np.max(r["allocated_underlier_gross"])) for r in records
                ),
            )
            try:
                loss, _, report = request_loss_and_gradient_v2(
                    request,
                    episode,
                    prototype,
                    plan=BoundaryPlan.full_fill_diagnostic(len(episode.contexts)),
                )
                nav, ret = report["nav"].detach().numpy(), report["net_return"].detach().numpy()
                detail.update(
                    loss=loss,
                    status=report["status"],
                    paid_terminal_cash_realized=report["terminal_cash_realized"],
                    maximum_drawdown=float(np.max(1 - nav / np.maximum.accumulate(nav))),
                    annualized_daily_surrogate_vol=float(np.std(ret, ddof=1) * np.sqrt(365)),
                    risk_event_count=len(report["risk_events"]),
                    risk_events=report["risk_events"],
                    plan_identity=report["plan_identity"],
                )
                detail.update(
                    {
                        k: float(report[k].detach())
                        for k in (
                            "net_PnL",
                            "fees",
                            "spread",
                            "slippage",
                            "funding",
                            "charged_reduction_cost",
                            "utility_sum",
                        )
                    }
                )
                for field in ("nav", "net_return", "quantity", "boundary_held_quantity"):
                    arrays[key + "__" + field] = report[field].detach().numpy()
            except BoundaryStop as error:
                detail.update(
                    loss=None,
                    net_PnL=None,
                    status=error.reason,
                    day_index=error.day_index,
                    equity=error.equity,
                    quantity=error.quantity.tolist(),
                    mark=error.mark.tolist(),
                    paid_terminal_cash_realized=False,
                    full_path_result_unavailable=True,
                )
            wallets.append(detail)
        assert model_identity(model) == identity
        train_rows = [w for w in wallets if w["role"] == "TRAIN"]
        final_loss = (
            None
            if any(w["loss"] is None for w in train_rows)
            else sum(w["loss"] * w["decisions"] for w in train_rows)
            / sum(w["decisions"] for w in train_rows)
        )
        arms[name] = dict(
            parameter_count=model.parameter_count,
            terminal=terminal[name],
            final_deterministic_train_loss=final_loss,
            history=loaded["trainer_state"]["history"],
            wallets=wallets,
        )
        dest = pack / name
        dest.mkdir(exist_ok=True)
        for file in ("RUN.json", "latest.json", "TERMINAL.json", pointers[name]["file"]):
            shutil.copyfile(folder / file, dest / file)
    request_fields = {
        k: v
        for k, v in arrays.items()
        if k.endswith(("__decision_us", "__requests_E5", "__net_targets", "__mapped_budget_E5"))
    }
    np.savez_compressed(output / "FROZEN_DAILY_REQUEST_PATHS.npz", **request_fields)
    np.savez_compressed(output / "SIMULATED_PATHS.npz", **arrays)
    request_file = output / "FROZEN_DAILY_REQUEST_PATHS.npz"
    _atomic_json(
        output / "NATIVE_HANDOFF.json",
        dict(
            schema="FROZEN_V2_DAILY_REQUEST_NATIVE_HANDOFF_V1",
            objective_version=2,
            classification="FROZEN_EXOGENOUS_DAILY_REQUESTS_FOR_SEPARATE_NATIVE_VALIDATION",
            file=request_file.name,
            SHA256=sha(request_file),
            paths=handoff,
            feature_contract="same_CORE5_real64x24_values_and24_masks;no_wallet_features",
            mapper="unchanged original mapped_path;forced common paid terminal per real episode",
            wallets_are_independent=True,
            concatenate_wallets=False,
            native_execution_results=False,
            events_or_minute_tapes_downloaded=0,
        ),
    )
    result = dict(
        schema="TEMPORAL_CHARGED_SURROGATE_V2_RESULT_V1",
        objective_version=2,
        status="ALL_FOUR_V2_TERMINAL_SEEN_SCORED",
        arms=arms,
        protocol=PROTOCOL_V2,
        resumed_arms=4,
        clean_new_comparison=False,
        original_runs_unchanged=True,
        dataset=dataset,
        scaler_identity=scaler.identity,
        source_identity=stage_sources(),
        development_classification="SEEN_MAY_JUNE2024_CONDITIONAL_DAILY_SURROGATE_NOT_NATIVE_NOT_OOS",
        native_wallets=0,
        brute_force_searches=0,
        scoring_barrier=barrier,
    )
    _atomic_json(output / "RESULT.json", result)
    _atomic_json(
        output / "DEVELOPMENT_RESULTS.json",
        dict(
            objective_version=2,
            checkpoint_selection="terminal_weights_frozen_before_seen_scores",
            classification=result["development_classification"],
            arms={
                name: dict(
                    training=arm["terminal"],
                    development=[w for w in arm["wallets"] if w["role"] == "SEEN_VALIDATION"],
                )
                for name, arm in arms.items()
            },
        ),
    )
    for file in (
        "RUN.json",
        "ALL_FOUR_TERMINAL.json",
        "NATIVE_HANDOFF.json",
        "DEVELOPMENT_RESULTS.json",
    ):
        shutil.copyfile(output / file, pack / file)
    for file in ("SCALER.npz", "SCALER.json"):
        shutil.copyfile(Path(state) / "four-fit" / file, pack / file)
    archive = output / "TERMINAL_MODELS_ADAM_RNG.zip"
    with zipfile.ZipFile(archive, "x", compression=zipfile.ZIP_DEFLATED) as z:
        for file in sorted(pack.rglob("*")):
            if file.is_file():
                z.write(file, str(file.relative_to(pack)))
    with zipfile.ZipFile(archive) as z:
        assert z.testzip() is None
    print(
        json.dumps(
            dict(
                stage="v2_scored_and_exported",
                status=result["status"],
                request_file_SHA256=sha(request_file),
            )
        ),
        flush=True,
    )
    return result
