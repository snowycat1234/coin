"""Synthetic resume and replay safeguards; zero historical optimizer updates."""

import copy
import json
from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest
import torch

from modules.temporal_risk_proxy_v2.proxy import BoundaryPlan, charged_path_loss
from modules.temporal_two_expert.checkpoint import model_identity
from modules.temporal_two_expert.comparison import train_arm
from modules.temporal_two_expert.exact import sha
from modules.temporal_two_expert.model import Selector, predict_windows
from modules.temporal_two_expert.test_comparison import synthetic_gradient
from modules.temporal_two_expert.test_temporal import episode

from . import stage
from .gradient import memory_bounded_gradients_v2


@pytest.mark.parametrize("family", ["GRU64", "LATEST_MLP"])
@pytest.mark.parametrize("cash", [False, True])
def test_charged_replay_matches_full_graph_and_single_dropout_stream(prototype, family, cash):
    e, scaler = episode(prototype, 8)
    model = Selector(scaler, family=family, cash_enabled=cash, dropout=0.2)
    torch.manual_seed(532)
    requests = predict_windows(model, e.windows, feature_batch_size=3)
    loss = charged_path_loss(requests, e, prototype, plan=BoundaryPlan.full_fill_diagnostic(8))
    loss.backward()
    wanted = [p.grad.clone() for p in model.parameters()]
    rng = torch.get_rng_state().clone()
    model.zero_grad(set_to_none=True)
    torch.manual_seed(532)
    value, _ = memory_bounded_gradients_v2(model, [e], prototype, feature_batch_size=3)
    assert value == float(loss.detach()) and torch.equal(rng, torch.get_rng_state())
    for parameter, expected in zip(model.parameters(), wanted, strict=True):
        torch.testing.assert_close(parameter.grad, expected, rtol=2e-12, atol=1e-15)


def create_parent(prototype, tmp_path):
    e, scaler = episode(prototype, 4)
    protocol = copy.deepcopy(stage.PROTOCOL_V2)
    protocol["limits"].update(maximum_updates_per_fit=2, seconds_per_fit=60.0)
    protocol["convergence"].update(evaluate_every=1, minimum_updates=20)

    def model():
        return Selector(scaler, family="LATEST_MLP", cash_enabled=True, zero_readout=True)

    train_arm(
        model(),
        [e],
        prototype,
        tmp_path / "parent",
        "synthetic",
        protocol=protocol,
        gradient_function=synthetic_gradient,
    )
    return e, model, {str(p): sha(p) for p in (tmp_path / "parent").iterdir() if p.is_file()}


def test_warm_moments_cumulative_steps_rng_and_interrupt_resume(prototype, tmp_path, monkeypatch):
    e, model, parent_bytes = create_parent(prototype, tmp_path)
    protocol = copy.deepcopy(stage.PROTOCOL_V2)
    protocol["limits"].update(maximum_updates_per_fit=4, seconds_per_fit=60.0)
    protocol["convergence"].update(evaluate_every=1, minimum_updates=20)
    whole = model()
    report = stage.train_stage(
        whole,
        [e],
        prototype,
        tmp_path / "parent",
        tmp_path / "whole",
        "synthetic",
        protocol=protocol,
        gradient_function=synthetic_gradient,
    )
    assert report["completed_stage_updates"] == 4 and report["cumulative_Adam_step"] == 6
    wanted_rng = torch.get_rng_state().clone()
    original = stage.save_checkpoint

    def interrupted(*args, **kwargs):
        pointer = original(*args, **kwargs)
        if kwargs["step"] == 4:
            raise KeyboardInterrupt("synthetic disconnect after atomic update")
        return pointer

    monkeypatch.setattr(stage, "save_checkpoint", interrupted)
    with pytest.raises(KeyboardInterrupt):
        stage.train_stage(
            model(),
            [e],
            prototype,
            tmp_path / "parent",
            tmp_path / "resume",
            "synthetic",
            protocol=protocol,
            gradient_function=synthetic_gradient,
        )
    monkeypatch.setattr(stage, "save_checkpoint", original)
    resumed = model()
    result = stage.train_stage(
        resumed,
        [e],
        prototype,
        tmp_path / "parent",
        tmp_path / "resume",
        "synthetic",
        protocol=protocol,
        gradient_function=synthetic_gradient,
    )
    assert result["cumulative_Adam_step"] == 6 and result["completed_stage_updates"] == 4
    assert model_identity(resumed) == model_identity(whole) and torch.equal(
        wanted_rng, torch.get_rng_state()
    )
    histories = []
    for folder in ("whole", "resume"):
        pointer = json.loads((tmp_path / folder / "latest.json").read_text())
        saved = torch.load(tmp_path / folder / pointer["file"], weights_only=True)
        histories.append(saved["trainer_state"]["history"])
        assert {float(s["step"]) for s in saved["optimizer"]["state"].values()} == {6.0}
    assert histories[0] == histories[1]
    assert all(sha(Path(p)) == value for p, value in parent_bytes.items())


