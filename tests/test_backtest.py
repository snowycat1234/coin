from dataclasses import replace

import numpy as np
import polars as pl
import pytest

from quant.backtest import (
    DAY_US,
    MINUTE_US,
    BacktestConfig,
    baseline_targets,
    run_backtest,
)
from quant.metrics import block_bootstrap_mean_ci, daily_metrics

START = 1_640_995_200_000_000  # 2022-01-01 UTC


def fixture_data(minutes=120, symbols=("BTCUSDT",)):
    frames = []
    for symbol in symbols:
        times = np.arange(minutes, dtype=np.int64) * MINUTE_US + START
        frames.append(pl.DataFrame({
            "symbol": [symbol] * minutes, "open_us": times,
            "close_us": times + MINUTE_US, "available_us": times + MINUTE_US,
            "open": np.full(minutes, 100.0), "close": np.full(minutes, 100.0),
            "quote_volume": np.full(minutes, 10_000_000.0),
        }))
    minute = pl.concat(frames)
    bars = minute.filter((pl.col("open_us") - START) % (15 * MINUTE_US) == 0).select(
        "symbol", "open_us", "close",
        (pl.col("open_us") + 15 * MINUTE_US).alias("close_us"),
        (pl.col("open_us") + 15 * MINUTE_US).alias("available_us"),
        pl.lit("15m").alias("interval"),
    )
    return bars, minute


def target_rows(*items):
    return pl.DataFrame([
        {"available_us": START + minute * MINUTE_US,
         "symbol": symbol, "target_weight": weight}
        for minute, symbol, weight in items
    ], schema={"available_us": pl.Int64, "symbol": pl.String, "target_weight": pl.Float64})


def unscaled(**kwargs):
    return BacktestConfig(target_annual_vol=None, min_notional=0, lot_step_by_symbol={}, **kwargs)


def test_roundtrip_costs_are_charged_once_and_net_nav_reconciles():
    bars, minute = fixture_data()
    result = run_backtest(
        bars, minute, target_rows((15, "BTCUSDT", .30), (30, "BTCUSDT", 0)), unscaled(),
    )
    assert result.summary["trade_count"] == 2
    assert result.summary["round_trip_count"] == 1
    assert result.trades["fee"][0] == pytest.approx(result.trades["notional"][0] * .001)
    assert result.trades["fill_price"].to_list() == pytest.approx([100.05, 99.95])
    assert result.summary["cost_rate_one_way_bps"] == pytest.approx(15)
    assert result.summary["final_nav"] == pytest.approx(
        10_000 - result.summary["fees"] - result.summary["execution_costs"],
    )
    assert result.round_trips["pnl"][0] == pytest.approx(result.summary["final_nav"] - 10_000)
    assert result.daily_nav["turnover"][0] == pytest.approx(
        result.trades["notional"].sum() / 10_000,
    )


def test_execution_is_after_close_and_uses_no_future_price_or_volume():
    bars, minute = fixture_data()
    targets = target_rows((15, "BTCUSDT", .30))
    first = run_backtest(bars, minute, targets, unscaled())
    assert first.trades["execution_us"][0] == START + 15 * MINUTE_US + 1
    assert first.trades["execution_us"][0] > targets["available_us"][0]
    changed = minute.with_columns(
        pl.when(pl.col("open_us") >= START + 16 * MINUTE_US)
        .then(1_000).otherwise(pl.col("open")).alias("open"),
        pl.when(pl.col("open_us") >= START + 15 * MINUTE_US)
        .then(0).otherwise(pl.col("quote_volume")).alias("quote_volume"),
    )
    second = run_backtest(bars, changed, targets, unscaled())
    assert first.trades.row(0) == second.trades.row(0)
    invalid_bars = bars.with_columns((pl.col("close_us") - 1).alias("available_us"))
    with pytest.raises(ValueError, match="exclusive close"):
        run_backtest(invalid_bars, minute, targets, unscaled())


