"""One synthetic source/calendar guard case; no market source is opened."""
from copy import deepcopy

import numpy as np
import polars as pl
import pytest

from scripts.investment import compare_simple_strategies as common


def synthetic_receipt(spec):
    scope, months, days, status = common.source_scope(spec)
    records = []
    for symbol in common.SYMBOLS:
        for month in months:
            first = common.date.fromisoformat(month + "-01")
            end = common.date(first.year + first.month // 12, first.month % 12 + 1, 1)
            rows = (end - first).days * 1440
            quality = dict(rows=rows, expected_rows=rows, first_open_us=common.day_us(first),
                last_open_us=common.day_us(end)-common.MINUTE_US, incomplete_days=[], quarantined_days=[])
            quality.update({key: 0 for key in ("missing_rows", "duplicate_rows", "bad_timestamps", "bad_values", "gaps", "quarantined_rows")})
            records.append(dict(symbol=symbol, month=month,
                normalized_path=str(common.ROOT / "data/normalized/spot" / symbol / "1m" / (month + ".parquet")),
                rows=rows, old_quality=quality))
    return dict(status=status, binding={"spec": {"source_scope":scope,"source_calendar":list(months)}},
        source_files=10, days_per_symbol=days, actual_minute_rows=days*1440*2, sources=records)


def test_two_fixed_source_scopes_and_exclusive_locked_boundary(monkeypatch, tmp_path):
    # Every negative fixture is confined to the isolated STATE pytest root.
    monkeypatch.setattr(common, "ROOT", tmp_path)
    monkeypatch.setattr(common, "file_sha", lambda path: (_ for _ in ()).throw(AssertionError("No market file IO in metadata guard")))
    strategies = ["CASH", "SPOT_BUY_AND_HOLD", "VOL_MANAGED_BUY_AND_HOLD",
        common.public_strategy.STRATEGY_ID, common.public_strategy.STRATEGY_2H_ID]
    spec = dict(source_scope="OCT2025_FEB2026", source_calendar=list(common.SOURCE_SCOPES["OCT2025_FEB2026"][0]),
        source_days_per_symbol=151, strategy_ids=strategies, planned_ledgers=15,
        folds=[dict(id="CONT90",period_start="2025-12-01",period_end_exclusive="2026-03-01")])
    source = synthetic_receipt(spec)
    assert common.verify_source_calendar(spec,source)==151
    chosen, windows, count = common.comparison_plan(spec)
    assert list(chosen)==strategies and count==15
    assert windows[0][1]==common.day_us(common.date(2025,10,31))
    assert windows[0][3]==common.day_us(common.LOCKED)
    assert (windows[0][3]-windows[0][2])//common.DAY_US==90
    old = dict(folds=[dict(id="CONT122",period_start="2025-08-01",period_end_exclusive="2025-12-01")])
    assert common.verify_source_calendar(old,synthetic_receipt(old))==153
    for month in ("2026-03", "2025-07"):
        with pytest.raises(ValueError,match="no locked IO"):
            common.allowed_source_path(dict(symbol="BTCUSDT",month=month,normalized_path="/never/open"),spec)
    corrupted = deepcopy(source); corrupted["sources"][0]["normalized_path"] = str(tmp_path/"wrong.parquet")
    with pytest.raises(ValueError,match="Exact explicit"):
        common.verify_source_calendar(spec,corrupted)
    corrupted = deepcopy(source); corrupted["status"] = "PASS_REUSED_FROZEN_SPOT_MINUTE_SOURCE_153D_CALENDAR"
    with pytest.raises(ValueError,match="Accepted original"):
        common.verify_source_calendar(spec,corrupted)
    corrupted = deepcopy(source); corrupted["sources"].pop()
    with pytest.raises(ValueError,match="Exactly ten"):
        common.verify_source_calendar(spec,corrupted)
    corrupted = deepcopy(source); corrupted["sources"][0]["old_quality"]["last_open_us"] -= common.MINUTE_US
    with pytest.raises(ValueError,match="Complete sealed"):
        common.verify_source_calendar(spec,corrupted)
    corrupted = deepcopy(source); corrupted["actual_minute_rows"] -= 1
    with pytest.raises(ValueError,match="Exact accepted source coverage"):
        common.verify_source_calendar(spec,corrupted)
    corrupted = deepcopy(source); corrupted["binding"]["spec"]["source_scope"] = "JUL_NOV_2025"
    with pytest.raises(ValueError,match="scope/calendar mismatch"):
        common.verify_source_calendar(spec,corrupted)
    altered = deepcopy(spec); altered["source_calendar"][-1]="2026-03"
    with pytest.raises(ValueError,match="source_calendar"):
        common.source_scope(altered)
    altered = deepcopy(spec); altered["source_scope"]="ANY_MONTH"
    with pytest.raises(ValueError,match="Only two"):
        common.source_scope(altered)
    uncovered = deepcopy(spec); uncovered["folds"][0]["period_start"]="2025-10-01"
    with pytest.raises(ValueError,match="does not cover"):
        common.verify_source_calendar(uncovered,source)
    locked = deepcopy(spec); locked["folds"][0]["period_end_exclusive"]="2026-03-02"
    with pytest.raises(ValueError,match="no locked IO"):
        common.comparison_plan(locked)


def test_final_close_metadata_only_after_last_decision_and_marks_preserved():
    # A February source minute may close exactly at LOCKED. It is required for
    # final valuation, but is after the last decision and never a signal input.
    boundary = common.day_us(common.LOCKED)
    stamps = np.arange(boundary-3*common.MINUTE_US,boundary+common.MINUTE_US,common.MINUTE_US,dtype=np.int64)
    complete = pl.concat([pl.DataFrame(dict(symbol=[symbol]*len(stamps),close_us=stamps,
        available_us=stamps,close=np.full(len(stamps),100.))) for symbol in common.SYMBOLS])
    calendar = stamps[1:-1]
    closes = common.signal_close_view(complete,calendar)
    assert closes.height==6 and complete.height==8
    assert closes['close_us'].max()==boundary-common.MINUTE_US
    common.benchmarks._integer_timestamp_columns(closes,('close_us','available_us'))
    # Only the new boundary guard is exercised; no old strategy suite replay.
    with pytest.raises(ValueError,match="locked timestamps forbidden"):
        common.benchmarks._integer_timestamp_columns(complete,('close_us','available_us'))
    early_calendar=stamps[:2]
    old_prefix=complete.filter(pl.col('close_us')<boundary)
    before=common.bulk_fixed_targets.fixed_targets('SPOT_BUY_AND_HOLD',old_prefix,early_calendar)
    after=common.bulk_fixed_targets.fixed_targets('SPOT_BUY_AND_HOLD',common.signal_close_view(complete,early_calendar),early_calendar)
    assert before.targets.equals(after.targets) and before.calendar_ledger.equals(after.calendar_ledger)
    assert before.receipt==after.receipt
    assert complete['close_us'].max()==boundary and complete['available_us'].max()==boundary
