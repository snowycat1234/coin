import copy
import json

import pytest
import torch

from modules.temporal_episode_weighting_v2.stage import tree_identity
from modules.temporal_history_expansion.data import new_episodes
from modules.temporal_history_expansion.gradient import memory_bounded_gradients
from modules.temporal_history_expansion.test_expansion import causal_fixture, economic_fixture
from modules.temporal_prequential_transfer.model import initialize
from modules.temporal_short_expansion.tests.test_checkpoint import assert_optimizer_equal
from modules.temporal_two_expert.checkpoint import _rng_state, model_identity, run_guard
from modules.temporal_two_expert.exact import sha
from modules.temporal_two_expert.inputs import digest, fit_standardizer
from modules.temporal_two_expert.test_temporal import samples

from . import stage
from .checkpoint import binding_for, load, optimizer_for, save, verify
from .protocol import ARM, protocol, sources, task
from .stage import optimizer_ages


def worker_fixture(tmp_path, monkeypatch, status="RUNNING", slices=0):
    _, scaler = samples()
    data = dict(synthetic=True, counts=dict(synthetic=True))
    monkeypatch.setattr(stage, "inputs", lambda *args: ([], None, data, scaler))
    output = tmp_path / "fit"
    stage.prepare(None, None, output)
    folder = output / ARM
    model, _ = initialize(scaler)
    optimizer = optimizer_for(model, task())
    binding = binding_for(model, data, task())
    saved, _ = load(folder, model, optimizer, binding)
    history = saved["trainer_state"]
    history.update(status=status, slices=slices)
    save(folder, model, optimizer, binding, step=0, elapsed=0.0, history=history)
    publication = tmp_path / "publication.json"
    publication.write_text(
        json.dumps(
            dict(
                status="PASS_ALL_PUBLIC_BYTES",
                remote_SHA="synthetic_publication",
                prefit_ready_SHA256=sha(output / "READY.json"),
            )
        )
    )
    assert json.loads((output / "READY.json").read_text())["sources"] == sources()
    return output, publication, folder, model, optimizer, binding


def test_saved_failure_without_terminal_is_not_retried(tmp_path, monkeypatch):
    output, publication, _, _, _, _ = worker_fixture(
        tmp_path, monkeypatch, status="STOP_NUMERICAL_OR_PATH_FAILURE"
    )

    def forbidden(*args, **kwargs):
        raise AssertionError("A saved failed fit must never request another gradient")

    monkeypatch.setattr(stage, "memory_bounded_gradients", forbidden)
    terminal = stage.worker(None, None, output, publication)
    assert terminal["status"] == "STOP_NUMERICAL_OR_PATH_FAILURE"
    assert terminal["completed_updates"] == 0
    assert set(terminal["optimizer_parameter_ages"].values()) == {0}


def test_hard_interrupt_before_first_update_consumes_bounded_slice(tmp_path, monkeypatch):
    output, publication, folder, model, optimizer, binding = worker_fixture(tmp_path, monkeypatch)

    def interrupted(*args, **kwargs):
        raise KeyboardInterrupt("Synthetic hard interruption before first Adam update")

    monkeypatch.setattr(stage, "memory_bounded_gradients", interrupted)
    for consumed in (1, 2, 3):
        with pytest.raises(KeyboardInterrupt):
            stage.worker(None, None, output, publication)
        saved, _ = load(folder, model, optimizer, binding)
        assert saved["step"] == 0 and saved["trainer_state"]["slices"] == consumed
    terminal = stage.worker(None, None, output, publication)
    assert terminal["status"] == "STOP_AUTHORIZED_RESOURCE_BUDGET"
    assert terminal["completed_updates"] == 0 and terminal["slices"] == 3


