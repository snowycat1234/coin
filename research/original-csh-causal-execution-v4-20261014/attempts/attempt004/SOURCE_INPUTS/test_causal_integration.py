"""Generated fixtures only: no history, network, targets from a market archive or annual run."""
import unittest
from copy import deepcopy
from decimal import Decimal as D
import numpy as np
import polars as pl
from candidate import S, FRACTIONS
from fine_account import FineGridAccount
from native_control import NATIVE
from causal_adapter import CompletedBarSource, CausalPartialAdapter, FreshExecutionPreview, DAY

MINUTE = 60_000_000
SIGNAL = 32*DAY


class Tests(unittest.TestCase):
    def vec(self, *values):
        return dict(zip(S, (D(str(x)) for x in (values or (0, 0, 0, 0, 0)))))

    def source(self, volatile=(S[0],), *, future_symbol=None, future_cov=False, future_book=False):
        rows = []
        for symbol in S:
            prices = [D(100)]*31
            if symbol in volatile:
                for i in range(29, -1, -1):
                    prices[i] = prices[i+1]/(D(1)+(D('.03') if i % 2 else D('-.03')))
            for i, price in enumerate(prices):
                stamp = SIGNAL-(30-i)*DAY
                available = stamp
                if symbol == future_symbol and i == 30 or future_cov and symbol == S[0] and i == 0:
                    available = SIGNAL+1
                rows.append(dict(symbol=symbol, close_us=stamp, available_us=available, close=str(price)))
            if future_book:
                rows.append(dict(symbol=symbol, close_us=SIGNAL+DAY,
                                 available_us=SIGNAL+DAY, close='999999'))
        return CompletedBarSource(rows)

    def sim(self, *, events=None, quote=100000000):
        window = {'start': SIGNAL, 'end': SIGNAL+DAY, 'symbols': S,
            'daily': pl.DataFrame([{'symbol': s, 'close_us': SIGNAL, 'close': 100.} for s in S]),
            'events': events or [], 'market': {s: {k: np.full(1440,
                float(quote) if k == 'quote_volume' else 100.)
                for k in ('open', 'close', 'mark', 'quote_volume')} for s in S}}
        sim = NATIVE(window, 'LONG_SHORT',
            {'id': 'BASE27', 'half_spread_bps': 4, 'slippage_bps': 4, 'roundtrip_bps': 27},
            {'id': 'RAW_AS_FRACTION', 'scale': 1.}, account_factory=FineGridAccount)
        sim.account.update_marks(0, {s: {'price': D(100), 'close_us': 0, 'available_us': 0} for s in S})
        sim.previous_quote = dict.fromkeys(S, float(quote))
        return sim

    def seed(self, sim, side='BUY', quantity=D(5)):
        sim.account.execute_fill(S[0], side, quantity, SIGNAL-2*MINUTE+1,
            SIGNAL-3*MINUTE, 'SEED', execution_mid_price=D(100), quote_available_us=SIGNAL-2*MINUTE)
        sim.account.update_marks(SIGNAL, {s: {'price': D(100), 'close_us': SIGNAL,
                                            'available_us': SIGNAL} for s in S})

    def market(self, **opens):
        return {s: {'open': float(opens.get(s, 100)), 'close': 100.,
                    'mark': 100., 'quote_volume': 100000000.} for s in S}

    def adapter(self, sim, source=None):
        return CausalPartialAdapter(sim, source or self.source())

    def assert_original_exact(self, baseline, candidate):
        self.assertEqual(candidate.account.snapshot(), baseline.account.snapshot())
        self.assertEqual(candidate.account.trades, baseline.account.trades)
        self.assertEqual(candidate.pending, baseline.pending)
        self.assertEqual(candidate.snapshot(), baseline.snapshot())

    def test_signal_binding_uses_completed_source_not_future_open(self):
        sim = self.sim(); adapter = self.adapter(sim)
        adapter.schedule(self.vec(10, 0, 0, 0, 0), SIGNAL, 'DAILY_TARGET')
        self.assertEqual(adapter.receipts[-1].fraction, D(1))
        binding = adapter.bindings[SIGNAL]
        self.assertEqual(binding.prices, ('100',)*5)
        self.assertTrue(all(row[1] <= SIGNAL and row[2] <= SIGNAL for row in binding.source_rows))
        self.assertEqual(len(binding.source_rows), 155)
        self.assertEqual(len(binding.source_sha256), 64)
        # No open argument exists on source binding or schedule.
        self.assertGreater(binding.covariance[0][0], .3)

    def test_gap_old_signal_go_fresh_volatility_rejected_account_unchanged(self):
        sim = self.sim(); adapter = self.adapter(sim)
        adapter.schedule(self.vec(10, 0, 0, 0, 0), SIGNAL, 'DAILY_TARGET')
        self.assertEqual(adapter.receipts[-1].fraction, D(1))
        before = sim.account.snapshot(); pending = deepcopy(sim.pending)
        adapter.attempt(SIGNAL+MINUTE, self.market(BTCUSDT=200))
        self.assertEqual(sim.account.snapshot(), before)
        self.assertEqual(sim.account.trades, [])
        self.assertEqual(sim.pending[S[0]]['target'], pending[S[0]]['target'])
        self.assertEqual(sim.pending[S[0]]['attempts'], 1)
        receipt = adapter.execution_receipts[0]
        self.assertFalse(receipt['allowed'])
        self.assertEqual(receipt['current_available_opens'][S[0]], '200.0')
        self.assertTrue(any(c['risk'].get('sigma', 0) > .1 for c in receipt['corners_checked']))
        self.assertEqual(sim.rejections[-1]['reason'], 'FRESH_EXECUTION_RISK_GUARD')

    def test_gap_native_without_guard_accepts_same_annual_vol_breach(self):
        sim = self.sim(); adapter = self.adapter(sim)
        adapter.schedule(self.vec(10, 0, 0, 0, 0), SIGNAL, 'DAILY_TARGET')
        adapter.original_attempt(SIGNAL+MINUTE, self.market(BTCUSDT=200))
        self.assertEqual(sim.account.positions[S[0]].quantity, D(10))
        risk = FreshExecutionPreview(sim.account, binding=adapter.bindings[SIGNAL],
            prices=self.vec(200, 100, 100, 100, 100), price_available_us=dict.fromkeys(S, SIGNAL+MINUTE),
            pending=self.vec(10, 0, 0, 0, 0), capacity=self.vec(100, 100, 100, 100, 100),
            event_us=SIGNAL+MINUTE+1, signal_us=SIGNAL, quote_available_us=SIGNAL+MINUTE)
        self.assertGreater(risk._risk(risk.account)['sigma'], .1)

    def test_funding_tie_after_signal_before_attempt_fresh_rejection(self):
        event = SIGNAL+MINUTE+1
        sim = self.sim(events=[{'symbol': S[0], 'event_us': event, 'raw_rate': 8.}])
        self.seed(sim); adapter = self.adapter(sim)
        adapter.schedule(self.vec(15, 0, 0, 0, 0), SIGNAL, 'DAILY_TARGET')
        self.assertEqual(adapter.receipts[-1].fraction, D(1))
        sim.funding_through(event, True)
        self.assertEqual(sim.account.funding_cash, D(-4000))
        self.assertEqual(sim.account.status, 'ACTIVE')
        before = sim.account.snapshot()
        adapter.attempt(SIGNAL+MINUTE, self.market())
        self.assertEqual(sim.account.snapshot(), before)
        self.assertEqual(sim.account.positions[S[0]].quantity, D(5))
        self.assertFalse(adapter.execution_receipts[0]['allowed'])
        self.assertEqual(D(adapter.execution_receipts[0]['fresh_funding_cash']), D(-4000))
        self.assertEqual(sim.funding_journal[0]['event_us'], event)

    def test_pending_change_after_signal_rejected_from_live_net_targets(self):
        sim = self.sim(); adapter = self.adapter(sim, self.source(volatile=(S[0], S[1])))
        adapter.schedule(self.vec(10, 0, 0, 0, 0), SIGNAL, 'DAILY_TARGET')
        self.assertEqual(adapter.receipts[-1].fraction, D(1))
        # Existing original-owner net target changes after the signal certificate.
        adapter.original_schedule(self.vec(10, 20, 0, 0, 0), SIGNAL, 'DAILY_TARGET', (S[1],))
        before = sim.account.snapshot()
        adapter.attempt(SIGNAL+MINUTE, self.market())
        self.assertEqual(sim.account.snapshot(), before)
        self.assertEqual(adapter.execution_receipts[0]['fresh_pending'][S[1]], '20')
        self.assertTrue(all(not r['allowed'] for r in adapter.execution_receipts))

    def test_unbound_order_signal_cannot_use_another_signal_certificate(self):
        sim = self.sim(); adapter = self.adapter(sim)
        adapter.schedule(self.vec(5, 0, 0, 0, 0), SIGNAL, 'DAILY_TARGET')
        adapter.original_schedule(self.vec(5, 0, 0, 0, 0), SIGNAL+1, 'DAILY_TARGET', (S[0],))
        before = sim.account.snapshot()
        adapter.attempt(SIGNAL+2*MINUTE, self.market())
        self.assertEqual(sim.account.snapshot(), before)
        self.assertIn('MISSING_SOURCE_BOUND_ORDER_SIGNAL', adapter.execution_receipts[0]['detail'])

    def test_future_selected_signal_price_rejected_before_scheduling(self):
        sim = self.sim(); before = sim.snapshot()
        with self.assertRaisesRegex(ValueError, 'FUTURE_SIGNAL'):
            self.adapter(sim, self.source(future_symbol=S[0])).schedule(self.vec(5, 0, 0, 0, 0), SIGNAL, 'DAILY_TARGET')
        self.assertEqual(sim.snapshot(), before)

    def test_future_covariance_constituent_rejected_before_scheduling(self):
        sim = self.sim(); before = sim.snapshot()
        with self.assertRaisesRegex(ValueError, 'FUTURE_SIGNAL'):
            self.adapter(sim, self.source(future_cov=True)).schedule(self.vec(5, 0, 0, 0, 0), SIGNAL, 'DAILY_TARGET')
        self.assertEqual(sim.snapshot(), before)

    def test_later_book_rows_cannot_change_signal_binding(self):
        self.assertEqual(self.source().bind(SIGNAL), self.source(future_book=True).bind(SIGNAL))

    def test_future_execution_price_availability_rejected_without_mutation(self):
        sim = self.sim(); before = sim.account.snapshot()
        with self.assertRaisesRegex(ValueError, 'ALREADY_BE_AVAILABLE'):
            FreshExecutionPreview(sim.account, binding=self.source().bind(SIGNAL),
                prices=self.vec(100, 100, 100, 100, 100), pending=self.vec(),
                capacity=self.vec(100, 100, 100, 100, 100), event_us=SIGNAL+MINUTE+1,
                signal_us=SIGNAL, quote_available_us=SIGNAL+MINUTE,
                price_available_us=dict.fromkeys(S, SIGNAL+MINUTE+2))
        self.assertEqual(sim.account.snapshot(), before)

    def test_full_valid_native_fills_account_pending_exact(self):
        baseline, sim = self.sim(), self.sim(); adapter = self.adapter(sim)
        raw = self.vec(5, 5, 0, 0, 0)
        baseline.schedule(raw, SIGNAL, 'DAILY_TARGET'); adapter.schedule(raw, SIGNAL, 'DAILY_TARGET')
        self.assertEqual(adapter.receipts[-1].fraction, D(1)); self.assertEqual(sim.pending, baseline.pending)
        baseline.attempt(SIGNAL+MINUTE, self.market()); adapter.attempt(SIGNAL+MINUTE, self.market())
        self.assert_original_exact(baseline, sim)
        self.assertTrue(all(r['allowed'] for r in adapter.execution_receipts))

    def test_full_valid_nontick_long_short_signflip_and_retry_exact(self):
        for side, target in [('BUY', '6.123456789'), ('SELL', '-6.123456789'),
                             ('BUY', '-3.123456789'), ('SELL', '3.123456789')]:
            with self.subTest(side=side, target=target):
                baseline, sim = self.sim(), self.sim()
                for native in (baseline, sim): self.seed(native, side)
                adapter = self.adapter(sim); raw = self.vec(target, 0, 0, 0, 0)
                baseline.schedule(raw, SIGNAL, 'DAILY_TARGET'); adapter.schedule(raw, SIGNAL, 'DAILY_TARGET')
                self.assertEqual(adapter.receipts[-1].fraction, D(1)); self.assertEqual(sim.pending, baseline.pending)
                for n in (1, 2):
                    baseline.attempt(SIGNAL+n*MINUTE, self.market()); adapter.attempt(SIGNAL+n*MINUTE, self.market())
                    self.assert_original_exact(baseline, sim)
                self.assertEqual(sim.pending[S[0]]['target'], D(target))

    def test_original_weight_nav_source_price_formula_dispatch_unchanged(self):
        baseline, sim = self.sim(), self.sim(); adapter = self.adapter(sim)
        raw = self.vec(D('.05123456789')*D('.99')*baseline.account.nav()/D(100), 0, 0, 0, 0)
        baseline.schedule(raw, SIGNAL, 'DAILY_TARGET'); adapter.schedule(raw, SIGNAL, 'DAILY_TARGET')
        self.assertEqual(adapter.receipts[-1].raw_target, raw); self.assertEqual(sim.pending, baseline.pending)
        baseline.attempt(SIGNAL+MINUTE, self.market()); adapter.attempt(SIGNAL+MINUTE, self.market())
        self.assert_original_exact(baseline, sim)

    def test_partial_enumeration_still_fixed_and_true_partial_refused(self):
        sim = self.sim(quote=100000); adapter = self.adapter(sim)
        adapter.schedule(self.vec(4, 0, 0, 0, 0), SIGNAL, 'DAILY_TARGET')
        self.assertEqual([e.fraction for e in adapter.receipts[-1].evaluations], list(FRACTIONS))
        self.assertEqual(adapter.receipts[-1].fraction, D('.25'))
        self.assertEqual(sim.pending[S[0]]['target'], D(1))
        self.assertFalse(adapter.receipts[-1].evaluations[0].allowed)
        adapter.attempt(SIGNAL+MINUTE, self.market())
        self.assertEqual(sim.account.positions[S[0]].quantity, D(1))

    def test_capacity_shrink_after_signal_rejects_true_partial_without_account_mutation(self):
        sim = self.sim(); adapter = self.adapter(sim)
        adapter.schedule(self.vec(4, 0, 0, 0, 0), SIGNAL, 'DAILY_TARGET')
        self.assertEqual(adapter.receipts[-1].fraction, D(1))
        sim.previous_quote = dict.fromkeys(S, 100000.)
        before = sim.account.snapshot(); adapter.attempt(SIGNAL+MINUTE, self.market())
        self.assertEqual(sim.account.snapshot(), before)
        self.assertFalse(adapter.execution_receipts[0]['allowed'])
        self.assertEqual(adapter.execution_receipts[0]['reason'], 'NATIVE_REFUSAL_OR_PARTIAL_WITH_RESIDUAL_PENDING')

    def test_terminal_passes_original_paid_close_even_without_signal_source(self):
        baseline, sim = self.sim(), self.sim()
        for native in (baseline, sim): self.seed(native)
        adapter = self.adapter(sim, CompletedBarSource([])); signal = sim.terminal_signal_us
        baseline.schedule(self.vec(), signal, 'TERMINAL'); adapter.schedule(self.vec(), signal, 'TERMINAL')
        baseline.attempt(signal+MINUTE, self.market()); adapter.attempt(signal+MINUTE, self.market())
        self.assert_original_exact(baseline, sim)
        self.assertEqual(adapter.receipts, []); self.assertEqual(adapter.execution_receipts, [])
        self.assertEqual(sim.account.positions[S[0]].quantity, 0); self.assertGreater(sim.account.fees, 0)

    def test_original_reduction_priority_parity_with_fresh_gap(self):
        for kind in ('RISK_REDUCTION', 'POOL_EXIT', 'DATA_GAP_EXIT', 'PROTECTIVE_STOP'):
            with self.subTest(kind=kind):
                baseline, sim = self.sim(), self.sim()
                for native in (baseline, sim):
                    self.seed(native)
                    if kind == 'RISK_REDUCTION': native.breaches.append({'signal_us': SIGNAL})
                adapter = self.adapter(sim, CompletedBarSource([]))
                raw = self.vec('2.000000005' if kind == 'RISK_REDUCTION' else 0, 0, 0, 0, 0)
                baseline.schedule(raw, SIGNAL, kind); adapter.schedule(raw, SIGNAL, kind)
                baseline.attempt(SIGNAL+MINUTE, self.market(BTCUSDT=200))
                adapter.attempt(SIGNAL+MINUTE, self.market(BTCUSDT=200))
                self.assert_original_exact(baseline, sim)
                self.assertEqual(adapter.execution_receipts, [])

    def test_mixed_priority_original_close_then_guard_unrelated_increase(self):
        sim = self.sim(); self.seed(sim); adapter = self.adapter(sim)
        kinds = dict.fromkeys(S, 'DAILY_TARGET'); kinds[S[0]] = 'PROTECTIVE_STOP'
        adapter.schedule(self.vec(0, 5, 0, 0, 0), SIGNAL, kinds)
        adapter.attempt(SIGNAL+MINUTE, self.market())
        self.assertEqual(sim.account.positions[S[0]].quantity, 0)
        self.assertEqual(sim.account.positions[S[1]].quantity, D(5))
        self.assertEqual([r['leg'] for r in sim.account.trades], ['OPEN', 'CLOSE', 'OPEN'])
        self.assertEqual(len(adapter.execution_receipts), 1)
        self.assertTrue(adapter.execution_receipts[0]['allowed'])

    def test_every_increase_refreshes_after_previous_native_fee_and_fill(self):
        sim = self.sim(); adapter = self.adapter(sim)
        adapter.schedule(self.vec(5, 5, 0, 0, 0), SIGNAL, 'DAILY_TARGET')
        adapter.attempt(SIGNAL+MINUTE, self.market())
        self.assertEqual(len(adapter.execution_receipts), 2)
        first, second = adapter.execution_receipts
        self.assertGreater(D(first['fresh_native_NAV']), D(second['fresh_native_NAV']))
        self.assertGreater(D(first['fresh_free_cash']), D(second['fresh_free_cash']))
        self.assertTrue(all(r['allowed'] for r in adapter.execution_receipts))

    def test_close_and_mark_future_fields_not_read_at_execution_seam(self):
        sim = self.sim(); adapter = self.adapter(sim)
        adapter.schedule(self.vec(5, 0, 0, 0, 0), SIGNAL, 'DAILY_TARGET')
        market = {s: {'open': 100., 'close': object(), 'mark': object(), 'quote_volume': object()} for s in S}
        adapter.attempt(SIGNAL+MINUTE, market)
        self.assertEqual(sim.account.positions[S[0]].quantity, D(5))
        self.assertTrue(adapter.execution_receipts[0]['allowed'])

    def test_source_covariance_is_original_sample_past30_annualized(self):
        binding = self.source(volatile=(S[0], S[1])).bind(SIGNAL)
        values = []
        for symbol in S:
            prices = np.asarray([float(D(row[3])) for row in binding.source_rows if row[0] == symbol])
            values.append(np.diff(prices)/prices[:-1])
        expected = np.cov(np.column_stack(values), rowvar=False, ddof=1)*365
        np.testing.assert_array_equal(np.asarray(binding.covariance), expected)

    def test_missing_source_calendar_fails_closed_before_native_dispatch(self):
        rows = [dict(symbol=r[0], close_us=r[1], available_us=r[2], close=r[3])
                for r in self.source().rows if not (r[0] == S[0] and r[1] == SIGNAL-20*DAY)]
        sim = self.sim(); before = sim.snapshot()
        with self.assertRaises(ValueError):
            self.adapter(sim, CompletedBarSource(rows)).schedule(self.vec(5, 0, 0, 0, 0), SIGNAL, 'DAILY_TARGET')
        self.assertEqual(sim.snapshot(), before)

    def test_fresh_mixed_corners_repeat_independently_without_live_profit_or_fee_reuse(self):
        sim = self.sim(); self.seed(sim)
        sim.account.execute_fill(S[1], 'SELL', D(5), SIGNAL+MINUTE+1, SIGNAL,
            'SECOND_SEED', execution_mid_price=D(100), quote_available_us=SIGNAL+MINUTE)
        before = sim.account.snapshot()
        preview = FreshExecutionPreview(sim.account, binding=self.source(volatile=(S[0], S[1])).bind(SIGNAL),
            prices=self.vec(110, 100, 100, 100, 100), price_available_us=dict.fromkeys(S, SIGNAL+2*MINUTE),
            pending=self.vec(10, -10, 0, 0, 0), capacity=self.vec(100, 100, 100, 100, 100),
            event_us=SIGNAL+2*MINUTE+1, signal_us=SIGNAL, quote_available_us=SIGNAL+2*MINUTE)
        fresh_before = preview.account.snapshot()
        first = preview.evaluate(self.vec(10, -10, 0, 0, 0), D(1))
        second = preview.evaluate(self.vec(10, -10, 0, 0, 0), D(1))
        self.assertEqual(first, second); self.assertTrue(first['allowed'])
        self.assertEqual(len(first['corners_checked']), 4)
        self.assertEqual(sim.account.snapshot(), before)
        self.assertEqual(preview.account.snapshot(), fresh_before)
        self.assertTrue(all(c['charge']['funding_before_preview_preserved'] for c in first['corners_checked']))

    def test_signflip_reduction_uses_shared_capacity_before_fresh_increase(self):
        baseline, sim = self.sim(quote=1000000), self.sim(quote=1000000)
        for native in (baseline, sim): self.seed(native)
        adapter = self.adapter(sim); raw = self.vec('-5.000000005', 0, 0, 0, 0)
        baseline.schedule(raw, SIGNAL, 'DAILY_TARGET'); adapter.schedule(raw, SIGNAL, 'DAILY_TARGET')
        self.assertEqual(adapter.receipts[-1].fraction, D(1))
        baseline.attempt(SIGNAL+MINUTE, self.market()); adapter.attempt(SIGNAL+MINUTE, self.market())
        self.assert_original_exact(baseline, sim)
        self.assertEqual([r['leg'] for r in sim.account.trades], ['OPEN', 'CLOSE', 'OPEN'])
        self.assertEqual(sim.account.positions[S[0]].quantity, D(-5))
        self.assertTrue(adapter.execution_receipts[0]['allowed'])
        executed = sum((D(r['decimal_strings']['quantity']) for r in sim.account.trades[1:]), D(0))
        self.assertEqual(executed, D(10))

    def test_install_routes_actual_native_advance_day_and_preserves_causal_order(self):
        sim = self.sim(events=[{'symbol': S[0], 'event_us': SIGNAL+MINUTE+1, 'raw_rate': 8.}])
        self.seed(sim); adapter = self.adapter(sim).install()
        weight = float(D(15)*D(100)/(D('.99')*sim.account.nav()))
        sim.advance_day(target_weights={s: weight if s == S[0] else 0. for s in S})
        # Five ordinary retries all inspect already-applied funding. Later original
        # terminal exits close the seed with paid native fills, never fabricate an increase.
        self.assertEqual(adapter.receipts[0].fraction, D(1))
        self.assertTrue(adapter.execution_receipts)
        self.assertTrue(all(not r['allowed'] for r in adapter.execution_receipts))
        self.assertEqual(D(adapter.execution_receipts[0]['fresh_funding_cash']), D(-4000))
        self.assertEqual([r['leg'] for r in sim.account.trades], ['OPEN', 'CLOSE'])
        self.assertEqual(sim.account.positions[S[0]].quantity, 0)
        self.assertEqual(sim.account.unpaid_liability, 0)
        self.assertEqual(sim.rows_written, 1440)
        self.assertEqual(sim.completion, 'COMPLETE_CONDITIONAL_ACCOUNT')
        adapter.uninstall(); self.assertFalse(adapter.installed)


if __name__ == '__main__':
    unittest.main()
