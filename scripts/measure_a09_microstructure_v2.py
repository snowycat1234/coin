"""Real public short smoke plus finite synthetic storage observation for A09 v2."""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import math
import os
import random
import resource
import time
from datetime import UTC, datetime
from pathlib import Path

import polars as pl

from quant import disk, resources
from quant.microstructure_v2 import (
    FEATURES,
    INVALID,
    SECOND,
    SYMBOLS,
    VERSION,
    MicrostructureConfig,
    aggregate_seconds,
    collect_microstructure,
    compact_frame,
    read_microstructure_status,
)
from quant.paths import ROOT, STATE, utc_now_us


def require(ok, reason):
    if not ok:
        raise ValueError(reason)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def frozen():
    name = ROOT / "reports/A07_MICROSTRUCTURE_ACCEPTANCE.json"
    require(sha(name) == "d0acb843b0f616e777ddeb698245a2e5d5cf10b03a0baf1718b295094f894517",
            "Frozen v1 receipt changed")
    source = json.loads(name.read_text())["source_hashes"]
    for relative, checksum in source.items():
        require(sha(ROOT / relative) == checksum, "Frozen v1 source changed: " + relative)
    return source


def synthetic_row(generator, symbol, second):
    opened = (1_790_812_800 + second) * SECOND
    mid = (65_000 if symbol == "BTCUSDT" else 2_800) * (1 + generator.uniform(-.01, .01))
    bid_quantity, ask_quantity = generator.uniform(0, 100), generator.uniform(0, 100)
    buys, sells = generator.uniform(0, 100_000), generator.uniform(0, 100_000)
    spread = generator.uniform(.001, 5)
    values = {
        "mid": mid, "spread_bps": generator.uniform(.001, 5),
        "bid_qty_mean": generator.uniform(0, 100), "ask_qty_mean": generator.uniform(0, 100),
        "L1_imbalance_mean": generator.uniform(-1, 1),
        "L1_imbalance_last": (bid_quantity - ask_quantity) / (bid_quantity + ask_quantity),
        "microprice_offset_bps_mean": generator.uniform(-3, 3),
        "quote_update_count": generator.randrange(1, 5000),
        "bid_price_change_count": generator.randrange(0, 1000),
        "ask_price_change_count": generator.randrange(0, 1000),
        "OFI_L1": generator.uniform(-1000, 1000),
        "agg_trade_count": generator.randrange(1, 500),
        "aggressive_buy_notional": buys, "aggressive_sell_notional": sells,
        "trade_flow_imbalance": (buys - sells) / (buys + sells),
        "trade_vwap": mid * (1 + generator.uniform(-.0001, .0001)),
        "realized_return_1s": generator.uniform(-.001, .001),
        "spread_bps_last": spread, "l1_total_depth_last": bid_quantity + ask_quantity,
    }
    require(set(values) == set(FEATURES), "V2 synthetic feature contract mismatch")
    return {
        "symbol": symbol, "open_us": opened, "close_us": opened + SECOND,
        "available_us": opened + SECOND + generator.randrange(10_000),
        "interval_s": 1, "received_first_us": opened + generator.randrange(10_000),
        "received_last_us": opened + generator.randrange(900_000, 999_999),
        "event_first_us": opened + generator.randrange(10_000),
        "event_last_us": opened + generator.randrange(800_000, 950_000),
        "trade_first_us": opened + generator.randrange(10_000),
        "trade_last_us": opened + generator.randrange(800_000, 950_000),
        "quality": 0, "known_seconds": 1, "valid_seconds": 1,
        "session": "synthetic_storage_a09_v2", "version": VERSION, "mode": "engineering",
        **values,
    }


def storage_probe(folder):
    folder.mkdir()
    chunks = []
    for seed in (20261001, 20261002, 20261003):
        generator = random.Random(seed)
        by_symbol = {symbol: [synthetic_row(generator, symbol, second) for second in range(600)]
                     for symbol in SYMBOLS}
        groups = {1: [row for rows in by_symbol.values() for row in rows]}
        for interval in (5, 30, 60):
            groups[interval] = [aggregate_seconds(rows[offset:offset + interval], interval)
                                for rows in by_symbol.values()
                                for offset in range(0, 600, interval)]
        sizes = {}
        for interval, rows in groups.items():
            target = folder / f"synthetic-{seed}-{interval}s.parquet"
            require(not target.exists(), "Do not overwrite synthetic evidence")
            frame = compact_frame(rows)
            frame.write_parquet(target, compression="zstd", compression_level=3, statistics=False)
            restored = pl.read_parquet(target)
            require(frame.equals(restored) and frame.schema == restored.schema,
                    "Exact v2 Parquet roundtrip mismatch")
            require(all(field in restored.columns for field in
                        ("spread_bps_last", "l1_total_depth_last")), "Missing v2 last fields")
            sizes[str(interval)] = {"path": str(target.relative_to(ROOT)),
                                    "bytes": target.stat().st_size, "rows": frame.height,
                                    "sha256": sha(target)}
        chunks.append({"seed": seed, "seconds": 600, "intervals": sizes,
                       "total_bytes": sum(item["bytes"] for item in sizes.values())})
    daily = max(item["total_bytes"] for item in chunks) * 144
    projection = (daily * 180 * 13 + 9) // 10
    return {"provenance": "synthetic_dense_high_entropy_engineering", "chunks": chunks,
            "daily_whole_files_projection_bytes": daily,
            "conditional_180d_with_30_percent_margin_bytes": projection,
            "feature_cap_bytes": 8_000_000_000,
            "finite_projection_within_cap": projection <= 8_000_000_000,
            "actual_180d_observed": False, "native_and_total_capacity_accepted": False,
            "limitation": "Finite synthetic samples; no real full UTC day or worst-case guarantee. "
                          "If over cap, retain failure; actual 24h capacity remains pending. "
                          "Native/raw/whole project+entire VHD assessed separately."}


