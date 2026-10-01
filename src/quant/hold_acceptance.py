"""Append hold correctness repairs without rewriting earlier acceptance evidence."""

from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path

import polars as pl

from .backtest import BacktestConfig, baseline_targets, run_backtest
from .execution_contract import ExecutionContractV2
from .execution_parity import cross_engine_parity, hold_repair_cases
from .operations import date_us
from .paths import ROOT
from .policy_acceptance import SOURCE_NAMES

RECEIPT = "reports/A05_HOLD_REPAIR_ACCEPTANCE.json"
REPAIRED = {"backtest.py", "shadow_v2.py", "execution_parity.py"}
SOURCES = (*SOURCE_NAMES, "hold_acceptance.py")


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def previous_evidence(root: Path = ROOT) -> dict:
    """Original sources and artifacts must still match their original receipts."""
    first_path = root / "reports/A01_EXECUTION_PARITY_ACCEPTANCE.json"
    policy_path = root / "reports/A05_POLICY_EXECUTION_ACCEPTANCE.json"
    first = json.loads(first_path.read_text())
    policy = json.loads(policy_path.read_text())
    digest = ExecutionContractV2().digest()
    if (first.get("status") != "PASS" or policy.get("status") != "PASS"
            or first.get("execution_contract_sha256") != digest
            or policy.get("execution_contract_sha256") != digest
            or policy.get("A01_sha256") != sha(first_path)
            or not first.get("cross_engine_parity", {}).get("pass")
            or not policy.get("cross_engine_policy", {}).get("pass")
            or not policy.get("default_baseline_invariance", {}).get("pass")):
        raise RuntimeError("Earlier execution/policy evidence failed")
    original = first["canonical_baselines"]
    if (original.get("status") != "PASS"
            or sha(root / original["path"] / "summary.json") != original["artifact_sha256"]):
        raise RuntimeError("Original baseline artifact changed")
    for report, archive in ((first, "legacy/a01_execution_v2"),
                            (policy, "legacy/a05_policy_original")):
        for relative, expected in report["source_hashes"].items():
            file = (root / relative).resolve()
            if not file.is_relative_to((root / "src/quant").resolve()):
                raise RuntimeError("Execution evidence source escaped project")
            if sha(file) != expected:
                if file.name not in REPAIRED or sha(root / archive / file.name) != expected:
                    raise RuntimeError(f"Previous source proof changed: {relative}")
    return {"A01_sha256": sha(first_path), "prior_policy_sha256": sha(policy_path),
            "execution_contract_sha256": digest}


def verify_hold_lineage(root: Path = ROOT) -> dict:
    previous = previous_evidence(root)
    path = root / RECEIPT
    if not path.exists():
        raise RuntimeError("Actual hold repair acceptance required before nonlinear study")
    receipt = json.loads(path.read_text())
    if (receipt.get("status") != "PASS"
            or any(receipt.get(key) != value for key, value in previous.items())
            or not receipt.get("default_baseline_invariance", {}).get("pass")
            or not receipt.get("cross_engine_policy", {}).get("pass")
            or not receipt.get("hold_repairs", {}).get("pass")):
        raise RuntimeError("Hold repair acceptance chain failed")
    sources = receipt["source_hashes"]
    if set(sources) != {"src/quant/" + name for name in SOURCES}:
        raise RuntimeError("Hold repair source set incomplete")
    for relative, digest in sources.items():
        if sha(root / relative) != digest:
            raise RuntimeError(f"Accepted hold implementation changed: {relative}")
    return {"status": "PASS", "basis": "A01_policy_and_hold_repair", **previous,
            "hold_receipt_sha256": sha(path), "source_hashes": sources}


def accept_hold_repair(progress=lambda event: None) -> dict:
    from .data import verify_dataset_lock
    from .disk import check
    from .resources import status

    path = ROOT / RECEIPT
    if path.exists():
        raise RuntimeError("Hold acceptance already exists; do not overwrite")
    started = time.monotonic()
    previous = previous_evidence()
    source_hashes = {"src/quant/" + name: sha(ROOT / "src/quant" / name) for name in SOURCES}
    check(reserve=300_000_000)
    repairs = hold_repair_cases()
    cases = [cross_engine_parity(), cross_engine_parity(partial=True),
             cross_engine_parity(fee_multiplier=2), cross_engine_parity(slippage_multiplier=2),
             cross_engine_parity(minimum_hold_minutes=120),
             cross_engine_parity(minimum_hold_minutes=120, force_exit=True)]
    lock = verify_dataset_lock()
    end = date_us("2026-03-01")
    files = [ROOT / name for name in lock["minute_files"] if Path(name).stem < "2026-03"]
    minutes = (pl.scan_parquet(files).filter(pl.col("valid_day") & (pl.col("open_us") < end))
               .select("symbol", "open_us", "open", "close", "quote_volume")
               .collect(engine="streaming"))
    bars = (pl.scan_parquet([ROOT / name for name in lock["bar_files"]
                            if Path(name).name == "1h.parquet"])
            .filter(pl.col("available_us") < end).collect(engine="streaming"))
    first = json.loads((ROOT / "reports/A01_EXECUTION_PARITY_ACCEPTANCE.json").read_text())
    folder = ROOT / first["canonical_baselines"]["path"]
    invariant = {}
    for name in ("B0", "B1", "B2"):
        targets = baseline_targets(bars, name)
        for scenario in ("base", "fee_x2", "slippage_x2"):
            stem = f"{name}_{scenario}"
            prior = json.loads((folder / f"{stem}.json").read_text())
            result = run_backtest(bars, minutes, targets, BacktestConfig(**prior["config"]))
            if result.summary != prior["summary"]:
                raise AssertionError(f"Reference metrics changed: {stem}")
            for label in ("daily_nav", "trades", "orders", "round_trips"):
                if not pl.read_parquet(folder / f"{stem}_{label}.parquet").equals(
                        getattr(result, label)):
                    raise AssertionError(f"Reference trajectory changed: {stem}/{label}")
            invariant[stem] = {"pass": True, "artifact_sha256": sha(folder / f"{stem}.json")}
            progress({"module": "A05_HOLD_REPAIR", "baseline_invariant": stem})
    if any(sha(ROOT / name) != digest for name, digest in source_hashes.items()):
        raise RuntimeError("Source changed while hold acceptance was running")
    report = {"status": "PASS", **previous,
              "hold_repairs": {"pass": True, "cases": repairs},
              "cross_engine_policy": {"pass": True, "cases": cases},
              "default_baseline_invariance": {"pass": True, "cases": invariant},
              "scope": "ENGINEERING_AND_UNCHANGED_DEVELOPMENT_REFERENCE",
              "new_alpha_model_fits": 0, "locked_historical_test_read": False,
              "true_forward_days": 0, "dataset_id": lock["dataset_id"],
              "seconds": time.monotonic() - started, "resources": status(), "disk": check(),
              "source_hashes": source_hashes}
    path.write_text(json.dumps(report, indent=2, ensure_ascii=False, allow_nan=False) + "\n")
    verify_hold_lineage()
    return report


if __name__ == "__main__":
    result = accept_hold_repair(progress=lambda event: print(json.dumps(event), flush=True))
    print(json.dumps({"status": result["status"], "seconds": result["seconds"]}), flush=True)
