"""Synthetic-only checks for comparison and target-gap censoring."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import tempfile
import unittest

import numpy as np

from build_report import contrast, target_gap
from provenance import sha, verify_completed_run


class ReportTests(unittest.TestCase):
    def test_halted_wallet_never_receives_annual_profit_delta(self):
        left = {"full_calendar": False, "completed_minutes": 10, "paid_flat": False,
                "paid_cash_PnL_USDT": None, "marked_PnL_USDT": 10.,
                "minute_drawdown": .1, "mean_actual_gross": .4,
                "mean_l1_target_weight_gap": .2,
                "terminal_residual_gross_notional_USDT": 100.,
                "trade_legs": 2, "gross_fill_turnover_USDT": 1000., "fees_USDT": 1.,
                "execution_cost_USDT": 2., "funding_USDT": 0.,
                "rejection_counts": {}, "halt_count": 1}
        right = dict(left, marked_PnL_USDT=100., paid_cash_PnL_USDT=None)
        row = contrast(left, right)
        self.assertFalse(row["same_full_calendar"])
        self.assertIsNone(row["paid_cash_PnL_delta_USDT"])
        self.assertIsNone(row["marked_PnL_delta_same_full_calendar_USDT"])
        self.assertIsNone(row["trade_legs_delta"])

    def test_full_calendar_relative_counts_zero_baseline_null(self):
        left = {"full_calendar": True, "completed_minutes": 10, "paid_flat": True,
                "paid_cash_PnL_USDT": 10., "marked_PnL_USDT": 10.,
                "minute_drawdown": .1, "mean_actual_gross": .4,
                "mean_l1_target_weight_gap": .2,
                "terminal_residual_gross_notional_USDT": 0.,
                "trade_legs": 2, "gross_fill_turnover_USDT": 1000., "fees_USDT": 1.,
                "execution_cost_USDT": 2., "funding_USDT": 0.,
                "rejection_counts": {"SOME_REASON": 4}, "halt_count": 0}
        right = dict(left, trade_legs=3, rejection_counts={"SOME_REASON": 2,
                                                          "NEW_REASON": 1})
        row = contrast(left, right)
        self.assertEqual(row["trade_legs_delta"], 1)
        self.assertEqual(row["trade_legs_relative_change"], .5)
        self.assertEqual(row["rejection_count_deltas"], {
            "SOME_REASON": -2, "NEW_REASON": 1})
        self.assertEqual(row["rejection_count_relative_changes"], {
            "SOME_REASON": -.5, "NEW_REASON": None})

    def test_target_gap_exact_prefix_and_sha(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            chunk = np.zeros((3, 36), dtype=np.float64)
            chunk[:, 29] = [0.1, 0.2, 0.3]
            path = root / "day.npz"
            np.savez_compressed(path, minute_chunk=chunk)
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            (root / "POINTER.json").write_text(json.dumps({
                "chunks": [{"path": "day.npz", "SHA256": digest, "rows": 3}],
                "completed_minutes": 3}))
            weights = np.zeros((1, 5), dtype=np.float64)
            self.assertAlmostEqual(target_gap(root, weights), 0.2)
            self.assertAlmostEqual(target_gap(root, weights, 2), 0.15)
            with self.assertRaises(ValueError):
                target_gap(root, weights, 4)
            path.write_bytes(path.read_bytes() + b"drift")
            with self.assertRaises(ValueError):
                target_gap(root, weights, 2)

    def test_completed_run_fails_closed_on_binding_and_stop_reason(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            module, state = root / "module", root / "state"
            module.mkdir()
            state.mkdir()
            for name in ("run_cases.py", "CASE_BINDINGS.json", "fine_account.py",
                         "FROZEN_CODE.json"):
                (module / name).write_text(name)
            plan = {"cases": [{"case_id": f"Y2023_ARM{i}"} for i in range(6)],
                    "modes": ["ORIGINAL", "GUARD50"],
                    "fine_profile_SHA256": "fine", "coarse_profile_SHA256": "coarse"}
            ids = [f"{case['case_id']}_FINE_{mode}" for case in plan["cases"]
                   for mode in plan["modes"]]
            binding = {"parent_GO": True, "nonce": "a" * 32,
                       "runner_SHA256": sha(module / "run_cases.py"),
                       "bindings_SHA256": sha(module / "CASE_BINDINGS.json"),
                       "fine_account_SHA256": sha(module / "fine_account.py"),
                       "freeze_manifest_SHA256": sha(module / "FROZEN_CODE.json"),
                       "fine_profile_SHA256": "fine", "coarse_profile_SHA256": "coarse",
                       "fine_case_ids": ids}
            controller = {"status": "ALL_CASES_FINISHED", "unstarted_case_ids": [],
                          "per_case": {identity: {"exit_code": 0, "stop_reason": None,
                                                  "peak_RSS": 10} for identity in ids}}
            (state / "RUN_BINDING.json").write_text(json.dumps(binding))
            (state / "RESOURCE_RECEIPTS.json").write_text(json.dumps(controller))
            self.assertEqual(verify_completed_run(state, module, plan), ids)
            controller["per_case"][ids[0]]["stop_reason"] = "WORKER_RSS"
            (state / "RESOURCE_RECEIPTS.json").write_text(json.dumps(controller))
            with self.assertRaises(ValueError):
                verify_completed_run(state, module, plan)
            controller["per_case"][ids[0]]["stop_reason"] = None
            (state / "RESOURCE_RECEIPTS.json").write_text(json.dumps(controller))
            (module / "fine_account.py").write_text("drift")
            with self.assertRaises(ValueError):
                verify_completed_run(state, module, plan)


if __name__ == "__main__":
    unittest.main()
