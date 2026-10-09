"""Terminal-only inference bundles; two-terminal barrier for economic scoring."""

import hashlib
import json
import shutil
import subprocess
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import torch

from modules.temporal_expert_input.checkpoint import load_checkpoint
from modules.temporal_expert_input.gradient import predict_episode, request_gradient
from modules.temporal_short_expansion.adapter import compress, expand
from modules.temporal_short_expansion.model import E6
from modules.temporal_two_expert.checkpoint import _atomic_json, model_identity
from modules.temporal_two_expert.exact import sha

from .stage import ARMS, PROTOCOL, SUCCESS, initialize, inputs, sources

ADAPTER_COMMIT = "a596f9e5983692873b70f6737cac6ce853dee72f"
ADAPTER_SHA256 = "9e29ad31a3c795e531e556c2da2f04dfa30d2d71e8df74111731360fc4ca07b2"


def frozen_arm(state, output, arm):
    train, development, prototype, dataset, scaler = inputs(state, include_development=True)
    folder = Path(output) / arm
    terminal = json.loads((folder / "TERMINAL.json").read_text())
    binding = json.loads((folder / "RUN.json").read_text())
    pointer = json.loads((folder / "latest.json").read_text())
    if binding["specification"]["algorithm"]["versioned_sources"] != sources():
        raise ValueError("Frozen experiment sources changed")
    model, optimizer, _, _ = initialize(state, scaler)
    saved = load_checkpoint(folder, model, optimizer, binding, sources=sources)
    if saved["model_identity"] != terminal["model_identity"]:
        raise ValueError("Exact terminal model required")
    if terminal["status"] != SUCCESS or terminal["completed_stage_updates"] != 512:
        raise ValueError("Exact fixed512 successful terminal required")
    model.eval()
    return train, development, prototype, model, optimizer, folder, terminal, pointer


