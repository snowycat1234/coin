"""One bounded, preregistered hourly tabular study. Development evidence only."""

from __future__ import annotations

import fcntl
import gc
import hashlib
import json
import time
from dataclasses import replace
from datetime import datetime
from pathlib import Path

import numpy as np
import polars as pl

from .alpha_rules_v2 import HOUR_US, executable_labels_v2, hysteresis_targets_v2, r2_gates
from .backtest import BacktestConfig, run_backtest
from .baselines_v2 import baseline_targets_v2
from .execution_contract import ExecutionContractV2
from .features_v2 import FEATURE_NAMES_V2, feature_contract_v2, feature_schema_v2
from .hold_acceptance import verify_hold_lineage
from .operations import date_us, frame_digest
from .paths import ROOT, STATE
from .predictor import (
    contracts_from_execution,
    load_frozen_predictor_bytes,
    make_predictor_manifest,
)

SOURCE_FILES = (
    "research_v2.py",
    "alpha_rules_v2.py",
    "features_v2.py",
    "predictor.py",
    "backtest.py",
    "shadow_v2.py",
    "execution_contract.py",
    "decision_policy.py",
    "policy_acceptance.py",
    "hold_acceptance.py",
    "baselines_v2.py",
    "data.py",
    "disk.py",
    "resources.py",
    "paths.py",
    "metrics.py",
    "cli_research_v2.py",
)
RECEIPTS = (
    "A01_EXECUTION_PARITY_ACCEPTANCE.json",
    "A05_POLICY_EXECUTION_ACCEPTANCE.json",
    "A05_HOLD_REPAIR_ACCEPTANCE.json",
    "A02_CANONICAL_ACCEPTANCE.json",
    "A03_NATIVE_INFERENCE_ACCEPTANCE.json",
    "A04_FEATURE_ACCEPTANCE.json",
)


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def fingerprint(value) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    ).hexdigest()


def write_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + "\n")
    temporary.replace(path)


def add_months(value: str, months: int) -> str:
    current = datetime.fromisoformat(value)
    index = current.year * 12 + current.month - 1 + months
    return f"{index // 12:04d}-{index % 12 + 1:02d}-01"


def load_protocol_v2(path: Path) -> dict:
    protocol = json.loads(path.read_text())
    if (
        protocol["version"] != "nonlinear_hourly_v2"
        or protocol["interval"] != "1h"
        or protocol["development_end"] != "2026-03-01"
        or protocol["cv_start"] != "2024-01-01"
        or protocol["cv_end"] != "2026-03-01"
        or protocol["max_configurations"] != 6
        or protocol["feature_count"] != 40
        or protocol["latency_minutes"] != 1
        or protocol["label_horizon_minutes"] != 240
        or protocol["minimum_hold_minutes"] != 120
        or protocol["gpu"] is not False
        or protocol["cpu_threads"] != 2
        or protocol["scaler"] != "none"
        or protocol["train_months"] != 24
        or protocol["embargo_hours"] != 1
        or protocol["test_months"] != 3
        or protocol["stride_months"] != 3
        or protocol["state_path"] != "state/research_nonlinear_v2.json"
        or protocol["output_dir"] != "reports/generated/A05_NONLINEAR_V2"
        or protocol["baseline_names"] != ["B0", "B1", "B2", "B3", "B4"]
        or protocol["active_baselines"] != ["B2", "B3", "B4"]
        or protocol["prediction_tail_policy"] != "last_4h_flat_for_shared_terminal_policy"
        or protocol["final_train_months"] != 24
        or protocol["final_train_end"] != "2026-03-01"
        or protocol["final_train_only_if_r2_passed"] is not True
        or protocol["cost_scenarios"] != ["base", "fee_x2", "slippage_x2"]
        or protocol["thresholds_bps"]
        != {
            "A": {"enter_gt": 45, "exit_lt": 15},
            "B": {"enter_gt": 60, "exit_lt": 15},
            "C": {"enter_gt": 75, "exit_lt": 30},
        }
    ):
        raise ValueError("Protocol differs from the frozen V2 study budget or boundary")
    configs = protocol["configurations"]
    expected = {f"{model}_{group}" for model in ("LGB", "XGB") for group in ("A", "B", "C")}
    if len(configs) != 6 or {item["id"] for item in configs} != expected:
        raise ValueError("Exactly six unique preregistered configurations required")
    for item in configs:
        model = "lightgbm" if item["id"].startswith("LGB_") else "xgboost"
        if (
            item["model_type"] != model
            or item["threshold"] != item["id"][-1]
            or item["rounds"] != 300
            or item["params"].get("seed") != 20261001
        ):
            raise ValueError("Model, threshold, fixed rounds or seed changed")
        params = item["params"]
        if model == "lightgbm":
            if params.get("device_type") != "cpu" or params.get("num_threads") != 2:
                raise ValueError("LightGBM must use two CPU threads")
        elif params.get("device") != "cpu" or params.get("nthread") != 2:
            raise ValueError("XGBoost must use two CPU threads")
    return protocol


