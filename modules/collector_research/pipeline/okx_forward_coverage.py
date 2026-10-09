"""Fixed OKX-only source coverage; no strategies, training or minute bulk intake."""

from __future__ import annotations

import argparse
import json
import math
import shutil
import time
from collections import Counter
from copy import deepcopy
from dataclasses import asdict, dataclass
from decimal import Decimal
from pathlib import Path

import requests

from .common import DAY_MS, atomic_text, dump, sha256
from .public_supplement import (
    BASES,
    Budget,
    Failure,
    Job,
    _payload,
    _read,
    bars_request,
    coverage,
    fingerprint,
    instrument_identity,
    metadata_request,
    normalize,
)

VERSION = "okx-forward-coverage-1"
ASSETS = ("BTC", "ETH", "SOL", "XRP", "DOGE")
DAILY_START, VALIDATION_START, END = 1735689600000, 1784073600000, 1791504000000
DOCS = "https://app.okx.com/docs-v5/en/#public-data-rest-api-get-funding-rate-history"


@dataclass(frozen=True)
class ForwardJob(Job):
    def __post_init__(self):
        asset = self.reference_symbol.removesuffix("USDT")
        if (
            self.provider != "okx"
            or asset not in ASSETS
            or self.market != "perpetual"
            or self.instrument_id != asset + "-USDT-SWAP"
        ):
            raise ValueError("Only the five explicitly authorized OKX USDT perpetuals")
        if (
            self.interval not in ("1d", "1m")
            or self.kind not in ("trade", "mark")
            or type(self.start_ms) is not int
            or type(self.end_ms) is not int
            or self.start_ms % self.step
            or self.end_ms % self.step
        ):
            raise ValueError("Explicit aligned candle clocks and kinds required")
        if self.interval == "1d":
            if (
                self.kind != "trade"
                or not DAILY_START <= self.start_ms < self.end_ms <= END
                or self.count > 646
            ):
                raise ValueError("Only January 2025–October 8 2026 daily trade bars")
        elif self.start_ms != VALIDATION_START or self.end_ms != VALIDATION_START + 100 * self.step:
            raise ValueError("Only the fixed July 15 100-minute retention sample; no bulk intake")
        if self.retention_start_ms is not None or self.retention_evidence is not None:
            raise ValueError("This stage measures actual retention, not a supplied assumption")


@dataclass
class CoverageBudget(Budget):
    max_requests: int = 70
    max_bytes: int = 10_000_000
    min_interval_seconds: float = 1.0

    def __post_init__(self):
        if (
            not 1 <= self.max_requests <= 70
            or not 0 < self.max_bytes <= 10_000_000
            or not 0 < self.max_response_bytes <= 1_000_000
            or not 1 <= self.max_attempts <= 2
            or not math.isfinite(self.min_interval_seconds)
            or self.min_interval_seconds < 1
            or not 0 <= self.requests_used <= self.max_requests
            or not 0 <= self.bytes_used <= self.max_bytes
        ):
            raise ValueError("Forward coverage exceeds explicit 70-request/10 MB bounds")


def daily_job(asset):
    return ForwardJob(
        "okx", asset + "USDT", asset + "-USDT-SWAP", "perpetual", "trade", "1d", DAILY_START, END
    )


def sample_job(asset, kind):
    return ForwardJob(
        "okx",
        asset + "USDT",
        asset + "-USDT-SWAP",
        "perpetual",
        kind,
        "1m",
        VALIDATION_START,
        VALIDATION_START + 6_000_000,
    )