async def smoke(config, seconds):
    result = await collect_microstructure(config, run_seconds=seconds)
    final = read_microstructure_status(config.db_path)
    require(result["version"] == VERSION == "microstructure_l1_v2", "Wrong live v2 version")
    require(result["accepted_events"] > 0 and final["state"] == "STOPPED", "No closed live smoke")
    intervals = {}
    for interval in (1, 5, 30, 60):
        paths = list((config.store / "features" / f"{interval}s").glob("*.parquet"))
        require(0 < len(paths) <= 20, "Missing/excessive short-smoke exports")
        frame = pl.read_parquet(paths)
        require(set(frame["symbol"].unique()) == set(SYMBOLS)
                and frame["version"].unique().to_list() == [VERSION]
                and frame["mode"].unique().to_list() == ["live"], "Wrong live provenance")
        mid_field = "mid" if interval == 1 else "mid_last"
        usable = frame.filter((pl.col("quality") & INVALID) == 0)
        reconstruction_count = 0
        for row in usable.select(mid_field, "spread_bps_last", "l1_total_depth_last",
                                 "L1_imbalance_last").iter_rows(named=True):
            mid, spread, depth, imbalance = (row[key] for key in
                                           (mid_field, "spread_bps_last", "l1_total_depth_last",
                                            "L1_imbalance_last"))
            if any(value is None for value in (mid, spread, depth, imbalance)):
                continue
            bid, ask = mid * (1 - spread / 20_000), mid * (1 + spread / 20_000)
            bq, aq = depth * (1 + imbalance) / 2, depth * (1 - imbalance) / 2
            require(all(math.isfinite(value) for value in (bid, ask, bq, aq))
                    and 0 < bid <= ask and bq >= 0 and aq >= 0,
                    "Invalid reconstructed v2 BBO")
            reconstruction_count += 1
        if interval in (1, 5):
            require(reconstruction_count > 0, "No usable reconstructed live BBO")
        intervals[str(interval)] = {
            "rows": frame.height, "valid_flag_rows": usable.height,
            "reconstructable_valid_rows": reconstruction_count,
            "quality_counts": frame.group_by("quality").len().sort("quality").to_dicts(),
            "schema": {key: str(value) for key, value in frame.schema.items()},
            "files": [{"path": str(path.relative_to(ROOT)), "sha256": sha(path),
                       "bytes": path.stat().st_size} for path in paths],
        }
    return {"status": "REAL_PUBLIC_V2_SHORT_SMOKE_PASS", "requested_seconds": seconds,
            "database": str(config.db_path), "store": str(config.store),
            "run_result": result, "closed_read_only_status": final, "intervals": intervals,
            "reconstruction_scope": "Positivity/finite/reconstructable rows, not an independent "
                                    "quote comparison; isolated event tests verify equality. "
                                    "No executable labels or forward qualification."}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--smoke-seconds", type=int, default=90)
    args = parser.parse_args()
    output = args.output.resolve()
    require(output.is_relative_to(ROOT / "reports") and output.parent.is_dir()
            and output.suffix == ".json" and 90 <= args.smoke_seconds <= 120,
            "Exclusive D reports output and bounded smoke required")
    with output.open("x", encoding="utf-8") as writer:
        token = str(utc_now_us())
        started = time.monotonic()
        report = {"module": "A09_V2_MEASUREMENT", "created_utc": datetime.now(UTC).isoformat(),
                  "status": "MEASUREMENT_FAILED_UNQUALIFIED",
                  "actual_24h_capacity_accepted": False, "actual_24h_quality_accepted": False,
                  "alpha_eligible": False, "training_authorized": False,
                  "healthy_credit_seconds": 0, "orders_sent": 0,
                  "token": token}
        try:
            report["frozen_v1_before"] = frozen()
            source = ROOT / "src/quant/microstructure_v2.py"
            report["source_sha256_before"] = sha(source)
            report["measurement_source_sha256"] = sha(Path(__file__).resolve())
            report["resources_before"] = resources.status()
            report["initial_disk"] = disk.check(reserve=20_000_000)
            report["storage"] = storage_probe(ROOT / "reports/generated" / f"A09_PROBE_{token}")
            config = MicrostructureConfig(db_path=STATE / f"a09-v2-smoke-{token}.sqlite3",
                                         store=ROOT / "data" / f"a09-v2-smoke-{token}")
            report["public_smoke"] = asyncio.run(smoke(config, args.smoke_seconds))
            report["frozen_v1_after"] = frozen()
            report["source_sha256_after"] = sha(source)
            require(report["source_sha256_before"] == report["source_sha256_after"],
                    "V2 source changed during real measurement")
            report["final_disk"] = disk.check()
            report["resources_after"] = resources.status()
            report["status"] = "A09_REAL_SHORT_AND_STORAGE_OBSERVATION_COMPLETE"
        except Exception as error:
            report["failure"] = {"type": type(error).__name__, "message": str(error)[:2048]}
        report["elapsed_monotonic_seconds"] = time.monotonic() - started
        report["process_lifetime_peak_rss_bytes"] = (
            resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024
        )
        report["completed_utc"] = datetime.now(UTC).isoformat()
        payload = json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
        require(len(payload.encode()) <= 2_000_000, "Measurement output bound")
        writer.write(payload)
        writer.flush()
        os.fsync(writer.fileno())
    print(json.dumps({key: report[key] for key in ("status", "elapsed_monotonic_seconds")}))
    if report["status"] != "A09_REAL_SHORT_AND_STORAGE_OBSERVATION_COMPLETE":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
