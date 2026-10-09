"""Explicit precedence using retained local evidence and synthetic missing pages."""

import json
import shutil
import time
from pathlib import Path

import pytest
from pipeline import okx_gap_resolution as gap
from pipeline import public_supplement as daily
from test_okx_minute_intake import FixtureSession


@pytest.fixture
def evidence(tmp_path, monkeypatch):
    monkeypatch.setattr(daily.time, "sleep", lambda seconds: None)
    repo = Path(__file__).resolve().parents[3]
    source = repo / "research/okx-forward-coverage-20261009/minute-intake"
    cache = tmp_path / "cache"
    target = cache / "artifacts"
    target.mkdir(parents=True)
    original_path = gap.INSTRUMENT + "/2026-08-28.manifest.json"
    original = json.loads((source / original_path).read_text())
    check = json.loads((source / "ARCHIVE_CHECK.json").read_text())
    names = [
        original_path,
        original["responses_file"],
        *original["bars_files"].values(),
        "ARCHIVE_CHECK.json",
        check["archive_file"],
        check["observation_file"],
    ]
    for name in names:
        (target / name).parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source / name, target / name)
    index = dict(
        started_ms=time.time_ns() // 1000000,
        full_window_ready=False,
        shards=[
            dict(
                instrument_id=gap.INSTRUMENT,
                start_ms=gap.START,
                end_ms_exclusive=gap.END,
                date="2026-08-28",
                status="INCOMPLETE_COVERAGE",
                manifest=original_path,
                coverage=original["coverage"],
            )
        ],
    )
    (target / "COVERAGE.json").write_text(json.dumps(index))
    return cache, original_path


def test_only_missing_ranges_and_explicit_archive_row_preserve_both_originals(evidence):
    cache, original_path = evidence
    before = gap.sha256(cache / "artifacts" / original_path)
    session = FixtureSession()
    manifest = gap.resolve(cache, "SYNTHETIC_TEST_ONLY", session)
    assert manifest["new_requests"] == len(session.calls) == 18
    assert gap.sha256(cache / "artifacts" / original_path) == before
    assert all(
        int(params["before"]) + 1 >= gap.START + 36000000
        for url, params in session.calls
        if "history-mark-price" not in url
    )
    rows = gap.verify_resolution(cache / "artifacts", manifest)
    assert len(rows) == 2880
    selected = next(
        row for row in rows if row["kind"] == "trade" and row["open_ms"] == gap.ARCHIVE_MINUTE
    )
    assert selected["source_confirm"] == "1" and selected["high"] == "106.52"
    assert manifest["archive_precedence"]["original_api_record"][-1] == "0"
    assert manifest["archive_precedence"]["original_api_record"][2] == "106.48"
    index = json.loads((cache / "artifacts/COVERAGE.json").read_text())
    assert not index["full_window_ready"]  # independent all-430 verification still required.
    assert index["resolved_strict_prior_mark"]["close_ms_exclusive"] < gap.END
    resumed = gap.resolve(cache, "SYNTHETIC_TEST_ONLY", FixtureSession(denied=True))
    assert resumed["new_requests"] == 18


def test_archive_normalized_disagreement_refuses_before_network(evidence):
    cache, original_path = evidence
    root = cache / "artifacts"
    check = json.loads((root / "ARCHIVE_CHECK.json").read_text())
    path = root / check["observation_file"]
    row = json.loads(path.read_text())
    row["high"] = "107"
    path.write_text(json.dumps(row))
    session = FixtureSession()
    with pytest.raises(ValueError, match="raw CSV"):
        gap.resolve(cache, "SYNTHETIC_TEST_ONLY", session)
    assert not session.calls


def test_permission_or_rate_limit_stops_without_source_fallback(evidence):
    cache, original_path = evidence
    session = FixtureSession(denied=True)
    with pytest.raises(daily.Failure, match="429"):
        gap.resolve(cache, "SYNTHETIC_TEST_ONLY", session)
    assert len(session.calls) == 1
    assert (cache / "access-stop.json").exists()
