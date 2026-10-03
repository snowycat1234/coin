"""Small hand-calculated tests for one configurable perpetual wallet.

No prices, source QA, historical accounts or native filter claims are used.
"""
from copy import deepcopy
from decimal import Decimal as D, localcontext

import pytest

from quant.perpetual_account import (
    InstrumentProfile, PerpetualConfig, SYMBOLS, USDTLinearPerpetualAccount as Raw,
)
from scripts.investment.perpetual_closing_exempt_account import USDTLinearPerpetualAccount as Closing

MINUTE = 60_000_000
TOL = D("1e-24")


def near(actual, expected):
    assert abs(actual - expected) <= TOL


def mark(account, stamp, prices=None):
    prices = {} if prices is None else prices
    account.update_marks(stamp, {symbol: dict(price=prices.get(symbol, "100"),
        close_us=stamp, available_us=stamp) for symbol in account.symbols})


def fill(account, symbol, side, quantity, minute, identity, *, mid="100", reduce_only=False):
    return account.execute_fill(symbol, side, quantity, minute * MINUTE + 1,
        (minute - 1) * MINUTE, identity, execution_mid_price=mid,
        quote_available_us=minute * MINUTE, reduce_only=reduce_only)


def test_default_two_assets_and_plain_closing_policy():
    """Original capital/fees/short signs remain; only small-close policy differs."""
    for account in (Raw(), Closing()):
        assert account.symbols == SYMBOLS
        assert account.config == PerpetualConfig()
        mark(account, 0)
        opened = fill(account, "BTCUSDT", "SELL", "1", 1, "short")
        assert opened["status"] == "FILLED"
        fee = D("99.92") * D(".00055")
        near(account.free_cash, D(10000) - D("99.92") - fee)
        near(account.nav(), D(10000) - D(".08") - fee)
        mark(account, 2 * MINUTE, {"BTCUSDT": "90"})
        small = fill(account, "BTCUSDT", "BUY", ".05", 2, "small-cover", mid="90", reduce_only=True)
        exempt = account.closing_min_notional_exempt
        assert bool(small["fills"]) is exempt
        assert account.positions["BTCUSDT"].quantity == (D("-.95") if exempt else D(-1))
        remaining = abs(account.positions["BTCUSDT"].quantity)
        fill(account, "BTCUSDT", "BUY", remaining, 3, "finish", mid="90", reduce_only=True)
        complete_fee = (D("99.92") + D("90.072")) * D(".00055")
        near(account.nav(), D(10000) + D(10) - D(".152") - complete_fee)
        assert account.positions["BTCUSDT"].isolated_balance == 0
        assert account.unpaid_liability == 0
        assert account.summary()["contract"]["native_filters_certified"] is False
    assert Closing.execute_fill is Raw.execute_fill
    assert Closing.snapshot is Raw.snapshot
    assert Closing.summary is Raw.summary
    with pytest.raises(ValueError, match="exemption"):
        Closing(closing_min_notional_exempt=False)


