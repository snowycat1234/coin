import copy
import hashlib
import json
import math

import numpy as np
import polars as pl
import pytest

from quant.features_v2 import (
    FEATURE_NAMES_V2,
    HOUR_US,
    FeatureInputError,
    HourlyFeatureState,
    build_features_v2,
    feature_contract_v2,
    feature_schema_v2,
)
from quant.research import FEATURE_NAMES, build_features

BASE = 1_704_067_200_000_000


def row(index, symbol="BTCUSDT", *, zero=False):
    multiplier = 1 if symbol == "BTCUSDT" else 2
    price = multiplier * (100 + index * 0.03 + math.sin(index / 11))
    opened = BASE + index * HOUR_US
    return {
        "symbol": symbol, "interval": "1h", "open_us": opened,
        "close_us": opened + HOUR_US, "available_us": opened + HOUR_US,
        "open": price - 0.1, "close": price, "high": price + 0.2, "low": price - 0.3,
        "volume": 0.0 if zero else 1000 + index,
        "quote_volume": 0.0 if zero else 90000 + 120 * index,
        "taker_buy_base": 0.0 if zero else (1000 + index) * (0.5 + 0.1 * math.sin(index / 7)),
        "taker_buy_quote": 0.0 if zero else (90000 + 120 * index) * 0.5,
    }


def data(count=260, *, missing=None):
    return pl.DataFrame([
        row(index, symbol) for index in range(count) for symbol in ("BTCUSDT", "ETHUSDT")
        if missing != (index, symbol)
    ])


def test_fixed40_schema_old_names_and_manifest_definition_contract():
    schema = feature_schema_v2()
    assert len(FEATURE_NAMES_V2) == 40 and len(set(FEATURE_NAMES_V2)) == 40
    assert FEATURE_NAMES_V2[:10] == FEATURE_NAMES
    assert schema["missing_policy"] == "reject"
    assert tuple(item["name"] for item in schema["features"]) == FEATURE_NAMES_V2
    assert all(item["dtype"] == "float64" and item["definition"] for item in schema["features"])
    contract = feature_contract_v2()
    expected = hashlib.sha256(json.dumps(schema, sort_keys=True, separators=(",", ":"),
                                       allow_nan=False).encode()).hexdigest()
    assert contract["schema_sha256"] == expected
    assert all(len(contract[key]) == 64 for key in (
        "schema_sha256", "definition_sha256", "implementation_sha256",
    ))


def test_legacy10_independent_polars_formulas_match_after100_and_40_are_finite():
    source = data()
    actual = build_features_v2(source)
    previous = build_features(source).filter(pl.col("ema_gap").is_not_null())
    assert actual.height == previous.height == 2 * (260 - 99)
    np.testing.assert_allclose(
        actual.select(FEATURE_NAMES).to_numpy(), previous.select(FEATURE_NAMES).to_numpy(),
        rtol=1e-9, atol=1e-12,
    )
    assert actual["feature_ready"].all()
    assert np.isfinite(actual.select(FEATURE_NAMES_V2).to_numpy()).all()


def test_incremental_live_equals_batch_and_json_restart_during_unpaired_hour():
    source = data()
    expected = build_features_v2(source)
    state, outputs = HourlyFeatureState(), []
    for index, bar in enumerate(source.sort(["available_us", "symbol"]).iter_rows(named=True)):
        result = state.ingest(bar)
        outputs.extend(item for item in result if item["feature_ready"])
        if index == 210:  # first asset only, preserving the causal pending snapshot
            state = HourlyFeatureState.from_snapshot(json.loads(json.dumps(state.export_state())))
    actual = pl.DataFrame(outputs).sort(["available_us", "symbol"])
    np.testing.assert_array_equal(
        actual.select(FEATURE_NAMES_V2).to_numpy(), expected.select(FEATURE_NAMES_V2).to_numpy()
    )
    assert actual.select("available_us", "received_us", "symbol").equals(
        expected.select("available_us", "received_us", "symbol")
    )


def test_delayed_other_asset_never_uses_newer_own_bar_and_receipt_stays_separate():
    state = HourlyFeatureState()
    for index in range(99):
        for symbol in ("BTCUSDT", "ETHUSDT"):
            state.ingest(row(index, symbol))
    earlier = row(99)
    assert state.ingest(earlier) == []
    future = row(100)
    future.update(open=100000, high=100001, low=99999, close=100000)
    assert state.ingest(future) == []
    late = row(99, "ETHUSDT")
    late["received_us"] = future["available_us"] + 100
    output = state.ingest(late)
    assert len(output) == 2 and all(item["feature_ready"] for item in output)
    btc = next(item for item in output if item["symbol"] == "BTCUSDT")
    assert btc["available_us"] == earlier["available_us"]
    assert btc["received_us"] == late["received_us"]
    assert btc["emitted_asof_us"] >= btc["received_us"]
    expected = math.log(earlier["close"]) - math.log(row(98)["close"])
    assert btc["log_return_1"] == pytest.approx(expected)
    assert btc["other_asset_return_1"] == pytest.approx(expected)
    assert btc["relative_return_1"] == pytest.approx(0)
    assert btc["rolling_corr_24"] == pytest.approx(1)


