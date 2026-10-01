"""Keep an independent unqualified receipt when the frozen A07 sampler raises."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import os
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

from quant.paths import ROOT, STATE
from quant.resources import status as resource_status

ACCEPTANCE = "reports/A07_RESOURCE_OBSERVER_ACCEPTANCE_20261001.json"
ACCEPTANCE_SHA = "79342daab8e447817a6e0120b1d1d4631ae90b9111ccc863c16af55f67c7a873"
OLD_SCRIPT = "scripts/observe_a07_resources.py"
BOUND_FILES = (
    "src/quant/microstructure.py",
    "scripts/microstructure.ps1",
    "scripts/microstructure.sh",
    OLD_SCRIPT,
    "scripts/observe_a07_resources.ps1",
    "tests/test_a07_resource_observer.py",
    "scripts/accept_a07_resource_observer.py",
    "docs/MODULE_A07_RESOURCE_OBSERVATION.md",
)


def require(ok, message):
    if not ok:
        raise ValueError(message)


def digest(path, maximum):
    require(path.is_file() and path.stat().st_size <= maximum, "Missing/oversize artifact")
    hashed, total = hashlib.sha256(), 0
    with path.open("rb") as reader:
        while block := reader.read(min(1_048_576, maximum + 1 - total)):
            total += len(block)
            require(total <= maximum, "Artifact read bound exceeded")
            hashed.update(block)
    return {"sha256": hashed.hexdigest(), "bytes": total}


def read_json(path, maximum=2_000_000):
    require(path.stat().st_size <= maximum, "Oversize JSON artifact")
    with path.open("rb") as reader:
        payload = reader.read(maximum + 1)
    require(len(payload) <= maximum, "JSON read bound exceeded")

    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result, "Duplicate JSON key")
            result[key] = value
        return result

    result = json.loads(payload, object_pairs_hook=pairs)
    json.dumps(result, allow_nan=False)
    return result


def bound_path(name):
    require(
        isinstance(name, str) and len(name) <= 1024 and not Path(name).is_absolute(),
        "Invalid frozen relative path",
    )
    path = (ROOT / name).resolve()
    require(path.is_relative_to(ROOT.resolve()), "Frozen path escaped ROOT")
    return path


def source_binding(expected_sha):
    path = bound_path(ACCEPTANCE)
    receipt_digest = digest(path, 2_000_000)
    require(receipt_digest["sha256"] == expected_sha, "Frozen sampler acceptance SHA changed")
    receipt = read_json(path)
    require(
        receipt["status"] == "A07_RESOURCE_OBSERVER_SHORT_ENGINEERING_PASS"
        and set(receipt["source_hashes"]) == set(BOUND_FILES),
        "Frozen eight-source binding missing",
    )
    actual = {name: digest(bound_path(name), 4_000_000)["sha256"] for name in BOUND_FILES}
    prior = receipt["verified_prior_files"]
    require(len(prior) <= 100, "Prior binding count bound")
    preserved = {name: digest(bound_path(name), 4_000_000)["sha256"] for name in prior}
    return {
        "acceptance": {"path": ACCEPTANCE, **receipt_digest},
        "expected_source_hashes": receipt["source_hashes"],
        "actual_source_hashes": actual,
        "verified_prior_hashes": preserved,
        "matches_frozen": actual == receipt["source_hashes"] and preserved == prior,
    }


def load_sampler(expected_source_sha):
    spec = importlib.util.spec_from_file_location(
        "_a07_frozen_sampler_for_resilient", bound_path(OLD_SCRIPT)
    )
    require(spec is not None and spec.loader is not None, "Frozen sampler loader unavailable")
    module = importlib.util.module_from_spec(spec)
    path = bound_path(OLD_SCRIPT)
    require(path.stat().st_size <= 4_000_000, "Oversize sampler source")
    with path.open("rb") as reader:
        source = reader.read(4_000_001)
    require(
        len(source) <= 4_000_000 and hashlib.sha256(source).hexdigest() == expected_source_sha,
        "Sampler source changed before compilation",
    )
    # Compile verified source bytes directly rather than trusting cached bytecode.
    exec(compile(source, str(path), "exec"), module.__dict__)
    return module.main


def exception_summary(error):
    frames, current = [], error.__traceback__
    while current is not None:
        frame = current.tb_frame
        frames.append(
            {
                "file": str(frame.f_code.co_filename)[-512:],
                "function": frame.f_code.co_name[:128],
                "line": current.tb_lineno,
            }
        )
        frames = frames[-8:]
        current = current.tb_next
    result = {"type": type(error).__name__, "message": str(error)[:2048], "frames": frames}
    if isinstance(error, SystemExit):
        code = error.code
        result["exit_code"] = code if type(code) in (int, type(None)) else str(code)[:512]
    return result


def created_window_from_exception(error, delegate, folder):
    """Frozen main assigns these locals only AFTER its exclusive folder.mkdir succeeds."""
    code = getattr(delegate, "__code__", None)
    if code is None:
        return False
    current = error.__traceback__
    while current is not None:
        frame = current.tb_frame
        if frame.f_code is code:
            values = frame.f_locals
            return (
                set(("started", "head", "count", "bytes_written", "folder")) <= values.keys()
                and isinstance(values["folder"], Path)
                and values["folder"] == folder
            )
        current = current.tb_next
    return False


def capture_artifacts(folder):
    artifacts, errors = {}, []
    for name, maximum in (("REPORT.json", 2_000_000), ("samples.jsonl", 10_000_000)):
        path = folder / name
        if not path.exists():
            artifacts[name] = {"status": "NOT_AVAILABLE"}
            continue
        try:
            require(path.resolve().is_relative_to(folder), "Sampler artifact escaped owned window")
            artifacts[name] = {"status": "READ_ONLY_HASHED", **digest(path, maximum)}
            if name == "REPORT.json":
                report = read_json(path)
                artifacts[name]["terminal_status"] = report.get("status")
                artifacts[name]["requested_seconds"] = report.get("requested_seconds")
                artifacts[name]["period_seconds"] = report.get("period_seconds")
        except Exception as error:
            artifacts[name] = {"status": "NOT_VERIFIED", "error": exception_summary(error)}
            errors.append(name)
    return artifacts, errors


def run_observer(
    directory,
    *,
    seconds=86400,
    period=300,
    output,
    expected_acceptance_sha=None,
    fixture_delegate=None,
):
    """Production delegates unchanged main. Paired fixture hooks are native STATE-only."""
    folder, output = Path(directory).resolve(), Path(output).resolve()
    require(
        output.is_relative_to((ROOT / "reports").resolve())
        and output.suffix == ".json"
        and output.parent.is_dir()
        and not output.is_relative_to(folder),
        "Independent existing D reports parent and JSON output required",
    )
    fixture = expected_acceptance_sha is not None or fixture_delegate is not None
    if fixture:
        require(
            ROOT.resolve().is_relative_to(STATE.resolve())
            and expected_acceptance_sha is not None
            and callable(fixture_delegate),
            "Paired engineering fixture hooks require isolated native STATE ROOT",
        )
    # This independent handle exists before any sampler/source/resource call; no
    # write ever enters an old or raced sampler directory.
    with output.open("x", encoding="utf-8") as writer:
        started = time.monotonic()
        safe_seconds = (
            seconds if type(seconds) in (int, float) and math.isfinite(seconds) else "INVALID"
        )
        safe_period = (
            period if type(period) in (int, float) and math.isfinite(period) else "INVALID"
        )
        result = {
            "module": "A07_RESILIENT_OBSERVER_WRAPPER",
            "created_utc": datetime.now(UTC).isoformat(),
            "status": "RESILIENT_WRAPPER_FAILURE_UNQUALIFIED",
            "directory": str(folder),
            "requested_seconds": safe_seconds,
            "period_seconds": safe_period,
            "engineering_fixture_hook": fixture,
            "delegate_started": False,
            "delegate_returned": False,
            "owned_sampler_directory_established": False,
            "sampler_artifacts": {},
            "collector_writes": 0,
            "collector_restarts": 0,
            "network_requests": 0,
            "actual_24h_capacity_accepted": False,
            "actual_24h_quality_accepted": False,
            "alpha_eligible": False,
            "training_authorized": False,
            "healthy_credit_seconds": 0,
            "exact_unsampled_peak_known": False,
            "limitations": [
                "Wrapper return is engineering evidence, never window/data qualification.",
                "The frozen sampler REPORT and samples are never repaired or overwritten.",
                "Initial/raced directories are never read or attributed to this attempt.",
                "No process state/recovery decision or restart is made.",
                "Forced kill, disk/OS write failure may leave an empty reserved receipt; "
                "such a file is not a closed report or an acceptance.",
            ],
        }
        delegate, owned, phase = None, False, "PREPARATION"
        expected = ACCEPTANCE_SHA if expected_acceptance_sha is None else expected_acceptance_sha
        wrapper_path = Path(__file__).resolve()
        try:
            require(
                folder.is_relative_to((ROOT / "reports/generated").resolve())
                and not folder.exists(),
                "New exclusive sampler directory required",
            )
            require(
                type(seconds) in (int, float)
                and math.isfinite(seconds)
                and 10 <= seconds <= 86400
                and type(period) in (int, float)
                and math.isfinite(period)
                and 1 <= period <= min(300, seconds),
                "Invalid schedule",
            )
            result["wrapper_source_before"] = digest(wrapper_path, 1_000_000)
            result["source_binding_before"] = source_binding(expected)
            require(
                result["source_binding_before"]["matches_frozen"], "Frozen sampler source changed"
            )
            result["runtime_resources_before"] = resource_status()
            delegate = (
                fixture_delegate
                if fixture_delegate is not None
                else load_sampler(
                    result["source_binding_before"]["actual_source_hashes"][OLD_SCRIPT]
                )
            )
            original_argv = sys.argv
            phase = "FROZEN_SAMPLER_MAIN"
            try:
                sys.argv = [
                    str(bound_path(OLD_SCRIPT)),
                    "--directory",
                    str(folder),
                    "--seconds",
                    str(seconds),
                    "--period",
                    str(period),
                ]
                result["delegated_argv"] = sys.argv.copy()
                result["delegate_started"] = True
                delegate()
                result["delegate_returned"], owned = True, True
            except (Exception, SystemExit, KeyboardInterrupt) as error:
                owned = created_window_from_exception(error, delegate, folder)
                raise
            finally:
                sys.argv = original_argv
            result["status"] = "RESILIENT_WRAPPER_ENGINEERING_RETURN_ONLY"
        except (Exception, SystemExit, KeyboardInterrupt) as error:
            result["exception"] = {"phase": phase, **exception_summary(error)}
        result["owned_sampler_directory_established"] = owned
        if owned:
            artifacts, errors = capture_artifacts(folder)
            result["sampler_artifacts"] = artifacts
            if errors:
                result["artifact_capture_failures"] = errors
                result["status"] = "RESILIENT_WRAPPER_FAILURE_UNQUALIFIED"
            if result["delegate_returned"]:
                terminal = artifacts.get("REPORT.json", {})
                if (
                    terminal.get("status") != "READ_ONLY_HASHED"
                    or terminal.get("terminal_status")
                    not in {
                        "REAL_SHORT_SAMPLED_RESOURCE_WINDOW_COMPLETE",
                        "REAL_24H_SAMPLED_RESOURCE_WINDOW_COMPLETE",
                    }
                    or terminal.get("requested_seconds") != seconds
                    or terminal.get("period_seconds") != period
                ):
                    result["status"] = "RESILIENT_WRAPPER_FAILURE_UNQUALIFIED"
                    result["terminal_result_error"] = (
                        "No matching complete original terminal report"
                    )
        try:
            result["source_binding_after"] = source_binding(expected)
            result["wrapper_source_after"] = digest(wrapper_path, 1_000_000)
            require(
                result["source_binding_after"]["matches_frozen"]
                and result["source_binding_after"] == result.get("source_binding_before")
                and result["wrapper_source_after"] == result.get("wrapper_source_before"),
                "Source binding changed/unverified across wrapper attempt",
            )
        except Exception as error:
            result["ending_source_error"] = exception_summary(error)
            result["status"] = "RESILIENT_WRAPPER_FAILURE_UNQUALIFIED"
        try:
            result["runtime_resources_after"] = resource_status()
        except Exception as error:
            result["ending_resource_error"] = exception_summary(error)
            result["status"] = "RESILIENT_WRAPPER_FAILURE_UNQUALIFIED"
        result["completed_utc"] = datetime.now(UTC).isoformat()
        result["wrapper_elapsed_monotonic_seconds"] = time.monotonic() - started
        payload = json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False) + "\n"
        require(len(payload.encode()) <= 2_000_000, "Independent receipt output bound")
        writer.write(payload)
        writer.flush()
        os.fsync(writer.fileno())
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--directory", type=Path, required=True)
    parser.add_argument("--seconds", type=float, default=86400)
    parser.add_argument("--period", type=float, default=300)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = run_observer(
        args.directory, seconds=args.seconds, period=args.period, output=args.output
    )
    print(
        json.dumps(
            {
                key: result[key]
                for key in (
                    "status",
                    "delegate_started",
                    "delegate_returned",
                    "owned_sampler_directory_established",
                    "actual_24h_capacity_accepted",
                    "actual_24h_quality_accepted",
                )
            }
        )
    )
    if result["status"] != "RESILIENT_WRAPPER_ENGINEERING_RETURN_ONLY":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
