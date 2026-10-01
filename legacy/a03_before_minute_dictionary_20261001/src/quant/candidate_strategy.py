"""Generic frozen inference and causal feature providers; no live admission or fitting."""

from __future__ import annotations

import copy
import hashlib
import math
from collections.abc import Mapping
from pathlib import Path

import numpy as np

from .alpha_rules_v2 import HOUR_US, THRESHOLDS
from .execution_contract import ExecutionContractV2
from .features_v2 import (
    FEATURE_NAMES_V2,
    HourlyFeatureState,
    feature_contract_v2,
    feature_schema_v2,
)
from .holdout import HoldoutDenied
from .predictor import (
    CONTEXT_FIELDS,
    LEGACY_FEATURE_NAMES,
    PROBABILITY_SEMANTICS,
    RETURN_SEMANTICS,
    FrozenPredictor,
    contracts_from_execution,
)
from .research import INTERVAL_US, canonical_hash
from .shadow import SYMBOLS

MINUTE_US = 60_000_000
_SOURCE_CACHE = {}
_FEATURE_CONTRACT_CACHE = None
_EXECUTION_CACHE = None


def execution_bindings():
    """Cache immutable contracts by current source SHA, never by an assumed version."""
    global _EXECUTION_CACHE
    sha = source_sha("execution_contract.py")
    if _EXECUTION_CACHE is None or _EXECUTION_CACHE[0] != sha:
        execution = ExecutionContractV2()
        cost, risk = contracts_from_execution(execution)
        _EXECUTION_CACHE = (sha, execution.digest(), cost, risk)
    return copy.deepcopy(_EXECUTION_CACHE[1:])


def hourly_contract():
    global _FEATURE_CONTRACT_CACHE
    sha = source_sha("features_v2.py")
    if _FEATURE_CONTRACT_CACHE is None or _FEATURE_CONTRACT_CACHE[0] != sha:
        _FEATURE_CONTRACT_CACHE = (sha, feature_contract_v2())
    return copy.deepcopy(_FEATURE_CONTRACT_CACHE[1])


def source_sha(name: str) -> str:
    path = Path(__file__).with_name(name)
    stat = path.stat()
    stamp = (stat.st_ino, stat.st_size, stat.st_mtime_ns, stat.st_ctime_ns)
    cached = _SOURCE_CACHE.get(name)
    if cached is None or cached[0] != stamp:
        cached = (stamp, hashlib.sha256(path.read_bytes()).hexdigest())
        _SOURCE_CACHE[name] = cached
    return cached[1]


def aggregate_minutes(minutes: list[dict], end: int, step: int) -> dict:
    return {
        "symbol": minutes[-1]["symbol"],
        "interval": "1h" if step == HOUR_US else "15m",
        "open_us": end - step,
        "close_us": end,
        "available_us": end,
        "received_us": minutes[-1]["received_us"],
        "open": minutes[0]["open"],
        "close": minutes[-1]["close"],
        "high": max(row["high"] for row in minutes),
        "low": min(row["low"] for row in minutes),
        **{
            key: sum(row[key] for row in minutes)
            for key in ("volume", "quote_volume", "taker_buy_base", "taker_buy_quote")
        },
    }


class LegacyFeatureProvider:
    """Existing ten-feature formulas remain available without an invented manifest."""

    pooled = False

    def __init__(self, interval, new_features, update_features):
        self.interval, self.feature_names = interval, LEGACY_FEATURE_NAMES
        self._new, self._update = new_features, update_features

    def contract(self):
        return {
            "version": "legacy_incremental_candidate_features_v1",
            "interval": self.interval,
            "features": list(self.feature_names),
            "source_sha256": source_sha("candidate_paper.py"),
            "provider_source_sha256": source_sha("candidate_strategy.py"),
        }

    def new_state(self):
        return {symbol: self._new() for symbol in SYMBOLS}

    def latest(self, state):
        return {symbol: state[symbol]["latest"] for symbol in SYMBOLS}

    def validate(self, state):
        if set(state) != set(SYMBOLS):
            raise HoldoutDenied("Legacy feature state shape changed")
        for symbol in SYMBOLS:
            if (
                len(state[symbol]["history"]) > 100
                or len(state[symbol]["pending_minutes"]) >= INTERVAL_US[self.interval] // MINUTE_US
            ):
                raise HoldoutDenied("Unbounded legacy feature state")

    def apply_minute(self, state, minute):
        symbol, opened, end = minute["symbol"], minute["open_us"], minute["close_us"]
        local, step = state[symbol], INTERVAL_US[self.interval]
        minutes = local["pending_minutes"]
        if minutes and (
            opened != minutes[-1]["open_us"] + MINUTE_US
            or opened // step != minutes[-1]["open_us"] // step
        ):
            minutes = []
        # Receipt is preserved so a paired provider never uses a logical timestamp
        # as evidence of when either coin actually arrived.
        minutes = minutes + [copy.deepcopy(minute)]
        local["pending_minutes"] = minutes
        if end % step:
            return [], False
        local["pending_minutes"] = []
        if len(minutes) != step // MINUTE_US or minutes[0]["open_us"] != end - step:
            local.update(self._new())
            return [], True
        result = self._update(local, aggregate_minutes(minutes, end, step), self.interval)
        return ([result] if result else []), True


