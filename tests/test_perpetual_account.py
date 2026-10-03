"""Independent hand arithmetic for the new perpetual product; synthetic only."""
from copy import deepcopy
from decimal import Decimal as D, localcontext

import pytest

from quant.perpetual_account import PerpetualConfig, USDTLinearPerpetualAccount

MINUTE = 60_000_000
SYMS = ("BTCUSDT", "ETHUSDT")
TOL = D("1e-24")


def near(actual, expected):
    assert abs(actual - expected) <= TOL


def marks(account, t, btc="100", eth="100", close=None):
    close = t if close is None else close
    return account.update_marks(t, {sym: {"price": price, "close_us": close, "available_us": t}
                                   for sym, price in zip(SYMS, (btc, eth))})


def fill(account, sym, side, qty, t, signal, identity, mid="100", **kwargs):
    return account.execute_fill(sym, side, qty, t, signal, identity,
                                execution_mid_price=mid, quote_available_us=t, **kwargs)


@pytest.mark.parametrize("side,direction", [("BUY", D(1)), ("SELL", D(-1))])
def test_two_long_or_two_short_cash_fee_and_terminal_mark(side, direction):
    """No long principal purchase or short proceeds enter economic cash."""
    account = USDTLinearPerpetualAccount()
    marks(account, 0)
    price = D("100") * (1 + direction * D("0.0008"))
    total_q = D("27")
    margin = total_q * price
    fee = margin * D("0.00055")
    execution = total_q * D("0.08")
    for sym, q in zip(SYMS, ("12", "15")):
        result = fill(account, sym, side, q, MINUTE + 1, 0, sym + side)
        assert result["status"] == "FILLED"
        assert account.positions[sym].quantity == direction * D(q)
        assert account.positions[sym].entry_price == price
    near(account.free_cash, D("10000") - margin - fee)
    near(account.nav(), D("10000") - fee - execution)
    marks(account, 2 * MINUTE, "105", "95")
    mid_gross = direction * (D(12) * D(5) - D(15) * D(5))
    near(account.nav(), D("10000") + mid_gross - execution - fee)
    report = account.summary()
    near(D(report["decimal_strings"]["gross_PnL_same_quantities"]), mid_gross)
    near(D(report["decimal_strings"]["accounting_bridge_error_USDT"]), D(0))
    assert report["contract"]["nominal_roundtrip_bps"] == 27
    assert report["contract"]["native_liquidation_certified"] is False


def test_trade_mid_is_separate_from_mark_no_execution_cost_double_debit():
    account = USDTLinearPerpetualAccount()
    marks(account, 0, "99", "99")
    result = fill(account, "BTCUSDT", "BUY", "10", MINUTE + 1, 0, "separate")
    trade = result["fills"][0]
    assert trade["fill_price"] == 100.08 and trade["mark_price"] == 99
    expected_fee = D(10) * D("100.08") * D("0.00055")
    near(account.nav(), D(10000) + D(10) * (D(99) - D("100.08")) - expected_fee)
    first_nav = account.nav()
    marks(account, 2 * MINUTE, "99", "99")
    near(account.nav(), first_nav)
    assert account.positions["BTCUSDT"].quantity == 10  # fees never subtract base
    assert trade["fee_asset"] == "USDT"


@pytest.mark.parametrize("exit_mid,gross", [("90", "10"), ("110", "-10")])
def test_one_short_100_to_90_or_110_gross_and_real_cost(exit_mid, gross):
    account = USDTLinearPerpetualAccount()
    marks(account, 0)
    opened = fill(account, "BTCUSDT", "SELL", "1", MINUTE + 1, 0, "short-100")
    marks(account, 2 * MINUTE, exit_mid, "100")
    closed = fill(account, "BTCUSDT", "BUY", "1", 2 * MINUTE + 1, MINUTE,
                  "short-exit", mid=exit_mid, reduce_only=True)
    assert opened["status"] == closed["status"] == "FILLED"
    fee = (D("99.92") + D(exit_mid) * D("1.0008")) * D("0.00055")
    execution = D("0.08") + D(exit_mid) * D("0.0008")
    near(account.nav(), D(10000) + D(gross) - fee - execution)
    report = account.summary()
    near(D(report["decimal_strings"]["gross_PnL_same_quantities"]), D(gross))
    near(D(report["decimal_strings"]["fees_USDT"]), fee)
    near(D(report["decimal_strings"]["execution_cost_USDT"]), execution)
    assert account.positions["BTCUSDT"].quantity == 0
    assert account.positions["BTCUSDT"].isolated_balance == 0


