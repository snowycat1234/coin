"""One frozen source-only lagged funding-adjusted CS21 basket discriminator.

No wallet, future utility, learned model, or financial return is computed.
The score is an approximation, conditional on raw rates being fractions.
"""
from __future__ import annotations

from dataclasses import dataclass
import numpy as np

DAY = 86_400_000_000
HOUR = 3_600_000_000
WEEK = 7 * DAY
ANCHOR = 1_704_067_200_000_000
JITTER = 60_000_000
SYMBOLS = ("BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT", "DOGEUSDT")


@dataclass(frozen=True)
class EventStream:
    times: np.ndarray
    rates: np.ndarray
    hours: np.ndarray
    # Immutable source-admission certificate: for each certified complete UTC
    # day, the exact original actual settlement IDs in that canonical source.
    # Missing keys are UNKNOWN. This must not be invented from an unverified
    # stream, inferred from a future event, or read from future payoff masks.
    complete_day_event_ids: dict | None = None

    def __post_init__(self):
        t, r, h = np.asarray(self.times), np.asarray(self.rates), np.asarray(self.hours)
        if t.ndim != 1 or t.dtype.kind not in "iu" or r.shape != t.shape or h.shape != t.shape:
            raise ValueError("Actual integer event clocks and aligned rate/hour vectors required")
        if np.any(t < 0) or np.any(t > np.iinfo(np.int64).max) or np.any(np.diff(t.astype(np.int64)) <= 0):
            raise ValueError("Unique increasing actual event timestamps required")
        object.__setattr__(self, "times", t.astype(np.int64))
        object.__setattr__(self, "rates", r.astype(float))
        object.__setattr__(self, "hours", h.astype(float))


def market_neutral(score, active):
    """Exact original stable CORE5 top2/bottom2/.6/fully-tied rule."""
    s, a = np.asarray(score, float), np.asarray(active, bool)
    if s.shape != (5,) or a.shape != (5,):
        raise ValueError("Fixed original CORE5 order and shape required")
    w = np.zeros(5)
    ids = np.flatnonzero(a & np.isfinite(s))
    if len(ids) < 4 or np.ptp(s[ids]) <= 1e-12:
        return w
    ranked = ids[np.argsort(s[ids], kind="stable")]
    w[ranked[-2:]] = .6 / 4
    w[ranked[:2]] = -.6 / 4
    return w


def settled_sum(stream, decision):
    """Same 21-day interval as lagged price: [D-22d,D-1d).

    Each complete input day starts at d and is conditionally available at d+2d.
    Actual timestamps are retained. No event at/after D-1d can establish
    completeness. Variable reported hours are validated, never rescaled.
    """
    certificates = stream.complete_day_event_ids or {}
    expected = []
    reasons = []
    for day in range(decision - 22 * DAY, decision - DAY, DAY):
        ids = certificates.get(int(day))
        # Actual source authority is mandatory. In particular no forward
        # extrapolation from the final settlement's preceding interval h.
        if ids is None or not len(ids) or any(not day <= x < day + DAY for x in ids):
            reasons.append(int(day))
        else:
            expected.extend(int(x) for x in ids)
    lower, upper = decision - 22 * DAY, decision - DAY
    keep = (stream.times >= lower) & (stream.times < upper)
    t, r, h = stream.times[keep], stream.rates[keep], stream.hours[keep]
    latest = int(t[-1]) if len(t) else None
    if not np.array_equal(t, np.array(expected, dtype=np.int64)):
        reasons.append("ACTUAL_EVENT_IDS_DIFFER_FROM_COMPLETE_SOURCE_CERTIFICATE")
    numeric = (len(t) > 0 and np.isfinite(r).all() and np.isfinite(h).all() and (h > 0).all())
    if not numeric:
        reasons.append("UNKNOWN_OR_INVALID_ORIGINAL_EVENT_VALUE")
    elif np.any(np.abs(np.diff(t) - h[1:] * HOUR) > JITTER):
        reasons.append("OBSERVED_PRECEDING_INTERVAL_GAP")
    if len(t):
        first_index = int(np.searchsorted(stream.times, t[0]))
        if first_index == 0:
            reasons.append("PRECEDING_BOUNDARY_SETTLEMENT_UNKNOWN")
        elif abs(float(t[0] - stream.times[first_index - 1]) - float(h[0]) * HOUR) > JITTER:
            reasons.append("PRECEDING_BOUNDARY_INTERVAL_GAP")
    with np.errstate(over="ignore", invalid="ignore"):
        aggregate = float(r.sum())
    if not np.isfinite(aggregate):
        reasons.append("NONFINITE_AGGREGATE_RATE_SUM")
    if reasons:
        return dict(status="NOT_READY", value=None, missing_or_invalid_day_us=reasons,
                    observed_events=len(t), latest_event_us=latest)
    assert latest is not None and latest < decision - DAY
    return dict(status="READY_CONDITIONAL_24H_DAY_PROXY", value=aggregate,
                missing_or_invalid_day_us=[], observed_events=len(t),
                event_ids=t.tolist(), reported_interval_hours_sum=float(h.sum()),
                latest_event_us=latest, latest_input_day_available_us=int(decision),
                completeness_authority="PINNED_COMPLETE_SOURCE_EVENT_IDS_NOT_FUTURE_CADENCE")


