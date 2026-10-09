"""Synthetic chronological weighting and read-only snapshot diagnostic contracts."""

import copy
import random
from dataclasses import replace

import numpy as np
import pytest
import torch
from torch import nn

from modules.temporal_episode_weighting_v2 import gradient
from modules.temporal_expert_input.gradient import memory_bounded_gradients as frozen_gradients
from modules.temporal_expert_input.inputs import expose_episode
from modules.temporal_expert_input.model import ExpertSelector
from modules.temporal_short_expansion.adapter import append_episode
from modules.temporal_short_expansion.tests.test_checkpoint import assert_optimizer_equal
from modules.temporal_two_expert.checkpoint import make_optimizer, model_identity
from modules.temporal_two_expert.inputs import DAY_US
from modules.temporal_two_expert.model import Selector
from modules.temporal_two_expert.test_temporal import episode


def setup(prototype):
    originals, scaler = [], None
    for index, count in enumerate((4, 7)):
        original, scaler = episode(prototype, count, release=False)
        delta = 20 * index * DAY_US
        windows = replace(
            original.windows,
            completed_us=original.windows.completed_us + delta,
            available_us=original.windows.available_us + delta,
            decision_us=original.windows.decision_us + delta,
        )
        contexts = tuple(
            replace(
                c,
                decision_us=c.decision_us + delta,
                available_us=c.available_us + delta,
                target_available_us=c.target_available_us + delta,
            )
            for c in original.contexts
        )
        originals.append(
            replace(
                original,
                wallet_id=f"wallet-{index}",
                windows=windows,
                contexts=contexts,
                label_available_us=original.label_available_us + delta,
                start_us=original.start_us + delta,
                end_us=original.end_us + delta,
                split_cutoff_us=original.split_cutoff_us + 40 * DAY_US,
            )
        )
    cutoff = originals[-1].split_cutoff_us
    episodes = []
    for original in originals:
        original = replace(original, split_cutoff_us=cutoff)
        count = len(original.contexts)
        short = np.tile([-0.021, -0.017, -0.011, -0.008, -0.005], (count, 1, 1))
        expanded = append_episode(
            original,
            short,
            np.ones((count, 1), bool),
            original.windows.decision_us[:, None],
            prototype,
            "a" * 64,
        )
        episodes.append(expose_episode(expanded))
    model = ExpertSelector(Selector(scaler, cash_enabled=True, dropout=0.2), input_enabled=True)
    return tuple(episodes), model


def test_fixed_coefficients_and_no_wallet_sampling():
    lengths = [54, 88, 62, 144, 430]
    np.testing.assert_array_equal(gradient.weights(lengths, 0), np.asarray(lengths) / 778)
    np.testing.assert_array_equal(
        gradient.weights(lengths, 0.5), np.asarray(lengths) / 778 * 0.5 + 0.1
    )
    assert gradient.weights(lengths, 0.5)[-1] == 0.3763496143958869
    assert gradient.weights(lengths, 0.5).sum() == 1


@pytest.mark.parametrize(
    "lengths,mixing",
    [
        ([], 0.5),
        ([0, 3], 0.5),
        ([-1, 3], 0.5),
        ([2.0, 3], 0.5),
        ([True], 0.5),
        ([2, 3], -0.1),
        ([2, 3], 1.1),
        ([2, 3], float("nan")),
        ([2, 3], "0.5"),
        ([2, 3], True),
    ],
)
def test_invalid_weight_definitions_rejected(lengths, mixing):
    with pytest.raises(ValueError):
        gradient.weights(lengths, mixing)


