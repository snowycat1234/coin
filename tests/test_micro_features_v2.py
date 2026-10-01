import copy
import hashlib
import json
import math

import pytest

from quant.micro_features_v2 import (
    DERIVED_FEATURES,
    EPS,
    FEATURE_NAMES_V2,
    HALF_LIFE_SECONDS,
    INPUT_FIELDS,
    INTERVAL_US,
    INVALID_QUALITY_MASK,
    MODEL_FEATURE_NAMES,
    SCALE_HEAVY_FEATURES,
    SOURCE_VERSION,
    WARMUP_PAST_SAMPLES,
    MicroFeatureInputError,
    MicroFeatureState,
    build_micro_features_v2,
    iter_micro_features_v2,
    micro_feature_contract_v2,
    micro_feature_schema_v2,
)

BASE = 1_704_067_200_000_000


def row(index, symbol="BTCUSDT", **changes):
    multiplier = 1 if symbol == "BTCUSDT" else 17
    phase = math.sin(index / 7)
    mid = multiplier * (100 + index / 100)
    buy, sell = multiplier * (100 + index % 13), multiplier * (80 + index % 7)
    opened = BASE + index * INTERVAL_US
    result = {
        "version": SOURCE_VERSION, "symbol": symbol, "mode": "engineering", "session": "s1",
        "interval_s": 5, "open_us": opened, "close_us": opened + INTERVAL_US,
        "available_us": opened + INTERVAL_US + 100, "quality": 0,
        "known_seconds": 5, "valid_seconds": 5, "mid_last": mid,
        "spread_bps_mean": 2 + phase / 10, "spread_bps_last": 2 + phase / 9,
        "l1_total_depth_last": multiplier * (8 + phase),
        "bid_qty_mean_mean": multiplier * (3 + phase),
        "ask_qty_mean_mean": multiplier * (5 + phase),
        "L1_imbalance_mean_mean": -0.25 + phase / 10,
        "L1_imbalance_last": -0.25 + phase / 9,
        "microprice_offset_bps_mean_mean": phase / 20, "OFI_L1": multiplier * phase,
        "aggressive_buy_notional": buy, "aggressive_sell_notional": sell,
        "trade_vwap": mid * (1 + phase / 10_000), "quote_update_count": 20 + index % 11,
        "agg_trade_count": 2 + index % 5, "realized_return": phase / 10_000,
    }
    result.update(changes)
    return result


def series(count=WARMUP_PAST_SAMPLES + 12):
    return [row(index, symbol) for index in range(count) for symbol in ("BTCUSDT", "ETHUSDT")]


def resign(snapshot):
    snapshot["sha256"] = hashlib.sha256(json.dumps(
        {key: value for key, value in snapshot.items() if key != "sha256"},
        sort_keys=True, separators=(",", ":"), allow_nan=False,
    ).encode()).hexdigest()
    return snapshot