def score_at(clocks, close, original_ready, streams, decision, *, symbols=SYMBOLS):
    """Inspect one decision, using externally source-verified original CSH masks.

    Original all-five current availability remains mandatory. Funding readiness
    is shared by both paired arms. NOT_READY is reported, never interpreted as
    a funding zero, changed universe, or historical financial gap repair.
    """
    t, p, mask = np.asarray(clocks), np.asarray(close, float), np.asarray(original_ready)
    if tuple(symbols) != SYMBOLS or len(streams) != 5:
        raise ValueError("Exact original symbol order required")
    if t.ndim != 1 or t.dtype.kind not in "iu" or len(t) == 0:
        raise ValueError("Integer close availability clock required")
    if np.any(t < 0) or np.any(t > np.iinfo(np.int64).max):
        raise ValueError("Close clock outside signed microsecond range")
    t = t.astype(np.int64)
    if np.any(t % DAY) or np.any(np.diff(t) <= 0):
        raise ValueError("Unique increasing UTC completed-close clock required")
    if p.shape != (len(t), 5) or mask.shape != p.shape or mask.dtype.kind != "b":
        raise ValueError("Aligned five-asset close and original boolean mask required")
    if not isinstance(decision, (int, np.integer)) or isinstance(decision, bool) or decision % DAY:
        raise ValueError("Actual UTC daily integer decision required")
    k = int(np.searchsorted(t, decision))
    price_known = np.zeros(5, bool)
    price = np.full(5, np.nan)
    unlagged = np.full(5, np.nan)
    base = np.zeros(5, bool)
    if k < len(t) and t[k] == decision:
        base = mask[k].copy()
        if k >= 30 and np.all(np.diff(t[k - 30:k + 1]) == DAY):
            history = p[k - 30:k + 1]
            price_known = np.all(np.isfinite(history) & (history > 0), axis=0)
            with np.errstate(invalid="ignore", divide="ignore"):
                price = p[k - 1] / p[k - 22] - 1.
                unlagged = p[k] / p[k - 21] - 1.
    if np.any(base & ~price_known):
        raise ValueError("Original ready mask contradicts current real31 close history")
    fp = [settled_sum(s, int(decision)) for s in streams]
    funding_known = np.array([x["value"] is not None for x in fp])
    common = base & price_known & funding_known
    adjusted = np.full(5, np.nan)
    with np.errstate(over="ignore", invalid="ignore"):
        for a in np.flatnonzero(common):
            adjusted[a] = price[a] - fp[a]["value"]
    score_known = np.isfinite(price) & np.isfinite(adjusted)
    # Retain original CSH all-five admission, rather than reopening min4,
    # including numeric failure. market_neutral must not silently drop one.
    ready = bool(base.all() and price_known.all() and funding_known.all() and score_known.all())
    active = np.full(5, ready, dtype=bool)
    pair_price = market_neutral(price, active)
    pair_funding = market_neutral(adjusted, active)
    original_active = np.full(5, bool(base.all() and price_known.all()), dtype=bool)
    original = market_neutral(unlagged, original_active)
    return dict(decision_us=int(decision),
                status="READY_PAIRED_BASKETS" if ready else "NOT_READY_PAIRED_BASKETS",
                interval_us=[int(decision - 22 * DAY), int(decision - DAY)],
                latest_price_feature_available_us=int(decision - DAY),
                original_ready=base.tolist(), price_known=price_known.tolist(),
                funding_known=funding_known.tolist(), score_known=score_known.tolist(), funding_proof=fp,
                price_score=price, funding_adjusted_score=adjusted,
                price_only_raw_basket=pair_price, funding_adjusted_raw_basket=pair_funding,
                original_unlagged_raw_basket_descriptive=original,
                paired_basket_changed=bool(np.any(pair_price != pair_funding)))


def scheduled_ranks(start, end):
    """Full [start,end) calendar ranks plus preceding ownership rank.

    The preceding rank is an initialization context, never an extra scored
    observation. No rerank on an off-schedule window's first day.
    """
    if (not isinstance(start, (int, np.integer)) or not isinstance(end, (int, np.integer))
            or isinstance(start, bool) or isinstance(end, bool)
            or start % DAY or end % DAY or end <= start):
        raise ValueError("Positive full UTC calendar window required")
    preceding = ANCHOR + (int(start) - ANCHOR) // WEEK * WEEK
    return preceding, list(range(preceding if preceding >= start else preceding + WEEK, int(end), WEEK))
