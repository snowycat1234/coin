"""One-pass official statistics for the accepted continuous minute view only.

This is a resource adapter over preserved benchmark rules. It does not accept
gaps, delayed/missing closes, learned models, new parameters or other sleeves.
"""
from __future__ import annotations

import numpy as np
import polars as pl
from scripts.research_v8 import benchmark_targets_v2 as common
from scripts.research_v8 import benchmark_targets as original


def fixed_targets(identifier, minute_closes, calendar, *, daily_returns=None):
    calendar = common.calendar_array(calendar)
    allowed = {"CASH", "SPOT_BUY_AND_HOLD", "VOL_MANAGED_BUY_AND_HOLD", "FIXED_TREND", "FIXED_MEAN_REVERSION"}
    common.require(identifier in allowed, "Only five preserved fixed sleeves; no fitted forecasts")
    if identifier == "CASH":
        return common.fixed_targets(identifier, minute_closes, calendar)
    original.contracts()
    common._integer_timestamp_columns(minute_closes, ("close_us", "available_us"))
    common.require(minute_closes.height == minute_closes.unique(["symbol", "close_us"]).height,
        "Duplicate closed-minute source")
    common.require(set(minute_closes["symbol"].unique().to_list()) == set(common.SYMBOLS), "Same two-symbol source")
    weights = np.zeros((len(calendar), 2))
    reasons = [["CASH", "CASH"] for _ in calendar]
    warmup_failed = False
    vol = None
    if identifier == "VOL_MANAGED_BUY_AND_HOLD":
        common.require(daily_returns is not None, "Explicit same gross-reference daily returns")
        common._integer_timestamp_columns(daily_returns, ("day_end_us", "available_us"), allow_end=True)
        vol = np.zeros(len(calendar))
        current = None
        for row, stamp in enumerate(calendar):
            if row == 0 or stamp % common.DAY_US == 0:
                current = common.causal_vol_multiplier(daily_returns, int(stamp))
            if current is None:
                warmup_failed = True
                vol[row] = np.nan
            else:
                vol[row] = current
    for column, symbol in enumerate(common.SYMBOLS):
        asset = minute_closes.filter(pl.col("symbol") == symbol).sort("close_us").rechunk()
        stamps = asset["close_us"].to_numpy()
        availability = asset["available_us"].to_numpy()
        prices = asset["close"].to_numpy()
        common.require(len(stamps) and np.all(np.diff(stamps) == common.MINUTE_US)
            and np.array_equal(stamps, availability) and np.isfinite(prices).all() and np.all(prices > 0),
            "Bulk adapter only accepts the shared complete finite on-time source; no imputation")
        indices = np.searchsorted(stamps, calendar, side="left")
        common.require(np.all(indices < len(stamps)) and np.array_equal(stamps[indices], calendar),
            "Every decision must have its completed current close")
        if identifier in ("SPOT_BUY_AND_HOLD", "VOL_MANAGED_BUY_AND_HOLD"):
            multiplier = np.ones(len(calendar)) if vol is None else vol
            weights[:, column] = np.where(np.isfinite(multiplier), .3 * multiplier, 0.)
            for row in range(len(calendar)):
                reasons[row][column] = ("INSUFFICIENT_SEVEN_COMPLETED_DAILY_GROSS_RETURNS" if not np.isfinite(multiplier[row])
                    else "CAPPED_HOLD_INTENT" if vol is None else "DAILY_EWMA_DOWNSCALED_HOLD_INTENT")
        elif identifier == "FIXED_TREND":
            # Official causal recurrences computed once over the same prefix.
            fast = asset["close"].ewm_mean(span=60, adjust=False, min_samples=240).to_numpy()
            slow = asset["close"].ewm_mean(span=240, adjust=False, min_samples=240).to_numpy()
            for row, index in enumerate(indices):
                if index < 239:
                    reasons[row][column] = "INSUFFICIENT_CONTIGUOUS_240_MINUTE_WARMUP"
                    warmup_failed = True
                    continue
                active = fast[index] > slow[index]
                weights[row, column] = .3 if active else 0.
                reasons[row][column] = "FIXED_EWMA60_GREATER_THAN_EWMA240" if active else "FIXED_TREND_FLAT"
        else:
            logs = asset["close"].log()
            log_values = logs.to_numpy()
            mean = logs.rolling_mean(60, min_samples=60).shift(1).to_numpy()
            std = logs.rolling_std(60, min_samples=60, ddof=0).shift(1).to_numpy()
            held_since = None
            for row, (stamp, index) in enumerate(zip(calendar, indices, strict=True)):
                if index < 60:
                    reasons[row][column], warmup_failed, held_since = "INSUFFICIENT_PRECEDING_60_MINUTE_WARMUP", True, None
                    continue
                if not np.isfinite(std[index]) or std[index] <= 0:
                    held_since, reasons[row][column] = None, "ZERO_STD_ABSTAIN"
                    continue
                z = (log_values[index] - mean[index]) / std[index]
                if held_since is not None and (z >= 0 or stamp - held_since >= 60 * common.MINUTE_US):
                    held_since, reasons[row][column] = None, "MR_Z0_OR_60MINUTE_INTENT_EXIT"
                elif held_since is None and z <= -2:
                    held_since, reasons[row][column] = int(stamp), "MR_PRECEDING60_Z_NEGATIVE2_INTENT_ENTRY"
                else:
                    reasons[row][column] = "MR_HOLD_OR_ABSTAIN"
                weights[row, column] = .3 if held_since is not None else 0.
    weights[-1] = 0.
    reasons[-1] = ["COMMON_TERMINAL_EXIT_INTENT_NEEDS_FEASIBLE_FILL"] * 2
    return common._version(original._plan(identifier, calendar, weights, reasons, warmup_failed=warmup_failed,
        metadata={"benchmark_contract_sha256": common.file_sha(common.ROOT / "protocols/BENCHMARK_CONTRACT_V1.json"),
            "cost_scenarios_sha256": common.file_sha(common.ROOT / "protocols/EXECUTION_COST_SCENARIOS_V8.json"),
            "cost_scenario_evaluated": None, "full_suite_available": False, "resource_adapter": "ONE_PASS_OFFICIAL_POLARS_ON_ACCEPTED_CONTINUOUS_SOURCE"}))
