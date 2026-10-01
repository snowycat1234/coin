"""Independent synthetic inference and release integrity; no model fitting or PnL."""

import copy
import hashlib
import json
import sys
from dataclasses import replace
from types import SimpleNamespace

import numpy as np
import polars as pl
import pytest

from quant.execution_contract import ExecutionContractV2
from quant.predictor import (
    ABS_TOLERANCE,
    LEGACY_FEATURE_NAMES,
    REL_TOLERANCE,
    FrozenPredictor,
    LogisticJsonPredictor,
    PredictorDenied,
    PredictorDependencyUnavailable,
    contracts_from_execution,
    legacy_feature_schema,
    load_frozen_predictor,
    load_frozen_predictor_bytes,
    make_predictor_manifest,
)
from quant.research import predict_exported_model


def encoded(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def bindings():
    execution = ExecutionContractV2()
    cost, risk = contracts_from_execution(execution)
    return {"execution_contract": execution, "cost_contract": cost, "risk_contract": risk}


def logistic():
    return {
        "features": list(LEGACY_FEATURE_NAMES),
        "classes": [0, 1],
        "configuration": {"interval": "1h", "threshold": 0.55},
        "scaler_mean": [i / 10 for i in range(10)],
        "scaler_scale": [1 + i / 20 for i in range(10)],
        "coefficients": [(-1) ** i * (i + 1) / 10 for i in range(10)],
        "intercept": 0.123,
        "training_last_available_us": 1_700_000_000_000_000,
        "training_last_label_end_us": 1_700_015_000_000_000,
    }


def manifest(model, kind="logistic_json", **overrides):
    parameters = {
        "model_type": kind,
        "feature_schema": legacy_feature_schema()
        if kind == "logistic_json"
        else {
            "version": "synthetic_vector_v1",
            "missing_policy": "reject",
            "features": [
                {"name": name, "dtype": "float64", "definition": f"synthetic_{name}"}
                for name in ("f0", "f1")
            ],
        },
        "training_cutoff": "2026-03-01T00:00:00Z",
        "training_last_available_us": 1_700_000_000_000_000,
        "training_last_label_end_us": 1_700_015_000_000_000,
        "training_data_sha256": hashlib.sha256(b"synthetic_not_market_data").hexdigest(),
        **bindings(),
        **overrides,
    }
    return make_predictor_manifest(model, **parameters)


def resigned(value):
    result = copy.deepcopy(value)
    result["release_sha256"] = hashlib.sha256(
        encoded({k: v for k, v in result.items() if k != "release_sha256"})
    ).hexdigest()
    return result


def test_logistic_research_export_predictor_equivalence_without_fitting():
    model = logistic()
    blob = encoded(model)
    release = manifest(blob)
    predictor = load_frozen_predictor_bytes(blob, release, **bindings())
    assert isinstance(predictor, FrozenPredictor)
    rng = np.random.default_rng(20261001)
    rows = [
        dict(zip(LEGACY_FEATURE_NAMES, vector, strict=True)) for vector in rng.normal(size=(25, 10))
    ]
    samples = pl.DataFrame(rows).with_columns(
        pl.lit(1700016000000000).alias("available_us"), pl.lit("BTCUSDT").alias("symbol")
    )
    exported = predict_exported_model(model, samples)
    # This is the original research pipeline's scaler + classifier math, applied
    # to manually declared coefficients; neither sklearn fit nor market evaluation.
    standardized = (samples.select(LEGACY_FEATURE_NAMES).to_numpy() - model["scaler_mean"]) / model[
        "scaler_scale"
    ]
    oracle = 1 / (
        1 + np.exp(-np.clip(standardized @ model["coefficients"] + model["intercept"], -700, 700))
    )
    for index, row in enumerate(rows):
        predicted = predictor.predict(
            {**row, "symbol": "BTCUSDT", "available_us": 1700016000000000}
        )
        assert predicted["confidence"] == pytest.approx(
            oracle[index], abs=ABS_TOLERANCE, rel=REL_TOLERANCE
        )
        assert predicted["confidence"] == pytest.approx(
            exported["probability"][index], abs=ABS_TOLERANCE, rel=REL_TOLERANCE
        )
        assert predicted["target_weight"] == exported["target_weight"][index]
        assert predicted["expected_return"] is None
        assert predicted["prediction_semantics"] == "probability_future_4h_net_positive"
    reordered = dict(reversed(list(rows[0].items())))
    assert predictor.predict(reordered) == predictor.predict(rows[0])


def test_release_and_runtime_are_frozen_and_detached():
    blob = encoded(logistic())
    release = manifest(blob)
    predictor = load_frozen_predictor_bytes(blob, release, **bindings())
    original = predictor.manifest
    release["feature_schema"]["features"][0]["definition"] = "future data"
    clone = predictor.manifest
    clone["training_cutoff"] = "2099-01-01T00:00:00Z"
    assert predictor.manifest == original
    with pytest.raises(AttributeError, match="frozen"):
        predictor._threshold = 0.1
    with pytest.raises(ValueError):
        predictor._coefficients[0] = 3


@pytest.mark.parametrize(
    "field,value",
    [
        ("training_cutoff", "2026-03-01T00:00:00.000001Z"),
        ("training_cutoff", "2026-03-01"),
        ("training_cutoff", "2026-03-01T00:00:00+08:00"),
        ("training_last_label_end_us", 1_900_000_000_000_000),
        ("training_last_available_us", True),
        ("prediction_horizon", "5s"),
        ("decision_interval", "1m"),
        ("training_data_sha256", "not a digest"),
    ],
)
def test_training_boundaries_and_schema_fail_closed(field, value):
    with pytest.raises(PredictorDenied):
        manifest(encoded(logistic()), **{field: value})


@pytest.mark.parametrize(
    "mutation", ["model", "schema", "release", "cost", "risk", "execution", "semantics"]
)
def test_tampered_or_mismatched_contract_rejected(mutation):
    blob = encoded(logistic())
    release = manifest(blob)
    expected = bindings()
    if mutation == "model":
        blob += b" "
    elif mutation == "schema":
        release["feature_schema"]["features"].reverse()
        release = resigned(release)
    elif mutation == "release":
        release["release_sha256"] = "0" * 64
    elif mutation == "cost":
        expected["cost_contract"]["definition"]["fee_bps"] = 0
    elif mutation == "risk":
        expected["risk_contract"]["definition"]["single_asset_max"] = 0.9
    elif mutation == "execution":
        expected["execution_contract"] = SimpleNamespace(
            version="execution_v2", digest=lambda: "0" * 64
        )
    else:
        release["prediction_semantics"] = "future_4h_gross_executable_return"
        release = resigned(release)
    with pytest.raises(PredictorDenied):
        load_frozen_predictor_bytes(blob, release, **expected)


def test_cannot_resign_economic_limits_or_gpu_into_valid_release():
    blob = encoded(logistic())
    wrong = bindings()
    wrong["risk_contract"]["definition"]["single_asset_max"] = 0.9
    with pytest.raises(PredictorDenied, match="canonical"):
        manifest(blob, **wrong)
    release = manifest(blob)
    release["runtime"]["device"] = "cuda"
    with pytest.raises(PredictorDenied, match="runtime"):
        load_frozen_predictor_bytes(blob, resigned(release), **bindings())
    with pytest.raises(ValueError):
        replace(ExecutionContractV2(), latency_minutes=0)


@pytest.mark.parametrize("change", ["missing", "extra", "nan", "infinity", "bool", "string"])
def test_invalid_input_features_freeze(change):
    blob = encoded(logistic())
    predictor = load_frozen_predictor_bytes(blob, manifest(blob), **bindings())
    vector = dict.fromkeys(LEGACY_FEATURE_NAMES, 1.0)
    if change == "missing":
        del vector[LEGACY_FEATURE_NAMES[0]]
    elif change == "extra":
        vector["future_return"] = 0.1
    else:
        vector[LEGACY_FEATURE_NAMES[0]] = {
            "nan": np.nan,
            "infinity": np.inf,
            "bool": True,
            "string": "1",
        }[change]
    with pytest.raises(PredictorDenied):
        predictor.predict(vector)


@pytest.mark.parametrize(
    "field,value",
    [
        ("scaler_scale", [0] * 10),
        ("coefficients", [1] * 9),
        ("classes", [1, 0]),
        ("training_last_label_end_us", 1_999_999_999_999_999),
    ],
)
def test_invalid_legacy_artifact_is_rejected_even_when_hash_matches(field, value):
    model = logistic()
    model[field] = value
    blob = encoded(model)
    with pytest.raises(PredictorDenied):
        load_frozen_predictor_bytes(blob, manifest(blob), **bindings())


def test_direct_predictor_constructor_cannot_bypass_release_validation():
    blob = encoded(logistic())
    release = manifest(blob)
    release["training_cutoff"] = "2027-01-01T00:00:00Z"
    with pytest.raises(PredictorDenied):
        LogisticJsonPredictor(blob, release, **bindings())


@pytest.mark.parametrize("value", [complex(1, 2), np.complex64(1 + 2j), 10**1000])
def test_invalid_float64_representation_is_explicit_denial(value):
    blob = encoded(logistic())
    predictor = load_frozen_predictor_bytes(blob, manifest(blob), **bindings())
    vector = dict.fromkeys(LEGACY_FEATURE_NAMES, 1.0)
    vector[LEGACY_FEATURE_NAMES[0]] = value
    with pytest.raises(PredictorDenied):
        predictor.predict(vector)


def test_implementation_digest_change_is_rejected():
    blob = encoded(logistic())
    release = manifest(blob)
    release["predictor_implementation_sha256"] = "0" * 64
    with pytest.raises(PredictorDenied, match="implementation"):
        load_frozen_predictor_bytes(blob, resigned(release), **bindings())


def test_strict_json_and_local_bounded_artifact_load(tmp_path):
    blob = encoded(logistic())
    release = manifest(blob)
    model_path, release_path = tmp_path / "logistic.json", tmp_path / "release.json"
    model_path.write_bytes(blob)
    release_path.write_bytes(encoded(release))
    predictor = load_frozen_predictor(model_path, release_path, **bindings())
    assert predictor.release_sha256 == release["release_sha256"]
    malformed = b'{"features": [], "features": []}'
    with pytest.raises(PredictorDenied, match="duplicate|strict JSON"):
        load_frozen_predictor_bytes(malformed, manifest(malformed), **bindings())
    with pytest.raises(PredictorDenied, match="D-hosted"):
        load_frozen_predictor("/mnt/c/invalid.json", release_path, **bindings())


@pytest.mark.parametrize(
    "kind,library,blob",
    [
        ("lightgbm", "lightgbm", b"synthetic native text"),
        ("xgboost", "xgboost", b'{"learner": {}}'),
    ],
)
def test_missing_optional_native_library_is_explicit_denial(monkeypatch, kind, library, blob):
    monkeypatch.setitem(sys.modules, library, None)
    with pytest.raises(PredictorDependencyUnavailable, match=library):
        load_frozen_predictor_bytes(blob, manifest(blob, kind), **bindings())


def test_native_lightgbm_adapter_contract_and_scalar_output(monkeypatch):
    calls = []

    class Booster:
        params = {"device_type": "cpu", "num_threads": 1}

        def __init__(self, *, model_str):
            assert model_str == "synthetic native text"

        def dump_model(self):
            return {"objective": "regression", "num_class": 1}

        def feature_name(self):
            return ["f0", "f1"]

        def num_feature(self):
            return 2

        def predict(self, values, **kwargs):
            calls.append(kwargs)
            return values.sum(axis=1) * 0.001

    monkeypatch.setitem(sys.modules, "lightgbm", SimpleNamespace(Booster=Booster))
    blob = b"synthetic native text"
    predictor = load_frozen_predictor_bytes(blob, manifest(blob, "lightgbm"), **bindings())
    output = predictor.predict({"f1": 2.0, "f0": 3.0})
    assert output["expected_return"] == 0.005
    assert output["confidence"] is None and output["target_weight"] is None
    assert calls == [{"num_threads": 1, "num_iteration": -1}]


def test_native_xgboost_adapter_contract_and_scalar_output(monkeypatch):
    class DMatrix:
        def __init__(self, values, *, feature_names, nthread):
            assert feature_names == ["f0", "f1"] and nthread == 1
            self.values = values

    class Booster:
        feature_names = ["f0", "f1"]

        def __init__(self, *, params):
            assert params == {"device": "cpu", "nthread": 1}

        def load_model(self, blob):
            assert isinstance(blob, bytearray)

        def set_param(self, params):
            assert params == {"device": "cpu", "nthread": 1}

        def save_config(self):
            return json.dumps(
                {
                    "learner": {
                        "objective": {"name": "reg:squarederror"},
                        "learner_model_param": {"num_target": "1", "num_class": "0"},
                        "generic_param": {"device": "cpu"},
                    }
                }
            )

        def num_features(self):
            return 2

        def predict(self, data, *, validate_features):
            assert validate_features is True
            return data.values.sum(axis=1) * 0.001

    monkeypatch.setitem(sys.modules, "xgboost", SimpleNamespace(Booster=Booster, DMatrix=DMatrix))
    blob = b'{"learner": {}}'
    predictor = load_frozen_predictor_bytes(blob, manifest(blob, "xgboost"), **bindings())
    assert predictor.predict({"f0": 3.0, "f1": 2.0})["expected_return"] == 0.005


def test_lightgbm_gpu_artifact_denied_before_native_construction(monkeypatch):
    def forbidden(**kwargs):
        raise AssertionError("non-CPU artifact must be rejected before native construction")

    monkeypatch.setitem(sys.modules, "lightgbm", SimpleNamespace(Booster=forbidden))
    blob = b"tree\n[device_type: gpu]\n"
    with pytest.raises(PredictorDenied, match="CPU"):
        load_frozen_predictor_bytes(blob, manifest(blob, "lightgbm"), **bindings())


@pytest.mark.parametrize("kind", ["lightgbm", "xgboost"])
def test_tree_classification_objective_cannot_masquerade_as_return(monkeypatch, kind):
    class Booster:
        params = {"device_type": "cpu"}

        def __init__(self, **kwargs):
            pass

        def dump_model(self):
            return {"objective": "binary", "num_class": 1}

        def load_model(self, value):
            pass

        def set_param(self, value):
            pass

        def save_config(self):
            return json.dumps({"learner": {"objective": {"name": "binary:logistic"}}})

    monkeypatch.setitem(sys.modules, kind, SimpleNamespace(Booster=Booster))
    blob = b"text" if kind == "lightgbm" else b'{"learner": {}}'
    with pytest.raises(PredictorDenied, match="objective"):
        load_frozen_predictor_bytes(blob, manifest(blob, kind), **bindings())


@pytest.mark.parametrize("kind", ["lightgbm", "xgboost"])
def test_real_native_cpu_synthetic_export_runtime_parity(kind, tmp_path, record_property):
    """A01-authorized engineering fit only: 32 synthetic rows, two small trees."""
    library = pytest.importorskip(kind)
    rng = np.random.default_rng(20261001)
    matrix = rng.normal(size=(32, 2))
    target = 0.003 * matrix[:, 0] - 0.002 * matrix[:, 1] + 0.001 * matrix[:, 0] * matrix[:, 1]
    names = ["f0", "f1"]
    if kind == "lightgbm":
        dataset = library.Dataset(matrix, label=target, feature_name=names)
        native = library.train(
            {
                "objective": "regression",
                "device_type": "cpu",
                "num_threads": 1,
                "seed": 20261001,
                "deterministic": True,
                "force_col_wise": True,
                "num_leaves": 4,
                "max_depth": 2,
                "min_data_in_leaf": 2,
                "max_bin": 16,
                "learning_rate": 0.1,
                "verbosity": -1,
            },
            dataset,
            num_boost_round=2,
        )
        blob = native.model_to_string(num_iteration=2).encode()
        oracle = native.predict(matrix, num_threads=1, num_iteration=2)
        exported = library.Booster(model_str=blob.decode())
        exported_oracle = exported.predict(matrix, num_threads=1, num_iteration=-1)
        assert exported.feature_name() == names
        assert exported.dump_model()["objective"] == "regression"
        assert exported.params["device_type"] == "cpu"
    else:
        dataset = library.DMatrix(matrix, label=target, feature_names=names, nthread=1)
        native = library.train(
            {
                "objective": "reg:squarederror",
                "device": "cpu",
                "nthread": 1,
                "seed": 20261001,
                "tree_method": "hist",
                "max_depth": 2,
                "max_bin": 16,
                "eta": 0.1,
            },
            dataset,
            num_boost_round=2,
        )
        blob = bytes(native.save_raw(raw_format="json"))
        oracle = native.predict(dataset, validate_features=True)
        exported = library.Booster(params={"device": "cpu", "nthread": 1})
        exported.load_model(bytearray(blob))
        exported.set_param({"device": "cpu", "nthread": 1})
        exported_oracle = exported.predict(dataset, validate_features=True)
        configuration = json.loads(exported.save_config())["learner"]
        assert configuration["generic_param"]["device"] == "cpu"
        assert configuration["objective"]["name"] == "reg:squarederror"
        assert exported.feature_names == names
    synthetic_data_sha = hashlib.sha256(matrix.tobytes() + target.tobytes()).hexdigest()
    release = manifest(blob, kind, training_data_sha256=synthetic_data_sha)
    model_path = tmp_path / ("model.txt" if kind == "lightgbm" else "model.json")
    release_path = tmp_path / "release.json"
    model_path.write_bytes(blob)
    release_path.write_bytes(encoded(release))
    predictor = load_frozen_predictor(model_path, release_path, **bindings())
    actual = [predictor.predict({"f1": row[1], "f0": row[0]})["expected_return"] for row in matrix]
    np.testing.assert_allclose(actual, oracle, atol=ABS_TOLERANCE, rtol=REL_TOLERANCE)
    np.testing.assert_allclose(actual, exported_oracle, atol=ABS_TOLERANCE, rtol=REL_TOLERANCE)
    record_property("model_type", kind)
    record_property("library_version", library.__version__)
    record_property("synthetic_rows", 32)
    record_property("features", names)
    record_property("trees", 2)
    record_property("device", "cpu")
    record_property("threads", 1)
    record_property("model_sha256", release["model_sha256"])
    record_property("synthetic_training_data_sha256", synthetic_data_sha)
    record_property("release_sha256", release["release_sha256"])
    record_property("artifact_path", str(model_path))
    record_property("maximum_absolute_prediction_error", float(np.max(np.abs(actual - oracle))))
    # Native feature names remain authoritative even if a caller re-signs a wrong
    # schema. A swapped column order must fail before producing any prediction.
    schema = copy.deepcopy(release["feature_schema"])
    schema.pop("sha256")
    schema["features"].reverse()
    wrong_release = manifest(blob, kind, feature_schema=schema)
    with pytest.raises(PredictorDenied, match="schema"):
        load_frozen_predictor_bytes(blob, wrong_release, **bindings())
    # Re-label a copy of the same tiny native tree model as binary classification;
    # no additional training. Its sigmoid output must never be called gross return.
    if kind == "lightgbm":
        classifier_blob = blob.replace(b"objective=regression", b"objective=binary sigmoid:1")
        classifier_blob = classifier_blob.replace(
            b"[objective: regression]", b"[objective: binary]"
        )
        classifier_blob = classifier_blob.replace(b"[sigmoid: -1]", b"[sigmoid: 1]")
    else:
        classifier = json.loads(blob)
        classifier["learner"]["objective"]["name"] = "binary:logistic"
        parameters = classifier["learner"]["learner_model_param"]
        parameters["base_score"] = "[5E-1]" if parameters["base_score"].startswith("[") else "5E-1"
        classifier_blob = encoded(classifier)
    with pytest.raises(PredictorDenied, match="objective"):
        load_frozen_predictor_bytes(classifier_blob, manifest(classifier_blob, kind), **bindings())
