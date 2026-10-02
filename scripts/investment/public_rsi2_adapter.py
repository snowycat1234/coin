"""Fixed long-only closed1h intents from the pinned public RSI2 hooks.

The official scalar RSI initialization window is guarded in full. Sizing,
received-asset fees, fills and economic acceptance belong to the common runner.
"""
from __future__ import annotations

import ast
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import polars as pl

from scripts.investment import public_donchian_hybrid as shared
from scripts.investment import public_rsi2_indicator as indicator
from scripts.research_v8 import public_donchian_adapter as public

common, original = public.common, public.original
STRATEGY_ID = "COIN_JESSE_RSI2_1H_SPOT_ADAPTER"
VENDOR = common.ROOT / "third_party/jesse_example_rsi2"
RAW_STRATEGY_SHA256 = "fd463da53b6ac78138a0886268f654973daa569dd2094c6aa96796a8a5015f70"
PINNED_HASHES = {
    "rsi2_original.py": RAW_STRATEGY_SHA256,
    "LICENSE": "80d873148413a3eb2f96bbe22657bf57ae42046e4d95e81852109c5f3a949d2d",
    "JESSE_LICENSE": "8985ca8447e233f34397a52fe77989c02e27b8145d43bd8c715ae9c7a96056d4",
}
BASE_ADAPTER_SHA256 = "169d7ba6ebde24be5ce4730c5e741ed281a0155e4cadc22f1bb2bedccb4093c2"
SHARED_STREAM_SHA256 = "80e4b24319becacefb0d6c9551473e3d4214cf3167ae45f5ac8ff7f559c27d68"
# The exact upstream non-sequential scalar window is also checked against the
# indicator shim. This is not an alternative tuned RSI initialization period.
SCALAR_CANDLE_WINDOW = 240


def _load_public_hooks():
    for name, expected in PINNED_HASHES.items():
        common.require(common.file_sha(VENDOR / name) == expected, "Pinned public RSI2 bytes changed")
    common.require(indicator.SCALAR_CANDLE_WINDOW == SCALAR_CANDLE_WINDOW,
                   "Official scalar RSI initialization window changed")
    # Reuse the already accepted SMA adapter; no new indicator implementation.
    PublicDonchian = public._load_public_hooks()
    accepted_sma = PublicDonchian.ma_trend.fget.__globals__["ta"].sma

    class Context:
        def __init__(self):
            self.vars = {}

    namespace = dict(Strategy=Context, utils=None,
                     ta=SimpleNamespace(sma=accepted_sma, rsi=indicator.rsi))
    tree = ast.parse((VENDOR / "rsi2_original.py").read_text())
    classes = [node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == "RSI2"]
    common.require(len(classes) == 1, "Exactly one pinned RSI2 strategy class required")
    exec(compile(ast.Module(classes, type_ignores=[]), str(VENDOR / "rsi2_original.py"), "exec"), namespace)
    return namespace["RSI2"]


def _closed_index(stream, decision: int):
    stamps, availability, _ = stream
    index = int(np.searchsorted(stamps, decision, side="right") - 1)
    first = index - SCALAR_CANDLE_WINDOW + 1
    valid = (first >= 0 and int(stamps[index]) == decision // public.HOUR_US * public.HOUR_US
             and np.all(np.diff(stamps[first:index + 1]) == public.HOUR_US)
             and np.all(availability[first:index + 1] <= decision))
    return valid, index


