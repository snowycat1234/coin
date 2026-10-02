"""Official monthly ZIP/CHECKSUM orchestration; reuse the frozen V2 daily converter."""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import os
import resource
import time
import zipfile
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace

import httpx
import pyarrow.parquet as pq

from quant import disk, resources
from quant.paths import ROOT, STATE
from quant.research_fast.trade_flow_v2 import (
    CONTRACT, SCHEMA, checksum, private_module, require, source_hashes, validate_request,
)

UPSTREAM_COMMIT = "f446ce3812bd4e5521f21faecd4ae3c6460e49fc"
TERMS_SHA = "dcf358e9d18f598a7a635fac80f6e643fa24a0e111a4d39bda47f1e246b31eb1"
DAILY_STORE = ROOT / "data/research_fast/trade_flow_5s_v2"
STORE = ROOT / "data/research_fast/trade_flow_5s_v2_monthly_v7"
MAX_ZIP = 2_000_000_000
MAX_MONTH_CSV = 12_000_000_000
DAY_US = 86_400_000_000


def publish(path, value):
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("x", encoding="utf8") as writer:
        writer.write(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n")
        writer.flush()
        os.fsync(writer.fileno())
    os.replace(temporary, path)


class MonthRows:
    """One bounded lookahead line; the original converter still parses every data row."""
    def __init__(self, stream, market, opened, closed):
        self.stream, self.market = stream, market
        self.opened, self.closed = opened, closed
        self.lookahead, self.bytes, self.lines = None, 0, 0

    def next_line(self):
        if self.lookahead is not None:
            line, timestamp = self.lookahead
            self.lookahead = None
            return line, timestamp
        line = self.stream.readline(16_385)
        if not line:
            return b"", None
        self.bytes += len(line)
        self.lines += 1
        require(len(line) <= 16_384 and self.bytes <= MAX_MONTH_CSV, "Monthly CSV byte/line bound")
        row = next(csv.reader(io.StringIO(line.decode("utf-8-sig"))))
        # An optional original header is delegated unchanged to the frozen parser.
        if not row[0].isdecimal():
            require(self.lines == 1, "Header only allowed as first monthly line")
            return line, None
        require(len(row) == (8 if self.market == "spot" else 7), "Monthly CSV columns")
        require(row[5].isascii() and row[5].isdecimal(), "Monthly timestamp integer")
        timestamp = int(row[5]) * (1 if self.market == "spot" else 1000)
        require(self.opened <= timestamp < self.closed, "Monthly timestamp range")
        return line, timestamp


class DayReader:
    def __init__(self, rows, opened):
        self.rows, self.opened, self.closed, self.bytes = rows, opened, opened + DAY_US, 0

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False  # The outer monthly ZipExtFile owns and verifies the whole member.

    def readline(self, _bound):
        line, timestamp = self.rows.next_line()
        if timestamp is not None and timestamp >= self.closed:
            self.rows.lookahead = line, timestamp
            return b""
        require(timestamp is None or timestamp >= self.opened, "Backward day in monthly stream")
        self.bytes += len(line)
        return line


class DayArchive:
    """Read-only daily view of one verified monthly member; no daily ZIP is fabricated."""
    def __init__(self, reader, name, max_bytes):
        self.reader = reader
        self.member = SimpleNamespace(filename=name, file_size=max_bytes, flag_bits=0)

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def infolist(self):
        return [self.member]

    def open(self, member):
        require(member is self.member, "Unexpected synthetic daily view member")
        return self.reader


def fetch_month(market, symbol, month, run_dir, output):
    started = time.monotonic()
    start = date.fromisoformat(month + "-01")
    end = (start.replace(day=28) + timedelta(days=4)).replace(day=1)
    validate_request(market, symbol, start)
    validate_request(market, symbol, end - timedelta(days=1))
    require(len(month) == 7 and start.isoformat()[:7] == month, "Explicit YYYY-MM required")
    run_dir = run_dir.resolve()
    output = output.resolve()
    require(run_dir.is_relative_to(STATE.resolve()) and not run_dir.exists(), "Exclusive native STATE run")
    require(output.is_relative_to(ROOT / "reports") and not output.exists(), "Exclusive report")
    run_dir.mkdir()
    days = (end - start).days
    category = "spot" if market == "spot" else "futures/um"
    name = f"{symbol}-aggTrades-{month}.zip"
    url = f"https://data.binance.vision/data/{category}/monthly/aggTrades/{symbol}/{name}"
    zip_path = run_dir / name
    bindings = {**source_hashes(), "scripts/research_v7/fetch_monthly.py": checksum(Path(__file__))}
    receipt = {
        "status": "MONTHLY_V7_RUNNING_UNACCEPTED", "created_utc": datetime.now(UTC).isoformat(),
        "market": market, "symbol": symbol, "month": month, "url": url,
        "checksum_url": url + ".CHECKSUM", "official_repository": "https://github.com/binance/binance-public-data",
        "upstream_commit": UPSTREAM_COMMIT, "software_license": "MIT",
        "data_terms_url": f"https://github.com/binance/binance-public-data/blob/{UPSTREAM_COMMIT}/TERMS_AND_CONDITIONS.md",
        "data_terms_sha256": TERMS_SHA, "use_purpose": "personal_nonproduction_research",
        "source_hashes": bindings, "store": str(STORE), "owned_temporary_directory": str(run_dir),
        "partition": "read-only UTC day stream views; frozen V2 parse/count/statistics unchanged",
        "synthetic_member_file_size": "upper bound; actual daily CSV bytes recorded independently",
        "required_days": days, "completed_days": 0, "daily": [], "raw_deleted": False,
        "alpha_eligible": False, "real_time_quality_eligible": False, "executable_price_evidence": False,
        "initial_resources": resources.status(),
    }
    publish(output, receipt)
    try:
        with httpx.Client(timeout=120, follow_redirects=False) as client:
            head = client.head(url)
            head.raise_for_status()
            announced = int(head.headers["content-length"])
            require(0 < announced <= MAX_ZIP, "Monthly ZIP too large; use explicit daily fallback")
            receipt["announced_zip_bytes"] = announced
            receipt["initial_disk"] = disk.check(reserve=2 * announced + days * 25_000_000 + 1_000_000_000)
            receipt["initial_disk_scan_utc"] = datetime.now(UTC).isoformat()
            with client.stream("GET", url + ".CHECKSUM") as response:
                response.raise_for_status()
                expected_bytes = b""
                for part in response.iter_bytes(chunk_size=1024):
                    expected_bytes += part
                    require(len(expected_bytes) <= 4096, "CHECKSUM response bound")
            fields = expected_bytes.decode("ascii").strip().split()
            require(len(fields) == 2 and len(fields[0]) == 64 and all(c in "0123456789abcdefABCDEF" for c in fields[0]) and fields[1].lstrip("*") == name, "CHECKSUM format/name")
            receipt["official_checksum_text"] = expected_bytes.decode("ascii")
            digest, downloaded = hashlib.sha256(), 0
            with client.stream("GET", url) as response, zip_path.open("xb") as writer:
                response.raise_for_status()
                for part in response.iter_bytes(chunk_size=1_048_576):
                    downloaded += len(part)
                    require(downloaded <= announced <= MAX_ZIP, "Monthly download hard bound")
                    writer.write(part)
                    digest.update(part)
                writer.flush()
                os.fsync(writer.fileno())
            require(downloaded == announced and digest.hexdigest() == fields[0].lower(), "Monthly size/CHECKSUM mismatch")
            receipt.update(zip_bytes=downloaded, zip_sha256=digest.hexdigest(), checksum_status="PASS", download_seconds=time.monotonic() - started)
            publish(output, receipt)
        # Reuse accepted resume validation for the prior immutable original daily boundary.
        history = private_module("v7_old_daily_source_validator", ROOT / "scripts/hf_fetch_history.py")
        prior_day = start - timedelta(days=1)
        prior = history.resume_day(market, symbol, prior_day, None)
        require(prior is not None, "Prior day source boundary required for pilot")
        previous = prior["conversion"]["last_l"], prior["conversion"]["last_a"]
        prior_manifest = DAILY_STORE / market / symbol / f"{prior_day}.manifest.json"
        receipt["prior_boundary"] = {"path": str(prior_manifest), "sha256": checksum(prior_manifest), "last_l": previous[0], "last_a": previous[1]}
        with zipfile.ZipFile(zip_path) as archive:
            members = archive.infolist()
            require(len(members) == 1 and members[0].filename == f"{symbol}-aggTrades-{month}.csv" and not members[0].flag_bits & 1 and 0 < members[0].file_size <= MAX_MONTH_CSV, "Monthly member name/count/encryption/size")
            receipt["uncompressed_csv_bytes"] = members[0].file_size
            opened = int(datetime.combine(start, datetime.min.time(), tzinfo=UTC).timestamp()) * 1_000_000
            with archive.open(members[0]) as binary:
                rows = MonthRows(binary, market, opened, opened + days * DAY_US)
                for index in range(days):
                    day = start + timedelta(days=index)
                    feature = STORE / market / symbol / f"{day}.parquet"
                    manifest = feature.with_suffix(".manifest.json")
                    require(not feature.exists() and not manifest.exists(), "Monthly source cannot overwrite")
                    feature.parent.mkdir(parents=True, exist_ok=True)
                    partial = run_dir / f"{day}.parquet"
                    reader = DayReader(rows, opened + index * DAY_US)
                    view = DayArchive(reader, f"{symbol}-aggTrades-{day}.csv", min(members[0].file_size, 4_000_000_000))
                    adapter = private_module("v7_private_frozen_v2_adapter", ROOT / "src/quant/research_fast/trade_flow_v2.py")
                    factory = adapter.private_module
                    def engine_factory(module_name, path):
                        engine = factory(module_name, path)
                        engine.zipfile = SimpleNamespace(ZipFile=lambda _path: view)
                        return engine
                    adapter.private_module = engine_factory
                    converted = adapter.convert_zip(zip_path, partial, market=market, symbol=symbol, day=day, previous_day_last_raw_id=previous[0], previous_day_last_agg_id=previous[1])
                    require(converted["rows"] == 17280 and converted["contract"] == CONTRACT and pq.read_schema(partial) == SCHEMA and pq.read_metadata(partial).num_rows == 17280, "Actual original V2 Parquet contract")
                    old = history.resume_day(market, symbol, day, previous)
                    overlap = None
                    if old is not None:
                        require(converted["parquet_sha256"] == old["feature_sha256"], "Monthly/daily overlap actual Parquet bytes differ; refuse merge")
                        old_manifest = DAILY_STORE / market / symbol / f"{day}.manifest.json"
                        overlap = {"manifest_path": str(old_manifest), "manifest_sha256": checksum(old_manifest), "parquet_sha256": old["feature_sha256"], "actual_byte_equality": True}
                    with partial.open("rb") as source, feature.open("xb") as target:
                        for part in iter(lambda: source.read(1_048_576), b""):
                            target.write(part)
                        target.flush()
                        os.fsync(target.fileno())
                    require(checksum(feature) == converted["parquet_sha256"], "Published SHA changed")
                    day_receipt = {
                        "status": "OFFICIAL_MONTHLY_V7_DAY_SOURCE_VERIFIED", "market": market, "symbol": symbol, "date": str(day),
                        "monthly_archive_url": url, "monthly_archive_sha256": receipt["zip_sha256"], "checksum_status": "PASS",
                        "source_hashes": bindings, "conversion": converted, "feature_path": str(feature), "feature_sha256": converted["parquet_sha256"],
                        "actual_day_csv_bytes": reader.bytes, "daily_overlap": overlap,
                        "data_terms_sha256": TERMS_SHA, "alpha_eligible": False,
                    }
                    publish(manifest, day_receipt)
                    partial.unlink()
                    previous = converted["last_l"], converted["last_a"]
                    receipt["daily"].append({"path": str(manifest), "sha256": checksum(manifest), "parquet_sha256": converted["parquet_sha256"], "parquet_bytes": converted["parquet_bytes"], "overlap": overlap})
                    receipt["completed_days"] += 1
                    receipt["peak_rss_bytes"] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024
                    publish(output, receipt)
                    print(json.dumps({"completed_days": index + 1, "required_days": days, "date": str(day), "actual_day_csv_bytes": reader.bytes, "peak_rss_bytes": receipt["peak_rss_bytes"]}), flush=True)
                require(rows.lookahead is None and rows.next_line()[0] == b"" and rows.bytes == members[0].file_size, "Monthly EOF/CRC/actual CSV byte count")
                receipt["actual_csv_bytes"] = rows.bytes
                receipt["zip_crc_read_to_eof"] = True
        receipt["status"] = "OFFICIAL_MONTHLY_V7_COMPLETE_PENDING_INDEPENDENT_QA"
        receipt["final_disk"] = disk.check(reserve=1_000_000_000)
        receipt["final_disk_scan_utc"] = datetime.now(UTC).isoformat()
        receipt["elapsed_seconds"] = time.monotonic() - started
        receipt["final_resources"] = resources.status()
        publish(output, receipt)
        zip_path.unlink()
        receipt.update(raw_deleted=True, raw_zip_exists=zip_path.exists())
        publish(output, receipt)
    except Exception as error:
        receipt.update(status="FAILED_MONTHLY_V7_SOURCE_UNACCEPTED", error_type=type(error).__name__, reason=str(error)[:2048], raw_zip_exists=zip_path.exists(), elapsed_seconds=time.monotonic() - started)
        publish(output, receipt)
        raise
    return receipt


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--market", choices=("spot", "perp"), required=True)
    parser.add_argument("--symbol", choices=("BTCUSDT", "ETHUSDT"), required=True)
    parser.add_argument("--month", required=True)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    result = fetch_month(**vars(parser.parse_args()))
    print(json.dumps({key: result[key] for key in ("status", "completed_days", "elapsed_seconds", "peak_rss_bytes", "raw_deleted")}))
