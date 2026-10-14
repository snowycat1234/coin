import unittest
import numpy as np
from core import DAY, HOUR, ANCHOR, EventStream, market_neutral, score_at, settled_sum, scheduled_ranks


def stream(start, days, rate=0., cadence=(8., 8., 8.), jitter=0):
    times, rates, hours = [], [], []
    for day in range(start, start + days * DAY, DAY):
        at = day
        for index, h in enumerate(cadence):
            times.append(at + jitter); rates.append(rate); hours.append(h)
            # Reported event h is the interval ending at that settlement.
            # The next event spacing therefore uses the NEXT reported h.
            if index + 1 < len(cadence):
                at += int(cadence[index + 1] * HOUR)
    certificate = {day: tuple(x for x in times if day <= x < day + DAY)
                   for day in range(start, start + days * DAY, DAY)}
    return EventStream(np.array(times, dtype=np.int64), np.array(rates), np.array(hours), certificate)


def fixture():
    d = ANCHOR
    t = np.arange(d - 40 * DAY, d + 5 * DAY, DAY, dtype=np.int64)
    slopes = np.array([.0001, .0002, .0003, .0004, .0005])
    p = 100 * (1 + slopes[None, :]) ** np.arange(len(t))[:, None]
    return d, t, p, np.ones_like(p, bool), [stream(d - 30 * DAY, 34) for _ in range(5)]


