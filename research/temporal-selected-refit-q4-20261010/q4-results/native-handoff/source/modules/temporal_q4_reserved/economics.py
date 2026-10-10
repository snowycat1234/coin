"""Verify the supplied real92/91 Q4 economic packet; no source acquisition."""

import json
import math
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

from modules.collector_research.pipeline.normalize import funding_windows
from modules.temporal_two_expert.exact import sha
from modules.temporal_two_expert.inputs import CORE5, DAY_US

from .data import EXECUTION_DELAY_US, ROOT

CONSUMER_SHA = "d972444cb43320ef3f356bd90d83a2a51dcea5d3ce552784870f99b40d2dbe23"
ECONOMICS_SHA = "9d58444304b3eceb15de444c50a8ae3242d73aed931b6aca08abb424373d3078"
Q4_PROTOCOL_SHA = "5f115345877644397dca2998c8dcf16f92fab271bc680b732cbebc0c8de64d88"


def economics(directory, decisions):
    directory = Path(directory)
    if (
        sha(directory / "CONSUMER_INDEX.json") != CONSUMER_SHA
        or sha(directory / "ECONOMICS.npz") != ECONOMICS_SHA
    ):
        raise ValueError("Exact supplied consumer index/array required")
    consumer = json.loads((directory / "CONSUMER_INDEX.json").read_text())
    for name, expected in consumer["normalization_source_SHA256"].items():
        if sha(ROOT / name) != expected:
            raise ValueError("Exact inherited economic normalization source required")
    if (
        consumer["protocol_SHA256"] != Q4_PROTOCOL_SHA
        or consumer["symbols_order"] != list(CORE5)
        or not consumer["execution_and_held_funding_ready"]
        or not consumer["native_minute_grid_complete"]
        or consumer["paid_close_UTC"] != "2024-12-31T00:01:00.000001Z"
    ):
        raise ValueError("Economic packet must bind fixed protocol and symbol order")
    with np.load(directory / "ECONOMICS.npz", allow_pickle=False) as z:
        arrays = {name: z[name].copy() for name in z.files}
    np.testing.assert_array_equal(arrays["symbol_order"], CORE5)
    for name, expected in (
        ("decision_us", decisions),
        ("execution_us", decisions + EXECUTION_DELAY_US),
        ("funding_interval_start_us", decisions[:-1] + EXECUTION_DELAY_US),
        ("funding_interval_end_us", decisions[1:] + EXECUTION_DELAY_US),
    ):
        np.testing.assert_array_equal(arrays[name], expected)
    prices, coeff = arrays["prices"], arrays["funding_coeff"]
    if (
        prices.shape != (92, 5)
        or coeff.shape != (91, 5)
        or not np.isfinite(prices).all()
        or np.any(prices <= 0)
        or not np.isfinite(coeff).all()
    ):
        raise ValueError("92 real prices/91 complete funding intervals required, no padding")
    for row in consumer["economic_table_artifacts"]:
        path = directory / row["path"]
        if path.stat().st_size != row["bytes"] or sha(path) != row["SHA256"]:
            raise ValueError("Exact supplied economic table bytes required")
    independent_errors = {}
    for j, symbol in enumerate(CORE5):
        events = pq.read_table(
            directory / f"normalized/data/normalized/{symbol}_funding_events.parquet"
        ).to_pandas()
        daily = pq.read_table(
            directory / f"normalized/data/normalized/{symbol}_daily.parquet"
        ).to_pandas()
        intervals = pq.read_table(
            directory / f"normalized/economics/{symbol}_funding_intervals.parquet"
        ).to_pandas()
        times = events.calc_time_ms.to_numpy(np.int64) * 1000
        marks = events.past_mark_price.to_numpy(float)
        available = events.past_mark_available_us.to_numpy(np.int64)
        np.testing.assert_array_equal(available, (times - 1) // 60000000 * 60000000)
        if (
            len(events) != 276
            or np.any(np.diff(times) <= 0)
            or not np.isfinite(marks).all()
            or np.any(marks <= 0)
            or np.any(times - available > 60000000)
        ):
            raise ValueError("Actual strictly-prior marked events required")
        actual = funding_windows(events, pd.to_datetime(decisions[:-1], unit="us", utc=True))
        if (
            not actual.funding_interval_complete.all()
            or not intervals.funding_interval_complete.all()
        ):
            raise ValueError("Both-sided held event coverage required")
        np.testing.assert_array_equal(actual.mark_funding_per_unit, coeff[:, j])
        np.testing.assert_array_equal(intervals.mark_funding_per_unit, coeff[:, j])
        np.testing.assert_array_equal(pd.DatetimeIndex(daily.dt).as_unit("us").asi8, decisions)
        np.testing.assert_array_equal(daily.exec_price, prices[:, j])
        if not daily.complete_kline.all() or not (daily.unique_minutes == 1440).all():
            raise ValueError("Actual complete execution days required")
        references = []
        for start in decisions[:-1] + EXECUTION_DELAY_US:
            selected = (times > start) & (times <= start + DAY_US)
            if selected.sum() != 3:
                raise ValueError("Expected actual held funding event count")
            references.append(
                math.fsum(
                    float(a) * float(b)
                    for a, b in zip(
                        events.last_funding_rate.to_numpy(float)[selected],
                        marks[selected],
                        strict=True,
                    )
                )
            )
        np.testing.assert_allclose(references, coeff[:, j], atol=1e-10, rtol=2e-15)
        independent_errors[symbol] = float(np.max(np.abs(np.asarray(references) - coeff[:, j])))
    # Real terminal ABI: no repeated endpoint or synthetic funding row.
    return (
        prices,
        coeff,
        dict(
            source_commit="152606ad56fe6d8943b27ce89c8c57e2068ee944",
            economic_SHA256=ECONOMICS_SHA,
            consumer_SHA256=CONSUMER_SHA,
            independent_funding_max_error=independent_errors,
            native_minute_grid_complete=True,
            missing_mark_open_UTC=[],
            original_minute_mark_values_verified_by_source_task=True,
            minute_tape_replayed_here=False,
            real_price_rows=92,
            real_funding_intervals=91,
            synthetic_economic_rows=0,
            source_capacity_zeros_retained_per_asset=89,
        ),
    )
