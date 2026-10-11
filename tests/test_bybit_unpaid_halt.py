"""Debt and permanent halt regressions for the isolated specialization."""
from copy import deepcopy
from decimal import Decimal as D
import importlib.util
from pathlib import Path

import pytest

from quant.bybit_isolated_account import BybitIsolatedAccount
from quant.perpetual_account import HALTS

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("unpaid_fixture", ROOT / "research/liquidation-semantics-20261011/reproduce_unpaid_halt.py")
fixture = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fixture)


def test_unpaid_funding_with_positive_nav_halts_without_cross_leg_topup():
    account, receipt = fixture.funding_deficit(BybitIsolatedAccount)
    assert account.nav() > 0 and account.unpaid_liability == D("1003.801760000")
    assert receipt["account_status"] == account.status == "BANKRUPT_HALT"
    assert account.positions["ETHUSDT"].isolated_balance == D("2001.600")
    assert account.positions["BTCUSDT"].quantity == 20  # No debt-forgiving takeover.
    assert account.liquidations == [] and account.free_cash == 0
    assert account.halt_witness["phase"] == "AFTER_FUNDING"
    witness = deepcopy(account.halt_witness)
    # Public event APIs reject activity after a permanent halt.
    with pytest.raises(RuntimeError, match="BANKRUPT_HALT"):
        account.update_marks(3 * fixture.MINUTE, {s: {"price": "1000", "close_us": 3 * fixture.MINUTE,
            "available_us": 3 * fixture.MINUTE} for s in account.symbols})
    with pytest.raises(RuntimeError, match="BANKRUPT_HALT"):
        account.apply_funding("ETHUSDT", "synthetic-credit", 4 * fixture.MINUTE, "-1", 4 * fixture.MINUTE)
    account._risk("LATER_CHECK")
    assert account.status == "BANKRUPT_HALT" and account.halt_witness == witness
    before = len(account.trades)
    with pytest.raises(RuntimeError, match="BANKRUPT_HALT"):
        account.execute_fill("ETHUSDT", "SELL", "1", 4 * fixture.MINUTE + 1,
            3 * fixture.MINUTE, "after-halt", execution_mid_price="1000", quote_available_us=4 * fixture.MINUTE,
            reduce_only=True)
    assert len(account.trades) == before
    restored = BybitIsolatedAccount.from_snapshot(account.snapshot())
    assert restored.status == "BANKRUPT_HALT" and restored.halt_witness == witness


@pytest.mark.parametrize("status", sorted(HALTS))
def test_existing_halts_are_permanent(status):
    account = BybitIsolatedAccount(symbols=("BTCUSDT", "ETHUSDT"))
    account.status = status
    account.halt_witness = {"original": True}
    account._risk("LATER_CHECK")
    assert account.status == status and account.halt_witness == {"original": True}


def test_debt_created_inside_exchange_ioc_also_halts():
    account = BybitIsolatedAccount(symbols=("BTCUSDT", "ETHUSDT"))
    account.update_marks(0, {s: {"price": "100", "close_us": 0, "available_us": 0} for s in account.symbols})
    account._inside_liquidation = True
    account.unpaid_liability = D(".01")
    account._risk("INSIDE_IOC")
    assert account.status == "ACTIVE"
    account._inside_liquidation = False
    account._risk("AFTER_IOC")
    assert account.status == "BANKRUPT_HALT" and account.nav() > 0
