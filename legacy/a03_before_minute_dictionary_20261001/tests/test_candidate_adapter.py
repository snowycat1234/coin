"""Synthetic integration only; no fitting, market evaluation, or live qualification."""

import copy
import hashlib
import importlib.util
import json
import math
import sqlite3
import tempfile
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import polars as pl
import pytest

from quant.alpha_rules_v2 import hysteresis_targets_v2
from quant.candidate_paper import (
    SCENARIOS,
    CandidateCollector,
    CandidatePaperEngine,
    _new_features,
    update_features,
)
from quant.candidate_storage import CHECKPOINT, FEATURE_SNAPSHOT, decode_record
from quant.candidate_strategy import (
    FrozenCandidateStrategy,
    Hourly40FeatureProvider,
    LegacyFeatureProvider,
    LegacyPredictorAdapter,
)
from quant.collector import Collector
from quant.execution_contract import ExecutionContractV2
from quant.features_v2 import FEATURE_NAMES_V2, feature_schema_v2
from quant.forward_report import evaluate_forward_snapshot
from quant.holdout import HoldoutDenied
from quant.paths import ROOT, STATE
from quant.predictor import RETURN_SEMANTICS, contracts_from_execution, load_frozen_predictor
from quant.research import FEATURE_NAMES, canonical_hash
from quant.shadow import DAY_MS, HOUR_MS, MINUTE_MS, Quote, ShadowConfig, read_forward_evidence

BASE = 1_735_689_600_000
END = BASE + 32 * DAY_MS + HOUR_MS
SYMBOLS = ("BTCUSDT", "ETHUSDT")
_FEATURE_SEEDS = {}
ARCHIVE = (
    ROOT
    / "legacy/a03_candidate_original"
    / ("e01f836c9640a9fafd648600024237c7cd26e32e048d0a7ff8632e5cb7d5de2a/candidate_paper.py")
)


def guard(**_):
    return {"status": "OK"}


def health(now):
    return {
        "state": "RUNNING",
        "healthy": True,
        "qualified_72h": True,
        "heartbeat_ms": now,
        "clock_offset_ms": 0,
        "unresolved_gaps": 0,
        "disk": {"status": "OK"},
    }


def bindings():
    execution = ExecutionContractV2()
    cost, risk = contracts_from_execution(execution)
    return {"execution_contract": execution, "cost_contract": cost, "risk_contract": risk}


class StubPredictor:
    """Explicit engineering branch oracle, never native/trained/alpha evidence."""

    model_type, schema_version = "engineering_stub", "stub_v1"
    feature_names, decision_interval, prediction_horizon = FEATURE_NAMES_V2, "1h", "4h"
    prediction_semantics = RETURN_SEMANTICS

    def __init__(self, value=0.01):
        self.value, self.calls = value, []
        execution = ExecutionContractV2()
        cost, risk = contracts_from_execution(execution)
        schema = feature_schema_v2()
        self.manifest = {
            "model_sha256": hashlib.sha256(b"no_fit_stub").hexdigest(),
            "feature_schema": {**schema, "sha256": canonical_hash(schema)},
            "execution_contract": {"version": execution.version, "sha256": execution.digest()},
            "cost_contract": {**cost, "sha256": canonical_hash(cost)},
            "risk_contract": {**risk, "sha256": canonical_hash(risk)},
            "qualification": "engineering_stub_no_training_provenance",
        }
        self.release_sha256 = canonical_hash(self.manifest)

    def predict(self, values):
        assert set(values) == set(FEATURE_NAMES_V2) | {
            "symbol",
            "interval",
            "available_us",
            "received_us",
        }
        self.calls.append(copy.deepcopy(values))
        return {
            "expected_return": self.value,
            "confidence": None,
            "target_weight": None,
            "prediction_semantics": self.prediction_semantics,
            "release_sha256": self.release_sha256,
        }


def minute(symbol, opened, index=0):
    price = 100 + 0.03 * math.sin(index / 70) + 0.00002 * index
    if symbol == "ETHUSDT":
        price = 100 + 0.025 * math.cos(index / 90) + 0.00002 * index
    return {
        "symbol": symbol,
        "open_us": opened * 1000,
        "close_us": (opened + MINUTE_MS) * 1000,
        "open": price - 0.01,
        "high": price + 0.03,
        "low": price - 0.02,
        "close": price,
        "volume": 100000 + index % 100,
        "quote_volume": 10_000_000.0,
        "taker_buy_base": 50000.0,
        "taker_buy_quote": 5_000_000.0,
        "source": "websocket",
    }


