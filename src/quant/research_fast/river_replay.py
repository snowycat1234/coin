"""Thin RIVER-1 chronological replay on the accepted common dataset and folds."""

from __future__ import annotations

import time

import numpy as np

from .adapters.river_adapter import RiverAdapter
from .cached_dataset import CachedSequenceDataset
from .dataset import DAY_US, Fold, _sha, protocol, tabular_view


def fit_river(dataset: CachedSequenceDataset, fold: Fold, checkpoint=None):
    """Match the shared trainer result API; report predictions in original units.

    Warm-up consumes the same fitting endpoints as the batch baselines. The
    external feature/target scalers are fitted once on the common train subset.
    Validation endpoints are excluded from online learning. During test each
    prediction occurs before that clock tick's matured-label updates.
    """
    if not isinstance(dataset, CachedSequenceDataset) or not isinstance(fold, Fold):
        raise ValueError("The common CachedSequenceDataset and Fold are required")
    started = time.monotonic()
    features, targets = dataset.fit_fold_scaler(fold), dataset.fit_target_scaler(fold)
    normalization_sha256 = _sha((features.receipt(), targets.receipt()))
    adapter = RiverAdapter(dataset.contract_sha256, fold.name, normalization_sha256)
    indices = {split: dataset.split_indices(fold, split) for split in ("train", "test")}
    if any(len(selected) == 0 for selected in indices.values()):
        raise ValueError("Common chronological train and test endpoints required")
    queued_indices = {}
    predictions = []
    for split in ("train", "test"):
        view = dataset.normalized(features, fold, split, targets=targets)

        def release(now_us, view=view):
            while adapter.pending and adapter.pending[0].label_available_us <= now_us:
                item = adapter.pending[0]
                # Re-read only at maturity. The queued adapter state contains no labels.
                mature_sample = view[queued_indices[item.sample_id]]
                if (
                    mature_sample["sample_id"] != item.sample_id
                    or mature_sample["label_available_us"] != item.label_available_us
                    or mature_sample["target_units"] != "standardized"
                ):
                    raise ValueError("Mature common label binding changed")
                adapter.learn_one(item.sample_id, mature_sample["y"], now_us=now_us)
                del queued_indices[item.sample_id]

        for index in indices[split]:
            sample = view[int(index)]
            prediction = adapter.predict_one(
                sample["sample_id"], sample["decision_us"], sample["label_available_us"],
                tabular_view(sample["x"]),
            )
            queued_indices[sample["sample_id"]] = int(index)
            if split == "test":
                predictions.append(prediction)
            release(sample["decision_us"])
        release(fold.interval(split)[2])
        if adapter.pending:
            raise ValueError("Common split ended before all complete labels matured")
    if checkpoint is not None:
        adapter.save(checkpoint)
    evidence = {
        "fit_evaluation_seconds": time.monotonic() - started,
        "training_endpoints": len(indices["train"]),
        "test_endpoints": len(indices["test"]),
        "predicted_samples": adapter.predicted_samples,
        "mature_learned_samples": adapter.learned_samples,
        "pending_labels": len(adapter.pending),
        "drift_events": adapter.drift_events,
        "last_learn_label_available_us": adapter.last_learn_label_available_us,
        "feature_scaler": features.receipt(),
        "target_scaler": targets.receipt(),
        "normalization_sha256": normalization_sha256,
        "river_version": adapter.binding[3],
        "internal_scaler": "official River StandardScaler; mature examples only",
        "error_for_adwin": "absolute standardized error of saved original prediction",
        "update_order": "predict -> complete label maturity -> learn_one",
        "validation_labels_learned": False,
        "train_predictions": "warm-up only; external scalers fixed at train cutoff",
        "checkpoint": None if checkpoint is None else str(checkpoint),
        "gpu_hours": 0,
    }
    return targets.inverse_transform(np.stack(predictions)), indices["test"], evidence


def replay_comparison(dataset, fold, *, static_result, weekly_xgb_result, online_result):
    """Reuse existing RIDGE-1/XGB-S results without adding configurations or refits.

    The weekly batch schedule is each common train cutoff, followed by a test
    of at most seven days. Therefore no second refit occurs inside one fold.
    Calling the shared fixed XGB-S trainer separately for each preregistered
    fold supplies this policy; skipped weeks have no synthetic result/state.
    """
    if fold.test_end_us - fold.test_start_us > 7 * DAY_US:
        raise ValueError("Weekly comparison requires the common at-most-seven-day test fold")
    expected = dataset.split_indices(fold, "test")
    reference = online_result[2]
    results = []
    configurations = {config["id"]: config for config in protocol()["configs"]}
    for config_id, policy, result in (
        ("RIDGE-1", "static linear", static_result),
        ("RIVER-1", "online linear", online_result),
        ("XGB-S", "weekly XGB refit", weekly_xgb_result),
    ):
        prediction, selected, receipt = result
        if (
            not np.array_equal(selected, expected)
            or np.asarray(prediction).shape != (len(expected), 2, 4)
            or not np.isfinite(prediction).all()
            or any(receipt.get(key) != reference.get(key) for key in (
                "feature_scaler", "target_scaler"
            ))
        ):
            raise ValueError("Comparison requires identical common endpoints and frozen scalers")
        details = {**receipt, "comparison_policy": policy, "config": configurations[config_id]}
        if config_id == "XGB-S":
            details.update({"refit_every_utc_days": 7, "in_test_refit_count": 0})
        results.append((config_id, prediction, selected, details))
    return results
