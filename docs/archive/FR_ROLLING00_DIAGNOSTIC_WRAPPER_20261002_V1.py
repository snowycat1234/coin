"""One original rolling_00 window; accepted FR-v6 interfaces, no formal claims."""
from __future__ import annotations

import argparse
import fcntl
import json
import os
import pickle
import resource
import subprocess
import sys
import tempfile
import time
import traceback
from dataclasses import replace
from datetime import timedelta
from pathlib import Path
from unittest.mock import patch

import numpy as np

from quant import disk, resources
from quant.paths import ROOT, STATE
from quant.research_fast.cached_dataset import CachedSequenceDataset
from quant.research_fast.dataset import START, ShardSpec, _sha, file_sha, make_folds, protocol
from quant.research_fast.native_inputs import native_shard_snapshot

sys.path.insert(0, str(ROOT / "scripts"))
import fr_run_first_round as accepted
from hf_fetch_history import STORE, STREAMS, resume_day

SCRIPT = Path(__file__).resolve()
FOLD = make_folds()[0]
STATUS = "SINGLE_FULL_WINDOW_DIAGNOSTIC_ONLY"


def preflight():
    accepted.require(file_sha(ROOT / "protocols/fast_research_v6.json") ==
                     "a51adea6ff382128c9d4632280ad31d00c486b165f2ef4019b0a4f508e2e03bd",
                     "Original fixed protocol changed")
    accepted.require(tuple(c["id"] for c in protocol()["configs"]) == accepted.IDS,
                     "Original ten configurations changed")
    previous, shards, manifests = {}, [], {}
    for n in range(22):
        day = START + timedelta(days=n)
        for market, symbol in STREAMS:
            path = STORE / market / symbol / f"{day}.manifest.json"
            value = resume_day(market, symbol, day, previous.get((market, symbol)))
            accepted.require(value is not None, f"Missing explicit diagnostic source: {path}")
            previous[market, symbol] = (value["conversion"]["last_l"], value["conversion"]["last_a"])
            shards.append(ShardSpec.from_manifest(path))
            manifests[str(path.relative_to(ROOT))] = file_sha(path)
    return CachedSequenceDataset(shards, mode="smoke"), manifests


def binding_sources():
    return {**accepted.sources(), str(SCRIPT.relative_to(ROOT)): file_sha(SCRIPT)}


def native_dataset(run, binding, dataset):
    snapshot = json.loads((run / FOLD.name / "native/SOURCE_SNAPSHOT.json").read_text())
    accepted.require(len(snapshot["files"]) == 88 and snapshot["bytes"] <= 1_000_000_000,
                     "Only explicit 22-day native snapshot allowed")
    replacements = {item["original"]: item for item in snapshot["files"]}
    native = []
    for source in dataset.shards:
        item = replacements[str(source.path)]
        target = Path(item["native"])
        accepted.require(target.parent == run / FOLD.name / "native"
                         and source.sha256 == item["sha256"] == file_sha(target),
                         "Native source byte binding changed")
        native.append(replace(source, path=target))
    result = CachedSequenceDataset(native, mode="smoke")
    accepted.attach_index(result, run, binding)
    return result


def save_fitted_models(attempt, group):
    """Persist actual models returned inside accepted fit calls without changing fit."""
    from sklearn.linear_model import Ridge
    from sklearn.multioutput import MultiOutputRegressor
    from xgboost import XGBRegressor
    from contextlib import ExitStack
    stack = ExitStack()
    for cls in (Ridge, XGBRegressor, MultiOutputRegressor):
        original = cls.fit
        def fit(model, *args, _original=original, _cls=cls, **kwargs):
            result = _original(model, *args, **kwargs)
            name = ("TS2VEC-LINEAR-1" if _cls is Ridge else "TS2VEC-LGB-1") if group == "TS2VEC-SHARED" else group
            target = attempt / f"{name}.pkl"
            with target.open("xb") as writer:
                pickle.dump(model, writer, protocol=pickle.HIGHEST_PROTOCOL)
                writer.flush()
                os.fsync(writer.fileno())
            print(json.dumps({"event": "MODEL_CHECKPOINT_SAVED", "group": group,
                              "path": str(target)}), flush=True)
            return result
        stack.enter_context(patch.object(cls, "fit", fit))
    return stack


