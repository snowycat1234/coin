"""Frozen causal CS21/SMA200 agreement targets; no economic scoring.

The input clock denotes *completed-close availability*, not bar open time.
Canonical public_targets performs ranking. Its rank-event vectors are replayed
through the same clear-on-missing daily state before common-policy risk sizing.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

import numpy as np

from scripts.research.public_cross_section_momentum_compat import (
    ANCHOR_US, DAY_US, WEEK_US, public_targets,
)

ROOT = Path(__file__).resolve().parents[2]
_spec = importlib.util.spec_from_file_location(
    "cs_sma_original_risk_budget", ROOT / "research/portfolio-risk-budget-20261012/risk_budget.py")
RISK = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(RISK)

SYMBOLS = ("BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT", "DOGEUSDT")
ARMS = ("CS", "SMA200", "STATIC50", "AGREEMENT", "AGREEMENT_NO_REALLOCATION")
SMA_DAYS = 200


def _inputs(close, available_us, decision_us):
    p = np.asarray(close, dtype=np.float64)
    clocks = []
    for value in (available_us, decision_us):
        t = np.asarray(value)
        if (t.ndim != 1 or t.dtype.kind not in "iu" or not len(t)
                or np.any(t < 0) or np.any(t > np.iinfo(np.int64).max)
                or np.any(t % DAY_US != 0)
                or np.any(np.diff(t.astype(np.int64)) <= 0)):
            raise ValueError("Increasing integer completed-close UTC daily clocks required")
        clocks.append(t.astype(np.int64))
    t, d = clocks
    if p.shape != (len(t), 5) or np.any(np.diff(d) != DAY_US):
        raise ValueError("Full daily decision calendar and explicit CORE5 close order required")
    return p, t, d


def _past_index(t, at, count):
    k = int(np.searchsorted(t, at, side="right") - 1)
    if (k < count - 1 or t[k] != at
            or np.any(np.diff(t[k - count + 1:k + 1]) != DAY_US)):
        return None
    return k


def cs_raw_targets(close, available_us, decision_us):
    """Exact canonical weekly raw ranks, including pre-output rank warmup.

    Daily missingness clears held members until a new scheduled weekly rank.
    Do not infer raw intent by inverting risk-sized weights.
    """
    p, t, d = _inputs(close, available_us, decision_us)
    canonical, diag = public_targets(p, t, d, SYMBOLS, SYMBOLS, anchor_us=ANCHOR_US)
    events = {int(row["rank_us"]): row for row in diag["rank_events"]}
    first_rank = ANCHOR_US + (int(d[0]) - ANCHOR_US) // WEEK_US * WEEK_US
    output_index = {int(at): i for i, at in enumerate(d)}
    out = np.zeros((len(d), 5))
    raw = np.zeros(5)
    for at in range(first_rank, int(d[-1]) + DAY_US, DAY_US):
        k = _past_index(t, at, 31)
        valid = (np.zeros(5, dtype=bool) if k is None else
                 np.all(np.isfinite(p[k-30:k+1]) & (p[k-30:k+1] > 0), axis=0))
        if at in events:
            raw = np.asarray(events[at]["raw_weights"], dtype=np.float64).copy()
        raw[~valid] = 0.
        if at in output_index:
            out[output_index[at]] = raw
    # This checks the reconstructed sticky/clear state against the original
    # independently risk-sized state, without mistaking sizing for raw signal.
    if not np.array_equal(np.sign(out), np.sign(canonical)):
        raise ValueError("Canonical raw-state/sign parity failure")
    return out, diag


def sma_raw_targets(close, available_us, decision_us):
    """Latest 200 contiguous completed closes, signed .12 or genuine flat.

    Ineligible raw cells are placeholders only; eligibility is returned
    separately and strict target admission cannot interpret unknown as CASH.
    """
    p, t, d = _inputs(close, available_us, decision_us)
    raw = np.zeros((len(d), 5))
    eligible = np.zeros_like(raw, dtype=bool)
    means = np.full_like(raw, np.nan)
    latest = np.full_like(raw, np.nan)
    for i, at in enumerate(d):
        k = _past_index(t, at, SMA_DAYS)
        if k is None:
            continue
        history = p[k-SMA_DAYS+1:k+1]
        valid = np.all(np.isfinite(history) & (history > 0), axis=0)
        eligible[i] = valid
        means[i, valid] = np.mean(history[:, valid], axis=0)
        latest[i, valid] = p[k, valid]
        raw[i, valid] = .12 * np.sign(latest[i, valid] - means[i, valid])
    return raw, eligible, means, latest


def agreement_mask(cs_raw, sma_raw, sma_eligible):
    cs = np.asarray(cs_raw, dtype=np.float64)
    sma = np.asarray(sma_raw, dtype=np.float64)
    valid = np.asarray(sma_eligible, dtype=bool)
    if cs.shape != sma.shape or valid.shape != cs.shape:
        raise ValueError("Aligned CS/SMA/eligibility arrays required")
    return valid & (cs != 0.) & (sma != 0.) & (np.sign(cs) == np.sign(sma))


def size_day(raw, gate, annual_covariance):
    """Common scaling for four raw arms; literal sized-CS survivor diagnostic."""
    if set(raw) != set(ARMS[:-1]):
        raise ValueError("Exactly the four frozen raw intents required")
    gate = np.asarray(gate, dtype=bool)
    if gate.shape != (5,):
        raise ValueError("Ordered CORE5 agreement gate required")
    c = np.asarray(annual_covariance, dtype=np.float64)
    out, proof = {}, {}
    for arm in ARMS[:-1]:
        out[arm], proof[arm] = RISK.scale(raw[arm], c)
    diagnostic = np.where(gate, out["CS"], 0.)
    out[ARMS[-1]] = diagnostic
    sigma = float(np.sqrt(max(0., diagnostic @ c @ diagnostic)))
    proof[ARMS[-1]] = dict(
        reason="FILTERED_SIZED_CS_NO_REALLOCATION", factor=None,
        cap_bound=None, risk_target_met=bool(abs(sigma-.10) <= 1e-12),
        post_sigma=sigma, shortfall=max(0., .10-sigma),
        above_nominal_risk=bool(sigma > .10+1e-12),
        gross=float(np.abs(diagnostic).sum()), largest=float(np.abs(diagnostic).max()),
        survivor_weights_exactly_sized_CS=True)
    return out, proof


def build_targets(close, available_us, decision_us, *, strict=True):
    """Return five frozen arms and causal proof, using original risk.scale.

    Missing common inputs fail strict admission. A permissive diagnostic call
    retains every calendar row with NaN targets and explicit UNKNOWN status.
    The no-reallocation arm filters sized CS with no second risk scaling;
    removing hedges can increase its estimated risk despite lower exposure.
    """
    if not isinstance(strict, bool):
        raise ValueError("Explicit boolean strict admission required")
    p, t, d = _inputs(close, available_us, decision_us)
    cs, cs_diag = cs_raw_targets(p, t, d)
    sma, sma_ok, means, latest = sma_raw_targets(p, t, d)
    gate = agreement_mask(cs, sma, sma_ok)
    raw = {"CS": cs, "SMA200": sma, "STATIC50": .5*cs + .5*sma,
           "AGREEMENT": np.where(gate, cs, 0.)}
    out = {arm: np.full((len(d), 5), np.nan) for arm in ARMS}
    covariance = np.full((len(d), 5, 5), np.nan)
    status = np.full(len(d), "UNKNOWN", dtype="<U7")
    proof = []
    for i, at in enumerate(d):
        k = _past_index(t, at, SMA_DAYS)
        ready = k is not None and bool(sma_ok[i].all())
        if not ready:
            row = dict(decision_us=int(at), status="UNKNOWN",
                       reason="INCOMPLETE_200_CONTIGUOUS_COMPLETED_FINITE_POSITIVE_CORE5_CLOSES")
            proof.append(row)
            if strict:
                raise ValueError(f"Strict common source admission failed at {int(at)}: {row['reason']}")
            continue
        history = p[k-30:k+1]
        returns = np.diff(history, axis=0) / history[:-1]
        c = np.cov(returns, rowvar=False, ddof=1) * 365
        row = dict(decision_us=int(at), status="READY",
                   last_close_available_us=int(t[k]),
                   oldest_sma_close_available_us=int(t[k-199]), sma_close_count=200,
                   oldest_risk_close_available_us=int(t[k-30]), risk_return_count=30,
                   cs_rank_us=int(cs_diag["rank_us"][i]),
                   sma_eligible=sma_ok[i].tolist(), sma_sign=np.sign(sma[i]).astype(int).tolist(),
                   agreement_mask=gate[i].tolist(), arms={})
        sized, row["arms"] = size_day({arm: raw[arm][i] for arm in ARMS[:-1]}, gate[i], c)
        for arm in ARMS:
            out[arm][i] = sized[arm]
        covariance[i] = c
        status[i] = "READY"
        proof.append(row)
    for arm in ARMS:
        finite = status == "READY"
        w = out[arm][finite]
        if (not np.isfinite(w).all() or np.max(np.abs(w), initial=0.) > .30+1e-12
                or np.max(np.abs(w).sum(axis=1), initial=0.) > .60+1e-12):
            raise ValueError(f"Finite original exposure caps failed for {arm}")
    return dict(targets=out, raw=raw, annual_covariance=covariance, proof=proof,
                source_status=status, sma_eligible=sma_ok, sma_mean=means,
                sma_latest_close=latest, agreement_mask=gate,
                cs_current_eligible=np.asarray(cs_diag["current_eligible"], dtype=bool),
                cs_diagnostics=cs_diag)