def seed_features(obj, hours=99):
    """Declared synthetic state seed, zero financial or collection credit."""
    first = END - (hours + 1) * HOUR_MS
    if hours not in _FEATURE_SEEDS:
        state = obj.feature_provider.new_state()
        for index in range(hours * 60):
            opened = first + index * MINUTE_MS
            for symbol in SYMBOLS:
                row = minute(symbol, opened, index)
                row.update(
                    received_us=(opened + MINUTE_MS + 100) * 1000,
                    available_us=(opened + MINUTE_MS + 100) * 1000,
                    source="synthetic",
                )
                obj.feature_provider.apply_minute(state, row)
        _FEATURE_SEEDS[hours] = state
    obj.state["features"] = copy.deepcopy(_FEATURE_SEEDS[hours])
    with obj.db:
        obj._append(
            END - HOUR_MS - 500,
            "engineering_seed",
            {"source": "synthetic", "historical_feature_hours": hours, "qualification_seconds": 0},
            "engineering_seed",
        )
        obj._snapshot_features(END - HOUR_MS - 500, SYMBOLS[0])
        obj._checkpoint(END - HOUR_MS - 500)


@pytest.fixture(scope="module")
def source():
    STATE.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="a03-adapter-source-", dir=STATE) as folder:
        path = Path(folder) / "source.sqlite3"
        collector = Collector(path, disk_check=guard)
        for symbol in SYMBOLS:

            def rows(symbol=symbol):
                for index in range(32 * 1440 + 120):
                    opened = BASE + index * MINUTE_MS
                    price = str(100 + 0.05 * math.sin(index / 1440))
                    yield (
                        symbol,
                        opened,
                        opened + MINUTE_MS - 1,
                        price,
                        price,
                        price,
                        price,
                        "100000",
                        "10000000",
                        100,
                        opened + MINUTE_MS,
                        opened + MINUTE_MS + 100,
                        "websocket",
                        opened + MINUTE_MS + 100,
                        1,
                    )

            collector.db.executemany(
                "INSERT INTO closed_bars VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", rows()
            )
        collector.db.commit()
        collector.db.execute(
            "CREATE INDEX fixture_closed_received ON closed_bars(symbol,source,received_ms)"
        )
        collector.db.commit()
        collector.close()
        yield path


@pytest.fixture
def engine(source):
    with tempfile.TemporaryDirectory(prefix="a03-adapter-case-", dir=STATE) as folder:
        obj = CandidatePaperEngine(
            source,
            Path(folder) / "journal.sqlite3",
            predictor=StubPredictor(),
            decision_policy="A",
            config=ShadowConfig(mode="engineering_simulation"),
            started_ms=END - HOUR_MS - 500,
            disk_check=guard,
        )
        yield obj
        obj.close()


def finish_hour(obj, *, omit=None):
    for index in range(60):
        opened = END - HOUR_MS + index * MINUTE_MS
        for symbol in SYMBOLS:
            if omit == (symbol, index):
                continue
            obj.ingest_bar(minute(symbol, opened, index + 5940), opened + MINUTE_MS + 100)


def payloads(obj, kind):
    rows = [
        json.loads(row[0])
        for row in obj.db.execute("SELECT payload FROM records WHERE kind=? ORDER BY seq", (kind,))
    ]
    codec_kind = {"checkpoint": CHECKPOINT, "feature_provider_snapshot": FEATURE_SNAPSHOT}.get(kind)
    return [decode_record(row, codec_kind) for row in rows] if codec_kind else rows


def test_lossless_checkpoint_and_joint_snapshot_recovery_preserves_newer_heartbeat(engine):
    seed_features(engine)
    finish_hour(engine)
    with engine.db:
        engine._checkpoint(END + 100)
    expected = copy.deepcopy(engine.state)
    checkpoint = json.loads(
        engine.db.execute(
            "SELECT payload FROM records WHERE kind='checkpoint' ORDER BY seq DESC LIMIT 1"
        ).fetchone()[0]
    )
    assert checkpoint["storage_kind"] == CHECKPOINT
    assert "accounts" not in checkpoint and "candidate_binding_sha256" not in checkpoint
    restored_financial = decode_record(checkpoint, CHECKPOINT)
    assert restored_financial == {
        key: value
        for key, value in expected.items()
        if key not in {"features", "candidate_binding"}
    }
    feature_anchor = json.loads(
        engine.db.execute(
            "SELECT payload FROM records WHERE kind='feature_provider_snapshot' "
            "ORDER BY seq DESC LIMIT 1"
        ).fetchone()[0]
    )
    assert feature_anchor["storage_kind"] == FEATURE_SNAPSHOT
    assert (
        engine.feature_provider.restore(decode_record(feature_anchor, FEATURE_SNAPSHOT))
        == expected["features"]
    )
    # This actual journal heartbeat follows the financial checkpoint. Parent
    # recovery must retain its observed counters and clear healthy restart credit.
    heartbeat_ms = END + 10_000
    with engine.db:
        engine._append(
            heartbeat_ms,
            "heartbeat",
            {
                "observed_seconds": 17.25,
                "healthy_seconds": 8.125,
            },
            "engineering_codec_newer_heartbeat",
        )
    seq, head, path = engine.seq, engine.head, engine.path
    engine.close()
    restored = CandidatePaperEngine(
        engine.collector_path,
        path,
        predictor=StubPredictor(),
        decision_policy="A",
        config=ShadowConfig(mode="engineering_simulation"),
        disk_check=guard,
    )
    try:
        assert restored.seq == seq and restored.head == head
        assert restored.state["features"] == expected["features"]
        assert restored.state["accounts"] == expected["accounts"]
        assert restored.state["account_controls"] == expected["account_controls"]
        assert restored.state["last_tick_ms"] == heartbeat_ms
        assert restored.state["observed_seconds"] == 17.25
        assert restored.state["healthy_seconds"] == 8.125
        assert restored.state["last_healthy"] is False
        assert restored._heartbeat_credit == 0
        assert restored.status()["actual_qualification_days"] == 0
    finally:
        restored.close()


