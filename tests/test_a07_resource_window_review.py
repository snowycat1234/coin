"""Native STATE fixtures exercise structural rejection without granting real data credit."""

import copy
import importlib.util
import json
import sys
import tempfile
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from quant.paths import ROOT, STATE

SPEC = importlib.util.spec_from_file_location(
    "isolated_a07_window_review_tests", ROOT / "scripts/audit_a07_resource_window.py"
)
review = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = review
SPEC.loader.exec_module(review)


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, allow_nan=False), encoding="utf-8")


@pytest.fixture
def fixture(monkeypatch):
    with tempfile.TemporaryDirectory(prefix="a07-window-review-", dir=STATE) as directory:
        root = Path(directory)
        monkeypatch.setattr(review, "ROOT", root)  # Only this isolated module; never quant.paths.
        sources = {}
        for name in review.BOUND_FILES:
            path = root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("EXPLICIT SYNTHETIC ENGINEERING FIXTURE " + name)
            sources[name] = review.sha(path.read_bytes())
        for name in ("reports/fixture_report.json", "reports/fixture_tests.xml"):
            path = root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("EXPLICIT SYNTHETIC ENGINEERING ACCEPTANCE FIXTURE")
        acceptance = {
            "status": "A07_RESOURCE_OBSERVER_SHORT_ENGINEERING_PASS",
            "source_hashes": sources,
            "verified_prior_files": {},
            "actual_report": {
                "path": "reports/fixture_report.json",
                "sha256": review.sha((root / "reports/fixture_report.json").read_bytes()),
            },
            "tests": {
                "path": "reports/fixture_tests.xml",
                "sha256": review.sha((root / "reports/fixture_tests.xml").read_bytes()),
            },
        }
        write_json(root / review.ACCEPTANCE, acceptance)
        accepted_sha = review.sha((root / review.ACCEPTANCE).read_bytes())
        folder = root / "reports/generated/window"
        folder.mkdir(parents=True)
        yield {"root": root, "folder": folder, "sources": sources, "acceptance_sha": accepted_sha}


def rows(fixture, span=60):
    stamp = datetime(2026, 10, 1, tzinfo=UTC)
    result = []
    for seq, elapsed in enumerate((0, span / 2, span)):
        utc = (stamp + timedelta(seconds=elapsed)).isoformat()
        result.append(
            {
                "sampled_utc": utc,
                "process": {
                    "pid": 500,
                    "start_ticks": 100,
                    "cpu_ticks": 100 + seq * 20,
                    "sampled_monotonic_seconds": 1000 + elapsed,
                    "rss_bytes": 1000 + seq,
                    "lifetime_rss_hwm_bytes": 2000 + seq,
                },
                "checkpoint": {
                    "asof_us": int((stamp + timedelta(seconds=elapsed)).timestamp() * 1e6),
                    "session": "EXPLICIT_SYNTHETIC_SESSION",
                    "connected": True,
                    "accepted_events": 100 + seq,
                    "duplicate_events": 0,
                    "rejected_events": 0,
                    "observed_monotonic_seconds": elapsed,
                },
                "binding": {
                    "mode": "live",
                    "version": "microstructure_l1_v1",
                    "store": str(fixture["root"] / "data/microstructure_v1"),
                    "compression": {"codec": "EXPLICIT_SYNTHETIC"},
                    "implementation_sha256": fixture["sources"]["src/quant/microstructure.py"],
                },
                "manifest_files": 3 + seq,
                "feature_bytes": 1000 + seq * 30,
                "feature_rows": 100 + seq,
                "audit_head_seq": 3 + seq,
                "audit_head_sha256": str(seq) * 64,
                "sql_read_seconds": 0.01,
                "sql_released_before_inventory": True,
                "native_files_sampled_bytes": {
                    "microstructure.sqlite3": 2000 + seq,
                    "microstructure.sqlite3-wal": 20,
                },
                "raw_inventory": {
                    "status": "AVAILABLE_SAMPLED_INVENTORY",
                    "sampled_bytes": 400 + seq,
                    "entries_seen": 3,
                    "scan_seconds": 0.01,
                    "legitimate_concurrent_retirement_or_missing_entries": 0,
                    "atomic_snapshot": False,
                    "exact_unsampled_peak_known": False,
                },
                "global_vhd_sampled_bytes": 6_000_000_000,
                "aggregate_ram": {
                    "ram_limit_bytes": 4_999_999_488,
                    "ram_current_bytes": 3000 + seq,
                    "ram_peak_bytes": 100000,
                    "swap_bytes": 0,
                    "gpu_used": False,
                    "aggregate_cgroup": "/fixture/coin-quant.slice",
                    "memory_events": "low 0\nhigh 0\nmax 0\noom 0\noom_kill 0\noom_group_kill 0",
                },
                "elapsed_monotonic_seconds": elapsed,
            }
        )
    return result


