"""One fixed portfolio risk budget using the existing 30 completed-day estimator."""
import numpy as np

DAY = 86400000000
SYMBOLS = ('BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'XRPUSDT', 'DOGEUSDT')
ARMS = ('CS_MATCHED', 'VOL_MATCHED', 'STATIC50')
ANNUAL_BUDGET = .10
ASSET_CAP = .30
GROSS_CAP = .60

def scale(weight, annual_covariance):
    w = np.asarray(weight, dtype=np.float64)
    c = np.asarray(annual_covariance, dtype=np.float64)
    if w.shape != (5,) or c.shape != (5, 5) or not np.isfinite(w).all() or not np.isfinite(c).all():
        raise ValueError('Finite ordered CORE5 weights and covariance required')
    if not np.allclose(c, c.T, rtol=0, atol=1e-14):
        raise ValueError('Symmetric covariance required')
    gross = float(np.abs(w).sum()); largest = float(np.abs(w).max())
    if largest > ASSET_CAP + 1e-12 or gross > GROSS_CAP + 1e-12:
        raise ValueError('Original input safety caps')
    variance = float(w @ c @ w)
    if variance < -1e-15:
        raise ValueError('Nonnegative covariance risk')
    sigma = float(np.sqrt(max(0., variance)))
    if gross == 0:
        return w.copy(), dict(raw_sigma=0., desired_factor=None, cap_factor=None, factor=0., post_sigma=0., cap_bound=False, risk_target_met=False, shortfall=ANNUAL_BUDGET, reason='INTRINSIC_CASH', gross=0., largest=0.)
    if sigma <= 1e-12:
        raise ValueError('Nonzero intent with degenerate estimated risk')
    desired = ANNUAL_BUDGET / sigma
    cap_factor = min(ASSET_CAP / largest, GROSS_CAP / gross)
    factor = min(desired, cap_factor)
    out = w * factor
    post = float(np.sqrt(max(0., out @ c @ out)))
    assert np.abs(out).max() <= ASSET_CAP + 1e-12 and np.abs(out).sum() <= GROSS_CAP + 1e-12
    assert post <= ANNUAL_BUDGET + 1e-12
    return out, dict(raw_sigma=sigma, desired_factor=desired, cap_factor=cap_factor, factor=factor, post_sigma=post, cap_bound=bool(cap_factor < desired - 1e-12), risk_target_met=bool(abs(post - ANNUAL_BUDGET) <= 1e-12), shortfall=max(0., ANNUAL_BUDGET-post), reason='CAP_BOUND' if cap_factor < desired - 1e-12 else 'RISK_TARGET_MET', gross=float(np.abs(out).sum()), largest=float(np.abs(out).max()))

def allocate(clocks, close, decisions, components):
    t = np.asarray(clocks, dtype=np.int64); p = np.asarray(close, dtype=np.float64); d = np.asarray(decisions, dtype=np.int64)
    if p.shape != (len(t), 5) or np.any(np.diff(t) != DAY) or np.any(np.diff(d) != DAY):
        raise ValueError('Original daily available-clock and CORE5 price order')
    if set(components) != set(ARMS) or any(np.asarray(w).shape != (len(d), 5) for w in components.values()):
        raise ValueError('Frozen three-arm complete target calendars')
    out = {arm: np.zeros((len(d), 5)) for arm in ARMS}; proof = []; covariance = []
    for i, at in enumerate(d):
        k = int(np.searchsorted(t, at))
        if k < 30 or k >= len(t) or t[k] != at or not np.isfinite(p[k-30:k+1]).all() or (p[k-30:k+1] <= 0).any():
            raise ValueError('No imputed current or past risk inputs')
        returns = np.diff(p[k-30:k+1], axis=0) / p[k-30:k]
        c = np.cov(returns, rowvar=False, ddof=1) * 365
        row = dict(decision_us=int(at), last_price_available_us=int(t[k]), oldest_price_available_us=int(t[k-30]), past_returns=30, annual_budget=ANNUAL_BUDGET, arms={})
        for arm in ARMS:
            out[arm][i], row['arms'][arm] = scale(components[arm][i], c)
        covariance.append(c); proof.append(row)
    return out, np.stack(covariance), proof
