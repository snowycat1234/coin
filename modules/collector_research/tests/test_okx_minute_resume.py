"""Quarantine and explicitly bounded pre-start requests; synthetic fixtures only."""

import json
import time
from dataclasses import replace

import pytest
from pipeline import okx_minute_resume as resume
from pipeline import public_supplement as daily
from test_okx_minute_intake import FixtureSession


def test_authorized_two_minute_boundary_one_request_and_cached_resume(tmp_path, monkeypatch):
    monkeypatch.setattr(daily.time, "sleep", lambda seconds: None)
    cache, parent = tmp_path / "cache", tmp_path / "parent"
    (cache / "artifacts/BTC-USDT-SWAP").mkdir(parents=True)
    (parent / "BTC-USDT-SWAP").mkdir(parents=True)
    identity = dict(
        provider="okx",
        instrument_id="BTC-USDT-SWAP",
        market="perpetual",
        underlying_asset="BTC",
        quote_currency="USDT",
        contract_value="0.01",
        contract_multiplier="1",
    )
    (parent / "BTC-USDT-SWAP/manifest.json").write_text(json.dumps(dict(identity=identity)))
    index = dict(binding={}, started_ms=time.time_ns() // 1000000)
    budget, session = resume.BulkBudget(), FixtureSession()
    proof = resume.boundary("BTC", cache, parent, index, budget, session, {})
    assert proof["status"] == "COMPLETE" and budget.requests_used == len(session.calls) == 1
    rows = resume.read_gzip(cache / "artifacts" / proof["bars_file"])
    assert rows[0]["close_ms_exclusive"] < resume.VALIDATION_START
    assert rows[1]["close_ms_exclusive"] == resume.VALIDATION_START
    resume.boundary("BTC", cache, parent, index, budget, FixtureSession(denied=True), {})
    assert budget.requests_used == 1
    job = resume.BoundaryJob(
        "okx",
        "BTCUSDT",
        "BTC-USDT-SWAP",
        "perpetual",
        "mark",
        "1m",
        resume.VALIDATION_START - 120000,
        resume.VALIDATION_START,
    )
    with pytest.raises(ValueError):
        replace(job, start_ms=job.start_ms - 60000)


def test_quarantine_does_not_claim_full_window_or_hide_absent_intervals(monkeypatch):
    start = resume.VALIDATION_START
    monkeypatch.setattr(resume, "ASSETS", ("BTC",))
    monkeypatch.setattr(resume, "END", start + 86400000 * 2)
    cov = {
        kind: dict(observed_bars=0, missing_ranges_ms_exclusive=[[start, start + 86400000]])
        for kind in ("trade", "mark")
    }
    index = dict(
        shards=[
            dict(
                instrument_id="BTC-USDT-SWAP",
                start_ms=start,
                status="INCOMPLETE_COVERAGE",
                coverage=cov,
            )
        ]
    )
    resume.refresh(index)
    assert not index["full_window_ready"] and index["verified_minute_rows"] == 0
    assert len(index["missing_or_unconfirmed_intervals"]) == 4
    assert {r["reason"] for r in index["missing_or_unconfirmed_intervals"]} == {
        "NOT_REQUESTED",
        "INCOMPLETE_SOURCE_OR_QUARANTINED",
    }