def test_authenticated_journal_with_corrupt_compressed_checkpoint_is_refused(engine):
    checkpoint = json.loads(
        engine.db.execute(
            "SELECT payload FROM records WHERE kind='checkpoint' ORDER BY seq DESC LIMIT 1"
        ).fetchone()[0]
    )
    checkpoint["raw_sha256"] = "0" * 64
    with engine.db:
        engine._append(END, "checkpoint", checkpoint, "engineering_corrupt_compressed_checkpoint")
    path, source, seq, head = engine.path, engine.collector_path, engine.seq, engine.head
    engine.close()
    before = hashlib.sha256(path.read_bytes()).hexdigest()
    with pytest.raises(HoldoutDenied, match="完整性"):
        CandidatePaperEngine(
            source,
            path,
            predictor=StubPredictor(),
            decision_policy="A",
            config=ShadowConfig(mode="engineering_simulation"),
            disk_check=guard,
        )
    assert hashlib.sha256(path.read_bytes()).hexdigest() == before
    evidence = read_forward_evidence(path, include_records=False)
    assert evidence["seq"] == seq and evidence["head_hash"] == head


def test_storage_helper_source_change_is_refused_before_new_journal_records(engine, monkeypatch):
    seq, head = engine.seq, engine.head
    monkeypatch.setattr("quant.candidate_paper.source_sha", lambda _name: "0" * 64)
    with pytest.raises(HoldoutDenied, match="冻结"):
        engine.process_tick(END, health(END), [Quote(s, 100, 100.02, END, 1) for s in SYMBOLS])
    assert engine.seq == seq and engine.head == head


@pytest.mark.parametrize("interval", ["15m", "1h"])
def test_archived_nonzero_logistic_and_aggregation_bitwise_compatibility(interval):
    spec = importlib.util.spec_from_file_location("quant._archived_candidate", ARCHIVE)
    archived = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(archived)
    provider = LegacyFeatureProvider(interval, _new_features, update_features)
    actual = provider.new_state()
    legacy = SimpleNamespace(
        state={"features": {s: archived._new_features() for s in SYMBOLS}},
        model={"interval": interval},
    )
    width = 15 if interval == "15m" else 60
    for index in range(101 * width):
        row = minute("BTCUSDT", BASE + index * MINUTE_MS, index)
        row.update(received_us=(BASE + (index + 1) * MINUTE_MS + 100) * 1000)
        reference, boundary = archived.CandidatePaperEngine._apply_feature_minute(legacy, row)
        outputs, actual_boundary = provider.apply_minute(actual, row)
        assert actual_boundary == boundary
        if reference:
            assert outputs == [reference]
    model = {
        "interval": interval,
        "configuration": {"threshold": 0.55},
        "scaler_mean": [i / 10 for i in range(10)],
        "scaler_scale": [1 + i / 20 for i in range(10)],
        "coefficients": [(-1) ** i * (i + 1) / 10 for i in range(10)],
        "intercept": 0.123,
    }
    vector = np.array([reference[name] for name in FEATURE_NAMES])
    score = float(
        ((vector - np.array(model["scaler_mean"])) / np.array(model["scaler_scale"]))
        @ np.array(model["coefficients"])
        + model["intercept"]
    )
    expected = float(1 / (1 + math.exp(-float(np.clip(score, -700, 700)))))
    output = LegacyPredictorAdapter(model).predict(reference)
    assert output["confidence"] == expected
    assert output["target_weight"] == (0.30 if expected >= 0.55 else 0.0)


