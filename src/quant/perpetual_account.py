"""Conditional USDT linear perpetual accounting; no exchange or order transport.

Configured one-way, isolated, 1x perpetuals share one free USDT wallet. Marks value
inventory; a separately supplied trade midpoint prices fills. MMR, quantity
step, liquidity and fees are declared research assumptions, not native filters.
Only the frozen ExecutionContractV2 clock and cost arithmetic are reused.
"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, fields
from decimal import Decimal, ROUND_DOWN, localcontext
from types import MappingProxyType
from typing import Any, Mapping

from .execution_contract import ExecutionContractV2

D = Decimal
ZERO = D("0")
SYMBOLS = ("BTCUSDT", "ETHUSDT")
VERSION = "usdt_linear_perpetual_account_v2"
HALTS = {"BANKRUPT_HALT", "LIQUIDATION_REQUIRED_HALT"}


def decimal(value: Any) -> Decimal:
    if isinstance(value, bool) or not isinstance(value, (str, int, float, Decimal)):
        raise ValueError("finite numeric value required")
    result = D(str(value))
    if not result.is_finite():
        raise ValueError("finite numeric value required")
    return result


def timestamp(value: Any) -> int:
    if type(value) is not int or value < 0:
        raise ValueError("timestamp must be a nonnegative integer microsecond")
    return value


def _numbers(value: Any) -> Any:
    """Receipts use ordinary JSON numbers; snapshots retain exact decimals."""
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, dict):
        result = {key: _numbers(item) for key, item in value.items()}
        exact = {key: str(item) for key, item in value.items() if isinstance(item, Decimal)}
        if exact:
            result["decimal_strings"] = exact
        return result
    if isinstance(value, list):
        return [_numbers(item) for item in value]
    return value


@dataclass(frozen=True)
class PerpetualConfig:
    initial_cash: Decimal = D("10000")
    fee_rate: Decimal = D("0.00055")
    half_spread_bps: Decimal = D("4")
    slippage_bps: Decimal = D("4")
    leverage: Decimal = D("1")
    max_asset_weight: Decimal = D("0.3")
    max_gross_weight: Decimal = D("0.6")
    maintenance_margin_rate: Decimal = D("0.005")
    min_notional: Decimal = D("10")
    quantity_step: Decimal = D("0.00000001")

    def __post_init__(self) -> None:
        for field in fields(self):
            object.__setattr__(self, field.name, decimal(getattr(self, field.name)))
        if (self.initial_cash <= 0 or self.fee_rate != D("0.00055")
                or self.half_spread_bps < 4 or self.slippage_bps < 4
                or self.leverage != 1 or not 0 < self.max_asset_weight <= D("0.3")
                or not 0 < self.max_gross_weight <= D("0.6")
                or self.maintenance_margin_rate != D("0.005")
                or self.min_notional != 10 or self.quantity_step != D("0.00000001")):
            raise ValueError("unsupported or less conservative perpetual scenario")


@dataclass(frozen=True)
class InstrumentProfile:
    """Declared research filters; no native or historical certification."""
    quantity_step: Decimal = D("0.00000001")
    min_notional: Decimal = D("10")
    quantity_asset: str = "BASE"
    contract_multiplier: Decimal = D("1")
    settlement_asset: str = "USDT"
    market_type: str = "LINEAR_USDT_PERPETUAL"
    quantity_profile_status: str = "UNCERTIFIED_PROXY_NOT_API_PROFILE"
    native_filters_certified: bool = False

    def __post_init__(self) -> None:
        for key in ("quantity_step", "min_notional", "contract_multiplier"):
            object.__setattr__(self, key, decimal(getattr(self, key)))
        if (self.quantity_step <= 0 or self.min_notional <= 0
                or self.quantity_asset != "BASE" or self.contract_multiplier != 1
                or self.settlement_asset != "USDT" or self.market_type != "LINEAR_USDT_PERPETUAL"
                or self.quantity_profile_status != "UNCERTIFIED_PROXY_NOT_API_PROFILE"
                or self.native_filters_certified is not False):
            raise ValueError("unsupported instrument product or uncertified filter profile")

    def metadata(self) -> dict[str, Any]:
        return {field.name: (str(getattr(self, field.name))
                if isinstance(getattr(self, field.name), Decimal) else getattr(self, field.name))
                for field in fields(self)}


def _symbols(value: Any) -> tuple[str, ...]:
    if not isinstance(value, (tuple, list)) or not value:
        raise ValueError("symbols must be a nonempty ordered tuple or list")
    result = tuple(value)
    if (any(type(symbol) is not str or not symbol.isascii() or not symbol.isalnum()
            or symbol != symbol.upper() or not symbol.endswith("USDT") or len(symbol) <= 4
            for symbol in result) or len(result) != len(set(result))):
        raise ValueError("symbols must be unique uppercase USDT instrument identities")
    return result


def _profiles(symbols: tuple[str, ...], value: Any,
              config: PerpetualConfig) -> Mapping[str, InstrumentProfile]:
    if value is None:
        value = {symbol: InstrumentProfile(quantity_step=config.quantity_step,
                                          min_notional=config.min_notional) for symbol in symbols}
    if not isinstance(value, Mapping) or set(value) != set(symbols):
        raise ValueError("instrument profile keys must exactly match configured symbols")
    result = {}
    for symbol in symbols:
        profile = value[symbol]
        if isinstance(profile, Mapping):
            try:
                profile = InstrumentProfile(**dict(profile))
            except TypeError as error:
                raise ValueError("invalid instrument profile fields") from error
        if not isinstance(profile, InstrumentProfile):
            raise ValueError("an InstrumentProfile or profile mapping is required")
        result[symbol] = profile
    return MappingProxyType(result)


@dataclass
class Position:
    quantity: Decimal = ZERO
    entry_price: Decimal = ZERO
    isolated_balance: Decimal = ZERO
    opened_us: int | None = None


class USDTLinearPerpetualAccount:
    """Fill-driven account. Call funding at t before any fill at t+1us.

    Reductions release the same fraction of the *remaining actual* isolated
    balance. Loss/fee debits consume free wallet, then that position's isolated
    balance; another position's collateral never rescues it. An unpaid debit is
    an explicit liability and a permanent bankruptcy halt. No margin top-up,
    liquidation fill, insurance payment or credit is invented.
    """
    VERSION = VERSION

    def __init__(self, config: PerpetualConfig | None = None, *,
                 symbols: tuple[str, ...] = SYMBOLS,
                 instrument_profiles: Mapping[str, InstrumentProfile | Mapping[str, Any]] | None = None,
                 closing_min_notional_exempt: bool = False,
                 market_type: str = "LINEAR_USDT_PERPETUAL",
                 external_gross_notional: Any = 0) -> None:
        if market_type != "LINEAR_USDT_PERPETUAL" or decimal(external_gross_notional) != 0:
            raise ValueError("mixed Spot/perpetual or external capital is unsupported")
        if config is not None and not isinstance(config, PerpetualConfig):
            raise ValueError("PerpetualConfig required")
        if type(closing_min_notional_exempt) is not bool:
            raise ValueError("closing minimum-notional policy must be an explicit bool")
        self.config = config or PerpetualConfig()
        self._symbols = _symbols(symbols)
        self.instrument_profiles = _profiles(self.symbols, instrument_profiles, self.config)
        self.closing_min_notional_exempt = closing_min_notional_exempt
        self.free_cash = self.config.initial_cash
        self.unpaid_liability = ZERO
        self.positions = {symbol: Position() for symbol in self.symbols}
        self.marks: dict[str, list[dict[str, Any]]] = {symbol: [] for symbol in self.symbols}
        self.clock_us = 0
        self.last_fill_us: int | None = None
        self.status = "ACTIVE"
        self.halt_witness: dict[str, Any] | None = None
        self.trades: list[dict[str, Any]] = []
        self.funding: list[dict[str, Any]] = []
        self.fill_requests: dict[str, dict[str, Any]] = {}
        self.funding_events: dict[str, dict[str, Any]] = {}
        self.funding_ids: dict[str, str] = {}
        self.fees = self.execution_cost = self.funding_cash = self.realized_PnL = ZERO
        self.gross_fill_turnover = ZERO

    @property
    def symbols(self) -> tuple[str, ...]:
        return self._symbols

    def contract_metadata(self) -> dict[str, Any]:
        steps = {profile.quantity_step for profile in self.instrument_profiles.values()}
        minimums = {profile.min_notional for profile in self.instrument_profiles.values()}
        return {
            "version": self.VERSION, "target_exchange": "Bybit", "market_type": "LINEAR_USDT_PERPETUAL",
            "symbols": list(self.symbols), "symbol_order_is_account_identity": True,
            "instrument_profiles": {symbol: self.instrument_profiles[symbol].metadata() for symbol in self.symbols},
            "settlement_asset": "USDT", "quantity_asset": "BASE", "contract_multiplier": 1,
            "position_mode": "ONE_WAY", "margin_mode": "ISOLATED", "leverage": 1,
            "fee_asset": "USDT", "taker_fee_bps_per_side": 5.5,
            "nominal_roundtrip_bps": 27, "mmr_assumption": "0.005_NOT_NATIVE_RISK_TIER",
            "quantity_step_assumption": str(next(iter(steps))) if len(steps) == 1 else "PER_INSTRUMENT_PROFILE",
            "min_notional_assumption_USDT": float(next(iter(minimums))) if len(minimums) == 1 else "PER_INSTRUMENT_PROFILE",
            "closing_min_notional_exempt": self.closing_min_notional_exempt,
            "min_notional_scope": "OPENING_LEGS_ONLY" if self.closing_min_notional_exempt else "OPENING_AND_CLOSING_REQUESTS",
            "quantity_profile_status": "UNCERTIFIED_PROXY_NOT_API_PROFILE",
            "historical_filters_certified": False,
            "execution_clock_source": "ExecutionContractV2.earliest_execution_us_PLUS_1US_ONLY",
            "annual_vol_target": "0.10_EXTERNAL_SIGNED_COVARIANCE_CONTROLLER_NOT_ENFORCED_HERE",
            "native_filters_certified": False, "native_liquidation_certified": False,
            "funding_publication_certified": False, "mixed_product_supported": False,
        }

    def _symbol(self, symbol: str) -> None:
        if symbol not in self.symbols:
            raise ValueError("symbol is not configured in this perpetual account")

    def _clock(self, event_us: int) -> None:
        if timestamp(event_us) < self.clock_us:
            raise ValueError("events must be chronological")
        if self.status in HALTS:
            raise RuntimeError(self.status)

    def _mark(self, symbol: str, *, strictly_before: int | None = None) -> Decimal:
        candidates = self.marks[symbol]
        if strictly_before is not None:
            candidates = [row for row in candidates if row["close_us"] < strictly_before
                          and row["available_us"] <= strictly_before]
        if not candidates:
            raise ValueError("no causally available mark")
        return candidates[-1]["price"]

    def nav(self) -> Decimal:
        with localcontext() as ctx:
            ctx.prec = 40
            result = self.free_cash - self.unpaid_liability
            for symbol, position in self.positions.items():
                result += position.isolated_balance
                if position.quantity:
                    result += position.quantity * (self._mark(symbol) - position.entry_price)
            return +result

    def _risk(self, phase: str) -> None:
        if self.status in HALTS:
            return
        nav = self.nav()
        for symbol, position in self.positions.items():
            if not position.quantity:
                continue
            mark = self._mark(symbol)
            equity = position.isolated_balance + position.quantity * (mark - position.entry_price)
            maintenance = abs(position.quantity) * mark * self.config.maintenance_margin_rate
            if equity <= maintenance or nav <= 0 or self.unpaid_liability:
                self.status = ("BANKRUPT_HALT" if equity <= 0 or nav <= 0 or self.unpaid_liability
                               else "LIQUIDATION_REQUIRED_HALT")
                self.halt_witness = _numbers({"event_us": self.clock_us, "phase": phase,
                    "symbol": symbol, "isolated_equity": equity, "maintenance_margin": maintenance,
                    "mark_price": mark, "quantity": position.quantity, "NAV": nav,
                    "unpaid_liability": self.unpaid_liability})
                return
        if nav <= 0 or self.unpaid_liability:
            self.status = "BANKRUPT_HALT"
            self.halt_witness = _numbers({"event_us": self.clock_us, "phase": phase,
                                         "NAV": nav, "unpaid_liability": self.unpaid_liability})
            return
        notionals = [abs(pos.quantity) * self._mark(sym) if pos.quantity else ZERO
                     for sym, pos in self.positions.items()]
        breached = (any(value > self.config.max_asset_weight * nav for value in notionals)
                    or sum(notionals, ZERO) > self.config.max_gross_weight * nav)
        self.status = "BOUND_BREACH_REDUCTION_REQUIRED" if breached else "ACTIVE"

    def update_marks(self, observation_us: int, marks: Mapping[str, Mapping[str, Any]]) -> dict[str, Any]:
        self._clock(observation_us)
        parsed = {}
        if not isinstance(marks, Mapping) or not marks:
            raise ValueError("nonempty mark mapping required")
        for symbol, row in marks.items():
            self._symbol(symbol)
            if set(row) != {"price", "close_us", "available_us"}:
                raise ValueError("mark schema must be price/close_us/available_us")
            price = decimal(row["price"])
            close, available = timestamp(row["close_us"]), timestamp(row["available_us"])
            if price <= 0 or close > available or available > observation_us:
                raise ValueError("mark price or availability is invalid")
            item = {"price": price, "close_us": close, "available_us": available}
            previous = self.marks[symbol]
            if previous and (close < previous[-1]["close_us"]
                             or close == previous[-1]["close_us"] and item != previous[-1]):
                raise ValueError("old or conflicting mark")
            parsed[symbol] = item
        self.clock_us = observation_us
        for symbol, item in parsed.items():
            if not self.marks[symbol] or self.marks[symbol][-1] != item:
                self.marks[symbol] = (self.marks[symbol] + [item])[-2:]
        with localcontext() as ctx:
            ctx.prec = 40
            self._risk("MARK_OBSERVATION")
        return self.summary()

    def _debit(self, symbol: str, amount: Decimal) -> None:
        self._symbol(symbol)
        amount = decimal(amount)
        if any(decimal(value) < 0 for value in
               (amount, self.free_cash, self.positions[symbol].isolated_balance, self.unpaid_liability)):
            raise ValueError("debit requires nonnegative amount, wallet, isolated balance and liability")
        free = min(self.free_cash, amount)
        self.free_cash -= free
        remaining = amount - free
        if remaining > 0:
            own = min(self.positions[symbol].isolated_balance, remaining)
            self.positions[symbol].isolated_balance -= own
            self.unpaid_liability += remaining - own

    def _floor(self, symbol: str, quantity: Decimal) -> Decimal:
        self._symbol(symbol)
        step = self.instrument_profiles[symbol].quantity_step
        return (quantity / step).to_integral_value(rounding=ROUND_DOWN) * step

    def _leg(self, symbol: str, side: str, quantity: Decimal, mid: Decimal, fill: Decimal,
             event_us: int, signal_us: int, fill_id: str, leg: str) -> dict[str, Any] | str:
        position = self.positions[symbol]
        direction = D(1) if side == "BUY" else D(-1)
        delta = direction * quantity
        opening = not position.quantity or position.quantity * delta > 0
        fee = quantity * fill * self.config.fee_rate
        before_cash, before_margin = self.free_cash, position.isolated_balance
        before_q, before_basis = position.quantity, position.entry_price
        released = allocated = realized = ZERO
        if opening:
            allocated = quantity * fill / self.config.leverage
            if self.free_cash < allocated + fee:
                return "INSUFFICIENT_FREE_MARGIN"
            candidate_q = position.quantity + delta
            basis = ((abs(position.quantity) * position.entry_price + quantity * fill)
                     / abs(candidate_q))
            post_nav = self.nav() + delta * (self._mark(symbol) - fill) - fee
            notionals = {sym: abs(pos.quantity) * self._mark(sym) if pos.quantity else ZERO
                         for sym, pos in self.positions.items()}
            notionals[symbol] = abs(candidate_q) * self._mark(symbol)
            if (post_nav <= 0 or any(value > self.config.max_asset_weight * post_nav for value in notionals.values())
                    or sum(notionals.values(), ZERO) > self.config.max_gross_weight * post_nav):
                return "POST_FILL_EXPOSURE_CAP_REJECTED"
            self.free_cash -= allocated + fee
            position.isolated_balance += allocated
            position.entry_price = basis
            position.quantity = candidate_q
            if not before_q:
                position.opened_us = event_us
        else:
            if quantity > abs(position.quantity):
                raise AssertionError("closing leg crosses zero")
            # Full-close identity must not multiply/divide through two rounded
            # intermediates: that can release one ulp MORE than actual balance.
            released = (position.isolated_balance if quantity == abs(position.quantity)
                        else position.isolated_balance * quantity / abs(position.quantity))
            realized = (D(1) if position.quantity > 0 else D(-1)) * quantity * (fill - position.entry_price)
            position.isolated_balance -= released
            self.free_cash += released
            position.quantity += delta
            if realized >= 0:
                self.free_cash += realized
            else:
                self._debit(symbol, -realized)
            self._debit(symbol, fee)
            if not position.quantity:
                # Exact Decimal zero only: no lot rounding or dust forgiveness.
                self.free_cash += position.isolated_balance
                position.isolated_balance = position.entry_price = ZERO
                position.opened_us = None
        cost = quantity * abs(fill - mid)
        self.fees += fee
        self.execution_cost += cost
        self.realized_PnL += realized
        self.gross_fill_turnover += quantity * fill
        self.last_fill_us = event_us
        row = _numbers({"symbol": symbol, "side": side, "leg": leg, "fill_id": fill_id,
            "event_us": event_us, "signal_us": signal_us, "quantity": quantity,
            "gross_quantity": quantity, "position_delta": delta, "execution_mid_price": mid,
            "mid_price": mid, "fill_price": fill, "mark_price": self._mark(symbol),
            "fee_asset": "USDT", "fee_amount": fee, "fee_USDT_mid": fee,
            "execution_cost": cost, "realized_PnL": realized, "cash_delta": realized - fee,
            "free_cash_delta": self.free_cash - before_cash,
            "isolated_balance_delta": position.isolated_balance - before_margin,
            "margin_allocated": allocated, "margin_released": released,
            "quantity_before": before_q, "quantity_after": position.quantity,
            "entry_price_before": before_basis, "entry_price_after": position.entry_price})
        self.trades.append(row)
        self._risk("AFTER_" + leg)
        return row

    def execute_fill(self, symbol: str, side: str, quantity: Any, event_us: int,
                     signal_us: int, fill_id: str, *, execution_mid_price: Any,
                     quote_available_us: int, available_quantity: Any | None = None,
                     reduce_only: bool = False) -> dict[str, Any]:
        self._symbol(symbol)
        signal_us, event_us = timestamp(signal_us), timestamp(event_us)
        quote_available_us = timestamp(quote_available_us)
        if not isinstance(fill_id, str) or not fill_id or side not in {"BUY", "SELL"} or type(reduce_only) is not bool:
            raise ValueError("invalid fill identity/side/reduce_only")
        requested, mid = decimal(quantity), decimal(execution_mid_price)
        available = requested if available_quantity is None else decimal(available_quantity)
        if requested <= 0 or mid <= 0 or available < 0:
            raise ValueError("invalid quantity or execution midpoint")
        identity = {"symbol": symbol, "side": side, "quantity": str(requested), "event_us": event_us,
                    "signal_us": signal_us, "execution_mid_price": str(mid), "available_quantity": str(available),
                    "quote_available_us": quote_available_us, "reduce_only": reduce_only}
        if fill_id in self.fill_requests:
            saved = self.fill_requests[fill_id]
            if saved["identity"] != identity:
                raise ValueError("conflicting fill identity")
            return deepcopy(saved["receipt"])
        self._clock(event_us)
        earliest = ExecutionContractV2().earliest_execution_us(signal_us) + 1
        if event_us < earliest or quote_available_us > event_us:
            raise ValueError("fill precedes execution latency or quote availability")
        self._mark(symbol)
        with localcontext() as ctx:
            ctx.prec = 40
            self._risk("BEFORE_FILL")
            if self.status in HALTS:
                raise RuntimeError(self.status)
            began_breached = self.status == "BOUND_BREACH_REDUCTION_REQUIRED"
            self.clock_us = event_us
            executable = self._floor(symbol, min(requested, available))
            position = self.positions[symbol]
            direction = D(1) if side == "BUY" else D(-1)
            reducing = bool(position.quantity and position.quantity * direction < 0)
            reason = None
            if reduce_only:
                if not reducing:
                    executable, reason = ZERO, "REDUCE_ONLY_NO_OPPOSITE_POSITION"
                else:
                    executable = min(executable, abs(position.quantity))
            rate = decimal(ExecutionContractV2.execution_rate(float(self.config.half_spread_bps),
                                                            float(self.config.slippage_bps)))
            fill = mid * (1 + direction * rate)
            minimum = self.instrument_profiles[symbol].min_notional
            if executable == ZERO or (executable * fill < minimum
                    and not (reducing and self.closing_min_notional_exempt)):
                executable, reason = ZERO, reason or "BELOW_MIN_NOTIONAL_OR_CAPACITY"
            closing = min(executable, abs(position.quantity)) if reducing else ZERO
            opening = executable - closing
            receipts = []
            if closing:
                result = self._leg(symbol, side, closing, mid, fill, event_us, signal_us, fill_id, "CLOSE")
                receipts.append(result)
            if opening and self.status not in HALTS:
                if opening * fill < minimum:
                    reason = "OPENING_LEG_BELOW_MIN_NOTIONAL"
                elif began_breached:
                    reason = "BOUND_BREACH_REDUCTION_REQUIRED"
                else:
                    result = self._leg(symbol, side, opening, mid, fill, event_us, signal_us, fill_id, "OPEN")
                    if isinstance(result, str):
                        reason = result
                    else:
                        receipts.append(result)
            elif opening:
                reason = self.status
            executed = sum((decimal(row["decimal_strings"]["quantity"]) for row in receipts), ZERO)
            receipt = _numbers({"fill_id": fill_id, "requested_quantity": requested,
                "executed_quantity": executed, "remaining_quantity": requested - executed,
                "status": "FILLED" if executed == requested else "PARTIAL" if executed else "REJECTED",
                "reason": reason, "account_status": self.status, "fills": receipts})
            self.fill_requests[fill_id] = {"identity": identity, "receipt": deepcopy(receipt)}
            return receipt

    def apply_funding(self, symbol: str, event_id: str, event_us: int, rate: Any,
                      rate_available_us: int) -> dict[str, Any]:
        self._symbol(symbol)
        event_us, available = timestamp(event_us), timestamp(rate_available_us)
        rate = decimal(rate)
        if not isinstance(event_id, str) or not event_id or available > event_us:
            raise ValueError("funding identity or rate availability invalid")
        key = f"{symbol}:{event_us}"
        identity = {"event_id": event_id, "rate": str(rate), "rate_available_us": available}
        if key in self.funding_events:
            if self.funding_events[key]["identity"] != identity:
                raise ValueError("conflicting duplicate funding event")
            return deepcopy(self.funding_events[key]["receipt"])
        if event_id in self.funding_ids:
            raise ValueError("funding event id reused at another time or symbol")
        self._clock(event_us)
        if self.last_fill_us is not None and event_us <= self.last_fill_us:
            raise ValueError("funding must precede same-timestamp fills")
        mark = self._mark(symbol, strictly_before=event_us)
        position = self.positions[symbol]
        owned = bool(position.quantity and position.opened_us is not None and position.opened_us < event_us)
        with localcontext() as ctx:
            ctx.prec = 40
            amount = -position.quantity * mark * rate if owned else ZERO
            self.clock_us = event_us
            if amount >= 0:
                self.free_cash += amount
            else:
                self._debit(symbol, -amount)
            self.funding_cash += amount
            self._risk("AFTER_FUNDING")
            receipt = _numbers({"symbol": symbol, "event_id": event_id, "event_us": event_us,
                "rate_available_us": available, "rate_fraction": rate, "mark_price": mark,
                "mark_close_us": next(row["close_us"] for row in reversed(self.marks[symbol])
                                       if row["close_us"] < event_us and row["available_us"] <= event_us),
                "owned": owned, "quantity": position.quantity, "signed_funding_USDT": amount,
                "account_status": self.status, "unit_and_publication_scope": "CALLER_DECLARED_CONDITIONAL"})
            self.funding.append(receipt)
            self.funding_events[key] = {"identity": identity, "receipt": deepcopy(receipt)}
            self.funding_ids[event_id] = key
            return receipt

    def summary(self) -> dict[str, Any]:
        with localcontext() as ctx:
            ctx.prec = 40
            nav = self.nav()
            unrealized = sum((pos.quantity * (self._mark(sym) - pos.entry_price)
                              for sym, pos in self.positions.items() if pos.quantity), ZERO)
            signed = {sym: pos.quantity * self._mark(sym) if pos.quantity else ZERO
                      for sym, pos in self.positions.items()}
            gross = sum((abs(value) for value in signed.values()), ZERO)
            gross_mid = self.realized_PnL + unrealized + self.execution_cost
            net = nav - self.config.initial_cash
            bridge = net - (gross_mid - self.execution_cost - self.fees + self.funding_cash)
            return _numbers({"version": self.VERSION, "contract": self.contract_metadata(),
                "symbols": list(self.symbols),
                "account_status": self.status, "clock_us": self.clock_us, "NAV": nav,
                "free_cash": self.free_cash, "isolated_balance": sum((p.isolated_balance for p in self.positions.values()), ZERO),
                "unpaid_liability": self.unpaid_liability, "net_PnL": net,
                "gross_PnL_same_quantities": gross_mid, "realized_PnL": self.realized_PnL,
                "unrealized_PnL": unrealized, "fees_USDT": self.fees,
                "execution_cost_USDT": self.execution_cost, "funding_USDT": self.funding_cash,
                "gross_notional": gross, "net_signed_notional": sum(signed.values(), ZERO),
                "gross_weight": gross / nav if nav > 0 else None,
                "asset_weights": {sym: value / nav if nav > 0 else None for sym, value in signed.items()},
                "positions": {sym: {"quantity": pos.quantity, "entry_price": pos.entry_price,
                                     "isolated_balance": pos.isolated_balance, "opened_us": pos.opened_us}
                              for sym, pos in self.positions.items()},
                "accounting_bridge_error_USDT": bridge,
                "gross_fill_turnover_USDT": self.gross_fill_turnover,
                "configured_nominal_roundtrip_bps": 2 * (self.config.fee_rate * 10000
                    + self.config.half_spread_bps + self.config.slippage_bps),
                "trade_legs": len(self.trades), "funding_events": len(self.funding),
                "halt_witness": self.halt_witness, "candidate": "NO_QUALIFIED_CANDIDATE",
                "long_term_APR": "NOT_EVALUABLE"})

    def snapshot(self) -> dict[str, Any]:
        return {"version": self.VERSION, "contract": self.contract_metadata(),
            "symbols": list(self.symbols),
            "instrument_profiles": {symbol: self.instrument_profiles[symbol].metadata() for symbol in self.symbols},
            "closing_min_notional_exempt": self.closing_min_notional_exempt,
            "config": {field.name: str(getattr(self.config, field.name)) for field in fields(self.config)},
            "free_cash": str(self.free_cash), "unpaid_liability": str(self.unpaid_liability),
            "positions": {sym: {"quantity": str(pos.quantity), "entry_price": str(pos.entry_price),
                                 "isolated_balance": str(pos.isolated_balance), "opened_us": pos.opened_us}
                          for sym, pos in self.positions.items()},
            "marks": {sym: [{**row, "price": str(row["price"])} for row in rows] for sym, rows in self.marks.items()},
            "clock_us": self.clock_us, "last_fill_us": self.last_fill_us, "status": self.status,
            "halt_witness": deepcopy(self.halt_witness), "trades": deepcopy(self.trades),
            "funding": deepcopy(self.funding), "fill_requests": deepcopy(self.fill_requests),
            "funding_events": deepcopy(self.funding_events), "funding_ids": deepcopy(self.funding_ids),
            "totals": {key: str(getattr(self, key)) for key in
                       ("fees", "execution_cost", "funding_cash", "realized_PnL", "gross_fill_turnover")}}

    @classmethod
    def from_snapshot(cls, snapshot: Mapping[str, Any], *, expected_symbols=None,
                      expected_instrument_profiles=None) -> "USDTLinearPerpetualAccount":
        if snapshot.get("version") != cls.VERSION:
            raise ValueError("snapshot product/version mismatch")
        symbols = _symbols(snapshot["symbols"])
        config = PerpetualConfig(**snapshot["config"])
        profiles = snapshot["instrument_profiles"]
        if (not isinstance(profiles, Mapping) or set(profiles) != set(symbols)
                or any(not isinstance(profile, Mapping) or set(profile) != {field.name for field in fields(InstrumentProfile)}
                       for profile in profiles.values())):
            raise ValueError("snapshot instrument profile identity is incomplete")
        result = cls(config, symbols=symbols, instrument_profiles=profiles,
                     closing_min_notional_exempt=snapshot["closing_min_notional_exempt"])
        if snapshot.get("contract") != result.contract_metadata():
            raise ValueError("snapshot product/symbol/profile/closing identity mismatch")
        if expected_symbols is not None and _symbols(expected_symbols) != symbols:
            raise ValueError("snapshot configured symbol order mismatch")
        if expected_instrument_profiles is not None:
            expected = _profiles(symbols, expected_instrument_profiles, config)
            if any(expected[symbol] != result.instrument_profiles[symbol] for symbol in symbols):
                raise ValueError("snapshot configured instrument profile mismatch")
        if set(snapshot["positions"]) != set(symbols) or set(snapshot["marks"]) != set(symbols):
            raise ValueError("snapshot inventory must exactly match configured symbols")
        result.free_cash = decimal(snapshot["free_cash"])
        result.unpaid_liability = decimal(snapshot["unpaid_liability"])
        if result.free_cash < 0 or result.unpaid_liability < 0:
            raise ValueError("negative snapshot wallet/liability")
        result.clock_us = timestamp(snapshot["clock_us"])
        result.last_fill_us = snapshot["last_fill_us"]
        if result.last_fill_us is not None and timestamp(result.last_fill_us) > result.clock_us:
            raise ValueError("snapshot future fill")
        if snapshot["status"] not in {"ACTIVE", "BOUND_BREACH_REDUCTION_REQUIRED"} | HALTS:
            raise ValueError("unknown snapshot status")
        for sym in result.symbols:
            row = snapshot["positions"][sym]
            pos = Position(decimal(row["quantity"]), decimal(row["entry_price"]),
                           decimal(row["isolated_balance"]), row["opened_us"])
            if (pos.isolated_balance < 0 or pos.quantity and (pos.entry_price <= 0 or pos.opened_us is None)
                    or not pos.quantity and (pos.entry_price != 0 or pos.isolated_balance != 0 or pos.opened_us is not None)):
                raise ValueError("inconsistent snapshot position")
            if abs(pos.quantity) % result.instrument_profiles[sym].quantity_step != 0:
                raise ValueError("snapshot quantity is not aligned to declared step")
            if pos.opened_us is not None and timestamp(pos.opened_us) > result.clock_us:
                raise ValueError("snapshot future entry")
            result.positions[sym] = pos
            rows = snapshot["marks"][sym]
            if len(rows) > 2:
                raise ValueError("snapshot mark window oversized")
            previous = -1
            for mark in rows:
                close, available = timestamp(mark["close_us"]), timestamp(mark["available_us"])
                price = decimal(mark["price"])
                if price <= 0 or not previous < close <= available <= result.clock_us:
                    raise ValueError("snapshot noncausal mark")
                previous = close
                result.marks[sym].append({"price": price, "close_us": close, "available_us": available})
            if pos.quantity and not result.marks[sym]:
                raise ValueError("snapshot position has no mark")
        for key in ("trades", "funding", "fill_requests", "funding_events", "funding_ids", "halt_witness"):
            setattr(result, key, deepcopy(snapshot[key]))
        for key in ("fees", "execution_cost", "funding_cash", "realized_PnL", "gross_fill_turnover"):
            setattr(result, key, decimal(snapshot["totals"][key]))
        result.status = snapshot["status"]
        if result.fees < 0 or result.execution_cost < 0:
            raise ValueError("negative snapshot costs")
        previous_status = result.status
        with localcontext() as ctx:
            ctx.prec = 40
            # Recovery must preserve actual accounting and event identities, not
            # merely produce an internally plausible free-wallet balance.
            if any(row["symbol"] not in result.symbols for row in result.trades + result.funding):
                raise ValueError("snapshot journal contains an unconfigured symbol")
            for sym in result.symbols:
                quantity = sum((decimal(row["decimal_strings"]["position_delta"])
                                for row in result.trades if row["symbol"] == sym), ZERO)
                if quantity != result.positions[sym].quantity:
                    raise ValueError("snapshot ledger/position bridge mismatch")
            totals = {
                "fees": sum((decimal(row["decimal_strings"]["fee_amount"]) for row in result.trades), ZERO),
                "execution_cost": sum((decimal(row["decimal_strings"]["execution_cost"]) for row in result.trades), ZERO),
                "realized_PnL": sum((decimal(row["decimal_strings"]["realized_PnL"]) for row in result.trades), ZERO),
                "funding_cash": sum((decimal(row["decimal_strings"]["signed_funding_USDT"]) for row in result.funding), ZERO),
                "gross_fill_turnover": sum((decimal(row["decimal_strings"]["quantity"]) *
                                             decimal(row["decimal_strings"]["fill_price"]) for row in result.trades), ZERO),
            }
            if any(abs(getattr(result, key) - value) > D("1e-25") for key, value in totals.items()):
                raise ValueError("snapshot ledger/total bridge mismatch")
            trade_groups: dict[str, list[dict[str, Any]]] = {}
            for row in result.trades:
                identity = row["fill_id"]
                if not isinstance(identity, str) or not identity:
                    raise ValueError("snapshot invalid trade fill id")
                trade_groups.setdefault(identity, []).append(row)
            if not set(trade_groups) <= set(result.fill_requests):
                raise ValueError("snapshot fill requests missing actual trades")
            expected_last_fill = max((timestamp(row["event_us"]) for row in result.trades), default=None)
            if result.last_fill_us != expected_last_fill:
                raise ValueError("snapshot last fill timestamp mismatch")
            for fill_id, saved in result.fill_requests.items():
                if (not isinstance(fill_id, str) or not fill_id or set(saved) != {"identity", "receipt"}
                        or set(saved["identity"]) != {"symbol", "side", "quantity", "event_us", "signal_us",
                            "execution_mid_price", "available_quantity", "quote_available_us", "reduce_only"}):
                    raise ValueError("snapshot invalid fill request identity")
                identity, receipt = saved["identity"], saved["receipt"]
                result._symbol(identity["symbol"])
                event, signal = timestamp(identity["event_us"]), timestamp(identity["signal_us"])
                available_us = timestamp(identity["quote_available_us"])
                requested, available_q = decimal(identity["quantity"]), decimal(identity["available_quantity"])
                mid = decimal(identity["execution_mid_price"])
                if (identity["side"] not in {"BUY", "SELL"} or type(identity["reduce_only"]) is not bool
                        or requested <= 0 or available_q < 0 or mid <= 0 or event > result.clock_us
                        or event < ExecutionContractV2().earliest_execution_us(signal) + 1 or available_us > event):
                    raise ValueError("snapshot noncausal fill request")
                legs = trade_groups.get(fill_id, [])
                if receipt["fill_id"] != fill_id or receipt["fills"] != legs or len(legs) > 2:
                    raise ValueError("snapshot fill request receipt/legs mismatch")
                executed = sum((decimal(row["decimal_strings"]["quantity"]) for row in legs), ZERO)
                expected = {"requested_quantity": requested, "executed_quantity": executed,
                            "remaining_quantity": requested - executed}
                if (executed > result._floor(identity["symbol"], min(requested, available_q))
                        or any(decimal(receipt["decimal_strings"][key]) != amount
                               or receipt[key] != float(amount) for key, amount in expected.items())
                        or receipt["status"] != ("FILLED" if executed == requested else "PARTIAL" if executed else "REJECTED")):
                    raise ValueError("snapshot fill request quantity/status mismatch")
                direction = D(1) if identity["side"] == "BUY" else D(-1)
                for row in legs:
                    exact = row["decimal_strings"]
                    quantity = decimal(exact["quantity"])
                    if (row["symbol"] != identity["symbol"] or row["side"] != identity["side"]
                            or row["event_us"] != event or row["signal_us"] != signal
                            or decimal(exact["execution_mid_price"]) != mid
                            or quantity <= 0 or quantity % result.instrument_profiles[identity["symbol"]].quantity_step != 0
                            or decimal(exact["position_delta"]) != direction * quantity
                            or row["leg"] not in {"OPEN", "CLOSE"}
                            or identity["reduce_only"] and row["leg"] != "CLOSE"):
                        raise ValueError("snapshot fill request/trade identity mismatch")
                if len(legs) == 2 and [row["leg"] for row in legs] != ["CLOSE", "OPEN"]:
                    raise ValueError("snapshot flip legs must close then open")
            keys = [f"{row['symbol']}:{row['event_us']}" for row in result.funding]
            ids = [row["event_id"] for row in result.funding]
            if (len(keys) != len(set(keys)) or len(ids) != len(set(ids))
                    or set(keys) != set(result.funding_events) or set(ids) != set(result.funding_ids)
                    or any(result.funding_ids[row["event_id"]] != key
                           or result.funding_events[key]["receipt"] != row
                           for key, row in zip(keys, result.funding))):
                raise ValueError("snapshot funding deduplication mismatch")
            if abs(result.nav() - result.config.initial_cash - result.realized_PnL
                   - sum((p.quantity * (result._mark(sym) - p.entry_price)
                          for sym, p in result.positions.items() if p.quantity), ZERO)
                   + result.fees - result.funding_cash) > D("1e-25"):
                raise ValueError("snapshot capital/PnL bridge mismatch")
            result._risk("RESTORE")
        if previous_status not in HALTS and result.status != previous_status:
            raise ValueError("snapshot risk state mismatch")
        return result
