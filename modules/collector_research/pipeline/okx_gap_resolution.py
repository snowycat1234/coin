"""Explicit one-row official archive precedence and bounded missing SOL portions."""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import time
import zipfile
from copy import deepcopy
from decimal import Decimal
from pathlib import Path

import requests

from .common import DAY_MS, dump, sha256
from .okx_minute_intake import (
    MINUTE,
    BulkBudget,
    enhanced_rows,
    gzip_jsonl,
    job_for,
    read_gzip,
    request_for,
    verify_shard,
)
from .okx_minute_resume import inventory, refresh
from .public_supplement import Failure, _read, coverage, fingerprint

START = 1787875200000
END = START + DAY_MS
ARCHIVE_MINUTE = 1787905800000
INSTRUMENT = "SOL-USDT-SWAP"


def archive_row(artifacts, identity):
    check = json.loads((artifacts / "ARCHIVE_CHECK.json").read_text())
    archive_path = artifacts / check["archive_file"]
    if sha256(archive_path) != check["archive_sha256"]:
        raise ValueError("Retained official archive checksum mismatch")
    with zipfile.ZipFile(archive_path) as archive:
        raw = archive.read(check["archive_csv_member"])
    if hashlib.sha256(raw).hexdigest() != check["archive_csv_sha256"]:
        raise ValueError("Retained archive CSV checksum mismatch")
    records = list(csv.DictReader(io.StringIO(raw.decode("utf-8-sig"))))
    selected = [r for r in records if r["open_time"] == str(ARCHIVE_MINUTE)]
    if (
        len(selected) != 1
        or selected[0]["instrument_name"] != INSTRUMENT
        or selected[0]["confirm"] != "1"
    ):
        raise ValueError("Exactly one explicitly completed native archive minute required")
    original = selected[0]
    numbers = [
        Decimal(original[name])
        for name in ("open", "high", "low", "close", "vol", "vol_ccy", "vol_quote")
    ]
    if any(not n.is_finite() for n in numbers) or min(numbers[:4]) <= 0 or min(numbers[4:]) < 0:
        raise ValueError("Invalid original archive values")
    row = json.loads((artifacts / check["observation_file"]).read_text())
    if row["native_csv_record"] != original or row["identity_sha256"] != fingerprint(identity):
        raise ValueError("Archive observation/native identity differs from retained CSV")
    mapping = dict(
        open="open",
        high="high",
        low="low",
        close="close",
        vol="vol",
        volCcy="vol_ccy",
        volCcyQuote="vol_quote",
        source_confirm="confirm",
    )
    if (
        any(row[key] != original[column] for key, column in mapping.items())
        or row["open_ms"] != int(original["open_time"])
        or row["raw_sha256"] != check["archive_sha256"]
        or row["received_ms"] != check["archive_request"]["received_ms"]
    ):
        raise ValueError("Normalized archive values differ from raw CSV")
    row = deepcopy(row)
    row.update(
        native_volume_fields=[original[n] for n in ("vol", "vol_ccy", "vol_quote")],
        volume_units="contracts,base,quote",
        resolution_source="OFFICIAL_ARCHIVE_PRECEDENCE",
        original_api_observation_preserved=True,
    )
    return row, check


