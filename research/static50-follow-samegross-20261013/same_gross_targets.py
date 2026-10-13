"""Fixed 50:50 signed pooling with a common downscale-only target gross.

No accounting, prices, PnL, fit, selected weights or historical simulation.
"""
from __future__ import annotations
import numpy as np

DAY = 86_400_000_000
SYMBOLS = ('BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'XRPUSDT', 'DOGEUSDT')
ARMS = ('STATIC50_SAMEGROSS', 'FOLLOW_POOL_SAMEGROSS')

def validate(clocks, symbols, weights):
    t = np.asarray(clocks)
    w = np.asarray(weights)
    if (t.dtype != np.dtype('int64') or t.ndim != 1 or not len(t)
            or np.any(np.diff(t) != DAY) or tuple(symbols) != SYMBOLS
            or w.dtype != np.dtype('float64') or w.shape != (len(t), 5)
            or not np.isfinite(w).all()):
        raise ValueError('Finite exact ordered CORE5 daily float64 target required')
    if np.abs(w).max() > .30 + 1e-12 or np.abs(w).sum(1).max() > .60 + 1e-12:
        raise ValueError('Frozen .30 asset/.60 gross caps exceeded')
    return t, w

def common_gross(static_clocks, static_symbols, static,
                 follow_clocks, follow_symbols, follow):
    ts, s = validate(static_clocks, static_symbols, static)
    tf, f = validate(follow_clocks, follow_symbols, follow)
    if not np.array_equal(ts, tf) or tuple(static_symbols) != tuple(follow_symbols):
        raise ValueError('Clock/order alignment cannot be inferred or repaired')
    c = .5 * s + .5 * f
    gs = np.abs(s).sum(axis=1)
    gc = np.abs(c).sum(axis=1)
    g = np.minimum(gs, gc)
    sf = np.divide(g, gs, out=np.zeros_like(g), where=gs != 0.)
    cf = np.divide(g, gc, out=np.zeros_like(g), where=gc != 0.)
    if (np.any(sf < 0.) or np.any(cf < 0.)
            or np.any(sf > 1.) or np.any(cf > 1.)):
        raise ValueError('Scaling may never increase either supplied portfolio')
    control = s * sf[:, None]
    pool = c * cf[:, None]
    # Zero common gross means exact positive-zero CASH, including signed-zero inputs.
    control[g == 0.] = 0.
    pool[g == 0.] = 0.
    for w in (control, pool):
        validate(ts, SYMBOLS, w)
        if not np.allclose(np.abs(w).sum(axis=1), g, rtol=0., atol=2e-16):
            raise ValueError('Common target gross equality failed')
    if (not np.all(np.abs(control) <= np.abs(s) + 1e-16)
            or not np.all(np.abs(pool) <= np.abs(c) + 1e-16)):
        raise ValueError('Elementwise downscale proof failed')
    return {ARMS[0]: control, ARMS[1]: pool,
            'STATIC50': s.copy(), 'FOLLOW': f.copy(), 'POOL_RAW': c,
            'common_gross': g, 'static_original_gross': gs,
            'pool_raw_gross': gc, 'static_factor': sf, 'pool_factor': cf}