class Hourly40FeatureProvider:
    """Compose the accepted pooled HourlyFeatureState, including joint pending pairs."""

    pooled = True
    interval = "1h"
    feature_names = FEATURE_NAMES_V2

    def contract(self):
        return {
            "version": "candidate_hourly40_provider_v1",
            "interval": self.interval,
            "feature_contract": hourly_contract(),
            "provider_source_sha256": source_sha("candidate_strategy.py"),
        }

    def new_state(self):
        return {
            **{
                symbol: {
                    "pending_minutes": [],
                    "last_open_us": None,
                    "last_minute_open_us": None,
                    "latest": None,
                    "last_boundary_us": None,
                    "last_boundary_complete": False,
                }
                for symbol in SYMBOLS
            },
            "_hourly": HourlyFeatureState().export_state(),
        }

    def phase(self, state, end_us):
        local = [state[symbol] for symbol in SYMBOLS]
        if any(
            row["last_boundary_us"] == end_us and not row["last_boundary_complete"] for row in local
        ):
            return "CONFIRMED_GAP"
        if state["_hourly"]["state"]["last_emitted_end_us"] == end_us:
            return "PAIR_CLOSED"
        return "WAITING_FOR_PAIR"

    def latest(self, state):
        return {symbol: state[symbol]["latest"] for symbol in SYMBOLS}

    def validate(self, state):
        if set(state) != set(SYMBOLS) | {"_hourly"}:
            raise HoldoutDenied("Pooled feature state shape changed")
        HourlyFeatureState.from_snapshot(state["_hourly"])
        for symbol in SYMBOLS:
            if len(state[symbol]["pending_minutes"]) >= 60:
                raise HoldoutDenied("Unbounded pending hourly minutes")

    def apply_minute(self, state, minute):
        local, opened, end = state[minute["symbol"]], minute["open_us"], minute["close_us"]
        if local["last_minute_open_us"] is not None and opened <= local["last_minute_open_us"]:
            raise ValueError("Pooled minute evidence is out of order")
        local["last_minute_open_us"] = opened
        minutes = local["pending_minutes"]
        if minutes and (
            opened != minutes[-1]["open_us"] + MINUTE_US
            or opened // HOUR_US != minutes[-1]["open_us"] // HOUR_US
        ):
            minutes = []
        minutes = minutes + [copy.deepcopy(minute)]
        local["pending_minutes"] = minutes
        if end % HOUR_US:
            return [], False
        local["pending_minutes"] = []
        local["last_open_us"] = end - HOUR_US
        local["last_boundary_us"] = end
        local["last_boundary_complete"] = (
            len(minutes) == 60 and minutes[0]["open_us"] == end - HOUR_US
        )
        if not local["last_boundary_complete"]:
            local["latest"] = None
            return [], True
        hourly = HourlyFeatureState.from_snapshot(state["_hourly"])
        results = hourly.ingest(
            aggregate_minutes(minutes, end, HOUR_US), asof_us=minute["received_us"]
        )
        state["_hourly"] = hourly.export_state()
        for row in results:
            state[row["symbol"]]["latest"] = row if row["feature_ready"] else None
        return [row for row in results if row["feature_ready"]], True

    def snapshot(self, state):
        self.validate(state)
        body = {"contract": self.contract(), "state": state}
        return copy.deepcopy({**body, "state_sha256": canonical_hash(body)})

    def restore(self, snapshot):
        body = {key: snapshot[key] for key in ("contract", "state")}
        if (
            snapshot.get("state_sha256") != canonical_hash(body)
            or body["contract"] != self.contract()
        ):
            raise HoldoutDenied("Pooled feature anchor contract/digest changed")
        self.validate(body["state"])
        return copy.deepcopy(body["state"])