def export_native(state, output, arm, destination, producer_commit):
    destination = Path(destination)
    if destination.exists():
        raise FileExistsError("Immutable request bundle required")
    train, dev, _, model, _, folder, terminal, pointer = frozen_arm(state, output, arm)
    before = model_identity(model)
    rng = torch.get_rng_state().clone()
    assert len(dev) == 1 and len(dev[0].contexts) == 61
    episode = dev[0]
    with torch.no_grad():
        requests = predict_episode(model, episode, feature_batch_size=32).numpy()
    assert model_identity(model) == before and torch.equal(rng, torch.get_rng_state())
    allowed = model.contract["allowed_actions"]
    mask = episode.eligible & np.array([n in allowed for n in E6])[None]
    # Preserve availability release as a separate forced operation. This replay
    # pack currently has no admitted dev eligibility loss, so no conversion of
    # actual neural requests is necessary or allowed.
    if np.any(requests[~mask]):
        raise ValueError(
            "Actual frozen dev requests violate admitted mask; do not silently renormalize"
        )
    feature_clock = np.maximum(
        np.where(episode.windows.valid, episode.windows.available_us, 0).max((1, 2, 3)),
        episode.windows.completed_us[:, -1],
    ).astype(np.int64)
    feature_clock = np.maximum(feature_clock, episode.expert_input_available_us.max(1))
    maximum_label = max(int(e.label_available_us.max()) for e in train)
    maximum_scaler_clock = max(
        int(np.where(e.windows.valid, e.windows.available_us, 0).max()) for e in train
    )
    cutoff = train[0].split_cutoff_us
    assert maximum_label < cutoff and maximum_scaler_clock <= cutoff
    root = Path(__file__).resolve().parents[2]
    producer_name = str(Path(__file__).resolve().relative_to(root))
    if (
        subprocess.check_output(["git", "show", producer_commit + ":" + producer_name], cwd=root)
        != Path(__file__).read_bytes()
    ):
        raise ValueError("Published producer source required")
    destination.mkdir(parents=True)
    np.savez_compressed(
        destination / "REQUESTS.npz",
        decision_us=episode.windows.decision_us,
        symbol_order=np.array(model.base.contract["symbols"]),
        expert_order=np.array(E6),
        desired_expert_budget=requests.astype(np.float64),
        action_eligible=mask,
        feature_available_us=feature_clock,
        request_available_us=episode.windows.decision_us,
    )
    np.savez_compressed(
        destination / "CURRENT_EXPERT_INPUTS61.npz",
        decision_us=episode.windows.decision_us,
        symbol_order=np.array(model.base.contract["symbols"]),
        input_expert_order=np.array(model.contract["current_expert_input"]["names"]),
        expert_state=episode.expert_state,
        input_available_us=episode.expert_input_available_us,
        signed_targets=episode.expert_targets[:, (1, 4, 5)],
        expert_eligible=episode.eligible[:, (1, 4, 5)],
        target_available_us=episode.target_available_us[:, (1, 4, 5)],
        target_unit=np.array(0.3),
    )
    source_paths = {
        **sources(),
        **json.loads((folder / "RUN.json").read_text())["specification"]["sources"],
    }
    source_members = []
    for name, expected in source_paths.items():
        original = root / name
        assert sha(original) == expected
        member = "source/" + name
        path = destination / member
        path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(original, path)
        source_members.append(member)
    shutil.copyfile(folder / pointer["file"], destination / "MODEL_ADAM_RNG.pt")
    shutil.copyfile(Path(state) / "four-fit/SCALER.npz", destination / "SCALER.npz")
    _atomic_json(destination / "TRAINING_PLAN.json", PROTOCOL)
    for name in ("RUN.json", "TERMINAL.json", "latest.json"):
        shutil.copyfile(folder / name, destination / name)
    files = {
        str(p.relative_to(destination)): dict(bytes=p.stat().st_size, sha256=sha(p))
        for p in sorted(destination.rglob("*"))
        if p.is_file()
    }
    adapter = subprocess.check_output(
        [
            "git",
            "show",
            ADAPTER_COMMIT
            + ":research/recover-frozen-runner-20261009/EVALUATE_REQUESTS61_ADAPTER.json",
        ],
        cwd=root,
    )
    assert hashlib.sha256(adapter).hexdigest() == ADAPTER_SHA256
    manifest = dict(
        schema="SOURCE_HASHED_FROZEN_NATIVE61_REQUESTS_V1",
        arm_id="EXP_" + arm,
        objective_version=2,
        prediction_role="HISTORICAL_FROZEN_REPLAY_NOT_LIVE_PREDICTIONS",
        expert_order=list(E6),
        allowed_actions=allowed,
        uses_feedback_features=False,
        request_file="REQUESTS.npz",
        source_files=source_members,
        files=files,
        model_sha256=pointer["SHA256"],
        model_identity=before,
        scaler_sha256=sha(destination / "SCALER.npz"),
        training_plan_sha256=sha(destination / "TRAINING_PLAN.json"),
        producer_commit=producer_commit,
        training_cutoff_us=cutoff,
        maximum_training_label_available_us=maximum_label,
        maximum_scaler_input_available_us=maximum_scaler_clock,
        actual_fit_completed_UTC=datetime.fromtimestamp(
            (folder / "TERMINAL.json").stat().st_mtime, timezone.utc
        ).isoformat(),
        completion_timestamp_source="atomic_terminal_record_mtime_original_execution_environment",
        terminal_training_status=terminal["status"],
        completed_weighting_updates=terminal["completed_stage_updates"],
        cumulative_base_Adam_step=terminal["cumulative_Adam_step"],
        new_head_Adam_step=terminal["new_head_Adam_step"],
        parent_checkpoint_sha256=terminal["parent_checkpoint_SHA256"],
        native_adapter_commit=ADAPTER_COMMIT,
        native_adapter_contract_sha256=hashlib.sha256(adapter).hexdigest(),
        export_operation="terminal_eval_requests_only;zero_optimizer_updates;no_economic_score",
        private_mapper_coordinates=[0, 1, 2, 4, 5],
        public_slots_preserved=True,
        eligibility_release=(
            "forced release to CASH precedes discretionaryL1<=.1;"
            "not counted against discretionary turnover"
        ),
        native_execution_results=False,
        current_expert_input=model.contract["current_expert_input"],
        input_enabled=model.input_enabled,
        source_target_clocks_preserved=True,
        current_expert_input_file="CURRENT_EXPERT_INPUTS61.npz",
        maximum_training_expert_input_available_us=max(
            int(e.expert_input_available_us.max()) for e in train
        ),
    )
    _atomic_json(destination / "MANIFEST.json", manifest)
    return dict(
        arm=manifest["arm_id"],
        manifest_SHA256=sha(destination / "MANIFEST.json"),
        requests_SHA256=sha(destination / "REQUESTS.npz"),
        completed_updates=terminal["completed_stage_updates"],
    )


