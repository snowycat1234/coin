"""Synthetic correctness tests; they are not historical or profitability evidence."""
import json
from pathlib import Path

import numpy as np
import pytest
import torch
from scipy.integrate import quad
from scipy.stats import norm

from experiment import (
    DAY, QLSTM, build_samples, causal_sigma, date_us, fit_scalers,
    pinball_numpy, quantile_crps, short_net, two_stage_loss,
)

CONFIG = json.loads((Path(__file__).parent / "config.json").read_text())


def reference_crps(q, y, taus):
    """Independent integration of squared CDF error in actual return coordinates."""
    lo, hi = min(y, q[0]), max(y, q[-1])
    if lo == hi:
        return 0.
    def integrand(x):
        f = np.interp(x, q, taus, left=0., right=1.)
        return (f-float(x >= y))**2
    points = sorted(set(float(x) for x in [*q, y] if lo < x < hi))
    return quad(integrand, lo, hi, points=points, epsabs=1e-11, limit=200)[0]


@pytest.mark.parametrize("y", [-3., -.2, 0., .7, 4.])
def test_crps_on_actual_return_axis(y):
    taus = [.01, .05, .25, .5, .75, .95, .99]
    q = np.array([-.7, -.4, -.2, -.03, .1, .3, .9])
    result = quantile_crps(q[None], np.array([[y]]), taus)[0, 0]
    assert result == pytest.approx(reference_crps(q, y, taus), abs=1e-10)


def test_crps_degenerate_is_absolute_error():
    q = np.full((1, 3), .2)
    y = np.array([[-.4, .2, .5]])
    np.testing.assert_allclose(quantile_crps(q, y, [.1, .5, .9]), abs(y-.2), atol=1e-14)


def test_crps_gaussian_grid_matches_closed_form_approximately():
    taus = CONFIG["quantiles"]
    q = norm.ppf(taus)[None]
    y = np.array([[-2., -1., 0., 1., 2.]])
    expected = y*(2*norm.cdf(y)-1)+2*norm.pdf(y)-1/np.sqrt(np.pi)
    np.testing.assert_allclose(quantile_crps(q, y, taus), expected, rtol=.015, atol=.002)


def test_two_stage_loss_independent_scalar_sum():
    taus = [.25, .75]
    raw = torch.tensor([[-.01, .02]])
    normalized = torch.tensor([[-1., 2.]])
    y = torch.tensor([[-.02, 0., .01]])
    sigma = torch.tensor([.01])
    expected = 0.
    for target, predicted in [(y.numpy()*100, raw.numpy()*100), (y.numpy()/.01, normalized.numpy())]:
        values = []
        for t, q in zip(taus, predicted[0], strict=True):
            for v in target[0]:
                d = v-q
                values.append(t*d if d >= 0 else (t-1)*d)
        expected += sum(values)/len(values)
    assert two_stage_loss(normalized, raw, y, sigma, taus).item() == pytest.approx(expected)


def synthetic_days(n=160):
    available = date_us("2021-01-01") + np.arange(n)*DAY
    r = np.random.default_rng(42).normal(0., .02, (n, 2))
    s = causal_sigma(r, .94, .0001)
    x = np.stack([r, r*0+1, r*0+10, s], axis=-1)
    z = np.stack([r.mean(1), s.mean(1)], axis=-1)
    return available, x, z, r, s


def test_labels_strictly_mature_and_disjoint():
    inputs = synthetic_days()
    a = build_samples(*inputs, CONFIG, [["2021-02-01", "2021-03-01"]])
    b = build_samples(*inputs, CONFIG, [["2021-03-01", "2021-05-01"]])
    assert (a["label_end_us"] < date_us("2021-03-01")).all()
    assert a["label_end_us"].max() < b["origin_us"].min()
    assert a["skipped"]["boundary_purge"] == 22*2


def test_future_perturbation_does_not_change_past_features_or_scaler():
    dates, x, z, r, sigma = synthetic_days()
    before = build_samples(dates, x, z, r, sigma, CONFIG, [["2021-02-01", "2021-03-01"]])
    r[dates >= date_us("2021-03-01")] += 10
    s2 = causal_sigma(r, .94, .0001)
    x2 = np.stack([r, r*0+1, r*0+10, s2], axis=-1)
    z2 = np.stack([r.mean(1), s2.mean(1)], axis=-1)
    after = build_samples(dates, x2, z2, r, s2, CONFIG, [["2021-02-01", "2021-03-01"]])
    for k in ["x", "z", "y", "sigma"]:
        np.testing.assert_array_equal(before[k], after[k])
    for name in ["x", "z"]:
        for part in ["mean", "std"]:
            np.testing.assert_array_equal(fit_scalers(before)[name][part], fit_scalers(after)[name][part])


def test_gap_keeps_calendar_and_excludes_cross_gap_samples():
    dates, x, z, r, sigma = synthetic_days()
    bad = 65
    x[bad, 0] = np.nan
    r[bad, 0] = np.nan
    a = build_samples(dates, x, z, r, sigma, CONFIG, [["2021-02-01", "2021-05-01"]])
    for t, asset in zip(a["origin_us"], a["asset"], strict=True):
        if asset == 0:
            assert not t-21*DAY <= dates[bad] <= t+22*DAY
    assert a["skipped"]["missing_past"] > 0
    assert a["skipped"]["missing_future"] > 0
    assert (a["label_end_us"]-a["origin_us"] == 22*DAY).all()


def test_positive_scaling_preserves_order_even_for_negative_market_logits():
    torch.manual_seed(1)
    model = QLSTM(CONFIG)
    with torch.no_grad():
        model.market_head[-1].bias.fill_(-100)
        normalized, raw = model(torch.zeros(3, 22, 4), torch.zeros(3, 22, 2), torch.ones(3)*.02)
    assert torch.isfinite(raw).all()
    assert (torch.diff(raw, dim=1) >= 0).all()
    np.testing.assert_allclose(raw.numpy(), normalized.numpy()*.02*np.exp(-3), rtol=1e-6)


def test_pinball_increases_on_wrong_tail():
    y = np.array([[.1]])
    good = pinball_numpy(np.array([[.05, .15]]), y, [.05, .95]).sum()
    wrong = pinball_numpy(np.array([[.15, .05]]), y, [.05, .95]).sum()
    assert good < wrong


def test_down_day_can_still_lose_after_cost():
    # BASE27-like fee5.5bp plus execution8bp per side.
    r = np.log(.999)
    assert r < 0
    assert short_net(r, .00055, .0008, 0.) < 0


def test_short_rebound_and_signed_funding():
    assert short_net(np.log(1.20), 0., 0., 0.) == pytest.approx(-.20)
    assert short_net(np.log(.80), 0., 0., 0.) == pytest.approx(.20)
    assert short_net(0., 0., 0., -.01) == pytest.approx(-.01)
    assert short_net(0., 0., 0., .01) == pytest.approx(.01)


def test_scaler_does_not_need_validation_data():
    train = {"x": np.array([[[1., 2.]], [[3., 2.]]]), "z": np.array([[[4.]], [[6.]]])}
    s = fit_scalers(train)
    np.testing.assert_array_equal(s["x"]["mean"], [2., 2.])
    np.testing.assert_array_equal(s["x"]["std"], [1., 1.])
