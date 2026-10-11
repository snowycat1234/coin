"""Read-only attempt2 training diagnostics; no validation, forward pass or steps."""

import argparse
import hashlib
import io
import json
import time
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq
import torch

from .core import DAY_US, SYMBOLS, sample_index, trend_features
from .run import sha, utc_us, write_json
from .sharpe import PositionLSTM

ARCHIVE_SHA = "bdbcdc488fc4245c1fb6b433df1fc4bf806a120433db71e180816119cebbcc30"
NAMES = (
    "lstm.weight_ih_l0",
    "lstm.weight_hh_l0",
    "lstm.bias_ih_l0",
    "lstm.bias_hh_l0",
    "output.weight",
    "output.bias",
)


def adam_update_estimate(mean, square, step, lr, betas, epsilon):
    """Algebraic last update from saved moments, not a proposed optimizer step."""
    mean, square = np.asarray(mean, dtype=float), np.asarray(square, dtype=float)
    if not np.isfinite(mean).all() or not np.isfinite(square).all() or (square < 0).any():
        raise ValueError("Invalid saved Adam moments")
    if step < 1:
        raise ValueError("Adam state must contain a mature step")
    return (
        -lr * mean / (1 - betas[0] ** step) / (np.sqrt(square / (1 - betas[1] ** step)) + epsilon)
    )


def read_training_close(archive):
    raw_archive = archive.read_bytes()
    assert sha(raw_archive) == ARCHIVE_SHA
    calendar = np.arange(utc_us("2020-01-01"), utc_us("2022-12-31"), DAY_US)
    close = np.full((len(calendar), 5), np.nan)
    with zipfile.ZipFile(io.BytesIO(raw_archive)) as z:
        members = json.loads(z.read("MEMBERS.json"))["files"]
        for asset, symbol in enumerate(SYMBOLS):
            name = f"source_tables_not_model_inputs/daily_features/{symbol}.parquet"
            raw = z.read(name)
            assert sha(raw) == members[name]["SHA256"] and len(raw) == members[name]["bytes"]
            timestamp_type = pq.read_schema(io.BytesIO(raw)).field("dt").type
            assert timestamp_type.tz in (None, "UTC")
            tz = timezone.utc if timestamp_type.tz else None
            # UTC bar start + one day must precede the training cutoff. Returned
            # rows exclude validation; opaque container/member bytes are hashed.
            table = pq.read_table(
                io.BytesIO(raw),
                columns=["dt", "close", "complete_kline", "symbol"],
                filters=[
                    ("dt", ">=", pa.scalar(datetime(2020, 1, 1, tzinfo=tz), type=timestamp_type)),
                    ("dt", "<", pa.scalar(datetime(2022, 12, 31, tzinfo=tz), type=timestamp_type)),
                ],
            ).sort_by([("dt", "ascending")])
            stamps = table["dt"].to_numpy().astype("datetime64[us]").astype("int64")
            assert len(np.unique(stamps)) == len(stamps)
            assert set(table["symbol"].to_pylist()) == {symbol}
            assert (stamps + DAY_US < utc_us("2023-01-01")).all()
            p = table["close"].to_numpy().astype(float)
            observed = np.array(table["complete_kline"].to_pylist(), dtype=bool)
            p[~observed | ~np.isfinite(p) | (p <= 0)] = np.nan
            close[np.searchsorted(calendar, stamps), asset] = p
    return calendar + DAY_US, close


def batch_diagnostics(rows, seed):
    rng = np.random.default_rng(seed)
    digest = hashlib.sha256()
    counts = np.zeros(len(rows), dtype=int)
    duplicate, same_day, overlapping, fractional_overlap = [], [], [], []
    upper = np.triu_indices(128, 1)
    unique_dates = []
    for _ in range(1024):
        selected = rng.integers(0, len(rows), size=128)
        digest.update(selected.astype("<i8").tobytes())
        np.add.at(counts, selected, 1)
        current = rows[selected]
        distance = np.abs(current[:, 0, None] - current[None, :, 0])[upper]
        same_asset = (current[:, 1, None] == current[None, :, 1])[upper]
        duplicate.append(1 - len(np.unique(selected)) / 128)
        same_day.append(float((distance == 0).mean()))
        overlapping.append(float((same_asset & (distance < 63)).mean()))
        fractional_overlap.append(float((same_asset * np.maximum(63 - distance, 0) / 63).mean()))
        unique_dates.append(len(np.unique(current[:, 0])))
    return {
        "seed": seed,
        "draws": 1024 * 128,
        "endpoint_epoch_equivalent": 1024 * 128 / len(rows),
        "unique_endpoints_visited": int((counts > 0).sum()),
        "visits_min_max": [int(counts.min()), int(counts.max())],
        "mean_within_batch_duplicate_fraction": float(np.mean(duplicate)),
        "mean_unique_decision_dates_per_batch": float(np.mean(unique_dates)),
        "mean_pair_same_date_fraction": float(np.mean(same_day)),
        "mean_pair_same_asset_overlapping_63day_input_fraction": float(np.mean(overlapping)),
        "mean_pair_fraction_of_identical_input_rows": float(np.mean(fractional_overlap)),
        "batch_indices_sha256": digest.hexdigest(),
        "final_numpy_rng": rng.bit_generator.state,
        "statistical_effective_sample_size": "UNKNOWN; pair overlap is not an ESS estimator",
    }


