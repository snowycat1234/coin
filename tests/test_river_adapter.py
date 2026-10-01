import importlib.util
import pickle

import numpy as np
import pytest
from river import drift, linear_model, preprocessing

from quant.paths import ROOT
from quant.research_fast.adapters.river_adapter import RiverAdapter
from quant.research_fast.cached_dataset import CachedSequenceDataset
from quant.research_fast.dataset import _sha
from quant.research_fast.labels import LABEL_LAG_US
from quant.research_fast.river_replay import fit_river, replay_comparison

DATASET_SHA = "1" * 64
NORMALIZATION_SHA = "2" * 64
MINUTE = 60_000_000


def adapter():
    return RiverAdapter(DATASET_SHA, "engineering_only", NORMALIZATION_SHA)


def sample_id(decision):
    return _sha((DATASET_SHA, decision))


def predict(model, decision, x=None):
    return model.predict_one(
        sample_id(decision), decision, decision + LABEL_LAG_US,
        np.ones(204) if x is None else x,
    )


def test_official_components_predict_first_and_no_premature_state_updates():
    model = adapter()
    assert isinstance(model.scaler, preprocessing.StandardScaler)
    assert all(isinstance(value, linear_model.LinearRegression) for value in model.models)
    assert all(isinstance(value, drift.ADWIN) for value in model.detectors)
    prediction = predict(model, 0)
    np.testing.assert_array_equal(prediction, np.zeros((2, 4)))
    assert model.learned_samples == 0 and not any(model.scaler.counts.values())
    assert all(detector.width == 0 for detector in model.detectors)
    before = pickle.dumps(model)
    with pytest.raises(ValueError, match="mature"):
        model.learn_one(sample_id(0), np.ones((2, 4)), now_us=LABEL_LAG_US - 1)
    assert pickle.dumps(model) == before
    errors = model.learn_one(sample_id(0), np.ones((2, 4)), now_us=LABEL_LAG_US)
    np.testing.assert_array_equal(errors, np.ones((2, 4)))
    assert model.learned_samples == 1 and not model.pending
    assert set(model.scaler.counts.values()) == {1}
    assert all(detector.width == 1 for detector in model.detectors)
    assert model.weights == (1, 1, .1, .1, 1, 1, .1, .1)


def test_saved_original_input_prediction_and_complete_oldest_label_only(monkeypatch):
    model = adapter()
    x = np.arange(204, dtype=float)
    first = predict(model, 0, x)
    x[:] = 9999
    first[:] = 9999
    predict(model, MINUTE, np.full(204, -500.))
    assert model.pending[0].x == tuple(range(204))
    assert model.pending[0].prediction == (0.,) * 8
    assert not hasattr(model.pending[0], "y")
    inputs_seen, errors_seen = [], []
    scaler_learn = model.scaler.learn_one

    def capture_input(inputs):
        inputs_seen.append(inputs.copy())
        scaler_learn(inputs)

    monkeypatch.setattr(model.scaler, "learn_one", capture_input)
    detector_update = model.detectors[0].update

    def capture_error(error):
        errors_seen.append(error)
        detector_update(error)

    monkeypatch.setattr(model.detectors[0], "update", capture_error)
    with pytest.raises(ValueError, match="Oldest"):
        model.learn_one(sample_id(MINUTE), np.ones((2, 4)), now_us=LABEL_LAG_US + MINUTE)
    for invalid in (np.ones(8), np.full((2, 4), np.nan)):
        with pytest.raises(ValueError, match="eight"):
            model.learn_one(sample_id(0), invalid, now_us=LABEL_LAG_US)
    assert not inputs_seen and not errors_seen
    model.learn_one(sample_id(0), np.full((2, 4), 3.), now_us=LABEL_LAG_US)
    assert inputs_seen == [dict(enumerate(range(204)))] and errors_seen == [3.]
    assert model.pending[0].sample_id == sample_id(MINUTE)