def test_frozen_schema_formula_and_units():
    schema = micro_feature_schema_v2()
    assert len(DERIVED_FEATURES) == 8 and len(FEATURE_NAMES_V2) == 20
    assert schema["inputs"] == list(INPUT_FIELDS)
    assert [item["name"] for item in schema["features"]] == list(FEATURE_NAMES_V2)
    assert len(MODEL_FEATURE_NAMES) == 13
    assert set(SCALE_HEAVY_FEATURES).isdisjoint(MODEL_FEATURE_NAMES)
    assert schema["future_model_input_fields"] == list(MODEL_FEATURE_NAMES)
    assert schema["qa_raw_only_fields"] == list(SCALE_HEAVY_FEATURES)
    assert all(item["role"] == ("MODEL_INPUT" if item["name"] in MODEL_FEATURE_NAMES
                                else "QA_RAW_ONLY") for item in schema["features"])
    assert HALF_LIFE_SECONDS == 3600 and EPS == 1e-12 and WARMUP_PAST_SAMPLES == 720
    assert INVALID_QUALITY_MASK == 507
    contract = micro_feature_contract_v2()
    assert contract["source_version"] == SOURCE_VERSION
    assert all(len(contract[name]) == 64 for name in (
        "schema_sha256", "definition_sha256", "implementation_sha256",
    ))
    source = row(4)
    result = MicroFeatureState().ingest(source)
    depth = source["bid_qty_mean_mean"] + source["ask_qty_mean_mean"]
    notional = source["aggressive_buy_notional"] + source["aggressive_sell_notional"]
    assert result["ofi_depth_norm"] == source["OFI_L1"] / (depth + EPS)
    assert result["log_l1_depth"] == math.log1p(depth)
    assert result["log_trade_notional"] == math.log1p(notional)
    assert result["trade_flow_imbalance"] == (
        source["aggressive_buy_notional"] - source["aggressive_sell_notional"]
    ) / (notional + EPS)
    assert result["vwap_offset_bps"] == (source["trade_vwap"] / source["mid_last"] - 1) * 10000
    assert result["quote_trade_ratio"] == math.log1p(source["quote_update_count"]) - math.log1p(
        source["agg_trade_count"]
    )
    assert result["spread_bps"] == source["spread_bps_mean"]
    assert result["spread_bps"] != source["spread_bps_last"]
    assert result["L1_imbalance_last"] == source["L1_imbalance_last"]
    assert result["realized_return_5s"] == source["realized_return"]


def test_batch_incremental_stream_match_exactly_with_interleaved_symbols():
    source = series()
    state = MicroFeatureState()
    actual = [state.ingest(item) for item in source]
    assert actual == build_micro_features_v2(source) == list(iter_micro_features_v2(iter(source)))
    assert any(result["feature_ready"] for result in actual)
    assert all(not result["feature_ready"] for result in actual[:2 * WARMUP_PAST_SAMPLES])


def test_future_edits_and_truncation_cannot_change_prefix():
    source = series()
    prefix = source[:2 * (WARMUP_PAST_SAMPLES + 2)]
    changed = copy.deepcopy(source)
    for item in changed[len(prefix):]:
        item["OFI_L1"] *= 1_000_000
        item["aggressive_buy_notional"] *= 10
    expected = build_micro_features_v2(prefix)
    assert build_micro_features_v2(source)[:len(prefix)] == expected
    assert build_micro_features_v2(changed)[:len(prefix)] == expected


def test_current_z_uses_only_past_moments_then_updates_state():
    state = MicroFeatureState()
    for index in range(WARMUP_PAST_SAMPLES):
        state.ingest(row(index))
    past = state.export_state()["symbols"]["BTCUSDT"]["ewm"]["ofi_depth_norm"]
    current = row(WARMUP_PAST_SAMPLES, OFI_L1=1_000_000)
    output = state.ingest(current)
    value = current["OFI_L1"] / (
        current["bid_qty_mean_mean"] + current["ask_qty_mean_mean"] + EPS
    )
    expected = (value - past["mean"]) / math.sqrt(past["variance"])
    assert output["ofi_depth_norm_z1h"] == expected
    assert output["scaler_prior_samples"]["ofi_depth_norm"] == WARMUP_PAST_SAMPLES
    after = state.export_state()["symbols"]["BTCUSDT"]["ewm"]["ofi_depth_norm"]
    alpha = -math.expm1(-math.log(2) * 5 / HALF_LIFE_SECONDS)
    delta = value - past["mean"]
    assert after["mean"] == past["mean"] + alpha * delta
    assert after["variance"] == (1 - alpha) * (past["variance"] + alpha * delta * delta)
    assert after["count"] == past["count"] + 1
    assert output["ofi_depth_norm_z1h"] != (value - after["mean"]) / math.sqrt(after["variance"])


def test_symbol_independence_and_interleaving_do_not_pool_raw_scale():
    source = series()
    combined = build_micro_features_v2(source)
    for symbol in ("BTCUSDT", "ETHUSDT"):
        isolated = build_micro_features_v2(item for item in source if item["symbol"] == symbol)
        assert [item for item in combined if item["symbol"] == symbol] == isolated
    changed = copy.deepcopy(source)
    for item in changed:
        if item["symbol"] == "ETHUSDT":
            item["OFI_L1"] += 100000
            item["aggressive_buy_notional"] *= 10
    actual = build_micro_features_v2(changed)
    assert [item for item in actual if item["symbol"] == "BTCUSDT"] == [
        item for item in combined if item["symbol"] == "BTCUSDT"
    ]


