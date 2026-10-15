"""Generated-only target, identity, risk and real Decimal-engine tests."""
import copy
from decimal import Decimal as D
import hashlib
import json
import unittest

import numpy as np

import frozen_grid as g


def returns_fixture():
    rng = np.random.default_rng(190713)
    return rng.normal(0, .004, (30, 5))


def prices_fixture():
    t = (19_000 + np.arange(230, dtype=np.int64)) * g.DAY
    j = np.arange(230)[:, None]
    drift = np.array([.002, .001, -.0015, -.0007, .0003])[None, :]
    increments = drift + .002 * np.sin(j * np.array([.29, .43, .59, .73, .89]))
    p = 100 * np.exp(np.cumsum(increments, axis=0))
    return p, t, t[205:220].copy()


class SourceTests(unittest.TestCase):
    def test_exact_twelve_public_sources(self):
        self.assertEqual(len(g.verify_sources()), 12)

    def test_original_six_source_manifest_all_exact(self):
        for rec in json.loads((g.HERE / 'sources/ORIGINAL_REFERENCE.json').read_text()):
            b = (g.HERE / 'sources' / rec['local_locator']).read_bytes()
            self.assertEqual(len(b), rec['bytes'])
            self.assertEqual(hashlib.sha256(b).hexdigest(), rec['SHA256'])

    def test_original_loader_executes_unmodified_functions(self):
        self.assertTrue(callable(g.originals().public_targets))
        self.assertTrue(callable(g.originals().scale))

    def test_fixed_nine_configurations(self):
        self.assertEqual(len(g.CONFIGS), 9)
        self.assertEqual(len(set(g.CONFIGS)), 9)
        self.assertEqual([(x.gross_cap, x.annual_vol_target) for x in g.TIERS],
                         [(.30, .05), (.60, .10), (.90, .15)])

    def test_unknown_tier_rejected(self):
        for bad in ('HIGHER', .9, None):
            with self.assertRaises(ValueError):
                g.tier_named(bad)

    def test_historical_run_remains_explicit_no_go(self):
        with self.assertRaisesRegex(RuntimeError, 'NO_GO'):
            g.require_historical_execution()


