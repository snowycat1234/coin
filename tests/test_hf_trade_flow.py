import hashlib
import importlib.util
import json
import zipfile
from datetime import UTC, date, datetime
from types import SimpleNamespace

import httpx
import pyarrow.parquet as pq
import pytest

from quant.paths import ROOT, STATE
from quant.research_fast import trade_flow as flow

DAY = date(2025, 7, 1)
OPENED = int(datetime(2025, 7, 1, tzinfo=UTC).timestamp()) * 1_000_000
SPEC = importlib.util.spec_from_file_location("isolated_hf_fetch", ROOT / "scripts/hf_fetch.py")
fetch = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(fetch)


def archive(tmp_path, rows, *, market="spot", header=False):
    assert tmp_path.resolve().is_relative_to(STATE)
    body = []
    if header:
        body.append(
            "agg_trade_id,price,quantity,first_trade_id,last_trade_id,transact_time,is_buyer_maker"
        )
    for agg, price, quantity, first, last, offset, maker in rows:
        timestamp = OPENED + offset
        timestamp = timestamp if market == "spot" else timestamp // 1000
        line = f"{agg},{price},{quantity},{first},{last},{timestamp},{maker}"
        body.append(line + (",True" if market == "spot" else ""))
    path = tmp_path / "BTCUSDT-aggTrades-2025-07-01.zip"
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as out:
        out.writestr("BTCUSDT-aggTrades-2025-07-01.csv", "\n".join(body) + "\n")
    return path


def convert(tmp_path, rows, **kwargs):
    source = archive(
        tmp_path, rows, market=kwargs.get("market", "spot"), header=kwargs.pop("header", False)
    )
    output = tmp_path / "bars.parquet"
    report = flow.convert_zip(
        source, output, symbol="BTCUSDT", day=DAY, **{"market": "spot", **kwargs}
    )
    return report, pq.read_table(output).to_pylist()


def test_raw_counts_size_maker_and_interarrival_across_bins(tmp_path):
    report, bars = convert(
        tmp_path,
        [
            (10, 100, 100, 100, 102, 1_000_000, "False"),
            (14, 101, 1, 103, 103, 3_000_000, "True"),
            (15, 102, 2, 104, 105, 6_000_000, "False"),
            (16, 103, 1, 106, 106, 8_000_000, "True"),
        ],
    )
    first, second = bars[:2]
    assert report["rows"] == len(bars) == 17280
    assert report["aggregate_rows"] == 4 and report["raw_trade_count"] == 7
    assert first["agg_count"] == 2 and first["trade_count"] == first["raw_trade_count"] == 4
    assert (first["buy_count"], first["sell_count"]) == (3, 1)
    assert first["large_trade_share"] == pytest.approx(10000 / 10101)
    assert first["mean_trade_size"] == pytest.approx(10101 / 2)
    assert first["vwap"] == pytest.approx(10101 / 101)
    assert second["interarrival_count"] == 2
    assert second["mean_interarrival"] == 2.5
    assert second["std_interarrival"] == 0.5
    assert second["first_trade_us"] == OPENED + 6_000_000
    assert second["last_trade_us"] == OPENED + 8_000_000
    assert second["available_us"] == second["close_us"] == OPENED + 10_000_000
    assert second["return_5s"] == pytest.approx(__import__("math").log(103 / 101))
    assert report["cross_day_raw_boundary_verified"] is False


def test_known_empty_bins_are_not_filled_and_trade_gap_interval_is_retained(tmp_path):
    _, bars = convert(
        tmp_path,
        [
            (1, 100, 1, 1, 1, 1_000_000, "False"),
            (2, 110, 1, 2, 2, 16_000_000, "False"),
        ],
    )
    assert bars[1]["empty_bin"] is True and bars[1]["trade_count"] == 0
    assert bars[1]["quote_notional"] == 0
    assert all(
        bars[1][key] is None for key in ("open", "close", "vwap", "first_trade_us", "last_trade_us")
    )
    assert bars[3]["return_5s"] is None
    assert bars[3]["mean_interarrival"] == 15
    assert bars[-1]["quality"] == 0


def test_perp_header_millisecond_conversion_and_cross_day_raw_binding(tmp_path):
    report, bars = convert(
        tmp_path,
        [(1, 100, 1, 101, 102, 2_000, "True")],
        market="perp",
        header=True,
        previous_day_last_raw_id=100,
    )
    assert bars[0]["first_trade_us"] == OPENED + 2_000
    assert bars[0]["sell_count"] == 2
    assert report["cross_day_raw_boundary_verified"] is True