def test_missing_other_hour_is_not_stale_join_and_all_windows_reset_for100():
    actual = build_features_v2(data(360, missing=(150, "ETHUSDT")), include_warmup=True)
    assert actual.filter(pl.col("close_us") == BASE + 151 * HOUR_US).is_empty()
    window = actual.filter((pl.col("open_us") > BASE + 150 * HOUR_US)
                           & (pl.col("open_us") < BASE + 250 * HOUR_US))
    assert not window["feature_ready"].any()
    resumed = actual.filter(pl.col("open_us") == BASE + 250 * HOUR_US)
    assert resumed.height == 2 and resumed["feature_ready"].all()
    expected = build_features(data(360).filter(pl.col("open_us") >= BASE + 151 * HOUR_US))
    expected = expected.filter(pl.col("open_us") == BASE + 250 * HOUR_US)
    np.testing.assert_allclose(
        resumed.filter(pl.col("symbol") == "ETHUSDT").select(FEATURE_NAMES).to_numpy(),
        expected.filter(pl.col("symbol") == "ETHUSDT").select(FEATURE_NAMES).to_numpy(),
        rtol=1e-9, atol=1e-12,
    )


def test_future_edit_cannot_change_any_earlier_vector():
    original = data(350)
    changed = original.with_columns(
        *[pl.when(pl.col("open_us") >= BASE + 250 * HOUR_US)
          .then(pl.col(column) * 5).otherwise(pl.col(column)).alias(column)
          for column in ("open", "high", "low", "close", "volume", "quote_volume",
                         "taker_buy_base", "taker_buy_quote")]
    )
    early = pl.col("open_us") < BASE + 250 * HOUR_US
    assert build_features_v2(original).filter(early).equals(
        build_features_v2(changed).filter(early)
    )


def test_new_range_volume_and_seasonality_formulas_against_direct_calculation():
    source = data(130)
    final = build_features_v2(source).filter(pl.col("symbol") == "BTCUSDT").tail(1).to_dicts()[0]
    rows = [row(index) for index in range(130)]
    price = rows[-1]["close"]
    assert final["high_distance_24"] == pytest.approx(
        price / max(r["high"] for r in rows[-24:]) - 1
    )
    assert final["low_distance_96"] == pytest.approx(price / min(r["low"] for r in rows[-96:]) - 1)
    tr = [max(r["high"] - r["low"], abs(r["high"] - rows[i - 1]["close"]),
              abs(r["low"] - rows[i - 1]["close"])) for i, r in enumerate(rows) if i > 0]
    assert final["atr_fraction_14"] == pytest.approx(np.mean(tr[-14:]) / price)
    volumes = [r["quote_volume"] for r in rows[-24:]]
    expected_z = (volumes[-1] - np.mean(volumes)) / (np.std(volumes, ddof=1) + 1e-12)
    assert final["quote_volume_z24"] == pytest.approx(expected_z)
    assert final["is_BTC"] == 1 and final["is_ETH"] == 0
    assert final["hour_sin"] ** 2 + final["hour_cos"] ** 2 == pytest.approx(1)
    assert final["weekday_sin"] ** 2 + final["weekday_cos"] ** 2 == pytest.approx(1)


def test_flat_prices_zero_range_zero_volume_are_neutral_and_finite():
    source = data(120).with_columns(
        *[pl.lit(100.0).alias(name) for name in ("open", "high", "low", "close")],
        *[pl.lit(0.0).alias(name) for name in (
            "volume", "quote_volume", "taker_buy_base", "taker_buy_quote",
        )],
    )
    actual = build_features_v2(source)
    assert np.isfinite(actual.select(FEATURE_NAMES_V2).to_numpy()).all()
    assert (actual["close_location"] == 0.5).all()
    assert (actual["taker_fraction"] == 0.5).all()
    assert (actual["rolling_corr_24"] == 0).all()
    assert (actual["taker_imbalance_mean_16"] == 0).all()


def test_duplicate_idempotent_changed_or_future_evidence_rejected_without_mutation():
    state = HourlyFeatureState()
    bar = row(0)
    state.ingest(bar)
    before = state.export_state()
    assert state.ingest({**bar, "received_us": bar["available_us"] + 100}) == []
    assert state.export_state() == before
    with pytest.raises(FeatureInputError, match="changed"):
        state.ingest({**bar, "volume": 999999})
    with pytest.raises(FeatureInputError, match="future"):
        state.ingest(row(1), asof_us=bar["available_us"])
    with pytest.raises(FeatureInputError, match="integers"):
        state.ingest({**row(1), "available_us": float(row(1)["available_us"])})
    with pytest.raises(FeatureInputError, match="finite"):
        state.ingest({**row(1), "quote_volume": float("nan")})
    assert state.export_state() == before


def test_state_definition_and_content_tampering_rejected_and_memory_stays_bounded():
    state = HourlyFeatureState()
    for index in range(600):
        state.ingest(row(index))
    snapshot = state.export_state()
    assert len(snapshot["state"]["symbols"]["BTCUSDT"]["rows"]) == 100
    assert len(snapshot["state"]["pending"]) == 4
    assert snapshot["state"]["unpaired_hours_discarded"] == 596
    assert len(json.dumps(snapshot)) < 200000
    changed = copy.deepcopy(snapshot)
    changed["state"]["last_asof_us"] += 1
    with pytest.raises(FeatureInputError, match="digest"):
        HourlyFeatureState.from_snapshot(changed)
    changed = copy.deepcopy(snapshot)
    changed["contract"]["definition_sha256"] = "0" * 64
    body = {key: changed[key] for key in ("contract", "state")}
    changed["state_sha256"] = hashlib.sha256(json.dumps(
        body, sort_keys=True, separators=(",", ":"), allow_nan=False,
    ).encode()).hexdigest()
    with pytest.raises(FeatureInputError, match="definition"):
        HourlyFeatureState.from_snapshot(changed)
