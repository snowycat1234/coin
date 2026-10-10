"""Payoff-direction, zero-gap, stable-gradient, adoption and exact-resume checks."""

import json

import numpy as np
import pytest
import torch

from modules.temporal_balanced_history.train import save
from modules.temporal_neutral_short.model import initialize
from modules.temporal_purged_supervised.experiment import load_checkpoint
from modules.temporal_two_expert.checkpoint import model_identity
from modules.temporal_two_expert.inputs import Standardizer

from .experiment import audit, train
from .objective import PAIRS, fit_scale, pairwise_loss
from .scoring import action_metrics, adoption_gate, comparison


def test_pair_log_ratio_analytic_and_finite_difference():
    logits = torch.tensor(
        [[0.4, -0.7, 0.2, 1.3], [-1.0, 0.6, 0.2, -0.5]], dtype=torch.float64, requires_grad=True
    )
    u = torch.tensor([[0.0, 0.02, 0.01, -0.05], [0.0, -0.01, 0.03, 0.03]], dtype=torch.float64)
    scale = 0.02
    loss = pairwise_loss(logits.softmax(1), u, scale)
    grad = torch.autograd.grad(loss, logits)[0]
    expected = torch.zeros_like(logits)
    for i, j in PAIRS:
        delta = u[:, i] - u[:, j]
        g = (
            delta.abs()
            / scale
            * ((logits[:, i] - logits[:, j]).sigmoid() - (delta > 0).to(logits.dtype))
            / (len(u) * 6)
        )
        expected[:, i] += g
        expected[:, j] -= g
    torch.testing.assert_close(grad, expected, rtol=1e-12, atol=1e-12)
    for row in range(2):
        for col in range(4):
            left, right = logits.detach().clone(), logits.detach().clone()
            left[row, col] += 1e-6
            right[row, col] -= 1e-6
            fd = (
                pairwise_loss(left.softmax(1), u, scale) - pairwise_loss(right.softmax(1), u, scale)
            ) / 2e-6
            torch.testing.assert_close(fd, grad[row, col], rtol=1e-6, atol=1e-9)


def test_zero_equal_gap_and_offset_invariance():
    logits = torch.tensor([[0.1, -0.4, 0.2, 2.0]], dtype=torch.float64, requires_grad=True)
    u = torch.ones_like(logits) * 0.2
    loss = pairwise_loss(logits.softmax(1), u, 0.01)
    assert float(loss) == 0
    assert torch.equal(torch.autograd.grad(loss, logits)[0], torch.zeros_like(logits))
    varied = torch.tensor([[0.0, 0.02, 0.01, -0.05]], dtype=torch.float64)
    torch.testing.assert_close(
        pairwise_loss(logits.softmax(1), varied, 0.01),
        pairwise_loss(logits.softmax(1), varied + 0.125, 0.01),
    )
    with pytest.raises(ValueError):
        fit_scale(u.detach().numpy())


def test_costly_wrong_SHORT_direction_tail_weighting_and_saturation():
    logits = torch.tensor([[0.0, 0.0, 0.0, 20.0]], dtype=torch.float64, requires_grad=True)
    u = torch.tensor([[0.0, 0.02, 0.01, -0.05]], dtype=torch.float64)
    loss = pairwise_loss(logits.softmax(1), u, 0.02)
    grad = torch.autograd.grad(loss, logits)[0]
    assert grad[0, 3] > 1 and grad[0, 1] < 0
    # Confidently wrong SHORT retains gradient rather than multiplying by tiny q_VOL.
    tail = pairwise_loss(logits.softmax(1), u * 3, 0.02)
    torch.testing.assert_close(torch.autograd.grad(tail, logits)[0], grad * 3)
    lesser = pairwise_loss(torch.zeros_like(logits).softmax(1), u, 0.02)
    assert loss > lesser
    correct_logits = torch.tensor([[0.0, 0.0, 0.0, -20.0]], dtype=torch.float64, requires_grad=True)
    good_u = torch.tensor([[0.0, 0.0, 0.0, 0.05]], dtype=torch.float64)
    good_grad = torch.autograd.grad(
        pairwise_loss(correct_logits.softmax(1), good_u, 0.02), correct_logits
    )[0]
    assert good_grad[0, 3] < -1
    extreme = torch.tensor(
        [[300.0, -300.0, 100.0, -100.0]], dtype=torch.float64, requires_grad=True
    )
    extreme_loss = pairwise_loss(extreme.softmax(1), u, 0.02)
    assert (
        torch.isfinite(extreme_loss)
        and torch.isfinite(torch.autograd.grad(extreme_loss, extreme)[0]).all()
    )


def test_scale_fourway_choices_and_no_forced_SHORT():
    u = np.array([[0.0, 0.02, 0.04, -0.05], [0.0, -0.01, -0.01, -0.01]])
    scale = fit_scale(u)
    assert scale == np.median(
        [abs(row[i] - row[j]) for row in u for i, j in PAIRS if row[i] != row[j]]
    )
    y = u.argmax(1)
    q = np.eye(4)[y]
    ce = np.tile([0.0, 1.0, 0.0, 0.0], (2, 1))
    score = action_metrics(q, y, u)
    assert score["predicted_counts"] == [1, 0, 1, 0] and score["SHORT_precision"] is None
    report = comparison(q, ce, y, u, np.array([0, 21 * 86400000000]), np.ones(4) / 4)
    assert adoption_gate(report)["passed"]
    tied = comparison(ce, ce, y, u, np.array([0, 21 * 86400000000]), np.ones(4) / 4)
    assert not adoption_gate(tied)["passed"]
    report["disjoint21_phase0"]["model_minus_reference_utility"]["matched_CE20"] = -0.001
    assert not adoption_gate(report)["passed"]


