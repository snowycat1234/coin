"""Pinned Jesse public hooks, ported to closed-hour COIN target intents."""
from __future__ import annotations

import ast
from collections import namedtuple
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import polars as pl

from . import benchmark_targets_v2 as common
from . import benchmark_targets as original

STRATEGY_ID = "COIN_JESSE_DONCHIAN_1H_SPOT_ADAPTER"
STRATEGY_2H_ID = "COIN_JESSE_DONCHIAN_2H_SPOT_ADAPTER"
HOUR_US = 60 * common.MINUTE_US
VENDOR = common.ROOT / "third_party/jesse_example_donchian"
PINNED_HASHES = {
    "donchian_original.py": "fc635b257ad1e12951dc140dae46a63bd37e9abfa5f2d681ef1e754d8ce393fe",
    "donchian_indicator_original.py": "b7e96ebe3ba476c771a65b353c269a84d02e04587f0d76166c5f322bbbb3a401",
    "LICENSE": "80d873148413a3eb2f96bbe22657bf57ae42046e4d95e81852109c5f3a949d2d",
    "JESSE_LICENSE": "8985ca8447e233f34397a52fe77989c02e27b8145d43bd8c715ae9c7a96056d4",
}


def _load_public_hooks():
    for name, expected in PINNED_HASHES.items():
        common.require(common.file_sha(VENDOR / name) == expected, "Public upstream bytes changed")
    namespace = {
        "np": np, "slice_candles": lambda candles, sequential: candles,
        "DonchianChannel": namedtuple("DonchianChannel", "upperband middleband lowerband"),
    }
    tree = ast.parse((VENDOR / "donchian_indicator_original.py").read_text())
    functions = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "donchian"]
    common.require(len(functions) == 1, "Exactly one pinned indicator function required")
    exec(compile(ast.Module(functions, type_ignores=[]), str(VENDOR / "donchian_indicator_original.py"), "exec"), namespace)
    namespace.update(Strategy=object, utils=None, ta=SimpleNamespace(
        donchian=namespace["donchian"],
        sma=lambda candles, period: float(np.mean(candles[-period:, 2])) if len(candles) >= period else np.nan,
    ))
    tree = ast.parse((VENDOR / "donchian_original.py").read_text())
    classes = [node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == "Donchian"]
    common.require(len(classes) == 1, "Exactly one pinned strategy class required")
    exec(compile(ast.Module(classes, type_ignores=[]), str(VENDOR / "donchian_original.py"), "exec"), namespace)
    return namespace["Donchian"]