def test_zero_mixing_exact_frozen_loss_gradients_paths_and_rng(prototype):
    episodes, model = setup(prototype)
    model.train()
    assert model.parameter_count == 13699 and model.input_enabled
    torch.manual_seed(991)
    loss, requests = frozen_gradients(model, episodes, prototype, feature_batch_size=3)
    expected = [p.grad.clone() for p in model.parameters()]
    rng = torch.get_rng_state().clone()
    model.zero_grad(set_to_none=True)
    torch.manual_seed(991)
    actual, actual_requests = gradient.memory_bounded_gradients(
        model, episodes, prototype, feature_batch_size=3, mixing=0
    )
    assert actual == loss and torch.equal(torch.get_rng_state(), rng)
    np.testing.assert_array_equal(actual_requests, requests)
    assert all(torch.equal(p.grad, g) for p, g in zip(model.parameters(), expected, strict=True))


def test_mixed_full_graph_gradients_and_dropout_rng_equivalence(prototype):
    episodes, model = setup(prototype)
    model.train()
    coefficients = gradient.weights([len(e.contexts) for e in episodes], 0.5)
    torch.manual_seed(997)
    outputs = [gradient.predict_episode(model, e, feature_batch_size=3) for e in episodes]
    rng = torch.get_rng_state().clone()
    expected_loss = 0.0
    for e, output, coefficient in zip(episodes, outputs, coefficients, strict=True):
        loss, vjp, _ = gradient.request_gradient(output.detach().numpy(), e, prototype)
        output.backward(torch.tensor(vjp * coefficient))
        expected_loss += coefficient * loss
    expected = [p.grad.clone() for p in model.parameters()]
    model.zero_grad(set_to_none=True)
    torch.manual_seed(997)
    actual, requests = gradient.memory_bounded_gradients(
        model, episodes, prototype, feature_batch_size=3, mixing=0.5
    )
    assert actual == expected_loss and torch.equal(torch.get_rng_state(), rng)
    np.testing.assert_array_equal(requests, torch.cat(outputs).detach().numpy())
    for p, wanted in zip(model.parameters(), expected, strict=True):
        torch.testing.assert_close(p.grad, wanted, rtol=2e-12, atol=1e-15)


def test_mixed_head_and_expert_projection_finite_differences(prototype):
    episodes, model = setup(prototype)
    model.eval()
    gradient.memory_bounded_gradients(model, episodes, prototype, feature_batch_size=3, mixing=0.5)
    projection = model.expert_projection.weight
    coordinate = np.unravel_index(int(projection.grad.abs().argmax()), projection.shape)
    coefficients = gradient.weights([len(e.contexts) for e in episodes], 0.5)
    parameters = [
        (head.bias, (0,)) for head in (model.base.w_head, model.base.s_head, model.r_head)
    ]
    parameters.append((projection, coordinate))
    for parameter, index in parameters:
        expected, original = float(parameter.grad[index]), float(parameter[index].detach())
        scores, epsilon = [], 1e-5
        for sign in (1, -1):
            with torch.no_grad():
                parameter[index] = original + sign * epsilon
            scores.append(
                sum(
                    a
                    * gradient.request_gradient(
                        gradient.predict_episode(model, e).detach().numpy(), e, prototype
                    )[0]
                    for e, a in zip(episodes, coefficients, strict=True)
                )
            )
        with torch.no_grad():
            parameter[index] = original
        assert abs((scores[0] - scores[1]) / (2 * epsilon) - expected) < 5e-10


class AlteredEpisode:
    def __init__(self, original, **changes):
        self.original = original
        self.__dict__.update(changes)

    def __getattr__(self, name):
        return getattr(self.original, name)


