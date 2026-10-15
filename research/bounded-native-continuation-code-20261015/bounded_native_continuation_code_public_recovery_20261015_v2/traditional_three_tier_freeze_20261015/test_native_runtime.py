"""Generated-only multi-day native/owned/tier guard integration checks."""
from copy import deepcopy
from decimal import Decimal as D
import unittest

import numpy as np
import polars as pl

import frozen_grid as g
import native_runtime as n
from test_frozen_grid import prices_fixture


BASE = np.array([50000., 2000., 20., .5, .05])
COST = dict(id='BASE27', half_spread_bps=4, slippage_bps=4, roundtrip_bps=27)


def fixture(days=3):
    p, t, d = prices_fixture()
    p = p / 100 * BASE
    d = d[:days]
    rows = [dict(symbol=s, close_us=int(at), available_us=int(at), close=float(p[i, j]))
            for i, at in enumerate(t) for j, s in enumerate(g.SYMBOLS)]
    start, end = int(d[0]), int(d[-1] + g.DAY)
    count = (end - start) // n.MINUTE
    events = [dict(symbol=s, event_us=int(day + 8 * 60 * n.MINUTE), raw_rate=.0001,
                   reported_interval_hours=8.) for day in d for s in g.SYMBOLS]
    window = dict(start=start, end=end, symbols=g.SYMBOLS,
        daily=pl.DataFrame(rows), events=events, fixture_scope='GENERATED_FAKE_ORIGIN_ONLY',
        market={s: dict(open=np.full(count, BASE[j]), close=np.full(count, BASE[j]),
            mark=np.full(count, BASE[j]), quote_volume=np.full(count, 1e10))
            for j, s in enumerate(g.SYMBOLS)})
    return window, rows, d.astype(np.int64)


def make_case(tier='MID', days=3, weights=None):
    window, rows, d = fixture(days)
    if weights is None:
        weights = np.full((days, 5), .03)
    return n.build_case(window, rows, d, weights, tier_name=tier,
        generated_scope='GENERATED_FAKE_ORIGIN_ONLY')


