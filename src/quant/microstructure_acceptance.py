"""Reproducible A07 storage probe and bounded public-network smoke; no alpha claim."""

from __future__ import annotations

import asyncio
import hashlib
import json
import random
import resource
import time
from pathlib import Path

import polars as pl

from . import resources
from .microstructure import (
    FEATURES,
    SECOND,
    SYMBOLS,
    MicrostructureConfig,
    aggregate_seconds,
    collect_microstructure,
    compact_frame,
    read_microstructure_status,
)
from .paths import ROOT, STATE, utc_now_us


def storage_probe(folder: Path, seeds=(20261001, 20261002, 20261003)) -> dict:
    """Three dense high-entropy 600s chunks, using the actual production Parquet schema."""
    if not folder.resolve().is_relative_to(ROOT.resolve()):
        raise ValueError("Probe artifacts require D ROOT")
    folder.mkdir(parents=True, exist_ok=True)
    chunks = []
    for seed in seeds:
        generator = random.Random(seed)
        all_rows = []
        by_symbol = {}
        for symbol in SYMBOLS:
            rows = []
            for second in range(600):
                stamp = (1_790_812_800 + second) * SECOND
                mid = (65000 if symbol == "BTCUSDT" else 2800) * (
                    1 + generator.uniform(-0.01, 0.01)
                )
                buy, sell = generator.uniform(0, 100000), generator.uniform(0, 100000)
                values = (
                    mid,
                    generator.uniform(0.001, 5),
                    generator.uniform(0, 100),
                    generator.uniform(0, 100),
                    generator.uniform(-1, 1),
                    generator.uniform(-1, 1),
                    generator.uniform(-3, 3),
                    generator.randrange(1, 5000),
                    generator.randrange(0, 1000),
                    generator.randrange(0, 1000),
                    generator.uniform(-1000, 1000),
                    generator.randrange(1, 500),
                    buy,
                    sell,
                    (buy - sell) / (buy + sell),
                    mid * (1 + generator.uniform(-0.0001, 0.0001)),
                    generator.uniform(-0.001, 0.001),
                )
                rows.append(
                    {
                        "symbol": symbol,
                        "open_us": stamp,
                        "close_us": stamp + SECOND,
                        "available_us": stamp + SECOND + generator.randrange(10000),
                        "interval_s": 1,
                        "received_first_us": stamp + generator.randrange(10000),
                        "received_last_us": stamp + generator.randrange(900000, 999999),
                        "event_first_us": stamp + generator.randrange(10000),
                        "event_last_us": stamp + generator.randrange(800000, 950000),
                        "trade_first_us": stamp + generator.randrange(10000),
                        "trade_last_us": stamp + generator.randrange(800000, 950000),
                        "quality": 0,
                        "known_seconds": 1,
                        "valid_seconds": 1,
                        "session": "storage_probe_synthetic",
                        "version": "microstructure_l1_v1",
                        "mode": "engineering",
                        **dict(zip(FEATURES, values, strict=True)),
                    }
                )
            by_symbol[symbol] = rows
            all_rows.extend(rows)
        groups = {1: all_rows}
        for interval in (5, 30, 60):
            groups[interval] = [
                aggregate_seconds(rows[start : start + interval], interval)
                for rows in by_symbol.values()
                for start in range(0, 600, interval)
            ]
        sizes = {}
        for interval, rows in groups.items():
            target = folder / f"synthetic-{seed}-{interval}s.parquet"
            if target.exists():
                raise FileExistsError("A storage probe never overwrites a previous artifact")
            frame = compact_frame(rows)
            frame.write_parquet(target, compression="zstd", compression_level=3, statistics=False)
            restored = pl.read_parquet(target)
            if frame.schema != restored.schema or frame.height != restored.height:
                raise RuntimeError("Parquet roundtrip schema mismatch")
            sizes[str(interval)] = {
                "bytes": target.stat().st_size,
                "rows": frame.height,
                "sha256": hashlib.sha256(target.read_bytes()).hexdigest(),
            }
        chunks.append(
            {
                "seed": seed,
                "seconds": 600,
                "intervals": sizes,
                "total_bytes": sum(item["bytes"] for item in sizes.values()),
            }
        )
    daily = max(chunk["total_bytes"] for chunk in chunks) * 144
    projected = daily * 180
    conservative = int(projected * 1.2) + 200_000_000
    return {
        "provenance": "engineering_synthetic_high_entropy",
        "chunks": chunks,
        "production_chunk_seconds": 600,
        "projected_daily_feature_bytes": daily,
        "projected_180d_feature_bytes": projected,
        "with_20_percent_margin_and_200MB_ledger": conservative,
        "target_bytes": 8_000_000_000,
        "projection_pass": conservative <= 8_000_000_000,
        "actual_24h_measurement_completed": False,
        "real_time_or_profit_qualification": False,
    }