def test_three_asset_profile_order_funding_and_exact_restore_identity():
    """Different lots and a nonalphabetic order cannot alter product identity."""
    symbols = ("SOLUSDT", "BTCUSDT", "ETHUSDT")
    profiles = {"SOLUSDT": InstrumentProfile(quantity_step=".1", min_notional="50"),
        "BTCUSDT": InstrumentProfile(quantity_step=".01"),
        "ETHUSDT": InstrumentProfile(quantity_step="1")}
    account = Closing(symbols=symbols, instrument_profiles=profiles)
    assert account.symbols == symbols and tuple(account.positions) == symbols
    assert account.contract_metadata()["symbols"] == list(symbols)
    assert account.contract_metadata()["quantity_step_assumption"] == "PER_INSTRUMENT_PROFILE"
    mark(account, 0)
    with pytest.raises(TypeError):
        account.instrument_profiles["SOLUSDT"] = InstrumentProfile()
    original = deepcopy(account.snapshot())
    with pytest.raises(ValueError, match="configured"):
        fill(account, "XRPUSDT", "BUY", "1", 1, "unknown")
    assert account.snapshot() == original
    with pytest.raises(ValueError):
        Closing(symbols=("SOLUSDT", "SOLUSDT"))
    with pytest.raises(ValueError, match="ordered"):
        Closing(symbols=set(symbols))
    with pytest.raises(ValueError, match="profile keys"):
        Closing(symbols=symbols, instrument_profiles={"SOLUSDT": profiles["SOLUSDT"]})
    with pytest.raises(ValueError, match="product"):
        InstrumentProfile(settlement_asset="BTC")
    with pytest.raises(ValueError, match="profile"):
        InstrumentProfile(native_filters_certified=True)
    for symbol, side, requested, actual in (("SOLUSDT", "BUY", "1.29", "1.2"),
            ("BTCUSDT", "SELL", "2.345", "2.34"), ("ETHUSDT", "BUY", "1.99", "1")):
        receipt = fill(account, symbol, side, requested, 1, symbol)
        assert receipt["decimal_strings"]["executed_quantity"] == actual
    fee = (D("1.2") * D("100.08") + D("2.34") * D("99.92") + D("100.08")) * D(".00055")
    cost = D("4.54") * D(".08")
    near(account.nav(), D(10000) - fee - cost)
    mark(account, 2 * MINUTE, {"SOLUSDT": "110", "BTCUSDT": "90", "ETHUSDT": "105"})
    funding = [account.apply_funding(s, s + ":coupon", 2 * MINUTE, ".001", 2 * MINUTE)
               for s in symbols]
    assert [row["signed_funding_USDT"] for row in funding] == [-.12, .234, -.1]
    assert all(row["mark_close_us"] == 0 for row in funding)
    near(account.nav(), D(10000) + D("40.4") - fee - cost + D(".014"))
    # Under50 SOL close is allowed, but a new under50 opening remains refused.
    small = fill(account, "SOLUSDT", "SELL", ".1", 3, "small-SOL", mid="110", reduce_only=True)
    assert small["status"] == "FILLED" and account.positions["SOLUSDT"].quantity == D("1.1")
    snapshot = account.snapshot()
    restored = Closing.from_snapshot(snapshot, expected_symbols=symbols, expected_instrument_profiles=profiles)
    assert restored.snapshot() == snapshot
    assert fill(restored, "SOLUSDT", "SELL", ".1", 3, "small-SOL", mid="110", reduce_only=True) == small
    assert restored.snapshot() == snapshot
    assert restored.apply_funding("BTCUSDT", "BTCUSDT:coupon", 2 * MINUTE, ".001", 2 * MINUTE) == funding[1]
    assert restored.snapshot() == snapshot
    with pytest.raises(ValueError, match="order"):
        Closing.from_snapshot(snapshot, expected_symbols=tuple(reversed(symbols)))
    wrong_profiles = dict(profiles, SOLUSDT=InstrumentProfile(quantity_step=".01", min_notional="50"))
    with pytest.raises(ValueError, match="profile"):
        Closing.from_snapshot(snapshot, expected_instrument_profiles=wrong_profiles)
    for key, replacement in (("version", "usdt_linear_perpetual_account_v1"),
                             ("symbols", list(reversed(symbols))), ("closing_min_notional_exempt", False)):
        bad = deepcopy(snapshot); bad[key] = replacement
        with pytest.raises(ValueError):
            Closing.from_snapshot(bad)
    bad = deepcopy(snapshot); bad["contract"]["market_type"] = "SPOT"
    with pytest.raises(ValueError, match="identity"):
        Closing.from_snapshot(bad)
    bad = deepcopy(snapshot); bad["positions"]["XRPUSDT"] = deepcopy(bad["positions"]["SOLUSDT"])
    with pytest.raises(ValueError, match="inventory"):
        Closing.from_snapshot(bad)
    raw_profile = Raw(symbols=symbols, instrument_profiles=profiles)
    with pytest.raises(ValueError, match="version"):
        Closing.from_snapshot(raw_profile.snapshot())
    with pytest.raises(ValueError, match="version"):
        Raw.from_snapshot(snapshot)