@pytest.mark.parametrize("threshold", ["A", "B", "C"])
def test_incremental_fixed_hysteresis_exactly_matches_accepted_batch(threshold):
    strategy = FrozenCandidateStrategy(
        StubPredictor(), Hourly40FeatureProvider(), threshold=threshold
    )
    state, rows, actual = strategy.new_policy_state(), [], []
    for index, value in enumerate(
        [0.0075, 0.009, -0.01, 0.0015, None, 0.008, -0.01, -0.01, 0.0015]
    ):
        end = END * 1000 + index * HOUR_MS * 1000
        if index >= 7:
            end += HOUR_MS * 1000  # disconnected decision path
        outputs = {s: {"expected_return": value} if value is not None else None for s in SYMBOLS}
        raw, policy = strategy.targets(outputs, end, state)
        for symbol in SYMBOLS:
            rows.append({"symbol": symbol, "available_us": end, "expected_return": value})
            actual.append(
                {
                    "symbol": symbol,
                    "available_us": end,
                    "target_weight": raw[symbol],
                    **policy[symbol],
                }
            )
    expected = hysteresis_targets_v2(pl.DataFrame(rows), threshold).select(
        "symbol", "available_us", "target_weight", "minimum_hold_minutes", "risk_forced_exit"
    )
    assert (
        pl.DataFrame(actual)
        .select(expected.columns)
        .sort("available_us", "symbol")
        .equals(expected)
    )


def test_timely_disordered_quotes_do_not_consume_unpaired_hour(engine):
    seed_features(engine)
    for index in range(59):
        for symbol in SYMBOLS:
            engine.ingest_bar(
                minute(symbol, END - HOUR_MS + index * MINUTE_MS, 5940 + index),
                END - HOUR_MS + (index + 1) * MINUTE_MS + 100,
            )
    engine.process_tick(
        END + 10, health(END + 10), [Quote(s, 100, 100.02, END + 10, 1) for s in SYMBOLS]
    )
    assert engine.state["last_candidate_end"] is None
    engine.ingest_bar(minute("ETHUSDT", END - MINUTE_MS, 5999), END + 100)
    engine.process_tick(
        END + 200, health(END + 200), [Quote(s, 100, 100.02, END + 200, 2) for s in SYMBOLS]
    )
    assert engine.state["last_candidate_end"] is None
    engine.ingest_bar(minute("BTCUSDT", END - MINUTE_MS, 5999), END + 400)
    engine.process_tick(
        END + 401, health(END + 401), [Quote(s, 100, 100.02, END + 401, 3) for s in SYMBOLS]
    )
    assert engine.state["last_candidate_end"] == END
    assert len(engine.strategy.predictor.calls) == 2
    assert all(
        order["not_before_ms"] == END + MINUTE_MS
        for s in SCENARIOS
        if s != "B2"
        for order in engine.state["accounts"][s]["pending"].values()
    )


def test_expired_missing_pair_emits_now_risk_flat_not_old_signal(engine):
    seed_features(engine)
    finish_hour(engine, omit=("ETHUSDT", 59))
    engine._decision(END + 1000)
    assert engine.state["last_candidate_end"] is None
    assert engine._decision(END + 15001)
    assert not engine.strategy.predictor.calls
    decisions = [r for r in payloads(engine, "decision") if r["scenario"] != "B2"]
    assert all(r["risk_missing_or_late"] for r in decisions)
    orders = [
        r
        for r in payloads(engine, "order")
        if r.get("account") in {"candidate", "fee_x2", "slippage_x2"}
    ]
    assert all(
        r["risk_forced_exit"] and r["target_weight"] == 0 and r["not_before_ms"] > END + 15001
        for r in orders
    )


def test_confirmed_incomplete_hour_forces_flat_without_wait_or_prediction(engine):
    seed_features(engine)
    finish_hour(engine, omit=("ETHUSDT", 20))
    assert engine._decision(END + 100)
    assert not engine.strategy.predictor.calls
    assert all(
        order["risk_forced_exit"]
        for scenario in SCENARIOS
        if scenario != "B2"
        for order in engine.state["accounts"][scenario]["pending"].values()
    )


def test_joint_anchor_pending_pair_incremental_restart_exact_and_zero_credit(engine):
    seed_features(engine)
    finish_hour(engine, omit=("ETHUSDT", 59))
    # Leave one coin's final minute in the increment after a joint snapshot/financial checkpoint.
    with engine.db:
        engine._checkpoint(END + 100)
    engine.ingest_bar(minute("ETHUSDT", END - MINUTE_MS, 5999), END + 200)
    # Non-boundary evidence is genuinely after the latest joint anchor; no new
    # feature or financial snapshot is written. Restore must execute the minute tail.
    for index in range(3):
        for symbol in SYMBOLS:
            engine.ingest_bar(
                minute(symbol, END + index * MINUTE_MS, 6000 + index),
                END + (index + 1) * MINUTE_MS + 100,
            )
    expected = copy.deepcopy(engine.state)
    seq, path = engine.seq, engine.path
    engine.close()
    restored = CandidatePaperEngine(
        engine.collector_path,
        path,
        predictor=StubPredictor(),
        decision_policy="A",
        config=ShadowConfig(mode="engineering_simulation"),
        disk_check=guard,
    )
    try:
        assert restored.state["features"] == expected["features"]
        assert restored.state["accounts"] == expected["accounts"]
        assert restored.state["account_controls"] == expected["account_controls"]
        assert restored.seq == seq
        assert restored.head == engine.head
        assert not restored.ingest_bar(
            minute("ETHUSDT", END + 2 * MINUTE_MS, 6002), END + 3 * MINUTE_MS + 200
        )
        assert restored.seq == seq
        assert restored.status()["actual_qualification_days"] == 0
    finally:
        restored.close()


