"""Bounded synthetic UTC date checkpoints; never a live source qualification."""

import hashlib
import json
import time

import pytest
from pipeline import okx_minute_intake as intake
from pipeline import public_supplement as daily
from test_public_supplement import Response


class FixtureSession:
    def __init__(self, denied=False, missing=False):
        self.calls, self.denied, self.missing = [], denied, missing

    def get(self, url, **kwargs):
        params = kwargs["params"]
        self.calls.append((url, params))
        if self.denied:
            return Response(b"denied", 429)
        start, end = int(params["before"]) + 1, int(params["after"])
        records = []
        for stamp in reversed(range(start, end, 60000)):
            if self.missing and stamp == start:
                continue
            row = [str(stamp), "2", "3", "1", "2.5"]
            if "history-mark-price" not in url:
                row += ["7", "0.07", "0.175"]
            row += ["1"]
            records.append(row)
        assert len(records) <= params["limit"]
        return Response(json.dumps(dict(code="0", data=records)).encode())


@pytest.fixture
def environment(tmp_path, monkeypatch):
    monkeypatch.setattr(daily.time, "sleep", lambda seconds: None)
    cache, parent = tmp_path / "cache", tmp_path / "parent"
    folder = parent / "BTC-USDT-SWAP"
    folder.mkdir(parents=True)
    identity = dict(
        provider="okx",
        instrument_id="BTC-USDT-SWAP",
        market="perpetual",
        quote_currency="USDT",
        underlying_asset="BTC",
        contract_value="0.01",
        contract_multiplier="1",
    )
    prior = dict(identity=identity, requests=[])
    (folder / "manifest.json").write_text(json.dumps(prior))
    (cache / "artifacts").mkdir(parents=True)
    index = dict(started_ms=time.time_ns() // 1000000)
    return cache, parent, index, identity


def test_max_pages_volume_units_exact_grid_and_zero_request_resume(environment):
    cache, parent, index, identity = environment
    session = FixtureSession()
    budget = intake.BulkBudget()
    start = intake.VALIDATION_START + 86400000
    manifest = intake.collect_shard(
        "BTC", start, start + 86400000, cache, parent, {}, budget, session, index
    )
    assert manifest["status"] == "COMPLETE" and len(session.calls) == 20
    assert [p["limit"] for url, p in session.calls if "history-mark-price" not in url] == [
        300
    ] * 4 + [240]
    rows = intake.verify_shard(cache / "artifacts", manifest)
    trade = [row for row in rows if row["kind"] == "trade"]
    assert len(trade) == 1440 and trade[0]["vol"] == "7" and trade[0]["volCcy"] == "0.07"
    assert trade[0]["quote_turnover_USDT"] == "0.175"
    assert trade[0]["source_confirm"] == "1" and trade[0]["completed"] is True
    assert trade[0]["contract_value"] == "0.01"
    resumed = intake.collect_shard(
        "BTC",
        start,
        start + 86400000,
        cache,
        parent,
        {},
        budget,
        FixtureSession(denied=True),
        index,
    )
    assert resumed["status"] == "COMPLETE" and budget.requests_used == 20


def test_probe_reuse_preserves_receipt_and_downloads_only_missing_ranges(environment):
    cache, parent, index, identity = environment
    fixture = FixtureSession()
    prior = json.loads((parent / "BTC-USDT-SWAP/manifest.json").read_text())
    for kind in ("trade", "mark"):
        job = intake.job_for(
            "BTC", kind, intake.VALIDATION_START, intake.VALIDATION_START + 6000000
        )
        endpoint, params = intake.request_for(job, job.start_ms, job.end_ms)
        raw = fixture.get(daily.BASES["okx"] + endpoint, params=params).content
        digest = hashlib.sha256(raw).hexdigest()
        name = digest + ".raw"
        (parent / "BTC-USDT-SWAP" / name).write_bytes(raw)
        prior["requests"].append(
            dict(
                status="OK",
                http_status=200,
                params=params,
                request_key=daily.fingerprint([daily.BASES["okx"] + endpoint, params]),
                url=daily.BASES["okx"] + endpoint,
                raw_file=name,
                raw_sha256=digest,
                received_ms=intake.END,
                body_bytes=len(raw),
            )
        )
    (parent / "BTC-USDT-SWAP/manifest.json").write_text(json.dumps(prior))
    session = FixtureSession()
    budget = intake.BulkBudget()
    manifest = intake.collect_shard(
        "BTC",
        intake.VALIDATION_START,
        intake.VALIDATION_START + 86400000,
        cache,
        parent,
        {},
        budget,
        session,
        index,
    )
    assert manifest["status"] == "COMPLETE" and manifest["reused_probe_pages"] == 2
    assert len(session.calls) == 19
    assert all(p["before"] >= intake.VALIDATION_START + 6000000 - 1 for url, p in session.calls)


def test_preceding_mark_witness_and_clock_intake_boundaries(environment):
    cache, parent, index, identity = environment
    session = FixtureSession()
    manifest = intake.collect_shard(
        "BTC",
        intake.VALIDATION_START - 60000,
        intake.VALIDATION_START,
        cache,
        parent,
        {},
        intake.BulkBudget(),
        session,
        index,
    )
    rows = intake.verify_shard(cache / "artifacts", manifest)
    assert len(rows) == 1 and rows[0]["close_ms_exclusive"] == intake.VALIDATION_START
    assert rows[0]["kind"] == "mark" and rows[0]["vol"] is None
    with pytest.raises(ValueError):
        intake.job_for("BTC", "trade", intake.VALIDATION_START - 60000, intake.VALIDATION_START)
    with pytest.raises(ValueError):
        intake.BulkBudget(min_interval_seconds=0.24)


@pytest.mark.parametrize(
    "denied,missing,status", [(True, False, "RATE_LIMITED"), (False, True, "INCOMPLETE_COVERAGE")]
)
def test_stop_without_filling_or_service_fallback(environment, denied, missing, status):
    cache, parent, index, identity = environment
    session = FixtureSession(denied, missing)
    start = intake.VALIDATION_START + 86400000
    manifest = intake.collect_shard(
        "BTC", start, start + 86400000, cache, parent, {}, intake.BulkBudget(), session, index
    )
    assert manifest["status"] == status and len(session.calls) == 1
    assert manifest["coverage"]["mark"]["missing_bars"] == 1440
    assert manifest["coverage"]["trade"]["missing_bars"] > 0


def test_tampered_completed_compressed_shard_refuses_before_requests(environment):
    cache, parent, index, identity = environment
    start = intake.VALIDATION_START + 86400000
    manifest = intake.collect_shard(
        "BTC",
        start,
        start + 86400000,
        cache,
        parent,
        {},
        intake.BulkBudget(),
        FixtureSession(),
        index,
    )
    (cache / "artifacts" / manifest["bars_files"]["trade"]).write_bytes(b"tampered")
    with pytest.raises(ValueError, match="checksum"):
        intake.collect_shard(
            "BTC",
            start,
            start + 86400000,
            cache,
            parent,
            {},
            intake.BulkBudget(),
            FixtureSession(),
            index,
        )


def test_funding_clock_requires_completed_preceding_mark(environment):
    cache, parent, index, identity = environment
    start = intake.VALIDATION_START
    budget, session = intake.BulkBudget(), FixtureSession()
    intake.collect_shard("BTC", start - 60000, start, cache, parent, {}, budget, session, index)
    manifest = intake.collect_shard(
        "BTC", start, start + 86400000, cache, parent, {}, budget, session, index
    )
    funding = [
        dict(
            instrument_id="BTC-USDT-SWAP",
            funding_time_ms=stamp,
            identity_sha256=daily.fingerprint(identity),
            realizedRate="0.0001",
            fundingRate="0.0002",
            raw_sha256="fixture",
        )
        for stamp in (start, start + 28800000, start + 57600000)
    ]
    (parent / "BTC-USDT-SWAP/funding.jsonl").write_text(
        "".join(json.dumps(row) + "\n" for row in funding)
    )
    clocks = intake.funding_clock_witnesses(cache / "artifacts", parent, manifest)
    assert len(clocks["verified_clocks"]) == 3
    assert clocks["verified_clocks"][0]["mark_open_ms"] == start - 60000
    assert clocks["actual_rate_field"] == "realizedRate"
    (cache / "artifacts" / "BTC-USDT-SWAP/start-witness.mark.jsonl.gz").unlink()
    with pytest.raises(FileNotFoundError):
        intake.funding_clock_witnesses(cache / "artifacts", parent, manifest)
