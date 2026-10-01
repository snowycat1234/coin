"""Isolated native fixtures; never alter the live ROOT, raw store or SQLite."""

import importlib.util
import json
import sqlite3
import stat
import sys
import tempfile
from pathlib import Path

import pytest

from quant.paths import ROOT, STATE

SPEC = importlib.util.spec_from_file_location(
    "a07_raw_retention_tests_isolated", ROOT / "scripts/audit_a07_raw_retention.py"
)
qa = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = qa
SPEC.loader.exec_module(qa)


@pytest.fixture
def raw():
    with tempfile.TemporaryDirectory(prefix="a07-raw-qa-", dir=STATE) as native:
        folder = Path(native) / "raw"
        folder.mkdir()
        yield folder


def write(folder, stamp, suffix="deadbeef", payload=b"not a complete gzip tail"):
    path = folder / f"raw-{stamp}-{suffix}.jsonl.gz"
    path.write_bytes(payload)
    return path


@pytest.mark.parametrize("old_age,expected", [
    (10, "WITHIN_24H_NAMED_START_ENVELOPE_OBSERVED"),
    (86400, "WITHIN_24H_NAMED_START_ENVELOPE_OBSERVED"),
    (86401, "OUTSIDE_24H_NAMED_START_ENVELOPE_OBSERVED"),
])
def test_filename_receipt_ages_include_boundary_not_mtime_and_never_credit_health(
    raw, monkeypatch, old_age, expected
):
    now = 1_800_000_000_000_000
    write(raw, now - old_age * 1_000_000, payload=b"12345")
    write(raw, now - 1_000_000, "aabbccdd", b"12")
    monkeypatch.setattr(qa.time, "time_ns", lambda: now * 1000)
    result = qa.inventory_raw(raw)
    assert result["age_envelope_observation"] == expected
    assert result["sampled_bytes"] == 7 and result["sampled_files"] == 2
    assert result["oldest_named_start_age_seconds_at_scan_end"] == old_age
    assert result["newest_named_start_age_seconds_at_scan_end"] == 1
    assert not result["gzip_closure_checked"] and not result["atomic_snapshot"]
    assert not result["raw_event_completeness_certified"]
    assert result["pending_unsealed_tail"].startswith("unknown")


def test_empty_store_is_no_coverage_and_future_filename_is_anomaly(raw, monkeypatch):
    now = 1_800_000_000_000_000
    monkeypatch.setattr(qa.time, "time_ns", lambda: now * 1000)
    empty = qa.inventory_raw(raw)
    assert empty["age_envelope_observation"] == "EMPTY_OBSERVED_NO_RETENTION_COVERAGE"
    assert empty["oldest_named_start_age_seconds_at_scan_end"] is None
    write(raw, now + 1_000_000)
    result = qa.inventory_raw(raw)
    assert result["age_envelope_observation"] == "FUTURE_NAMED_RECEIPT_OBSERVED"
    assert result["raw_byte_cap_observation"] == "NOT_ESTABLISHED_FUTURE_NAMED_TIME"


@pytest.mark.parametrize("bad", ["symlink", "directory", "format", "timestamp", "path_alias"])
def test_untrusted_paths_entries_and_names_are_rejected_in_native_fixture(raw, bad):
    if bad == "symlink":
        (raw / "external").symlink_to(STATE)
    elif bad == "directory":
        (raw / "nested").mkdir()
    elif bad == "format":
        (raw / "unknown.gz").write_bytes(b"123")
    elif bad == "timestamp":
        write(raw, 999_999_999_999_999_999)
    else:
        alias = raw.parent / "alias"
        alias.symlink_to(raw, target_is_directory=True)
        with pytest.raises(qa.Rejected, match="Symlink"):
            qa.inventory_raw(alias)
        return
    with pytest.raises(qa.Rejected):
        qa.inventory_raw(raw)


@pytest.mark.parametrize("budget", ["entries", "slow_final_entry"])
def test_budget_unknown_preserves_partial_bytes_without_complete_sample(raw, monkeypatch, budget):
    for index in range(3):
        write(raw, 1_800_000_000_000_000 + index, f"{index:08x}", b"12345")
    if budget == "entries":
        result = qa.inventory_raw(raw, max_entries=1)
        assert result["partial_known_bytes_not_a_complete_sample"] == 5
    else:
        ticks = iter((0, 0, 0, 0, 11))
        monkeypatch.setattr(qa.time, "monotonic", lambda: next(ticks))
        result = qa.inventory_raw(raw)
        assert result["partial_known_bytes_not_a_complete_sample"] == 15
    assert result["status"] == "UNKNOWN_BUDGET_EXCEEDED"
    assert result["sampled_bytes"] is None and result["sampled_files"] is None
    assert result["age_envelope_observation"] == "UNKNOWN_INCOMPLETE_INVENTORY"


