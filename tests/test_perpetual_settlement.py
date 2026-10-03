"""One regression for exact complete-margin release; no old suites or market IO."""
from copy import deepcopy
from decimal import Decimal as D, localcontext
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

import pytest

from quant.perpetual_account import USDTLinearPerpetualAccount

ROOT = Path(__file__).resolve().parents[1]
OLD_SHA = "2bae17b6351dec5c632e3af42fed2a6a5cf91293dba0a08c06a7aa81f4df58fb"
Q = D("0.00870327")
BALANCE = D("731.1570871092490859857031240710756816866")
ENTRY = D("84009.46852266436477159770110212318837474")
MID = D("66951.0")
MARK = D("66952.3")
MINUTE = 60_000_000


def test_exact_full_close_release_and_nonnegative_debit(tmp_path):
    archived = ROOT / "docs/archive/PERPETUAL_ACCOUNT_PRE_SETTLEMENT_FIX_SOURCE_20261003_V1.py"
    assert hashlib.sha256(archived.read_bytes()).hexdigest() == OLD_SHA
    spec = importlib.util.spec_from_file_location("quant._perpetual_pre_settlement_fix", archived)
    old = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = old
    spec.loader.exec_module(old)

    def state(account_type, quantity=Q, balance=BALANCE, entry=ENTRY):
        # Explicit starting-position microfixture: exact numbers copied from
        # the saved small close receipt, NOT a market replay or future input.
        account = account_type()
        account.update_marks(0, {s: {"price": str(MARK), "close_us": 0, "available_us": 0}
                                for s in ("BTCUSDT", "ETHUSDT")})
        with localcontext() as context:
            context.prec = 40
            position = account.positions["BTCUSDT"]
            position.quantity, position.entry_price = -quantity, entry
            position.isolated_balance, position.opened_us = balance, 0
            account.free_cash = D(10000) - balance
        return account

    def close(account, quantity=Q, identity="full", available=None):
        return account.execute_fill("BTCUSDT", "BUY", quantity, MINUTE + 1, 0, identity,
            execution_mid_price=MID, quote_available_us=MINUTE,
            available_quantity=available, reduce_only=True)

    # Reproduce the accepted old numerical bug in the same new regression case;
    # old source remains byte exact. Genuine financial debt is not forgiven.
    before = state(old.USDTLinearPerpetualAccount)
    old_receipt = close(before)
    assert before.status == "BANKRUPT_HALT"
    assert before.unpaid_liability == D("1e-37")
    old_release = D(old_receipt["fills"][0]["decimal_strings"]["margin_released"])
    assert old_release == D("731.1570871092490859857031240710756816867")

    after = state(USDTLinearPerpetualAccount)
    new_receipt = close(after)
    position = after.positions["BTCUSDT"]
    assert after.status == "ACTIVE" and after.unpaid_liability == 0
    assert position.quantity == 0 and position.isolated_balance == 0 and position.entry_price == 0
    assert D(new_receipt["fills"][0]["decimal_strings"]["margin_released"]) == BALANCE
    with localcontext() as context:
        context.prec = 50
        fill_price = MID * D("1.0008")
        realized = Q * (ENTRY - fill_price)
        fee = Q * fill_price * D(".00055")
        assert abs(after.nav() - (D(10000) + realized - fee)) <= D("1e-24")
        assert after.fees == fee

    # Partial release still uses the original ratio. Reduce-only clamps an
    # oversized final request to actual held quantity and refunds ALL remainder.
    partial = state(USDTLinearPerpetualAccount, D(".01"), D("700"), D("70000"))
    first = close(partial, D(".004"), "partial", available=D(".003"))
    assert first["status"] == "PARTIAL" and first["executed_quantity"] == .003
    assert partial.positions["BTCUSDT"].quantity == D("-.007")
    assert partial.positions["BTCUSDT"].isolated_balance == D("490")
    assert first["fills"][0]["margin_released"] == 210.
    partial.update_marks(2 * MINUTE, {s: {"price": str(MARK), "close_us": 2 * MINUTE,
                                       "available_us": 2 * MINUTE} for s in ("BTCUSDT", "ETHUSDT")})
    remainder = partial.execute_fill("BTCUSDT", "BUY", ".02", 2 * MINUTE + 1,
        MINUTE, "full-reduce-only", execution_mid_price=MID,
        quote_available_us=2 * MINUTE, reduce_only=True)
    assert remainder["executed_quantity"] == .007 and remainder["remaining_quantity"] == .013
    assert remainder["fills"][0]["margin_released"] == 490.
    assert partial.positions["BTCUSDT"].quantity == 0 and partial.unpaid_liability == 0

    # Negative input/state is rejected before any debit; never clamped to zero.
    debit = USDTLinearPerpetualAccount()
    original = debit.snapshot()
    with pytest.raises(ValueError, match="nonnegative"):
        debit._debit("BTCUSDT", D("-.001"))
    assert debit.snapshot() == original
    debit.positions["BTCUSDT"].isolated_balance = D("-1e-37")
    corrupt = deepcopy(debit.snapshot())
    with pytest.raises(ValueError, match="nonnegative"):
        debit._debit("BTCUSDT", D(1))
    assert debit.snapshot() == corrupt

    # Free-wallet first, then OWN isolated, then exact genuine unpaid amount.
    debit = USDTLinearPerpetualAccount()
    debit.free_cash = D(1)
    debit.positions["BTCUSDT"].isolated_balance = D(2)
    debit.positions["ETHUSDT"].isolated_balance = D(100)
    with localcontext() as context:
        context.prec = 40  # Same context as the actual public fill/funding APIs.
        debit._debit("BTCUSDT", D("3.0000000000000000000000000000000000001"))
    assert debit.free_cash == 0 and debit.positions["BTCUSDT"].isolated_balance == 0
    assert debit.positions["ETHUSDT"].isolated_balance == 100
    assert debit.unpaid_liability == D("1e-37")
    # An actual public entry/funding chain independently retains genuine debt.
    genuine = USDTLinearPerpetualAccount()
    genuine.update_marks(0, {s: {"price": "100", "close_us": 0, "available_us": 0}
                             for s in ("BTCUSDT", "ETHUSDT")})
    genuine.execute_fill("BTCUSDT", "SELL", "1", MINUTE + 1, 0, "actual-short",
        execution_mid_price="100", quote_available_us=MINUTE)
    charge = genuine.apply_funding("BTCUSDT", "real-deficit", 2 * MINUTE,
                                   D("-101"), 2 * MINUTE)
    assert charge["signed_funding_USDT"] < 0
    assert genuine.unpaid_liability > 0 and genuine.status == "BANKRUPT_HALT"
    assert genuine.positions["ETHUSDT"].isolated_balance == 0
    assert abs(D(genuine.summary()["decimal_strings"]["accounting_bridge_error_USDT"])) <= D("1e-24")
    (tmp_path / "settlement_evidence.json").write_text(json.dumps({
        "scope": "EXACT_SETTLEMENT_MICROFIXTURE_NOT_NEW_MARKET_RESULT",
        "archived_source_sha256": OLD_SHA, "old_false_halt": old_receipt,
        "old_false_liability": str(before.unpaid_liability), "new_full_close": new_receipt,
        "new_summary": after.summary(), "partial_final_summary": partial.summary(),
        "genuine_funding_deficit": charge, "genuine_summary": genuine.summary(),
        "no_epsilon_or_debt_forgiveness": True}, indent=2, sort_keys=True), encoding="utf-8")
