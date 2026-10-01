"""Thin httpx orchestration of official Binance daily ZIP/CHECKSUM conventions."""

from __future__ import annotations

import argparse
import json
import os
import tempfile
import time
from datetime import UTC, date, datetime
from pathlib import Path

import httpx

from quant import disk, resources
from quant.paths import ROOT, STATE
from quant.research_fast.trade_flow import checksum, convert_zip, require, validate_request

OFFICIAL_REPOSITORY = "https://github.com/binance/binance-public-data"
DATA_TERMS_URL = OFFICIAL_REPOSITORY + "/blob/master/TERMS_AND_CONDITIONS.md"
DATA_TERMS_SHA256 = "dcf358e9d18f598a7a635fac80f6e643fa24a0e111a4d39bda47f1e246b31eb1"
BASE = "https://data.binance.vision/data"
STORE = ROOT / "data/research_fast/trade_flow_5s_v1"
MAX_ZIP_BYTES = 512_000_000


def official_url(market, symbol, day):
    validate_request(market, symbol, day)
    category = "spot" if market == "spot" else "futures/um"
    filename = f"{symbol}-aggTrades-{day.isoformat()}.zip"
    return f"{BASE}/{category}/daily/aggTrades/{symbol}/{filename}"


def fetch_day(
    market,
    symbol,
    day,
    *,
    store=STORE,
    client=None,
    previous_day_last_raw_id=None,
    max_zip_bytes=MAX_ZIP_BYTES,
):
    started = time.monotonic()
    url = official_url(market, symbol, day)
    store = Path(store).resolve()
    fixture = client is not None
    require(
        store.is_relative_to(ROOT.resolve()) or fixture and store.is_relative_to(STATE.resolve()),
        "Historical features must stay on D/native STATE fixture",
    )
    require(type(max_zip_bytes) is int and 0 < max_zip_bytes <= MAX_ZIP_BYTES, "ZIP byte bound")
    initial_resources = resources.status()
    feature = store / market / symbol / f"{day.isoformat()}.parquet"
    manifest = store / market / symbol / f"{day.isoformat()}.manifest.json"
    require(not feature.exists() and not manifest.exists(), "Accepted daily output already exists")
    feature.parent.mkdir(parents=True, exist_ok=True)
    native = Path(tempfile.mkdtemp(prefix="hf-official-", dir=STATE))
    zip_path = native / url.rsplit("/", 1)[1]
    partial = native / "converted.parquet"
    receipt = {
        "status": "FAILED_OFFICIAL_PIPELINE_UNACCEPTED",
        "created_utc": datetime.now(UTC).isoformat(),
        "market": market,
        "symbol": symbol,
        "date": day.isoformat(),
        "official_repository": OFFICIAL_REPOSITORY,
        "data_terms_url": DATA_TERMS_URL,
        "data_terms_sha256": DATA_TERMS_SHA256,
        "use_purpose": "personal_nonproduction_research",
        "url": url,
        "checksum_url": url + ".CHECKSUM",
        "owned_temporary_directory": str(native),
        "raw_deleted": False,
        "engineering_fixture_hook": fixture,
        "initial_resources": initial_resources,
        "alpha_eligible": False,
        "real_time_quality_eligible": False,
        "executable_price_evidence": False,
        "source_hashes": {
            "scripts/hf_fetch.py": checksum(Path(__file__)),
            "src/quant/research_fast/trade_flow.py": checksum(
                ROOT / "src/quant/research_fast/trade_flow.py"
            ),
        },
    }
    own_client = client is None
    client = client or httpx.Client(timeout=120, follow_redirects=False)
    try:
        head = client.head(url)
        head.raise_for_status()
        length = head.headers.get("content-length")
        announced = int(length) if length is not None else max_zip_bytes
        require(0 < announced <= max_zip_bytes, "HEAD ZIP size above hard stream limit")
        guard_started = time.monotonic()
        receipt["initial_disk"] = disk.check(reserve=announced + 25_000_000)
        receipt["initial_disk_scan_seconds"] = time.monotonic() - guard_started
        with client.stream("GET", url + ".CHECKSUM") as response:
            response.raise_for_status()
            expected_bytes = b""
            for part in response.iter_bytes(chunk_size=1024):
                expected_bytes += part
                require(len(expected_bytes) <= 4096, "CHECKSUM response bound")
        checksum_fields = expected_bytes.decode("ascii").strip().split()
        require(
            len(checksum_fields) == 2
            and len(checksum_fields[0]) == 64
            and all(char in "0123456789abcdefABCDEF" for char in checksum_fields[0])
            and checksum_fields[1].lstrip("*") == zip_path.name,
            "Official CHECKSUM format/filename mismatch",
        )
        downloaded = 0
        with client.stream("GET", url) as response, zip_path.open("xb") as writer:
            response.raise_for_status()
            for part in response.iter_bytes(chunk_size=1_048_576):
                downloaded += len(part)
                require(downloaded <= max_zip_bytes, "ZIP hard download bound exceeded")
                writer.write(part)
            writer.flush()
            os.fsync(writer.fileno())
        require(length is None or downloaded == announced, "HEAD/download ZIP size mismatch")
        actual = checksum(zip_path)
        require(actual == checksum_fields[0].lower(), "Official CHECKSUM MISMATCH")
        receipt.update(zip_bytes=downloaded, source_checksum=actual, checksum_status="PASS")
        conversion_started = time.monotonic()
        converted = convert_zip(
            zip_path,
            partial,
            market=market,
            symbol=symbol,
            day=day,
            previous_day_last_raw_id=previous_day_last_raw_id,
        )
        require(converted["rows"] == 17280, "Daily 5s row count mismatch")
        conversion_seconds = time.monotonic() - conversion_started
        guard_started = time.monotonic()
        receipt["publish_disk"] = disk.check(reserve=converted["parquet_bytes"] + 1_000_000)
        receipt["publish_disk_scan_seconds"] = time.monotonic() - guard_started
        # Native staging avoids large CSV/ZIP materialization and only publishes
        # after every input row was verified. An exclusive copy cannot overwrite.
        with partial.open("rb") as reader, feature.open("xb") as writer:
            for part in iter(lambda: reader.read(1_048_576), b""):
                writer.write(part)
            writer.flush()
            os.fsync(writer.fileno())
        require(checksum(feature) == converted["parquet_sha256"], "Published Parquet SHA mismatch")
        receipt.update(
            status="OFFICIAL_HF_DAY_ACCEPTED",
            conversion=converted,
            feature_path=str(feature),
            feature_sha256=converted["parquet_sha256"],
            raw_deletion_authorized_after_manifest=True,
            conversion_seconds=conversion_seconds,
        )
        with manifest.open("x", encoding="utf-8") as writer:
            writer.write(json.dumps(receipt, indent=2, allow_nan=False) + "\n")
            writer.flush()
            os.fsync(writer.fileno())
        # Delete only these literal task-owned raw/temp files, after accepted
        # conversion and durable manifest. Failures retain source for diagnosis.
        zip_path.unlink()
        partial.unlink()
        receipt.update(
            raw_deleted=True,
            owned_raw_zip_exists=zip_path.exists(),
            manifest_path=str(manifest),
            manifest_sha256=checksum(manifest),
            final_resources=resources.status(),
            elapsed_seconds=time.monotonic() - started,
        )
        native.rmdir()
        return receipt
    except Exception as error:
        receipt.update(
            status="FAILED_OFFICIAL_PIPELINE_UNACCEPTED",
            error_type=type(error).__name__,
            reason=str(error)[:2048],
            owned_raw_zip_exists=zip_path.exists(),
        )
        with (native / "FAILURE.json").open("x", encoding="utf-8") as writer:
            writer.write(json.dumps(receipt, indent=2, allow_nan=False) + "\n")
        raise RuntimeError(f"Official pipeline failed; evidence retained: {native}") from error
    finally:
        if own_client:
            client.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--market", choices=("spot", "perp"), required=True)
    parser.add_argument("--symbol", choices=("BTCUSDT", "ETHUSDT"), required=True)
    parser.add_argument("--day", type=date.fromisoformat, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    require(
        output.is_relative_to(ROOT / "reports") and not output.exists(), "New D report required"
    )
    with output.open("x", encoding="utf-8") as writer:
        try:
            receipt = fetch_day(args.market, args.symbol, args.day)
        except Exception as error:
            writer.write(
                json.dumps(
                    {
                        "status": "FAILED_OFFICIAL_PIPELINE_UNACCEPTED",
                        "market": args.market,
                        "symbol": args.symbol,
                        "date": args.day.isoformat(),
                        "error_type": type(error).__name__,
                        "reason": str(error)[:2048],
                        "alpha_eligible": False,
                    },
                    indent=2,
                )
                + "\n"
            )
            writer.flush()
            os.fsync(writer.fileno())
            raise
        writer.write(json.dumps(receipt, indent=2, allow_nan=False) + "\n")
        writer.flush()
        os.fsync(writer.fileno())
    print(json.dumps({key: receipt[key] for key in ("status", "raw_deleted", "feature_path")}))


if __name__ == "__main__":
    main()