class FrozenTests(unittest.TestCase):
    def test_zero_funding_exact_same_lag_basket(self):
        d, t, p, m, e = fixture(); r = score_at(t, p, m, e, d)
        np.testing.assert_array_equal(r['price_score'], r['funding_adjusted_score'])
        np.testing.assert_array_equal(r['price_only_raw_basket'], r['funding_adjusted_raw_basket'])
        self.assertFalse(r['paired_basket_changed'])

    def test_variable_intervals_not_eight_hour_rescaled(self):
        d = ANCHOR
        e = stream(d - 23 * DAY, 22, .0001, cadence=(8., 2., 2., 4., 8.), jitter=6000)
        r = settled_sum(e, d)
        self.assertEqual(r['observed_events'], 105)
        self.assertAlmostEqual(r['value'], .0105)
        self.assertLess(r['latest_event_us'], d - DAY)

    def test_upper_boundary_and_future_suffix_not_read(self):
        d, t, p, m, e = fixture(); before = score_at(t, p, m, e, d)
        altered = []
        for s in e:
            rates = s.rates.copy(); rates[s.times >= d - DAY] = np.nan
            altered.append(EventStream(s.times, rates, s.hours, s.complete_day_event_ids))
        prices = p.copy(); prices[t > d] = np.nan
        after = score_at(t, prices, m, altered, d)
        np.testing.assert_array_equal(before['funding_adjusted_score'], after['funding_adjusted_score'])
        np.testing.assert_array_equal(before['funding_adjusted_raw_basket'], after['funding_adjusted_raw_basket'])

    def test_current_close_is_only_descriptive_or_readiness(self):
        d, t, p, m, e = fixture(); before = score_at(t, p, m, e, d)
        q = p.copy(); q[t == d] *= np.array([5., 4., 3., 2., 1.])
        after = score_at(t, q, m, e, d)
        np.testing.assert_array_equal(before['price_score'], after['price_score'])
        np.testing.assert_array_equal(before['funding_adjusted_score'], after['funding_adjusted_score'])

    def test_missing_settlement_is_not_zero_common_support(self):
        d, t, p, m, e = fixture(); s = e[0]
        keep = s.times != d - 10 * DAY
        e[0] = EventStream(s.times[keep], s.rates[keep], s.hours[keep], s.complete_day_event_ids)
        r = score_at(t, p, m, e, d)
        self.assertEqual(r['status'], 'NOT_READY_PAIRED_BASKETS')
        self.assertIsNone(r['funding_proof'][0]['value'])
        np.testing.assert_array_equal(r['price_only_raw_basket'], np.zeros(5))
        np.testing.assert_array_equal(r['funding_adjusted_raw_basket'], np.zeros(5))

    def test_bad_interval_hours_are_not_ready(self):
        e = stream(ANCHOR - 22 * DAY, 21); h = e.hours.copy(); h[2] = 4
        self.assertIsNone(settled_sum(EventStream(e.times, e.rates, h, e.complete_day_event_ids), ANCHOR)['value'])

    def test_asymmetric_cadence_ending_interval_not_forward_extrapolated(self):
        # Complete observed day has0/8/16/20/22h settlements. The first h is
        # the2h preceding interval; last h is2h too. Change last day so its
        # final2h interval differs from first8h, without inventing a next h.
        d = ANCHOR
        e = stream(d - 24 * DAY, 23, .0001)
        times, rates, hours = [], [], []
        for day in range(d - 24 * DAY, d - DAY, DAY):
            offsets = [0, 8, 16] if day < d - 2 * DAY else [0, 8, 16, 20, 22]
            for index, offset in enumerate(offsets):
                times.append(day + offset * HOUR)
                rates.append(.0001)
                hours.append(8. if index == 0 else float(offset - offsets[index - 1]))
        cert = {day: tuple(x for x in times if day <= x < day + DAY)
                for day in range(d - 24 * DAY, d - DAY, DAY)}
        a = EventStream(np.array(times, np.int64), np.array(rates), np.array(hours), cert)
        r = settled_sum(a, d)
        self.assertEqual(r['observed_events'], 65)
        self.assertAlmostEqual(r['value'], .0065)
        # Preceding reported hours add to510h here, not504h. No inferred
        # last2h accrual or future settlement is added to the rate sum.
        self.assertEqual(r['reported_interval_hours_sum'], 510.)

    def test_repeated_asymmetric_four_eight_hour_cadence(self):
        d = ANCHOR
        a = stream(d - 23 * DAY, 22, .0001, cadence=(4., 8., 4., 8.))
        r = settled_sum(a, d)
        self.assertEqual(r['observed_events'], 84)
        self.assertAlmostEqual(r['value'], .0084)

    def test_missing_final_event_is_not_hidden_by_forward_interval_guess(self):
        d, t, p, m, e = fixture(); s = e[0]
        keep = s.times != d - DAY - 8 * HOUR
        e[0] = EventStream(s.times[keep], s.rates[keep], s.hours[keep], s.complete_day_event_ids)
        self.assertIsNone(settled_sum(e[0], d)['value'])

    def test_missing_source_authority_is_unknown(self):
        d, t, p, m, e = fixture(); s = e[0]
        a = EventStream(s.times, s.rates, s.hours)
        self.assertIsNone(settled_sum(a, d)['value'])

    def test_original_all_five_gate_is_preserved(self):
        d, t, p, m, e = fixture(); m[t == d, 0] = False
        r = score_at(t, p, m, e, d)
        self.assertEqual(r['status'], 'NOT_READY_PAIRED_BASKETS')
        np.testing.assert_array_equal(r['funding_adjusted_raw_basket'], np.zeros(5))

    def test_original_mask_contradiction_stops(self):
        d, t, p, m, e = fixture(); p[t == d - 12 * DAY, 0] = np.nan
        with self.assertRaisesRegex(ValueError, 'contradicts'):
            score_at(t, p, m, e, d)

    def test_fully_tied_cash_and_stable_partial_ties(self):
        np.testing.assert_array_equal(market_neutral(np.ones(5), np.ones(5, bool)), np.zeros(5))
        np.testing.assert_array_equal(market_neutral([0, 0, 1, 2, 2], np.ones(5, bool)), [-.15, -.15, 0, .15, .15])
        np.testing.assert_array_equal(market_neutral([0, 1, 1, 1, 2], np.ones(5, bool)), [-.15, -.15, 0, .15, .15])

    def test_signed_funding_same_score_for_long_and_short(self):
        d, t, p, m, e = fixture(); e[4] = stream(d - 30 * DAY, 34, .002)
        r = score_at(t, p, m, e, d)
        self.assertGreater(r['price_only_raw_basket'][4], 0)
        self.assertLess(r['funding_adjusted_raw_basket'][4], 0)
        self.assertLess(r['funding_adjusted_score'][4], r['price_score'][4])
        e[0] = stream(d - 30 * DAY, 34, -.002)
        r = score_at(t, p, m, e, d)
        self.assertGreater(r['funding_adjusted_raw_basket'][0], 0)

    def test_constant_funding_shift_does_not_change_baskets(self):
        d, t, p, m, _ = fixture(); e = [stream(d - 30 * DAY, 34, .0001) for _ in range(5)]
        r = score_at(t, p, m, e, d)
        np.testing.assert_array_equal(r['price_only_raw_basket'], r['funding_adjusted_raw_basket'])

    def test_finite_rates_overflow_is_not_a_four_asset_fallback(self):
        d, t, p, m, e = fixture(); e[0] = stream(d - 30 * DAY, 34, 1e308)
        r = score_at(t, p, m, e, d)
        self.assertEqual(r['status'], 'NOT_READY_PAIRED_BASKETS')
        self.assertIsNone(r['funding_proof'][0]['value'])
        np.testing.assert_array_equal(r['funding_adjusted_raw_basket'], np.zeros(5))

    def test_finite_close_ratio_overflow_is_not_a_four_asset_fallback(self):
        d, t, p, m, e = fixture(); p[t == d - 22 * DAY, 0] = 1e-308; p[t == d - DAY, 0] = 1e308
        with np.errstate(over='ignore'):
            r = score_at(t, p, m, e, d)
        self.assertEqual(r['status'], 'NOT_READY_PAIRED_BASKETS')
        np.testing.assert_array_equal(r['funding_adjusted_raw_basket'], np.zeros(5))

    def test_weekly_anchor_preceding_rank_no_year_start_rerank(self):
        preceding, ranks = scheduled_ranks(ANCHOR + DAY, ANCHOR + 20 * DAY)
        self.assertEqual(preceding, ANCHOR)
        self.assertEqual(ranks, [ANCHOR + 7 * DAY, ANCHOR + 14 * DAY])

    def test_source_order_and_duplicate_event_rejected(self):
        d, t, p, m, e = fixture()
        with self.assertRaises(ValueError):
            score_at(t, p, m, e, d, symbols=('ETHUSDT', 'BTCUSDT', 'SOLUSDT', 'XRPUSDT', 'DOGEUSDT'))
        with self.assertRaises(ValueError):
            EventStream(np.array([d, d]), np.array([0., 0.]), np.array([8., 8.]))


if __name__ == '__main__':
    unittest.main(verbosity=2)
