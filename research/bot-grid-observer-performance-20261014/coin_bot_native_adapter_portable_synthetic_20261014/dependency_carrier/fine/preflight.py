"""Read-only gate: no historical simulator is constructed here."""
from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path

from freeze_bootstrap import verify as verify_reviewed_freeze

REVIEWED_FREEZE = verify_reviewed_freeze()

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
REPO = ROOT / "coin_native_half_mix_20261013/repo"
POLICY = ROOT / "coin_margin_protective_policy_20261013"
BINDINGS_SHA256 = "68379d5adf916f06695bb64163f9dcf33b593a60167db26a8ec2782456eac9a2"
RUNNER_SHA256 = "b5e8a6ebd54e790066861da5c05d0c193175d965ceb75995779d70b2fe8c27a6"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def bindings() -> dict:
    if verify_reviewed_freeze()["freeze_manifest_SHA256"] != REVIEWED_FREEZE["freeze_manifest_SHA256"]:
        raise ValueError("Reviewed module changed after import")
    path = HERE / "CASE_BINDINGS.json"
    if sha(path) != BINDINGS_SHA256:
        raise ValueError("Frozen case bindings changed")
    document = json.loads(path.read_text())
    if document["case_count"] != 12 or document["modes"] != ["ORIGINAL", "GUARD50"]:
        raise ValueError("Unexpected mode or case count")
    if sha(HERE / "FINE_PROFILE.json") != document["fine_profile_SHA256"]:
        raise ValueError("Fine profile bytes changed")
    if sha(POLICY / "RUN_MANIFEST.json") != document["guard_run_manifest_SHA256"]:
        raise ValueError("Frozen guard manifest bytes changed")
    if sha(ROOT / "new_coin_guard_baseline_identity_20261013/BASELINE_IDENTITY.json") != document["baseline_identity_SHA256"]:
        raise ValueError("Published baseline identity audit changed")
    if sha(ROOT / "coin_margin_protective_runner_20261013/run_guard_cases.py") != RUNNER_SHA256:
        raise ValueError("Bound transport runner changed")
    return document


def check(*, full_source: bool = True) -> dict:
    import numpy as np

    document = bindings()
    expected = {(year, arm) for year in (2023, 2024, 2025)
                for arm in ("STATIC50", "EXACTHALF" if year == 2024 else "COMBINED")}
    if len(document["cases"]) != 6 or {(c["year"], c["arm"]) for c in document["cases"]} != expected:
        raise ValueError("The six fixed year/arm pairs differ")
    guard_manifest = json.loads((POLICY / "RUN_MANIFEST.json").read_text())
    indexed = {c["case_id"]: c for c in guard_manifest["cases"]}
    for case in document["cases"]:
        original = indexed[case["case_id"]]
        for key in ("case_id", "year", "arm", "calendar", "symbols",
                    "source_index_local_locator", "source_index_SHA256",
                    "target_archive_local_locator", "target_archive_SHA256",
                    "target_array_SHA256", "target_dtype", "target_shape"):
            if case[key] != original[key]:
                raise ValueError(f"Frozen target/source binding changed: {case['case_id']}, {key}")
        source = ROOT / case["source_index_local_locator"]
        target = ROOT / case["target_archive_local_locator"]
        if sha(source) != case["source_index_SHA256"] or sha(target) != case["target_archive_SHA256"]:
            raise ValueError(f"Input bytes changed: {case['case_id']}")
        with np.load(target, allow_pickle=False) as archive:
            matrix = archive[case["arm"]]
            if (matrix.dtype.str != case["target_dtype"] or list(matrix.shape) != case["target_shape"]
                    or sha_bytes(matrix.tobytes(order="C")) != case["target_array_SHA256"]
                    or not np.array_equal(archive["decision_us"], np.arange(
                        case["calendar"][0], case["calendar"][1], 86_400_000_000, dtype=np.int64))
                    or tuple(archive["symbol_order"]) != tuple(case["symbols"])):
                raise ValueError(f"Target array changed: {case['case_id']}")
            if case["arm"] in ("EXACTHALF", "COMBINED") and not np.array_equal(
                    matrix, .5 * archive["STATIC50"] + .5 * archive["SMA200_10PCT"]):
                raise ValueError(f"Half-sum target changed: {case['case_id']}")
        for kind in ("result", "binding"):
            coarse = case["coarse_guard"]
            if sha(ROOT / coarse[f"{kind}_local_locator"]) != coarse[f"{kind}_SHA256"]:
                raise ValueError(f"Coarse guard {kind} changed: {case['case_id']}")
        guard_binding = json.loads((ROOT / case["coarse_guard"]["binding_local_locator"]).read_text())
        if (guard_binding["target_array_SHA256"] != case["target_array_SHA256"]
                or guard_binding["source_index_SHA256"] != case["source_index_SHA256"]
                or guard_binding["quantity_profile_SHA256"] != document["coarse_profile_SHA256"]):
            raise ValueError(f"Coarse guard pairing changed: {case['case_id']}")
        prior = case["coarse_original"]
        if not all(prior["published_identity"]["identity_checks"].values()):
            raise ValueError(f"Baseline published identity incomplete: {case['case_id']}")
        if prior["published_identity"]["guard_target_array_SHA256"] != case["target_array_SHA256"]:
            raise ValueError(f"Baseline target differs: {case['case_id']}")
        if prior["local_result_locator"] and sha(ROOT / prior["local_result_locator"]) != prior["local_result_SHA256"]:
            raise ValueError(f"Local coarse original result changed: {case['case_id']}")
    if full_source:
        # Reuse the already published read-only preflight, which checks all
        # source-month, daily/event, and target bytes. It never makes a wallet.
        source = POLICY / "preflight_run_plan.py"
        spec = importlib.util.spec_from_file_location("quantity_source_preflight", source)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        result = module.check(POLICY / "RUN_MANIFEST.json", ROOT)
        if result["wallets_started"] != 0 or set(result["case_ids"]) != set(indexed):
            raise ValueError("Published read-only preflight differs")
    return {"status": "INPUTS_BOUND_NO_FINE_HISTORY_EXECUTED", "year_arm_pairs": 6,
            "planned_fine_wallets": 12, "coarse_wallets_to_rerun": 0,
            "full_source_checked": full_source, "parent_GO_required": True}


def sha_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


if __name__ == "__main__":
    print(json.dumps(check(), indent=2))
