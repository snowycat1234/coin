"""Thin shared-data fitting and sklearn/LightGBM probes for official TS2Vec."""

import time

import numpy as np
import polars as pl
from lightgbm import LGBMRegressor
from sklearn.linear_model import Ridge
from sklearn.multioutput import MultiOutputRegressor

from .adapters.ts2vec_adapter import TS2VecEncoder
from .dataset import DAY_US, STREAMS, day_us, feature_matrix, protocol


def fitting_rows(dataset, fold, normalizer):
    chunks = []
    for day in dataset.days:
        lower = max(day_us(day), fold.train_start_us)
        upper = min(day_us(day) + DAY_US, fold.fit_cutoff_us)
        if lower >= upper:
            continue
        joint = dataset.joint_rows(lower, upper).filter(
            pl.max_horizontal([f"{s}__available_us" for s in STREAMS]) <= fold.fit_cutoff_us
        )
        chunks.append(normalizer.transform(feature_matrix(joint)))
    values = np.concatenate(chunks).astype(np.float32)
    if len(values) != normalizer.rows:
        raise ValueError("Representation rows must equal the unique common scaler fitting rows")
    return values


def encoded_arrays(encoder, view, indices):
    x = np.empty((len(indices), encoder.output_dim), np.float32)
    y = np.empty((len(indices), 8), np.float32)
    for start in range(0, len(indices), 16):
        selected = indices[start : start + 16]
        samples = [view[int(i)] for i in selected]
        x[start : start + len(selected)] = encoder.encode(np.stack([s["x"] for s in samples]))
        y[start : start + len(selected)] = np.stack([s["y"].reshape(8) for s in samples])
    return x, y


def fit_ts2vec_probes(dataset, fold, checkpoint, *, iterations=600):
    """Both preregistered probes share one fitting-only encoder and the same endpoints."""
    started = time.monotonic()
    features = dataset.fit_fold_scaler(fold)
    targets = dataset.fit_target_scaler(fold)
    encoder = TS2VecEncoder()
    rows = fitting_rows(dataset, fold, features)
    history = encoder.fit_train_series(rows, iterations=iterations)
    encoder.model.save(checkpoint)
    representation_seconds = time.monotonic() - started
    views = {s: dataset.normalized(features, fold, s, targets=targets) for s in ("train", "test")}
    indices = {s: dataset.split_indices(fold, s) for s in views}
    train_x, train_y = encoded_arrays(encoder, views["train"], indices["train"])
    test_x, _ = encoded_arrays(encoder, views["test"], indices["test"])
    results = []
    for config in protocol()["configs"][7:9]:
        begin = time.monotonic()
        if config["kind"] == "frozen-ts2vec-ridge":
            model = Ridge(alpha=config["probe_alpha"])
        else:
            model = MultiOutputRegressor(
                LGBMRegressor(
                    num_leaves=config["num_leaves"],
                    n_estimators=config["n_estimators"],
                    learning_rate=config["learning_rate"],
                    n_jobs=config["n_jobs"],
                    random_state=20261001,
                    verbosity=-1,
                ),
                n_jobs=1,
            )
        model.fit(train_x, train_y)
        predictions = targets.inverse_transform(model.predict(test_x).reshape(-1, 2, 4))
        results.append(
            (
                config["id"],
                predictions,
                indices["test"],
                {
                    "probe_seconds": time.monotonic() - begin,
                    "representation_shared": True,
                    "upstream_pretrain_iterations": iterations,
                    "unique_train_rows": len(rows),
                    "representation_seconds": representation_seconds,
                    "loss_history": history,
                    "feature_scaler": features.receipt(),
                    "target_scaler": targets.receipt(),
                    "checkpoint": str(checkpoint),
                    "gpu_hours": 0,
                },
            )
        )
    return results