def verify_resolution(artifacts, manifest):
    """Raw oracle allowing one exact, documented archive selection over native confirm=0."""
    identity = manifest["identity"]
    all_rows = []
    selected = {}
    for kind, name in manifest["bars_files"].items():
        if sha256(artifacts / name) != manifest["bars_sha256"][kind]:
            raise ValueError("Resolution normalized checksum changed")
        rows = read_gzip(artifacts / name)
        if [r["open_ms"] for r in rows] != list(range(START, END, MINUTE)):
            raise ValueError("Exact ordered full-day resolution grid required")
        if any(r["kind"] != kind or r["identity_sha256"] != fingerprint(identity) for r in rows):
            raise ValueError("Resolution kind or native identity mismatch")
        selected.update({(kind, r["open_ms"]): r for r in rows})
        all_rows.extend(rows)
    archive, check = archive_row(artifacts, identity)
    chosen = selected[("trade", ARCHIVE_MINUTE)]
    for key in (
        "open",
        "high",
        "low",
        "close",
        "vol",
        "volCcy",
        "volCcyQuote",
        "raw_sha256",
        "received_ms",
    ):
        if chosen[key] != archive[key]:
            raise ValueError("Archive precedence differs from original completed archive row")
    if (
        chosen["resolution_source"] != "OFFICIAL_ARCHIVE_PRECEDENCE"
        or chosen["source_confirm"] != "1"
    ):
        raise ValueError("Archive precedence must be explicit")
    witnessed = set()
    unfinished = []
    for source in manifest["api_response_sources"]:
        if sha256(artifacts / source["path"]) != source["sha256"]:
            raise ValueError("Retained API raw-proof checksum changed")
        for item in read_gzip(artifacts / source["path"]):
            record, body = item["request"], item["body_utf8"].encode()
            if (
                hashlib.sha256(body).hexdigest() != record["raw_sha256"]
                or record["http_status"] != 200
            ):
                raise ValueError("API raw/HTTP provenance differs")
            kind = "mark" if "history-mark-price" in record["url"] else "trade"
            if record["params"]["instId"] != INSTRUMENT:
                raise ValueError("API request instrument differs")
            for original in json.loads(body)["data"]:
                key = kind, int(original[0])
                if original[-1] != "1":
                    if key != ("trade", ARCHIVE_MINUTE) or original[-1] != "0":
                        raise ValueError("No additional source substitutions authorized")
                    unfinished.append(original)
                    continue
                row = selected[key]
                if (
                    [row[n] for n in ("open", "high", "low", "close")] != original[1:5]
                    or row["raw_sha256"] != record["raw_sha256"]
                    or row["received_ms"] != record["received_ms"]
                    or row["source_confirm"] != "1"
                ):
                    raise ValueError("Completed API observation changed")
                if (
                    kind == "trade"
                    and [row[n] for n in ("vol", "volCcy", "volCcyQuote")] != original[5:8]
                ):
                    raise ValueError("Original API volume changed")
                witnessed.add(key)
    if (
        len(unfinished) != 1
        or unfinished[0] != manifest["archive_precedence"]["original_api_record"]
    ):
        raise ValueError("Immutable confirm=0 original must remain an exact raw witness")
    witnessed.add(("trade", ARCHIVE_MINUTE))
    if witnessed != set(selected):
        raise ValueError("Every selected row needs an exact source witness")
    for row in all_rows:
        if (
            row["close_ms_exclusive"] != row["open_ms"] + MINUTE
            or row["available_ms"] != row["received_ms"]
            or row["historical_available_ms"] is not None
            or row["publication_time_certified"]
            or (row["kind"] == "trade" and row["quote_turnover_USDT"] != row["volCcyQuote"])
        ):
            raise ValueError("Resolution units/clocks/availability changed")
    return all_rows