def save_window(fixture, samples, *, terminal=review.SHORT, span=60):
    records, lines, head, peaks = [], [], "0" * 64, {}
    for seq, row in enumerate(samples, 1):
        base = {"seq": seq, "previous_sha256": head, "sample": row}
        head = review.sha(review.canonical(base))
        record = {**base, "sha256": head}
        records.append(record)
        lines.append(review.canonical(record) + b"\n")
        values = {
            "raw_sampled_bytes": row["raw_inventory"]["sampled_bytes"],
            "native_sampled_bytes": sum(row["native_files_sampled_bytes"].values()),
            "vhd_sampled_bytes": row["global_vhd_sampled_bytes"],
            "collector_rss_sampled_bytes": row["process"]["rss_bytes"],
            "collector_lifetime_rss_hwm_bytes": row["process"]["lifetime_rss_hwm_bytes"],
            "aggregate_ram_sampled_bytes": row["aggregate_ram"]["ram_current_bytes"],
        }
        for key, value in values.items():
            if value is not None:
                peaks[key] = max(peaks.get(key, 0), value)
    first, last = (samples[0], samples[-1]) if samples else (None, None)
    disk = {
        "project_bytes": 2_000_000_000,
        "wsl_vhd_bytes": 6_000_000_000,
        "total_bytes": 8_000_000_000,
        "reserved_bytes": 0,
        "d_free_bytes": 30_000_000_000,
        "hard_limit_bytes": 40_000_000_000,
        "status": "OK",
    }
    unknown = sum(row["raw_inventory"]["sampled_bytes"] is None for row in samples)
    report = {
        "status": terminal,
        "failure": "EXPLICIT SYNTHETIC FAILURE" if terminal == review.FAILED else None,
        "source_hashes": fixture["sources"],
        "created_utc": "2026-10-03T00:00:00+00:00",
        "first": first,
        "last": last,
        "samples": len(samples),
        "samples_sha256": review.sha(b"".join(lines)),
        "head_sha256": head,
        "sampled_peaks": peaks,
        "raw_samples_unavailable": unknown,
        "raw_sampling_complete": bool(samples) and unknown == 0,
        "maximum_sample_gap_seconds": max(
            (
                after["elapsed_monotonic_seconds"] - before["elapsed_monotonic_seconds"]
                for before, after in zip(samples, samples[1:], strict=False)
            ),
            default=0,
        ),
        "requested_seconds": span,
        "period_seconds": min(300, span / 2),
        "clock_ticks_per_second": 100,
        "initial_disk": copy.deepcopy(disk),
        "final_disk": copy.deepcopy(disk),
        "quality_accepted": False,
        "actual_24h_capacity_accepted": False,
        "alpha_eligible": False,
        "training_authorized": False,
        "network_requests": 0,
        "collector_writes": 0,
        "collector_restarts": 0,
    }
    if samples:
        report.update(
            measured_elapsed_seconds=last["elapsed_monotonic_seconds"]
            - first["elapsed_monotonic_seconds"],
            collector_cpu_seconds_in_observed_span=(
                last["process"]["cpu_ticks"] - first["process"]["cpu_ticks"]
            )
            / 100,
            committed_feature_growth_bytes=last["feature_bytes"] - first["feature_bytes"],
        )
    (fixture["folder"] / "samples.jsonl").write_bytes(b"".join(lines))
    write_json(fixture["folder"] / "REPORT.json", report)
    return report, records