def fixed_targets(minutes: pl.DataFrame, calendar) -> common.TargetPlan:
    calendar = common.calendar_array(calendar)
    base_path = common.ROOT / "scripts/research_v8/public_donchian_adapter.py"
    shared_path = common.ROOT / "scripts/investment/public_donchian_hybrid.py"
    common.require(common.file_sha(base_path) == BASE_ADAPTER_SHA256,
                   "Preserved closed-hour/SMA adapter bytes changed")
    common.require(common.file_sha(shared_path) == SHARED_STREAM_SHA256,
                   "Preserved hourly stream adapter bytes changed")
    common.require({"symbol", "open_us"} <= set(minutes.columns), "Original minute source required")
    common.require(set(minutes["symbol"].unique().to_list()) == set(common.SYMBOLS),
                   "Same two-symbol source required")
    signal = minutes.filter(pl.col("open_us") + common.MINUTE_US <= int(calendar[-1]))
    common._integer_timestamp_columns(signal, ("open_us",))
    if "available_us" in signal.columns:
        common._integer_timestamp_columns(signal, ("available_us",))
    valid = pl.lit(True)
    for flag in ("minute_valid", "valid_day"):
        if flag in signal.columns:
            common.require(signal.schema[flag] == pl.Boolean, "Original Boolean validity required")
            valid = valid & pl.col(flag).fill_null(False)
    hours = public.closed_hours(signal.filter(valid), timeframe_minutes=60)
    Rules = _load_public_hooks()
    weights = np.zeros((len(calendar), len(common.SYMBOLS)), dtype=np.float64)
    reasons = [["RSI2_FLAT", "RSI2_FLAT"] for _ in calendar]
    warmup_failed = False
    for asset_index, symbol in enumerate(common.SYMBOLS):
        stream, rules = shared._stream(hours, symbol), Rules()
        common.require(rules.vars == dict(fast_sma_period=5, slow_sma_period=200,
            rsi_period=2, rsi_ob_threshold=90, rsi_os_threshold=10), "Fixed upstream RSI2 parameters required")
        held = False
        for row, stamp in enumerate(calendar):
            decision = int(stamp)
            available, index = _closed_index(stream, decision)
            if not available:
                warmup_failed, held = True, False
                reasons[row][asset_index] = "MISSING_OR_UNAVAILABLE_CONTIGUOUS_240_CLOSED_HOURS"
                continue
            exited, entered = False, False
            if int(stream[0][index]) == decision:
                rules.candles = stream[2][index - SCALAR_CANDLE_WINDOW + 1:index + 1]
                rules.price = float(stream[2][index, 2])  # Completed close, not an intrabar ticker.
                rules.is_long, rules.is_short = held, False
                if held:
                    exits = []
                    rules.liquidate = lambda: exits.append(True)
                    rules.update_position()  # Original close>SMA5 long-only exit.
                    if exits:
                        held, exited = False, True
                if not held and not exited and rules.should_long():
                    held, entered = True, True
            weights[row, asset_index] = .30 if held else 0.
            reasons[row][asset_index] = ("RSI2_PUBLIC_1H_EXIT_NO_SAME_STAMP_REENTRY" if exited
                else "RSI2_PUBLIC_1H_ENTRY" if entered else "RSI2_LONG" if held else "RSI2_FLAT")
    weights[-1] = 0.
    reasons[-1] = ["COMMON_TERMINAL_EXIT_INTENT_NEEDS_FEASIBLE_FILL"] * 2
    paths = (Path(__file__), Path(indicator.__file__), base_path, shared_path,
             common.ROOT / "scripts/research_v8/benchmark_targets.py",
             common.ROOT / "scripts/research_v8/benchmark_targets_v2.py")
    source_hashes = {str(path.relative_to(common.ROOT)): common.file_sha(path) for path in paths}
    return common._version(original._plan(STRATEGY_ID, calendar, weights, reasons,
        warmup_failed=warmup_failed, metadata={
            "source_hashes": source_hashes, "raw_strategy_sha256": RAW_STRATEGY_SHA256,
            "public_upstream_sha256": PINNED_HASHES,
            "public_example_commit": "7c91e0a37bf62165790120d730442e4f6eb00364",
            "public_indicator_commit": "417f8765225e3bfc12043d4b712f19fe15a3c078",
            "public_upstream_license": "MIT", "signal_hooks_reused_unmodified": True,
            "timeframe_minutes": 60, "rsi_period": 2, "entry_rsi_threshold": 10,
            "entry_trend_sma_period": 200, "exit_sma_period": 5,
            "official_scalar_candle_window": SCALAR_CANDLE_WINDOW,
            "continuous_availability_guard_bars": SCALAR_CANDLE_WINDOW,
            "rsi_initialization": "OFFICIAL_SCALAR_KERNEL_ON_EACH_CLOSED_240_BAR_WINDOW",
            "sma_implementation": "REUSE_ACCEPTED_169D_PUBLIC_ADAPTER_NUMPY_MEAN_PORT",
            "long_only": True, "upstream_balance_sizing_called": False,
            "same_stamp_priority": "HELD_EXIT_FIRST_NO_REENTRY",
            "entry_eligibility_restores": "NEXT_NEW_CLOSED_1H_BAR_NO_EXTRA_COOLDOWN",
            "missing_policy": "WHOLE_PAIRED_FOLD_NOT_EVALUABLE_NO_EXECUTION",
            "failure_target_difference_from_preserved_public":
                "Causal earlier intents retained; future source failure never retroactively zeros earlier targets",
            "model_fits": 0, "native_Jesse_engine_replicated": False,
        }))