def closed_hours(minutes: pl.DataFrame, *, timeframe_minutes: int = 60) -> pl.DataFrame:
    common.require(type(timeframe_minutes) is int and timeframe_minutes in (60, 120), "Only fixed60/120minute public bars")
    bar_us = timeframe_minutes * common.MINUTE_US
    required = {"symbol", "open_us", "high", "low", "close"}
    common.require(required <= set(minutes.columns), "Public strategy requires original minute OHLC")
    common.require(minutes.schema["open_us"] == pl.Int64, "Integer original open timestamps required")
    columns = ["symbol", "open_us", "high", "low", "close"]
    frame = minutes.select(columns + (["available_us"] if "available_us" in minutes.columns else []))
    common.require(frame.height == frame.unique(["symbol", "open_us"]).height, "Duplicate minute input")
    for key in ("high", "low", "close"):
        values = frame[key].to_numpy()
        common.require(np.isfinite(values).all() and np.all(values > 0), "Finite positive minute OHLC required")
    common.require(frame.filter((pl.col("low") > pl.col("close")) | (pl.col("close") > pl.col("high"))).is_empty(), "Consistent minute high/low/close required")
    common.require(np.all(frame["open_us"].to_numpy() % common.MINUTE_US == 0), "Minute-aligned OHLC required")
    if "available_us" not in frame.columns:
        frame = frame.with_columns((pl.col("open_us") + common.MINUTE_US).alias("available_us"))
    common.require(frame.schema["available_us"] == pl.Int64, "Integer availability timestamps required")
    common.require(frame["available_us"].null_count() == 0, "Unknown minute availability must not disappear in hourly max")
    common.require(frame.filter(pl.col("available_us") < pl.col("open_us") + common.MINUTE_US).is_empty(), "Completed candles only")
    hourly = frame.sort(["symbol", "open_us"]).with_columns(
        (pl.col("open_us") // bar_us * bar_us).alias("hour_open_us")
    ).group_by(["symbol", "hour_open_us"], maintain_order=True).agg(
        pl.col("open_us").first().alias("first_us"), pl.col("open_us").last().alias("last_us"),
        pl.len().alias("count"), pl.col("high").max(), pl.col("low").min(),
        pl.col("close").last(), pl.col("available_us").max(),
    ).filter((pl.col("count") == timeframe_minutes) & (pl.col("first_us") == pl.col("hour_open_us")) &
             (pl.col("last_us") == pl.col("hour_open_us") + bar_us - common.MINUTE_US))
    return hourly.with_columns((pl.col("hour_open_us") + bar_us).alias("close_us")).sort(["symbol", "close_us"])


def fixed_targets(minutes: pl.DataFrame, calendar, *, timeframe_minutes: int = 60) -> common.TargetPlan:
    calendar = common.calendar_array(calendar)
    hours = closed_hours(minutes.filter(pl.col("open_us") + common.MINUTE_US <= int(calendar[-1])), timeframe_minutes=timeframe_minutes)
    bar_us = timeframe_minutes * common.MINUTE_US
    PublicRules = _load_public_hooks()
    weights = np.zeros((len(calendar), 2), dtype=np.float64)
    reasons = [["PUBLIC_RULE_FLAT", "PUBLIC_RULE_FLAT"] for _ in calendar]
    warmup_failed = False
    for asset_index, symbol in enumerate(common.SYMBOLS):
        asset = hours.filter(pl.col("symbol") == symbol).sort("close_us")
        stamps = asset["close_us"].to_numpy()
        available = asset["available_us"].to_numpy()
        # Jesse candle layout is timestamp/open/close/high/low/volume. Unused
        # columns are zero; these hooks only read close/high/low.
        candles = np.zeros((len(asset), 6), dtype=np.float64)
        candles[:, 0] = stamps // 1000
        for column, field in ((2, "close"), (3, "high"), (4, "low")):
            candles[:, column] = asset[field].to_numpy()
        rules = PublicRules()
        held, prior_index = False, None
        for row_index, decision in enumerate(calendar):
            index = int(np.searchsorted(stamps, decision, side="right") - 1)
            expected = int(decision) // bar_us * bar_us
            valid = (index >= 199 and int(stamps[index]) == expected and
                     np.all(np.diff(stamps[index - 199:index + 1]) == bar_us) and
                     np.all(available[index - 199:index + 1] <= decision))
            if not valid:
                warmup_failed = True
                reasons[row_index][asset_index] = ("MISSING_OR_UNAVAILABLE_COMPLETE_200_HOURS" if timeframe_minutes == 60
                    else "MISSING_OR_UNAVAILABLE_COMPLETE_200_2H_BARS")
                continue
            if index != prior_index:
                rules.candles = candles[max(0, index - 200):index + 1]
                rules.close = float(candles[index, 2])
                exits = []
                rules.liquidate = lambda: exits.append(True)
                if held:
                    rules.update_position()
                    held = not bool(exits)
                elif rules.should_long() and all(f() for f in rules.filters()):
                    held = True
                prior_index = index
            weights[row_index, asset_index] = .30 if held else 0.
            reasons[row_index][asset_index] = "PUBLIC_RULE_LONG" if held else "PUBLIC_RULE_FLAT"
    if warmup_failed:
        weights[:] = 0.
    weights[-1] = 0.
    identifier = STRATEGY_ID if timeframe_minutes == 60 else STRATEGY_2H_ID
    return original._plan(identifier, calendar, weights, reasons,
        warmup_failed=warmup_failed, metadata={
            "public_upstream_sha256": PINNED_HASHES,
            "timeframe_minutes": timeframe_minutes, "donchian_period": 20, "trend_sma_period": 200,
            "signal_hooks_reused_unmodified": True, "native_Jesse_engine_replicated": False,
            "adaptations": ["fixed closed1h" if timeframe_minutes == 60 else "fixed closed2h", "SMA NumPy mean port", "common COIN risk and sizing", "common COIN proxy execution"],
            "upstream_balance_sizing_called": False, "model_fits": 0,
        })