def test_funding_sign_strict_previous_mark_entry_boundary_dedupe_restore():
    account = USDTLinearPerpetualAccount()
    marks(account, 0)
    flat = account.apply_funding("BTCUSDT", "flat", MINUTE, "0.01", MINUTE)
    assert flat["owned"] is False and flat["signed_funding_USDT"] == 0
    fill(account, "BTCUSDT", "BUY", "10", MINUTE + 1, 0, "long")
    fill(account, "ETHUSDT", "SELL", "10", MINUTE + 1, 0, "short")
    marks(account, 2 * MINUTE, "110", "110")
    start = account.nav()
    # Mark at the event boundary is excluded; old mark=100 settles this event.
    long = account.apply_funding("BTCUSDT", "long-plus", 2 * MINUTE, ".001", 2 * MINUTE)
    short = account.apply_funding("ETHUSDT", "short-plus", 2 * MINUTE, ".001", 2 * MINUTE)
    assert long["signed_funding_USDT"] == -1 and short["signed_funding_USDT"] == 1
    assert long["mark_close_us"] == 0
    near(account.nav(), start)
    again = account.apply_funding("ETHUSDT", "short-plus", 2 * MINUTE, ".001", 2 * MINUTE)
    assert again == short and len(account.funding) == 3
    restored = USDTLinearPerpetualAccount.from_snapshot(account.snapshot())
    assert restored.snapshot() == account.snapshot()
    assert restored.apply_funding("ETHUSDT", "short-plus", 2 * MINUTE, ".001", 2 * MINUTE) == short
    with pytest.raises(ValueError, match="conflicting"):
        restored.apply_funding("ETHUSDT", "short-plus", 2 * MINUTE, ".002", 2 * MINUTE)
    with pytest.raises(ValueError, match="availability"):
        restored.apply_funding("BTCUSDT", "future-rate", 3 * MINUTE, ".001", 3 * MINUTE + 1)
    marks(restored, 3 * MINUTE, "109", "109")
    long_negative = restored.apply_funding("BTCUSDT", "long-minus", 3 * MINUTE, "-.001", 3 * MINUTE)
    short_negative = restored.apply_funding("ETHUSDT", "short-minus", 3 * MINUTE, "-.001", 3 * MINUTE)
    assert long_negative["signed_funding_USDT"] == 1.1
    assert short_negative["signed_funding_USDT"] == -1.1
    assert restored.funding_cash == 0
    # Funding then close at event+1us receives exactly one coupon before close.
    fill(restored, "BTCUSDT", "SELL", "10", 3 * MINUTE + 1, 2 * MINUTE, "close", mid="109", reduce_only=True)
    with pytest.raises(ValueError, match="must precede"):
        restored.apply_funding("BTCUSDT", "late-tie", 3 * MINUTE + 1, ".001", 3 * MINUTE + 1)


def test_add_reduce_partial_and_flip_turnover_basis_and_fees_once():
    account = USDTLinearPerpetualAccount()
    marks(account, 0)
    fill(account, "BTCUSDT", "BUY", "10", MINUTE + 1, 0, "open")
    marks(account, 2 * MINUTE, "110", "100")
    add = fill(account, "BTCUSDT", "BUY", "2", 2 * MINUTE + 1, MINUTE, "add", mid="110")
    assert add["status"] == "FILLED"
    with localcontext() as ctx:
        ctx.prec = 40
        basis = (D(10) * D("100.08") + D(2) * D("110.088")) / D(12)
        near(account.positions["BTCUSDT"].entry_price, basis)
        old_balance = account.positions["BTCUSDT"].isolated_balance
        partial = fill(account, "BTCUSDT", "SELL", "6", 3 * MINUTE + 1, 2 * MINUTE,
                       "partial", mid="110", available_quantity="4")
        assert partial["status"] == "PARTIAL" and partial["executed_quantity"] == 4
        assert account.positions["BTCUSDT"].quantity == 8
        near(account.positions["BTCUSDT"].isolated_balance, old_balance * D(8) / D(12))
        near(account.positions["BTCUSDT"].entry_price, basis)
        # Remaining long8 closes, short5 opens: two legs, gross13, netdelta−13.
        flipped = fill(account, "BTCUSDT", "SELL", "13", 4 * MINUTE + 1, 3 * MINUTE,
                       "flip", mid="110")
        assert [row["leg"] for row in flipped["fills"]] == ["CLOSE", "OPEN"]
        assert [row["quantity"] for row in flipped["fills"]] == [8, 5]
        assert account.positions["BTCUSDT"].quantity == -5
        assert account.positions["BTCUSDT"].entry_price == D("109.912")
        flip_fee = D(13) * D("109.912") * D("0.00055")
        near(sum((D(row["decimal_strings"]["fee_amount"]) for row in flipped["fills"]), D(0)), flip_fee)
        saved = account.snapshot()
        assert fill(account, "BTCUSDT", "SELL", "13", 4 * MINUTE + 1, 3 * MINUTE,
                    "flip", mid="110") == flipped
        assert account.snapshot() == saved
        reduced = fill(account, "BTCUSDT", "BUY", "9", 5 * MINUTE + 1, 4 * MINUTE,
                       "reduce", mid="110", reduce_only=True)
        assert reduced["executed_quantity"] == 5 and reduced["remaining_quantity"] == 4
        assert account.positions["BTCUSDT"].quantity == 0
        assert account.positions["BTCUSDT"].isolated_balance == 0
        near(D(account.summary()["decimal_strings"]["accounting_bridge_error_USDT"]), D(0))


