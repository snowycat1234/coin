"""Frozen five-arm 2024 shared-wallet replay, using the exact existing kernel.

The account class, scheduler, economics and quantity profile are imported from
the previously verified local port. This module supplies only saved targets,
the cold-rebuilt source window, identity checks and observer-only persistence.
"""
from __future__ import annotations

import argparse
import gc
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import sys
import time

import numpy as np

HERE = Path(__file__).resolve().parent
S = ("BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT", "DOGEUSDT")
ARMS = ("CS_MATCHED", "VOL_MATCHED", "STATIC50", "SMA200_10PCT", "EXACTHALF")
DAY = 86400000000
START = 1704067200000000
END = 1735689600000000
AUG12_START = 1723420800000000
TARGET_SHA = "4f3b615b524de3220df3c10595ba2a7723f6e62dcff59b31ed82cb9476a9b5d5"
SOURCE_SHA = "0b319baf450c8a0f2f89c2a15fdabf2741471bd0ae75aef6f5be1f76cb439c69"
PROFILE_SHA = "94b2238b25ed345a24a1fa148c6f35523b8efe9bf47496958028844432cb8ebf"
ENGINE_SHA = "318a0ae63056775db4e24c09abc1831de0dd166f9117b0ce0240630de6aad585"
ACCOUNT_SHA = "6c51c4efe33d652b2ddb1e3befd4e90f1aefca1140a578f9ff6fc3d50a8da0d6"
PORT_SHA = "c290175e490ac982b37f60e5b45793068169629fbeb70dc1625d49f7cfb4cb22"
STATE_IO_SHA = "5be8524a6b0ae69bca24a3e0f94b7f7b18d102fddbdddb8a83812c5d7317d7b2"
ACTIVITY_SHA = "b58ce1ec9584aea7c1ac3cc8e333cc34c3ddf2d48a09ab640a6734e036160b53"
LAUNCHER_SHA = "99432c34f2b7e6411ec9b68e5370deded6d1a94e6ff08d71e22e4a1164df914e"
DISK_RESERVE_BYTES = 16106127360
CASE_BYTES = 250000000
REFERENCE_PACKET_BYTES = 63204609
REQUIRED_MARGIN_BYTES = max(277457794, CASE_BYTES + 2 * REFERENCE_PACKET_BYTES + 1048576)
WALLET_SECONDS = 1200


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_native(repo: Path):
    if sha(repo / "scripts/investment/resumable_perpetual.py") != ENGINE_SHA:
        raise ValueError("Frozen scheduler SHA mismatch")
    if sha(repo / "research/quantity-grid-sensitivity-20261012/grid_account.py") != ACCOUNT_SHA:
        raise ValueError("Frozen account SHA mismatch")
    if sha(repo / "research/quantity-grid-sensitivity-20261012/QUANTITY_PROFILE.json") != PROFILE_SHA:
        raise ValueError("Frozen quantity profile SHA mismatch")
    if sha(repo / "research/cs-continuous-economics-20261012/state_io.py") != STATE_IO_SHA:
        raise ValueError("Frozen checkpoint code SHA mismatch")
    if sha(repo / "research/short-native-activity-20261012/activity.py") != ACTIVITY_SHA:
        raise ValueError("Frozen independent financial audit code SHA mismatch")
    sys.path[:0] = [str(repo), str(repo / "src"), str(HERE)]
    os.environ.setdefault("QUANT_ROOT", str(repo))
    os.environ.setdefault("QUANT_STATE", str(HERE))
    os.environ.setdefault("CONFIG_FILE", "/dev/null")
    port = repo / "research/static50-sma-20261013/local_native_apis.py"
    if sha(port) != PORT_SHA:
        raise ValueError("Original frozen local native port SHA mismatch")
    spec = importlib.util.spec_from_file_location("frozen_static50_native_port", port)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    if module.Closing.VERSION != "conditional_btc_anchored_quantity_grid_sensitivity_v1":
        raise ValueError("Original account VERSION differs")
    if module.profile_sha() != PROFILE_SHA:
        raise ValueError("Original quantity profile differs")
    module.verify()  # All original financial dependencies, not just top-level files.
    from window_2024 import window
    return module, window


