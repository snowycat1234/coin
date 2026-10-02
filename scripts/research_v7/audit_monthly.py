"""Independent source/actual-row audit of one completed official monthly conversion."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import resource
import time
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

import httpx
import pyarrow.parquet as pq

from quant.paths import ROOT, STATE
from quant.research_fast.trade_flow_v2 import CONTRACT, SCHEMA, checksum, require, source_hashes


def audit(receipt_path, output):
    started = time.monotonic()
    require(receipt_path.resolve().is_relative_to(ROOT / "reports"), "D source receipt required")
    require(output.resolve().is_relative_to(ROOT / "reports") and not output.exists(), "Exclusive audit report")
    source = json.loads(receipt_path.read_text())
    result = {
        "status": "FAILED_MONTHLY_V7_INDEPENDENT_SOURCE_QA", "created_utc": datetime.now(UTC).isoformat(),
        "receipt_path": str(receipt_path.resolve()), "receipt_sha256": checksum(receipt_path),
        "auditor_sha256": checksum(Path(__file__)), "checked_days": 0, "checked_rows": 0,
        "files": [], "alpha_eligible": False, "real_time_quality_eligible": False,
        "limitations": ["Independent checks do not reconstruct each raw archive row after deletion", "Monthly source QA is not predictive or tradable economic evidence"],
    }
    try:
        require(source["status"] == "OFFICIAL_MONTHLY_V7_COMPLETE_PENDING_INDEPENDENT_QA" and source["completed_days"] == source["required_days"] and len(source["daily"]) == source["required_days"] and source["checksum_status"] == "PASS" and source["raw_deleted"] and source["zip_crc_read_to_eof"], "Source month not actually complete")
        bindings = source_hashes()
        for path, sha in source["source_hashes"].items():
            require(checksum(ROOT / path) == sha, "Actual source binding changed")
        native = Path(source["owned_temporary_directory"]).resolve()
        require(native.is_relative_to(STATE.resolve()) and native.is_dir() and not any(native.iterdir()), "Raw/temp must actually be absent")
        start = date.fromisoformat(source["month"] + "-01")
        end = (start.replace(day=28) + timedelta(days=4)).replace(day=1)
        require((end - start).days == source["required_days"] and date(2025, 7, 1) <= start < end <= date(2026, 3, 1), "Month/range seal")
        prior_path = Path(source["prior_boundary"]["path"])
        require(checksum(prior_path) == source["prior_boundary"]["sha256"], "Prior manifest changed")
        prior = json.loads(prior_path.read_text())
        prior_feature = Path(prior["feature_path"])
        require(checksum(prior_feature) == prior["feature_sha256"], "Prior actual feature changed")
        previous_raw, previous_agg = source["prior_boundary"]["last_l"], source["prior_boundary"]["last_a"]
        require((previous_raw, previous_agg) == (prior["conversion"]["last_l"], prior["conversion"]["last_a"]), "Prior actual ID boundary")
        with httpx.Client(timeout=30, follow_redirects=False) as client:
            with client.stream("GET", source["checksum_url"]) as response:
                response.raise_for_status()
                official = b""
                for part in response.iter_bytes(1024):
                    official += part
                    require(len(official) <= 4096, "Official CHECKSUM response bound")
        fields = official.decode("ascii").strip().split()
        require(len(fields) == 2 and fields[0].lower() == source["zip_sha256"] and fields[1].lstrip("*") == source["url"].rsplit("/", 1)[1], "Independent official CHECKSUM changed")
        result["official_checksum_rechecked"] = official.decode("ascii")
        for index, entry in enumerate(source["daily"]):
            day = start + timedelta(days=index)
            opened = int(datetime.combine(day, datetime.min.time(), tzinfo=UTC).timestamp()) * 1_000_000
            manifest_path = Path(entry["path"])
            require(manifest_path.resolve().is_relative_to(ROOT / "data/research_fast/trade_flow_5s_v2_monthly_v7") and checksum(manifest_path) == entry["sha256"], "Month manifest path/SHA")
            daily = json.loads(manifest_path.read_text())
            converted = daily["conversion"]
            feature = Path(daily["feature_path"])
            require(daily["status"] == "OFFICIAL_MONTHLY_V7_DAY_SOURCE_VERIFIED" and daily["market"] == source["market"] and daily["symbol"] == source["symbol"] and daily["date"] == str(day) and daily["monthly_archive_sha256"] == source["zip_sha256"] and daily["source_hashes"] == source["source_hashes"], "Daily/month binding")
            require(converted["adapter_source_hashes"] == bindings and converted["contract"] == CONTRACT and converted["schema_sha256"] == hashlib.sha256(str(SCHEMA).encode()).hexdigest() and converted["raw_gap_cause"] == "UNCONFIRMED", "Frozen converter/schema/raw gap scope")
            require(checksum(feature) == daily["feature_sha256"] == converted["parquet_sha256"] == entry["parquet_sha256"] and feature.stat().st_size == entry["parquet_bytes"] == converted["parquet_bytes"] and pq.read_schema(feature) == SCHEMA and pq.read_metadata(feature).num_rows == 17280, "Actual Parquet SHA/schema/size/rows")
            require(converted["cross_day_scope_boundary_verified"] and converted["first_f"] > previous_raw and converted["first_a"] > previous_agg, "Cross-day monotonic original IDs")
            if source["market"] == "spot":
                require(converted["first_f"] == previous_raw + 1 and converted["original_raw_range_gap_events"] == 0, "Spot raw adjacency")
            else:
                require(converted["first_a"] == previous_agg + 1, "Perp aggregate adjacency")
            require(converted["cross_day_unrepresented_raw_ids"] == converted["first_f"] - previous_raw - 1, "Actual raw boundary arithmetic")
            count, aggregate_count, empty_bins = 0, 0, 0
            for batch in pq.ParquetFile(feature).iter_batches(batch_size=512, use_threads=False):
                for row in batch.to_pylist():
                    require(row["market"] == source["market"] and row["symbol"] == source["symbol"] and row["date"] == str(day) and row["timestamp"] == opened + count * 5_000_000 and row["available_us"] == row["close_us"] == row["timestamp"] + 5_000_000 and row["quality"] == 0, "Actual causal UTC row geometry")
                    require(row["trade_count"] == row["agg_count"] == row["buy_count"] + row["sell_count"] and min(row["trade_count"], row["buy_count"], row["sell_count"]) >= 0, "Observed aggregate counts")
                    for key, value in row.items():
                        if isinstance(value, float):
                            require(math.isfinite(value), "Actual finite derived floats")
                    require(math.isclose(row["aggressive_buy_notional"] + row["aggressive_sell_notional"], row["quote_notional"], rel_tol=1e-12, abs_tol=1e-6), "Actual buy/sell notional partition")
                    if row["empty_bin"]:
                        require(row["trade_count"] == row["base_volume"] == row["quote_notional"] == 0 and all(row[k] is None for k in ("open", "high", "low", "close", "vwap", "first_trade_us", "last_trade_us")), "Actual known-empty bin")
                        empty_bins += 1
                    else:
                        require(row["trade_count"] > 0 and row["timestamp"] <= row["first_trade_us"] <= row["last_trade_us"] < row["close_us"], "Actual populated bin timestamp")
                    aggregate_count += row["trade_count"]
                    count += 1
            require(count == converted["rows"] == 17280 and aggregate_count == converted["observed_aggregate_count"] and empty_bins == converted["empty_bins"], "Actual daily totals")
            overlap = daily["daily_overlap"]
            if overlap is not None:
                require(checksum(Path(overlap["manifest_path"])) == overlap["manifest_sha256"], "Prior overlap manifest changed")
                old = json.loads(Path(overlap["manifest_path"]).read_text())
                require(checksum(Path(old["feature_path"])) == overlap["parquet_sha256"] == converted["parquet_sha256"], "Independent exact monthly/daily actual byte equality")
            previous_raw, previous_agg = converted["last_l"], converted["last_a"]
            result["checked_days"] += 1
            result["checked_rows"] += count
            result["files"].append({"manifest_path": str(manifest_path), "manifest_sha256": entry["sha256"], "parquet_path": str(feature), "parquet_sha256": entry["parquet_sha256"], "overlap_checked": overlap is not None, "actual_rows": count})
            print(json.dumps({"qa_checked_days": result["checked_days"], "required_days": source["required_days"], "qa_checked_rows": result["checked_rows"]}), flush=True)
        result["status"] = "PASS_MONTHLY_V7_INDEPENDENT_SOURCE_QA"
    except Exception as error:
        result.update(error_type=type(error).__name__, reason=str(error)[:2048])
        raise
    finally:
        result["elapsed_seconds"] = time.monotonic() - started
        result["peak_rss_bytes"] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024
        with output.open("x", encoding="utf8") as writer:
            writer.write(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False) + "\n")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = audit(args.receipt, args.output)
    print(json.dumps({key: result[key] for key in ("status", "checked_days", "checked_rows", "elapsed_seconds", "peak_rss_bytes")}))