def test_concurrent_raw_retirement_is_explicit_without_opening_or_zero_filling(raw, monkeypatch):
    class Gone:
        name = "raw-1800000000000000-deadbeef.jsonl.gz"

        def is_symlink(self):
            return False

        def stat(self, **kwargs):
            raise FileNotFoundError("legitimate concurrent retirement")

    class Scan:
        def __enter__(self):
            return iter([Gone()])

        def __exit__(self, *args):
            pass

    monkeypatch.setattr(qa.os, "scandir", lambda _: Scan())
    result = qa.inventory_raw(raw)
    assert result["concurrent_retired_or_missing_entries"] == 1
    assert result["sampled_files"] == 0
    assert result["age_envelope_observation"] == "EMPTY_OBSERVED_NO_RETENTION_COVERAGE"


@pytest.mark.parametrize("size,expected", [
    (4_000_000_000, "WITHIN_4GB_SAMPLED_METADATA"),
    (4_000_000_001, "EXCEEDS_4GB_SAMPLED_METADATA"),
])
def test_byte_cap_boundary_is_metadata_comparison_without_large_file_allocation(
    raw, monkeypatch, size, expected
):
    class Entry:
        name = "raw-1800000000000000-deadbeef.jsonl.gz"

        def is_symlink(self):
            return False

        def stat(self, **kwargs):
            class Metadata:
                st_mode = stat.S_IFREG
                st_size = size

            return Metadata()

    class Scan:
        def __enter__(self):
            return iter([Entry()])

        def __exit__(self, *args):
            pass

    monkeypatch.setattr(qa.os, "scandir", lambda _: Scan())
    monkeypatch.setattr(qa.time, "time_ns", lambda: 1_800_000_000_000_000_000)
    result = qa.inventory_raw(raw)
    assert result["raw_byte_cap_observation"] == expected
    assert result["sampled_bytes"] == size


@pytest.fixture
def evidence(monkeypatch):
    with tempfile.TemporaryDirectory(prefix="a07-raw-source-", dir=STATE) as native:
        base = Path(native)
        monkeypatch.setattr(qa, "ROOT", base)
        store = base / "data/microstructure_v1"
        (store / "raw").mkdir(parents=True)
        source = base / "src/quant/microstructure.py"
        source.parent.mkdir(parents=True)
        source.write_text("EXPLICIT SYNTHETIC SOURCE FIXTURE ONLY\n")
        receipt = {"status": "DATA_ENGINEERING_SHORT_ACCEPTANCE_PASS",
                   "limits": {"raw_bytes": 4_000_000_000, "raw_retention_seconds": 86400},
                   "source_hashes": {"src/quant/microstructure.py": qa.sha(source)}}
        prior = base / qa.ACCEPTANCE
        prior.parent.mkdir()
        prior.write_text(json.dumps(receipt))
        monkeypatch.setattr(qa, "ACCEPTANCE_SHA", qa.sha(prior))
        database = base / "source.sqlite3"
        marker = store / ".microstructure-store.json"
        marker.write_text(json.dumps({"database": str(database), "mode": "live",
                                      "version": qa.VERSION}))
        stamp = qa.time.time_ns() // 1000
        binding = {"mode": "live", "version": qa.VERSION, "store": str(store),
                   "implementation_sha256": qa.sha(source)}
        checkpoint = {"mode": "live", "session": "0" * 32, "asof_us": stamp,
                      "connected": True, "accepted_events": 10, "duplicate_events": 0,
                      "rejected_events": 0, "observed_monotonic_seconds": 30}
        with sqlite3.connect(database) as writer:
            writer.executescript("CREATE TABLE state(key TEXT,value TEXT);"
                                 "CREATE TABLE audit(seq INTEGER,received_us INTEGER,kind TEXT,"
                                 "payload TEXT,sha256 TEXT);")
            writer.executemany("INSERT INTO state VALUES(?,?)", [
                ("binding", json.dumps(binding)), ("checkpoint", json.dumps(checkpoint)),
            ])
            writer.execute("INSERT INTO audit VALUES(1,?,'RAW_PRUNED',?,?)", (stamp, json.dumps({
                "count": 2, "bytes": 100, "oldest_us": stamp - 2 * qa.RETENTION_US,
                "latest_us": stamp - qa.RETENTION_US,
            }), "a" * 64))
        write(store / "raw", stamp)
        yield database, store, prior


