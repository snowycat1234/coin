import json

import polars as pl
import pytest

from quant import data
from quant.data import MINUTE_US, aggregate_frame, month_range, parse_csv


def csv_fixture(scale=1000, minutes=60):
    start = 1_640_995_200_000_000
    lines = []
    for i in range(minutes):
        opened = (start + i * MINUTE_US) // scale
        closed = (start + (i + 1) * MINUTE_US) // scale - 1
        lines.append(f"{opened},100,102,99,101,5,{closed},500,10,2,200,0")
    return ("\n".join(lines) + "\n").encode()


@pytest.mark.parametrize("scale,unit", [(1000, "milliseconds"), (1, "microseconds")])
def test_units_and_complete_aggregation(scale, unit):
    frame, quality = parse_csv(csv_fixture(scale), "BTCUSDT")
    assert quality["timestamp_unit"] == unit
    result, excluded = aggregate_frame(frame, 60)
    assert result.height == 1 and excluded == 0
    assert result["open_us"][0] == 1_640_995_200_000_000
    assert result["available_us"][0] == result["close_us"][0]
    assert result["volume"][0] == 300


def test_incomplete_window_is_quarantined():
    frame, _ = parse_csv(csv_fixture(minutes=59), "BTCUSDT")
    result, excluded = aggregate_frame(frame, 60)
    assert result.height == 0 and excluded == 1


def test_duplicates_and_bad_timestamp_rejected():
    fixture = csv_fixture(minutes=1)
    with pytest.raises(ValueError, match="duplicates=1"):
        parse_csv(fixture + fixture, "BTCUSDT")
    with pytest.raises(ValueError, match="timestamp"):
        parse_csv(fixture.replace(b"1640995200000", b"1640995200001"), "BTCUSDT")


def test_months_include_leap_year_boundary():
    assert month_range("2023-12", "2024-02") == ["2023-12", "2024-01", "2024-02"]


def test_official_partial_close_is_audited_and_quarantined():
    fixture = csv_fixture(minutes=60)
    fixture = fixture.replace(b"1640995259999", b"1640995259000")
    frame, quality = parse_csv(fixture, "BTCUSDT")
    assert len(quality["nonstandard_closes"]) == 1
    frame = frame.with_columns(pl.lit(False).alias("valid_day"))
    result, excluded = aggregate_frame(frame, 60)
    assert result.height == 0 and excluded == 1


def test_minute_input_tampering_invalidates_seal(tmp_path, monkeypatch):
    monkeypatch.setattr(data, "ROOT", tmp_path)
    (tmp_path / "state").mkdir()
    protected = ["bars.parquet", "minutes.parquet",
                 "reports/generated/DATA_QUALITY_REPORT.json", "configs/dataset_policy.json"]
    for relative in protected:
        path = tmp_path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("sealed content")
    hashes = {relative: data.sha256_file(tmp_path / relative) for relative in protected}
    lock = {"bar_files": {protected[0]: hashes[protected[0]]},
            "minute_files": {protected[1]: hashes[protected[1]]},
            "quality_report_sha256": hashes[protected[2]],
            "dataset_policy_sha256": hashes[protected[3]]}
    (tmp_path / "state/dataset_lock.json").write_text(json.dumps(lock))
    assert data.verify_dataset_lock() == lock
    (tmp_path / "minutes.parquet").write_text("modified execution price")
    with pytest.raises(RuntimeError, match="minutes.parquet"):
        data.verify_dataset_lock()