def test_gross_caps_net_zero_drift_reduce_and_open_rejections():
    account = USDTLinearPerpetualAccount()
    marks(account, 0)
    # Two opposite exposures still consume gross risk; caps cannot net them away.
    fill(account, "BTCUSDT", "BUY", "29", MINUTE + 1, 0, "long")
    fill(account, "ETHUSDT", "SELL", "29", MINUTE + 1, 0, "short")
    assert account.summary()["net_signed_notional"] == 0
    assert account.summary()["gross_weight"] > .58
    rejected = fill(account, "ETHUSDT", "SELL", "2", 2 * MINUTE + 1, MINUTE, "overcap")
    assert rejected["reason"] == "POST_FILL_EXPOSURE_CAP_REJECTED"
    assert account.positions["ETHUSDT"].quantity == -29
    marks(account, 3 * MINUTE, "120", "100")
    assert account.status == "BOUND_BREACH_REDUCTION_REQUIRED"
    no_risk = fill(account, "ETHUSDT", "SELL", "1", 3 * MINUTE + 1, 2 * MINUTE, "no-risk")
    assert no_risk["reason"] == "BOUND_BREACH_REDUCTION_REQUIRED"
    reduction = fill(account, "BTCUSDT", "SELL", "5", 4 * MINUTE + 1, 3 * MINUTE,
                     "reduce-drift", mid="120", reduce_only=True)
    assert reduction["status"] == "FILLED" and account.positions["BTCUSDT"].quantity == 24
    assert account.status == "ACTIVE"
    cash = USDTLinearPerpetualAccount()
    marks(cash, 0)
    no_margin = fill(cash, "BTCUSDT", "BUY", "1", MINUTE + 1, 0, "no-margin", mid="20000")
    assert no_margin["reason"] == "INSUFFICIENT_FREE_MARGIN"
    assert cash.free_cash == 10000 and cash.positions["BTCUSDT"].quantity == 0
    assert fill(cash, "BTCUSDT", "SELL", "1", 2 * MINUTE + 1, MINUTE, "flat-reduce",
                reduce_only=True)["reason"] == "REDUCE_ONLY_NO_OPPOSITE_POSITION"
    with pytest.raises(ValueError, match="mixed"):
        USDTLinearPerpetualAccount(external_gross_notional=1)
    with pytest.raises(ValueError, match="mixed"):
        USDTLinearPerpetualAccount(market_type="SPOT")
    with pytest.raises(ValueError):
        PerpetualConfig(leverage=2)


