"""Read-only structural review of a closed, frozen A07 sampled resource window."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from datetime import UTC, datetime
from pathlib import Path

from quant.paths import ROOT, STATE

ACCEPTANCE = "reports/A07_RESOURCE_OBSERVER_ACCEPTANCE_20261001.json"
ACCEPTANCE_SHA = "79342daab8e447817a6e0120b1d1d4631ae90b9111ccc863c16af55f67c7a873"
BOUND_FILES = (
    "src/quant/microstructure.py",
    "scripts/microstructure.ps1",
    "scripts/microstructure.sh",
    "scripts/observe_a07_resources.py",
    "scripts/observe_a07_resources.ps1",
)
STREAM_LIMIT, LINE_LIMIT, RECORD_LIMIT = 10_000_000, 32_000, 5000
SHORT = "REAL_SHORT_SAMPLED_RESOURCE_WINDOW_COMPLETE"
FULL = "REAL_24H_SAMPLED_RESOURCE_WINDOW_COMPLETE"
FAILED = "FAILED_RESOURCE_WINDOW_NOT_ACCEPTED"
INTERRUPTED = "INTERRUPTED_RESOURCE_WINDOW_NOT_ACCEPTED"


def require(ok, message):
    if not ok:
        raise ValueError(message)


def canonical(value):
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode()


def parse(payload):
    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result, "Duplicate JSON key")
            result[key] = value
        return result

    value = json.loads(
        payload,
        object_pairs_hook=pairs,
        parse_constant=lambda _: (_ for _ in ()).throw(ValueError("Nonfinite JSON")),
    )
    canonical(value)  # Includes overflowed floats in unknown/extra fields.
    return value


def read(path, limit):
    require(path.is_file() and path.stat().st_size <= limit, "Missing/oversize evidence file")
    with path.open("rb") as reader:
        payload = reader.read(limit + 1)
    require(len(payload) <= limit, "Evidence read bound exceeded")
    return payload


def sha(payload):
    return hashlib.sha256(payload).hexdigest()


def integer(value, name, *, minimum=0):
    require(type(value) is int and value >= minimum, f"Invalid {name}")
    return value


def number(value, name, *, minimum=0):
    require(
        type(value) in (int, float) and math.isfinite(value) and value >= minimum, f"Invalid {name}"
    )
    return value


def digest(value):
    require(
        isinstance(value, str)
        and len(value) == 64
        and all(char in "0123456789abcdef" for char in value),
        "Invalid SHA256",
    )
    return value


def utc(value):
    parsed = datetime.fromisoformat(value)
    require(
        parsed.utcoffset() is not None and parsed.utcoffset().total_seconds() == 0,
        "UTC timestamp required",
    )
    return parsed.timestamp()


def relative_file(name):
    require(isinstance(name, str) and len(name) <= 1024, "Invalid bound relative path")
    path = (ROOT / name).resolve()
    require(
        not Path(name).is_absolute() and path.is_relative_to(ROOT.resolve()),
        "Bound source path escaped ROOT",
    )
    return path


def frozen_sources(expected_sha):
    payload = read(relative_file(ACCEPTANCE), 2_000_000)
    require(sha(payload) == expected_sha, "Frozen observer acceptance hash changed")
    receipt = parse(payload)
    require(
        receipt["status"] == "A07_RESOURCE_OBSERVER_SHORT_ENGINEERING_PASS",
        "Observer engineering acceptance missing",
    )
    sources = receipt["source_hashes"]
    require(set(BOUND_FILES) <= sources.keys(), "Incomplete frozen observer binding")
    verified = {}
    for mapping in (sources, receipt["verified_prior_files"]):
        require(len(mapping) <= 100, "Frozen source count bound")
        for name, expected in mapping.items():
            require(
                sha(read(relative_file(name), 4_000_000)) == digest(expected),
                f"Frozen file changed: {name}",
            )
            require(
                name not in verified or verified[name] == expected,
                "Conflicting frozen file binding",
            )
            verified[name] = expected
    for binding in (receipt["actual_report"], receipt["tests"]):
        require(
            sha(read(relative_file(binding["path"]), 2_000_000)) == digest(binding["sha256"]),
            "Frozen observer acceptance evidence changed",
        )
        verified[binding["path"]] = binding["sha256"]
    return {name: sources[name] for name in BOUND_FILES}, verified


def validate_ram(ram):
    limit = integer(ram["ram_limit_bytes"], "RAM limit", minimum=1)
    current = integer(ram["ram_current_bytes"], "RAM current")
    peak = integer(ram["ram_peak_bytes"], "RAM lifetime peak")
    require(current <= peak <= limit <= 5_000_000_000, "Shared RAM bound exceeded")
    require(
        type(ram["swap_bytes"]) is int and ram["swap_bytes"] == 0 and ram["gpu_used"] is False,
        "Swap/GPU forbidden",
    )
    require(
        isinstance(ram["aggregate_cgroup"], str)
        and ram["aggregate_cgroup"].endswith("/coin-quant.slice"),
        "Wrong aggregate cgroup",
    )
    events = {}
    for line in ram["memory_events"].splitlines():
        key, value = line.split()
        require(key not in events and value.isdecimal(), "Invalid memory event counter")
        events[key] = int(value)
    require(
        all(key in events and events[key] == 0 for key in ("oom", "oom_kill", "oom_group_kill")),
        "OOM event or unknown counter",
    )


def validate_disk(ledger):
    fields = {
        key: integer(ledger[key], key)
        for key in (
            "project_bytes",
            "wsl_vhd_bytes",
            "total_bytes",
            "reserved_bytes",
            "d_free_bytes",
            "hard_limit_bytes",
        )
    }
    total = fields["total_bytes"]
    require(
        total == fields["project_bytes"] + fields["wsl_vhd_bytes"],
        "Whole-project plus entire VHD sum mismatch",
    )
    require(
        fields["hard_limit_bytes"] == 40_000_000_000
        and total + fields["reserved_bytes"] < 36_000_000_000,
        "40 GB hard / 36 GB intake bound exceeded",
    )
    require(
        fields["d_free_bytes"] >= fields["reserved_bytes"] + 4_000_000_000,
        "D emergency free-space buffer violated",
    )
    require(
        ledger["status"]
        == ("WARNING" if total + fields["reserved_bytes"] >= 32_000_000_000 else "OK"),
        "Disk status mismatch",
    )


def validate_sample(row, sources):
    process, checkpoint, binding = row["process"], row["checkpoint"], row["binding"]
    for key in ("pid", "start_ticks"):
        integer(process[key], key, minimum=1)
    for key in ("cpu_ticks", "rss_bytes", "lifetime_rss_hwm_bytes"):
        integer(process[key], key)
    number(process["sampled_monotonic_seconds"], "Process monotonic time")
    number(row["elapsed_monotonic_seconds"], "Elapsed monotonic time")
    require(
        process["rss_bytes"] <= process["lifetime_rss_hwm_bytes"] <= 5_000_000_000,
        "Process RSS bound exceeded",
    )
    require(
        binding["mode"] == "live"
        and binding["version"] == "microstructure_l1_v1"
        and binding["implementation_sha256"] == sources["src/quant/microstructure.py"]
        and binding["store"] == str(ROOT / "data/microstructure_v1"),
        "Wrong live source",
    )
    require(
        isinstance(checkpoint["session"], str)
        and 0 < len(checkpoint["session"]) <= 128
        and type(checkpoint["connected"]) is bool,
        "Invalid session/connectivity",
    )
    for key in ("asof_us", "accepted_events", "duplicate_events", "rejected_events"):
        integer(checkpoint[key], key)
    number(checkpoint["observed_monotonic_seconds"], "Collector observed time")
    sample_utc = utc(row["sampled_utc"])
    require(
        0 <= sample_utc - checkpoint["asof_us"] / 1_000_000 <= 10, "Stale/future sampled checkpoint"
    )
    for key in ("feature_bytes", "feature_rows", "manifest_files", "audit_head_seq"):
        integer(row[key], key)
    require(row["feature_bytes"] <= 8_000_000_000, "Immutable feature cap exceeded")
    digest(row["audit_head_sha256"])
    require(
        row["sql_released_before_inventory"] is True
        and number(row["sql_read_seconds"], "SQL read seconds") <= 5,
        "Live SQL snapshot bound/release violated",
    )
    native = row["native_files_sampled_bytes"]
    require(
        isinstance(native, dict)
        and "microstructure.sqlite3" in native
        and native.keys()
        <= {"microstructure.sqlite3", "microstructure.sqlite3-wal", "microstructure.sqlite3-shm"},
        "Unexpected native files",
    )
    for key, value in native.items():
        integer(value, key)
    require(
        integer(row["global_vhd_sampled_bytes"], "Entire VHD sampled bytes") < 40_000_000_000,
        "Entire VHD alone exceeds hard disk bound",
    )
    validate_ram(row["aggregate_ram"])
    raw = row["raw_inventory"]
    require(
        raw["atomic_snapshot"] is False and raw["exact_unsampled_peak_known"] is False,
        "Sampled raw inventory cannot certify exact peaks",
    )
    integer(raw["entries_seen"], "Raw inventory entries")
    integer(raw["legitimate_concurrent_retirement_or_missing_entries"], "Raw retired entries")
    scan = number(raw["scan_seconds"], "Raw inventory seconds")
    if raw["sampled_bytes"] is None:
        require(
            raw["status"] == "BUDGET_EXCEEDED_UNAVAILABLE"
            and (raw["entries_seen"] > 20_000 or scan > 10),
            "Unknown raw sample mislabelled",
        )
        integer(raw["partial_known_bytes_not_a_sample"], "Partial raw bytes")
    else:
        require(
            raw["status"] == "AVAILABLE_SAMPLED_INVENTORY"
            and raw["entries_seen"] <= 20_000
            and integer(raw["sampled_bytes"], "Raw sampled bytes") <= 4_000_000_000,
            "Raw sample status/cap mismatch",
        )


def same_window(previous, current):
    require(
        (
            previous["process"]["pid"],
            previous["process"]["start_ticks"],
            previous["checkpoint"]["session"],
            previous["binding"],
        )
        == (
            current["process"]["pid"],
            current["process"]["start_ticks"],
            current["checkpoint"]["session"],
            current["binding"],
        ),
        "Spliced PID/start/session/source window",
    )
    for section, keys in (
        ("process", ("cpu_ticks", "sampled_monotonic_seconds", "lifetime_rss_hwm_bytes")),
        (
            "checkpoint",
            (
                "asof_us",
                "accepted_events",
                "duplicate_events",
                "rejected_events",
                "observed_monotonic_seconds",
            ),
        ),
    ):
        for key in keys:
            require(current[section][key] >= previous[section][key], "Sample counter reversed")
    for key in (
        "feature_bytes",
        "feature_rows",
        "manifest_files",
        "audit_head_seq",
        "elapsed_monotonic_seconds",
    ):
        require(current[key] >= previous[key], "Immutable/monotonic counter reversed")
    require(utc(current["sampled_utc"]) >= utc(previous["sampled_utc"]), "UTC clock reversed")
    require(
        current["aggregate_ram"]["aggregate_cgroup"]
        == previous["aggregate_ram"]["aggregate_cgroup"],
        "Aggregate cgroup changed",
    )
    if current["audit_head_seq"] == previous["audit_head_seq"]:
        require(current["audit_head_sha256"] == previous["audit_head_sha256"], "Audit head changed")


def audit_window(directory, *, launch=None, quality=None, expected_acceptance_sha=None):
    """Never grants data/alpha/health qualification. Hash override is STATE-fixture-only."""
    result = {
        "module": "A07_RESOURCE_WINDOW_STRUCTURAL_REVIEW",
        "read_only": True,
        "created_utc": datetime.now(UTC).isoformat(),
        "status": "FAIL_CLOSED",
        "integrity": "NOT_ESTABLISHED",
        "actual_24h_capacity_accepted": False,
        "actual_24h_quality_accepted": False,
        "alpha_eligible": False,
        "training_authorized": False,
        "predictive_diagnostics_data_review_eligible": False,
        "preregistered_research_data_review_eligible": False,
        "healthy_credit_seconds": 0,
        "exact_unsampled_peak_known": False,
        "network_requests": 0,
        "collector_writes": 0,
        "collector_restarts": 0,
        "engineering_fixture_hook": expected_acceptance_sha is not None,
        "limitations": [
            "Local canonical hash bindings are not external signatures.",
            "Cadence and endpoints do not prove continuous resource coverage.",
            "Raw inventories are non-atomic; unknown samples are not zero.",
            "Native/VHD peaks are sampled, not exact unsampled peaks.",
            "Terminal frozen quality audit and separate resource review required.",
        ],
    }
    try:
        folder = Path(directory).resolve()
        require(
            folder.is_relative_to((ROOT / "reports/generated").resolve()),
            "Window evidence escaped D reports/generated",
        )
        result["directory"] = str(folder)
        if expected_acceptance_sha is not None:
            require(
                ROOT.resolve().is_relative_to(STATE.resolve()),
                "Fixture hash override outside STATE",
            )
        expected = (
            ACCEPTANCE_SHA if expected_acceptance_sha is None else digest(expected_acceptance_sha)
        )
        sources, preserved = frozen_sources(expected)
        result["engineering_acceptance"] = {"path": ACCEPTANCE, "sha256": expected}
        result["verified_frozen_files"] = preserved
        report_path = folder / "REPORT.json"
        if not report_path.exists():
            result.update(
                status="TERMINAL_REPORT_NOT_AVAILABLE",
                integrity="NOT_EVALUATED",
                reason="No terminal REPORT.json; process state was not inspected.",
            )
            return result
        require(report_path.resolve().is_relative_to(folder), "Terminal report escaped window")
        report_bytes = read(report_path, 2_000_000)
        measured = parse(report_bytes)
        result["terminal_report"] = {
            "path": str(report_path.relative_to(ROOT)),
            "sha256": sha(report_bytes),
        }
        require(measured["status"] in {SHORT, FULL, FAILED, INTERRUPTED}, "Unknown terminal status")
        utc(measured["created_utc"])
        require(measured["source_hashes"] == sources, "Terminal observer source binding changed")
        require(
            all(
                measured[key] is False
                for key in (
                    "quality_accepted",
                    "actual_24h_capacity_accepted",
                    "alpha_eligible",
                    "training_authorized",
                )
            ),
            "Sampler cannot grant qualification",
        )
        require(
            all(
                type(measured[key]) is int and measured[key] == 0
                for key in (
                    "collector_writes",
                    "collector_restarts",
                    "network_requests",
                )
            ),
            "Unexpected sampler mutation/network",
        )
        requested = number(measured["requested_seconds"], "Requested duration")
        period = number(measured["period_seconds"], "Sample period")
        require(10 <= requested <= 86400 and 1 <= period <= min(300, requested), "Invalid schedule")
        ticks = integer(measured["clock_ticks_per_second"], "Clock ticks", minimum=1)
        require(ticks == os.sysconf("SC_CLK_TCK"), "Kernel clock ticks binding mismatch")
        for key in ("initial_disk", "final_disk"):
            validate_disk(measured[key])
        sample_path = folder / "samples.jsonl"
        require(sample_path.resolve().is_relative_to(folder), "Sample stream escaped window")
        require(sample_path.stat().st_size <= STREAM_LIMIT, "Sample stream size bound")
        head, count, first, last, peaks, maximum_gap = "0" * 64, 0, None, None, {}, 0
        raw_unknown, disconnected, excess_gaps = 0, 0, 0
        stream_sha, stream_bytes, initial_records = hashlib.sha256(), 0, []
        with sample_path.open("rb") as reader:
            while line := reader.readline(LINE_LIMIT + 1):
                stream_bytes += len(line)
                require(
                    len(line) <= LINE_LIMIT
                    and stream_bytes <= STREAM_LIMIT
                    and count < RECORD_LIMIT,
                    "Sample read bound exceeded",
                )
                record = parse(line)
                require(
                    set(record) == {"seq", "previous_sha256", "sample", "sha256"}
                    and line == canonical(record) + b"\n",
                    "Noncanonical/extra sample record",
                )
                require(
                    type(record["seq"]) is int
                    and record["seq"] == count + 1
                    and record["previous_sha256"] == head,
                    "Sample sequence/previous SHA mismatch",
                )
                head = sha(
                    canonical({key: record[key] for key in ("seq", "previous_sha256", "sample")})
                )
                require(head == digest(record["sha256"]), "Sample canonical SHA mismatch")
                row = record["sample"]
                validate_sample(row, sources)
                if last is not None:
                    same_window(last, row)
                    gap = row["elapsed_monotonic_seconds"] - last["elapsed_monotonic_seconds"]
                    process_gap = (
                        row["process"]["sampled_monotonic_seconds"]
                        - last["process"]["sampled_monotonic_seconds"]
                    )
                    require(
                        gap > 0 and math.isclose(gap, process_gap, rel_tol=0, abs_tol=1e-6),
                        "Elapsed/process clock difference mismatch",
                    )
                    maximum_gap = max(maximum_gap, gap)
                    excess_gaps += gap > period
                raw_unknown += row["raw_inventory"]["sampled_bytes"] is None
                disconnected += not row["checkpoint"]["connected"]
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
                if count < 2:
                    initial_records.append(record)
                first = row if first is None else first
                last, count = row, count + 1
                stream_sha.update(line)
        for key, value in measured["sampled_peaks"].items():
            integer(value, key)
        require(
            type(measured["samples"]) is int
            and count == measured["samples"]
            and head == measured["head_sha256"]
            and canonical(first) == canonical(measured["first"])
            and canonical(last) == canonical(measured["last"])
            and peaks == measured["sampled_peaks"]
            and stream_sha.hexdigest() == measured["samples_sha256"],
            "Stream/terminal count/endpoints/peaks/SHA mismatch",
        )
        require(
            type(measured["raw_samples_unavailable"]) is int
            and raw_unknown == measured["raw_samples_unavailable"]
            and measured["raw_sampling_complete"] is (count > 0 and raw_unknown == 0),
            "Unknown raw sample accounting mismatch",
        )
        require(
            maximum_gap == number(measured["maximum_sample_gap_seconds"], "Maximum gap"),
            "Maximum gap mismatch",
        )
        span = cpu = growth = 0
        if count:
            span = last["elapsed_monotonic_seconds"] - first["elapsed_monotonic_seconds"]
            cpu = (last["process"]["cpu_ticks"] - first["process"]["cpu_ticks"]) / ticks
            growth = last["feature_bytes"] - first["feature_bytes"]
            number(measured["measured_elapsed_seconds"], "Measured elapsed")
            number(measured["collector_cpu_seconds_in_observed_span"], "Measured CPU delta")
            integer(measured["committed_feature_growth_bytes"], "Measured feature growth")
            require(
                span == measured["measured_elapsed_seconds"]
                and cpu == measured["collector_cpu_seconds_in_observed_span"]
                and growth == measured["committed_feature_growth_bytes"],
                "Window arithmetic mismatch",
            )
            require(
                utc(measured["created_utc"]) >= utc(last["sampled_utc"]),
                "Terminal timestamp reversed",
            )
        else:
            require(
                not any(
                    key in measured
                    for key in (
                        "measured_elapsed_seconds",
                        "collector_cpu_seconds_in_observed_span",
                        "committed_feature_growth_bytes",
                    )
                ),
                "Empty stream cannot report measured duration/CPU/growth",
            )
        if measured["status"] in {SHORT, FULL}:
            require(
                count >= 2 and span >= requested and measured["failure"] is None,
                "Complete status without requested span",
            )
            require(
                (measured["status"] == FULL) == (requested == 86400), "24h status/request mismatch"
            )
        elif measured["status"] == FAILED:
            require(
                isinstance(measured["failure"], str) and measured["failure"],
                "Missing failure reason",
            )
        if launch is not None:
            launch_path = Path(launch).resolve()
            require(
                launch_path.is_relative_to((ROOT / "reports").resolve()),
                "Launch path escaped reports",
            )
            payload = read(launch_path, 2_000_000)
            launched = parse(payload)
            require(
                launched["status"] == "REAL_RESOURCE_WINDOW_STARTED_NOT_24H_ACCEPTED"
                and Path(launched["window_directory"]).resolve() == folder
                and launched["engineering_acceptance"] == result["engineering_acceptance"]
                and launched["requested_seconds"] == requested
                and launched["period_seconds"] == period
                and len(initial_records) == 2
                and canonical(launched["verified_initial_records"]) == canonical(initial_records),
                "Launch binding/immutable first two records changed",
            )
            if "hostcheck" in launched:
                host = launched["hostcheck"]
                require(
                    sha(read(relative_file(host["path"]), 2_000_000)) == digest(host["sha256"]),
                    "Launch hostcheck receipt changed",
                )
            number(launched["initial_two_sample_span_seconds"], "Launch sample span")
            require(
                launched["initial_two_sample_span_seconds"]
                == initial_records[1]["sample"]["elapsed_monotonic_seconds"]
                - initial_records[0]["sample"]["elapsed_monotonic_seconds"],
                "Launch span mismatch",
            )
            for key in (
                "actual_24h_capacity_accepted",
                "actual_24h_quality_accepted",
                "training_authorized",
                "alpha_eligible",
            ):
                require(launched[key] is False, "Launch cannot grant qualification")
            result["launch_receipt"] = {
                "path": str(launch_path.relative_to(ROOT)),
                "sha256": sha(payload),
            }
        if quality is not None:
            quality_path = Path(quality).resolve()
            require(
                quality_path.is_relative_to((ROOT / "reports").resolve()),
                "Quality path escaped reports",
            )
            payload = read(quality_path, STREAM_LIMIT)
            linked = parse(payload)
            result["quality_report_link"] = {
                "path": str(quality_path.relative_to(ROOT)),
                "sha256": sha(payload),
                "status": linked.get("status"),
                "scope": "LINK_ONLY_NOT_A_TERMINAL_QUALITY_ACCEPTANCE",
            }
        require(
            frozen_sources(expected) == (sources, preserved), "Frozen sources changed during review"
        )
        require(
            read(report_path, 2_000_000) == report_bytes, "Terminal report changed during review"
        )
        result.update(
            integrity="PASS",
            terminal_status=measured["status"],
            samples=count,
            samples_sha256=stream_sha.hexdigest(),
            head_sha256=head,
            measured_elapsed_seconds=span,
            collector_cpu_seconds_in_observed_span=cpu,
            committed_feature_growth_bytes=growth,
            sampled_peaks=peaks,
            raw_samples_unavailable=raw_unknown,
            raw_sampling_complete=count > 0 and raw_unknown == 0,
            disconnected_samples=disconnected,
            period_seconds=period,
            maximum_sample_gap_seconds=maximum_gap,
            sample_gaps_exceeding_period=excess_gaps,
            maximum_gap_excess_seconds=max(0, maximum_gap - period),
            initial_disk=measured["initial_disk"],
            final_disk=measured["final_disk"],
            disk_scope="Whole project plus entire VHD at endpoints only; no mid-window total scan",
            status="ENGINEERING_FIXTURE_STRUCTURAL_PASS_UNQUALIFIED"
            if result["engineering_fixture_hook"]
            else "SAMPLED_24H_RESOURCE_EVIDENCE_REVIEW_REQUIRED"
            if measured["status"] == FULL
            else "SHORT_SAMPLED_RESOURCE_EVIDENCE_UNQUALIFIED"
            if measured["status"] == SHORT
            else "INCOMPLETE_RESOURCE_WINDOW_UNQUALIFIED",
        )
    except (
        OSError,
        ValueError,
        KeyError,
        TypeError,
        AttributeError,
        OverflowError,
        RecursionError,
    ) as error:
        result.update(status="FAIL_CLOSED", integrity="NOT_ESTABLISHED", reason=str(error))
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--directory", type=Path, required=True)
    parser.add_argument("--launch", type=Path)
    parser.add_argument("--quality", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    require(
        output.is_relative_to((ROOT / "reports").resolve())
        and output.suffix == ".json"
        and not output.exists(),
        "New exclusive D report required",
    )
    result = audit_window(args.directory, launch=args.launch, quality=args.quality)
    payload = json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False) + "\n"
    require(len(payload.encode()) <= 2_000_000, "Review output bound")
    with output.open("x", encoding="utf-8") as writer:
        writer.write(payload)
    print(
        json.dumps(
            {
                key: result[key]
                for key in (
                    "status",
                    "integrity",
                    "actual_24h_capacity_accepted",
                    "actual_24h_quality_accepted",
                )
            }
        )
    )
    if result["status"] == "FAIL_CLOSED":
        raise SystemExit(2)


if __name__ == "__main__":
    main()
