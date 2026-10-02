"""One explicit immutable daily/monthly logical view for the shared research dataset."""
from __future__ import annotations

import json
from datetime import date, timedelta
from pathlib import Path

import pyarrow.parquet as pq

from quant.paths import ROOT, STATE
from quant.research_fast.dataset import ShardSpec
from quant.research_fast.trade_flow_v2 import CONTRACT, SCHEMA, checksum, require, source_hashes

DAILY_STORE = ROOT / "data/research_fast/trade_flow_5s_v2"
MONTHLY_STORE = ROOT / "data/research_fast/trade_flow_5s_v2_monthly_v7"
STREAMS = (("spot", "BTCUSDT"), ("spot", "ETHUSDT"), ("perp", "BTCUSDT"), ("perp", "ETHUSDT"))


def _json(path, limit=2_000_000):
    path = Path(path).resolve()
    require(path.is_relative_to(ROOT) and path.is_file() and path.stat().st_size <= limit, "Explicit bounded D proof")
    return json.loads(path.read_text())


def monthly_records(pairs):
    """Only fully completed, independently audited months; never glob unseen history."""
    records, proofs = {}, []
    for receipt_path, qa_path in pairs:
        receipt_path, qa_path = Path(receipt_path).resolve(), Path(qa_path).resolve()
        receipt, qa = _json(receipt_path), _json(qa_path)
        require(qa["status"] == "PASS_MONTHLY_V7_INDEPENDENT_SOURCE_QA" and qa["receipt_path"] == str(receipt_path) and qa["receipt_sha256"] == checksum(receipt_path), "Independent monthly QA/receipt SHA binding")
        require(receipt["status"] == "OFFICIAL_MONTHLY_V7_COMPLETE_PENDING_INDEPENDENT_QA" and receipt["raw_deleted"] and receipt["zip_crc_read_to_eof"] and receipt["checksum_status"] == "PASS" and receipt["required_days"] == receipt["completed_days"] == qa["checked_days"] == len(receipt["daily"]) == len(qa["files"]) and qa["checked_rows"] == receipt["required_days"] * 17280, "Complete actual monthly evidence")
        native = Path(receipt["owned_temporary_directory"]).resolve()
        require(native.is_relative_to(STATE.resolve()) and native.is_dir() and not any(native.iterdir()), "Actual month raw/temp absence")
        fields = receipt["official_checksum_text"].strip().split()
        recheck = qa["official_checksum_rechecked"].strip().split()
        require(fields == recheck and len(fields) == 2 and fields[0].lower() == receipt["zip_sha256"] and fields[1].lstrip("*") == receipt["url"].rsplit("/", 1)[1], "Official monthly CHECKSUM proof")
        for name, sha in receipt["source_hashes"].items():
            require(checksum(ROOT / name) == sha, "Monthly source byte binding changed")
        require(checksum(ROOT / "scripts/research_v7/audit_monthly.py") == qa["auditor_sha256"], "Independent auditor byte binding changed")
        first = date.fromisoformat(receipt["month"] + "-01")
        last = (first.replace(day=28) + timedelta(days=4)).replace(day=1)
        require(date(2025, 7, 1) <= first < last <= date(2026, 3, 1) and (last - first).days == receipt["required_days"], "Development month seal")
        for index, (entry, checked) in enumerate(zip(receipt["daily"], qa["files"], strict=True)):
            manifest = Path(entry["path"]).resolve()
            require(manifest.is_relative_to(MONTHLY_STORE) and str(manifest) == checked["manifest_path"] and entry["sha256"] == checked["manifest_sha256"] == checksum(manifest), "Actual monthly daily manifest SHA")
            value = _json(manifest, 131_072)
            day = first + timedelta(days=index)
            converted = value["conversion"]
            key = value["market"], value["symbol"], day
            require(key not in records and key[:2] in STREAMS and key[:2] == (receipt["market"], receipt["symbol"]) and value["date"] == str(day), "Duplicate or misordered stream/day")
            require(value["status"] == "OFFICIAL_MONTHLY_V7_DAY_SOURCE_VERIFIED" and value["monthly_archive_sha256"] == receipt["zip_sha256"] and value["source_hashes"] == receipt["source_hashes"] and value["checksum_status"] == "PASS" and converted["adapter_source_hashes"] == source_hashes() and converted["contract"] == CONTRACT and converted["raw_gap_cause"] == "UNCONFIRMED", "Original converter/month provenance")
            feature = Path(value["feature_path"]).resolve()
            require(feature.is_relative_to(MONTHLY_STORE) and str(feature) == checked["parquet_path"] and checksum(feature) == value["feature_sha256"] == converted["parquet_sha256"] == entry["parquet_sha256"] == checked["parquet_sha256"] and feature.stat().st_size == converted["parquet_bytes"] == entry["parquet_bytes"] and pq.read_schema(feature) == SCHEMA and pq.read_metadata(feature).num_rows == converted["rows"] == checked["actual_rows"] == 17280, "Actual shared Parquet bytes/schema")
            records[key] = {"manifest": manifest, "value": value, "shard": ShardSpec.from_conversion(feature, converted, checksum_verified=True)}
            require((records[key]["shard"].market, records[key]["shard"].symbol, records[key]["shard"].day) == key, "Conversion/daily identity")
        proofs.append({"receipt_path": str(receipt_path), "receipt_sha256": checksum(receipt_path), "qa_path": str(qa_path), "qa_sha256": checksum(qa_path), "month": receipt["month"], "market": receipt["market"], "symbol": receipt["symbol"]})
    return records, proofs