@pytest.mark.parametrize(
    "mutation",
    ["strategy", "predictor", "provider", "threshold", "model", "interval", "model_sha", "binding"],
)
def test_runtime_rebinding_refused_before_any_append(engine, mutation):
    previous = engine.seq
    if mutation == "strategy":
        engine.strategy = FrozenCandidateStrategy(
            StubPredictor(), Hourly40FeatureProvider(), threshold="A"
        )
    elif mutation == "predictor":
        engine.strategy.predictor = StubPredictor()
    elif mutation == "provider":
        engine.feature_provider = Hourly40FeatureProvider()
    elif mutation == "threshold":
        engine.strategy.threshold = "B"
    elif mutation == "model":
        engine.model["interval"] = "15m"
    elif mutation == "interval":
        engine.interval = "15m"
    elif mutation == "model_sha":
        engine.model_sha = "0" * 64
    else:
        engine.binding["model_sha256"] = "0" * 64
    with pytest.raises(HoldoutDenied):
        engine.process_tick(END, health(END), [])
    assert engine.seq == previous


def test_generic_live_admission_denied_before_database_or_source_io(tmp_path):
    path = tmp_path / "must_not_exist.sqlite3"
    with pytest.raises(HoldoutDenied, match="STOP_v2"):
        CandidatePaperEngine(
            tmp_path / "absent_source.sqlite3", path, predictor=StubPredictor(), decision_policy="A"
        )
    assert not path.exists()


@pytest.mark.parametrize("bad", [None, "not_numeric", float("nan"), True])
def test_output_missing_return_riskflat_or_malformed_denied(engine, bad):
    seed_features(engine)
    finish_hour(engine)
    engine.strategy.predictor.value = bad
    if bad is None:
        engine._decision(END + 100)
        assert all(
            r["risk_forced_exit"] and r["target_weight"] == 0
            for s in SCENARIOS
            if s != "B2"
            for r in engine.state["accounts"][s]["pending"].values()
        )
    else:
        with pytest.raises(HoldoutDenied, match="invalid scalar"):
            engine._decision(END + 100)


def test_account_holding_alias_exception_and_partial_fill_independence(engine):
    # Give each cost account a different first executable arrival; B2 remains hold=0.
    with sqlite3.connect(engine.collector_path) as writer:
        writer.execute("UPDATE closed_bars SET quote_volume='100000' WHERE open_ms>=?", (END,))
    for index, scenario in enumerate(SCENARIOS):
        account = engine.state["accounts"][scenario]
        account["pending"] = {
            "BTCUSDT": {
                "order_id": scenario + ":first",
                "account": scenario,
                "symbol": "BTCUSDT",
                "target_weight": 0.30,
                "minimum_hold_minutes": 0 if scenario == "B2" else 120,
                "risk_forced_exit": False,
                "not_before_ms": END + (index + 1) * MINUTE_MS,
                "signal_received_ms": END,
                "decision_us": END * 1000,
                "expires_ms": END + 10 * MINUTE_MS,
            }
        }
        engine.state["account_controls"][scenario]["alpha_holding"]["BTCUSDT"] = {
            "last_raw": 0.3,
            "awaiting_first_fill": True,
            "first_fill_ms": 0,
        }
    for index in range(1, 5):
        now = END + index * MINUTE_MS + 200
        engine._fill(now, {s: Quote(s, 100, 100.02, now, index) for s in SYMBOLS})
    with sqlite3.connect(engine.collector_path) as writer:
        writer.execute("UPDATE closed_bars SET quote_volume='10000000' WHERE open_ms>=?", (END,))
    controls = engine.state["account_controls"]
    assert all(0 < engine.state["accounts"][s]["positions"]["BTCUSDT"] < 5 for s in SCENARIOS)
    assert engine.state["accounts"]["candidate"]["positions"]["BTCUSDT"] > 2
    assert [
        controls[s]["alpha_holding"]["BTCUSDT"]["first_fill_ms"]
        for s in ("candidate", "fee_x2", "slippage_x2")
    ] == [END + MINUTE_MS + 200, END + 3 * MINUTE_MS + 200, END + 4 * MINUTE_MS + 200]
    prior = engine.state.get("alpha_holding")
    config, b2 = engine.config, engine.state["accounts"]["B2"]
    with pytest.raises(ValueError):
        with engine._account("fee_x2"):
            raise ValueError("synthetic failure")
    assert engine.config == config and engine.state["accounts"]["B2"] is b2
    assert engine.state.get("alpha_holding") is prior and engine._active_account is None
    with engine.db:
        engine._checkpoint(END + 4 * MINUTE_MS + 200)
    expected, path, seq = copy.deepcopy(engine.state), engine.path, engine.seq
    checkpoints = payloads(engine, "checkpoint")
    assert "candidate_binding" not in checkpoints[-1]
    assert checkpoints[-1]["candidate_binding_sha256"] == canonical_hash(engine.binding)
    engine.close()
    restored = CandidatePaperEngine(
        engine.collector_path,
        path,
        predictor=StubPredictor(),
        decision_policy="A",
        config=ShadowConfig(mode="engineering_simulation"),
        disk_check=guard,
    )
    try:
        assert restored.state == expected
        assert restored.state["accounts"] == expected["accounts"]
        assert restored.state["account_controls"] == expected["account_controls"]
        assert restored.seq == seq and restored.head == engine.head
    finally:
        restored.close()


