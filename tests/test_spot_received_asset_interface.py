"""Direct tests of active Spot fee settlement, with hand-derived reference cash."""
from dataclasses import replace

import numpy as np
import polars as pl
import pytest

from quant.backtest import BacktestConfig, MINUTE_US, run_backtest

START = 1_640_995_200_000_000


def fixture(symbols=("BTCUSDT",), volume=10_000_000.0):
    minutes = pl.concat([
        pl.DataFrame({"symbol": [symbol] * 60,
            "open_us": np.arange(60, dtype=np.int64) * MINUTE_US + START,
            "open": [100.0] * 60, "close": [100.0] * 60,
            "quote_volume": [volume] * 60}) for symbol in symbols
    ])
    bars = pl.DataFrame([
        {"symbol": symbol, "available_us": START + t * MINUTE_US,
         "close_us": START + t * MINUTE_US}
        for t in (15, 30, 45) for symbol in symbols
    ])
    return bars, minutes


def targets(*rows):
    return pl.DataFrame([{"available_us": START + t * MINUTE_US,
        "symbol": s, "target_weight": w} for t, s, w in rows])


def config(**changes):
    return BacktestConfig(target_annual_vol=None, min_notional=0,
        lot_step_by_symbol={}, fee_settlement="RECEIVED_ASSET", **changes)


def assert_reference(result, rate=.001, mode="RECEIVED_ASSET"):
    cash = 10_000.0
    inventory = {s: 0.0 for s in result.summary["open_positions"]}
    for row in result.trades.iter_rows(named=True):
        q, p, mid = row.get("gross_quantity", row["quantity"]), row["fill_price"], row["mid_price"]
        buy = row["side"] == "buy"
        if mode == "RECEIVED_ASSET" and buy:
            base_change, cash_change = q * (1 - rate), -q * p
            fee_asset, fee_amount, fee_value = row["symbol"][:-4], q * rate, q * rate * mid
        else:
            base_change = q if buy else -q
            cash_change = -q * p * (1 + rate) if buy else q * p * (1 - rate)
            fee_asset, fee_amount, fee_value = "USDT", q * p * rate, q * p * rate
        if mode == "RECEIVED_ASSET":
            assert row["position_delta"] == pytest.approx(base_change, abs=1e-10)
            assert row["cash_delta"] == pytest.approx(cash_change, abs=1e-8)
            assert row["fee_asset"] == fee_asset
            assert row["fee_amount"] == pytest.approx(fee_amount)
            assert row["fee_USDT_mid"] == pytest.approx(fee_value)
        assert row["fee"] == pytest.approx(fee_value)
        inventory[row["symbol"]] += base_change
        cash += cash_change
        assert inventory[row["symbol"]] >= -1e-10
        assert cash >= -1e-8
        assert row["cash_after"] == pytest.approx(cash, abs=1e-8)
        assert row["execution_us"] > row["signal_us"]
        assert row["notional"] <= row["capacity"] + 1e-8
    assert result.summary["open_positions"] == pytest.approx(inventory, abs=1e-10)
    assert result.summary["final_nav"] == pytest.approx(
        cash + sum(inventory.values()) * 100, abs=1e-8)


def test_received_base_buy_and_quote_sell_are_charged_once():
    bars, minutes = fixture()
    result = run_backtest(bars, minutes,
        targets((15, "BTCUSDT", .3), (30, "BTCUSDT", 0)), config())
    assert result.trades.height == 2
    assert result.trades["side"].to_list() == ["buy", "sell"]
    assert_reference(result)
    assert result.summary["final_nav"] == pytest.approx(
        10_000 - result.summary["fees"] - result.summary["execution_costs"], abs=1e-8)
    assert result.round_trips["pnl"][0] == pytest.approx(result.summary["final_nav"] - 10_000)