def score(state, output):
    output = Path(output)
    terminal = {arm: json.loads((output / arm / "TERMINAL.json").read_text()) for arm in ARMS}
    if any(
        t["status"] != SUCCESS
        or t["completed_stage_updates"] != 512
        or t["fixed_update_target"] != 512
        for t in terminal.values()
    ):
        raise ValueError("Both successful fixed512 terminals required before seen scoring")
    barrier = dict(
        schema="MATCHED_FIXED512_WEIGHTING_TWO_TERMINAL_BARRIER_V2",
        arms=terminal,
        rule="both last completed training snapshots frozen before seen economic scoring",
    )
    _atomic_json(output / "BOTH_TERMINAL.json", barrier)
    results, arrays = {}, {}
    for arm in ARMS:
        train, dev, prototype, model, optimizer, folder, t, pointer = frozen_arm(state, output, arm)
        identity, rng = model_identity(model), torch.get_rng_state().clone()
        last = t["last_diagnostic"]
        assert last["snapshot_step"] == 512 and last["model_identity"] == identity
        final_loss = last["trained_objective_summary"]["weighted_mean_loss"]
        norm = last["trained_objective_summary"]["gradient_norm"]
        assert identity == model_identity(model) and torch.equal(rng, torch.get_rng_state())
        wallets = []
        for i, episode in enumerate((*train, *dev)):
            with torch.no_grad():
                requests = predict_episode(model, episode, feature_batch_size=32).numpy()
            loss, _, report = request_gradient(requests, episode, prototype)
            targets, records = prototype.mapped_path(compress(requests), episode.internal.contexts)
            nav = report["nav"].detach().numpy()
            risk = report["risk_events"]
            wallets.append(
                dict(
                    wallet_id=episode.wallet_id,
                    role=episode.role,
                    decisions=len(requests),
                    capital=10000.0,
                    loss=loss,
                    net_PnL=float(report["net_PnL"].detach()),
                    maximum_drawdown=float(np.max(1 - nav / np.maximum.accumulate(nav))),
                    fees=float(report["fees"].detach()),
                    spread=float(report["spread"].detach()),
                    slippage=float(report["slippage"].detach()),
                    funding=float(report["funding"].detach()),
                    charged_reduction_cost=float(report["charged_reduction_cost"].detach()),
                    risk_event_count=len(risk),
                    paid_terminal_cash=report["terminal_cash_realized"],
                    maximum_allocated_gross=max(r["allocated_leg_gross"] for r in records),
                    maximum_allocated_asset_gross=max(
                        float(r["allocated_underlier_gross"].max()) for r in records
                    ),
                    request_mean=requests.mean(0).tolist(),
                    status=report["status"],
                )
            )
            key = arm + "__" + str(i)
            arrays[key + "__decision_us"] = episode.windows.decision_us
            arrays[key + "__desired"] = requests
            arrays[key + "__mapped_budget"] = expand(np.stack([r["budget"] for r in records]))
            arrays[key + "__target"] = targets
            arrays[key + "__nav"] = nav
        results[arm] = dict(
            terminal=t,
            pointer=pointer,
            parameter_count=model.parameter_count,
            final_train_loss=final_loss,
            final_train_gradient_norm=norm,
            wallets=wallets,
        )
    np.savez_compressed(output / "SIMULATED_PATHS.npz", **arrays)
    with zipfile.ZipFile(output / "TERMINAL_MODELS_ADAM_RNG.zip", "w", zipfile.ZIP_DEFLATED) as z:
        for arm in ARMS:
            folder = output / arm
            p = json.loads((folder / "latest.json").read_text())
            for name in ("RUN.json", "TERMINAL.json", "latest.json", p["file"]):
                z.write(folder / name, arm + "/" + name)
        for name in ("READY.json", "BOTH_TERMINAL.json"):
            z.write(output / name, name)
        z.write(Path(state) / "four-fit/SCALER.npz", "SCALER.npz")
    result = dict(
        schema="MATCHED_FIXED512_EPISODE_WEIGHTING_RESULT_V2",
        objective_version=2,
        protocol=PROTOCOL,
        arms=results,
        sources=sources(),
        seen_development=True,
        native_wallets=0,
        architecture_searches=0,
        outcome_oversampling=False,
        checkpoint_selection="512th_completed_training_step;no_seen_selection",
        all_previous_four_arm_runs_unchanged=True,
    )
    _atomic_json(output / "RESULT.json", result)
    return result
