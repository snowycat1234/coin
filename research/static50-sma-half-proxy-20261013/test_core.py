"""Synthetic-only protocol assertions; never touches saved target years."""
import importlib.util
from pathlib import Path
import unittest
import numpy as np

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('half_core', HERE / 'core.py')
core = importlib.util.module_from_spec(spec)
spec.loader.exec_module(core)


class HalfMixTests(unittest.TestCase):
    def setUp(self):
        self.c = np.diag([.04, .09, .16, .01, .25])

    def test_literal_half_sum_no_post_mix_amplification(self):
        a = np.array([.2, -.1, 0, .1, 0])
        b = np.array([-.1, .2, .1, 0, -.1])
        w, _ = core.mix_day(a, b, self.c)
        np.testing.assert_array_equal(w, .5*a + .5*b)
        self.assertLessEqual(np.abs(w).sum(), .5*(np.abs(a).sum()+np.abs(b).sum()))

    def test_signed_cancellation_genuine_cash(self):
        a = np.array([.2, -.2, 0, 0, 0])
        w, proof = core.mix_day(a, -a, self.c)
        np.testing.assert_array_equal(w, np.zeros(5))
        self.assertTrue(proof['mix_cash'])
        self.assertAlmostEqual(proof['signed_cancellation_gross'], np.abs(a).sum())

    def test_convex_caps_and_psd_risk_triangle(self):
        a = np.array([.3, -.3, 0, 0, 0])
        b = np.array([0, 0, .3, -.3, 0])
        w, proof = core.mix_day(a, b, self.c)
        self.assertLessEqual(np.max(np.abs(w)), .3)
        self.assertLessEqual(np.abs(w).sum(), .6)
        self.assertLessEqual(proof['mix_annual_sigma'],
                             .5*(proof['static_annual_sigma']+proof['sma_annual_sigma'])+1e-12)
        self.assertLessEqual(proof['mix_annual_sigma'],
                             max(proof['static_annual_sigma'], proof['sma_annual_sigma'])+1e-12)

    def test_no_unknown_or_bad_covariance_admission(self):
        with self.assertRaises(ValueError):
            core.mix_day(np.zeros(5), np.array([np.nan,0,0,0,0]), self.c)
        bad = self.c.copy(); bad[0, 0] = -.01
        with self.assertRaises(ValueError):
            core.mix_day(np.zeros(5), np.zeros(5), bad)
        with self.assertRaises(ValueError):
            core.mix_day(np.array([.31,0,0,0,0]), np.zeros(5), self.c)

    def test_future_target_and_covariance_prefix_invariance(self):
        a = np.zeros((365, 5)); b = np.zeros_like(a)
        a[:, 0] = .1; b[:, 1] = -.1
        c = np.repeat(self.c[None, :, :], 365, axis=0)
        first, _ = core.mix_arrays(a, b, c)
        changed_a, changed_b, changed_c = a.copy(), b.copy(), c.copy()
        changed_a[90:, 0] = -.2
        changed_b[90:, 1] = .2
        changed_c[90:] *= 2
        second, _ = core.mix_arrays(changed_a, changed_b, changed_c)
        np.testing.assert_array_equal(first[:90], second[:90])

    def test_calendar_exact_and_order(self):
        packet = dict(decision_us=core.calendar(2023), symbol_order=np.array(core.SYMBOLS))
        core.check_packet(packet, 2023, ('decision_us','symbol_order'))
        bad = {key: val.copy() for key,val in packet.items()}; bad['decision_us'][14] += core.DAY
        with self.assertRaises(ValueError): core.check_packet(bad, 2023, ('decision_us','symbol_order'))
        bad = {key: val.copy() for key,val in packet.items()}; bad['symbol_order'][0],bad['symbol_order'][1] = bad['symbol_order'][1],bad['symbol_order'][0]
        with self.assertRaises(ValueError): core.check_packet(bad, 2023, ('decision_us','symbol_order'))

    def test_reproducible_npz_and_no_pickle(self):
        import tempfile
        with tempfile.TemporaryDirectory() as directory:
            x, y = Path(directory)/'x.npz', Path(directory)/'y.npz'
            core.save_npz(x, a=np.array([1,2],dtype=np.int64))
            core.save_npz(y, a=np.array([1,2],dtype=np.int64))
            self.assertEqual(core.sha256(x), core.sha256(y))
            with self.assertRaises(ValueError): core.save_npz(y, bad=np.array([{}], dtype=object))


if __name__ == '__main__': unittest.main()
