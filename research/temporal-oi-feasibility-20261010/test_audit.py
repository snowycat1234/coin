"""Small synthetic counterexamples, no provider calls or training."""

import csv
import importlib.util
import io
import zipfile
from datetime import datetime, timedelta
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("oi_verify", HERE / "verify.py")
verify = importlib.util.module_from_spec(spec)
spec.loader.exec_module(verify)
audit = verify.audit


def sample(*, reverse=False, duplicates=False, conflicting=False, missing=False, zero=False):
    day, symbol = "2022-01-01", "BTCUSDT"
    origin = datetime.fromisoformat(day)
    rows = []
    for i in range(288):
        if missing and i == 287:
            continue
        row = dict(
            zip(
                audit.EXPECTED_FIELDS,
                [
                    (origin + timedelta(minutes=5 * i)).isoformat(sep=" "),
                    symbol,
                    "0" if zero and i == 287 else "2",
                    "0" if zero and i == 287 else "40000",
                    "1",
                    "1",
                    "1",
                    "1",
                ],
                strict=True,
            )
        )
        rows.append(row)
        if duplicates:
            duplicate = dict(row)
            if conflicting and i == 287:
                duplicate["sum_open_interest"] = "3"
            rows.append(duplicate)
    if reverse:
        rows.reverse()
    csvbuf = io.StringIO()
    writer = csv.DictWriter(csvbuf, fieldnames=audit.EXPECTED_FIELDS)
    writer.writeheader()
    writer.writerows(rows)
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(f"{symbol}-metrics-{day}.csv", csvbuf.getvalue())
    return buf.getvalue(), symbol, day


def test_complete_stock_grid():
    q = audit.quality(*sample())
    assert q["complete_positive_unique_288_grid"]
    assert q["value_over_quantity_median"] == 20000


def test_reverse_rows_only_needs_timestamp_sort():
    q = verify.normalize_diagnostic(*sample(reverse=True))
    assert not q["raw_strictly_ordered"]
    assert q["canonical_complete_positive_grid"]
    assert q["terminal_2355_exists_and_positive_after_identical_dedup"]


def test_identical_duplicates_losslessly_deduplicable():
    q = verify.normalize_diagnostic(*sample(duplicates=True))
    assert q["physical_rows"] == 576
    assert q["identical_duplicate_timestamp_count"] == 288
    assert q["conflicting_duplicate_timestamp_count"] == 0
    assert q["canonical_complete_positive_grid"]


def test_conflict_is_not_first_or_last_row_choice():
    q = verify.normalize_diagnostic(*sample(duplicates=True, conflicting=True))
    assert q["conflicting_duplicate_timestamp_count"] == 1
    assert not q["canonical_complete_positive_grid"]
    assert not q["terminal_2355_exists_and_positive_after_identical_dedup"]


def test_missing_terminal_never_forward_filled():
    q = verify.normalize_diagnostic(*sample(missing=True))
    assert q["missing_5m_slots"] == 1
    assert not q["canonical_complete_positive_grid"]
    assert not q["terminal_2355_exists_and_positive_after_identical_dedup"]


def test_zero_oi_is_masked_as_invalid():
    q = verify.normalize_diagnostic(*sample(zero=True))
    assert q["invalid_oi_rows"] == 1
    assert not q["canonical_complete_positive_grid"]
    assert not q["terminal_2355_exists_and_positive_after_identical_dedup"]


def test_provider_url_cannot_cross_time_or_asset_scope():
    with pytest.raises(AssertionError):
        audit.url("BTCUSDT", "2025-01-01")
    with pytest.raises(AssertionError):
        audit.url("ADAUSDT", "2023-01-01")
