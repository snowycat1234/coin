"""Offline hash-only protection, metadata binding, and isolated generated tests.

This wrapper opens no market archive and parses no historical price row. Hashing
protected bytes is deliberately outside the generated runtime I/O counters.
"""
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import subprocess
import sys

from metadata_binding import validate_actual27_metadata_bytes
from overlay import (FIXTURE_HOLES, FIXTURE_ALLOWLIST_SHA256, POLICY_SHA256,
                     build_generated_overlay, build_generated_past_only_sensitivity)
from test_overlay import all_anchors, B, M

HERE = Path(__file__).resolve().parent
BASE = HERE.parent
# These are explicit existing frozen originals/code. They are never imported or
# decompressed. This check does not claim to hash every file in the workspace.
PROTECTED = (
    "partial2022_aug_nov_source_manifest_20261015/metadata/MARK_Q32022_RECOVERY.json",
    "full2022_source_metadata_plan_20261015/EXACT_JULY_MARK_GAP_ALLOWLIST.json",
    "full2022_source_metadata_plan_20261015/FULL2022_GAP_TAXONOMY.json",
    "native_2021_source_restore_20261015/source/Y2021.zip",
    "native_2023_source_restore_20261015/source-phases/Q2/archive-020/original.zip",
    "native_2024_source_restore_20261015/wrappers/H1.zip",
    "bounded_native_continuation_guard50_exit_expansion_20261015/expansion_entry.py",
    "bounded_native_continuation_guard50_exit_expansion_20261015/expansion.py",
    "bounded_native_continuation_guard50_exit_expansion_20261015/run_expansion.py",
) + tuple("full2022_source_metadata_plan_20261015/december_mark_restore/raw/" + s + "-1m-2022-12.zip"
          for s in ("BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT", "DOGEUSDT"))


def pin(path):
    digest = hashlib.sha256()
    with path.open("rb") as f:
        while chunk := f.read(1024 * 1024):
            digest.update(chunk)
    return {"path": path.relative_to(BASE).as_posix(), "bytes": path.stat().st_size,
            "SHA256": digest.hexdigest()}


def save(name, value):
    (HERE / name).write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n")


def main():
    before = [pin(BASE / p) for p in PROTECTED]
    blobs = [(HERE / "evidence" / n).read_bytes() for n in (
        "ORIGINAL_MARK_Q3_RECOVERY.json", "EXACT_JULY_MARK_GAP_ALLOWLIST.json", "FULL2022_GAP_TAXONOMY.json")]
    binding = validate_actual27_metadata_bytes(*blobs)
    save("ACTUAL_METADATA_BINDING_VALIDATION.json", asdict(binding))
    policy_bytes=(HERE / "policy.json").read_bytes()
    if hashlib.sha256(policy_bytes).hexdigest() != POLICY_SHA256:
        raise RuntimeError("Exact fixed policy hash mismatch")
    fixture={"schema":"EXACT_GENERATED_FIXTURE_ALLOWLIST_V1", "scope":"GENERATED_ONLY_DISJOINT_FROM_ACTUAL27",
             "canonical_holes_SHA256":FIXTURE_ALLOWLIST_SHA256, "holes":[asdict(h) for h in FIXTURE_HOLES]}
    save("fixture_allowlist.json",fixture)
    completed = subprocess.run([sys.executable, "-B", "run_generated_tests.py"], cwd=HERE,
                               capture_output=True, text=True, check=False)
    (HERE / "GENERATED_TESTS.log").write_text(completed.stdout + completed.stderr)
    if completed.returncode != 0:
        raise RuntimeError("Generated tests failed; inspect local generated test log")
    result = json.loads(completed.stdout.strip().splitlines()[-1])
    obs = all_anchors()
    example = build_generated_overlay(obs, FIXTURE_HOLES, as_of_ms=B + 1100*M)
    save("GENERATED_EXAMPLE_OVERLAY.json", {"scope":"GENERATED_EXAMPLE_ONLY_NO_HISTORICAL_VALUES",
         "overlay":asdict(example), "past_only_sensitivity":[asdict(x) for x in build_generated_past_only_sensitivity(example, obs)]})
    after = [pin(BASE / p) for p in PROTECTED]
    save("PROTECTED_ORIGINALS_BEFORE_AFTER.json", {
        "schema":"SCOPED_FROZEN_ORIGINAL_BYTE_HASH_CHECK_V1", "before":before, "after":after,
        "unchanged":before == after, "archive_bodies_decompressed":0,
        "historical_price_rows_parsed":0, "scope":"Only the explicit14 existing files listed; not a claim to scan the entire workspace"})
    if before != after:
        raise RuntimeError("Protected original hash changed")
    save("VALIDATION.json", {"schema":"SOURCE_ONLY_CAUSAL27_GENERATED_VALIDATION_V1", "status":"PASS_GENERATED_ONLY_PENDING_INDEPENDENT_REVIEW",
         "generated_tests":result, "policy_SHA256":POLICY_SHA256,
         "actual_metadata_binding":asdict(binding), "protected_original_count":len(PROTECTED),
         "protected_originals_unchanged":True,"actual_overlay_records_created":0,
         "source_admission":"NOT_GRANTED", "financial_GO":False,"publication":False,
         "actual_impact_sensitivity":"PENDING_SOURCE_AND_SAVED_EVENT_EVIDENCE",
         "software_installs":0, "new_dependencies":0})
    save("DEPENDENCY_PINS.json", {"schema":"STDLIB_ONLY_OVERLAY_DEPENDENCIES_V1", "Python":sys.version,
         "interpreter":"coin_partial_restore_20261014/.venv/bin/python -B", "third_party_imports":[],
         "financial_modules_imported":False, "source_adapters_imported":False,
         "execution_affinity":"CPU0; no CPU6/CPU7 work", "external_network":False})
    print(json.dumps({"status":"PASS_GENERATED_ONLY", "tests":result['tests_run'],
                      "protected_originals_unchanged":True, "actual_overlay_records_created":0},sort_keys=True))


if __name__ == "__main__":
    main()
