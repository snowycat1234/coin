"""Pre-registered isolated half-equity full-exit scheduler sensitivity.

This is a new policy adapter. It neither mutates the generic financial account nor
changes the original frozen NativeDailySimulator or historical baseline wallets.
"""
from __future__ import annotations

from copy import deepcopy
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import sys

from quant.perpetual_account import HALTS, ZERO
from scripts.investment.perpetual_directional import MINUTE
from scripts.investment.resumable_perpetual import NativeDailySimulator

HERE = Path(__file__).resolve().parent
POLICY_ID = "isolated_half_equity_full_exit_v1"
PROTOCOL_SHA256 = "1ff06b9c9225ce28c36e32010f0e2551d344c0742baf644c6096a2d22e579adc"
TRIGGER_FRACTION = Decimal("0.5")


def verified_protocol() -> dict:
    path = HERE / "PROTOCOL.json"
    if hashlib.sha256(path.read_bytes()).hexdigest() != PROTOCOL_SHA256:
        raise ValueError("Protective policy protocol bytes changed")
    protocol = json.loads(path.read_text())
    if (protocol.get("policy_id") != POLICY_ID
            or protocol.get("primary_parameter", {}).get("isolated_equity_fraction_trigger") != "0.5"):
        raise ValueError("Protective policy identity or threshold changed")
    return protocol


def verified_freeze() -> dict:
    """Fail closed if this adapter or its frozen financial dependencies drift."""
    freeze = json.loads((HERE / "FREEZE.json").read_text())
    repo = Path(sys.modules[NativeDailySimulator.__module__].__file__).resolve().parents[2]
    paths = {
        "protocol": HERE / "PROTOCOL.json",
        "adapter": HERE / "protective_policy.py",
        "synthetic_tests": HERE / "test_policy_synthetic.py",
        "run_manifest": HERE / "RUN_MANIFEST.json",
        "read_only_preflight": HERE / "preflight_run_plan.py",
        "scheduler": repo / "scripts/investment/resumable_perpetual.py",
        "account": repo / "src/quant/perpetual_account.py",
        "quantity_adapter": repo / "research/quantity-grid-sensitivity-20261012/grid_account.py",
        "quantity_profile": repo / "research/quantity-grid-sensitivity-20261012/QUANTITY_PROFILE.json",
    }
    if freeze.get("policy_id") != POLICY_ID or set(freeze.get("SHA256", {})) != set(paths):
        raise ValueError("Protective policy freeze manifest invalid")
    for key, path in paths.items():
        if hashlib.sha256(path.read_bytes()).hexdigest() != freeze["SHA256"][key]:
            raise ValueError(f"Protective policy freeze mismatch: {key}")
    verified_protocol()
    return freeze


def sign(value: Decimal) -> int:
    return (value > 0) - (value < 0)


