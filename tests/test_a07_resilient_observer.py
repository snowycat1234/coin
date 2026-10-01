"""Independent receipts survive synthetic sampler faults without touching live collectors."""

import errno
import importlib.util
import json
import sys
import tempfile
from pathlib import Path

import pytest

from quant.paths import ROOT, STATE

SPEC = importlib.util.spec_from_file_location(
    "isolated_resilient_a07_tests", ROOT / "scripts/observe_a07_resources_resilient.py"
)
wrapper = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = wrapper
SPEC.loader.exec_module(wrapper)


def write_json(path, value):
    path.write_text(json.dumps(value, allow_nan=False), encoding="utf-8")


@pytest.fixture
def fixture(monkeypatch):
    with tempfile.TemporaryDirectory(prefix="a07-resilient-", dir=STATE) as native:
        root = Path(native)
        monkeypatch.setattr(wrapper, "ROOT", root)  # Only our isolated wrapper module.
        sources = {}
        for name in wrapper.BOUND_FILES:
            path = root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("EXPLICIT SYNTHETIC ENGINEERING SOURCE " + name)
            sources[name] = wrapper.digest(path, 4_000_000)["sha256"]
        receipt = root / wrapper.ACCEPTANCE
        receipt.parent.mkdir(parents=True)
        write_json(
            receipt,
            {
                "status": "A07_RESOURCE_OBSERVER_SHORT_ENGINEERING_PASS",
                "source_hashes": sources,
                "verified_prior_files": {},
            },
        )
        (root / "reports/generated").mkdir()
        yield {
            "root": root,
            "folder": root / "reports/generated/new-window",
            "output": root / "reports/independent.json",
            "acceptance_sha": wrapper.digest(receipt, 2_000_000)["sha256"],
            "calls": [],
            "original_artifacts": {},
        }


def delegate_for(fixture, *, outcome="success"):
    def delegate():
        folder = fixture["folder"]
        fixture["calls"].append(sys.argv.copy())
        assert fixture["output"].is_file() and fixture["output"].read_bytes() == b""
        assert not folder.exists()  # Wrapper never pre-creates or enters the sampler directory.
        if outcome == "initial":
            raise RuntimeError("SYNTHETIC initial disk.check failure")
        if outcome == "race":
            folder.mkdir()
            (folder / "REPORT.json").write_text("FOREIGN OWNED WINDOW")
            raise FileExistsError("SYNTHETIC directory race before original mkdir")
        folder.mkdir()
        # Match the frozen main's after-successful-mkdir ownership marker locals.
        started, head, count, bytes_written = 0.0, "0" * 64, 0, 0
        assert started == 0 and head and count == bytes_written == 0
        sample = folder / "samples.jsonl"
        sample.write_bytes(b"EXPLICIT_SYNTHETIC_PARTIAL_SAMPLE\n")
        fixture["original_artifacts"]["samples.jsonl"] = sample.read_bytes()
        if outcome == "mid":
            raise RuntimeError("SYNTHETIC mid status() failure")
        if outcome == "final":
            raise RuntimeError("SYNTHETIC final disk.check failure")
        if outcome == "os_error":
            raise OSError("SYNTHETIC disk IO failure")
        if outcome == "interrupt":
            raise KeyboardInterrupt("SYNTHETIC interruption")
        if outcome == "oversize_sample":
            with sample.open("wb") as writer:
                writer.truncate(10_000_001)
        status = (
            "FAILED_RESOURCE_WINDOW_NOT_ACCEPTED"
            if outcome == "old_failed"
            else ("REAL_SHORT_SAMPLED_RESOURCE_WINDOW_COMPLETE")
        )
        old_report = folder / "REPORT.json"
        if outcome == "oversize_report":
            with old_report.open("wb") as writer:
                writer.truncate(2_000_001)
        else:
            write_json(
                old_report,
                {
                    "status": status,
                    "requested_seconds": 60,
                    "period_seconds": 10,
                    "actual_24h_capacity_accepted": False,
                    "actual_24h_quality_accepted": False,
                },
            )
        fixture["original_artifacts"] = {
            name: (folder / name).read_bytes() for name in ("REPORT.json", "samples.jsonl")
        }
        if outcome == "old_failed":
            raise SystemExit(1)
        if outcome == "source_changed":
            (fixture["root"] / wrapper.OLD_SCRIPT).write_text("MODIFIED SYNTHETIC SOURCE")

    return delegate