def test_failure_retains_last_atomic_update_and_original_parent(prototype, tmp_path):
    e, model, parent_bytes = create_parent(prototype, tmp_path)
    protocol = copy.deepcopy(stage.PROTOCOL_V2)
    protocol["limits"].update(maximum_updates_per_fit=4, seconds_per_fit=60.0)
    calls = 0

    def fail(model, episodes, prototype, *, feature_batch_size):
        nonlocal calls
        calls += 1
        if calls == 3:
            raise ValueError("synthetic numerical failure")
        return synthetic_gradient(model, episodes, prototype, feature_batch_size=feature_batch_size)

    result = stage.train_stage(
        model(),
        [e],
        prototype,
        tmp_path / "parent",
        tmp_path / "failed",
        "synthetic",
        protocol=protocol,
        gradient_function=fail,
    )
    assert result["status"] == "STOP_V2_NUMERICAL_OR_PATH_FAILURE"
    assert result["completed_stage_updates"] == 1 and result["cumulative_Adam_step"] == 3
    assert result["failure"]["attempted_stage_update"] == 2
    assert all(sha(Path(p)) == value for p, value in parent_bytes.items())


def test_protocol_keeps_fixed_training_choices_and_versioned_surrogate():
    from modules.temporal_two_expert.comparison import PROTOCOL

    for key in (
        "seed",
        "dropout",
        "feature_batch_size",
        "optimizer",
        "fixed_expert_set",
        "convergence",
    ):
        assert stage.PROTOCOL_V2[key] == PROTOCOL[key]
    assert stage.PROTOCOL_V2["objective"]["minute_native"] is False
    assert stage.PROTOCOL_V2["limits"]["maximum_concurrent_arms"] == 2
    assert stage.PROTOCOL_V2["model_observed_wallet"] is False


def test_terminal_barrier_and_complete_frozen_request_export(prototype, tmp_path, monkeypatch):
    from modules.temporal_two_expert.comparison import ARMS

    from . import export

    e, scaler = episode(prototype, 4)
    dev = replace(e, wallet_id="synthetic-seen-wallet", role="SEEN_VALIDATION")
    protocol = copy.deepcopy(stage.PROTOCOL_V2)
    protocol["limits"].update(maximum_updates_per_fit=1, seconds_per_fit=60.0)
    parent = tmp_path / "state/four-fit"
    parent.mkdir(parents=True)
    np.savez(parent / "SCALER.npz", mean=scaler.mean, scale=scaler.scale, count=scaler.count)
    (parent / "SCALER.json").write_text("{}")
    output = tmp_path / "v2"
    output.mkdir()
    (output / "RUN.json").write_text('{"scope":"synthetic_test_only"}')
    monkeypatch.setattr(
        export, "load_inputs", lambda state: ([e], [dev], prototype, "synthetic", scaler)
    )
    for index, (family, cash) in enumerate(ARMS):
        name = family + ("_WITH_CASH" if cash else "_NO_CASH")

        def model(family=family, cash=cash):
            return Selector(scaler, family=family, cash_enabled=cash, zero_readout=True)

        train_arm(
            model(),
            [e],
            prototype,
            parent / name,
            "synthetic",
            protocol=protocol,
            gradient_function=synthetic_gradient,
        )
        stage.train_stage(
            model(),
            [e],
            prototype,
            parent / name,
            output / name,
            "synthetic",
            protocol=protocol,
            gradient_function=synthetic_gradient,
        )
        if index < 3:
            with pytest.raises(FileNotFoundError):
                export.freeze_and_export(tmp_path / "state", output)
            assert not (output / "ALL_FOUR_TERMINAL.json").exists()
    result = export.freeze_and_export(tmp_path / "state", output)
    assert len(result["arms"]) == 4 and result["clean_new_comparison"] is False
    handoff = json.loads((output / "NATIVE_HANDOFF.json").read_text())
    assert len(handoff["paths"]) == 8 and handoff["native_execution_results"] is False
    with np.load(output / "FROZEN_DAILY_REQUEST_PATHS.npz", allow_pickle=False) as z:
        for path in handoff["paths"]:
            request = z[path["key"] + "__requests_E5"]
            np.testing.assert_array_equal(request[:, 2:4], 0.0)
            np.testing.assert_array_equal(z[path["key"] + "__net_targets"][-1], 0.0)
    assert (output / "TERMINAL_MODELS_ADAM_RNG.zip").exists()
