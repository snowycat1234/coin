"""Generated-array-only tests. No market arrays or actual outcome runs."""
import ast
from pathlib import Path
import unittest

import numpy as np

import analyze as a

HERE = Path(__file__).resolve().parent
ORIGINAL = HERE.parent / 'public_2023_source_restore/closure/source'


def original_public_targets():
    """Execute original function ASTs unchanged, skipping unrelated heavy imports."""
    namespace = {'np': np, 'DAY_US': a.DAY, 'WEEK_US': a.WEEK, 'ANCHOR_US': a.ANCHOR,
                 'market_neutral': a.load_original_ranker(ORIGINAL)}
    modules = [
        ('scripts/investment/public_sma_perpetual.py', {'require', 'symbol_order', 'signed_risk_weights'}),
        ('scripts/research/public_cross_section_momentum.py', {'public_targets'}),
    ]
    for name, functions in modules:
        tree = ast.parse((ORIGINAL / name).read_text())
        body = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name in functions]
        assert len(body) == len(functions)
        exec(compile(ast.Module(body=body, type_ignores=[]), str(ORIGINAL / name), 'exec'), namespace)
    return namespace['public_targets']


def generated_cube():
    times = np.arange(a.START - 70 * a.DAY, a.START + 60 * a.DAY, a.DAY, dtype=np.int64)
    t = np.arange(len(times))[:, None]
    trend = np.array([-.002, -.001, 0., .001, .002])[None, :]
    phases = np.arange(5)[None, :]
    prices = 100. * np.exp(t * trend + .08 * np.sin(t / 7. + phases))
    return times, prices


class Accounting(unittest.TestCase):
    def test_no_change_exact_zero(self):
        result = a.compare_baskets([], [])
        self.assertEqual(result['m'], 0)
        self.assertTrue(all(result[k] == 0 for k in a.METRICS))
        self.assertTrue(all(result['primary_' + k] == 0 for k in a.METRICS))

    def test_flat_asset_replacement_cost_only(self):
        one = a.member_costs(100., 100.)
        for m in (1, 2):
            result = a.compare_baskets([one] * m, [one] * m)
            self.assertAlmostEqual(result['keep_net'], -.00134956, places=14)
            self.assertAlmostEqual(result['switch_net'], -.00404956, places=14)
            self.assertAlmostEqual(result['delta_net'], -.0027, places=14)
            self.assertAlmostEqual(result['primary_delta_net'], -m / 2 * .0027, places=14)
            self.assertAlmostEqual(result['delta_fee'], .0011, places=14)
            self.assertAlmostEqual(result['delta_execution_cost'], .0016, places=14)

    def test_cash_transitions_flat_cost_only(self):
        one = a.member_costs(100., 100.)
        # Counts refer to differing non-CASH names after retained-name cancellation.
        for no, ni in [(0, 2), (2, 0), (1, 2), (2, 1), (0, 1), (1, 0)]:
            with self.subTest(outgoing=no, incoming=ni):
                result = a.compare_baskets([one] * no, [one] * ni)
                m = max(no, ni)
                self.assertAlmostEqual(result['keep_net'], -no / m * .00134956, places=14)
                self.assertAlmostEqual(result['switch_net'],
                                       -(no * .00134956 + ni * .0027) / m, places=14)
                # Selling an incumbent to CASH now vs at a flat-price terminal costs equally.
                self.assertAlmostEqual(result['delta_net'], -ni / m * .0027, places=14)
                self.assertAlmostEqual(result['primary_delta_net'], -ni * .00135, places=14)

    def test_zero_cost_zero_movement(self):
        member = a.member_costs(123., 123., fee=0., execution=0.)
        result = a.compare_baskets([member], [member])
        self.assertEqual(result['keep_net'], 0.)
        self.assertEqual(result['switch_net'], 0.)
        self.assertEqual(result['delta_net'], 0.)

    def test_zero_cost_price_only(self):
        outgoing = a.member_costs(100., 90., fee=0., execution=0.)
        incoming = a.member_costs(20., 24., fee=0., execution=0.)
        result = a.compare_baskets([outgoing], [incoming])
        self.assertAlmostEqual(result['delta_net'], .3)
        self.assertAlmostEqual(result['primary_delta_net'], .15)

    def test_terminal_fee_actual_fill_notional(self):
        member = a.member_costs(100., 170.)
        self.assertAlmostEqual(member['terminal_sell_fee'], .00055 * 1.7 * (1 - .0008))
        self.assertAlmostEqual(member['initial_buy_fee'], .00055 * (1 + .0008))
        self.assertAlmostEqual(member['initial_sell_fee'], .00055 * (1 - .0008))

    def test_generated_cashflow_reconciliation_and_pair_invariance(self):
        rng = np.random.default_rng(2131)
        for _ in range(300):
            no, ni = rng.integers(0, 3, size=2)
            if no == ni == 0:
                continue
            m = max(no, ni)
            out = [a.member_costs(float(p), float(p * r), float(f)) for p, r, f in
                   zip(rng.uniform(1, 100, no), rng.uniform(.5, 2, no), rng.uniform(-.01, .01, no))]
            inc = [a.member_costs(float(p), float(p * r), float(f)) for p, r, f in
                   zip(rng.uniform(1, 100, ni), rng.uniform(.5, 2, ni), rng.uniform(-.01, .01, ni))]
            result = a.compare_baskets(out, inc)
            cs = a.EXECUTION + a.FEE * (1 - a.EXECUTION)
            cb = a.EXECUTION + a.FEE * (1 + a.EXECUTION)
            # Independent final liquidation cash minus one initial reference dollar.
            keep = ((m - no) + sum((1 - cs) * x['exit'] / x['entry'] + x['funding']
                                   for x in out)) / m - 1
            start_cash = ((m - no) + no * (1 - cs) - ni * (1 + cb)) / m
            switch = start_cash + sum((1 - cs) * x['exit'] / x['entry'] + x['funding']
                                      for x in inc) / m - 1
            self.assertAlmostEqual(result['keep_net'], keep, places=13)
            self.assertAlmostEqual(result['switch_net'], switch, places=13)
            reverse = a.compare_baskets(list(reversed(out)), list(reversed(inc)))
            for key in a.METRICS:
                self.assertAlmostEqual(result[key], reverse[key], places=14)

    def test_same_funding_cancels_equal_assets(self):
        result = a.compare_baskets([a.member_costs(100., 110., -.003)],
                                   [a.member_costs(200., 220., -.003)])
        self.assertAlmostEqual(result['delta_net'], -.0027, places=14)
        self.assertAlmostEqual(result['delta_funding'], 0.)

    def test_equal_count_closed_form(self):
        out = a.member_costs(10., 9., -.01)
        inc = a.member_costs(20., 23., .004)
        result = a.compare_baskets([out], [inc])
        cs = a.EXECUTION + a.FEE * (1 - a.EXECUTION)
        self.assertAlmostEqual(result['delta_net'], (1 - cs) * (1.15 - .9) + .014 - .0027)


