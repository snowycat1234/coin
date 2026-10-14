"""Independent generated-only tests for the frozen native grid adapter.

No market source, historical loader, network client, optimizer or live account.
The financial account/scheduler are imported unchanged through bind_sources.
"""
from copy import deepcopy
from dataclasses import replace
from decimal import localcontext
from pathlib import Path
import sys
import unittest
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
CANDIDATE = ROOT / 'coin_bot_native_adapter_synthetic_20261014'
sys.path.insert(0, str(CANDIDATE))
from generated_fixtures import make, new_sim, finish
from native_adapter import GridNativeAdapter, PORT, ACCOUNT, NATIVE, H, D, ZERO, S, BTC, DAY, M


def generated(arm='GRID', name='RANGE', weights=None, covariance='DEFAULT',
              prices=None, quote=None, kinds=None, cls=GridNativeAdapter):
    window, original_factory, closes, cov, default_weights = make(name)
    if prices is not None:
        for key in ('open', 'close', 'mark'):
            window['market'][BTC][key] = np.asarray(prices, dtype=float).copy()
    if quote is not None:
        for symbol in S:
            window['market'][symbol]['quote_volume'][:] = quote
    if weights is None and kinds is None:
        factory = original_factory
    else:
        w = np.asarray(default_weights if weights is None else weights, dtype=float)
        if w.ndim == 1:
            w = np.tile(w, (len(default_weights), 1))
        def factory(daily, clocks, mode):
            rows = []
            for i, clock in enumerate(clocks):
                for j, symbol in enumerate(S):
                    row = dict(available_us=int(clock), symbol=symbol, target_weight=float(w[i, j]))
                    if kinds is not None:
                        row['eligibility_reason'] = kinds.get(symbol, 'ELIGIBLE')
                    rows.append(row)
            return PORT.native.pl.DataFrame(rows), dict(source='INDEPENDENT_GENERATED_STATE_MACHINE')
    if not isinstance(covariance, str):
        cov = {int(t): covariance for t in range(window['start'], window['end'], DAY)}
    elif covariance == 'MISSING':
        cov = {}
    elif covariance != 'DEFAULT':
        raise ValueError('fixed generated covariance name')
    return cls(window, 'LONG_SHORT', PORT.native.COSTS[0], PORT.native.UNITS[0],
               target_factory=factory, account_factory=ACCOUNT, arm=arm,
               daily_closes=closes, covariance=cov,
               initial_observations={window['start']: H.CompletedMinute(window['start'], D(100), window['start'])})