def test_ten_assets_share_gross_wallet_and_reduce_before_increase():
    """Opposite positions share gross risk, cash and actual isolated collateral."""
    symbols = ("BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT", "BNBUSDT", "ADAUSDT",
               "DOGEUSDT", "AVAXUSDT", "LINKUSDT", "DOTUSDT")
    account = Closing(symbols=symbols)
    mark(account, 0)
    for i, symbol in enumerate(symbols):
        result = fill(account, symbol, "BUY" if i % 2 == 0 else "SELL", "5.8", 1, symbol)
        assert result["status"] == "FILLED"
    margin = D("5800")
    fee = margin * D(".00055")
    cost = D("58") * D(".08")
    near(account.free_cash, D(10000) - margin - fee)
    near(account.nav(), D(10000) - fee - cost)
    assert account.summary()["net_signed_notional"] == 0
    assert .58 < account.summary()["gross_weight"] < .6
    before = deepcopy(account.trades)
    rejected = fill(account, "BTCUSDT", "BUY", "3", 2, "global-cap")
    assert rejected["reason"] == "POST_FILL_EXPOSURE_CAP_REJECTED"
    assert account.trades == before
    # A causal execution quote can differ from valuation. The shared wallet
    # refuses allocation that a separate fresh10k account could afford.
    rejected = fill(account, "ETHUSDT", "SELL", "1", 2, "shared-wallet", mid="6000")
    assert rejected["reason"] == "INSUFFICIENT_FREE_MARGIN"
    assert account.free_cash == D(10000) - margin - fee
    fresh = Closing(symbols=symbols); mark(fresh, 0)
    assert fill(fresh, "ETHUSDT", "SELL", "1", 1, "separate", mid="6000")["status"] == "FILLED"
    prices = {symbol: "200" if i % 2 == 0 else "100" for i, symbol in enumerate(symbols)}
    mark(account, 3 * MINUTE, prices)
    assert account.status == "BOUND_BREACH_REDUCTION_REQUIRED"
    before = deepcopy(account.trades)
    rejected = fill(account, "ETHUSDT", "SELL", "1", 3, "increase-during-drift")
    assert rejected["reason"] == "BOUND_BREACH_REDUCTION_REQUIRED" and account.trades == before
    first = fill(account, "BTCUSDT", "SELL", "3", 4, "reduce-first", mid="200", reduce_only=True)
    assert first["status"] == "FILLED" and account.status == "BOUND_BREACH_REDUCTION_REQUIRED"
    second = fill(account, "SOLUSDT", "SELL", "3", 4, "reduce-second", mid="200", reduce_only=True)
    assert second["status"] == "FILLED" and account.status == "ACTIVE"
    assert fill(account, "SOLUSDT", "BUY", "1", 5, "increase-after-reductions", mid="200")["status"] == "FILLED"
    assert account.summary()["gross_weight"] <= .6
    assert max(abs(w) for w in account.summary()["asset_weights"].values()) <= .3
    near(D(account.summary()["decimal_strings"]["accounting_bridge_error_USDT"]), D(0))
    assert Closing.from_snapshot(account.snapshot(), expected_symbols=symbols).snapshot() == account.snapshot()

    # Free-wallet loss then this asset's collateral; no other isolated rescue.
    loss = Closing(symbols=("BTCUSDT", "ETHUSDT", "SOLUSDT")); mark(loss, 0)
    fill(loss, "BTCUSDT", "BUY", "1", 1, "BTC")
    fill(loss, "ETHUSDT", "BUY", "1", 1, "ETH")
    other_margin = loss.positions["ETHUSDT"].isolated_balance
    result = loss.apply_funding("BTCUSDT", "deficit", 2 * MINUTE, "100", 2 * MINUTE)
    assert result["signed_funding_USDT"] == -10000
    assert loss.free_cash == 0 and loss.unpaid_liability > 0 and loss.status == "BANKRUPT_HALT"
    assert loss.positions["BTCUSDT"].isolated_balance == 0
    assert loss.positions["ETHUSDT"].isolated_balance == other_margin
    near(D(loss.summary()["decimal_strings"]["accounting_bridge_error_USDT"]), D(0))
