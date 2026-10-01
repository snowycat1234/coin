"""Explicit A02 development-only canonical run; launch through bounded.sh."""

import json
import os
import time

import polars as pl

from quant.backtest import BacktestConfig
from quant.baselines_v2 import LOCKED_HISTORICAL_START_US, _v2_preflight, run_baseline_suite
from quant.data import verify_dataset_lock
from quant.paths import ROOT
from quant.resources import status


def main():
    if os.environ.get("WSL_DISTRO_NAME") != "hpc_linux":
        raise RuntimeError("Only D-hosted hpc_linux is supported")
    started = time.monotonic()
    config = BacktestConfig(
        latency_minutes=1, start_us=1_643_673_600_000_000,
        end_us=LOCKED_HISTORICAL_START_US,
    )
    _v2_preflight(config, ROOT / "reports/A01_EXECUTION_PARITY_ACCEPTANCE.json")
    lock = verify_dataset_lock()
    minute_files = sorted(
        file for symbol in ("BTCUSDT", "ETHUSDT")
        for file in (ROOT / "data/normalized/spot" / symbol / "1m").glob("*.parquet")
        if file.stem < "2026-03"
    )
    assert minute_files and all(file.stem < "2026-03" for file in minute_files)
    minutes = (
        pl.scan_parquet(minute_files).filter(pl.col("valid_day"))
        .select("symbol", "open_us", "open", "close", "quote_volume")
        .collect()
    )
    hourly = (
        pl.scan_parquet([
            ROOT / "data/bars/spot" / symbol / "1h.parquet"
            for symbol in ("BTCUSDT", "ETHUSDT")
        ])
        .filter(pl.col("available_us") < LOCKED_HISTORICAL_START_US).collect()
    )
    print(json.dumps({"phase": "development_data_loaded", "minute_files": len(minute_files),
                      "minute_rows": minutes.height, "hour_rows": hourly.height,
                      "locked_month_file_reads": 0}), flush=True)
    output = ROOT / "reports/generated/P03_STRONG_BASELINES_V2"
    report = run_baseline_suite(
        hourly, minutes, config, output_dir=output, dataset_id=lock["dataset_id"],
    )
    runtime = {
        "seconds": time.monotonic() - started, "resources": status(),
        "minute_files": [str(path.relative_to(ROOT)) for path in minute_files],
        "locked_month_file_reads": 0,
    }
    (output / "RUN_RESOURCES.json").write_text(
        json.dumps(runtime, indent=2, ensure_ascii=False) + "\n", encoding="utf-8",
    )
    print(json.dumps({"phase": "completed", "status": report["status"],
                      "seconds": runtime["seconds"], "output": str(output)},
                     ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