def load_targets(path: Path):
    if sha(path) != TARGET_SHA:
        raise ValueError("Published 2024 target SHA differs")
    with np.load(path, allow_pickle=False) as z:
        if set(z.files) != {"decision_us", "symbol_order", "annual_covariance", *ARMS}:
            raise ValueError("Frozen five-arm target schema differs")
        d = z["decision_us"].copy()
        if not np.array_equal(d, np.arange(START, END, DAY)) or len(d) != 366:
            raise ValueError("2024 leap-year target calendar differs")
        if tuple(z["symbol_order"]) != S:
            raise ValueError("Original CORE5 order differs")
        arrays = {arm: z[arm].copy() for arm in ARMS}
    for arm, matrix in arrays.items():
        if (matrix.shape != (366, 5) or not np.isfinite(matrix).all()
                or np.abs(matrix).max() > .30 + 1e-12
                or np.abs(matrix).sum(axis=1).max() > .60 + 1e-12):
            raise ValueError(f"Invalid original frozen target: {arm}")
    np.testing.assert_array_equal(arrays["EXACTHALF"],
                                  .5*arrays["STATIC50"] + .5*arrays["SMA200_10PCT"])
    return d, arrays


def preflight(repo: Path, prepared: Path, target: Path):
    if sha(prepared / "SOURCE_INDEX.json") != SOURCE_SHA:
        raise ValueError("Frozen rebuilt public market source index differs")
    d, arrays = load_targets(target)
    api, window = load_native(repo)
    source = window(prepared)
    if source["start"] != START or source["end"] != END or tuple(source["symbols"]) != S:
        raise ValueError("2024 source window differs")
    if len(source["events"]) != 5490 or source["daily"].height != 1830:
        raise ValueError("2024 actual events/daily context incomplete")
    return api, source, d, arrays


def save(path, value):
    with Path(path).open("x") as out:
        json.dump(value, out, indent=2, sort_keys=True, allow_nan=False)
        out.write("\n")


def allocated_case_bytes(state: Path):
    """Count inode disk usage once, since the Aug-12 checkpoint hard-links immutable days."""
    seen = set()
    total = 0
    for path in state.rglob("*"):
        if not path.is_file():
            continue
        stat = path.stat()
        identity = (stat.st_dev, stat.st_ino)
        if identity not in seen:
            total += stat.st_size
            seen.add(identity)
    return total


def verify_storage_budget(state: Path):
    used = allocated_case_bytes(state)
    if used > CASE_BYTES:
        save(state / "BUDGET_STOP.json", {"reason": "CASE_BYTES", "used_bytes": used,
                                          "limit_bytes": CASE_BYTES,
                                          "recovery_checkpoint": str(state / "recovery")})
        raise RuntimeError("Frozen 250MB wallet state budget STOP; genuine checkpoint retained")


def checkpoint_aug12(api, state: Path, sim, binding):
    """Observer-only frozen original account snapshot, hard-linked to avoid duplicate data."""
    recovery = state / "recovery"
    pointer = api.checkpoint(recovery, sim, binding)
    observer = state / "aug12_start"
    observer.mkdir()
    required = [record["path"] for record in pointer["chunks"]] + [pointer["snapshot_path"], "POINTER.json"]
    for name in required:
        os.link(recovery / name, observer / name)
    if len(pointer["chunks"]) != 224 or pointer["cursor"] != AUG12_START:
        raise ValueError("Actual Aug-12 00:00 checkpoint scope differs")
    return pointer


