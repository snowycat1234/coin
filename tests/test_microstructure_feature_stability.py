"""Descriptive QA acceptance; no future targets or model fitting."""

import importlib.util
import math
import sys
import tempfile
from pathlib import Path

import pytest

from quant.microstructure import MicrostructureCollector, MicrostructureConfig
from quant.paths import ROOT, STATE

SPEC = importlib.util.spec_from_file_location(
    "a07_stability_tests", ROOT / "scripts/audit_microstructure_feature_stability.py"
)
analysis = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = analysis
SPEC.loader.exec_module(analysis)
qa = analysis.qa


def row(symbol, opened, *, quality=0):
    values = {name: 0 for name in qa.FEATURES}
    values.update(mid=100.0, trade_vwap=None, trade_flow_imbalance=None,
                  realized_return_1s=None, spread_bps=2.0, quote_update_count=2,
                  bid_qty_mean=3.0, ask_qty_mean=4.0)
    return {**values, "symbol": symbol, "open_us": opened, "quality": quality,
            "known_seconds": 1, "valid_seconds": int(not quality & qa.INVALID)}


def test_welford_nulls_zero_and_population_std_have_correct_denominators():
    moment = analysis.Moment()
    for value in (None, 0, 2, 4):
        moment.add(value)
    report = moment.report()
    assert report["finite_count"] == 3 and report["legal_null_count"] == 1
    assert report["nonzero_count"] == 2 and report["sum_of_observed_values"] == 6
    assert report["mean"] == 2 and report["population_std"] == pytest.approx(math.sqrt(8 / 3))
    assert report["min"] == 0 and report["max"] == 4
    empty = analysis.Moment().report()
    assert empty["mean"] is None and empty["population_std"] is None


@pytest.mark.parametrize("bad", [float("nan"), float("inf"), "1.0", True])
def test_nonfinite_or_non_numeric_values_are_refused(bad):
    with pytest.raises(qa.QualityRejected):
        analysis.Moment().add(bad)


def test_descriptive_pairing_matches_frozen_exclusion_and_keeps_hour_boundaries():
    begin = qa.FUTURE_START
    uncertain = [(begin + 2 * qa.SECOND + 500, begin + 3 * qa.SECOND)]
    limits = qa.Limits()
    original, observed = qa.CommonSeconds(uncertain, limits), analysis.FeatureCommonSeconds(
        uncertain, limits
    )
    for index in range(6):
        for symbol in qa.SYMBOLS:
            if index == 4 and symbol == "ETHUSDT":
                continue
            value = row(symbol, begin + index * qa.SECOND,
                        quality=qa.FLAGS["STALE_QUOTE"] if index == 1 else 0)
            original.add(value)
            observed.add(value)
    for symbol in qa.SYMBOLS:
        value = row(symbol, begin + 3600 * qa.SECOND)
        original.add(value)
        observed.add(value)
    original.flush()
    observed.flush()
    assert original.report() == observed.report()
    report = observed.descriptive_report()
    assert report["paired_usable_seconds"] == 4
    assert len(report["hour_groups"]) == 4
    assert sum(group["paired_usable_seconds"] for group in report["hour_groups"].values()) == 8
    for group in report["hour_groups"].values():
        assert group["features"]["trade_vwap"]["finite_count"] == 0
        assert group["features"]["trade_vwap"]["legal_null_count"] == group["paired_usable_seconds"]


def test_numeric_ranges_report_alerts_without_censoring_values_or_conferring_alpha():
    hour = analysis.Hour()
    value = row("BTCUSDT", qa.FUTURE_START)
    value.update(L1_imbalance_last=1.5, aggressive_sell_notional=-10,
                 bid_price_change_count=3)
    hour.add(value)
    report = hour.report()
    assert report["range_alert_counts"] == {
        "L1_imbalance_last": 1, "aggressive_sell_notional": 1,
        "bid_price_change_count_exceeds_quote_updates": 1,
    }
    assert report["features"]["aggressive_sell_notional"]["min"] == -10


def test_real_collector_format_readonly_integrity_pairs_and_nullable_statistics():
    with tempfile.TemporaryDirectory(prefix="a07-stability-", dir=STATE) as native:
        with tempfile.TemporaryDirectory(prefix="a07-stability-", dir=ROOT / ".cache/tmp") as data:
            database, store = Path(native) / "source.sqlite3", Path(data)
            writer = MicrostructureCollector(
                MicrostructureConfig(db_path=database, store=store, mode="engineering"),
                disk_check=lambda **_: {"status": "OK"},
            )
            begin = qa.FUTURE_START
            writer.set_connected(True, received_us=begin)
            for second in range(120):
                for symbol in qa.SYMBOLS:
                    writer.ingest({"s": symbol, "u": second + 1, "b": "100", "a": "102",
                                   "B": "10", "A": "20"},
                                  received_us=begin + second * qa.SECOND + 100)
            writer.advance(begin + 120 * qa.SECOND)
            writer.close()
            sources = (database, *store.rglob("*.parquet"))
            before = {path: qa.digest(path) for path in sources}
            original = qa.CommonSeconds
            result = analysis.diagnose(database, store, now_us=begin + 121 * qa.SECOND)
            assert qa.CommonSeconds is original
            assert result["status"] == "DESCRIPTIVE_FEATURE_QA_ONLY"
            assert result["quality_snapshot"]["integrity"] == "PASS"
            assert result["quality_snapshot"]["snapshot"]["read_transaction_seconds"] <= 5
            assert result["quality_snapshot"]["snapshot"][
                "read_transaction_released_before_file_scan"
            ]
            assert result["descriptive"]["paired_usable_seconds"] > 0
            assert not result["alpha_eligible"] and not result["training_authorized"]
            assert not result["actual_24h_capacity_accepted"]
            assert not result["actual_24h_quality_accepted"]
            assert not result["descriptive"]["range_alerts_present"]
            assert all(qa.digest(path) == digest for path, digest in before.items())


def test_frozen_auditor_failure_discards_partial_observations_and_restores_consumer(tmp_path):
    original = qa.CommonSeconds
    result = analysis.diagnose(STATE / "absent-stability.sqlite3", ROOT / ".cache/absent-store")
    assert result["status"] == "FAIL_CLOSED" and "descriptive" not in result
    assert not result["alpha_eligible"] and qa.CommonSeconds is original
