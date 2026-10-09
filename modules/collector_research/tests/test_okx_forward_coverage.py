"""Synthetic source coverage only, never a wallet or a provider availability claim."""

import json
from dataclasses import replace

import pytest
from pipeline import okx_forward_coverage as forward
from pipeline import public_supplement as daily
from test_public_supplement import Response, Session, candles, metadata


@pytest.fixture(autouse=True)
def no_wait(monkeypatch):
    monkeypatch.setattr(daily.time, "sleep", lambda seconds: None)


def funding(j, stamps, actual="-0.00012"):
    return json.dumps(
        dict(
            code="0",
            data=[
                dict(
                    instId=j.instrument_id,
                    instType="SWAP",
                    fundingTime=str(t),
                    fundingRate="0.00010",
                    realizedRate=actual,
                    formulaType="withRate",
                    method="current_period",
                )
                for t in reversed(list(stamps))
            ],
        )
    ).encode()


def fixture_responses(asset="BTC"):
    j = forward.daily_job(asset)
    pages = [
        replace(j, start_ms=s, end_ms=min(s + 100 * j.step, j.end_ms))
        for s in range(j.start_ms, j.end_ms, 100 * j.step)
    ]
    return [
        Response(metadata(j)),
        *(Response(candles(p)) for p in pages),
        Response(funding(j, range(forward.VALIDATION_START, forward.END, 28800000))),
        Response(candles(forward.sample_job(asset, "trade"))),
        Response(candles(forward.sample_job(asset, "mark"))),
    ]


def test_daily_full_grid_funding_actual_not_predicted_and_small_samples(tmp_path, monkeypatch):
    monkeypatch.setattr(forward, "ASSETS", ("BTC",))
    session = Session(*fixture_responses())
    result = forward.collect_forward(tmp_path, session=session)
    asset = result["assets"][0]
    assert asset["daily_coverage"]["observed_bars"] == 646
    assert asset["funding_coverage"]["event_count"] == 258
    assert asset["funding_coverage"]["historical_schedule_certified"] is False
    assert asset["funding_coverage"]["assumed_8h_grid_missing_event_ms"] == []
    assert all(s["coverage"]["observed_bars"] == 100 for s in asset["minute_samples"].values())
    rows = [
        json.loads(line)
        for line in (tmp_path / "BTC-USDT-SWAP/funding.jsonl").read_text().splitlines()
    ]
    assert rows[0]["realizedRate"] == "-0.00012" and rows[0]["fundingRate"] == "0.00010"
    assert rows[0]["historical_available_ms"] is None
    assert len(session.calls) == 11
    resumed = forward.collect_forward(tmp_path, session=Session())
    assert resumed["requests"] == 11
    assert resumed["bulk_minute_estimate"]["bars_per_instrument_per_kind"] == 123840


def test_funding_empty_actual_is_not_filled_and_gap_is_preserved():
    j = forward.daily_job("ETH")
    identity = daily.instrument_identity(j, metadata(j))
    record = dict(raw_sha256="a" * 64, received_ms=forward.END)
    raw = funding(j, [forward.VALIDATION_START, forward.VALIDATION_START + 57600000], actual="")
    rows = forward.funding_rows(raw, j, identity, record, forward.END)
    assert rows[0]["realizedRate"] == ""
    coverage = forward.funding_coverage(rows)
    assert coverage["missing_realized_rate_events"] == 2
    assert coverage["intervals_longer_than_8h_ms"] == [
        [forward.VALIDATION_START, forward.VALIDATION_START + 57600000]
    ]
    assert forward.VALIDATION_START + 28800000 in coverage["assumed_8h_grid_missing_event_ms"]


def test_reused_doge_metadata_preserves_origin_without_request(tmp_path):
    j = forward.daily_job("DOGE")
    source = tmp_path / "old/okx-mark/owned"
    source.mkdir(parents=True)
    raw = metadata(j)
    raw_sha = daily.hashlib.sha256(raw).hexdigest()
    (source / (raw_sha + ".raw")).write_bytes(raw)
    endpoint, params = daily.metadata_request(j)
    receipt = dict(
        binding=dict(source_sha256="original-source"),
        requests=[
            dict(
                request_key=daily.fingerprint([daily.BASES["okx"] + endpoint, params]),
                status="OK",
                raw_file=raw_sha + ".raw",
                raw_sha256=raw_sha,
            )
        ],
    )
    (source / "manifest.json").write_text(json.dumps(receipt))
    target = tmp_path / "new"
    target.mkdir()
    manifest = dict(requests=[])
    forward._reuse_metadata(j, target, manifest, tmp_path / "old")
    assert manifest["requests"][0]["reused_source_binding"]["source_sha256"] == "original-source"
    assert (target / (raw_sha + ".raw")).read_bytes() == raw


def test_denial_stops_all_instruments_and_caps_are_explicit(tmp_path):
    session = Session(Response(b"denied", 403))
    result = forward.collect_forward(tmp_path, session=session)
    assert len(session.calls) == 1 and len(result["assets"]) == 1
    assert result["assets"][0]["status"] == "PERMISSION_DENIED"
    assert forward.collect_forward(tmp_path, session=Session())["requests"] == 1
    with pytest.raises(ValueError):
        forward.CoverageBudget(max_requests=71)
    with pytest.raises(ValueError):
        replace(forward.sample_job("BTC", "mark"), end_ms=forward.END)
    with pytest.raises(ValueError):
        replace(forward.daily_job("BTC"), instrument_id="BTC-USDT")


def test_tampered_retained_forward_raw_is_not_adopted(tmp_path, monkeypatch):
    monkeypatch.setattr(forward, "ASSETS", ("BTC",))
    forward.collect_forward(tmp_path, session=Session(*fixture_responses()))
    receipt = json.loads((tmp_path / "BTC-USDT-SWAP/manifest.json").read_text())
    (tmp_path / "BTC-USDT-SWAP" / receipt["requests"][0]["raw_file"]).write_bytes(b"tampered")
    with pytest.raises(ValueError, match="checksum"):
        forward.collect_forward(tmp_path, session=Session())
