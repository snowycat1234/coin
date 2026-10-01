"""Sealed development-only input path for the single nonlinear V2 study."""

from __future__ import annotations

import json

import polars as pl

from .data import verify_dataset_lock
from .features_v2 import build_features_v2
from .operations import date_us
from .paths import ROOT


def development_files(lock: dict) -> tuple[list, list]:
    """Select permitted monthly members before opening any minute price file."""
    minutes = [
        ROOT / name for name in sorted(lock["minute_files"]) if (ROOT / name).stem < "2026-03"
    ]
    hours = [
        ROOT / name for name in sorted(lock["bar_files"]) if (ROOT / name).name == "1h.parquet"
    ]
    if len(minutes) != 100 or len(hours) != 2:
        raise RuntimeError("Sealed development inputs must contain 100 months and two hourly files")
    for path in minutes + hours:
        if not path.resolve().is_relative_to(ROOT / "data"):
            raise RuntimeError("Dataset member escaped D project data")
    return minutes, hours


def load_development(lock: dict) -> tuple[pl.DataFrame, pl.DataFrame, dict]:
    minutes, hours = development_files(lock)
    cutoff = date_us("2026-03-01")
    minute_frame = (
        pl.scan_parquet(minutes)
        .filter(pl.col("valid_day") & (pl.col("open_us") < cutoff))
        .select("symbol", "open_us", "open", "close", "quote_volume")
        .collect(engine="streaming")
        .sort("symbol", "open_us")
    )
    hour_frame = (
        pl.scan_parquet(hours)
        .filter(pl.col("available_us") < cutoff)
        .collect(engine="streaming")
        .sort("available_us", "symbol")
    )
    return (
        minute_frame,
        hour_frame,
        {
            "dataset_id": lock["dataset_id"],
            "minute_files": {
                str(path.relative_to(ROOT)): lock["minute_files"][str(path.relative_to(ROOT))]
                for path in minutes
            },
            "hour_files": {
                str(path.relative_to(ROOT)): lock["bar_files"][str(path.relative_to(ROOT))]
                for path in hours
            },
            "locked_month_price_files_opened": 0,
            "hourly_price_filter": "available_us < 2026-03-01 UTC pushed into scan",
            "minute_rows": len(minute_frame),
            "hour_rows": len(hour_frame),
        },
    )


def run_command(args) -> dict:
    from .disk import check
    from .research_v2 import run_research_v2
    from .resources import status

    status()
    check(reserve=1_500_000_000)
    lock = verify_dataset_lock()
    minutes, bars, inputs = load_development(lock)
    print(
        json.dumps(
            {
                "phase": "sealed_development_loaded",
                "dataset_id": inputs["dataset_id"],
                "minute_files": len(inputs["minute_files"]),
                "locked_month_price_files_opened": 0,
                "minute_rows": len(minutes),
                "hour_rows": len(bars),
            }
        ),
        flush=True,
    )
    features = build_features_v2(bars)
    print(json.dumps({"phase": "40_causal_features_built", "rows": len(features)}), flush=True)
    report = run_research_v2(
        ROOT / "configs/experiments/nonlinear_v2.json",
        features,
        minutes,
        bars,
        dataset_id=lock["dataset_id"],
        resume_reason=args.resume_reason,
        progress=lambda event: print(json.dumps(event, allow_nan=False), flush=True),
    )
    return {
        key: report[key]
        for key in (
            "status",
            "cv_days",
            "fit_count",
            "final_fit_count",
            "frozen_candidate",
            "resources",
            "disk",
        )
    }
