"""Read-only audit of the single A05 study; never trains or opens locked prices.

Run with scripts/bounded.sh. Only --write-acceptance writes, and it writes a new
acceptance receipt after all real result checks succeed. Engineering helpers do
not grant alpha, locked-test, forward or deployment authority.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import math
import sqlite3
import tomllib
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

import numpy as np
import polars as pl

from quant.alpha_rules_v2 import HOUR_US, r2_gates
from quant.execution_contract import ExecutionContractV2
from quant.features_v2 import FEATURE_NAMES_V2, feature_contract_v2, feature_schema_v2
from quant.operations import date_us, frame_digest
from quant.paths import ROOT, STATE

DAY_US = 24 * HOUR_US
MINUTE_US = HOUR_US // 60
OUTPUT = "reports/generated/A05_NONLINEAR_V2"
REGISTRY = "state/research_nonlinear_v2.json"
ACCEPTANCE = "reports/A06_NONLINEAR_RESEARCH_ACCEPTANCE.json"
CONFIG_IDS = {f"{model}_{group}" for model in ("LGB", "XGB") for group in ("A", "B", "C")}
BASELINES = {f"B{index}" for index in range(5)}
SCENARIOS = {"base", "fee_x2", "slippage_x2"}
REQUIRED_SOURCES = {
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
}
REQUIRED_RECEIPTS = {
    "A01_EXECUTION_PARITY_ACCEPTANCE.json",
    "A05_POLICY_EXECUTION_ACCEPTANCE.json",
    "A05_HOLD_REPAIR_ACCEPTANCE.json",
    "A02_CANONICAL_ACCEPTANCE.json",
    "A03_NATIVE_INFERENCE_ACCEPTANCE.json",
    "A04_FEATURE_ACCEPTANCE.json",
}


class AuditRejected(ValueError):
    """Evidence is incomplete, inconsistent, modified or outside its boundary."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AuditRejected(message)


def digest(path: Path) -> str:
    result = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1_048_576), b""):
            result.update(block)
    return result.hexdigest()


def fingerprint(value) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    ).hexdigest()


def _unique(pairs):
    value = {}
    for key, item in pairs:
        require(key not in value, f"Duplicate JSON field: {key}")
        value[key] = item
    return value


def read_json(path: Path) -> dict:
    try:
        value = json.loads(
            path.read_text(),
            object_pairs_hook=_unique,
            parse_constant=lambda value: (_ for _ in ()).throw(
                AuditRejected(f"Nonfinite JSON value: {value}")
            ),
        )
    except (OSError, json.JSONDecodeError) as error:
        raise AuditRejected(f"Missing or invalid JSON evidence: {path}") from error
    require(isinstance(value, dict), f"JSON object required: {path}")
    return value


def safe_path(root: Path, relative: str, *, under: str | None = None) -> Path:
    require(isinstance(relative, str) and relative != "", "Empty artifact path")
    item = Path(relative)
    require(not item.is_absolute() and ".." not in item.parts, "Artifact path escaped root")
    path = (root / item).resolve()
    base = (root / under).resolve() if under else root.resolve()
    require(path.is_relative_to(base), "Artifact path escaped permitted directory")
    require(path.is_file(), f"Missing artifact: {relative}")
    return path


def compare(actual, expected, context: str) -> None:
    """Allow only ordinary floating-point summation error, not metric rounding."""
    if isinstance(expected, dict):
        require(isinstance(actual, dict) and set(actual) == set(expected), f"{context}: fields")
        for key, value in expected.items():
            compare(actual[key], value, f"{context}/{key}")
    elif isinstance(expected, list):
        require(isinstance(actual, list) and len(actual) == len(expected), f"{context}: length")
        for index, value in enumerate(expected):
            compare(actual[index], value, f"{context}/{index}")
    elif isinstance(expected, float):
        require(
            isinstance(actual, (float, int))
            and not isinstance(actual, bool)
            and math.isfinite(actual)
            and math.isfinite(expected)
            and math.isclose(actual, expected, rel_tol=1e-9, abs_tol=1e-8),
            f"{context}: numeric discrepancy",
        )
    else:
        require(actual == expected and type(actual) is type(expected), f"{context}: discrepancy")


def audit_hashes(root: Path, artifacts: dict, *, exact: bool = False) -> None:
    require(isinstance(artifacts, dict) and artifacts, "Artifact hashes required")
    for relative, expected in artifacts.items():
        path = safe_path(root, relative)
        require(digest(path) == expected, f"Artifact SHA256 mismatch: {relative}")
    if exact:
        current = {
            str(item.relative_to(root))
            for item in root.rglob("*")
            if item.is_file() and item.name not in {"summary.json", "REPORT.md"}
        }
        require(current == set(artifacts), "Unregistered or missing output artifacts")