def inspect_checkpoint(cp, fit):
    assert cp["updates"] == 1024 and cp["seed"] == fit["seed"]
    assert tuple(cp["model"]) == NAMES
    groups = cp["optimizer"]["param_groups"]
    assert len(groups) == 1
    group = groups[0]
    assert len(group["params"]) == len(NAMES)
    assert group["lr"] == 0.001 and tuple(group["betas"]) == (0.9, 0.999)
    assert group["eps"] == 1e-8 and group["weight_decay"] == 0
    assert not group["amsgrad"] and not group["maximize"]
    torch.manual_seed(fit["seed"])
    initial = PositionLSTM().state_dict()
    assert sha(b"".join(v.numpy().tobytes() for v in initial.values())) == fit["initial_sha256"]
    per_parameter = {}
    vectors, estimates, movement = [], [], []
    for name, identity in zip(NAMES, group["params"], strict=True):
        value = cp["model"][name].numpy().astype(float)
        state = cp["optimizer"]["state"][identity]
        assert int(state["step"]) == 1024 and np.isfinite(value).all()
        mean = state["exp_avg"].numpy()
        square = state["exp_avg_sq"].numpy()
        update = adam_update_estimate(mean, square, 1024, 0.001, (0.9, 0.999), 1e-8)
        assert update.shape == value.shape
        per_parameter[name] = {
            "weight_l2": float(np.linalg.norm(value)),
            "last_update_l2_estimate": float(np.linalg.norm(update)),
            "maximum_absolute_coordinate_update_estimate": float(np.abs(update).max()),
            "saved_gradient_first_moment_l2": float(np.linalg.norm(mean)),
            "saved_gradient_second_moment_sum": float(square.sum()),
        }
        vectors.append(value.ravel())
        estimates.append(update.ravel())
        movement.append((value - initial[name].numpy()).ravel())
    weights, updates = np.concatenate(vectors), np.concatenate(estimates)
    if fit["arm"] == "trend":
        dormant = cp["model"][NAMES[0]][:, 8:]
        assert torch.equal(dormant, initial[NAMES[0]][:, 8:])
    curve = fit["diagnostics"]
    full_loss = [
        -np.sqrt(365) * p["captured_mean"] / np.sqrt(p["captured_variance"] + 1e-9) for p in curve
    ]
    sr = [p["full_train_pooled_sharpe"] for p in curve]
    gradient = [p["last_preclip_gradient_norm"] for p in curve[1:]]
    minibatch_loss = [p["last_minibatch_loss"] for p in curve[1:]]
    assert np.isfinite(full_loss + sr + gradient + minibatch_loss).all()
    return {
        "arm": fit["arm"],
        "seed": fit["seed"],
        "optimizer_steps": 1024,
        "parameters": int(len(weights)),
        "saved_state": "COMPLETE_MODEL_ADAM_MOMENTS_AND_TORCH_NUMPY_RNG",
        "optimizer_configuration": {k: group[k] for k in ["lr", "betas", "eps", "weight_decay"]},
        "weight_l2": float(np.linalg.norm(weights)),
        "displacement_from_seeded_initial_l2": float(np.linalg.norm(np.concatenate(movement))),
        "last_update_l2_estimate": float(np.linalg.norm(updates)),
        "last_update_to_current_weight_l2_ratio": float(
            np.linalg.norm(updates) / np.linalg.norm(weights)
        ),
        "per_parameter": per_parameter,
        "regularized_full_training_loss_curve": [
            {"update": p["update"], "loss": float(loss)}
            for p, loss in zip(curve, full_loss, strict=True)
        ],
        "all_recorded_full_loss_checks_improve": bool(np.all(np.diff(full_loss) < 0)),
        "last_128_full_loss_improvement": float(full_loss[-2] - full_loss[-1]),
        "last_256_full_loss_improvement": float(full_loss[-3] - full_loss[-1]),
        "last_256_unregularized_sr_improvement": float(sr[-1] - sr[-3]),
        "recorded_minibatch_loss_range": [float(min(minibatch_loss)), float(max(minibatch_loss))],
        "recorded_preclip_gradient_range": [float(min(gradient)), float(max(gradient))],
        "recorded_gradient_checks_clipped": int(sum(g > 1 for g in gradient)),
        "recorded_gradient_checks": len(gradient),
        "all_update_gradients_clipped_fraction": "UNKNOWN; only eight points were recorded",
        "final_epsilon_fraction": curve[-1]["epsilon_denominator_fraction"],
        "final_position_variance": curve[-1]["position_variance"],
        "final_saturation_fraction": curve[-1]["position_saturated_fraction"],
        "historical_update_norm_trajectory": "UNKNOWN; only final moments are saved",
        "intermediate_checkpoints": "NOT_SAVED; final1024 only",
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--state", type=Path, required=True)
    parser.add_argument(
        "--models", type=Path, default=Path("/workspace/slow-momentum-sharpe-state")
    )
    parser.add_argument(
        "--archive", type=Path, default=Path("/workspace/slow-momentum-state/source/features.zip")
    )
    args = parser.parse_args()
    torch.set_num_threads(1)
    torch.set_grad_enabled(False)
    started = time.monotonic()
    assert args.state.resolve().is_relative_to(Path("/workspace"))
    assert not args.state.resolve().is_relative_to(args.models.resolve())
    assert not args.state.resolve().is_relative_to(Path("/workspace/slow-momentum-state"))
    args.state.mkdir(parents=True, exist_ok=True)
    available, close = read_training_close(args.archive)
    features, returns, vol = trend_features(close)
    rows = sample_index(
        features, returns, vol, available, utc_us("2021-01-01"), utc_us("2023-01-01")
    )
    assert len(rows) == 2526 and (available[rows[:, 0] + 1] < utc_us("2023-01-01")).all()
    batches = {seed: batch_diagnostics(rows, seed) for seed in [2001, 2002, 2003]}
    files, fits, rngs = {}, [], {}
    for seed in batches:
        for arm in ["trend", "trend_cpd"]:
            fit_path = args.models / f"FIT_{arm}_{seed}.json"
            fit = json.loads(fit_path.read_text())
            path = args.models / f"{arm}-seed{seed}.pt"
            files[str(fit_path)] = sha(fit_path.read_bytes())
            files[str(path)] = sha(path.read_bytes())
            assert files[str(path)] == fit["checkpoint_sha256"]
            cp = torch.load(path, map_location="cpu", weights_only=True)
            assert cp["numpy_rng"] == batches[seed]["final_numpy_rng"]
            assert (
                cp["batch_indices_sha256"]
                == fit["batch_indices_sha256"]
                == batches[seed]["batch_indices_sha256"]
            )
            rngs.setdefault(seed, []).append(cp["torch_rng"])
            fits.append(inspect_checkpoint(cp, fit))
    assert all(torch.equal(pair[0], pair[1]) for pair in rngs.values())
    for path, identity in files.items():
        assert sha(Path(path).read_bytes()) == identity
    report = {
        "schema": "TRAINING_ONLY_READONLY_DIAGNOSTIC_V1",
        "fit_source_commit": json.loads((args.models / "ATTEMPT.json").read_text())[
            "source_commit"
        ],
        "diagnostic_source_sha256": sha(Path(__file__).read_bytes()),
        "archive_sha256": ARCHIVE_SHA,
        "training_endpoint_count": len(rows),
        "training_unique_decision_dates": len(np.unique(rows[:, 0])),
        "earliest_latest_training_available_us": [
            int(available[rows[:, 0]].min()),
            int(available[rows[:, 0]].max()),
        ],
        "latest_training_label_end_us": int(available[rows[:, 0] + 1].max()),
        "asset_endpoint_counts": {s: int((rows[:, 1] == i).sum()) for i, s in enumerate(SYMBOLS)},
        "sharpe_estimator": (
            "Full training pooled2526 asset endpoints; batch128 with replacement; "
            "calendar ESS UNKNOWN"
        ),
        "data_read_scope": (
            "Opaque archive/member hash verification; "
            "Parquet query returns only bars with dt+1day<2023-01-01"
        ),
        "batches": list(batches.values()),
        "fits": fits,
        "input_files_unchanged_sha256": files,
        "validation_queries": 0,
        "model_forward_passes": 0,
        "gradient_evaluations": 0,
        "optimizer_steps": 0,
        "new_gp_scaler_fits": 0,
        "new_wallets": 0,
        "interpretation": (
            "Recorded full regularized training objective still improves in all six fits; "
            "no observed numerical failure; convergence and generalization remain unestablished"
        ),
        "seconds": time.monotonic() - started,
    }
    write_json(args.state / "DIAGNOSTIC.json", report)
    print(
        json.dumps(
            {
                k: report[k]
                for k in [
                    "training_endpoint_count",
                    "training_unique_decision_dates",
                    "asset_endpoint_counts",
                    "seconds",
                    "interpretation",
                ]
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
