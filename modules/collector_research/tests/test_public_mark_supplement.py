"""Offline mark-stage boundaries; no actual provider access."""
import gzip
import json
from dataclasses import replace

import pytest
from pipeline import public_mark_supplement as marks
from pipeline import public_supplement as daily
from test_public_supplement import Response, Session, candles, metadata


@pytest.fixture(autouse=True)
def no_wait(monkeypatch):
    monkeypatch.setattr(daily.time, 'sleep', lambda seconds: None)


def test_empty_historical_pilot_stops_without_claiming_retention(tmp_path):
    j = daily.mark_job('okx')
    session = Session(Response(metadata(j)), Response(candles(j, [])))
    result = marks.collect_doge_marks(tmp_path, session)
    assert len(session.calls) == 2 and result['status'] == 'INCOMPLETE_COVERAGE'
    assert result['coverage']['missing_bars'] == 44640
    manifest = json.loads(open(result['manifest']).read())
    assert manifest['requests'][-1]['coverage_note'] == 'HISTORY_UNAVAILABLE_UNCLASSIFIED'
    assert gzip.decompress(open(result['normalized_file'], 'rb').read()) == b''
    assert marks.collect_doge_marks(tmp_path, Session())['status'] == 'INCOMPLETE_COVERAGE'


def test_pilot_complete_then_gap_retains_mark_kind_and_clocks(tmp_path):
    j = daily.mark_job('okx')
    pilot = replace(j, end_ms=j.start_ms + 100 * j.step)
    session = Session(Response(metadata(j)), Response(candles(pilot)), Response(candles(j, [])))
    result = marks.collect_doge_marks(tmp_path, session)
    assert result['coverage']['observed_bars'] == 100 and len(session.calls) == 3
    rows = [json.loads(line) for line in gzip.decompress(
        open(result['normalized_file'], 'rb').read()).splitlines()]
    assert all(row['kind'] == 'mark' and row['market'] == 'perpetual' for row in rows)
    assert rows[0]['native_volume_fields'] is None and rows[0]['volume_units'] is None
    assert rows[0]['historical_available_ms'] is None
    assert rows[-1]['close_ms_exclusive'] == pilot.end_ms


def test_mark_budget_scope_and_denial_stop(tmp_path):
    with pytest.raises(ValueError):
        marks.MarkBudget(max_requests=461)
    with pytest.raises(ValueError):
        marks.MarkBudget(min_interval_seconds=0.5)
    session = Session(Response(b'denied', 403))
    result = marks.collect_doge_marks(tmp_path, session)
    assert result['status'] == 'PERMISSION_DENIED' and len(session.calls) == 1
    assert marks.collect_doge_marks(tmp_path, Session())['status'] == 'PERMISSION_DENIED'


def test_full_44640_calendar_final_short_page_and_zero_request_resume(tmp_path):
    j = daily.mark_job('okx')
    pages = [replace(j, start_ms=start, end_ms=min(start + 100 * j.step, j.end_ms))
             for start in range(j.start_ms, j.end_ms, 100 * j.step)]
    session = Session(Response(metadata(j)), *(Response(candles(page)) for page in pages))
    result = marks.collect_doge_marks(tmp_path, session)
    assert result['status'] == 'COMPLETE' and result['coverage']['observed_bars'] == 44640
    assert len(session.calls) == 448 and session.calls[-1][1]['params']['limit'] == 40
    rows = [json.loads(line) for line in gzip.decompress(
        open(result['normalized_file'], 'rb').read()).splitlines()]
    assert [row['open_ms'] for row in rows] == list(range(1764547200000, 1767225600000, 60000))
    assert rows[0]['kind'] == 'mark' and rows[-1]['close_ms_exclusive'] == 1767225600000
    resumed = marks.collect_doge_marks(tmp_path, Session())
    assert resumed['status'] == 'COMPLETE' and resumed['requests'] == 448
