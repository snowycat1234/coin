"""Small synthetic report tests: never imports a historical financial runner."""
from __future__ import annotations
import builtins
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import build_report as report


def saved_recovery(root: Path, arrays):
    import numpy as np
    root.mkdir()
    chunks = []
    for day, array in enumerate(arrays):
        path = root / (f"DAY_{day:04d}.npz")
        np.savez_compressed(path, minute_chunk=array)
        chunks.append({"path": path.name, "rows": len(array), "columns": 36,
                       "SHA256": report.sha(path)})
    pointer = {"completed_minutes": sum(len(a) for a in arrays), "chunks": chunks}
    (root / "POINTER.json").write_text(json.dumps(pointer))
    return root


def minute_array(n):
    import numpy as np
    data = np.zeros((n, 36), dtype=np.float64)
    data[:, 0] = 10000.0
    data[:, 34] = 0.5
    return data


def summary(n=1440, paid=True, quantity="0", status="ACTIVE"):
    return {"completed_minutes": n, "net_PnL": 100.0,
            "completion": "COMPLETE_CONDITIONAL_ACCOUNT", "account_status": status,
            "terminal_cash_realized": paid, "positions": {"X": {"quantity": quantity}}}


def permission(signal=1704153600000000, kind="SAME_DIRECTION_REENTRY_ALLOWED", new_sign=1):
    return {"kind": kind, "symbol": "X", "event_us": signal, "signal_us": signal,
            "trigger_us": signal - 2 * report.DAY, "flat_us": signal - report.DAY + 1,
            "stopped_sign": 1, "new_sign": new_sign, "target_quantity": str(new_sign),
            "actual_quantity": "0", "account_status": "ACTIVE"}


def opening(event, *, signal=None, before="0", after="1", delay=60000001, fill_id="f1"):
    return {"symbol": event["symbol"], "signal_us": event["signal_us"] if signal is None else signal,
            "event_us": event["signal_us"] + delay, "quantity_before": before, "quantity_after": after,
            "leg": "OPEN", "fill_id": fill_id}


