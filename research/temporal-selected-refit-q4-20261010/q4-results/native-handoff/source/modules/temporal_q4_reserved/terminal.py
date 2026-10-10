"""Evaluation-only terminal ABI adapter of frozen v2 charged boundary kernel.

Original loop and risk/cost semantics retained verbatim except terminal branch:
N real execution prices, N-1 real intervals; final CASH pays cost at p[N-1]
and ends immediately. No repeated price or fabricated funding row is supplied.
Training keeps its original unchanged objective/ABI. Synthetic parity tests bind
this adapter to the original structural-CASH ABI, including gradients.
"""

import numpy as np
import torch

from modules.temporal_risk_proxy_v2.proxy import (
    CONTRACT,
    BoundaryPlan,
    BoundaryStop,
    _breached,
    _cost,
)


def charged_terminal_path(targets, prices, funding_coeff, *, plan):
    """Own-path differentiable rollout; one original complete chronological wallet.

    Funding and marked PnL precede detection at the interval's end. The frozen
    reduce-only intent is charged independently of the next regular rebalance.
    The boundary grid/full-fill assumptions are visible in every result.
    """
    if (
        targets.dtype != torch.float64
        or targets.device.type != "cpu"
        or targets.ndim != 2
        or targets.shape[1] != 5
        or len(targets) < 2
        or not torch.isfinite(targets).all()
        or bool(targets[-1].any())
        or bool((targets.abs() > 0.3 + 1e-12).any())
        or bool((targets.abs().sum(1) > 0.6 + 1e-12).any())
    ):
        raise ValueError("Unchanged finite CORE5 target caps and paid forced-final cash required")
    prices, funding_coeff = map(np.asarray, (prices, funding_coeff))
    n = len(targets)
    if (
        prices.shape != (n, 5)
        or funding_coeff.shape != (n - 1, 5)
        or not np.isfinite(prices).all()
        or not np.isfinite(funding_coeff).all()
        or np.any(prices <= 0)
        or not isinstance(plan, BoundaryPlan)
        or plan.capacity.shape != (n, 5, 5)
    ):
        raise ValueError(
            "Complete original price/funding and explicit boundary execution plan required"
        )
    p = torch.tensor(prices.copy(), dtype=torch.float64)
    f = torch.tensor(funding_coeff.copy(), dtype=torch.float64)
    capacities = torch.tensor(plan.capacity.copy(), dtype=torch.float64)
    nav = [targets.new_tensor(10000.0)]
    carry = targets.new_zeros(5)
    quantities, held, returns, events = [], [], [], []
    fee_total, spread_total, slip_total, funding_total = [targets.new_tensor(0.0) for _ in range(4)]
    reduction_cost_total = targets.new_tensor(0.0)
    for t in range(n):
        weight = targets[t] if t < n - 1 else targets[t] * 0.0
        quantity = 0.99 * nav[-1] * weight / p[t]
        charge, fee, spread, slip = _cost(quantity - carry, p[t])
        after_cost = nav[-1] - charge
        if bool(after_cost <= 0) or _breached(quantity, p[t], after_cost):
            raise BoundaryStop(
                "HARD_POST_FILL_CAP_OR_INSOLVENCY_STOP",
                t,
                equity=after_cost,
                quantity=quantity,
                mark=p[t],
            )
        funding = -(quantity * f[t]).sum() if t < n - 1 else targets.new_tensor(0.0)
        marked = (
            after_cost + (quantity * (p[t + 1] - p[t])).sum() + funding if t < n - 1 else after_cost
        )
        if bool(marked <= 0):
            raise BoundaryStop(
                "INSOLVENCY_STOP",
                t,
                equity=marked,
                quantity=quantity,
                mark=p[t + 1] if t < n - 1 else p[t],
            )
        fee_total, spread_total, slip_total = (
            fee_total + fee,
            spread_total + spread,
            slip_total + slip,
        )
        funding_total = funding_total + funding
        carry = quantity
        if t < n - 1 and _breached(carry, p[t + 1], marked):
            notional = carry.abs() * p[t + 1]
            scale = torch.minimum(
                marked.new_tensor(1.0),
                torch.minimum(
                    0.99 * 0.3 * marked / notional.max(), 0.99 * 0.6 * marked / notional.sum()
                ),
            )
            intent = carry * scale  # frozen before reduction costs, as native schedule
            before_equity = marked
            costs = marked.new_tensor(0.0)
            attempts = 0
            for k in range(5):
                remaining = (carry - intent).abs()
                amount = torch.minimum(remaining, capacities[t, k])
                delta = -carry.sign() * amount  # reduce-only, cannot flip or add
                payment, rfee, rspread, rslip = _cost(delta, p[t + 1])
                carry = torch.where(amount == remaining, intent, carry + delta)
                marked = marked - payment
                costs = costs + payment
                fee_total, spread_total, slip_total = (
                    fee_total + rfee,
                    spread_total + rspread,
                    slip_total + rslip,
                )
                attempts = k + 1
                if bool(marked <= 0):
                    raise BoundaryStop(
                        "REDUCTION_INSOLVENCY_STOP",
                        t,
                        equity=marked,
                        quantity=carry,
                        mark=p[t + 1],
                        reduction_cost=costs,
                    )
                # Identical zero/same-side completion semantics in continuous units.
                if bool((carry.abs() <= intent.abs()).all()):
                    break
            unresolved = _breached(carry, p[t + 1], marked)
            events.append(
                dict(
                    day_index=t,
                    scale=float(scale.detach()),
                    attempts=attempts,
                    equity_before=float(before_equity.detach()),
                    equity_after=float(marked.detach()),
                    quantity_before=quantity.detach().numpy().tolist(),
                    frozen_intent=intent.detach().numpy().tolist(),
                    quantity_after=carry.detach().numpy().tolist(),
                    charged_reduction_cost=float(costs.detach()),
                    unresolved_mark_breach=unresolved,
                )
            )
            reduction_cost_total = reduction_cost_total + costs
            if unresolved:
                raise BoundaryStop(
                    "UNEXECUTABLE_REQUIRED_REDUCTION_STOP",
                    t,
                    equity=marked,
                    quantity=carry,
                    mark=p[t + 1],
                    reduction_cost=costs,
                )
        returns.append(marked / nav[-1] - 1.0)
        nav.append(marked)
        quantities.append(quantity)
        held.append(carry)
    path = torch.stack(nav)
    net_return = torch.stack(returns)
    utility = (
        torch.log(path[1:] / path[:-1])
        - 5.0 * torch.minimum(net_return, net_return.new_tensor(0.0)).square()
    )
    return dict(
        utility_sum=utility.sum(),
        nav=path,
        net_return=net_return,
        quantity=torch.stack(quantities),
        boundary_held_quantity=torch.stack(held),
        net_PnL=path[-1] - 10000.0,
        fees=fee_total,
        spread=spread_total,
        slippage=slip_total,
        funding=funding_total,
        charged_reduction_cost=reduction_cost_total,
        risk_events=events,
        terminal_cash_realized=bool((carry == 0).all()),
        plan_identity=plan.identity,
        status="DAILY_BOUNDARY_DIAGNOSTIC_SURROGATE_NOT_MINUTE_NATIVE",
        contract=CONTRACT,
    )