def funding_rows(raw, job, identity, record, end):
    records = _payload(raw, "okx").get("data")
    if not isinstance(records, list) or any(not isinstance(r, dict) for r in records):
        raise Failure("INVALID_RESPONSE", "Funding history list required")
    rows, seen = [], set()
    for item in records:
        stamp = item.get("fundingTime")
        if (
            item.get("instId") != job.instrument_id
            or item.get("instType") != "SWAP"
            or not isinstance(stamp, str)
            or not stamp.isascii()
            or not stamp.isdigit()
        ):
            raise Failure("IDENTITY_MISMATCH", "Exact native funding instrument/time required")
        timestamp = int(stamp)
        if not VALIDATION_START <= timestamp < end or timestamp in seen:
            raise Failure("INVALID_RESPONSE", "Duplicate or out-of-window funding event")
        seen.add(timestamp)
        for name in ("fundingRate", "realizedRate"):
            value = item.get(name)
            if not isinstance(value, str):
                raise Failure("INVALID_RESPONSE", "Original published rate strings required")
            if value:
                try:
                    if not Decimal(value).is_finite():
                        raise ValueError("Nonfinite funding rate")
                except (ValueError, ArithmeticError) as exc:
                    raise Failure("INVALID_RESPONSE", "Invalid raw funding rate") from exc
        rows.append(
            dict(
                provider="okx",
                instrument_id=job.instrument_id,
                market="perpetual",
                kind="funding",
                funding_time_ms=timestamp,
                fundingRate=item["fundingRate"],
                realizedRate=item["realizedRate"],
                rate_unit="DIMENSIONLESS_PUBLISHED_DECIMAL_NOT_RESCALED",
                predicted_rate_field="fundingRate",
                actual_rate_field="realizedRate",
                native_record=item,
                identity_sha256=fingerprint(identity),
                raw_sha256=record["raw_sha256"],
                received_ms=record["received_ms"],
                available_ms=record["received_ms"],
                historical_available_ms=None,
                publication_time_certified=False,
                account_settlement_verified=False,
            )
        )
    return sorted(rows, key=lambda r: r["funding_time_ms"])


def funding_coverage(rows):
    stamps = sorted(r["funding_time_ms"] for r in rows)
    gaps = Counter(b - a for a, b in zip(stamps, stamps[1:], strict=False))
    # Dynamic schedules are documented. The 8-hour grid is a named diagnostic,
    # never a claim that an unobserved schedule or cash charge has been certified.
    assumed = set(range(VALIDATION_START, END, 8 * 3_600_000))
    missing = sorted(assumed - set(stamps))
    return dict(
        status="OBSERVED_HISTORY_NOT_SCHEDULE_CERTIFIED",
        event_count=len(stamps),
        requested_start_ms=VALIDATION_START,
        requested_end_ms_exclusive=END,
        earliest_event_ms=stamps[0] if stamps else None,
        latest_event_ms=stamps[-1] if stamps else None,
        observed_interval_histogram_ms={str(k): v for k, v in sorted(gaps.items())},
        intervals_longer_than_8h_ms=[
            [a, b] for a, b in zip(stamps, stamps[1:], strict=False) if b - a > 8 * 3_600_000
        ],
        assumed_8h_grid_expected_events=len(assumed),
        assumed_8h_grid_missing_event_ms=missing,
        historical_schedule_certified=False,
        missing_realized_rate_events=sum(not r["realizedRate"] for r in rows),
        documentary_source=DOCS,
    )


def _save_rows(directory, filename, rows, manifest):
    output = directory / filename
    atomic_text(
        output, "".join(json.dumps(row, sort_keys=True, allow_nan=False) + "\n" for row in rows)
    )
    manifest.setdefault("normalized", {})[filename] = dict(sha256=sha256(output), rows=len(rows))


def _reuse_metadata(job, directory, manifest, reuse_cache):
    if reuse_cache is None:
        return
    path, params = metadata_request(job)
    key = fingerprint([BASES["okx"] + path, params])
    if any(r["request_key"] == key and r["status"] == "OK" for r in manifest["requests"]):
        return
    # Only inspect caller-selected public supplement receipts, never local accounts/inventories.
    for receipt in sorted(Path(reuse_cache).glob("okx*/*/manifest.json")):
        prior = json.loads(receipt.read_text())
        for record in prior.get("requests", []):
            if record.get("request_key") != key or record.get("status") != "OK":
                continue
            source = receipt.parent / record["raw_file"]
            if sha256(source) != record["raw_sha256"]:
                raise ValueError("Reusable public metadata checksum mismatch")
            instrument_identity(job, source.read_bytes())
            shutil.copyfile(source, directory / record["raw_file"])
            reused = deepcopy(record)
            reused["reused_source_receipt_sha256"] = sha256(receipt)
            reused["reused_source_binding"] = prior["binding"]
            manifest["requests"].append(reused)
            return


