"""Verify frozen sources/tests, then write targets only. Never scores returns."""
from __future__ import annotations

import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import sys
import time
import unittest

# The frozen compute budget is one CPU and single-threaded numerical kernels.
for name in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ[name] = "1"
sys.dont_write_bytecode = True
import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
WORKSPACE = ROOT.parent
sys.path.insert(0, str(ROOT))

def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result

core = module("cs_sma_agreement_core", HERE / "core.py")
EXPECTED_PROTOCOL_SHA256 = "bb37fd619777bd69e043eddfe3ade6c564e00ebe0eef0257181b68d25fe7f47c"
EXPECTED_INPUTS = {
    2023: "1c500e9d5b0244a1daaabc597d7cc5ae97a21a156cc42d8a44a1504b821e599f",
    2025: "88a698ceed87603a36ca2bcf4ae76d805aa90085b344bbeee47e58a8c9770add",
}

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False)+"\n")

def require(ok, message):
    if not bool(ok):
        raise ValueError(message)

def test_names(suite):
    names = []
    for test in suite:
        if isinstance(test, unittest.TestSuite):
            names.extend(test_names(test))
        else:
            names.append(test.id())
    return names

def verified_sources():
    restoration = json.loads((WORKSPACE / "RESTORATION_SOURCE.json").read_text())
    compat = json.loads((WORKSPACE / "CS_COMPAT_QA.json").read_text())
    require(restoration["commit"] == "53357f33f4e6ccb536af762fbff39b269c24d837", "Pinned source restoration identity")
    sources = []
    for entry in restoration["restored_sources"]:
        path = ROOT / entry["repository_path"]
        require(path.is_file() and sha(path) == entry["SHA256"], "Original source hash: "+entry["repository_path"])
        sources.append(dict(entry))
    for relative, expected in compat["sources"].items():
        path = ROOT / relative
        require(path.is_file() and sha(path) == expected, "Compatibility source hash: "+relative)
        sources.append(dict(repository_path=relative, SHA256=expected, bytes=path.stat().st_size,
                            provenance="Verified import-only compatibility or retained canonical original"))
    for name in ("core.py", "test_core.py", "prepare_targets.py", "PROTOCOL.json"):
        path = HERE / name
        sources.append(dict(repository_path=str(path.relative_to(ROOT)), SHA256=sha(path),
                            bytes=path.stat().st_size, provenance="Frozen agreement experiment implementation"))
    return dict(repository=restoration["repository"], original_source_commit=restoration["commit"],
                protocol_commit="78e1d03eb6229bdc345a92225a32c869e534afa5",
                protocol_SHA256=EXPECTED_PROTOCOL_SHA256,
                exact_source_files=sources, input_packet=restoration["packet_index"],
                source_restoration_manifest=restoration,
                compatibility_note="Canonical algorithm bodies unchanged; Polars-only unused import dependency removed in retained compatibility adapter.")

