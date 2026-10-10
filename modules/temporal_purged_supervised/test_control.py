"""Focused causality, scoring, and synthetic exact-resume regression tests."""

import numpy as np
import pytest
import torch

from modules.temporal_neutral_short.model import initialize
from modules.temporal_two_expert.checkpoint import _restore_rng, _rng_state, model_identity
from modules.temporal_two_expert.inputs import DAY_US, Standardizer, WindowBatch, fit_standardizer

from .inputs import CUTOFF, SELECT_END, TRAIN_END, role_indices, slice_windows
from .scoring import correct, disjoint_indices, metrics


def test_strict_maturity_and_both_purges():
    d = np.array(
        [
            TRAIN_END - 22 * DAY_US,
            TRAIN_END - 21 * DAY_US,
            TRAIN_END,
            SELECT_END - 22 * DAY_US,
            SELECT_END - 21 * DAY_US,
            SELECT_END,
        ]
    )
    a = d + 21 * DAY_US + 60000001
    roles = role_indices(d, a)
    assert roles["TRAIN"].tolist() == [0]
    assert roles["SELECT2023"].tolist() == [2, 3]
    assert roles["AUDIT2024"].tolist() == [5]
    assert roles["PURGED"].tolist() == [1, 4]
    with pytest.raises(ValueError):
        role_indices(np.array([CUTOFF]), np.array([CUTOFF + DAY_US]))


def test_prefix_scaler_ignores_validation_extreme_and_keeps64():
    decisions = np.array([TRAIN_END - 30 * DAY_US, TRAIN_END])
    clocks = decisions[:, None] - np.arange(63, -1, -1)[None] * DAY_US
    values = np.ones((2, 64, 5, 24), dtype=float)
    values[1] = 1e12
    valid = np.ones_like(values, dtype=bool)
    step = np.ones(values.shape[:-1], dtype=bool)
    available = np.broadcast_to(clocks[..., None, None], values.shape).copy()
    w = WindowBatch(values, valid, step, clocks, available, decisions, "a" * 64)
    prefix = slice_windows(w, np.array([0]))
    scaler = fit_standardizer([prefix], training_cutoff_us=TRAIN_END)
    np.testing.assert_array_equal(scaler.mean, np.ones(24))
    assert scaler.provenance["real_row_count"] == 64
    assert prefix.values.shape[1] == 64
    with pytest.raises(ValueError):
        fit_standardizer([w], training_cutoff_us=TRAIN_END)


def test_prior_correction_and_short_precision_vs_prevalence():
    prior = np.array([0.05, 0.45, 0.25, 0.25])
    weights = 1 / (4 * prior)
    q = np.ones((4, 4)) / 4
    np.testing.assert_allclose(correct(q, weights), np.tile(prior, (4, 1)))
    p = np.eye(4)[[3, 3, 1, 1]] * 0.8 + 0.05
    y = np.array([3, 1, 3, 1])
    score = metrics(p, y, np.zeros((4, 4)))
    assert score["SHORT_precision"] == 0.5 and score["SHORT_recall"] == 0.5
    assert score["SHORT_prevalence"] == 0.5 and score["SHORT_precision_lift"] == 1
    assert metrics(q, y, np.zeros((4, 4)))["SHORT_precision"] is None
    d = TRAIN_END + np.array([0, 1, 21, 42, 64]) * DAY_US
    assert disjoint_indices(d).tolist() == [0, 2, 3]


def test_synthetic_dropout_adam_rng_exact_resume(tmp_path):
    torch.set_num_threads(1)
    torch.use_deterministic_algorithms(True)
    scaler = Standardizer(np.zeros(24), np.ones(24), np.ones(24, dtype=int), {"synthetic": True})
    model, optimizer = initialize(scaler)
    x = torch.randn(2, 64, 5, 24, dtype=torch.float64)
    mask, steps = torch.ones_like(x, dtype=torch.bool), torch.ones(2, 64, 5, dtype=torch.bool)
    expert = torch.zeros(2, 18, dtype=torch.float64)

    def update(m, o):
        m.train()
        o.zero_grad(set_to_none=True)
        q = m(x, mask, steps, expert)[:, [0, 1, 4, 5]]
        loss = -q[torch.arange(2), torch.tensor([1, 3])].log().mean()
        loss.backward()
        torch.nn.utils.clip_grad_norm_(m.parameters(), 1.0)
        o.step()
        o.zero_grad(set_to_none=True)

    update(model, optimizer)
    path = tmp_path / "synthetic.pt"
    torch.save(
        {"model": model.state_dict(), "optimizer": optimizer.state_dict(), "rng": _rng_state()},
        path,
    )
    update(model, optimizer)
    expected = model_identity(model)
    expected_moments = {
        k: {n: v.clone() for n, v in s.items()} for k, s in optimizer.state_dict()["state"].items()
    }
    restored, restored_optimizer = initialize(scaler)
    saved = torch.load(path, weights_only=True)
    restored.load_state_dict(saved["model"])
    restored_optimizer.load_state_dict(saved["optimizer"])
    _restore_rng(saved["rng"])
    update(restored, restored_optimizer)
    assert model_identity(restored) == expected
    for k, s in restored_optimizer.state_dict()["state"].items():
        for name, value in s.items():
            assert torch.equal(value, expected_moments[k][name])