class RiskTests(unittest.TestCase):
    def setUp(self):
        self.r = returns_fixture()
        self.c = np.cov(self.r, rowvar=False, ddof=1) * 365
        self.w = np.array([.14, .14, -.01, -.01, .06])

    def test_each_tier_caps_and_forecast_vol(self):
        for tier in g.TIERS:
            w, info = g.scale_to_tier(self.w, self.c, tier.name)
            self.assertLessEqual(abs(w).max(), .30 + 1e-12)
            self.assertLessEqual(abs(w).sum(), tier.gross_cap + 1e-12)
            self.assertLessEqual(np.sqrt(w @ self.c @ w), tier.annual_vol_target + 1e-12)
            self.assertAlmostEqual(info['post_sigma'], np.sqrt(w @ self.c @ w))

    def test_medium_matches_exact_canonical_uniform_risk_function(self):
        expected, expected_meta = g.originals().scale(self.w, self.c)
        actual, actual_meta = g.scale_to_tier(self.w, self.c, 'MID')
        np.testing.assert_array_equal(actual, expected)
        self.assertEqual(actual_meta, expected_meta)

    def test_uniform_scale_preserves_sign_and_relative_proportions(self):
        for tier in g.TIERS:
            w, info = g.scale_to_tier(self.w, self.c, tier.name)
            np.testing.assert_array_equal(w, self.w * info['factor'])
            np.testing.assert_array_equal(np.sign(w), np.sign(self.w))

    def test_cash_not_reexpanded(self):
        for tier in g.TIERS:
            w, info = g.scale_to_tier(np.zeros(5), self.c, tier.name)
            np.testing.assert_array_equal(w, 0)
            self.assertEqual(info['reason'], 'INTRINSIC_CASH')
            self.assertFalse(info['risk_target_met'])

    def test_cap_bound_is_reported_instead_of_equal_risk_claim(self):
        w, info = g.scale_to_tier(self.w, np.eye(5) * 1e-5, 'HIGH')
        self.assertTrue(info['cap_bound'])
        self.assertGreater(info['shortfall'], 0)
        self.assertFalse(info['risk_target_met'])

    def test_degenerate_nonzero_risk_rejected(self):
        with self.assertRaisesRegex(ValueError, 'DEGENERATE'):
            g.scale_to_tier(self.w, np.zeros((5, 5)), 'MID')

    def test_nonfinite_weight_rejected(self):
        for value in (np.nan, np.inf):
            w = self.w.copy(); w[0] = value
            with self.assertRaises(ValueError):
                g.scale_to_tier(w, self.c, 'MID')

    def test_shape_and_input_caps_rejected(self):
        for w in (np.ones(4), np.array([.31, 0, 0, 0, 0]), np.full(5, .2)):
            with self.assertRaises(ValueError):
                g.scale_to_tier(w, self.c, 'MID')

    def test_asymmetric_nonfinite_nonpsd_covariance_rejected(self):
        bad = []
        c = self.c.copy(); c[0, 1] += .01; bad.append(c)
        c = self.c.copy(); c[0, 0] = np.inf; bad.append(c)
        bad.append(-np.eye(5))
        for c in bad:
            with self.assertRaises(ValueError):
                g.scale_to_tier(self.w, c, 'MID')

    def test_no_input_mutation(self):
        w, c = self.w.copy(), self.c.copy()
        g.scale_to_tier(w, c, 'HIGH')
        np.testing.assert_array_equal(w, self.w)
        np.testing.assert_array_equal(c, self.c)

    def test_h090_exact_once_and_hold_original(self):
        cs, _ = g.originals().signed_risk_weights([.15, .15, -.15, -.15, 0], self.r)
        intents, c, proof = g.canonical_intents(cs, self.r)
        expected, _, ec = g._h090()._math(1.5 * intents['STATIC50'], self.r, .90, .30, .15)
        np.testing.assert_array_equal(intents['H090'], expected)
        np.testing.assert_array_equal(c, ec)
        hold, _ = g.originals().signed_risk_weights(np.full(5, .12), self.r)
        np.testing.assert_array_equal(intents['VOL_MANAGED_HOLD'], hold)
        self.assertFalse(proof['new_alpha_claim'])

    def test_complete_zero_risk_cs_matches_generic_original_cash_semantics(self):
        r = np.tile(((np.arange(30) % 2) * 2. - 1.)[:, None] / 64., (1, 5))
        cs = np.array([.15, .15, -.15, -.15, 0.])
        intents, _, proof = g.canonical_intents(cs, r)
        np.testing.assert_array_equal(intents['STATIC50'], 0.)
        np.testing.assert_array_equal(intents['H090'], 0.)
        self.assertGreater(abs(intents['VOL_MANAGED_HOLD']).sum(), 0)
        self.assertEqual(proof['common_matched_sigma'], 0.)

    def test_old_static_and_retargeted_are_distinct_fields(self):
        cs, _ = g.originals().signed_risk_weights([.15, .15, -.15, -.15, 0], self.r)
        intents, c, proof = g.canonical_intents(cs, self.r)
        old = np.asarray(proof['STATIC50_OLD_NO_REEXPANSION'])
        expected, _ = g.originals().scale(old, c)
        np.testing.assert_array_equal(intents['STATIC50'], expected)

    def test_h090_no_clip_normalizes_same_signal(self):
        c = np.eye(5) * .25
        base = np.array([.05, .04, -.03, -.02, .03])
        for tier in g.TIERS:
            a, _ = g.scale_to_tier(base, c, tier.name)
            b, _ = g.scale_to_tier(base * 1.5, c, tier.name)
            np.testing.assert_allclose(a, b, rtol=0, atol=1e-15)

    def test_h090_clip_can_change_shape(self):
        raw = np.array([.25, .20, .05, -.05, .05])
        # Construct zero-mean sample returns with very small nondegenerate risk.
        r = self.r * .01
        h090, _, c = g._h090()._math(raw * 1.5, r, .90, .30, .15)
        a, _ = g.scale_to_tier(raw, c, 'MID')
        b, _ = g.scale_to_tier(h090, c, 'MID')
        self.assertFalse(np.allclose(a, b, rtol=0, atol=1e-12))


