"""Independent generated mathematical checks of the exact original ASTs."""
from pathlib import Path
from unittest.mock import patch
import sys
import unittest
import numpy as np
import bind_sources as B


class PortableMathematicalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.port, cls.account, cls.sim, cls.helper, cls.risk, cls.F = B.load()

    def test_original_scale_formula_generated_covariance(self):
        random = np.random.default_rng(73910)
        for _ in range(80):
            raw = random.uniform(-.08, .08, 5)
            basis = random.normal(size=(5, 5))
            cov = basis @ basis.T * .03 + np.eye(5) * .002
            sigma = np.sqrt(raw @ cov @ raw)
            factor = min(.1 / sigma, .3 / np.abs(raw).max(), .6 / np.abs(raw).sum())
            actual, proof = self.F.scale(raw, cov)
            np.testing.assert_array_equal(actual, raw * factor)
            self.assertEqual(proof['factor'], factor)
            self.assertLessEqual(np.sqrt(actual @ cov @ actual), .1 + 1e-12)

    def test_original_signed_safety_and_covariance_formula(self):
        random = np.random.default_rng(29101)
        for _ in range(80):
            raw = random.uniform(-.8, .8, 5)
            returns = random.normal(scale=.025, size=(44, 5))
            bounded = np.clip(raw, -.3, .3)
            if np.abs(bounded).sum() > .6:
                bounded *= .6 / np.abs(bounded).sum()
            covariance = np.cov(returns[-30:], rowvar=False, ddof=1) * 365
            sigma = np.sqrt(max(0., bounded @ covariance @ bounded))
            expected = bounded * (.1 / sigma) if sigma > .1 else bounded
            actual, proof = self.F.signed_risk_weights(raw, returns)
            np.testing.assert_array_equal(actual, expected)
            self.assertTrue(proof['past_only'])
            self.assertEqual(proof['covariance_observations'], 30)

    def test_original_allocate_exact_completed_covariance_and_future_suffix(self):
        random = np.random.default_rng(13502)
        day = 86_400_000_000
        clocks = np.arange(70, dtype=np.int64) * day
        prices = 100 * np.cumprod(1 + random.normal(scale=.006, size=(70, 5)), axis=0)
        decisions = clocks[35:40]
        components = {a: random.uniform(-.06, .06, (5, 5))
                      for a in ('CS_MATCHED', 'VOL_MATCHED', 'STATIC50')}
        sized, covariance, proof = self.F.allocate(clocks, prices, decisions, components)
        for i, k in enumerate(range(35, 40)):
            expected = np.cov(np.diff(prices[k-30:k+1], axis=0) / prices[k-30:k],
                              rowvar=False, ddof=1) * 365
            np.testing.assert_array_equal(covariance[i], expected)
            self.assertEqual(proof[i]['last_price_available_us'], int(clocks[k]))
            for arm in components:
                np.testing.assert_array_equal(sized[arm][i], self.F.scale(components[arm][i], expected)[0])
        later = prices.copy()
        later[40:] *= random.uniform(.1, 10, size=later[40:].shape)
        other, other_cov, other_proof = self.F.allocate(clocks, later, decisions, components)
        for arm in sized:
            np.testing.assert_array_equal(sized[arm], other[arm])
        np.testing.assert_array_equal(covariance, other_cov)
        self.assertEqual(proof, other_proof)

    def test_original_risk_rejections_remain_active(self):
        for weights, covariance in ((np.ones(5) * .2, np.eye(5)),
                                     (np.array([.31, 0, 0, 0, 0]), np.eye(5)),
                                     (np.ones(5) * .05, np.zeros((5, 5))),
                                     (np.ones(5) * .05, np.eye(5) * -1)):
            with self.assertRaises(ValueError):
                self.F.scale(weights, covariance)
        with self.assertRaises(ValueError):
            self.F.signed_risk_weights(np.ones(5), np.zeros((29, 5)))

    def test_exact_python_patch_version_refused(self):
        with patch.object(sys, 'version_info', (3, 12, 13, 'final', 0)):
            with self.assertRaisesRegex(B.GateError, 'EXACT_PYTHON_3_12_14'):
                B.configure_runtime()

    def test_carrier_unsafe_paths_refused(self):
        for relative in ('/tmp/example.py', '../example.py', 'missing_carrier.py'):
            with self.assertRaises(B.GateError):
                B.safe(relative)

    def test_original_historical_gate_is_not_reachable(self):
        for function in (self.port.verify, self.port.prepared, self.port.window,
                         B.verify_financial, B.bind_saved_targets, B.source_window,
                         B.history_admission):
            with self.assertRaisesRegex(B.GateError, 'REFUSES_ORIGINAL26'):
                function('Y2025')


if __name__ == '__main__':
    unittest.main()
