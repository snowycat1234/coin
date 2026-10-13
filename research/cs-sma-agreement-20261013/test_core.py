"""Synthetic numpy/std-unittest tests; no historical economic scoring."""
import importlib.util
from pathlib import Path
import sys
import unittest

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))
spec = importlib.util.spec_from_file_location("cs_sma_agreement_core", HERE / "core.py")
core = importlib.util.module_from_spec(spec)
spec.loader.exec_module(core)


def history(days=350):
    times = core.ANCHOR_US + np.arange(-252, days-252, dtype=np.int64) * core.DAY_US
    u = np.arange(days, dtype=float)[:, None]
    rates = np.array([-.004, -.002, -.0005, .002, .004])[None, :]
    prices = 100 * np.exp(u*rates + .007*np.sin(u*.7 + np.arange(5)[None, :]))
    return prices, times


class TargetTests(unittest.TestCase):
    def test_sma_requires_exactly_200_and_includes_latest_completed_close(self):
        p, t = history()
        raw, eligible, mean, latest = core.sma_raw_targets(p, t, t[198:201])
        self.assertFalse(eligible[0].any())
        self.assertTrue(eligible[1:].all())
        np.testing.assert_allclose(mean[1], p[:200].mean(0), rtol=1e-14, atol=0.)
        np.testing.assert_array_equal(latest[1], p[199])
        np.testing.assert_array_equal(raw[1], .12*np.sign(p[199]-p[:200].mean(0)))

    def test_sma_long_short_and_genuine_flat(self):
        p, t = history()
        p[:, 2] = 100.
        raw, ok, _, _ = core.sma_raw_targets(p, t, t[252:253])
        self.assertTrue(ok.all())
        np.testing.assert_array_equal(raw[0], [-.12, -.12, 0., .12, .12])

    def test_current_close_unavailable_does_not_substitute_previous_bar(self):
        p, t = history()
        raw, ok, _, _ = core.sma_raw_targets(p[:252], t[:252], t[252:253])
        self.assertFalse(ok.any())
        self.assertFalse(raw.any())
        raw, ok, _, _ = core.sma_raw_targets(np.delete(p, 200, 0), np.delete(t, 200), t[252:253])
        self.assertFalse(ok.any())

    def test_nonfinite_or_nonpositive_history_is_unknown_not_flat(self):
        p, t = history()
        for value in (np.nan, np.inf, 0., -1.):
            with self.subTest(value=value):
                changed = p.copy()
                changed[100, 0] = value
                raw, ok, _, _ = core.sma_raw_targets(changed, t, t[252:253])
                self.assertFalse(ok[0, 0])
                self.assertTrue(ok[0, 1:].all())
                self.assertEqual(raw[0, 0], 0.)
                with self.assertRaisesRegex(ValueError, "Strict common source admission"):
                    core.build_targets(changed, t, t[252:253])
                diagnostic = core.build_targets(changed, t, t[252:253], strict=False)
                self.assertEqual(diagnostic["source_status"][0], "UNKNOWN")
                self.assertTrue(all(np.isnan(w[0]).all() for w in diagnostic["targets"].values()))

    def test_clock_and_full_calendar_validation(self):
        p, t = history()
        for bad in (t.astype(float), np.r_[t[:100], t[99:]], t[::-1]):
            with self.assertRaises(ValueError):
                core.sma_raw_targets(p, bad, t[252:253])
        with self.assertRaises(ValueError):
            core.build_targets(p, t, t[[252, 254]])

    def test_future_price_and_future_nan_mask_prefix_invariance(self):
        p, t = history()
        d = t[252:]
        base = core.build_targets(p, t, d)
        cut = 280
        for kind in ("value", "NaN_mask", "both"):
            with self.subTest(kind=kind):
                changed = p.copy()
                if kind != "NaN_mask":
                    changed[cut:] *= np.array([10., 2., .1, 30., .2])
                if kind != "value":
                    changed[cut:, [0, 3]] = np.nan
                later = core.build_targets(changed, t, d, strict=False)
                count = cut-252
                for field in ("targets", "raw"):
                    for arm in base[field]:
                        np.testing.assert_array_equal(base[field][arm][:count], later[field][arm][:count])
                for field in ("annual_covariance", "sma_eligible", "sma_mean", "sma_latest_close", "agreement_mask"):
                    np.testing.assert_array_equal(base[field][:count], later[field][:count])
                self.assertEqual(base["proof"][:count], later["proof"][:count])
                prefix = core.build_targets(p[:cut], t[:cut], d[:count])
                for arm in core.ARMS:
                    np.testing.assert_array_equal(base["targets"][arm][:count], prefix["targets"][arm])

    def test_cs_exact_21_daily_returns(self):
        p, t = history()
        p[252-21, 0] = 1.
        raw, diag = core.cs_raw_targets(p, t, t[252:253])
        event = diag["rank_events"][0]
        self.assertEqual(event["momentum"][0], p[252, 0]/p[231, 0]-1.)
        self.assertNotEqual(event["momentum"][0], p[252, 0]/p[232, 0]-1.)
        self.assertEqual(raw[0, 0], .15)

    def test_cs_stable_partial_ties_and_fully_tied_cash(self):
        p, t = history()
        u = np.arange(len(t), dtype=float)[:, None]
        p = 100*np.exp(u*np.array([.001, .001, .002, .003, .003])[None, :])
        raw, _ = core.cs_raw_targets(p, t, t[252:253])
        np.testing.assert_array_equal(raw[0], [-.15, -.15, 0., .15, .15])
        p[:] = p[:, [2]]
        tied, _ = core.cs_raw_targets(p, t, t[252:253])
        self.assertFalse(tied.any())

    def test_cs_prior_scheduled_rank_warmup_sticky_midweek(self):
        p, t = history()
        p[254:259, 0] *= 2.
        full, diag = core.cs_raw_targets(p, t, t[252:268])
        partial, pd = core.cs_raw_targets(p, t, t[254:268])
        np.testing.assert_array_equal(partial, full[2:])
        np.testing.assert_array_equal(full[:7], np.tile(full[0], (7, 1)))
        self.assertEqual(pd["rank_us"][0], core.ANCHOR_US)
        self.assertEqual(diag["rank_us"][7], core.ANCHOR_US+7*core.DAY_US)

    def test_cs_missing_clear_no_reentry_until_new_scheduled_rank(self):
        p, t = history()
        p[252, 0] = np.nan
        raw, diag = core.cs_raw_targets(p, t, t[281:291])
        self.assertTrue(diag["current_eligible"][2][0])
        self.assertEqual(raw[2, 0], 0.)
        self.assertEqual(raw[6, 0], -.15)
        partial, _ = core.cs_raw_targets(p, t, t[283:291])
        np.testing.assert_array_equal(partial, raw[2:])

    def test_cs_raw_canonical_events_and_sized_sign_parity(self):
        p, t = history()
        d = t[252:]
        raw, diag = core.cs_raw_targets(p, t, d)
        sized, canonical_diag = core.public_targets(p, t, d, core.SYMBOLS, core.SYMBOLS)
        self.assertEqual(diag, canonical_diag)
        np.testing.assert_array_equal(np.sign(raw), np.sign(sized))
        self.assertTrue(set(np.unique(raw)) <= {-.15, 0., .15})
        for event in diag["rank_events"]:
            i = int(np.searchsorted(d, event["rank_us"]))
            if i < len(d) and d[i] == event["rank_us"]:
                np.testing.assert_array_equal(raw[i], event["raw_weights"])

    def test_symmetric_gate_no_replacement_or_raw_slot_redistribution(self):
        cs = np.array([-.15, -.15, 0., .15, .15])
        sma = np.array([-.12, .12, -.12, .12, 0.])
        gate = core.agreement_mask(cs, sma, np.ones(5, bool))
        np.testing.assert_array_equal(gate, [True, False, False, True, False])
        np.testing.assert_array_equal(np.where(gate, cs, 0.), [-.15, 0., 0., .15, 0.])
        blocked = core.agreement_mask(cs, sma, np.zeros(5, bool))
        self.assertFalse(blocked.any())

    def test_shared_risk_covariance_ddof1_annual365_and_exact_scale(self):
        p, t = history()
        result = core.build_targets(p, t, t[252:260])
        for i, at in enumerate(t[252:260]):
            k = 252+i
            returns = np.diff(p[k-30:k+1], axis=0)/p[k-30:k]
            cov = np.cov(returns, rowvar=False, ddof=1)*365
            np.testing.assert_array_equal(result["annual_covariance"][i], cov)
            for arm in core.ARMS[:-1]:
                expected, proof = core.RISK.scale(result["raw"][arm][i], cov)
                np.testing.assert_array_equal(result["targets"][arm][i], expected)
                self.assertEqual(result["proof"][i]["arms"][arm], proof)
            np.testing.assert_array_equal(result["raw"]["STATIC50"][i],
                .5*result["raw"]["CS"][i]+.5*result["raw"]["SMA200"][i])

    def test_risk_caps_scale_up_and_scale_down_and_cash(self):
        raw = np.array([.15, -.15, 0., 0., 0.])
        up, up_proof = core.RISK.scale(raw, np.eye(5)*.001)
        np.testing.assert_array_equal(up, [.3, -.3, 0., 0., 0.])
        self.assertTrue(up_proof["cap_bound"])
        down, down_proof = core.RISK.scale(raw, np.eye(5)*10.)
        self.assertLess(down_proof["factor"], 1.)
        self.assertAlmostEqual(down_proof["post_sigma"], .10)
        cash, cash_proof = core.RISK.scale(np.zeros(5), np.zeros((5, 5)))
        self.assertFalse(cash.any())
        self.assertEqual(cash_proof["reason"], "INTRINSIC_CASH")
        for weights in (up, down, cash):
            self.assertLessEqual(abs(weights).max(), .30+1e-12)
            self.assertLessEqual(abs(weights).sum(), .60+1e-12)

    def test_signed_covariance_preserves_long_short_hedges(self):
        cov = np.ones((5, 5))*.25 + np.eye(5)*.01
        _, hedge = core.RISK.scale(np.array([.15, -.15, 0., 0., 0.]), cov)
        _, same = core.RISK.scale(np.array([.15, .15, 0., 0., 0.]), cov)
        self.assertLess(hedge["raw_sigma"], same["raw_sigma"])

    def test_diagnostic_survivors_exact_no_resizing_risk_can_increase(self):
        cs = np.array([.15, -.15, 0., 0., 0.])
        sma = np.array([.12, .12, 0., 0., 0.])
        gate = core.agreement_mask(cs, sma, np.ones(5, bool))
        raw = dict(CS=cs, SMA200=sma, STATIC50=.5*(cs+sma), AGREEMENT=np.where(gate, cs, 0.))
        cov = np.ones((5, 5))*.25 + np.eye(5)*.01
        out, proof = core.size_day(raw, gate, cov)
        diagnostic = out["AGREEMENT_NO_REALLOCATION"]
        np.testing.assert_array_equal(diagnostic, np.where(gate, out["CS"], 0.))
        self.assertTrue(np.all(abs(diagnostic) <= abs(out["CS"])))
        self.assertTrue(proof["AGREEMENT_NO_REALLOCATION"]["above_nominal_risk"])
        self.assertGreater(proof["AGREEMENT_NO_REALLOCATION"]["post_sigma"], proof["CS"]["post_sigma"])
        self.assertLessEqual(proof["AGREEMENT"]["post_sigma"], .10+1e-12)

    def test_all_target_exposure_caps_and_causal_proof(self):
        p, t = history()
        result = core.build_targets(p, t, t[252:])
        self.assertTrue(np.all(result["source_status"] == "READY"))
        for arm, w in result["targets"].items():
            self.assertLessEqual(abs(w).max(), .30+1e-12)
            self.assertLessEqual(abs(w).sum(1).max(), .60+1e-12)
            for i, row in enumerate(result["proof"]):
                self.assertLessEqual(row["last_close_available_us"], row["decision_us"])
                self.assertLessEqual(row["cs_rank_us"], row["decision_us"])
                if arm != "AGREEMENT_NO_REALLOCATION":
                    self.assertLessEqual(row["arms"][arm]["post_sigma"], .10+1e-12)


def load_tests(loader, tests, pattern):
    # Run six unchanged original synthetic tests through std unittest, keeping
    # the retained import-only compatibility copy and original source intact.
    path = ROOT / "tests/test_public_cross_section_momentum_compat.py"
    spec = importlib.util.spec_from_file_location("canonical_cs_golden_tests", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    for name in sorted(n for n in vars(module) if n.startswith("test_")):
        tests.addTest(unittest.FunctionTestCase(getattr(module, name), description="canonical "+name))
    return tests


if __name__ == "__main__":
    unittest.main(verbosity=2)
