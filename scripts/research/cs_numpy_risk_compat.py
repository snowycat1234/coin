"""Compatibility copy of unchanged numpy helpers from public_sma_perpetual.

The source originals and hashes are retained. Only unused Polars-based APIs
and their imports are omitted; no signal or risk equations are changed.
"""
import numpy as np

def require(ok, message):
    if not bool(ok):
        raise ValueError(message)


def symbol_order(symbols):
    names = tuple(symbols)
    require(bool(names) and len(names) == len(set(names)) and all(
        isinstance(s, str) and s.isascii() and s.isalnum() and s.endswith('USDT')
        for s in names), 'Unique explicit ordered USDT symbols required')
    return names


def signed_risk_weights(raw, past_returns, annual_vol_target=.10):
    """N ordered assets; zero net exposure still has gross and covariance risk."""
    w = np.asarray(raw, dtype=np.float64).copy()
    r = np.asarray(past_returns, dtype=np.float64)
    require(w.ndim == 1 and len(w) > 0 and np.isfinite(w).all()
        and r.ndim == 2 and r.shape[1] == len(w) and r.shape[0] >= 30
        and np.isfinite(r).all(), 'Ordered assets and complete 30 past returns')
    require(0 < annual_vol_target <= .10, 'Existing volatility target cannot increase')
    w = np.clip(w, -.3, .3)
    gross = float(np.abs(w).sum())
    if gross > .6:
        w *= .6 / gross
    covariance = np.atleast_2d(np.cov(r[-30:], rowvar=False, ddof=1)) * 365
    variance = float(w @ covariance @ w)
    require(variance >= -1e-15, 'Nonnegative covariance risk required')
    sigma = float(np.sqrt(max(variance, 0.)))
    if sigma > annual_vol_target:
        w *= annual_vol_target / sigma
    return w, dict(unscaled_signed_covariance_annual_vol=sigma,
        net_target_weight=float(w.sum()), gross_target_weight=float(np.abs(w).sum()),
        covariance_observations=30, covariance_assets=len(w), past_only=True)


