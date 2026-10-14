"""Fixed published 3-week momentum rule adapted to the existing shared wallet.

This is an equal-weight top/bottom-two adaptation, not a replication of the
paper's capitalization-weighted portfolios. Daily risk sizing reuses the
existing signed covariance control; this module performs no training or PnL.
"""
from __future__ import annotations

import numpy as np

from modules.transformer_v2.portfolio import market_neutral
from scripts.investment.public_sma_perpetual import signed_risk_weights, symbol_order

DAY_US = 86_400_000_000
WEEK_US = 7 * DAY_US
ANCHOR_US = 1_704_067_200_000_000  # 2024-01-01 00:00 UTC.


def public_targets(close, available_us, decision_us, symbols, allowed_symbols,
                   anchor_us=ANCHOR_US, *, short_absolute_confirmation=False):
    """Return ``(weights, diagnostics)`` in the explicit input symbol order.

    ``close`` is a dense (daily rows, assets) matrix with NaN for missing data.
    ``available_us`` is the common one-dimensional UTC daily-close availability
    clock; absent rows remain absent. ``decision_us`` selects output dates.
    No earlier row substitutes for an unavailable daily close. The fixed
    allowed pool is identical for the whole independent research account.

    Ranking uses exactly 21 daily returns (22 closes), on the fixed weekly
    calendar. At least 31 contiguous available closes are additionally required
    for the existing 30-return covariance control. Missing data clears a held
    asset until the next weekly ranking. Complete history before the output
    window restores the most recent scheduled ranking, without reranking on
    the first output day. Risk sizing may recover toward the unchanged raw
    weekly target on another day; that is a risk rebalance, not a new ranking.
    """
    names = symbol_order(symbols)
    allowed = set(allowed_symbols)
    if not allowed <= set(names):
        raise ValueError('Allowed pool outside the explicit symbol order')
    prices = np.asarray(close, dtype=np.float64)
    available = np.asarray(available_us)
    decisions = np.asarray(decision_us)
    for clock in (available, decisions):
        if (clock.ndim != 1 or clock.dtype.kind not in 'iu' or not len(clock)
                or np.any(clock < 0) or np.any(clock > np.iinfo(np.int64).max)
                or np.any(clock % DAY_US != 0) or np.any(np.diff(clock.astype(np.int64)) <= 0)):
            raise ValueError('Unique increasing UTC daily integer clocks required')
    available = available.astype(np.int64)
    decisions = decisions.astype(np.int64)
    if prices.shape != (len(available), len(names)):
        raise ValueError('Close rows and ordered assets must match the clocks')
    if (not isinstance(anchor_us, (int, np.integer)) or isinstance(anchor_us, bool)
            or anchor_us % DAY_US != 0):
        raise ValueError('Fixed UTC daily weekly anchor required')
    allowed_mask = np.array([s in allowed for s in names], dtype=bool)
    if not isinstance(short_absolute_confirmation, bool):
        raise ValueError('Explicit boolean absolute SHORT confirmation required')

    def past_context(timestamp):
        index = int(np.searchsorted(available, timestamp, side='right') - 1)
        valid = np.zeros(len(names), dtype=bool)
        if (index < 30 or available[index] != timestamp
                or np.any(np.diff(available[index - 30:index + 1]) != DAY_US)):
            return valid, None, None
        history = prices[index - 30:index + 1]
        valid = allowed_mask & np.all(np.isfinite(history) & (history > 0), axis=0)
        # Timestamp selection and contiguity above ensure every source row was
        # actually available by this decision; no future-filled window exists.
        with np.errstate(invalid='ignore', divide='ignore'):
            momentum = history[-1] / history[-22] - 1.
            returns = np.diff(history, axis=0) / history[:-1]
        return valid, momentum, returns

    first_rank = int(anchor_us + (int(decisions[0]) - anchor_us) // WEEK_US * WEEK_US)
    raw = np.zeros(len(names), dtype=np.float64)
    weights = np.zeros((len(decisions), len(names)), dtype=np.float64)
    output_index = {int(t): i for i, t in enumerate(decisions)}
    diagnostics = dict(symbol_order=list(names), allowed_symbols=[s for s in names if s in allowed],
        momentum_days=21, weekly_anchor_us=int(anchor_us), annual_vol_target=.10,
        rank_us=[], feature_available_us=[], current_eligible=[], rank_events=[],
        unscaled_signed_covariance_annual_vol=[],
        daily_risk_rebalance_can_restore_unchanged_weekly_raw_target=True)
    if short_absolute_confirmation:
        diagnostics.update(short_confirmation='DAILY_PAST_21D_RETURN_STRICTLY_NEGATIVE',
                           short_confirmation_blocked=[], post_confirmation_risk_vol=[])
    rank_date = first_rank
    for timestamp in range(first_rank, int(decisions[-1]) + DAY_US, DAY_US):
        valid, momentum, returns = past_context(timestamp)
        if (timestamp - anchor_us) % WEEK_US == 0:
            scores = np.full(len(names), np.nan) if momentum is None else momentum
            raw = market_neutral(scores[None, :], valid[None, :], k=2, gross=.6)[0]
            rank_date = timestamp
            diagnostics['rank_events'].append(dict(rank_us=timestamp,
                feature_available_us=[timestamp if v else None for v in valid],
                eligible=valid.tolist(), raw_weights=raw.tolist(),
                momentum=[float(scores[j]) if valid[j] else None for j in range(len(names))]))
        raw[~valid] = 0.  # A recovered asset cannot enter before the next rank.
        row = np.zeros(len(names), dtype=np.float64)
        held = np.flatnonzero(raw != 0.)
        sigma = 0.
        if len(held):
            row[held], risk = signed_risk_weights(raw[held], returns[:, held], annual_vol_target=.10)
            sigma = risk['unscaled_signed_covariance_annual_vol']
        if short_absolute_confirmation:
            blocked = (row < 0) & (momentum >= 0) if momentum is not None else np.zeros(len(names), dtype=bool)
            row[blocked] = 0.
            # Removing a hedge may INCREASE covariance risk. Recheck the kept
            # targets, downscale only; never redistribute the released budget.
            kept = np.flatnonzero(row != 0.)
            post_sigma = 0.
            if len(kept):
                row[kept], risk = signed_risk_weights(row[kept], returns[:, kept], annual_vol_target=.10)
                post_sigma = risk['unscaled_signed_covariance_annual_vol']
        if timestamp in output_index:
            weights[output_index[timestamp]] = row
            diagnostics['rank_us'].append(rank_date)
            diagnostics['feature_available_us'].append([timestamp if v else None for v in valid])
            diagnostics['current_eligible'].append(valid.tolist())
            diagnostics['unscaled_signed_covariance_annual_vol'].append(sigma)
            if short_absolute_confirmation:
                diagnostics['short_confirmation_blocked'].append(blocked.tolist())
                diagnostics['post_confirmation_risk_vol'].append(post_sigma)
    return weights, diagnostics