def worker(run, group, binding, lock_fd):
    from quant.research_fast.evaluation import EvaluationBatch, evaluate_fold
    from quant.research_fast.trainer import fit_sequence, fit_tabular
    accepted.require(Path(f"/proc/self/fd/{lock_fd}").resolve() == STATE / ".fr-first-round.lock",
                     "Inherited shared first-round lock required")
    started = time.monotonic()
    original, manifests = preflight()
    accepted.require(manifests == binding["manifests"] and binding_sources() == binding["sources"]
                     and accepted.runtime() == binding["runtime"], "Worker binding changed")
    accepted.attach_index(original, run, binding)
    dataset = native_dataset(run, binding, original)
    job = run / FOLD.name / group
    job.mkdir(exist_ok=True)
    attempt = Path(tempfile.mkdtemp(prefix="attempt-", dir=job))
    print(json.dumps({"event": "WORKER_START", "group": group, "pid": os.getpid(),
                      "attempt": str(attempt), "splits": binding["splits"]}), flush=True)
    try:
        with save_fitted_models(attempt, group):
            if group == "TS2VEC-SHARED":
                from quant.research_fast.representation_probes import fit_ts2vec_probes
                results = fit_ts2vec_probes(dataset, FOLD, attempt / "encoder.pt", iterations=600)
            elif group == "RIVER-1":
                from quant.research_fast.river_replay import fit_river
                results = [(group, *fit_river(dataset, FOLD, attempt / "river.pkl"))]
            elif group in accepted.IDS[:3]:
                config = next(c for c in protocol()["configs"] if c["id"] == group)
                results = [(group, *fit_tabular(dataset, FOLD, config))]
            else:
                results = [(group, *fit_sequence(dataset, FOLD, group, attempt / "best.pt"))]
        expected = dataset.split_indices(FOLD, "test")
        batch = EvaluationBatch.from_dataset(dataset, expected, fold=FOLD)
        completed = []
        for config, predictions, indices, evidence in results:
            accepted.require(np.array_equal(indices, expected), "Common test IDs changed")
            destination = run / FOLD.name / config
            destination.mkdir(exist_ok=True)
            output = attempt if config == group else Path(tempfile.mkdtemp(prefix="attempt-", dir=destination))
            np.save(output / "predictions.npy", predictions, allow_pickle=False)
            np.save(output / "indices.npy", indices, allow_pickle=False)
            np.save(output / "truth.npy", batch.truth, allow_pickle=False)
            np.save(output / "decision_us.npy", batch.decision_us, allow_pickle=False)
            evidence.update(process_peak_scope=group, gpu_hours=0, diagnostic_status=STATUS,
                            original_max_epochs=10, original_patience=3, seed=20261001)
            accepted.publish(output / "TRAINING.json", evidence)
            evaluation = evaluate_fold(batch, predictions, batch.sample_ids, resources=evidence)
            for spread, economics in evaluation.economics.items():
                economics.daily_nav.write_parquet(output / f"daily-{spread}.parquet")
                economics.trades.write_parquet(output / f"trades-{spread}.parquet")
            completed.append((config, output, evaluation))
        measured = {"worker_seconds": time.monotonic() - started,
                    "process_peak_RAM_bytes": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024,
                    "shared_cgroup_cumulative": resources.status()}
        jobs = {}
        for config, output, evaluation in completed:
            evaluation.metadata["resources"].update(measured)
            checkpoints = [p for p in attempt.iterdir() if p.suffix in (".pt", ".pkl")] if group == "TS2VEC-SHARED" else ()
            jobs[config] = accepted.complete_job(run, FOLD, config, binding, output, evaluation,
                batch.sample_ids, checkpoints, publish_completion=group != "TS2VEC-SHARED")
        if group == "TS2VEC-SHARED":
            accepted.publish(attempt / "GROUP_COMPLETE.json", {"binding_sha256": _sha(binding), "jobs": jobs})
            accepted.recover_shared_pair(run, FOLD, binding, dataset)
        print(json.dumps({"event": "WORKER_COMPLETE", "group": group, **measured}), flush=True)
    except BaseException as error:
        accepted.publish(attempt / "FAILURE.json", {"status": "FAILED_NO_RESULT", "reason": str(error),
            "traceback": traceback.format_exc(), "binding_sha256": _sha(binding), "group": group,
            "worker_seconds": time.monotonic() - started,
            "process_peak_RAM_bytes": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024,
            "resources": resources.status()})
        raise


