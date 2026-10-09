"""Exact replay, named representation, and synthetic stopping/resume tests."""

import copy
import json
from dataclasses import replace

import numpy as np
import pytest
import torch

from . import comparison
from .checkpoint import model_identity
from .exact import memory_bounded_gradients, training_loss
from .model import Selector, predict_windows
from .test_temporal import episode, samples
from .training_packet import NAMED_SLOTS, load_packet, named_context


@pytest.mark.parametrize("cash", [False, True])
def test_zero_readouts_match_architectures(cash):
    windows, scaler = samples(3)
    models = [
        Selector(scaler, family=f, cash_enabled=cash, zero_readout=True).train()
        for f in ("GRU64", "LATEST_MLP")
    ]
    outputs = [predict_windows(m, windows) for m in models]
    torch.testing.assert_close(outputs[0], outputs[1], rtol=0, atol=0)
    desired = [0.5, 0.25, 0.0, 0.0, 0.25] if cash else [0.0, 0.5, 0.0, 0.0, 0.5]
    torch.testing.assert_close(
        outputs[0], torch.tensor([desired] * 3, dtype=torch.float64), rtol=0, atol=0
    )


@pytest.mark.parametrize("family", ["GRU64", "LATEST_MLP"])
@pytest.mark.parametrize("cash", [False, True])
def test_replayed_exact_gradients_and_rng_match_full_graph(prototype, family, cash):
    e, scaler = episode(prototype, 8)
    mask = e.windows.step_valid.copy()
    valid = e.windows.valid.copy()
    mask[:, 12:15, 2] = False
    valid[:, 12:15, 2] = False
    e = replace(e, windows=replace(e.windows, step_valid=mask, valid=valid))
    model = Selector(scaler, family=family, cash_enabled=cash, dropout=0.2)
    torch.manual_seed(932)
    loss = training_loss(model, [e], prototype, feature_batch_size=3)
    loss.backward()
    expected = [p.grad.clone() for p in model.parameters()]
    rng = torch.get_rng_state().clone()
    model.zero_grad(set_to_none=True)
    torch.manual_seed(932)
    value, _ = memory_bounded_gradients(model, [e], prototype, feature_batch_size=3)
    assert value == float(loss.detach())
    assert torch.equal(torch.get_rng_state(), rng)
    for parameter, wanted in zip(model.parameters(), expected, strict=True):
        torch.testing.assert_close(parameter.grad, wanted, rtol=2e-12, atol=1e-15)


def test_named_context_parity_all_182_original_references(prototype, recovery):
    count = 0
    for name in ("H1_TRAIN", "BEAR2022NOV", "RECOVERY2023JAN"):
        with np.load(recovery / "direct_path_fragments" / (name + ".npz"), allow_pickle=False) as z:
            a = {k: z[k] for k in z.files}
        original, named = [], []
        for i, d in enumerate(a["decision_us"]):
            original.append(
                prototype.Context(
                    int(d),
                    int(d),
                    a["expert_targets"][i],
                    a["expert_eligible"][i],
                    a["past_returns30"][i],
                    a["market_state13"][i],
                    a["target_available_us"][i],
                )
            )
            named.append(
                named_context(
                    prototype,
                    int(d),
                    a["expert_targets"][i, NAMED_SLOTS],
                    a["expert_eligible"][i, NAMED_SLOTS],
                    a["past_returns30"][i],
                    np.zeros(13),
                    a["target_available_us"][i, NAMED_SLOTS],
                )
            )
        rng = np.random.default_rng(18)
        q = rng.dirichlet([1, 2, 3], len(named))
        requests = np.zeros((len(named), 5))
        requests[:, NAMED_SLOTS] = q
        targets, records = prototype.mapped_path(requests, original)
        actual, mapped = prototype.mapped_path(requests, named)
        np.testing.assert_array_equal(actual, targets)
        for old, new in zip(records, mapped, strict=True):
            np.testing.assert_array_equal(old["budget"], new["budget"])
        report = prototype.daily_proxy(targets, a["prices"], a["funding_coeff"])
        old = prototype.mapping_vjp(report["target_gradient"], records, original)
        new = prototype.mapping_vjp(report["target_gradient"], mapped, named)
        np.testing.assert_array_equal(old[:, NAMED_SLOTS], new[:, NAMED_SLOTS])
        assert all(not c.eligible[2:4].any() and not c.expert_targets[2:4].any() for c in named)
        count += len(named)
    assert count == 182


def test_convergence_requires_stable_train_loss_gradient_and_requests():
    rule = comparison.PROTOCOL["convergence"]
    history = [dict(loss=0.01, gradient_norm=0.01, request_change=0.0005)] * 5
    assert comparison.convergence_met(history, 1.0, 128, rule)
    assert not comparison.convergence_met(history, 1.0, 127, rule)
    assert not comparison.convergence_met(history, 0.01, 128, rule)
    assert not comparison.convergence_met(
        history[:-1] + [dict(history[-1], request_change=0.2)], 1.0, 128, rule
    )
    assert not comparison.convergence_met(
        history[:-1] + [dict(history[-1], loss=0.02)], 1.0, 128, rule
    )


def synthetic_gradient(model, episodes, prototype, *, feature_batch_size):
    output = predict_windows(model, episodes[0].windows, feature_batch_size=feature_batch_size)
    loss = (output - 0.31).square().sum() + 0.001 * sum(
        p.square().sum() for p in model.parameters()
    )
    loss.backward()
    return float(loss.detach()), output.detach().numpy()