async def short_network_smoke(seconds=60) -> dict:
    token = str(utc_now_us())
    config = MicrostructureConfig(
        db_path=STATE / f"micro-smoke-{token}.sqlite3", store=ROOT / "data" / f"micro-smoke-{token}"
    )
    wall, cpu = time.monotonic(), time.process_time()
    initial_resources = resources.status()
    result = await collect_microstructure(config, run_seconds=seconds)
    final = read_microstructure_status(config.db_path)
    intervals = {}
    for interval in (1, 5, 30, 60):
        paths = list((config.store / "features" / f"{interval}s").glob("*.parquet"))
        if not paths:
            intervals[str(interval)] = {"rows": 0}
            continue
        rows = pl.scan_parquet(paths).collect()
        intervals[str(interval)] = {
            "rows": rows.height,
            "symbols": rows["symbol"].unique().to_list(),
            "quality": rows.group_by("quality").len().sort("quality").to_dicts(),
            "source_modes": rows["mode"].unique().to_list(),
            "first_bucket_us": rows["open_us"].min(),
            "last_bucket_us": rows["open_us"].max(),
            "quote_updates": rows["quote_update_count"].sum(),
            "aggregate_trades": rows["agg_trade_count"].sum(),
        }
    one = intervals["1"]
    passed = (
        result["accepted_events"] > 0
        and result["rejected_events"] == 0
        and set(one.get("symbols", [])) == set(SYMBOLS)
        and one.get("quote_updates", 0) > 0
        and one.get("aggregate_trades", 0) > 0
        and final["state"] == "STOPPED"
    )
    return {
        "status": "SHORT_PUBLIC_SMOKE_PASS" if passed else "SHORT_PUBLIC_SMOKE_FAIL",
        "duration_requested_seconds": seconds,
        "total_wall_seconds": time.monotonic() - wall,
        "cpu_seconds": time.process_time() - cpu,
        "process_peak_rss_bytes": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024,
        "resource_before": initial_resources,
        "resource_after": resources.status(),
        "runtime": result,
        "persistent": final,
        "intervals": intervals,
        "state_db": str(config.db_path),
        "store": str(config.store),
        "credentials_used": False,
        "orders": 0,
        "actual_24h_pass": False,
        "actual_14_or_30d_pass": False,
        "long_running_process_started": False,
    }


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--smoke-seconds", type=float, default=0)
    args = parser.parse_args()
    resources.status()
    folder = ROOT / "reports/generated" / f"A07_probe_{utc_now_us()}"
    report = {"module": "A07", "created_us": utc_now_us(), "storage": storage_probe(folder)}
    if args.smoke_seconds:
        report["public_smoke"] = asyncio.run(short_network_smoke(args.smoke_seconds))
    report["source_sha256"] = hashlib.sha256(
        Path(__file__).with_name("microstructure.py").read_bytes()
    ).hexdigest()
    target = folder / "acceptance.json"
    target.write_text(json.dumps(report, indent=2))
    print(
        json.dumps(
            {
                "report": str(target),
                "projection_pass": report["storage"]["projection_pass"],
                "smoke": report.get("public_smoke", {}).get("status"),
            }
        )
    )
