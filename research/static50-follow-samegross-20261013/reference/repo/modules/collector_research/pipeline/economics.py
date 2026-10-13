"""A quantity-accounted DAILY research proxy, NOT the repository's execution engine.

A decision using UTC day d's completed data executes at day d+1 00:01:00.000001.
It owns quantity through the next execution boundary. Funding uses strictly-past
minute marks and original archive calc_time, under an explicitly conditional rate
scale. No margin/liquidation/capacity/latency-certification claims are made.
"""
from __future__ import annotations
import numpy as np
import pandas as pd


def allocate_positions(positions: np.ndarray, active_count: int, asset_cap: float = .3, gross_cap: float = .6) -> np.ndarray:
    p = np.asarray(positions, dtype=float)
    if not np.isfinite(p).all() or (np.abs(p) > 1 + 1e-8).any():
        raise ValueError('Invalid expert direction mixture')
    if active_count < 1 or not 0 < asset_cap <= .3 or not 0 < gross_cap <= .6:
        raise ValueError('Risk caps cannot exceed the project .30/.60 boundary')
    # Do not lever tiny predictions back to gross .6: CASH allocations must survive.
    return p * min(asset_cap, gross_cap / active_count)


def proxy_step(nav: float, previous_q: np.ndarray, weights: np.ndarray, start_prices: np.ndarray,
               end_prices: np.ndarray, funding_per_unit: np.ndarray, valid: np.ndarray,
               cost: float) -> tuple[float, np.ndarray, float, float, float, float]:
    q0 = np.asarray(previous_q, float)
    weights = np.asarray(weights, float)
    p0, p1, fp = (np.asarray(x, float) for x in (start_prices, end_prices, funding_per_unit))
    touching = (np.abs(q0) > 1e-15) | (np.abs(weights) > 1e-15)
    holding = np.abs(weights) > 1e-15
    if not np.isfinite(nav) or nav <= 0 or not np.isfinite(weights).all():
        raise ValueError('Invalid NAV/target')
    if np.any(touching & (~np.isfinite(p0) | (p0 <= 0))):
        raise ValueError('Missing executable price for entry/exit; cannot skip this day')
    if np.any(holding & (~np.asarray(valid, bool) | ~np.isfinite(p1) | (p1 <= 0) | ~np.isfinite(fp))):
        raise ValueError('Incomplete owned price/funding interval; cannot cherry-pick or zero-fill')
    target_q = np.divide(nav * weights, p0, out=np.zeros_like(weights), where=holding)
    traded_notional = float(np.sum(np.abs(target_q[touching] - q0[touching]) * p0[touching]))
    fees = traded_notional * cost
    pnl = float(np.sum(target_q[holding] * (p1[holding] - p0[holding])))
    funding = float(np.sum(target_q[holding] * fp[holding]))
    result = nav + pnl - fees - funding
    if not np.isfinite(result) or result <= 0:
        raise ValueError('Nonpositive/nonfinite proxy NAV; stop, do not fabricate liquidation')
    return result, target_q, fees, funding, traded_notional, pnl


def interval_arrays(frame: pd.DataFrame, indices: np.ndarray, scale: float) -> tuple[np.ndarray, ...]:
    # Decision index i -> execution interval day i+1 -> day i+2.
    n = len(frame)
    i = np.asarray(indices, dtype=int)
    if np.any(i < 0) or np.any(i + 2 >= n):
        raise ValueError('Decision has no complete future execution boundary')
    p = frame.exec_price.to_numpy(float)
    funding = frame.mark_funding_per_unit.to_numpy(float) * scale
    good = frame.funding_interval_complete.to_numpy(bool) & frame.complete_kline.to_numpy(bool)
    return p[i + 1], p[i + 2], funding[i + 1], good[i + 1]