def run_one(repo: Path, source_root: Path, target: Path, state: Path, arm: str,
            source_publication_commit: str, target_publication_commit: str):
    if state.exists() or arm not in ARMS:
        raise ValueError("Fresh arm state and one frozen arm required")
    if any(len(commit) != 40 or any(c not in "0123456789abcdef" for c in commit)
           for commit in (source_publication_commit, target_publication_commit)):
        raise ValueError("Exact public Git source and target commit SHAs required")
    if sha(HERE / "bounded_2024.py") != LAUNCHER_SHA:
        raise ValueError("Frozen one-wallet resource launcher SHA mismatch")
    if os.environ.get("COIN_CLOUD_BOUNDED") != "1":
        raise RuntimeError("Frozen one-CPU, 4GB AS, 2GB RSS, 8GB host, zero-swap launcher required")
    if not state.parent.is_dir():
        raise FileNotFoundError("State parent must exist before frozen resource admission")
    margin = shutil.disk_usage(state.parent).free - DISK_RESERVE_BYTES
    if margin < REQUIRED_MARGIN_BYTES:
        raise RuntimeError(f"RESOURCE_STOP: reserve margin {margin}, need {REQUIRED_MARGIN_BYTES}; no wallet state created")
    api, source, d, arrays = preflight(repo, source_root, target)
    native, Closing = api.native, api.Closing
    w = arrays[arm]
    state.mkdir(parents=True)
    binding = {"year": 2024, "arm": arm, "calendar": [START, END], "days": 366,
               "source_index_SHA256": SOURCE_SHA, "source_publication_commit": source_publication_commit,
               "target_archive_SHA256": TARGET_SHA, "target_publication_commit": target_publication_commit,
               "protocol_SHA256": sha(HERE / "PROTOCOL.json"), "account_class": Closing.VERSION,
               "profile_SHA256": PROFILE_SHA, "scheduler_SHA256": ENGINE_SHA,
               "local_native_port_SHA256": PORT_SHA, "checkpoint_code_SHA256": STATE_IO_SHA,
               "independent_audit_code_SHA256": ACTIVITY_SHA,
               "bounded_launcher_SHA256": LAUNCHER_SHA,
               "native_2024_adapter_SHA256": sha(HERE / "native_2024.py"),
               "window_2024_adapter_SHA256": sha(HERE / "window_2024.py"),
               "from_fresh_capital_USDT": 10000, "persist_cash_close": False,
               "final_day_target_zero": False,
               "derived_mark_cells": 10, "observed_gap_day_checkpoint_us": AUG12_START,
               "disk_reserve_bytes": DISK_RESERVE_BYTES, "preflight_margin_bytes": margin,
               "required_margin_bytes": REQUIRED_MARGIN_BYTES,
               "case_state_budget_bytes": CASE_BYTES, "wallet_seconds": WALLET_SECONDS}
    save(state / "BINDING.json", binding)

    def factory(_daily, clocks, mode):
        np.testing.assert_array_equal(clocks, d)
        if mode != "LONG_SHORT":
            raise ValueError("Original long-short simulation mode differs")
        frame = native.pl.DataFrame([{"available_us": int(at), "symbol": s,
                                      "target_weight": float(w[i, j])}
                                     for i, at in enumerate(d) for j, s in enumerate(S)])
        return frame, {"kind": "SAVED_FROZEN_2024_FIVE_ARM_TARGET", "binding": binding}

    sim = native.NativeDailySimulator(source, "LONG_SHORT", native.COSTS[0], native.UNITS[0],
                                      target_factory=factory, account_factory=Closing,
                                      persist_cash_close=False, final_day_target_zero=False)
    if type(sim.account) is not Closing or sim.account.nav() != 10000:
        raise ValueError("Original native wallet admission failed")
    begin = time.monotonic()
    api.checkpoint(state / "recovery", sim, binding)
    print("ACTUAL_2024_WALLET_STARTED", arm, flush=True)
    while sim.cursor < END and sim.stop is None:
        sim.advance_day()
        days = len(sim.minute_chunks)
        if sim.cursor == AUG12_START:
            checkpoint_aug12(api, state, sim, binding)
            verify_storage_budget(state)
        if days % 30 == 0 or sim.cursor == END or sim.stop is not None:
            api.checkpoint(state / "recovery", sim, binding)
            verify_storage_budget(state)
            print("ACTUAL_2024_WALLET_PROGRESS", arm, days, 366,
                  "NAV", float(sim.account.nav()), "STATUS", sim.account.status, flush=True)
        if time.monotonic() - begin > WALLET_SECONDS - 45:
            api.checkpoint(state / "recovery", sim, binding)
            save(state / "BUDGET_STOP.json", {"reason": "WALL_SECONDS", "elapsed": time.monotonic() - begin,
                                              "limit": WALLET_SECONDS, "recovery_checkpoint": str(state / "recovery")})
            raise RuntimeError("Bounded 1200s wallet STOP; genuine partial checkpoint retained")
    case = sim.result()
    summary = case["summary"]
    _, q = native.episodes(case["trades"], S)
    for s in S:
        if q[s] != sim.account.positions[s].quantity:
            raise ValueError("Independent original inventory journal mismatch")
    audit = native.nav_bridge(case["trades"], case["funding"], q,
                              summary["terminal_mark_prices"], sim.account.nav())
    minute = case["minute"]
    daily = minute.filter(native.pl.col("close_us") % DAY == 0)
    if case["targets"].height != 1830:
        raise ValueError("Original recorded target rows incomplete")
    np.testing.assert_array_equal(case["targets"]["target_weight"].to_numpy().reshape(-1, 5), w)
    body = {key: case[key] for key in ("trades", "funding", "rejections", "breaches", "extrema", "target_meta")}
    body.update(summary=summary, targets=case["targets"].to_dicts(), liquidations=case.get("liquidations", []))
    save(state / "ACCOUNT.json", body)
    daily.write_csv(state / "DAILY.csv")
    save(state / "MINUTE_NUMERIC.json", {"columns": api.fingerprint(minute),
                                         "storage": "ALL_ACTUAL_MINUTE_NUMERIC_VALUE_BITS"})
    full = summary["completed_minutes"] == 527040
    nav = np.r_[10000., daily["nav"].to_numpy()]
    returns = np.diff(nav) / nav[:-1]
    rolling = nav[30:] / nav[:-30] - 1 if len(nav) > 30 else np.array([])
    metrics = {"days": len(returns),
               "annual_daily_vol": float(returns.std(ddof=1) * np.sqrt(365)) if len(returns) > 1 else None,
               "worst30": float(rolling.min()) if len(rolling) else None,
               "mean_actual_gross": float(minute["gross_weight"].mean()),
               "max_actual_gross": float(minute["gross_weight"].max()),
               "mean_signed_net": float(minute["net_signed_weight"].mean()),
               "max_abs_signed_net": float(np.abs(minute["net_signed_weight"].to_numpy()).max()),
               "minute_drawdown": summary["all_observation_max_drawdown"]}
    pointer = json.loads((state / "recovery" / "POINTER.json").read_text())
    result = {"status": "COMPLETE_FROZEN_2024_NATIVE_SENSITIVITY" if full else "STOP_PARTIAL_2024_NATIVE_SENSITIVITY",
              "arm": arm, "calendar": [START, END], "days": 366, "summary": summary,
              "metrics": metrics, "full_527040_minutes": full,
              "paid_flat": bool(summary["terminal_cash_realized"]),
              "net_USDT_marked": summary["net_PnL"],
              "paid_cash_return": summary["net_PnL"] / 10000 if summary["terminal_cash_realized"] else None,
              "cumulative_marked_return": summary["net_PnL"] / 10000,
              "genuine_state_hash": pointer["state_hash"],
              "independent_decimal_NAV_bridge": audit,
              "rejection_counts": native.rejection_counts(case["rejections"]),
              "liquidations": case.get("liquidations", []),
              "source_index_SHA256": SOURCE_SHA, "targets_SHA256": TARGET_SHA,
              "quantity_profile_SHA256": PROFILE_SHA,
              "derived_mark_cells": 10,
              "aug12_start_checkpoint_saved": (state / "aug12_start").exists(),
              "new_wallets": 1, "new_fits": 0, "provider_downloads": 0,
              "seconds": time.monotonic() - begin}
    save(state / "RESULT.json", result)
    print("ACTUAL_2024_WALLET_RESULT", arm, result["status"],
          summary["net_PnL"], result["paid_flat"], flush=True)
    del sim, case, minute, daily
    gc.collect()
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", required=True, type=Path)
    parser.add_argument("--prepared", required=True, type=Path)
    parser.add_argument("--targets", required=True, type=Path)
    parser.add_argument("--state", required=True, type=Path)
    parser.add_argument("--arm", required=True, choices=ARMS)
    parser.add_argument("--source-publication-commit", required=True)
    parser.add_argument("--target-publication-commit", required=True)
    parser.add_argument("--parent-go", action="store_true")
    args = parser.parse_args()
    if not args.parent_go:
        parser.error("No financial account without parent source/target publication verification and GO")
    run_one(args.repo, args.prepared, args.targets, args.state, args.arm,
            args.source_publication_commit, args.target_publication_commit)