def shared_terminal_flat(targets: pl.DataFrame, bars: pl.DataFrame, end_us: int) -> pl.DataFrame:
    """The known evaluation end has the same four-hour flat tail for every account."""
    tail = (
        bars.filter(
            (pl.col("available_us") >= end_us - 4 * HOUR_US) & (pl.col("available_us") < end_us)
        )
        .select("symbol", "available_us")
        .with_columns(pl.lit(0.0).alias("target_weight"))
        .select(targets.columns)
    )
    prior = targets.filter(pl.col("available_us") < end_us - 4 * HOUR_US)
    return pl.concat([prior, tail]).sort("available_us", "symbol")


def make_folds_v2(protocol: dict) -> list[dict]:
    start, end, output = protocol["cv_start"], protocol["cv_end"], []
    while date_us(start) < date_us(end):
        stop = min(add_months(start, protocol["test_months"]), end)
        output.append(
            {
                "id": len(output),
                "train_start": add_months(start, -24),
                "test_start": start,
                "test_end": stop,
            }
        )
        start = add_months(start, protocol["stride_months"])
    if len(output) != 9:
        raise ValueError("Fixed study requires nine chronological folds")
    return output


def training_rows(samples: pl.DataFrame, fold: dict, embargo_hours: int = 1) -> pl.DataFrame:
    cutoff = date_us(fold["test_start"]) - embargo_hours * HOUR_US
    return (
        samples.filter(
            pl.col("label_valid")
            & (pl.col("available_us") >= date_us(fold["train_start"]))
            & (pl.col("label_end_us") < cutoff)
        )
        .drop_nulls(list(FEATURE_NAMES_V2) + ["gross_return"])
        .sort("available_us", "symbol")
    )


