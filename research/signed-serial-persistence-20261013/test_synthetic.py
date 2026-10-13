"""Synthetic-only tests. No historical source reader or account import."""
import unittest
import numpy as np
import core


def fixture(days=80):
    rng = np.random.default_rng(811760)
    increments = rng.normal(0, .001, (days, 288, 5))
    # Vary sign clustering and slow volatility enough for the fixed control schema.
    for day in range(days):
        increments[day] *= (1 + .2 * np.sin(day / 3))
        increments[day, 1:] += .12 * increments[day, :-1]
    previous = np.array([100., 70., 30., 2., .1])
    panel = np.exp(np.cumsum(increments.reshape(-1, 5), axis=0)).reshape(days, 288, 5) * previous
    available = core.START + np.arange(1, days + 1) * core.DAY
    real = np.ones(panel.shape, bool)
    rv1m = (increments * increments).sum(1) * (1.1 + rng.uniform(0, .2, (days, 5)))
    return panel, previous, available, real, rv1m


class Synthetic(unittest.TestCase):
    def test_path_order_signed_information_beyond_unsigned(self):
        # Same absolute returns, RV, RS, BV and net return; different signed adjacency.
        a = np.r_[np.full(216, .001), np.full(72, -.001)]
        b = np.r_[np.tile([.001, -.001], 72), np.full(144, .001)]
        r = np.column_stack([a] * 5)
        s = np.column_stack([b] * 5)
        p = np.exp(np.cumsum(r, axis=0))[None]
        q = np.exp(np.cumsum(s, axis=0))[None]
        args = (np.ones(5), np.array([core.START + core.DAY]), np.ones(p.shape, bool), np.ones(5, bool))
        first = core.path_statistics(p, *args)
        second = core.path_statistics(q, *args)
        for name in ('R1', 'RV', 'down_share', 'jump_share'):
            np.testing.assert_allclose(first[name], second[name], atol=1e-12, rtol=1e-10)
        self.assertGreater(float(np.max(np.abs(first['signed_serial'] - second['signed_serial']))), .1)

    def test_price_scale_and_sign_symmetry(self):
        p, prev, t, real, _ = fixture(3)
        a = core.path_statistics(p, prev, t, real, np.ones(5, bool))
        b = core.path_statistics(p * 11, prev * 11, t, real, np.ones(5, bool))
        c = core.path_statistics(1 / p, 1 / prev, t, real, np.ones(5, bool))
        for name in ('R1', 'RV', 'signed_serial'):
            np.testing.assert_allclose(a[name], b[name], atol=1e-12, rtol=1e-10)
        np.testing.assert_allclose(c['signed_serial'], a['signed_serial'], atol=1e-12)
        np.testing.assert_allclose(c['R1'], -a['R1'], atol=1e-12)

    def test_missing_derived_anchor_and_exact_288(self):
        p, prev, t, real, _ = fixture(3)
        unknown = prev.copy(); unknown[0] = np.nan
        z = core.path_statistics(p, unknown, t, real, np.ones(5, bool))
        self.assertFalse(z['ready'][0, 0])
        anchor = np.ones(5, bool); anchor[2] = False
        z = core.path_statistics(p, prev, t, real, anchor)
        self.assertFalse(z['ready'][0, 2])
        real[1, 45, 3] = False
        z = core.path_statistics(p, prev, t, real, np.ones(5, bool))
        self.assertFalse(z['ready'][1, 3])
        with self.assertRaises(ValueError):
            core.path_statistics(p[:, :-1], prev, t, real[:, :-1], np.ones(5, bool))
        with self.assertRaises(ValueError):
            core.path_statistics(p, prev, t[::-1], real, np.ones(5, bool))

    def test_future_price_quality_and_rv_invariance(self):
        p, prev, t, real, rv = fixture()
        x, reason = core.make_features(p, prev, t, real, rv, t, np.ones(5, bool))
        changed = p.copy(); changed[55:] *= 3; changed[62:] = np.nan
        changed_real = real.copy(); changed_real[55:] = False
        changed_rv = rv.copy(); changed_rv[55:] = np.nan
        y, why = core.make_features(changed, prev, t, changed_real, changed_rv, t, np.ones(5, bool))
        np.testing.assert_array_equal(x[:55], y[:55])
        np.testing.assert_array_equal(reason[:55], why[:55])

    def test_common_mask_strict_maturity_and_unknown_labels(self):
        d = np.arange(core.FIT_AT - 6 * core.DAY, core.FIT_AT, core.DAY, dtype=np.int64)
        x = np.ones((6, 5, len(core.ALL_NAMES))); y = np.ones((6, 5))
        x[0, 2, -1] = np.nan; y[1, 3] = np.nan
        mask = core.training_mask(d, x, y, d + 2 * core.DAY, minimum=0)
        np.testing.assert_array_equal(mask, [False, False, True, True, False, False])
        with self.assertRaises(AssertionError):
            core.training_mask(d, x, y, d + core.DAY, minimum=0)
        # Prediction eligibility cannot depend on future outcome quality.
        model = dict(fit_available_us=core.FIT_AT, feature_mean=np.zeros((5, 17)).tolist(),
                     feature_std=np.ones((5, 17)).tolist(), coefficients={arm: [
                         np.zeros(len(core.columns(j, arm == 'CANDIDATE')) + 1).tolist()
                         for j in range(5)] for arm in ('CONTROL', 'CANDIDATE')})
        _, ready = core.predict(model, d + 10 * core.DAY, x)
        np.testing.assert_array_equal(ready, [False, True, True, True, True, True])

    def test_structural_columns_and_no_rank_rescue(self):
        self.assertNotIn(core.ALL_NAMES.index('BTC_R1'), core.columns(0))
        self.assertNotIn(core.ALL_NAMES.index('ETH_R21'), core.columns(1))
        for asset in range(5):
            self.assertEqual(core.columns(asset, True)[:-1], core.columns(asset))
        d = core.START + np.arange(80) * core.DAY
        rng = np.random.default_rng(17); x = rng.normal(size=(80, 5, 17)); y = rng.normal(size=(80, 5))
        model = core.fit(d, x, y, d + 2 * core.DAY, minimum=60)
        self.assertEqual(model['extra_candidate_coefficients'], 5)
        self.assertTrue(all(b == a + 1 for a, b in zip(model['ranks']['CONTROL'], model['ranks']['CANDIDATE'])))
        x[:, :, 1] = x[:, :, 0]
        with self.assertRaisesRegex(ValueError, 'Rank-deficient'):
            core.fit(d, x, y, d + 2 * core.DAY, minimum=60)

    def test_price_cost_long_short_flat_and_unknown(self):
        mu = np.array([[.02, -.02, 0, np.nan, .02]])
        y = np.array([[.03, -.03, .01, 0, np.nan]])
        value, directions = core.price_cost_probe(mu, y)
        np.testing.assert_array_equal(directions, [[1, -1, 0, 0, 1]])
        self.assertGreater(value[0, 0], 0); self.assertGreater(value[0, 1], 0)
        self.assertEqual(value[0, 2], 0)
        self.assertTrue(np.isnan(value[0, 3:]).all())

    def test_natural_date_bootstrap_unknown_retention(self):
        a = np.arange(365, dtype=float) / 365; a[100:103] = np.nan
        first, starts, values = core.bootstrap(a)
        second, again, twice = core.bootstrap(a)
        np.testing.assert_array_equal(starts, again); np.testing.assert_array_equal(values, twice)
        self.assertEqual(first, second); self.assertEqual(starts.shape, (1000, 27))
        self.assertTrue(np.isfinite(values).all())

    def test_full_calendar_grid_and_no_compressed_gap(self):
        self.assertEqual([len(core.annual_grid(y)) for y in (2023, 2024, 2025)], [365, 366, 365])
        d = core.annual_grid(2023)
        with self.assertRaises(AssertionError):
            core.score({}, d[:-1], np.empty((364, 5, 17)), np.empty((364, 5)), d[:-1]+2*core.DAY, 2023)
        with self.assertRaises(AssertionError):
            core.score({}, np.delete(d, 100), np.empty((364, 5, 17)), np.empty((364, 5)), np.delete(d, 100)+2*core.DAY, 2023)


if __name__ == '__main__':
    unittest.main(verbosity=2)