def build_shards(start, end, *, monthly_pairs=()):
    """Daily-first selection, one shard per stream/day; labels/scalers/models are unchanged."""
    require(type(start) is date and type(end) is date and date(2025, 7, 1) <= start < end <= date(2026, 3, 1), "Explicit development range")
    monthly, proofs = monthly_records(monthly_pairs)
    shards, selected, previous = [], [], {}
    for offset in range((end - start).days):
        day = start + timedelta(days=offset)
        for market, symbol in STREAMS:
            key = market, symbol, day
            original = DAILY_STORE / market / symbol / f"{day}.manifest.json"
            if original.exists():
                shard, manifest, kind = ShardSpec.from_manifest(original), original, "original_daily"
                value = _json(manifest, 131_072)
                require(checksum(shard.path) == shard.sha256 and pq.read_schema(shard.path) == SCHEMA and pq.read_metadata(shard.path).num_rows == shard.rows == 17280, "Actual original daily SHA/schema")
            else:
                require(key in monthly, f"Missing verified stream/day: {key}")
                item = monthly[key]
                shard, manifest, value, kind = item["shard"], item["manifest"], item["value"], "independently_audited_monthly"
            converted = value["conversion"]
            if (market, symbol) in previous:
                raw, agg = previous[(market, symbol)]
                require(converted["cross_day_scope_boundary_verified"] and converted["first_f"] > raw and converted["first_a"] > agg, "Mixed-view original ID continuity")
                if market == "spot":
                    require(converted["first_f"] == raw + 1, "Mixed-view Spot raw adjacency")
                else:
                    require(converted["first_a"] == agg + 1, "Mixed-view Perp aggregate adjacency")
                require(converted["cross_day_unrepresented_raw_ids"] == converted["first_f"] - raw - 1, "Mixed-view raw boundary arithmetic")
            previous[(market, symbol)] = converted["last_l"], converted["last_a"]
            shards.append(shard)
            selected.append({"market": market, "symbol": symbol, "day": str(day), "source_kind": kind, "manifest_path": str(manifest), "manifest_sha256": checksum(manifest), "parquet_path": str(shard.path), "parquet_sha256": shard.sha256})
    require(len(shards) == (end - start).days * len(STREAMS), "Complete unique logical range")
    return shards, {"start": str(start), "end_exclusive": str(end), "source_view_sha256": checksum(Path(__file__)), "monthly_proofs": proofs, "selected": selected}
