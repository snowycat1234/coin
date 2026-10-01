"""Thin chronological loop over the accepted official daily Binance wrapper."""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

import pyarrow.parquet as pq

from quant.paths import ROOT
from quant.research_fast.trade_flow import CONTRACT, SCHEMA, checksum, require

STREAMS = (("spot", "BTCUSDT"), ("spot", "ETHUSDT"), ("perp", "BTCUSDT"), ("perp", "ETHUSDT"))
PINNED = {
    "scripts/hf_fetch.py": "b515610fefcbf8ad18209c12da27b8c98fb38162a95137bc816a7a2bd80d23c3",
    "src/quant/research_fast/trade_flow.py": (
        "be07e53ad9c2f1590c1ca8e7c6332f3953d53a79cd869bdc36052c0a24003439"
    ),
}
STORE = ROOT / "data/research_fast/trade_flow_5s_v1"


def dates(start, end):
    require(date(2025, 7, 1) <= start < end <= date(2026, 3, 1), "Locked/range denied")
    return [start + timedelta(days=index) for index in range((end - start).days)]


def resume_day(market, symbol, day, previous, *, store=STORE):
    feature = store / market / symbol / f"{day.isoformat()}.parquet"
    manifest = feature.with_suffix(".manifest.json")
    if not feature.exists() and not manifest.exists():
        return None
    require(feature.is_file() and manifest.is_file(), "Partial daily output; evidence retained")
    require(manifest.stat().st_size <= 131072, "Daily manifest size")
    value = json.loads(manifest.read_text())
    converted = value["conversion"]
    import hashlib

    expected_schema = hashlib.sha256(str(SCHEMA).encode()).hexdigest()
    require(
        value["status"] == "OFFICIAL_HF_DAY_ACCEPTED"
        and (value["market"], value["symbol"], value["date"]) == (market, symbol, day.isoformat())
        and value["checksum_status"] == "PASS"
        and value["engineering_fixture_hook"] is False
        and value["source_hashes"] == PINNED
        and value["feature_path"] == str(feature)
        and converted["version"] == "trade_flow_5s_v1"
        and converted["rows"] == 17280
        and converted["contract"] == CONTRACT
        and converted["schema_sha256"] == expected_schema
        and feature.stat().st_size == converted["parquet_bytes"]
        and checksum(feature) == converted["parquet_sha256"] == value["feature_sha256"],
        "Accepted daily source/schema/checksum/file binding changed",
    )
    require(not Path(value["owned_temporary_directory"]).exists(), "Raw temp still present")
    require(pq.read_metadata(feature).num_rows == 17280
            and pq.read_schema(feature) == SCHEMA, "Actual Parquet rows/schema mismatch")
    if previous is not None:
        require(
            converted["first_f"] == previous + 1
            and converted["cross_day_raw_boundary_verified"] is True,
            "Cross-day raw IDs unverified or discontinuous",
        )
    return value


def publish(path, value):
    temporary = path.with_suffix(path.suffix + ".task-tmp")
    with temporary.open("x") as writer:
        writer.write(json.dumps(value, indent=2, allow_nan=False) + "\n")
        writer.flush()
        os.fsync(writer.fileno())
    os.replace(temporary, path)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--start", type=date.fromisoformat, default=date(2025, 7, 1))
    parser.add_argument("--end", type=date.fromisoformat, default=date(2025, 12, 28))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    days = dates(args.start, args.end)
    output = args.output.resolve()
    require(output.is_relative_to(ROOT / "reports") and not output.exists(), "Exclusive report")
    for name, digest in PINNED.items():
        require(checksum(ROOT / name) == digest, "Frozen FR62 changed")
    spec = importlib.util.spec_from_file_location("official_hf_fetch", ROOT / "scripts/hf_fetch.py")
    wrapper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(wrapper)
    summary = {
        "status": "HISTORICAL_DATASET_BUILD_RUNNING",
        "start": args.start.isoformat(),
        "end_exclusive": args.end.isoformat(),
        "required_daily_stream_files": len(days) * 4,
        "completed_daily_stream_files": 0,
        "complete_common_days": 0,
        "source_hashes": PINNED,
        "manifests": [],
        "persistent_feature_bytes": sum(p.stat().st_size for p in STORE.rglob("*.parquet")),
        "feature_budget_bytes": 8_000_000_000,
        "alpha_eligible": False,
        "created_utc": datetime.now(UTC).isoformat(),
    }
    publish(output, summary)
    previous = {stream: None for stream in STREAMS}
    try:
        for day in days:
            for market, symbol in STREAMS:
                value = resume_day(market, symbol, day, previous[(market, symbol)])
                if value is None:
                    require(
                        summary["persistent_feature_bytes"] + 25_000_000 <= 8_000_000_000,
                        "Historical feature intake would exceed 8GB",
                    )
                    value = wrapper.fetch_day(
                        market, symbol, day, previous_day_last_raw_id=previous[(market, symbol)]
                    )
                    summary["persistent_feature_bytes"] += value["conversion"]["parquet_bytes"]
                previous[(market, symbol)] = value["conversion"]["last_l"]
                manifest = STORE / market / symbol / f"{day.isoformat()}.manifest.json"
                summary["manifests"].append({"path": str(manifest), "sha256": checksum(manifest)})
                require(summary["persistent_feature_bytes"] <= 8_000_000_000, "8GB exceeded")
                summary["completed_daily_stream_files"] += 1
                publish(output, summary)
                print(
                    json.dumps(
                        {
                            "completed": summary["completed_daily_stream_files"],
                            "required": summary["required_daily_stream_files"],
                            "date": str(day),
                            "market": market,
                            "symbol": symbol,
                        }
                    ),
                    flush=True,
                )
            summary["complete_common_days"] += 1
            publish(output, summary)
        summary["status"] = (
            "HISTORICAL_180D_DATASET_COMPLETE_PENDING_INDEPENDENT_QA"
            if len(days) >= 180
            else "REAL_HISTORICAL_SHORT_DATA_SMOKE_COMPLETE"
        )
    except Exception as error:
        summary.update(
            status="HISTORICAL_DATASET_BUILD_FAILED_UNACCEPTED",
            error_type=type(error).__name__,
            reason=str(error)[:2048],
        )
        raise
    finally:
        summary["updated_utc"] = datetime.now(UTC).isoformat()
        publish(output, summary)


if __name__ == "__main__":
    main()
