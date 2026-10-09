"""Terminal-only native61 handoff followed by one seen-development score."""

import hashlib
import json
import os
import shutil
import subprocess
import uuid
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import torch

from modules.temporal_episode_weighting_v2.export import ADAPTER_COMMIT, ADAPTER_SHA256
from modules.temporal_expert_input.gradient import predict_episode, request_gradient
from modules.temporal_short_expansion.adapter import compress, expand
from modules.temporal_short_expansion.model import E6
from modules.temporal_two_expert.checkpoint import (
    _atomic_json,
    _rng_state,
    _sync_directory,
    model_identity,
)
from modules.temporal_two_expert.exact import sha

from .stage import ARM, COMPARATOR_COMMIT, PROTOCOL, frozen_state, sources, tree_identity


def gate_statistics(requests):
    """Invert the unchanged three-sigmoid output equations, never fit labels."""
    request = np.asarray(requests)
    s = 1 - request[:, 0]
    pair = request[:, 1] + request[:, 4]
    if np.any(s <= 0) or np.any(pair <= 0):
        raise ValueError("Nonzero sigmoid denominators required for gate interpretation")
    values = {"s": s, "w": request[:, 4] / pair, "r": request[:, 5] / s}
    return {
        key: dict(
            mean=float(value.mean()),
            minimum=float(value.min()),
            maximum=float(value.max()),
            fraction_gt99=float((value > 0.99).mean()),
            fraction_lt01=float((value < 0.01).mean()),
            fraction_derivative_lt001=float((value * (1 - value) < 0.001).mean()),
        )
        for key, value in values.items()
    }


def feature_clock(episode):
    return np.maximum.reduce(
        [
            np.where(episode.windows.valid, episode.windows.available_us, 0).max((1, 2, 3)),
            episode.windows.completed_us[:, -1],
            episode.expert_input_available_us.max(1),
        ]
    ).astype(np.int64)


