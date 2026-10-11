"""Causal and numerical tests, not market PnL or extra scientific fits."""

from pathlib import Path

import numpy as np
import pytest
import torch

from . import sharpe
from .core import DAY_US, FrozenGP, Scaler

torch.set_num_threads(1)


def test_decision_mask_past_only_gap_asset_and_positive_vol():
    x = np.ones((20, 5, 10))
    vol = np.ones((20, 5))
    original = sharpe.decision_mask(x, vol, 3)
    x[7, 2] = np.nan
    vol[4, 3] = 0
    masked = sharpe.decision_mask(x, vol, 3)
    assert not masked[7:10, 2].any()
    assert masked[10, 2] and not masked[4, 3]
    np.testing.assert_array_equal(masked[:, :2], original[:, :2])
    x[15:] = np.nan
    np.testing.assert_array_equal(sharpe.decision_mask(x, vol, 3)[:15], masked[:15])


def test_calendar_strict_label_maturity_purges_equality():
    clock = np.arange(20) * DAY_US
    axis = sharpe.calendar_axis(clock, 5 * DAY_US, 10 * DAY_US)
    np.testing.assert_array_equal(axis, [5, 6, 7, 8])
    assert np.all(clock[axis] + DAY_US < 10 * DAY_US)


def test_future_missing_outcome_never_changes_decision_cash_mask_even_zero_position():
    x = np.ones((20, 5, 10))
    vol = np.ones((20, 5))
    mask = sharpe.decision_mask(x, vol, 3)[[5, 6, 7]]
    r = np.ones((20, 5))
    r[7, 2] = np.nan
    outcomes, missing = sharpe.scaled_outcomes(np.array([5, 6, 7]), mask, r, vol)
    np.testing.assert_array_equal(mask, np.ones((3, 5), dtype=bool))
    np.testing.assert_array_equal(missing, [[1, 2]])
    with pytest.raises(sharpe.InvalidScore, match="Eligible"):
        sharpe.capture(np.zeros((3, 5)), mask, outcomes)
    mask[1, 2] = False
    outcomes, missing = sharpe.scaled_outcomes(np.array([5, 6, 7]), mask, r, vol)
    assert len(missing) == 0 and outcomes[1, 2] == 0


def test_current_vol_next_return_alignment_and_fixed_five_asset_denominator():
    r = np.zeros((20, 5))
    r[6] = 0.03
    vol = np.ones((20, 5))
    vol[5] = 0.02
    vol[6] = 900
    mask = np.array([[True, True, True, False, False]])
    outcomes, missing = sharpe.scaled_outcomes(np.array([5]), mask, r, vol)
    assert not len(missing)
    np.testing.assert_allclose(outcomes[mask], sharpe.RATE * 1.5)
    captured = sharpe.capture(np.full((1, 5), 0.5), mask, outcomes)
    assert (captured.sum(axis=1) / 5)[0] == pytest.approx(3 * 0.5 * sharpe.RATE * 1.5 / 5)


def test_sharpe_loss_matches_frozen_moments_and_has_finite_gradient():
    p = torch.tensor([0.3, -0.2, 0.5, 0.1], dtype=torch.float64, requires_grad=True)
    y = torch.tensor([0.01, 0.03, -0.02, 0.05], dtype=torch.float64)
    z = p.detach().numpy() * y.numpy()
    expected = -np.sqrt(365) * z.mean() / np.sqrt((z * z).mean() - z.mean() ** 2 + 1e-9)
    loss = sharpe.policy_loss(p, y)
    assert float(loss.detach()) == pytest.approx(expected, abs=1e-12)
    loss.backward()
    assert torch.isfinite(p.grad).all()


def test_centered_denominator_survives_large_offset_and_small_variance():
    y = torch.tensor(1e8 + np.array([-0.002, 0.001, 0.003, -0.001]), dtype=torch.float64)
    p = torch.ones(4, dtype=torch.float64, requires_grad=True)
    z = y.numpy()
    expected = -np.sqrt(365) * z.mean() / np.sqrt(z.var() + 1e-9)
    loss = sharpe.policy_loss(p, y)
    assert float(loss.detach()) == pytest.approx(expected)
    loss.backward()
    assert torch.isfinite(p.grad).all()


@pytest.mark.parametrize("value", [0.0, 0.02])
def test_training_epsilon_is_finite_but_scoring_constant_returns_invalid(value):
    p = torch.ones(8, requires_grad=True)
    y = torch.full((8,), value)
    loss = sharpe.policy_loss(p, y)
    assert torch.isfinite(loss)
    with pytest.raises(sharpe.InvalidScore, match="variance"):
        sharpe.scored_sharpe(np.full(8, value))


def test_policy_tanh_bounds_pair_initialization_and_dormant_columns():
    torch.manual_seed(2001)
    baseline = sharpe.PositionLSTM()
    torch.manual_seed(2001)
    treatment = sharpe.PositionLSTM()
    assert sum(p.numel() for p in baseline.parameters()) == 1809
    for p, q in zip(baseline.parameters(), treatment.parameters(), strict=True):
        assert torch.equal(p, q)
    x = torch.randn(4, 63, 10)
    x[:, :, 8:] = 0
    output = baseline(x)
    assert torch.isfinite(output).all() and torch.all(torch.abs(output) <= 1)
    loss = sharpe.policy_loss(output, torch.tensor([0.01, -0.02, 0.03, 0.02]))
    loss.backward()
    assert torch.count_nonzero(baseline.lstm.weight_ih_l0.grad[:, 8:]) == 0
    modified = x.clone()
    modified[2:] *= 100
    np.testing.assert_array_equal(
        output.detach().numpy()[:2], baseline(modified).detach().numpy()[:2]
    )