class NativeIntegrationTests(unittest.TestCase):
    def test_generated_three_days_all_nine_configs_paid(self):
        for strategy in g.STRATEGIES:
            for tier in g.TIERS:
                with self.subTest(strategy=strategy, tier=tier.name):
                    weights = np.full((3, 5), .02 if strategy == 'H090' else .03)
                    sim, guard = make_case(tier.name, weights=weights)
                    while sim.cursor < sim.end and sim.stop is None:
                        sim.advance_day()
                    result = sim.result(); summary = result['summary']
                    self.assertIsNone(sim.stop)
                    self.assertEqual(summary['completed_minutes'], 3 * 1440)
                    self.assertTrue(summary['terminal_cash_realized'])
                    self.assertEqual(summary['terminal_marked_notional'], 0)
                    self.assertEqual(sim.account.unpaid_liability, 0)
                    self.assertEqual(D(summary['decimal_strings']['accounting_bridge_error_USDT']), 0)
                    self.assertTrue(any(r['phase'] == 'INITIAL_SIGNAL_DEFERRED_UNKNOWN_PRIOR_QUOTE' for r in guard.receipts))
                    admit = next(r for r in guard.receipts if r['phase'] == 'INITIAL_INTENT_ADMITTED_REAL_QUOTE')
                    self.assertEqual(admit['admission_us'], sim.start + n.MINUTE + 1)
                    self.assertIsNotNone(summary['first_entry_us'])
                    self.assertGreaterEqual(summary['first_entry_us'], sim.start + n.MINUTE + 1)
                    self.assertGreater(summary['trade_legs'], 0)
                    self.assertEqual(summary['funding_observed_events'], 15)
                    self.assertGreater(summary['fees_USDT'], 0)
                    self.assertGreater(summary['execution_cost_USDT'], 0)
                    self.assertGreater(sim.account.funding_cash.__abs__(), 0)

    def test_native_finance_and_attempt_methods_are_inherited(self):
        engine, scheduler, terminal, _, owned, _ = n.runtime()
        self.assertIs(owned.OwnedFineGridAccount.execute_fill, engine.USDTLinearPerpetualAccount.execute_fill)
        self.assertIs(owned.OwnedFineGridAccount.apply_funding, engine.USDTLinearPerpetualAccount.apply_funding)
        self.assertIs(owned.OwnedFineGridAccount._leg, engine.USDTLinearPerpetualAccount._leg)
        self.assertIs(terminal.EarlierTerminalSimulator.advance_day, scheduler.NativeDailySimulator.advance_day)

    def test_initial_no_quote_no_pending_or_fill_until_real_quote(self):
        sim, guard = make_case(days=1)
        day = sim.tape.day(sim.start)
        # A single direct signal phase reproduces only the fresh initial queue.
        raw = {s: D('1') for s in g.SYMBOLS}
        guard.schedule(raw, sim.start, dict.fromkeys(g.SYMBOLS, 'DAILY_TARGET'))
        self.assertEqual(sim.pending, {})
        guard.attempt(sim.start, day[0][1])
        self.assertEqual(len(sim.account.trades), 0)
        self.assertEqual(sim.pending, {})

    def test_unknown_quote_never_general_fallback(self):
        sim, guard = make_case(days=1)
        sim.rows_written = 2
        with self.assertRaisesRegex(ValueError, 'FRESH_FLAT'):
            guard.schedule(dict.fromkeys(g.SYMBOLS, D('1')), sim.start,
                           dict.fromkeys(g.SYMBOLS, 'DAILY_TARGET'))

    def test_source_late_daily_close_rejected_before_fill(self):
        window, rows, d = fixture(1)
        for row in rows:
            if row['close_us'] == int(d[0]): row['available_us'] += g.DAY
        sim, guard = n.build_case(window, rows, d, np.full((1, 5), .02),
            tier_name='MID', generated_scope='GENERATED_FAKE_ORIGIN_ONLY')
        with self.assertRaisesRegex(ValueError, 'FUTURE_SIGNAL'):
            sim.advance_day()
        self.assertFalse(sim.account.trades)

    def test_target_tier_cap_rejected_before_construction(self):
        window, rows, d = fixture(1)
        with self.assertRaisesRegex(ValueError, 'TIER_CORE5'):
            n.build_case(window, rows, d, np.full((1, 5), .1), tier_name='LOW',
                generated_scope='GENERATED_FAKE_ORIGIN_ONLY')

    def test_real_data_scope_needs_exact_admission(self):
        window, rows, d = fixture(1)
        for approval in (None, True, b'{}'):
            with self.assertRaises(ValueError):
                n.build_case(window, rows, d, np.full((1, 5), .02),
                    tier_name='MID', admission=approval)