def audit(fixture, **kwargs):
    before = {str(path): path.read_bytes() for path in fixture["root"].rglob("*") if path.is_file()}
    result = review.audit_window(
        fixture["folder"], expected_acceptance_sha=fixture["acceptance_sha"], **kwargs
    )
    after = {str(path): path.read_bytes() for path in fixture["root"].rglob("*") if path.is_file()}
    assert before == after  # Verifier cannot write any of its inputs.
    assert not any(
        result[key]
        for key in (
            "actual_24h_capacity_accepted",
            "actual_24h_quality_accepted",
            "alpha_eligible",
            "training_authorized",
        )
    )
    assert result["healthy_credit_seconds"] == 0 and not result["exact_unsampled_peak_known"]
    return result


def test_synthetic_24h_only_verifies_structure_reports_sparse_cadence_and_stays_unqualified(
    fixture,
):
    save_window(fixture, rows(fixture, 86400), terminal=review.FULL, span=86400)
    result = audit(fixture)
    assert result["status"] == "ENGINEERING_FIXTURE_STRUCTURAL_PASS_UNQUALIFIED"
    assert result["measured_elapsed_seconds"] == 86400
    assert result["sample_gaps_exceeding_period"] == 2
    assert result["maximum_gap_excess_seconds"] == 42900
    assert result["committed_feature_growth_bytes"] == 60


@pytest.mark.parametrize("terminal", [review.SHORT, review.FAILED, review.INTERRUPTED])
def test_short_failed_or_interrupted_cannot_get_24h_credit_even_with_valid_structure(
    fixture, terminal
):
    save_window(fixture, rows(fixture), terminal=terminal)
    result = audit(fixture)
    assert result["integrity"] == "PASS" and result["terminal_status"] == terminal


def test_missing_terminal_does_not_inspect_incomplete_stream_or_claim_process_stopped(fixture):
    (fixture["folder"] / "samples.jsonl").write_bytes(b"incomplete live trailing record")
    result = audit(fixture)
    assert result["status"] == "TERMINAL_REPORT_NOT_AVAILABLE"
    assert (
        result["integrity"] == "NOT_EVALUATED"
        and "process state was not inspected" in result["reason"]
    )


@pytest.mark.parametrize(
    "change",
    [
        "pid",
        "start_ticks",
        "session",
        "binding",
        "cpu",
        "events",
        "feature",
        "manifest",
        "audit",
        "elapsed",
        "process_time",
    ],
)
def test_rehashed_splice_and_regressed_counter_records_are_rejected(fixture, change):
    samples = rows(fixture)
    middle = samples[1]
    if change in {"pid", "start_ticks"}:
        middle["process"][change] += 1
    elif change == "session":
        middle["checkpoint"]["session"] = "OTHER_SYNTHETIC_SESSION"
    elif change == "binding":
        middle["binding"]["compression"]["codec"] = "OTHER_SYNTHETIC_BINDING"
    elif change == "cpu":
        middle["process"]["cpu_ticks"] = 1
    elif change == "events":
        middle["checkpoint"]["accepted_events"] = 1
    elif change == "feature":
        middle["feature_bytes"] = 1
    elif change == "manifest":
        middle["manifest_files"] = 1
    elif change == "audit":
        middle["audit_head_seq"] = 1
    elif change == "elapsed":
        middle["elapsed_monotonic_seconds"] += 1
    else:
        middle["process"]["sampled_monotonic_seconds"] -= 31
    save_window(fixture, samples)
    assert audit(fixture)["status"] == "FAIL_CLOSED"


@pytest.mark.parametrize(
    "change", ["chain", "sequence", "line_format", "trailing", "oversize_line", "duplicate_key"]
)
def test_corrupt_or_unbounded_sample_stream_fails_closed(fixture, change):
    report, records = save_window(fixture, rows(fixture))
    if change == "chain":
        records[1]["previous_sha256"] = "a" * 64
    elif change == "sequence":
        records[1]["seq"] = 1
    lines = [review.canonical(record) + b"\n" for record in records]
    if change == "line_format":
        lines[0] = json.dumps(records[0]).encode() + b"\n"
    elif change == "trailing":
        lines.append(b"{")
    elif change == "oversize_line":
        lines[0] = b" " * (review.LINE_LIMIT + 1) + b"\n"
    elif change == "duplicate_key":
        lines[0] = lines[0].replace(b'"seq":1', b'"seq":1,"seq":1')
    payload = b"".join(lines)
    (fixture["folder"] / "samples.jsonl").write_bytes(payload)
    report["samples_sha256"] = review.sha(
        payload
    )  # Updated whole-file SHA cannot hide bad structure.
    write_json(fixture["folder"] / "REPORT.json", report)
    assert audit(fixture)["status"] == "FAIL_CLOSED"