def validate_native_bundle(bundle, model, saved, terminal, episode):
    """Validate the full source/model/clock handoff before any seen economics."""
    bundle = Path(bundle)
    manifest = json.loads((bundle / "MANIFEST.json").read_text())
    expected_sources = {**sources(), **saved["binding"]["specification"]["sources"]}
    members = {"source/" + name: expected for name, expected in expected_sources.items()}
    required = {
        "REQUESTS.npz",
        "CURRENT_EXPERT_INPUTS61.npz",
        "MODEL_ADAM_RNG.pt",
        "SCALER.npz",
        "TRAINING_PLAN.json",
        "RUN.json",
        "TERMINAL.json",
        "latest.json",
        *members,
    }
    expected_fields = dict(
        schema="SOURCE_HASHED_FROZEN_NATIVE61_REQUESTS_V1",
        arm_id="EXP_" + ARM,
        model_sha256=saved["checkpoint_SHA256"],
        model_identity=saved["model_identity"],
        expert_order=list(E6),
        allowed_actions=model.contract["allowed_actions"],
        objective_version=2,
        completed_initialization_updates=512,
        initial_step=0,
        cumulative_base_Adam_step=512,
        new_head_Adam_step=512,
        terminal_training_status=terminal["status"],
        uses_feedback_features=False,
        native_execution_results=False,
        request_file="REQUESTS.npz",
        current_expert_input_file="CURRENT_EXPERT_INPUTS61.npz",
        data_role="SEEN_DEVELOPMENT_INITIALIZATION_ABLATION_NOT_OOS",
        native_adapter_commit=ADAPTER_COMMIT,
        native_adapter_contract_sha256=ADAPTER_SHA256,
    )
    if any(manifest.get(k) != v for k, v in expected_fields.items()):
        raise ValueError("Exact fixed512 native export manifest required before seen score")
    if (
        set(manifest.get("source_files", [])) != set(members)
        or set(manifest.get("files", {})) != required
    ):
        raise ValueError("Complete model/scaler/source/native request bundle required")
    for name in required:
        path = bundle / name
        receipt = manifest["files"][name]
        if not path.is_file() or receipt != dict(bytes=path.stat().st_size, sha256=sha(path)):
            raise ValueError("Exact manifest-listed native file bytes required: " + name)
    if any(sha(bundle / name) != expected for name, expected in members.items()):
        raise ValueError("Exact bound native source closure required")
    if sha(bundle / "MODEL_ADAM_RNG.pt") != saved["checkpoint_SHA256"]:
        raise ValueError("Exact frozen checkpoint bytes required")
    for name, expected in [
        ("RUN.json", saved["binding"]),
        ("TERMINAL.json", terminal),
        ("TRAINING_PLAN.json", PROTOCOL),
    ]:
        if json.loads((bundle / name).read_text()) != expected:
            raise ValueError("Exact frozen native run/terminal/protocol required")
    pointer = json.loads((bundle / "latest.json").read_text())
    if (pointer["step"], pointer["SHA256"], pointer["model_identity"], pointer["run_id"]) != (
        512,
        saved["checkpoint_SHA256"],
        saved["model_identity"],
        saved["binding"]["run_id"],
    ):
        raise ValueError("Exact terminal512 native pointer required")
    if manifest["scaler_sha256"] != sha(bundle / "SCALER.npz") or (
        manifest["training_plan_sha256"] != sha(bundle / "TRAINING_PLAN.json")
    ):
        raise ValueError("Exact native scaler/protocol hash required")
    with np.load(bundle / "SCALER.npz", allow_pickle=False) as z:
        for name, actual in [
            ("mean", model.base.mean),
            ("scale", model.base.scale),
            ("count", model.base.normalization_count),
        ]:
            np.testing.assert_array_equal(z[name], actual.detach().numpy())
    mask = episode.eligible & np.array([n in model.contract["allowed_actions"] for n in E6])
    with np.load(bundle / "REQUESTS.npz", allow_pickle=False) as z:
        fields = dict(
            decision_us=episode.windows.decision_us,
            symbol_order=np.array(model.base.contract["symbols"]),
            expert_order=np.array(E6),
            action_eligible=mask,
            feature_available_us=feature_clock(episode),
            request_available_us=episode.windows.decision_us,
        )
        if set(z.files) != {*fields, "desired_expert_budget"}:
            raise ValueError("Exact seven-field native requests schema required")
        for name, expected in fields.items():
            np.testing.assert_array_equal(z[name], expected)
        request = z["desired_expert_budget"]
        if (
            request.shape != mask.shape
            or not np.isfinite(request).all()
            or (
                np.any(request < 0)
                or np.any(request[~mask])
                or np.any(request[:, 2:4])
                or not np.allclose(request.sum(1), 1, rtol=0, atol=1e-12)
                or np.any(z["feature_available_us"] > z["decision_us"])
            )
        ):
            raise ValueError("Causal actual native requests must preserve simplex and masks")
    with np.load(bundle / "CURRENT_EXPERT_INPUTS61.npz", allow_pickle=False) as z:
        fields = dict(
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
        if set(z.files) != set(fields):
            raise ValueError("Exact native current expert input schema required")
        for name, expected in fields.items():
            np.testing.assert_array_equal(z[name], expected)
    return manifest


def export_native(state, output, destination, producer_commit):
    destination = Path(destination)
    if destination.exists():
        raise FileExistsError("Immutable native request destination required")
    train, development, _, model, _, folder, saved, terminal = frozen_state(state, output)
    model.eval()
    identity, rng = model_identity(model), tree_identity(_rng_state())
    if len(development) != 1 or len(development[0].contexts) != 61:
        raise ValueError("Original61 seen-development decisions required")
    episode = development[0]
    with torch.no_grad():
        requests = predict_episode(model, episode, feature_batch_size=32).numpy()
    if identity != model_identity(model) or rng != tree_identity(_rng_state()):
        raise ValueError("Frozen inference changed model/RNG")
    mask = episode.eligible & np.array([name in model.contract["allowed_actions"] for name in E6])
    if np.any(requests[~mask]) or np.any(requests[:, 2:4]):
        raise ValueError("Preserve actual requests; never silently renormalize")
    root = Path(__file__).resolve().parents[2]
    source_paths = {**sources(), **saved["binding"]["specification"]["sources"]}
    for name, expected in source_paths.items():
        if (
            sha(root / name) != expected
            or subprocess.check_output(["git", "show", producer_commit + ":" + name], cwd=root)
            != (root / name).read_bytes()
        ):
            raise ValueError("Exact publicly frozen producer source required")
    clock = feature_clock(episode)
    if np.any(clock > episode.windows.decision_us):
        raise ValueError("Causal published-proxy feature clocks required")
    staging = destination.parent / ("." + destination.name + ".staging-" + uuid.uuid4().hex)
    staging.mkdir(parents=True)
    np.savez_compressed(
        staging / "REQUESTS.npz",
        decision_us=episode.windows.decision_us,
        symbol_order=np.array(model.base.contract["symbols"]),
        expert_order=np.array(E6),
        desired_expert_budget=requests,
        action_eligible=mask,
        feature_available_us=clock,
        request_available_us=episode.windows.decision_us,
    )
    np.savez_compressed(
        staging / "CURRENT_EXPERT_INPUTS61.npz",
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
    members = []
    for name in source_paths:
        target = staging / "source" / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(root / name, target)
        members.append(str(target.relative_to(staging)))
    pointer = json.loads((folder / "latest.json").read_text())
    shutil.copyfile(folder / pointer["file"], staging / "MODEL_ADAM_RNG.pt")
    # Keep the original compressed scaler bytes, whose numeric prefix refit was verified.
    shutil.copyfile(Path(state) / "four-fit/SCALER.npz", staging / "SCALER.npz")
    _atomic_json(staging / "TRAINING_PLAN.json", PROTOCOL)
    for name in ("RUN.json", "TERMINAL.json", "latest.json"):
        shutil.copyfile(folder / name, staging / name)
    adapter = subprocess.check_output(
        [
            "git",
            "show",
            ADAPTER_COMMIT
            + ":research/recover-frozen-runner-20261009/EVALUATE_REQUESTS61_ADAPTER.json",
        ],
        cwd=root,
    )
    if hashlib.sha256(adapter).hexdigest() != ADAPTER_SHA256:
        raise ValueError("Existing corrected native61 execution adapter required")
    manifest = dict(
        schema="SOURCE_HASHED_FROZEN_NATIVE61_REQUESTS_V1",
        arm_id="EXP_" + ARM,
        objective_version=2,
        prediction_role="HISTORICAL_FROZEN_REPLAY_NOT_LIVE_PREDICTIONS",
        expert_order=list(E6),
        allowed_actions=model.contract["allowed_actions"],
        uses_feedback_features=False,
        request_file="REQUESTS.npz",
        source_files=members,
        files={
            str(p.relative_to(staging)): dict(bytes=p.stat().st_size, sha256=sha(p))
            for p in sorted(staging.rglob("*"))
            if p.is_file()
        },
        model_sha256=saved["checkpoint_SHA256"],
        model_identity=identity,
        scaler_sha256=sha(staging / "SCALER.npz"),
        training_plan_sha256=sha(staging / "TRAINING_PLAN.json"),
        producer_commit=producer_commit,
        training_cutoff_us=train[0].split_cutoff_us,
        maximum_training_label_available_us=max(int(e.label_available_us.max()) for e in train),
        maximum_scaler_input_available_us=max(
            int(np.where(e.windows.valid, e.windows.available_us, 0).max()) for e in train
        ),
        actual_fit_completed_UTC=datetime.fromtimestamp(
            (folder / "TERMINAL.json").stat().st_mtime, timezone.utc
        ).isoformat(),
        completion_timestamp_source="atomic_terminal_record_mtime_original_execution_environment",
        terminal_training_status=terminal["status"],
        completed_initialization_updates=512,
        cumulative_base_Adam_step=512,
        new_head_Adam_step=512,
        initial_step=0,
        initialization_regime="same_three_fresh_folds_recipe;no_warm_model_or_Adam_loaded_into_fit",
        comparator_commit=COMPARATOR_COMMIT,
        native_adapter_commit=ADAPTER_COMMIT,
        native_adapter_contract_sha256=ADAPTER_SHA256,
        export_operation="terminal_eval_requests_only;zero_optimizer_updates;no_economic_score",
        private_mapper_coordinates=[0, 1, 2, 4, 5],
        public_slots_preserved=True,
        eligibility_release="forced CASH release precedes discretionary L1<=.1",
        native_execution_results=False,
        current_expert_input=model.contract["current_expert_input"],
        input_enabled=True,
        source_target_clocks_preserved=True,
        current_expert_input_file="CURRENT_EXPERT_INPUTS61.npz",
        maximum_training_expert_input_available_us=max(
            int(e.expert_input_available_us.max()) for e in train
        ),
        data_role="SEEN_DEVELOPMENT_INITIALIZATION_ABLATION_NOT_OOS",
    )
    if (
        manifest["maximum_training_label_available_us"] >= manifest["training_cutoff_us"]
        or manifest["maximum_scaler_input_available_us"] > manifest["training_cutoff_us"]
        or manifest["maximum_training_expert_input_available_us"] > manifest["training_cutoff_us"]
    ):
        raise ValueError("All training outcomes/features must mature before May cutoff")
    _atomic_json(staging / "MANIFEST.json", manifest)
    validate_native_bundle(staging, model, saved, terminal, episode)
    os.replace(staging, destination)
    _sync_directory(destination.parent)
    return dict(
        arm=manifest["arm_id"],
        model_identity=identity,
        requests_SHA256=sha(destination / "REQUESTS.npz"),
        completed_updates=512,
    )


def score(state, output, native_bundle):
    train, development, prototype, model, optimizer, folder, saved, terminal = frozen_state(
        state, output
    )
    native_bundle = Path(native_bundle)
    episode = development[0]
    validate_native_bundle(native_bundle, model, saved, terminal, episode)
    _atomic_json(
        Path(output) / "TERMINAL_BEFORE_SEEN_SCORE.json",
        dict(
            terminal=terminal,
            checkpoint_SHA256=saved["checkpoint_SHA256"],
            native_manifest_SHA256=sha(native_bundle / "MANIFEST.json"),
            optimizer_updates_during_scoring=0,
        ),
    )
    model.eval()
    identity, rng = model_identity(model), tree_identity(_rng_state())
    with torch.no_grad():
        requests = predict_episode(model, episode, feature_batch_size=32).numpy()
        train_requests = np.concatenate([predict_episode(model, e).numpy() for e in train])
    with np.load(native_bundle / "REQUESTS.npz", allow_pickle=False) as z:
        np.testing.assert_array_equal(requests, z["desired_expert_budget"])
    loss, _, report = request_gradient(requests, episode, prototype)
    targets, mapped = prototype.mapped_path(compress(requests), episode.internal.contexts)
    nav = report["nav"].detach().numpy()
    warm_path = (
        Path(__file__).resolve().parents[2] / "research/temporal-episode-weighting-v2-20261009"
    )
    warm_receipt = json.loads(
        subprocess.check_output(
            [
                "git",
                "show",
                COMPARATOR_COMMIT
                + ":research/temporal-episode-weighting-v2-20261009/results/RECEIPT.json",
            ],
            cwd=Path(__file__).resolve().parents[2],
        )
    )["arms"]["GRU64_WEIGHT_DATE"]
    warm_requests_file = warm_path / "native61-requests/EXP_GRU64_WEIGHT_DATE/REQUESTS.npz"
    audit = json.loads((Path(output) / "READY.json").read_text())["comparability"]
    if sha(warm_requests_file) != audit["comparator_files_SHA256"]["REQUESTS.npz"]:
        raise ValueError("Exact d3d57332 warm requests required")
    with np.load(warm_requests_file, allow_pickle=False) as z:
        warm_requests = z["desired_expert_budget"].copy()
        np.testing.assert_array_equal(z["decision_us"], episode.windows.decision_us)
    record = dict(
        data_role="SEEN_DEVELOPMENT_INITIALIZATION_ABLATION_NOT_OOS",
        capital=10000.0,
        decisions=61,
        loss=loss,
        utility_sum=float(report["utility_sum"].detach()),
        net_PnL=float(report["net_PnL"].detach()),
        maximum_drawdown=float(np.max(1 - nav / np.maximum.accumulate(nav))),
        maximum_allocated_gross=max(r["allocated_leg_gross"] for r in mapped),
        maximum_allocated_asset_gross=max(
            float(r["allocated_underlier_gross"].max()) for r in mapped
        ),
        **{
            name: float(report[name].detach())
            for name in ("fees", "spread", "slippage", "funding", "charged_reduction_cost")
        },
        risk_events=len(report["risk_events"]),
        paid_terminal_cash=report["terminal_cash_realized"],
        request_mean=requests.mean(0).tolist(),
        train_gate_statistics=gate_statistics(train_requests),
        seen_gate_statistics=gate_statistics(requests),
        mean_mapped_budget=expand(np.stack([r["budget"] for r in mapped])).mean(0).tolist(),
    )
    if identity != model_identity(model) or rng != tree_identity(_rng_state()):
        raise ValueError("Frozen score changed model/RNG")
    if any(float(optimizer.state[p]["step"]) != 512 for p in model.parameters()):
        raise ValueError("All actual fresh Adam ages must remain512")
    result = dict(
        schema="ONE_SEEN_FIXED512_INITIALIZATION_RESULT_V1",
        arm=ARM,
        model_identity=identity,
        completed_updates=512,
        parameter_count=13699,
        initial_train_loss=terminal["diagnostics"][0]["date_mean_loss"],
        final_train_loss=terminal["diagnostics"][-1]["date_mean_loss"],
        final_train_gradient_norm=terminal["diagnostics"][-1]["trained_objective_summary"][
            "gradient_norm"
        ],
        fresh=record,
        warm_comparator=warm_receipt,
        warm_seen_gate_statistics=gate_statistics(warm_requests),
        PnL_difference_vs_exact_warm=record["net_PnL"]
        - warm_receipt["seen_May_June_charged_daily_proxy"]["net_PnL"],
        comparator_commit=COMPARATOR_COMMIT,
        not_equal_lifetime_exposure=True,
        optimizer_updates_during_scoring=0,
        native_wallets=0,
        provider_downloads=0,
        native_pending_separate_executor=True,
    )
    np.savez_compressed(
        Path(output) / "SEEN61_PATH.npz",
        decision_us=episode.windows.decision_us,
        requests=requests,
        targets=targets,
        nav=nav,
        mapped_budget=expand(np.stack([r["budget"] for r in mapped])),
    )
    _atomic_json(Path(output) / "RESULT.json", result)
    return result