class NativeAdversarial(unittest.TestCase):
    def test_disabled_control_full_eight_day_account_journal_and_minute_parity(self):
        direct = finish(new_sim('CONTROL', 'WEEK_RESET', direct=True))
        adapted = finish(new_sim('CONTROL', 'WEEK_RESET'))
        self.assertEqual(direct.account.snapshot(), adapted.account.snapshot())
        self.assertEqual(direct.rejections, adapted.rejections)
        self.assertEqual(direct.funding_journal, adapted.funding_journal)
        self.assertEqual(direct.breaches, adapted.breaches)
        for left, right in zip(direct.minute_chunks, adapted.minute_chunks, strict=True):
            np.testing.assert_array_equal(left, right)

    def test_cash_sign_flip_exact_native_account_and_journals(self):
        direct = finish(new_sim('CASH', 'SIGN_FLIP', direct=True))
        adapted = finish(new_sim('CASH', 'SIGN_FLIP'))
        # The fixed reference transforms original native Decimal quantities,
        # preserving lot boundaries and exact requested/fill receipt text.
        self.assertEqual(direct.account.snapshot(), adapted.account.snapshot())
        self.assertEqual(direct.account.summary(), adapted.account.summary())
        self.assertEqual(direct.account.trades, adapted.account.trades)
        self.assertEqual(direct.account.funding, adapted.account.funding)
        self.assertEqual(direct.funding_journal, adapted.funding_journal)

    def test_unknown_covariance_never_creates_grid_fill(self):
        for cov in ('MISSING', np.zeros((5, 5)), np.full((5, 5), np.nan), np.eye(5) * 100):
            with self.subTest(cov=str(cov)):
                sim = finish(generated(covariance=cov))
                self.assertFalse(any(a['owner'] == 'GRID' for a in sim.allocations))
                self.assertEqual(sim.native_certification, 'NOT_CERTIFIED_SYNTHETIC_ONLY')

    def test_unbound_future_or_stale_initial_observation_falls_back_to_original(self):
        reference = finish(new_sim('CONTROL', direct=True))
        for mode in ('MISSING', 'FUTURE', 'STALE'):
            with self.subTest(mode=mode):
                sim = generated()
                if mode == 'MISSING':
                    sim.initial_observations = {}
                elif mode == 'FUTURE':
                    sim.initial_observations = {sim.start: H.CompletedMinute(sim.start + 1, D(100), sim.start + 1)}
                else:
                    sim.initial_observations = {sim.start: H.CompletedMinute(sim.start - 2 * M, D(100), sim.start - 2 * M)}
                finish(sim)
                self.assertFalse(any(a['owner'] == 'GRID' for a in sim.allocations))
                self.assertEqual(sim.account.snapshot(), reference.account.snapshot())

    def test_native_point99_budget_minimum_lot_boundary_is_inactive_not_crash(self):
        candidate = finish(generated(weights=[.0492, 0, 0, 0, 0], quote=5_000_000.))
        reference = finish(generated(arm='CONTROL', weights=[.0492, 0, 0, 0, 0], quote=5_000_000.))
        self.assertFalse(any(a['owner'] == 'GRID' for a in candidate.allocations))
        self.assertEqual(candidate.account.snapshot(), reference.account.snapshot())

    def test_balanced_hedge_cannot_admit_grid_or_unmatched_cash_removal(self):
        sim = finish(generated(weights=[.2, 0, 0, 0, -.2], covariance=np.eye(5) * .01))
        self.assertFalse(any(a['owner'] == 'GRID' for a in sim.allocations))
        paid = sum((D(r['decimal_strings']['quantity']) for r in sim.account.trades
                    if r['symbol'] == BTC and r['leg'] == 'OPEN' and r['signal_us'] == sim.start), ZERO)
        self.assertEqual(paid, D('19.8'))

    def test_other_asset_pool_exit_does_not_remove_cash_replacement(self):
        sim = generated(arm='CASH')
        target = dict.fromkeys(S, ZERO)
        target[BTC] = D('19.8')
        kinds = dict.fromkeys(S, 'DAILY_TARGET')
        kinds[S[-1]] = 'POOL_EXIT'
        sim.schedule(target, sim.start, kinds)
        self.assertEqual(sim.pending[BTC]['target'], D('17.82'))
        self.assertEqual(sim.pending[S[-1]]['kind'], 'POOL_EXIT')

    def test_other_asset_data_gap_keeps_grid_positive_replacement_lineage(self):
        sim = generated()
        target = dict.fromkeys(S, ZERO)
        target[BTC] = D('19.8')
        kinds = dict.fromkeys(S, 'DAILY_TARGET')
        kinds[S[-1]] = 'DATA_GAP_EXIT'
        sim.schedule(target, sim.start, kinds)
        self.assertEqual(sim.pending[BTC]['target'], D('17.82'))
        self.assertEqual(sim.pending[S[-1]]['kind'], 'DATA_GAP_EXIT')

    def test_post_hard_risk_settlement_never_reopens_old_base_target(self):
        prices = np.r_[np.full(30, 100.), np.full(1410, 200.)]
        records = []
        class Spy(GridNativeAdapter):
            def risk_schedule(self, stamp):
                super().risk_schedule(stamp)
                order = self.pending.get(BTC)
                if self.breaches and order and order['kind'] == 'DAILY_TARGET':
                    records.append((stamp, order['target'], self.account.positions[BTC].quantity))
        sim = finish(generated(weights=[.29, 0, 0, 0, -.1], prices=prices,
                               quote=5_000_000., covariance=np.eye(5) * .001, cls=Spy))
        self.assertTrue(sim.breaches)
        self.assertFalse(any(target > actual for _, target, actual in records))

    def test_pending_nonbtc_increase_cannot_use_replacement_risk_headroom(self):
        sim = generated(covariance=np.diag([.01, .000001, .000001, .000001, .000001]))
        reference = {s: D(q) for s, q in zip(S, ('19.8', '4.95', '0', '0', '-9.9'))}
        ends = [(D('17.82'), D('19.6')), (D('4.95'), D('6')), (ZERO,), (ZERO,), (D('-9.9'),)]
        good, witness = sim._risk_envelope(ends, reference)
        self.assertFalse(good)
        self.assertIn('ASSET_CAP_OR_ORIGINAL_TARGET', witness['reasons'])
        self.assertIn('GROSS_CAP_OR_ORIGINAL_TARGET', witness['reasons'])

    def test_flat_expired_week_can_activate_new_session_without_overlap(self):
        prices = np.full(8 * 1440, 111.)
        prices[:20] = 100.
        prices[20:35] = 105.
        prices[35:50] = 110.
        # The last completed close available at the next Monday is inside the
        # range. Changing only Monday's future open cannot admit a new plan.
        prices[7 * 1440 - 1:] = 100.
        # Positive-only lifecycle fixture avoids an unrelated, correctly
        # rejected native short-lot remainder above a later target envelope.
        sessions = []
        class Spy(GridNativeAdapter):
            def risk_schedule(self, stamp):
                super().risk_schedule(stamp)
                if self.grid is not None:
                    sessions.append((stamp, self.grid.session_id, self.grid.inventory()))
        sim = generated(name='WEEK_RESET', weights=[.2, 0, 0, 0, 0], prices=prices, quote=5_000_000.,
                        covariance=np.eye(5) * .001, cls=Spy)
        sim.window['events'] = []
        finish(sim)
        earlier = [e for e in sim.policy_events if e['kind'] == 'GRID_NATIVE_BOUND'
                   and e['event_us'] < sim.start + 7 * DAY]
        later = [session for stamp, session, _ in sessions if stamp >= sim.start + 7 * DAY]
        self.assertTrue(earlier)
        self.assertTrue(later)
        self.assertNotEqual(earlier[0]['orders'][0].rsplit(':', 1)[0], later[0])
        exits = [e for e in sim.policy_events if e['kind'] == 'PAID_GRID_SETTLEMENT_REQUIRED'
                 and e.get('reason') == 'FIXED_WEEK_END']
        self.assertLessEqual(len(exits), 1)

    def test_duplicate_native_attempt_rejected_before_account_mutation(self):
        sim = finish(new_sim('GRID'))
        before = sim.account.snapshot()
        with self.assertRaisesRegex(ValueError, 'DUPLICATE_OR_REWOUND_NATIVE_ATTEMPT'):
            sim.attempt(sim._last_attempt_open, {})
        self.assertEqual(sim.account.snapshot(), before)

    def test_duplicate_paid_leg_attribution_rejected_without_mutation(self):
        sim = finish(new_sim('GRID'))
        before = deepcopy(sim.allocations)
        with self.assertRaisesRegex(ValueError, 'DUPLICATE_NATIVE_LEG'):
            sim._allocate_trade(sim.account.trades[0], 'BASE', None)
        self.assertEqual(sim.allocations, before)

    def binding_negative(self, mutation, expected):
        attempted = []
        class Spy(GridNativeAdapter):
            def attempt(self, open_us, market_row):
                if self.binding is not None:
                    mutation(self)
                    before = self.account.snapshot()
                    grid_before = deepcopy(vars(self.grid))
                    try:
                        super().attempt(open_us, market_row)
                    except ValueError as error:
                        attempted.append((str(error), before == self.account.snapshot(),
                                          grid_before == vars(self.grid)))
                        raise
                else:
                    super().attempt(open_us, market_row)
        sim = generated(cls=Spy)
        with self.assertRaisesRegex(ValueError, expected):
            finish(sim)
        self.assertTrue(attempted)
        self.assertTrue(attempted[0][1])
        self.assertTrue(attempted[0][2])

    def test_stale_native_order_rejected_before_finance(self):
        def mutate(sim):
            sim.pending[BTC]['order_id'] += ':STALE'
        self.binding_negative(mutate, 'STALE_NATIVE_ORDER_BINDING')

    def test_stale_helper_order_rejected_before_finance(self):
        def mutate(sim):
            slot = sim.binding['intents'][0].slot
            sim.grid.pending[slot] = replace(sim.grid.pending[slot], order_id='STALE_HELPER')
        self.binding_negative(mutate, 'STALE_HELPER_BINDING_BEFORE_FINANCE')

    def test_wrong_helper_side_rejected_before_finance(self):
        def mutate(sim):
            slot = sim.binding['intents'][0].slot
            old = sim.grid.pending[slot]
            sim.grid.pending[slot] = replace(old, side='SELL' if old.side == 'BUY' else 'BUY')
        self.binding_negative(mutate, 'STALE_HELPER_BINDING_BEFORE_FINANCE')

    def test_tampered_native_quantity_rejected_before_finance(self):
        def mutate(sim):
            sim.pending[BTC]['target'] += H.STEP
        self.binding_negative(mutate, 'NATIVE_PENDING_QUANTITY_UNBOUND')

    def test_confirmed_cancel_removes_native_order_before_releasing_helper_reserve(self):
        observations = []
        class Spy(GridNativeAdapter):
            def risk_schedule(self, stamp):
                super().risk_schedule(stamp)
                if self.binding is not None and not observations:
                    old_id = self.binding['native_order']
                    callback = self.grid.on_cancel_confirmed
                    def observe_cancel(*args, **kwargs):
                        observations.append(not (BTC in self.pending and self.pending[BTC]['order_id'] == old_id))
                        return callback(*args, **kwargs)
                    self.grid.on_cancel_confirmed = observe_cancel
                    self._cancel_grid_binding(stamp)
                    self.grid.on_cancel_confirmed = callback
        finish(generated(cls=Spy))
        self.assertTrue(observations)
        self.assertTrue(all(observations))

    def test_equal_close_funding_is_fully_paid_before_grid_decision(self):
        decisions = []
        class Spy(GridNativeAdapter):
            def risk_schedule(self, stamp):
                old = self.binding
                super().risk_schedule(stamp)
                if old is None and self.binding is not None:
                    decisions.append((stamp, self._inside_funding, len(self.account.funding)))
        sim = generated(quote=5_000_000., cls=Spy)
        event = sim.start + 2 * M
        sim.window['events'] = [dict(event_us=event, symbol=s, raw_rate=.001) for s in (BTC, S[-1])]
        finish(sim)
        self.assertTrue(decisions)
        self.assertEqual(decisions[0], (event, False, 2))
        first_funding = next(r for r in sim.account.funding if r['symbol'] == BTC)
        first_parts = [a for a in sim.funding_allocations if a['native_event'] == first_funding['event_id']]
        self.assertEqual(next(D(a['cash']) for a in first_parts if a['owner'] == 'GRID'), ZERO)

    def test_future_quote_price_suffix_does_not_change_paid_prefix(self):
        reference = generated()
        altered = generated()
        cutoff = reference.start + 60 * M
        for key in ('open', 'close', 'mark'):
            altered.window['market'][BTC][key][60:] = 200.
        for symbol in S:
            altered.window['market'][symbol]['quote_volume'][60:] = 0.
        finish(reference)
        finish(altered)
        self.assertEqual([r for r in reference.account.trades if r['event_us'] < cutoff],
                         [r for r in altered.account.trades if r['event_us'] < cutoff])
        self.assertEqual([r for r in reference.account.funding if r['event_us'] < cutoff],
                         [r for r in altered.account.funding if r['event_us'] < cutoff])
        self.assertEqual([a for a in reference.allocations if a['native_leg'][2] < cutoff],
                         [a for a in altered.allocations if a['native_leg'][2] < cutoff])

    def test_partial_paid_fills_obey_original_per_symbol_previous_minute_capacity(self):
        sim = finish(new_sim('GRID', 'PARTIAL'))
        for row in sim.account.trades:
            index = (row['event_us'] - sim.start - 1) // M
            self.assertGreater(index, 0)
            quote = D(str(sim.window['market'][row['symbol']]['quote_volume'][index - 1]))
            open_price = D(str(sim.window['market'][row['symbol']]['open'][index]))
            same_minute = sum((D(r['decimal_strings']['quantity']) for r in sim.account.trades
                              if r['symbol'] == row['symbol'] and r['event_us'] == row['event_us']), ZERO)
            self.assertLessEqual(same_minute * open_price, quote * D('.001'))
        sim._reconcile()

    def test_entirely_zero_quote_does_not_invent_base_or_grid_inventory(self):
        sim = finish(generated(quote=0.))
        self.assertEqual(len(sim.account.trades), 0)
        self.assertEqual(sim.base_btc, ZERO)
        self.assertFalse(any(a['owner'] == 'GRID' for a in sim.allocations))
        self.assertEqual(sim.account.nav(), D('10000'))

    def test_exact_fee_friction_and_eventwise_funding_allocation(self):
        sim = finish(new_sim('GRID'))
        with localcontext() as ctx:
            ctx.prec = 40
            for row in sim.account.trades:
                key = [row['fill_id'], row['leg'], row['event_us']]
                parts = [a for a in sim.allocations if a['native_leg'] == key]
                for native, allocated in [('quantity', 'quantity'), ('fee_amount', 'fee'), ('execution_cost', 'execution_cost')]:
                    self.assertEqual(sum((D(a[allocated]) for a in parts), ZERO), D(row['decimal_strings'][native]))
            for row in sim.account.funding:
                parts = [a for a in sim.funding_allocations if a['native_event'] == row['event_id']]
                self.assertEqual(sum((D(a['cash']) for a in parts), ZERO), D(row['decimal_strings']['signed_funding_USDT']))
        sim._reconcile()

    def test_original_terminal60_zero_liquidity_keeps_all_sixty_paid_attempts_and_residual(self):
        sim = finish(new_sim('GRID', 'TERMINAL_RESIDUAL'))
        expired = [r for r in sim.rejections if r['reason'] == 'SIXTY_TERMINAL_ATTEMPTS_EXPIRED']
        self.assertTrue(expired)
        self.assertTrue(all(r['event_us'] == sim.end - M + 1 for r in expired))
        terminal_ids = {r['order_id'] for r in expired}
        for order_id in terminal_ids:
            attempts = {r['event_us'] for r in sim.rejections if r.get('order_id') == order_id
                        and r.get('phase') == 'REDUCE'}
            self.assertEqual(len(attempts), 60)
        self.assertFalse(sim.result()['summary']['terminal_cash_realized'])
        self.assertGreater(sim.account.summary()['gross_notional'], 0)
        sim._reconcile()

    def test_sign_reversal_opens_btc_short_only_after_paid_grid_flat(self):
        violations = []
        class Spy(GridNativeAdapter):
            def _allocate_trade(self, row, purpose, binding):
                if row['symbol'] == BTC and row['side'] == 'SELL' and row['leg'] == 'OPEN':
                    violations.append(self.grid is not None and self.grid.inventory() != ZERO)
                super()._allocate_trade(row, purpose, binding)
        sim = finish(generated(name='SIGN_FLIP', cls=Spy))
        self.assertTrue(any(r['symbol'] == BTC and r['side'] == 'SELL' and r['leg'] == 'OPEN'
                            for r in sim.account.trades))
        self.assertFalse(any(violations))

    def test_snapshot_is_diagnostic_and_restore_fork_explicitly_fail_closed(self):
        sim = new_sim('GRID', 'WEEK_RESET')
        sim.advance_day()
        snapshot = sim.snapshot()
        self.assertIn('adapter_state', snapshot)
        self.assertEqual(snapshot['adapter_state']['base_btc'], str(sim.base_btc))
        self.assertEqual(snapshot['adapter_state']['grid']['session_id'], sim.grid.session_id)
        with self.assertRaisesRegex(ValueError, 'ADAPTER_RESTORE_NOT_IMPLEMENTED'):
            GridNativeAdapter.from_snapshot(snapshot, sim.window, account_class=ACCOUNT)
        with self.assertRaisesRegex(ValueError, 'ADAPTER_FORK_NOT_IMPLEMENTED'):
            sim.fork()


if __name__ == '__main__':
    unittest.main(verbosity=2)
