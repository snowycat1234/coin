"""Algorithm-independent frozen inference, with no training or trading authority.

The release SHA binds native model bytes, ordered feature definitions, execution,
cost/risk contracts, output semantics and training/label cutoffs. Tree dependencies
are imported only when requested. All inference is CPU-only and single-threaded.
"""

from __future__ import annotations

import copy
import hashlib
import importlib
import json
import math
import re
from collections.abc import Mapping
from datetime import datetime
from pathlib import Path
from typing import Any, Protocol, runtime_checkable

import numpy as np

from .paths import STATE

SCHEMA_VERSION = "frozen_predictor_v1"
DEVELOPMENT_CUTOFF = "2026-03-01T00:00:00Z"
MAX_MODEL_BYTES = 64_000_000
MAX_MANIFEST_BYTES = 128_000
PROBABILITY_SEMANTICS = "probability_future_4h_net_positive"
RETURN_SEMANTICS = "future_4h_gross_executable_return"
ABS_TOLERANCE = 1e-12
REL_TOLERANCE = 1e-10
LEGACY_FEATURE_NAMES = (
    "log_return_1",
    "log_return_4",
    "log_return_16",
    "volatility_24",
    "volatility_96",
    "volume_z96",
    "range_fraction",
    "body_fraction",
    "ema_gap",
    "taker_fraction",
)
MODEL_FORMATS = {"logistic_json": "json", "lightgbm": "native_text", "xgboost": "native_json"}
CONTEXT_FIELDS = {"symbol", "interval", "available_us", "received_us"}


class PredictorDenied(ValueError):
    """Invalid, modified, unsupported or incompatible frozen artifact."""


class PredictorDependencyUnavailable(PredictorDenied):
    """Requested optional native CPU library is not available; do not substitute a model."""


class ExecutionBinding(Protocol):
    version: str

    def digest(self) -> str: ...


@runtime_checkable
class FrozenPredictor(Protocol):
    model_type: str
    schema_version: str
    feature_names: tuple[str, ...]
    decision_interval: str
    prediction_horizon: str
    release_sha256: str

    def predict(self, features: Mapping[str, float]) -> dict[str, Any]: ...


def _json(value: Any) -> bytes:
    try:
        return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    except (ValueError, TypeError) as error:
        raise PredictorDenied("release must contain only finite JSON values") from error


def _hash(value: Any) -> str:
    return hashlib.sha256(_json(value)).hexdigest()