def summarize(run, binding, dataset, failures):
    models = {}
    for config in accepted.IDS:
        receipt = accepted.verified(run, FOLD, config, binding, dataset)
        if receipt:
            value = receipt["evaluation"]
            models[config] = {"metrics": value["metrics"], "economics": value["economics"],
                "resources": value["metadata"]["resources"], "completion_sha256":
                file_sha(run / FOLD.name / config / "COMPLETE.json")}
    result = {"status": STATUS, "completed_configs": len(models), "requested_configs": 10,
        "formal_six_fold_complete": False, "top3_selected": False, "candidate_qualification": False,
        "binding_sha256": _sha(binding), "run_dir": str(run), "fold": FOLD.__dict__,
        "dataset_mode": "smoke", "source_complete_days": 22, "source_files": 88,
        "splits": binding["splits"], "native_bytes": binding["native_bytes"],
        "fixed_max_epochs": 10, "fixed_patience": 3, "ts2vec_iterations": 600,
        "seed": 20261001, "gpu_hours": 0, "failures": failures, "models": models,
        "scope": "Original rolling_00 full 12d fit + 2d validation + 7d test; additional final UTC day only serves cache/label boundary. No screening or promotion."}
    accepted.publish(run / "DIAGNOSTIC_SUMMARY.json", result)
    report = ROOT / "reports/fast_research/FR_ROLLING00_FULL_WINDOW_DIAGNOSTIC_20261002_V1.json"
    accepted.publish(report, result)
    print(json.dumps({"event": "DIAGNOSTIC_FINISHED", "completed_configs": len(models),
                      "failures": len(failures), "summary": str(report)}), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--worker")
    parser.add_argument("--lock-fd", type=int, default=-1)
    args = parser.parse_args()
    resources.status()
    run = args.run_dir.resolve()
    accepted.require(run.is_relative_to(STATE.resolve()) and run != STATE.resolve(), "Owned STATE only")
    if args.worker:
        worker(run, args.worker, json.loads((run / "RUN_BINDING.json").read_text()), args.lock_fd)
        return
    with (STATE / ".fr-first-round.lock").open("a+") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        dataset, manifests = preflight()
        if run.exists():
            binding = json.loads((run / "RUN_BINDING.json").read_text())
            accepted.require(binding["sources"] == binding_sources() and binding["manifests"] == manifests
                             and binding["runtime"] == accepted.runtime(), "Resume binding changed")
            accepted.attach_index(dataset, run, binding)
        else:
            ledger = disk.check(reserve=1_000_000_000)
            run.mkdir()
            (run / FOLD.name).mkdir()
            native_shard_snapshot(dataset.shards, run / FOLD.name / "native")
            snapshot = json.loads((run / FOLD.name / "native/SOURCE_SNAPSHOT.json").read_text())
            initial_native = CachedSequenceDataset([replace(s, path=Path(next(
                item["native"] for item in snapshot["files"] if item["original"] == str(s.path))))
                for s in dataset.shards], mode="smoke")
            index = initial_native.prepare_index(run / "endpoints.i64")
            dataset.index = initial_native.index
            binding = {"sources": binding_sources(), "runtime": accepted.runtime(), "manifests": manifests,
                "seed": 20261001, "dataset_sha256": dataset.contract_sha256,
                "index_sha256": index["sha256"], "endpoints": index["endpoints"],
                "configs": accepted.IDS, "folds": [FOLD.name], "diagnostic_status": STATUS,
                "dataset_mode": "smoke", "index_receipt": index, "ledger_before": ledger,
                "native_bytes": snapshot["bytes"], "splits": {s: len(dataset.split_indices(FOLD, s))
                    for s in ("train", "validation", "test")}}
            accepted.publish(run / "RUN_BINDING.json", binding)
            accepted.publish(run / "PREFLIGHT_22D.json", {"status": "22_COMPLETE_COMMON_DAYS_BOUND_NO_FORMAL_CLAIM",
                "source_files": 88, "manifests": manifests, "dataset_sha256": dataset.contract_sha256,
                "native_snapshot_sha256": file_sha(run / FOLD.name / "native/SOURCE_SNAPSHOT.json"),
                "index": index, "splits": binding["splits"], "resources": resources.status()})
        print(json.dumps({"event": "BINDING_READY", "run_dir": str(run), "binding_sha256": _sha(binding),
                          "splits": binding["splits"], "native_bytes": binding["native_bytes"]}), flush=True)
        (run / "tmp").mkdir(exist_ok=True)
        accepted.recover_shared_pair(run, FOLD, binding, dataset)
        failures = []
        for config in accepted.IDS:
            if config == accepted.IDS[8] or accepted.verified(run, FOLD, config, binding, dataset):
                continue
            group = "TS2VEC-SHARED" if config == accepted.IDS[7] else config
            accepted.require(binding_sources() == binding["sources"], "Accepted sources changed")
            disk.check(reserve=100_000_000)
            logpath = run / FOLD.name / f"{group}-{time.time_ns()}.log"
            command = [sys.executable, str(SCRIPT), "--run-dir", str(run), "--worker", group,
                       "--lock-fd", str(lock.fileno())]
            with logpath.open("x") as writer:
                completed = subprocess.run(command, stdout=writer, stderr=subprocess.STDOUT,
                    pass_fds=(lock.fileno(),), env={**os.environ, "CUDA_VISIBLE_DEVICES": "",
                    "PYTHONDONTWRITEBYTECODE": "1", "TMPDIR": str(run / "tmp")})
            if completed.returncode:
                failure = {"status": "WORKER_FAILED_NO_RESULT", "group": group,
                    "returncode": completed.returncode, "log": str(logpath),
                    "log_sha256": file_sha(logpath), "resources": resources.status()}
                failures.append(failure)
                accepted.publish(run / f"FAILURE-{group}-{time.time_ns()}.json", failure)
            print(json.dumps({"event": "GROUP_FINISHED", "group": group,
                              "returncode": completed.returncode, "log": str(logpath)}), flush=True)
        accepted.require(binding_sources() == binding["sources"], "Accepted sources changed at finish")
        summarize(run, binding, dataset, failures)


if __name__ == "__main__":
    main()