class Membership(unittest.TestCase):
    def setUp(self):
        self.ranker = a.load_original_ranker(ORIGINAL)

    def test_stable_tie_and_minimum_actual_original_ranker(self):
        scores = np.array([[0., 1., 1., 1., 1.]])
        weights = self.ranker(scores, np.ones_like(scores, dtype=bool), k=2, gross=.6)[0]
        self.assertEqual(a.names_for(weights > 0), [a.SYMBOLS[3], a.SYMBOLS[4]])
        self.assertFalse(self.ranker(np.ones((1, 5)), np.ones((1, 5), bool)).any())
        self.assertFalse(self.ranker(scores, np.array([[1, 1, 1, 0, 0]], bool)).any())

    def test_negative_absolute_momentum_can_be_long(self):
        times, close = generated_cube()
        close = 100. * np.exp(-np.arange(len(times))[:, None] * np.array([.01, .02, .03, .04, .05]))
        rows, _, _ = a.replacement_schedule(close, times, self.ranker, end=a.START + 30 * a.DAY)
        self.assertTrue(all(score < 0 for row in rows for score in row['momentum']))
        self.assertTrue(all(len(row['new_rank_long_names']) == 2 for row in rows))

    def test_original_public_targets_ast_differential(self):
        times, close = generated_cube()
        start, end = a.START, a.START + 49 * a.DAY
        rows, _, _ = a.replacement_schedule(close, times, self.ranker, start=start, end=end)
        # Start a day before the first requested day to expose incumbents at every Monday.
        decisions = np.arange(start - a.DAY, end, a.DAY, dtype=np.int64)
        weights, diagnostics = original_public_targets()(close, times, decisions, a.SYMBOLS, a.SYMBOLS)
        reference = {r['rank_us']: r for r in diagnostics['rank_events']}
        for row in rows:
            event = reference[row['rank_us']]
            self.assertEqual(row['new_rank_long_names'], a.names_for(np.array(event['raw_weights']) > 0))
            self.assertEqual(row['eligible'], event['eligible'])
            np.testing.assert_allclose(row['momentum'], event['momentum'])
            prior = int(np.searchsorted(decisions, row['rank_us'] - a.DAY))
            self.assertEqual(row['incumbent_before_rank'], a.names_for(weights[prior] > 0))

    def test_future_prices_do_not_change_earlier_memberships(self):
        times, close = generated_cube()
        cutoff = a.START + 22 * a.DAY
        rows, _, _ = a.replacement_schedule(close, times, self.ranker, end=a.START + 49 * a.DAY)
        changed = close.copy()
        changed[times > cutoff] *= np.array([100., .01, 20., .2, 5.])
        later, _, _ = a.replacement_schedule(changed, times, self.ranker, end=a.START + 49 * a.DAY)
        self.assertEqual([r for r in rows if r['rank_us'] <= cutoff],
                         [r for r in later if r['rank_us'] <= cutoff])

    def test_31_contiguous_closes_required_no_backfill(self):
        times, close = generated_cube()
        stamp = a.START
        index = np.searchsorted(times, stamp)
        broken = np.delete(times, index - 28)
        prices = np.delete(close, index - 28, axis=0)
        valid, scores = a.past_context(prices, broken, stamp)
        self.assertFalse(valid.any())
        self.assertIsNone(scores)
        # A missing 31st close cannot be ignored just because 22 closes are sufficient for momentum.
        close[index - 30, 0] = np.nan
        valid, _ = a.past_context(close, times, stamp)
        self.assertFalse(valid[0])

    def test_daily_clear_persists_until_rank_and_matches_original(self):
        times, close = generated_cube()
        initial, _, _ = a.replacement_schedule(close, times, self.ranker, end=a.START + 35 * a.DAY)
        first = initial[0]
        symbol = first['new_rank_long_names'][0]
        timestamp = first['rank_us'] + 2 * a.DAY
        close[np.searchsorted(times, timestamp), a.SYMBOLS.index(symbol)] = np.nan
        rows, forced, eligibility = a.replacement_schedule(close, times, self.ranker,
                                                          end=a.START + 35 * a.DAY)
        self.assertTrue(any(symbol in r['long_symbols'] for r in forced))
        self.assertNotIn(symbol, rows[1]['incumbent_before_rank'])
        status, problems = a.classify_week(rows[0], eligibility, forced)
        self.assertEqual(status, 'NOT_ESTIMABLE_FORCED_ELIGIBILITY')
        self.assertTrue(problems)
        decisions = np.arange(a.START, a.START + 35 * a.DAY, a.DAY, dtype=np.int64)
        weights, _ = original_public_targets()(close, times, decisions, a.SYMBOLS, a.SYMBOLS)
        prior = np.searchsorted(decisions, rows[1]['rank_us'] - a.DAY)
        self.assertEqual(rows[1]['incumbent_before_rank'], a.names_for(weights[prior] > 0))

    def test_boundary_excludes_even_unchanged_no_future_endpoint(self):
        row = {'entry_us': a.END - a.WEEK + a.MINUTE, 'exit_us': a.END + a.MINUTE,
               'm': 0}
        status, reasons = a.classify_week(row, {}, [])
        self.assertEqual(status, 'BOUNDARY_EXCLUDED')
        self.assertEqual(reasons[0]['required_exit_us'], a.END + a.MINUTE)

    def test_complete_no_change_is_not_dropped(self):
        stamp = a.START + a.DAY
        row = {'entry_us': stamp + a.MINUTE, 'exit_us': stamp + a.WEEK + a.MINUTE,
               'rank_us': stamp, 'm': 0, 'forced_at_rank': [], 'outgoing': [], 'incoming': []}
        eligibility = {t: np.ones(5, bool) for t in range(stamp, stamp + a.WEEK + a.DAY, a.DAY)}
        self.assertEqual(a.classify_week(row, eligibility, [])[0], 'COMPLETE_NO_CHANGE')


    def test_next_monday_invalid_before_actual_exit_fails_closed(self):
        stamp = a.START + a.DAY
        next_rank = stamp + a.WEEK
        row = {'entry_us': stamp + a.MINUTE, 'exit_us': next_rank + a.MINUTE,
               'rank_us': stamp, 'm': 1, 'forced_at_rank': [],
               'outgoing': [a.SYMBOLS[0]], 'incoming': [a.SYMBOLS[1]],
               'n_outgoing': 1, 'n_incoming': 1, 'preceding_daily_forced_clears': []}
        eligibility = {t: np.ones(5, bool) for t in range(stamp, next_rank + a.DAY, a.DAY)}
        self.assertEqual(a.classify_week(row, eligibility, [])[0], 'COMPLETE_RANK_REPLACEMENT')
        # Both differing paths remain exposed for a minute after next Monday's eligibility check.
        for asset in (0, 1):
            with self.subTest(endpoint_invalid_asset=asset):
                eligibility[next_rank][asset] = False
                status, reasons = a.classify_week(row, eligibility, [])
                self.assertEqual(status, 'NOT_ESTIMABLE_FORCED_ELIGIBILITY')
                self.assertTrue(any(r.get('decision_us') == next_rank for r in reasons))
                eligibility[next_rank][asset] = True
        # A forced retained-name clear at Tnext must also be caught, including no-change weeks.
        event = {'decision_us': next_rank, 'long_symbols': [a.SYMBOLS[2]],
                 'kind': 'AT_SCHEDULED_RANK'}
        status, reasons = a.classify_week(row, eligibility, [event])
        self.assertEqual(status, 'NOT_ESTIMABLE_FORCED_ELIGIBILITY')
        self.assertTrue(any(r.get('event') == event for r in reasons))
        unchanged = {**row, 'm': 0, 'outgoing': [], 'incoming': [],
                     'n_outgoing': 0, 'n_incoming': 0}
        self.assertEqual(a.classify_week(unchanged, eligibility, [event])[0],
                         'NOT_ESTIMABLE_FORCED_ELIGIBILITY')