def _unique(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise PredictorDenied(f"duplicate JSON field: {key}")
        result[key] = value
    return result


def _decode(value: bytes) -> dict:
    try:
        result = json.loads(
            value,
            object_pairs_hook=_unique,
            parse_constant=lambda _: (_ for _ in ()).throw(
                PredictorDenied("non-finite JSON constant")
            ),
        )
    except (ValueError, UnicodeDecodeError) as error:
        raise PredictorDenied("model/manifest is not valid strict JSON") from error
    if not isinstance(result, dict):
        raise PredictorDenied("model/manifest must be a JSON object")
    return result


def _timestamp(value: str) -> int:
    if not isinstance(value, str):
        raise PredictorDenied("training cutoff must be explicit ISO UTC")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise PredictorDenied("invalid training cutoff") from error
    if parsed.tzinfo is None or parsed.utcoffset().total_seconds() != 0:
        raise PredictorDenied("training cutoff requires explicit UTC timezone")
    return int(parsed.timestamp() * 1_000_000)


def _sha_value(value: Any, name: str) -> str:
    if not isinstance(value, str) or not re.fullmatch("[0-9a-f]{64}", value):
        raise PredictorDenied(f"invalid {name} SHA256")
    return value


def _execution(contract: ExecutionBinding) -> dict:
    if contract.version != "execution_v2":
        raise PredictorDenied("new predictor release requires execution_v2")
    return {"version": contract.version, "sha256": _sha_value(contract.digest(), "execution")}


def contracts_from_execution(contract: ExecutionBinding) -> tuple[dict, dict]:
    """Produce the canonical cost/risk documents from ExecutionContractV2 fields."""
    _execution(contract)
    try:
        cost = {
            "version": contract.cost_version,
            "definition": {
                "fee_bps": contract.fee_bps,
                "half_spread_floor_bps": contract.half_spread_floor_bps,
                "extra_slippage_bps": contract.extra_slippage_bps,
                "fee_basis": "actual_fill_notional",
            },
        }
        risk = {
            "version": contract.risk_version,
            "definition": {
                "single_asset_max": contract.max_weight,
                "gross_max": contract.max_gross,
                "annual_vol_target": contract.annual_vol_target,
                "participation_rate": contract.participation_rate,
                "min_notional": contract.min_notional,
                "market": "spot_long_cash",
                "lot_steps": {"BTCUSDT": 0.00001, "ETHUSDT": 0.0001},
            },
        }
    except AttributeError as error:
        raise PredictorDenied("execution contract is missing canonical cost/risk fields") from error
    return cost, risk


def _contract(value: Mapping, name: str) -> dict:
    plain = copy.deepcopy(dict(value))
    if not isinstance(plain.get("version"), str) or not plain["version"]:
        raise PredictorDenied(f"{name} requires an explicit version and definition")
    if not isinstance(plain.get("definition"), dict) or not plain["definition"]:
        raise PredictorDenied(f"{name} requires an explicit version and definition")
    if set(plain) != {"version", "definition"}:
        raise PredictorDenied(f"{name} contract has unexpected fields")
    return {**plain, "sha256": _hash(plain)}


def _features(schema: Mapping) -> tuple[dict, tuple[str, ...]]:
    plain = copy.deepcopy(dict(schema))
    if set(plain) != {"version", "features", "missing_policy"}:
        raise PredictorDenied(
            "feature schema requires version, ordered features and missing policy"
        )
    items = plain["features"]
    if not isinstance(plain["version"], str) or not plain["version"]:
        raise PredictorDenied("feature schema needs a version")
    if (
        plain["missing_policy"] != "reject"
        or not isinstance(items, list)
        or not 1 <= len(items) <= 64
    ):
        raise PredictorDenied(
            "feature schema must reject missing values and contain 1..64 features"
        )
    names = []
    for item in items:
        if not isinstance(item, dict) or set(item) != {"name", "dtype", "definition"}:
            raise PredictorDenied("every feature needs name, dtype and definition")
        if (
            not isinstance(item["name"], str)
            or not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", item["name"])
            or item["dtype"] != "float64"
            or not isinstance(item["definition"], str)
            or not item["definition"].strip()
        ):
            raise PredictorDenied("unsupported feature name, dtype or definition")
        names.append(item["name"])
    if len(set(names)) != len(names) or set(names) & CONTEXT_FIELDS:
        raise PredictorDenied("duplicate/reserved feature name")
    return {**plain, "sha256": _hash(plain)}, tuple(names)


def legacy_feature_schema() -> dict:
    """Ordered legacy ten-feature schema; definitions do not recompute market data."""
    definitions = (
        "log(close/close_lag1)",
        "log(close/close_lag4)",
        "log(close/close_lag16)",
        "sample_std(last24_log_returns,ddof=1)",
        "sample_std(last96_log_returns,ddof=1)",
        "(volume-mean(last96_volumes))/(sample_std(last96_volumes,ddof=1)+1e-12)",
        "(high-low)/close",
        "(close-open)/open",
        "EMA20(close)/EMA100(close)-1",
        "taker_buy_base/volume; zero_volume_fallback=0.5",
    )
    return {
        "version": "legacy_ohlcv_features_v1",
        "missing_policy": "reject",
        "features": [
            {"name": name, "dtype": "float64", "definition": definition}
            for name, definition in zip(LEGACY_FEATURE_NAMES, definitions, strict=True)
        ],
    }


def make_predictor_manifest(
    model_bytes: bytes,
    *,
    model_type: str,
    feature_schema: Mapping,
    execution_contract: ExecutionBinding,
    cost_contract: Mapping,
    risk_contract: Mapping,
    training_cutoff: str,
    training_last_available_us: int,
    training_last_label_end_us: int,
    training_data_sha256: str,
    decision_interval: str = "1h",
    prediction_horizon: str = "4h",
) -> dict:
    """Build a binding for already exported bytes; does not train, write or qualify.

    Training metadata is a verifiable declaration from a later research exporter,
    not proof that a malicious exporter respected the declared training boundary.
    """
    if not isinstance(model_bytes, bytes) or not 0 < len(model_bytes) <= MAX_MODEL_BYTES:
        raise PredictorDenied("model bytes must be nonempty and <=64 MB")
    if model_type not in MODEL_FORMATS:
        raise PredictorDenied("unsupported model type")
    schema, _ = _features(feature_schema)
    semantics = PROBABILITY_SEMANTICS if model_type == "logistic_json" else RETURN_SEMANTICS
    result = {
        "schema_version": SCHEMA_VERSION,
        "model_type": model_type,
        "model_format": MODEL_FORMATS[model_type],
        "model_sha256": hashlib.sha256(model_bytes).hexdigest(),
        "predictor_implementation_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "model_bytes": len(model_bytes),
        "feature_schema": schema,
        "execution_contract": _execution(execution_contract),
        "cost_contract": _contract(cost_contract, "cost"),
        "risk_contract": _contract(risk_contract, "risk"),
        "training_cutoff": training_cutoff,
        "training_last_available_us": training_last_available_us,
        "training_last_label_end_us": training_last_label_end_us,
        "training_data_sha256": _sha_value(training_data_sha256, "training data"),
        "decision_interval": decision_interval,
        "prediction_horizon": prediction_horizon,
        "prediction_semantics": semantics,
        "return_unit": "decimal_simple_return",
        "runtime": {"device": "cpu", "threads": 1, "missing_features": "reject"},
        "qualification": "inference_binding_only_not_alpha_or_live_authorization",
    }
    result["release_sha256"] = _hash(result)
    _validate_manifest(result, model_bytes, execution_contract, cost_contract, risk_contract)
    return result


def _validate_manifest(
    manifest: dict,
    model_bytes: bytes,
    execution_contract: ExecutionBinding,
    cost_contract: Mapping,
    risk_contract: Mapping,
) -> tuple[str, ...]:
    required = {
        "schema_version",
        "model_type",
        "model_format",
        "model_sha256",
        "predictor_implementation_sha256",
        "model_bytes",
        "feature_schema",
        "execution_contract",
        "cost_contract",
        "risk_contract",
        "training_cutoff",
        "training_last_available_us",
        "training_last_label_end_us",
        "training_data_sha256",
        "decision_interval",
        "prediction_horizon",
        "prediction_semantics",
        "return_unit",
        "runtime",
        "qualification",
        "release_sha256",
    }
    if set(manifest) != required or manifest["schema_version"] != SCHEMA_VERSION:
        raise PredictorDenied("unsupported/incomplete frozen predictor schema")
    if (
        _hash({k: v for k, v in manifest.items() if k != "release_sha256"})
        != manifest["release_sha256"]
    ):
        raise PredictorDenied("release binding SHA mismatch")
    if (
        manifest["predictor_implementation_sha256"]
        != hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    ):
        raise PredictorDenied("predictor implementation differs from frozen release")
    if (
        not isinstance(model_bytes, bytes)
        or not 0 < len(model_bytes) <= MAX_MODEL_BYTES
        or len(model_bytes) != manifest["model_bytes"]
        or hashlib.sha256(model_bytes).hexdigest() != manifest["model_sha256"]
    ):
        raise PredictorDenied("model bytes differ from the frozen release")
    model_type = manifest["model_type"]
    if model_type not in MODEL_FORMATS or manifest["model_format"] != MODEL_FORMATS[model_type]:
        raise PredictorDenied("unsupported model type/format pairing")
    plain_schema = {k: v for k, v in manifest["feature_schema"].items() if k != "sha256"}
    feature_schema, names = _features(plain_schema)
    if manifest["feature_schema"] != feature_schema:
        raise PredictorDenied("feature schema SHA mismatch")
    if manifest["execution_contract"] != _execution(execution_contract):
        raise PredictorDenied("execution contract changed")
    if manifest["cost_contract"] != _contract(cost_contract, "cost"):
        raise PredictorDenied("cost contract changed")
    if manifest["risk_contract"] != _contract(risk_contract, "risk"):
        raise PredictorDenied("risk contract changed")
    canonical_cost, canonical_risk = contracts_from_execution(execution_contract)
    if manifest["cost_contract"] != _contract(canonical_cost, "cost") or manifest[
        "risk_contract"
    ] != _contract(canonical_risk, "risk"):
        raise PredictorDenied("cost/risk documents disagree with execution_v2 canonical parameters")
    cutoff = _timestamp(manifest["training_cutoff"])
    if cutoff > _timestamp(DEVELOPMENT_CUTOFF):
        raise PredictorDenied("training cutoff enters the locked historical test")
    available, label = (
        manifest["training_last_available_us"],
        manifest["training_last_label_end_us"],
    )
    if type(available) is not int or type(label) is not int or not 0 < available <= label <= cutoff:
        raise PredictorDenied("training availability/label ends exceed the declared cutoff")
    _sha_value(manifest["training_data_sha256"], "training data")
    expected = PROBABILITY_SEMANTICS if model_type == "logistic_json" else RETURN_SEMANTICS
    if manifest["prediction_semantics"] != expected or manifest["prediction_horizon"] != "4h":
        raise PredictorDenied("model output task/horizon mismatch")
    intervals = {"1h", "15m"} if model_type == "logistic_json" else {"1h"}
    if manifest["decision_interval"] not in intervals:
        raise PredictorDenied("unsupported decision interval")
    if (
        manifest["return_unit"] != "decimal_simple_return"
        or manifest["runtime"] != {"device": "cpu", "threads": 1, "missing_features": "reject"}
        or manifest["qualification"] != "inference_binding_only_not_alpha_or_live_authorization"
    ):
        raise PredictorDenied("runtime/output/authority contract changed")
    return names


def _optional(name: str):
    try:
        return importlib.import_module(name)
    except (ImportError, OSError) as error:
        raise PredictorDependencyUnavailable(
            f"optional CPU dependency unavailable: {name}"
        ) from error


class _BasePredictor:
    def __init__(
        self,
        model_bytes: bytes,
        manifest: dict,
        *,
        execution_contract: ExecutionBinding,
        cost_contract: Mapping,
        risk_contract: Mapping,
    ):
        _validate_manifest(manifest, model_bytes, execution_contract, cost_contract, risk_contract)
        self._manifest_bytes = _json(manifest)
        self.model_type = manifest["model_type"]
        self.schema_version = manifest["schema_version"]
        self.feature_names = tuple(x["name"] for x in manifest["feature_schema"]["features"])
        self.decision_interval = manifest["decision_interval"]
        self.prediction_horizon = manifest["prediction_horizon"]
        self.release_sha256 = manifest["release_sha256"]
        self.prediction_semantics = manifest["prediction_semantics"]

    def __setattr__(self, key, value):
        if getattr(self, "_sealed", False):
            raise AttributeError("frozen predictor attributes cannot be changed")
        object.__setattr__(self, key, value)

    @property
    def manifest(self) -> dict:
        return _decode(self._manifest_bytes)

    def _vector(self, features: Mapping[str, float]) -> np.ndarray:
        if not isinstance(features, Mapping):
            raise PredictorDenied("features must be an explicit name/value mapping")
        missing = set(self.feature_names) - features.keys()
        unknown = features.keys() - set(self.feature_names) - CONTEXT_FIELDS
        if missing or unknown:
            raise PredictorDenied(
                f"feature names mismatch: missing={sorted(missing)}, extra={sorted(unknown)}"
            )
        values = [features[name] for name in self.feature_names]
        if any(
            isinstance(v, (str, bool)) or not isinstance(v, (int, float, np.integer, np.floating))
            for v in values
        ):
            raise PredictorDenied("feature values must be numeric, not strings/bools")
        try:
            vector = np.asarray(values, dtype=np.float64).reshape(1, -1)
        except (TypeError, ValueError, OverflowError) as error:
            raise PredictorDenied("feature values exceed finite float64 representation") from error
        if not np.isfinite(vector).all():
            raise PredictorDenied("missing/nonfinite features: freeze the signal")
        return vector

    def _output(self, *, expected_return=None, confidence=None, target_weight=None) -> dict:
        for value in (expected_return, confidence, target_weight):
            if value is not None and not math.isfinite(value):
                raise PredictorDenied("native model returned a nonfinite prediction")
        return {
            "expected_return": expected_return,
            "confidence": confidence,
            "target_weight": target_weight,
            "prediction_semantics": self.prediction_semantics,
            "release_sha256": self.release_sha256,
        }


class LogisticJsonPredictor(_BasePredictor):
    """Exact legacy JSON scaler/logit/threshold inference; probability is not return."""

    def __init__(self, model_bytes: bytes, manifest: dict, **bindings):
        super().__init__(model_bytes, manifest, **bindings)
        model = _decode(model_bytes)
        if (
            self.feature_names != LEGACY_FEATURE_NAMES
            or tuple(model.get("features", ())) != self.feature_names
            or model.get("classes") != [0, 1]
        ):
            raise PredictorDenied("Logistic legacy feature/class contract mismatch")
        for name in ("scaler_mean", "scaler_scale", "coefficients"):
            try:
                vector = np.asarray(model[name], dtype=float)
            except (KeyError, TypeError, ValueError) as error:
                raise PredictorDenied("invalid Logistic coefficients/scaler") from error
            if vector.shape != (len(self.feature_names),) or not np.isfinite(vector).all():
                raise PredictorDenied("invalid Logistic coefficients/scaler")
            if name == "scaler_scale" and np.any(vector <= 0):
                raise PredictorDenied("scaler scale must be positive")
            vector.setflags(write=False)
            setattr(self, "_" + name, vector)
        try:
            configuration = model["configuration"]
            self._threshold = float(configuration["threshold"])
            self._intercept = float(model["intercept"])
        except (KeyError, TypeError, ValueError) as error:
            raise PredictorDenied("missing Logistic inference configuration") from error
        if (
            configuration.get("interval") != self.decision_interval
            or not 0.5 <= self._threshold < 1
            or not math.isfinite(self._intercept)
        ):
            raise PredictorDenied("invalid Logistic threshold/interval/intercept")
        for name in ("training_last_available_us", "training_last_label_end_us"):
            if model.get(name) != manifest[name]:
                raise PredictorDenied("Logistic training metadata and release disagree")
        risk = manifest["risk_contract"]["definition"]
        self._maximum_weight = float(risk.get("single_asset_max", math.nan))
        if not 0 < self._maximum_weight <= 0.30:
            raise PredictorDenied("Logistic target exceeds frozen spot limit")
        self._sealed = True

    def predict(self, features: Mapping[str, float]) -> dict:
        vector = self._vector(features)
        standardized = (vector - self._scaler_mean) / self._scaler_scale
        score = standardized @ self._coefficients + self._intercept
        probability = float((1 / (1 + np.exp(-np.clip(score, -700, 700))))[0])
        return self._output(
            confidence=probability,
            target_weight=self._maximum_weight if probability >= self._threshold else 0.0,
        )


class LightGBMPredictor(_BasePredictor):
    """Native CPU scalar gross-return regression. Sizing/hysteresis stay outside."""

    def __init__(self, model_bytes: bytes, manifest: dict, **bindings):
        super().__init__(model_bytes, manifest, **bindings)
        library = _optional("lightgbm")
        try:
            model_text = model_bytes.decode("utf-8")
        except UnicodeDecodeError as error:
            raise PredictorDenied("invalid native LightGBM text model") from error
        declared_devices = re.findall(
            r"^\[(?:device_type|device):\s*([^\]]+)\]$", model_text, flags=re.MULTILINE
        )
        if any(value.strip() != "cpu" for value in declared_devices):
            raise PredictorDenied("LightGBM native artifact is not bound to CPU")
        try:
            # Native model_str loading ignores constructor params in LightGBM.
            # Inspect the actual restored backend parameters and bind prediction
            # threads explicitly rather than claiming those ignored params apply.
            self._booster = library.Booster(model_str=model_text)
            saved = self._booster.dump_model()
        except Exception as error:
            raise PredictorDenied("invalid native LightGBM text model") from error
        if (
            self._booster.params.get("device_type", "cpu") != "cpu"
            or self._booster.params.get("device", "cpu") != "cpu"
        ):
            raise PredictorDenied("LightGBM native artifact is not bound to CPU")
        objective_fields = str(saved.get("objective", "")).split()
        objective = objective_fields[0] if objective_fields else ""
        if objective not in {"regression", "regression_l1", "huber", "fair"}:
            raise PredictorDenied("LightGBM objective does not output scalar simple return")
        if (
            tuple(self._booster.feature_name()) != self.feature_names
            or saved.get("num_class") != 1
            or self._booster.num_feature() != len(self.feature_names)
        ):
            raise PredictorDenied("LightGBM native feature/class schema differs from release")
        self._sealed = True

    def predict(self, features: Mapping[str, float]) -> dict:
        result = np.asarray(
            self._booster.predict(self._vector(features), num_threads=1, num_iteration=-1),
            dtype=float,
        )
        if result.shape != (1,):
            raise PredictorDenied("LightGBM must produce one scalar return")
        return self._output(expected_return=float(result[0]))


class XGBoostPredictor(_BasePredictor):
    """Native JSON CPU scalar gross-return regression. No pickle or GPU loading."""

    def __init__(self, model_bytes: bytes, manifest: dict, **bindings):
        super().__init__(model_bytes, manifest, **bindings)
        native = _decode(model_bytes)
        if "learner" not in native:
            raise PredictorDenied("XGBoost requires native JSON, not sklearn/pickle serialization")
        library = _optional("xgboost")
        self._library = library
        try:
            self._booster = library.Booster(params={"device": "cpu", "nthread": 1})
            self._booster.load_model(bytearray(model_bytes))
            self._booster.set_param({"device": "cpu", "nthread": 1})
            configuration = json.loads(self._booster.save_config())["learner"]
        except Exception as error:
            raise PredictorDenied("invalid native XGBoost JSON model") from error
        if configuration.get("objective", {}).get("name") not in {
            "reg:squarederror",
            "reg:absoluteerror",
            "reg:pseudohubererror",
        }:
            raise PredictorDenied("XGBoost objective does not output scalar simple return")
        if (
            tuple(self._booster.feature_names or ()) != self.feature_names
            or self._booster.num_features() != len(self.feature_names)
            or configuration["learner_model_param"].get("num_target", "1") != "1"
            or configuration["learner_model_param"].get("num_class", "0") != "0"
        ):
            raise PredictorDenied("XGBoost native feature/output schema differs from release")
        if configuration["generic_param"].get("device", "cpu") != "cpu":
            raise PredictorDenied("XGBoost failed to bind CPU runtime")
        self._sealed = True

    def predict(self, features: Mapping[str, float]) -> dict:
        data = self._library.DMatrix(
            self._vector(features), feature_names=list(self.feature_names), nthread=1
        )
        result = np.asarray(self._booster.predict(data, validate_features=True), dtype=float)
        if result.shape != (1,):
            raise PredictorDenied("XGBoost must produce one scalar return")
        return self._output(expected_return=float(result[0]))


def load_frozen_predictor_bytes(
    model_bytes: bytes,
    manifest: Mapping,
    *,
    execution_contract: ExecutionBinding,
    cost_contract: Mapping,
    risk_contract: Mapping,
) -> FrozenPredictor:
    """Load a bound artifact for engineering/research inference; never grant deployment."""
    manifest = _decode(_json(dict(manifest)))
    _validate_manifest(manifest, model_bytes, execution_contract, cost_contract, risk_contract)
    classes = {
        "logistic_json": LogisticJsonPredictor,
        "lightgbm": LightGBMPredictor,
        "xgboost": XGBoostPredictor,
    }
    return classes[manifest["model_type"]](
        model_bytes,
        manifest,
        execution_contract=execution_contract,
        cost_contract=cost_contract,
        risk_contract=risk_contract,
    )


def _local_bytes(path: str | Path, maximum: int) -> bytes:
    path = Path(path).resolve()
    if not (str(path).startswith("/mnt/d/") or path.is_relative_to(STATE.resolve())):
        raise PredictorDenied("model/release artifacts must stay on D-hosted storage")
    if not path.is_file() or path.stat().st_size > maximum:
        raise PredictorDenied("artifact missing or exceeds the frozen loader size limit")
    # Bounded read also protects against file growth between stat and read.
    with path.open("rb") as stream:
        result = stream.read(maximum + 1)
    if len(result) > maximum:
        raise PredictorDenied("artifact grew beyond loader size limit")
    return result


def load_frozen_predictor(
    model_path: str | Path,
    manifest_path: str | Path,
    *,
    execution_contract: ExecutionBinding,
    cost_contract: Mapping,
    risk_contract: Mapping,
) -> FrozenPredictor:
    """Read exact bounded local bytes and validate before importing an optional library."""
    return load_frozen_predictor_bytes(
        _local_bytes(model_path, MAX_MODEL_BYTES),
        _decode(_local_bytes(manifest_path, MAX_MANIFEST_BYTES)),
        execution_contract=execution_contract,
        cost_contract=cost_contract,
        risk_contract=risk_contract,
    )
