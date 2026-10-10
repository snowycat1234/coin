import copy

import pytest
import torch

from modules.temporal_episode_weighting_v2.gradient import memory_bounded_gradients
from modules.temporal_episode_weighting_v2.stage import tree_identity
from modules.temporal_prequential_transfer.model import initialize, parameter_identity
from modules.temporal_prequential_transfer.test_transfer import (
    prefix,
    synthetic,
    test_terminal_maturity_rejects_future_active_interval as original_maturity_check,
    test_future_suffix_cannot_change_prefix_scaler_loss_gradient_or_rng as original_future_check,
)
from modules.temporal_short_expansion import checkpoint as old
from modules.temporal_short_expansion.tests.test_checkpoint import assert_optimizer_equal
from modules.temporal_two_expert.checkpoint import OPTIMIZER, _rng_state, model_identity, run_guard
from modules.temporal_two_expert.inputs import digest, fit_standardizer
from modules.temporal_two_expert.test_temporal import samples

from modules.temporal_small_tuning.checkpoint import binding_for, load, optimizer_for, save, verify
from modules.temporal_small_tuning.protocol import plan, task
from modules.temporal_small_tuning.stage import register_validation


def test_only_approved_overrides_and_original_contract_preserved():
    _, scaler = samples()
    raw, rng = set(), set()
    old_configuration = copy.deepcopy(OPTIMIZER)
    for settings in plan()["actual_fit_tasks"][:3]:
        model, _ = initialize(scaler)
        optimizer = optimizer_for(model, settings)
        binding = binding_for(model, dict(scaler=scaler.identity), settings)
        verify(model, optimizer, binding)
        raw.add(parameter_identity(model))
        rng.add(tree_identity(_rng_state()))
        assert not optimizer.state and model.parameter_count == 13699
        if settings["lr"] != 0.001:
            with pytest.raises(ValueError, match="configuration|contract"):
                old._verify_optimizer_contract(model, optimizer)
        changed = dict(settings, lr=0.00031)
        with pytest.raises(ValueError, match="approved"):
            optimizer_for(model, changed)
        forged = copy.deepcopy(binding)
        forged["specification"]["algorithm"]["task"]["wallet_equal_mix"] = 0.2
        forged["run_id"] = digest(forged["specification"])
        with pytest.raises(ValueError, match="binding"):
            verify(model, optimizer, forged)
    assert len(raw) == len(rng) == 1 and OPTIMIZER == old_configuration


@pytest.mark.parametrize("candidate", ("BASE_DATE_LR1E3", "LOW_LR3E4", "MIXED_WALLET_HALF"))
def test_exact_dropout_and_adam_resume_with_approved_lr(prototype, tmp_path, candidate):
    expanded, clocks, cutoff = synthetic(prototype)
    episode = prefix(expanded, clocks, cutoff)
    scaler = fit_standardizer([episode.windows], training_cutoff_us=cutoff)
    settings = task("FOLD_20240101__" + candidate)
    model, _ = initialize(scaler)
    optimizer = optimizer_for(model, settings)
    binding = binding_for(model, dict(scaler=scaler.identity, synthetic=True), settings)

    def update(model, optimizer):
        model.train()
        optimizer.zero_grad(set_to_none=True)
        loss, _ = memory_bounded_gradients(
            model, [episode], prototype, mixing=settings["wallet_equal_mix"]
        )
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0, error_if_nonfinite=True)
        optimizer.step()
        optimizer.zero_grad(set_to_none=True)
        return loss

    first = update(model, optimizer)
    with run_guard(tmp_path / candidate, binding) as folder:
        save(
            folder,
            model,
            optimizer,
            binding,
            step=1,
            elapsed=1.0,
            history=dict(completed_updates=1, loss=first),
        )
        second = update(model, optimizer)
        identity, state, rng = (
            model_identity(model),
            copy.deepcopy(optimizer.state_dict()),
            tree_identity(_rng_state()),
        )
        restored, _ = initialize(scaler)
        other = optimizer_for(restored, settings)
        saved, _ = load(folder, restored, other, binding)
        assert saved["step"] == 1
        assert update(restored, other) == second
        assert model_identity(restored) == identity and tree_identity(_rng_state()) == rng
        assert_optimizer_equal(state, other.state_dict())
        wrong = binding_for(restored, dict(scaler=scaler.identity, changed=True), settings)
        with pytest.raises(ValueError, match="identity"):
            load(folder, restored, other, wrong)


def test_frozen_checkpoint_schedule_patience_and_ties():
    history = dict(validation=[], best=None, stale_checks=0, status="RUNNING")
    for step, value in ((256, 0.04), (384, 0.03), (512, 0.03), (640, 0.03)):
        register_validation(history, dict(step=step, utility_excess=value))
        assert history["status"] == ("EARLY_STOP_RULE" if step == 640 else "RUNNING")
    assert history["best"]["step"] == 256 and history["stale_checks"] == 3
    with pytest.raises(ValueError, match="counted once"):
        register_validation(history, dict(step=640, utility_excess=0.02))
    with pytest.raises(ValueError, match="approved"):
        register_validation(history, dict(step=700, utility_excess=100.0))


def test_reused_causal_prefix_maturity(prototype):
    original_maturity_check(prototype)


def test_reused_future_suffix_invariance(prototype):
    original_future_check(prototype)