@pytest.mark.parametrize(
    "field",
    [
        "samples",
        "first",
        "last",
        "head_sha256",
        "sampled_peaks",
        "measured_elapsed_seconds",
        "maximum_sample_gap_seconds",
        "collector_cpu_seconds_in_observed_span",
        "committed_feature_growth_bytes",
        "raw_samples_unavailable",
        "raw_sampling_complete",
    ],
)
def test_terminal_summary_must_match_independently_recomputed_stream(fixture, field):
    report, _ = save_window(fixture, rows(fixture))
    if field in {"first", "last"}:
        report[field]["feature_bytes"] += 1
    elif field == "head_sha256":
        report[field] = "f" * 64
    elif field == "sampled_peaks":
        report[field]["raw_sampled_bytes"] += 1
    elif field == "raw_sampling_complete":
        report[field] = False
    else:
        report[field] += 1
    write_json(fixture["folder"] / "REPORT.json", report)
    assert audit(fixture)["status"] == "FAIL_CLOSED"


def test_all_unknown_raw_samples_remain_unknown_and_never_zero_peaks(fixture):
    samples = rows(fixture)
    for row in samples:
        row["raw_inventory"].update(
            status="BUDGET_EXCEEDED_UNAVAILABLE",
            sampled_bytes=None,
            scan_seconds=11,
            partial_known_bytes_not_a_sample=45,
        )
    save_window(fixture, samples)
    result = audit(fixture)
    assert result["integrity"] == "PASS" and result["raw_samples_unavailable"] == 3
    assert (
        not result["raw_sampling_complete"] and "raw_sampled_bytes" not in result["sampled_peaks"]
    )


@pytest.mark.parametrize(
    "change",
    [
        "ram",
        "current",
        "peak",
        "swap",
        "gpu",
        "oom",
        "oom_missing",
        "cgroup",
        "raw_cap",
        "feature_cap",
        "sql",
        "raw_zero_unknown",
    ],
)
def test_rehashed_resource_violations_are_rejected(fixture, change):
    samples = rows(fixture)
    row, ram = samples[1], samples[1]["aggregate_ram"]
    if change == "ram":
        ram["ram_limit_bytes"] = 5_000_000_001
    elif change == "current":
        ram["ram_current_bytes"] = 5_000_000_001
    elif change == "peak":
        ram["ram_peak_bytes"] = 5_000_000_001
    elif change == "swap":
        ram["swap_bytes"] = 1
    elif change == "gpu":
        ram["gpu_used"] = True
    elif change == "oom":
        ram["memory_events"] = ram["memory_events"].replace("oom 0", "oom 1")
    elif change == "oom_missing":
        ram["memory_events"] = "low 0\nhigh 0\nmax 0"
    elif change == "cgroup":
        ram["aggregate_cgroup"] = "/not_project.slice"
    elif change == "raw_cap":
        row["raw_inventory"]["sampled_bytes"] = 4_000_000_001
    elif change == "feature_cap":
        row["feature_bytes"] = 8_000_000_001
    elif change == "sql":
        row["sql_released_before_inventory"] = False
    else:
        row["raw_inventory"].update(status="BUDGET_EXCEEDED_UNAVAILABLE", sampled_bytes=0)
    save_window(fixture, samples)
    assert audit(fixture)["status"] == "FAIL_CLOSED"


