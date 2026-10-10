"""Reusable causal expert diagnostics and real expert-budget target allocation.

This module never opens market files, starts a fit, or runs a wallet on import.
Reference utility is a training proxy. Portfolio economics must use the existing
shared quantity/isolated wallet after target netting; expert PnLs are not added.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

DAY_US = 86_400_000_000


def clock(values, name):
    raw = np.asarray(values)
    if (
        raw.ndim != 1
        or raw.dtype.kind not in "iu"
        or not len(raw)
        or np.any(raw < 0)
        or np.any(raw > np.iinfo(np.int64).max)
    ):
        raise ValueError(f"{name}: nonnegative integer microsecond clock required")
    return raw.astype(np.int64)


def chronological_training_mask(
    decisions, label_available, complete, validation_start, embargo_days=7
):
    d = clock(decisions, "decisions")
    a = clock(label_available, "label_available")
    valid = np.asarray(complete)
    if (
        a.shape != d.shape
        or valid.shape != d.shape
        or valid.dtype != bool
        or np.any(np.diff(d) != DAY_US)
        or np.any(a <= d)
    ):
        raise ValueError("Full daily calendar, future label maturity, and Boolean masks required")
    if (
        not isinstance(validation_start, int)
        or not isinstance(embargo_days, int)
        or embargo_days < 0
    ):
        raise ValueError("Explicit validation clock and nonnegative embargo required")
    cutoff = validation_start - embargo_days * DAY_US
    return valid & (d < validation_start) & (a < cutoff)


def nonoverlap_indices(decisions, label_available, eligible):
    """Greedy time intervals; gaps never become adjacent independent samples."""
    d, a = clock(decisions, "decisions"), clock(label_available, "label_available")
    e = np.asarray(eligible)
    if (
        a.shape != d.shape
        or e.shape != d.shape
        or e.dtype != bool
        or np.any(np.diff(d) <= 0)
        or np.any(a <= d)
    ):
        raise ValueError("Ordered full clocks and explicit maturity required")
    selected = []
    previous_end = -1
    for i in np.flatnonzero(e):
        if int(d[i]) >= previous_end:
            selected.append(int(i))
            previous_end = int(a[i])
    return np.asarray(selected, dtype=np.int64)


def validate_feature_clocks(decisions, feature_available_us, feedback_available_us):
    d = clock(decisions, "feature decisions")
    f = clock(feature_available_us, "feature availability")
    r = clock(feedback_available_us, "feedback availability")
    if f.shape != d.shape or r.shape != d.shape or np.any(f > d) or np.any(r >= d):
        raise ValueError(
            "Market features must be available; completed feedback must be strictly past"
        )


@dataclass(frozen=True)
class RankProvenance:
    fit_completed_us: np.ndarray
    train_cutoff_us: np.ndarray
    maximum_training_label_available_us: np.ndarray
    maximum_scaler_source_available_us: np.ndarray
    model_sha256: tuple[str, ...]
    scaler_sha256: tuple[str, ...]

    def validate(self, decision_us):
        """A later fit/scaler cannot manufacture an earlier rank prediction."""
        d = clock(decision_us, "rank decisions")
        arrays = [
            clock(getattr(self, name), name)
            for name in (
                "fit_completed_us",
                "train_cutoff_us",
                "maximum_training_label_available_us",
                "maximum_scaler_source_available_us",
            )
        ]
        if any(a.shape != d.shape for a in arrays):
            raise ValueError("One rank model/scaler provenance record per prediction required")
        fit, cutoff, labels, scaler = arrays
        if (
            np.any(fit > d)
            or np.any(cutoff > fit)
            or np.any(labels >= cutoff)
            or np.any(scaler >= cutoff)
        ):
            raise ValueError("Late rank model, unmature training label, or non-training scaler")
        for hashes in (self.model_sha256, self.scaler_sha256):
            if len(hashes) != len(d) or any(
                len(h) != 64 or any(c not in "0123456789abcdef" for c in h) for h in hashes
            ):
                raise ValueError("Exact model and scaler SHA256 required for every prediction")


def training_complementarity(net_returns, targets, train_mask, states=None):
    """Training-only correlations, signed position overlap and shared loss tails.

    These are descriptive diagnostics. Negative low-correlation streams still
    need positive incremental utility in an actual shared training wallet. This
    function intentionally does not select a pool or average subwallet profits.
    """
    r, t = np.asarray(net_returns, float), np.asarray(targets, float)
    mask = np.asarray(train_mask)
    if (
        r.ndim != 2
        or t.ndim != 3
        or t.shape[:2] != r.shape
        or mask.shape != (len(r),)
        or mask.dtype != bool
    ):
        raise ValueError(
            "Aligned daily net feedback, expert/asset targets and training mask required"
        )
    valid = mask & np.isfinite(r).all(axis=1) & np.isfinite(t).all(axis=(1, 2))
    if valid.sum() < 30 or np.any(r[valid] <= -1):
        raise ValueError("Insufficient common valid training feedback or bankrupt return")
    rv, tv = r[valid], t[valid]
    sd = rv.std(axis=0)
    n = r.shape[1]
    pairs = []
    tails = rv <= np.quantile(rv, 0.05, axis=0)
    tails &= rv < 0  # a constant CASH stream does not have a losing tail
    state_values = None
    if states is not None:
        state_values = np.asarray(states)
        if state_values.shape != (len(r),):
            raise ValueError("Past-only regime state per calendar day required")
        state_values = state_values[valid]
    for a in range(n):
        for b in range(a + 1, n):
            corr = float(np.corrcoef(rv[:, a], rv[:, b])[0, 1]) if sd[a] > 0 and sd[b] > 0 else None
            wa, wb = tv[:, a], tv[:, b]
            same_sign = wa * wb > 0
            denominator = float(np.maximum(np.abs(wa), np.abs(wb)).sum())
            overlap = float((np.minimum(np.abs(wa), np.abs(wb)) * same_sign).sum())
            conditions = []
            if state_values is not None:
                for state in np.unique(state_values):
                    own = state_values == state
                    if own.sum() >= 14:
                        conditions.append(
                            dict(
                                state=str(state),
                                days=int(own.sum()),
                                mean_net_excess_a_over_b=float((rv[own, a] - rv[own, b]).mean()),
                                fraction_a_better=float((rv[own, a] > rv[own, b]).mean()),
                            )
                        )
            pairs.append(
                dict(
                    expert_a=a,
                    expert_b=b,
                    net_return_correlation=corr,
                    signed_position_overlap=overlap / denominator if denominator else None,
                    shared_bottom5_loss_days=int((tails[:, a] & tails[:, b]).sum()),
                    a_tail_days=int(tails[:, a].sum()),
                    b_tail_days=int(tails[:, b].sum()),
                    conditions=conditions,
                )
            )
    return dict(
        common_training_days=int(valid.sum()),
        missing_training_days=int((mask & ~valid).sum()),
        training_log_growth=np.log1p(rv).sum(axis=0).tolist(),
        pairs=pairs,
        portfolio_increment="NOT_COMPUTED_REQUIRES_SHARED_WALLET",
        pool_selected=False,
    )


def budget_path(
    predicted_net_risk_utility,
    utility_scale,
    *,
    cash_index,
    eligible=None,
    initial=None,
    max_l1=0.1,
):
    """Conditional simplex budgets; missing experts release budget to CASH.

    Scaling is frozen from mature training utilities. max_l1 applies to expert
    budget changes. Execution/risk reductions in the wallet must retain priority.
    """
    from scripts.investment.regime_ranking_screen import bounded_path

    scores = np.asarray(predicted_net_risk_utility, float)
    if scores.ndim != 2 or not len(scores) or not np.isfinite(scores).all():
        raise ValueError("Finite utility prediction matrix required")
    n, experts = scores.shape
    if (
        not isinstance(cash_index, int)
        or not 0 <= cash_index < experts
        or not np.isfinite(utility_scale)
        or utility_scale <= 0
        or not 0 < max_l1 <= 2
    ):
        raise ValueError("Explicit CASH, positive frozen scale and valid L1 budget required")
    available = np.ones((n, experts), bool) if eligible is None else np.asarray(eligible)
    if (
        available.shape != scores.shape
        or available.dtype != bool
        or not available[:, cash_index].all()
    ):
        raise ValueError("Boolean expert availability required; CASH must always be available")
    masked = np.where(available, scores, -np.inf)
    with np.errstate(over="ignore", under="ignore"):
        logits = (masked - masked.max(axis=1, keepdims=True)) / utility_scale
        desired = np.exp(logits)
    desired[~available] = 0
    # If only CASH is eligible and exp underflows, explicitly retain it.
    zero = desired.sum(axis=1) == 0
    desired[zero, cash_index] = 1
    desired /= desired.sum(axis=1, keepdims=True)
    previous = np.zeros(experts) if initial is None else np.asarray(initial, float).copy()
    if initial is None:
        previous[cash_index] = 1
    if (
        previous.shape != (experts,)
        or not np.isfinite(previous).all()
        or np.any(previous < 0)
        or not np.isclose(previous.sum(), 1, atol=1e-12, rtol=0)
    ):
        raise ValueError("Initial complete-capital simplex budget required")
    out = []
    forced = []
    for i, request in enumerate(desired):
        # Loss of current eligibility is a forced reduction, not discretionary
        # turnover. Clear it immediately and never reallocate it to another risk.
        freed = float(previous[~available[i]].sum())
        before = previous.copy()
        previous[~available[i]] = 0
        previous[cash_index] += freed
        current = bounded_path([request], previous, max_l1)[0]
        # The next forced eligibility reduction mutates `previous` in place.
        # Persist a copy so that tomorrow cannot rewrite today's saved budget.
        out.append(current.copy())
        forced.append(float(np.abs(previous - before).sum()))
        previous = current.copy()
    return np.asarray(out), dict(
        forced_eligibility_L1=forced,
        discretionary_L1_cap=max_l1,
        cash_initial=True if initial is None else False,
    )


def shared_targets(frames, expert_order, decisions, symbols, budgets):
    """Reuse the accepted same-wallet target combiner and preserve asset order."""
    from scripts.investment.frozen_expert_mixture import combine

    names = tuple(expert_order)
    if len(set(names)) != len(names) or set(frames) != set(names):
        raise ValueError("Exact unique expert identity order required")
    w = np.asarray(budgets, float)
    d = clock(decisions, "target decisions")
    if np.any(np.diff(d) != DAY_US):
        raise ValueError("Full common daily execution calendar required")
    result = combine(frames, list(names), d, tuple(symbols), w)
    # Preserve allocated leg gross separately from one-way net execution.
    source = []
    for name in names:
        lookup = {
            (r["available_us"], r["symbol"]): r["target_weight"]
            for r in frames[name].iter_rows(named=True)
        }
        source.append([[lookup[int(t), s] for s in symbols] for t in decisions])
    allocated = w[:, :, None] * np.asarray(source).transpose(1, 0, 2)
    gross = np.abs(allocated).sum(axis=(1, 2))
    asset_gross = np.abs(allocated).sum(axis=1)
    if np.any(gross > 0.6 + 1e-12) or np.any(asset_gross > 0.3 + 1e-12):
        raise ValueError("Allocated expert legs exceed shared capital caps before netting")
    return result, dict(
        allocated_leg_gross=gross.tolist(),
        allocated_underlier_gross=asset_gross.tolist(),
        one_shared_wallet_required=True,
        subwallet_profits_added=False,
    )


class UtilitySelector:
    """Fixed lightweight utility regressors; caller supplies approved causal data.

    Training targets must be after-cost reference utility minus the registered
    daily-path downside penalty. No market training is invoked by this module.
    Ridge is a control; a small nonlinear challenger needs >=80 disjoint label
    intervals. More overlapping rows do not satisfy this gate.
    """

    def __init__(self, family="RIDGE", seed=20261008):
        if family not in ("RIDGE", "HIST_GB"):
            raise ValueError("Only two preregistered finite model families")
        self.family, self.seed = family, seed

    def fit(
        self,
        x,
        net_risk_utility,
        decisions,
        label_available,
        train_mask,
        cutoff_us,
        *,
        fit_available_us,
        feature_available_us,
        feedback_available_us,
    ):
        from sklearn.ensemble import HistGradientBoostingRegressor
        from sklearn.linear_model import Ridge
        from sklearn.multioutput import MultiOutputRegressor
        from sklearn.pipeline import make_pipeline
        from sklearn.preprocessing import StandardScaler

        x, y = np.asarray(x, float), np.asarray(net_risk_utility, float)
        d, a = clock(decisions, "decisions"), clock(label_available, "label_available")
        validate_feature_clocks(d, feature_available_us, feedback_available_us)
        mask = np.asarray(train_mask)
        if (
            not isinstance(cutoff_us, int)
            or not isinstance(fit_available_us, int)
            or cutoff_us < 0
            or fit_available_us < cutoff_us
        ):
            raise ValueError("Explicit logical fit availability must follow the training cutoff")
        if (
            x.ndim != 2
            or y.ndim != 2
            or len(x) != len(d)
            or len(y) != len(d)
            or a.shape != d.shape
            or mask.shape != d.shape
            or mask.dtype != bool
            or np.any(np.diff(d) <= 0)
            or np.any(a <= d)
            or not mask.any()
        ):
            raise ValueError("Aligned explicit training rows and clocks required")
        if (
            np.any(d[mask] >= cutoff_us)
            or np.any(a[mask] >= cutoff_us)
            or not np.isfinite(x[mask]).all()
            or not np.isfinite(y[mask]).all()
        ):
            raise ValueError("Unmature labels, future data or missing training inputs")
        independent = nonoverlap_indices(d, a, mask)
        minimum = 40 if self.family == "RIDGE" else 80
        if len(independent) < minimum:
            raise ValueError(f"Need {minimum} disjoint mature intervals; have {len(independent)}")
        # Train on the time-disjoint labels, keeping their whole market vectors.
        # Coin count and daily horizon overlap cannot multiply effective support.
        if self.family == "RIDGE":
            model = make_pipeline(StandardScaler(), Ridge(alpha=30.0))
        else:
            model = MultiOutputRegressor(
                HistGradientBoostingRegressor(
                    max_iter=64,
                    max_leaf_nodes=4,
                    max_depth=2,
                    min_samples_leaf=16,
                    l2_regularization=10.0,
                    early_stopping=False,
                    random_state=self.seed,
                ),
                n_jobs=1,
            )
        model.fit(x[independent], y[independent])
        self.model = model
        self.cutoff_us = int(cutoff_us)
        self.fit_available_us = int(fit_available_us)
        self.training_indices = independent
        centered = y[independent] - y[independent].mean(axis=1, keepdims=True)
        self.utility_scale = max(1e-4, float(np.median(np.abs(centered))))
        return self

    def predict(self, x, decision_us, *, feature_available_us, feedback_available_us):
        if not hasattr(self, "model"):
            raise ValueError("No fitted selector; missing checkpoint is not a restored model")
        d = clock(decision_us, "prediction decisions")
        validate_feature_clocks(d, feature_available_us, feedback_available_us)
        values = np.asarray(x, float)
        if (
            values.ndim != 2
            or len(values) != len(d)
            or np.any(d < self.fit_available_us)
            or not np.isfinite(values).all()
        ):
            raise ValueError("Prediction predates fit cutoff or has missing features")
        return self.model.predict(values)
