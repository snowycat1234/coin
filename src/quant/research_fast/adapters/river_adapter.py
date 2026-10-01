"""RIVER-1: official River components with complete-label maturity gating."""

from __future__ import annotations

import pickle
from collections import deque
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import river
from river import drift, linear_model, preprocessing

from ..dataset import _sha, protocol
from ..labels import LABEL_LAG_US

VERSION = "0.26.1"


@dataclass(frozen=True)
class PendingPrediction:
    sample_id: str
    decision_us: int
    label_available_us: int
    x: tuple[float, ...]
    prediction: tuple[float, ...]


class RiverAdapter:
    """Eight official regressors; no target is retained before its maturity.

    The external shared train-only normalization happens before this adapter.
    Its official River scaler is an additional model component, updated once
    per matured example. Explicit API calls avoid Pipeline's implicit updates.
    ADWIN observes the saved prediction error, and never resets/tunes a model.
    """

    def __init__(self, dataset_sha256: str, fold_name: str, normalization_sha256: str):
        if river.__version__ != VERSION:
            raise ValueError("RIVER-1 requires the registered River 0.26.1 release")
        if any(len(value) != 64 for value in (dataset_sha256, normalization_sha256)) or not (
            fold_name
        ):
            raise ValueError("Dataset, fold and external normalization binding required")
        self.binding = (dataset_sha256, fold_name, normalization_sha256, VERSION)
        self.scaler = preprocessing.StandardScaler()
        self.models = [linear_model.LinearRegression() for _ in range(8)]
        self.detectors = [drift.ADWIN() for _ in range(8)]
        self.weights = tuple(protocol()["loss"]["per_spot_task_weights"] * 2)
        self.pending: deque[PendingPrediction] = deque()
        self.clock_us = -1
        self.last_decision_us = -1
        self.predicted_samples = 0
        self.learned_samples = 0
        self.last_learn_label_available_us = None
        self.drift_events: list[dict] = []

    def predict_one(self, sample_id: str, decision_us: int, label_available_us: int, x):
        """Predict from 204 common features; store an immutable input/prediction copy."""
        values = np.asarray(x, dtype=np.float64)
        if values.shape != (204,) or not np.isfinite(values).all():
            raise ValueError("Exactly 204 finite shared tabular features required")
        if (
            decision_us <= self.last_decision_us
            or decision_us < self.clock_us
            or label_available_us != decision_us + LABEL_LAG_US
            or sample_id != _sha((self.binding[0], decision_us))
        ):
            raise ValueError("Chronological common sample ID and complete maturity required")
        inputs = dict(enumerate(values.tolist()))
        transformed = self.scaler.transform_one(inputs)
        prediction = tuple(float(model.predict_one(transformed)) for model in self.models)
        if not np.isfinite(prediction).all():
            raise ValueError("Nonfinite official River prediction")
        self.pending.append(
            PendingPrediction(sample_id, decision_us, label_available_us, tuple(values), prediction)
        )
        self.last_decision_us = self.clock_us = decision_us
        self.predicted_samples += 1
        return np.array(prediction).reshape(2, 4)

    def learn_one(self, sample_id: str, y, *, now_us: int):
        """Only the oldest complete matured label may update any River component."""
        if (
            not self.pending
            or self.pending[0].sample_id != sample_id
            or now_us < self.clock_us
            or now_us < self.pending[0].label_available_us
        ):
            raise ValueError("Oldest complete label must mature before learn_one")
        values = np.asarray(y, dtype=np.float64)
        if values.shape != (2, 4) or not np.isfinite(values).all():
            raise ValueError("All eight finite standardized targets required")
        item = self.pending[0]
        errors = np.abs(np.array(item.prediction) - values.reshape(8))
        if not np.isfinite(errors).all():
            raise ValueError("Nonfinite matured prediction error")
        # Use the original input saved at prediction, never the current input.
        inputs = dict(enumerate(item.x))
        self.scaler.learn_one(inputs)
        transformed = self.scaler.transform_one(inputs)
        for index, (model, detector, target, error, weight) in enumerate(
            zip(self.models, self.detectors, values.reshape(8), errors, self.weights, strict=True)
        ):
            model.learn_one(transformed, float(target), w=weight)
            detector.update(float(error))
            if detector.drift_detected:
                self.drift_events.append(
                    {"sample_id": sample_id, "target": index, "observed_us": now_us}
                )
        self.pending.popleft()
        self.clock_us = now_us
        self.learned_samples += 1
        self.last_learn_label_available_us = item.label_available_us
        return errors.reshape(2, 4)

    def save(self, path: Path):
        """Exclusive local checkpoint, including pending inputs and upstream states."""
        with Path(path).open("xb") as handle:
            pickle.dump(self, handle, protocol=pickle.HIGHEST_PROTOCOL)

    @classmethod
    def load(cls, path: Path, *, dataset_sha256: str, fold_name: str, normalization_sha256: str):
        """Load only trusted task-owned pickle, and require identical data/scaler binding."""
        with Path(path).open("rb") as handle:
            result = pickle.load(handle)
        if not isinstance(result, cls) or result.binding != (
            dataset_sha256, fold_name, normalization_sha256, river.__version__
        ) or river.__version__ != VERSION:
            raise ValueError("Checkpoint dataset/fold/normalization/version binding mismatch")
        return result