class ProtectiveFullExitSimulator(NativeDailySimulator):
    """Full close after a completed 50%-collateral-loss mark; no new account math.

    The original PROTECTIVE_STOP intent already persists after its first five
    capacity-limited attempts. This adapter prevents newer daily targets and
    exposure-cap reductions from replacing it. Same-direction reentry requires
    a later neutral/opposite *daily* target after the position is flat.
    """

    VERSION = "native_daily_scheduler_with_isolated_half_equity_full_exit_v1"

    def __init__(self, *args, **kwargs):
        verified_freeze()
        super().__init__(*args, **kwargs)
        self.protective_locks: dict[str, dict] = {}
        self.protective_events: list[dict] = []

    def schedule(self, target, signal, kind, only_symbols=None):
        symbols = self.symbols if only_symbols is None else tuple(only_symbols)
        for symbol in symbols:
            order_kind = kind[symbol] if isinstance(kind, dict) else kind
            lock = self.protective_locks.get(symbol)
            if lock is not None:
                position = self.account.positions[symbol].quantity
                desired = Decimal(str(target[symbol]))
                if position:
                    if order_kind == "RISK_REDUCTION":
                        # The frozen cap-breach five-attempt stop has priority.
                        # A protected instrument's cap order still aims at
                        # full zero; the original scheduler decides whether
                        # an unexecutable cap breach must stop the case.
                        super().schedule({symbol: ZERO}, int(signal),
                                         "RISK_REDUCTION", only_symbols=(symbol,))
                        continue
                    if self.pending.get(symbol, {}).get("kind") == "RISK_REDUCTION":
                        # Do not let a later daily target reset the original
                        # hard-risk order's five-attempt clock.
                        continue
                    # Only the existing full reduce-only order may act on this
                    # instrument while exposure remains. Never supersede it.
                    if self.pending.get(symbol, {}).get("kind") != "PROTECTIVE_STOP":
                        super().schedule({symbol: ZERO}, int(signal), "PROTECTIVE_STOP",
                                         only_symbols=(symbol,))
                    continue
                if order_kind == "DAILY_TARGET" and sign(desired) != lock["stopped_sign"]:
                    self.protective_events.append({"kind": "RESET_BY_NEW_DAILY_DIRECTION",
                        "symbol": symbol, "event_us": int(signal), "new_sign": sign(desired)})
                    del self.protective_locks[symbol]
                else:
                    # Flat, but the old direction has not reset. Non-daily
                    # instructions cannot unlock the entry gate.
                    continue
            super().schedule(target, signal, kind, only_symbols=(symbol,))

    def risk_schedule(self, stamp):
        # All protection decisions use the causally completed mark, not an
        # intraminute high/low or the next execution open. An account halt on
        # update_marks/apply_funding has priority and is never overridden.
        next_event_same_clock = (self.event_cursor < len(self.window["events"])
            and self.window["events"][self.event_cursor]["event_us"] == int(stamp))
        if (self.account.status not in HALTS and int(stamp) % MINUTE == 0
                and not next_event_same_clock):
            for symbol in self.symbols:
                position = self.account.positions[symbol]
                if not position.quantity or symbol in self.protective_locks:
                    continue
                marks = self.account.marks[symbol]
                if not marks or marks[-1]["close_us"] != int(stamp):
                    continue
                mark = marks[-1]["price"]
                balance = position.isolated_balance
                equity = balance + position.quantity * (mark - position.entry_price)
                if balance > ZERO and equity <= TRIGGER_FRACTION * balance:
                    self.protective_locks[symbol] = {
                        "stopped_sign": sign(position.quantity),
                        "trigger_us": int(stamp), "flat_us": None,
                        "deferred_no_lot_minutes": 0}
                    self.protective_events.append({"kind": "FULL_EXIT_SIGNAL",
                        "symbol": symbol, "event_us": int(stamp),
                        "quantity": str(position.quantity), "mark": str(mark),
                        "isolated_balance": str(balance), "isolated_equity": str(equity)})
                    super().schedule({symbol: ZERO}, int(stamp), "PROTECTIVE_STOP",
                                     only_symbols=(symbol,))
        super().risk_schedule(stamp)

    def attempt(self, open_us, market_row):
        # A whole-lot close is impossible when the *previous completed*
        # minute's quote-volume participation cap is smaller than one lot.
        # Keep the intent but avoid an unbounded duplicate rejection journal
        # on a long zero-volume stretch. The base scheduler still handles
        # every minute with executable capacity, including partial fills.
        deferred = {}
        for symbol, lock in self.protective_locks.items():
            order = self.pending.get(symbol)
            if (order is None or order["kind"] != "PROTECTIVE_STOP"
                    or not self.account.positions[symbol].quantity
                    or symbol not in market_row or self.previous_quote is None):
                continue
            available = (Decimal(str(self.previous_quote[symbol])) * Decimal("0.001")
                         / Decimal(str(market_row[symbol]["open"])))
            step = self.account.instrument_profiles[symbol].quantity_step
            if available < step:
                deferred[symbol] = self.pending.pop(symbol)
                lock["deferred_no_lot_minutes"] += 1
        try:
            result = super().attempt(open_us, market_row)
        finally:
            for symbol, order in deferred.items():
                if symbol not in self.pending:
                    self.pending[symbol] = order
        for symbol, lock in self.protective_locks.items():
            if lock["flat_us"] is None and not self.account.positions[symbol].quantity:
                lock["flat_us"] = int(open_us) + 1
                kind = ("FLAT_ON_HALTED_ACCOUNT" if self.account.status in HALTS
                        else "FULL_EXIT_FLAT")
                self.protective_events.append({"kind": kind,
                    "symbol": symbol, "event_us": lock["flat_us"]})
            elif (self.stop is None and self.account.status not in HALTS
                  and self.account.positions[symbol].quantity
                  and symbol not in self.pending):
                # If a cap-priority order completed/expired after resolving
                # the cap breach but left exposure, resume the full exit on
                # the original latency clock. Never revive a stopped case.
                super().schedule({symbol: ZERO}, int(open_us) + 1,
                                 "PROTECTIVE_STOP", only_symbols=(symbol,))
        return result

    def advance_day(self, *args, **kwargs):
        result = super().advance_day(*args, **kwargs)
        if self.cursor >= self.end and self.stop is None and any(
                self.account.positions[symbol].quantity
                for symbol in self.protective_locks):
            self.completion = "NOT_EVALUABLE_PROTECTIVE_EXIT_UNFILLED_AT_HORIZON"
            result["completion"] = self.completion
        return result

    def snapshot(self):
        image = super().snapshot()
        image["protective_policy"] = {
            "policy_id": POLICY_ID, "protocol_sha256": PROTOCOL_SHA256,
            "trigger_fraction": str(TRIGGER_FRACTION)}
        image["state"]["protective_locks"] = deepcopy(self.protective_locks)
        image["state"]["protective_events"] = deepcopy(self.protective_events)
        return image

    @classmethod
    def from_snapshot(cls, snapshot, window, *, account_class):
        verified_freeze()
        if snapshot.get("protective_policy") != {
                "policy_id": POLICY_ID, "protocol_sha256": PROTOCOL_SHA256,
                "trigger_fraction": str(TRIGGER_FRACTION)}:
            raise ValueError("Protective policy recovery identity mismatch")
        if not {"protective_locks", "protective_events"} <= set(snapshot.get("state", {})):
            raise ValueError("Protective policy recovery state missing")
        result = super().from_snapshot(snapshot, window, account_class=account_class)
        for symbol, row in result.protective_locks.items():
            if (symbol not in result.symbols or set(row) != {
                    "stopped_sign", "trigger_us", "flat_us", "deferred_no_lot_minutes"}
                    or row["stopped_sign"] not in (-1, 1)
                    or type(row["trigger_us"]) is not int
                    or not 0 <= row["trigger_us"] <= result.account.clock_us
                    or row["flat_us"] is not None and (
                        type(row["flat_us"]) is not int
                        or not row["trigger_us"] <= row["flat_us"] <= result.account.clock_us)
                    or type(row["deferred_no_lot_minutes"]) is not int
                    or row["deferred_no_lot_minutes"] < 0):
                raise ValueError("Protective policy recovery lock invalid")
            quantity = result.account.positions[symbol].quantity
            if quantity and result.account.status not in HALTS and (
                    sign(quantity) != row["stopped_sign"] or row["flat_us"] is not None
                    or result.pending.get(symbol, {}).get("kind") not in
                    ("PROTECTIVE_STOP", "RISK_REDUCTION")
                    or result.pending[symbol]["target"] != ZERO):
                raise ValueError("Protective policy live exit intent missing")
        return result

    def result(self):
        case = super().result()
        case["protective_policy"] = {
            "policy_id": POLICY_ID, "protocol_sha256": PROTOCOL_SHA256,
            "trigger_fraction": str(TRIGGER_FRACTION),
            "events": deepcopy(self.protective_events),
            "open_locks": deepcopy(self.protective_locks)}
        case["summary"]["protective_policy_id"] = POLICY_ID
        case["summary"]["protective_trigger_count"] = sum(
            event["kind"] == "FULL_EXIT_SIGNAL" for event in self.protective_events)
        case["summary"]["protective_full_exit_count"] = sum(
            event["kind"] == "FULL_EXIT_FLAT" for event in self.protective_events)
        return case
