"""Synthetic accounting and causal-source invariants, no market IO."""
from __future__ import annotations

import numpy as np
import polars as pl
import pytest

from scripts.investment import compare_simple_strategies as common
from scripts.investment import bulk_fixed_targets as bulk


@pytest.fixture(scope="module")
def history():
    start = common.day_us(common.date(2025, 8, 20))
    stamps = np.arange(start - 31 * common.DAY_US, start + common.DAY_US, common.MINUTE_US, dtype=np.int64)
    frames = []
    for symbol, price in (("BTCUSDT", 10_000.), ("ETHUSDT", 1_000.)):
        frames.append(pl.DataFrame({"symbol": [symbol] * len(stamps), "open_us": stamps,
            "close_us": stamps + common.MINUTE_US, "available_us": stamps + common.MINUTE_US,
            "open": np.full(len(stamps), price), "high": np.full(len(stamps), price),
            "low": np.full(len(stamps), price), "close": np.full(len(stamps), price),
            "quote_volume": np.full(len(stamps), 10_000_000.), "valid_day": np.ones(len(stamps), dtype=bool)}))
    return common.minute_view(pl.concat(frames)), start, start + common.DAY_US


def initial_targets(start):
    return pl.DataFrame({"symbol": list(common.SYMBOLS), "available_us": [start, start],
        "target_weight": [.3, .3]}, schema=common.benchmarks.TARGET_SCHEMA)


@pytest.mark.parametrize("spread", [2, 4, 8])
def test_costs_cash_latency_and_terminal_inventory(history, spread, tmp_path):
    minutes, start, end = history
    result = common.run_backtest(minutes.select("symbol", "close_us", "available_us"), minutes,
        initial_targets(start), common.comparison_config(start, end, spread))
    assert result.summary["trade_count"] >= 4
    assert result.summary["fees"] > 0 and result.summary["execution_costs"] > 0
    assert result.summary["final_nav"] < 10_000
    inventory = common.account_inventory(result, minutes)
    assert inventory.height == 1440
    assert abs(inventory["nav"][-1] - 10_000 + result.summary["fees"] + result.summary["execution_costs"]) < 1e-6
    assert result.trades["execution_us"].min() == start + common.MINUTE_US + 1
    ledger = common.write_ledger(tmp_path / "ledger", result, minutes)
    assert ledger["summary"]["same_quantity_gross_minus_cost_equals_net"]
    assert ledger["summary"]["terminal_marked_notional"] >= 0
    assert not ledger["summary"]["candidate_qualification_allowed"]
    assert len(ledger["artifacts"]) == 6


def test_cash_and_future_perturbation(history):
    minutes, start, end = history
    bars = minutes.select("symbol", "close_us", "available_us")
    calendar = np.arange(start, start + 20 * common.MINUTE_US, common.MINUTE_US, dtype=np.int64)
    closes = minutes.select("symbol", "close_us", "available_us", "close")
    plan = common.benchmarks.fixed_targets("CASH", closes, calendar)
    result = common.run_backtest(bars, minutes, plan.targets, common.comparison_config(start, end, 2))
    assert result.summary["final_nav"] == 10_000 and result.trades.is_empty()
    common.account_inventory(result, minutes)
    # Even large later execution-source changes cannot change the entry fill.
    later = pl.col("open_us") >= start + 10 * common.MINUTE_US
    mutated = minutes.with_columns([pl.when(later).then(pl.col(name) * 3).otherwise(pl.col(name)).alias(name)
        for name in ("open", "high", "low", "close", "quote_volume")])
    a = common.run_backtest(bars, minutes, initial_targets(start), common.comparison_config(start, end, 2))
    b = common.run_backtest(bars, mutated, initial_targets(start), common.comparison_config(start, end, 2))
    assert a.trades.filter(pl.col("execution_us") < start + 10 * common.MINUTE_US).equals(
        b.trades.filter(pl.col("execution_us") < start + 10 * common.MINUTE_US))
    # Test a fixed signal rule, not only hand-built engine targets.
    cutoff = start + 10 * common.MINUTE_US
    perturbed_closes = closes.with_columns(pl.when(pl.col("close_us") > cutoff)
        .then(pl.col("close") * 3).otherwise(pl.col("close")).alias("close"))
    original = common.benchmarks.fixed_targets("FIXED_TREND", closes, calendar)
    changed = common.benchmarks.fixed_targets("FIXED_TREND", perturbed_closes, calendar)
    assert original.calendar_ledger.filter(pl.col("decision_us") <= cutoff).equals(
        changed.calendar_ledger.filter(pl.col("decision_us") <= cutoff))


