"""Pure resource/admission tests; no historical wallet or market replay."""
from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import patch

import run_guard_cases as runner


class RunnerAdmissionTests(unittest.TestCase):
    def test_exact_published_eleven_case_binding(self):
        manifest = runner.verify_published_policy()
        self.assertEqual(len(manifest["cases"]), 11)
        self.assertEqual({row["case_id"] for row in manifest["cases"]}, runner.CASE_SET)
        self.assertEqual(runner.sha(runner.POLICY / "FREEZE.json"),
                         runner.POLICY_FREEZE_SHA256)

    def test_read_only_input_preflight(self):
        import sys
        sys.path.insert(0, str(runner.POLICY))
        from preflight_run_plan import check
        proof = check(runner.POLICY / "RUN_MANIFEST.json", runner.WORKSPACE)
        self.assertEqual(set(proof["case_ids"]), runner.CASE_SET)
        self.assertEqual(proof["wallets_started"], 0)
        runner.require_input_preflight(proof)

    def test_preflight_disk_false_fails_before_state_creation(self):
        report = {"status": "INPUTS_BOUND_RESOURCE_RECHECK_REQUIRED_BEFORE_GO",
            "case_ids": sorted(runner.CASE_SET), "disk_preflight_pass": False,
            "wallets_started": 0}
        with self.assertRaisesRegex(RuntimeError, "disk preflight"):
            runner.require_input_preflight(report)

    def test_full_calendar_unfilled_protection_is_not_complete_paid(self):
        incomplete = {"completed_minutes": 525600,
            "completion": "NOT_EVALUABLE_PROTECTIVE_EXIT_UNFILLED_AT_HORIZON",
            "terminal_cash_realized": False}
        self.assertEqual(runner.classify_result(incomplete, 525600),
            ("FULL_CALENDAR_NOT_PAID_OR_NOT_EVALUABLE_GUARD", True, False))
        complete = {"completed_minutes": 525600,
            "completion": "COMPLETE_CONDITIONAL_ACCOUNT", "terminal_cash_realized": True}
        self.assertEqual(runner.classify_result(complete, 525600),
            ("COMPLETE_PAID_FLAT_GUARD_SHARED_NATIVE", True, True))
        incomplete["completed_minutes"] -= 1
        self.assertEqual(runner.classify_result(incomplete, 525600),
            ("STOP_PARTIAL_GUARD_SHARED_NATIVE", False, False))

    def test_final_pointer_must_equal_live_state_and_snapshot_bytes(self):
        with tempfile.TemporaryDirectory() as directory:
            recovery = Path(directory)
            (recovery / "STATE.json.gz").write_bytes(b"synthetic checkpoint bytes")
            sim = SimpleNamespace(rows_written=5, cursor=300_000_000, stop=None,
                                  state_hash=lambda: "actual-state-hash")
            binding = {"case_id": "synthetic"}
            pointer = {"binding": binding, "completed_minutes": 5,
                "cursor": 300_000_000, "stop": None, "state_hash": "actual-state-hash",
                "chunks": [{"rows": 5}], "snapshot_path": "STATE.json.gz",
                "snapshot_SHA256": runner.sha(recovery / "STATE.json.gz")}
            summary = {"completed_minutes": 5, "stop_us": None}
            runner.verify_final_pointer(pointer, sim, summary, binding, recovery)
            for key, wrong in [("state_hash", "wrong"), ("completed_minutes", 4),
                               ("cursor", 4), ("snapshot_SHA256", "0" * 64)]:
                changed = pointer | {key: wrong}
                with self.subTest(key=key), self.assertRaisesRegex(ValueError, "checkpoint pointer differs"):
                    runner.verify_final_pointer(changed, sim, summary, binding, recovery)

    def test_transport_ports_load_all_three_calendars_without_wallet(self):
        for year, expected_events, expected_days in [(2023, 5475, 365),
                                                      (2024, 5490, 366),
                                                      (2025, 5475, 365)]:
            with self.subTest(year=year):
                port, window, cls = runner.load_port(year)
                self.assertEqual(len(window["events"]), expected_events)
                self.assertEqual((window["end"] - window["start"]) // runner.DAY,
                                 expected_days)
                self.assertEqual(port.Closing.VERSION,
                                 "conditional_btc_anchored_quantity_grid_sensitivity_v1")
                self.assertIn("isolated_half_equity", cls.VERSION)

    def test_2024_window_drift_rejected_before_import(self):
        original = runner.sha
        def altered(path):
            if str(path).endswith("window_2024.py"):
                return "0" * 64
            return original(path)
        with patch.object(runner, "sha", side_effect=altered):
            with self.assertRaisesRegex(ValueError, "2024 window bytes differ"):
                runner.load_port(2024)
            with self.assertRaisesRegex(ValueError, "transport/window adapter bytes changed"):
                runner.verify_published_policy()

    def test_port_manifest_drift_rejected_before_import(self):
        original = runner.sha
        def altered(path):
            if str(path).endswith("LOCAL_CODE_MANIFEST_2025.json"):
                return "0" * 64
            return original(path)
        with patch.object(runner, "sha", side_effect=altered):
            with self.assertRaisesRegex(ValueError, "port manifest bytes differ"):
                runner.load_port(2025)
            with self.assertRaisesRegex(ValueError, "transport/window adapter bytes changed"):
                runner.verify_published_policy()

    def test_python_optimization_rejected_before_month_checks(self):
        runner.require_assertions_enabled(0)
        with self.assertRaisesRegex(RuntimeError, "optimization disables"):
            runner.require_assertions_enabled(1)

    def test_resource_admission_good_two_distinct_cpus(self):
        mem = {"MemTotal": 10_000_000_000, "MemAvailable": 7_000_000_000,
               "SwapTotal": 0, "SwapFree": 0, "host_used": 3_000_000_000,
               "active_swaps": 0}
        with patch.object(runner, "memory_observation", return_value=mem), \
             patch.object(runner.shutil, "disk_usage", return_value=type("Disk", (), {"free": 20_000_000_000})()), \
             patch.object(runner.os, "sched_getaffinity", return_value={4, 6}):
            proof = runner.resource_admission(Path("/tmp"), 1)
        self.assertEqual(proof["allowed_cpus"], [4, 6])

    def test_resource_admission_rejects_swap_host_disk_and_cpu(self):
        base = {"MemTotal": 10_000_000_000, "MemAvailable": 7_000_000_000,
                "SwapTotal": 0, "SwapFree": 0, "host_used": 3_000_000_000,
                "active_swaps": 0}
        for mutation, free, cpus in [
            ({"SwapTotal": 1}, 20_000_000_000, {0, 1}),
            ({"host_used": 6_500_000_001}, 20_000_000_000, {0, 1}),
            ({"cgroup_limit_verified": True, "cgroup_memory_max": 4_000_000_000,
              "cgroup_memory_current": 2_500_000_000}, 20_000_000_000, {0, 1}),
            ({"cgroup_swap_current": 1}, 20_000_000_000, {0, 1}),
            ({}, 16_000_000_000, {0, 1}),
            ({}, 20_000_000_000, {0}),
        ]:
            with self.subTest(mutation=mutation, free=free, cpus=cpus):
                with patch.object(runner, "memory_observation", return_value=base | mutation), \
                     patch.object(runner.shutil, "disk_usage", return_value=type("Disk", (), {"free": free})()), \
                     patch.object(runner.os, "sched_getaffinity", return_value=cpus):
                    with self.assertRaises(RuntimeError):
                        runner.resource_admission(Path("/tmp"), 0)

    def test_second_admission_reserves_full_unallocated_first_worker(self):
        mem = {"MemTotal": 10_000_000_000, "MemAvailable": 4_500_000_000,
               "SwapTotal": 0, "SwapFree": 0, "host_used": 5_500_000_000,
               "active_swaps": 0}
        disk = type("Disk", (), {"free": 20_000_000_000})()
        with patch.object(runner, "memory_observation", return_value=mem), \
             patch.object(runner.shutil, "disk_usage", return_value=disk), \
             patch.object(runner.os, "sched_getaffinity", return_value={0, 1}):
            runner.resource_admission(Path("/tmp"), 0)
            with self.assertRaisesRegex(RuntimeError, "two-worker commitment"):
                runner.resource_admission(Path("/tmp"), 1)
        mem["host_used"] = 2_000_000_000
        one_case_free = runner.DISK_RESERVE + runner.CASE_LIMIT + 2 * 63_204_609 + 1_048_576
        disk = type("Disk", (), {"free": one_case_free})()
        with patch.object(runner, "memory_observation", return_value=mem), \
             patch.object(runner.shutil, "disk_usage", return_value=disk), \
             patch.object(runner.os, "sched_getaffinity", return_value={0, 1}):
            runner.resource_admission(Path("/tmp"), 0)
            with self.assertRaisesRegex(RuntimeError, "disk reserve"):
                runner.resource_admission(Path("/tmp"), 1)

    def test_missing_parent_go_cannot_create_state(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "fresh"
            with self.assertRaisesRegex(RuntimeError, "parent GO"):
                runner.controller(root, runner.verify_published_policy(), go=False)
            self.assertFalse(root.exists())

    def test_state_root_cannot_point_at_an_original_wallet(self):
        with self.assertRaisesRegex(ValueError, "under this runner"):
            runner.validate_state_root(runner.WORKSPACE /
                "coin_expanded_coverage_20261013/wallets/STATIC50")

    def test_direct_worker_requires_controller_binding_and_launcher(self):
        with self.assertRaisesRegex(RuntimeError, "GO binding missing"):
            runner.worker({"case_id": "Y2024_STATIC50"}, runner.HERE / "state_synthetic_not_created")
        with tempfile.TemporaryDirectory(dir=runner.HERE, prefix="state_synthetic_") as directory:
            root = Path(directory)
            nonce = "synthetic-not-a-real-launch"
            runner.exclusive_json(root / "RUN_BINDING.json", {"parent_go": True,
                "run_nonce": nonce, "case_ids": sorted(runner.CASE_SET),
                "policy_commit": runner.POLICY_COMMIT,
                "policy_freeze_SHA256": runner.POLICY_FREEZE_SHA256,
                "run_manifest_SHA256": runner.sha(runner.POLICY / "RUN_MANIFEST.json"),
                "runner_SHA256": runner.sha(Path(runner.__file__))})
            with patch.dict(runner.os.environ, {"COIN_GUARD_RUN_NONCE": "wrong",
                                                "COIN_GUARD_BOUNDED": ""}):
                with self.assertRaisesRegex(RuntimeError, "run nonce differs"):
                    runner.worker({"case_id": "Y2024_STATIC50"}, root)
            with patch.dict(runner.os.environ, {"COIN_GUARD_RUN_NONCE": nonce,
                                                "COIN_GUARD_BOUNDED": ""}):
                with self.assertRaisesRegex(RuntimeError, "bounded controller"):
                    runner.worker({"case_id": "Y2024_STATIC50"}, root)

    def test_worker_check_only_cli_is_rejected_before_source(self):
        proc = subprocess.run([sys.executable, str(Path(runner.__file__)),
            "--worker-case", "Y2024_STATIC50", "--check-only"],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        self.assertEqual(proc.returncode, 2)
        self.assertIn("cannot be check-only", proc.stderr)

    def test_exclusive_output_never_overwrites(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "receipt.json"
            runner.exclusive_json(path, {"first": 1})
            with self.assertRaises(FileExistsError):
                runner.exclusive_json(path, {"second": 2})
            self.assertEqual(json.loads(path.read_text()), {"first": 1})


if __name__ == "__main__":
    unittest.main(verbosity=2)