def run(fixture, delegate, **kwargs):
    original_argv = sys.argv
    result = wrapper.run_observer(
        fixture["folder"],
        seconds=60,
        period=10,
        output=fixture["output"],
        expected_acceptance_sha=fixture["acceptance_sha"],
        fixture_delegate=delegate,
        **kwargs,
    )
    assert sys.argv is original_argv
    saved = json.loads(fixture["output"].read_text())
    assert saved == result
    assert all(
        result[key] is False
        for key in (
            "actual_24h_capacity_accepted",
            "actual_24h_quality_accepted",
            "alpha_eligible",
            "training_authorized",
            "exact_unsampled_peak_known",
        )
    )
    assert result["healthy_credit_seconds"] == result["collector_restarts"] == 0
    for name, original in fixture["original_artifacts"].items():
        assert (fixture["folder"] / name).read_bytes() == original
    return result


@pytest.mark.parametrize("phase", ["initial", "mid", "final"])
def test_runtime_failures_at_all_three_stages_keep_independent_unaccepted_receipt(fixture, phase):
    result = run(fixture, delegate_for(fixture, outcome=phase))
    assert result["status"] == "RESILIENT_WRAPPER_FAILURE_UNQUALIFIED"
    assert result["exception"]["type"] == "RuntimeError" and phase in result["exception"]["message"]
    assert result["delegate_started"] and not result["delegate_returned"]
    assert result["owned_sampler_directory_established"] is (phase != "initial")
    if phase == "initial":
        assert not fixture["folder"].exists() and not result["sampler_artifacts"]
    else:
        assert result["sampler_artifacts"]["REPORT.json"]["status"] == "NOT_AVAILABLE"
        assert (
            result["sampler_artifacts"]["samples.jsonl"]["sha256"]
            == wrapper.digest(fixture["folder"] / "samples.jsonl", 10_000_000)["sha256"]
        )


@pytest.mark.parametrize(
    "outcome,kind",
    [("old_failed", "SystemExit"), ("os_error", "OSError"), ("interrupt", "KeyboardInterrupt")],
)
def test_old_failed_report_systemexit_oserror_and_interruption_are_preserved(
    fixture, outcome, kind
):
    result = run(fixture, delegate_for(fixture, outcome=outcome))
    assert result["exception"]["type"] == kind and result["owned_sampler_directory_established"]
    assert result["status"] == "RESILIENT_WRAPPER_FAILURE_UNQUALIFIED"
    if outcome == "old_failed":
        assert result["exception"]["exit_code"] == 1
        assert result["sampler_artifacts"]["REPORT.json"]["terminal_status"] == (
            "FAILED_RESOURCE_WINDOW_NOT_ACCEPTED"
        )


def test_success_delegates_exact_old_arguments_and_only_yields_wrapper_engineering_result(fixture):
    result = run(fixture, delegate_for(fixture))
    assert result["status"] == "RESILIENT_WRAPPER_ENGINEERING_RETURN_ONLY"
    assert fixture["calls"] == [
        [
            str(fixture["root"] / wrapper.OLD_SCRIPT),
            "--directory",
            str(fixture["folder"]),
            "--seconds",
            "60",
            "--period",
            "10",
        ]
    ]
    assert result["source_binding_before"] == result["source_binding_after"]
    assert result["wrapper_source_before"] == result["wrapper_source_after"]
    assert result["runtime_resources_before"]["ram_limit_bytes"] <= 5_000_000_000