@pytest.mark.parametrize(
    "mutation", ["reversed", "overlap", "duplicate", "seen", "cutoff", "partial", "batch"]
)
def test_wallet_contract_rejects_before_rng_or_gradient_use(prototype, mutation):
    episodes, model = setup(prototype)
    first, second = episodes
    if mutation == "reversed":
        first, second = second, first
    elif mutation == "overlap":
        second = AlteredEpisode(first, wallet_id="overlap-distinct")
    elif mutation == "duplicate":
        second = AlteredEpisode(second, wallet_id=first.wallet_id)
    elif mutation == "seen":
        second = AlteredEpisode(second, role="SEEN_VALIDATION")
    elif mutation == "cutoff":
        second = AlteredEpisode(second, split_cutoff_us=second.split_cutoff_us + DAY_US)
    elif mutation == "partial":
        second = AlteredEpisode(second, contexts=second.contexts[:-1])
    rng = torch.get_rng_state().clone()
    with pytest.raises(ValueError):
        gradient.memory_bounded_gradients(
            model,
            [first, second],
            prototype,
            feature_batch_size=0 if mutation == "batch" else 3,
            mixing=0.5,
        )
    assert torch.equal(torch.get_rng_state(), rng) and all(
        p.grad is None for p in model.parameters()
    )


def test_each_economic_rollout_is_one_intact_wallet(prototype, monkeypatch):
    episodes, model = setup(prototype)
    visited, real = [], gradient.request_gradient

    def record(requests, e, recovered):
        loss, vjp, report = real(requests, e, recovered)
        visited.append(
            (e.wallet_id, len(requests), len(e.prices), report["terminal_cash_realized"])
        )
        return loss, vjp, report

    monkeypatch.setattr(gradient, "request_gradient", record)
    gradient.memory_bounded_gradients(model, episodes, prototype, feature_batch_size=1, mixing=0.5)
    assert visited == [("wallet-0", 4, 5, True), ("wallet-1", 7, 8, True)]


def assert_rng_equal(first, second):
    assert torch.equal(first["torch"], second["torch"]) and first["python"] == second["python"]
    assert first["numpy"].keys() == second["numpy"].keys()
    for key, value in first["numpy"].items():
        if isinstance(value, torch.Tensor):
            assert torch.equal(value, second["numpy"][key])
        else:
            assert value == second["numpy"][key]


@pytest.mark.parametrize("mixing", [0.0, 0.5])
def test_snapshot_diagnostic_both_summaries_full_sum_and_state_preservation(prototype, mixing):
    episodes, model = setup(prototype)
    optimizer = make_optimizer(model)
    model.eval()
    gradient.memory_bounded_gradients(model, episodes, prototype, feature_batch_size=3, mixing=0.0)
    optimizer.step()
    optimizer.zero_grad(set_to_none=True)
    model.train()
    model.base.encoder.eval()  # Preserve even an intentionally mixed module mode.
    random.seed(1009)
    np.random.seed(1013)
    np.random.normal()  # exercise the saved NumPy Gaussian cache
    rng, identity = gradient._rng_state(), model_identity(model)
    modes = [m.training for m in model.modules()]
    before_optimizer = copy.deepcopy(optimizer.state_dict())
    report = gradient.episode_diagnostic(
        model,
        episodes,
        prototype,
        mixing=mixing,
        feature_batch_size=3,
        snapshot_step=128,
        check_aggregate=True,
    )
    assert report["snapshot_step"] == 128 and report["optimizer_updates"] == 0
    assert report["date_mean_loss"] == report["date_gradient_summary"]["weighted_mean_loss"]
    assert report["mixed_mean_loss"] == report["mixed_gradient_summary"]["weighted_mean_loss"]
    assert report["trained_objective_summary"]["mixing"] == mixing
    assert report["independent_full_sum_check"]["maximum_gradient_abs_error"] < 1e-14
    for key in ("date_gradient_summary", "mixed_gradient_summary", "trained_objective_summary"):
        assert abs(report[key]["signed_projection_sum"] - 1) < 1e-12
    assert model_identity(model) == identity and [m.training for m in model.modules()] == modes
    assert_optimizer_equal(before_optimizer, optimizer.state_dict())
    assert_rng_equal(rng, gradient._rng_state())
    assert all(p.grad is None for p in model.parameters())