def registration_binding(protocol: dict, dataset_id: str, *, input_frames: dict) -> dict:
    from . import resources

    resources.status()
    lineage = verify_hold_lineage()
    native = json.loads((ROOT / "reports/A03_NATIVE_INFERENCE_ACCEPTANCE.json").read_text())
    feature = json.loads((ROOT / "reports/A04_FEATURE_ACCEPTANCE.json").read_text())
    baseline = json.loads((ROOT / "reports/A02_CANONICAL_ACCEPTANCE.json").read_text())
    if native.get("status") != "ENGINEERING_NATIVE_INFERENCE_PASS" or native[
        "production_source_sha256"
    ] != sha(ROOT / "src/quant/predictor.py"):
        raise RuntimeError("Actual native backend acceptance required")
    if feature.get("status") != "PASS" or feature["implementation_sha256"] != sha(
        ROOT / "src/quant/features_v2.py"
    ):
        raise RuntimeError("Current feature acceptance required")
    if (
        baseline.get("status") != "PASS"
        or baseline["dataset_id"] != dataset_id
        or sha(ROOT / baseline["output"] / "summary.json") != baseline["summary_sha256"]
        or sha(ROOT / "src/quant/baselines_v2.py") != baseline["baseline_implementation_sha256"]
    ):
        raise RuntimeError("Strong baseline artifact binding failed")
    import lightgbm
    import xgboost

    if any(
        native["models"][name]["library_version"] != version
        for name, version in {
            "lightgbm": lightgbm.__version__,
            "xgboost": xgboost.__version__,
        }.items()
    ):
        raise RuntimeError("Native dependency versions differ from acceptance")

    return {
        "protocol_sha256": fingerprint(protocol),
        "dataset_id": dataset_id,
        "input_frames": {
            name: {"rows": len(frame), "sha256": frame_digest(frame)}
            for name, frame in input_frames.items()
        },
        "state_path": protocol["state_path"],
        "output_dir": protocol["output_dir"],
        "execution_lineage": lineage,
        "feature_contract": feature_contract_v2(),
        "source_hashes": {
            "src/quant/" + name: sha(ROOT / "src/quant" / name) for name in SOURCE_FILES
        },
        "receipts": {name: sha(ROOT / "reports" / name) for name in RECEIPTS},
        "dependency_lock_sha256": sha(ROOT / "uv.lock"),
        "native_versions": {"lightgbm": lightgbm.__version__, "xgboost": xgboost.__version__},
    }