def test_partial_fills_charge_actual_gross_and_expire_without_extra_fee():
    bars, minutes = fixture(volume=10_000)
    result = run_backtest(bars, minutes, targets((15, "BTCUSDT", .3)), config())
    assert result.trades.height == 5
    assert result.orders["status"].to_list() == ["partial"] * 5 + ["expired"]
    assert result.trades["notional"].to_list() == pytest.approx([10] * 5)
    assert_reference(result)


def test_fee_dust_cannot_be_borrowed_or_silently_removed():
    bars, minutes = fixture()
    cfg = replace(config(), lot_step_by_symbol={"BTCUSDT": .01}, min_notional=10)
    result = run_backtest(bars, minutes,
        targets((15, "BTCUSDT", .3), (30, "BTCUSDT", 0), (45, "BTCUSDT", -.3)), cfg)
    assert_reference(result)
    remainder = result.summary["open_positions"]["BTCUSDT"]
    assert 0 < remainder < .01
    assert "dust_unexecuted" in result.orders["status"].to_list()


def test_two_coins_share_cash_and_post_fee_caps():
    bars, minutes = fixture(symbols=("BTCUSDT", "ETHUSDT"))
    result = run_backtest(bars, minutes,
        targets((15, "BTCUSDT", .3), (15, "ETHUSDT", .3)), config())
    assert_reference(result)
    assert result.summary["max_observed_weight"] <= .3 + 1e-9
    assert result.summary["max_observed_gross"] <= .6 + 1e-9


def test_current_capacity_and_future_prices_do_not_change_first_fill():
    bars, minutes = fixture()
    target = targets((15, "BTCUSDT", .3))
    original = run_backtest(bars, minutes, target, config())
    changed = minutes.with_columns(
        pl.when(pl.col("open_us") >= START + 17 * MINUTE_US)
        .then(500).otherwise(pl.col("open")).alias("open"),
        pl.when(pl.col("open_us") >= START + 16 * MINUTE_US)
        .then(0).otherwise(pl.col("quote_volume")).alias("quote_volume"))
    altered = run_backtest(bars, changed, target, config())
    assert original.trades.row(0, named=True) == altered.trades.row(0, named=True)
    assert original.trades["execution_us"][0] == START + 16 * MINUTE_US + 1
    assert original.trades["capacity_open_us"][0] == START + 15 * MINUTE_US


def test_default_quote_mode_remains_explicit_quote_semantics():
    bars, minutes = fixture()
    target = targets((15, "BTCUSDT", .3), (30, "BTCUSDT", 0))
    default = BacktestConfig(target_annual_vol=None, min_notional=0, lot_step_by_symbol={})
    implicit = run_backtest(bars, minutes, target, default)
    explicit = run_backtest(bars, minutes, target, replace(default, fee_settlement="QUOTE"))
    assert implicit.trades.equals(explicit.trades)
    assert implicit.daily_nav.equals(explicit.daily_nav)
    assert_reference(implicit, mode="QUOTE")


def test_terminal_five_attempt_budget_uses_past_capacity_and_retains_inventory():
    bars, minutes = fixture()
    # Entry has ample past-minute capacity, but only 10USDT capacity per exit.
    minutes = minutes.with_columns(pl.when(pl.col("open_us") >= START + 54 * MINUTE_US)
        .then(10_000).otherwise(pl.col("quote_volume")).alias("quote_volume"))
    result = run_backtest(bars, minutes, targets((15, "BTCUSDT", .3)),
        config(liquidate_at_end=True, terminal_exit_minutes=5))
    exits = result.trades.filter(pl.col("side") == "sell")
    assert exits["execution_us"].to_list() == [START + t * MINUTE_US + 1 for t in range(55, 60)]
    assert exits["notional"].to_list() == pytest.approx([10] * 5)
    assert result.summary["open_positions"]["BTCUSDT"] > 0
    assert_reference(result)


def test_terminal_exit_budget_cannot_extend_order_lifetime():
    with pytest.raises(ValueError):
        config(terminal_exit_minutes=6, max_order_wait_minutes=5)
    with pytest.raises(ValueError):
        config(terminal_exit_minutes=0)