def test_minute_delay_uses_later_proxy_price():
    bars, minute = fixture_data()
    minute = minute.with_columns(
        pl.when(pl.col("open_us") == START + 16 * MINUTE_US)
        .then(200).otherwise(pl.col("open")).alias("open"),
    )
    result = run_backtest(
        bars, minute, target_rows((15, "BTCUSDT", .30)), unscaled(latency_minutes=1),
    )
    assert result.trades["execution_us"][0] == START + 16 * MINUTE_US + 1
    assert result.trades["fill_price"][0] == pytest.approx(200.1)


def test_capacity_uses_previous_minute_not_current_and_expires_partial_orders():
    bars, minute = fixture_data()
    minute = minute.with_columns(
        pl.when(pl.col("open_us") == START + 14 * MINUTE_US)
        .then(10_000).otherwise(0).alias("quote_volume"),
    )
    result = run_backtest(bars, minute, target_rows((15, "BTCUSDT", .30)), unscaled())
    assert result.trades["notional"][0] == pytest.approx(10)
    assert result.trades["capacity"][0] == pytest.approx(10)
    assert result.orders["status"].to_list() == [
        "partial", "capacity_zero", "capacity_zero", "capacity_zero", "capacity_zero", "expired",
    ]
    assert result.summary["capacity_limits"] == 5
    assert result.summary["expired_orders"] == 1


def test_gap_in_either_coin_freezes_all_new_orders_and_then_recovers():
    bars, minute = fixture_data(symbols=("BTCUSDT", "ETHUSDT"))
    minute = minute.filter(~(
        (pl.col("symbol") == "ETHUSDT")
        & (pl.col("open_us") == START + 14 * MINUTE_US)
    ))
    targets = target_rows((15, "BTCUSDT", .30), (15, "ETHUSDT", .30))
    result = run_backtest(bars, minute, targets, unscaled())
    assert result.summary["gap_blocks"] == 2
    assert result.trades["execution_us"].min() == START + 16 * MINUTE_US + 1
    assert result.orders["status"].to_list()[:2] == ["gap_frozen", "gap_frozen"]


def test_whole_day_gap_preserves_positions_and_recognizes_recovery_pnl():
    bars, minute = fixture_data(minutes=3 * 1440)
    minute = minute.with_columns(
        pl.when(pl.col("open_us") >= START + 2 * DAY_US)
        .then(50).otherwise(pl.col("open")).alias("open"),
        pl.when(pl.col("open_us") >= START + 2 * DAY_US)
        .then(50).otherwise(pl.col("close")).alias("close"),
    )
    isolated = (pl.col("open_us") >= START + DAY_US) & (
        pl.col("open_us") < START + 2 * DAY_US
    )
    targets = target_rows((15, "BTCUSDT", .3))
    gap = run_backtest(bars.filter(~isolated), minute.filter(~isolated), targets, unscaled())
    quantity = gap.summary["open_positions"]["BTCUSDT"]
    assert quantity == pytest.approx(gap.trades["quantity"][0])
    assert gap.daily_nav["nav"][1] == gap.daily_nav["nav"][0]
    assert gap.daily_nav["stale_prices"].to_list() == [False, True, False]
    assert gap.daily_nav["stale_exposure"].to_list() == [False, True, False]
    assert gap.daily_nav["nav"][2] == pytest.approx(gap.daily_nav["nav"][0] - quantity * 50)
    assert gap.summary["gap_blocks"] == 0  # no orders attempted during the isolated day
    assert gap.summary["valuation_gap_days"] == 1
    assert gap.summary["exposed_valuation_gap_days"] == 1
    assert gap.summary["daily_risk_observable"] is False
    # A hidden low price is possible inside the gap: observed MDD cannot certify the true path.
    hypothetical = minute.with_columns(
        pl.when(isolated).then(10).otherwise(pl.col("close")).alias("close"),
    )
    complete = run_backtest(bars, hypothetical, targets, unscaled())
    assert complete.summary["max_drawdown"] > gap.summary["max_drawdown"]
    assert complete.summary["final_nav"] == pytest.approx(gap.summary["final_nav"])
    cash = run_backtest(bars.filter(~isolated), minute.filter(~isolated),
                        baseline_targets(bars.filter(~isolated), "B0"))
    assert cash.summary["valuation_gap_days"] == 1
    assert cash.summary["exposed_valuation_gap_days"] == 0
    assert cash.summary["daily_risk_observable"] is True