class ClockAndIdentityTests(unittest.TestCase):
    def setUp(self):
        self.p, self.t, self.d = prices_fixture()

    def test_generated_grid_all_nine_and_clocks(self):
        d, arrays, cov, proof = g.build_target_grid(self.p, self.t, self.t.copy(), self.d)
        np.testing.assert_array_equal(d, self.d)
        self.assertEqual(len(arrays), 9)
        self.assertEqual(cov.shape, (len(d), 5, 5))
        for row in proof:
            self.assertLessEqual(row['last_close_available_us'], row['decision_us'])
            self.assertEqual(len(row['tiers']), 9)

    def test_future_prices_do_not_change_past_targets(self):
        d = self.d[:4]
        _, a, _, _ = g.build_target_grid(self.p, self.t, self.t.copy(), d)
        later = self.p.copy(); later[210:] *= np.linspace(1, 100, 20)[:, None]
        _, b, _, _ = g.build_target_grid(later, self.t, self.t.copy(), d)
        for key in a:
            np.testing.assert_array_equal(a[key], b[key])

    def test_missing_or_late_daily_bar_is_not_imputed(self):
        for kind in ('missing', 'late', 'nan', 'nonpositive'):
            p, t, a = self.p.copy(), self.t.copy(), self.t.copy()
            if kind == 'missing': p, t, a = np.delete(p, 100, 0), np.delete(t, 100), np.delete(a, 100)
            elif kind == 'late': a[100] += g.DAY
            elif kind == 'nan': p[100, 0] = np.nan
            else: p[100, 0] = 0
            with self.assertRaises(ValueError):
                g.build_target_grid(p, t, a, self.d)

    def test_warmup_under200_rejected(self):
        with self.assertRaisesRegex(ValueError, '200'):
            g.build_target_grid(self.p, self.t, self.t.copy(), self.t[190:195])

    def test_symbol_order_rejected(self):
        with self.assertRaisesRegex(ValueError, 'ORDER'):
            g.build_target_grid(self.p, self.t, self.t.copy(), self.d, symbols=g.SYMBOLS[::-1])

    def test_float_duplicate_or_non_daily_clocks_rejected(self):
        for t in (self.t.astype(float), np.zeros_like(self.t), self.t + 1):
            with self.assertRaises(ValueError):
                g.build_target_grid(self.p, t, t.copy(), self.d)

    def test_exact_dedup_across_full_calendar(self):
        arrays = {s + '_' + t: np.zeros((len(self.d), 5)) for s, t in g.CONFIGS}
        info = g.target_identities(self.d, arrays)
        self.assertEqual(info['distinct_target_paths'], 1)
        self.assertFalse(info['independent_alpha_families_claimed'])

    def test_one_bit_change_is_not_deduplicated(self):
        arrays = {s + '_' + t: np.zeros((len(self.d), 5)) for s, t in g.CONFIGS}
        arrays['H090_HIGH'][0, 0] = np.nextafter(0., 1.)
        self.assertEqual(g.target_identities(self.d, arrays)['distinct_target_paths'], 2)

    def test_equal_targets_never_reuse_across_different_tiers(self):
        arrays = {s + '_' + t: np.zeros((len(self.d), 5)) for s, t in g.CONFIGS}
        info = g.target_identities(self.d, arrays)
        self.assertFalse(info['execution_reuse_authorized_by_target_equality'])
        groups = g.execution_reuse_groups(self.d, arrays, source_identity='a'*64,
            cost_name='BASE27', execution_identity='b'*64)
        self.assertEqual(len(groups), 3)
        for group in groups:
            self.assertEqual(len({x.rsplit('_', 1)[1] for x in group}), 1)

    def test_dedup_rejects_incomplete_grid(self):
        with self.assertRaises(ValueError):
            g.target_identities(self.d, {})