def test_exact_json_restart_in_native_state_file_and_snapshot_copy_isolation(tmp_path):
    assert str(tmp_path.resolve()).startswith("/home/xflops/coin-state/")
    source = series()
    state = MicroFeatureState()
    halfway = WARMUP_PAST_SAMPLES + 19  # between symbols, no shared paired state
    outputs = [state.ingest(item) for item in source[:halfway]]
    path = tmp_path / "a10-engineering-state.json"
    exported = state.export_state()
    path.write_text(json.dumps(exported, allow_nan=False))
    restored = MicroFeatureState.from_snapshot(json.loads(path.read_text()))
    assert restored.export_state() == exported
    exported["symbols"]["BTCUSDT"]["ewm"]["ofi_depth_norm"]["mean"] = 100000
    assert state.export_state() == restored.export_state()
    outputs += [restored.ingest(item) for item in source[halfway:]]
    assert outputs == build_micro_features_v2(source)


@pytest.mark.parametrize("change", [
    {"version": "microstructure_l1_v1"}, {"interval_s": 1}, {"symbol": "BNBUSDT"},
    {"open_us": BASE + 1}, {"close_us": BASE + INTERVAL_US - 1},
    {"available_us": BASE}, {"quality": 2048}, {"valid_seconds": 6},
    {"quote_update_count": True}, {"quote_update_count": 0.5},
    {"OFI_L1": float("nan")}, {"trade_vwap": float("inf")},
    {"spread_bps_mean": -1}, {"L1_imbalance_last": 1.1}, {"mid_last": 0},
    {"aggressive_buy_notional": -1}, {"session": ""},
])
def test_bad_source_is_rejected_without_state_change(change):
    state = MicroFeatureState()
    before = state.export_state()
    with pytest.raises(MicroFeatureInputError):
        state.ingest(row(0, **change))
    assert state.export_state() == before


def test_available_time_and_future_or_out_of_order_rejection_are_atomic():
    state = MicroFeatureState()
    source = row(0, available_us=BASE + INTERVAL_US + 10_000_000)
    before = state.export_state()
    with pytest.raises(MicroFeatureInputError):
        state.ingest(source, asof_us=source["available_us"] - 1)
    assert state.export_state() == before
    result = state.ingest(source, asof_us=source["available_us"])
    assert result["emitted_asof_us"] == result["available_us"] == source["available_us"]
    before = state.export_state()
    for bad in (source, row(1), row(0, session="s2")):
        with pytest.raises(MicroFeatureInputError):
            state.ingest(bad)
        assert state.export_state() == before
    # BTC's late availability does not make an independently available ETH row future.
    assert state.ingest(row(0, "ETHUSDT"))["symbol"] == "ETHUSDT"


@pytest.mark.parametrize("reason,change,next_index", [
    ("INVALID_QUALITY", {"quality": 16, "valid_seconds": 4}, 4),
    ("INCOMPLETE_BUCKET", {"known_seconds": 4, "valid_seconds": 4}, 4),
    ("NULL_REQUIRED_INPUT", {"mid_last": None}, 4),
    ("SESSION_CHANGE", {"session": "s2"}, 4),
    ("TIME_GAP", {}, 5),
])
def test_quality_gap_session_and_null_reset_only_affected_symbol(reason, change, next_index):
    state = MicroFeatureState()
    for index in range(4):
        for symbol in ("BTCUSDT", "ETHUSDT"):
            state.ingest(row(index, symbol))
    eth = state.export_state()["symbols"]["ETHUSDT"]
    output = state.ingest(row(next_index, **change))
    assert output["reset_reason"] == reason and not output["feature_ready"]
    assert state.export_state()["symbols"]["ETHUSDT"] == eth
    btc = state.export_state()["symbols"]["BTCUSDT"]
    if reason in {"TIME_GAP", "SESSION_CHANGE"}:
        assert btc["consecutive_valid_buckets"] == 1
        assert all(item["count"] == 1 for item in btc["ewm"].values())
    else:
        assert btc["consecutive_valid_buckets"] == 0 and btc["ewm"] == {}
        assert all(output[name] is None for name in FEATURE_NAMES_V2)
        resumed = state.ingest(row(next_index + 1))
        assert resumed["scaler_prior_samples"]["ofi_depth_norm"] == 0


