import numpy as np
import pytest
from level import DAY, fit_model, targets, risk


def synthetic():
    t = np.arange(18263, 18763, dtype=np.int64)*DAY
    j = np.arange(len(t))
    btc = np.exp(8+j*.002+.1*np.sin(j*.07))
    eth = np.exp(-3+1.1*np.log(btc)+.06*np.sin(j*.21))
    return t, np.column_stack([btc, eth])


def test_fixed_model_prefix_and_actual_future_perturbation():
    t, p = synthetic()
    model = fit_model(p[:300])  # Synthetic calibration, not a historical fit.
    d = t[330:440]
    before = targets(p, t, model, d)
    changed = p.copy()
    changed[420:, 1] *= 8
    after = targets(changed, t, model, d)
    for arm in before["weights"]:
        np.testing.assert_array_equal(before["weights"][arm][d<t[420]], after["weights"][arm][d<t[420]])
        np.testing.assert_array_equal(before["weights"][arm][:50], targets(p[:400], t[:400], model, d[:50])["weights"][arm])


def test_identity_caps_and_missing_mask():
    t, p = synthetic()
    model = fit_model(p[:300])
    before = targets(p, t, model, t[330:390])
    for w in before["weights"].values():
        assert np.max(abs(w)) <= .3+1e-12 and np.max(abs(w).sum(1)) <= .6+1e-12
        np.testing.assert_allclose(w[:,0]+model["beta"]*w[:,1], 0, atol=1e-12)
    missing = p.copy()
    missing[350, 1] = np.nan
    after = targets(missing, t, model, t[330:390])
    assert not after["ready"][20:51].any()
    assert np.count_nonzero(after["weights"]["reversion"][20:51]) == 0
    with pytest.raises(ValueError):
        fit_model(missing[:360])
    with pytest.raises(ValueError, match="coordinates"):
        fit_model(p[:300], symbols=("ETHUSDT", "BTCUSDT"))
    with pytest.raises(ValueError, match="coordinates"):
        targets(p, t, model, t[330:390], symbols=("ETHUSDT", "BTCUSDT"))


def test_weekly_signal_seven_day_holding_and_covariance_limit():
    t, p = synthetic()
    model = fit_model(p[:300])
    out = targets(p, t, model, t[330:440])
    assert all((r["decision_us"]//DAY)%7 == 4 for r in out["formations"])
    for r in out["formations"]:
        if r["active"]:
            assert r["directions"]["reversion"] == -np.sign(r["z"])
    returns = np.diff(p[300:331], axis=0)/p[300:330]
    w = risk(1, model, returns)
    assert np.sqrt(w@np.cov(returns,rowvar=False)*365@w) <= .1+1e-12