class FundingAndUncertainty(unittest.TestCase):
    def test_actual_timestamp_not_slot_membership(self):
        events = [{'event_us': 1001, 'scheduled_slot_us': 1000},
                  {'event_us': 2001, 'scheduled_slot_us': 2000}]
        self.assertEqual(a.funding_events_between(events, 1000, 2000), [events[0]])
        self.assertEqual(a.funding_events_between(events, 1002, 2002), [events[1]])
        with self.assertRaises(ValueError):
            a.funding_events_between(events, 1001, 3000)
        with self.assertRaises(ValueError):
            a.funding_events_between(events, 0, 2001)

    def test_fractional_rate_long_sign_and_fixed_strict_past_mark(self):
        slot = 10 * a.MINUTE
        times = np.arange(0, 20 * a.MINUTE, a.MINUTE, dtype=np.int64)
        marks = np.full(len(times), 100.)
        marks[8] = 110.
        events = [{'event_us': slot + 29_000, 'scheduled_slot_us': slot, 'raw_rate': .001}]
        cash, rows = a.long_funding(a.SYMBOLS[0], slot - a.MINUTE, slot + a.MINUTE,
                                   100., events, marks, times)
        self.assertAlmostEqual(cash, -.0011, places=15)
        self.assertEqual(rows[0]['mark_bar_open_us'], slot - 2 * a.MINUTE)
        self.assertEqual(rows[0]['mark_logical_available_us'], slot - a.MINUTE)
        events[0]['raw_rate'] = -.001
        self.assertAlmostEqual(a.long_funding(a.SYMBOLS[0], slot - a.MINUTE, slot + a.MINUTE,
                                             100., events, marks, times)[0], .0011, places=15)

    def test_funding_grid_and_source_offsets_fail_closed(self):
        start, end = 0, 24 * 60 * a.MINUTE
        events = [{'symbol': s, 'event_us': t + 29_000, 'raw_rate': .0001,
                   'reported_interval_hours': 8.}
                  for s in a.SYMBOLS for t in range(start, end, 8 * 60 * a.MINUTE)]
        result = a.prepare_events(events, start, end)
        self.assertEqual(sum(map(len, result.values())), 15)
        for broken in (events[:-1], events + [events[0]]):
            with self.assertRaises(ValueError):
                a.prepare_events(broken, start, end)
        bad = [e.copy() for e in events]
        bad[0]['event_us'] = 1_000_001
        with self.assertRaises(ValueError):
            a.prepare_events(bad, start, end)

    def test_joint_two_week_bootstrap_deterministic_zero_weeks_retained(self):
        zero = a.compare_baskets([], [])
        change = a.compare_baskets([a.member_costs(100., 100.)], [a.member_costs(100., 110.)])
        rows = [zero, change, zero, change, zero]
        intervals = a.bootstrap(rows)
        self.assertEqual(intervals, a.bootstrap(rows))
        self.assertAlmostEqual(a.mean_components(rows)['delta_net'],
                               change['primary_delta_net'] * .4 * 10_000)
        self.assertNotEqual(a.mean_components(rows)['delta_net'],
                            a.mean_components([change])['delta_net'])
        all_zero = a.bootstrap([zero] * 5)
        self.assertTrue(all(bounds == [0., 0.] for bounds in all_zero.values()))


if __name__ == '__main__':
    unittest.main(verbosity=2)