def test_no_trade_null_is_not_zero_vwap_and_elapsed_time_controls_next_update():
    state = MicroFeatureState()
    state.ingest(row(0))
    initial = state.export_state()["symbols"]["BTCUSDT"]["ewm"]["vwap_offset_bps"]
    null_trade = dict(agg_trade_count=0, aggressive_buy_notional=0,
                      aggressive_sell_notional=0, trade_vwap=None, realized_return=None)
    no_trade = state.ingest(row(1, **null_trade))
    assert no_trade["vwap_offset_bps"] is None and no_trade["vwap_offset_bps_z1h"] is None
    assert no_trade["trade_flow_imbalance"] == no_trade["log_trade_notional"] == 0
    assert no_trade["realized_return_5s"] is None and no_trade["source_status"] == "VALID"
    assert state.export_state()["symbols"]["BTCUSDT"]["ewm"]["vwap_offset_bps"] == initial
    source = row(2)
    state.ingest(source)
    after = state.export_state()["symbols"]["BTCUSDT"]["ewm"]["vwap_offset_bps"]
    value = (source["trade_vwap"] / source["mid_last"] - 1) * 10000
    alpha = -math.expm1(-math.log(2) * 10 / HALF_LIFE_SECONDS)
    assert after["mean"] == initial["mean"] + alpha * (value - initial["mean"])
    assert after["count"] == 2


def test_zero_variance_constant_and_changed_current_have_explicit_distinct_status():
    state = MicroFeatureState()
    for index in range(WARMUP_PAST_SAMPLES):
        state.ingest(row(index, quote_update_count=10))
    constant = state.ingest(row(WARMUP_PAST_SAMPLES, quote_update_count=10))
    assert constant["log_quote_updates_z1h"] == 0
    assert constant["normalization_status"]["log_quote_updates"] == "ZERO_VARIANCE_CONSTANT"
    changed = state.ingest(row(WARMUP_PAST_SAMPLES + 1, quote_update_count=100))
    assert changed["log_quote_updates_z1h"] is None
    assert changed["normalization_status"]["log_quote_updates"] == "ZERO_VARIANCE_CHANGE"


@pytest.mark.parametrize("change", [
    {"agg_trade_count": 0}, {"trade_vwap": None},
    {"agg_trade_count": 0, "aggressive_buy_notional": 0, "aggressive_sell_notional": 0},
    {"bid_qty_mean_mean": 1e308, "ask_qty_mean_mean": 1e308},
    {"mid_last": 1e-308, "trade_vwap": 1e308},
    {"OFI_L1": 1e308},
])
def test_inconsistent_or_overflow_derived_transition_is_atomic(change):
    state = MicroFeatureState()
    state.ingest(row(0))
    before = state.export_state()
    with pytest.raises(MicroFeatureInputError):
        state.ingest(row(1, **change))
    assert state.export_state() == before


@pytest.mark.parametrize("part", ["sha256", "state_version", "contract", "symbols", "variance"])
def test_restart_rejects_checksum_version_symbols_and_impossible_moments(part):
    state = MicroFeatureState()
    state.ingest(row(0))
    bad = state.export_state()
    if part == "sha256":
        bad[part] = "0" * 64
    elif part == "state_version":
        bad[part] = "v1"
        resign(bad)
    elif part == "contract":
        bad[part]["source_version"] = "microstructure_l1_v1"
        resign(bad)
    elif part == "symbols":
        bad[part]["BNBUSDT"] = bad[part].pop("ETHUSDT")
        resign(bad)
    else:
        bad["symbols"]["BTCUSDT"]["ewm"]["ofi_depth_norm"]["variance"] = -1
        resign(bad)
    with pytest.raises(MicroFeatureInputError):
        MicroFeatureState.from_snapshot(bad)


