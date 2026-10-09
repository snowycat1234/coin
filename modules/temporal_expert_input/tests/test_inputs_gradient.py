"""Current input availability, information contrast and exact economic chain rule."""

from dataclasses import replace

import numpy as np
import pytest
import torch

from modules.temporal_expert_input.gradient import memory_bounded_gradients, predict_episode
from modules.temporal_expert_input.inputs import expose_episode
from modules.temporal_expert_input.model import ExpertSelector
from modules.temporal_short_expansion.gradient import request_gradient
from modules.temporal_short_expansion.test_expansion import setup as old_setup
from modules.temporal_two_expert.model import predict_windows


def setup(prototype, enabled=True):
    episode, old = old_setup(prototype)
    return expose_episode(episode), ExpertSelector(old.base, input_enabled=enabled), old


@pytest.mark.parametrize("enabled", [False, True])
def test_initial_parity_counts_simplex_masks_and_rng(prototype, enabled):
    rng = torch.get_rng_state().clone()
    e, model, old = setup(prototype, enabled)
    assert torch.equal(rng, torch.get_rng_state())
    assert model.parameter_count == 13699
    model.eval()
    old.eval()
    out = predict_episode(model, e, feature_batch_size=3)
    assert torch.equal(out, predict_windows(old, e.windows, feature_batch_size=3))
    assert torch.count_nonzero(out[:, 2:4]) == 0 and out.shape == (8, 6)
    torch.testing.assert_close(out.sum(1), torch.ones(8, dtype=torch.float64), rtol=0, atol=4e-16)
    assert model._expert_state is None and model._joint is None


def test_named_input_exact_clocks_and_flat_unavailable_distinction(prototype):
    e, _, _ = setup(prototype)
    wanted = e.original.expert_targets[:, (1, 4, 5)].copy()
    masks = e.original.eligible[:, (1, 4, 5)]
    wanted[~masks] = 0
    np.testing.assert_array_equal(e.expert_state[:, :15], wanted.reshape(8, 15) / 0.3)
    np.testing.assert_array_equal(e.expert_state[:, 15:], masks)
    assert not e.expert_state.flags.writeable and not e.expert_input_available_us.flags.writeable
    assert np.all(e.expert_input_available_us <= e.windows.decision_us[:, None])
    assert np.all(e.expert_input_available_us < e.windows.decision_us[:, None] + 60000001)
    bad = e.original.target_available_us.copy()
    bad[0, 4] += 1
    with pytest.raises(ValueError, match="causal"):
        expose_episode(replace(e.original, target_available_us=bad))
    flat = e.original.expert_targets.copy()
    flat[:, 5] = 0
    unavailable = e.original.eligible.copy()
    unavailable[:, 5] = False
    a = expose_episode(replace(e.original, expert_targets=flat))
    b = expose_episode(replace(e.original, expert_targets=flat, eligible=unavailable))
    assert np.array_equal(a.expert_state[:, :15], b.expert_state[:, :15])
    assert np.any(a.expert_state[:, 17] != b.expert_state[:, 17])


def test_outcomes_and_later_targets_cannot_change_earlier_input(prototype):
    e, _, _ = setup(prototype)
    original = e.original.original
    outcome = replace(
        original, prices=original.prices * 1.07, funding_coeff=original.funding_coeff * 2
    )
    modified = replace(e.original, original=outcome)
    np.testing.assert_array_equal(expose_episode(modified).expert_state, e.expert_state)
    targets = modified.expert_targets.copy()
    targets[4:, 4] *= -1
    after = expose_episode(replace(modified, expert_targets=targets))
    np.testing.assert_array_equal(after.expert_state[:4], e.expert_state[:4])


@pytest.mark.parametrize("enabled", [False, True])
def test_information_contrast_and_projection_gradient(prototype, enabled):
    e, model, _ = setup(prototype, enabled)
    model.eval()
    # Move away from the deliberately equal initial projection; test the
    # ability to respond to exact CS state under identical market windows.
    with torch.no_grad():
        model.expert_projection.weight.fill_(0.01)
    state = e.expert_state.copy()
    state[:, 5:10] *= -1
    altered = replace(e, expert_state=state)
    a = predict_episode(model, e)
    b = predict_episode(model, altered)
    assert torch.equal(a, b) is (not enabled)
    loss, _ = memory_bounded_gradients(model, [e], prototype, feature_batch_size=3)
    gradient = model.expert_projection.weight.grad
    assert torch.isfinite(gradient).all() and np.isfinite(loss)
    assert bool(torch.count_nonzero(gradient)) is enabled


@pytest.mark.parametrize("enabled", [False, True])
def test_dropout_complete_path_gradient_and_rng_replay(prototype, enabled):
    e, model, _ = setup(prototype, enabled)
    torch.manual_seed(811)
    output = predict_episode(model, e, feature_batch_size=3)
    loss, gradient, _ = request_gradient(output.detach().numpy(), e, prototype)
    output.backward(torch.tensor(gradient))
    expected = [p.grad.clone() for p in model.parameters()]
    rng = torch.get_rng_state().clone()
    model.zero_grad(set_to_none=True)
    torch.manual_seed(811)
    actual, _ = memory_bounded_gradients(model, [e], prototype, feature_batch_size=3)
    assert actual == loss and torch.equal(rng, torch.get_rng_state())
    for p, wanted in zip(model.parameters(), expected, strict=True):
        torch.testing.assert_close(p.grad, wanted, rtol=2e-12, atol=1e-15)


def test_projection_full_economic_finite_difference(prototype):
    e, model, _ = setup(prototype)
    model.eval()
    memory_bounded_gradients(model, [e], prototype, feature_batch_size=3)
    gradient = model.expert_projection.weight.grad
    k = np.unravel_index(int(gradient.abs().argmax()), gradient.shape)
    actual, original = float(gradient[k]), float(model.expert_projection.weight[k].detach())
    assert abs(actual) > 1e-12
    scores = []
    eps = 1e-5
    for sign in (1, -1):
        with torch.no_grad():
            model.expert_projection.weight[k] = original + sign * eps
        scores.append(request_gradient(predict_episode(model, e).detach().numpy(), e, prototype)[0])
    with torch.no_grad():
        model.expert_projection.weight[k] = original
    assert abs((scores[0] - scores[1]) / (2 * eps) - actual) < 5e-10


def test_invalid_unavailable_target_masked_before_arithmetic(prototype):
    e, _, _ = setup(prototype)
    targets = e.original.expert_targets.copy()
    targets[3, 5] = np.nan
    masked = expose_episode(replace(e.original, expert_targets=targets))
    assert np.isfinite(masked.expert_state).all()
    targets[0, 5] = np.nan
    with pytest.raises(ValueError, match="finite"):
        expose_episode(replace(e.original, expert_targets=targets))
