import importlib.util
import zipfile
from datetime import UTC, date, datetime

import pyarrow.parquet as pq
import pytest

from quant.paths import ROOT, STATE
from quant.research_fast import trade_flow as v1
from quant.research_fast import trade_flow_v2 as v2

DAY = date(2025, 7, 1)
OPENED = int(datetime(2025, 7, 1, tzinfo=UTC).timestamp()) * 1_000_000


def archive(tmp_path, market, rows):
    assert tmp_path.resolve().is_relative_to(STATE)
    path = tmp_path / "BTCUSDT-aggTrades-2025-07-01.zip"
    body = (
        "\n".join(
            f"{a},{p},{q},{f},{last},{(OPENED + t) // (1000 if market == 'perp' else 1)},"
            f"{maker}" + (",True" if market == "spot" else "")
            for a, p, q, f, last, t, maker in rows
        )
        + "\n"
    )
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as out:
        out.writestr(path.stem + ".csv", body)
    return path


def convert(tmp_path, market, rows, **kwargs):
    path = archive(tmp_path, market, rows)
    report = v2.convert_zip(
        path, tmp_path / "bars.parquet", market=market, symbol="BTCUSDT", day=DAY, **kwargs
    )
    return report, pq.read_table(tmp_path / "bars.parquet")


def test_spot_observed_counts_and_all_market_values_match_frozen_core(tmp_path):
    rows = [
        (10, 100, 2, 100, 102, 1_000_000, "False"),
        (14, 101, 1, 103, 103, 3_000_000, "True"),
        (15, 102, 2, 104, 105, 6_000_000, "False"),
    ]
    report, bars = convert(tmp_path, "spot", rows)
    v1.convert_zip(
        tmp_path / "BTCUSDT-aggTrades-2025-07-01.zip",
        tmp_path / "v1.parquet",
        market="spot",
        symbol="BTCUSDT",
        day=DAY,
    )
    old = pq.read_table(tmp_path / "v1.parquet")
    assert bars.select(v1.FLOAT_COLUMNS).equals(old.select(v1.FLOAT_COLUMNS))
    assert report["first_f"] == 100 and report["last_l"] == 105
    assert "raw_trade_count" not in bars.column_names and "raw_trade_count" not in report
    first = bars.slice(0, 1).to_pylist()[0]
    assert first["trade_count"] == first["agg_count"] == 2
    assert first["buy_count"] == first["sell_count"] == 1
    assert v1.VERSION == "trade_flow_5s_v1" and "raw_trade_count" in v1.SCHEMA.names
    assert bars.num_rows == 17280 and report["version"] == v2.VERSION


def test_perp_range_gaps_are_audited_original_ids_preserved(tmp_path):
    report, bars = convert(
        tmp_path,
        "perp",
        [
            (10, 100, 2, 100, 102, 1_000_000, "False"),
            (11, 101, 1, 146, 146, 3_000_000, "True"),
        ],
    )
    assert report["original_raw_range_gap_events"] == 1
    assert report["original_unrepresented_raw_ids"] == 43
    assert report["first_a"] == 10 and report["last_a"] == 11
    assert report["first_f"] == 100 and report["last_l"] == 146
    assert report["raw_gap_cause"] == "UNCONFIRMED"
    assert bars["trade_count"][0].as_py() == 2
    assert bars["quote_notional"][0].as_py() == 301
    assert report["adapter_source_hashes"] == v2.source_hashes()


@pytest.mark.parametrize(
    "market,second,match",
    [
        ("perp", (12, 101, 1, 103, 103, 3_000_000, "True"), "AGGREGATE_ID_GAP"),
        ("perp", (11, 101, 1, 102, 103, 3_000_000, "True"), "OVERLAP"),
        ("spot", (11, 101, 1, 104, 104, 3_000_000, "True"), "SPOT_ORIGINAL_RAW_ID_GAP"),
    ],
)
def test_unresolved_aggregate_gaps_and_original_overlaps_still_fail(
    tmp_path, market, second, match
):
    with pytest.raises(ValueError, match=match):
        convert(tmp_path, market, [(10, 100, 2, 100, 102, 1_000_000, "False"), second])


def test_cross_day_perp_scope_boundary_and_unknown_raw_scope(tmp_path):
    report, _ = convert(
        tmp_path,
        "perp",
        [(11, 100, 1, 110, 112, 0, "False")],
        previous_day_last_raw_id=100,
        previous_day_last_agg_id=10,
    )
    assert report["cross_day_scope_boundary_verified"] is True
    assert report["cross_day_raw_boundary_verified"] is False
    assert report["cross_day_unrepresented_raw_ids"] == 9


def test_boundary_pair_and_locked_seal_before_read(tmp_path):
    with pytest.raises(ValueError, match="Both preceding"):
        v2.convert_zip(
            tmp_path / "missing",
            tmp_path / "out",
            market="spot",
            symbol="BTCUSDT",
            day=DAY,
            previous_day_last_raw_id=1,
        )
    with pytest.raises(ValueError, match="seal"):
        v2.convert_zip(
            tmp_path / "missing",
            tmp_path / "out",
            market="spot",
            symbol="BTCUSDT",
            day=date(2026, 3, 1),
        )
    assert not (tmp_path / "out").exists()


def test_thin_wrapper_uses_original_orchestrator_source_without_mutating_it():
    spec = importlib.util.spec_from_file_location("new_wrapper", ROOT / "scripts/hf_fetch_v2.py")
    adapter = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(adapter)
    assert adapter.STORE.name == v2.VERSION
    assert all(v1.checksum(ROOT / name) == digest for name, digest in v2.FROZEN_CORE.items())
