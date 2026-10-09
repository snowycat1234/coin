"""Sequential, date-checkpointed OKX CORE5 minute intake; no wallet or models."""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import math
import shutil
import subprocess
import time
from copy import deepcopy
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import requests

from .common import DAY_MS, dump, sha256
from .okx_forward_coverage import ASSETS, END, VALIDATION_START
from .public_supplement import (
    Budget,
    Failure,
    Job,
    _payload,
    _read,
    coverage,
    fingerprint,
    normalize,
)

VERSION = "okx-core5-minute-intake-1"
MINUTE = 60_000
PAGE_SIZE = {"trade": 300, "mark": 100}
BRANCH = "research/okx-forward-coverage-20261009"
PUBLIC_PREFIX = Path("research/okx-forward-coverage-20261009/minute-intake")
PARENT_COMMIT = "856ecfabe3d889f87a3e1f1cdb6672d127c41d53"
DOCS = {
    "trade": "https://app.okx.com/docs-v5/en/#order-book-trading-market-data-get-candlesticks-history",
    "mark": "https://app.okx.com/docs-v5/en/#public-data-rest-api-get-mark-price-candlesticks-history",
}


@dataclass(frozen=True)
class MinuteJob(Job):
    def __post_init__(self):
        asset = self.reference_symbol.removesuffix("USDT")
        if (
            self.provider != "okx"
            or asset not in ASSETS
            or self.market != "perpetual"
            or self.instrument_id != asset + "-USDT-SWAP"
            or self.interval != "1m"
            or self.kind not in PAGE_SIZE
        ):
            raise ValueError("Only authorized CORE5 OKX perpetual minute trade/mark candles")
        if (
            type(self.start_ms) is not int
            or type(self.end_ms) is not int
            or self.start_ms % MINUTE
            or self.end_ms % MINUTE
            or not VALIDATION_START - MINUTE <= self.start_ms < self.end_ms <= END
            or self.count > 1440
        ):
            raise ValueError("One authorized UTC date or immediately preceding start witness")
        if self.start_ms < VALIDATION_START and (self.kind != "mark" or self.count != 1):
            raise ValueError("Only the preceding minute mark witness is authorized before start")
        if self.retention_start_ms is not None or self.retention_evidence is not None:
            raise ValueError("Actual coverage is required, never a retention assumption")


@dataclass
class BulkBudget(Budget):
    max_requests: int = 14_000
    max_bytes: int = 160_000_000
    min_interval_seconds: float = 0.25

    def __post_init__(self):
        if (
            not 1 <= self.max_requests <= 14_000
            or not 0 < self.max_bytes <= 160_000_000
            or not 0 < self.max_response_bytes <= 1_000_000
            or self.max_attempts != 2
            or not math.isfinite(self.min_interval_seconds)
            or self.min_interval_seconds < 0.25
            or not 0 <= self.requests_used <= self.max_requests
            or not 0 <= self.bytes_used <= self.max_bytes
        ):
            raise ValueError("Bulk intake exceeds explicit requests/bytes/shared cadence bounds")


def job_for(asset, kind, start, end):
    return MinuteJob(
        "okx", asset + "USDT", asset + "-USDT-SWAP", "perpetual", kind, "1m", start, end
    )


