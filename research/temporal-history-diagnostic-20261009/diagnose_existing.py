"""Read-only existing snapshots, inputs and saved economic paths; zero fits."""

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import torch

from modules.temporal_episode_weighting_v2.export import frozen_arm
from modules.temporal_episode_weighting_v2.snapshot import initialize
from modules.temporal_episode_weighting_v2.stage import inputs
from modules.temporal_expert_input.gradient import predict_episode
from modules.temporal_two_expert.checkpoint import model_identity
from modules.temporal_two_expert.inputs import FEATURE_NAMES

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--state", type=Path, required=True, help="Restored prior experiment STATE")
parser.add_argument("--output", type=Path, required=True)
args = parser.parse_args()
state = args.state.resolve()
root = Path(__file__).resolve().parents[2]
run = state / "episode-weighting-v2"
torch.set_num_threads(1)
torch.use_deterministic_algorithms(True)
train, dev, prototype, dataset, scaler = inputs(state, include_development=True)


def distribution(a):
    a = np.asarray(a).reshape(-1)
    a = a[np.isfinite(a)]
    return dict(
        n=len(a),
        mean=float(a.mean()),
        std=float(a.std()),
        min=float(a.min()),
        max=float(a.max()),
        quantiles={str(q): float(np.quantile(a, q)) for q in (0, 0.01, 0.1, 0.5, 0.9, 0.99, 1)},
    )


def feature_stats(episodes):
    # One last-day observation per retained decision, never duplicated64windows.
    x = np.concatenate([e.windows.values[:, -1] for e in episodes]).astype(float)
    v = np.concatenate([e.windows.valid[:, -1] for e in episodes])
    z = (np.where(v, x, scaler.mean) - scaler.mean) / scaler.scale
    out = {}
    for j, name in enumerate(FEATURE_NAMES):
        a = z[:, :, j][v[:, :, j]]
        out[name] = {
            **distribution(a),
            "absZ_gt3_fraction": float(np.mean(np.abs(a) > 3)),
            "absZ_gt5_fraction": float(np.mean(np.abs(a) > 5)),
            "valid_fraction": float(v[:, :, j].mean()),
        }
    expert = np.concatenate([e.expert_state for e in episodes])
    return dict(
        features=out,
        expert_state_columns=[distribution(expert[:, j]) for j in range(18)],
        decisions=len(x),
        statistic_unit="unique_retained_decision_last_completed_day_x_CORE5;not_repeatedwindows",
    )


def model_stats(model, episodes):
    before = model_identity(model)
    model.eval()
    captured = {k: [] for k in ("w", "s", "r", "joint")}
    handles = []
    for k, layer in (
        ("w", model.base.w_head),
        ("s", model.base.s_head),
        ("r", model.r_head),
        ("joint", model.base.joint),
    ):

        def hook(module, args, output, k=k):
            captured[k].append(output.detach().cpu().numpy().copy())

        handles.append(layer.register_forward_hook(hook))
    requests = []
    try:
        for e in episodes:
            with torch.no_grad():
                requests.append(predict_episode(model, e, feature_batch_size=32).numpy())
    finally:
        for h in handles:
            h.remove()
    assert before == model_identity(model)
    q = np.concatenate(requests)
    stats = {"model_identity": before}
    for k in ("w", "s", "r"):
        logits = np.concatenate(captured[k]).reshape(-1)
        p = 1 / (1 + np.exp(-logits))
        derivative = p * (1 - p)
        stats[k] = dict(
            logits=distribution(logits),
            probability=distribution(p),
            derivative=distribution(derivative),
            fraction_p_lt01=float((p < 0.01).mean()),
            fraction_p_gt99=float((p > 0.99).mean()),
            fraction_derivative_lt001=float((derivative < 0.001).mean()),
        )
    j = np.concatenate(captured["joint"])
    stats["joint_tanh"] = dict(
        preactivation=distribution(j),
        fraction_abs_tanh_gt99=float((np.abs(np.tanh(j)) > 0.99).mean()),
    )
    stats["requests"] = dict(
        mean=q.mean(0).tolist(),
        minimum=q.min(0).tolist(),
        maximum=q.max(0).tolist(),
        mean_entropy=float((-np.where(q > 0, q * np.log(np.maximum(q, 1e-300)), 0)).sum(1).mean()),
        fraction_any_action_gt99=float((q.max(1) > 0.99).mean()),
    )
    stats["per_wallet"] = [
        dict(
            wallet_id=e.wallet_id,
            start_us=e.start_us,
            end_us=e.end_us,
            dates=len(e.contexts),
            request_mean=x.mean(0).tolist(),
        )
        for e, x in zip(episodes, requests, strict=True)
    ]
    return stats


initial, _, parent, _ = initialize(state, scaler)
base = {n: p.detach().clone() for n, p in initial.named_parameters()}
models = {
    "INITIAL": {role: model_stats(initial, e) for role, e in [("TRAIN", train), ("SEEN", dev)]}
}
for arm in ("GRU64_WEIGHT_DATE", "GRU64_WEIGHT_MIXED"):
    _, _, _, m, _, _, _, _ = frozen_arm(state, run, arm)
    stats = {role: model_stats(m, e) for role, e in [("TRAIN", train), ("SEEN", dev)]}
    stats["weight_change_from_same_initial"] = {
        n: dict(
            initial_norm=float(torch.linalg.vector_norm(base[n])),
            final_norm=float(torch.linalg.vector_norm(p)),
            delta_norm=float(torch.linalg.vector_norm(p - base[n])),
            maximum_abs=float(p.detach().abs().max()),
        )
        for n, p in m.named_parameters()
    }
    models[arm] = stats