def test_old_window_and_directory_race_are_never_read_overwritten_or_attributed(fixture):
    result = run(fixture, delegate_for(fixture, outcome="race"))
    assert result["status"] == "RESILIENT_WRAPPER_FAILURE_UNQUALIFIED"
    assert not result["owned_sampler_directory_established"] and not result["sampler_artifacts"]
    assert (fixture["folder"] / "REPORT.json").read_text() == "FOREIGN OWNED WINDOW"


def test_already_existing_directory_never_calls_sampler_and_old_files_stay_byte_identical(fixture):
    fixture["folder"].mkdir()
    (fixture["folder"] / "REPORT.json").write_bytes(b"EXISTING OWNED REPORT")
    result = run(fixture, delegate_for(fixture))
    assert not fixture["calls"] and not result["sampler_artifacts"]
    assert (fixture["folder"] / "REPORT.json").read_bytes() == b"EXISTING OWNED REPORT"


def test_output_collision_preserves_existing_receipt_and_never_delegates(fixture):
    fixture["output"].write_bytes(b"EXISTING INDEPENDENT RECEIPT")
    with pytest.raises(FileExistsError):
        run(fixture, delegate_for(fixture))
    assert (
        fixture["output"].read_bytes() == b"EXISTING INDEPENDENT RECEIPT" and not fixture["calls"]
    )


@pytest.mark.parametrize("escape", ["outside_reports", "inside_window"])
def test_output_path_escape_or_sampler_directory_output_is_refused_before_any_write(
    fixture, escape
):
    output = (
        fixture["root"] / "outside.json"
        if escape == "outside_reports"
        else (fixture["folder"] / "own.json")
    )
    with pytest.raises(ValueError, match="Independent"):
        wrapper.run_observer(
            fixture["folder"],
            seconds=60,
            period=10,
            output=output,
            expected_acceptance_sha=fixture["acceptance_sha"],
            fixture_delegate=delegate_for(fixture),
        )
    assert not output.exists() and not fixture["calls"]


@pytest.mark.parametrize("target", ["source", "acceptance"])
def test_frozen_source_or_receipt_mismatch_saves_failure_and_never_delegates(fixture, target):
    changed = fixture["root"] / (wrapper.OLD_SCRIPT if target == "source" else wrapper.ACCEPTANCE)
    changed.write_text("MODIFIED ENGINEERING FIXTURE")
    result = run(fixture, delegate_for(fixture))
    assert result["status"] == "RESILIENT_WRAPPER_FAILURE_UNQUALIFIED" and not fixture["calls"]
    assert result["exception"]["phase"] == "PREPARATION"


@pytest.mark.parametrize("outcome", ["oversize_sample", "oversize_report"])
def test_oversized_artifacts_are_bounded_preserved_and_cannot_claim_success(fixture, outcome):
    result = run(fixture, delegate_for(fixture, outcome=outcome))
    assert result["status"] == "RESILIENT_WRAPPER_FAILURE_UNQUALIFIED"
    name = "samples.jsonl" if outcome == "oversize_sample" else "REPORT.json"
    assert name in result["artifact_capture_failures"]
    assert result["sampler_artifacts"][name]["status"] == "NOT_VERIFIED"


def test_source_change_during_delegate_cannot_claim_success(fixture):
    result = run(fixture, delegate_for(fixture, outcome="source_changed"))
    assert (
        result["delegate_returned"] and result["status"] == "RESILIENT_WRAPPER_FAILURE_UNQUALIFIED"
    )
    assert result["ending_source_error"] and not result["source_binding_after"]["matches_frozen"]


def test_exception_text_and_trace_are_bounded_without_serializing_local_data(fixture):
    def delegate():
        private_local = "DO_NOT_SERIALIZE_LOCAL_CONTENT"
        assert private_local
        raise RuntimeError("e" * 10000)

    result = run(fixture, delegate)
    assert len(result["exception"]["message"]) == 2048 and len(result["exception"]["frames"]) <= 8
    assert "DO_NOT_SERIALIZE_LOCAL_CONTENT" not in fixture["output"].read_text()


