"""Fixed 2h-entry/1h-exit composition of the preserved pinned Jesse hooks.

Target intents only. This changes both exit frequency and its physical lookback;
it is not a pure exit-latency experiment or an executable-profit claim.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import polars as pl

from scripts.research_v8 import public_donchian_adapter as public

common, original = public.common, public.original
STRATEGY_ID = "COIN_JESSE_DONCHIAN_2H_ENTRY_1H_EXIT_SPOT_ADAPTER"
BASE_ADAPTER_SHA256 = "169d7ba6ebde24be5ce4730c5e741ed281a0155e4cadc22f1bb2bedccb4093c2"
WARMUP_BARS = 200


def _stream(hours: pl.DataFrame, symbol: str):
    bars = hours.filter(pl.col("symbol") == symbol).sort("close_us")
    stamps = bars["close_us"].to_numpy()
    candles = np.zeros((len(bars), 6), dtype=np.float64)
    candles[:, 0] = stamps // 1000  # Original Jesse timestamp/open/close/high/low/volume.
    for column, field in ((2, "close"), (3, "high"), (4, "low")):
        candles[:, column] = bars[field].to_numpy()
    return stamps, bars["available_us"].to_numpy(), candles


def _closed_index(stream, decision: int, period: int):
    stamps, available, _ = stream
    index = int(np.searchsorted(stamps, decision, side="right") - 1)
    expected = decision // period * period
    valid = (index >= WARMUP_BARS - 1 and int(stamps[index]) == expected and
             np.all(np.diff(stamps[index - WARMUP_BARS + 1:index + 1]) == period) and
             np.all(available[index - WARMUP_BARS + 1:index + 1] <= decision))
    return valid, index


def _context(rules, stream, index):
    candles = stream[2]
    rules.candles = candles[max(0, index - WARMUP_BARS):index + 1]
    rules.close = float(candles[index, 2])


def fixed_targets(minutes: pl.DataFrame, calendar) -> common.TargetPlan:
    calendar = common.calendar_array(calendar)
    base_path = common.ROOT / "scripts/research_v8/public_donchian_adapter.py"
    common.require(common.file_sha(base_path) == BASE_ADAPTER_SHA256,
                   "Preserved pinned public adapter bytes changed")
    common.require({"symbol", "open_us"} <= set(minutes.columns), "Original minute source required")
    common.require(set(minutes["symbol"].unique().to_list()) == set(common.SYMBOLS),
                   "Same two-symbol source required")
    # Only complete minutes through the last decision enter signal aggregation.
    # The caller retains its full execution/valuation source independently.
    signal = minutes.filter(pl.col("open_us") + common.MINUTE_US <= int(calendar[-1]))
    common._integer_timestamp_columns(signal, ("open_us",))
    if "available_us" in signal.columns:
        common._integer_timestamp_columns(signal, ("available_us",))
    valid = pl.lit(True)
    for flag in ("minute_valid", "valid_day"):
        if flag in signal.columns:
            common.require(signal.schema[flag] == pl.Boolean, "Original Boolean minute validity required")
            valid = valid & pl.col(flag).fill_null(False)
    signal = signal.filter(valid)
    entry_bars = public.closed_hours(signal, timeframe_minutes=120)
    exit_bars = public.closed_hours(signal, timeframe_minutes=60)
    Rules = public._load_public_hooks()
    weights = np.zeros((len(calendar), len(common.SYMBOLS)), dtype=np.float64)
    reasons = [["HYBRID_FLAT", "HYBRID_FLAT"] for _ in calendar]
    warmup_failed = False
    for asset_index, symbol in enumerate(common.SYMBOLS):
        entry, exit_ = _stream(entry_bars, symbol), _stream(exit_bars, symbol)
        entry_rules, exit_rules = Rules(), Rules()
        held = False
        for row, stamp in enumerate(calendar):
            decision = int(stamp)
            entry_valid, entry_index = _closed_index(entry, decision, 2 * public.HOUR_US)
            exit_valid, exit_index = _closed_index(exit_, decision, public.HOUR_US)
            if not entry_valid or not exit_valid:
                warmup_failed, held = True, False
                reasons[row][asset_index] = "MISSING_OR_UNAVAILABLE_CONTIGUOUS_200_2H_AND_1H_BARS"
                continue
            new_entry = int(entry[0][entry_index]) == decision
            new_exit = int(exit_[0][exit_index]) == decision
            exited = False
            if held and new_exit:
                _context(exit_rules, exit_, exit_index)
                exits = []
                exit_rules.liquidate = lambda: exits.append(True)
                exit_rules.update_position()  # Original prior20 lower-channel hook; no SMA exit.
                if exits:
                    held, exited = False, True
            # Exit has priority; no same-decision reentry and no added cooldown.
            # Eligibility returns at the next new closed2h event, even 1h later.
            if not held and new_entry and not exited:
                _context(entry_rules, entry, entry_index)
                if entry_rules.should_long() and all(check() for check in entry_rules.filters()):
                    held = True
                    reasons[row][asset_index] = "HYBRID_PUBLIC_2H_ENTRY"
            if exited:
                reasons[row][asset_index] = "HYBRID_PUBLIC_1H_EXIT_NO_SAME_STAMP_REENTRY"
            elif reasons[row][asset_index] != "HYBRID_PUBLIC_2H_ENTRY":
                reasons[row][asset_index] = "HYBRID_LONG" if held else "HYBRID_FLAT"
            weights[row, asset_index] = .30 if held else 0.
    # Same predeclared terminal policy as the preserved public targets. It is
    # an intent needing a feasible costed fill, not an assumed liquidation.
    weights[-1] = 0.
    reasons[-1] = ["COMMON_TERMINAL_EXIT_INTENT_NEEDS_FEASIBLE_FILL"] * 2
    source_hashes = {
        "scripts/investment/public_donchian_hybrid.py": common.file_sha(Path(__file__)),
        "scripts/research_v8/public_donchian_adapter.py": common.file_sha(base_path),
        "scripts/research_v8/benchmark_targets.py": common.file_sha(common.ROOT / "scripts/research_v8/benchmark_targets.py"),
        "scripts/research_v8/benchmark_targets_v2.py": common.file_sha(common.ROOT / "scripts/research_v8/benchmark_targets_v2.py"),
    }
    return common._version(original._plan(STRATEGY_ID, calendar, weights, reasons,
        warmup_failed=warmup_failed, metadata={
            "public_upstream_sha256": public.PINNED_HASHES, "source_hashes": source_hashes,
            "entry_timeframe_minutes": 120, "exit_timeframe_minutes": 60,
            "donchian_period": 20, "entry_trend_sma_period": 200,
            "continuous_warmup_bars_per_timeframe": WARMUP_BARS,
            "signal_hooks_reused_unmodified": True, "native_Jesse_engine_replicated": False,
            "upstream_balance_sizing_called": False, "model_fits": 0,
            "same_stamp_priority": "HELD_EXIT_FIRST_NO_REENTRY",
            "entry_eligibility_restores": "NEXT_NEW_CLOSED_2H_BAR_NO_EXTRA_COOLDOWN",
            "diagnostic_scope": "JOINT_EXIT_FREQUENCY_AND_40H_TO_20H_LOOKBACK_NOT_PURE_LATENCY",
            "missing_policy": "WHOLE_PAIRED_FOLD_NOT_EVALUABLE_NO_EXECUTION",
            "failure_target_difference_from_preserved_public":
                "Causal earlier intents retained; future source failure never retroactively zeros earlier targets",
        }))
