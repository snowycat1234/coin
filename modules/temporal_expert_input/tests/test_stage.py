"""Synthetic two-stage interruption and failure recovery, never historical fitting."""

import copy
import json
from pathlib import Path

import numpy as np
import pytest
import torch

from modules.temporal_expert_input import export, stage
from modules.temporal_expert_input.inputs import expose_episode
from modules.temporal_expert_input.model import ExpertSelector
from modules.temporal_short_expansion.adapter import append_episode
from modules.temporal_surrogate_resume_v2.stage import warm_parent
from modules.temporal_two_expert.checkpoint import make_optimizer
from modules.temporal_two_expert.comparison import train_arm as original_train
from modules.temporal_two_expert.exact import sha
from modules.temporal_two_expert.model import Selector
from modules.temporal_two_expert.test_comparison import synthetic_gradient
from modules.temporal_two_expert.test_temporal import episode


def synthetic_setup(prototype, tmp_path, monkeypatch):
    e, scaler = episode(prototype, 4, release=False)
    protocol = copy.deepcopy(stage.PROTOCOL)
    protocol["limits"].update(maximum_updates_per_fit=2, seconds_per_fit=60.0)
    protocol["convergence"].update(evaluate_every=1, minimum_updates=20)
    parent_protocol = copy.deepcopy(protocol)
    parent_protocol["limits"]["maximum_updates_per_fit"] = 1
    parent_folder = tmp_path / "parent"
    original_train(
        Selector(scaler, cash_enabled=True, zero_readout=True),
        [e],
        prototype,
        parent_folder,
        "synthetic",
        protocol=parent_protocol,
        gradient_function=synthetic_gradient,
    )
    short = np.full((4, 1, 5), -0.01)
    expanded = append_episode(
        e, short, np.ones((4, 1), bool), e.windows.decision_us[:, None], prototype, "a" * 64
    )

    def initialize(state, standardizer, enabled):
        base = Selector(standardizer, cash_enabled=True, zero_readout=True)
        old, parent = warm_parent(parent_folder, base)
        model = ExpertSelector(base, input_enabled=enabled)
        optimizer = make_optimizer(model)
        for p in base.parameters():
            optimizer.state[p] = copy.deepcopy(old.state[p])
        births = {
            n: 0 if n.startswith("base.") else parent["step"] for n, _ in model.named_parameters()
        }
        return model, optimizer, parent, births

    monkeypatch.setattr(stage, "initialize", initialize)
    monkeypatch.setattr(
        stage,
        "inputs",
        lambda *a, **kw: ([expose_episode(expanded)], [], prototype, "synthetic", scaler),
    )
    frozen = {str(p): sha(p) for p in parent_folder.iterdir() if p.is_file()}
    return protocol, initialize, scaler, frozen


@pytest.mark.parametrize("enabled", [False, True])
def test_stage_interrupt_resume_keeps_parent_and_exact_next_update(
    prototype, tmp_path, monkeypatch, enabled
):
    protocol, initialize, scaler, frozen = synthetic_setup(prototype, tmp_path, monkeypatch)
    arm = stage.ARMS[int(enabled)]

    def ready(name):
        folder = tmp_path / name
        folder.mkdir()
        model, _, parent, births = initialize(None, scaler, enabled)
        binding = stage.binding_for(model, parent, births, "synthetic", protocol)
        (folder / "READY.json").write_text(json.dumps(dict(arms={arm: dict(binding=binding)})))
        return folder

    whole = ready("whole")
    result = stage.train_arm(None, whole, arm, protocol=protocol)
    assert result["completed_stage_updates"] == 2 and result["cumulative_Adam_step"] == 3
    rng = torch.get_rng_state().clone()
    resumed = ready("resumed")
    save = stage.save_checkpoint

    def interrupt(*args, **kw):
        pointer = save(*args, **kw)
        if kw["step"] == 2:
            raise KeyboardInterrupt("disconnect after atomic completed update")
        return pointer

    monkeypatch.setattr(stage, "save_checkpoint", interrupt)
    with pytest.raises(KeyboardInterrupt):
        stage.train_arm(None, resumed, arm, protocol=protocol)
    monkeypatch.setattr(stage, "save_checkpoint", save)
    final = stage.train_arm(None, resumed, arm, protocol=protocol)
    assert final["model_identity"] == result["model_identity"] and torch.equal(
        rng, torch.get_rng_state()
    )
    histories = []
    for folder in (whole, resumed):
        p = json.loads((folder / arm / "latest.json").read_text())
        s = torch.load(folder / arm / p["file"], weights_only=True)
        histories.append(s["trainer_state"]["history"])
        assert {float(v["step"]) for v in s["optimizer"]["state"].values()} == {2.0, 3.0}
    assert histories[0] == histories[1] and all(sha(Path(p)) == h for p, h in frozen.items())


def test_failure_retains_atomic_parent_step(prototype, tmp_path, monkeypatch):
    protocol, initialize, scaler, frozen = synthetic_setup(prototype, tmp_path, monkeypatch)
    model, _, parent, births = initialize(None, scaler, True)
    arm = stage.ARMS[1]
    out = tmp_path / "bad"
    out.mkdir()
    binding = stage.binding_for(model, parent, births, "synthetic", protocol)
    (out / "READY.json").write_text(json.dumps(dict(arms={arm: dict(binding=binding)})))

    def fail(*a, **kw):
        raise ValueError("synthetic nonfinite path witness")

    monkeypatch.setattr(stage, "memory_bounded_gradients", fail)
    result = stage.train_arm(None, out, arm, protocol=protocol)
    assert (
        result["status"] == "STOP_NUMERICAL_OR_PATH_FAILURE"
        and result["completed_stage_updates"] == 0
    )
    assert result["failure"]["phase"] == "initial_training_evaluation"
    assert all(sha(Path(p)) == h for p, h in frozen.items())


def test_seen_score_barrier_precedes_any_model_or_economic_access(tmp_path, monkeypatch):
    first = tmp_path / stage.ARMS[0]
    first.mkdir()
    (first / "TERMINAL.json").write_text(json.dumps(dict(status="CAPPED_NOT_CONVERGED")))

    def forbidden(*a, **kw):
        raise AssertionError("seen or model access before both terminals")

    monkeypatch.setattr(export, "frozen_arm", forbidden)
    with pytest.raises(FileNotFoundError):
        export.score(None, tmp_path)
    assert not (tmp_path / "BOTH_TERMINAL.json").exists()
