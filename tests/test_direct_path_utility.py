"""Bounded synthetic arithmetic, native fixed fills and analytic-gradient checks."""
from copy import deepcopy
from decimal import Decimal as D
import unittest

import numpy as np

from modules.direct_path.prototype import (
    CORE5, DAY_US, Context, SmallBudgetHead, daily_proxy, loss_and_gradient,
    map_budget, mapped_path, mapping_vjp, net_trade_cost,
)
from quant.perpetual_account import USDTLinearPerpetualAccount
from quant.bybit_isolated_account import BybitIsolatedAccount
from modules.direct_path.calibrate import fixed_ledger
from modules.direct_path.training import fit_pair, stamp, validate_fragment


def context(day=0, targets=None, eligible=None, returns=None):
    if targets is None:
        targets = np.array([[0.] * 5, [.08, .02, .01, 0., 0.],
                            [-.03, .01, 0., 0., 0.], [0., -.04, 0., 0., 0.],
                            [.02, .02, -.02, .01, 0.]])
    return Context((19700 + day) * DAY_US, (19700 + day) * DAY_US,
                   targets, np.ones(5, bool) if eligible is None else eligible,
                   np.zeros((30, 5)) if returns is None else returns,
                   np.linspace(-.3, .3, 13), np.full(5, (19700 + day) * DAY_US, np.int64))


def prices(rows=4):
    return np.ones((rows, 5)) * 100.


class MapperTests(unittest.TestCase):
    def test_ramp_continuation_and_cash_reset(self):
        c = context()
        p = np.array([1., 0., 0., 0., 0.])
        for i in range(3):
            m = map_budget(p, np.eye(5)[1], c)
            np.testing.assert_allclose(m['budget'], [1 - .05 * (i + 1), .05 * (i + 1), 0, 0, 0])
            self.assertLessEqual(np.abs(m['budget'] - p).sum(), .1 + 1e-12)
            p = m['budget']
        targets, _ = mapped_path(np.tile(np.eye(5)[1], (3, 1)), [context(i) for i in range(3)])
        self.assertGreater(targets[1, 0], targets[0, 0])
        np.testing.assert_array_equal(targets[-1], np.zeros(5))

    def test_release_before_ramp(self):
        mask = np.array([True, False, True, True, True])
        m = map_budget(np.eye(5)[1], np.eye(5)[2], context(eligible=mask))
        np.testing.assert_allclose(m['released_prior'], np.eye(5)[0])
        np.testing.assert_allclose(m['budget'], [.95, 0, .05, 0, 0])

    def test_cap_before_netting(self):
        e = np.zeros((5, 5)); e[1, 0] = .4; e[2, 0] = -.4
        p = np.array([0., .5, .5, 0., 0.])
        with self.assertRaisesRegex(ValueError, 'before netting'):
            map_budget(p, p, context(targets=e))

    def test_covariance_check_does_not_rescale(self):
        e = np.zeros((5, 5)); e[1, 0] = .2
        r = np.zeros((30, 5)); r[:, 0] = np.tile([-.5, .5], 15)
        with self.assertRaisesRegex(ValueError, 'covariance budget'):
            map_budget(np.eye(5)[1], np.eye(5)[1], context(targets=e, returns=r))

    def test_missing_identity_clock_and_gap_refused(self):
        c = context(); c.market13[2] = np.nan
        with self.assertRaisesRegex(ValueError, 'market13'):
            c.features()
        bad = context(); object.__setattr__(bad, 'symbol_order', CORE5[::-1])
        with self.assertRaisesRegex(ValueError, 'identity'):
            bad.validate()
        late = context(); object.__setattr__(late, 'available_us', late.decision_us + 1)
        with self.assertRaisesRegex(ValueError, 'clocks'):
            late.validate()
        late_expert = context(); late_expert.target_available_us[2] += 1
        with self.assertRaisesRegex(ValueError, 'expert target'):
            late_expert.validate()
        with self.assertRaisesRegex(ValueError, 'Date gaps'):
            mapped_path(np.tile(np.eye(5)[1], (2, 1)), [context(0), context(2)])

    def test_mapper_adjoint_directional_derivative(self):
        cs = [context(i) for i in range(4)]
        request = np.array([[.11, .28, .23, .19, .19]] * 4)
        direction = np.array([[.02, -.01, -.02, .03, -.02]] * 4)
        g = np.arange(20.).reshape(4, 5) / 20.
        _, records = mapped_path(request, cs)
        analytic = float((mapping_vjp(g, records, cs) * direction).sum())
        step = 1e-5
        plus = mapped_path(request + step * direction, cs)[0]
        minus = mapped_path(request - step * direction, cs)[0]
        numeric = float(((plus - minus) * g).sum()) / (2 * step)
        self.assertAlmostEqual(analytic, numeric, places=9)


