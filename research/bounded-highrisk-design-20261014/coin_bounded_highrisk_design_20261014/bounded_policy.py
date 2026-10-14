"""Synthetic policy prototype, not an exchange bot or historical runner.

Reservations are a planning layer. They never manufacture wallet cash, transfer
isolated margin, or write P&L. All financial updates use the pinned Decimal
account. Full-program margin is reserved before the first finite add.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal, localcontext
from typing import Mapping
import math
from copy import deepcopy
import hashlib
import json

from vendor_quant.perpetual_account import (
    PerpetualConfig, USDTLinearPerpetualAccount, decimal,
)

D = Decimal
ZERO = D("0")
SYMBOLS = ("BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT", "DOGEUSDT")
INITIAL_CASH = D("10000")


@dataclass(frozen=True)
class RiskStage:
    name: str = "H090_ISOLATED1X"
    gross_cap: Decimal = D("0.90")
    asset_cap: Decimal = D("0.30")
    absolute_net_cap: Decimal = D("0.90")
    annual_vol_target: Decimal = D("0.15")
    initial_committed_capital_cap: Decimal = D("9000")
    initial_cash_floor: Decimal = D("1000")
    leverage: Decimal = D("1")

    def __post_init__(self):
        expected = ("H090_ISOLATED1X", D(".90"), D(".30"), D(".90"),
                    D(".15"), D("9000"), D("1000"), D("1"))
        if tuple(vars(self).values()) != expected:
            raise ValueError("Only the fixed moderate H090 stage is admitted to toys")


STAGE = RiskStage()


class HighRiskToyAccount(USDTLinearPerpetualAccount):
    """One reviewed validation extension; the inherited finance is unchanged."""
    VERSION = "bounded_highrisk_synthetic_090_isolated1x_v1"

    def __init__(self, config=None, *, symbols=SYMBOLS,
                 closing_min_notional_exempt=True, **kwargs):
        config = config or PerpetualConfig(max_gross_weight=".90")
        if (config.initial_cash != INITIAL_CASH or config.max_gross_weight != STAGE.gross_cap
                or config.max_asset_weight != STAGE.asset_cap or config.leverage != 1
                or closing_min_notional_exempt is not True):
            raise ValueError("Fixed fresh 10k, .90/.30, isolated 1x, closing exemption")
        super().__init__(config, symbols=symbols,
                         closing_min_notional_exempt=True, **kwargs)

    def contract_metadata(self):
        result = super().contract_metadata()
        result.update(
            research_scope="SYNTHETIC_ONLY_NOT_HISTORICAL_GO",
            max_gross_weight=str(STAGE.gross_cap),
            max_asset_weight=str(STAGE.asset_cap),
            annual_vol_target="0.15_EXTERNAL_PAST_ONLY_CONTROLLER_NOT_ENFORCED_HERE",
            original_execution_contract_risk_fields="NOT_USED_AS_HIGHER_RISK_CERTIFICATION",
            initial_committed_capital_cap_USDT=str(STAGE.initial_committed_capital_cap),
            initial_cash_floor_USDT=str(STAGE.initial_cash_floor),
            capital_envelope="EXTERNAL_RESERVATION_POLICY_NOT_ENFORCED_BY_ACCOUNT",
            no_margin_topups=True,
            native_bot_replica=False,
        )
        return result


@dataclass(frozen=True)
class FiniteAddsPlan:
    """Multiplier acts on order margin, not base-asset quantity."""
    owner: str = "MART_FINITE_REPLACE10"
    symbol: str = "BTCUSDT"
    direction: int = 1
    initial_order_margin: Decimal = D("150")
    margin_multiplier: Decimal = D("1.25")
    maximum_adds: int = 3
    trigger_fraction: Decimal = D(".05")
    total_sleeve_investment: Decimal = D("1000")
    loss_limit_fraction: Decimal = D(".20")

    def __post_init__(self):
        if (self.owner != "MART_FINITE_REPLACE10" or self.symbol != "BTCUSDT"
                or type(self.direction) is not int or self.direction != 1 or type(self.maximum_adds) is not int
                or self.maximum_adds != 3):
            raise ValueError("Only the fixed long BTC candidate with exactly three maximum adds")
        for key in ("initial_order_margin", "margin_multiplier", "trigger_fraction",
                    "total_sleeve_investment", "loss_limit_fraction"):
            object.__setattr__(self, key, decimal(getattr(self, key)))
        if (self.initial_order_margin != D("150") or self.margin_multiplier != D("1.25")
                or self.trigger_fraction != D(".05")
                or self.loss_limit_fraction != D(".20")
                or self.total_sleeve_investment != D("1000")
                or self.margin_total() >= self.total_sleeve_investment):
            raise ValueError("Bounded declared margin and positive cost/funding reserve required")

    def margins(self):
        return tuple(self.initial_order_margin * self.margin_multiplier ** i
                     for i in range(self.maximum_adds + 1))

    def margin_total(self):
        return sum(self.margins(), ZERO)

    def cost_funding_reserve(self):
        return self.total_sleeve_investment - self.margin_total()

    def trigger_price(self, quantity_weighted_fill_basis):
        basis = decimal(quantity_weighted_fill_basis)
        if basis <= 0:
            raise ValueError("Positive actual quantity-weighted fill basis required")
        return basis * (1 - self.direction * self.trigger_fraction)

    def loss_exit_due(self, total_sleeve_pnl):
        # This is an exit SIGNAL. Gaps, capacity and halts can overshoot it.
        return decimal(total_sleeve_pnl) <= -self.total_sleeve_investment * self.loss_limit_fraction


@dataclass
class ReservationBook:
    """No independently funded sleeves, top-ups, or capital reuse."""
    initial_cash: Decimal = INITIAL_CASH
    reservations: dict[str, Decimal] = field(default_factory=dict)
    released: set[str] = field(default_factory=set)
    retired_reservations: dict[str, Decimal] = field(default_factory=dict)

    def __post_init__(self):
        if (self.initial_cash != INITIAL_CASH or self.reservations or self.released
                or self.retired_reservations):
            raise ValueError("A fresh empty planning book for the original shared 10000 USDT is required")

    def reserve(self, owner: str, amount):
        amount = decimal(amount)
        if self.initial_cash != INITIAL_CASH or not owner or amount <= 0:
            raise ValueError("Fixed shared 10k planning book and positive owner budget")
        if owner in self.reservations or owner in self.released:
            raise ValueError("Owner reservation cannot be duplicated or automatically restarted")
        committed = sum(self.reservations.values(), ZERO) + sum(self.retired_reservations.values(), ZERO)
        if committed + amount > STAGE.initial_committed_capital_cap:
            raise ValueError("Shared initial committed capital cap exceeded")
        self.reservations[owner] = amount

    def release(self, owner: str, *, actual_quantity, pending_increase_count):
        if decimal(actual_quantity) != 0 or pending_increase_count != 0:
            raise ValueError("No release until flat and all increases are cancelled")
        if owner not in self.reservations:
            raise ValueError("Unknown owner")
        # This first prototype has one program per capital allocation. Retired
        # capital cannot be renamed into a fresh allocation or hidden top-up.
        self.retired_reservations[owner] = self.reservations.pop(owner)
        self.released.add(owner)

    def available_initial_capital(self):
        return (self.initial_cash - sum(self.reservations.values(), ZERO)
                - sum(self.retired_reservations.values(), ZERO))


@dataclass
class FiniteAddsState:
    plan: FiniteAddsPlan = field(default_factory=FiniteAddsPlan)
    completed_opening_orders: int = 0
    terminal: bool = False
    current_order_filled_margin: Decimal = ZERO
    processed_fill_receipts: dict[str, tuple[int, str]] = field(default_factory=dict)

    def __post_init__(self):
        if (self.completed_opening_orders != 0 or self.terminal
                or self.current_order_filled_margin != ZERO or self.processed_fill_receipts):
            raise ValueError("Fresh finite-program state must advance only through actual receipts")

    def next_order_margin(self):
        if self.terminal or self.completed_opening_orders >= len(self.plan.margins()):
            return None
        return self.plan.margins()[self.completed_opening_orders]

    def record_complete_opening_order(self, signed_quantity, actual_filled_margin,
                                      *, quantization_remainder=0, maximum_remainder=0):
        """Caller-supplied completion totals are deliberately unsupported."""
        raise ValueError("Use actual account-bound fill receipts; caller totals cannot advance an add")

    def record_fill_receipt(self, account, fill_id: str, order_index: int):
        """Bind one order's partials to actual immutable-identity account receipts.

        A small requested fill marked FILLED is still a partial MARGIN program
        order. Only its accumulated actual margin within one native quantity
        tick of the fixed order budget advances the add count. The bound comes
        from the account's actual fill price and pinned 1e-8 filter, never the
        caller. Replays are idempotent and cannot migrate to another add.
        """
        if (not isinstance(account, USDTLinearPerpetualAccount) or not isinstance(fill_id, str)
                or not fill_id or type(order_index) is not int or fill_id not in account.fill_requests):
            raise ValueError("Actual account and known fill receipt identity required")
        request = account.fill_requests[fill_id]
        digest = hashlib.sha256(json.dumps(request, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        identity = (order_index, digest)
        if fill_id in self.processed_fill_receipts:
            if self.processed_fill_receipts[fill_id] != identity:
                raise ValueError("Fill receipt replay changed identity or order ownership")
            return self.next_order_margin()
        expected = self.next_order_margin()
        if expected is None or order_index != self.completed_opening_orders:
            raise ValueError("Finite order limit, terminal lock or incorrect current add index")
        rows = request["receipt"]["fills"]
        journal_rows = [row for row in account.trades if row["fill_id"] == fill_id]
        if (not rows or rows != journal_rows
                or any(row["symbol"] != self.plan.symbol or row["side"] != "BUY"
                       or row["leg"] != "OPEN" for row in rows)
                or account.config.leverage != 1
                or account.instrument_profiles[self.plan.symbol].quantity_step != D(".00000001")):
            raise ValueError("Known long-BTC opening margin receipts and pinned quantity profile required")
        with localcontext() as ctx:
            ctx.prec = 40
            delta = sum((D(row["decimal_strings"]["margin_allocated"]) for row in rows), ZERO)
            total = self.current_order_filled_margin + delta
            if delta <= 0 or total > expected:
                raise ValueError("Actual margin must be positive and cannot exceed the fixed order budget")
            last_fill = D(rows[-1]["decimal_strings"]["fill_price"])
            one_tick = account.instrument_profiles[self.plan.symbol].quantity_step * last_fill
            remainder = expected - total
            self.processed_fill_receipts[fill_id] = identity
            self.current_order_filled_margin = total
            if remainder < one_tick:
                self.completed_opening_orders += 1
                self.current_order_filled_margin = ZERO
        return self.next_order_margin()

    def begin_terminal(self):
        self.terminal = True


@dataclass
class ProgramBudget:
    """One pre-reserved fee/funding buffer, deduplicated actual receipt events.

    Funding credits/profits do not restart rounds or replenish reserved spending.
    A debit above the buffer is retained and disables increases. The original
    wallet already debited it; this planner neither rolls it back nor rescues it.
    Fill-price friction is already included in order margin, not debited twice.
    """
    plan: FiniteAddsPlan = field(default_factory=FiniteAddsPlan)
    consumed_fee_funding_reserve: Decimal = ZERO
    cost_events: dict[str, tuple[Decimal, Decimal]] = field(default_factory=dict)

    def record_cost_event(self, event_id: str, *, actual_fee=0, signed_funding=0):
        fee, funding = decimal(actual_fee), decimal(signed_funding)
        if not event_id or fee < 0:
            raise ValueError("Unique actual receipt ID and nonnegative fee required")
        identity = (fee, funding)
        if event_id in self.cost_events:
            if self.cost_events[event_id] != identity:
                raise ValueError("Conflicting duplicate fee/funding event")
            return self.allow_further_increases()
        self.cost_events[event_id] = identity
        self.consumed_fee_funding_reserve += fee + max(-funding, ZERO)
        return self.allow_further_increases()

    def allow_further_increases(self):
        return self.consumed_fee_funding_reserve < self.plan.cost_funding_reserve()


class CapitalGuard:
    """Exact original-engine dry run, then commit only the identical valid fill.

    This planning gate adds no financial formula. Original reduce-only fills
    are never denied by the capital floor. Funding/losses may cross the floor;
    this disables increases rather than pretending cash is rescued.
    """
    maximum_actual_isolated_margin = D("8500")

    def __init__(self, account):
        self.account = account

    def execute_fill(self, *args, **kwargs):
        fill_id = args[5] if len(args) > 5 else kwargs.get("fill_id")
        if fill_id in self.account.fill_requests:
            # Original identity validation and duplicate replay must precede
            # current planning guards; no new fill occurs in the replay.
            return self.account.execute_fill(*args, **kwargs)
        if kwargs.get("reduce_only") is not True:
            if self.account.free_cash < STAGE.initial_cash_floor:
                return {"status": "POLICY_REJECTED", "reason": "INITIAL_CASH_FLOOR_BREACHED"}
            # The original scheduler fork shares this immutable profile map.
            probe = deepcopy(self.account, {id(self.account.instrument_profiles):
                                            self.account.instrument_profiles})
            preview = probe.execute_fill(*args, **kwargs)
            margin = sum((p.isolated_balance for p in probe.positions.values()), ZERO)
            if probe.free_cash < STAGE.initial_cash_floor or margin > self.maximum_actual_isolated_margin:
                return {"status": "POLICY_REJECTED", "reason": "SHARED_CAPITAL_OR_RESERVE_CAP"}
            receipt = self.account.execute_fill(*args, **kwargs)
            if receipt != preview or self.account.snapshot() != probe.snapshot():
                raise AssertionError("Exact unchanged-account dry run and commit differ")
            return receipt
        return self.account.execute_fill(*args, **kwargs)


def validate_intent_envelope(sleeve_notionals: Mapping[str, Mapping[str, Decimal]], nav,
                             *, actual_signed_notionals, pending_increases):
    """Conservative gross before netting prevents hidden opposing sleeve risk.

    Mark drift is observed, never clipped away. A breach disables increases and
    requires an execution-limited reduction; it does not guarantee a cap.
    """
    nav = decimal(nav)
    if nav <= 0:
        return {"allow_increases": False, "reason": "NONPOSITIVE_EQUITY"}
    if any(set(legs) - set(SYMBOLS) for legs in sleeve_notionals.values()):
        raise ValueError("Known CORE5 sleeve notionals only")
    asset_gross = dict.fromkeys(SYMBOLS, ZERO)
    net = ZERO
    for legs in sleeve_notionals.values():
        for symbol, value in legs.items():
            value = decimal(value)
            asset_gross[symbol] += abs(value)
            net += value
    gross = sum(asset_gross.values(), ZERO)
    actual = actual_signed_notionals
    if not isinstance(actual, Mapping) or set(actual) != set(SYMBOLS):
        raise ValueError("Complete actual signed CORE5 notionals required")
    actual = {s: decimal(v) for s, v in actual.items()}
    if (not isinstance(pending_increases, Mapping)
            or any(not isinstance(legs, Mapping) or set(legs) - set(SYMBOLS)
                   for legs in pending_increases.values())):
        raise ValueError("Pending increases need owner and per-symbol signed notional")
    pending_asset = dict.fromkeys(SYMBOLS, ZERO)
    for legs in pending_increases.values():
        for s, v in legs.items():
            pending_asset[s] += abs(decimal(v))
    risk_assets = {s: max(asset_gross[s], abs(actual[s])) + pending_asset[s] for s in SYMBOLS}
    risk_gross = sum(risk_assets.values(), ZERO)
    net_risk = max(abs(net), abs(sum(actual.values(), ZERO))) + sum(pending_asset.values(), ZERO)
    reasons = []
    if risk_gross > nav * STAGE.gross_cap:
        reasons.append("GROSS_OR_PENDING_CAP")
    if any(value > nav * STAGE.asset_cap for value in risk_assets.values()):
        reasons.append("CONSERVATIVE_ASSET_CAP")
    if net_risk > nav * STAGE.absolute_net_cap:
        reasons.append("NET_CAP")
    return dict(allow_increases=not reasons, reasons=reasons,
                conservative_gross=str(gross), risk_gross_including_pending=str(risk_gross),
                net_notional=str(net), asset_gross={s: str(v) for s, v in asset_gross.items()},
                actual_net_notional=str(sum(actual.values(), ZERO)),
                conservative_net_including_pending=str(net_risk),
                risk_assets_including_pending={s: str(v) for s, v in risk_assets.items()},
                requires_reduce_only=bool(reasons), cap_guaranteed_after_mark=False)


def bounded_weights(raw, past_returns, *, gross_cap=.90, vol_target=.15):
    """Separate pure intent controller; unchanged 30-day sample covariance rule.

    Time-stamp availability must be certified by the eventual source adapter.
    Here inputs are generated arrays only. This is not a selector or alpha model.
    """
    import numpy as np
    w = np.asarray(raw, dtype=np.float64).copy()
    r = np.asarray(past_returns, dtype=np.float64)
    if (w.shape != (len(SYMBOLS),) or not np.isfinite(w).all()
            or r.ndim != 2 or r.shape[1] != len(SYMBOLS) or r.shape[0] < 30
            or not np.isfinite(r).all() or (gross_cap, vol_target) not in ((.60, .10), (.90, .15))):
        raise ValueError("Fixed baseline/high-risk stages and 30 complete past observations")
    w = np.clip(w, -.30, .30)
    gross = float(np.abs(w).sum())
    if gross > gross_cap:
        w *= gross_cap / gross
    covariance = np.atleast_2d(np.cov(r[-30:], rowvar=False, ddof=1)) * 365
    variance = float(w @ covariance @ w)
    if not math.isfinite(variance) or variance < -1e-15:
        raise ValueError("Finite nonnegative covariance risk required")
    sigma = float(np.sqrt(max(variance, 0.)))
    if sigma > vol_target:
        w *= vol_target / sigma
    return w, dict(pre_vol_scaling_annual_vol=sigma,
                   gross_target_weight=float(np.abs(w).sum()),
                   net_target_weight=float(w.sum()),
                   past_observations=30, historical_availability_certified=False)


def matched_csh_h090_intents(original_csh_weights, past_returns):
    """Fixed 1.5x original CSH target proposal, then H090 concentration/vol caps.

    The cap may bind after scaling, so this does not assert 1.5x realized risk.
    No CSH signal is refitted or selected; its source needs later certification.
    """
    import numpy as np
    original = np.asarray(original_csh_weights, dtype=np.float64)
    if (original.shape != (len(SYMBOLS),) or not np.isfinite(original).all()
            or np.abs(original).max() > .30 + 1e-12 or np.abs(original).sum() > .60 + 1e-12):
        raise ValueError("Original canonical CSH target envelope required")
    weights, meta = bounded_weights(1.5 * original, past_returns)
    meta.update(control_id="CSH_H090_CONTROL", original_strategy_parameters_unchanged=True,
                original_weight_multiplier=1.5, realized_risk_matching_certified=False)
    return weights, meta
