"""FR64 participant-flow targets and explicitly trade-based, non-BBO price proxies."""

from __future__ import annotations

import polars as pl

BAR_US = 5_000_000
LABEL_LAG_US = 310_000_000
EPS = 1e-12
TARGET_STREAMS = ("spot_BTCUSDT", "spot_ETHUSDT")
TASKS = ("flow_5m", "return_5m_proxy", "flow_30s", "logrv_5m")
LABEL_COLUMNS = tuple(f"{stream}__{task}" for stream in TARGET_STREAMS for task in TASKS)


def label_table(joint: pl.DataFrame) -> pl.DataFrame:
    """One label row per source close; callers must supply a dense, validated joint grid.

    At row i, decision is its close. Flow uses i+1..i+60; the entry proxy is i+2,
    exit is i+62. All eight labels mature at decision+310s. This function never
    returns future quantities as input features.
    """
    expressions = []
    qa = []
    valid = []
    maturity = []
    for stream in TARGET_STREAMS:

        def col(name, stream=stream):
            return pl.col(f"{stream}__{name}")

        buy, sell = col("aggressive_buy_notional"), col("aggressive_sell_notional")
        for task, count in (("flow_5m", 60), ("flow_30s", 6)):
            net = (buy - sell).rolling_sum(count, min_samples=count).shift(-count)
            total = (buy + sell).rolling_sum(count, min_samples=count).shift(-count)
            expressions.append((net / (total + EPS)).alias(f"{stream}__{task}"))
            qa.append(net.alias(f"{stream}__{task}_raw_net_notional"))
        entry, exit_price = col("open").shift(-2), col("open").shift(-62)
        entry_us, exit_us = col("first_trade_us").shift(-2), col("first_trade_us").shift(-62)
        entry_anchor = pl.col("timestamp") + 2 * BAR_US
        exit_anchor = pl.col("timestamp") + 62 * BAR_US
        wait_valid = entry_us.is_between(entry_anchor, entry_anchor + 2_000_000) & (
            exit_us.is_between(exit_anchor, exit_anchor + 2_000_000)
        )
        expressions.extend(
            [
                pl.when(wait_valid & (entry > 0) & (exit_price > 0))
                .then(exit_price / entry - 1)
                .otherwise(None)
                .alias(f"{stream}__return_5m_proxy"),
                (col("return_5s").pow(2).rolling_sum(60, min_samples=60).shift(-60) + EPS)
                .log()
                .alias(f"{stream}__logrv_5m"),
            ]
        )
        qa.extend(
            [
                entry.alias(f"{stream}__entry_price_proxy"),
                exit_price.alias(f"{stream}__exit_price_proxy"),
                entry_us.alias(f"{stream}__entry_trade_us"),
                exit_us.alias(f"{stream}__exit_trade_us"),
            ]
        )
        maturity.append(col("available_us").shift(-62))
        # Any unknown/invalid future bar invalidates the shared endpoint.
        valid.append(col("quality").cast(pl.Int64).rolling_sum(62, min_samples=62).shift(-62) == 0)
    result = joint.select(
        (pl.col("timestamp") + BAR_US).alias("decision_us"),
        pl.max_horizontal(maturity).alias("label_available_us"),
        *expressions,
        *qa,
        pl.all_horizontal(valid).fill_null(False).alias("future_quality_valid"),
    )
    return result.with_columns(
        (
            pl.all_horizontal(
                [pl.col(name).is_not_null() & pl.col(name).is_finite() for name in LABEL_COLUMNS]
            )
            & pl.col("future_quality_valid")
        ).alias("label_valid")
    )
