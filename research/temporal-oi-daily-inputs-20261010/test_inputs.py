"""Input-clock, masking and exact-byte normalization counterexamples only."""

import csv
import io
import json
import zipfile
from datetime import datetime, timedelta
from pathlib import Path

import ingest
import inputs
import pytest
import requests


def fixture(*, missing=(), zero=(), duplicate=None, conflict=None, reverse=False):
    day, symbol = "2022-01-01", "BTCUSDT"
    rows = []
    for i in range(288):
        if i in missing:
            continue
        row = [
            (datetime.fromisoformat(day) + timedelta(minutes=5 * i)).isoformat(sep=" "),
            symbol,
            "0" if i in zero else "2",
            "40000",
            "1",
            "1",
            "1",
            "1",
        ]
        rows.append(row)
        if i == duplicate:
            rows.append(list(row))
        if i == conflict:
            other = list(row)
            other[2] = "2.0"  # Equal parsed value still differs in original bytes.
            rows.append(other)
    if reverse:
        rows.reverse()
    text = io.StringIO()
    writer = csv.writer(text)
    writer.writerow(inputs.audit.EXPECTED_FIELDS)
    writer.writerows(rows)
    body = io.BytesIO()
    with zipfile.ZipFile(body, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(f"{symbol}-metrics-{day}.csv", text.getvalue())
    return body.getvalue(), symbol, day


def test_complete_grid_and_assumed_clock():
    row = inputs.normalize(*fixture())
    assert row["complete_positive_288_grid"] and row["terminal_valid"]
    assert row["assumed_available_UTC"] == "2022-01-03T00:00:00+00:00"
    assert row["original_publication_UTC"] is None


def test_actual_time_sort_not_physical_last_row():
    row = inputs.normalize(*fixture(reverse=True))
    assert row["terminal_valid"] and row["complete_positive_288_grid"]
    assert not row["raw_strictly_ordered"]


def test_terminal_valid_independently_of_full_intraday_coverage():
    row = inputs.normalize(*fixture(missing=(0, 100), zero=(2,)))
    assert row["terminal_valid"] and not row["complete_positive_288_grid"]
    assert row["valid_5m_slots"] == 285


def test_missing_or_zero_terminal_masked():
    for options in (dict(missing=(287,)), dict(zero=(287,))):
        row = inputs.normalize(*fixture(**options))
        assert not row["terminal_valid"]
        assert row["terminal_oi_quantity"] is None


def test_only_byte_identical_duplicates_removed():
    row = inputs.normalize(*fixture(duplicate=287))
    assert row["terminal_valid"] and row["identical_duplicate_extra_rows"] == 1
    row = inputs.normalize(*fixture(conflict=287))
    assert not row["terminal_valid"] and row["conflicting_timestamp_count"] == 1


def test_nonterminal_conflict_does_not_invent_terminal_missing():
    row = inputs.normalize(*fixture(conflict=0))
    assert row["terminal_valid"] and not row["complete_positive_288_grid"]


def replace_csv(raw, symbol, day, transform):
    name = f"{symbol}-metrics-{day}.csv"
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        original = archive.read(name)
    result = io.BytesIO()
    with zipfile.ZipFile(result, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(name, transform(original))
    return result.getvalue(), symbol, day


def test_line_ending_differences_are_not_byte_identical_duplicates():
    raw, symbol, day = fixture(duplicate=287)
    changed = replace_csv(raw, symbol, day, lambda body: body[:-2] + b"\n")
    row = inputs.normalize(*changed)
    assert not row["terminal_valid"] and row["conflicting_timestamp_count"] == 1


def test_alternate_timestamp_serialization_grouped_by_actual_time():
    raw, symbol, day = fixture(duplicate=287)
    changed = replace_csv(
        raw,
        symbol,
        day,
        lambda body: (
            body.rsplit(b"2022-01-01 23:55:00", 1)[0]
            + b"2022-01-01T23:55:00"
            + body.rsplit(b"2022-01-01 23:55:00", 1)[1]
        ),
    )
    row = inputs.normalize(*changed)
    assert not row["terminal_valid"] and row["conflicting_timestamp_count"] == 1


@pytest.mark.parametrize("invalid", [b"-2", b"NaN", b"inf"])
def test_negative_nonfinite_terminal_quantity_masked(invalid):
    raw, symbol, day = fixture()
    changed = replace_csv(
        raw,
        symbol,
        day,
        lambda body: body.replace(
            b"2022-01-01 23:55:00,BTCUSDT,2,", b"2022-01-01 23:55:00,BTCUSDT," + invalid + b","
        ),
    )
    assert not inputs.normalize(*changed)["terminal_valid"]


def daily_sequence():
    source = inputs.normalize(*fixture())
    records = []
    for i in range(9):
        row = dict(source)
        row["source_day"] = str((datetime(2022, 1, 1) + timedelta(days=i)).date())
        row["terminal_oi_quantity"] = str(2 + i)
        records.append(row)
    return records


def test_change_needs_endpoints_and_all_calendar_terminals():
    records = daily_sequence()
    rows = inputs.consumer_rows(records)
    assert rows[7]["oi_quantity_relchange_7d_valid"] == 1
    assert rows[7]["oi_quantity_relchange_7d"] == 3.5
    assert rows[0]["oi_quantity_relchange_1d_valid"] == 0
    records[3]["terminal_valid"] = False
    records[3]["terminal_oi_quantity"] = None
    rows = inputs.consumer_rows(records)
    assert rows[7]["oi_quantity_relchange_1d_valid"] == 1
    assert rows[7]["oi_quantity_relchange_7d_valid"] == 0
    assert rows[7]["oi_quantity_relchange_7d"] is None
    assert rows[4]["oi_quantity_relchange_1d_valid"] == 0


def test_calendar_hole_cannot_be_replaced_by_previous_row():
    records = daily_sequence()
    del records[3]
    rows = inputs.consumer_rows(records)
    assert rows[-1]["oi_quantity_relchange_7d_valid"] == 0


def test_fixed_calendar_asset_order_and_bounds():
    plan = json.loads((Path(__file__).parent / "PLAN.json").read_text())
    rows = plan["rows"]
    assert len(rows) == 4410 and len({(r["symbol"], r["day"]) for r in rows}) == 4410
    assert len({r["day"] for r in rows}) == 882
    assert rows[0]["day"] == "2021-12-01" and rows[-1]["day"] == "2024-04-30"
    assert all("2025" not in r["official_URL"] for r in rows)
    assert sum(r["cached_verified_sample"] for r in rows) == 43


def download_fixture(tmp_path, monkeypatch, statuses):
    raw, symbol, day = fixture()
    name = f"{symbol}-metrics-{day}.zip"
    target = inputs.audit.url(symbol, day)
    side = f"{ingest.sha(raw)}  {name}\n".encode()
    plan = dict(
        max_total_new_network_body_bytes=100_000_000,
        max_ZIP_body_bytes=512_000,
        max_CHECKSUM_body_bytes=4096,
        rows=[
            dict(
                quarter="2022Q1",
                symbol=symbol,
                day=day,
                ZIP=name,
                official_URL=target,
                CHECKSUM_URL=target + ".CHECKSUM",
                reused_manifest=None,
            )
        ],
    )
    (tmp_path / "PLAN.json").write_text(json.dumps(plan))
    store = tmp_path / "store"
    calls = []

    class Response:
        def __init__(self, status, body):
            self.status_code, self.body, self.headers = status, body, {}

        def iter_content(self, _):
            yield self.body

        def close(self):
            pass

    class Session:
        headers = {}

        def get(self, url, **options):
            assert options["allow_redirects"] is False
            calls.append(url)
            status = statuses[min(len(calls) - 1, len(statuses) - 1)]
            if status == "timeout":
                raise requests.Timeout("synthetic timeout")
            return Response(status, side if url.endswith(".CHECKSUM") else raw)

        def close(self):
            pass

    monkeypatch.setattr(ingest, "HERE", tmp_path)
    monkeypatch.setattr(ingest, "STORE", store)
    monkeypatch.setattr(ingest.requests, "Session", Session)
    monkeypatch.setattr(ingest.time, "sleep", lambda _: None)
    return store, calls, name


def test_verified_cache_resume_has_zero_repeated_gets(tmp_path, monkeypatch):
    store, calls, name = download_fixture(tmp_path, monkeypatch, [200, 200])
    ingest.main("2022Q1", 500)
    assert len(calls) == 2
    ingest.main("2022Q1", 500)
    assert len(calls) == 2
    record = json.loads((store / "records" / (name.removesuffix(".zip") + ".json")).read_text())
    assert record["terminal_valid"] and record["status"] == "VERIFIED_CURRENT_ARCHIVE"


def test_404_is_explicit_missing_and_never_retried(tmp_path, monkeypatch):
    store, calls, name = download_fixture(tmp_path, monkeypatch, [404])
    ingest.main("2022Q1", 500)
    ingest.main("2022Q1", 500)
    assert len(calls) == 1
    record = json.loads((store / "records" / (name.removesuffix(".zip") + ".json")).read_text())
    assert record["status"] == "MISSING_ARCHIVE_404" and not record["terminal_valid"]


def test_access_denial_stops_stream_and_future_resume(tmp_path, monkeypatch):
    store, calls, _ = download_fixture(tmp_path, monkeypatch, [451])
    with pytest.raises(PermissionError):
        ingest.main("2022Q1", 500)
    assert (store / "NETWORK_STOP.json").exists() and len(calls) == 1
    with pytest.raises(AssertionError):
        ingest.main("2022Q1", 500)
    assert len(calls) == 1


def test_transient_retries_bounded_across_resume(tmp_path, monkeypatch):
    store, calls, name = download_fixture(tmp_path, monkeypatch, ["timeout"])
    ingest.main("2022Q1", 500)
    ingest.main("2022Q1", 500)
    assert len(calls) == 3
    record = json.loads((store / "records" / (name.removesuffix(".zip") + ".json")).read_text())
    assert record["status"] == "UNRESOLVED_TRANSIENT_GET" and not record["terminal_valid"]