class ProxyTests(unittest.TestCase):
    def test_cash_is_exactly_zero(self):
        p = prices(); p[1:] *= 1.1
        r = daily_proxy(np.zeros((3, 5)), p, np.full((3, 5), .01))
        for key in ('net_PnL', 'fees', 'spread', 'slippage', 'funding', 'gross', 'utility_sum'):
            self.assertEqual(r[key], 0.)

    def test_fixed_long_short_and_paid_boundaries(self):
        for direction in (1, -1):
            w = np.zeros((2, 5)); w[0, 0] = direction * .1
            p = prices(3); p[1:, 0] = 110
            r = daily_proxy(w, p, np.zeros((2, 5)))
            quantity = direction * 9.9
            opening_fee = 9.9 * 100 * (1 + direction * .0008) * .00055
            closing_fee = 9.9 * 110 * (1 - direction * .0008) * .00055
            execution = 9.9 * (100 + 110) * .0008
            self.assertAlmostEqual(r['gross'], quantity * 10)
            self.assertAlmostEqual(r['fees'], opening_fee + closing_fee)
            self.assertAlmostEqual(r['spread'] + r['slippage'], execution)
            self.assertAlmostEqual(r['net_PnL'], quantity * 10 - execution - opening_fee - closing_fee)
            np.testing.assert_array_equal(r['quantity'][-1], np.zeros(5))

    def test_netting_has_no_expert_turnover_surcharge(self):
        e = np.zeros((5, 5)); e[1, 0] = .2; e[2, 0] = -.2
        budget = np.array([0., .5, .5, 0., 0.])
        m = map_budget(budget, budget, context(targets=e))
        self.assertAlmostEqual(m['allocated_leg_gross'], .2)
        np.testing.assert_array_equal(m['targets'], np.zeros(5))
        cost = net_trade_cost(np.zeros(5), np.ones(5) * 100)[0]
        self.assertEqual(cost.sum(), 0.)

    def test_same_units_continue_without_fee(self):
        charge, *_ = net_trade_cost(np.zeros(5), np.ones(5) * 105)
        self.assertEqual(charge.sum(), 0.)
        charge, *_ = net_trade_cost(np.array([-20., 0., 0., 0., 0.]), np.ones(5) * 100)
        self.assertAlmostEqual(charge.sum(), 20 * 100 * (.0008 + .00055 * .9992))

    def test_positive_negative_funding_sign(self):
        for direction in (1, -1):
            for funding_rate in (.001, -.001):
                w = np.zeros((2, 5)); w[0, 0] = .1 * direction
                coeff = np.zeros((2, 5)); coeff[0, 0] = 100 * funding_rate
                r = daily_proxy(w, prices(3), coeff)
                self.assertAlmostEqual(r['funding'], -direction * 9.9 * 100 * funding_rate)

    def test_missing_data_no_free_terminal_and_actual_caps(self):
        w = np.zeros((2, 5)); w[0, 0] = .1
        p = prices(3); p[0, 0] = np.nan
        with self.assertRaisesRegex(ValueError, 'prices'):
            daily_proxy(w, p, np.zeros((2, 5)))
        f = np.zeros((2, 5)); f[0, 0] = np.nan
        with self.assertRaisesRegex(ValueError, 'funding'):
            daily_proxy(w, prices(3), f)
        w[-1, 0] = .1
        with self.assertRaisesRegex(ValueError, 'final cash'):
            daily_proxy(w, prices(3), np.zeros((2, 5)))
        w[-1] = 0; w[0, 0] = .3
        p = prices(3); p[1:, 0] = 150
        with self.assertRaisesRegex(ValueError, 'EXPOSURE_BREACH'):
            daily_proxy(w, p, np.zeros((2, 5)))

    def test_wallet_adjoint_directional_derivative(self):
        w = np.array([[.04, -.02, 0., .01, 0.], [.03, -.03, 0., .02, 0.], [0.] * 5])
        p = prices(); p[1] *= [1.02, 1.03, 1., 1.01, 1.]
        p[2] *= [1.01, .99, 1., 1.02, 1.]
        f = np.full((3, 5), .02)
        direction = np.array([[.01, -.02, 0., .01, 0.], [.01, .01, 0., -.01, 0.], [0.] * 5])
        r = daily_proxy(w, p, f)
        analytic = float((r['target_gradient'] * direction).sum())
        step = 1e-5
        numeric = (daily_proxy(w + step * direction, p, f)['utility_sum'] -
                   daily_proxy(w - step * direction, p, f)['utility_sum']) / (2 * step)
        self.assertAlmostEqual(analytic, numeric, places=9)

    def test_native_fixed_fills_match_midpoint_proxy_no_double_cost(self):
        for direction in (1, -1):
            account = USDTLinearPerpetualAccount(symbols=CORE5)
            def marks(t, btc):
                account.update_marks(t, {s: {'price': str(btc if j == 0 else 100),
                                            'close_us': t, 'available_us': t}
                                         for j, s in enumerate(CORE5)})
            marks(0, 100)
            open_side = 'BUY' if direction == 1 else 'SELL'
            close_side = 'SELL' if direction == 1 else 'BUY'
            opened = account.execute_fill(CORE5[0], open_side, '9.9', 60_000_001, 0, 'open',
                                          execution_mid_price='100', quote_available_us=60_000_001)
            self.assertEqual(opened['status'], 'FILLED')
            marks(120_000_000, 105)
            # Funding at this boundary MUST use the strictly older mark=100.
            coupon = account.apply_funding(CORE5[0], 'coupon', 120_000_000, '.001', 120_000_000)
            self.assertAlmostEqual(coupon['signed_funding_USDT'], -direction * .99)
            self.assertEqual(coupon['mark_close_us'], 0)
            account.apply_funding(CORE5[0], 'coupon', 120_000_000, '.001', 120_000_000)
            self.assertEqual(len(account.funding), 1)
            account.execute_fill(CORE5[0], close_side, '9.9', 120_000_001, 60_000_000, 'close',
                                 execution_mid_price='105', quote_available_us=120_000_001, reduce_only=True)
            w = np.zeros((2, 5)); w[0, 0] = direction * .1
            p = prices(3); p[1:, 0] = 105
            f = np.zeros((2, 5)); f[0, 0] = .1
            r = daily_proxy(w, p, f)
            self.assertAlmostEqual(float(account.nav()), r['nav'][-1], places=10)
            self.assertAlmostEqual(float(account.fees), r['fees'], places=10)
            self.assertAlmostEqual(float(account.execution_cost), r['spread'] + r['slippage'], places=10)
            self.assertEqual(account.positions[CORE5[0]].quantity, D(0))


