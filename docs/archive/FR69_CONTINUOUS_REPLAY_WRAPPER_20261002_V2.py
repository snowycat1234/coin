"""Local FR69 continuous replay: frozen common scaling, static/online/weekly policies.

Diagnostic 30-day source prefix: 2025-07-15 <= OOS < 2025-07-29.
Formal 180-day prefix: 2025-07-15 <= OOS < 2025-12-28, original D-path streaming.
Reuse accepted dataset, fit_tabular, fit_river and evaluation. No search or new models.
"""

from __future__ import annotations

import argparse
import fcntl
import importlib.util
import json
import resource
import time
from datetime import timedelta
from pathlib import Path

import numpy as np

from quant import disk, resources
from quant.paths import ROOT, STATE
from quant.research_fast.cached_dataset import CachedSequenceDataset
from quant.research_fast.dataset import (
    START,
    Fold,
    ShardSpec,
    _sha,
    day_us,
    file_sha,
    protocol,
)


def runner_helpers():
    path = ROOT / "scripts/fr_run_first_round.py"
    spec = importlib.util.spec_from_file_location("fr69_accepted_receipt_helpers", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


HELPERS = runner_helpers()
CONTRACT_NAME = "FR69_CONTINUOUS_INITIAL_SCALERS_V1"
WRAPPER_PATH = Path(__file__).resolve()
WRAPPER_KEY = WRAPPER_PATH.relative_to(ROOT.resolve()).as_posix()


class FrozenReplayDataset(CachedSequenceDataset):
    """A view of the same dataset; inject the actual unchanged initial scaler objects.

    Fold.name denotes this single replay/normalization contract. Weekly windows
    retain their real time bounds and are separately recorded, not renamed scaler
    receipts or fabricated per-week scaler fits. Test maturity uses global OOS end;
    predict_stop only assigns a decision to one weekly XGB version.
    """

    def __init__(self, dataset, features, targets, *, predict_stop=None):
        self.__dict__.update(dataset.__dict__)
        self.frozen_features = features
        self.frozen_targets = targets
        self.predict_stop = predict_stop

    def _check_contract(self, fold):
        HELPERS.require(
            fold.name == CONTRACT_NAME
            and fold.fit_cutoff_us >= self.frozen_features.fit_last_us
            and fold.fit_cutoff_us >= self.frozen_targets.fit_last_label_available_us,
            "Only the shared initial normalization contract can be reused",
        )

    def fit_fold_scaler(self, fold):
        self._check_contract(fold)
        return self.frozen_features

    def fit_target_scaler(self, fold):
        self._check_contract(fold)
        return self.frozen_targets

    def split_indices(self, fold, split):
        indices = super().split_indices(fold, split)
        if split == "test" and self.predict_stop is not None:
            indices = indices[self.index[indices] < self.predict_stop]
        return indices


def common_sources(history_days):
    specification = importlib.util.spec_from_file_location(
        "fr69_accepted_history_helpers", ROOT / "scripts/hf_fetch_history.py"
    )
    history = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(history)

    paths = [
        history.STORE / market / symbol / f"{START + timedelta(days=n)}.manifest.json"
        for n in range(history_days)
        for market, symbol in (
            ("spot", "BTCUSDT"),
            ("spot", "ETHUSDT"),
            ("perp", "BTCUSDT"),
            ("perp", "ETHUSDT"),
        )
    ]
    missing = [
        str(path)
        for path in paths
        if not path.is_file() or not (path.parent / f"{path.name[:10]}.parquet").is_file()
    ]
    HELPERS.require(not missing, f"INCOMPLETE_{history_days}D: {len(missing)} missing; fits=0")
    previous, shards, manifests = {}, [], {}
    for path in paths:
        market, symbol = path.parts[-3:-1]
        day = START + timedelta(days=len(shards) // 4)
        value = history.resume_day(market, symbol, day, previous.get((market, symbol)))
        HELPERS.require(value is not None, "Daily evidence disappeared")
        previous[market, symbol] = (value["conversion"]["last_l"], value["conversion"]["last_a"])
        shards.append(ShardSpec.from_manifest(path))
        manifests[str(path.relative_to(ROOT))] = file_sha(path)
    dataset = CachedSequenceDataset(shards, mode="formal" if history_days == 180 else "smoke")
    HELPERS.require(len(dataset.complete_days) == history_days, "Full common UTC days required")
    return dataset, manifests


def replay_fold(history_days):
    # This name is one continuous normalization contract, not an old rolling fold.
    test_end = START + timedelta(days=28 if history_days == 30 else 180)
    return Fold(
        CONTRACT_NAME,
        day_us(START),
        day_us(START + timedelta(days=12)),
        day_us(START + timedelta(days=14)),
        day_us(test_end),
    )


def check_result(dataset, fold, result, features, targets):
    values, indices, evidence = result
    HELPERS.require(
        np.array_equal(indices, dataset.split_indices(fold, "test"))
        and values.shape == (len(indices), 2, 4)
        and np.isfinite(values).all()
        and evidence["feature_scaler"] == features.receipt()
        and evidence["target_scaler"] == targets.receipt(),
        "Predictions must retain exact shared IDs, original units and unchanged scaler receipts",
    )


def emit_model(run, config, batch, values, indices, evidence, binding):
    from quant.research_fast.evaluation import evaluate_fold

    output = run / config
    output.mkdir()
    np.save(output / "predictions.npy", values, allow_pickle=False)
    np.save(output / "indices.npy", indices, allow_pickle=False)
    evidence.update(
        process_peak_scope="SHARED_CONTINUOUS_REPLAY_PROCESS_CUMULATIVE",
        process_peak_RAM_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024,
        shared_cgroup_cumulative=resources.status(),
        gpu_hours=0,
    )
    evaluation = evaluate_fold(batch, values, batch.sample_ids, resources=evidence)
    HELPERS.publish(output / "EVALUATION.json", evaluation.receipt())
    for spread, economics in evaluation.economics.items():
        economics.daily_nav.write_parquet(output / f"daily-{spread}.parquet")
        economics.trades.write_parquet(output / f"trades-{spread}.parquet")
    artifacts = {str(path.relative_to(run)): file_sha(path) for path in output.iterdir()}
    if config == "RIVER-1":
        checkpoint = run / "river-final.pkl"
        artifacts[str(checkpoint.relative_to(run))] = file_sha(checkpoint)
    HELPERS.publish(
        output / "COMPLETE.json",
        {
            "status": "COMPLETE_CONTINUOUS_REPLAY",
            "config": config,
            "binding_sha256": _sha(binding),
            "sample_ids_sha256": _sha(batch.sample_ids),
            "artifacts": artifacts,
            "evaluation": evaluation.receipt(),
        },
    )
    return evaluation.receipt()


def execute(run, dataset, manifests, history_days):
    from quant.research_fast.evaluation import EvaluationBatch
    from quant.research_fast.native_inputs import native_shard_snapshot
    from quant.research_fast.river_replay import fit_river
    from quant.research_fast.trainer import fit_tabular

    HELPERS.require(history_days in (30, 180), "Fixed 30d/180d continuous replay only")
    fold = replay_fold(history_days)
    disk.check(reserve=1_000_000_000)
    run.mkdir()
    native = None
    if history_days == 30:
        original_contract = dataset.contract_sha256
        native = run / "native"
        shards = native_shard_snapshot(dataset.shards, native)
        dataset = CachedSequenceDataset(shards, mode="smoke")
        HELPERS.require(dataset.contract_sha256 == original_contract, "Native path changed dataset IDs")
        HELPERS.publish(
            run / "SOURCE_SNAPSHOT.json", json.loads((native / "SOURCE_SNAPSHOT.json").read_text())
        )
    index = dataset.prepare_index(run / "endpoints.i64")
    # Only these calls fit the common external scalers in this replay.
    features, targets = dataset.fit_fold_scaler(fold), dataset.fit_target_scaler(fold)
    frozen = FrozenReplayDataset(dataset, features, targets)
    expected = dataset.split_indices(fold, "test")
    HELPERS.require(len(expected) > 0, "Nonempty continuous test required")
    configs = {config["id"]: config for config in protocol()["configs"]}
    source_binding = {**HELPERS.sources(), WRAPPER_KEY: file_sha(WRAPPER_PATH)}
    binding = {
        "status": "FORMAL_DATA_READY" if history_days == 180 else "SMOKE_ONLY",
        "wrapper_source_version": 2,
        "policy": "FR69_STATIC_RIDGE_CONTINUOUS_RIVER_WEEKLY_XGB_FIXED_INITIAL_EXTERNAL_SCALERS_V1",
        "dataset_sha256": dataset.contract_sha256,
        "index": index,
        "manifests": manifests,
        "sources": source_binding,
        "runtime": HELPERS.runtime(),
        "input_mode": "NATIVE_30D_SNAPSHOT" if native is not None else "ORIGINAL_D_BOUNDED_READS_24_DAY_CACHE",
        "native_snapshot_sha256": file_sha(run / "SOURCE_SNAPSHOT.json") if native is not None else None,
        "history_days": history_days,
        "seed": 20261001,
        "configs": {name: configs[name] for name in ("RIDGE-1", "XGB-S", "RIVER-1")},
        "initial_training_window": vars(fold),
        "feature_scaler": features.receipt(),
        "target_scaler": targets.receipt(),
        "normalizers_fitted_once": True,
        "sample_ids_sha256": _sha(
            tuple(_sha((dataset.contract_sha256, int(dataset.index[i]))) for i in expected)
        ),
        "production_or_candidate_qualification": False,
    }
    HELPERS.publish(run / "RUN_BINDING.json", binding)
    started = time.monotonic()
    batch = EvaluationBatch.from_dataset(dataset, expected, fold=fold)
    evaluations = {}
    result = fit_tabular(frozen, fold, configs["RIDGE-1"])
    check_result(frozen, fold, result, features, targets)
    evaluations["RIDGE-1"] = emit_model(
        run, "RIDGE-1", batch, *result[:2], {**result[2], "static_fit_count": 1}, binding
    )
    result = fit_river(frozen, fold, run / "river-final.pkl")
    check_result(frozen, fold, result, features, targets)
    evaluations["RIVER-1"] = emit_model(
        run, "RIVER-1", batch, *result[:2], {**result[2], "cross_week_state_reset_count": 0}, binding
    )
    xgb_values = np.empty((len(expected), 2, 4), dtype=np.float64)
    assigned = np.zeros(len(expected), dtype=np.bool_)
    weeks = []
    week_start = fold.test_start_us
    while week_start < fold.test_end_us:
        disk.check(reserve=100_000_000)
        week_end = min(week_start + 7 * 86_400_000_000, fold.test_end_us)
        weekly_fold = Fold(
            CONTRACT_NAME,
            week_start - 14 * 86_400_000_000,
            week_start - 2 * 86_400_000_000,
            week_start,
            fold.test_end_us,
        )
        weekly = FrozenReplayDataset(dataset, features, targets, predict_stop=week_end)
        result = fit_tabular(weekly, weekly_fold, configs["XGB-S"])
        check_result(weekly, weekly_fold, result, features, targets)
        positions = np.searchsorted(expected, result[1])
        HELPERS.require(
            np.array_equal(expected[positions], result[1]) and not assigned[positions].any(),
            "Each continuous XGB endpoint must belong to exactly one model version",
        )
        xgb_values[positions] = result[0]
        assigned[positions] = True
        weeks.append(
            {
                "model_version": len(weeks),
                "real_training_fold_bounds": vars(weekly_fold),
                "prediction_start_us": week_start,
                "prediction_end_us": week_end,
                "prediction_count": len(result[1]),
                "within_last_310s_before_week_end": int(
                    np.sum(dataset.index[result[1]] >= week_end - 310_000_000)
                ),
                "feature_scaler": features.receipt(),
                "target_scaler": targets.receipt(),
                "fit_evidence": result[2],
            }
        )
        week_start = week_end
    HELPERS.require(assigned.all(), "No continuous XGB endpoints may be dropped")
    evaluations["XGB-S"] = emit_model(
        run,
        "XGB-S",
        batch,
        xgb_values,
        expected,
        {
            "weekly_versions": weeks,
            "weekly_refit_count": len(weeks),
            "external_scaler_refit_count": 0,
            "feature_scaler": features.receipt(),
            "target_scaler": targets.receipt(),
        },
        binding,
    )
    HELPERS.require(
        len({value["metadata"]["batch_sha256"] for value in evaluations.values()}) == 1,
        "One complete continuous truth/QA/valuation batch required",
    )
    HELPERS.require(
        source_binding == {**HELPERS.sources(), WRAPPER_KEY: file_sha(WRAPPER_PATH)},
        "Source changed during replay; preserve artifacts without overall acceptance",
    )
    if native is not None:
        HELPERS.cleanup_snapshot(native)
    HELPERS.publish(
        run / "CONTINUOUS_REPLAY_COMPLETE.json",
        {
            "status": "FR69_CONTINUOUS_REPLAY_COMPLETE",
            "wrapper_source_version": 2,
            "binding_sha256": _sha(binding),
            "history_days": history_days,
            "oos_start_us": fold.test_start_us,
            "oos_end_us": fold.test_end_us,
            "shared_test_endpoints": len(expected),
            "same_week_boundary_predictions_retained": True,
            "nav_reset_inside_oos": False,
            "weekly_xgb_versions": len(weeks),
            "native_inputs": (
                "DELETED_AFTER_OWNERSHIP_AND_BOUND_SHA_VERIFICATION" if native is not None
                else "NOT_CREATED_ORIGINAL_D_SOURCES_RETAINED"
            ),
            "elapsed_seconds": time.monotonic() - started,
            "formal_six_fold_sprint_gate": False,
            "production_or_candidate_qualification": False,
            "evaluations": evaluations,
            "completion_receipt_sha256": {
                name: file_sha(run / name / "COMPLETE.json") for name in evaluations
            },
        },
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--history-days", type=int, choices=(30, 180), default=30)
    parser.add_argument("--run-dir", type=Path)
    parser.add_argument("--preflight-only", action="store_true")
    args = parser.parse_args()
    resources.status()
    HELPERS.require(
        file_sha(ROOT / "protocols/fast_research_v6.json")
        == "a51adea6ff382128c9d4632280ad31d00c486b165f2ef4019b0a4f508e2e03bd",
        "Accepted fixed protocol required",
    )
    dataset, manifests = common_sources(args.history_days)
    if args.preflight_only:
        print(json.dumps({"status": "CONTINUOUS_SOURCE_PREFLIGHT_NO_FIT", "days": args.history_days, "fits": 0}))
        return
    HELPERS.require(args.run_dir is not None, "New owned STATE run directory required")
    run = args.run_dir.resolve()
    HELPERS.require(
        run.is_relative_to(STATE.resolve()) and run != STATE.resolve() and not run.exists(),
        "Exclusive new run only; never overwrite or implicitly restart an old replay",
    )
    with (STATE / ".fr-first-round.lock").open("a+") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        try:
            execute(run, dataset, manifests, args.history_days)
        except Exception as error:
            if run.exists() and not (run / "FAILED_NO_OVERALL_RESULT.json").exists():
                HELPERS.publish(run / "FAILED_NO_OVERALL_RESULT.json", {"reason": str(error)})
            raise


if __name__ == "__main__":
    main()