def test_durable_256_completion_precedes_slice_cap_without_new_gradient(tmp_path, monkeypatch):
    output, publication, folder, model, optimizer, binding = worker_fixture(
        tmp_path, monkeypatch, slices=3
    )
    saved, _ = load(folder, model, optimizer, binding)
    # Mechanical zero-gradient optimizer states; no feature inference or economic fitting.
    for _ in range(256):
        for parameter in model.parameters():
            parameter.grad = torch.zeros_like(parameter)
        optimizer.step()
        optimizer.zero_grad(set_to_none=True)
    history = saved["trainer_state"]
    history["completed_updates"] = 256
    save(folder, model, optimizer, binding, step=256, elapsed=1.0, history=history)

    def forbidden(*args, **kwargs):
        raise AssertionError("Completed256 must finalize without any gradient")

    monkeypatch.setattr(stage, "memory_bounded_gradients", forbidden)
    terminal = stage.worker(None, None, output, publication)
    assert terminal["status"] == "FIXED256_COMPLETE"
    assert terminal["completed_updates"] == 256 and terminal["slices"] == 3
    assert set(terminal["optimizer_parameter_ages"].values()) == {256}


def test_exact_expanded_recipe_and_fixed907_contract():
    _, scaler = samples()
    model, _ = initialize(scaler)
    optimizer = optimizer_for(model, task())
    binding = binding_for(model, dict(synthetic=True), task())
    verify(model, optimizer, binding)
    assert model.parameter_count == 13699 and not optimizer.state
    p = protocol()
    assert p["scaler_rows"] == 907 and p["scaler_refits"] == 0
    assert p["wallet_lengths"] == [365, 54, 88, 62, 144, 430]
    assert p["active_training_intervals"] == 1137 and p["training_decisions"] == 1143
    with pytest.raises(ValueError):
        optimizer_for(model, dict(task(), lr=0.001))
    forged = copy.deepcopy(binding)
    forged["specification"]["max_steps"] = 257
    forged["run_id"] = digest(forged["specification"])
    with pytest.raises(ValueError):
        verify(model, optimizer, forged)


def test_real_terminal_dropout_atomic_adam_rng_exact_resume_and_stepzero_failure(
    prototype, tmp_path
):
    causal = causal_fixture(prototype)
    episode = new_episodes(economic_fixture(causal), causal, prototype)[0][0]
    scaler = fit_standardizer([episode.windows], training_cutoff_us=episode.split_cutoff_us)
    model, _ = initialize(scaler)
    optimizer = optimizer_for(model, task())
    binding = binding_for(model, dict(synthetic=True), task())

    def step(m, o):
        m.train()
        o.zero_grad(set_to_none=True)
        loss, _ = memory_bounded_gradients(m, [episode], prototype, feature_batch_size=3)
        torch.nn.utils.clip_grad_norm_(m.parameters(), 1.0, error_if_nonfinite=True)
        o.step()
        o.zero_grad(set_to_none=True)
        return loss

    with run_guard(tmp_path / "refit", binding) as directory:
        save(
            directory,
            model,
            optimizer,
            binding,
            step=0,
            elapsed=0.0,
            history=dict(completed_updates=0),
        )
        identity, rng = model_identity(model), tree_identity(_rng_state())
        step(model, optimizer)
        # Restore initial snapshot as the first-update failure path must do.
        load(directory, model, optimizer, binding)
        assert model_identity(model) == identity and tree_identity(_rng_state()) == rng
        assert set(optimizer_ages(model, optimizer).values()) == {0}
        step(model, optimizer)
        save(
            directory,
            model,
            optimizer,
            binding,
            step=1,
            elapsed=1.0,
            history=dict(completed_updates=1),
        )
        expected_loss = step(model, optimizer)
        expected = (
            model_identity(model),
            tree_identity(_rng_state()),
            copy.deepcopy(optimizer.state_dict()),
        )
        restored, _ = initialize(scaler)
        other = optimizer_for(restored, task())
        load(directory, restored, other, binding)
        assert step(restored, other) == expected_loss
        assert (model_identity(restored), tree_identity(_rng_state())) == expected[:2]
        assert_optimizer_equal(expected[2], other.state_dict())
        assert set(optimizer_ages(restored, other).values()) == {2}
        with pytest.raises(ValueError):
            save(
                directory,
                restored,
                other,
                binding,
                step=257,
                elapsed=2.0,
                history=dict(completed_updates=257),
            )