loss_curves = {}
for phase in (
    "temporal-four-fit",
    "temporal-surrogate-resume-v2",
    "temporal-short-expansion",
    "temporal-expert-input",
    "temporal-episode-weighting-v2",
):
    r = json.loads((root / f"research/{phase}-20261009/results/RESULT.json").read_text())
    loss_curves[phase] = {}
    for arm, x in r["arms"].items():
        t = x["terminal"]
        h = t.get("diagnostics") or t.get("history")
        if h is None:
            phase_state = {
                "temporal-four-fit": "four-fit",
                "temporal-surrogate-resume-v2": "surrogate-v2",
                "temporal-short-expansion": "short-expansion",
                "temporal-expert-input": "expert-input",
                "temporal-episode-weighting-v2": "episode-weighting-v2",
            }[phase]
            folder = state / phase_state / arm
            pointer = json.loads((folder / "latest.json").read_text())
            snap = torch.load(folder / pointer["file"], weights_only=True, map_location="cpu")
            h = snap["trainer_state"].get("history", [])
        points = []
        for d in h:
            points.append(
                dict(
                    step=d.get("snapshot_step", d.get("step")),
                    loss=d.get(
                        "loss", d.get("trained_objective_summary", {}).get("weighted_mean_loss")
                    ),
                    gradient_norm=d.get(
                        "gradient_norm", d.get("trained_objective_summary", {}).get("gradient_norm")
                    ),
                )
            )
        loss_curves[phase][arm] = dict(
            status=t["status"],
            updates=t.get("completed_stage_updates", t.get("step")),
            points=points,
            train_wallets=[
                {k: w[k] for k in ("wallet_id", "decisions", "loss", "net_PnL", "request_mean")}
                for w in x.get("wallets", [])
                if w["role"] == "TRAIN"
            ],
        )
result = dict(
    schema="EXISTING_TEMPORAL_READ_ONLY_DIAGNOSTIC_V1",
    created_UTC=datetime.now(timezone.utc).isoformat(),
    optimizer_updates=0,
    native_wallets=0,
    provider_downloads=0,
    input_contract="64x5x24plus24masks;18existingexpertinputs",
    normalizer_identity=scaler.identity,
    dates=[
        dict(wallet_id=e.wallet_id, start_us=e.start_us, end_us=e.end_us, dates=len(e.contexts))
        for e in train
    ],
    input_statistics={role: feature_stats(e) for role, e in [("TRAIN", train), ("SEEN", dev)]},
    dataset_identity=dataset,
    models=models,
    loss_curves=loss_curves,
    output_parameterization="threefactorizedsigmoidsgatesw,s,r;nottemperature-softmax",
)
# Plan feasibility only: select existing clocks. Do not fit a scaler, construct
# a replacement wallet, call the economic objective, or update an optimizer.
day_us = 86400 * 1000000
folds = []
for start in ("2023-07-03", "2023-10-02", "2024-01-01"):
    validation_start = (
        int(datetime.fromisoformat(start).replace(tzinfo=timezone.utc).timestamp()) * 1000000
    )
    training_maturity_cutoff = validation_start - 64 * day_us
    validation_end = validation_start + 63 * day_us
    admitted, scored = [], []
    for e in train:
        decisions = e.windows.decision_us
        rows = np.flatnonzero(e.label_available_us < training_maturity_cutoff)
        if len(rows):
            assert np.array_equal(rows, np.arange(len(rows)))
            admitted.append(
                dict(
                    wallet_id=e.wallet_id,
                    dates=len(rows),
                    first_decision_us=int(decisions[rows[0]]),
                    last_decision_us=int(decisions[rows[-1]]),
                    latest_outcome_available_us=int(e.label_available_us[rows].max()),
                    declared_prefix_requires_paid_terminal_close=True,
                )
            )
        rows = np.flatnonzero((decisions >= validation_start) & (decisions < validation_end))
        if len(rows):
            assert len(rows) == 63
            assert np.all(np.diff(decisions[rows]) == day_us)
            scored.append(
                dict(
                    wallet_id=e.wallet_id,
                    dates=len(rows),
                    first_decision_us=int(decisions[rows[0]]),
                    last_decision_us=int(decisions[rows[-1]]),
                )
            )
    assert len(scored) == 1
    folds.append(
        dict(
            validation_first_decision=start,
            validation_end_exclusive_us=validation_end,
            strict_training_outcome_maturity_cutoff_us=training_maturity_cutoff,
            embargo_completed_days=64,
            training_dates=sum(w["dates"] for w in admitted),
            training_wallet_prefixes=admitted,
            validation_wallet_block=scored[0],
            status="CLOCK_FEASIBLE_ONLY_NOT_RUN",
        )
    )
result["proposed_fold_clock_feasibility"] = folds
out = args.output.resolve()
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
print(
    json.dumps(
        dict(status="READ_ONLY_COMPLETE", model_count=len(models), updates=0, output=str(out))
    )
)