class LegacyPredictorAdapter:
    """Legacy JSON compatibility only; no fabricated training cutoff/source declaration."""

    model_type = "logistic_legacy_adapter"
    schema_version = "legacy_candidate_adapter_v1"
    feature_names = LEGACY_FEATURE_NAMES
    prediction_horizon = "4h"
    prediction_semantics = PROBABILITY_SEMANTICS

    def __init__(self, model):
        self._model = copy.deepcopy(model)
        self.decision_interval = model["interval"]
        self.model_sha256 = canonical_hash(model)
        self.release_sha256 = canonical_hash(self.binding_document)

    @property
    def binding_document(self):
        return {
            "model_sha256": canonical_hash(self._model),
            "legacy_metadata": "as_originally_saved",
            "training_provenance_certified_by_this_adapter": False,
            "adapter_source_sha256": source_sha("candidate_strategy.py"),
        }

    def predict(self, features):
        vector = np.array([features[name] for name in self.feature_names], dtype=float)
        model = self._model
        standardized = (vector - np.array(model["scaler_mean"])) / np.array(model["scaler_scale"])
        score = float(standardized @ np.array(model["coefficients"]) + model["intercept"])
        probability = float(1 / (1 + math.exp(-float(np.clip(score, -700, 700)))))
        return {
            "expected_return": None,
            "confidence": probability,
            "target_weight": 0.30 if probability >= model["configuration"]["threshold"] else 0.0,
            "prediction_semantics": self.prediction_semantics,
            "release_sha256": self.release_sha256,
        }