@pytest.mark.parametrize(
    "bad,match",
    [
        ((2, 100, 1, 103, 103, 2_000_000, "False"), "RAW_TRADE_ID_GAP_OR_OVERLAP"),
        ((2, 100, 1, 100, 102, 2_000_000, "False"), "RAW_TRADE_ID_GAP_OR_OVERLAP"),
        ((1, 100, 1, 102, 102, 2_000_000, "False"), "Duplicate/nonordered"),
        ((2, 100, 1, 102, 102, 0, "False"), "Duplicate/nonordered"),
    ],
)
def test_invalid_raw_continuity_order_and_duplicates_fail_without_manifest(tmp_path, bad, match):
    with pytest.raises(ValueError, match=match):
        convert(tmp_path, [(1, 100, 1, 100, 101, 1_000_000, "False"), bad])
    assert not list(tmp_path.glob("*.manifest.json"))


def test_date_seal_runs_before_file_or_network_access(tmp_path):
    for day in (date(2025, 6, 30), date(2026, 3, 1)):
        with pytest.raises(ValueError, match="seal"):
            fetch.official_url("spot", "BTCUSDT", day)
        with pytest.raises(ValueError, match="seal"):
            flow.convert_zip(
                tmp_path / "absent.zip",
                tmp_path / "absent.parquet",
                market="spot",
                symbol="BTCUSDT",
                day=day,
            )
    assert not (tmp_path / "absent.parquet").exists()


def test_csv_zip_member_bound_and_cross_day_mismatch_fail(tmp_path):
    source = archive(tmp_path, [(1, 100, 1, 101, 101, 0, "False")])
    with pytest.raises(ValueError, match="oversize"):
        flow.convert_zip(
            source,
            tmp_path / "size.parquet",
            market="spot",
            symbol="BTCUSDT",
            day=DAY,
            max_csv_bytes=1,
        )
    with pytest.raises(ValueError, match="CROSS_DAY"):
        flow.convert_zip(
            source,
            tmp_path / "boundary.parquet",
            market="spot",
            symbol="BTCUSDT",
            day=DAY,
            previous_day_last_raw_id=99,
        )


def mock_client(payload, *, bad_checksum=False, announced=None):
    digest = "0" * 64 if bad_checksum else hashlib.sha256(payload).hexdigest()

    def handler(request):
        if request.method == "HEAD":
            return httpx.Response(
                200,
                headers={"content-length": str(len(payload) if announced is None else announced)},
            )
        if request.url.path.endswith(".CHECKSUM"):
            return httpx.Response(
                200, content=f"{digest}  BTCUSDT-aggTrades-2025-07-01.zip\n".encode()
            )
        return httpx.Response(200, content=payload)

    return httpx.Client(transport=httpx.MockTransport(handler))


@pytest.mark.parametrize("bad_checksum", [False, True])
def test_thin_wrapper_manifest_then_owned_raw_deletion_or_failure_retention(
    tmp_path, monkeypatch, bad_checksum
):
    payload = archive(tmp_path, [(1, 100, 1, 1, 1, 0, "False")]).read_bytes()
    monkeypatch.setattr(fetch, "STATE", tmp_path)
    monkeypatch.setattr(
        fetch, "disk", SimpleNamespace(check=lambda **kwargs: {"status": "FIXTURE", **kwargs})
    )
    with mock_client(payload, bad_checksum=bad_checksum) as client:
        if bad_checksum:
            with pytest.raises(RuntimeError, match="evidence retained"):
                fetch.fetch_day("spot", "BTCUSDT", DAY, store=tmp_path / "store", client=client)
            failed = next(tmp_path.glob("hf-official-*/FAILURE.json"))
            receipt = json.loads(failed.read_text())
            assert receipt["status"] == "FAILED_OFFICIAL_PIPELINE_UNACCEPTED"
            assert receipt["owned_raw_zip_exists"] is True
            assert not list((tmp_path / "store").rglob("*.manifest.json"))
        else:
            receipt = fetch.fetch_day(
                "spot", "BTCUSDT", DAY, store=tmp_path / "store", client=client
            )
            assert receipt["raw_deleted"] is True
            assert not list(tmp_path.glob("hf-official-*"))
            manifest = json.loads(__import__("pathlib").Path(receipt["manifest_path"]).read_text())
            assert manifest["checksum_status"] == "PASS"
            assert manifest["conversion"]["rows"] == 17280
            assert receipt["feature_sha256"] == manifest["feature_sha256"]
            assert manifest["engineering_fixture_hook"] is True
            assert manifest["raw_deleted"] is False  # Durable authorization precedes deletion.
            with pytest.raises(ValueError, match="already exists"):
                fetch.fetch_day("spot", "BTCUSDT", DAY, store=tmp_path / "store", client=client)


def test_head_size_limit_stops_download_and_keeps_failure_receipt(tmp_path, monkeypatch):
    monkeypatch.setattr(fetch, "STATE", tmp_path)
    with mock_client(b"unused", announced=100) as client:
        with pytest.raises(RuntimeError, match="evidence retained"):
            fetch.fetch_day(
                "spot", "BTCUSDT", DAY, store=tmp_path / "store", client=client, max_zip_bytes=10
            )
    assert next(tmp_path.glob("hf-official-*/FAILURE.json")).is_file()
    assert not list(tmp_path.glob("hf-official-*/*.zip"))
