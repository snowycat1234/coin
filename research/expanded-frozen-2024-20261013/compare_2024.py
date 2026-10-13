"""Frozen 2024 same-calendar five-wallet report; read-only after all runs end.

No targets, fees, market source or native financial state are altered here.
Bootstrap follows PROTOCOL.json: paired 14-day circular blocks, 1000 draws,
seed 811764. It is descriptive because this history has already been seen.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path

import numpy as np

ARMS = ("CS_MATCHED", "VOL_MATCHED", "STATIC50", "SMA200_10PCT", "EXACTHALF")
SOURCE_SHA = "0b319baf450c8a0f2f89c2a15fdabf2741471bd0ae75aef6f5be1f76cb439c69"
TARGET_SHA = "4f3b615b524de3220df3c10595ba2a7723f6e62dcff59b31ed82cb9476a9b5d5"
DAY = 86400000000
START = 1704067200000000
END = 1735689600000000
N = 366
B = 14
R = 1000
SEED = 811764


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def daily_return(path):
    with Path(path).open(newline="") as inp:
        rows = list(csv.DictReader(inp))
    clocks = np.array([int(row["close_us"]) for row in rows])
    if not np.array_equal(clocks, np.arange(START + DAY, END + DAY, DAY)):
        raise ValueError("Exact 366 completed daily cash/marked observations required")
    nav = np.r_[10000., np.array([float(row["nav"]) for row in rows])]
    if not np.isfinite(nav).all() or np.min(nav) <= 0:
        raise ValueError("Nonpositive/nonfinite whole-calendar native NAV")
    return np.diff(nav) / nav[:-1], float(nav[-1])


def report(root):
    result = {}
    daily = {}
    for arm in ARMS:
        folder = Path(root) / arm
        binding = json.loads((folder / "BINDING.json").read_text())
        record = json.loads((folder / "RESULT.json").read_text())
        if binding["arm"] != arm or record["arm"] != arm:
            raise ValueError("Wrong wallet arm binding")
        if binding["source_index_SHA256"] != SOURCE_SHA or binding["target_archive_SHA256"] != TARGET_SHA:
            raise ValueError("Same original source and target identities required")
        if not record["full_527040_minutes"] or record["summary"]["completed_minutes"] != 527040:
            raise ValueError("No partial-calendar return comparison")
        r, terminal_nav = daily_return(folder / "DAILY.csv")
        if not np.isclose(terminal_nav, 10000 + record["summary"]["net_PnL"], atol=1e-7, rtol=0):
            raise ValueError("Independent daily NAV versus native account terminal mismatch")
        daily[arm] = r
        result[arm] = {
            "net_marked_USDT": record["summary"]["net_PnL"],
            "marked_return": record["cumulative_marked_return"],
            "paid_cash_return": record["paid_cash_return"],
            "paid_flat": record["paid_flat"],
            "annual_daily_vol": record["metrics"]["annual_daily_vol"],
            "max_observed_minute_drawdown": record["metrics"]["minute_drawdown"],
            "worst_30_days": record["metrics"]["worst30"],
            "mean_actual_gross": record["metrics"]["mean_actual_gross"],
            "max_actual_gross": record["metrics"]["max_actual_gross"],
            "turnover_USDT": record["summary"].get("gross_fill_turnover"),
            "independent_decimal_NAV_bridge": record["independent_decimal_NAV_bridge"],
            "liquidation_count": len(record["liquidations"]),
            "account_stop_us": record["summary"]["stop_us"],
            "rejections": record["rejection_counts"],
            "Aug12_day_start_checkpoint": record["aug12_start_checkpoint_saved"],
            "state_hash": record["genuine_state_hash"],
        }
    rng = np.random.default_rng(SEED)
    starts = rng.integers(0, N, size=(R, (N + B - 1) // B))
    picks = ((starts[:, :, None] + np.arange(B)) % N).reshape(R, -1)[:, :N]
    sampled = {arm: np.expm1(np.log1p(daily[arm][picks]).sum(axis=1)) for arm in ARMS}
    mix = sampled["EXACTHALF"]
    paired = {}
    for arm in ARMS:
        if arm == "EXACTHALF":
            continue
        diff = mix - sampled[arm]
        observed = result["EXACTHALF"]["marked_return"] - result[arm]["marked_return"]
        paired[arm] = {"actual_return_difference": observed,
                       "bootstrap_return_difference_95pct": np.quantile(diff, [.025, .975]).tolist(),
                       "bootstrap_fraction_mix_not_above": float(np.mean(diff <= 0)),
                       "draws": R, "circular_block_days": B, "seed": SEED}
    return {"status": "COMPLETE_FIVE_FROZEN_2024_NATIVE_WALLETS",
            "calendar_UTC": [START, END], "days": N,
            "source_index_SHA256": SOURCE_SHA, "targets_SHA256": TARGET_SHA,
            "interpretation": "Already-seen historical development, descriptive paired bootstrap only",
            "wallets": result, "EXACTHALF_minus_controls": paired,
            "fixed_descriptive_gates": {arm: {
                "positive_net": value["net_marked_USDT"] > 0,
                "minute_drawdown_at_most_12pct": value["max_observed_minute_drawdown"] <= .12,
                "zero_liquidations": value["liquidation_count"] == 0,
                "paid_terminal_flat": value["paid_flat"]}
                for arm, value in result.items()}}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--wallet-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    value = report(args.wallet_root)
    with args.output.open("x") as out:
        json.dump(value, out, indent=2, sort_keys=True, allow_nan=False)
        out.write("\n")
    print("FIVE_WALLET_2024_REPORT_PASS", sha(args.output))