def test_failed_adoption_rejects_before_dataset_or_AUDIT_reads(tmp_path, monkeypatch):
    (tmp_path / "SELECTION.json").write_text(
        json.dumps({"status": "FAIL_STOP_NO2024_AUDIT", "gate": {"passed": False}})
    )

    def forbidden(*args):
        pytest.fail("Failed adoption must stop before data loading")

    monkeypatch.setitem(audit.__globals__, "checked_data", forbidden)
    with pytest.raises(AssertionError):
        audit(tmp_path, tmp_path, tmp_path / "nonexistent_receipt.json", {})
    assert not (tmp_path / "AUDIT_SCORES.json").exists()


def test_pairwise_atomic_checkpoint_dropout_adam_rng_exact_resume(tmp_path):
    torch.set_num_threads(1)
    torch.use_deterministic_algorithms(True)
    scaler = Standardizer(np.zeros(24), np.ones(24), np.ones(24, dtype=int), {"synthetic": True})
    model, optimizer = initialize(scaler)
    x = torch.randn(2, 64, 5, 24, dtype=torch.float64)
    mask, steps = torch.ones_like(x, dtype=torch.bool), torch.ones(2, 64, 5, dtype=torch.bool)
    expert = torch.zeros(2, 18, dtype=torch.float64)
    utility = torch.tensor(
        [[0.0, 0.02, 0.01, -0.05], [0.0, -0.01, 0.03, 0.03]], dtype=torch.float64
    )

    def update(m, o):
        permutation = np.random.permutation(2)
        m.train()
        o.zero_grad(set_to_none=True)
        q = m(x[permutation], mask[permutation], steps[permutation], expert[permutation])[
            :, [0, 1, 4, 5]
        ]
        pairwise_loss(q, utility[permutation], 0.02).backward()
        torch.nn.utils.clip_grad_norm_(m.parameters(), 1.0)
        o.step()
        o.zero_grad(set_to_none=True)
        return permutation

    update(model, optimizer)
    binding = {"synthetic": True}
    pointer = save(
        tmp_path,
        model,
        optimizer,
        1,
        binding,
        0.0,
        {"epoch": 0, "permutation": [1, 0], "offset": 1},
    )
    with pytest.raises(AssertionError):
        save(tmp_path, model, optimizer, 1, binding, 0.0, {})
    expected_perm = update(model, optimizer)
    expected = model_identity(model)
    moments = {
        k: {n: v.clone() for n, v in s.items()} for k, s in optimizer.state_dict()["state"].items()
    }
    restored, opt, snap = load_checkpoint(tmp_path, pointer, scaler, binding)
    assert snap["history"] == {"epoch": 0, "permutation": [1, 0], "offset": 1}
    np.testing.assert_array_equal(update(restored, opt), expected_perm)
    assert model_identity(restored) == expected
    for k, s in opt.state_dict()["state"].items():
        for name, value in s.items():
            assert torch.equal(value, moments[k][name])


def test_recover_final_minibatch_before_terminal_without_refitting(tmp_path, monkeypatch):
    import hashlib

    (tmp_path / "PLAN.json").write_text("{}")
    publication = {
        "status": "PAYOFF_PAIRWISE_PREFIT_PUBLIC_VERIFIED",
        "plan_SHA256": hashlib.sha256((tmp_path / "PLAN.json").read_bytes()).hexdigest(),
    }
    pub = tmp_path / "publication.json"
    pub.write_text(json.dumps(publication))
    pointer = {"step": 240, "path": "final.pt", "SHA256": "a" * 64}
    (tmp_path / "latest.json").write_text(json.dumps(pointer))
    (tmp_path / "READY.json").write_text(json.dumps({"binding": {}}))
    scaler = Standardizer(np.zeros(24), np.ones(24), np.ones(24, dtype=int), {"synthetic": True})
    model, optimizer = initialize(scaler)
    data = (None, None, None, None, None, scaler, None)
    monkeypatch.setitem(
        train.__globals__, "checked_data",
        lambda *args: ({"updates": 240}, data),
    )
    monkeypatch.setitem(
        train.__globals__, "arrays_for_role",
        lambda *args: (None, None, np.zeros((1, 4)), None),
    )
    monkeypatch.setitem(
        train.__globals__, "load_checkpoint",
        lambda *args: (model, optimizer, {"history": {"epoch": 20}, "step": 240, "elapsed": 5.}),
    )
    before = model_identity(model)
    train(tmp_path, tmp_path, pub, {"forbidden_2025_attempts": [], "state_file_opens": set()})
    terminal = json.loads((tmp_path / "TERMINAL.json").read_text())
    assert terminal["elapsed_training"] == 5. and terminal["step"] == 240
    assert terminal["snapshot"]["checkpoint"] == pointer and model_identity(model) == before