def test_joint_date_bootstrap_scale_invariance_and_identical_arms():
    rng = np.random.default_rng(31)
    x = rng.normal(0.0003, 0.01, (42, 5))
    dates = np.arange(42) * DAY_US
    for factor in [1.0, 2.0]:
        joint = np.stack([x, factor * x], axis=2)
        result = sharpe.joint_bootstrap([(dates, joint)], replicates=60, seed=17)
        assert result["status"] == "VALID"
        np.testing.assert_allclose(result["ci95"], [0, 0], atol=1e-12)


def test_joint_date_bootstrap_no_gap_bridging_and_all_degenerate_draws_invalid():
    dates = np.arange(28) * DAY_US
    zero = np.zeros((28, 5, 2))
    result = sharpe.joint_bootstrap([(dates, zero)], replicates=20)
    assert result["invalid_replicates"] == 20 and result["ci95"] is None
    with pytest.raises(sharpe.InvalidScore, match="calendar"):
        sharpe.joint_bootstrap([(np.delete(dates, 12), np.delete(zero, 12, axis=0))])


def test_nonlinear_ensemble_positions_before_sharpe():
    times = np.arange(42)
    outcomes = np.broadcast_to((0.01 + 0.02 * np.sin(times / 3))[:, None], (42, 5))
    baseline = np.array([np.full((42, 5), 0.2), np.full((42, 5), 0.5), np.full((42, 5), 0.8)])
    treatment = np.array(
        [
            np.broadcast_to((0.3 + 0.4 * np.sin(times / 4))[:, None], (42, 5)),
            np.broadcast_to((0.1 + 0.5 * np.cos(times / 5))[:, None], (42, 5)),
            np.full((42, 5), -0.2),
        ]
    )
    block = {
        "dates": ["2023-01-01", "2023-03-01"],
        "times": times,
        "clock": times * DAY_US,
        "mask": np.ones((42, 5), dtype=bool),
        "outcomes": outcomes,
        "missing": np.empty((0, 2)),
        "position": {"trend": baseline, "trend_cpd": treatment},
    }
    proposal = {"scoring": {"bootstrap": {"replicates": 40, "block_days": 14, "seed": 9901}}}
    result = sharpe.score_blocks([block], proposal, np.full((42, 5), 0.02))
    expected = sharpe.scored_sharpe((treatment.mean(axis=0) * outcomes).sum(axis=1) / 5)
    actual = result["blocks"][0]["arms"]["trend_cpd"]
    assert actual["ensemble"]["sharpe"] == pytest.approx(expected)
    assert abs(expected - np.mean([s["sharpe"] for s in actual["seeds"]])) > 1e-3


def test_actual_frozen_inputs_no_refit_or_future_normalization(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("No refit on any prepare/inference path")

    monkeypatch.setattr(FrozenGP, "fit", forbidden)
    monkeypatch.setattr(Scaler, "fit", forbidden)
    archive = Path("/workspace/slow-momentum-state/source/features.zip")
    original = sharpe.prepare(archive)
    original_loader = sharpe.load_close

    def mutated_future(*args):
        available, close, audit = original_loader(*args)
        close[available >= sharpe.utc_us("2023-01-01")] *= 100
        return available, close, audit

    monkeypatch.setattr(sharpe, "load_close", mutated_future)
    changed = sharpe.prepare(archive)
    for index in (4, 5, 6):
        np.testing.assert_array_equal(original[index], changed[index])
    assert [len(b["times"]) for b in original[7]] == [180, 183, 120]
    assert sharpe.verify_predecessor()["manifest_files"] == 43


def test_bootstrap_keeps_assets_on_same_date_under_exact_offsetting_returns():
    values = np.random.default_rng(51).normal(0, 0.01, 42)
    joint = np.zeros((42, 5, 2))
    joint[:, 0, :] = values[:, None]
    joint[:, 1, :] = -values[:, None]
    result = sharpe.joint_bootstrap([(np.arange(42) * DAY_US, joint)], replicates=40)
    assert result["invalid_replicates"] == 40 and result["ci95"] is None


def test_missing_future_and_degenerate_policy_propagate_to_invalid_final_gate():
    times = np.arange(42)
    outcomes = np.full((42, 5), 0.001)
    positions = np.full((3, 42, 5), 0.5)
    block = {
        "dates": ["2023-01-01", "2023-03-01"],
        "times": times,
        "clock": times * DAY_US,
        "mask": np.ones((42, 5), dtype=bool),
        "outcomes": outcomes,
        "missing": np.empty((0, 2)),
        "position": {"trend": positions, "trend_cpd": positions},
    }
    proposal = {"scoring": {"bootstrap": {"replicates": 40, "block_days": 14, "seed": 9901}}}
    outcomes[17, 2] = np.nan
    result = sharpe.score_blocks([block], proposal, np.ones((42, 5)))
    assert result["status"] == "INVALID_POLICY_EVALUATION"
    assert result["gates"] is None and result["bootstrap"]["replicates"] == 0
    outcomes[:] = 0
    result = sharpe.score_blocks([block], proposal, np.ones((42, 5)))
    assert result["status"] == "INVALID_POLICY_EVALUATION"
    assert result["gates"] is None
