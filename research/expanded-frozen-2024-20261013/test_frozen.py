"""Small non-economic preflight for the frozen 2024 expansion."""
import json
import os
from pathlib import Path
import tempfile
import unittest

import numpy as np
import pandas as pd

import mark_gap_bridge as bridge
import targets_2024 as target

HERE = Path(__file__).resolve().parent
BASE = HERE.parent
REPO = Path(os.environ.get("COIN_REPO_ROOT", str(HERE.parents[1] if HERE.parent.name == "research" else BASE / "coin_cs_sma_recovery_20261013/repo")))
INPUTS = Path(os.environ.get("COIN_INPUTS_DIR", str(BASE / "coin_cs_sma_recovery_20261013/inputs")))
SAVED = Path(os.environ.get("COIN_SAVED_TARGETS_DIR", str(BASE / "coin_strong_candidates_20261013")))
JULY_WRAPPER = Path(os.environ.get("COIN_JULY_WRAPPER", str(HERE / "JULY2024.zip")))


class FrozenTests(unittest.TestCase):
    def test_gregorian_2024_calendar_and_200_closes(self):
        d = np.arange(target.us(2024), target.us(2025), target.DAY, dtype=np.int64)
        self.assertEqual(len(d), 366)
        self.assertEqual(int(d[-1]), target.us(2025) - target.DAY)
        with np.load(INPUTS / "Y2025.npz", allow_pickle=False) as z:
            t, p = z["close_available_us"], z["close"]
            k = int(np.searchsorted(t, d[0]))
            self.assertEqual(int(t[k]), int(d[0]))
            self.assertTrue(np.all(np.diff(t[k-199:k+1]) == target.DAY))
            self.assertTrue(np.isfinite(p[k-199:k+1]).all())
            self.assertTrue((p[k-199:k+1] > 0).all())

    def test_frozen_original_target_reproduction(self):
        proof = target.verify_history(REPO, INPUTS, SAVED)
        self.assertEqual([proof[str(y)]["days"] for y in (2023, 2025)], [365, 365])
        self.assertTrue(all(v["status"] == "BIT_EXACT_ORIGINAL_TARGET_AND_COVARIANCE_PARITY" for v in proof.values()))

    def test_future_close_prefix_invariance(self):
        public_targets, _, _ = target.load_modules(REPO)
        with np.load(INPUTS / "Y2025.npz", allow_pickle=False) as z:
            t, p = z["close_available_us"], z["close"]
        d = np.arange(target.us(2024), target.us(2024) + 182 * target.DAY, target.DAY)
        full, _ = public_targets(p, t, d, target.SYMBOLS, target.SYMBOLS)
        cut = int(np.searchsorted(t, d[-1])) + 1
        prefix, _ = public_targets(p[:cut], t[:cut], d, target.SYMBOLS, target.SYMBOLS)
        np.testing.assert_array_equal(full, prefix)
        # Rolling200 means at/inside this prefix also ignore the omitted suffix.
        m1 = pd.DataFrame(p).rolling(200, min_periods=200).mean().to_numpy()
        m2 = pd.DataFrame(p[:cut]).rolling(200, min_periods=200).mean().to_numpy()
        np.testing.assert_array_equal(m1[:cut], m2)

    def test_gap_pair_ohlc_and_allowlist(self):
        made = bridge.derive_pair(bridge.Decimal("100.00000000"), bridge.Decimal("90.00000000"))
        self.assertEqual(made, [
            {"open": "100.00000000", "high": "100.00000000", "low": "95.00000000", "close": "95.00000000"},
            {"open": "95.00000000", "high": "95.00000000", "low": "90.00000000", "close": "90.00000000"},
        ])
        self.assertEqual(bridge.GAPS, (1723456920000, 1723456980000))
        wrapper = JULY_WRAPPER
        if wrapper.exists():
            with tempfile.TemporaryDirectory() as tmp:
                result = bridge.build(wrapper, Path(tmp) / "derived")
                self.assertEqual(result["derived_rows"], 10)
                rows = (Path(tmp) / "derived" / "DERIVED_MARK_OHLC.csv").read_text().splitlines()
                self.assertEqual(len(rows), 11)
                self.assertEqual(result["derived_csv_SHA256"], "0af6d1cc66bc81afd39582ae4de2b1aa25d9e0031765ce6bce74e917a5577d0c")

    def test_protocol_only_ten_mark_rows(self):
        p = json.loads((HERE / "PROTOCOL.json").read_text())
        self.assertEqual(p["days"], 366)
        self.assertEqual(p["expected_native_minutes_per_arm"], 366 * 1440)
        self.assertEqual(len(p["arms"]), 5)
        self.assertIn("exactly the ten known absent", p["market_source"]["source_admission"])


if __name__ == "__main__":
    unittest.main()