def request_for(job, start, end):
    endpoint = (
        "/api/v5/market/history-candles"
        if job.kind == "trade"
        else "/api/v5/market/history-mark-price-candles"
    )
    return endpoint, dict(
        instId=job.instrument_id,
        bar="1m",
        after=end,
        before=start - 1,
        limit=min(PAGE_SIZE[job.kind], (end - start) // MINUTE),
    )


def gzip_jsonl(path, values):
    raw = "".join(json.dumps(v, sort_keys=True, allow_nan=False) + "\n" for v in values).encode()
    temporary = path.with_suffix(path.suffix + ".part")
    temporary.write_bytes(gzip.compress(raw, mtime=0))
    temporary.replace(path)


def read_gzip(path):
    return [json.loads(line) for line in gzip.decompress(path.read_bytes()).splitlines()]


def enhanced_rows(job, raw, identity, record, start, end):
    rows = normalize(job, raw, identity, record["received_ms"], record["raw_sha256"], start, end)
    originals = {int(r[0]): r for r in _payload(raw, "okx")["data"]}
    for row in rows:
        original = originals[row["open_ms"]]
        row.update(
            source_confirm=original[-1],
            completed=original[-1] == "1",
            vol=original[5] if job.kind == "trade" else None,
            volCcy=original[6] if job.kind == "trade" else None,
            volCcyQuote=original[7] if job.kind == "trade" else None,
            quote_turnover_USDT=original[7] if job.kind == "trade" else None,
            contract_value=identity["contract_value"],
            contract_multiplier=identity["contract_multiplier"],
            underlying_asset=identity["underlying_asset"],
            price_unit="USDT_PER_UNDERLYING_COIN",
        )
        if job.kind == "mark":
            row["volume_units"] = None
    return rows


def verify_shard(artifacts, manifest):
    """Independent raw/normalized oracle plus exact UTC grid; no market requests."""
    responses = artifacts / manifest["responses_file"]
    if sha256(responses) != manifest["responses_sha256"]:
        raise ValueError("Compressed checkpoint checksum mismatch")
    rows, packed = [], read_gzip(responses)
    for kind, name in manifest["bars_files"].items():
        if sha256(artifacts / name) != manifest["bars_sha256"][kind]:
            raise ValueError("Compressed normalized checkpoint checksum mismatch")
        rows.extend(read_gzip(artifacts / name))
    selected = {kind: [r for r in rows if r["kind"] == kind] for kind in ("trade", "mark")}
    for kind, info in manifest["coverage"].items():
        stamps = [r["open_ms"] for r in selected[kind]]
        expected = list(range(manifest["start_ms"], manifest["end_ms_exclusive"], MINUTE))
        if stamps != expected or info["status"] != "COMPLETE":
            raise ValueError("Complete ordered UTC minute grid required")
    lookup = {(r["kind"], r["open_ms"]): r for r in rows}
    if len(lookup) != len(rows):
        raise ValueError("Duplicate minute observation")
    verified = set()
    for item in packed:
        request, body = item["request"], item["body_utf8"].encode()
        if hashlib.sha256(body).hexdigest() != request["raw_sha256"]:
            raise ValueError("Packed original response checksum mismatch")
        if request["status"] != "OK" or request["http_status"] != 200:
            raise ValueError("Only successful market responses can certify a complete shard")
        if request["params"]["instId"] != manifest["instrument_id"]:
            raise ValueError("Raw request instrument differs from shard identity")
        kind = "mark" if "history-mark-price" in request["url"] else "trade"
        for original in json.loads(body)["data"]:
            key = (kind, int(original[0]))
            row = lookup[key]
            if (
                [row[name] for name in ("open", "high", "low", "close")] != original[1:5]
                or row["source_confirm"] != original[-1]
                or original[-1] != "1"
                or row["close_ms_exclusive"] != row["open_ms"] + MINUTE
                or row["raw_sha256"] != request["raw_sha256"]
                or row["received_ms"] != request["received_ms"]
                or row["available_ms"] != request["received_ms"]
                or row["historical_available_ms"] is not None
                or row["publication_time_certified"]
                or not row["completed"]
            ):
                raise ValueError("Original OHLC/clock/completion provenance mismatch")
            if any(
                row[key] != manifest["identity"][key]
                for key in (
                    "provider",
                    "instrument_id",
                    "market",
                    "contract_value",
                    "contract_multiplier",
                    "underlying_asset",
                )
            ) or row["identity_sha256"] != fingerprint(manifest["identity"]):
                raise ValueError("Native contract identity binding differs")
            if (
                kind == "trade"
                and [row[n] for n in ("vol", "volCcy", "volCcyQuote")] != original[5:8]
            ):
                raise ValueError("Contract/base/quote volume identity mismatch")
            if kind == "trade" and row["quote_turnover_USDT"] != original[7]:
                raise ValueError("Capacity turnover must be original quote-USDT volume")
            verified.add(key)
    if verified != set(lookup):
        raise ValueError("Every normalized minute needs an exact raw response witness")
    return rows


def funding_clock_witnesses(artifacts, parent, manifest):
    """Bind every funding/start clock to a completed immediately preceding mark."""
    instrument = manifest["instrument_id"]
    start, end = manifest["start_ms"], manifest["end_ms_exclusive"]
    funding_path = parent / instrument / "funding.jsonl"
    events = [json.loads(line) for line in funding_path.read_text().splitlines()]
    events = [event for event in events if start <= event["funding_time_ms"] < end]
    current_path = manifest["bars_files"]["mark"]
    current = {r["open_ms"]: r for r in read_gzip(artifacts / current_path)}
    previous_date = datetime.fromtimestamp((start - MINUTE) / 1000, UTC).strftime("%Y-%m-%d")
    previous_path = (
        instrument
        + "/"
        + ("start-witness" if start == VALIDATION_START else previous_date)
        + ".mark.jsonl.gz"
    )
    clocks = sorted({event["funding_time_ms"] for event in events} | {start})
    witnesses = []
    for clock in clocks:
        stamp = clock - MINUTE
        name = previous_path if stamp < start else current_path
        marks = {r["open_ms"]: r for r in read_gzip(artifacts / name)} if stamp < start else current
        row = marks.get(stamp)
        if row is None or row["close_ms_exclusive"] != clock or not row["completed"]:
            raise ValueError("Funding/start clock lacks its immediately preceding mark")
        if row["identity_sha256"] != fingerprint(manifest["identity"]):
            raise ValueError("Funding witness native identity changed")
        matching = [event for event in events if event["funding_time_ms"] == clock]
        if len(matching) > 1 or any(
            event["instrument_id"] != instrument
            or event["identity_sha256"] != row["identity_sha256"]
            or not event["realizedRate"]
            for event in matching
        ):
            raise ValueError("Funding identity, duplication or actual rate mismatch")
        witnesses.append(
            dict(
                clock_ms=clock,
                basis="FUNDING" if matching else "DATE_START",
                mark_bars_file=name,
                mark_bars_sha256=sha256(artifacts / name),
                mark_open_ms=stamp,
                mark_close_ms_exclusive=clock,
                mark_raw_sha256=row["raw_sha256"],
                mark_received_ms=row["received_ms"],
                publication_time_certified=False,
                funding_record_sha256=fingerprint(matching[0]) if matching else None,
                funding_raw_sha256=matching[0]["raw_sha256"] if matching else None,
            )
        )
    return dict(
        funding_input_file="../" + instrument + "/funding.jsonl",
        funding_input_sha256=sha256(funding_path),
        actual_rate_field="realizedRate",
        predicted_rate_field="fundingRate",
        verified_clocks=witnesses,
    )


def write_schema(artifacts):
    schema = dict(
        version=VERSION,
        index="COVERAGE.json",
        path_basis="RELATIVE_TO_INDEX_DIRECTORY",
        compression="gzip",
        normalized_encoding="UTF8_JSONL",
        normalized_order="ASCENDING_OPEN_MS_PER_INSTRUMENT_PER_KIND",
        shards="index.shards ordered by UTC date then CORE5; use status COMPLETE only",
        normalized_paths="shards[].bars_files.trade and .mark; separate kinds, no overlaps",
        timestamps=dict(
            open_ms="UTC minute open",
            close_ms_exclusive="open_ms + 60000",
            received_ms="Original retrieval completion",
            available_ms="received_ms only; historical availability unknown",
            historical_available_ms=None,
            publication_time_certified=False,
        ),
        prices="Original decimal strings; USDT per underlying coin; never rescaled",
        trade_volume=dict(
            vol="Original contracts",
            volCcy="Original base-coin units",
            volCcyQuote="Original quote-USDT turnover",
            quote_turnover_USDT="Exact volCcyQuote alias; capacity denominator",
        ),
        mark_volume="All volume fields null; mark is not a traded price",
        identity="Full native identity in each manifest; fingerprint(identity) in each row",
        contract_metadata="Current metadata retained; historical contract rules uncertified",
        raw="responses.jsonl.gz contains exact original UTF8 bodies plus original receipts",
        checksum="SHA256 of original UTF8 bytes and compressed artifacts; local, not attested",
        clock_witnesses="manifest.funding_clock_witnesses.verified_clocks; prior completed mark",
        funding="Existing ../<instrument>/funding.jsonl; realizedRate separate from fundingRate",
        dataset_role="OKX_ONLY_PUBLIC_OFFLINE_RESEARCH",
        frozen_selector_certified=False,
        training=False,
        wallet_backtest=False,
    )
    dump(schema, artifacts / "SCHEMA.json")
    (artifacts / "README.md").write_text(
        "# OKX CORE5 minute intake\n\n"
        "Read COVERAGE.json and SCHEMA.json. Paths are relative to this directory. "
        "Each COMPLETE instrument/date manifest binds separate ordered trade and mark "
        "JSONL gzip shards, exact original responses and local SHA256 receipts. "
        "Reject gaps, overlaps and other statuses. Funding remains in the parent directory; "
        "each date manifest records completed prior-minute marks for start/funding clocks.\n\n"
        "Scope: BTC, ETH, SOL, XRP and DOGE USDT perpetual swaps, 2026-07-15 inclusive "
        "through 2026-10-09 exclusive, plus five preceding start marks. "
        "Original price/volume strings remain unchanged. Contract metadata is current. "
        "Historical publication, contract rules and account settlement are uncertified. "
        "This separate OKX dataset cannot certify the frozen Binance selector. "
        "No training or wallet backtest is performed.\n\n"
        "Fixed official source, serial calls, shared start spacing at least 250 ms; "
        "20/2s documented IP limits per endpoint; trade max 300, mark max 100. "
        "Stop on denial/rate limit or incomplete page; at most 14,000 new requests, "
        "160 MB response bodies and four hours. Verified prior probes are reused.\n"
    )


def _read_page(job, start, end, work, receipt, budget, session, index, index_path):
    if time.time_ns() // 1_000_000 - index["started_ms"] >= 14_380_000:
        raise Failure("WALL_BUDGET_EXHAUSTED", "Stop before the four-hour acquisition limit")
    try:
        return _read(job, *request_for(job, start, end), work, receipt, budget, session)
    finally:
        index.update(
            new_requests=budget.requests_used,
            new_response_body_bytes=budget.bytes_used,
            elapsed_seconds=(time.time_ns() // 1_000_000 - index["started_ms"]) / 1000,
        )
        dump(index, index_path)


def seed_probes(asset, day_start, work, receipt, parent):
    if day_start != VALIDATION_START or receipt["requests"]:
        return
    directory = parent / (asset + "-USDT-SWAP")
    prior_path = directory / "manifest.json"
    prior = json.loads(prior_path.read_text())
    for record in prior["requests"]:
        if record["params"].get("bar") != "1m":
            continue
        if sha256(directory / record["raw_file"]) != record["raw_sha256"]:
            raise ValueError("Verified probe raw checksum changed")
        shutil.copyfile(directory / record["raw_file"], work / record["raw_file"])
        reused = deepcopy(record)
        reused.update(
            reused_source_commit=PARENT_COMMIT,
            reused_source_receipt_sha256=sha256(prior_path),
            reused_source_manifest="research/okx-forward-coverage-20261009/"
            + asset
            + "-USDT-SWAP/manifest.json",
        )
        receipt["requests"].append(reused)


def collect_shard(asset, start, end, cache, parent, binding, budget, session, index):
    date = datetime.fromtimestamp(start / 1000, UTC).strftime("%Y-%m-%d")
    witness = start == VALIDATION_START - MINUTE
    stem = "start-witness" if witness else date
    instrument = asset + "-USDT-SWAP"
    work = cache / "work" / instrument / stem
    artifacts = cache / "artifacts"
    out = artifacts / instrument
    work.mkdir(parents=True, exist_ok=True)
    out.mkdir(parents=True, exist_ok=True)
    state_path = work / "manifest.json"
    public_manifest = out / (stem + ".manifest.json")
    if public_manifest.exists():
        saved = json.loads(public_manifest.read_text())
        if saved["binding"] != binding:
            raise ValueError("Saved completed shard source binding changed")
        if saved["status"] == "COMPLETE":
            verify_shard(artifacts, saved)
            return saved
    receipt = (
        json.loads(state_path.read_text())
        if state_path.exists()
        else dict(binding=binding, requests=[], status="PENDING")
    )
    if receipt["binding"] != binding:
        raise ValueError("Saved page source binding changed")
    for record in receipt["requests"]:
        if "raw_file" in record and sha256(work / record["raw_file"]) != record["raw_sha256"]:
            raise ValueError("Retained page checksum mismatch")
    if not witness:
        seed_probes(asset, start, work, receipt, parent)
    input_path = parent / instrument / "manifest.json"
    prior = json.loads(input_path.read_text())
    identity = prior["identity"]
    if (
        identity["provider"] != "okx"
        or identity["instrument_id"] != instrument
        or identity["market"] != "perpetual"
        or identity["quote_currency"] != "USDT"
    ):
        raise ValueError("Exact verified native instrument metadata required")
    rows, page_failure = [], None
    kinds = ("mark",) if witness else ("trade", "mark")
    try:
        for kind in kinds:
            job = job_for(asset, kind, start, end)
            cursor = start
            while cursor < end:
                # Reuse the exact 100-minute probe, then use the documented maxima.
                size = 100 if start == VALIDATION_START and cursor == start else PAGE_SIZE[kind]
                stop = min(cursor + size * MINUTE, end)
                raw, record = _read_page(
                    job,
                    cursor,
                    stop,
                    work,
                    receipt,
                    budget,
                    session,
                    index,
                    artifacts / "COVERAGE.json",
                )
                page = enhanced_rows(job, raw, identity, record, cursor, stop)
                rows.extend(page)
                if len(page) != (stop - cursor) // MINUTE:
                    raise Failure("INCOMPLETE_COVERAGE", "Incomplete historical page; stop intake")
                cursor = stop
    except Failure as exc:
        page_failure = dict(status=exc.status, detail=str(exc))
        receipt.update(status=exc.status, last_failure=page_failure)
        dump(receipt, state_path)
        if exc.status in ("PERMISSION_DENIED", "RATE_LIMITED"):
            dump(page_failure, cache / "access-stop.json")
    rows.sort(key=lambda row: (row["kind"], row["open_ms"]))
    bars_files = {kind: instrument + "/" + stem + "." + kind + ".jsonl.gz" for kind in kinds}
    raw_file = instrument + "/" + stem + ".responses.jsonl.gz"
    for kind, name in bars_files.items():
        gzip_jsonl(artifacts / name, [row for row in rows if row["kind"] == kind])
    packed = []
    for record in receipt["requests"]:
        if record["status"] == "OK":
            public_record = {k: v for k, v in record.items() if k != "raw_file"}
            packed.append(
                dict(
                    request=public_record,
                    body_utf8=(work / record["raw_file"]).read_bytes().decode(),
                )
            )
    gzip_jsonl(artifacts / raw_file, packed)
    cov = {
        kind: coverage(job_for(asset, kind, start, end), [r for r in rows if r["kind"] == kind])
        for kind in kinds
    }
    manifest = dict(
        binding=binding,
        instrument_id=instrument,
        date=stem,
        status="COMPLETE" if page_failure is None else page_failure["status"],
        start_ms=start,
        end_ms_exclusive=end,
        coverage=cov,
        bars_files=bars_files,
        bars_sha256={kind: sha256(artifacts / name) for kind, name in bars_files.items()},
        responses_file=raw_file,
        responses_sha256=sha256(artifacts / raw_file),
        identity=identity,
        input_manifest=dict(
            repository_commit=PARENT_COMMIT,
            repository_path="research/okx-forward-coverage-20261009/"
            + instrument
            + "/manifest.json",
            sha256=sha256(input_path),
        ),
        new_requests=sum("reused_source_commit" not in r for r in receipt["requests"]),
        reused_probe_pages=sum("reused_source_commit" in r for r in receipt["requests"]),
        raw_response_count=len(packed),
        failure=page_failure,
    )
    if page_failure is None:
        verify_shard(artifacts, manifest)
    dump(manifest, public_manifest)
    return manifest


def publish(cache, repo):
    repo = Path(repo).resolve()
    if (
        subprocess.check_output(["git", "branch", "--show-current"], cwd=repo, text=True).strip()
        != BRANCH
    ):
        raise Failure("PUBLICATION_BLOCKED", "Expected authorized research branch")
    target = repo / PUBLIC_PREFIX
    target.mkdir(parents=True, exist_ok=True)
    for source in (cache / "artifacts").rglob("*"):
        if source.is_file():
            relative = source.relative_to(cache / "artifacts")
            destination = target / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            if not destination.exists() or sha256(destination) != sha256(source):
                shutil.copyfile(source, destination)
    for command in (
        ["git", "add", "--", str(PUBLIC_PREFIX)],
        ["git", "diff", "--cached", "--check"],
    ):
        subprocess.run(command, cwd=repo, check=True, capture_output=True)
    staged = subprocess.check_output(
        ["git", "diff", "--cached", "--name-only"], cwd=repo, text=True
    ).splitlines()
    if any(not p.startswith(str(PUBLIC_PREFIX) + "/") for p in staged):
        raise Failure("PUBLICATION_BLOCKED", "Unrelated staged files; preserve them")
    if staged:
        subprocess.run(
            ["git", "commit", "-q", "-m", "Checkpoint verified OKX minute shards"],
            cwd=repo,
            check=True,
            capture_output=True,
        )
        result = subprocess.run(
            ["git", "push", "origin", "HEAD:refs/heads/" + BRANCH],
            cwd=repo,
            capture_output=True,
            text=True,
        )
        if result.returncode:
            raise Failure("PUBLICATION_DENIED", result.stderr[-1000:])
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repo, text=True).strip()
    remote = subprocess.check_output(
        ["git", "ls-remote", "--heads", "origin", "refs/heads/" + BRANCH], cwd=repo, text=True
    ).split()[0]
    if remote != head:
        raise Failure("PUBLICATION_UNCONFIRMED", "Remote research branch SHA differs")
    return head


def run(cache, parent, source_commit, publish_repo=None, session=None):
    cache, parent = Path(cache).resolve(), Path(parent).resolve()
    checkout = Path(__file__).resolve().parents[3]
    if cache.is_relative_to(checkout):
        raise ValueError("Bulk cache must be outside the source checkout")
    cache.mkdir(parents=True, exist_ok=True)
    if shutil.disk_usage(cache).free < 15 * 2**30:
        raise Failure("DISK_RESERVE", "Preserve the existing 15 GiB free-space reserve")
    binding = dict(
        version=VERSION,
        source_commit=source_commit,
        source_sha256=sha256(Path(__file__)),
        adapter_source_sha256=sha256(Path(__file__).with_name("public_supplement.py")),
        input_commit=PARENT_COMMIT,
        provider="okx",
        assets=list(ASSETS),
        market="perpetual",
        start_ms=VALIDATION_START,
        end_ms_exclusive=END,
        kinds=["trade", "mark"],
        page_sizes=PAGE_SIZE,
        documented_ip_limits={"trade": "20/2s", "mark": "20/2s"},
        official_docs=DOCS,
        shared_min_spacing_ms=250,
        max_requests=14000,
        max_response_body_bytes=160000000,
        max_wall_seconds=14400,
        dataset_role="OKX_ONLY_PUBLIC_OFFLINE_RESEARCH",
        historical_publication_certified=False,
        historical_instrument_rules_certified=False,
        account_settlement_verified=False,
        frozen_selector_certified=False,
        training=False,
        wallet_backtest=False,
    )
    artifacts = cache / "artifacts"
    artifacts.mkdir(exist_ok=True)
    index_path = artifacts / "COVERAGE.json"
    index = (
        json.loads(index_path.read_text())
        if index_path.exists()
        else dict(
            binding=binding,
            started_ms=time.time_ns() // 1_000_000,
            status="RUNNING",
            shards=[],
            witnesses=[],
            expected_minute_rows=1238400,
            new_requests=0,
            new_response_body_bytes=0,
        )
    )
    if index["binding"] != binding:
        raise ValueError("Saved bulk source binding changed")
    write_schema(artifacts)
    records = []
    for receipt in (cache / "work").glob("*/*/manifest.json"):
        records.extend(json.loads(receipt.read_text())["requests"])
    own = [r for r in records if "reused_source_commit" not in r]
    budget = BulkBudget(
        requests_used=len(own), bytes_used=sum(r.get("body_bytes", 1_000_000) for r in own)
    )
    if (cache / "access-stop.json").exists() or (parent / "access-stop.json").exists():
        budget.denied_providers.add("okx")
    session_owned = session is None
    session = session or requests.Session()
    try:
        for start in range(VALIDATION_START, END, DAY_MS):
            for asset in ASSETS:
                if start == VALIDATION_START:
                    witness = collect_shard(
                        asset, start - MINUTE, start, cache, parent, binding, budget, session, index
                    )
                    if witness["status"] != "COMPLETE":
                        raise Failure(witness["status"], str(witness["failure"]))
                    index["witnesses"] = [
                        w
                        for w in index["witnesses"]
                        if w["instrument_id"] != witness["instrument_id"]
                    ] + [
                        dict(
                            instrument_id=witness["instrument_id"],
                            manifest=witness["instrument_id"] + "/start-witness.manifest.json",
                            bars_file=witness["bars_files"]["mark"],
                            bars_sha256=witness["bars_sha256"]["mark"],
                            open_ms=start - MINUTE,
                            close_ms_exclusive=start,
                        )
                    ]
                shard = collect_shard(
                    asset, start, start + DAY_MS, cache, parent, binding, budget, session, index
                )
                if shard["status"] == "COMPLETE":
                    shard["funding_clock_witnesses"] = funding_clock_witnesses(
                        artifacts, parent, shard
                    )
                    dump(
                        shard,
                        artifacts
                        / (asset + "-USDT-SWAP")
                        / (shard["date"] + ".manifest.json"),
                    )
                key = (shard["instrument_id"], shard["date"])
                index["shards"] = [
                    s for s in index["shards"] if (s["instrument_id"], s["date"]) != key
                ]
                index["shards"].append(
                    dict(
                        instrument_id=key[0],
                        date=key[1],
                        status=shard["status"],
                        start_ms=start,
                        end_ms_exclusive=start + DAY_MS,
                        manifest=key[0] + "/" + key[1] + ".manifest.json",
                        bars_files=shard["bars_files"],
                        bars_sha256=shard["bars_sha256"],
                        responses_file=shard["responses_file"],
                        responses_sha256=shard["responses_sha256"],
                        coverage=shard["coverage"],
                        identity_sha256=fingerprint(shard["identity"]),
                        contract_value=shard["identity"]["contract_value"],
                        contract_multiplier=shard["identity"]["contract_multiplier"],
                        manifest_sha256=sha256(artifacts / key[0] / (key[1] + ".manifest.json")),
                    )
                )
                index["verified_minute_rows"] = sum(
                    s["coverage"][k]["observed_bars"]
                    for s in index["shards"]
                    if s["status"] == "COMPLETE"
                    for k in ("trade", "mark")
                )
                dump(index, index_path)
                if shard["status"] != "COMPLETE":
                    raise Failure(shard["status"], str(shard["failure"]))
                count = len(index["shards"])
                if count == 1:
                    elapsed = (time.time_ns() // 1_000_000 - index["started_ms"]) / 1000
                    starts = sorted(
                        r["requested_ms"]
                        for path in (cache / "work").glob("*/*/manifest.json")
                        for r in json.loads(path.read_text())["requests"]
                        if "reused_source_commit" not in r
                    )
                    gaps = [b - a for a, b in zip(starts, starts[1:], strict=False)]
                    index["first_checkpoint_estimate"] = dict(
                        measured_new_requests=budget.requests_used,
                        measured_verified_minute_rows=index["verified_minute_rows"],
                        measured_elapsed_seconds=elapsed,
                        measured_effective_requests_per_second=budget.requests_used / elapsed,
                        measured_min_request_start_spacing_ms=min(gaps) if gaps else None,
                        expected_new_requests_without_retries=8600,
                        projected_total_seconds=elapsed * 8600 / budget.requests_used,
                        projected_total_body_bytes=budget.bytes_used * 8600 / budget.requests_used,
                        estimate_basis="FIRST_INSTRUMENT_DATE_INCLUDING_WITNESS_EXCLUDING_PUSH",
                    )
                    dump(index, index_path)
                print(
                    json.dumps(
                        dict(
                            stage="VERIFIED_SHARD",
                            instrument=asset,
                            date=key[1],
                            completed_shards=count,
                            total_shards=430,
                            requests=budget.requests_used,
                            body_bytes=budget.bytes_used,
                            elapsed_seconds=index.get("elapsed_seconds"),
                        )
                    ),
                    flush=True,
                )
                if count == 1 and publish_repo:
                    head = publish(cache, publish_repo)
                    print(
                        json.dumps(
                            dict(
                                stage="FIRST_CHECKPOINT_PUBLISHED",
                                sha=head,
                                index=str(PUBLIC_PREFIX / "COVERAGE.json"),
                                schema=str(PUBLIC_PREFIX / "SCHEMA.json"),
                                measured=index["first_checkpoint_estimate"],
                            )
                        ),
                        flush=True,
                    )
            if publish_repo:
                head = publish(cache, publish_repo)
                print(
                    json.dumps(dict(stage="CORE5_DATE_PUBLISHED", date=key[1], sha=head)),
                    flush=True,
                )
        index["status"] = "COMPLETE"
    except Failure as exc:
        index.update(status=exc.status, failure=dict(status=exc.status, detail=str(exc)))
    finally:
        if session_owned:
            session.close()
        index.update(
            new_requests=budget.requests_used,
            new_response_body_bytes=budget.bytes_used,
            elapsed_seconds=(time.time_ns() // 1_000_000 - index["started_ms"]) / 1000,
            verified_minute_rows=sum(
                s["coverage"][k]["observed_bars"]
                for s in index["shards"]
                if s["status"] == "COMPLETE"
                for k in ("trade", "mark")
            ),
            verified_start_witnesses=len(index["witnesses"]),
        )
        dump(index, index_path)
    if publish_repo and index["status"] == "COMPLETE":
        index["published_sha"] = publish(cache, publish_repo)
    return index


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache", type=Path, required=True)
    parser.add_argument("--parent", type=Path, required=True)
    parser.add_argument("--source-commit", required=True)
    parser.add_argument("--publish-repo", type=Path)
    args = parser.parse_args()
    result = run(args.cache, args.parent, args.source_commit, args.publish_repo)
    print(
        json.dumps(
            dict(
                status=result["status"],
                requests=result["new_requests"],
                body_bytes=result["new_response_body_bytes"],
                elapsed_seconds=result["elapsed_seconds"],
            )
        )
    )
    return 0 if result["status"] == "COMPLETE" else 1


if __name__ == "__main__":
    raise SystemExit(main())