def test_informational_quality_flags_do_not_invalidate_complete_finite_input():
    output = MicroFeatureState().ingest(row(0, quality=4 | 512 | 1024))
    assert output["source_status"] == "VALID"
    assert all(output[name] is not None for name in DERIVED_FEATURES)
    assert output["normalization_status"] == dict.fromkeys(SCALE_HEAVY_FEATURES, "WARMUP")


def test_missing_v2_terminal_columns_or_mean_field_alias_are_rejected():
    for name in ("spread_bps_last", "l1_total_depth_last", "bid_qty_mean_mean"):
        source = row(0)
        source.pop(name)
        source["bid_qty_mean"] = 3
        with pytest.raises(MicroFeatureInputError):
            MicroFeatureState().ingest(source)


def test_engineering_and_live_warmup_cannot_share_incremental_or_restored_symbol_state():
    state = MicroFeatureState()
    state.ingest(row(0))
    before = state.export_state()
    for instance in (state, MicroFeatureState.from_snapshot(json.loads(json.dumps(before)))):
        with pytest.raises(MicroFeatureInputError):
            instance.ingest(row(1, mode="live", session="live-new-session"))
        assert instance.export_state() == before
    assert state.ingest(row(0, "ETHUSDT", mode="live"))["mode"] == "live"
    with pytest.raises(MicroFeatureInputError):
        state.ingest(row(1, "ETHUSDT", mode="engineering"))


def test_real_a09_5s_aggregate_interface_and_tail_null_quality_boundary():
    from quant.microstructure_v2 import INVALID, VERSION, aggregate_seconds

    assert VERSION == SOURCE_VERSION and INVALID == INVALID_QUALITY_MASK
    seconds = []
    for index in range(5):
        seconds.append({
            "version": SOURCE_VERSION, "symbol": "BTCUSDT", "mode": "engineering",
            "session": "a09-interface", "open_us": BASE + index * 1_000_000,
            "close_us": BASE + (index + 1) * 1_000_000,
            "available_us": BASE + (index + 1) * 1_000_000 + 7,
            "quality": 0, "received_first_us": None, "received_last_us": None,
            "event_first_us": None, "event_last_us": None,
            "mid": 100 + index, "spread_bps": 2 + index / 100,
            "spread_bps_last": 3 + index / 100, "l1_total_depth_last": 30 + index,
            "bid_qty_mean": 10 + index, "ask_qty_mean": 20 + index,
            "L1_imbalance_mean": -0.2, "L1_imbalance_last": -0.3,
            "microprice_offset_bps_mean": 0.1, "quote_update_count": 2,
            "bid_price_change_count": 1, "ask_price_change_count": 1,
            "OFI_L1": index / 100, "agg_trade_count": 1,
            "aggressive_buy_notional": 50, "aggressive_sell_notional": 0,
            "trade_vwap": 100, "trade_flow_imbalance": 1, "realized_return_1s": 0.01,
        })
    aggregate = aggregate_seconds(seconds, 5)
    output = MicroFeatureState().ingest(aggregate)
    assert output["source_status"] == "VALID"
    assert output["spread_bps"] == sum(item["spread_bps"] for item in seconds) / 5
    assert output["log_quote_updates"] == math.log1p(10)
    assert output["log_trade_count"] == math.log1p(5)
    assert output["realized_return_5s"] == pytest.approx(0.05)
    assert output["available_us"] == seconds[-1]["available_us"]
    assert output["L1_imbalance_last"] == seconds[-1]["L1_imbalance_last"]
    for field in ("mid", "spread_bps_last", "l1_total_depth_last", "L1_imbalance_last"):
        seconds[-1][field] = None
    aggregate = aggregate_seconds(seconds, 5)
    assert aggregate["mid_last"] is None and aggregate["spread_bps_last"] is None
    rejected = MicroFeatureState().ingest(aggregate)
    assert rejected["source_status"] == "NULL_REQUIRED_INPUT"
    assert all(rejected[name] is None for name in FEATURE_NAMES_V2)
