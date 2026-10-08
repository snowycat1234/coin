"""Independent NumPy mathematics for continuous E5 budgets and a daily proxy.

This is not NativeDailySimulator and has no order, margin or liquidation engine.
The mapper preserves the frozen E5 release/ramp/allocated-leg/covariance checks.
The wallet proxy costs NET quantity changes once, carries units, and closes on
the common final cash day. Gradients are analytic on the current active set;
L1 ties use sign(0)=0. No smoothing, relaxed costs, training or networking here.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

DAY_US = 86_400_000_000
E5 = ("CASH", "VOL_MANAGED_HOLD", "PUBLIC_SMA50_200_SIGNED", "DONCHIAN_EXIT10", "CSMOM21")
CORE5 = ("BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT", "DOGEUSDT")
FEATURES = 43  # same causal market13 + frozen expert25 + expert availability5
HIDDEN = 8
SEED = 20261009


class ProxyExposureBreach(ValueError):
    """A diagnostic STOP, never a fabricated native reduction/liquidation."""

    def __init__(self, day_index, boundary_index, equity, exposure):
        self.day_index = day_index
        self.boundary_index = boundary_index
        self.equity = equity
        self.exposure = np.asarray(exposure).copy()
        super().__init__(f"STOP_PROXY_EXPOSURE_BREACH at day {day_index}, boundary {boundary_index}; "
                         "native risk orders required")


def finite(value, shape, name):
    result = np.asarray(value, dtype=np.float64)
    if result.shape != shape or not np.isfinite(result).all():
        raise ValueError(f"Complete finite {name}, shape {shape}, required")
    return result


def simplex(value):
    result = finite(value, (5,), "ordered E5 simplex")
    if np.any(result < 0) or abs(float(result.sum()) - 1) > 1e-12:
        raise ValueError("Nonnegative E5 budget must sum to one")
    return result


@dataclass(frozen=True)
class Context:
    decision_us: int
    available_us: int
    expert_targets: np.ndarray
    eligible: np.ndarray
    past_returns30: np.ndarray
    market13: np.ndarray
    target_available_us: np.ndarray
    symbol_order: tuple = CORE5
    expert_order: tuple = E5

    def validate(self):
        if (type(self.decision_us) is not int or self.decision_us < 0
                or self.decision_us % DAY_US or type(self.available_us) is not int
                or not 0 <= self.available_us <= self.decision_us
                or tuple(self.symbol_order) != CORE5 or tuple(self.expert_order) != E5):
            raise ValueError("Exact causal daily clocks and E5/CORE5 identity required")
        targets = finite(self.expert_targets, (5, 5), "frozen expert targets")
        mask = np.asarray(self.eligible)
        if mask.shape != (5,) or mask.dtype != bool or not mask[0] or np.any(targets[0]):
            raise ValueError("Explicit expert eligibility and available zero CASH required")
        finite(self.past_returns30, (30, 5), "past-only covariance returns")
        finite(self.market13, (13,), "causal market13")
        clocks = np.asarray(self.target_available_us)
        if (clocks.shape != (5,) or clocks.dtype.kind not in "iu"
                or np.any(clocks < 0) or np.any(clocks > self.decision_us)):
            raise ValueError("Every frozen expert target must be available at decision")

    def features(self):
        self.validate()
        # An unavailable expert's known target may still be supplied for identity,
        # but cannot become a tradable leg. Both arms see these exact same inputs.
        return np.r_[self.market13, self.expert_targets.ravel(), self.eligible.astype(float)]


def map_budget(prior, request, context):
    """Exact forward release -> L1 ramp -> legs -> net -> covariance CHECK.

    Return budget, net targets, request/prior Jacobians and leg-risk diagnostics.
    Expert targets are already risk scaled; do not apply another vol scaler.
    Availability release may exceed .1 relative to the unreleased old budget,
    as in the frozen mapper. The .1 constraint applies AFTER release to CASH.
    """
    context.validate()
    prior, request = simplex(prior), simplex(request)
    release = np.eye(5)
    for k in np.flatnonzero(~context.eligible):
        release[k, k] = 0
        release[0, k] = 1
    previous, desired = release @ prior, release @ request
    change = desired - previous
    distance = float(np.abs(change).sum())
    if distance > .1:
        scale = .1 / distance
        jac = scale * (np.eye(5) - np.outer(change, np.sign(change)) / distance)
    else:
        scale, jac = 1., np.eye(5)
    budget = previous + scale * change
    simplex(budget)
    legs = budget[:, None] * context.expert_targets
    underlier_gross = np.abs(legs).sum(axis=0)
    allocated_gross = float(underlier_gross.sum())
    if allocated_gross > .6 + 1e-12 or np.any(underlier_gross > .3 + 1e-12):
        raise ValueError("Allocated expert legs exceed caps before netting")
    target = legs.sum(axis=0)
    covariance = np.cov(context.past_returns30, rowvar=False, ddof=1) * 365
    variance = float(target @ covariance @ target)
    if variance < -1e-15 or variance > .1 ** 2 + 1e-12:
        raise ValueError("Frozen combination exceeds existing covariance budget")
    return dict(budget=budget, targets=target, request_jacobian=jac @ release,
                prior_jacobian=(np.eye(5) - jac) @ release,
                allocated_leg_gross=allocated_gross, allocated_underlier_gross=underlier_gross,
                annual_vol=float(np.sqrt(max(0., variance))), released_prior=previous)


def mapped_path(requests, contexts):
    """Each fragment starts at CASH and has its own charged final cash day."""
    if len(contexts) < 2:
        raise ValueError("A fragment needs at least an active day and final cash day")
    if any(b.decision_us - a.decision_us != DAY_US for a, b in zip(contexts, contexts[1:])):
        raise ValueError("Date gaps must be separate wallets, never concatenated")
    requests = finite(requests, (len(contexts), 5), "chronological E5 requests")
    prior = np.array([1., 0., 0., 0., 0.])
    records, targets = [], []
    for t, context in enumerate(contexts):
        proposal = map_budget(prior, requests[t], context)
        prior = proposal["budget"]
        targets.append(proposal["targets"] if t < len(contexts) - 1 else np.zeros(5))
        records.append(proposal)
    return np.asarray(targets), records


def mapping_vjp(target_gradient, records, contexts):
    gradient = finite(target_gradient, (len(contexts), 5), "target gradient")
    result = np.zeros_like(gradient)
    carry = np.zeros(5)
    for t in range(len(contexts) - 1, -1, -1):
        own = contexts[t].expert_targets @ gradient[t]
        if t == len(contexts) - 1:
            own = np.zeros(5)  # final targets forced to CASH
        adjoint = carry + own
        result[t] = records[t]["request_jacobian"].T @ adjoint
        carry = records[t]["prior_jacobian"].T @ adjoint
    return result


@dataclass(frozen=True)
class Costs:
    fee: float = .00055
    half_spread: float = .0004
    slippage: float = .0004
    sizing_buffer: float = .99

    def validate(self):
        if (self.fee != .00055 or self.half_spread != .0004 or self.slippage != .0004
                or self.sizing_buffer != .99):
            raise ValueError("Fixed BASE27 full costs and existing .99 sizing buffer required")


def net_trade_cost(delta, midpoint, costs=Costs()):
    """Midpoint PnL basis; charge friction ONCE plus fee at adverse fill price.

    Long/short flip turnover is abs(new_qty-old_qty), NOT expert-leg turnover.
    Fee = fee_rate * mid * (abs(delta) + friction * delta).
    """
    costs.validate()
    friction = costs.half_spread + costs.slippage
    spread = np.abs(delta) * midpoint * costs.half_spread
    slip = np.abs(delta) * midpoint * costs.slippage
    fee = costs.fee * midpoint * (np.abs(delta) + friction * delta)
    slope = midpoint * ((friction + costs.fee) * np.sign(delta) + costs.fee * friction)
    return fee + spread + slip, slope, fee, spread, slip


def daily_proxy(targets, prices, funding_coeff, *, costs=Costs(), downside=5.):
    """Analytic daily proxy and objective gradient, NOT a native wallet.

    prices[t] conflates decision sizing close, fill mid and mark: daily-only
    simplification. funding_coeff[t,j] is sum(strictly-past event mark * rate)
    for events in (decision[t], decision[t+1]], BEFORE next day's fill. It has
    USDT per base unit; it is not a daily rate times a guessed price. No missing
    mark/rate/price is zero filled. Initial ownership is zero. Last day's target
    must be zero, with paid close at that day's start; no second terminal bill.

    Stop if boundary observations breach actual caps; intraday risk and fills
    remain unrepresented. Daily utility is log(NAV ratio)-5*negative_return^2.
    """
    w = np.asarray(targets, dtype=float)
    if w.ndim != 2 or w.shape[1] != 5 or len(w) < 2:
        raise ValueError("Complete CORE5 fragment target path required")
    t_count = len(w)
    w = finite(w, (t_count, 5), "targets")
    p = finite(prices, (t_count + 1, 5), "strict daily prices")
    f = finite(funding_coeff, (t_count, 5), "complete event funding coefficient")
    if np.any(p <= 0) or np.any(w[-1]) or downside != 5.:
        raise ValueError("Positive prices, common final cash day and fixed utility required")
    if np.any(np.abs(w) > .3 + 1e-12) or np.any(np.abs(w).sum(axis=1) > .6 + 1e-12):
        raise ValueError("Target caps exceeded")
    costs.validate()
    nav, quantities, slopes, net_returns = [10000.], [], [], []
    fee_path, spread_path, slip_path, funding_path, gross_path = [], [], [], [], []
    prior = np.zeros(5)
    for t in range(t_count):
        quantity = costs.sizing_buffer * nav[-1] * w[t] / p[t]
        charge, slope, fee, spread, slip = net_trade_cost(quantity - prior, p[t], costs)
        after_cost = nav[-1] - float(charge.sum())
        gross = float(quantity @ (p[t + 1] - p[t]))
        funding = -float(quantity @ f[t])
        following = after_cost + gross + funding
        for stamp, equity in ((t, after_cost), (t + 1, following)):
            exposure = np.abs(quantity) * p[stamp]
            if (equity <= 0 or np.any(exposure > .3 * equity + 1e-8)
                    or exposure.sum() > .6 * equity + 1e-8):
                raise ProxyExposureBreach(t, stamp, equity, exposure)
        quantities.append(quantity)
        slopes.append(slope)
        net_returns.append(following / nav[-1] - 1)
        nav.append(following)
        fee_path.append(float(fee.sum()))
        spread_path.append(float(spread.sum()))
        slip_path.append(float(slip.sum()))
        gross_path.append(gross)
        funding_path.append(funding)
        prior = quantity
    nav, q, slopes = np.asarray(nav), np.asarray(quantities), np.asarray(slopes)
    returns = np.asarray(net_returns)
    utility = np.log(nav[1:] / nav[:-1]) - downside * np.minimum(returns, 0.) ** 2
    # Reverse adjoint includes wallet compounding, quantity carry and all costs.
    grad = np.zeros_like(w)
    equity_carry, quantity_carry = 0., np.zeros(5)
    for t in range(t_count - 1, -1, -1):
        negative = min(returns[t], 0.)
        adjoint = equity_carry + 1 / nav[t + 1] - 2 * downside * negative / nav[t]
        local_equity = -1 / nav[t] + 2 * downside * negative * nav[t + 1] / nav[t] ** 2
        quantity_adjoint = (quantity_carry + adjoint *
                            (p[t + 1] - p[t] - f[t] - slopes[t]))
        grad[t] = quantity_adjoint * costs.sizing_buffer * nav[t] / p[t]
        equity_carry = (adjoint + local_equity +
                        float(quantity_adjoint @ (costs.sizing_buffer * w[t] / p[t])))
        quantity_carry = adjoint * slopes[t]
    grad[-1] = 0.  # forced cash action is never a learnable final target
    return dict(utility_sum=float(utility.sum()), target_gradient=grad, nav=nav,
                quantity=q, net_return=returns, net_PnL=float(nav[-1] - 10000.),
                fees=float(sum(fee_path)), spread=float(sum(spread_path)),
                slippage=float(sum(slip_path)), funding=float(sum(funding_path)),
                gross=float(sum(gross_path)), terminal_cash_realized=True,
                status="DAILY_PROXY_ONLY_NOT_NATIVE_OR_REAL_MONEY")


class SmallBudgetHead:
    """Exactly 397 parameters: causal 43 -> tanh8 -> softmax5, fixed seed.

    Shared training-only standardizer must be supplied before either arm.
    Fitting is a separate explicit API; neither import nor calibration fits it.
    """

    def __init__(self, mean, scale):
        self.mean = finite(mean, (FEATURES,), "common training-only means").copy()
        self.scale = finite(scale, (FEATURES,), "common training-only scales").copy()
        if np.any(self.scale <= 0):
            raise ValueError("Positive frozen training-only scales required")
        rng = np.random.default_rng(SEED)
        self.parameters = dict(w1=rng.normal(0., .05, (FEATURES, HIDDEN)), b1=np.zeros(HIDDEN),
                               w2=rng.normal(0., .05, (HIDDEN, 5)), b2=np.zeros(5))

    def forward(self, features):
        x = np.asarray(features, dtype=float)
        x = finite(x, (len(x), FEATURES), "shared causal features")
        x = (x - self.mean) / self.scale
        hidden = np.tanh(x @ self.parameters["w1"] + self.parameters["b1"])
        logits = hidden @ self.parameters["w2"] + self.parameters["b2"]
        logits -= logits.max(axis=1, keepdims=True)
        request = np.exp(logits)
        request /= request.sum(axis=1, keepdims=True)
        return request, (x, hidden, request)

    def backward(self, request_gradient, cache):
        x, hidden, request = cache
        g = finite(request_gradient, request.shape, "request gradient")
        logits = request * (g - (g * request).sum(axis=1, keepdims=True))
        hidden_grad = (logits @ self.parameters["w2"].T) * (1 - hidden ** 2)
        return dict(w1=x.T @ hidden_grad, b1=hidden_grad.sum(axis=0),
                    w2=hidden.T @ logits, b2=logits.sum(axis=0))


def loss_and_gradient(head, fragments, arm):
    """Both arms identical data/head/mapper; only CE vs own path utility differs.

    Each fragment dict contains contexts, prices, funding_coeff and optional
    greedy_request (actual winning candidate REQUEST, not ramped budget).
    Caller must bind labels and clocks using the preregistered protocol before
    this pure in-memory calculation. This function performs no fitting.
    """
    if arm not in ("IMITATE_REQUEST", "DIRECT_PATH_UTILITY") or not fragments:
        raise ValueError("Explicit fixed paired arm and independent fragments required")
    grads = {k: np.zeros_like(v) for k, v in head.parameters.items()}
    numerator, denominator, reports = 0., 0, []
    for fragment in fragments:
        contexts = fragment["contexts"]
        request, cache = head.forward(np.asarray([c.features() for c in contexts]))
        targets, records = mapped_path(request, contexts)
        path = daily_proxy(targets, fragment["prices"], fragment["funding_coeff"])
        if arm == "IMITATE_REQUEST":
            teacher = finite(fragment["greedy_request"], request.shape, "greedy actual request")
            if not all(np.array_equal(row, np.eye(5)[np.argmax(row)]) for row in teacher[:-1]):
                raise ValueError("Original greedy one-hot REQUEST labels required")
            numerator -= float((teacher[:-1] * np.log(request[:-1])).sum())
            denominator += len(contexts) - 1
            request_gradient = np.zeros_like(request)
            request_gradient[:-1] = -teacher[:-1] / request[:-1]
        else:
            numerator -= path["utility_sum"]
            denominator += len(contexts)
            request_gradient = -mapping_vjp(path["target_gradient"], records, contexts)
        local = head.backward(request_gradient, cache)
        for name in grads:
            grads[name] += local[name]
        reports.append(path)
    return numerator / denominator, {k: v / denominator for k, v in grads.items()}, reports
