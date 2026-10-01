"""Append an independently checked alpha hold policy to the immutable A01 evidence."""

from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path

import polars as pl

from .backtest import BacktestConfig, baseline_targets, run_backtest
from .execution_contract import ExecutionContractV2
from .execution_parity import cross_engine_parity
from .operations import date_us
from .paths import ROOT

EXTENSION = "reports/A05_POLICY_EXECUTION_ACCEPTANCE.json"
SOURCE_NAMES = ("backtest.py", "shadow_v2.py", "execution_parity.py", "decision_policy.py",
                "execution_contract.py", "shadow.py", "concurrent_budget.py",
                "policy_acceptance.py", "operations.py", "metrics.py")
ARCHIVED = {"backtest.py", "shadow_v2.py", "execution_parity.py"}


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_execution_lineage(root: Path = ROOT) -> dict:
    """Require the original contract plus either exact original source or a valid extension."""
    path = root / "reports/A01_EXECUTION_PARITY_ACCEPTANCE.json"
    original = json.loads(path.read_text())
    contract = ExecutionContractV2()
    if (original.get("status") != "PASS"
            or original.get("execution_contract_sha256") != contract.digest()
            or not original.get("cross_engine_parity", {}).get("pass")):
        raise RuntimeError("A01 contract/parity admission failed")
    canonical = original["canonical_baselines"]
    if canonical.get("status") != "PASS":
        raise RuntimeError("Canonical baseline admission failed")
    artifact = (root / canonical["path"] / "summary.json").resolve()
    if (not artifact.is_relative_to(root.resolve())
            or _sha(artifact) != canonical["artifact_sha256"]):
        raise RuntimeError("Canonical baseline artifact changed")
    changed = []
    for relative, digest in original["source_hashes"].items():
        file = (root / relative).resolve()
        if not file.is_relative_to((root / "src/quant").resolve()):
            raise RuntimeError("Invalid A01 source path")
        if _sha(file) != digest:
            if file.name not in ARCHIVED:
                raise RuntimeError(f"Unaccepted execution dependency changed: {relative}")
            archive = root / "legacy/a01_execution_v2" / file.name
            if _sha(archive) != digest:
                raise RuntimeError(f"Original A01 source archive changed: {relative}")
            changed.append(relative)
    if not changed:
        return {"status": "PASS", "basis": "original_A01", "A01_sha256": _sha(path)}
    extension_path = root / EXTENSION
    if not extension_path.exists():
        raise RuntimeError("Modified executor requires the A05 policy acceptance extension")
    extension = json.loads(extension_path.read_text())
    if (extension.get("status") != "PASS" or extension.get("A01_sha256") != _sha(path)
            or extension.get("execution_contract_sha256") != contract.digest()
            or not extension.get("default_baseline_invariance", {}).get("pass")
            or not extension.get("cross_engine_policy", {}).get("pass")):
        raise RuntimeError("Policy acceptance chain failed")
    expected = {"src/quant/" + name for name in SOURCE_NAMES}
    if set(extension.get("source_hashes", {})) != expected:
        raise RuntimeError("Policy acceptance source set incomplete")
    for relative, digest in extension["source_hashes"].items():
        if _sha(root / relative) != digest:
            raise RuntimeError(f"Accepted executor changed again: {relative}")
    return {"status": "PASS", "basis": "A01_plus_policy_extension",
            "A01_sha256": _sha(path), "extension_sha256": _sha(extension_path),
            "source_hashes": extension["source_hashes"]}


def accept_policy_extension(progress=lambda event: None) -> dict:
    """Check both holding cases and all nine *unchanged* real reference artifacts."""
    from .data import verify_dataset_lock
    from .disk import check
    from .resources import status

    path = ROOT / EXTENSION
    if path.exists():
        raise RuntimeError("Policy receipt already exists; original acceptance is immutable")
    started = time.monotonic()
    check(reserve=300_000_000)
    original_path = ROOT / "reports/A01_EXECUTION_PARITY_ACCEPTANCE.json"
    original = json.loads(original_path.read_text())
    for relative, digest in original["source_hashes"].items():
        source = ROOT / relative
        if _sha(source) != digest:
            if source.name not in ARCHIVED or _sha(
                    ROOT / "legacy/a01_execution_v2" / source.name) != digest:
                raise RuntimeError(f"Original A01 proof missing: {relative}")
    cases = [cross_engine_parity(), cross_engine_parity(partial=True),
             cross_engine_parity(fee_multiplier=2), cross_engine_parity(slippage_multiplier=2),
             cross_engine_parity(minimum_hold_minutes=120),
             cross_engine_parity(minimum_hold_minutes=120, force_exit=True)]
    lock = verify_dataset_lock()
    end = date_us("2026-03-01")
    files = [ROOT / relative for relative in lock["minute_files"]
             if Path(relative).stem < "2026-03"]
    minutes = (pl.scan_parquet(files).filter(pl.col("valid_day") & (pl.col("open_us") < end))
               .select("symbol", "open_us", "open", "close", "quote_volume")
               .collect(engine="streaming"))
    bars = (pl.scan_parquet([ROOT / relative for relative in lock["bar_files"]
                            if Path(relative).name == "1h.parquet"])
            .filter(pl.col("available_us") < end).collect(engine="streaming"))
    folder = ROOT / original["canonical_baselines"]["path"]
    invariant = {}
    for name in ("B0", "B1", "B2"):
        targets = baseline_targets(bars, name)
        for scenario in ("base", "fee_x2", "slippage_x2"):
            stem = f"{name}_{scenario}"
            prior = json.loads((folder / f"{stem}.json").read_text())
            result = run_backtest(bars, minutes, targets, BacktestConfig(**prior["config"]))
            if result.summary != prior["summary"]:
                raise AssertionError(f"Default baseline metrics changed: {stem}")
            for label in ("daily_nav", "trades", "orders", "round_trips"):
                old = pl.read_parquet(folder / f"{stem}_{label}.parquet")
                # IPC serialization can differ in Arrow metadata after a Parquet
                # round trip. Compare schema and every value, without tolerances.
                if not old.equals(getattr(result, label)):
                    raise AssertionError(f"Default baseline trajectory changed: {stem}/{label}")
            invariant[stem] = {"pass": True, "artifact_sha256": _sha(folder / f"{stem}.json")}
            progress({"module": "A05_POLICY", "baseline_invariant": stem})
    report = {"status": "PASS", "A01_sha256": _sha(original_path),
              "execution_contract_sha256": ExecutionContractV2().digest(),
              "cross_engine_policy": {"pass": True, "cases": cases},
              "default_baseline_invariance": {"pass": True, "cases": invariant},
              "evidence_scope": "ENGINEERING_PLUS_DEVELOPMENT_REFERENCE_REGRESSION",
              "new_alpha_model_fits": 0, "locked_historical_test_read": False,
              "true_forward_days": 0, "seconds": time.monotonic() - started,
              "resources": status(), "disk": check(),
              "source_hashes": {"src/quant/" + name: _sha(ROOT / "src/quant" / name)
                                for name in SOURCE_NAMES}}
    path.write_text(json.dumps(report, indent=2, ensure_ascii=False, allow_nan=False) + "\n")
    verify_execution_lineage()
    return report