def test_nonfinite_schedule_is_structured_failure_not_a_second_json_serialization_error(fixture):
    result = wrapper.run_observer(
        fixture["folder"],
        seconds=float("nan"),
        period=10,
        output=fixture["output"],
        expected_acceptance_sha=fixture["acceptance_sha"],
        fixture_delegate=delegate_for(fixture),
    )
    assert result["status"] == "RESILIENT_WRAPPER_FAILURE_UNQUALIFIED"
    assert result["requested_seconds"] == "INVALID" and not fixture["calls"]
    assert json.loads(fixture["output"].read_text()) == result


def test_default_pinned_receipt_rejects_freshly_self_issued_fixture_acceptance(fixture):
    result = wrapper.run_observer(
        fixture["folder"], seconds=60, period=10, output=fixture["output"]
    )
    assert result["status"] == "RESILIENT_WRAPPER_FAILURE_UNQUALIFIED"
    assert not result["delegate_started"] and "acceptance SHA" in result["exception"]["message"]


def test_unpaired_fixture_hook_is_refused_without_creating_output(fixture):
    with pytest.raises(ValueError, match="Paired"):
        wrapper.run_observer(
            fixture["folder"],
            output=fixture["output"],
            expected_acceptance_sha=fixture["acceptance_sha"],
        )
    assert not fixture["output"].exists()


@pytest.mark.parametrize("operation", ["exists", "stat"])
@pytest.mark.parametrize("error_number", [errno.EACCES, errno.EIO])
def test_artifact_exists_and_stat_io_errors_keep_independent_receipt(
    fixture, monkeypatch, operation, error_number
):
    # Replace this isolated wrapper's Path alias only. No global pathlib class or
    # frozen module is patched, and the sole failing path is a native fixture.
    target = fixture["folder"] / "REPORT.json"

    class FaultPath(type(fixture["folder"])):
        def exists(self):
            if operation == "exists" and str(self) == str(target):
                raise OSError(error_number, "SYNTHETIC artifact exists IO failure")
            return super().exists()

        def stat(self, **kwargs):
            if operation == "stat" and str(self) == str(target):
                raise OSError(error_number, "SYNTHETIC artifact stat IO failure")
            return super().stat(**kwargs)

    monkeypatch.setattr(wrapper, "Path", FaultPath)
    result = run(fixture, delegate_for(fixture))
    assert (
        result["delegate_returned"] and result["status"] == "RESILIENT_WRAPPER_FAILURE_UNQUALIFIED"
    )
    artifact = result["sampler_artifacts"]["REPORT.json"]
    assert artifact["status"] == "NOT_VERIFIED" and artifact["error"]["type"] in {
        "PermissionError",
        "OSError",
    }
    assert result["sampler_artifacts"]["samples.jsonl"]["status"] == "READ_ONLY_HASHED"
    assert result["source_binding_after"]["matches_frozen"] and "ending_source_error" not in result


def test_artifact_capture_framework_error_keeps_receipt_and_is_not_source_corruption(
    fixture, monkeypatch
):
    def failed_capture(_):
        raise RuntimeError("SYNTHETIC unexpected capture framework failure")

    monkeypatch.setattr(wrapper, "capture_artifacts", failed_capture)
    result = run(fixture, delegate_for(fixture))
    assert result["status"] == "RESILIENT_WRAPPER_FAILURE_UNQUALIFIED"
    assert result["artifact_capture_framework_error"]["type"] == "RuntimeError"
    assert all(
        artifact["status"] == "NOT_VERIFIED" for artifact in result["sampler_artifacts"].values()
    )
    assert result["source_binding_after"]["matches_frozen"] and "ending_source_error" not in result
