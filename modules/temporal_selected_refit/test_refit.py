import copy

import pytest
import torch

from modules.temporal_episode_weighting_v2.gradient import memory_bounded_gradients
from modules.temporal_episode_weighting_v2.stage import tree_identity
from modules.temporal_prequential_transfer.model import initialize
from modules.temporal_prequential_transfer.test_transfer import prefix, synthetic
from modules.temporal_short_expansion.tests.test_checkpoint import assert_optimizer_equal
from modules.temporal_two_expert.checkpoint import _rng_state, model_identity, run_guard
from modules.temporal_two_expert.inputs import digest, fit_standardizer
from modules.temporal_two_expert.test_temporal import samples

from .checkpoint import binding_for, load, optimizer_for, save, verify
from .protocol import task
from .stage import ARM


def test_exact_single_recipe_and256_binding():
    _, scaler = samples()
    model, _ = initialize(scaler)
    settings = task(ARM)
    optimizer = optimizer_for(model, settings)
    binding = binding_for(model, dict(scaler=scaler.identity), settings)
    verify(model, optimizer, binding)
    assert model.parameter_count == 13699 and not optimizer.state
    assert binding["specification"]["max_steps"] == 256
    assert optimizer.param_groups[0]["lr"] == 0.0003
    with pytest.raises(ValueError, match="approved"):
        optimizer_for(model, dict(settings, lr=0.00031))
    forged = copy.deepcopy(binding)
    forged["specification"]["max_steps"] = 257
    forged["run_id"] = digest(forged["specification"])
    with pytest.raises(ValueError, match="binding"):
        verify(model, optimizer, forged)


def test_dropout_adam_all_rng_exact_resume_and_cap(prototype, tmp_path):
    expanded, clocks, cutoff = synthetic(prototype)
    episode = prefix(expanded, clocks, cutoff)
    scaler = fit_standardizer([episode.windows], training_cutoff_us=cutoff)
    model, _ = initialize(scaler)
    settings = task(ARM)
    optimizer = optimizer_for(model, settings)
    binding = binding_for(model, dict(scaler=scaler.identity, synthetic=True), settings)

    def update(m, o):
        m.train()
        o.zero_grad(set_to_none=True)
        loss, _ = memory_bounded_gradients(m, [episode], prototype, mixing=0.0)
        torch.nn.utils.clip_grad_norm_(m.parameters(), 1.0, error_if_nonfinite=True)
        o.step()
        o.zero_grad(set_to_none=True)
        return loss

    update(model, optimizer)
    with run_guard(tmp_path / "refit", binding) as folder:
        save(
            folder,
            model,
            optimizer,
            binding,
            step=1,
            elapsed=1.0,
            history=dict(completed_updates=1),
        )
        expected_loss = update(model, optimizer)
        expected = (
            model_identity(model),
            tree_identity(_rng_state()),
            copy.deepcopy(optimizer.state_dict()),
        )
        restored, _ = initialize(scaler)
        other = optimizer_for(restored, settings)
        load(folder, restored, other, binding)
        assert update(restored, other) == expected_loss
        assert (model_identity(restored), tree_identity(_rng_state())) == expected[:2]
        assert_optimizer_equal(expected[2], other.state_dict())
        with pytest.raises(ValueError):
            save(
                folder,
                restored,
                other,
                binding,
                step=257,
                elapsed=2.0,
                history=dict(completed_updates=257),
            )