def main():
    start = time.monotonic()
    require(sha(HERE / "PROTOCOL.json") == EXPECTED_PROTOCOL_SHA256, "Frozen protocol identity changed")
    protocol = json.loads((HERE / "PROTOCOL.json").read_text())
    require(tuple(protocol["arms"]) == core.ARMS and tuple(protocol["symbols"]) == core.SYMBOLS,
            "Frozen arm and symbol order")
    require(protocol["years"] == [2023, 2025], "Only two preselected seen development years")
    provenance = verified_sources()
    tests = module("cs_sma_agreement_tests", HERE / "test_core.py")
    suite = unittest.defaultTestLoader.loadTestsFromModule(tests)
    names = test_names(suite)
    log = io.StringIO()
    result = unittest.TextTestRunner(stream=log, verbosity=2).run(suite)
    (HERE / "TEST_RESULTS.txt").write_text(log.getvalue())
    require(result.wasSuccessful(), "Synthetic tests failed; do not generate targets")
    qa = dict(status="PASS_FROZEN_CAUSAL_TARGETS_NO_ECONOMIC_SCORING", tests_run=result.testsRun,
              failures=len(result.failures), errors=len(result.errors), synthetic_tests=names,
              economic_runs_started=False, historical_economic_accounts=0,
              new_financial_GETs=0, new_fits=0, protected_or_reserved_data_accessed=False,
              own_compute_policy="Single process; numerical kernel threads1", years={})
    manifest = dict(status="TARGETS_ONLY_PRE_ECONOMICS", schema_version=1,
                    experiment=protocol["experiment"], arms=list(core.ARMS),
                    symbol_order=list(core.SYMBOLS), protocol_SHA256=EXPECTED_PROTOCOL_SHA256,
                    protocol_commit=provenance["protocol_commit"], economic_runs_started=False,
                    years={}, files={})
    targets_dir = HERE / "targets"
    targets_dir.mkdir(exist_ok=True)
    for year, expected in EXPECTED_INPUTS.items():
        source = WORKSPACE / "inputs" / f"Y{year}.npz"
        require(sha(source) == expected, "Original INPUTS_FINAL member identity")
        with np.load(source, allow_pickle=False) as z:
            arrays = {name: z[name].copy() for name in
                      ("symbol_order", "close_available_us", "close", "decision_us", "p0", "p1", "funding_per_unit", "owned_interval_valid")}
        from datetime import datetime, timezone
        first = int(datetime(year, 1, 1, tzinfo=timezone.utc).timestamp())*1_000_000
        expected_dates = first + np.arange(365, dtype=np.int64)*core.DAY_US
        require(np.array_equal(arrays["decision_us"], expected_dates), "Complete fixed 365 calendar")
        require(tuple(arrays["symbol_order"]) == core.SYMBOLS, "Original CORE5 order")
        require(arrays["owned_interval_valid"].shape == (365, 5) and arrays["owned_interval_valid"].all(),
                "Full actual owned-interval source validity; no eligible-day cherry picking")
        for name in ("p0", "p1", "funding_per_unit"):
            require(arrays[name].shape == (365, 5) and np.isfinite(arrays[name]).all(), "Finite actual owned source "+name)
        require((arrays["p0"] > 0).all() and (arrays["p1"] > 0).all(), "Positive actual execution boundaries")
        require(np.array_equal(arrays["p1"][:-1], arrays["p0"][1:]), "Continuous owned execution boundaries")
        targets = core.build_targets(arrays["close"], arrays["close_available_us"], arrays["decision_us"])
        # A historical-context causal check changes ONLY available rows at/after
        # a future decision. Values and NaN masks both change; prefix must be exact.
        count = 180
        changed = arrays["close"].copy()
        cut = int(np.searchsorted(arrays["close_available_us"], arrays["decision_us"][count]))
        changed[cut:] *= np.array([2., .2, 10., 3., .1])
        changed[cut:, [0, 3]] = np.nan
        after = core.build_targets(changed, arrays["close_available_us"], arrays["decision_us"], strict=False)
        for field in ("targets", "raw"):
            for arm in targets[field]:
                require(np.array_equal(targets[field][arm][:count], after[field][arm][:count]), "Exact historical-context causal target prefix")
        require(targets["proof"][:count] == after["proof"][:count], "Exact historical-context causal proof prefix")
        target_file = targets_dir / f"Y{year}.npz"
        saved = dict(decision_us=arrays["decision_us"], symbol_order=arrays["symbol_order"],
                     annual_covariance=targets["annual_covariance"], source_status=targets["source_status"],
                     sma_eligible=targets["sma_eligible"], sma_mean=targets["sma_mean"],
                     sma_latest_close=targets["sma_latest_close"], agreement_mask=targets["agreement_mask"],
                     cs_current_eligible=targets["cs_current_eligible"])
        saved.update(targets["targets"])
        saved.update({"raw_"+name: value for name, value in targets["raw"].items()})
        np.savez_compressed(target_file, **saved)
        with np.load(target_file, allow_pickle=False) as restored:
            require(set(restored.files) == set(saved), "Cold-read target key equality")
            for name, values in saved.items():
                require(np.array_equal(restored[name], values), "Cold-read target bit equality: "+name)
        proof_file = targets_dir / f"Y{year}_PROOF.json"
        write_json(proof_file, targets["proof"])
        arm_summary = {}
        for arm in core.ARMS:
            w = targets["targets"][arm]
            risk = [row["arms"][arm] for row in targets["proof"]]
            arm_summary[arm] = dict(
                cash_days=int(np.count_nonzero(np.abs(w).sum(1) == 0.)),
                long_asset_days=int(np.count_nonzero(w > 0)), short_asset_days=int(np.count_nonzero(w < 0)),
                estimated_cap_bound_days=sum(row["cap_bound"] is True for row in risk),
                nominal_risk_shortfall_days=sum(row["shortfall"] > 1e-12 for row in risk),
                nominal_risk_target_met_days=sum(row["risk_target_met"] for row in risk),
                above_nominal_estimated_risk_days=sum(row["post_sigma"] > .10+1e-12 for row in risk),
                estimated_annual_risk_min=min(row["post_sigma"] for row in risk),
                estimated_annual_risk_max=max(row["post_sigma"] for row in risk),
                estimated_annual_risk_mean=float(np.mean([row["post_sigma"] for row in risk])),
                estimated_annual_risk_shortfall_mean=float(np.mean([row["shortfall"] for row in risk])),
                max_absolute_weight=float(np.abs(w).max()), max_gross_weight=float(np.abs(w).sum(1).max()))
        qa["years"][str(year)] = dict(input_SHA256=expected, decision_rows=365,
            all_200_completed_closes_finite_positive_contiguous=True,
            original_full_owned_source_asset_intervals=1825,
            canonical_raw_rank_events=len(targets["cs_diagnostics"]["rank_events"]),
            first_rank_us=int(targets["cs_diagnostics"]["rank_us"][0]),
            first_decision_us=int(arrays["decision_us"][0]),
            historical_context_future_value_and_NaN_mask_prefix="BIT_EXACT_180_DAYS",
            target_cold_read="ALL_KEYS_AND_ARRAYS_BIT_EXACT", arms=arm_summary)
        manifest["years"][str(year)] = dict(input_relative_path=f"../inputs/Y{year}.npz", input_SHA256=expected,
            target_relative_path=str(target_file.relative_to(HERE)), target_SHA256=sha(target_file),
            proof_relative_path=str(proof_file.relative_to(HERE)), proof_SHA256=sha(proof_file),
            decision_rows=365, target_shapes={name: list(value.shape) for name, value in saved.items()})
    qa["seconds"] = time.monotonic()-start
    qa["risk_note"] = "Four common-policy scaled arms are at or below nominal10% estimated risk; no-reallocation diagnostic preserves sized-CS survivors and may exceed10% after hedge removal. Realized risk is not calculated here."
    write_json(HERE / "SOURCE_PROVENANCE.json", provenance)
    write_json(HERE / "QA.json", qa)
    for name in ("SOURCE_PROVENANCE.json", "QA.json", "TEST_RESULTS.txt", "core.py", "test_core.py", "prepare_targets.py", "PROTOCOL.json"):
        path = HERE / name
        manifest["files"][name] = dict(SHA256=sha(path), bytes=path.stat().st_size)
    for row in manifest["years"].values():
        for key in ("target_relative_path", "proof_relative_path"):
            path = HERE / row[key]
            manifest["files"][row[key]] = dict(SHA256=sha(path), bytes=path.stat().st_size)
    write_json(HERE / "TARGETS_MANIFEST.json", manifest)
    print(json.dumps(dict(status=qa["status"], tests_run=result.testsRun, seconds=qa["seconds"], years=manifest["years"]), indent=2))

if __name__ == "__main__":
    main()
