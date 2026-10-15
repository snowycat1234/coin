"""Independent fixtures: generated prices only, no source-year or saved runs."""
from copy import deepcopy
from decimal import Decimal as D
from pathlib import Path
import sys

import numpy as np
import polars as pl

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'causal_forecast_risk_monitor_20261015'))
import forecast_monitor as f
from test_native_runtime import fixture, BASE


def synthetic_source(days=1, annual_common_sigma=.5, *, returns=None):
    """Exact 30-return common-factor daily source, ending at generated BASE."""
    window, _, decisions = fixture(days)
    start = int(decisions[0])
    if returns is None:
        amplitude = annual_common_sigma * np.sqrt(29 / (30 * 365))
        returns = np.asarray([amplitude if i % 2 else -amplitude for i in range(30)])
    else:
        returns = np.asarray(returns, dtype=float)
    assert returns.shape in ((30,), (30, 5)) and np.all(returns > -1)
    if returns.ndim == 1:
        returns = np.repeat(returns[:, None], 5, axis=1)
    multiplier = np.vstack([np.ones(5), np.cumprod(1 + returns, axis=0)])
    multiplier /= multiplier[-1]
    times = start + np.arange(-30, 1, dtype=np.int64) * f.DAY
    rows = [dict(symbol=s, close_us=int(at), available_us=int(at), close=float(BASE[j] * multiplier[i, j]))
            for i, at in enumerate(times) for j, s in enumerate(f.S)]
    for day in range(1, days + 1):
        rows.extend(dict(symbol=s, close_us=start + day * f.DAY, available_us=start + day * f.DAY,
                         close=float(BASE[j])) for j, s in enumerate(f.S))
    window['daily'] = pl.DataFrame(rows)
    window['events'] = []
    return window, rows, decisions


def make_sim(sigma=.5, *, days=1, returns=None, quality_intervals=(), targets=None):
    window, rows, decisions = synthetic_source(days, sigma, returns=returns)
    if targets is None:
        targets = np.zeros((days, 5))
    sim, guard = f.construct_case(window, rows, decisions, targets,
                                 generated_scope=f.GENERATED, quality_intervals=quality_intervals)
    return sim, guard, rows


def make_account():
    plain = f.V2.grid.make_account('MID', 'BASE27')
    return f.ForecastRiskAccount(plain.config, symbols=f.S, instrument_profiles=plain.instrument_profiles,
                                 closing_min_notional_exempt=True, generated_scope=f.GENERATED)


def mark(a, at, prices=None, quality=None, symbols=None, close_us=None):
    prices = prices or {}
    return a.update_marks(at, {s: dict(price=str(prices.get(s, BASE[j])),
                           close_us=at if close_us is None else close_us, available_us=at)
                              for j, s in enumerate(f.S) if symbols is None or s in symbols}, quality=quality)


def seed_paid(a, quantities, signal):
    event = signal + f.MINUTE + 1
    mark(a, event - 1)
    for s, q in quantities.items():
        q = D(str(q))
        if q:
            receipt = a.execute_fill(s, 'BUY' if q > 0 else 'SELL', abs(q), event, signal,
                'INDEPENDENT_SEED:' + s, execution_mid_price=str(BASE[f.S.index(s)]),
                quote_available_us=event - 1, available_quantity=abs(q))
            assert receipt['status'] == 'FILLED', receipt
    return event


def market(prices=None):
    prices = prices or {}
    return {s: dict(open=float(prices.get(s, BASE[j])), close=float(prices.get(s, BASE[j])),
                    mark=float(prices.get(s, BASE[j])), quote_volume=1e10) for j, s in enumerate(f.S)}


def set_capacity(sim, quantities=None):
    quantities = quantities or dict.fromkeys(f.S, D('100000'))
    sim.previous_quote = {s: float(D(str(quantities.get(s, 0))) * D(str(BASE[j])) / D('.001'))
                          for j, s in enumerate(f.S)}


def trigger(sim):
    at = sim.start + 2 * f.MINUTE
    mark(sim.account, at)
    receipt = sim.risk_schedule(at)
    return at, receipt


def quantities(a):
    return {s: a.positions[s].quantity for s in f.S}


def finance(a):
    snap = a.snapshot()
    return {k: snap[k] for k in ('free_cash', 'unpaid_liability', 'positions', 'marks', 'totals',
                                'trades', 'funding', 'fill_requests', 'funding_events', 'funding_ids')}


def run(sim):
    while sim.cursor < sim.end and sim.stop is None:
        sim.advance_day()
    return sim


def tree_equal(left, right):
    return f.V2.native._exact_tree_equal(left, right)
