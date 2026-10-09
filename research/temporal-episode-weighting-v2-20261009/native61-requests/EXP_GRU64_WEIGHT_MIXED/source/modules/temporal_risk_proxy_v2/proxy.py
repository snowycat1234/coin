"""Charged mandatory reductions on a declared daily boundary grid.

Continuous quantity, immediate boundary-mid fills and no intermediate prices are
explicit *diagnostic surrogate* assumptions. Capacity trials below are not minute
observations. This is not NativeDailySimulator, margin/lot/filter certification,
or a substitute for the native tape. Never label its output minute-native.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import torch

from modules.temporal_two_expert.exact import PROTOTYPE_SHA256, verify_prototype
from modules.temporal_two_expert.inputs import array_digest, digest

CONTRACT = dict(
    version="DAILY_BOUNDARY_CHARGED_REDUCTION_DIAGNOSTIC_V1",
    original_prototype_SHA256=PROTOTYPE_SHA256,
    target_caps="unchanged_allocated_gross.6_asset.3_original_mapper",
    opening_caps="unchanged_post_cost_gross.6_asset.3",
    drift="REDUCTION_REQUIRED;no_new_increase_until_resolved",
    reduction="frozen_quantity_target=min(1,.99*.3*NAV/max_notional,.99*.6*NAV/gross)*held_quantity",
    costs="unchanged_fee.00055_spread.0004_slippage.0004_each_executed_reduction;no_netting_with_next_rebalance",
    funding="unchanged_USDT_per_base_coefficient;held_units_own_entire_interval_before_boundary_reduction",
    execution="declared_immediate_constant_boundary_mid;up_to5_continuous_capacity_trials",
    known_omissions=[
        "minute_latency",
        "intra_interval_marks",
        "actual_quote_volume_capacity",
        "lot_steps",
        "historical_filters",
        "isolated_margin_or_liquidation",
    ],
    minute_native=False,
    historical_execution_certified=False,
)


@dataclass(frozen=True)
class BoundaryPlan:
    capacity: np.ndarray  # day x at-most-five coarse trials x CORE5 base units
    declaration: str

    def __post_init__(self):
        a = np.asarray(self.capacity)
        if (
            a.ndim != 3
            or a.shape[1:] != (5, 5)
            or a.dtype != np.float64
            or not np.isfinite(a).all()
            or np.any(a < 0)
            or self.declaration
            not in (
                "DECLARED_FULL_FILL_DIAGNOSTIC_ONLY",
                "DECLARED_COARSE_CAPACITY_DIAGNOSTIC_ONLY",
            )
        ):
            raise ValueError(
                "Explicit finite diagnostic-only boundary capacity declaration required"
            )
        value = a.copy()
        value.flags.writeable = False
        object.__setattr__(self, "capacity", value)

    @classmethod
    def full_fill_diagnostic(cls, days):
        # This value is an assumption, never a claim about observed liquidity.
        return cls(
            np.full((days, 5, 5), 1e30, dtype=np.float64), "DECLARED_FULL_FILL_DIAGNOSTIC_ONLY"
        )

    @property
    def identity(self):
        return digest(
            dict(
                contract=CONTRACT,
                declaration=self.declaration,
                capacities=array_digest(self.capacity),
            )
        )


class BoundaryStop(ValueError):
    def __init__(self, reason, day, *, equity, quantity, mark, reduction_cost=None):
        self.reason, self.day_index = reason, day
        self.equity = float(equity)
        self.quantity = quantity.detach().numpy().copy()
        self.mark = mark.detach().numpy().copy()
        self.reduction_cost = float(reduction_cost) if reduction_cost is not None else 0.0
        super().__init__(f"{reason} at diagnostic boundary {day}")


def _cost(delta, midpoint):
    absolute = delta.abs()
    fee = 0.00055 * midpoint * (absolute + 0.0008 * delta)
    spread, slippage = 0.0004 * midpoint * absolute, 0.0004 * midpoint * absolute
    return (fee + spread + slippage).sum(), fee.sum(), spread.sum(), slippage.sum()


def _breached(quantity, mark, equity):
    notional = quantity.abs() * mark
    # Exactly the source tolerance; no extra tolerance to permit more exposure.
    return bool((notional > 0.3 * equity + 1e-8).any() or notional.sum() > 0.6 * equity + 1e-8)


def charged_boundary_path(targets, prices, funding_coeff, *, plan):
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
        prices.shape != (n + 1, 5)
        or funding_coeff.shape != (n, 5)
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
        funding = -(quantity * f[t]).sum()
        marked = after_cost + (quantity * (p[t + 1] - p[t])).sum() + funding
        if bool(marked <= 0):
            raise BoundaryStop(
                "INSOLVENCY_STOP", t, equity=marked, quantity=quantity, mark=p[t + 1]
            )
        fee_total, spread_total, slip_total = (
            fee_total + fee,
            spread_total + spread,
            slip_total + slip,
        )
        funding_total = funding_total + funding
        carry = quantity
        if _breached(carry, p[t + 1], marked):
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


def request_loss_and_gradient_v2(requests, episode, prototype, *, plan):
    """Exact continuous-surrogate VJP through the unchanged original request mapper."""
    verify_prototype(prototype)
    targets, records = prototype.mapped_path(requests, episode.contexts)
    w = torch.tensor(targets, dtype=torch.float64, requires_grad=True)
    with torch.enable_grad():
        report = charged_boundary_path(w, episode.prices, episode.funding_coeff, plan=plan)
        gradient = torch.autograd.grad(report["utility_sum"], w)[0].detach().numpy()
    n = len(episode.contexts)
    request_gradient = -prototype.mapping_vjp(gradient, records, episode.contexts) / n
    return -float(report["utility_sum"].detach()) / n, request_gradient, report


class _ChargedPathLoss(torch.autograd.Function):
    @staticmethod
    def forward(ctx, requests, episode, prototype, plan):
        loss, gradient, _ = request_loss_and_gradient_v2(
            requests.detach().cpu().numpy(), episode, prototype, plan=plan
        )
        ctx.save_for_backward(torch.tensor(gradient, dtype=requests.dtype, device=requests.device))
        return requests.new_tensor(loss)

    @staticmethod
    def backward(ctx, upstream):
        (gradient,) = ctx.saved_tensors
        return upstream * gradient, None, None, None


def charged_path_loss(requests, episode, prototype, *, plan):
    """Neural-head bridge for an explicitly declared complete surrogate wallet.

    This builds no optimizer or new checkpoint. A revised training stage must
    bind the objective/plan identities and obtain the missing execution scope.
    """
    if (
        requests.dtype != torch.float64
        or requests.device.type != "cpu"
        or requests.shape != (len(episode.contexts), 5)
        or not torch.isfinite(requests).all()
    ):
        raise ValueError("Chronological CPU float64 E5 request path required")
    return _ChargedPathLoss.apply(requests, episode, prototype, plan)


def require_native_resume_data(packet):
    """Fail closed: daily aggregates cannot identify native risk-order execution."""
    required = {
        "minute_trade_mid",
        "minute_mark",
        "prior_minute_quote_volume",
        "funding_event_us",
        "funding_event_rate",
        "declared_instrument_profile_identity",
        "native_contract_identity",
    }
    if not required <= set(packet):
        raise ValueError(
            "NATIVE_RESUME_NOT_READY: missing minute prices/capacity/events/declared contract"
        )
    raise NotImplementedError("Exact minute-native differentiated reduction bridge not certified")
