"""Synthetic causal event tests only; no source QA or market economics."""
from datetime import UTC, datetime

import numpy as np
import polars as pl
import pytest

from scripts.investment import public_donchian_hybrid as hybrid

MINUTE, HOUR = hybrid.common.MINUTE_US, hybrid.public.HOUR_US
START = int(datetime(2025, 8, 1, tzinfo=UTC).timestamp() * 1_000_000)


@pytest.fixture(scope="module")
def source():
    hourly = np.full(414, 100.)
    hourly[400:406] = [103., 103., 90., 106., 80., 107.]
    hourly[406:] = [108., 108., 109., 109., 110., 110., 111., 111.]
    prices = np.repeat(hourly, 60)
    stamps = START + np.arange(len(prices), dtype=np.int64) * MINUTE
    return pl.concat([pl.DataFrame({"symbol": [symbol] * len(prices), "open_us": stamps,
        "high": prices + .1, "low": prices - .1, "close": prices,
        "available_us": stamps + MINUTE}) for symbol in hybrid.common.SYMBOLS])


def calendar():
    return START + np.arange(400 * 60, 414 * 60, dtype=np.int64) * MINUTE


def btc(plan):
    return plan.calendar_ledger.filter(pl.col("symbol") == "BTCUSDT")


def weight(plan, hour):
    return btc(plan).filter(pl.col("decision_us") == START + hour * HOUR)["target_weight"][0]


def test_pinned_hooks_entry_2h_exit_1h_and_next_event_eligibility(source):
    plan = hybrid.fixed_targets(source, calendar())
    assert plan.strategy_id == hybrid.STRATEGY_ID
    assert plan.receipt["paired_comparison_allowed"] and not plan.receipt["warmup_failed"]
    assert plan.receipt["signal_hooks_reused_unmodified"] and plan.receipt["model_fits"] == 0
    assert plan.receipt["source_hashes"]["scripts/research_v8/public_donchian_adapter.py"] == hybrid.BASE_ADAPTER_SHA256
    for hour, expected in ((400, 0.), (401, 0.), (402, .3), (403, 0.), (404, .3), (405, 0.), (406, .3)):
        assert weight(plan, hour) == expected
    assert set(plan.targets["target_weight"].to_list()) == {0., .3}
    assert btc(plan)["target_weight"][-1] == 0.
    assert btc(plan)["reason"][-1] == "COMMON_TERMINAL_EXIT_INTENT_NEEDS_FEASIBLE_FILL"
    assert not plan.receipt["costs_paid"] and not plan.receipt["candidate_qualification_allowed"]


def test_same_stamp_exit_has_priority_no_reentry_or_hidden_cooldown(source, monkeypatch):
    # Defensive conflict control flow is synthetic: consistent real price
    # channels need not make both strict predicates true at the same close.
    entries = []
    class Hooks:
        def should_long(self):
            entries.append(int(self.candles[-1, 0]) * 1000)
            return True
        def filters(self):
            return [lambda: True]
        def update_position(self):
            close = int(self.candles[-1, 0]) * 1000
            if close == START + 402 * HOUR:
                self.liquidate()
    monkeypatch.setattr(hybrid.public, "_load_public_hooks", lambda: Hooks)
    plan = hybrid.fixed_targets(source, calendar())
    assert weight(plan, 400) == .3 and weight(plan, 401) == .3
    assert weight(plan, 402) == 0. and weight(plan, 403) == 0.
    assert weight(plan, 404) == .3
    assert START + 402 * HOUR not in entries
    assert btc(plan).filter(pl.col("decision_us") == START + 402 * HOUR)["reason"][0] == "HYBRID_PUBLIC_1H_EXIT_NO_SAME_STAMP_REENTRY"


def test_future_raw_minutes_never_change_earlier_targets(source):
    boundary = START + 406 * HOUR
    future = source.with_columns([pl.when(pl.col("open_us") >= boundary)
        .then(pl.col(field) * 10).otherwise(pl.col(field)).alias(field) for field in ("high", "low", "close")])
    base, altered = hybrid.fixed_targets(source, calendar()), hybrid.fixed_targets(future, calendar())
    assert base.calendar_ledger.filter(pl.col("decision_us") <= boundary).equals(
        altered.calendar_ledger.filter(pl.col("decision_us") <= boundary))
    # Entirely unfinished/future rows past the final signal decision are not
    # aggregated, even when their prices would fail finite OHLC validation.
    unread = source.with_columns([pl.when(pl.col("open_us") >= int(calendar()[-1]))
        .then(float("nan")).otherwise(pl.col(field)).alias(field) for field in ("high", "low", "close")])
    assert base.calendar_ledger.equals(hybrid.fixed_targets(unread, calendar()).calendar_ledger)


@pytest.mark.parametrize("failure", ["missing", "delayed", "invalid"])
def test_future_source_failure_rejects_fold_but_retains_causal_prefix(source, failure):
    boundary = START + 406 * HOUR
    selected = (pl.col("symbol") == "BTCUSDT") & (pl.col("open_us") == boundary + MINUTE)
    if failure == "missing":
        bad = source.filter(~selected)
    elif failure == "delayed":
        bad = source.with_columns(pl.when(selected).then(START + 420 * HOUR)
            .otherwise(pl.col("available_us")).alias("available_us"))
    else:
        bad = source.with_columns((~selected).alias("minute_valid"))
    base, rejected = hybrid.fixed_targets(source, calendar()), hybrid.fixed_targets(bad, calendar())
    assert rejected.receipt["warmup_failed"] and not rejected.receipt["paired_comparison_allowed"]
    assert rejected.receipt["status"] == "NOT_EVALUABLE_PAIRED_FOLD_WARMUP"
    assert rejected.calendar_ledger.filter(pl.col("decision_us") <= boundary).equals(
        base.calendar_ledger.filter(pl.col("decision_us") <= boundary))
    assert weight(rejected, 402) == .3  # A later failure must not erase earlier intents.
    assert weight(rejected, 407) == 0.
    assert rejected.receipt["executed_orders"] == 0 and rejected.receipt["economic_metrics"] is None


def test_initial_warmup_and_unknown_availability_are_not_filled(source):
    missing = source.filter(~((pl.col("symbol") == "BTCUSDT") &
        (pl.col("open_us") == START + 399 * HOUR + MINUTE)))
    assert not hybrid.fixed_targets(missing, calendar()).receipt["paired_comparison_allowed"]
    delayed = source.with_columns(pl.when(pl.col("open_us") == START + 399 * HOUR + MINUTE)
        .then(START + 400 * HOUR + MINUTE).otherwise(pl.col("available_us")).alias("available_us"))
    assert not hybrid.fixed_targets(delayed, calendar()).receipt["paired_comparison_allowed"]
    unknown = source.with_columns(pl.when(pl.col("open_us") == START + 399 * HOUR + MINUTE)
        .then(None).otherwise(pl.col("available_us")).alias("available_us"))
    with pytest.raises(ValueError, match="Unknown minute availability"):
        hybrid.fixed_targets(unknown, calendar())