def test_liquidation_assumption_and_bankruptcy_halt_without_fabricated_fill():
    account = USDTLinearPerpetualAccount()
    marks(account, 0)
    fill(account, "BTCUSDT", "SELL", "10", MINUTE + 1, 0, "short")
    marks(account, 2 * MINUTE, "199", "100")
    assert account.status == "LIQUIDATION_REQUIRED_HALT"
    assert len(account.trades) == 1 and account.positions["BTCUSDT"].quantity == -10
    assert account.halt_witness["maintenance_margin"] == 9.95
    with pytest.raises(RuntimeError, match="LIQUIDATION"):
        fill(account, "BTCUSDT", "BUY", "10", 2 * MINUTE + 1, MINUTE, "invent-liquidation")
    bankrupt = USDTLinearPerpetualAccount()
    marks(bankrupt, 0)
    fill(bankrupt, "BTCUSDT", "SELL", "10", MINUTE + 1, 0, "short")
    marks(bankrupt, 2 * MINUTE, "201", "100")
    assert bankrupt.status == "BANKRUPT_HALT"
    with pytest.raises(RuntimeError, match="BANKRUPT"):
        marks(bankrupt, 3 * MINUTE, "100", "100")
    restored = USDTLinearPerpetualAccount.from_snapshot(bankrupt.snapshot())
    assert restored.status == "BANKRUPT_HALT"
    # A funding liability is recorded rather than credited by a hidden loan.
    funding_loss = USDTLinearPerpetualAccount()
    marks(funding_loss, 0)
    fill(funding_loss, "BTCUSDT", "BUY", "10", MINUTE + 1, 0, "long")
    funding_loss.apply_funding("BTCUSDT", "huge-negative", 2 * MINUTE, "11", 2 * MINUTE)
    assert funding_loss.free_cash == 0 and funding_loss.unpaid_liability > 0
    assert funding_loss.status == "BANKRUPT_HALT"
    assert len(funding_loss.trades) == 1
    near(D(funding_loss.summary()["decimal_strings"]["accounting_bridge_error_USDT"]), D(0))


def test_timing_integer_steps_snapshot_rejection_and_future_prefix_invariance():
    account = USDTLinearPerpetualAccount()
    marks(account, 0)
    original = account.snapshot()
    with pytest.raises(ValueError, match="latency"):
        fill(account, "BTCUSDT", "BUY", "1", MINUTE, 0, "too-early")
    with pytest.raises(ValueError, match="availability"):
        account.execute_fill("BTCUSDT", "BUY", "1", MINUTE + 1, 0, "future-quote",
                             execution_mid_price=100, quote_available_us=MINUTE + 2)
    with pytest.raises(ValueError):
        marks(account, True)
    assert account.snapshot() == original
    partial = fill(account, "BTCUSDT", "BUY", "1.123456789", MINUTE + 1, 0, "step",
                   available_quantity="1.123456789")
    assert partial["fills"][0]["decimal_strings"]["quantity"] == "1.12345678"
    prefix = account.snapshot()
    first = USDTLinearPerpetualAccount.from_snapshot(prefix)
    second = USDTLinearPerpetualAccount.from_snapshot(prefix)
    marks(first, 2 * MINUTE, "101", "100")
    marks(second, 2 * MINUTE, "101", "100")
    first.apply_funding("BTCUSDT", "past", 2 * MINUTE, ".001", 2 * MINUTE)
    second.apply_funding("BTCUSDT", "past", 2 * MINUTE, ".001", 2 * MINUTE)
    prior_first, prior_second = deepcopy(first.trades + first.funding), deepcopy(second.trades + second.funding)
    assert prior_first == prior_second
    marks(first, 3 * MINUTE, "102", "100")
    marks(second, 3 * MINUTE, "103", "100")
    first.apply_funding("BTCUSDT", "future", 3 * MINUTE, ".001", 3 * MINUTE)
    second.apply_funding("BTCUSDT", "future", 3 * MINUTE, "-.001", 3 * MINUTE)
    assert first.trades + first.funding[:1] == prior_first
    assert second.trades + second.funding[:1] == prior_second
    bad = deepcopy(prefix)
    bad["fill_requests"] = {}
    with pytest.raises(ValueError, match="fill requests missing"):
        USDTLinearPerpetualAccount.from_snapshot(bad)
    bad = deepcopy(prefix)
    bad["fill_requests"]["step"]["identity"]["execution_mid_price"] = "101"
    with pytest.raises(ValueError, match="identity mismatch"):
        USDTLinearPerpetualAccount.from_snapshot(bad)
    bad = deepcopy(prefix)
    bad["last_fill_us"] = None
    with pytest.raises(ValueError, match="last fill"):
        USDTLinearPerpetualAccount.from_snapshot(bad)
    bad = deepcopy(prefix)
    bad["positions"]["BTCUSDT"]["quantity"] = "-9"
    with pytest.raises(ValueError, match="bridge"):
        USDTLinearPerpetualAccount.from_snapshot(bad)
    bad = deepcopy(prefix)
    bad["marks"]["BTCUSDT"][0]["available_us"] = prefix["clock_us"] + 1
    with pytest.raises(ValueError, match="mark"):
        USDTLinearPerpetualAccount.from_snapshot(bad)