def pending(obj, scenario, *, weight=0.3, now=END, risk=False):
    obj.state["accounts"][scenario]["pending"] = {
        "BTCUSDT": {
            "order_id": f"{scenario}:unit:{now}",
            "account": scenario,
            "symbol": "BTCUSDT",
            "target_weight": weight,
            "minimum_hold_minutes": 120,
            "risk_forced_exit": risk,
            **obj.execution_contract.order_times_ms(now * 1000, now + 100),
        }
    }


def test_hold_blocks_alpha_exit_but_risk_reduction_and_dust_reentry_reset_anchor(engine):
    controls = engine.state["account_controls"]["candidate"]
    controls["alpha_holding"]["BTCUSDT"] = {
        "last_raw": 0.3,
        "awaiting_first_fill": True,
        "first_fill_ms": 0,
    }
    pending(engine, "candidate")
    first = END + MINUTE_MS + 200
    engine._fill(first, {s: Quote(s, 100, 100.02, first, 1) for s in SYMBOLS})
    before = engine.state["accounts"]["candidate"]["positions"]["BTCUSDT"]
    pending(engine, "candidate", weight=0, now=END + MINUTE_MS)
    now = END + 2 * MINUTE_MS + 200
    engine._fill(now, {s: Quote(s, 100, 100.02, now, 2) for s in SYMBOLS})
    assert engine.state["accounts"]["candidate"]["positions"]["BTCUSDT"] == before
    assert any(r["status"] == "MINIMUM_HOLD" for r in payloads(engine, "order_event"))
    pending(engine, "candidate", weight=0.01, now=END + 2 * MINUTE_MS, risk=True)
    now = END + 3 * MINUTE_MS + 200
    engine._fill(now, {s: Quote(s, 100, 100.02, now, 3) for s in SYMBOLS})
    assert engine.state["accounts"]["candidate"]["positions"]["BTCUSDT"] < before / 5
    account = engine.state["accounts"]["candidate"]
    account["positions"]["BTCUSDT"] = 0.001  # explicitly injected remaining financial dust
    account["cycles"]["BTCUSDT"]["entry_ms"] = END - 10 * HOUR_MS
    controls["alpha_holding"]["BTCUSDT"].update(last_raw=0.3, awaiting_first_fill=True)
    pending(engine, "candidate", now=END + 3 * MINUTE_MS)
    now = END + 4 * MINUTE_MS + 200
    engine._fill(now, {s: Quote(s, 100, 100.02, now, 4) for s in SYMBOLS})
    assert controls["alpha_holding"]["BTCUSDT"]["first_fill_ms"] == now
    assert account["cycles"]["BTCUSDT"]["entry_ms"] == END - 10 * HOUR_MS
    assert not engine.state["account_controls"]["fee_x2"]["alpha_holding"]


def test_financial_transaction_failure_restores_feature_reference_and_all_aliases(
    engine, monkeypatch
):
    now = END + 200
    engine.process_tick(now, health(now), [Quote(s, 100, 100.02, now, 1) for s in SYMBOLS])
    engine.state["last_candidate_end"] = END
    engine.state["last_signal_hour"] = END
    pending(engine, "candidate")
    before, seq, head, config = copy.deepcopy(engine.state), engine.seq, engine.head, engine.config
    original = engine._append

    def fail(at, kind, payload, key):
        if kind == "position" and engine._active_account == "candidate":
            raise RuntimeError("synthetic middle transaction failure")
        return original(at, kind, payload, key)

    monkeypatch.setattr(engine, "_append", fail)
    now = END + MINUTE_MS + 200
    quotes = [Quote(s, 100, 100.02, now, 2) for s in SYMBOLS]
    with pytest.raises(RuntimeError, match="middle transaction"):
        engine.process_tick(now, health(now), quotes)
    assert engine.state == before and engine.seq == seq and engine.head == head
    assert engine.config == config and engine._active_account is None
    assert engine.db.execute("SELECT MAX(seq) FROM records").fetchone()[0] == seq
    monkeypatch.setattr(engine, "_append", original)
    engine.process_tick(now, health(now), quotes)
    assert len([r for r in payloads(engine, "fill") if r["scenario"] == "candidate"]) == 1
    seq = engine.seq
    engine.process_tick(now, health(now), quotes)
    assert engine.seq == seq


