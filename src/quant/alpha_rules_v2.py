"""Preregisterable V2 labels, stateful long/flat decisions and acceptance metrics."""

from __future__ import annotations

import math
import statistics

import numpy as np
import polars as pl

from .execution_contract import MINUTE_US, ExecutionContractV2

HOUR_US = 60 * MINUTE_US
THRESHOLDS = {"A": (45.0, 15.0), "B": (60.0, 15.0), "C": (75.0, 30.0)}
LOCKED_START_US = 1_772_323_200_000_000


def executable_labels_v2(features: pl.DataFrame, minutes: pl.DataFrame) -> pl.DataFrame:
    """Four hours between V2 entry/exit minute opens; contiguous minute path required.

    Gross is the mid/open proxy return before trading costs. The diagnostic net
    return includes both execution costs and both fees on actual fill notional.
    Capacity/lot/risk constraints are evaluated separately by the trading simulator.
    """
    contract = ExecutionContractV2()
    if features.is_empty() or minutes.is_empty():
        raise ValueError("Development features and minutes are required")
    if (features["available_us"].max() >= LOCKED_START_US
            or minutes["open_us"].max() >= LOCKED_START_US):
        raise ValueError("Locked historical test prohibited")
    execution_rate = contract.execution_rate(contract.half_spread_floor_bps,
                                              contract.extra_slippage_bps)
    fee_rate = contract.fee_bps / 10_000
    roundtrip_factor = ((1 - execution_rate) * (1 - fee_rate)
                        / ((1 + execution_rate) * (1 + fee_rate)))
    results = []
    for group in features.sort("available_us", "symbol").partition_by("symbol"):
        symbol = group["symbol"][0]
        asset = minutes.filter(pl.col("symbol") == symbol).sort("open_us")
        if asset.is_empty():
            raise ValueError("Missing symbol minute history")
        times, prices = asset["open_us"].to_numpy(), asset["open"].to_numpy()
        if (np.any(np.diff(times) <= 0) or np.any(times % MINUTE_US)
                or np.any(~np.isfinite(prices)) or np.any(prices <= 0)):
            raise ValueError("Unique aligned positive minute prices required")
        expected = np.array([contract.earliest_execution_us(int(value))
                             for value in group["available_us"].to_list()], dtype=np.int64)
        expected_exits = np.array([contract.earliest_execution_us(int(value) + 4 * HOUR_US)
                                  for value in group["available_us"].to_list()], dtype=np.int64)
        entries, exits = np.searchsorted(times, expected), np.searchsorted(times, expected_exits)
        safe_entry = np.minimum(entries, len(times) - 1)
        safe_exit = np.minimum(exits, len(times) - 1)
        previous = np.maximum(safe_entry - 1, 0)
        # Exactly 240 minute transitions proves no hidden missing minute between endpoints.
        valid = ((entries > 0) & (entries < len(times)) & (exits < len(times))
                 & (times[safe_entry] == expected) & (times[safe_exit] == expected_exits)
                 & (times[previous] == expected - MINUTE_US) & (exits - entries == 240)
                 & (expected_exits + 1 < LOCKED_START_US))
        gross = prices[safe_exit] / prices[safe_entry] - 1
        net = (1 + gross) * roundtrip_factor - 1
        results.append(group.with_columns(
            pl.Series("entry_us", np.where(valid, expected + 1, 0)),
            pl.Series("label_end_us", np.where(valid, expected_exits + 1, 0)),
            pl.Series("gross_return", [float(value) if okay else None
                                        for value, okay in zip(gross, valid, strict=True)]),
            pl.Series("diagnostic_net_return", [float(value) if okay else None
                                                 for value, okay in zip(net, valid, strict=True)]),
            pl.Series("profitable_after_cost", valid & (net > 0)),
            pl.Series("label_valid", valid),
            pl.lit(1 - roundtrip_factor).alias("estimated_roundtrip_cost"),
        ))
    return pl.concat(results).sort("available_us", "symbol")


