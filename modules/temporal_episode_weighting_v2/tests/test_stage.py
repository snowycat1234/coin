"""Synthetic fixed-update interruptions/slices; no historical optimizer fits."""

import copy
import json
from pathlib import Path
from types import SimpleNamespace

import pytest
import torch

from modules.temporal_episode_weighting_v2 import export, stage
from modules.temporal_episode_weighting_v2.tests.test_gradient import setup
from modules.temporal_expert_input.model import ExpertSelector
from modules.temporal_short_expansion.tests.test_checkpoint import assert_optimizer_equal
from modules.temporal_surrogate_resume_v2.stage import warm_parent
from modules.temporal_two_expert.checkpoint import make_optimizer
from modules.temporal_two_expert.comparison import PROTOCOL as PARENT_PROTOCOL
from modules.temporal_two_expert.comparison import train_arm as parent_train
from modules.temporal_two_expert.exact import sha
from modules.temporal_two_expert.model import Selector
from modules.temporal_two_expert.test_comparison import synthetic_gradient


def synthetic_setup(prototype, tmp_path, monkeypatch):
    episodes, example = setup(prototype)
    scaler = None
    # Reuse the same validated synthetic feature producer used by gradient tests.
    from modules.temporal_two_expert.test_temporal import samples

    _, scaler = samples(7)
    protocol = copy.deepcopy(stage.PROTOCOL)
    protocol["limits"].update(maximum_updates_per_fit=2, seconds_per_slice=60.0)
    protocol["diagnostics"] = [0, 1, 2]
    parent_protocol = copy.deepcopy(PARENT_PROTOCOL)
    parent_protocol["limits"].update(maximum_updates_per_fit=1, seconds_per_fit=60.0)
    parent_folder = tmp_path / "parent"
    parent_train(
        Selector(scaler, cash_enabled=True, zero_readout=True),
        [episodes[0].original.original],
        prototype,
        parent_folder,
        "synthetic",
        protocol=parent_protocol,
        gradient_function=synthetic_gradient,
    )

    def initialize(state, standardizer):
        base = Selector(standardizer, cash_enabled=True, zero_readout=True)
        previous, parent = warm_parent(parent_folder, base)
        model = ExpertSelector(base, input_enabled=True)
        optimizer = make_optimizer(model)
        for parameter in base.parameters():
            optimizer.state[parameter] = copy.deepcopy(previous.state[parameter])
        births = {
            name: 0 if name.startswith("base.") else parent["step"]
            for name, _ in model.named_parameters()
        }
        return model, optimizer, parent, births

    monkeypatch.setattr(stage, "initialize", initialize)
    monkeypatch.setattr(stage, "preserve", lambda *a, **kw: None)
    monkeypatch.setattr(
        stage, "inputs", lambda *a, **kw: (episodes, [], prototype, "synthetic", scaler)
    )
    frozen = {str(p): sha(p) for p in parent_folder.iterdir() if p.is_file()}
    assert example.parameter_count == 13699 and example.input_enabled
    return protocol, frozen


def snapshot(output, arm):
    folder = output / arm
    pointer = json.loads((folder / "latest.json").read_text())
    return torch.load(folder / pointer["file"], weights_only=True), pointer


def assert_same_completion(first_output, second_output, arm):
    first, _ = snapshot(first_output, arm)
    second, _ = snapshot(second_output, arm)
    assert first["step"] == second["step"] == 3
    assert first["model_identity"] == second["model_identity"]
    assert all(torch.equal(t, second["model"][k]) for k, t in first["model"].items())
    assert_optimizer_equal(first["optimizer"], second["optimizer"])
    assert first["trainer_state"]["history"] == second["trainer_state"]["history"]
    assert [d["snapshot_step"] for d in second["trainer_state"]["history"]] == [0, 1, 2]
    assert {float(s["step"]) for s in second["optimizer"]["state"].values()} == {2.0, 3.0}


@pytest.mark.parametrize("arm", stage.ARMS)
def test_interrupt_after_update_before_diagnostic_resumes_exactly(
    prototype, tmp_path, monkeypatch, arm
):
    protocol, frozen = synthetic_setup(prototype, tmp_path, monkeypatch)
    whole, resumed = tmp_path / "whole", tmp_path / "resumed"
    stage.prepare(None, whole, protocol=protocol)
    completed = stage.train_arm(None, whole, arm, protocol=protocol)
    assert completed["status"] == stage.SUCCESS and completed["completed_stage_updates"] == 2
    assert completed["fixed_update_target"] == 2
    rng = torch.get_rng_state().clone()
    stage.prepare(None, resumed, protocol=protocol)
    save, interrupted = stage.save_checkpoint, False

    def disconnect(*a, **kw):
        nonlocal interrupted
        pointer = save(*a, **kw)
        if kw["step"] == 2 and not interrupted:
            interrupted = True
            raise KeyboardInterrupt("disconnect after completed update before its diagnostic")
        return pointer

    monkeypatch.setattr(stage, "save_checkpoint", disconnect)
    with pytest.raises(KeyboardInterrupt):
        stage.train_arm(None, resumed, arm, protocol=protocol)
    partial, _ = snapshot(resumed, arm)
    assert partial["step"] == 2
    assert [d["snapshot_step"] for d in partial["trainer_state"]["history"]] == [0]
    monkeypatch.setattr(stage, "save_checkpoint", save)
    final = stage.train_arm(None, resumed, arm, protocol=protocol)
    assert (
        final["status"] == stage.SUCCESS and final["model_identity"] == completed["model_identity"]
    )
    assert torch.equal(torch.get_rng_state(), rng)
    assert_same_completion(whole, resumed, arm)
    assert all(sha(Path(path)) == expected for path, expected in frozen.items())


