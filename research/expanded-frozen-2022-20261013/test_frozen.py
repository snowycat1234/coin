"""Non-economic verification of the frozen 2022 target specification."""
import json
import os
from pathlib import Path
import unittest

import preflight_2022
import targets_2022

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
REPO = Path(os.environ.get("COIN_REPO_ROOT",
    str(HERE.parents[1] if HERE.parent.name == "research" else ROOT / "coin_cs_sma_recovery_20261013/repo")))
INPUTS = Path(os.environ.get("COIN_INPUTS_DIR", str(ROOT / "coin_cs_sma_recovery_20261013/inputs")))
SAVED = Path(os.environ.get("COIN_SAVED_TARGETS_DIR", str(ROOT / "coin_strong_candidates_20261013")))


class Frozen2022Tests(unittest.TestCase):
    def test_full_year_original_cube_and_warmup(self):
        r = preflight_2022.inspect(INPUTS)
        self.assertEqual(r["decision_days"], 365)
        self.assertEqual(r["complete_full_five_200_close_days"], 365)
        self.assertEqual(r["oldest_200_close_first_decision_utc"], "2021-06-16T00:00:00+00:00")
        self.assertEqual(r["first_pre_window_scheduled_rank_utc"], "2021-12-27T00:00:00+00:00")
        self.assertEqual(r["later_cube_2022_discrepancy_count"], 10)

    def test_original_saved_year_targets_remain_bit_exact(self):
        result = targets_2022.verify_history(
            REPO, INPUTS, SAVED,
        )
        self.assertEqual(set(result), {"2023", "2025"})
        for row in result.values():
            self.assertEqual(row["status"], "BIT_EXACT_ORIGINAL_TARGET_AND_COVARIANCE_PARITY")

    def test_source_gate_remains_closed(self):
        protocol = json.loads((HERE / "PROTOCOL.json").read_text())
        inventory = json.loads((HERE / "SOURCE_INVENTORY.json").read_text())
        git_archive = json.loads((HERE / "GIT_ARCHIVE_MATRIX.json").read_text())
        self.assertEqual(protocol["days"], 365)
        self.assertEqual(protocol["expected_native_minutes_per_arm"], 525600)
        self.assertEqual(inventory["mark_gap_original_total"], 27)
        self.assertEqual(git_archive["unique_month_symbol_family"], 110)
        self.assertEqual(git_archive["december_missing"], 10)
        self.assertIn("No 2022 interpolation", protocol["market_source"]["mark_policy"])


if __name__ == "__main__":
    unittest.main()