def test_caps_and_cash_are_checked_after_all_transaction_costs():
    bars, minute = fixture_data(symbols=("BTCUSDT", "ETHUSDT"))
    result = run_backtest(
        bars, minute, target_rows((15, "BTCUSDT", 10), (15, "ETHUSDT", 10)), unscaled(),
    )
    assert result.trades["cash_after"].min() >= 0
    assert result.summary["max_observed_weight"] <= .30 + 1e-10
    assert result.summary["max_observed_gross"] <= .60 + 1e-10
    final_nav = result.summary["final_nav"]
    for quantity in result.summary["open_positions"].values():
        assert quantity * 100 / final_nav <= .30 + 1e-10
    with pytest.raises(ValueError, match="frozen"):
        BacktestConfig(max_gross=1.0)


def test_volatility_sizing_is_causal_and_history_shortage_stays_cash():
    bars, minute = fixture_data(minutes=36 * 1440)
    minute = minute.with_columns(
        (((pl.col("open_us") - START) // DAY_US) % 2 * 30 + 100).alias("open"),
        (((pl.col("open_us") - START) // DAY_US) % 2 * 30 + 100).alias("close"),
    )
    # Existing availability timestamps remain valid but daily minute prices supply risk.
    targets = target_rows((15, "BTCUSDT", .30), (31 * 1440, "BTCUSDT", .30))
    first = run_backtest(bars, minute, targets)
    assert first.summary["warmup_signals"] == 1
    assert first.trades["asset_weight_after"][0] < .10
    modified = minute.with_columns(
        pl.when(pl.col("open_us") >= START + 32 * DAY_US)
        .then(1_000_000).otherwise(pl.col("close")).alias("close"),
    )
    second = run_backtest(bars, modified, targets)
    assert first.trades.equals(second.trades)


def test_same_inputs_replay_exactly_ten_times():
    bars, minute = fixture_data(symbols=("BTCUSDT", "ETHUSDT"))
    targets = target_rows(
        (15, "BTCUSDT", .3), (15, "ETHUSDT", .3),
        (30, "BTCUSDT", 0), (30, "ETHUSDT", 0),
    )
    expected = run_backtest(bars, minute, targets, unscaled())
    for _ in range(9):
        actual = run_backtest(bars, minute, targets, unscaled())
        assert actual.daily_nav.equals(expected.daily_nav)
        assert actual.orders.equals(expected.orders)
        assert actual.trades.equals(expected.trades)
        assert actual.round_trips.equals(expected.round_trips)
        assert actual.summary == expected.summary


def test_cost_stresses_and_cash_baseline():
    bars, minute = fixture_data()
    targets = target_rows((15, "BTCUSDT", .3), (30, "BTCUSDT", 0))
    base = unscaled()
    results = [run_backtest(bars, minute, targets, config) for config in (
        base, replace(base, fee_multiplier=2), replace(base, slippage_multiplier=2),
        replace(base, fee_multiplier=2, slippage_multiplier=2),
    )]
    assert [r.summary["cost_rate_one_way_bps"] for r in results] == pytest.approx([15, 25, 19, 29])
    assert results[1].summary["final_nav"] < results[0].summary["final_nav"]
    assert results[2].summary["final_nav"] < results[0].summary["final_nav"]
    cash = run_backtest(bars, minute, baseline_targets(bars, "B0"))
    assert cash.summary["total_return"] == 0
    assert cash.summary["fees"] == 0
    assert cash.summary["trade_count"] == 0
    with pytest.raises(ValueError, match="1h"):
        baseline_targets(bars, "B2")


def test_b2_targets_do_not_change_when_future_bars_are_appended():
    bars, minute = fixture_data(minutes=200 * 60)
    hourly = bars.filter((pl.col("open_us") - START) % (60 * MINUTE_US) == 0).with_columns(
        (pl.col("open_us") + 60 * MINUTE_US).alias("close_us"),
        (pl.col("open_us") + 60 * MINUTE_US).alias("available_us"),
        pl.lit("1h").alias("interval"),
        ((pl.col("open_us") - START) / MINUTE_US + 100).alias("close"),
    )
    earlier = baseline_targets(hourly.head(120), "B2")
    full = baseline_targets(hourly, "B2")
    assert full.head(120).equals(earlier)
    assert earlier["target_weight"].head(99).sum() == 0
    assert earlier["target_weight"][99] == .30
    assert baseline_targets(hourly, "B1").height == 1
    with_gap = hourly.filter(pl.col("open_us") != START + 110 * 60 * MINUTE_US)
    reset = baseline_targets(with_gap, "B2")
    assert reset.filter(pl.col("available_us") > START + 111 * 60 * MINUTE_US)[
        "target_weight"
    ].sum() == 0


def test_liquidation_costs_and_cutoff_do_not_assume_free_or_unlimited_fills():
    bars, minute = fixture_data()
    targets = target_rows((15, "BTCUSDT", .30), (30, "BTCUSDT", 0))
    result = run_backtest(
        bars, minute, targets,
        unscaled(end_us=START + 30 * MINUTE_US, liquidate_at_end=True),
    )
    assert result.summary["round_trip_count"] == 1
    assert result.trades["execution_us"][-1] == START + 29 * MINUTE_US + 1
    assert result.summary["open_positions"]["BTCUSDT"] == 0
    illiquid = minute.with_columns(
        pl.when(pl.col("open_us") == START + 28 * MINUTE_US)
        .then(0).otherwise(pl.col("quote_volume")).alias("quote_volume"),
    )
    blocked = run_backtest(
        bars, illiquid, targets,
        unscaled(end_us=START + 30 * MINUTE_US, liquidate_at_end=True),
    )
    assert blocked.summary["round_trip_count"] == 0
    assert blocked.summary["open_positions"]["BTCUSDT"] > 0
    assert blocked.summary["trade_count"] == 1


def test_lot_steps_minimum_notional_and_dust_do_not_create_fake_roundtrips():
    bars, minute = fixture_data()
    filtered = BacktestConfig(target_annual_vol=None)
    result = run_backtest(bars, minute, target_rows((15, "BTCUSDT", .3)), filtered)
    quantity = result.trades["quantity"][0]
    assert quantity / .00001 == pytest.approx(round(quantity / .00001))
    assert result.trades["notional"][0] >= 10
    tiny = run_backtest(bars, minute, target_rows((15, "BTCUSDT", .0001)), filtered)
    assert tiny.trades.height == 0
    assert tiny.orders["status"].to_list() == ["below_min_notional"]
    cheap_after_entry = minute.with_columns(
        pl.when(pl.col("open_us") >= START + 30 * MINUTE_US)
        .then(10).otherwise(pl.col("open")).alias("open"),
        pl.when(pl.col("open_us") >= START + 30 * MINUTE_US)
        .then(10).otherwise(pl.col("close")).alias("close"),
    )
    dust = run_backtest(
        bars, cheap_after_entry, target_rows((15, "BTCUSDT", .3), (30, "BTCUSDT", 0)),
        replace(filtered, initial_cash=100),
    )
    assert "dust_unexecuted" in dust.orders["status"].to_list()
    assert dust.summary["round_trip_count"] == 0
    assert dust.summary["open_positions"]["BTCUSDT"] > 0


def test_daily_metrics_use_365_and_include_initial_cash_drawdown():
    frame = pl.DataFrame({"nav": [90.0, 99.0], "fees": [0., 0.],
                          "execution_costs": [0., 0.], "turnover": [0., 0.]})
    result = daily_metrics(frame, 100)
    assert result["max_drawdown"] == pytest.approx(.1)
    assert result["annual_volatility"] == pytest.approx(np.std([-.1, .1], ddof=1) * np.sqrt(365))
    assert result["annual_return"] == pytest.approx(.99 ** (365 / 2) - 1)
    assert block_bootstrap_mean_ci(np.array([.01, .02, -.01])) == block_bootstrap_mean_ci(
        np.array([.01, .02, -.01]),
    )