class ExactAccountTests(unittest.TestCase):
    def test_same_engine_and_frozen_costs_all_tiers(self):
        classes = set()
        for tier in g.TIERS:
            for cost, rt in (('BASE27', 27), ('STRESS43', 43)):
                a = g.make_account(tier.name, cost); classes.add(type(a))
                self.assertEqual(a.config.initial_cash, D(10000))
                self.assertEqual(a.config.max_gross_weight, D(str(tier.gross_cap)))
                self.assertEqual(a.config.max_asset_weight, D('.30'))
                self.assertEqual(a.config.leverage, D(1))
                self.assertEqual(a.contract_metadata()['nominal_roundtrip_bps'], rt)
                self.assertTrue(a.closing_min_notional_exempt)
        self.assertEqual(len(classes), 1)

    def test_unknown_cost_rejected(self):
        with self.assertRaises(ValueError):
            g.make_account('MID', 'FREE')

    def test_declared_coarse_quantity_profile_preserved(self):
        a = g.make_account('HIGH')
        self.assertEqual([str(a.instrument_profiles[s].quantity_step) for s in g.SYMBOLS],
                         ['0.001', '0.01', '1', '100', '1000'])

    def test_actual_generated_fill_and_cost_bridge_each_tier(self):
        for tier in g.TIERS:
            a = g.make_account(tier.name)
            a.update_marks(0, {s: dict(price='100', close_us=0, available_us=0) for s in g.SYMBOLS})
            receipt = a.execute_fill('BTCUSDT', 'BUY', '1', 60_000_001, 0, 'generated-open',
                execution_mid_price='100', quote_available_us=60_000_000, available_quantity='1')
            self.assertEqual(receipt['status'], 'FILLED')
            summary = a.summary()
            self.assertEqual(summary['decimal_strings']['accounting_bridge_error_USDT'], '0E-9')
            self.assertEqual(a.positions['BTCUSDT'].quantity, D(1))
            self.assertGreater(a.fees, 0)
            self.assertGreater(a.execution_cost, 0)

    def test_actual_generated_gross_cap_rejects_increase(self):
        for tier in g.TIERS:
            a = g.make_account(tier.name)
            a.update_marks(0, {s: dict(price='100', close_us=0, available_us=0) for s in g.SYMBOLS})
            target_total = 0
            for i, symbol in enumerate(g.SYMBOLS):
                q = '25' if symbol in ('BTCUSDT', 'ETHUSDT', 'SOLUSDT') else '1000'
                a.execute_fill(symbol, 'BUY', q, 60_000_001 + i, 0, 'generated-' + symbol,
                    execution_mid_price='100', quote_available_us=60_000_000, available_quantity=q)
                target_total += 1
            nav = a.nav()
            notionals = [abs(p.quantity) * a._mark(s) for s, p in a.positions.items()]
            self.assertLessEqual(sum(notionals), a.config.max_gross_weight * nav)
            self.assertTrue(any(row['receipt']['status'] == 'REJECTED' for row in a.fill_requests.values()))

    def test_fresh_fill_guard_and_history_status_honest(self):
        for tier in g.TIERS:
            binding = g.account_contract(tier.name)
            self.assertEqual(binding['annual_vol_actual_fill_guard_status'], 'NOT_INTEGRATED_FOR_NEW_GRID')
            self.assertFalse(binding['native_venue_certified'])


if __name__ == '__main__':
    unittest.main()
