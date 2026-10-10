"""Causal/action coordinates, mapper equivalence and exact neural VJP tests."""

import numpy as np
import pytest
import torch

from modules.temporal_risk_proxy_v2.proxy import BoundaryPlan, request_loss_and_gradient_v2
from modules.temporal_two_expert.model import Selector, predict_windows
from modules.temporal_two_expert.test_temporal import episode

from .adapter import append_episode, compress, expand
from .gradient import memory_bounded_gradients, request_gradient
from .model import E6, ShortSelector


def setup(prototype, count=8, enabled=True):
    e, scaler = episode(prototype, count, release=False)
    short = np.tile([-0.021, -0.017, -0.011, -0.008, -0.005], (count, 1, 1))
    short = short.reshape(count, 1, 5)
    eligible = np.ones((count, 1), bool)
    eligible[3] = False
    extended = append_episode(
        e, short, eligible, e.windows.decision_us[:, None], prototype, "a" * 64
    )
    model = ShortSelector(Selector(scaler, cash_enabled=True, dropout=0.2), short_enabled=enabled)
    return extended, model


@pytest.mark.parametrize("enabled", [False, True])
def test_counts_masks_simplex_and_rng(prototype, enabled):
    before = torch.get_rng_state().clone()
    e, model = setup(prototype, enabled=enabled)
    assert torch.equal(before, torch.get_rng_state()) and model.parameter_count == 13123
    model.eval()
    output = predict_windows(model, e.windows, feature_batch_size=3)
    assert output.shape == (8, 6) and len(E6) == 6
    assert torch.count_nonzero(output[:, 2:4]) == 0
    torch.testing.assert_close(
        output.sum(1), torch.ones(8, dtype=torch.float64), rtol=0, atol=4e-16
    )
    pair = predict_windows(model.base, e.windows, feature_batch_size=3)
    if not enabled:
        assert torch.equal(output[:, :5], pair) and torch.count_nonzero(output[:, 5]) == 0
    else:
        torch.testing.assert_close(
            output[:, 5], 0.01 * (pair[:, 1] + pair[:, 4]), rtol=1e-15, atol=1e-17
        )
    assert model._joint is None
    output.sum().backward()
    assert all(p.grad is not None for p in model.parameters())


def test_zero_append_original_mapped_objective_and_request_vjp(prototype):
    e, model = setup(prototype, enabled=False)
    model.eval()
    requests = predict_windows(model, e.windows).detach().numpy()
    loss, g, _ = request_gradient(requests, e, prototype)
    old_loss, old_g, _ = request_loss_and_gradient_v2(
        requests[:, :5], e.original, prototype, plan=BoundaryPlan.full_fill_diagnostic(8)
    )
    assert loss == old_loss
    np.testing.assert_array_equal(g[:, (0, 1, 4)], old_g[:, (0, 1, 4)])
    target, private = prototype.mapped_path(compress(requests), e.internal.contexts)
    expected, original = prototype.mapped_path(requests[:, :5], e.original.contexts)
    np.testing.assert_array_equal(target, expected)
    for a, b in zip(private, original, strict=True):
        np.testing.assert_array_equal(expand(a["budget"][None])[:, :5], b["budget"][None])


def test_appended_leg_generic_l1_forward_and_new_request_finite_differences(prototype):
    e, _ = setup(prototype)
    requests = np.tile([0.18, 0.28, 0, 0, 0.27, 0.27], (8, 1))
    requests[2:5] = [0.34, 0.16, 0, 0, 0.19, 0.31]
    loss, gradient, _ = request_gradient(requests, e, prototype)
    targets, records = prototype.mapped_path(compress(requests), e.internal.contexts)
    prior = np.array([1.0, 0, 0, 0, 0, 0])
    for i, record in enumerate(records):
        desired = requests[i].copy()
        eligible = e.eligible[i].copy()
        # Public dormant old slots have no allocation and therefore release no value.
        for v in (prior, desired):
            v[0] += v[~eligible].sum()
            v[~eligible] = 0
        change = desired - prior
        distance = abs(change).sum()
        prior = prior + min(1.0, 0.1 / distance if distance else 1.0) * change
        np.testing.assert_allclose(expand(record["budget"][None])[0], prior, rtol=0, atol=1e-16)
        wanted = (prior[:, None] * e.expert_targets[i]).sum(0) if i < 7 else np.zeros(5)
        np.testing.assert_allclose(targets[i], wanted, rtol=0, atol=1e-17)
    for t in (0, 2, 4, 6):
        for k in (1, 4, 5):
            direction = np.zeros_like(requests)
            direction[t, k] = 1
            direction[t, 0] = -1
            eps = 1e-6
            plus = request_gradient(requests + eps * direction, e, prototype)[0]
            minus = request_gradient(requests - eps * direction, e, prototype)[0]
            assert abs((plus - minus) / (2 * eps) - (gradient * direction).sum()) < 5e-10
    assert np.isfinite(loss)


