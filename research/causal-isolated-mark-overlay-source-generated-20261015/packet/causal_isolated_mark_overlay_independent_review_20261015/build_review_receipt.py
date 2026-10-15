"""Read generated artifacts and metadata only; write this review's receipt."""
import ast
from hashlib import sha256
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
BASE = HERE.parent
SOURCE = BASE / sys.argv[1]


def pin(path):
    b = path.read_bytes()
    return {"path": path.relative_to(BASE).as_posix(), "bytes": len(b), "SHA256": sha256(b).hexdigest()}


def save(name, value):
    (HERE / name).write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n")


def log_result(name):
    return json.loads((HERE / name).read_text().strip().splitlines()[-1])


manifest = json.loads((SOURCE / "DELIVERABLE_PINS.json").read_text())
verified = []
for item in manifest["files"]:
    p = SOURCE / item["path"]
    if not p.resolve().is_relative_to(SOURCE.resolve()):
        raise RuntimeError("Manifest escaped generated package")
    actual = pin(p)
    if (actual["bytes"], actual["SHA256"]) != (item["bytes"], item["SHA256"]):
        raise RuntimeError("Source package pin changed: " + item["path"])
    verified.append(actual)
before = json.loads((HERE / "SOURCE_PACKAGE_BEFORE_TESTS.json").read_text())
after = [{"path": p["path"].removeprefix(SOURCE.name + "/"),
          "bytes": p["bytes"], "SHA256": p["SHA256"]}
         for p in [pin(SOURCE / "DELIVERABLE_PINS.json")] + verified]
if before["reviewed_package"] != SOURCE.name or before["files"] != after:
    raise RuntimeError("Generated source package changed during review tests")
save("SOURCE_PACKAGE_BEFORE_AFTER.json", {"reviewed_package": SOURCE.name,
     "before": before["files"], "after": after, "unchanged": True,
     "scope": "Generated code, fake outputs and metadata package only; no raw-source archive reads."})

policy = json.loads((SOURCE / "policy.json").read_text())
validation = json.loads((SOURCE / "VALIDATION.json").read_text())
protected = json.loads((SOURCE / "PROTECTED_ORIGINALS_BEFORE_AFTER.json").read_text())
if not (protected["before"] == protected["after"] and protected["unchanged"] is True
        and len(protected["before"]) == 14
        and protected["archive_bodies_decompressed"] == protected["historical_price_rows_parsed"] == 0):
    raise RuntimeError("Scoped protected-original metadata receipt invalid")
actual_metadata_paths = (
    "partial2022_aug_nov_source_manifest_20261015/metadata/MARK_Q32022_RECOVERY.json",
    "full2022_source_metadata_plan_20261015/EXACT_JULY_MARK_GAP_ALLOWLIST.json",
    "full2022_source_metadata_plan_20261015/FULL2022_GAP_TAXONOMY.json")
for name in actual_metadata_paths:
    actual = pin(BASE / name)
    expected = next(x for x in protected["before"] if x["path"] == name)
    if actual != expected:
        raise RuntimeError("Original metadata pin mismatch")

static = {}
for name in ("overlay.py", "metadata_binding.py"):
    tree = ast.parse((SOURCE / name).read_text())
    imports = sorted({x.module for x in ast.walk(tree) if isinstance(x, ast.ImportFrom)} |
                     {a.name for x in ast.walk(tree) if isinstance(x, ast.Import) for a in x.names})
    blocked_calls = [x.func.id for x in ast.walk(tree) if isinstance(x, ast.Call)
                     and isinstance(x.func, ast.Name)
                     and x.func.id in {"open", "eval", "exec", "compile", "__import__", "input"}]
    if blocked_calls:
        raise RuntimeError("Unexpected dynamic/file entry point")
    static[name] = {"imports": imports, "dynamic_or_file_builtin_calls": blocked_calls}

independent, author = log_result("INDEPENDENT_TESTS.log"), log_result("AUTHOR_TESTS_RERUN.log")
for result in (independent, author):
    if not result["successful"] or result["failures"] or result["errors"] or any(result["counters"].values()):
        raise RuntimeError("Final generated tests did not pass")
if policy["actual_application_enabled"] or validation["actual_overlay_records_created"] or validation["financial_GO"]:
    raise RuntimeError("Actual application unexpectedly enabled")

save("STATIC_SOURCE_REVIEW.json", static)
save("VERIFIED_SOURCE_PACKAGE_PINS.json", {"schema": "INDEPENDENT_EXACT_GENERATED_PACKAGE_PINS_V1",
     "manifest": pin(SOURCE / "DELIVERABLE_PINS.json"), "files_count": len(verified), "files": verified})
