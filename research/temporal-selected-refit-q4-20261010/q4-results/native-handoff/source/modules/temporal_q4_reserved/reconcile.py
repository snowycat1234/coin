"""Independent accounting algebra adapted from July to real terminal arrays."""

import numpy as np

from modules.temporal_short_expansion.adapter import expand
from modules.temporal_two_expert.inputs import CORE5

from .data import EXECUTION_DELAY_US


def cost(delta, price):
    fees = float((0.00055 * price * (np.abs(delta) + 0.0008 * delta)).sum())
    spread = float((0.0004 * price * np.abs(delta)).sum())
    return fees, spread, spread


def reconcile(request, episode, targets, mapped, report):
    """Independent algebra on the frozen path; no second wallet or optimizer."""
    nav = report["nav"].detach().numpy()
    quantity = report["quantity"].detach().numpy()
    held = report["boundary_held_quantity"].detach().numpy()
    prices, coeff = episode.prices, episode.funding_coeff
    budget = np.stack([r["budget"] for r in mapped])
    released = np.stack([r["released_prior"] for r in mapped])
    distance = np.abs(budget - released).sum(1)
    masks = np.stack([c.eligible for c in episode.internal.contexts])
    if (
        np.any(distance > 0.1 + 1e-12)
        or np.any(budget[~masks])
        or np.any(request[:, 2:4])
        or np.any(targets[-1])
        or np.any(quantity[-1])
        or np.any(held[-1])
    ):
        raise ValueError("Original masks, post-release ramp and paid forced-flat contract failed")
    np.testing.assert_allclose(budget.sum(1), 1, rtol=0, atol=1e-12)
    np.testing.assert_allclose(request.sum(1), 1, rtol=0, atol=1e-12)
    if min(budget.min(), request.min()) < 0:
        raise ValueError("Simplex budget required")
    np.testing.assert_allclose(
        quantity, 0.99 * nav[:-1, None] * targets / prices, rtol=1e-13, atol=1e-12
    )
    rows, carry = [], np.zeros(5)
    totals = np.zeros(3)
    funding_total, price_total, turnover_total, reduction_total, residual = 0.0, 0.0, 0.0, 0.0, 0.0
    for t in range(len(targets)):
        active = t < len(targets) - 1
        boundary_price = prices[t + 1] if active else prices[t]
        opening = cost(quantity[t] - carry, prices[t])
        reduction = cost(held[t] - quantity[t], boundary_price)
        payment, reduction_payment = sum(opening), sum(reduction)
        funding = -float(quantity[t] @ coeff[t]) if active else 0.0
        price_pnl = float(quantity[t] @ (boundary_price - prices[t])) if active else 0.0
        expected = nav[t] - payment + price_pnl + funding - reduction_payment
        residual = max(residual, abs(expected - nav[t + 1]))
        opening_nav = nav[t] - payment
        before_reduction_nav = nav[t + 1] + reduction_payment
        opening_abs = np.abs(quantity[t]) * prices[t]
        before_abs = np.abs(quantity[t]) * boundary_price
        boundary_abs = np.abs(held[t]) * boundary_price
        if (
            opening_abs.sum() > 0.6 * opening_nav + 1e-8
            or np.any(opening_abs > 0.3 * opening_nav + 1e-8)
            or boundary_abs.sum() > 0.6 * nav[t + 1] + 1e-8
            or np.any(boundary_abs > 0.3 * nav[t + 1] + 1e-8)
        ):
            raise ValueError("Original opening/post-reduction position caps failed")
        covariance = np.cov(episode.contexts[t].past_returns30, rowvar=False, ddof=1) * 365
        annual_risk = math_sqrt(float(targets[t] @ covariance @ targets[t]))
        if (
            annual_risk > 0.1 + 1e-12
            or mapped[t]["allocated_leg_gross"] > 0.6 + 1e-12
            or mapped[t]["allocated_underlier_gross"].max() > 0.3 + 1e-12
        ):
            raise ValueError("Original allocation/covariance caps failed")
        turnover = float(
            (np.abs(quantity[t] - carry) * prices[t]).sum()
            + (np.abs(held[t] - quantity[t]) * boundary_price).sum()
        )
        totals += np.asarray(opening) + reduction
        funding_total += funding
        price_total += price_pnl
        turnover_total += turnover
        reduction_total += reduction_payment
        row = dict(
            decision_us=int(episode.windows.decision_us[t]),
            execution_us=int(episode.windows.decision_us[t] + EXECUTION_DELAY_US),
            start_nav=float(nav[t]),
            end_nav=float(nav[t + 1]),
            price_PnL=price_pnl,
            funding_PnL=funding,
            fees=opening[0] + reduction[0],
            spread=opening[1] + reduction[1],
            slippage=opening[2] + reduction[2],
            charged_reduction_cost=reduction_payment,
            turnover_USDT=turnover,
            opening_actual_gross=float(opening_abs.sum() / opening_nav),
            opening_actual_net=float(quantity[t] @ prices[t] / opening_nav),
            opening_maximum_asset_gross=float(opening_abs.max() / opening_nav),
            before_reduction_actual_gross=float(before_abs.sum() / before_reduction_nav),
            before_reduction_maximum_asset_gross=float(before_abs.max() / before_reduction_nav),
            boundary_actual_gross=float(boundary_abs.sum() / nav[t + 1]),
            boundary_actual_net=float(held[t] @ boundary_price / nav[t + 1]),
            boundary_maximum_asset_gross=float(boundary_abs.max() / nav[t + 1]),
            allocated_leg_gross=float(mapped[t]["allocated_leg_gross"]) if t < 91 else 0.0,
            allocated_maximum_asset_gross=float(mapped[t]["allocated_underlier_gross"].max())
            if t < 91
            else 0.0,
            covariance_annual_vol=annual_risk,
            ramp_L1_after_eligibility_release=float(distance[t]),
            terminal_paid_flat=bool(t == 91),
        )
        for j, name in enumerate(CORE5):
            row["held_" + name] = float(held[t, j])
        rows.append(row)
        carry = held[t]
    np.testing.assert_allclose(
        totals,
        [float(report[n].detach()) for n in ("fees", "spread", "slippage")],
        rtol=1e-12,
        atol=1e-10,
    )
    np.testing.assert_allclose(
        funding_total, float(report["funding"].detach()), rtol=1e-12, atol=1e-10
    )
    np.testing.assert_allclose(
        reduction_total, float(report["charged_reduction_cost"].detach()), rtol=1e-12, atol=1e-10
    )
    if (
        residual > 1e-8
        or abs(price_total + funding_total - totals.sum() - (nav[-1] - 10000)) > 1e-8
    ):
        raise ValueError("Complete independent PnL algebra failed")
    daily_return = nav[1:] / nav[:-1] - 1
    utility = float(np.sum(np.log(nav[1:] / nav[:-1]) - 5 * np.minimum(daily_return, 0) ** 2))
    np.testing.assert_allclose(
        utility, float(report["utility_sum"].detach()), rtol=1e-12, atol=1e-14
    )
    active = rows[:91]
    metrics = dict(
        capital=10000.0,
        decisions=92,
        active_intervals=91,
        net_PnL=float(nav[-1] - 10000),
        return_fraction=float(nav[-1] / 10000 - 1),
        utility_sum=utility,
        mean_loss=-utility / 92,
        maximum_daily_drawdown=float(np.max(1 - nav / np.maximum.accumulate(nav))),
        fees=float(totals[0]),
        spread=float(totals[1]),
        slippage=float(totals[2]),
        total_cost=float(totals.sum()),
        funding=funding_total,
        price_PnL=price_total,
        turnover_USDT=turnover_total,
        charged_reduction_cost=reduction_total,
        risk_events=len(report["risk_events"]),
        terminal_paid_cost=sum(cost(-held[-2], prices[-1])),
        paid_terminal_cash=bool(report["terminal_cash_realized"]),
        terminal_NAV=float(nav[-1]),
        request_mean=request.mean(0).tolist(),
        applied_budget_mean=expand(budget).mean(0).tolist(),
        maximum_ramp_L1_after_release=float(distance.max()),
        accounting_maximum_NAV_error=residual,
        cost_funding_utility_independent_algebra_pass=True,
        status="CHARGED_DAILY_SURROGATE_NOT_NATIVE",
    )
    for name in (
        "opening_actual_gross",
        "opening_maximum_asset_gross",
        "before_reduction_actual_gross",
        "before_reduction_maximum_asset_gross",
        "boundary_actual_gross",
        "boundary_maximum_asset_gross",
        "allocated_leg_gross",
        "allocated_maximum_asset_gross",
        "covariance_annual_vol",
    ):
        metrics["maximum_" + name] = max(r[name] for r in active)
        metrics["mean_active_" + name] = float(np.mean([r[name] for r in active]))
    for name in ("opening_actual_net", "boundary_actual_net"):
        metrics["mean_active_" + name] = float(np.mean([r[name] for r in active]))
        metrics["minimum_" + name], metrics["maximum_" + name] = (
            min(r[name] for r in active),
            max(r[name] for r in active),
        )
    return metrics, rows


def math_sqrt(value):
    if value < -1e-15:
        raise ValueError("Invalid covariance variance")
    return float(np.sqrt(max(0.0, value)))