def register_once(path: Path, binding: dict, *, resume_reason: str | None = None) -> dict:
    if path.exists():
        state = json.loads(path.read_text())
        if state["binding"] != binding:
            raise RuntimeError("Registered code/data/protocol changed; no additional study allowed")
        if state["status"] in {"STOP_v2", "ALPHA_CANDIDATE"}:
            raise RuntimeError("Study already completed; immutable results cannot be rerun")
        if not resume_reason:
            raise RuntimeError("Interrupted study requires an explicit technical resume reason")
        # A fit without committed hashes cannot be silently run again after seeing output.
        if state.get("inflight_fit"):
            raise RuntimeError("Uncommitted fit exists; preserve evidence and audit before resume")
        state["audit"].append({"event": "technical_resume", "reason": resume_reason})
    else:
        state = {
            "status": "REGISTERED",
            "binding": binding,
            "completed_fits": {},
            "inflight_fit": None,
            "fit_count": 0,
            "final_fit_count": 0,
            "audit": [{"event": "registered_before_any_fit", "created_us": time.time_ns() // 1000}],
        }
    write_json(path, state)
    return state


def verify_registered_sources(binding: dict, protocol_path: Path) -> None:
    for relative, digest in binding["source_hashes"].items():
        if sha(ROOT / relative) != digest:
            raise RuntimeError("Registered source changed during the study")
    if sha(ROOT / "uv.lock") != binding["dependency_lock_sha256"]:
        raise RuntimeError("Registered dependency lock changed during the study")
    if fingerprint(load_protocol_v2(protocol_path)) != binding["protocol_sha256"]:
        raise RuntimeError("Registered protocol changed during the study")


def _fit_export(config: dict, train: pl.DataFrame, test: pl.DataFrame) -> tuple[bytes, np.ndarray]:
    # Matrix allocation is a few MB; no preprocessing is fitted on held-out samples.
    # Match the frozen inference schema's float64 input. XGBoost performs its
    # own internal conversion in both research and frozen inference DMatrix.
    x = train.select(FEATURE_NAMES_V2).to_numpy().astype(np.float64)
    y = train["gross_return"].to_numpy().astype(np.float64)
    test_x = test.select(FEATURE_NAMES_V2).to_numpy().astype(np.float64)
    if config["model_type"] == "lightgbm":
        import lightgbm as lgb

        dataset = lgb.Dataset(x, label=y, feature_name=list(FEATURE_NAMES_V2), free_raw_data=True)
        model = lgb.train(config["params"], dataset, num_boost_round=config["rounds"])
        prediction = model.predict(test_x, num_threads=2)
        blob = model.model_to_string().encode()
    else:
        import xgboost as xgb

        dataset = xgb.DMatrix(x, label=y, feature_names=list(FEATURE_NAMES_V2), nthread=2)
        model = xgb.train(config["params"], dataset, num_boost_round=config["rounds"])
        prediction = model.predict(
            xgb.DMatrix(test_x, feature_names=list(FEATURE_NAMES_V2), nthread=2)
        )
        blob = bytes(model.save_raw(raw_format="json"))
    prediction = np.asarray(prediction, dtype=float)
    if len(blob) > 2_000_000:
        raise RuntimeError("Fixed tree study exceeded its 2 MB per-model artifact reserve")
    if prediction.shape != (len(test),) or not np.isfinite(prediction).all():
        raise RuntimeError("Native regressor returned invalid predictions")
    return blob, prediction


def _manifest(blob: bytes, config: dict, train: pl.DataFrame, cutoff: str) -> dict:
    contract = ExecutionContractV2()
    cost, risk = contracts_from_execution(contract)
    columns = ["available_us", "symbol", *FEATURE_NAMES_V2, "gross_return", "label_end_us"]
    return make_predictor_manifest(
        blob,
        model_type=config["model_type"],
        feature_schema=feature_schema_v2(),
        execution_contract=contract,
        cost_contract=cost,
        risk_contract=risk,
        training_cutoff=cutoff + "T00:00:00Z",
        training_last_available_us=int(train["available_us"].max()),
        training_last_label_end_us=int(train["label_end_us"].max()),
        training_data_sha256=frame_digest(train.select(columns)),
    )


def _verify_native_predictions(
    blob: bytes, manifest: dict, test: pl.DataFrame, predictions: np.ndarray
) -> float:
    contract = ExecutionContractV2()
    cost, risk = contracts_from_execution(contract)
    predictor = load_frozen_predictor_bytes(
        blob, manifest, execution_contract=contract, cost_contract=cost, risk_contract=risk
    )
    matrix = test.select(FEATURE_NAMES_V2).head(20).to_numpy().astype(np.float64)
    restored = np.array(
        [
            predictor.predict(dict(zip(FEATURE_NAMES_V2, map(float, row), strict=True)))[
                "expected_return"
            ]
            for row in matrix
        ]
    )
    error = float(np.max(np.abs(restored - predictions[: len(restored)])))
    if not np.allclose(restored, predictions[: len(restored)], atol=1e-10, rtol=1e-8):
        raise AssertionError("Native export/inference prediction parity failed")
    return error


def run_research_v2(
    protocol_path: Path,
    features: pl.DataFrame,
    minutes: pl.DataFrame,
    bars: pl.DataFrame,
    *,
    dataset_id: str,
    resume_reason: str | None = None,
    progress=lambda event: None,
) -> dict:
    from .disk import check
    from .resources import status

    protocol = load_protocol_v2(protocol_path)
    state_path = (ROOT / protocol["state_path"]).resolve()
    output = (ROOT / protocol["output_dir"]).resolve()
    if not state_path.is_relative_to(ROOT / "state") or not output.is_relative_to(ROOT / "reports"):
        raise ValueError("Study artifacts must use D project state/reports")
    cutoff = date_us(protocol["development_end"])
    if (
        minutes["open_us"].max() >= cutoff
        or bars["available_us"].max() >= cutoff
        or features["available_us"].max() >= cutoff
    ):
        raise ValueError("Locked historical test rows prohibited")
    check(reserve=1_500_000_000)
    STATE.mkdir(parents=True, exist_ok=True)
    with (STATE / "nonlinear_v2.lock").open("a+") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        binding = registration_binding(
            protocol,
            dataset_id,
            input_frames={
                "features": features,
                "minutes": minutes,
                "bars": bars,
            },
        )
        preflight_path = ROOT / "reports/A05_RESEARCH_PREFLIGHT_ACCEPTANCE.json"
        preflight = json.loads(preflight_path.read_text())
        if (preflight.get("status") != "ENGINEERING_PREFLIGHT_PASS"
                or preflight.get("source_hashes") != binding["source_hashes"]):
            raise RuntimeError("Current study preflight acceptance required before any fit")
        binding["engineering_preflight_sha256"] = sha(preflight_path)
        if not state_path.exists() and output.exists() and any(output.iterdir()):
            raise RuntimeError("Orphaned study artifacts exist; refuse an unregistered repeat")
        state = register_once(state_path, binding, resume_reason=resume_reason)
        if "resource_start" not in state:
            state["resource_start"] = status()
            write_json(state_path, state)
        output.mkdir(parents=True, exist_ok=True)
        write_json(output / "REGISTRATION.json", state["binding"])
        started = time.monotonic()
        try:
            samples = executable_labels_v2(features, minutes)
            folds = make_folds_v2(protocol)
            cv_start, cv_end = date_us(protocol["cv_start"]), date_us(protocol["cv_end"])
            all_predictions = {}
            for config in protocol["configurations"]:
                chunks = []
                for fold in folds:
                    verify_registered_sources(binding, protocol_path)
                    key = f"{config['id']}:fold{fold['id']}"
                    folder = output / config["id"] / f"fold{fold['id']}"
                    if key in state["completed_fits"]:
                        receipt = state["completed_fits"][key]
                        for file, digest in receipt["artifacts"].items():
                            if sha(output / file) != digest:
                                raise RuntimeError("Committed fit artifact changed")
                        chunks.append(pl.read_parquet(folder / "predictions.parquet"))
                        continue
                    train = training_rows(samples, fold, protocol["embargo_hours"])
                    test = features.filter(
                        (pl.col("available_us") >= date_us(fold["test_start"]))
                        & (pl.col("available_us") < date_us(fold["test_end"]))
                    )
                    if len(train) < protocol["minimum_training_rows"] or test.is_empty():
                        raise RuntimeError("Fixed fold has insufficient data; no silent shortening")
                    if state["fit_count"] >= 54:
                        raise RuntimeError("Registered 54-fit budget exhausted")
                    state.update(status="RUNNING", inflight_fit=key)
                    state["fit_count"] += 1
                    write_json(state_path, state)
                    blob, prediction = _fit_export(config, train, test)
                    manifest = _manifest(blob, config, train, fold["test_start"])
                    error = _verify_native_predictions(blob, manifest, test, prediction)
                    verify_registered_sources(binding, protocol_path)
                    folder.mkdir(parents=True, exist_ok=False)
                    model_path = folder / (
                        "model.txt" if config["model_type"] == "lightgbm" else "model.json"
                    )
                    model_path.write_bytes(blob)
                    write_json(folder / "manifest.json", manifest)
                    predicted = test.select("symbol", "available_us").with_columns(
                        pl.Series("expected_return", prediction)
                    )
                    predicted.write_parquet(folder / "predictions.parquet")
                    receipt = {
                        "rows": len(train),
                        "test_rows": len(test),
                        "fold": fold,
                        "max_train_label_end_us": int(train["label_end_us"].max()),
                        "native_parity_max_error": error,
                        "training_sha256": manifest["training_data_sha256"],
                        "artifacts": {
                            str(file.relative_to(output)): sha(file) for file in folder.iterdir()
                        },
                    }
                    state["completed_fits"][key] = receipt
                    state["inflight_fit"] = None
                    write_json(state_path, state)
                    chunks.append(predicted)
                    progress(
                        {
                            "module": "A05",
                            "completed_fit": key,
                            "fit_count": state["fit_count"],
                            "max_fit_count": 54,
                        }
                    )
                    del train, test, blob, prediction
                    gc.collect()
                prediction = pl.concat(chunks).sort("available_us", "symbol")
                # Every observed complete hour appears in the policy. Missing model
                # features become explicit null/risk exits, never stale predictions.
                decisions = (
                    bars.filter(
                        (pl.col("available_us") >= cv_start) & (pl.col("available_us") < cv_end)
                    )
                    .select("symbol", "available_us")
                    .join(prediction, on=["symbol", "available_us"], how="left")
                )
                decisions = decisions.with_columns(
                    pl.when(pl.col("available_us") >= cv_end - 4 * HOUR_US)
                    .then(None)
                    .otherwise(pl.col("expected_return"))
                    .alias("expected_return")
                )
                all_predictions[config["id"]] = hysteresis_targets_v2(
                    decisions, config["threshold"]
                )
            settings = BacktestConfig(start_us=cv_start, end_us=cv_end)
            scenarios = {
                "base": settings,
                "fee_x2": replace(settings, fee_multiplier=2),
                "slippage_x2": replace(settings, slippage_multiplier=2),
            }
            baseline_metrics = {}
            for name in protocol["baseline_names"]:
                targets = shared_terminal_flat(baseline_targets_v2(bars, name), bars, cv_end)
                result = run_backtest(bars, minutes, targets, settings)
                result.write_report(output / "baselines", name, disk_checked=True)
                baseline_metrics[name] = result.summary
            results = {}
            for config in protocol["configurations"]:
                metrics = {}
                for scenario, parameters in scenarios.items():
                    result = run_backtest(bars, minutes, all_predictions[config["id"]], parameters)
                    result.write_report(
                        output / config["id"] / "performance", scenario, disk_checked=True
                    )
                    metrics[scenario] = result.summary
                gates = r2_gates(
                    metrics["base"],
                    {key: metrics[key] for key in ("fee_x2", "slippage_x2")},
                    {key: baseline_metrics[key] for key in protocol["active_baselines"]},
                )
                results[config["id"]] = {"metrics": metrics, "R2": gates}
                progress(
                    {
                        "module": "A06",
                        "configuration": config["id"],
                        "net_return": metrics["base"]["total_return"],
                        "R2_pass": gates["passed"],
                    }
                )
            passing = [
                item for item in protocol["configurations"] if results[item["id"]]["R2"]["passed"]
            ]
            passing.sort(
                key=lambda item: (
                    -results[item["id"]]["metrics"]["base"]["sharpe"],
                    results[item["id"]]["metrics"]["base"]["fees"],
                    item["id"],
                )
            )
            winner = passing[0] if passing else None
            final = None
            if winner is not None:
                state["inflight_fit"] = "FINAL_FROZEN_MODEL"
                state["final_fit_count"] += 1
                if state["final_fit_count"] != 1:
                    raise RuntimeError("Only one final fit is allowed")
                write_json(state_path, state)
                fold = {
                    "train_start": add_months(protocol["final_train_end"], -24),
                    "test_start": protocol["final_train_end"],
                }
                train = training_rows(samples, fold)
                test = train.tail(20)
                blob, predictions = _fit_export(winner, train, test)
                manifest = _manifest(blob, winner, train, protocol["final_train_end"])
                _verify_native_predictions(blob, manifest, test, predictions)
                folder = ROOT / "models/nonlinear_v2"
                folder.mkdir(parents=True, exist_ok=False)
                model_path = folder / (
                    "model.txt" if winner["model_type"] == "lightgbm" else "model.json"
                )
                model_path.write_bytes(blob)
                write_json(folder / "manifest.json", manifest)
                strategy = {
                    "version": "nonlinear_hourly_v2_frozen_strategy",
                    "configuration": winner["id"],
                    "predictor_release_sha256": manifest["release_sha256"],
                    "model_sha256": sha(model_path),
                    "decision_policy": {
                        "version": "hysteresis_v2",
                        "threshold": winner["threshold"],
                        "thresholds_bps": protocol["thresholds_bps"][winner["threshold"]],
                        "minimum_hold_minutes": 120,
                        "hold_basis": "actual_first_fill_distinct_from_financial_cycle",
                        "risk_override": protocol["risk_exit_override"],
                    },
                    "execution_lineage": binding["execution_lineage"],
                    "study_binding_sha256": fingerprint(binding),
                    "training_data_sha256": manifest["training_data_sha256"],
                    "training_cutoff": manifest["training_cutoff"],
                    "locked_historical_test_authorized": False,
                    "true_forward_days": 0,
                }
                strategy_sha = fingerprint(strategy)
                write_json(folder / "strategy_release.json", {
                    **strategy, "strategy_sha256": strategy_sha,
                })
                final = {
                    "configuration": winner["id"],
                    "model": str(model_path.relative_to(ROOT)),
                    "manifest": str((folder / "manifest.json").relative_to(ROOT)),
                    "release_sha256": manifest["release_sha256"],
                    "strategy_release": str((folder / "strategy_release.json").relative_to(ROOT)),
                    "strategy_sha256": strategy_sha,
                    "decision_policy": {
                        "threshold": winner["threshold"],
                        "minimum_hold_minutes": 120,
                    },
                }
                state["inflight_fit"] = None
            report = {
                "status": "ALPHA_CANDIDATE" if winner else "STOP_v2",
                "evidence_scope": "DEVELOPMENT_HISTORY",
                "true_forward_days": 0,
                "locked_historical_test_read": False,
                "locked_test_authorized": False,
                "binding": binding,
                "results": results,
                "baselines": baseline_metrics,
                "folds": folds,
                "cv_days": (cv_end - cv_start) // (24 * HOUR_US),
                "fit_count": state["fit_count"],
                "final_fit_count": state["final_fit_count"],
                "frozen_candidate": final,
                "artifacts": {
                    str(file.relative_to(output)): sha(file)
                    for file in sorted(output.rglob("*"))
                    if file.is_file() and file.name not in {"summary.json", "REPORT.md"}
                },
                "seconds": time.monotonic() - started,
                "resources": status(),
                "resource_start": state["resource_start"],
                "disk": check(),
            }
            verify_registered_sources(binding, protocol_path)
            write_json(output / "summary.json", report)
            lines = [
                "# A05/A06 受控非线性研究",
                "",
                f"结果：**{report['status']}**。",
                "",
                "所有数据均为开发历史；没有启封锁定测试，没有真实前向策略证据。",
                "",
                "|配置|净收益|Sharpe|MDD|费用2倍|滑点2倍|周期|R2|",
                "|---|---:|---:|---:|---:|---:|---:|---|",
            ]
            for name, item in results.items():
                base = item["metrics"]["base"]
                lines.append(
                    f"|{name}|{base['total_return']:.4%}|{base['sharpe']:.3f}|"
                    f"{base['max_drawdown']:.2%}|"
                    f"{item['metrics']['fee_x2']['total_return']:.4%}|"
                    f"{item['metrics']['slippage_x2']['total_return']:.4%}|"
                    f"{base['round_trip_count']}|{item['R2']['passed']}|"
                )
            lines += [
                "",
                "失败则停止本轮，不追加参数。研究通过仍须锁定历史测试授权及真实未来证据。",
                "日度观察MDD没有覆盖真实日内路径，不能视为实际交易风险保证。",
            ]
            (output / "REPORT.md").write_text("\n".join(lines) + "\n")
            state["status"] = report["status"]
            state["summary_sha256"] = sha(output / "summary.json")
            write_json(state_path, state)
            return report
        except BaseException as error:
            state["status"] = "INVALID_RUN"
            state["audit"].append({"event": "technical_failure", "error": repr(error)})
            write_json(state_path, state)
            raise
