"""Rebuild a 2024 NativeDailySimulator window from pinned, existing public ZIPs.

Source preparation only: no targets are used here and no account is created.
All source omissions other than the ten separately flagged August mark closes
fail. Original ZIPs are read-only.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
import csv
from datetime import datetime, timezone
import hashlib
import io
import json
import math
from pathlib import Path
import zipfile

import numpy as np
import polars as pl

S = ("BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT", "DOGEUSDT")
START = 1704067200000000
END = 1735689600000000
DAY = 86400000000
MINUTE = 60000000
WRAPPER_SHA = {
    "H1.zip": "a998b786d781a5dd314c6efb44dc55702972977b9bdf2fea315426b7c4362deb",
    "coin_public_tail_archives_20261008_part01.zip": "10de51c5daed8bcc63e9d2cecbd17146ca2e7c0ab488dea221eab44b920a9bbc",
    "coin_public_tail_archives_20261008_part02.zip": "02c1e379231d388bab4c1df1c3342ef0ccf1582ad6c6e58164ca78a239fa7d4e",
    "coin_public_tail_archives_20261008_part03.zip": "104f03ce110de7003c573a3af5c88f0b19e843c956e45e550ab85af8f429a1e1",
}
DAILY_CUBE_SHA = "88a698ceed87603a36ca2bcf4ae76d805aa90085b344bbeee47e58a8c9770add"
BRIDGE_SHA = "0af6d1cc66bc81afd39582ae4de2b1aa25d9e0031765ce6bce74e917a5577d0c"
GAPS = (1723456920000, 1723456980000)


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def file_sha(path: Path) -> str:
    return sha(path.read_bytes())


def save_json(path: Path, value):
    path.write_text(json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + "\n")


def month_limits(year: int, month: int):
    a = datetime(year, month, 1, tzinfo=timezone.utc)
    b = datetime(year + (month == 12), month % 12 + 1, 1, tzinfo=timezone.utc)
    return int(a.timestamp() * 1000), int(b.timestamp() * 1000)


def parse_source(outer, name: str):
    blob = outer.read(name)
    actual_sha = sha(blob)
    official = outer.read(name + ".CHECKSUM").decode().split()[0]
    if actual_sha != official:
        raise ValueError(f"Original official checksum mismatch: {name}")
    with zipfile.ZipFile(io.BytesIO(blob)) as z:
        if z.testzip() is not None or len(z.namelist()) != 1:
            raise ValueError(f"Original inner ZIP CRC/member failure: {name}")
        rows = list(csv.DictReader(io.StringIO(z.read(z.namelist()[0]).decode())))
    return rows, {"member": name, "ZIP_SHA256": actual_sha, "ZIP_bytes": len(blob),
                  "rows": len(rows)}


def prepare(source_dir: Path, close_cube: Path, output: Path):
    if output.exists():
        raise FileExistsError(output)
    for name, expected in WRAPPER_SHA.items():
        if file_sha(source_dir / name) != expected:
            raise ValueError(f"Original public wrapper SHA mismatch: {name}")
    bridge_path = source_dir / "derived_mark/DERIVED_MARK_OHLC.csv"
    if not bridge_path.is_file():
        bridge_path = source_dir / "DERIVED_MARK_OHLC.csv"
    if file_sha(close_cube) != DAILY_CUBE_SHA or file_sha(bridge_path) != BRIDGE_SHA:
        raise ValueError("Original daily cube or frozen mark derivative SHA mismatch")
    output.mkdir(parents=True)
    (output / "months").mkdir()
    archives = {name: zipfile.ZipFile(source_dir / name) for name in WRAPPER_SHA}
    for name, z in archives.items():
        if z.testzip() is not None:
            raise ValueError(f"Original wrapper CRC failure: {name}")
    h1 = archives["H1.zip"]
    tail = [archives[f"coin_public_tail_archives_20261008_part{k:02d}.zip"] for k in (1, 2, 3)]
    lookup = {n: z for z in tail for n in z.namelist()}
    bridge = list(csv.DictReader(bridge_path.open()))
    over = {(r["symbol"], int(r["open_time_ms"])): float(r["close"]) for r in bridge}
    if len(bridge) != 10 or len(over) != 10 or set(over) != {(s, t) for s in S for t in GAPS}:
        raise ValueError("Exact ten original gap rows only")
    h1_funding = {}
    h1_mark_needed = set()
    for s in S:
        # Read the original normalized event stream directly from its pinned
        # public wrapper, so an unpublished extracted copy is never required.
        table = pl.read_parquet(io.BytesIO(h1.read(f"h1_market/data/normalized/{s}_funding_events.parquet")))
        rows = table.filter((pl.col("calc_time_ms") >= START // 1000) &
                            (pl.col("calc_time_ms") < month_limits(2024, 7)[0])).to_dicts()
        h1_funding[s] = rows
        h1_mark_needed.update((s, int(row["past_mark_available_us"])) for row in rows
                              if int(row["calc_time_ms"]) != START // 1000 and row["past_mark_available_us"] is not None)
    months = []
    prior = {s: None for s in S}
    observed_marks = {}
    trade_daily_close = {}
    for month in range(1, 13):
        label = f"2024-{month:02d}"
        lo, hi = month_limits(2024, month)
        ticks = np.arange(lo * 1000, hi * 1000, MINUTE, dtype=np.int64)
        arrays = {"times": ticks}
        source_records = []
        for s in S:
            for family in ("klines", "markPriceKlines"):
                name = (f"h1_market/data/raw/{family}/{s}/{s}-1m-{label}.zip" if month <= 6 else
                        f"tail_data/data/raw/{family}/{s}/{s}-1m-{label}.zip")
                outer = h1 if month <= 6 else lookup[name]
                rows, record = parse_source(outer, name)
                source_records.append({"symbol": s, "family": family, **record})
                expected = len(ticks) - (2 if month == 8 and family == "markPriceKlines" else 0)
                if len(rows) != expected:
                    raise ValueError(f"Unexpected original source row count: {name}")
                times = np.asarray([int(row["open_time"]) for row in rows], dtype=np.int64)
                if (np.any(np.diff(times) <= 0) or np.any((times - lo) % 60000) or
                        np.any(times < lo) or np.any(times >= hi)):
                    raise ValueError(f"Nonmonotone or nongrid original minute: {name}")
                positions = ((times - lo) // 60000).astype(np.int64)
                expected_positions = np.arange(len(ticks), dtype=np.int64)
                if month == 8 and family == "markPriceKlines":
                    expected_positions = expected_positions[np.isin(ticks // 1000, GAPS, invert=True)]
                if not np.array_equal(positions, expected_positions):
                    raise ValueError(f"Unallowlisted original minute gap: {name}")
                if family == "klines":
                    oo = np.asarray([float(row["open"]) for row in rows], dtype=np.float64)
                    cc = np.asarray([float(row["close"]) for row in rows], dtype=np.float64)
                    qv = np.asarray([float(row["quote_volume"]) for row in rows], dtype=np.float64)
                    if (not np.isfinite(oo).all() or not np.isfinite(cc).all() or
                            not np.isfinite(qv).all() or min(oo.min(), cc.min()) <= 0 or qv.min() < 0):
                        raise ValueError(f"Actual trade price or quote invalid: {name}")
                    arrays[s + "_open"] = oo
                    arrays[s + "_close"] = cc
                    arrays[s + "_quote_volume"] = qv
                    if prior[s] is not None:
                        record["prior_completed_close"] = prior[s]
                    prior[s] = float(cc[-1])
                    for day in range(0, len(ticks), 1440):
                        available = int(ticks[day + 1439] + MINUTE)
                        trade_daily_close[(s, available)] = float(cc[day + 1439])
                else:
                    mark = np.full(len(ticks), np.nan, dtype=np.float64)
                    mark[positions] = [float(row["close"]) for row in rows]
                    if month == 8:
                        for t in GAPS:
                            mark[(t - lo) // 60000] = over[s, t]
                    if not np.isfinite(mark).all() or (mark <= 0).any():
                        raise ValueError(f"Unresolved observed or allowed derived mark: {name}")
                    arrays[s + "_mark"] = mark
                    for position, price in zip(positions, mark[positions]):
                        key = (s, int(ticks[position] + MINUTE))
                        if key in h1_mark_needed:
                            observed_marks[key] = float(price)
        path = output / "months" / (label + ".npz")
        np.savez_compressed(path, **arrays)
        months.append({"month": label, "minutes": len(ticks), "source_NPZ_SHA256": file_sha(path),
                       "source_NPZ_bytes": path.stat().st_size, "sources": source_records})
    with np.load(close_cube, allow_pickle=False) as z:
        t, p = z["close_available_us"], z["close"]
        if tuple(z["symbol_order"]) != S:
            raise ValueError("Daily cube original CORE5 order mismatch")
    decisions = np.arange(START, END, DAY, dtype=np.int64)
    if len(decisions) != 366:
        raise ValueError("Leap year not complete")
    day_rows = []
    for j, s in enumerate(S):
        for stamp in decisions:
            k = int(np.searchsorted(t, stamp))
            if k == len(t) or t[k] != stamp or not np.isfinite(p[k, j]) or p[k, j] <= 0:
                raise ValueError("Incomplete actual completed daily close")
            value = float(p[k, j])
            if stamp != START and trade_daily_close[(s, int(stamp))] != value:
                raise ValueError("Original daily cube differs from actual prior trade minute")
            day_rows.append({"symbol": s, "close_us": int(stamp), "close": value})
    save_json(output / "DAILY.json", day_rows)
    fund = []
    h1_mark_matches = 0
    for s in S:
        jan_jun = h1_funding[s]
        if len(jan_jun) != 546:
            raise ValueError("H1 actual normalized funding event count")
        for row in jan_jun:
            if row["past_mark_price"] is None or row["past_mark_available_us"] is None:
                raise ValueError("H1 saved actual past mark missing")
            # The first midnight mark belongs to the unowned pre-start episode.
            if int(row["calc_time_ms"]) != START // 1000:
                clock = int(row["past_mark_available_us"])
                actual = observed_marks.get((s, clock))
                if actual is None or actual != float(row["past_mark_price"]):
                    raise ValueError("H1 past funding mark differs from original 1m mark close")
                h1_mark_matches += 1
            fund.append({"symbol": s, "event_us": int(row["calc_time_ms"]) * 1000,
                         "raw_rate": float(row["last_funding_rate"]),
                         "reported_interval_hours": float(row["funding_interval_hours"])})
        for month in range(7, 13):
            label = f"2024-{month:02d}"
            name = f"tail_data/data/raw/fundingRate/{s}/{s}-fundingRate-{label}.zip"
            rows, _ = parse_source(lookup[name], name)
            for row in rows:
                fund.append({"symbol": s, "event_us": int(row["calc_time"]) * 1000,
                             "raw_rate": float(row["last_funding_rate"]),
                             "reported_interval_hours": float(row["funding_interval_hours"])})
    fund.sort(key=lambda x: (x["event_us"], x["symbol"]))
    if len(fund) != 5490 or len({(x["symbol"], x["event_us"]) for x in fund}) != 5490:
        raise ValueError("Full-year unique original funding events required")
    if any(not math.isfinite(x["raw_rate"]) or not math.isfinite(x["reported_interval_hours"])
           or x["reported_interval_hours"] <= 0 for x in fund):
        raise ValueError("Nonfinite original rate or interval")
    for s in S:
        times = [x["event_us"] for x in fund if x["symbol"] == s]
        slots = [x // (8 * 3600 * 1000000) for x in times]
        if len(times) != 1098 or slots != list(range(START // (8 * 3600 * 1000000),
                                                    END // (8 * 3600 * 1000000))):
            raise ValueError("Missing or duplicate actual funding slot")
    save_json(output / "EVENTS.json", fund)
    files = {n: {"SHA256": file_sha(output / n), "bytes": (output / n).stat().st_size}
             for n in ("DAILY.json", "EVENTS.json")}
    index = {"schema": "EXISTING_PUBLIC_CORE5_2024_NATIVE_SOURCE_WITH_10_MARK_OVERLAY_V1",
             "calendar": [START, END], "days": 366, "minutes_per_asset": 527040,
             "symbol_order": list(S), "funding_events": len(fund), "months": months,
             "files": files, "daily_cube_SHA256": DAILY_CUBE_SHA,
             "public_wrappers_SHA256": WRAPPER_SHA,
             "derived_mark_csv_SHA256": BRIDGE_SHA,
             "original_missing_mark_open_ms": list(GAPS),
             "derived_mark_cells": 10,
             "original_trade_minute_missing": 0,
             "H1_saved_actual_prior_funding_marks_matched_original_1m": h1_mark_matches,
             "actual_2024_completed_daily_closes_match_cube": True,
             "new_wallets": 0, "financial_scores": 0, "new_provider_downloads": 0}
    save_json(output / "SOURCE_INDEX.json", index)
    return index


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-dir", required=True, type=Path)
    parser.add_argument("--close-cube", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    result = prepare(args.source_dir, args.close_cube, args.output)
    print(json.dumps({"days": result["days"], "minutes_per_asset": result["minutes_per_asset"],
                      "funding_events": result["funding_events"],
                      "h1_marks_matched": result["H1_saved_actual_prior_funding_marks_matched_original_1m"]}))