def test_slice_elapsed_above_budget_does_not_stop_next_invocation(prototype, tmp_path, monkeypatch):
    protocol, _ = synthetic_setup(prototype, tmp_path, monkeypatch)
    arm = stage.ARMS[1]
    whole, sliced = tmp_path / "whole", tmp_path / "sliced"
    stage.prepare(None, whole, protocol=protocol)
    expected = stage.train_arm(None, whole, arm, protocol=protocol)
    rng = torch.get_rng_state().clone()
    stage.prepare(None, sliced, protocol=protocol)
    clock = SimpleNamespace(now=0.0)
    monkeypatch.setattr(stage, "time", SimpleNamespace(monotonic=lambda: clock.now))
    save = stage.save_checkpoint

    def expire_after_first_update(*a, **kw):
        pointer = save(*a, **kw)
        if kw["step"] == 2:
            clock.now = 61.0
        return pointer

    monkeypatch.setattr(stage, "save_checkpoint", expire_after_first_update)
    first = stage.train_arm(None, sliced, arm, protocol=protocol)
    assert first["status"] == "SLICE_EXHAUSTED_RESUME_REQUIRED"
    assert first["completed_stage_updates"] == 1 and first["elapsed_seconds"] == 61
    assert not (sliced / arm / "TERMINAL.json").exists()
    _, pointer = snapshot(sliced, arm)
    assert pointer["elapsed_seconds"] > protocol["limits"]["seconds_per_slice"]
    monkeypatch.setattr(stage, "save_checkpoint", save)
    clock.now = 100.0  # new invocation starts a fresh local slice, despite prior elapsed61
    final = stage.train_arm(None, sliced, arm, protocol=protocol)
    assert (
        final["status"] == stage.SUCCESS and final["model_identity"] == expected["model_identity"]
    )
    assert final["completed_stage_updates"] == 2 and torch.equal(torch.get_rng_state(), rng)
    assert_same_completion(whole, sliced, arm)


def test_no_convergence_stop_and_exact_fixed_update_history(prototype, tmp_path, monkeypatch):
    protocol, _ = synthetic_setup(prototype, tmp_path, monkeypatch)
    assert "convergence" not in protocol
    output = tmp_path / "fixed"
    stage.prepare(None, output, protocol=protocol)
    first = stage.train_arm(None, output, stage.ARMS[0], protocol=protocol)
    assert first["status"] == stage.SUCCESS and first["completed_stage_updates"] == 2
    assert first["last_diagnostic"]["snapshot_step"] == 2
    # A completed arm is read back without another optimizer update.
    second = stage.train_arm(None, output, stage.ARMS[0], protocol=protocol)
    assert first == second


def test_second_update_failure_retains_completed_first_update(prototype, tmp_path, monkeypatch):
    protocol, frozen = synthetic_setup(prototype, tmp_path, monkeypatch)
    output, arm = tmp_path / "failed", stage.ARMS[0]
    stage.prepare(None, output, protocol=protocol)
    real, calls = stage.memory_bounded_gradients, 0

    def failure(model, *a, **kw):
        nonlocal calls
        calls += 1
        if calls == 2:
            with torch.no_grad():
                model.expert_projection.weight.fill_(float("nan"))
            raise ValueError("synthetic second update path failure")
        return real(model, *a, **kw)

    monkeypatch.setattr(stage, "memory_bounded_gradients", failure)
    result = stage.train_arm(None, output, arm, protocol=protocol)
    assert result["status"] == "STOP_NUMERICAL_OR_PATH_FAILURE"
    assert result["completed_stage_updates"] == 1 and result["cumulative_Adam_step"] == 2
    assert result["failure"]["attempted_stage_update"] == 2
    state, _ = snapshot(output, arm)
    assert all(torch.isfinite(t).all() for t in state["model"].values())
    assert state["trainer_state"]["completed_stage_updates"] == 1
    assert all(sha(Path(path)) == expected for path, expected in frozen.items())


@pytest.mark.parametrize("bad", ["missing", "count", "target", "failed"])
def test_seen_score_barrier_rejects_before_model_or_development_access(tmp_path, monkeypatch, bad):
    for index, arm in enumerate(stage.ARMS):
        if bad == "missing" and index == 1:
            continue
        folder = tmp_path / arm
        folder.mkdir()
        terminal = dict(status=stage.SUCCESS, completed_stage_updates=512, fixed_update_target=512)
        if index == 1:
            if bad == "count":
                terminal["completed_stage_updates"] = 511
            elif bad == "target":
                terminal["fixed_update_target"] = 1024
            elif bad == "failed":
                terminal["status"] = "STOP_NUMERICAL_OR_PATH_FAILURE"
        (folder / "TERMINAL.json").write_text(json.dumps(terminal))

    def forbidden(*a, **kw):
        raise AssertionError("model/development accessed before both fixed512 completions")

    monkeypatch.setattr(export, "frozen_arm", forbidden)
    with pytest.raises((FileNotFoundError, ValueError)):
        export.score(None, tmp_path)
    assert not (tmp_path / "BOTH_TERMINAL.json").exists()
