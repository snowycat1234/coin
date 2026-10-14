"""Pure synthetic signal/intent policy. No accounts, transport, data loader or AI.

The fixed-range replacement rule is inspired by documented Spot Grid. Execution
and wallet semantics are intentionally delegated to the original financial engine.
This is a perpetual-target emulation, not a Bybit Spot Grid/Aurora replica.
"""
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation, ROUND_DOWN
from math import isfinite
from datetime import datetime, timezone
from uuid import uuid4

CORE5 = ("BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT", "DOGEUSDT")
CANDIDATE_ID = "CSH_BTC_GRID_REPLACE10"
MINUTE_US = 60_000_000
STEP = Decimal("0.00000001")


def dec(x):
    if isinstance(x, bool) or not isinstance(x,(str,int,float,Decimal)):
        raise ValueError("finite numeric required")
    try:
        y = Decimal(str(x))
    except InvalidOperation as e:
        raise ValueError("finite numeric required") from e
    if not y.is_finite():
        raise ValueError("finite numeric required")
    return y


@dataclass(frozen=True)
class CompletedClose:
    available_us: int
    price: Decimal
    bar_end_us: int  # exclusive UTC daily candle end, separate from availability


@dataclass(frozen=True)
class CompletedMinute:
    available_us: int
    price: Decimal
    bar_end_us: int


def observed_price(observation, decision_us):
    if (not isinstance(observation,CompletedMinute)
            or type(observation.available_us) is not int
            or type(observation.bar_end_us) is not int
            or not 0 <= observation.bar_end_us <= observation.available_us <= decision_us
            or decision_us-observation.available_us > MINUTE_US
            or decision_us-observation.bar_end_us > MINUTE_US):
        raise ValueError("fresh timestamped completed-minute observation required")
    price=dec(observation.price)
    if price <= 0:
        raise ValueError("positive observation price required")
    return price


@dataclass(frozen=True)
class Intent:
    slot: int
    side: str
    quantity: Decimal
    decision_us: int
    not_before_us: int
    reason: str
    order_id: str
    session_id: str


@dataclass
class Slot:
    buy_level: Decimal
    sell_level: Decimal
    mode: str
    owned: Decimal = Decimal(0)