class PairTests(unittest.TestCase):
    def test_same_head_parameter_count_no_fit_and_full_chain_gradient(self):
        h = SmallBudgetHead(np.zeros(43), np.ones(43))
        before = deepcopy(h.parameters)
        self.assertEqual(sum(p.size for p in h.parameters.values()), 397)
        self.assertFalse(hasattr(h, 'fit'))
        fragment = dict(contexts=[context(i) for i in range(4)], prices=prices(5),
                        funding_coeff=np.zeros((4, 5)), greedy_request=np.tile(np.eye(5)[1], (4, 1)))
        fragment['prices'][1:, 0] += np.arange(4)
        for arm in ('IMITATE_REQUEST', 'DIRECT_PATH_UTILITY'):
            loss, g, _ = loss_and_gradient(h, [fragment], arm)
            direction = np.linspace(-.03, .03, h.parameters['w2'].size).reshape(h.parameters['w2'].shape)
            analytic = float((g['w2'] * direction).sum())
            step = 1e-5
            h.parameters['w2'] = before['w2'] + step * direction
            plus = loss_and_gradient(h, [fragment], arm)[0]
            h.parameters['w2'] = before['w2'] - step * direction
            minus = loss_and_gradient(h, [fragment], arm)[0]
            h.parameters['w2'] = before['w2'].copy()
            self.assertTrue(np.isfinite(loss))
            self.assertAlmostEqual(analytic, (plus - minus) / (2 * step), places=8)
        for name in before:
            np.testing.assert_array_equal(h.parameters[name], before[name])

    def test_separate_fragment_wallets_reset(self):
        h = SmallBudgetHead(np.zeros(43), np.ones(43))
        a = dict(contexts=[context(0), context(1)], prices=prices(3), funding_coeff=np.zeros((2, 5)))
        b = dict(contexts=[context(100), context(101)], prices=prices(3), funding_coeff=np.zeros((2, 5)))
        _, _, reports = loss_and_gradient(h, [a, b], 'DIRECT_PATH_UTILITY')
        self.assertEqual(reports[0]['nav'][0], 10000.)
        self.assertEqual(reports[1]['nav'][0], 10000.)
        self.assertTrue(reports[0]['terminal_cash_realized'])
        self.assertTrue(reports[1]['terminal_cash_realized'])

    def test_fit_api_refuses_extra_data_before_fitting(self):
        with self.assertRaisesRegex(ValueError, 'Exactly Nov2022'):
            fit_pair([])
        with self.assertRaisesRegex(ValueError, 'data role'):
            validate_fragment({'window_id': '2025H2'}, '2025H2')

    def test_one_day_label_cannot_mature_at_decision_plus_one(self):
        start = stamp('2022-11-01')
        cs = [context(i) for i in range(30)]
        for i, c in enumerate(cs):
            d = start + i * DAY_US
            object.__setattr__(c, 'decision_us', d)
            object.__setattr__(c, 'available_us', d)
            c.target_available_us[:] = d
        names = ('input_npz_sha256', 'teacher_jsonl_sha256', 'expert_identity_sha256',
                 'mapper_sha256', 'market_binding_sha256')
        f = dict(window_id='BEAR2022NOV', contexts=cs,
                 label_available_us=np.array([c.decision_us + DAY_US for c in cs], np.int64),
                 binding={k: 'a' * 64 for k in names})
        validate_fragment(f, 'BEAR2022NOV')  # only a metadata guard, no fit
        f['label_available_us'][0] = cs[0].decision_us + 1
        with self.assertRaisesRegex(ValueError, 'mature'):
            validate_fragment(f, 'BEAR2022NOV')