def resolve(cache, source_commit, session=None):
    cache = Path(cache)
    artifacts = cache / "artifacts"
    index = json.loads((artifacts / "COVERAGE.json").read_text())
    original_path = INSTRUMENT + "/2026-08-28.manifest.json"
    original = json.loads((artifacts / original_path).read_text())
    if original["status"] != "INCOMPLETE_COVERAGE":
        raise ValueError("Original partial API dataset must be preserved")
    identity = original["identity"]
    selected_archive, check = archive_row(artifacts, identity)
    original_packed = read_gzip(artifacts / original["responses_file"])
    unfinished = [
        r
        for p in original_packed
        for r in json.loads(p["body_utf8"])["data"]
        if r[0] == str(ARCHIVE_MINUTE)
    ]
    if len(unfinished) != 1 or unfinished[0][-1] != "0":
        raise ValueError("Expected original unconfirmed API minute is absent")
    work = cache / "work" / INSTRUMENT / "gap-resolution-2026-08-28"
    work.mkdir(parents=True, exist_ok=True)
    binding = dict(
        version="okx-sol-one-row-resolution-1",
        source_commit=source_commit,
        source_sha256=sha256(Path(__file__)),
        original_manifest=original_path,
        original_manifest_sha256=sha256(artifacts / original_path),
        max_new_requests=40,
        max_new_bytes=5000000,
        shared_min_spacing_ms=250,
    )
    state = work / "manifest.json"
    receipt = (
        json.loads(state.read_text()) if state.exists() else dict(binding=binding, requests=[])
    )
    if receipt["binding"] != binding:
        raise ValueError("Resolution source binding changed")
    for r in receipt["requests"]:
        if sha256(work / r["raw_file"]) != r["raw_sha256"]:
            raise ValueError("Saved resolution raw bytes changed")
    owned = receipt["requests"]
    budget = BulkBudget(
        max_requests=40,
        max_bytes=5000000,
        requests_used=len(owned),
        bytes_used=sum(r.get("body_bytes", 1000000) for r in owned),
    )
    other = [
        r
        for p in (cache / "work").glob("*/*/manifest.json")
        if p != state
        for r in json.loads(p.read_text())["requests"]
        if "reused_source_commit" not in r
    ]
    if (
        len(other) + 40 > 14000
        or sum(r.get("body_bytes", 1000000) for r in other) + 5000000 > 160000000
    ):
        raise Failure("BUDGET_EXHAUSTED", "Resolution cannot fit original remaining caps")
    if (cache / "access-stop.json").exists():
        raise Failure("PERMISSION_DENIED", "Persisted endpoint denial")
    rows = read_gzip(artifacts / original["bars_files"]["trade"]) + [selected_archive]
    session_owned = session is None
    session = session or requests.Session()
    try:
        for kind, start in (("trade", START + 10 * 3600000), ("mark", START)):
            job = job_for("SOL", kind, START, END)
            cursor = start
            while cursor < END:
                if time.time_ns() // 1000000 - index["started_ms"] >= 14380000:
                    raise Failure("WALL_BUDGET_EXHAUSTED", "Original four-hour cap")
                stop = min(cursor + (300 if kind == "trade" else 100) * MINUTE, END)
                raw, record = _read(
                    job, *request_for(job, cursor, stop), work, receipt, budget, session
                )
                page = enhanced_rows(job, raw, identity, record, cursor, stop)
                if len(page) != (stop - cursor) // MINUTE:
                    raise Failure(
                        "INCOMPLETE_COVERAGE", "Additional missing/unconfirmed page; no fallback"
                    )
                rows.extend(page)
                cursor = stop
    except Failure as exc:
        receipt.update(status=exc.status, detail=str(exc))
        dump(receipt, state)
        if exc.status in ("PERMISSION_DENIED", "RATE_LIMITED"):
            dump(dict(status=exc.status, detail=str(exc)), cache / "access-stop.json")
        raise
    finally:
        if session_owned:
            session.close()
    out = artifacts / "gap-resolution" / INSTRUMENT
    out.mkdir(parents=True, exist_ok=True)
    prefix = "gap-resolution/" + INSTRUMENT + "/2026-08-28"
    bars_files = {kind: prefix + "." + kind + ".jsonl.gz" for kind in ("trade", "mark")}
    for kind, name in bars_files.items():
        gzip_jsonl(
            artifacts / name,
            sorted((r for r in rows if r["kind"] == kind), key=lambda r: r["open_ms"]),
        )
    raw_file = prefix + ".new-api-responses.jsonl.gz"
    packed = [
        dict(
            request={k: v for k, v in r.items() if k != "raw_file"},
            body_utf8=(work / r["raw_file"]).read_bytes().decode(),
        )
        for r in receipt["requests"]
        if r["status"] == "OK"
    ]
    gzip_jsonl(artifacts / raw_file, packed)
    manifest = dict(
        binding=binding,
        instrument_id=INSTRUMENT,
        date="2026-08-28",
        status="COMPLETE",
        start_ms=START,
        end_ms_exclusive=END,
        identity=identity,
        bars_files=bars_files,
        bars_sha256={kind: sha256(artifacts / name) for kind, name in bars_files.items()},
        responses_file=raw_file,
        responses_sha256=sha256(artifacts / raw_file),
        api_response_sources=[
            dict(path=original["responses_file"], sha256=original["responses_sha256"]),
            dict(path=raw_file, sha256=sha256(artifacts / raw_file)),
        ],
        archive_precedence=dict(
            timestamp_ms=ARCHIVE_MINUTE,
            rule="COMPLETED_OFFICIAL_ARCHIVE_OVER_NATIVE_API_CONFIRM_0_ONLY_THIS_ROW",
            original_api_record=unfinished[0],
            original_api_manifest=original_path,
            original_api_manifest_sha256=sha256(artifacts / original_path),
            archive_file=check["archive_file"],
            archive_sha256=check["archive_sha256"],
            native_archive_record=selected_archive["native_csv_record"],
            both_originals_preserved=True,
        ),
        coverage={
            kind: coverage(job_for("SOL", kind, START, END), [r for r in rows if r["kind"] == kind])
            for kind in ("trade", "mark")
        },
        new_requests=budget.requests_used,
        new_body_bytes=budget.bytes_used,
        full_window_ready=False,
        frozen_original_api_certified=False,
        frozen_selector_certified=False,
        historical_publication_certified=False,
        historical_instrument_rules_certified=False,
        account_settlement_verified=False,
        training=False,
        wallet_backtest=False,
    )
    verify_resolution(artifacts, manifest)
    name = prefix + ".manifest.json"
    dump(manifest, artifacts / name)
    index.setdefault(
        "prior_quarantine_shard",
        next(
            s
            for s in index["shards"]
            if s["instrument_id"] == INSTRUMENT and s["start_ms"] == START
        ),
    )
    descriptor = dict(
        instrument_id=INSTRUMENT,
        date="2026-08-28",
        status="COMPLETE",
        start_ms=START,
        end_ms_exclusive=END,
        manifest=name,
        manifest_sha256=sha256(artifacts / name),
        bars_files=bars_files,
        bars_sha256=manifest["bars_sha256"],
        responses_file=raw_file,
        responses_sha256=manifest["responses_sha256"],
        coverage=manifest["coverage"],
        identity_sha256=fingerprint(identity),
        contract_value=identity["contract_value"],
        contract_multiplier=identity["contract_multiplier"],
        archive_precedence_timestamp_ms=ARCHIVE_MINUTE,
    )
    index["shards"] = [
        descriptor if (s["instrument_id"], s["start_ms"]) == (INSTRUMENT, START) else s
        for s in index["shards"]
    ]
    refresh(index)
    index["full_window_ready"] = (
        False  # only an independent all-430 verification can raise this flag.
    )
    index["status"] = "RESOLUTION_PENDING_ALL_430_VERIFICATION"
    index["resolution"] = dict(
        manifest=name,
        new_requests=budget.requests_used,
        new_body_bytes=budget.bytes_used,
        source_policy="ONE_EXPLICIT_OFFICIAL_ARCHIVE_PRECEDENCE_ROW",
        preserves_original_partial_dataset=True,
    )
    index["new_requests"] = len(other) + budget.requests_used
    index["new_response_body_bytes"] = sum(r["body_bytes"] for r in other) + budget.bytes_used
    marks = [r for r in rows if r["kind"] == "mark" and r["open_ms"] == END - 2 * MINUTE]
    if len(marks) != 1 or marks[0]["close_ms_exclusive"] >= END:
        raise ValueError("Strict August29 prior mark is absent")
    index["resolved_strict_prior_mark"] = dict(
        instrument_id=INSTRUMENT,
        funding_time_ms=END,
        bars_file=bars_files["mark"],
        open_ms=marks[0]["open_ms"],
        close_ms_exclusive=marks[0]["close_ms_exclusive"],
        raw_sha256=marks[0]["raw_sha256"],
    )
    dump(index, artifacts / "COVERAGE.json")
    inventory(artifacts)
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache", required=True, type=Path)
    parser.add_argument("--source-commit", required=True)
    args = parser.parse_args()
    result = resolve(args.cache, args.source_commit)
    print(
        json.dumps(
            dict(
                status=result["status"],
                requests=result["new_requests"],
                body_bytes=result["new_body_bytes"],
            )
        )
    )