class FixedGrid:
    """Four fixed equal-base-quantity slots, no trailing, top-up or doubling.

    A caller owns the complete-price history. Initial long inventory is an
    explicit paid buy intent. Cash and position risk must be reserved externally.
    Replacements occur only after actual fill callbacks, never price touches.
    """
    def __init__(self, closes, decision_us, current_price, replacement_notional):
        if type(decision_us) is not int or decision_us < 0:
            raise ValueError("invalid decision clock")
        if len(closes) != 30:
            raise ValueError("exactly 30 completed daily closes required")
        if any(type(c.available_us) is not int or type(c.bar_end_us) is not int
               or not 0 <= c.bar_end_us <= c.available_us <= decision_us
               for c in closes):
            raise ValueError("future or invalid availability clock")
        if any(a.bar_end_us >= b.bar_end_us for a, b in zip(closes, closes[1:])):
            raise ValueError("strict chronological source required")
        if any(b.bar_end_us-a.bar_end_us != 1440*MINUTE_US
               for a, b in zip(closes, closes[1:])):
            raise ValueError("daily complete history required")
        if not 0 <= decision_us-closes[-1].available_us <= 1440*MINUTE_US:
            raise ValueError("completed-close availability older than maximum24h")
        if not 0 <= decision_us-closes[-1].bar_end_us <= 1440*MINUTE_US:
            raise ValueError("latest completed daily candle older than maximum24h")
        prices = [dec(c.price) for c in closes]
        self.lower, self.upper = min(prices), max(prices)
        current = observed_price(current_price,decision_us)
        self.budget = dec(replacement_notional)
        if self.lower <= 0 or not self.lower < current < self.upper or self.budget <= 0:
            raise ValueError("no active grid without positive budget and interior current price")
        # Transparent self-defined allocator; Bybit's initial allocator is undisclosed.
        # Four slots all long at U plus BASE27 one-side cash debit fit this budget.
        self.quantity = (self.budget / (4*self.upper*Decimal("1.00135044"))).quantize(
            STEP, rounding=ROUND_DOWN)
        buy_debit = Decimal("1.0008")*Decimal("1.00055")
        sell_credit = Decimal(".9992")*Decimal(".99945")
        minimum_ratio = self.upper / (self.upper-(self.upper-self.lower)/4)
        if minimum_ratio <= buy_debit/sell_credit:
            raise ValueError("spacing cannot cover identical BASE27 round-trip friction")
        if self.quantity*self.lower < 10:
            raise ValueError("opening minimum notional cannot be met")
        levels = [self.lower + i*(self.upper-self.lower)/4 for i in range(5)]
        self.slots = [Slot(levels[i], levels[i+1],
                           "BUY" if levels[i] < current else "INIT") for i in range(4)]
        self.pending = {}
        self.session_id = f"{CANDIDATE_ID}:{decision_us}:{uuid4().hex}"
        self.order_sequence = 0
        self.seen_fill_ids = set()
        self.last_clock = decision_us
        self.last_observation = current_price
        self.session_end_us = decision_us+7*1440*MINUTE_US
        self.expired = False

    def reserve_quantity(self):
        """All potential filled inventory; sells never free risk before filling."""
        if self.expired:
            return self.inventory()+sum((i.quantity for i in self.pending.values()
                if i.side == "BUY"), Decimal(0))
        return self.quantity*4

    def settled(self):
        return self.inventory() == 0 and not self.pending

    def inventory(self):
        return sum((s.owned for s in self.slots), Decimal(0))

    def intents(self, decision_us, observation):
        if type(decision_us) is not int or decision_us < self.last_clock:
            raise ValueError("noncausal observation")
        price = observed_price(observation,decision_us)
        if (observation.available_us == self.last_observation.available_us
                and observation != self.last_observation):
            raise ValueError("conflicting observation at same availability clock")
        if observation.available_us < self.last_observation.available_us:
            raise ValueError("observation availability cannot rewind")
        self.last_clock = decision_us
        self.last_observation = observation
        next_open = (decision_us//MINUTE_US+1)*MINUTE_US+1
        if decision_us >= self.session_end_us or next_open >= self.session_end_us:
            self.expire(decision_us)
        if self.expired or not self.lower <= price <= self.upper:
            return []  # Existing inventory remains owned and marked.
        out = []
        for i, slot in enumerate(self.slots):
            if i in self.pending:
                continue
            side = None
            if slot.mode == "INIT":
                side, reason = "BUY", "PAID_INITIAL_INVENTORY"
            elif slot.mode == "BUY" and price <= slot.buy_level:
                side, reason = "BUY", "COMPLETED_CLOSE_BUY_LEVEL"
            elif slot.mode == "SELL" and price >= slot.sell_level:
                side, reason = "SELL", "COMPLETED_CLOSE_SELL_LEVEL"
            if side:
                qty = self.quantity-slot.owned if side == "BUY" else slot.owned
                # Original scheduler owns precise timing/expiry. This intent is only
                # eligible at the next minute open +1us, never at the signal price.
                next_open = (decision_us//MINUTE_US+1)*MINUTE_US+1
                self.order_sequence += 1
                order_id = f"{self.session_id}:{self.order_sequence}"
                intent = Intent(i, side, qty, decision_us, next_open, reason,
                                order_id, self.session_id)
                self.pending[i] = intent
                out.append(intent)
        return out

    def on_fill(self, slot_id, quantity, fill_us, *, order_id, side, fill_id):
        intent = self.pending.get(slot_id) if type(slot_id) is int else None
        if (intent is None or order_id != intent.order_id or side != intent.side
                or type(fill_id) is not str or not fill_id or fill_id in self.seen_fill_ids):
            raise ValueError("stale order, wrong side or duplicate/invalid fill identity")
        qty = dec(quantity)
        if type(fill_us) is not int or fill_us < max(intent.not_before_us,self.last_clock):
            raise ValueError("fill before eligible execution")
        if qty <= 0 or qty > intent.quantity or qty % STEP:
            raise ValueError("invalid actual fill quantity")
        slot = self.slots[slot_id]
        new_owned=slot.owned+(qty if intent.side == "BUY" else -qty)
        if not 0 <= new_owned <= self.quantity:
            raise ValueError("inventory violation")
        self.seen_fill_ids.add(fill_id)
        self.last_clock = fill_us
        slot.owned = new_owned
        remain = intent.quantity-qty
        if remain:
            self.pending[slot_id] = Intent(slot_id, intent.side, remain,
                                           intent.decision_us, intent.not_before_us,
                                           intent.reason, intent.order_id, intent.session_id)
        else:
            del self.pending[slot_id]
            slot.mode = "SELL" if intent.side == "BUY" else "BUY"

    def on_cancel_confirmed(self, slot_id, *, order_id, cancel_us):
        """Only confirmed original-scheduler cancellation, never a cancel request.

        A partial fill stays owned. Reservation is retained until this callback.
        """
        intent = self.pending.get(slot_id) if type(slot_id) is int else None
        if (intent is None or order_id != intent.order_id or type(cancel_us) is not int
                or cancel_us < self.last_clock):
            raise ValueError("stale cancellation identity")
        self.last_clock=cancel_us
        del self.pending[slot_id]

    def expire(self, event_us):
        """Stop new intents; pending orders remain executable until confirmed canceled.

        A caller must request cancels and obtain on_cancel_confirmed callbacks,
        then execute an original paid reduction. Settled requires actual flat
        inventory AND no pending orders. No reservations are released here.
        """
        if type(event_us) is not int or event_us < self.last_clock:
            raise ValueError("noncausal expiry clock")
        self.last_clock=event_us
        self.expired = True
        return self.inventory()


def replacement_weight(original_core5_weights):
    raw=tuple(original_core5_weights)
    if any(isinstance(x,bool) or not isinstance(x,(int,float,Decimal)) for x in raw):
        raise ValueError("numeric CORE5 targets required; booleans forbidden")
    weights = tuple(float(x) for x in raw)
    if len(weights) != 5 or any(not isfinite(x) for x in weights):
        raise ValueError("ordered finite CORE5 target required")
    return .10*max(0., weights[0])


def compose_target(original_core5_weights, removed_weight, actual_grid_qty, mark, nav):
    """One-way net target only. Separate gross/reservation risk checks still required."""
    weights = tuple(float(x) for x in original_core5_weights)
    expected = replacement_weight(weights)
    if isinstance(removed_weight,bool) or not isfinite(removed_weight) or abs(removed_weight-expected) > 1e-12:
        raise ValueError("only fixed 10% positive original BTC sleeve may be replaced")
    qty, mark, nav = float(actual_grid_qty), float(mark), float(nav)
    if not all(isfinite(x) for x in (qty, mark, nav)) or qty < 0 or mark <= 0 or nav <= 0:
        raise ValueError("invalid inventory/valuation")
    return (weights[0]-removed_weight+qty*mark/nav, *weights[1:])


def weekly_plan(closes, decision_us, current_price, nav, original_weights):
    """Candidate's single causal weekly gate. No regime/AI selector exists."""
    if type(decision_us) is not int or decision_us < 0:
        raise ValueError("invalid weekly clock")
    d = datetime.fromtimestamp(decision_us/1_000_000, tz=timezone.utc)
    if (d.weekday(), d.hour, d.minute, d.second, d.microsecond) != (0,0,0,0,0):
        raise ValueError("weekly reset only Monday 00:00 UTC")
    if not closes:
        raise ValueError("completed daily history required")
    weight = replacement_weight(original_weights)
    if weight == 0:
        return None
    return FixedGrid(closes, decision_us, current_price, dec(nav)*dec(weight))