def test_actual_threshold_numbers_are_frozen_not_only_policy_letter(engine, monkeypatch):
    from quant.alpha_rules_v2 import THRESHOLDS

    monkeypatch.setitem(THRESHOLDS, "A", (1.0, -100.0))
    before = engine.seq
    with pytest.raises(HoldoutDenied, match="policy参数"):
        engine.process_tick(END, health(END), [])
    assert engine.seq == before


@pytest.mark.parametrize("marker", ["public_contract", "state"])
def test_renamed_real_pipeline_schema_refused_readonly_before_lock_or_index(marker):
    with tempfile.TemporaryDirectory(prefix="a03-foreign-source-", dir=STATE) as folder:
        path = Path(folder) / "innocent_name.sqlite3"
        with sqlite3.connect(path) as db:
            db.execute(f"CREATE TABLE {marker}(id INTEGER PRIMARY KEY,value TEXT)")
        before = hashlib.sha256(path.read_bytes()).hexdigest()
        with pytest.raises(HoldoutDenied, match="来源绑定"):
            CandidateCollector(path, candidate_factory=lambda *_: None, disk_check=guard)
        assert hashlib.sha256(path.read_bytes()).hexdigest() == before
        assert not path.with_suffix(".lock").exists()


@pytest.mark.parametrize("name", ["collector_public_v3.sqlite3", "microstructure.sqlite3"])
def test_actual_real_source_names_refused_before_any_io(name):
    with tempfile.TemporaryDirectory(prefix="a03-protected-name-", dir=STATE) as folder:
        path = Path(folder) / name
        with pytest.raises(HoldoutDenied, match="参考库"):
            CandidateCollector(path, candidate_factory=lambda *_: None, disk_check=guard)
        assert not path.exists() and not path.with_suffix(".lock").exists()


def test_corrupt_joint_snapshot_is_explicitly_refused(engine):
    snapshot = engine.feature_provider.snapshot(engine.state["features"])
    snapshot["state"]["BTCUSDT"]["last_minute_open_us"] = 10
    with pytest.raises(HoldoutDenied, match="digest"):
        engine.feature_provider.restore(snapshot)


def test_wrong_immutable_binding_reference_refused_without_append_or_account_loss(engine):
    financial = {
        key: value
        for key, value in engine.state.items()
        if key not in {"features", "candidate_binding"}
    }
    financial["candidate_binding_sha256"] = "0" * 64
    accounts = copy.deepcopy(engine.state["accounts"])
    with engine.db:
        engine._append(END, "checkpoint", financial, "engineering_bad_binding_reference")
    path, source, seq = engine.path, engine.collector_path, engine.seq
    engine.close()
    before = hashlib.sha256(path.read_bytes()).hexdigest()
    with pytest.raises(HoldoutDenied, match="immutable binding"):
        CandidatePaperEngine(
            source,
            path,
            predictor=StubPredictor(),
            decision_policy="A",
            config=ShadowConfig(mode="engineering_simulation"),
            disk_check=guard,
        )
    assert hashlib.sha256(path.read_bytes()).hexdigest() == before
    with sqlite3.connect(path) as db:
        assert db.execute("SELECT MAX(seq) FROM records").fetchone()[0] == seq
        saved = json.loads(
            db.execute(
                "SELECT payload FROM records WHERE event_key=?",
                ("engineering_bad_binding_reference",),
            ).fetchone()[0]
        )
        assert saved["accounts"] == accounts


def test_model_feature_definition_binding_rejects_same_names_changed_formula(source):
    predictor = StubPredictor()
    predictor.manifest["feature_schema"]["features"][0]["definition"] = "noncausal future"
    with tempfile.TemporaryDirectory(prefix="a03-definition-", dir=STATE) as folder:
        path = Path(folder) / "never.sqlite3"
        with pytest.raises(HoldoutDenied, match="definitions mismatch"):
            CandidatePaperEngine(
                source,
                path,
                predictor=predictor,
                decision_policy="A",
                config=ShadowConfig(mode="engineering_simulation"),
                disk_check=guard,
            )
        assert not path.exists()


