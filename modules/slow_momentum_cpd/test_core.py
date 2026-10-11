"""Mechanism and causal counterexamples; synthetic evidence is not market profit."""

import numpy as np
import pytest
from scipy.special import expit

from . import core
from .core import DAY_US, FrozenGP, Scaler, covariance, cp_summary, sample_index, trend_features


def prices(n=650):
    rng = np.random.default_rng(47)
    return np.exp(np.cumsum(rng.normal(0.001, 0.02, size=(n, 5)), axis=0)) * 100


def test_future_mutation_does_not_change_trends_and_warmup():
    p = prices()
    original, _, _ = trend_features(p)
    p[500:] *= 100
    changed, _, _ = trend_features(p)
    np.testing.assert_equal(original[:500], changed[:500])
    assert np.isnan(original[:313, :, 5:]).all()
    assert np.isfinite(original[400:500]).all()


def test_missing_prices_reset_context_no_gap_bridge():
    p = prices(800)
    p[400, 2] = np.nan
    x, r, _ = trend_features(p)
    assert np.isnan(r[400:402, 2]).all()
    assert np.isnan(x[401:653, 2, 4]).all()
    assert np.isfinite(x[800 - 1, 2]).all()


def test_nonpositive_price_resets_macd_like_missing_price():
    p = prices(800)
    p[400, 2] = -1
    negative = trend_features(p)
    p[400, 2] = np.nan
    missing = trend_features(p)
    for a, b in zip(negative, missing, strict=True):
        np.testing.assert_equal(a, b)


def test_strict_maturity_purge_and_common_observation_mask():
    x = np.ones((20, 5, 8))
    r = np.ones((20, 5))
    v = r.copy()
    clock = np.arange(20) * DAY_US
    rows = sample_index(x, r, v, clock, 5 * DAY_US, 10 * DAY_US, sequence=3)
    assert rows[:, 0].max() == 8
    assert np.all(clock[rows[:, 0] + 1] < 10 * DAY_US)
    r[7, 1] = np.nan
    masked = sample_index(x, r, v, clock, 5 * DAY_US, 10 * DAY_US, sequence=3)
    assert (6, 1) not in map(tuple, masked)
    assert (6, 2) in map(tuple, masked)


def test_unique_train_scaler_does_not_use_validation():
    x = np.arange(30 * 5 * 10, dtype=float).reshape(30, 5, 10)
    rows = np.array([[8, 0], [9, 0], [9, 1]])
    scaler, used = Scaler.fit(x, rows, sequence=3)
    assert used.sum() == 7
    x[10:] = 1e20
    changed, _ = Scaler.fit(x, rows, sequence=3)
    np.testing.assert_equal(scaler.mean, changed.mean)
    np.testing.assert_equal(scaler.scale, changed.scale)


def test_covariance_independent_sides_positive_definite():
    theta = np.log([0.2, 2, 4, 0.5, 0.1, 1])
    cov = covariance(theta, 22, location=9)
    assert np.linalg.eigvalsh(cov).min() > 0
    assert cov[0, 0] < cov[-1, -1]
    np.testing.assert_allclose(cov, cov.T)


def test_evidence_equal_half_age_direction_and_stability():
    locations = np.array([3.0, 18.0])
    out = cp_summary(
        np.array([20.0, 100000.0]), np.array([[20.0, 20.0], [-100000.0, 100000.0]]), locations, 21
    )
    assert out[0, 1] == pytest.approx(0.5)
    assert out[1, 0] == pytest.approx(18 / 21)
    assert np.isfinite(out).all()
    assert 0 <= out[1, 1] <= 1


