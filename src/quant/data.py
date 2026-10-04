"""Checksum-verified Binance archive ingestion with explicit timestamp units."""
import calendar
import hashlib
import io
import json
import sqlite3
import time
import zipfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path

import httpx
import polars as pl

from .disk import check
from .paths import ROOT, STATE, utc_now_us

SYMBOLS = ("BTCUSDT", "ETHUSDT")
MINUTE_US = 60_000_000
SOURCE_COLUMNS = ["raw_open", "open", "high", "low", "close", "volume", "raw_close",
                  "quote_volume", "trade_count", "taker_buy_base", "taker_buy_quote", "ignore"]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


@contextmanager
def manifest_connection():
    path = STATE / "archive_manifest.sqlite3"
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, timeout=60)
    conn.execute("PRAGMA busy_timeout=60000")
    conn.execute("""CREATE TABLE IF NOT EXISTS archives (
        name TEXT PRIMARY KEY, symbol TEXT NOT NULL, month TEXT NOT NULL,
        url TEXT NOT NULL, sha256 TEXT NOT NULL, bytes INTEGER NOT NULL,
        downloaded_us INTEGER NOT NULL, status TEXT NOT NULL, rows INTEGER,
        timestamp_unit TEXT, quality_json TEXT, normalized_sha256 TEXT)""")
    try:
        yield conn
        conn.commit()
    except BaseException:
        conn.rollback()
        raise
    finally:
        conn.close()


def month_range(start: str, end: str) -> list[str]:
    current = datetime.strptime(start, "%Y-%m")
    last = datetime.strptime(end, "%Y-%m")
    if current > last:
        raise ValueError("Start month must not exceed end month")
    result = []
    while current <= last:
        result.append(current.strftime("%Y-%m"))
        current = datetime(current.year + (current.month == 12), current.month % 12 + 1, 1)
    return result


def archive_url(symbol: str, month: str) -> str:
    if symbol not in SYMBOLS:
        raise ValueError("Only preregistered BTCUSDT and ETHUSDT are allowed")
    datetime.strptime(month, "%Y-%m")
    return (f"https://data.binance.vision/data/spot/monthly/klines/{symbol}/1m/"
            f"{symbol}-1m-{month}.zip")


def download_one(symbol: str, month: str) -> dict:
    url = archive_url(symbol, month)
    name = url.rsplit("/", 1)[1]
    directory = ROOT / "data/raw/spot" / symbol / "1m"
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / name
    with manifest_connection() as conn:
        row = conn.execute("SELECT sha256 FROM archives WHERE name=?", (name,)).fetchone()
        if row and path.exists() and sha256_file(path) == row[0]:
            return {"name": name, "status": "cached", "bytes": path.stat().st_size}
    with httpx.Client(timeout=60, follow_redirects=True) as client:
        checksum_response = client.get(url + ".CHECKSUM")
        checksum_response.raise_for_status()
        checksum_fields = checksum_response.text.strip().split()
        if len(checksum_fields) != 2 or checksum_fields[1].lstrip("*") != name:
            raise ValueError(f"Unexpected CHECKSUM format: {name}")
        expected_sha = checksum_fields[0]
        if len(expected_sha) != 64:
            raise ValueError("Invalid SHA-256 digest")
        partial = path.with_suffix(".zip.part")
        # Bulk callers reserve the entire batch once before these bounded writes.
        for attempt in range(3):
            try:
                digest = hashlib.sha256()
                size = 0
                with client.stream("GET", url) as response:
                    response.raise_for_status()
                    advertised = int(response.headers.get("content-length", "0"))
                    if advertised > 12_000_000:
                        raise RuntimeError("Unexpectedly large 1m monthly archive")
                    with partial.open("wb") as stream:
                        for chunk in response.iter_bytes(256 * 1024):
                            size += len(chunk)
                            if size > 12_000_000:
                                raise RuntimeError("Archive exceeded reserved maximum")
                            digest.update(chunk)
                            stream.write(chunk)
                if advertised and size != advertised:
                    raise ValueError("Truncated archive")
                if digest.hexdigest() != expected_sha:
                    raise ValueError(f"Checksum mismatch: {name}")
                with zipfile.ZipFile(partial) as archive:
                    if archive.testzip() is not None:
                        raise ValueError("ZIP CRC failure")
                partial.replace(path)
                path.with_suffix(".zip.CHECKSUM").write_text(checksum_response.text)
                with manifest_connection() as conn:
                    conn.execute("""INSERT INTO archives
                        (name,symbol,month,url,sha256,bytes,downloaded_us,status)
                        VALUES (?,?,?,?,?,?,?,?) ON CONFLICT(name) DO UPDATE SET
                        sha256=excluded.sha256, bytes=excluded.bytes,
                        downloaded_us=excluded.downloaded_us, status=excluded.status""",
                                 (name, symbol, month, url, expected_sha, size,
                                  utc_now_us(), "verified"))
                return {"name": name, "status": "verified", "bytes": size}
            except (httpx.HTTPError, ValueError):
                partial.unlink(missing_ok=True)
                if attempt == 2:
                    raise
                time.sleep(2 ** attempt)
    raise RuntimeError("Download did not complete")


