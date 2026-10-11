"""One frozen price-level relation, convergence versus spread continuation."""
import numpy as np
from scripts.investment.public_sma_perpetual import signed_risk_weights

DAY = 86_400_000_000
SYMBOLS = ("BTCUSDT", "ETHUSDT")


def fit_model(prices, symbols=SYMBOLS):
    if tuple(symbols) != SYMBOLS:
        raise ValueError("Exact BTC/ETH symbol coordinates required")
    p = np.asarray(prices, dtype=float)
    if p.ndim != 2 or p.shape[1] != 2 or len(p) < 30 or not np.isfinite(p).all() or np.any(p <= 0):
        raise ValueError("Complete ordered BTC/ETH calibration prices required")
    x, y = np.log(p).T
    alpha, beta = np.linalg.lstsq(np.column_stack([np.ones(len(x)), x]), y, rcond=None)[0]
    residual = y-alpha-beta*x
    sigma = float(residual.std(ddof=1))
    if not np.isfinite([alpha, beta, sigma]).all() or beta <= 0 or sigma <= 1e-12:
        raise ValueError("Positive elasticity and nondegenerate fixed scale required")
    return dict(alpha=float(alpha), beta=float(beta), mean=float(residual.mean()), sigma=sigma,
                observations=len(p))


def spread(prices, model):
    p = np.asarray(prices, dtype=float)
    return np.log(p[..., 1])-model["alpha"]-model["beta"]*np.log(p[..., 0])


def risk(direction, model, returns):
    w = np.array([-model["beta"]*.3*direction, .3*direction])
    w *= min(1., .3/max(np.max(np.abs(w)), 1e-30), .6/max(np.abs(w).sum(), 1e-30))
    out, receipt = signed_risk_weights(w, returns, annual_vol_target=.10)
    if abs(out[0]+model["beta"]*out[1]) > 1e-12:
        raise ValueError("Fixed price elasticity hedge identity changed")
    return out


def targets(prices, clocks, model, decisions, symbols=SYMBOLS):
    if tuple(symbols) != SYMBOLS:
        raise ValueError("Exact BTC/ETH symbol coordinates required")
    p, t, d = np.asarray(prices, float), np.asarray(clocks), np.asarray(decisions)
    if p.shape != (len(t), 2) or t.dtype.kind not in "iu" or d.dtype.kind not in "iu" or np.any(np.diff(t) != DAY) or np.any(np.diff(d) != DAY):
        raise ValueError("Dense daily ordered price/decision clocks required")
    out = {arm: np.zeros((len(d), 2)) for arm in ("reversion", "momentum")}
    ready, formed = np.zeros(len(d), bool), []
    directions = {arm: 0. for arm in out}
    for i, stamp in enumerate(d):
        k = np.searchsorted(t, stamp)
        valid = k < len(t) and t[k] == stamp and k >= 30 and np.isfinite(p[k-30:k+1]).all() and (p[k-30:k+1]>0).all()
        # UTC epoch Thursday; Monday is day-of-epoch modulo7 ==4.
        monday = (int(stamp)//DAY) % 7 == 4
        if monday:
            directions = {arm: 0. for arm in out}
            row = dict(decision_us=int(stamp), ready=bool(valid), active=False)
            if valid:
                value = float(spread(p[k], model))
                z = (value-model["mean"])/model["sigma"]
                past = value-float(spread(p[k-7], model))
                active = abs(z) >= 1.
                directions = dict(reversion=-float(np.sign(z)) if active else 0.,
                                  momentum=float(np.sign(past)) if active else 0.)
                row.update(z=z, past_seven_day_spread_change=past, active=bool(active), directions=directions.copy())
            formed.append(row)
        if valid:
            r = np.diff(p[k-30:k+1], axis=0)/p[k-30:k]
            for arm in out:
                out[arm][i] = risk(directions[arm], model, r)
            ready[i] = True
        else:
            directions = {arm: 0. for arm in out}
    return dict(decision_us=d, weights=out, ready=ready, formations=formed)