def test_frozen_gp_inference_no_fit_and_no_future_or_asset_contamination(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("No inference optimisation allowed")

    monkeypatch.setattr(core, "minimize", forbidden)
    gp = FrozenGP(
        0.0,
        0.02,
        np.log([1, 2, 0.1]),
        np.log([1, 2, 2, 1, 0.1, 1]),
        np.array([3.0, 9.0, 18.0]),
        21,
        {},
    )
    rng = np.random.default_rng(97)
    r = rng.normal(0, 0.02, (100, 5))
    original = gp.transform(r)
    r[75:] += 50
    r[:, 3] -= 10
    changed = gp.transform(r)
    np.testing.assert_equal(original[:75, :3], changed[:75, :3])
    np.testing.assert_equal(original[:75, 4], changed[:75, 4])
    assert np.isnan(original[:21]).all()


def test_direct_independent_likelihood_formula():
    # Independent matrix inverse / slogdet calculation, not calling tested nlml.
    y = np.random.default_rng(6).normal(size=(3, 22))
    cov = covariance(np.log([1.0, 2.0, 0.1]), 22)
    expected = 0.5 * np.einsum("bi,ij,bj->b", y, np.linalg.inv(cov), y)
    expected += 0.5 * np.linalg.slogdet(cov)[1] + 11 * np.log(2 * np.pi)
    np.testing.assert_allclose(core.nlml(cov, y), expected, atol=1e-10)


def test_synthetic_segment_covariance_score_is_only_mechanism_evidence():
    rng = np.random.default_rng(4)
    theta_m = np.log([1, 3, 0.1])
    theta_c = np.log([0.1, 3, 4, 3, 0.1, 1])
    y = rng.multivariate_normal(np.zeros(22), covariance(theta_c, 22, 12), size=300)
    m = core.nlml(covariance(theta_m, 22), y)
    c = core.nlml(covariance(theta_c, 22, 12), y)
    assert expit(m - c).mean() > 0.6


def test_paired_model_future_labels_do_not_enter_inference():
    import torch

    from .run import TrendLSTM, predict

    torch.manual_seed(2001)
    first = TrendLSTM()
    torch.manual_seed(2001)
    second = TrendLSTM()
    for a, b in zip(first.parameters(), second.parameters(), strict=True):
        assert torch.equal(a, b)
    x = np.random.default_rng(3).normal(size=(5, 63, 10)).astype("float32")
    before = predict(first, x)
    x[3:] += 100
    np.testing.assert_equal(before[:3], predict(first, x)[:3])


def test_gp_training_parameters_are_invariant_to_future_returns(monkeypatch):
    from types import SimpleNamespace

    def fixed_optimizer(fun, initial, **kwargs):
        return SimpleNamespace(
            x=initial.copy(),
            success=True,
            nit=0,
            message="synthetic fixed optimizer",
            fun=fun(initial),
        )

    monkeypatch.setattr(core, "minimize", fixed_optimizer)
    rng = np.random.default_rng(15)
    r = rng.normal(0, 0.02, (130, 5))
    clocks = np.arange(130) * DAY_US
    a = FrozenGP.fit(r, clocks, 30 * DAY_US, 90 * DAY_US, per_asset=4)
    r[89:] = 1e9
    b = FrozenGP.fit(r, clocks, 30 * DAY_US, 90 * DAY_US, per_asset=4)
    assert a.mean == b.mean and a.scale == b.scale
    assert a.fit_info == b.fit_info
    assert a.fit_info["latest_fit_available_us"] < 89 * DAY_US


def test_archive_tamper_rejected_before_table_loading(tmp_path):
    from .run import load_close

    archive = tmp_path / "wrong.zip"
    archive.write_bytes(b"not original public data")
    with pytest.raises(ValueError, match="archive hash"):
        load_close(archive, {"source": {"archive_sha256": "0" * 64}})


def test_bootstrap_refuses_compressing_a_calendar_gap():
    from .run import block_bootstrap

    days = np.concatenate((np.arange(20), np.arange(21, 40)))
    rows = np.stack((days, np.zeros(len(days), dtype=int)), axis=1)
    with pytest.raises(ValueError, match="missing calendar"):
        block_bootstrap([rows], [np.ones(len(rows))])
