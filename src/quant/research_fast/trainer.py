"""One small training path for the common FR64 dataset and upstream encoders."""

from __future__ import annotations

import copy
import time

import numpy as np
import torch
from sklearn.linear_model import Ridge
from torch.utils.data import DataLoader, Subset
from xgboost import XGBRegressor

from .dataset import tabular_view

SEED = 20261001
TASK_WEIGHTS = torch.tensor([1, 1, .1, .1], dtype=torch.float32).reshape(1, 1, 4)


def tabular_arrays(view, indices):
    """Compact 204 features per endpoint; never materialize the full sequence tensor."""
    x, y = np.empty((len(indices), 204), np.float32), np.empty((len(indices), 8), np.float32)
    for offset, index in enumerate(indices):
        sample = view[int(index)]
        x[offset], y[offset] = tabular_view(sample["x"]), sample["y"].reshape(8)
    return x, y


def fit_tabular(dataset, fold, config):
    feature_scaler = dataset.fit_fold_scaler(fold)
    target_scaler = dataset.fit_target_scaler(fold)
    train = dataset.normalized(feature_scaler, fold, "train", targets=target_scaler)
    x, y = tabular_arrays(train, dataset.split_indices(fold, "train"))
    if config["kind"] == "ridge":
        model = Ridge(alpha=config["alpha"])
    elif config["kind"] == "xgboost":
        settings = {key: value for key, value in config.items() if key not in ("id", "kind")}
        model = XGBRegressor(**settings, random_state=SEED)
    else:
        raise ValueError("Only the three preregistered tabular configs")
    started = time.monotonic()
    model.fit(x, y)
    test = dataset.normalized(feature_scaler, fold, "test", targets=target_scaler)
    indices = dataset.split_indices(fold, "test")
    test_x, _ = tabular_arrays(test, indices)
    prediction = target_scaler.inverse_transform(model.predict(test_x).reshape(-1, 2, 4))
    return prediction, indices, {
        "fit_evaluation_seconds": time.monotonic() - started, "training_endpoints": len(x),
        "test_endpoints": len(indices), "feature_scaler": feature_scaler.receipt(),
        "target_scaler": target_scaler.receipt(), "gpu_hours": 0,
    }


def sequence_model(config_id):
    from .adapters.common import SequenceModel
    if config_id in ("TCN-S", "TCN-M"):
        from .adapters.tcn_adapter import TCNEncoder
        encoder = TCNEncoder(config_id)
    elif config_id in ("TLOB-1", "MLPLOB-1"):
        from .adapters.tlob_adapter import MLPLOBEncoder, TLOBEncoder
        encoder = TLOBEncoder() if config_id == "TLOB-1" else MLPLOBEncoder()
    else:
        raise ValueError("Upstream sequence config not adopted")
    return SequenceModel(encoder)


def fit_sequence(dataset, fold, config_id, checkpoint, *, epochs=10, patience=3):
    """CPU-only initial path; AMP remains off until GPU resources are agreed."""
    torch.manual_seed(SEED)
    np.random.seed(SEED)
    torch.set_num_threads(2)
    feature_scaler = dataset.fit_fold_scaler(fold)
    target_scaler = dataset.fit_target_scaler(fold)
    views = {split: dataset.normalized(feature_scaler, fold, split, targets=target_scaler)
             for split in ("train", "validation", "test")}
    indices = {split: dataset.split_indices(fold, split) for split in views}
    require_samples = all(len(value) > 0 for value in indices.values())
    if not require_samples:
        raise ValueError("Common chronological train/validation/test required")
    generator = torch.Generator().manual_seed(SEED)
    loaders = {split: DataLoader(Subset(view.as_torch_dataset(), indices[split].tolist()),
                                batch_size=16, num_workers=0, shuffle=split == "train",
                                generator=generator) for split, view in views.items()}
    model = sequence_model(config_id).train()
    optimizer = torch.optim.AdamW(model.parameters(), lr=1e-3, weight_decay=1e-4)
    best, failures, history, best_state = float("inf"), 0, [], None
    started = time.monotonic()
    for epoch in range(epochs):
        model.train()
        optimizer.zero_grad(set_to_none=True)
        for step, batch in enumerate(loaders["train"]):
            output = model(batch["x"])
            loss = (((output - batch["y"]) ** 2) * TASK_WEIGHTS).mean()
            if not torch.isfinite(loss):
                raise ValueError("Nonfinite training loss")
            group_start = step // 4 * 4
            group_size = min(4, len(loaders["train"]) - group_start)
            (loss / group_size).backward()
            if (step + 1) % 4 == 0 or step + 1 == len(loaders["train"]):
                torch.nn.utils.clip_grad_norm_(model.parameters(), 1)
                optimizer.step()
                optimizer.zero_grad(set_to_none=True)
        model.eval()
        total, count = 0., 0
        with torch.no_grad():
            for batch in loaders["validation"]:
                loss = (((model(batch["x"]) - batch["y"]) ** 2) * TASK_WEIGHTS).mean()
                total += float(loss) * len(batch["x"])
                count += len(batch["x"])
        score = total / count
        history.append({"epoch": epoch + 1, "validation_weighted_mse": score})
        if score < best:
            best, failures = score, 0
            best_state = copy.deepcopy(model.state_dict())
            torch.save(best_state, checkpoint)
        else:
            failures += 1
            if failures >= patience:
                break
    if best_state is None:
        raise ValueError("No finite validation checkpoint")
    model.load_state_dict(best_state)
    model.eval()
    chunks = []
    with torch.no_grad():
        for batch in loaders["test"]:
            chunks.append(model(batch["x"]).numpy())
    predictions = target_scaler.inverse_transform(np.concatenate(chunks))
    return predictions, indices["test"], {
        "fit_evaluation_seconds": time.monotonic() - started, "epochs": history,
        "validation_best_weighted_mse": best, "checkpoint": str(checkpoint), "gpu_hours": 0,
        "feature_scaler": feature_scaler.receipt(), "target_scaler": target_scaler.receipt(),
    }