class LedgerTests(unittest.TestCase):
    def test_legal_native_flip_has_two_legs_with_one_fill_id(self):
        account = USDTLinearPerpetualAccount(symbols=CORE5)
        def marks(t, btc):
            account.update_marks(t, {s: {'price': str(btc if j == 0 else 100),
                                        'close_us': t, 'available_us': t}
                                     for j, s in enumerate(CORE5)})
        def fill(side, quantity, t, signal, identity, mid):
            return account.execute_fill(CORE5[0], side, quantity, t, signal, identity,
                                        execution_mid_price=mid, quote_available_us=t)
        marks(0, 100)
        fill('BUY', '1', 60_000_001, 0, 'open-long', '100')
        marks(120_000_000, 105)
        flipped = fill('SELL', '2', 120_000_001, 60_000_000, 'one-flip', '105')
        self.assertEqual(len(flipped['fills']), 2)
        self.assertEqual(flipped['fills'][0]['fill_id'], flipped['fills'][1]['fill_id'])
        marks(180_000_000, 90)
        fill('BUY', '1', 180_000_001, 120_000_000, 'close-short', '90')
        summary = dict(account.summary(), terminal_cash_realized=all(
            p.quantity == 0 for p in account.positions.values()))
        report = fixed_ledger(account.trades, [], summary)
        self.assertLess(report['midpoint_bridge_error_USDT'], 1e-24)
        self.assertLess(report['fill_cashflow_bridge_error_USDT'], 1e-24)

    def test_takeover_loss_is_already_in_cashflow(self):
        account = BybitIsolatedAccount(symbols=CORE5)
        def marks(t, btc):
            account.update_marks(t, {s: {'price': str(btc if j == 0 else 100),
                                        'close_us': t, 'available_us': t}
                                     for j, s in enumerate(CORE5)})
        marks(0, 100)
        account.execute_fill(CORE5[0], 'SELL', '1', 60_000_001, 0, 'open-short',
                             execution_mid_price='100', quote_available_us=60_000_001)
        marks(120_000_000, 210)
        self.assertEqual(len(account.liquidations), 1)
        summary = dict(account.summary(), terminal_cash_realized=all(
            p.quantity == 0 for p in account.positions.values()))
        report = fixed_ledger(account.trades, [], summary)
        self.assertEqual(report['takeover_count'], 1)
        self.assertLess(report['fill_cashflow_bridge_error_USDT'], 1e-24)
        self.assertFalse(report['liquidation_loss_debited_again'])

    def test_duplicate_fill_cannot_double_cost(self):
        account = USDTLinearPerpetualAccount(symbols=CORE5)
        account.update_marks(0, {s: {'price': '100', 'close_us': 0, 'available_us': 0} for s in CORE5})
        account.execute_fill(CORE5[0], 'BUY', '1', 60_000_001, 0, 'same-id',
                             execution_mid_price='100', quote_available_us=60_000_001)
        with self.assertRaisesRegex(ValueError, 'Duplicate recorded fill'):
            fixed_ledger(account.trades * 2, [], account.summary())


if __name__ == '__main__':
    unittest.main()