@pytest.mark.parametrize("enabled", [False, True])
def test_dropout_replay_matches_full_graph_and_stream(prototype, enabled):
    e, model = setup(prototype, enabled=enabled)
    torch.manual_seed(711)
    output = predict_windows(model, e.windows, feature_batch_size=3)
    loss, gradient, _ = request_gradient(output.detach().numpy(), e, prototype)
    output.backward(torch.tensor(gradient))
    expected = [p.grad.clone() for p in model.parameters()]
    rng = torch.get_rng_state().clone()
    model.zero_grad(set_to_none=True)
    torch.manual_seed(711)
    actual, _ = memory_bounded_gradients(model, [e], prototype, feature_batch_size=3)
    assert actual == loss and torch.equal(rng, torch.get_rng_state())
    for p, g in zip(model.parameters(), expected, strict=True):
        torch.testing.assert_close(p.grad, g, rtol=2e-12, atol=1e-15)


def test_neural_heads_finite_differences_and_missing_values(prototype):
    e, model = setup(prototype)
    model.eval()
    loss, _ = memory_bounded_gradients(model, [e], prototype, feature_batch_size=3)
    for head in (model.base.w_head, model.base.s_head, model.r_head):
        actual = head.bias.grad.clone()
        original = head.bias.detach().clone()
        eps = 1e-5
        scores = []
        for sign in (1, -1):
            with torch.no_grad():
                head.bias.copy_(original + sign * eps)
            scores.append(
                request_gradient(predict_windows(model, e.windows).detach().numpy(), e, prototype)[
                    0
                ]
            )
        with torch.no_grad():
            head.bias.copy_(original)
        assert abs((scores[0] - scores[1]) / (2 * eps) - float(actual)) < 5e-10
    values = torch.tensor(e.windows.values.copy())
    valid = torch.tensor(e.windows.valid.copy())
    steps = torch.tensor(e.windows.step_valid.copy())
    valid[:, 10, 0, :] = False
    values[:, 10, 0, :] = float("nan")
    a = model(values, valid, steps)
    values[:, 10, 0, :] = float("inf")
    assert torch.equal(a, model(values, valid, steps)) and np.isfinite(loss)


def test_causal_clocks_and_public_slot_rejection(prototype):
    e, _ = setup(prototype)
    future = e.target_available_us[:, -1:] + 1
    with pytest.raises(ValueError, match="causal"):
        append_episode(
            e.original, e.expert_targets[:, -1:], e.eligible[:, -1:], future, prototype, "a" * 64
        )
    bad = np.tile([0.5, 0.2, 0.1, 0, 0.2, 0], (8, 1))
    with pytest.raises(ValueError, match="slots2/3"):
        compress(bad)


def test_forced_release_is_outside_discretionary_l1_budget(prototype):
    e, _ = setup(prototype)
    requests = np.tile([0.01, 0.0, 0.0, 0.0, 0.0, 0.99], (8, 1))
    _, records = prototype.mapped_path(compress(requests), e.internal.contexts)
    before = records[2]["budget"]
    after = records[3]["budget"]
    assert np.abs(after - before).sum() > 0.1
    assert np.abs(after - records[3]["released_prior"]).sum() <= 0.1
    assert after[4] == 0 and after[0] == 1