@pytest.mark.parametrize("change", ["sum", "intake", "hard", "reserve", "free", "status"])
def test_disk_ledger_requires_whole_vhd_sum_and_intake_emergency_bounds(fixture, change):
    report, _ = save_window(fixture, rows(fixture))
    ledger = report["final_disk"]
    if change == "sum":
        ledger["total_bytes"] -= 1
    elif change == "intake":
        ledger.update(total_bytes=36_000_000_000, project_bytes=30_000_000_000)
    elif change == "hard":
        ledger["hard_limit_bytes"] = 41_000_000_000
    elif change == "reserve":
        ledger["reserved_bytes"] = 28_000_000_000
    elif change == "free":
        ledger["d_free_bytes"] = 3_999_999_999
    else:
        ledger["status"] = "WARNING"
    write_json(fixture["folder"] / "REPORT.json", report)
    assert audit(fixture)["status"] == "FAIL_CLOSED"


@pytest.mark.parametrize(
    "change",
    [
        "source",
        "acceptance",
        "false_qualification",
        "short_full",
        "empty_complete",
        "shortened_complete",
    ],
)
def test_frozen_source_and_complete_status_cannot_be_rebound_or_elevated(fixture, change):
    report, _ = save_window(fixture, rows(fixture))
    if change == "source":
        (fixture["root"] / "src/quant/microstructure.py").write_text("MODIFIED FIXTURE")
    elif change == "acceptance":
        (fixture["root"] / review.ACCEPTANCE).write_text("MODIFIED FIXTURE")
    elif change == "false_qualification":
        report["quality_accepted"] = True
    elif change == "short_full":
        report["status"] = review.FULL
    elif change == "empty_complete":
        report, _ = save_window(fixture, [], terminal=review.SHORT)
    else:
        report["requested_seconds"] = 61
    write_json(fixture["folder"] / "REPORT.json", report)
    assert audit(fixture)["status"] == "FAIL_CLOSED"


def test_failed_window_with_zero_samples_preserves_failure_without_qualification(fixture):
    save_window(fixture, [], terminal=review.FAILED)
    result = audit(fixture)
    assert result["integrity"] == "PASS" and result["samples"] == 0


@pytest.mark.parametrize("tamper", [False, True])
def test_optional_launch_binds_first_two_immutable_records_and_quality_is_link_only(
    fixture, tamper
):
    report, records = save_window(fixture, rows(fixture))
    launch = {
        "status": "REAL_RESOURCE_WINDOW_STARTED_NOT_24H_ACCEPTED",
        "window_directory": str(fixture["folder"]),
        "engineering_acceptance": {"path": review.ACCEPTANCE, "sha256": fixture["acceptance_sha"]},
        "requested_seconds": report["requested_seconds"],
        "period_seconds": report["period_seconds"],
        "verified_initial_records": records[:2],
        "initial_two_sample_span_seconds": 30,
        "actual_24h_capacity_accepted": False,
        "actual_24h_quality_accepted": False,
        "training_authorized": False,
        "alpha_eligible": False,
    }
    if tamper:
        launch["verified_initial_records"][0]["sha256"] = "a" * 64
    launch_path, quality_path = (
        fixture["root"] / "reports/launch.json",
        fixture["root"] / "reports/quality.json",
    )
    write_json(launch_path, launch)
    write_json(quality_path, {"status": "UNTRUSTED_FIXTURE", "actual_24h_quality_accepted": True})
    result = audit(fixture, launch=launch_path, quality=quality_path)
    assert result["status"] == "FAIL_CLOSED" if tamper else result["integrity"] == "PASS"
    if not tamper:
        assert (
            result["quality_report_link"]["scope"] == "LINK_ONLY_NOT_A_TERMINAL_QUALITY_ACCEPTANCE"
        )
        assert result["launch_receipt"]["sha256"] == review.sha(launch_path.read_bytes())


def test_default_pinned_acceptance_rejects_self_reissued_fixture_receipt(fixture):
    save_window(fixture, rows(fixture))
    result = review.audit_window(fixture["folder"])
    assert result["status"] == "FAIL_CLOSED" and "acceptance hash" in result["reason"]


def test_window_path_cannot_escape_reports_or_read_arbitrary_source(fixture):
    result = review.audit_window(STATE, expected_acceptance_sha=fixture["acceptance_sha"])
    assert result["status"] == "FAIL_CLOSED" and "escaped" in result["reason"]