def test_mid_queue_save_restore_matches_uninterrupted_replay_and_binding(tmp_path):
    original = adapter()
    rng = np.random.default_rng(20261001)
    x = rng.normal(size=(18, 204))
    y = rng.normal(size=(18, 2, 4))
    for index in range(5):
        predict(original, index * MINUTE, x[index])
    checkpoint = tmp_path / "river-synthetic-only.pkl"
    original.save(checkpoint)
    restored = RiverAdapter.load(
        checkpoint, dataset_sha256=DATASET_SHA, fold_name="engineering_only",
        normalization_sha256=NORMALIZATION_SHA,
    )
    assert len(restored.pending) == 5
    assert pickle.dumps(original) == pickle.dumps(restored)
    for index in range(5, len(x)):
        now = index * MINUTE
        np.testing.assert_array_equal(
            predict(original, now, x[index]), predict(restored, now, x[index])
        )
        while original.pending and original.pending[0].label_available_us <= now:
            item = original.pending[0]
            target = y[item.decision_us // MINUTE]
            np.testing.assert_array_equal(
                original.learn_one(item.sample_id, target, now_us=now),
                restored.learn_one(item.sample_id, target, now_us=now),
            )
    assert original.learned_samples == restored.learned_samples == 12
    assert original.drift_events == restored.drift_events
    np.testing.assert_array_equal(
        list(original.scaler.means.values()), list(restored.scaler.means.values())
    )
    with pytest.raises(FileExistsError):
        original.save(checkpoint)
    for wrong in ({"dataset_sha256": "3" * 64}, {"fold_name": "wrong"},
                  {"normalization_sha256": "4" * 64}):
        arguments = dict(dataset_sha256=DATASET_SHA, fold_name="engineering_only",
                         normalization_sha256=NORMALIZATION_SHA)
        arguments.update(wrong)
        with pytest.raises(ValueError, match="binding"):
            RiverAdapter.load(checkpoint, **arguments)


def test_future_labels_cannot_change_predictions_before_maturity():
    a, b = adapter(), adapter()
    for index in range(6):
        np.testing.assert_array_equal(predict(a, index * MINUTE), predict(b, index * MINUTE))
    assert a.learned_samples == b.learned_samples == 0
    assert not any(a.scaler.counts.values()) and not any(b.scaler.counts.values())
    a.learn_one(sample_id(0), np.ones((2, 4)), now_us=6 * MINUTE)
    b.learn_one(sample_id(0), np.full((2, 4), 20.), now_us=6 * MINUTE)
    assert not np.array_equal(predict(a, 7 * MINUTE), predict(b, 7 * MINUTE))


def test_invalid_feature_maturity_id_and_clock_are_rejected():
    model = adapter()
    for values in (np.ones(203), np.ones((1, 204)), np.full(204, np.inf)):
        with pytest.raises(ValueError, match="204"):
            predict(model, 0, values)
    with pytest.raises(ValueError, match="common"):
        model.predict_one("bad", 0, LABEL_LAG_US, np.ones(204))
    with pytest.raises(ValueError, match="maturity"):
        model.predict_one(sample_id(0), 0, LABEL_LAG_US - 1, np.ones(204))
    predict(model, 0)
    with pytest.raises(ValueError, match="Chronological"):
        predict(model, 0)
    model.learn_one(sample_id(0), np.ones((2, 4)), now_us=LABEL_LAG_US)
    with pytest.raises(ValueError, match="Chronological"):
        predict(model, MINUTE)
    assert model.predicted_samples == model.learned_samples == 1


def test_common_cached_dataset_replay_and_existing_static_weekly_baselines(tmp_path):
    from quant.research_fast.trainer import fit_tabular

    spec = importlib.util.spec_from_file_location(
        "river_common_fixture", ROOT / "tests/test_fast_dataset.py"
    )
    fixture = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(fixture)
    reference, _ = fixture.write_dataset(tmp_path / "common")
    dataset = CachedSequenceDataset(reference.shards)
    dataset.prepare_index(tmp_path / "cache.i64")
    fold = fixture.mini_fold()
    checkpoint = tmp_path / "common-river-synthetic.pkl"
    online = fit_river(dataset, fold, checkpoint)
    static = fit_tabular(dataset, fold, {"id": "RIDGE-1", "kind": "ridge", "alpha": 1.})
    from quant.research_fast.dataset import protocol
    weekly = fit_tabular(dataset, fold, protocol()["configs"][1])
    comparison = replay_comparison(
        dataset, fold, static_result=static, weekly_xgb_result=weekly, online_result=online
    )
    assert [result[0] for result in comparison] == ["RIDGE-1", "RIVER-1", "XGB-S"]
    assert comparison[2][3]["in_test_refit_count"] == 0
    prediction, indices, receipt = online
    assert prediction.shape == (len(indices), 2, 4) and np.isfinite(prediction).all()
    assert receipt["pending_labels"] == 0 and receipt["gpu_hours"] == 0
    assert receipt["mature_learned_samples"] == (
        receipt["training_endpoints"] + receipt["test_endpoints"]
    )
    restored = RiverAdapter.load(
        checkpoint, dataset_sha256=dataset.contract_sha256, fold_name=fold.name,
        normalization_sha256=receipt["normalization_sha256"],
    )
    assert set(restored.scaler.counts.values()) == {receipt["mature_learned_samples"]}
    assert restored.last_learn_label_available_us <= fold.test_end_us
    scalers = (receipt["feature_scaler"], receipt["target_scaler"])
    assert scalers[0]["fit_last_us"] <= fold.fit_cutoff_us
    assert scalers[1]["fit_last_label_available_us"] <= fold.fit_cutoff_us
    with pytest.raises(ValueError, match="identical"):
        replay_comparison(
            dataset, fold, static_result=(static[0], static[1][::-1], static[2]),
            weekly_xgb_result=weekly, online_result=online,
        )