def replay(frames: dict[str, pd.DataFrame], indices: np.ndarray, weights: np.ndarray,
           scale: float, cost: float, capital: float = 10000.) -> tuple[dict, pd.DataFrame]:
    syms = list(frames)
    idx = np.asarray(indices, dtype=int)
    w = np.asarray(weights, dtype=float)
    if not len(idx) or not np.all(np.diff(idx) == 1) or w.shape != (len(idx), len(syms)):
        raise ValueError('Replay must cover the full contiguous calendar, including CASH days')
    if np.any(np.abs(w) > .3 + 1e-9) or np.any(np.abs(w).sum(axis=1) > .6 + 1e-9):
        raise ValueError('Target risk caps breached')
    arrays = [interval_arrays(frames[s], idx, scale) for s in syms]
    p0, p1, funds, valid = [np.stack([a[k] for a in arrays], axis=1) for k in range(4)]
    q = np.zeros(len(syms))
    nav = float(capital)
    records = []
    for j, i in enumerate(idx):
        before = nav
        nav, q, fees, funding, notional, pnl = proxy_step(nav, q, w[j], p0[j], p1[j], funds[j], valid[j], cost)
        row = dict(decision_day=str(frames[syms[0]].dt.iloc[i]), nav_before=before, nav_after=nav,
                   fees=fees, funding=funding, price_pnl=pnl, turnover=notional / before,
                   daily_return=nav / before - 1)
        records.append(row)
    owned = np.abs(q) > 1e-15
    if np.any(owned & ~np.isfinite(p1[-1])):
        raise ValueError('Missing terminal liquidation price')
    terminal_notional = float(np.sum(np.abs(q[owned]) * p1[-1][owned]))
    terminal_fee = terminal_notional * cost
    terminal_turnover = terminal_notional / nav
    nav -= terminal_fee
    if nav <= 0:
        raise ValueError('Terminal fees exhaust NAV')
    records[-1]['nav_after'] = nav
    records[-1]['fees'] += terminal_fee
    records[-1]['turnover'] += terminal_turnover
    records[-1]['daily_return'] = nav / records[-1]['nav_before'] - 1
    trace = pd.DataFrame(records)
    values = np.r_[capital, trace.nav_after.to_numpy(float)]
    mdd = float(np.max(1 - values / np.maximum.accumulate(values)))
    r = trace.daily_return.to_numpy(float)
    sd = np.std(r, ddof=1) if len(r) > 1 else 0.
    sharpe = float(np.mean(r) / sd * np.sqrt(365)) if sd > 0 else 0.
    metrics = dict(net=nav - capital, net_return=nav / capital - 1, final_nav=nav,
                   mdd=mdd, sharpe=sharpe, days=len(r), fees=float(trace.fees.sum()),
                   funding=float(trace.funding.sum()), turnover=float(trace.turnover.sum()),
                   terminal_fee=terminal_fee, final_positions=0, economics='CONDITIONAL_DAILY_QUANTITY_PROXY')
    return metrics, trace


def continuous_expert_returns(frame: pd.DataFrame, signals: np.ndarray, weight: float,
                              scale: float, cost: float) -> pd.Series:
    output = np.full(len(frame), np.nan)
    nav, q = 1., np.zeros(1)
    indices = np.arange(max(0, len(frame) - 2))
    p0, p1, funds, valid = interval_arrays(frame, indices, scale)
    for i in indices:
        if not np.isfinite(signals[i]) or not valid[i] or not np.isfinite([p0[i], p1[i], funds[i]]).all():
            # Unknown return is not zero. A later valid segment restarts from cash;
            # no future label may cross the NaN gap.
            nav, q = 1., np.zeros(1)
            continue
        before = nav
        nav, q, *_ = proxy_step(nav, q, np.array([weight * signals[i]]), np.array([p0[i]]),
                               np.array([p1[i]]), np.array([funds[i]]), np.array([True]), cost)
        output[i] = nav / before - 1
    return pd.Series(output, index=frame.index)