def test_readonly_short_sql_released_before_inventory_and_no_raw_gzip_read(evidence, monkeypatch):
    database, store, _ = evidence
    before = qa.sha(database)
    original = qa.inventory_raw

    def inventory(path, **kwargs):
        with sqlite3.connect(database, timeout=0.01) as writer:
            writer.execute("BEGIN EXCLUSIVE")
            writer.rollback()
        return original(path, **kwargs)

    monkeypatch.setattr(qa, "inventory_raw", inventory)
    result = qa.audit_retention(database=database, store=store)
    assert result["status"] == "RAW_RETENTION_METADATA_OBSERVATION_COMPLETE"
    assert qa.sha(database) == before
    snapshot = result["source_snapshot"]
    assert snapshot["sql_released_before_inventory"] and snapshot["sql_read_seconds"] <= 5
    assert snapshot["raw_pruned_lifetime_summary"]["files"] == 2
    assert not snapshot["audit_chain_verified_here"]
    assert all(result[key] is False for key in (
        "actual_24h_capacity_accepted", "actual_24h_quality_accepted", "actual_14d_accepted",
        "actual_30d_accepted", "alpha_eligible", "training_authorized",
    ))
    assert result["healthy_time_credit_seconds"] == result["network_requests"] == 0


@pytest.mark.parametrize("changed", ["source", "acceptance", "marker", "binding"])
def test_source_marker_and_receipt_changes_fail_closed_before_inventory(
    evidence, monkeypatch, changed
):
    database, store, prior = evidence
    if changed == "source":
        (qa.ROOT / "src/quant/microstructure.py").write_text("changed\n")
    elif changed == "acceptance":
        prior.write_text("changed\n")
    elif changed == "marker":
        (store / ".microstructure-store.json").write_text("{}")
    else:
        with sqlite3.connect(database) as writer:
            saved = json.loads(writer.execute(
                "SELECT value FROM state WHERE key='binding'"
            ).fetchone()[0])
            saved["mode"] = "engineering"
            writer.execute("UPDATE state SET value=? WHERE key='binding'", (json.dumps(saved),))
    monkeypatch.setattr(qa, "inventory_raw", lambda *_a, **_k: pytest.fail("must not scan"))
    result = qa.audit_retention(database=database, store=store)
    assert result["status"] == "RAW_RETENTION_NOT_ESTABLISHED" and result["inventory"] is None


def test_source_change_during_scan_invalidates_observation_without_live_source_writes(
    evidence, monkeypatch
):
    database, store, _ = evidence
    original = qa.inventory_raw

    def inventory(*args, **kwargs):
        result = original(*args, **kwargs)
        (qa.ROOT / "src/quant/microstructure.py").write_text("changed fixture\n")
        return result

    monkeypatch.setattr(qa, "inventory_raw", inventory)
    result = qa.audit_retention(database=database, store=store)
    assert result["status"] == "RAW_RETENTION_NOT_ESTABLISHED"
    assert "Frozen source changed" in result["reason"]


def test_global_guard_runtimeerror_is_not_raw_expiry_or_raw_cap_proof(evidence, monkeypatch):
    database, store, _ = evidence
    output = qa.ROOT / "reports/result.json"
    original = qa.audit_retention
    monkeypatch.setattr(qa, "audit_retention", lambda: original(database=database, store=store))
    monkeypatch.setattr(qa, "status", lambda: {"ram_limit_bytes": 4_999_999_488, "swap_bytes": 0})

    def guard(**kwargs):
        raise RuntimeError("36 GB intake limit: preserve the 4 GB emergency buffer")

    monkeypatch.setattr(qa.disk, "check", guard)
    monkeypatch.setattr(sys, "argv", ["audit_a07_raw_retention.py", "--output", str(output)])
    qa.main()
    result = json.loads(output.read_text())
    assert result["status"] == "RAW_RETENTION_METADATA_OBSERVATION_COMPLETE"
    assert result["resource_guards"]["whole_project_and_vhd"]["error_type"] == "RuntimeError"
    assert not result["global_resource_constraints_accepted"]
    with pytest.raises(qa.Rejected, match="exclusive"):
        qa.main()