class ReportSynthetic(unittest.TestCase):
    def synthetic_audit(self):
        go = {"parent_GO": True, "approved_stages": ["AUDIT"], "manifest_SHA256": "manifest",
              "state_locator": "synthetic/state", "run_binding_SHA256": "run",
              "controller_receipt_SHA256": "controller", "historical_controller_released": True}
        text = json.dumps(go, indent=2) + "\n"
        return {"stage": "AUDIT", "status": "ALL_OBSERVERS_FINISHED", "case_ids": list(report.CASE_IDS),
                "per_observer": {key: {} for key in report.CASE_IDS}, "unstarted_observer_ids": [],
                "financial_advances": 0, "historical_wallets_opened": 0, "observer_manifest_SHA256": "manifest",
                "postrun_GO_text": text, "postrun_GO_SHA256": hashlib.sha256(text.encode()).hexdigest()}

    def test_original_audit_go_bytes_survive_separate_report_authorization(self):
        audit = self.synthetic_audit()
        report.verify_audit_stage(audit, manifest_sha="manifest", run_binding_sha="run",
                                 controller_sha="controller", state_locator="synthetic/state")
        audit["postrun_GO_text"] += " "
        with self.assertRaisesRegex(ValueError, "bytes/hash"):
            report.verify_audit_stage(audit, manifest_sha="manifest", run_binding_sha="run",
                                     controller_sha="controller", state_locator="synthetic/state")

    def test_audit_stage_rejects_incomplete_population_and_wrong_binding(self):
        audit = self.synthetic_audit()
        with self.assertRaisesRegex(ValueError, "authorize"):
            report.verify_audit_stage(audit, manifest_sha="manifest", run_binding_sha="changed",
                                     controller_sha="controller", state_locator="synthetic/state")
        audit["case_ids"].pop()
        with self.assertRaisesRegex(ValueError, "full-population"):
            report.verify_audit_stage(audit, manifest_sha="manifest", run_binding_sha="run",
                                     controller_sha="controller", state_locator="synthetic/state")

    def test_import_never_loads_financial_modules(self):
        original = builtins.__import__
        forbidden = ("run_cases", "fine_account", "daily_reentry_policy", "protective_policy", "quant", "scripts")
        def guarded(name, *args, **kwargs):
            if any(name == prefix or name.startswith(prefix + ".") for prefix in forbidden):
                self.fail("Report imported a financial module: " + name)
            return original(name, *args, **kwargs)
        with patch("builtins.__import__", side_effect=guarded):
            spec = importlib.util.spec_from_file_location("synthetic_report_import", HERE / "build_report.py")
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
        self.assertEqual(module.CASE_IDS, report.CASE_IDS)

    def test_gate_blocks_before_inputs_or_outputs(self):
        with patch.object(report.gate, "verify_observer_go", side_effect=RuntimeError("synthetic no GO")), \
                patch.object(report, "read_json", side_effect=AssertionError("Input opened before GO")):
            with self.assertRaisesRegex(RuntimeError, "synthetic no GO"):
                report.main()

    def test_bounded_worker_gate_blocks_before_inputs(self):
        with patch.object(report.gate, "verify_observer_go", return_value=None), \
                patch.object(report.gate, "require_bounded_worker", side_effect=RuntimeError("unbounded")), \
                patch.object(report, "read_json", side_effect=AssertionError("Input opened before bounds")):
            with self.assertRaisesRegex(RuntimeError, "unbounded"):
                report.main()

    def test_paid_flat_requires_exact_inventory_and_official_result(self):
        self.assertTrue(report.censoring(summary(), 1440, official_result=True)["paid_flat"])
        self.assertFalse(report.censoring(summary(quantity="0.00000001"), 1440, official_result=True)["paid_flat"])
        partial = report.censoring(summary(), 1440, official_result=False)
        self.assertFalse(partial["full_calendar"])
        self.assertIsNone(partial["annual_paid_return"])

    def test_full_marked_is_separate_from_paid(self):
        marked = report.censoring(summary(paid=False, quantity="1"), 1440, official_result=True)
        self.assertEqual(marked["observation_class"], "FULL_MARKED")
        self.assertIsNone(marked["paid_cash_PnL_USDT"])

    def test_partial_halt_is_censored(self):
        row = report.censoring(summary(n=700, paid=False, quantity="1", status="BANKRUPT_HALT"),
                               1440, official_result=True)
        self.assertEqual(row["observation_class"], "PARTIAL_HALTED")
        self.assertFalse(row["full_calendar"])
        self.assertIsNone(row["annual_paid_return"])

    def test_contrast_annual_requires_both_full_paid(self):
        a = {"available": True, **report.censoring(summary(), 1440, official_result=True)}
        b = {"available": True, **report.censoring({**summary(), "net_PnL": 180.0}, 1440, official_result=True)}
        self.assertEqual(report.contrast(a, b)["paid_cash_PnL_delta_USDT"], 80.0)
        b.update(report.censoring(summary(paid=False, quantity="1"), 1440, official_result=True))
        self.assertIsNone(report.contrast(a, b)["annual_paid_return_delta"])
        b.update(report.censoring(summary(n=500), 1440, official_result=True))
        answer = report.contrast(a, b)
        self.assertTrue(answer["unequal_or_partial_horizon_needs_common_prefix"])
        self.assertTrue(all(value is None for value in answer["same_full_calendar_observed_deltas"].values()))
        self.assertIsNone(report.contrast(a, {"available": False})["annual_paid_return_delta"])

    def test_streaming_matched_prefix_and_tracking_gap(self):
        import numpy as np
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            a, b = minute_array(4), minute_array(2)
            a[:, 0] = [11000, 9900, 15000, 14000]
            b[:, 0] = [11000, 10000]
            a[:, 29] = 0.1
            b[:, 29] = 0.3
            a[:, 5:9] = [10, 20, -30, 100]
            b[:, 5:9] = [13, 24, -35, 150]
            ar, br = saved_recovery(root / "a", [a]), saved_recovery(root / "b", [b])
            weights = np.zeros((1, 5), dtype=np.float64)
            data = report.common_prefix({"completed_minutes": 4}, {"completed_minutes": 2},
                                        ar, br, weights, start_us=1704067200000000)
            self.assertEqual(data["common_completed_minutes"], 2)
            self.assertEqual(data["control"]["last_completed_minute_marked_PnL_USDT"], -100.0)
            self.assertAlmostEqual(data["control"]["max_drawdown_of_completed_minute_prefix"], 0.1)
            self.assertAlmostEqual(data["reentry_minus_control_observed_prefix"]["mean_l1_target_weight_gap_of_prefix"], 0.2)
            self.assertEqual(data["control"]["minute_prefix_raw_SHA256"], hashlib.sha256(a[:2].tobytes()).hexdigest())
            self.assertIsNone(data["annual_return_delta"])
            self.assertEqual(data["control"]["financial_advances"], 0)
            self.assertEqual(data["reentry_minus_control_saved_cumulative_prefix"],
                             {"fees_USDT": 3.0, "execution_cost_USDT": 4.0,
                              "funding_USDT": -5.0, "gross_fill_turnover_USDT": 50.0})

    def test_streaming_weights_are_day_specific(self):
        import numpy as np
        with tempfile.TemporaryDirectory() as temporary:
            first, last = minute_array(1440), minute_array(1)
            weights = np.zeros((2, 5), dtype=np.float64)
            weights[1, 0] = 0.5
            recovery = saved_recovery(Path(temporary) / "r", [first, last])
            row = report.stream_prefix(recovery, 1441, weights)
            self.assertAlmostEqual(row["mean_l1_target_weight_gap_of_prefix"], 0.5 / 1441)
            self.assertEqual(row["chunks_sha_and_geometry_verified"], 2)

    def test_streaming_checks_sha_even_beyond_selected_prefix(self):
        with tempfile.TemporaryDirectory() as temporary:
            recovery = saved_recovery(Path(temporary) / "r", [minute_array(1440), minute_array(1)])
            with (recovery / "DAY_0001.npz").open("ab") as file:
                file.write(b"tamper")
            with self.assertRaisesRegex(ValueError, "SHA"):
                report.stream_prefix(recovery, 1)

    def test_streaming_rejects_dtype_geometry_and_truncation(self):
        import numpy as np
        for array in (np.zeros((2, 35), dtype=np.float64), np.zeros((2, 36), dtype=np.float32)):
            with tempfile.TemporaryDirectory() as temporary:
                recovery = saved_recovery(Path(temporary) / "r", [array])
                with self.assertRaisesRegex(ValueError, "geometry"):
                    report.stream_prefix(recovery, 2)
        with tempfile.TemporaryDirectory() as temporary:
            recovery = saved_recovery(Path(temporary) / "r", [minute_array(2)])
            with self.assertRaisesRegex(ValueError, "exceeds"):
                report.stream_prefix(recovery, 3)

    def test_zero_observation_prefix_has_no_pnl_or_dd_claim(self):
        with tempfile.TemporaryDirectory() as temporary:
            recovery = saved_recovery(Path(temporary) / "r", [])
            row = report.stream_prefix(recovery, 0)
            self.assertIsNone(row["last_completed_minute_marked_PnL_USDT"])
            self.assertIsNone(row["max_drawdown_of_completed_minute_prefix"])

    def test_permission_without_matching_fill_is_not_entry(self):
        event = permission()
        unmatched = opening(event, signal=event["signal_us"] - report.DAY)
        data = report.reentry_entry_evidence([unmatched], {"events": [event]}, {"events": []})
        self.assertEqual(data["same_direction_permission_count"], 1)
        self.assertEqual(data["same_direction_executed_entry_count"], 0)
        self.assertIsNone(data["first_actual_same_direction_entry_us"])

    def test_entry_and_later_protection_cycles(self):
        event = permission()
        first, second = opening(event), opening(event, before="1", after="2", delay=120000001, fill_id="f2")
        protection = {"events": [
            {"symbol": "X", "event_us": first["event_us"] + 5 * report.MINUTE, "kind": "FULL_EXIT_SIGNAL"},
            {"symbol": "X", "event_us": first["event_us"] + 6 * report.MINUTE, "kind": "FULL_EXIT_FLAT"}]}
        data = report.reentry_entry_evidence([first, second], {"events": [event]}, protection)
        self.assertEqual(data["same_direction_executed_entry_count"], 1)
        self.assertEqual(data["actual_opening_fill_legs_for_permissions"], 2)
        self.assertEqual(data["events"][0]["later_full_exit_signal_count"], 1)
        self.assertEqual(data["events"][0]["later_paid_flat_count"], 1)

    def test_reentry_fill_rejects_past_clock_residue_or_wrong_direction(self):
        event = permission()
        for fill in (opening(event, delay=0), opening(event, before="0.00000001"), opening(event, after="-1")):
            with self.assertRaises(ValueError):
                report.reentry_entry_evidence([fill], {"events": [event]}, {"events": []})

    def test_next_reentry_permission_bounds_later_cycle_counts(self):
        first, second = permission(), permission(signal=1704153600000000 + report.DAY)
        later = {"events": [{"symbol": "X", "event_us": second["signal_us"] + 300000000,
                             "kind": "FULL_EXIT_SIGNAL"}]}
        data = report.reentry_entry_evidence([opening(first), opening(second)], {"events": [first, second]}, later)
        self.assertEqual(data["events"][0]["later_full_exit_signal_count"], 0)
        self.assertEqual(data["events"][1]["later_full_exit_signal_count"], 1)

    def test_fresh_reset_and_zero_target_permission_are_distinct(self):
        zero = permission(kind="FRESH_DAILY_RESET", new_sign=0)
        data = report.reentry_entry_evidence([], {"events": [zero]}, {})
        self.assertEqual(data["fresh_daily_reset_permission_count"], 1)
        self.assertEqual(data["all_direction_executed_entry_count"], 0)

    def test_terminal_attempt_kinds_retained_without_control_invention(self):
        data = report.terminal_attempt_evidence({"terminal_attempt_observations": {
            "X:PROTECTIVE_STOP": {"symbol": "X", "kind": "PROTECTIVE_STOP", "actual_attempts": 7,
                                  "first_attempt_us": 1, "last_attempt_us": 7},
            "Y:TERMINAL": {"symbol": "Y", "kind": "TERMINAL", "actual_attempts": 5,
                           "first_attempt_us": 2, "last_attempt_us": 6}}}, observed=True)
        self.assertEqual(data["actual_attempts_by_kind"], {"PROTECTIVE_STOP": 7, "TERMINAL": 5})
        self.assertEqual(data["actual_attempt_count"], 12)
        control = report.terminal_attempt_evidence(None, observed=False)
        self.assertIsNone(control["actual_attempt_count"])
        self.assertIsNone(control["actual_attempts_by_kind"])

    def test_subsequent_halt_needs_actual_entry_and_exact_halt_clock(self):
        halted = {**summary(status="LIQUIDATION_REQUIRED_HALT"), "stop_us": 200, "clock_us": 200}
        evidence = {"events": [{"entry_us": 100}], "first_actual_same_direction_entry_us": 100}
        self.assertTrue(report.subsequent_halt_evidence(halted, evidence)["halt_after_actual_same_direction_entry"])
        self.assertFalse(report.subsequent_halt_evidence(halted, {"events": []})["halt_after_any_actual_reentry"])
        halted["stop_us"] = None
        self.assertIsNone(report.subsequent_halt_evidence(halted, evidence)["halt_after_any_actual_reentry"])

    def test_locator_and_output_no_overwrite(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for locator in ("../secret", "/absolute"):
                with self.assertRaises(ValueError):
                    report.safe_path(root, locator)
            output = root / "result.json"
            report.save_new(output, {"synthetic": True})
            with self.assertRaises(FileExistsError):
                report.save_new(output, {"synthetic": False})
            self.assertEqual(json.loads(output.read_text()), {"synthetic": True})


if __name__ == "__main__":
    unittest.main(verbosity=2)