def download_months(months: list[str], workers: int = 4) -> list[dict]:
    check(reserve=len(months) * len(SYMBOLS) * 12_000_000 + 20_000_000)
    results, failures = [], []
    with ThreadPoolExecutor(max_workers=min(workers, 4)) as pool:
        tasks = {pool.submit(download_one, symbol, month): (symbol, month)
                 for month in months for symbol in SYMBOLS}
        for future in as_completed(tasks):
            try:
                results.append(future.result())
            except Exception as exc:
                failures.append({"source": tasks[future], "error": str(exc)})
            done = len(results) + len(failures)
            if done % 10 == 0 or done == len(tasks):
                print(json.dumps({"download_done": done, "total": len(tasks),
                                  "failures": len(failures)}, ensure_ascii=False), flush=True)
    if failures:
        raise RuntimeError(json.dumps(failures, ensure_ascii=False))
    return sorted(results, key=lambda item: item["name"])


def parse_csv(content: bytes, symbol: str, ingested_us: int = 0) -> tuple[pl.DataFrame, dict]:
    frame = pl.read_csv(io.BytesIO(content), has_header=False, new_columns=SOURCE_COLUMNS,
                        schema_overrides={"raw_open": pl.Int64, "raw_close": pl.Int64,
                                          "trade_count": pl.Int64,
                                          **{name: pl.Float64 for name in
                                             ("open", "high", "low", "close", "volume",
                                              "quote_volume", "taker_buy_base", "taker_buy_quote", "ignore")}})
    if frame.height == 0:
        raise ValueError("Empty CSV")
    units = frame.select((pl.col("raw_open") < 100_000_000_000_000).n_unique()).item()
    if units != 1:
        raise ValueError("Mixed timestamp units in one archive")
    scale = 1000 if frame["raw_open"][0] < 100_000_000_000_000 else 1
    unit = "milliseconds" if scale == 1000 else "microseconds"
    frame = frame.with_columns((pl.col("raw_open") * scale).alias("open_us"))
    bad_open = frame.filter(pl.col("open_us") % MINUTE_US != 0).height
    close_anomalies = frame.filter(
        (pl.col("raw_close") * scale) != pl.col("open_us") + MINUTE_US - scale
    ).select("open_us", (pl.col("raw_close") * scale).alias("source_close_us")).to_dicts()
    bad_timestamp = bad_open + len(close_anomalies)
    numeric = ["open", "high", "low", "close", "volume", "quote_volume",
               "taker_buy_base", "taker_buy_quote"]
    frame = frame.with_columns([pl.col(col).cast(pl.Float64) for col in numeric])
    bad_values = frame.filter(
        ~pl.all_horizontal([pl.col(col).is_finite() for col in numeric])
        | (pl.col("low") <= 0)
        | (pl.col("high") < pl.max_horizontal("open", "close", "low"))
        | (pl.col("low") > pl.min_horizontal("open", "close", "high"))
        | pl.any_horizontal([pl.col(col) < 0 for col in
                             ["volume", "quote_volume", "taker_buy_base", "taker_buy_quote",
                              "trade_count"]])
        | (pl.col("taker_buy_base") > pl.col("volume") * (1 + 1e-8))
    ).height
    duplicates = frame.height - frame["open_us"].n_unique()
    if bad_open or bad_values or duplicates:
        raise ValueError(f"Invalid archive: timestamp={bad_timestamp}, "
                         f"values={bad_values}, duplicates={duplicates}")
    frame = frame.sort("open_us").with_columns(
        (pl.col("open_us") + MINUTE_US).alias("close_us"),
        (pl.col("open_us") + MINUTE_US).alias("available_us"),
        pl.lit(symbol).alias("symbol"), pl.lit("1m").alias("interval"),
        pl.lit(ingested_us).alias("ingested_us"),
        (pl.col("raw_close") * scale).alias("source_close_us"),
    )
    dates = (frame.with_columns((pl.col("open_us") // (MINUTE_US * 1440)).alias("day"))
             .group_by("day").len().sort("day"))
    bad_days = [{"date": datetime.fromtimestamp(row[0] * 86400, UTC).date().isoformat(),
                 "rows": row[1]} for row in dates.iter_rows() if row[1] != 1440]
    quality = {"rows": frame.height, "timestamp_unit": unit, "duplicate_rows": duplicates,
               "bad_timestamps": bad_timestamp, "bad_values": bad_values,
               "gaps": frame.filter(pl.col("open_us").diff() > MINUTE_US).height,
               "incomplete_days": bad_days, "nonstandard_closes": close_anomalies}
    return frame.drop("raw_open", "raw_close", "ignore"), quality


def aggregate_frame(frame: pl.DataFrame, minutes: int) -> tuple[pl.DataFrame, int]:
    if minutes not in (15, 60):
        raise ValueError("Only preregistered 15m and 1h intervals")
    if frame["open_us"].n_unique() != frame.height:
        raise ValueError("Duplicate input bars")
    duration = minutes * MINUTE_US
    if "valid_day" not in frame.columns:
        frame = frame.with_columns(pl.lit(True).alias("valid_day"))
    grouped = (frame.sort("open_us")
               .with_columns(((pl.col("open_us") // duration) * duration).alias("bucket"))
               .group_by("symbol", "bucket", maintain_order=True).agg(
                   pl.col("open").first(), pl.col("high").max(), pl.col("low").min(),
                   pl.col("close").last(),
                   *[pl.col(col).sum() for col in ["volume", "quote_volume", "trade_count",
                                                  "taker_buy_base", "taker_buy_quote"]],
                   pl.col("available_us").max(), pl.col("open_us").min().alias("first_us"),
                   pl.col("open_us").max().alias("last_us"), pl.len().alias("minute_count")))
    # Rebuild the validity flag by bucket; an audited bad day cannot feed features.
    validity = (frame.with_columns(((pl.col("open_us") // duration) * duration).alias("bucket"))
                .group_by("symbol", "bucket").agg(pl.col("valid_day").all()))
    grouped = grouped.join(validity, on=["symbol", "bucket"])
    complete = ((pl.col("minute_count") == minutes)
                & (pl.col("first_us") == pl.col("bucket"))
                & (pl.col("last_us") == pl.col("bucket") + duration - MINUTE_US)
                & pl.col("valid_day"))
    excluded = grouped.filter(~complete).height
    result = (grouped.filter(complete).drop("first_us", "last_us", "minute_count", "valid_day")
              .rename({"bucket": "open_us"})
              .with_columns((pl.col("open_us") + duration).alias("close_us"),
                            pl.lit("1h" if minutes == 60 else "15m").alias("interval"))
              .sort("symbol", "open_us"))
    return result, excluded


def ingest_all() -> dict:
    if (ROOT / "state/dataset_lock.json").exists():
        raise RuntimeError("Dataset is sealed; register a separate version before rebuilding")
    check(reserve=1_500_000_000)
    with manifest_connection() as conn:
        sources = conn.execute("SELECT name,symbol,month,sha256,downloaded_us FROM archives "
                               "ORDER BY symbol,month").fetchall()
    if not sources:
        raise ValueError("No verified sources")
    results = []
    for name, symbol, month, digest, received in sources:
        raw = ROOT / "data/raw/spot" / symbol / "1m" / name
        if sha256_file(raw) != digest:
            raise ValueError(f"Immutable archive changed: {name}")
        with zipfile.ZipFile(raw) as archive:
            members = archive.namelist()
            if members != [name.removesuffix(".zip") + ".csv"]:
                raise ValueError(f"Unexpected ZIP members: {name}")
            frame, quality = parse_csv(archive.read(members[0]), symbol, received)
        year, month_number = map(int, month.split("-"))
        expected = calendar.monthrange(year, month_number)[1] * 1440
        quality["expected_rows"] = expected
        quality["missing_rows"] = expected - frame.height
        quality["first_open_us"] = frame["open_us"][0]
        quality["last_open_us"] = frame["open_us"][-1]
        start_us = int(datetime(year, month_number, 1, tzinfo=UTC).timestamp() * 1_000_000)
        if quality["first_open_us"] != start_us:
            quality["missing_start"] = True
        expected_end = start_us + expected * MINUTE_US
        if quality["last_open_us"] != expected_end - MINUTE_US:
            quality["missing_end"] = True
        counts = (frame.with_columns((pl.col("open_us") // (MINUTE_US * 1440)).alias("day"))
                  .group_by("day").len())
        observed = dict(counts.iter_rows())
        first_day = start_us // (MINUTE_US * 1440)
        quality["incomplete_days"] = [
            {"date": datetime.fromtimestamp(day * 86400, UTC).date().isoformat(),
             "rows": observed.get(day, 0)}
            for day in range(first_day, first_day + calendar.monthrange(year, month_number)[1])
            if observed.get(day, 0) != 1440]
        invalid_days = {day for day, count in observed.items() if count != 1440}
        invalid_days.update(row["open_us"] // (MINUTE_US * 1440)
                            for row in quality["nonstandard_closes"])
        frame = frame.with_columns(
            (~(pl.col("open_us") // (MINUTE_US * 1440)).is_in(list(invalid_days)))
            .alias("valid_day"))
        quality["quarantined_rows"] = frame.filter(~pl.col("valid_day")).height
        quality["quarantined_days"] = [datetime.fromtimestamp(day * 86400, UTC)
                                       .date().isoformat() for day in sorted(invalid_days)]
        output = ROOT / "data/normalized/spot" / symbol / "1m" / f"{month}.parquet"
        output.parent.mkdir(parents=True, exist_ok=True)
        frame = frame.with_columns(pl.lit(digest).alias("source_file_sha256"))
        temp = output.with_suffix(".parquet.tmp")
        frame.write_parquet(temp, compression="zstd", statistics=True)
        temp.replace(output)
        with manifest_connection() as conn:
            conn.execute("UPDATE archives SET status=?,rows=?,timestamp_unit=?,quality_json=?,"
                         "normalized_sha256=? WHERE name=?",
                         ("ingested", frame.height, quality["timestamp_unit"], json.dumps(quality),
                          sha256_file(output), name))
        results.append({"source": name, **quality, "normalized_bytes": output.stat().st_size})
        if len(results) % 20 == 0:
            print(json.dumps({"ingested": len(results), "total": len(sources)}), flush=True)
    aggregate_results = []
    for symbol in SYMBOLS:
        files = sorted((ROOT / "data/normalized/spot" / symbol / "1m").glob("*.parquet"))
        frame = pl.scan_parquet(files).collect(engine="streaming")
        for minutes in (15, 60):
            aggregated, excluded = aggregate_frame(frame, minutes)
            interval = "1h" if minutes == 60 else "15m"
            output = ROOT / "data/bars/spot" / symbol / f"{interval}.parquet"
            output.parent.mkdir(parents=True, exist_ok=True)
            aggregated.write_parquet(output, compression="zstd")
            aggregate_results.append({"symbol": symbol, "interval": interval,
                                      "rows": aggregated.height, "excluded_windows": excluded,
                                      "bytes": output.stat().st_size,
                                      "sha256": sha256_file(output)})
    dataset_digest = hashlib.sha256(json.dumps(
        [(row[0], row[3]) for row in sources], sort_keys=True).encode()).hexdigest()
    report = {"dataset_id": dataset_digest, "source_count": len(sources),
              "minute_rows": sum(row["rows"] for row in results),
              "missing_rows": sum(row["missing_rows"] for row in results),
              "nonstandard_closes": sum(len(row["nonstandard_closes"]) for row in results),
              "quarantined_days": [{"source": row["source"], "dates": row["quarantined_days"]}
                                   for row in results if row["quarantined_days"]],
              "sources": results, "aggregated": aggregate_results, "disk": check(),
              "holdout_start_utc": "2026-03-01T00:00:00Z",
              "holdout_end_exclusive_utc": "2026-09-01T00:00:00Z",
              "holdout_performance_revealed": False}
    output = ROOT / "reports/generated/DATA_QUALITY_REPORT.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, ensure_ascii=False))
    print(json.dumps({key: report[key] for key in ["dataset_id", "source_count", "minute_rows",
                                                "missing_rows", "aggregated", "disk"]}, indent=2))
    return report


def freeze_dataset() -> dict:
    """Seal the complete preregistered dataset before any outcome is evaluated."""
    report = json.loads((ROOT / "reports/generated/DATA_QUALITY_REPORT.json").read_text())
    expected_names = {f"{symbol}-1m-{month}.zip" for symbol in SYMBOLS
                      for month in month_range("2022-01", "2026-08")}
    actual_names = {source["source"] for source in report["sources"]}
    if actual_names != expected_names:
        raise RuntimeError("Cannot freeze: complete preregistered monthly source set is missing")
    files = {}
    for source in report["aggregated"]:
        path = ROOT / "data/bars/spot" / source["symbol"] / f"{source['interval']}.parquet"
        files[str(path.relative_to(ROOT))] = sha256_file(path)
    minute_files = {}
    with manifest_connection() as conn:
        normalized = conn.execute("SELECT symbol,month,normalized_sha256 FROM archives "
                                  "WHERE status='ingested' ORDER BY symbol,month").fetchall()
    if len(normalized) != len(expected_names):
        raise RuntimeError("Cannot freeze: normalized monthly source set is incomplete")
    for symbol, month, expected_digest in normalized:
        path = ROOT / "data/normalized/spot" / symbol / "1m" / f"{month}.parquet"
        digest = sha256_file(path)
        if digest != expected_digest:
            raise RuntimeError(f"Normalized source changed before sealing: {path.name}")
        minute_files[str(path.relative_to(ROOT))] = digest
    lock = {"dataset_id": report["dataset_id"], "bar_files": files,
            "minute_files": minute_files,
            "quality_report_sha256": sha256_file(
                ROOT / "reports/generated/DATA_QUALITY_REPORT.json"),
            "dataset_policy_sha256": sha256_file(ROOT / "configs/dataset_policy.json"),
            "holdout_start_utc": report["holdout_start_utc"],
            "holdout_end_exclusive_utc": report["holdout_end_exclusive_utc"],
            "policy": "No outcome-based iteration on final holdout. One final candidate only."}
    path = ROOT / "state/dataset_lock.json"
    if path.exists():
        if json.loads(path.read_text()) != lock:
            raise RuntimeError("Sealed dataset changed: create a separately registered dataset")
    else:
        path.write_text(json.dumps(lock, indent=2))
    return lock


def verify_dataset_lock() -> dict:
    lock = json.loads((ROOT / "state/dataset_lock.json").read_text())
    files = {**lock["bar_files"], **lock["minute_files"],
             "reports/generated/DATA_QUALITY_REPORT.json": lock["quality_report_sha256"],
             "configs/dataset_policy.json": lock["dataset_policy_sha256"]}
    for relative, digest in files.items():
        if sha256_file(ROOT / relative) != digest:
            raise RuntimeError(f"Sealed dataset changed: {relative}")
    return lock


def load_bars(intervals: tuple[str, ...] = ("1h",)) -> pl.DataFrame:
    files = [ROOT / "data/bars/spot" / symbol / f"{interval}.parquet"
             for symbol in SYMBOLS for interval in intervals]
    return pl.concat([pl.read_parquet(path) for path in files]).sort("symbol", "open_us")


def load_minutes() -> pl.DataFrame:
    lock = json.loads((ROOT / "state/dataset_lock.json").read_text())
    # Only sealed members are research inputs, even if more archive files appear.
    files = [ROOT / relative for relative in sorted(lock["minute_files"])]
    columns = ["symbol", "interval", "open_us", "close_us", "available_us", "open", "high",
               "low", "close", "volume", "quote_volume", "trade_count",
               "taker_buy_base", "taker_buy_quote"]
    return (pl.scan_parquet(files).filter(pl.col("valid_day"))
            .select(columns).collect(engine="streaming"))


def fetch_instruments() -> dict:
    symbols = []
    with httpx.Client(timeout=30) as client:
        for symbol in SYMBOLS:
            response = client.get("https://data-api.binance.vision/api/v3/exchangeInfo",
                                  params={"symbol": symbol})
            if response.status_code != 200:
                raise RuntimeError(f"Instrument metadata unavailable: {response.text[:300]}")
            symbols.extend(response.json()["symbols"])
    snapshot = {"received_us": utc_now_us(), "source":
                "https://data-api.binance.vision/api/v3/exchangeInfo",
                "historical_filters_available": False, "symbols": symbols}
    (ROOT / "state/instrument_snapshot.json").write_text(json.dumps(snapshot, indent=2))
    return {row["symbol"]: {item["filterType"]: item for item in row["filters"]
                            if item["filterType"] in {"LOT_SIZE", "MIN_NOTIONAL", "NOTIONAL"}}
            for row in symbols}