def test_complete_calendar_no_future_filter_or_missing_zero(history):
    minutes, start, end = history
    assert common.complete_fold(minutes, start - 31 * common.DAY_US, start, end)
    bad = minutes.with_columns(pl.when((pl.col("open_us") == start) & (pl.col("symbol") == "BTCUSDT"))
        .then(None).otherwise(pl.col("close")).alias("close"))
    bad = common.minute_view(bad.drop("minute_valid", "missing_reason"))
    assert bad.height == minutes.height and bad.filter(~pl.col("minute_valid")).height == 1
    assert not common.complete_fold(bad, start - 31 * common.DAY_US, start, end)
    assert not common.complete_fold(minutes.filter(~((pl.col("open_us") == start) & (pl.col("symbol") == "BTCUSDT"))),
        start - 31 * common.DAY_US, start, end)


def test_source_date_rejection_before_open():
    # No actual locked path exists/opens in this test.
    with pytest.raises(ValueError, match="no locked IO"):
        common.allowed_source_path({"symbol": "BTCUSDT", "month": "2026-03", "normalized_path": "/never/open"})
    with pytest.raises(ValueError, match="Exact explicit"):
        common.allowed_source_path({"symbol": "BTCUSDT", "month": "2025-07", "normalized_path": "/never/open"})


def test_bulk_exact_fixed_intents_and_canonical_reasons():
    start = common.day_us(common.date(2025, 8, 20))
    stamps = np.arange(start - 300 * common.MINUTE_US, start + 96 * common.MINUTE_US, common.MINUTE_US, dtype=np.int64)
    generator = np.random.default_rng(20261002)
    frames = []
    for symbol, base in (("BTCUSDT", 10000.), ("ETHUSDT", 1000.)):
        # Fixed finite synthetic walks cover trend/MR changes without HPO.
        prices = base * np.exp(np.cumsum(generator.normal(0., .003, len(stamps))))
        frames.append(pl.DataFrame({"symbol": [symbol] * len(stamps), "close_us": stamps,
            "available_us": stamps, "close": prices}))
    closes = pl.concat(frames)
    calendar = np.arange(start, start + 96 * common.MINUTE_US, common.MINUTE_US, dtype=np.int64)
    days = np.arange(start - 13 * common.DAY_US, start + common.DAY_US, common.DAY_US, dtype=np.int64)
    daily = pl.DataFrame({"day_end_us": days, "available_us": days,
        "gross_exposure_return": np.where(np.arange(len(days)) % 2, .03, -.025)})
    for identifier in common.STRATEGIES[:5]:
        kw = {"daily_returns": daily} if identifier == "VOL_MANAGED_BUY_AND_HOLD" else {}
        old = common.benchmarks.fixed_targets(identifier, closes, calendar, **kw)
        new = bulk.fixed_targets(identifier, closes, calendar, **kw)
        assert old.targets.equals(new.targets), identifier
        assert old.calendar_ledger.equals(new.calendar_ledger), identifier
        assert old.receipt["paired_comparison_allowed"] == new.receipt["paired_comparison_allowed"]
    cutoff = int(calendar[32])
    changed = closes.with_columns(pl.when(pl.col("close_us") > cutoff)
        .then(pl.col("close") * 12).otherwise(pl.col("close")).alias("close"))
    for identifier in ("FIXED_TREND", "FIXED_MEAN_REVERSION"):
        a, b = bulk.fixed_targets(identifier, closes, calendar), bulk.fixed_targets(identifier, changed, calendar)
        assert a.calendar_ledger.filter(pl.col("decision_us") <= cutoff).equals(b.calendar_ledger.filter(pl.col("decision_us") <= cutoff))
    with pytest.raises(ValueError, match="complete finite on-time"):
        bulk.fixed_targets("FIXED_TREND", closes.with_columns(
            pl.when(pl.col("close_us") == start).then(None).otherwise(pl.col("available_us")).alias("available_us")), calendar)


def test_public_null_guard_valid_snapshot_equivalence(history):
    import importlib.util
    from quant.paths import STATE
    from scripts.research_v8 import public_donchian_adapter as public
    minutes, start, _ = history
    invalid = minutes.with_columns(pl.when(pl.col("open_us") == start)
        .then(None).otherwise(pl.col("available_us")).alias("available_us"))
    with pytest.raises(ValueError, match="Unknown minute availability"):
        public.closed_hours(invalid)
    # Previous frozen implementation bytes come from the actual prebound run.
    path = STATE / "simple-strategy-comparison-actual-20261002-v1/source-snapshot/scripts/research_v8/public_donchian_adapter.py"
    assert common.file_sha(path) == "0cbd141f3ef60280826013137e67dfcdd59756f51b29ad77a46e7ca15d46c344"
    spec = importlib.util.spec_from_file_location("scripts.research_v8.public_donchian_before_null_guard", path)
    old = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(old)
    calendar = np.arange(start, start + 61 * common.MINUTE_US, common.MINUTE_US, dtype=np.int64)
    a, b = old.fixed_targets(minutes, calendar), public.fixed_targets(minutes, calendar)
    assert a.targets.equals(b.targets) and a.calendar_ledger.equals(b.calendar_ledger)