def test_atomic_stopping_state_resume_exact_synthetic(prototype, tmp_path, monkeypatch):
    e, scaler = episode(prototype, 4)
    protocol = copy.deepcopy(comparison.PROTOCOL)
    protocol["limits"].update(maximum_updates_per_fit=4, seconds_per_fit=60.0)
    protocol["convergence"].update(evaluate_every=1, minimum_updates=20)

    def model():
        return Selector(scaler, family="LATEST_MLP", cash_enabled=True, zero_readout=True)

    whole = model()
    report = comparison.train_arm(
        whole,
        [e],
        prototype,
        tmp_path / "whole",
        "synthetic",
        protocol=protocol,
        gradient_function=synthetic_gradient,
    )
    assert report["status"] == "CAPPED_NOT_CONVERGED" and report["step"] == 4
    expected_rng = torch.get_rng_state().clone()
    original = comparison.save_checkpoint

    def interrupt(*args, **kwargs):
        result = original(*args, **kwargs)
        if kwargs["step"] == 2:
            raise RuntimeError("simulated disconnect after atomic snapshot")
        return result

    monkeypatch.setattr(comparison, "save_checkpoint", interrupt)
    with pytest.raises(RuntimeError, match="simulated disconnect"):
        comparison.train_arm(
            model(),
            [e],
            prototype,
            tmp_path / "resume",
            "synthetic",
            protocol=protocol,
            gradient_function=synthetic_gradient,
        )
    monkeypatch.setattr(comparison, "save_checkpoint", original)
    resumed = model()
    result = comparison.train_arm(
        resumed,
        [e],
        prototype,
        tmp_path / "resume",
        "synthetic",
        protocol=protocol,
        gradient_function=synthetic_gradient,
    )
    assert result["status"] == "CAPPED_NOT_CONVERGED" and result["step"] == 4
    assert model_identity(resumed) == model_identity(whole)
    assert torch.equal(expected_rng, torch.get_rng_state())
    histories = []
    for folder in ("whole", "resume"):
        root = tmp_path / folder
        histories.append(
            torch.load(
                root / json.loads((root / "latest.json").read_text())["file"], weights_only=True
            )
        )
    assert histories[0]["trainer_state"]["history"] == histories[1]["trainer_state"]["history"]
    for a, b in zip(
        histories[0]["optimizer"]["state"].values(),
        histories[1]["optimizer"]["state"].values(),
        strict=True,
    ):
        for k in a:
            torch.testing.assert_close(a[k], b[k], rtol=0, atol=0)


def test_packet_rejects_pending_before_data_access(tmp_path):
    from .exact import sha

    path = tmp_path / "PACKET.json"
    path.write_text(json.dumps(dict(schema="TEMPORAL_FROZEN_FOUR_FIT_PACKET_V1", status="PENDING")))
    with pytest.raises(ValueError, match="Frozen economic/input packet"):
        load_packet(path, sha(path), "nonexistent-prototype")


def test_all_four_frozen_before_seen_scoring_and_shared_scaler(prototype, tmp_path, monkeypatch):
    e, _ = episode(prototype, 4)
    offset = e.split_cutoff_us - e.start_us
    windows = replace(
        e.windows,
        decision_us=e.windows.decision_us + offset,
        completed_us=e.windows.completed_us + offset,
        available_us=e.windows.available_us + offset,
    )
    contexts = tuple(
        replace(
            c,
            decision_us=c.decision_us + offset,
            available_us=c.available_us + offset,
            target_available_us=c.target_available_us + offset,
        )
        for c in e.contexts
    )
    dev = replace(
        e,
        wallet_id="seen",
        role="SEEN_VALIDATION",
        windows=windows,
        contexts=contexts,
        start_us=e.start_us + offset,
        end_us=e.end_us + offset,
        split_cutoff_us=e.split_cutoff_us + offset,
        label_available_us=e.label_available_us + offset,
    )
    calls = []

    def arm(model, *args, **kwargs):
        calls.append((model.family, model.cash_enabled))
        return dict(status="CAPPED_NOT_CONVERGED", model_identity=model_identity(model), step=0)

    def score(*args):
        assert (tmp_path / "run" / "ALL_FOUR_TERMINAL.json").exists() and len(calls) == 4
        return (
            0.0,
            None,
            dict(
                net_PnL=0.0,
                utility_sum=0.0,
                fees=0.0,
                spread=0.0,
                slippage=0.0,
                funding=0.0,
                terminal_cash_realized=True,
                status="SYNTHETIC",
            ),
        )

    monkeypatch.setattr(comparison, "train_arm", arm)
    monkeypatch.setattr(comparison, "request_loss_and_gradient", score)
    first = comparison.run_comparison(
        [e], [dev], prototype, tmp_path / "run", packet_identity="synthetic"
    )
    assert first["actual_fits"] == 4 and first["status"] == "CAPPED_COMPARISON_NOT_CONVERGED"
    proof = json.loads((tmp_path / "run" / "SCALER.json").read_text())
    assert proof["fit_count"] == 1
    monkeypatch.setattr(
        comparison, "fit_standardizer", lambda *a, **k: pytest.fail("must not refit scaler")
    )
    second = comparison.run_comparison(
        [e], [dev], prototype, tmp_path / "run", packet_identity="synthetic"
    )
    assert second == first and len(calls) == 4