@pytest.mark.parametrize("kind", ["LGB_A", "XGB_A"])
def test_existing_native_40feature_WS_collector_generic_engine_without_fit(source, kind):
    folder = ROOT / "reports/generated/A05_NONLINEAR_V2" / kind / "fold0"
    model = folder / ("model.txt" if kind == "LGB_A" else "model.json")
    predictor = load_frozen_predictor(model, folder / "manifest.json", **bindings())
    before = hashlib.sha256(model.read_bytes()).hexdigest()
    with tempfile.TemporaryDirectory(prefix="a03-native-wire-", dir=STATE) as directory:
        own_source = Path(directory) / "source.sqlite3"
        with sqlite3.connect(source) as original, sqlite3.connect(own_source) as destination:
            original.backup(destination)
            destination.execute("DELETE FROM closed_bars WHERE open_ms>=?", (END - HOUR_MS,))
            destination.commit()
        obj = CandidatePaperEngine(
            own_source,
            Path(directory) / "journal.sqlite3",
            predictor=predictor,
            decision_policy="A",
            config=ShadowConfig(mode="engineering_simulation"),
            started_ms=END - HOUR_MS - 500,
            disk_check=guard,
        )
        seed_features(obj)
        collector = CandidateCollector(own_source, candidate=obj, disk_check=guard)
        collector.health_snapshot = lambda at: {
            **health(at),
            "connected": True,
            "live_session": True,
            "qualification": {"qualified_72h": True},
        }
        try:
            for index in range(60):
                opened = END - HOUR_MS + index * MINUTE_MS
                now = opened + MINUTE_MS + 100
                for symbol in SYMBOLS:
                    collector.latest_quotes[symbol] = {
                        "symbol": symbol,
                        "bid": 100.0,
                        "ask": 100.02,
                        "received_ms": now,
                        "update_id": index + 1,
                    }
                for symbol in SYMBOLS:
                    raw = minute(symbol, opened, 5940 + index)
                    k = {
                        "s": symbol,
                        "t": opened,
                        "T": opened + MINUTE_MS - 1,
                        "i": "1m",
                        "x": True,
                        "n": 100,
                        **{
                            dest: str(raw[src])
                            for dest, src in (
                                ("o", "open"),
                                ("h", "high"),
                                ("l", "low"),
                                ("c", "close"),
                                ("v", "volume"),
                                ("q", "quote_volume"),
                                ("V", "taker_buy_base"),
                                ("Q", "taker_buy_quote"),
                            )
                        },
                    }
                    collector.handle_message({"e": "kline", "E": now, "s": symbol, "k": k}, now)
            obj.process_tick(
                END + 200,
                health(END + 200),
                [Quote(s, 100, 100.02, END + 200, 100) for s in SYMBOLS],
            )
            decisions = [
                r
                for r in payloads(obj, "decision")
                if r["scenario"] != "B2" and r["bar_end_ms"] == END
            ]
            assert {r["scenario"] for r in decisions} == {"candidate", "fee_x2", "slippage_x2"}
            assert len(payloads(obj, "feature")) == 2
            for symbol in SYMBOLS:
                feature = obj.feature_provider.latest(obj.state["features"])[symbol]
                vector = {k: feature[k] for k in FEATURE_NAMES_V2}
                expected = predictor.predict(vector)
                assert decisions[0]["predictions"][symbol] == expected
                values = np.array([[vector[k] for k in FEATURE_NAMES_V2]], dtype=np.float64)
                if kind == "LGB_A":
                    import lightgbm as lgb

                    native = lgb.Booster(model_file=str(model))
                    oracle = float(native.predict(values, num_threads=1)[0])
                else:
                    import xgboost as xgb

                    native = xgb.Booster(params={"device": "cpu", "nthread": 1})
                    native.load_model(str(model))
                    native.set_param({"device": "cpu", "nthread": 1})
                    oracle = float(
                        native.predict(
                            xgb.DMatrix(values, feature_names=list(FEATURE_NAMES_V2), nthread=1)
                        )[0]
                    )
                assert expected["expected_return"] == pytest.approx(oracle, abs=1e-12, rel=1e-10)
                assert feature["received_us"] == (END + 100) * 1000
            now = END + MINUTE_MS + 100
            for symbol in SYMBOLS:
                collector.latest_quotes[symbol]["received_ms"] = now - 50
            for symbol in SYMBOLS:
                k = {
                    "s": symbol,
                    "t": END,
                    "T": END + MINUTE_MS - 1,
                    "i": "1m",
                    "x": True,
                    "n": 100,
                    "o": "100",
                    "h": "101",
                    "l": "99",
                    "c": "100",
                    "v": "100000",
                    "q": "10000000",
                    "V": "50000",
                    "Q": "5000000",
                }
                collector.handle_message({"e": "kline", "E": now, "s": symbol, "k": k}, now)
            obj.process_tick(
                END + MINUTE_MS + 200,
                health(END + MINUTE_MS + 200),
                [Quote(s, 100, 100.02, END + MINUTE_MS + 200, 101) for s in SYMBOLS],
            )
            assert any(r["scenario"] == "B2" for r in payloads(obj, "fill"))
            assert obj.status()["actual_qualification_days"] == 0
            report = evaluate_forward_snapshot(read_forward_evidence(obj.path))
            assert report["status"] == "INSUFFICIENT_EVIDENCE"
            assert hashlib.sha256(model.read_bytes()).hexdigest() == before
        finally:
            collector.close()
            obj.close()