receipt = {
    "schema": "INDEPENDENT_CAUSAL27_GENERATED_SOURCE_REVIEW_V1",
    "status": "PASS_SOURCE_ONLY_GENERATED_NO_ACTUAL_APPLICATION",
    "reviewed_package": SOURCE.name,
    "source_manifest": pin(SOURCE / "DELIVERABLE_PINS.json"),
    "exact_key_pins": [pin(SOURCE / n) for n in ("overlay.py", "metadata_binding.py", "policy.json",
        "fixture_allowlist.json", "evidence/EXACT_JULY_MARK_GAP_ALLOWLIST.json",
        "evidence/ORIGINAL_MARK_Q3_RECOVERY.json", "evidence/FULL2022_GAP_TAXONOMY.json",
        "PROTECTED_ORIGINALS_BEFORE_AFTER.json")],
    "independent_tests": independent, "author_tests_independently_rerun": author,
    "source_manifest_all_pins_match": True,
    "source_package_unchanged_during_review_tests": True,
    "scoped_original_metadata_pins_independently_verified": list(actual_metadata_paths),
    "protected_original_receipt": {"pin": pin(SOURCE / "PROTECTED_ORIGINALS_BEFORE_AFTER.json"),
        "named_files": 14, "before_equals_after": True, "recorded_before_after_pins": protected["before"],
        "independent_raw_archive_rehash": False,
        "scope": "Reviewer verified the pinned metadata receipt and three original metadata files. Raw source archives were neither opened nor rehashed by the reviewer."},
    "findings_resolved": [
        "Rehashed malformed exported records now reject invalid prices, clocks, age, freshness and provenance.",
        "Frozen missing cells cannot be declared genuine or used as anchors outside a requested subset.",
        "Requested OPEN identities require strict integer type; cross-record shared-anchor provenance/value conflicts reject."],
    "causal_contract": {"asset_minutes": 27, "distinct_original_open_clocks": 11,
        "asset_specific_runs": 8, "single_minute_runs": 4, "maximum_missing_run": 7,
        "target_clock": "ORIGINAL_OPEN_PLUS_60000MS_NOMINAL_COMPLETION",
        "anchor": "LATEST_PRIOR_GENUINE_AVAILABLE_AND_INSTALLED_AT_TARGET_CLOCK",
        "output_quality": "UNKNOWN_OR_DERIVED", "primary_price": "EXACT_UNCHANGED_ANCHOR_DECIMAL_TEXT",
        "derived_to_genuine_promotion": False, "source_overwrite": False,
        "native_intent_lifecycle": "UNCHANGED_NOT_IMPLEMENTED_HERE"},
    "limits": {"actual_overlay_application": "NOT_PERFORMED_AND_NOT_AUTHORIZED",
        "actual_price_rows_read_by_reviewer": 0, "actual_source_archive_bodies_opened_by_reviewer": 0,
        "source_admission": "NOT_GRANTED", "financial_GO": False, "publication": False,
        "actual_historical_arrival": "UNKNOWN_CANNOT_BE_CERTIFIED_FROM_NOMINAL_COMPLETION",
        "actual_missingness_and_anchors": "PENDING_GENUINE_RAW_SOURCE_REVALIDATION",
        "actual_positions_fills_funding_guard50_native_risk_terminal_impact": "PENDING_ACTUAL_ANNUAL_SAVED_EVENT_EVIDENCE",
        "actual_quantity_cashflow_sensitivity": "PENDING_ACTUAL_EVIDENCE",
        "last_two_past_prices": "WEAK_DESCRIPTIVE_ANCHORS_ONLY_NOT_FUTURE_BOUNDS_OR_ROBUST_STRESS_GUARANTEES",
        "fewer_than_two_past_genuine_anchors": "PENDING",
        "certifies_liquidation": False, "certifies_no_liquidation": False,
        "ETH_February2022_40320_trade_minutes": "DENIED_HARD_BLOCK_NEVER_IMPUTATION_TARGET"},
    "reproduce": ["taskset -c 6 coin_partial_restore_20261014/.venv/bin/python -B " +
        HERE.name + "/run_independent_tests.py " + SOURCE.name,
        "taskset -c 6 coin_partial_restore_20261014/.venv/bin/python -B " +
        SOURCE.name + "/run_generated_tests.py"],
}
save("INDEPENDENT_REVIEW_RECEIPT.json", receipt)
print(json.dumps({"status": receipt["status"], "independent_tests": independent["tests_run"],
    "author_tests": author["tests_run"], "verified_source_files": len(verified),
    "source_manifest_SHA256": receipt["source_manifest"]["SHA256"]}, sort_keys=True))
