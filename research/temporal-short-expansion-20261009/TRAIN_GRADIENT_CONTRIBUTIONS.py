"""Actual terminal own-path training gradients by intact episode; no optimizer steps."""

import argparse
import json
from pathlib import Path

import numpy as np
import torch

from modules.temporal_short_expansion.checkpoint import load_checkpoint
from modules.temporal_short_expansion.gradient import memory_bounded_gradients
from modules.temporal_short_expansion.stage import ARMS, initialize, inputs, sources
from modules.temporal_two_expert.checkpoint import model_identity


def vector(model):
    return torch.cat([p.grad.flatten() for p in model.parameters()]).numpy().copy()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--state", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args()
    torch.set_num_threads(1)
    torch.use_deterministic_algorithms(True)
    train, _, prototype, _, scaler = inputs(a.state)
    rows = {}
    for arm in ARMS:
        folder = a.output / arm
        terminal = json.loads((folder / "TERMINAL.json").read_text())
        binding = json.loads((folder / "RUN.json").read_text())
        assert binding["specification"]["algorithm"]["versioned_sources"] == sources()
        model, optimizer, _, _ = initialize(a.state, scaler, arm == ARMS[1])
        saved = load_checkpoint(folder, model, optimizer, binding)
        assert saved["model_identity"] == terminal["model_identity"]
        model.eval()
        before = model_identity(model)
        rng = torch.get_rng_state().clone()
        lengths = np.array([len(e.contexts) for e in train], dtype=np.float64)
        date_weight = lengths / lengths.sum()
        mixed_weight = 0.5 * date_weight + 0.5 / len(train)
        gradients = []
        losses = []
        for e in train:
            optimizer.zero_grad(set_to_none=True)
            loss, _ = memory_bounded_gradients(model, [e], prototype, feature_batch_size=32)
            gradients.append(vector(model))
            losses.append(loss)
        gradients = np.stack(gradients)
        losses = np.array(losses)
        total = (date_weight[:, None] * gradients).sum(0)
        denominator = float(total @ total)
        optimizer.zero_grad(set_to_none=True)
        full_loss, _ = memory_bounded_gradients(model, train, prototype, feature_batch_size=32)
        np.testing.assert_allclose(vector(model), total, rtol=2e-12, atol=1e-15)
        assert abs(full_loss - float(date_weight @ losses)) < 1e-15
        optimizer.zero_grad(set_to_none=True)
        assert before == model_identity(model) and torch.equal(rng, torch.get_rng_state())
        rows[arm] = dict(
            model_identity=before,
            checkpoint_SHA256=saved["checkpoint_SHA256"],
            objective_version=2,
            dropout=False,
            actual_charged_daily_wallets=True,
            unweighted_train_loss=full_loss,
            full_train_gradient_norm=float(np.linalg.norm(total)),
            predetermined_mixed_weight_loss_at_same_weights=float(mixed_weight @ losses),
            predetermined_mixed_weight_gradient_norm_at_same_weights=float(
                np.linalg.norm((mixed_weight[:, None] * gradients).sum(0))
            ),
            episodes=[
                dict(
                    wallet_id=e.wallet_id,
                    dates=len(e.contexts),
                    date_coefficient=float(date_weight[i]),
                    predetermined_mixed_coefficient=float(mixed_weight[i]),
                    own_path_loss=float(losses[i]),
                    weighted_loss_contribution=float(date_weight[i] * losses[i]),
                    individual_gradient_norm=float(np.linalg.norm(gradients[i])),
                    date_weighted_gradient_vector_norm=float(
                        date_weight[i] * np.linalg.norm(gradients[i])
                    ),
                    signed_projection_share_of_total_gradient=float(
                        date_weight[i] * gradients[i] @ total / denominator
                    )
                    if denominator
                    else None,
                )
                for i, e in enumerate(train)
            ],
            projection_share_definition=(
                "dot(date_coefficient*episode_gradient,total_gradient)/squared_norm(total_gradient);"
                "signed and additive, not gradient norm fraction"
            ),
            norm_warning=(
                "vector norms are not additive; "
                "coefficients are not measured gradient contributions"
            ),
            optimizer_updates=0,
            weights_unchanged=True,
            RNG_unchanged=True,
        )
    result = dict(
        schema="ACTUAL_TERMINAL_CHARGED_V2_EPISODE_GRADIENT_CONTRIBUTIONS_V1",
        data_role="778_pre-May_dates_only;no_development_economic_score",
        arms=rows,
        no_outcome_classification_or_win_day_resampling=True,
    )
    (a.output / "TRAIN_GRADIENT_CONTRIBUTIONS.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n"
    )
    print(json.dumps(result))


if __name__ == "__main__":
    main()