def collect_forward(cache, reuse_cache=None, session=None, budget=None):
    cache = Path(cache).resolve()
    if cache.is_relative_to(Path(__file__).resolve().parents[3]):
        raise ValueError("Coverage cache must be outside the source checkout")
    binding = dict(
        version=VERSION,
        source_sha256=sha256(Path(__file__)),
        adapter_source_sha256=sha256(Path(__file__).with_name("public_supplement.py")),
        assets=list(ASSETS),
        provider="okx",
        market="perpetual",
        dataset_role="OKX_ONLY_FORWARD_SOURCE_COVERAGE_NO_WALLET",
        daily_start_ms=DAILY_START,
        funding_start_ms=VALIDATION_START,
        end_ms_exclusive=END,
        historical_publication_certified=False,
        historical_instrument_rules_certified=False,
        frozen_selector_certified=False,
        strategy_changed=False,
        training=False,
        wallet_backtest=False,
    )
    cache.mkdir(parents=True, exist_ok=True)
    index_path = cache / "COVERAGE.json"
    index = (
        json.loads(index_path.read_text())
        if index_path.exists()
        else dict(binding=binding, assets=[], status="PENDING")
    )
    if index["binding"] != binding:
        raise ValueError("Saved forward source binding changed")
    saved_requests = []
    for receipt in cache.glob("*/manifest.json"):
        saved_requests.extend(json.loads(receipt.read_text())["requests"])
    own = [r for r in saved_requests if "reused_source_receipt_sha256" not in r]
    budget = budget or CoverageBudget(
        requests_used=len(own), bytes_used=sum(r.get("body_bytes", 0) for r in own)
    )
    if not isinstance(budget, CoverageBudget):
        raise ValueError("Explicit independent coverage budget required")
    if reuse_cache and (Path(reuse_cache) / "okx/access-stop.json").exists():
        budget.denied_providers.add("okx")
    if (cache / "access-stop.json").exists():
        budget.denied_providers.add("okx")
    owned_session = session is None
    session = session or requests.Session()
    started, results = time.monotonic(), []
    try:
        for asset in ASSETS:
            job = daily_job(asset)
            directory = cache / job.instrument_id
            directory.mkdir(exist_ok=True)
            receipt = directory / "manifest.json"
            manifest = (
                json.loads(receipt.read_text())
                if receipt.exists()
                else dict(binding=binding, job=asdict(job), requests=[], status="PENDING")
            )
            if manifest["binding"] != binding:
                raise ValueError("Saved instrument source binding changed")
            for record in manifest["requests"]:
                if (
                    "raw_file" in record
                    and sha256(directory / record["raw_file"]) != record["raw_sha256"]
                ):
                    raise ValueError("Retained forward raw checksum mismatch")
            for name, info in manifest.get("normalized", {}).items():
                if sha256(directory / name) != info["sha256"]:
                    raise ValueError("Retained forward normalized checksum mismatch")
            daily, funds, samples = [], [], {}
            try:
                _reuse_metadata(job, directory, manifest, reuse_cache)
                raw, meta = _read(job, *metadata_request(job), directory, manifest, budget, session)
                identity = instrument_identity(job, raw)
                identity["metadata_raw_sha256"] = meta["raw_sha256"]
                manifest["identity"] = identity
                for start in range(DAILY_START, END, 100 * DAY_MS):
                    end = min(start + 100 * DAY_MS, END)
                    raw, record = _read(
                        job, *bars_request(job, start, end), directory, manifest, budget, session
                    )
                    daily.extend(
                        normalize(
                            job,
                            raw,
                            identity,
                            record["received_ms"],
                            record["raw_sha256"],
                            start,
                            end,
                        )
                    )
                manifest["daily_coverage"] = coverage(job, daily)
                cursor = END
                while True:
                    params = dict(
                        instId=job.instrument_id,
                        after=cursor,
                        before=VALIDATION_START - 1,
                        limit=400,
                    )
                    raw, record = _read(
                        job,
                        "/api/v5/public/funding-rate-history",
                        params,
                        directory,
                        manifest,
                        budget,
                        session,
                    )
                    page = funding_rows(raw, job, identity, record, cursor)
                    funds.extend(page)
                    if len(page) < 400:
                        manifest["funding_pagination_ended"] = "SHORT_OR_EMPTY_PROVIDER_PAGE"
                        break
                    cursor = page[0]["funding_time_ms"]
                    if cursor <= VALIDATION_START:
                        break
                funds.sort(key=lambda row: row["funding_time_ms"])
                manifest["funding_coverage"] = funding_coverage(funds)
                for kind in ("trade", "mark"):
                    sample = sample_job(asset, kind)
                    raw, record = _read(
                        sample,
                        *bars_request(sample, sample.start_ms, sample.end_ms),
                        directory,
                        manifest,
                        budget,
                        session,
                    )
                    rows = normalize(
                        sample, raw, identity, record["received_ms"], record["raw_sha256"]
                    )
                    if kind == "mark":
                        for row in rows:
                            row["volume_units"] = None
                    samples[kind] = rows
                    manifest.setdefault("minute_samples", {})[kind] = dict(
                        coverage=coverage(sample, rows),
                        response_body_bytes=record["body_bytes"],
                        sample_bars=100,
                        raw_sha256=record["raw_sha256"],
                        retention_scope="ONLY_THIS_100_MINUTE_WINDOW_NOT_FULL_HISTORY",
                    )
                manifest["status"] = "SOURCE_COVERAGE_ASSESSED_NO_WALLET"
                manifest.pop("last_failure", None)
            except Failure as exc:
                manifest.update(
                    status=exc.status, last_failure=dict(status=exc.status, detail=str(exc))
                )
                if exc.status in ("PERMISSION_DENIED", "RATE_LIMITED"):
                    dump(
                        dict(status=exc.status, detail=str(exc), provider="okx"),
                        cache / "access-stop.json",
                    )
            _save_rows(directory, "daily.jsonl", daily, manifest)
            _save_rows(directory, "funding.jsonl", funds, manifest)
            for kind, rows in samples.items():
                _save_rows(directory, "minute-" + kind + "-sample.jsonl", rows, manifest)
            manifest.setdefault("daily_coverage", coverage(job, daily))
            dump(manifest, receipt)
            results.append(
                dict(
                    instrument_id=job.instrument_id,
                    status=manifest["status"],
                    daily_coverage=manifest["daily_coverage"],
                    funding_coverage=manifest.get("funding_coverage"),
                    minute_samples=manifest.get("minute_samples"),
                    manifest=job.instrument_id + "/manifest.json",
                    manifest_sha256=sha256(receipt),
                )
            )
            index.update(
                assets=results,
                requests=budget.requests_used,
                body_bytes=budget.bytes_used,
                elapsed_seconds=time.monotonic() - started,
            )
            dump(index, index_path)
            print(json.dumps(results[-1]), flush=True)
            if budget.denied_providers or manifest["status"] in (
                "BUDGET_EXHAUSTED",
                "RESPONSE_LIMIT",
            ):
                break
    finally:
        if owned_session:
            session.close()
    index.update(
        status="SOURCE_COVERAGE_ASSESSED_NO_WALLET",
        assets=results,
        requests=budget.requests_used,
        body_bytes=budget.bytes_used,
        elapsed_seconds=time.monotonic() - started,
    )
    minutes = (END - VALIDATION_START) // 60_000
    request_count = 2 * len(ASSETS) * math.ceil(minutes / 100)
    sample_stats = [
        entry["minute_samples"][kind]
        for entry in results
        if entry.get("minute_samples")
        for kind in ("trade", "mark")
    ]
    estimates = [
        s["response_body_bytes"] / s["sample_bars"]
        for s in sample_stats
        if s["coverage"]["status"] == "COMPLETE"
    ]
    index["bulk_minute_estimate"] = dict(
        status="ESTIMATE_ONLY_NOT_AUTHORIZED_NOT_RUN",
        interval_days=86,
        bars_per_instrument_per_kind=minutes,
        trade_and_mark_total_bars=minutes * 10,
        minimum_candle_requests=request_count,
        minimum_seconds_at_1_request_per_second=request_count,
        estimated_response_body_bytes=round(sum(estimates) * minutes)
        if len(estimates) == 10
        else None,
        scope="July15–October9 trade+mark five perpetuals; funding/metadata separate",
        limitations=("100-minute samples do not prove full-window retention/coverage; "
                     "wire bytes unknown"),
    )
    dump(index, index_path)
    return index


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache", type=Path, required=True)
    parser.add_argument("--reuse-public-cache", type=Path)
    args = parser.parse_args()
    result = collect_forward(args.cache, args.reuse_public_cache)
    print(
        json.dumps(
            dict(
                status=result["status"],
                requests=result["requests"],
                body_bytes=result["body_bytes"],
                estimate=result["bulk_minute_estimate"],
            )
        )
    )
    return (
        0
        if len(result["assets"]) == 5
        and all(r["status"] == "SOURCE_COVERAGE_ASSESSED_NO_WALLET" for r in result["assets"])
        else 1
    )


if __name__ == "__main__":
    raise SystemExit(main())
