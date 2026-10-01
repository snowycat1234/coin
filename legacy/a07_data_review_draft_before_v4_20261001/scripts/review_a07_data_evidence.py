"""Versioned read-only composition; diagnostic readiness never grants qualification."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import sys
from datetime import UTC, date, datetime
from pathlib import Path
from types import SimpleNamespace

from quant.paths import ROOT, STATE
from quant.resources import status

PROTOCOL = "protocols/a07_data_evidence_review_v2.json"
PROTOCOL_SHA = "ef95cd9bd39f5c808c996aa061a25ee7d9f56ebb1ff8ff7b666b72305789b448"
FUTURE_DAY = date(2026, 10, 1)
SYMBOLS, INTERVALS = ("BTCUSDT", "ETHUSDT"), (1, 5, 30, 60)
QUALITY_SOURCE = "scripts/audit_microstructure_quality.py"
WINDOW_SOURCE = "scripts/audit_a07_resource_window.py"
RAW_SOURCE = "scripts/audit_a07_raw_retention.py"


def require(ok, message):
    if not ok:
        raise ValueError(message)


def integer(value, name, minimum=0, maximum=None):
    require(type(value) is int and value >= minimum
            and (maximum is None or value <= maximum), "Invalid " + name)
    return value


def number(value, name, minimum=0):
    require(type(value) in (int, float) and math.isfinite(value) and value >= minimum,
            "Invalid " + name)
    return value


def digest_bytes(payload):
    return hashlib.sha256(payload).hexdigest()


def local_path(path, *, reports=False):
    path = Path(path).absolute()
    require(not any(part == ".." for part in path.parts), "Parent path escape rejected")
    for part in (path, *path.parents):
        require(not part.is_symlink(), "Symlink path rejected")
    require(path.resolve() == path and path.is_relative_to(ROOT.resolve()), "D ROOT path required")
    if reports:
        require(path.is_relative_to(ROOT / "reports") and path.suffix == ".json",
                "D report JSON required")
    return path


def read(path, maximum=10_000_000):
    path = local_path(path)
    require(path.is_file() and path.stat().st_size <= maximum, "Missing/oversize input")
    with path.open("rb") as reader:
        payload = reader.read(maximum + 1)
    require(len(payload) <= maximum, "Input read bound exceeded")
    return payload


def parse(payload):
    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result, "Duplicate JSON key")
            result[key] = value
        return result

    result = json.loads(payload, object_pairs_hook=pairs)
    json.dumps(result, allow_nan=False)
    return result


def load_verified(name, expected):
    path = local_path(ROOT / name)
    payload = read(path, 4_000_000)
    require(digest_bytes(payload) == expected, "Verified consumer source changed")
    spec = importlib.util.spec_from_file_location("_a07_review_v2_" + path.stem, path)
    require(spec is not None, "Consumer loader missing")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    exec(compile(payload, str(path), "exec"), module.__dict__)
    return module


def verify_sources(expected_protocol):
    payload = read(ROOT / PROTOCOL, 20_000)
    require(digest_bytes(payload) == expected_protocol, "Protocol hash changed")
    protocol = parse(payload)
    require(protocol["protocol"] == "A07_DATA_EVIDENCE_REVIEW_V2", "Different protocol")
    fixed = protocol["data_review_stage"]
    require((fixed["predictive_minimum_consecutive_observed_days"],
             fixed["predictive_minimum_actual_paired_usable_seconds"],
             fixed["preregistration_minimum_consecutive_observed_days"],
             fixed["preregistration_minimum_actual_paired_usable_seconds"])
            == (14, 1_209_600, 30, 2_592_000), "Original data volume gate cannot change")
    hashes = {PROTOCOL: expected_protocol}
    for name, expected in protocol["frozen_acceptances"].items():
        raw = read(ROOT / name, 2_000_000)
        require(digest_bytes(raw) == expected, "Frozen acceptance changed: " + name)
        hashes[name] = expected
        receipt = parse(raw)
        for field in ("source_hashes", "verified_prior_files"):
            mapping = receipt.get(field, {})
            require(len(mapping) <= 100, "Frozen file count bound")
            for source, value in mapping.items():
                require(isinstance(source, str) and not Path(source).is_absolute(),
                        "Frozen source path invalid")
                require(digest_bytes(read(ROOT / source, 4_000_000)) == value,
                        "Frozen source changed: " + source)
                require(source not in hashes or hashes[source] == value, "Conflicting source hash")
                hashes[source] = value
    return protocol, hashes


def day_number(value):
    require(isinstance(value, str) and len(value) == 10, "Invalid UTC day")
    parsed = date.fromisoformat(value)
    require(parsed.isoformat() == value, "Noncanonical UTC day")
    return (parsed - date(1970, 1, 1)).days


def same_source(binding, protocol):
    require(all(binding.get(key) == value for key, value in protocol["accepted_source"].items()),
            "Different live collector binding")


def quality_summary(report, protocol, hashes, coverage):
    require(report["module"] == "A07_QUALITY_DIAGNOSIS" and report["read_only"] is True
            and report["engineering_fixture_hook"] is False and report["integrity"] == "PASS",
            "Actual frozen quality integrity not established")
    require(report["diagnostic_source_sha256"] == hashes[QUALITY_SOURCE], "Quality source changed")
    same_source(report["binding"], protocol)
    require(report["audit"]["timestamp_regressions"] == 0
            and report["snapshot"]["read_transaction_released_before_file_scan"] is True
            and report["snapshot"]["query_only"] is True,
            "Quality source clock/short snapshot not established")
    number(report["snapshot"]["read_transaction_seconds"], "SQL seconds")
    require(report["snapshot"]["read_transaction_seconds"] <= 5, "Long live SQL snapshot")
    expected_streams = {f"{symbol}/{interval}s" for symbol in SYMBOLS for interval in INTERVALS}
    require(set(report["streams"]) == expected_streams, "Eight fixed streams required")
    buckets = {}
    for symbol in SYMBOLS:
        for interval in INTERVALS:
            stream = report["streams"][f"{symbol}/{interval}s"]
            require(not any(stream["nonfinite"].values())
                    and not any(stream["unexpected_missing"].values()), "Feature quality not finite")
            rows = stream["utc_days"]
            require(len(rows) <= 4096, "UTC-day bound exceeded")
            days = {}
            for day, counts in rows.items():
                index = day_number(day)
                observed = integer(counts["rows"], "day rows", maximum=86400 // interval)
                known = integer(counts["known_seconds"], "known seconds", maximum=86400)
                valid = integer(counts["valid_seconds"], "valid seconds", maximum=known)
                integer(counts["quality_valid_rows"], "quality rows", maximum=observed)
                require(known <= observed * interval and counts["bad_feature_rows"] == 0,
                        "Inconsistent observed/feature day")
                days[index] = {**counts, "valid_seconds": valid}
            buckets[symbol, interval] = SimpleNamespace(days=days)
    common = report["common_usable_1s_market_data"]
    require(common["pending_row_limit"] == 2 and len(common["utc_days"]) <= 4096,
            "Paired quality bound changed")
    sums, usable = {}, {}
    keys = {"matched_seconds", "usable_seconds", "invalid_or_no_mid_seconds",
            "audit_uncertain_seconds", "unpaired_seconds"}
    for day, counts in common["utc_days"].items():
        index = day_number(day)
        require(set(counts) <= keys, "Unknown paired counters")
        values = {key: integer(counts.get(key, 0), key, maximum=86400) for key in keys}
        require(values["matched_seconds"] == values["usable_seconds"]
                + values["invalid_or_no_mid_seconds"] + values["audit_uncertain_seconds"],
                "Paired seconds accounting mismatch")
        minimum_rows = min(buckets[symbol, 1].days.get(index, {}).get("rows", 0)
                           for symbol in SYMBOLS)
        minimum_valid = min(buckets[symbol, 1].days.get(index, {}).get("valid_seconds", 0)
                            for symbol in SYMBOLS)
        require(values["matched_seconds"] <= minimum_rows
                and values["usable_seconds"] <= minimum_valid, "Paired volume impossible")
        usable[index] = values["usable_seconds"]
        for key, value in values.items():
            sums[key] = sums.get(key, 0) + value
    require(set(common["totals"]) <= keys
            and all(common["totals"].get(key, 0) == value for key, value in sums.items()),
            "Paired total counters mismatch")
    require(set(common["totals"]) <= sums.keys(), "Unexplained paired totals")
    uncertain = {day_number(day) for day in report["coverage"]["excluded_audit_uncertain_utc_days"]}
    derived = {}
    for field, future in (("coverage", False), ("future_since_2026_10_01_utc", True)):
        result = coverage(buckets, future_only=future, uncertain_days=uncertain,
                          common_valid_by_day=usable)
        original = report[field]
        for key, value in result.items():
            require(original.get(key) == value, "Frozen coverage summary differs: " + key)
        derived[field] = result
    require(report["evidence_stage"] == derived["future_since_2026_10_01_utc"]["evidence_stage"],
            "Future data stage mismatch")
    require(report["actual_24h_capacity_accepted"] == derived["coverage"][
                "actual_24h_capacity_accepted"]
            and report["actual_24h_quality_accepted"] == derived["coverage"][
                "actual_24h_quality_accepted"], "Original diagnostic flags mismatch")
    kinds = report["audit"]["kind_counts"]
    counts = {key: integer(value, "audit kind count") for key, value in kinds.items()}
    require(sum(counts.values()) == report["audit"]["records"]
            == report["snapshot"]["audit_records"], "Full audit aggregate count mismatch")
    return derived, {"classification": "UNCLASSIFIED_DISCONNECT",
                     "total_disconnect_records": counts.get("DISCONNECTED", 0),
                     "complete_audit_kind_counts": counts,
                     "incident_samples_used_for_cause_inference": False,
                     "planned_rotation_records_established": False,
                     "normal_or_abnormal_gap_usable_seconds_added": 0,
                     "reason": protocol["disconnect_cause"]["reason"]}


def capacity_inputs(quality, raw, resource, protocol, hashes):
    reasons = []
    full = quality["coverage"]["fully_observed_common_utc_days"]
    caps = quality["capacity"]
    require(caps["feature_cap_bytes"] == 8_000_000_000 and caps["raw_cap_bytes"] == 4_000_000_000,
            "Different feature/raw caps")
    upper = caps["complete_utc_day_feature_bytes_whole_file_upper_bound"]
    require(set(upper) == set(full), "Full-day feature upper-bound days mismatch")
    for value in upper.values():
        integer(value, "whole-file upper bytes", minimum=1)
    maximum = max(upper.values(), default=None)
    require(maximum == caps["complete_utc_day_peak_feature_bytes_whole_file_upper_bound"],
            "Full-day feature peak mismatch")
    projected = None if maximum is None else (maximum * 180 * 13 + 9) // 10
    if not full:
        reasons.append("COMPLETE_COMMON_UTC_DAY_NOT_AVAILABLE")
    if projected is None:
        reasons.append("COMPLETE_DAY_180D_FEATURE_PROJECTION_NOT_AVAILABLE")
    elif projected > 8_000_000_000:
        reasons.append("COMPLETE_DAY_180D_FEATURE_PROJECTION_EXCEEDS_8GB")
    resource_full = resource["status"] == "SAMPLED_24H_RESOURCE_EVIDENCE_REVIEW_REQUIRED"
    if not resource_full:
        reasons.append("CLOSED_86400S_RESOURCE_WINDOW_NOT_ESTABLISHED")
    if resource.get("raw_sampling_complete") is not True:
        reasons.append("RESOURCE_RAW_SAMPLES_UNKNOWN_OR_NOT_AVAILABLE")
    raw_ready = raw["status"] == "RAW_RETENTION_METADATA_OBSERVATION_COMPLETE"
    if not raw_ready:
        reasons.append("RAW_INVENTORY_NOT_ESTABLISHED")
    require(raw["module"] == "A07_RAW_RETENTION_METADATA_QA" and raw["read_only"] is True
            and raw["helper_sha256"] == hashes[RAW_SOURCE], "Raw diagnostic source changed")
    for name, expected in raw["source_hashes"].items():
        require(hashes.get(name) == expected, "Raw source receipt binding changed")
    inventory, snapshot = raw.get("inventory"), raw.get("source_snapshot")
    if snapshot is None or inventory is None:
        reasons.append("RAW_SOURCE_OR_METADATA_MISSING")
    else:
        require(snapshot["binding"] == quality["binding"], "Cross-source raw/quality binding")
        require(snapshot["sql_released_before_inventory"] is True, "Raw reader not released")
        if inventory["status"] != "COMPLETE_NONATOMIC_METADATA_SCAN":
            reasons.append("RAW_SCAN_INCOMPLETE_UNKNOWN")
        else:
            integer(inventory["sampled_bytes"], "raw sampled bytes")
            if inventory["age_envelope_observation"] != (
                "WITHIN_24H_NAMED_START_ENVELOPE_OBSERVED"
            ):
                reasons.append("RAW_AGE_ENVELOPE_NOT_WITHIN_24H")
            if inventory["raw_byte_cap_observation"] != "WITHIN_4GB_SAMPLED_METADATA":
                reasons.append("RAW_BYTES_NOT_WITHIN_4GB")
            if inventory["sampled_bytes"] > 4_000_000_000:
                reasons.append("RAW_BYTES_EXCEED_4GB")
            if inventory["oldest_named_start_age_seconds_at_scan_end"] is not None:
                number(inventory["oldest_named_start_age_seconds_at_scan_end"], "raw oldest age")
                if inventory["oldest_named_start_age_seconds_at_scan_end"] > 86400:
                    reasons.append("RAW_NAMED_START_OLDER_THAN_24H_OBSERVED")
            else:
                reasons.append("RAW_RETENTION_COVERAGE_EMPTY_OR_UNKNOWN")
        if snapshot["checkpoint_fresh_at_snapshot"] is not True:
            reasons.append("RAW_CHECKPOINT_NOT_FRESH")
        pruned = snapshot["raw_pruned_lifetime_summary"]
        oldest = pruned["oldest_named_received_us"]
        ending = datetime.fromisoformat(inventory["scan_finished_utc"])
        require(ending.tzinfo is not None, "Raw inventory end must carry timezone")
        retired = (integer(pruned["records"], "pruning records") > 0
                   and integer(pruned["files"], "pruned files") > 0 and oldest is not None
                   and integer(oldest, "retired named time") < int(ending.timestamp() * 1e6)
                   - 86_400_000_000)
        if not retired:
            reasons.append("ACTUAL_OLDER_THAN_24H_RAW_RETIREMENT_WITNESS_NOT_AVAILABLE")
        if resource_full:
            require(snapshot["checkpoint"]["session"] == resource["terminal_session"],
                    "Raw post-window session changed")
            require(snapshot["binding"] == resource["terminal_binding"],
                    "Raw post-window binding changed")
            if snapshot["checkpoint"]["asof_us"] < resource["terminal_asof_us"]:
                reasons.append("RAW_DIAGNOSTIC_PRECEDES_RESOURCE_ENDPOINT")
    guards = raw.get("resource_guards", {})
    for name in ("aggregate_ram", "whole_project_and_vhd"):
        if guards.get(name, {}).get("status") != "OBSERVED":
            reasons.append("RAW_DIAGNOSTIC_RESOURCE_GUARD_NOT_ESTABLISHED_" + name.upper())
    if guards.get("whole_project_and_vhd", {}).get("status") == "OBSERVED":
        ledger = guards["whole_project_and_vhd"]["value"]
        require(ledger["project_bytes"] + ledger["wsl_vhd_bytes"] == ledger["total_bytes"],
                "Whole project/VHD ledger arithmetic mismatch")
        if ledger["total_bytes"] + ledger["reserved_bytes"] >= 36_000_000_000:
            reasons.append("WHOLE_PROJECT_VHD_AT_OR_OVER_INTAKE_STOP")
        if ledger["d_free_bytes"] < 4_000_000_000 + ledger["reserved_bytes"]:
            reasons.append("D_FREE_EMERGENCY_BUFFER_NOT_ESTABLISHED")
    return {"status": "PENDING_PRIMARY_REVIEW" if reasons else
            "FINITE_CAPACITY_EVIDENCE_COMPLETE_PRIMARY_REVIEW_REQUIRED",
            "pending_reasons": list(dict.fromkeys(reasons)),
            "complete_common_utc_day_whole_file_peak_bytes": maximum,
            "finite_180d_feature_projection_with_30pct_margin_bytes": projected,
            "projection_is_guarantee": False, "feature_budget_bytes": 8_000_000_000,
            "resource_window_status": resource["status"],
            "resource_sampled_peaks": resource.get("sampled_peaks"),
            "native_initial_bytes": resource.get("native_initial_bytes"),
            "native_final_bytes": resource.get("native_final_bytes"),
            "native_observed_endpoint_growth_bytes": resource.get("native_endpoint_growth_bytes"),
            "whole_project_vhd_initial_ledger": resource.get("initial_disk"),
            "whole_project_vhd_final_ledger": resource.get("final_disk"),
            "native_auxiliary_180d_growth_certified": False,
            "native_added_to_vhd_again": False, "primary_review_required": True}


def review_evidence(quality_path, resource_path, raw_path, *, expected_protocol_sha=None,
                    fixture_coverage=None, fixture_window_audit=None):
    """Native fixture hooks are paired; CLI never supplies them or grants eligibility."""
    fixture = any(item is not None for item in
                  (expected_protocol_sha, fixture_coverage, fixture_window_audit))
    require(not fixture or (ROOT.resolve().is_relative_to(STATE.resolve())
                            and expected_protocol_sha is not None and callable(fixture_coverage)
                            and callable(fixture_window_audit)), "Paired STATE fixture hooks required")
    result = {"module": "A07_DATA_EVIDENCE_REVIEW_V2", "read_only": True,
              "created_utc": datetime.now(UTC).isoformat(), "status": "FAIL_CLOSED",
              "engineering_fixture_hook": fixture, "actual_24h_capacity_accepted": False,
              "actual_24h_quality_accepted": False, "actual_14d_accepted": False,
              "actual_30d_accepted": False, "alpha_eligible": False, "training_authorized": False,
              "predictive_diagnostics_data_review_eligible": False,
              "preregistered_research_data_review_eligible": False,
              "healthy_credit_seconds": 0, "network_requests": 0,
              "collector_writes": 0, "collector_restarts": 0,
              "report_stage": "QA_ONLY", "inputs": {}}
    try:
        expected = PROTOCOL_SHA if expected_protocol_sha is None else expected_protocol_sha
        protocol, hashes = verify_sources(expected)
        result["protocol_sha256"], result["verified_frozen_sources"] = expected, hashes
        paths = {"quality": local_path(quality_path, reports=True),
                 "resource_review": local_path(resource_path, reports=True),
                 "raw": local_path(raw_path, reports=True)}
        payloads = {name: read(path) for name, path in paths.items()}
        reports = {name: parse(value) for name, value in payloads.items()}
        result["inputs"] = {name: {"path": str(paths[name].relative_to(ROOT)),
                                   "sha256": digest_bytes(value), "bytes": len(value)}
                            for name, value in payloads.items()}
        qa, raw, resource_input = reports["quality"], reports["raw"], reports["resource_review"]
        coverage = fixture_coverage if fixture else load_verified(
            QUALITY_SOURCE, hashes[QUALITY_SOURCE]).coverage
        derived, disconnect = quality_summary(qa, protocol, hashes, coverage)
        auditor = fixture_window_audit if fixture else load_verified(
            WINDOW_SOURCE, hashes[WINDOW_SOURCE]).audit_window
        resource = auditor(resource_input["directory"])
        for key, value in resource.items():
            if key != "created_utc":
                require(resource_input.get(key) == value, "Resource review differs: " + key)
        require(resource["status"] != "FAIL_CLOSED", "Resource evidence integrity rejected")
        if resource["status"] == "SAMPLED_24H_RESOURCE_EVIDENCE_REVIEW_REQUIRED":
            terminal = parse(read(ROOT / resource["terminal_report"]["path"], 2_000_000))
            require(digest_bytes(read(ROOT / resource["terminal_report"]["path"], 2_000_000))
                    == resource["terminal_report"]["sha256"], "Resource terminal hash changed")
            first, last = terminal["first"], terminal["last"]
            resource = {**resource, "terminal_session": last["checkpoint"]["session"],
                        "terminal_binding": last["binding"],
                        "terminal_asof_us": last["checkpoint"]["asof_us"],
                        "native_initial_bytes": sum(first["native_files_sampled_bytes"].values()),
                        "native_final_bytes": sum(last["native_files_sampled_bytes"].values())}
            resource["native_endpoint_growth_bytes"] = (resource["native_final_bytes"]
                                                        - resource["native_initial_bytes"])
        capacity = capacity_inputs(qa, raw, resource, protocol, hashes)
        complete = bool(derived["coverage"]["fully_observed_common_utc_days"])
        future = derived["future_since_2026_10_01_utc"]
        result.update(status="DATA_EVIDENCE_DIAGNOSTIC_REVIEW_ONLY",
                      calendar_quality_report={"status":
                          "COMPLETE_COMMON_UTC_DAY_DIAGNOSTIC_REPORT_ONLY" if complete else
                          "PENDING_COMPLETE_COMMON_UTC_DAY", "full_coverage": derived["coverage"],
                          "strict_clean_days_unchanged": derived["coverage"][
                              "fully_quality_valid_common_utc_days"],
                          "original_quality_status_unchanged": qa["status"],
                          "whole_day_healthy_certified": False},
                      capacity_evidence=capacity, disconnects=disconnect,
                      data_review_stage={"frozen_data_stage_observed": future["evidence_stage"],
                          "future_coverage_unchanged": future,
                          "predictive_minimum_actual_paired_usable_seconds": 1_209_600,
                          "preregistration_minimum_actual_paired_usable_seconds": 2_592_000,
                          "data_review_is_training_authorization": False,
                          "primary_stage_review_required": True},
                      report_stage="QA_ONLY" if fixture else future["evidence_stage"],
                      limitations="Summary arithmetic and source bindings are local integrity "
                      "evidence, not signatures or independent content re-audit of quality/raw. "
                      "Frozen resource audit is rerun on terminal artifacts. Cause classification "
                      "does not use truncated incident samples; no bad seconds restored. "
                      "Complete diagnostic reports and finite evidence readiness require primary "
                      "review, never automatic 24h acceptance, fitting, alpha or health credit.")
        require(verify_sources(expected) == (protocol, hashes), "Source changed during review")
        for name, path in paths.items():
            require(read(path) == payloads[name], "Input changed during review")
    except (OSError, ValueError, KeyError, TypeError, AttributeError, OverflowError, RecursionError) as e:
        result.update(status="FAIL_CLOSED", reason=str(e), report_stage="QA_ONLY")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("quality", "resource-review", "raw", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    output = local_path(args.output, reports=True)
    require(not output.exists() and output.parent.is_dir(), "New exclusive report required")
    result = review_evidence(args.quality, args.resource_review, args.raw)
    result["runtime_resources"] = status()
    payload = json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
    require(len(payload.encode()) <= 2_000_000, "Review output byte bound exceeded")
    with output.open("x", encoding="utf-8") as writer:
        writer.write(payload)
    print(json.dumps({key: result[key] for key in
                      ("status", "report_stage", "actual_24h_capacity_accepted", "alpha_eligible")}))
    if result["status"] == "FAIL_CLOSED":
        raise SystemExit(2)


if __name__ == "__main__":
    main()