class OwnedFreshPreviewTests(unittest.TestCase):
    def prepare(self, tier='MID'):
        window, rows, d = fixture(1)
        a = n.make_owned_account(tier, COST)
        signal = int(d[0]); event = signal + n.MINUTE + 1
        a.update_marks(signal, {s: dict(price=str(BASE[j]), close_us=signal,
            available_us=signal) for j, s in enumerate(g.SYMBOLS)})
        binding = n.runtime()[5].CompletedBarSource(rows).bind(signal)
        kwargs = dict(binding=binding, prices=dict(zip(g.SYMBOLS, BASE)),
            price_available_us=dict.fromkeys(g.SYMBOLS, signal+n.MINUTE),
            pending=dict.fromkeys(g.SYMBOLS, D(0)),
            capacity=dict.fromkeys(g.SYMBOLS, D('10000000')),
            event_us=event, signal_us=signal, quote_available_us=signal+n.MINUTE)
        return a, kwargs

    def test_preview_does_not_change_live_account_and_commits_real_paid_fill(self):
        for tier in g.TIERS:
            a, kwargs = self.prepare(tier.name)
            target = dict(zip(g.SYMBOLS, map(D, ['.001', '.01', '1', '100', '1000'])))
            kwargs['pending'] = target
            before = a.preview_state_token()
            preview = n.fresh_preview(a, tier_name=tier.name, **kwargs)
            witness = preview.evaluate(target, D(1))
            self.assertTrue(witness['allowed'], witness.get('reason'))
            self.assertEqual(a.preview_state_token(), before)
            self.assertEqual(len(a.trades), 0)
            self.assertGreater(len(witness['corners_checked']), 1)
            r = a.execute_fill('BTCUSDT', 'BUY', '.001', kwargs['event_us'], kwargs['signal_us'],
                'generated-direct-commit', execution_mid_price=str(BASE[0]),
                quote_available_us=kwargs['quote_available_us'], available_quantity='.001')
            self.assertEqual(r['status'], 'FILLED')
            self.assertGreater(a.fees, 0)

    def test_preview_tier_must_match_account(self):
        a, kwargs = self.prepare('LOW')
        with self.assertRaisesRegex(ValueError, 'TIER'):
            n.fresh_preview(a, tier_name='HIGH', **kwargs)

    def test_flat_signal_preview_preserves_distinct_same_clock_native_mark(self):
        a, kwargs = self.prepare('MID')
        binding = kwargs['binding']
        self.assertTrue(any(a._mark(s) != D(binding.prices[i]) for i, s in enumerate(g.SYMBOLS)))
        before = a.preview_state_token()
        oracle = n.signal_preview(a, binding, dict.fromkeys(g.SYMBOLS, D('1e10')),
            binding.signal_us, tier_name='MID', admission_us=binding.signal_us+n.MINUTE+1)
        self.assertEqual(a.preview_state_token(), before)
        for s in g.SYMBOLS:
            self.assertEqual(oracle.account._mark(s), a._mark(s))

    def test_fresh_flat_missing_marks_seed_only_detached_signal_probe(self):
        _, kwargs = self.prepare('MID')
        binding = kwargs['binding']
        account = n.make_owned_account('MID', COST)
        before = account.preview_state_token()
        oracle = n.signal_preview(account, binding, dict.fromkeys(g.SYMBOLS, D('1e10')),
            binding.signal_us+n.MINUTE, tier_name='MID', admission_us=binding.signal_us+n.MINUTE+1)
        self.assertEqual(account.preview_state_token(), before)
        self.assertTrue(all(not account.marks[s] for s in g.SYMBOLS))
        for i, s in enumerate(g.SYMBOLS):
            self.assertEqual(oracle.account._mark(s), D(binding.prices[i]))

    def test_owned_fork_isolation_and_historical_journal_edit_rejection(self):
        a, kwargs = self.prepare('HIGH')
        b = n.runtime()[4].fork_owned_account(a)
        b.execute_fill('BTCUSDT', 'BUY', '.001', kwargs['event_us'], kwargs['signal_us'],
            'generated-fork-only', execution_mid_price=str(BASE[0]),
            quote_available_us=kwargs['quote_available_us'], available_quantity='.001')
        self.assertEqual(len(a.trades), 0)
        self.assertEqual(len(b.trades), 1)
        with self.assertRaises(TypeError):
            b.trades[0] = {}
        with self.assertRaises(TypeError):
            b.fill_requests['generated-fork-only'] = {}

    def test_preview_capacity_partial_fails_closed(self):
        a, kwargs = self.prepare('MID')
        target = dict.fromkeys(g.SYMBOLS, D(0)); target['BTCUSDT'] = D('.01')
        kwargs['pending'] = target; kwargs['capacity']['BTCUSDT'] = D('.001')
        before = a.preview_state_token()
        witness = n.fresh_preview(a, tier_name='MID', **kwargs).evaluate(target, D(1))
        self.assertFalse(witness['allowed'])
        self.assertEqual(a.preview_state_token(), before)

    def test_high_volatility_corner_fails_closed(self):
        a, kwargs = self.prepare('MID')
        binding = kwargs['binding']
        from dataclasses import replace
        kwargs['binding'] = replace(binding, covariance=tuple(tuple(float(x) for x in r) for r in np.eye(5)*10000))
        target = dict.fromkeys(g.SYMBOLS, D(0)); target['BTCUSDT'] = D('.01')
        kwargs['pending'] = target
        witness = n.fresh_preview(a, tier_name='MID', **kwargs).evaluate(target, D(1))
        self.assertFalse(witness['allowed'])

    def test_exact_capital_dry_run_commit_and_duplicate_single_charge(self):
        for tier in g.TIERS:
            a, kwargs = self.prepare(tier.name)
            args = ('BTCUSDT', 'BUY', '.001', kwargs['event_us'], kwargs['signal_us'], 'capital-once')
            kw = dict(execution_mid_price=str(BASE[0]), quote_available_us=kwargs['quote_available_us'],
                      available_quantity='.001')
            receipt = n.capital_guard_fill(a, *args, **kw)
            self.assertEqual(receipt['status'], 'FILLED')
            state = a.snapshot()
            self.assertEqual(n.capital_guard_fill(a, *args, **kw), receipt)
            self.assertEqual(a.snapshot(), state)
            with self.assertRaisesRegex(ValueError, 'conflicting fill identity'):
                n.capital_guard_fill(a, *(args[:-1] + ('capital-once',)), **{**kw, 'available_quantity': '.002'})

    def test_capital_token_equality_exactly_tracks_native_snapshot(self):
        a, kwargs = self.prepare('HIGH')
        b = n.runtime()[4].fork_owned_account(a)
        self.assertEqual(n._ExactCapitalToken(a), n._ExactCapitalToken(b))
        args = ('BTCUSDT', 'BUY', '.001', kwargs['event_us'], kwargs['signal_us'], 'same-both')
        kw = dict(execution_mid_price=str(BASE[0]), quote_available_us=kwargs['quote_available_us'], available_quantity='.001')
        a.execute_fill(*args, **kw); b.execute_fill(*args, **kw)
        self.assertIsNot(a.trades._root, b.trades._root)
        self.assertEqual(a.snapshot(), b.snapshot())
        self.assertEqual(n._ExactCapitalToken(a), n._ExactCapitalToken(b))
        b.free_cash -= D('.0000000001')
        self.assertNotEqual(a.snapshot(), b.snapshot())
        self.assertNotEqual(n._ExactCapitalToken(a), n._ExactCapitalToken(b))

    def test_capital_cash_floor_rejects_increases_but_not_reduce_only(self):
        a, kwargs = self.prepare('HIGH')
        a.free_cash = D('999')  # Explicit generated damaged-state boundary.
        before = a.preview_state_token()
        receipt = n.capital_guard_fill(a, 'BTCUSDT', 'BUY', '.001', kwargs['event_us'],
            kwargs['signal_us'], 'floor-reject', execution_mid_price=str(BASE[0]),
            quote_available_us=kwargs['quote_available_us'], available_quantity='.001')
        self.assertEqual(receipt['reason'], 'INITIAL_CASH_FLOOR_BREACHED')
        self.assertEqual(a.preview_state_token(), before)
        # A true reduce-only request is delegated even below the increase floor.
        receipt = n.capital_guard_fill(a, 'BTCUSDT', 'SELL', '.001', kwargs['event_us'],
            kwargs['signal_us'], 'floor-reduce-no-position', execution_mid_price=str(BASE[0]),
            quote_available_us=kwargs['quote_available_us'], available_quantity='.001', reduce_only=True)
        self.assertEqual(receipt['reason'], 'REDUCE_ONLY_NO_OPPOSITE_POSITION')

    def test_capital_margin_ceiling_rejects_paid_dry_run_without_commit(self):
        a, kwargs = self.prepare('HIGH')
        signal, event = kwargs['signal_us'], kwargs['event_us']
        for i, symbol in enumerate(g.SYMBOLS[:3]):
            price = BASE[i]
            # Three .28-NAV legs fit .90gross but the third exceeds 8500margin.
            q = a._floor(symbol, D('2800') / D(str(price)))
            receipt = n.capital_guard_fill(a, symbol, 'BUY', q, event+i, signal,
                'margin-' + symbol, execution_mid_price=str(price),
                quote_available_us=event-1, available_quantity=q)
            self.assertEqual(receipt['status'], 'FILLED')
        before = a.preview_state_token()
        receipt = n.capital_guard_fill(a, 'XRPUSDT', 'BUY', '400', event+4, signal,
            'margin-overflow', execution_mid_price='.5', quote_available_us=event-1,
            available_quantity='400')
        self.assertEqual(receipt['status'], 'POLICY_REJECTED')
        self.assertEqual(a.preview_state_token(), before)

    def test_common_capital_limits_are_part_of_each_pending_corner(self):
        a, kwargs = self.prepare('HIGH')
        # The .90 target ceiling does not promise achievable .90gross when the
        # common fixed8500margin/1000cash constraints bind.
        target = {s: a._floor(s, D('1790') / D(str(BASE[i]))) for i, s in enumerate(g.SYMBOLS)}
        kwargs['pending'] = target
        witness = n.fresh_preview(a, tier_name='HIGH', **kwargs).evaluate(target, D(1))
        self.assertFalse(witness['allowed'])
        self.assertEqual(len(a.trades), 0)


if __name__ == '__main__':
    unittest.main()
