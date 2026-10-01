"""Fixed FR-v6 first round: existing models, one process per job, no search."""

from __future__ import annotations

import argparse
import fcntl
import hashlib
import importlib.metadata
import json
import os
import resource
import shutil
import subprocess
import sys
import tempfile
import time
from dataclasses import replace
from datetime import timedelta
from pathlib import Path

import numpy as np

from quant import disk, resources
from quant.paths import ROOT, STATE
from quant.research_fast.cached_dataset import CachedSequenceDataset
from quant.research_fast.dataset import (
    START,
    STREAMS,
    ShardSpec,
    _sha,
    file_sha,
    make_folds,
    protocol,
)
from quant.research_fast.native_inputs import native_shard_snapshot

IDS = (
    "RIDGE-1",
    "XGB-S",
    "XGB-M",
    "TCN-S",
    "TCN-M",
    "MLPLOB-1",
    "TLOB-1",
    "TS2VEC-LINEAR-1",
    "TS2VEC-LGB-1",
    "RIVER-1",
)
SCRIPT = ROOT / "scripts/fr_run_first_round.py"


def require(ok, reason):
    if not ok:
        raise ValueError(reason)


def publish(path, value):
    with tempfile.NamedTemporaryFile(
        mode="w", dir=path.parent, prefix=".publish-", suffix=".tmp", delete=False
    ) as writer:
        writer.write(json.dumps(value, indent=2, allow_nan=False) + "\n")
        writer.flush()
        os.fsync(writer.fileno())
    temporary = Path(writer.name)
    try:
        os.link(temporary, path)
        directory = os.open(path.parent, os.O_DIRECTORY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        temporary.unlink(missing_ok=True)


def sources():
    paths = [SCRIPT, ROOT / "protocols/fast_research_v6.json"]
    paths += [
        ROOT / p
        for p in (
            "src/quant/paths.py",
            "src/quant/disk.py",
            "src/quant/resources.py",
            "src/quant/metrics.py",
            "scripts/hf_fetch.py",
            "scripts/hf_fetch_v2.py",
            "scripts/hf_fetch_history.py",
        )
    ]
    for directory in ("src/quant/research_fast", "third_party/tlob", "third_party/ts2vec"):
        paths += [
            p for p in (ROOT / directory).rglob("*") if p.is_file() and "__pycache__" not in p.parts
        ]
    return {str(p.relative_to(ROOT)): file_sha(p) for p in sorted(set(paths))}


def runtime():
    return {
        name: {
            "version": (d := importlib.metadata.distribution(name)).version,
            "metadata_sha256": hashlib.sha256(d.read_text("METADATA").encode()).hexdigest(),
            "record_sha256": hashlib.sha256(d.read_text("RECORD").encode()).hexdigest(),
        }
        for name in (
            "numpy",
            "scipy",
            "polars",
            "pyarrow",
            "scikit-learn",
            "xgboost-cpu",
            "torch",
            "pytorch-tcn",
            "einops",
            "lightgbm",
            "river",
            "narwhals",
        )
    }


def preflight():
    from hf_fetch_history import STORE, resume_day

    settings = protocol()
    require(
        file_sha(ROOT / "protocols/fast_research_v6.json")
        == "a51adea6ff382128c9d4632280ad31d00c486b165f2ef4019b0a4f508e2e03bd",
        "Fixed protocol changed; refuse a new search",
    )
    require(
        tuple(c["id"] for c in settings["configs"]) == IDS
        and settings["training"]["seeds"] == [20261001]
        and len(make_folds()) == 6,
        "Exactly ten configurations, one seed and six fixed folds required",
    )
    paths = [
        (STORE / market / symbol / f"{START + timedelta(days=n)}.manifest.json")
        for n in range(180)
        for market, symbol in (
            ("spot", "BTCUSDT"),
            ("spot", "ETHUSDT"),
            ("perp", "BTCUSDT"),
            ("perp", "ETHUSDT"),
        )
    ]
    missing = [
        str(p)
        for p in paths
        if not p.is_file()
        or not p.with_name(p.name.replace(".manifest.json", ".parquet")).is_file()
    ]
    require(not missing, f"INSUFFICIENT_180D: {len(missing)}/720 missing; model_fits=0")
    previous, shards, manifests = {}, [], {}
    for path in paths:
        market, symbol = path.parts[-3:-1]
        day = START + timedelta(days=(len(shards) // 4))
        value = resume_day(market, symbol, day, previous.get((market, symbol)))
        require(value is not None, "Daily evidence disappeared")
        previous[market, symbol] = (value["conversion"]["last_l"], value["conversion"]["last_a"])
        shards.append(ShardSpec.from_manifest(path))
        manifests[str(path.relative_to(ROOT))] = file_sha(path)
    return CachedSequenceDataset(shards, mode="formal"), manifests


def attach_index(dataset, run, binding):
    path = run / "endpoints.i64"
    require(file_sha(path) == binding["index_sha256"], "Canonical endpoint index changed")
    dataset.index = np.memmap(path, dtype="<i8", mode="r")
    require(
        dataset.contract_sha256 == binding["dataset_sha256"]
        and len(dataset.index) == binding["endpoints"],
        "Canonical dataset changed",
    )


def verified(run, fold, config, binding, dataset, candidate=None):
    path = run / fold.name / config / "COMPLETE.json"
    if candidate is None and not path.exists():
        return None
    if candidate is None:
        require(path.stat().st_size < 250_000, "Oversized completion receipt")
    value = json.loads(path.read_text()) if candidate is None else candidate
    require(
        value["status"] == "COMPLETE"
        and value["binding_sha256"] == _sha(binding)
        and value["fold"] == fold.name
        and value["config"] == config,
        "Completed job binding changed; never silently refit",
    )
    for name, digest in value["artifacts"].items():
        artifact = (run / name).resolve()
        require(
            artifact.is_relative_to((run / fold.name / config).resolve())
            or (
                config.startswith("TS2VEC-")
                and artifact.is_relative_to((run / fold.name / "TS2VEC-SHARED").resolve())
            ),
            "Artifact escaped owned job",
        )
        require(file_sha(artifact) == digest, "Completed artifact changed")
    require(
        value["evaluation"]["metadata"]["dataset_sha256"] == binding["dataset_sha256"],
        "Completed evaluation dataset changed",
    )
    evaluation = next(run / p for p in value["artifacts"] if p.endswith("/EVALUATION.json"))
    output = evaluation.parent
    indices = np.load(output / "indices.npy", allow_pickle=False)
    predictions = np.load(output / "predictions.npy", allow_pickle=False)
    require(
        json.loads(evaluation.read_text()) == value["evaluation"]
        and np.array_equal(indices, dataset.split_indices(fold, "test"))
        and predictions.shape == (len(indices), 2, 4)
        and hashlib.sha256(predictions.astype(np.float64).tobytes()).hexdigest()
        == value["evaluation"]["metadata"]["prediction_sha256"]
        and value["sample_ids_sha256"]
        == _sha(tuple(_sha((binding["dataset_sha256"], int(dataset.index[i]))) for i in indices)),
        "Completed predictions/IDs/evaluation do not agree",
    )
    return value


def complete_job(
    run,
    fold,
    config,
    binding,
    output,
    evaluation,
    sample_ids,
    shared_checkpoints=(),
    *,
    publish_completion=True,
):
    publish(output / "EVALUATION.json", evaluation.receipt())
    artifacts = {str(p.relative_to(run)): file_sha(p) for p in output.iterdir() if p.is_file()}
    artifacts.update({str(p.relative_to(run)): file_sha(p) for p in shared_checkpoints})
    value = {
        "status": "COMPLETE",
        "config": config,
        "fold": fold.name,
        "binding_sha256": _sha(binding),
        "artifacts": artifacts,
        "sample_ids_sha256": _sha(sample_ids),
        "evaluation": evaluation.receipt(),
    }
    if publish_completion:
        publish(run / fold.name / config / "COMPLETE.json", value)
    return value


def recover_shared_pair(run, fold, binding, dataset):
    paths = (run / fold.name / "TS2VEC-SHARED").glob("attempt-*/GROUP_COMPLETE.json")
    for path in sorted(paths):
        value = json.loads(path.read_text())
        require(
            value["binding_sha256"] == _sha(binding) and set(value["jobs"]) == set(IDS[7:9]),
            "Shared representation group changed",
        )
        for config, candidate in value["jobs"].items():
            verified(run, fold, config, binding, dataset, candidate)
        for config, candidate in value["jobs"].items():
            target = run / fold.name / config / "COMPLETE.json"
            if target.exists():
                require(
                    json.loads(target.read_text()) == candidate,
                    "Existing shared probe completion differs",
                )
            else:
                publish(target, candidate)
        return


def worker(run, fold, group, binding, lock_fd):
    from quant.research_fast.evaluation import EvaluationBatch, evaluate_fold
    from quant.research_fast.trainer import fit_sequence, fit_tabular

    require(
        Path(f"/proc/self/fd/{lock_fd}").resolve() == STATE / ".fr-first-round.lock",
        "Worker requires inherited formal-run lock",
    )
    started = time.monotonic()
    dataset, manifests = preflight()
    require(
        manifests == binding["manifests"]
        and sources() == binding["sources"]
        and runtime() == binding["runtime"],
        "Inputs or runtime changed",
    )
    attach_index(dataset, run, binding)
    snapshot = json.loads((run / fold.name / "native/SOURCE_SNAPSHOT.json").read_text())
    selected = [
        s
        for s in dataset.shards
        if s.end_us > fold.train_start_us - 1_280_000_000 and s.start_us < fold.test_end_us
    ]
    require(
        len(snapshot["files"]) == len(selected) and snapshot["bytes"] <= 1_000_000_000,
        "Native fold scope or budget changed",
    )
    for s, item in zip(selected, snapshot["files"], strict=True):
        native = run / fold.name / "native" / f"{s.market}-{s.symbol}-{s.day}.parquet"
        require(
            item["original"] == str(s.path)
            and item["native"] == str(native)
            and item["sha256"] == file_sha(native) == s.sha256,
            "Native source binding changed",
        )
    replacements = {item["original"]: item["native"] for item in snapshot["files"]}
    dataset = CachedSequenceDataset(
        [
            replace(s, path=Path(replacements[str(s.path)])) if str(s.path) in replacements else s
            for s in dataset.shards
        ],
        mode="formal",
    )
    attach_index(dataset, run, binding)
    job = run / fold.name / group
    job.mkdir(exist_ok=True)
    attempt = Path(tempfile.mkdtemp(prefix="attempt-", dir=job))
    try:
        if group == "TS2VEC-SHARED":
            from quant.research_fast.representation_probes import fit_ts2vec_probes

            results = fit_ts2vec_probes(dataset, fold, attempt / "encoder.pt", iterations=600)
        elif group == "RIVER-1":
            from quant.research_fast.river_replay import fit_river

            results = [(group, *fit_river(dataset, fold, attempt / "river.pkl"))]
        elif group in IDS[:3]:
            config = next(c for c in protocol()["configs"] if c["id"] == group)
            results = [(group, *fit_tabular(dataset, fold, config))]
        else:
            results = [(group, *fit_sequence(dataset, fold, group, attempt / "best.pt"))]
        expected = dataset.split_indices(fold, "test")
        batch = EvaluationBatch.from_dataset(dataset, expected, fold=fold)
        completed = []
        for config, predictions, indices, evidence in results:
            require(np.array_equal(indices, expected), "Test IDs changed")
            destination = run / fold.name / config
            destination.mkdir(exist_ok=True)
            output = (
                attempt
                if config == group
                else Path(tempfile.mkdtemp(prefix="attempt-", dir=destination))
            )
            np.save(output / "predictions.npy", predictions, allow_pickle=False)
            np.save(output / "indices.npy", indices, allow_pickle=False)
            shutil.copy2(
                run / fold.name / "native/SOURCE_SNAPSHOT.json", output / "SOURCE_SNAPSHOT.json"
            )
            evidence.update(process_peak_scope=group, gpu_hours=0)
            evaluation = evaluate_fold(batch, predictions, batch.sample_ids, resources=evidence)
            for spread, economics in evaluation.economics.items():
                economics.daily_nav.write_parquet(output / f"daily-{spread}.parquet")
                economics.trades.write_parquet(output / f"trades-{spread}.parquet")
            completed.append((config, output, evaluation))
        measured = {
            "worker_seconds": time.monotonic() - started,
            "process_peak_RAM_bytes": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024,
            "shared_cgroup_cumulative": resources.status(),
        }
        jobs = {}
        for config, output, evaluation in completed:
            evaluation.metadata["resources"].update(measured)
            checkpoints = attempt.glob("*.pt") if group == "TS2VEC-SHARED" else ()
            jobs[config] = complete_job(
                run,
                fold,
                config,
                binding,
                output,
                evaluation,
                batch.sample_ids,
                checkpoints,
                publish_completion=group != "TS2VEC-SHARED",
            )
        if group == "TS2VEC-SHARED":
            publish(
                attempt / "GROUP_COMPLETE.json", {"binding_sha256": _sha(binding), "jobs": jobs}
            )
            recover_shared_pair(run, fold, binding, dataset)
    except Exception as error:
        publish(
            attempt / "FAILURE.json",
            {"status": "FAILED_NO_RESULT", "reason": str(error), "binding_sha256": _sha(binding)},
        )
        raise


def cleanup_snapshot(directory):
    value = json.loads((directory / "SOURCE_SNAPSHOT.json").read_text())
    require(
        directory.resolve().is_relative_to(STATE.resolve())
        and {p.name for p in directory.iterdir()}
        == {"SOURCE_SNAPSHOT.json", *[Path(item["native"]).name for item in value["files"]]},
        "Refuse to remove unowned snapshot contents",
    )
    require(
        all(
            Path(item["native"]).parent == directory
            and file_sha(Path(item["native"])) == item["sha256"]
            for item in value["files"]
        ),
        "Native snapshot changed; retain evidence",
    )
    shutil.rmtree(directory)


def leaderboard(run, binding, dataset):
    from quant.research_fast.evaluation import EconomicsResult, FoldEvaluation, first_round_screen

    models = {name: [] for name in IDS}
    for fold in make_folds():
        for config in IDS:
            receipt = verified(run, fold, config, binding, dataset)
            require(receipt is not None, "60 complete jobs required; no partial leaderboard")
            value = receipt["evaluation"]
            models[config].append(
                FoldEvaluation(
                    value["metadata"],
                    value["metrics"],
                    {int(k): EconomicsResult(None, None, v) for k, v in value["economics"].items()},
                )
            )
    result = first_round_screen(models)
    require(result["status"] == "SPRINT_SCREEN_ONLY", "Shared formal screen incomplete")
    text = [
        "# FR-v6 第一轮统一排行榜",
        "",
        f"Binding SHA256: `{_sha(binding)}`",
        "",
        "60项同合同完成；IC/收益/成本/换手/Sharpe为六fold等权平均，MDD为最差fold。",
        "IC与sign列依次为BTC/ETH；孤立测试周不冒充连续收益。费用/点差/滑点为20/2/8bps。",
        "仅CONDITIONAL_FUTURE_VALID_ENDPOINT_TRADE_PRICE_PROXY；无真实BBO/候选/生产资格。",
        "时间为worker墙钟，RAM为进程峰值；TS2Vec两probe共享时间/峰值不可重复加总。",
        "",
        "|config|flow IC|sign|return P|return S|RV rank|gross|fee|spread|slippage|"
        "cost|net|turnover|Sharpe|MDD|time s|RAM B|GPU h|screen|",
        "|" + "---|" * 19,
    ]
    for row in result["leaderboard"]:
        config, folds = row["config"], models[row["config"]]
        cells = [config]
        for metric in (
            "flow_IC",
            "flow_sign_accuracy",
            "return_Pearson_IC",
            "return_Spearman_IC",
            "RV_rank_IC",
        ):
            cells.append(
                "/".join(
                    "null"
                    if any(f.metrics[s][metric] is None for f in folds)
                    else f"{np.mean([f.metrics[s][metric] for f in folds]):.5g}"
                    for s in STREAMS[:2]
                )
            )
        summaries = [f.economics[2].summary for f in folds]
        cells.append(f"{np.mean([s['gross_proxy_return'] for s in summaries]):.6g}")
        for key, proportion in (("fees", 1), ("execution_costs", 0.2), ("execution_costs", 0.8)):
            fraction = np.mean([s[key] / s["initial_nav"] for s in summaries]) * proportion
            cells.append(f"{fraction:.6g}")
        for key in ("estimated_cost", "net_proxy_return", "turnover", "sharpe"):
            cells.append(f"{np.mean([f.economics[2].summary[key] for f in folds]):.6g}")
        cells += [
            f"{max(f.economics[2].summary['max_drawdown'] for f in folds):.6g}",
            f"{sum(f.metadata['resources']['worker_seconds'] for f in folds):.6g}",
            str(max(f.metadata["resources"]["process_peak_RAM_bytes"] for f in folds)),
            "0",
            row["screen"]["status"],
        ]
        text.append("|" + "|".join(cells) + "|")
    text += [
        "",
        "晋级方向（最多3）：" + json.dumps(result["top_directions"], ensure_ascii=False),
        "",
        "费用/点差/滑点列为初始NAV占比。4/8bps spread和逐fold工件见绑定STATE receipt。",
    ]
    final = run / "FIRST_ROUND_SCREEN.json"
    if not final.exists():
        publish(final, result)
    else:
        require(json.loads(final.read_text()) == result, "Final screen receipt changed")
    target = ROOT / "reports/fast_research/MODEL_LEADERBOARD.md"
    content = "\n".join(text) + "\n"
    if target.exists():
        require(target.read_text() == content, "Existing leaderboard differs; preserve it")
    else:
        with target.open("x") as writer:
            writer.write(content)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path)
    parser.add_argument("--preflight-only", action="store_true")
    parser.add_argument("--worker", nargs=2, metavar=("FOLD", "GROUP"))
    parser.add_argument("--lock-fd", type=int, default=-1)
    args = parser.parse_args()
    resources.status()
    if args.preflight_only:
        dataset, _ = preflight()
        print(
            json.dumps(
                {
                    "status": "FORMAL_PREFLIGHT_PASS_NO_FIT",
                    "model_fits": 0,
                    "complete_days": len(dataset.complete_days),
                }
            )
        )
        return
    require(args.run_dir is not None, "Explicit owned STATE run directory required")
    run = args.run_dir.resolve()
    require(run.is_relative_to(STATE.resolve()) and run != STATE.resolve(), "STATE ownership")
    if args.worker:
        binding = json.loads((run / "RUN_BINDING.json").read_text())
        fold = next(f for f in make_folds() if f.name == args.worker[0])
        worker(run, fold, args.worker[1], binding, args.lock_fd)
        return
    with (STATE / ".fr-first-round.lock").open("a+") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        dataset, manifests = preflight()
        binding_path = run / "RUN_BINDING.json"
        if run.exists():
            binding = json.loads(binding_path.read_text())
            require(
                binding["sources"] == sources()
                and binding["manifests"] == manifests
                and binding["runtime"] == runtime(),
                "Resume source/protocol/manifest binding changed",
            )
            attach_index(dataset, run, binding)
        else:
            disk.check(reserve=1_000_000_000)
            run.mkdir()
            index = dataset.prepare_index(run / "endpoints.i64")
            binding = {
                "sources": sources(),
                "runtime": runtime(),
                "manifests": manifests,
                "seed": 20261001,
                "dataset_sha256": dataset.contract_sha256,
                "index_sha256": index["sha256"],
                "endpoints": index["endpoints"],
                "configs": IDS,
                "folds": [f.name for f in make_folds()],
            }
            publish(binding_path, binding)
        for fold in make_folds():
            folder = run / fold.name
            folder.mkdir(exist_ok=True)
            native = folder / "native"
            recover_shared_pair(run, fold, binding, dataset)
            pending = [c for c in IDS if verified(run, fold, c, binding, dataset) is None]
            require(
                not (
                    any(c.startswith("TS2VEC-") for c in pending)
                    and not all(c in pending for c in IDS[7:9])
                ),
                "Partial TS2Vec pair: no refit",
            )
            if pending and not native.exists():
                selected = [
                    s
                    for s in dataset.shards
                    if s.end_us > fold.train_start_us - 1_280_000_000
                    and s.start_us < fold.test_end_us
                ]
                native_shard_snapshot(selected, native)
            for config in pending:
                if config == IDS[8]:
                    continue
                group = "TS2VEC-SHARED" if config == IDS[7] else config
                disk.check(reserve=100_000_000)
                subprocess.run(
                    [
                        sys.executable,
                        str(SCRIPT),
                        "--run-dir",
                        str(run),
                        "--worker",
                        fold.name,
                        group,
                        "--lock-fd",
                        str(lock.fileno()),
                    ],
                    check=True,
                    pass_fds=(lock.fileno(),),
                    env={**os.environ, "CUDA_VISIBLE_DEVICES": "", "PYTHONDONTWRITEBYTECODE": "1"},
                )
                print(json.dumps({"fold": fold.name, "completed": group}), flush=True)
            if native.exists():
                cleanup_snapshot(native)
        leaderboard(run, binding, dataset)


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(
            json.dumps({"status": "REJECTED_OR_FAILED_NO_LEADERBOARD", "reason": str(error)}),
            flush=True,
        )
        raise