def expected_folds() -> list[dict]:
    start, stop, output = date(2024, 1, 1), date(2026, 3, 1), []
    while start < stop:
        month_index = start.year * 12 + start.month - 1 + 3
        following = date(month_index // 12, month_index % 12 + 1, 1)
        output.append(
            {
                "id": len(output),
                "train_start": start.replace(year=start.year - 2).isoformat(),
                "test_start": start.isoformat(),
                "test_end": min(following, stop).isoformat(),
            }
        )
        start = following
    return output


def audit_fit_budget(state: dict, report: dict) -> None:
    expected = {f"{name}:fold{index}" for name in CONFIG_IDS for index in range(9)}
    require(set(state["completed_fits"]) == expected, "Exactly 54 independently committed fits")
    require(state["fit_count"] == report["fit_count"] == 54, "CV fit budget/count mismatch")
    require(state.get("inflight_fit") is None, "Uncommitted fit cannot be accepted")
    require(
        report["folds"] == expected_folds() and report["cv_days"] == 790,
        "Nine folds and the shared 790-day evaluation period required",
    )
    require(
        state["audit"][0]["event"] == "registered_before_any_fit",
        "Registration must precede every fit",
    )
    require(isinstance(state["audit"][0].get("created_us"), int), "Registration timestamp missing")
    for event in state["audit"]:
        if event["event"] == "technical_resume":
            require(
                isinstance(event.get("reason"), str) and event["reason"].strip(),
                "Technical resume reason missing",
            )


def audit_registration(root: Path, state: dict, report: dict, protocol: dict) -> dict:
    from quant.hold_acceptance import verify_hold_lineage

    binding = state["binding"]
    compare(report["binding"], binding, "summary registration")
    compare(read_json(root / OUTPUT / "REGISTRATION.json"), binding, "registration artifact")
    require(binding["protocol_sha256"] == fingerprint(protocol), "Protocol binding changed")
    require(
        binding["state_path"] == REGISTRY and binding["output_dir"] == OUTPUT,
        "Canonical once-only study paths required",
    )
    require(
        set(binding["source_hashes"]) == {"src/quant/" + name for name in REQUIRED_SOURCES},
        "Registered source set incomplete",
    )
    for relative, expected in binding["source_hashes"].items():
        require(
            digest(safe_path(root, relative, under="src/quant")) == expected,
            f"Registered source changed: {relative}",
        )
    require(set(binding["receipts"]) == REQUIRED_RECEIPTS, "Predecessor receipt set incomplete")
    for name, expected in binding["receipts"].items():
        require(
            digest(safe_path(root, "reports/" + name, under="reports")) == expected,
            f"Predecessor receipt changed: {name}",
        )
    require(
        digest(root / "uv.lock") == binding["dependency_lock_sha256"], "Dependency lock changed"
    )
    preflight_path = root / "reports/A05_RESEARCH_PREFLIGHT_ACCEPTANCE.json"
    require(
        binding["engineering_preflight_sha256"] == digest(preflight_path),
        "Engineering preflight receipt changed",
    )
    preflight = read_json(preflight_path)
    require(
        preflight["status"] == "ENGINEERING_PREFLIGHT_PASS"
        and preflight["maximum_cv_fits"] == 54
        and preflight["formal_market_model_fits"] == 0
        and preflight["protocol_sha256"] == binding["protocol_sha256"]
        and preflight["source_hashes"] == binding["source_hashes"]
        and preflight["predecessor_receipts"] == binding["receipts"]
        and preflight["native_versions"] == binding["native_versions"],
        "Registered preflight differs from actual immutable study inputs",
    )
    compare(binding["execution_lineage"], verify_hold_lineage(root), "Execution lineage")
    compare(binding["feature_contract"], feature_contract_v2(), "Feature contract")
    native = read_json(root / "reports/A03_NATIVE_INFERENCE_ACCEPTANCE.json")
    require(
        native["status"] == "ENGINEERING_NATIVE_INFERENCE_PASS"
        and native["production_source_sha256"]
        == binding["source_hashes"]["src/quant/predictor.py"],
        "Native inference acceptance does not bind current predictor",
    )
    for model, distribution in (("lightgbm", "lightgbm"), ("xgboost", "xgboost-cpu")):
        version = importlib.metadata.version(distribution)
        require(
            binding["native_versions"][model]
            == native["models"][model]["library_version"]
            == version,
            "CPU native dependency version changed",
        )
    dependency_receipt_path = root / "reports/CPU_RESEARCH_DEPENDENCIES.json"
    require(
        digest(dependency_receipt_path) == native["dependency_receipt_sha256"],
        "CPU dependency acceptance receipt changed",
    )
    dependency_receipt = read_json(dependency_receipt_path)
    require(
        dependency_receipt["status"] == "PASS"
        and dependency_receipt["cpu_only"] is True
        and dependency_receipt["gpu_used"] is False
        and dependency_receipt["lock_sha256"] == binding["dependency_lock_sha256"],
        "Accepted CPU dependency lock does not match this study",
    )
    packages = {
        item["name"]: item for item in tomllib.loads((root / "uv.lock").read_text())["package"]
    }
    for name in (
        "numpy",
        "polars",
        "pyarrow",
        "scipy",
        "scikit-learn",
        "lightgbm",
        "xgboost-cpu",
        "narwhals",
    ):
        require(
            importlib.metadata.version(name) == packages[name]["version"],
            f"Installed numerical dependency differs from lock: {name}",
        )
    for wheel in dependency_receipt["wheels"]:
        package = packages[wheel["name"]]
        require(
            package["version"] == wheel["version"]
            and any(
                member["hash"] == "sha256:" + wheel["sha256"]
                for member in package.get("wheels", [])
            ),
            "CPU dependency wheel hash differs from accepted lock",
        )
    baseline = read_json(root / "reports/A02_CANONICAL_ACCEPTANCE.json")
    require(
        baseline["status"] == "PASS"
        and baseline["dataset_id"] == binding["dataset_id"]
        and baseline["baseline_implementation_sha256"]
        == binding["source_hashes"]["src/quant/baselines_v2.py"],
        "Strong baseline proof changed",
    )
    require(
        digest(safe_path(root, baseline["output"] + "/summary.json", under="reports"))
        == baseline["summary_sha256"],
        "Strong baseline result artifact changed",
    )
    feature = read_json(root / "reports/A04_FEATURE_ACCEPTANCE.json")
    require(
        feature["status"] == "PASS"
        and feature["implementation_sha256"]
        == binding["source_hashes"]["src/quant/features_v2.py"],
        "Feature acceptance changed",
    )
    return binding


def audit_resources(report: dict) -> dict:
    start, end, disk = report.get("resource_start"), report["resources"], report["disk"]
    require(isinstance(start, dict), "Registered run resource_start evidence missing")
    for value in (start, end):
        require(
            value["aggregate_cgroup"].endswith("/coin-quant.slice")
            and 0 < value["ram_limit_bytes"] <= 5_000_000_000
            and 0 <= value["ram_current_bytes"] <= value["ram_limit_bytes"]
            and 0 <= value["ram_peak_bytes"] <= value["ram_limit_bytes"]
            and value["swap_bytes"] == 0
            and value["gpu_used"] is False,
            "Shared kernel 5GB/no-swap/CPU resource evidence failed",
        )
    require(
        start["aggregate_cgroup"] == end["aggregate_cgroup"]
        and start["ram_limit_bytes"] == end["ram_limit_bytes"]
        and end["ram_peak_bytes"] >= start["ram_peak_bytes"],
        "Resource scope continuity failed",
    )

    def events(value):
        return {
            name: int(count)
            for name, count in (line.split() for line in value["memory_events"].splitlines())
        }

    before, after = events(start), events(end)
    for name in ("oom", "oom_kill", "oom_group_kill"):
        require(
            name in before and name in after and after[name] == before[name],
            "OOM during the registered study",
        )
    require(
        disk["hard_limit_bytes"] == 40_000_000_000
        and disk["total_bytes"] == disk["project_bytes"] + disk["wsl_vhd_bytes"]
        and disk["total_bytes"] + disk["reserved_bytes"] < 36_000_000_000
        and disk["d_free_bytes"] >= disk["reserved_bytes"] + 4_000_000_000
        and disk["status"] in {"OK", "WARNING"},
        "D disk limit/emergency buffer evidence failed",
    )
    return {
        "kernel_ram_peak_bytes": end["ram_peak_bytes"],
        "ram_limit_bytes": end["ram_limit_bytes"],
        "swap_bytes": 0,
        "gpu_used": False,
        "oom_during_study": False,
        "recorded_disk_total_bytes": disk["total_bytes"],
        "resource_scope": "shared_project_kernel_cgroup_including_concurrent_monitoring",
    }


def _training_rows(samples: pl.DataFrame, fold: dict) -> pl.DataFrame:
    return (
        samples.filter(
            pl.col("label_valid")
            & (pl.col("available_us") >= date_us(fold["train_start"]))
            & (pl.col("label_end_us") < date_us(fold["test_start"]) - HOUR_US)
        )
        .drop_nulls([*FEATURE_NAMES_V2, "gross_return"])
        .sort("available_us", "symbol")
    )


def audit_fit(
    output: Path,
    receipt: dict,
    configuration: dict,
    fold: dict,
    train: pl.DataFrame,
    test: pl.DataFrame,
    *,
    native_parity: bool = True,
) -> dict:
    require(receipt["fold"] == fold, "Fit fold changed")
    require(
        receipt["rows"] == len(train) >= 5000 and receipt["test_rows"] == len(test) >= 20,
        "Fit training/test count mismatch",
    )
    cutoff = date_us(fold["test_start"])
    require(
        train["available_us"].min() >= date_us(fold["train_start"])
        and train["available_us"].max() < cutoff - HOUR_US
        and train["label_end_us"].max() < cutoff - HOUR_US,
        "Training feature/label crosses strict purge boundary",
    )
    require(
        receipt["max_train_label_end_us"] == train["label_end_us"].max(),
        "Fit label-boundary declaration differs from actual samples",
    )
    folder = f"{configuration['id']}/fold{fold['id']}"
    model_file = "model.txt" if configuration["model_type"] == "lightgbm" else "model.json"
    require(
        set(receipt["artifacts"])
        == {
            f"{folder}/{model_file}",
            f"{folder}/manifest.json",
            f"{folder}/predictions.parquet",
        },
        "Fit must bind model, manifest and predictions independently",
    )
    audit_hashes(output, receipt["artifacts"])
    model = safe_path(output, folder + "/" + model_file)
    manifest = read_json(output / folder / "manifest.json")
    predicted = pl.read_parquet(output / folder / "predictions.parquet")
    require(
        predicted.columns == ["symbol", "available_us", "expected_return"],
        "Prediction artifact schema changed",
    )
    require(
        predicted.select("symbol", "available_us").equals(test.select("symbol", "available_us")),
        "Prediction keys differ from all available feature-ready held-out rows",
    )
    require(
        predicted["expected_return"].null_count() == 0
        and predicted["expected_return"].is_finite().all(),
        "Nonfinite native predictions",
    )
    columns = ["available_us", "symbol", *FEATURE_NAMES_V2, "gross_return", "label_end_us"]
    train_sha = frame_digest(train.select(columns))
    require(
        receipt["training_sha256"] == manifest["training_data_sha256"] == train_sha,
        "Actual training matrix provenance SHA256 mismatch",
    )
    require(
        manifest["model_type"] == configuration["model_type"]
        and manifest["model_sha256"] == digest(model)
        and manifest["model_bytes"] == model.stat().st_size <= 2_000_000
        and manifest["training_cutoff"] == fold["test_start"] + "T00:00:00Z"
        and manifest["training_last_available_us"] == int(train["available_us"].max())
        and manifest["training_last_label_end_us"] == int(train["label_end_us"].max()),
        "Native manifest model/training boundary mismatch",
    )
    plain = {key: value for key, value in manifest.items() if key != "release_sha256"}
    require(fingerprint(plain) == manifest["release_sha256"], "Native release SHA256 mismatch")
    schema = {key: value for key, value in manifest["feature_schema"].items() if key != "sha256"}
    require(
        schema == feature_schema_v2()
        and fingerprint(schema) == manifest["feature_schema"]["sha256"],
        "Native 40-feature definition mismatch",
    )
    require(0 <= receipt["native_parity_max_error"] <= 1e-10, "Recorded native parity failed")
    error = None
    if native_parity:
        from quant.predictor import contracts_from_execution, load_frozen_predictor_bytes

        contract = ExecutionContractV2()
        cost, risk = contracts_from_execution(contract)
        predictor = load_frozen_predictor_bytes(
            model.read_bytes(),
            manifest,
            execution_contract=contract,
            cost_contract=cost,
            risk_contract=risk,
        )
        matrix = test.select(FEATURE_NAMES_V2).head(20).to_numpy()
        restored = np.array(
            [
                predictor.predict(dict(zip(FEATURE_NAMES_V2, row, strict=True)))["expected_return"]
                for row in matrix
            ]
        )
        stored = predicted["expected_return"].head(20).to_numpy()
        require(
            np.allclose(restored, stored, atol=1e-10, rtol=1e-8),
            "Independent native inference parity failed",
        )
        error = float(np.max(np.abs(restored - stored)))
    return {
        "configuration": configuration["id"],
        "fold": fold["id"],
        "rows": len(train),
        "training_sha256": train_sha,
        "max_train_label_end_us": int(train["label_end_us"].max()),
        "test_rows": len(test),
        "native_vectors_verified": 20 if native_parity else 0,
        "native_max_error": error,
    }


class MinutePrices:
    """Bounded column arrays from permitted development minutes; no price-file access."""

    def __init__(self, minutes: pl.DataFrame):
        self.assets = {}
        for frame in minutes.sort("symbol", "open_us").partition_by("symbol"):
            symbol = frame["symbol"][0]
            times = frame["open_us"].to_numpy()
            require(
                np.all(np.diff(times) > 0) and np.all(times % MINUTE_US == 0),
                "Unique ordered complete minute keys required",
            )
            self.assets[symbol] = {
                name: frame[name].to_numpy()
                for name in ("open_us", "open", "close", "quote_volume")
            }

    def value(self, symbol: str, timestamp: int, field: str, *, exact: bool = False):
        asset = self.assets[symbol]
        index = int(np.searchsorted(asset["open_us"], timestamp))
        present = index < len(asset["open_us"]) and asset["open_us"][index] == timestamp
        require(not exact or present, "Fill used a missing execution/capacity minute")
        if not present:
            index -= 1
            require(index >= 0, "Valuation precedes available development prices")
        return float(asset[field][index]), not present


def audit_financial_report(
    folder: Path,
    stem: str,
    declared: dict,
    scenario: str,
    prices: MinutePrices,
    *,
    expected_days: int = 790,
) -> dict:
    payload = read_json(folder / (stem + ".json"))
    config, summary = payload["config"], payload["summary"]
    compare(summary, declared, f"{stem} summary artifact")
    start, end = date_us("2024-01-01"), date_us("2026-03-01")
    require(
        config["start_us"] == start and config["end_us"] == end,
        "Account does not cover the common 790-day period",
    )
    fixed = {
        "initial_cash": 10000.0,
        "fee_bps": 10.0,
        "half_spread_bps": 1.0,
        "slippage_bps": 4.0,
        "latency_minutes": 1,
        "max_weight": 0.30,
        "max_gross": 0.60,
        "target_annual_vol": 0.10,
        "vol_window_days": 30,
        "min_vol_days": 20,
        "participation_rate": 0.001,
        "max_order_wait_minutes": 5,
        "min_notional": 10.0,
        "liquidate_at_end": False,
        "lot_step_by_symbol": {"BTCUSDT": 0.00001, "ETHUSDT": 0.0001},
        "fee_multiplier": 2.0 if scenario == "fee_x2" else 1.0,
        "slippage_multiplier": 2.0 if scenario == "slippage_x2" else 1.0,
    }
    for key, value in fixed.items():
        compare(config[key], value, f"{stem} configuration/{key}")
    contract = ExecutionContractV2()
    require(
        summary["execution_contract_version"] == "execution_v2"
        and summary["execution_contract_sha256"] == contract.digest()
        and summary["canonical_latency"] is True,
        "Legacy execution report cannot be certified",
    )
    nav, trades, orders, cycles = [
        pl.read_parquet(folder / f"{stem}_{name}.parquet")
        for name in ("daily_nav", "trades", "orders", "round_trips")
    ]
    require(len(nav) == expected_days, "Financial report daily evidence length mismatch")
    dates = [date(2024, 1, 1) + timedelta(days=index) for index in range(expected_days)]
    require(nav["date"].to_list() == dates, "NAV dates missing, duplicated or out of order")
    require(
        summary["start_utc"] == "2024-01-01T00:00:00+00:00"
        and summary["end_utc"] == "2026-03-01T00:00:00+00:00",
        "Financial summary period changed",
    )
    values = nav["nav"].to_numpy()
    require(np.isfinite(values).all() and np.all(values > 0), "Invalid NAV")
    previous = np.r_[config["initial_cash"], values[:-1]]
    returns = values / previous - 1
    volatility = float(np.std(returns, ddof=1) * math.sqrt(365)) if len(values) > 1 else 0.0
    full = np.r_[config["initial_cash"], values]
    computed = {
        "days": len(values),
        "initial_nav": config["initial_cash"],
        "final_nav": float(values[-1]),
        "total_return": float(values[-1] / config["initial_cash"] - 1),
        "annual_return": float((values[-1] / config["initial_cash"]) ** (365 / len(values)) - 1),
        "annual_volatility": volatility,
        "sharpe": float(np.mean(returns) * 365 / volatility) if volatility else 0.0,
        "max_drawdown": float(-np.min(full / np.maximum.accumulate(full) - 1)),
        "fees": float(nav["fees"].sum()),
        "execution_costs": float(nav["execution_costs"].sum()),
        "turnover": float(nav["turnover"].sum()),
        "trade_count": len(trades),
        "round_trip_count": len(cycles),
        "valuation_gap_days": int(nav["stale_prices"].sum()),
        "exposed_valuation_gap_days": int(nav["stale_exposure"].sum()),
        "daily_risk_observable": not nav["stale_exposure"].any(),
        "gross_pnl_before_costs": float(
            values[-1] - config["initial_cash"] + nav["fees"].sum() + nav["execution_costs"].sum()
        ),
    }
    for key, value in computed.items():
        compare(summary[key], value, f"{stem} recomputed/{key}")
    require(
        np.allclose(nav["return"].to_numpy(), returns, rtol=1e-9, atol=1e-10),
        "Stored daily returns do not match NAV",
    )
    cash, positions = float(config["initial_cash"]), {name: 0.0 for name in prices.assets}
    accounting, reconstructed, records = {}, [], list(trades.iter_rows(named=True))
    require(
        [item["execution_us"] for item in records]
        == sorted(item["execution_us"] for item in records),
        "Trade time ordering changed",
    )
    index, total_fees, total_costs, notional_total = 0, 0.0, 0.0, 0.0
    fee_rate = config["fee_bps"] * config["fee_multiplier"] / 10000
    execution_rate = contract.execution_rate(
        config["half_spread_bps"], config["slippage_bps"] * config["slippage_multiplier"]
    )
    for day_index, daily in enumerate(nav.iter_rows(named=True)):
        timestamp = date_us(daily["date"].isoformat()) + DAY_US - MINUTE_US
        day_fees, day_costs, day_notional = 0.0, 0.0, 0.0
        while index < len(records) and records[index]["execution_us"] <= timestamp + 1:
            trade = records[index]
            symbol, now = trade["symbol"], trade["execution_us"]
            require(
                symbol in positions and trade["side"] in {"buy", "sell"}, "Invalid trade asset/side"
            )
            direction = 1 if trade["side"] == "buy" else -1
            require(
                start <= now < end
                and now % MINUTE_US == 1
                and now >= contract.earliest_execution_us(trade["signal_us"]) + 1,
                "Fill precedes V2 causal eligibility",
            )
            require(
                trade["capacity_open_us"] == now - 1 - MINUTE_US,
                "Capacity used a future/unclosed minute",
            )
            mid = prices.value(symbol, now - 1, "open", exact=True)[0]
            quote = prices.value(symbol, trade["capacity_open_us"], "quote_volume", exact=True)[0]
            quantity = trade["quantity"]
            require(math.isfinite(quantity) and quantity > 0, "Invalid fill quantity")
            step = config["lot_step_by_symbol"][symbol]
            require(
                abs(quantity / step - round(quantity / step)) < 1e-6, "Fill violates quantity step"
            )
            fill = mid * (1 + direction * execution_rate)
            notional, fee, cost = (
                quantity * fill,
                quantity * fill * fee_rate,
                quantity * abs(fill - mid),
            )
            for field, value in {
                "mid_price": mid,
                "fill_price": fill,
                "notional": notional,
                "fee": fee,
                "execution_cost": cost,
                "capacity": quote * config["participation_rate"],
            }.items():
                compare(trade[field], value, f"{stem} fill/{field}")
            require(
                notional + 1e-7 >= config["min_notional"] and notional <= trade["capacity"] + 1e-7,
                "Fill violates amount/capacity",
            )
            if direction == 1 and positions[symbol] <= 1e-12:
                accounting[symbol] = {"entry_us": now, "cost": 0.0, "proceeds": 0.0, "fees": 0.0}
            require(symbol in accounting, "Sell without financial entry")
            cycle = accounting[symbol]
            cash -= direction * notional + fee
            positions[symbol] += direction * quantity
            if abs(positions[symbol]) < 1e-10:
                positions[symbol] = 0.0
            require(cash >= -1e-7 and positions[symbol] >= -1e-10, "Negative spot cash/position")
            compare(trade["cash_after"], cash, f"{stem} journal cash")
            fill_marks = {
                asset: prices.value(asset, now - 1, "open", exact=True)[0] for asset in positions
            }
            fill_nav = cash + sum(positions[asset] * price for asset, price in fill_marks.items())
            asset_weights = {
                asset: positions[asset] * price / fill_nav for asset, price in fill_marks.items()
            }
            compare(trade["nav_after"], fill_nav, f"{stem} actual post-fill NAV")
            compare(
                trade["asset_weight_after"],
                asset_weights[symbol],
                f"{stem} actual post-fill asset weight",
            )
            compare(
                trade["gross_weight_after"],
                sum(asset_weights.values()),
                f"{stem} actual post-fill gross weight",
            )
            cycle["fees"] += fee
            cycle["cost" if direction == 1 else "proceeds"] += (
                notional + fee if direction == 1 else notional - fee
            )
            if direction == -1 and positions[symbol] == 0:
                reconstructed.append(
                    {
                        "symbol": symbol,
                        "entry_us": cycle["entry_us"],
                        "exit_us": now,
                        "pnl": cycle["proceeds"] - cycle["cost"],
                        "fees": cycle["fees"],
                    }
                )
            if direction == 1:
                require(
                    max(asset_weights.values()) <= 0.30 + 1e-9
                    and sum(asset_weights.values()) <= 0.60 + 1e-9,
                    "New buy breached post-cost asset/gross risk",
                )
            day_fees += fee
            day_costs += cost
            day_notional += notional
            index += 1
        marks = {symbol: prices.value(symbol, timestamp, "close") for symbol in positions}
        expected_nav = cash + sum(positions[symbol] * mark[0] for symbol, mark in marks.items())
        for field, value in {
            "nav": expected_nav,
            "cash": cash,
            "fees": day_fees,
            "execution_costs": day_costs,
            "turnover": day_notional / previous[day_index],
            "gross_weight": (expected_nav - cash) / expected_nav,
        }.items():
            compare(daily[field], value, f"{stem} reconstructed daily/{field}")
        require(
            daily["stale_prices"] == any(mark[1] for mark in marks.values())
            and daily["stale_exposure"]
            == any(marks[symbol][1] and quantity > 1e-12 for symbol, quantity in positions.items()),
            "Daily stale-price risk evidence changed",
        )
        total_fees += day_fees
        total_costs += day_costs
        notional_total += day_notional
    require(index == len(records), "Trade outside observed daily trajectory")
    compare(cycles.to_dicts(), reconstructed, f"{stem} independently closed financial cycles")
    compare(summary["open_positions"], positions, f"{stem} final spot quantities")
    compare(summary["fees"], total_fees, f"{stem} actual fill fees")
    compare(summary["execution_costs"], total_costs, f"{stem} actual fill costs")
    filled = orders.filter(pl.col("status").is_in(["filled", "partial"]))
    require(
        set(orders["status"].unique().to_list()).issubset(
            {
                "expired",
                "gap_frozen",
                "minimum_hold",
                "below_min_notional",
                "dust_unexecuted",
                "capacity_below_min",
                "capacity_zero",
                "risk_limit",
                "partial",
                "filled",
            }
        ),
        "Unknown order-attempt status",
    )
    require(len(filled) == len(trades), "Filled orders and trades are not one-to-one")
    for order, trade in zip(filled.iter_rows(named=True), records, strict=True):
        require(
            order["open_us"] + 1 == trade["execution_us"]
            and order["symbol"] == trade["symbol"]
            and order["side"] == trade["side"]
            and order["signal_us"] == trade["signal_us"],
            "Order/fill identity mismatch",
        )
        compare(order["filled_notional"], trade["notional"], f"{stem} order filled notional")
    require(
        orders.filter(~pl.col("status").is_in(["filled", "partial"]))["filled_notional"].sum() == 0,
        "Rejected/unfilled order has fabricated notional",
    )
    return {
        "days": len(nav),
        "closed_cycles": len(reconstructed),
        "actual_trade_count": len(records),
        "net_pnl": float(values[-1] - config["initial_cash"]),
        "fees": total_fees,
        "execution_costs": total_costs,
        "gross_pnl_before_costs": computed["gross_pnl_before_costs"],
        "actual_one_way_notional": notional_total,
        "daily_risk_observable": computed["daily_risk_observable"],
    }


def audit_r2_summary(state: dict, report: dict) -> dict:
    require(
        set(report["results"]) == CONFIG_IDS and set(report["baselines"]) == BASELINES,
        "Fixed six models/five baselines required",
    )
    passing = []
    for name, item in report["results"].items():
        require(set(item["metrics"]) == SCENARIOS, "Both cost stress accounts required")
        recalculated = r2_gates(
            item["metrics"]["base"],
            {key: item["metrics"][key] for key in ("fee_x2", "slippage_x2")},
            {key: report["baselines"][key] for key in ("B2", "B3", "B4")},
        )
        compare(item["R2"], recalculated, f"{name} R2 recomputation")
        if recalculated["passed"]:
            passing.append(name)
    passing.sort(
        key=lambda name: (
            -report["results"][name]["metrics"]["base"]["sharpe"],
            report["results"][name]["metrics"]["base"]["fees"],
            name,
        )
    )
    winner = passing[0] if passing else None
    expected_status = "ALPHA_CANDIDATE" if winner else "STOP_v2"
    require(
        state["status"] == report["status"] == expected_status,
        "Final status differs from actual R2",
    )
    require(
        state["final_fit_count"] == report["final_fit_count"] == (1 if winner else 0),
        "Only the selected passing configuration may receive one final fit",
    )
    if winner:
        require(
            report["frozen_candidate"]["configuration"] == winner,
            "Frozen model differs from preregistered unique selection",
        )
    else:
        require(report["frozen_candidate"] is None, "STOP cannot freeze a final model")
    return {
        "passing_configurations": passing,
        "unique_selected_configuration": winner,
        "status": expected_status,
        "gate_interpretation": "development_history_only",
    }


def _locked_metadata_check(dataset_id: str) -> dict:
    # Read only authorization/attempt metadata, never any held-out price or result.
    db = STATE / "holdout.sqlite3"
    attempts = 0
    if db.exists():
        with sqlite3.connect(f"file:{db}?mode=ro", uri=True) as connection:
            for current_dataset, ticket_json in connection.execute(
                "SELECT dataset_id,ticket FROM attempts"
            ):
                ticket = json.loads(ticket_json)
                if current_dataset == dataset_id and ticket.get("engineering") is not True:
                    attempts += 1
    require(attempts == 0, "Locked historical test already consumed in the real release ledger")
    return {
        "real_locked_test_attempts": attempts,
        "price_files_read": 0,
        "basis": "report flags, sealed input provenance and read-only release ledger metadata",
    }


def audit_results(root: Path = ROOT) -> dict:
    """Audit actual canonical artifacts. No engineering root or trainer injection."""
    from quant.alpha_rules_v2 import executable_labels_v2
    from quant.cli_research_v2 import load_development
    from quant.features_v2 import build_features_v2
    from quant.research_v2 import load_protocol_v2
    from quant.resources import status

    require(root.resolve() == ROOT.resolve(), "Actual audit only accepts the canonical D project")
    status()
    output, state_path = root / OUTPUT, root / REGISTRY
    report, state = read_json(output / "summary.json"), read_json(state_path)
    require(
        state["summary_sha256"] == digest(output / "summary.json"), "Final summary hash changed"
    )
    require(
        report["evidence_scope"] == "DEVELOPMENT_HISTORY"
        and report["true_forward_days"] == 0
        and report["locked_historical_test_read"] is False
        and report["locked_test_authorized"] is False,
        "Evidence scope or locked authorization changed",
    )
    protocol = load_protocol_v2(root / "configs/experiments/nonlinear_v2.json")
    binding = audit_registration(root, state, report, protocol)
    audit_fit_budget(state, report)
    audit_hashes(output, report["artifacts"], exact=True)
    resource = audit_resources(report)
    compare(state.get("resource_start"), report["resource_start"], "Registered resource start")
    lock = read_json(root / "state/dataset_lock.json")
    require(binding["dataset_id"] == lock["dataset_id"], "Dataset ID changed")
    minutes, bars, inputs = load_development(lock)
    require(
        inputs["locked_month_price_files_opened"] == 0
        and minutes["open_us"].max() < date_us("2026-03-01")
        and bars["available_us"].max() < date_us("2026-03-01"),
        "Input price boundary violated",
    )
    for mapping in (inputs["minute_files"], inputs["hour_files"]):
        for relative, expected in mapping.items():
            require(
                digest(safe_path(root, relative, under="data")) == expected,
                "Sealed permitted data artifact changed",
            )
    features = build_features_v2(bars)
    for name, frame in {"minutes": minutes, "bars": bars, "features": features}.items():
        compare(
            binding["input_frames"][name],
            {"rows": len(frame), "sha256": frame_digest(frame)},
            f"Actual permitted input frame/{name}",
        )
    samples = executable_labels_v2(features, minutes)
    fit_checks = []
    for configuration in protocol["configurations"]:
        for fold in expected_folds():
            train = _training_rows(samples, fold)
            test = features.filter(
                (pl.col("available_us") >= date_us(fold["test_start"]))
                & (pl.col("available_us") < date_us(fold["test_end"]))
            )
            fit_checks.append(
                audit_fit(
                    output,
                    state["completed_fits"][f"{configuration['id']}:fold{fold['id']}"],
                    configuration,
                    fold,
                    train,
                    test,
                )
            )
    prices, financial = MinutePrices(minutes), {}
    for name in sorted(BASELINES):
        financial[name] = audit_financial_report(
            output / "baselines", name, report["baselines"][name], "base", prices
        )
    for name in sorted(CONFIG_IDS):
        for scenario in sorted(SCENARIOS):
            financial[f"{name}/{scenario}"] = audit_financial_report(
                output / name / "performance",
                scenario,
                report["results"][name]["metrics"][scenario],
                scenario,
                prices,
            )
    selection = audit_r2_summary(state, report)
    final = report["frozen_candidate"]
    final_check = None
    if final:
        from quant.predictor import contracts_from_execution, load_frozen_predictor_bytes

        model = safe_path(root, final["model"], under="models/nonlinear_v2")
        manifest = read_json(safe_path(root, final["manifest"], under="models/nonlinear_v2"))
        strategy = read_json(
            safe_path(root, final["strategy_release"], under="models/nonlinear_v2")
        )
        plain = {key: value for key, value in strategy.items() if key != "strategy_sha256"}
        require(
            fingerprint(plain) == strategy["strategy_sha256"] == final["strategy_sha256"],
            "Frozen strategy release SHA mismatch",
        )
        require(
            strategy["model_sha256"] == manifest["model_sha256"] == digest(model)
            and final["release_sha256"]
            == manifest["release_sha256"]
            == strategy["predictor_release_sha256"]
            and strategy["study_binding_sha256"] == fingerprint(binding)
            and strategy["configuration"] == final["configuration"]
            and strategy["locked_historical_test_authorized"] is False
            and strategy["true_forward_days"] == 0,
            "Frozen model/strategy registration mismatch",
        )
        config = next(
            item for item in protocol["configurations"] if item["id"] == final["configuration"]
        )
        require(
            strategy["decision_policy"]["threshold"] == config["threshold"]
            and strategy["decision_policy"]["thresholds_bps"]
            == protocol["thresholds_bps"][config["threshold"]]
            and strategy["decision_policy"]["minimum_hold_minutes"] == 120
            and strategy["decision_policy"]["hold_basis"]
            == "actual_first_fill_distinct_from_financial_cycle",
            "Frozen decision policy changed",
        )
        train = _training_rows(samples, {"train_start": "2024-03-01", "test_start": "2026-03-01"})
        columns = ["available_us", "symbol", *FEATURE_NAMES_V2, "gross_return", "label_end_us"]
        require(
            manifest["training_data_sha256"]
            == strategy["training_data_sha256"]
            == frame_digest(train.select(columns))
            and manifest["training_last_label_end_us"] == train["label_end_us"].max()
            and manifest["training_last_available_us"] == train["available_us"].max()
            and manifest["training_cutoff"] == "2026-03-01T00:00:00Z",
            "Final rolling 24-month train provenance/purge mismatch",
        )
        contract = ExecutionContractV2()
        cost, risk = contracts_from_execution(contract)
        predictor = load_frozen_predictor_bytes(
            model.read_bytes(),
            manifest,
            execution_contract=contract,
            cost_contract=cost,
            risk_contract=risk,
        )
        for row in train.select(FEATURE_NAMES_V2).tail(20).iter_rows(named=True):
            require(
                math.isfinite(predictor.predict(row)["expected_return"]),
                "Final native inference invalid",
            )
        final_check = {
            "configuration": config["id"],
            "model_sha256": digest(model),
            "training_sha256": manifest["training_data_sha256"],
            "native_vectors_verified": 20,
        }
    else:
        require(
            not (root / "models/nonlinear_v2").exists(),
            "STOP has unregistered final-model artifacts",
        )
    locked = _locked_metadata_check(binding["dataset_id"])
    return {
        "status": "PASS",
        "module": "A06_INDEPENDENT_RESULT_AUDIT",
        "created_utc": datetime.now(UTC).isoformat(),
        "evidence_scope": "DEVELOPMENT_HISTORY",
        "study_status": report["status"],
        "formal_cv_fits": 54,
        "final_fit_count": report["final_fit_count"],
        "financial_accounts": 23,
        "common_utc_days": 790,
        "true_forward_days": 0,
        "locked_historical_test_consumed": False,
        "study_summary_sha256": digest(output / "summary.json"),
        "study_state_sha256": digest(state_path),
        "study_binding_sha256": fingerprint(binding),
        "auditor_source_sha256": digest(Path(__file__)),
        "selection": selection,
        "resources": resource,
        "locked_metadata": locked,
        "fit_checks": fit_checks,
        "financial_reconciliation": financial,
        "frozen_candidate_check": final_check,
        "limits": [
            "PASS certifies the audit, not profitability or deployment eligibility.",
            "NAV/MDD are observed UTC daily values, not verified intraday extremes.",
            "The local hashes are audit bindings, not external anti-rewrite signatures.",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--write-acceptance",
        action="store_true",
        help="Write a NEW A06 receipt after actual evidence passes; never overwrite",
    )
    args = parser.parse_args()
    destination = ROOT / ACCEPTANCE
    if args.write_acceptance:
        require(not destination.exists(), "A06 acceptance already exists; do not overwrite")
    receipt = audit_results()
    if args.write_acceptance:
        with destination.open("x", encoding="utf-8") as stream:
            stream.write(json.dumps(receipt, indent=2, ensure_ascii=False, allow_nan=False) + "\n")
    print(
        json.dumps(
            {
                key: receipt[key]
                for key in (
                    "status",
                    "study_status",
                    "formal_cv_fits",
                    "final_fit_count",
                    "financial_accounts",
                    "common_utc_days",
                )
            },
            ensure_ascii=False,
        ),
        flush=True,
    )


if __name__ == "__main__":
    main()
