"""Meaningful process identity, read-only SQL and sampled-window observer checks."""

import copy
import importlib.util
import json
import sqlite3
import sys
import tempfile
import time
from pathlib import Path

import pytest

from quant.paths import ROOT, STATE

SPEC = importlib.util.spec_from_file_location(
    "a07_resource_observer_tests", ROOT / "scripts/observe_a07_resources.py"
)
observer = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = observer
SPEC.loader.exec_module(observer)


def sample():
    return {"process": {"pid": 50, "start_ticks": 100, "cpu_ticks": 200},
            "checkpoint": {"session": "owned", "asof_us": 100,
                           "accepted_events": 10, "duplicate_events": 0,
                           "rejected_events": 0, "observed_monotonic_seconds": 30},
            "binding": {"mode": "live"}, "feature_bytes": 50, "feature_rows": 10,
            "manifest_files": 2, "audit_head_seq": 3}


def test_linux_process_stat_with_spaces_and_parentheses_uses_correct_cpu_and_start_fields():
    fields = ["S", *map(str, range(4, 53))]
    result = observer.parse_stat("50 (collect (quoted) name) " + " ".join(fields))
    assert result == {"start_ticks": 22, "cpu_ticks": 29}
    with pytest.raises(ValueError):
        observer.parse_stat("50 (short) S 4 5")


@pytest.mark.parametrize("change", ["pid_reuse", "session", "binding", "cpu", "counter"])
def test_changed_process_session_source_or_reversed_counters_cannot_splice_windows(change):
    before, after = sample(), sample()
    if change == "pid_reuse":
        after["process"]["start_ticks"] += 1
    elif change == "session":
        after["checkpoint"]["session"] = "different"
    elif change == "binding":
        after["binding"]["mode"] = "engineering"
    elif change == "cpu":
        after["process"]["cpu_ticks"] -= 1
    else:
        after["checkpoint"]["accepted_events"] -= 1
    with pytest.raises(ValueError):
        observer.same_window(before, after)
    observer.same_window(before, copy.deepcopy(before))


def test_raw_inventory_is_explicitly_sampled_and_refuses_external_symlinks():
    # A rejected external link must never enter ROOT, even briefly: live writers
    # enforce the whole-project disk guard independently of this test process.
    with tempfile.TemporaryDirectory(prefix="a07-observer-link-", dir=STATE) as native:
        folder = Path(native)
        (folder / "segment.gz").write_bytes(b"12345")
        result = observer.raw_inventory(folder)
        assert result["sampled_bytes"] == 5 and result["entries_seen"] == 1
        assert not result["atomic_snapshot"] and not result["exact_unsampled_peak_known"]
        link = folder / "external"
        link.symlink_to(STATE, target_is_directory=True)
        try:
            with pytest.raises(ValueError, match="symlink"):
                observer.raw_inventory(folder)
        finally:
            link.unlink()


def test_inventory_budget_exhaustion_is_unknown_and_never_zero_or_a_complete_peak(monkeypatch):
    with tempfile.TemporaryDirectory(prefix="a07-observer-budget-", dir=STATE) as native:
        folder = Path(native)
        for name in ("a.gz", "b.gz"):
            (folder / name).write_bytes(b"12345")
        ticks = iter((0, 0, 11, 11))
        monkeypatch.setattr(observer.time, "monotonic", lambda: next(ticks))
        result = observer.raw_inventory(folder)
        assert result["status"] == "BUDGET_EXCEEDED_UNAVAILABLE"
        assert result["sampled_bytes"] is None
        assert result["partial_known_bytes_not_a_sample"] == 5
        assert not result["atomic_snapshot"] and not result["exact_unsampled_peak_known"]


