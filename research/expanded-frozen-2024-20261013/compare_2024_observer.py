"""Read-only failure-aware report for the already frozen 2024 five-arm replay.

The source, targets, account, costs, risk rules, and frozen paired bootstrap
method are never changed. A halted wallet remains halted; full-year bootstrap
is emitted only for genuinely complete paired calendars.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path

import numpy as np

import compare_2024 as fixed

SOURCE_COMMIT = "1baa2add503a13518547f3be3692092382136032"
TARGET_COMMIT = "97e8631d01af612e07f461600710232949725be5"


def iso(microseconds):
    return datetime.fromtimestamp(microseconds / 1_000_000, timezone.utc).isoformat() if microseconds else None


def report(root):
    records = {}
    returns = {}
    for arm in fixed.ARMS:
        folder = Path(root) / arm
        binding = json.loads((folder / "BINDING.json").read_text())
        value = json.loads((folder / "RESULT.json").read_text())
        resource = json.loads((Path(root) / f"{arm}_RESOURCE.json").read_text())
        if binding["arm"] != arm or value["arm"] != arm:
            raise ValueError(f"Wrong original frozen arm identity: {arm}")
        if binding["source_index_SHA256"] != fixed.SOURCE_SHA or binding["target_archive_SHA256"] != fixed.TARGET_SHA:
            raise ValueError("2024 original source/target binding mismatch")
        if binding["source_publication_commit"] != SOURCE_COMMIT or binding["target_publication_commit"] != TARGET_COMMIT:
            raise ValueError("Public pre-score code/source/target commit binding mismatch")
        if resource["exit_code"] != 0 or resource["stop_reason"] is not None:
            raise ValueError(f"Original wallet resource launch did not finish cleanly: {arm}")
        summary = value["summary"]
        complete = bool(value["full_527040_minutes"] and summary["completed_minutes"] == 527040)
        if complete and summary["stop_us"] is not None:
            raise ValueError("Completed 2024 account has a stop timestamp")
        if not complete and (not summary["stop_us"] or summary["completed_minutes"] >= 527040):
            raise ValueError("Partial native wallet must show genuine earlier stop")
        if complete:
            returns[arm], terminal_nav = fixed.daily_return(folder / "DAILY.csv")
            if not np.isclose(terminal_nav, 10000. + summary["net_PnL"], atol=1e-7, rtol=0):
                raise ValueError(f"Actual daily NAV versus native terminal account differs: {arm}")
        audit = value["independent_decimal_NAV_bridge"]
        if abs(float(audit["maximum_error_USDT"])) > 1e-8:
            raise ValueError(f"Independent Decimal inventory/account audit fails: {arm}")
        records[arm] = {
            "calendar_completion": "FULL_366_DAYS" if complete else "HALTED_PARTIAL_NO_366_DAY_RETURN",
            "completed_minutes": summary["completed_minutes"],
            "required_minutes": 527040,
            "account_status": summary["account_status"],
            "completion_reason": summary["completion"],
            "stop_UTC": iso(summary["stop_us"]),
            "partial_or_full_marked_PnL_USDT": summary["net_PnL"],
            "full_calendar_marked_return": value["cumulative_marked_return"] if complete else None,
            "paid_terminal_flat": value["paid_flat"],
            "paid_cash_return": value["paid_cash_return"] if complete else None,
            "observed_minute_max_drawdown": value["metrics"]["minute_drawdown"],
            "full_calendar_daily_vol": value["metrics"]["annual_daily_vol"] if complete else None,
            "full_calendar_worst_30_days": value["metrics"]["worst30"] if complete else None,
            "mean_actual_gross": value["metrics"]["mean_actual_gross"],
            "max_actual_gross": value["metrics"]["max_actual_gross"],
            "gross_fill_turnover_USDT": summary["gross_fill_turnover_USDT"],
            "independent_decimal_accounting_USDT": audit,
            "liquidation_simulated_count": len(value["liquidations"]),
            "risk_reduction_signal_count": summary["risk_reduction_signal_count"],
            "rejections": value["rejection_counts"],
            "aug12_observer_checkpoint_saved": value["aug12_start_checkpoint_saved"],
            "quantity_profile_SHA256": value["quantity_profile_SHA256"],
            "genuine_state_hash": value["genuine_state_hash"],
            "resource_receipt": {k: resource[k] for k in (
                "exit_code", "stop_reason", "elapsed_seconds", "maximum_sampled_descendant_RSS_bytes",
                "maximum_host_used_bytes", "per_process_address_limit_bytes", "aggregate_RSS_stop_bytes",
                "host_used_stop_bytes", "affinity_cpu_count", "swap_active")},
            "descriptive_gates": {
                "full_calendar": complete,
                "positive_full_calendar_net": summary["net_PnL"] > 0 if complete else None,
                "max_minute_drawdown_at_most_12pct": value["metrics"]["minute_drawdown"] <= .12 if complete else None,
                "no_account_halt": summary["stop_us"] is None,
                "zero_simulated_liquidations": len(value["liquidations"]) == 0,
                "paid_terminal_flat": value["paid_flat"] if complete else None,
            },
        }
    pairs = {}
    if "EXACTHALF" in returns:
        rng = np.random.default_rng(fixed.SEED)
        starts = rng.integers(0, fixed.N, size=(fixed.R, (fixed.N + fixed.B - 1) // fixed.B))
        picks = ((starts[:, :, None] + np.arange(fixed.B)) % fixed.N).reshape(fixed.R, -1)[:, :fixed.N]
        mix = np.expm1(np.log1p(returns["EXACTHALF"][picks]).sum(axis=1))
        for arm in fixed.ARMS:
            if arm == "EXACTHALF":
                continue
            if arm not in returns:
                pairs[arm] = {"status": "NO_FULL_YEAR_PAIRED_COMPARISON_CONTROL_HALTED"}
                continue
            other = np.expm1(np.log1p(returns[arm][picks]).sum(axis=1))
            difference = mix - other
            pairs[arm] = {
                "status": "BOTH_FULL_366_DAY_NATIVE_WALLETS",
                "actual_return_difference_mix_minus_control":
                    records["EXACTHALF"]["full_calendar_marked_return"] - records[arm]["full_calendar_marked_return"],
                "descriptive_bootstrap_95pct": np.quantile(difference, [.025, .975]).tolist(),
                "bootstrap_fraction_mix_not_above": float(np.mean(difference <= 0)),
                "paired_circular_block_days": fixed.B, "draws": fixed.R, "seed": fixed.SEED,
            }
    return {
        "status": "FROZEN_2024_FIVE_WALLETS_WITH_HALT_AWARE_REPORTING",
        "scope": "Already-seen 2024 development calendar; no new OOS or live-trading approval",
        "calendar_UTC": ["2024-01-01T00:00:00Z", "2025-01-01T00:00:00Z"],
        "days": 366,
        "symbols_ordered": ["BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT", "DOGEUSDT"],
        "one_fresh_shared_wallet_per_arm_USDT": 10000,
        "source_index_SHA256": fixed.SOURCE_SHA, "targets_SHA256": fixed.TARGET_SHA,
        "source_publication_commit": SOURCE_COMMIT, "targets_publication_commit": TARGET_COMMIT,
        "native_assumptions": {
            "cost_per_side": "BASE27: 5.5bp fee + 4bp half-spread + 4bp slippage",
            "funding": "Actual signed rates, RAW_AS_FRACTION scale 1; venue-unit certification unavailable",
            "execution": "Actual trade 1m OPEN at 00:01; previous minute quote volume * .001 fill capacity",
            "mark": "Actual original marks except exactly ten linear-smoothed 2024-08-12 rows",
            "account": "One-way isolated 1x, no auto topup, MMR .005, original paid final six-minute five-attempt close",
            "assumed_quantity_steps": {"BTCUSDT": .001, "ETHUSDT": .01, "SOLUSDT": 1,
                                       "XRPUSDT": 100, "DOGEUSDT": 1000},
            "quantity_profile_is_conditional_not_venue_certified": True,
            "caps_at_target": "Absolute asset .3, gross .6; observed minute overshoots retained",
        },
        "wallets": records, "EXACTHALF_minus_controls": pairs,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--wallet-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    value = report(args.wallet_root)
    with args.output.open("x") as output:
        json.dump(value, output, indent=2, sort_keys=True, allow_nan=False)
        output.write("\n")
    print("HALT_AWARE_FIVE_WALLET_REPORT_PASS")
