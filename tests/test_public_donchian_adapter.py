from datetime import UTC, datetime

import numpy as np
import polars as pl

from scripts.research_v8 import public_donchian_adapter as public

HOUR = public.HOUR_US
MINUTE = public.common.MINUTE_US
START = int(datetime(2025, 8, 1, tzinfo=UTC).timestamp() * 1_000_000)


def synthetic_minutes():
    count = 212 * 60
    stamps = START + np.arange(count, dtype=np.int64) * MINUTE
    # Quiet warmup, followed by entry/hold/exit/re-entry: assert actual reused
    # public hooks, rather than a parallel hand-written strategy implementation.
    hourly = np.full(212, 100.)
    hourly[200:203] = [103., 104., 105.]
    hourly[203:206] = [90., 89., 90.]
    hourly[206:] = [106., 107., 108., 109., 110., 111.]
    values = np.repeat(hourly, 60)
    rows = [pl.DataFrame({"symbol": [symbol] * count, "open_us": stamps,
        "high": values + .1, "low": values - .1, "close": values,
        "available_us": stamps + MINUTE}) for symbol in public.common.SYMBOLS]
    return pl.concat(rows)


def test_public_hooks_entry_hold_exit_and_original_prior_channel():
    minutes = synthetic_minutes()
    calendar = START + np.arange(200 * 60, 212 * 60, dtype=np.int64) * MINUTE
    plan = public.fixed_targets(minutes, calendar)
    assert not plan.receipt["warmup_failed"]
    assert plan.receipt["signal_hooks_reused_unmodified"]
    btc = plan.calendar_ledger.filter(pl.col("symbol") == "BTCUSDT")
    for hour, expected in ((200, 0.), (201, .3), (203, .3), (204, 0.), (206, 0.), (207, .3)):
        decision = START + hour * HOUR
        assert btc.filter(pl.col("decision_us") == decision)["target_weight"][0] == expected
    assert plan.targets.filter(pl.col("target_weight") > .3).is_empty()
    assert btc["target_weight"][-1] == 0.
    Rules = public._load_public_hooks()
    context = Rules()
    context.candles = np.array([[i, 0, 100, 101 + i, 99 - i, 0] for i in range(21)], dtype=float)
    assert context.donchian.upperband == 120.  # excludes current high 121
    assert context.donchian.lowerband == 80.


def test_future_ohlc_perturbation_preserves_all_earlier_targets():
    minutes = synthetic_minutes()
    calendar = START + np.arange(200 * 60, 212 * 60, dtype=np.int64) * MINUTE
    boundary = START + 207 * HOUR
    perturbed = minutes.with_columns([
        pl.when(pl.col("open_us") >= boundary).then(pl.col(key) * 10).otherwise(pl.col(key)).alias(key)
        for key in ("high", "low", "close")])
    before = public.fixed_targets(minutes, calendar).calendar_ledger.filter(pl.col("decision_us") <= boundary)
    after = public.fixed_targets(perturbed, calendar).calendar_ledger.filter(pl.col("decision_us") <= boundary)
    assert before.equals(after)


def test_incomplete_or_delayed_hour_rejects_whole_paired_fold():
    minutes = synthetic_minutes()
    calendar = START + np.arange(200 * 60, 204 * 60, dtype=np.int64) * MINUTE
    hole = minutes.filter(pl.col("open_us") != START + 150 * HOUR + MINUTE)
    delayed = minutes.with_columns(pl.when(pl.col("open_us") == START + 150 * HOUR + MINUTE)
        .then(START + 205 * HOUR).otherwise(pl.col("available_us")).alias("available_us"))
    for bad in (hole, delayed):
        plan = public.fixed_targets(bad, calendar)
        assert plan.receipt["warmup_failed"]
        assert not plan.receipt["paired_comparison_allowed"]
        assert plan.targets["target_weight"].sum() == 0.
