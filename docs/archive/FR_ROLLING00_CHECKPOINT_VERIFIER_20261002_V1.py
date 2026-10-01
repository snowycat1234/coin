"""Independent byte/ID/scaler/artifact verification of the diagnostic, no fitting."""
import argparse
import json
import os
import pickle
import sys
from datetime import UTC, datetime
from pathlib import Path

import numpy as np

from quant import resources
from quant.paths import ROOT, STATE
from quant.research_fast.dataset import (
    FoldNormalizer, TargetNormalizer, _sha, file_sha, make_folds, tabular_view,
)

sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / ".cache"))
import fr_run_first_round as accepted
import fr_rolling00_full_window_diagnostic_v6 as diagnostic

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--run-dir", type=Path, required=True)
args = parser.parse_args()
resources.status()
run = args.run_dir.resolve()
accepted.require(run.is_relative_to(STATE.resolve()), "Owned STATE required")
binding = json.loads((run / "RUN_BINDING.json").read_text())
dataset, manifests = diagnostic.preflight()
accepted.require(binding["sources"] == diagnostic.binding_sources()
                 and binding["runtime"] == accepted.runtime()
                 and binding["manifests"] == manifests, "Source/runtime/manifest binding changed")
accepted.attach_index(dataset, run, binding)
fold = make_folds()[0]
native = diagnostic.native_dataset(run, binding, dataset)
rows, truth_hashes, scaler_hashes, sample_hashes, process_scopes = {}, set(), set(), set(), {}
sample_views = None
sample_positions = np.array([0, 1, 9773 // 2, 9773 // 2 + 1, 9773 - 2, 9773 - 1])
checkpoint_checks, representation = {}, None


def restored_scaler(receipt):
    from sklearn.preprocessing import StandardScaler
    scaler = StandardScaler()
    scaler.mean_ = np.asarray(receipt["mean"], dtype=np.float64)
    scaler.scale_ = np.asarray(receipt["scale"], dtype=np.float64)
    scaler.var_ = np.asarray(receipt["variance"], dtype=np.float64)
    scaler.n_features_in_ = len(scaler.mean_)
    scaler.n_samples_seen_ = receipt["rows"]
    return scaler


for config in accepted.IDS:
    receipt = accepted.verified(run, fold, config, binding, dataset)
    accepted.require(receipt is not None, f"Missing completed diagnostic config: {config}")
    evaluation = receipt["evaluation"]
    prediction_path = next(run / p for p in receipt["artifacts"] if p.endswith("/predictions.npy"))
    output = prediction_path.parent
    truth = np.load(output / "truth.npy", allow_pickle=False)
    decisions = np.load(output / "decision_us.npy", allow_pickle=False)
    accepted.require(truth.shape == (9773, 2, 4)
                     and np.array_equal(decisions, dataset.index[dataset.split_indices(fold, "test")])
                     and evaluation["economics"]["2"]["days"] == 7,
                     "Actual full original test window changed")
    truth_hashes.add(file_sha(output / "truth.npy"))
    sample_hashes.add(receipt["sample_ids_sha256"])
    measured = evaluation["metadata"]["resources"]
    scaler_hashes.add(_sha((measured["feature_scaler"], measured["target_scaler"])))
    scope = measured["process_peak_scope"]
    process_scopes[scope] = {"reported_worker_seconds_after_model_imports": measured["worker_seconds"],
        "process_peak_RAM_bytes": measured["process_peak_RAM_bytes"]}
    rows[config] = {"completion_sha256": file_sha(run / fold.name / config / "COMPLETE.json"),
        "test_endpoints": len(decisions), "prediction_sha256": file_sha(prediction_path),
        "checkpoint_artifacts": {p: sha for p, sha in receipt["artifacts"].items()
                                 if Path(p).suffix in (".pt", ".pkl")},
        "epochs": measured.get("epochs"), "upstream_iterations": measured.get("upstream_pretrain_iterations")}
    accepted.require(rows[config]["checkpoint_artifacts"], "Actual model checkpoint missing")
    if sample_views is None:
        features, targets = measured["feature_scaler"], measured["target_scaler"]
        feature_normalizer = FoldNormalizer(restored_scaler(features), features["dataset_sha256"],
            features["fold"], features["fit_first_us"], features["fit_last_us"], features["rows"])
        target_normalizer = TargetNormalizer(restored_scaler(targets), targets["dataset_sha256"],
            targets["fold"], targets["fit_last_label_available_us"], targets["rows"])
        sample_views = native.normalized(feature_normalizer, fold, "test", targets=target_normalizer)
        selected_indices = native.split_indices(fold, "test")[sample_positions]
        windows = np.stack([sample_views[int(i)]["x"] for i in selected_indices])
        tabular = tabular_view(windows)
    checkpoints = {Path(p).name: run / p for p in rows[config]["checkpoint_artifacts"]}
    if config == "RIVER-1":
        from quant.research_fast.adapters.river_adapter import RiverAdapter
        model = RiverAdapter.load(checkpoints["river.pkl"], dataset_sha256=binding["dataset_sha256"],
            fold_name=fold.name, normalization_sha256=measured["normalization_sha256"])
        accepted.require(model.predicted_samples == measured["predicted_samples"]
            and model.learned_samples == measured["mature_learned_samples"]
            and len(model.pending) == measured["pending_labels"] == 0
            and model.last_learn_label_available_us == measured["last_learn_label_available_us"],
            "River saved final state/queue changed")
        checkpoint_checks[config] = {"status": "FINAL_STATE_BINDING_AND_COUNTS_VERIFIED",
            "predicted_samples": model.predicted_samples, "learned_samples": model.learned_samples,
            "pending_labels": len(model.pending), "test_predictions_replayed": False}
    else:
        if config in accepted.IDS[:3]:
            with checkpoints[f"{config}.pkl"].open("rb") as reader:
                model = pickle.load(reader)
            standardized = model.predict(tabular).reshape(-1, 2, 4)
        elif config.startswith("TS2VEC-"):
            if representation is None:
                from quant.research_fast.adapters.ts2vec_adapter import TS2VecEncoder
                encoder = TS2VecEncoder()
                encoder.model.load(checkpoints["encoder.pt"])
                encoder.model.net.eval()
                representation = encoder.encode(windows)
                del encoder
            with checkpoints[f"{config}.pkl"].open("rb") as reader:
                model = pickle.load(reader)
            standardized = model.predict(representation).reshape(-1, 2, 4)
        else:
            import torch
            from quant.research_fast.trainer import sequence_model
            torch.set_num_threads(2)
            model = sequence_model(config)
            model.load_state_dict(torch.load(checkpoints["best.pt"], map_location="cpu", weights_only=True))
            model.eval()
            with torch.no_grad():
                standardized = model(torch.from_numpy(windows)).numpy()
        reproduced = target_normalizer.inverse_transform(standardized)
        stored = np.load(prediction_path, allow_pickle=False)[sample_positions]
        error = np.abs(reproduced.astype(np.float64) - stored.astype(np.float64))
        accepted.require(np.allclose(reproduced, stored, rtol=1e-4, atol=1e-6),
                         f"Actual saved checkpoint does not reproduce sample predictions: {config}")
        checkpoint_checks[config] = {"status": "SIX_FIXED_TEST_PREDICTIONS_REPRODUCED",
            "test_positions": sample_positions.tolist(), "decision_us": decisions[sample_positions].tolist(),
            "max_absolute_error": float(error.max()), "max_absolute_error_by_task": error.max(axis=(0, 1)).tolist(),
            "rtol": 1e-4, "atol": 1e-6}
        del model
accepted.require(len(truth_hashes) == len(sample_hashes) == len(scaler_hashes) == 1,
                 "All ten configurations must share exact truth/IDs/scalers")
accepted.require(len(process_scopes) == 9 and "TS2VEC-SHARED" in process_scopes,
                 "TS2Vec two probes must share one process measurement")
timings = {}
for log in (run / fold.name).glob("*.log"):
    name, start = log.stem.rsplit("-", 1)
    timings[name] = {"log": str(log), "log_sha256": file_sha(log),
        "launch_timestamp_ns_from_parent_filename": int(start),
        "launch_utc": datetime.fromtimestamp(int(start) / 1e9, UTC).isoformat(),
        "final_worker_log_mtime_ns": log.stat().st_mtime_ns,
        "final_worker_log_utc": datetime.fromtimestamp(log.stat().st_mtime_ns / 1e9, UTC).isoformat(),
        "launch_to_last_worker_log_seconds": (log.stat().st_mtime_ns - int(start)) / 1e9}
result = {"status": "TEN_CONFIGS_SINGLE_FULL_WINDOW_DIAGNOSTIC_VERIFIED",
    "verified_at_utc": datetime.now(UTC).isoformat(),
    "formal_six_fold_complete": False, "top3_selected": False, "candidate_qualification": False,
    "run_dir": str(run), "binding_sha256": _sha(binding), "verifier_sha256": file_sha(Path(__file__)),
    "exact_common_truth_npy_sha256": next(iter(truth_hashes)),
    "exact_common_sample_ids_sha256": next(iter(sample_hashes)),
    "exact_common_normalization_sha256": next(iter(scaler_hashes)),
    "splits": binding["splits"], "models": rows, "unique_worker_processes": process_scopes,
    "checkpoint_load_verification": checkpoint_checks,
    "timing_note": "Accepted worker timer starts after model imports. Parent timestamp to final flushed worker log is a separate UTC wall interval, including startup/imports; process teardown is excluded. Shared TS2Vec compute counted once.",
    "parent_launch_to_final_log_intervals": timings, "resources": resources.status()}
accepted.publish(run / "INDEPENDENT_DIAGNOSTIC_VERIFICATION.json", result)
print(json.dumps({"status": result["status"], "configurations": len(rows),
    "unique_worker_processes": len(process_scopes), "verification": str(run / "INDEPENDENT_DIAGNOSTIC_VERIFICATION.json")}))