def verify_all(cache):
    """Independently reread all 430 active days and all 1,290 strict funding clocks."""
    artifacts = Path(cache) / "artifacts"
    index = json.loads((artifacts / "COVERAGE.json").read_text())
    from .okx_minute_intake import ASSETS, VALIDATION_START
    from .okx_minute_intake import END as WINDOW_END

    expected = {
        (asset + "-USDT-SWAP", start)
        for asset in ASSETS
        for start in range(VALIDATION_START, WINDOW_END, DAY_MS)
    }
    actual = {(s["instrument_id"], s["start_ms"]) for s in index["shards"]}
    if actual != expected or len(index["shards"]) != 430:
        raise ValueError("Exactly all 430 unique asset-day identities required")
    marks = {asset + "-USDT-SWAP": {} for asset in ASSETS}
    for witness in index["strict_start_witnesses"]:
        proof = json.loads((artifacts / witness["manifest"]).read_text())
        rows = verify_shard(artifacts, proof)
        marks[witness["instrument_id"]].update(
            {r["open_ms"]: r["close_ms_exclusive"] for r in rows}
        )
    row_count = 0
    for shard in index["shards"]:
        if (
            shard["status"] != "COMPLETE"
            or sha256(artifacts / shard["manifest"]) != shard["manifest_sha256"]
        ):
            raise ValueError("Active completed-day manifest/checksum mismatch")
        manifest = json.loads((artifacts / shard["manifest"]).read_text())
        verifier = verify_resolution if "archive_precedence" in manifest else verify_shard
        rows = verifier(artifacts, manifest)
        if len(rows) != 2880:
            raise ValueError("Every day requires 1,440 trade and 1,440 mark rows")
        row_count += len(rows)
        marks[shard["instrument_id"]].update(
            {r["open_ms"]: r["close_ms_exclusive"] for r in rows if r["kind"] == "mark"}
        )
    if row_count != 1238400:
        raise ValueError("Full-window scored row count mismatch")
    funding_clocks = 0
    parent = Path(__file__).resolve().parents[3] / "research/okx-forward-coverage-20261009"
    for instrument, observations in marks.items():
        for line in (parent / instrument / "funding.jsonl").read_text().splitlines():
            event = json.loads(line)
            clock = event["funding_time_ms"]
            if observations.get(clock - 2 * MINUTE) != clock - MINUTE:
                raise ValueError("Missing strict-prior funding mark")
            funding_clocks += 1
    if funding_clocks != 1290:
        raise ValueError("Exactly 1,290 retained funding clocks required")
    audit = dict(
        version="okx-430-day-archive-precedence-audit-1",
        verifier_source_sha256=sha256(Path(__file__)),
        complete_asset_days=430,
        verified_minute_rows=row_count,
        strict_funding_clocks_verified=funding_clocks,
        initial_two_minute_witnesses_verified=5,
        archive_precedence=dict(
            timestamp_ms=ARCHIVE_MINUTE,
            provider="okx",
            kind="trade",
            original_API_confirm="0",
            selected_archive_confirm="1",
            preserves_original_API=True,
        ),
        full_window_ready=True,
        original_API_only_window_ready=False,
        historical_publication_certified=False,
        historical_instrument_rules_certified=False,
        account_settlement_verified=False,
        frozen_selector_certified=False,
        training=False,
        wallet_backtest=False,
    )
    dump(audit, artifacts / "RESOLUTION_ALL_430_AUDIT.json")
    index["full_window_ready"] = True
    index["status"] = "COMPLETE_WITH_EXPLICIT_ARCHIVE_PRECEDENCE"
    index["original_API_only_window_ready"] = False
    index["historical_quarantined_instrument_dates"] = index["quarantined_instrument_dates"]
    index["quarantined_instrument_dates"] = []
    index["readiness_policy"] = "USER_AUTHORIZED_ONE_ROW_SAME_VENUE_ARCHIVE_PRECEDENCE"
    index["all_430_audit"] = dict(
        path="RESOLUTION_ALL_430_AUDIT.json",
        sha256=sha256(artifacts / "RESOLUTION_ALL_430_AUDIT.json"),
    )
    dump(index, artifacts / "COVERAGE.json")
    inventory(artifacts)
    return audit


if __name__ == "__main__":
    main()