def hysteresis_targets_v2(predictions: pl.DataFrame, threshold: str) -> pl.DataFrame:
    """Strict A/B/C thresholds, two-hour intended hold, explicit data-risk exits.

    The executor must also enforce two hours from the *actual first fill*. A missing
    prediction or disconnected decision path forces flat as a risk exit. Merely
    becoming negative during the hold does not force exit.
    """
    if threshold not in THRESHOLDS:
        raise ValueError("Only preregistered A/B/C thresholds allowed")
    if not {"symbol", "available_us", "expected_return"}.issubset(predictions.columns):
        raise ValueError("Prediction schema is incomplete")
    if predictions.select(pl.struct("symbol", "available_us").is_duplicated().any()).item():
        raise ValueError("Duplicate prediction primary key")
    enter, leave = (value / 10_000 for value in THRESHOLDS[threshold])
    output = []
    contract = ExecutionContractV2()
    for asset in predictions.sort("symbol", "available_us").partition_by("symbol"):
        long, entry_execution, last = False, None, None
        for row in asset.iter_rows(named=True):
            now = int(row["available_us"])
            value = row["expected_return"]
            missing = value is None or not math.isfinite(value)
            forced = missing or (last is not None and now != last + HOUR_US)
            eligible = contract.earliest_execution_us(now)
            if forced:
                long, entry_execution = False, None
            elif long:
                if eligible - entry_execution >= 2 * HOUR_US and value < leave:
                    long, entry_execution = False, None
            elif value > enter:
                long, entry_execution = True, eligible
            output.append({"symbol": row["symbol"], "available_us": now,
                           "target_weight": 0.30 if long else 0.0,
                           "risk_forced_exit": forced, "minimum_hold_minutes": 120,
                           "decision_expected_return": value,
                           "decision_policy_version": "hysteresis_v2"})
            last = now
    return pl.DataFrame(output, schema={
        "symbol": pl.String, "available_us": pl.Int64, "target_weight": pl.Float64,
        "risk_forced_exit": pl.Boolean, "minimum_hold_minutes": pl.Int64,
        "decision_expected_return": pl.Float64, "decision_policy_version": pl.String,
    }).sort("available_us", "symbol")


def r2_gates(summary: dict, stress: dict[str, dict], active: dict[str, dict]) -> dict:
    """All R2 conditions must pass; gates do not guarantee later profitability."""
    if set(active) != {"B2", "B3", "B4"} or set(stress) != {"fee_x2", "slippage_x2"}:
        raise ValueError("All three active baselines and both stress paths required")
    gross_alpha = summary["gross_pnl_before_costs"]
    fee_ratio = summary["fees"] / gross_alpha if gross_alpha > 0 else None
    median_sharpe = statistics.median(item["sharpe"] for item in active.values())
    median_return = statistics.median(item["total_return"] for item in active.values())
    checks = {
        "net_positive": summary["total_return"] > 0,
        "exceed_active_median_net_return": summary["total_return"] > median_return,
        "exceed_active_median_risk_adjusted": summary["sharpe"] > median_sharpe,
        "minimum_sharpe": summary["sharpe"] >= 0.6,
        "fee_stress_nonnegative": stress["fee_x2"]["total_return"] >= 0,
        "slippage_stress_nonnegative": stress["slippage_x2"]["total_return"] >= 0,
        "maximum_drawdown": summary["max_drawdown"] <= 0.15,
        "drawdown_observable": summary.get("daily_risk_observable", False),
        "fee_to_positive_gross_alpha": fee_ratio is not None and fee_ratio < 0.6,
        "minimum_independent_cycles": summary["round_trip_count"] >= 30,
    }
    return {"passed": all(checks.values()), "checks": checks, "fee_gross_alpha_ratio": fee_ratio,
            "active_median_sharpe": median_sharpe, "active_median_return": median_return,
            "net_return_excess": summary["total_return"] - median_return,
            "risk_adjusted_excess": summary["sharpe"] - median_sharpe,
            "evidence_scope": "DEVELOPMENT_HISTORY", "true_forward_days": 0}