@pytest.mark.parametrize("stale", [False, True])
def test_snapshot_uses_real_sqlite_readonly_and_releases_before_inventory(monkeypatch, stale):
    with tempfile.TemporaryDirectory(prefix="a07-observer-", dir=STATE) as native:
        monkeypatch.setattr(observer, "ROOT", Path(native))
        (Path(native) / "data").mkdir()
        with tempfile.TemporaryDirectory(prefix="a07-observer-", dir=Path(native) / "data") as data:
            database, store = Path(native) / "source.sqlite3", Path(data)
            (store / "raw").mkdir()
            (store / "raw/segment.gz").write_bytes(b"12345")
            with sqlite3.connect(database) as writer:
                writer.executescript("CREATE TABLE state(key TEXT,value TEXT);"
                                     "CREATE TABLE manifests(bytes INTEGER,rows INTEGER);"
                                     "CREATE TABLE audit(seq INTEGER,sha256 TEXT);")
                binding = {"mode": "live", "store": str(store)}
                checkpoint = sample()["checkpoint"]
                checkpoint.update(mode="live", connected=True,
                                  asof_us=int(time.time() * 1e6) - (20_000_000 if stale else 0))
                writer.executemany("INSERT INTO state VALUES(?,?)", [
                    ("binding", json.dumps(binding)), ("checkpoint", json.dumps(checkpoint)),
                ])
                writer.execute("INSERT INTO manifests VALUES(50,10)")
                writer.execute("INSERT INTO audit VALUES(3,?)", ("a" * 64,))
            original_sha = observer.sha(database)
            process = {**sample()["process"], "sampled_monotonic_seconds": time.monotonic(),
                       "rss_bytes": 1000, "lifetime_rss_hwm_bytes": 2000}
            monkeypatch.setattr(observer, "process", lambda _: copy.deepcopy(process))
            monkeypatch.setattr(observer, "status", lambda: {"ram_current_bytes": 1000})
            original_inventory = observer.raw_inventory

            def inventory(path):
                # Under DELETE journaling, an open SQL reader would block this writer.
                with sqlite3.connect(database, timeout=0.01) as writer:
                    writer.execute("BEGIN EXCLUSIVE")
                    writer.rollback()
                return original_inventory(path)

            monkeypatch.setattr(observer, "raw_inventory", inventory)
            if stale:
                with pytest.raises(ValueError, match="Stale"):
                    observer.snapshot(50, database=database, store=store)
            else:
                result = observer.snapshot(50, database=database, store=store)
                assert result["sql_released_before_inventory"]
                assert result["feature_bytes"] == 50 and result["feature_rows"] == 10
                assert result["raw_inventory"]["sampled_bytes"] == 5
                assert result["native_files_sampled_bytes"][database.name] > 0
            assert observer.sha(database) == original_sha


def test_full_requested_span_starts_after_first_snapshot_and_not_before_its_setup(monkeypatch):
    with tempfile.TemporaryDirectory(prefix="a07-observer-clock-",
                                     dir=STATE) as native:
        fixture_root = Path(native)
        data = fixture_root / "reports/generated"
        data.mkdir(parents=True)
        for name in observer.BOUND_FILES:
            path = fixture_root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("EXPLICIT ENGINEERING TEST FIXTURE ONLY\n")
        prior_path = fixture_root / "reports/A07_MICROSTRUCTURE_ACCEPTANCE.json"
        prior_path.write_text(json.dumps({
            "status": "DATA_ENGINEERING_SHORT_ACCEPTANCE_PASS",
            "source_hashes": {"src/quant/microstructure.py": observer.sha(
                fixture_root / "src/quant/microstructure.py"
            )},
        }))
        monkeypatch.setattr(observer, "ROOT", fixture_root)
        clock = [0.0]

        class ClockEvent:
            def is_set(self):
                return False

            def wait(self, seconds):
                clock[0] += seconds
                return False

        def snapshot(_):
            clock[0] += 2  # Setup/snapshot time cannot shorten a real requested span.
            row = sample()
            row["process"].update(sampled_monotonic_seconds=clock[0],
                                  cpu_ticks=int(100 * clock[0]), rss_bytes=1000,
                                  lifetime_rss_hwm_bytes=2000)
            row["binding"]["implementation_sha256"] = observer.sha(
                fixture_root / "src/quant/microstructure.py"
            )
            row.update(raw_inventory={"sampled_bytes": 50}, native_files_sampled_bytes={"db": 50},
                       global_vhd_sampled_bytes=50, aggregate_ram={"ram_current_bytes": 1000})
            return row

        monkeypatch.setattr(observer.time, "monotonic", lambda: clock[0])
        monkeypatch.setattr(observer, "Event", ClockEvent)
        monkeypatch.setattr(observer.signal, "signal", lambda *_: None)
        monkeypatch.setattr(observer, "find_collector", lambda: 50)
        monkeypatch.setattr(observer, "snapshot", snapshot)
        monkeypatch.setattr(observer.disk, "check", lambda **_: {"status": "TEST_FIXTURE"})
        monkeypatch.setattr(sys, "argv", ["observe_a07_resources.py", "--directory",
                                        str(Path(data) / "new-window"), "--seconds", "10",
                                        "--period", "5"])
        observer.main()
        result = json.loads((Path(data) / "new-window/REPORT.json").read_text())
        assert result["first"]["elapsed_monotonic_seconds"] == 2
        assert result["measured_elapsed_seconds"] >= 10
        assert result["samples"] == 3
        assert not result["quality_accepted"] and not result["actual_24h_capacity_accepted"]