class FrozenCandidateStrategy:
    """One generic output contract plus a fixed probability or A/B/C return policy."""

    def __init__(self, predictor: FrozenPredictor, provider, *, threshold: str | None = None):
        if not isinstance(predictor, FrozenPredictor):
            raise HoldoutDenied("FrozenPredictor interface missing")
        if (
            predictor.feature_names != tuple(provider.feature_names)
            or predictor.decision_interval != provider.interval
            or predictor.prediction_horizon != "4h"
        ):
            raise HoldoutDenied("Predictor/provider feature/interval/horizon mismatch")
        legacy = predictor.prediction_semantics == PROBABILITY_SEMANTICS
        if legacy and threshold is not None or not legacy and threshold not in THRESHOLDS:
            raise HoldoutDenied("Fixed legacy or preregistered A/B/C policy required")
        if not legacy and (
            provider.interval != "1h" or predictor.prediction_semantics != RETURN_SEMANTICS
        ):
            raise HoldoutDenied("V2 strategy requires hourly executable return semantics")
        if not isinstance(predictor, LegacyPredictorAdapter):
            document = predictor.manifest
            contract = ExecutionContractV2()
            cost, risk = contracts_from_execution(contract)
            if document["execution_contract"] != {
                "version": contract.version,
                "sha256": contract.digest(),
            } or any(
                document[key] != {**value, "sha256": canonical_hash(value)}
                for key, value in (("cost_contract", cost), ("risk_contract", risk))
            ):
                raise HoldoutDenied("Predictor execution/cost/risk binding mismatch")
            if isinstance(provider, Hourly40FeatureProvider):
                schema = feature_schema_v2()
                if document["feature_schema"] != {**schema, "sha256": canonical_hash(schema)}:
                    raise HoldoutDenied("Hourly40 feature definitions mismatch")
        self.predictor, self.provider, self.threshold = predictor, provider, threshold
        self.legacy, self.interval = legacy, provider.interval
        self._threshold_bps = None if legacy else tuple(THRESHOLDS[threshold])
        self._identity = (id(predictor), id(provider))
        self._frozen_binding = self.binding()

    def binding(self):
        predictor = self.predictor
        document = (
            predictor.binding_document
            if isinstance(predictor, LegacyPredictorAdapter)
            else predictor.manifest
        )
        execution_sha, cost, risk = execution_bindings()
        return {
            "version": "generic_candidate_strategy_v1",
            "legacy": self.legacy,
            "model_native_sha256": document["model_sha256"],
            "predictor_release_sha256": predictor.release_sha256,
            "predictor_document_sha256": canonical_hash(document),
            "feature_provider": self.provider.contract(),
            "interval": self.interval,
            "feature_names": list(predictor.feature_names),
            "model_type": predictor.model_type,
            "semantics": predictor.prediction_semantics,
            "policy": {
                "threshold": self.threshold,
                "threshold_bps": None if self.legacy else list(THRESHOLDS[self.threshold]),
                "hold_minutes": 0 if self.legacy else 120,
                "policy_source_sha256": source_sha("alpha_rules_v2.py"),
            },
            "execution_sha256": execution_sha,
            "cost": cost,
            "risk": risk,
            "sources": {
                name: source_sha(name)
                for name in (
                    "candidate_strategy.py",
                    "candidate_paper.py",
                    "predictor.py",
                    "features_v2.py",
                    "decision_policy.py",
                    "execution_contract.py",
                    "alpha_rules_v2.py",
                    "collector.py",
                    "shadow.py",
                    "shadow_v2.py",
                    "concurrent_budget.py",
                    "research.py",
                )
            },
        }

    def guard(self):
        if (
            (
                id(self.predictor),
                id(self.provider),
            )
            != self._identity
            or self.binding() != self._frozen_binding
            or (not self.legacy and tuple(THRESHOLDS[self.threshold]) != self._threshold_bps)
        ):
            raise HoldoutDenied("冻结strategy/predictor/provider/policy参数改变")

    def new_policy_state(self):
        return {
            symbol: {"long": False, "entry_execution_us": None, "last_us": None}
            for symbol in SYMBOLS
        }

    def ready(self, features, end_us, now_us):
        return all(
            feature is not None
            and feature["available_us"] == end_us
            and feature.get("received_us", now_us + 1) <= now_us
            for feature in features.values()
        )

    def predictions(self, state, end_us, now_us):
        features = self.provider.latest(state)
        if self.legacy and not self.ready(features, end_us, now_us):
            return None
        output = {}
        for symbol in SYMBOLS:
            feature = features[symbol]
            if (
                feature is None
                or feature["available_us"] != end_us
                or feature["received_us"] > now_us
            ):
                output[symbol] = None
                continue
            values = {key: feature[key] for key in (*self.predictor.feature_names, *CONTEXT_FIELDS)}
            result = self.predictor.predict(values)
            if not isinstance(result, Mapping) or not {
                "expected_return",
                "confidence",
                "target_weight",
                "prediction_semantics",
                "release_sha256",
            }.issubset(result):
                raise HoldoutDenied("Generic predictor output is not a complete mapping")
            if (
                result.get("release_sha256") != self.predictor.release_sha256
                or result.get("prediction_semantics") != self.predictor.prediction_semantics
            ):
                raise HoldoutDenied("Generic output release/semantics changed")
            for key in ("expected_return", "confidence", "target_weight"):
                value = result[key]
                if value is not None and (
                    isinstance(value, bool)
                    or not isinstance(value, (int, float, np.integer, np.floating))
                    or not math.isfinite(value)
                ):
                    raise HoldoutDenied("Generic predictor returned invalid scalar")
            if result["confidence"] is not None and not 0 <= result["confidence"] <= 1:
                raise HoldoutDenied("Generic confidence outside [0,1]")
            if self.legacy:
                if (
                    result["expected_return"] is not None
                    or result["confidence"] is None
                    or result["target_weight"] is None
                    or not 0 <= result["target_weight"] <= 0.30
                ):
                    raise HoldoutDenied("Probability output contract mismatch")
            elif result["target_weight"] is not None:
                raise HoldoutDenied("Return output must not supply a precomputed target")
            # A missing regression output is an explicit data-risk flat; never infer long.
            if not self.legacy and result["expected_return"] is None:
                output[symbol] = None
                continue
            output[symbol] = result
        return output

    def targets(self, outputs, end_us, state):
        raw, policies = {}, {}
        eligible = ExecutionContractV2().earliest_execution_us(end_us)
        for symbol in SYMBOLS:
            output, local = outputs[symbol], state[symbol]
            if self.legacy:
                raw[symbol] = output["target_weight"]
                policies[symbol] = {"minimum_hold_minutes": 0, "risk_forced_exit": False}
                continue
            forced = (
                output is None
                or local["last_us"] is not None
                and end_us != local["last_us"] + HOUR_US
            )
            if forced:
                local.update(long=False, entry_execution_us=None)
            elif local["long"]:
                if (
                    eligible - local["entry_execution_us"] >= 2 * HOUR_US
                    and output["expected_return"] < self._threshold_bps[1] / 10_000
                ):
                    local.update(long=False, entry_execution_us=None)
            elif output["expected_return"] > self._threshold_bps[0] / 10_000:
                local.update(long=True, entry_execution_us=eligible)
            local["last_us"] = end_us
            raw[symbol] = 0.30 if local["long"] else 0.0
            policies[symbol] = {"minimum_hold_minutes": 120, "risk_forced_exit": forced}
        return raw, policies