class TinySnapshot(nn.Module):
    def __init__(self):
        super().__init__()
        self.vector = nn.Parameter(torch.zeros(2, dtype=torch.float64))
        self.register_buffer("mean", torch.zeros(1, dtype=torch.float64))
        self.contract = dict(schema="SYNTHETIC_SIGNED_CONTRIBUTION")


def test_signed_projection_is_not_coefficient_or_norm_fraction(prototype, monkeypatch):
    episodes, _ = setup(prototype)
    model = TinySnapshot()
    vectors, losses = (
        [
            torch.tensor([1.0, 0.0], dtype=torch.float64),
            torch.tensor([-2.0, 1.0], dtype=torch.float64),
        ],
        [0.2, -0.1],
    )

    def synthetic(model, batch, recovered, *, mixing=0.0, **kw):
        coefficients = gradient.weights([len(e.contexts) for e in batch], mixing)
        indices = [0 if e.wallet_id == "wallet-0" else 1 for e in batch]
        model.vector.grad = sum(
            (vectors[i] * float(a) for i, a in zip(indices, coefficients, strict=True)),
            torch.zeros(2, dtype=torch.float64),
        )
        return float(
            sum(losses[i] * a for i, a in zip(indices, coefficients, strict=True))
        ), np.zeros((sum(len(e.contexts) for e in batch), 6))

    monkeypatch.setattr(gradient, "memory_bounded_gradients", synthetic)
    report = gradient.episode_diagnostic(
        model, episodes, prototype, mixing=0.5, check_aggregate=True
    )
    summary = report["mixed_gradient_summary"]
    assert summary["signed_projection_shares"][0] < 0 and summary["signed_projection_shares"][1] > 1
    assert summary["coefficients"][0] > 0 and summary["weighted_gradient_vector_norms"][0] > 0
    assert abs(summary["signed_projection_sum"] - 1) < 1e-15
    assert report["date_mean_loss"] == sum(
        a * loss for a, loss in zip(gradient.weights([4, 7], 0), losses, strict=True)
    )
    assert report["mixed_mean_loss"] == sum(
        a * loss for a, loss in zip(gradient.weights([4, 7], 0.5), losses, strict=True)
    )
    assert all(p.grad is None for p in model.parameters())


def test_zero_total_gradient_marks_projection_undefined(prototype, monkeypatch):
    episodes, _ = setup(prototype)
    model = TinySnapshot()

    def zero(model, *a, **kw):
        model.vector.grad = torch.zeros_like(model.vector)
        return 0.0, np.zeros((1, 6))

    monkeypatch.setattr(gradient, "memory_bounded_gradients", zero)
    summary = gradient.episode_diagnostic(model, episodes, prototype)["trained_objective_summary"]
    assert summary["gradient_norm"] == 0 and summary["signed_projection_shares"] == [None, None]
    assert summary["signed_projection_sum"] is None and not summary["signed_projection_defined"]


def test_diagnostic_rejects_pending_grads_and_restores_after_failure(prototype, monkeypatch):
    episodes, model = setup(prototype)
    model.expert_projection.weight.grad = torch.zeros_like(model.expert_projection.weight)
    with pytest.raises(ValueError, match="pending gradients"):
        gradient.episode_diagnostic(model, episodes, prototype)
    model.zero_grad(set_to_none=True)
    rng, identity = gradient._rng_state(), model_identity(model)
    modes = [m.training for m in model.modules()]

    def failure(*a, **kw):
        random.random()
        np.random.random()
        torch.rand(3)
        raise ValueError("synthetic incomplete diagnostic")

    monkeypatch.setattr(gradient, "request_gradient", failure)
    with pytest.raises(ValueError, match="incomplete diagnostic"):
        gradient.episode_diagnostic(model, episodes, prototype)
    assert model_identity(model) == identity and [m.training for m in model.modules()] == modes
    assert_rng_equal(rng, gradient._rng_state())
    assert all(p.grad is None for p in model.parameters())
