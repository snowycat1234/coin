"""Independent generated-only controller boundaries; no historical admission."""
from copy import deepcopy
from decimal import Decimal as D
from hashlib import sha256
import importlib.util
import json
import math
import unittest
from unittest.mock import Mock, patch

import numpy as np

from generated_helpers import (f, BASE, fixture, synthetic_source, make_sim, make_account,
                               mark, seed_paid, market, set_capacity, trigger, quantities,
                               finance, run, tree_equal)


class ProjectionBoundaries(unittest.TestCase):
    def test_original_mid_exact_native_math_and_signed_native_lots(self):
        for signs in ((1, 1), (-1, -1), (-1, 1)):
            with self.subTest(signs=signs):
                a = make_account()
                seed_paid(a, {'BTCUSDT': D('.02') * signs[0], 'ETHUSDT': D('.6') * signs[1]}, 0)
                c = np.eye(5) * 36
                before = a.preview_state_token()
                got = f.project_target(a, c)
                expected_risk = f.V2.native._tier_risk(a, c, 'MID')
                alpha = min(1., .1 / expected_risk['sigma'])
                expected = {s: (D(1) if p.quantity >= 0 else D(-1)) *
                    a._floor(s, abs(p.quantity) * D(str(alpha))) for s, p in a.positions.items()}
                self.assertEqual(got['sigma'], expected_risk['sigma'])
                self.assertEqual(got['alpha'], alpha)
                self.assertEqual(got['target'], expected)
                self.assertTrue(got['feasible'])
                self.assertLess(got['projected_variance'], got['current_variance'])
                self.assertTrue(all(abs(expected[s]) <= abs(a.positions[s].quantity) for s in f.S))
                self.assertTrue(tree_equal(before, a.preview_state_token()))

    def test_hedge_coarse_lot_removal_can_be_infeasible_and_must_hold(self):
        a = make_account()
        seed_paid(a, {'BTCUSDT': '-.001', 'ETHUSDT': '.03'}, 0)
        before = a.preview_state_token()
        result = f.project_target(a, np.ones((5, 5)) * 16900)
        self.assertGreater(result['sigma'], .1)
        self.assertEqual(result['target']['BTCUSDT'], 0)
        self.assertEqual(result['target']['ETHUSDT'], D('.02'))
        self.assertGreater(result['projected_variance'], result['current_variance'])
        self.assertFalse(result['feasible'])
        self.assertIn('INFEASIBLE', result['reason'])
        self.assertTrue(tree_equal(before, a.preview_state_token()))

    def test_strict_budget_comparison_has_no_added_monitor_epsilon(self):
        a = make_account()
        seed_paid(a, {'BTCUSDT': '.02'}, 0)
        w = float(a.positions['BTCUSDT'].quantity * a._mark('BTCUSDT') / a.nav())
        desired = np.nextafter(.1, math.inf)
        c = np.zeros((5, 5)); c[0, 0] = (desired / w) ** 2
        for _ in range(8):
            if f.V2.native._tier_risk(a, c, 'MID')['sigma'] > .1:
                break
            c[0, 0] = np.nextafter(c[0, 0], math.inf)
        self.assertGreater(f.V2.native._tier_risk(a, c, 'MID')['sigma'], .1)
        result = f.project_target(a, c)
        self.assertTrue(result['feasible'])
        self.assertLess(result['alpha'], 1)


class CoupledBoundaries(unittest.TestCase):
    def test_generated_gate_no_historical_constructor_or_snapshot_restore(self):
        plain = f.V2.grid.make_account('MID', 'BASE27')
        for scope in (object(), True, {'approved': True}):
            with self.assertRaisesRegex(ValueError, 'HISTORICAL_NO_GO'):
                f.ForecastRiskAccount(plain.config, historical_scope=scope)
        with self.assertRaisesRegex(ValueError, 'GENERATED_ORIGINAL_MID_ONLY'):
            f.ForecastRiskAccount(plain.config)
        with self.assertRaisesRegex(NotImplementedError, 'NOT_CERTIFIED'):
            make_account().from_snapshot({})

    def test_below_budget_full_native_D_finance_pending_observe_golden(self):
        window, rows, decisions = fixture(1)
        target = np.full((1, 5), .03)
        old, oldguard = f.E.construct_case(window, rows, decisions, target, generated_scope=f.GENERATED)
        new, newguard = f.construct_case(window, rows, decisions, target, generated_scope=f.GENERATED)
        for sim in (old, new):
            sim.independent_pending_trace = []
            original = sim.risk_schedule
            def observed(at, *, sim=sim, original=original):
                result = original(at)
                sim.independent_pending_trace.append((at, deepcopy(sim.pending)))
                return result
            sim.risk_schedule = observed
            run(sim)
        self.assertIsNone(new.stop)
        self.assertEqual(finance(old.account), finance(new.account))
        self.assertEqual(old.independent_pending_trace, new.independent_pending_trace)
        self.assertEqual(old.result()['minute'].to_numpy().tobytes(), new.result()['minute'].to_numpy().tobytes())
        self.assertEqual(old.extrema, new.extrema)
        self.assertGreater(len(new.account.trades), 0)
        self.assertGreater(new.account.fees, 0)
        self.assertFalse(new.account.forecast_journal)
        self.assertFalse(new.account.transfer_journal)

    def test_known_above_budget_real_paid_trim_first_native_eligible_open(self):
        for sign in (1, -1):
            with self.subTest(sign=sign):
                sim, guard, rows = make_sim(.5)
                a = sim.account
                seed_paid(a, {'BTCUSDT': D('.05') * sign}, sim.start)
                set_capacity(sim)
                at, receipt = trigger(sim)
                self.assertEqual(receipt['action'], 'NATIVE_PAID_REDUCTION_INTENT')
                self.assertLess(receipt['projected_variance'], receipt['current_variance'])
                count, fees, oldq = len(a.trades), a.fees, quantities(a)
                sim.attempt(at, market())
                self.assertEqual(len(a.trades), count)
                mark(a, at + f.MINUTE)
                sim.attempt(at + f.MINUTE, market())
                self.assertGreater(len(a.trades), count)
                paid = list(a.trades)[count:]
                self.assertTrue(all(row['leg'] == 'CLOSE' for row in paid))
                self.assertEqual(paid[0]['event_us'], at + f.MINUTE + 1)
                self.assertGreater(a.fees, fees)
                self.assertLess(abs(a.positions['BTCUSDT'].quantity), abs(oldq['BTCUSDT']))
                self.assertFalse(a.transfer_journal)
                self.assertIsNone(a._forecast_active)
                self.assertIn('COMPLETED_NATIVE_PAID_TARGET', [x['kind'] for x in a.forecast_journal])

    def test_partial_hedge_fill_variance_increase_is_explicit_completed_cohort_improves(self):
        sim, guard, rows = make_sim(6)
        a = sim.account
        seed_paid(a, {'BTCUSDT': '-.02', 'ETHUSDT': '.6'}, sim.start)
        set_capacity(sim)
        at, receipt = trigger(sim)
        self.assertEqual(receipt['action'], 'NATIVE_PAID_REDUCTION_INTENT')
        initial = receipt['current_variance']
        mark(a, at + f.MINUTE)
        sim.attempt(at + f.MINUTE, market())
        records = list(a.forecast_fill_journal)
        self.assertEqual([r['symbol'] for r in records], ['BTCUSDT', 'ETHUSDT'])
        self.assertTrue(records[0]['variance_increased'])
        self.assertGreater(records[0]['variance_after'], records[0]['variance_before'])
        self.assertLess(records[-1]['variance_after'], initial)
        self.assertTrue(all(D(r['paid_fee_delta']) > 0 for r in records))
        self.assertIsNone(a._forecast_active)

    def test_full_same_clock_funding_batch_precedes_new_trim(self):
        sim, guard, rows = make_sim(.5)
        a = sim.account
        seed_paid(a, {'BTCUSDT': '.05'}, sim.start)
        at = sim.start + 2 * f.MINUTE
        mark(a, at)
        sim.window['events'] = [dict(symbol=s, event_us=at, raw_rate=.0001,
                                     reported_interval_hours=8.) for s in f.S]
        observed = []
        original = a.apply_funding
        def record(*args, **kwargs):
            observed.append((args[0], a._forecast_active is not None, len(a.forecast_journal)))
            return original(*args, **kwargs)
        a.apply_funding = record
        try:
            sim.funding_through(at, True)
        finally:
            del a.apply_funding
        self.assertEqual([x[0] for x in observed], list(f.S))
        self.assertFalse(any(active for _, active, _ in observed))
        self.assertTrue(all(n == 0 for _, _, n in observed))
        self.assertEqual(sim.event_cursor, 5)
        self.assertIsNotNone(a._forecast_active)
        self.assertEqual(a._forecast_active['born_us'], at)
        self.assertEqual(len(a.trades), 1)

    def test_controller_infeasible_projection_holds_without_financial_change(self):
        # Fixed independent tiny factors keep the huge common covariance
        # positive definite under the unchanged native floating PSD check.
        independent = .01 * np.sin(np.arange(30)[:, None] * np.arange(1, 6)[None, :])
        returns = np.asarray([37.] + [0.] * 29)[:, None] + independent
        sim, guard, rows = make_sim(returns=returns)
        a = sim.account
        seed_paid(a, {'BTCUSDT': '-.001', 'ETHUSDT': '.03'}, sim.start)
        at = sim.start + 2 * f.MINUTE
        mark(a, at)
        before = finance(a)
        receipt = sim.risk_schedule(at)
        self.assertEqual(receipt['action'], 'HOLD')
        self.assertIn('INFEASIBLE', receipt['reason'])
        self.assertEqual(finance(a), before)
        self.assertIsNone(a._forecast_active)
        self.assertFalse(sim.pending)
        self.assertEqual(a.forecast_journal[-1]['kind'], 'LOT_PROJECTION_INFEASIBLE')

    def test_capacity_limited_five_opens_renewal_requires_new_latency(self):
        sim, guard, rows = make_sim(2)
        a = sim.account
        seed_paid(a, {'BTCUSDT': '.05'}, sim.start)
        set_capacity(sim, {'BTCUSDT': D('.001')})
        at, receipt = trigger(sim)
        old = abs(a.positions['BTCUSDT'].quantity)
        for k in range(1, 6):
            mark(a, at + k * f.MINUTE)
            sim.attempt(at + k * f.MINUTE, market())
            paid = [r for r in a.trades if r['event_us'] == at + k * f.MINUTE + 1]
            self.assertEqual(sum((D(r['decimal_strings']['quantity']) for r in paid), D(0)), D('.001'))
        self.assertEqual(abs(a.positions['BTCUSDT'].quantity), old - D('.005'))
        self.assertEqual(a._forecast_active['renewals'], 1)
        renewed = sim.pending['BTCUSDT']
        self.assertEqual(renewed['signal_us'], at + 5 * f.MINUTE + 1)
        q = a.positions['BTCUSDT'].quantity
        mark(a, at + 6 * f.MINUTE)
        sim.attempt(at + 6 * f.MINUTE, market())
        self.assertEqual(a.positions['BTCUSDT'].quantity, q)
        mark(a, at + 7 * f.MINUTE)
        sim.attempt(at + 7 * f.MINUTE, market())
        self.assertEqual(a.positions['BTCUSDT'].quantity, q - D('.001'))
        self.assertIsNone(sim.stop)

    def test_unknown_quality_preserves_existing_daily_intent_and_paid_reductions(self):
        sim, guard, rows = make_sim(.5)
        a = sim.account
        seed_paid(a, {'BTCUSDT': '.05'}, sim.start)
        set_capacity(sim)
        at = sim.start + 2 * f.MINUTE
        a._quality_intervals = ((at, at + 5 * f.MINUTE, f.S),)
        target = quantities(a); target['BTCUSDT'] = D(0); target['ETHUSDT'] = D('.1')
        # Existing original native order fixture, preceding the quality gap.
        guard.original_schedule(target, sim.start, 'DAILY_TARGET')
        mark(a, at)
        pending = deepcopy(sim.pending)
        receipt = sim.risk_schedule(at)
        self.assertIn('UNKNOWN_DERIVED_OR_STALE', receipt['reason'])
        self.assertEqual(sim.pending, pending)
        self.assertFalse(a.forecast_journal)
        mark(a, at + f.MINUTE)
        sim.attempt(at + f.MINUTE, market())
        self.assertEqual(a.positions['BTCUSDT'].quantity, 0)
        self.assertEqual(a.positions['ETHUSDT'].quantity, 0)
        self.assertEqual(sim.pending['ETHUSDT']['target'], D('.1'))
        self.assertEqual(sim.pending['ETHUSDT']['signal_us'], sim.start)
        self.assertFalse(a.pending_exits)

    def test_absent_completed_mark_adds_no_monitor_action_or_fabricated_exit(self):
        sim, guard, rows = make_sim(.5)
        a = sim.account
        seed_paid(a, {'BTCUSDT': '.05'}, sim.start)
        at = sim.start + 2 * f.MINUTE
        oldq = quantities(a)
        mark(a, at, symbols=f.S[:-1])
        count = a._forecast_noop_count
        self.assertIsNone(sim.risk_schedule(at))
        self.assertEqual(a._forecast_noop_count, count)
        self.assertEqual(quantities(a), oldq)
        self.assertFalse(a.forecast_journal)
        self.assertFalse(a.pending_exits)

    def test_gap_new_daily_signal_whole_native_D_financial_and_pending_golden(self):
        window, rows, decisions = fixture(2)
        at = int(decisions[1])
        intervals = ((at - 2 * f.MINUTE, at + 3 * f.MINUTE, f.S),)
        targets = np.asarray([[.03] * 5, [.05] * 5])
        old, _ = f.E.construct_case(window, rows, decisions, targets,
                     generated_scope=f.GENERATED, quality_intervals=intervals)
        new, _ = f.construct_case(window, rows, decisions, targets,
                     generated_scope=f.GENERATED, quality_intervals=intervals)
        for sim in (old, new):
            sim.independent_trace = []
            original = sim.risk_schedule
            def observed(at, *, sim=sim, original=original):
                result = original(at)
                sim.independent_trace.append((at, deepcopy(sim.pending)))
                return result
            sim.risk_schedule = observed
            run(sim)
        self.assertEqual(finance(old.account), finance(new.account))
        self.assertEqual(old.independent_trace, new.independent_trace)
        self.assertGreater(len(new.account.trades), 10)
        self.assertFalse(new.account.pending_exits)
        self.assertFalse(new.account.forecast_journal)

    def test_D_full_protective_exit_supersedes_weaker_forecast_trim(self):
        sim, guard, rows = make_sim(.5)
        a = sim.account
        seed_paid(a, {'BTCUSDT': '-.05'}, sim.start)
        at = sim.start + 2 * f.MINUTE
        mark(a, at, {'BTCUSDT': 75000})
        receipt = sim.risk_schedule(at)
        self.assertEqual(receipt['reason'], 'EXISTING_NATIVE_OR_D_PRIORITY_PRESERVED')
        self.assertEqual(sim.pending['BTCUSDT']['kind'], 'PROTECTIVE_STOP')
        self.assertEqual(sim.pending['BTCUSDT']['target'], 0)
        self.assertIsNone(a._forecast_active)
        self.assertFalse(a.transfer_journal)

    def test_native_terminal_supersedes_owned_cohort_and_cannot_be_weakened(self):
        sim, guard, rows = make_sim(.5)
        a = sim.account
        seed_paid(a, {'BTCUSDT': '.05'}, sim.start)
        at, _ = trigger(sim)
        self.assertIsNotNone(a._forecast_active)
        terminal = sim.terminal_signal_us
        sim.funding_through(terminal + 1, True)
        self.assertTrue(sim.terminal)
        self.assertIsNone(a._forecast_active)
        self.assertTrue(all(o['kind'] == 'TERMINAL' and o['target'] == 0 for o in sim.pending.values()))
        mark(a, terminal + f.MINUTE)
        pending = deepcopy(sim.pending)
        result = sim.risk_schedule(terminal + f.MINUTE)
        self.assertEqual(result['reason'], 'NATIVE_TERMINAL_OR_STOP_PRIORITY')
        self.assertEqual(sim.pending, pending)

    def test_old_daily_pending_cannot_refill_after_trim_without_genuine_new_signal(self):
        sim, guard, rows = make_sim(.5, days=2)
        a = sim.account
        seed_paid(a, {'BTCUSDT': '.05'}, sim.start)
        set_capacity(sim)
        target = quantities(a); target['BTCUSDT'] = D('.055'); target['ETHUSDT'] = D('.1')
        guard.original_schedule(target, sim.start, 'DAILY_TARGET')
        at, receipt = trigger(sim)
        self.assertEqual(receipt['action'], 'NATIVE_PAID_REDUCTION_INTENT')
        self.assertTrue(all(o['kind'] == 'RISK_REDUCTION' for o in sim.pending.values()))
        mark(a, at + f.MINUTE); sim.attempt(at + f.MINUTE, market())
        after, count = quantities(a), len(a.trades)
        for k in range(2, 12):
            mark(a, at + k * f.MINUTE)
            sim.risk_schedule(at + k * f.MINUTE)
            sim.attempt(at + k * f.MINUTE, market())
        self.assertEqual(quantities(a), after)
        self.assertEqual(len(a.trades), count)
        self.assertEqual(a.positions['ETHUSDT'].quantity, 0)
        # A genuine newer original DAILY signal still passes through fresh guards.
        new_signal = sim.start + f.DAY
        mark(a, new_signal)
        genuine = quantities(a); genuine['BTCUSDT'] = D('.04')
        guard.schedule(genuine, new_signal, 'DAILY_TARGET')
        self.assertTrue(any(o['kind'] == 'DAILY_TARGET' and o['signal_us'] == new_signal
                            for o in sim.pending.values()))
        mark(a, new_signal + f.MINUTE)
        sim.attempt(new_signal + f.MINUTE, market())
        self.assertGreater(a.positions['BTCUSDT'].quantity, after['BTCUSDT'])

    def test_replay_conflict_noop_eviction_and_permanent_changing_identity(self):
        sim, guard, rows = make_sim(.5)
        a = sim.account
        seed_paid(a, {'BTCUSDT': '.02'}, sim.start)
        at, first = trigger(sim)
        before = a.preview_state_token()
        self.assertEqual(sim.forecast_controller.after_native_risk(at), first)
        self.assertTrue(tree_equal(before, a.preview_state_token()))
        with self.assertRaisesRegex(ValueError, 'CONFLICTING_FORECAST'):
            a._forecast_replay(at, dict(kind='ALTERED_MONITOR', event_us=at))
        for k in range(1, 81):
            mark(a, at + k * f.MINUTE); sim.risk_schedule(at + k * f.MINUTE)
        self.assertEqual(len(a._forecast_noops), 64)
        self.assertGreaterEqual(a._forecast_noop_count, 81)
        self.assertNotEqual(a._forecast_noop_commitment, '0' * 64)
        with self.assertRaisesRegex(ValueError, 'EXPIRED_OR_REUSED_FORECAST'):
            a._forecast_replay(at, dict(kind='FORECAST_MONITOR', event_us=at))
        active, _, _ = make_sim(.5)
        seed_paid(active.account, {'BTCUSDT': '.05'}, active.start)
        born, changing = trigger(active)
        key = 'FORECAST_MONITOR:' + str(born)
        self.assertIn(key, active.account.operation_ids)
        self.assertEqual(active.account._forecast_replay(born, dict(kind='FORECAST_MONITOR', event_us=born)), changing)

    def test_source_cache_keeps_original_clock_hash_and_rejects_unpublished_daily(self):
        sim, guard, rows = make_sim(.5)
        a = sim.account
        seed_paid(a, {'BTCUSDT': '.02'}, sim.start)
        at, receipt = trigger(sim)
        binding = guard.source.bind(sim.start)
        self.assertEqual(a._forecast_cache['binding_signal_us'], sim.start)
        self.assertEqual(a._forecast_cache['covariance_available_us'], sim.start)
        self.assertEqual(a._forecast_cache['source_sha256'], binding.source_sha256)
        mark(a, at + 10 * f.MINUTE)
        sim.risk_schedule(at + 10 * f.MINUTE)
        self.assertEqual(a._forecast_cache['binding_signal_us'], sim.start)
        np.testing.assert_array_equal(a._forecast_cache['covariance'], binding.covariance)
        window, late_rows, decisions = synthetic_source(1, .5)
        for row in late_rows:
            if row['close_us'] == window['start']:
                row['available_us'] += f.DAY
        late, _ = f.construct_case(window, late_rows, decisions, np.zeros((1, 5)), generated_scope=f.GENERATED)
        seed_paid(late.account, {'BTCUSDT': '.05'}, late.start)
        _, denied = trigger(late)
        self.assertEqual(denied['action'], 'HOLD')
        self.assertIn('FUTURE_SIGNAL', denied['reason'])
        self.assertIsNone(late.account._forecast_active)

    def test_preview_owns_cohort_receipts_capacity_quality_and_suppresses_callbacks(self):
        sim, guard, rows = make_sim(.5)
        a = sim.account
        seed_paid(a, {'BTCUSDT': '-.05'}, sim.start)
        at, _ = trigger(sim)
        calls = []
        a.liquidation_callback = lambda *args, **kwargs: calls.append((args, kwargs))
        a.capacity_used[('BTCUSDT', at)] = D('.001')
        before, pending = a.preview_state_token(), deepcopy(sim.pending)
        clone = a.fork_for_preview()
        self.assertIs(type(clone), f.ForecastRiskAccount)
        self.assertIsNone(clone.liquidation_callback)
        self.assertIs(clone.forecast_journal._root, a.forecast_journal._root)
        clone._forecast_active['targets']['BTCUSDT'] = D(0)
        clone._forecast_cache['binding_signal_us'] = 1
        clone.capacity_used[('BTCUSDT', at)] = D('.002')
        self.assertTrue(tree_equal(before, a.preview_state_token()))
        binding = guard.source.bind(sim.start)
        target = quantities(a); target['ETHUSDT'] = D('.1')
        oracle = f.fresh_preview(a, tier_name='MID', binding=binding,
            prices={s: D(100000) if s == 'BTCUSDT' else D(str(BASE[j])) for j, s in enumerate(f.S)},
            price_available_us=dict.fromkeys(f.S, at + f.MINUTE), pending=target,
            capacity=dict.fromkeys(f.S, D(100000)), event_us=at + f.MINUTE + 1,
            signal_us=sim.start, quote_available_us=at + f.MINUTE)
        witness = oracle.evaluate(target, D(1))
        self.assertFalse(witness['allowed'])
        self.assertTrue(tree_equal(before, a.preview_state_token()))
        self.assertEqual(sim.pending, pending)
        self.assertFalse(calls)
        with self.assertRaises(TypeError):
            a.forecast_journal[0] = {}

    def test_actual_unpaid_debt_and_unknown_native_halt_are_never_rescued(self):
        sim, guard, rows = make_sim(.5)
        a = sim.account
        seed_paid(a, {'BTCUSDT': '.05'}, sim.start)
        at = sim.start + 2 * f.MINUTE
        mark(a, at - 1)
        mark(a, at)
        a.apply_funding('BTCUSDT', 'INDEPENDENT_REAL_DEBT', at, D(10), at)
        self.assertGreater(a.unpaid_liability, 0)
        self.assertIn(a.status, f.V2.P.HALTS)
        debt, status = a.unpaid_liability, a.status
        result = sim.risk_schedule(at)
        self.assertIn('DEBT_OR_NATIVE_HALT', result['reason'])
        self.assertEqual(a.unpaid_liability, debt)
        self.assertEqual(a.status, status)
        self.assertFalse(a.transfer_journal)
        self.assertIsNone(a._forecast_active)
        # Unknown mark quality cannot be represented as a paid conditional rescue.
        other, _, _ = make_sim(.5)
        b = other.account
        seed_paid(b, {'BTCUSDT': '-.02'}, other.start)
        when = other.start + 2 * f.MINUTE
        b._quality_intervals = ((when, when + f.MINUTE, f.S),)
        mark(b, when, {'BTCUSDT': 100000})
        self.assertIn(b.status, f.V2.P.HALTS)
        self.assertFalse(b.settlement_journal)
        held = quantities(b)
        other.risk_schedule(when)
        self.assertEqual(quantities(b), held)
        self.assertFalse(b.transfer_journal)
        self.assertIsNone(b._forecast_active)

    def test_full_generated_active_calendar_has_paid_trims_and_terminal_execution(self):
        window, rows, decisions = synthetic_source(1, .5)
        for j, s in enumerate(f.S):
            for key in ('open', 'close', 'mark'):
                window['market'][s][key][10:] = BASE[j] * 2
        sim, guard = f.construct_case(window, rows, decisions, np.full((1, 5), .03),
                                      generated_scope=f.GENERATED)
        run(sim)
        self.assertIsNone(sim.stop)
        self.assertEqual(sim.rows_written, 1440)
        self.assertTrue(any(r['kind'] == 'COHORT_CREATED' for r in sim.account.forecast_journal))
        self.assertTrue(any(r['kind'] == 'COMPLETED_NATIVE_PAID_TARGET' for r in sim.account.forecast_journal))
        self.assertGreater(len(sim.account.forecast_fill_journal), 0)
        self.assertGreater(len(sim.account.trades), 10)
        self.assertGreater(sim.account.fees, 0)
        self.assertTrue(all(p.quantity == 0 for p in sim.account.positions.values()))
        self.assertFalse(sim.account.transfer_journal)
        self.assertFalse(sim.account.settlement_journal)
        checker_spec = importlib.util.spec_from_file_location('_independent_forecast_native40',
                           f.FROZEN / 'saved_native_reconciliation.py')
        checker = importlib.util.module_from_spec(checker_spec)
        checker_spec.loader.exec_module(checker)
        audit = f.V2.OWNED.export_tree(sim.account.snapshot())
        result = f.case_result(sim, guard)
        result.pop('minute')
        result['targets'] = result['targets'].to_dicts()
        result = f.V2.OWNED.export_tree(result)
        proof = checker.reconcile_saved_native(audit, result, expected_continuation_version=f.VERSION)
        self.assertTrue(proof['passed'])
        self.assertEqual(proof['native_financial_precision'], 40)
        self.assertEqual(proof['raw_diagnostic_precision'], 100)
        self.assertFalse(proof['tolerance_or_epsilon_used'])
        self.assertIn('raw_precision100_stored_delta_terminal_residuals', proof)
        self.assertEqual(sha256((f.FROZEN / 'saved_native_reconciliation.py').read_bytes()).hexdigest(),
                         f.PINS['saved_native_reconciliation.py'])

    def test_stale_zero_executable_native_clock_replay_and_positive_fail_closed(self):
        accounts = []
        for cls in (f.E.ExpansionAccount, f.ForecastRiskAccount):
            plain = f.V2.grid.make_account('MID', 'BASE27')
            a = cls(plain.config, symbols=f.S, instrument_profiles=plain.instrument_profiles,
                    closing_min_notional_exempt=True, generated_scope=f.GENERATED)
            seed_paid(a, {'BTCUSDT': '.02'}, 0)
            at = 2 * f.MINUTE
            a._quality_intervals = ((at, at + 5 * f.MINUTE, f.S),)
            mark(a, at)
            args = ('BTCUSDT', 'BUY', '.001', at + f.MINUTE + 1, 0, 'NATIVE_ZERO_EXECUTABLE')
            kwargs = dict(execution_mid_price='50000', quote_available_us=at + f.MINUTE,
                          available_quantity='.0001')
            zero = a.execute_fill(*args, **kwargs)
            self.assertEqual(D(zero['decimal_strings']['executed_quantity']), 0)
            self.assertEqual(a.clock_us, at + f.MINUTE + 1)
            before = a.preview_state_token()
            self.assertEqual(a.execute_fill(*args, **kwargs), zero)
            self.assertTrue(tree_equal(before, a.preview_state_token()))
            with self.assertRaisesRegex(ValueError, 'conflicting fill identity'):
                a.execute_fill(*args, **{**kwargs, 'available_quantity': '.0002'})
            with self.assertRaisesRegex(ValueError, 'NEW_INCREASE_FAIL_CLOSED'):
                a.execute_fill('BTCUSDT', 'BUY', '.001', at + 2 * f.MINUTE + 1, 0,
                    'NATIVE_POSITIVE_BLOCKED', execution_mid_price='50000',
                    quote_available_us=at + 2 * f.MINUTE, available_quantity='.001')
            self.assertTrue(tree_equal(before, a.preview_state_token()))
            accounts.append(a)
        self.assertEqual(finance(accounts[0]), finance(accounts[1]))

    def test_genuine_daily_at_same_day_boundary_supersedes_just_born_cohort(self):
        sim, guard, rows = make_sim(.5, days=2)
        a = sim.account
        seed_paid(a, {'BTCUSDT': '.05'}, sim.start)
        set_capacity(sim)
        day = sim.start + f.DAY
        mark(a, day)
        receipt = sim.risk_schedule(day)
        self.assertEqual(receipt['action'], 'NATIVE_PAID_REDUCTION_INTENT')
        self.assertEqual(a._forecast_active['born_us'], day)
        target = quantities(a); target['BTCUSDT'] = D('.04')
        guard.schedule(target, day, 'DAILY_TARGET')
        self.assertIsNone(a._forecast_active)
        self.assertEqual(a.forecast_journal[-1]['kind'], 'SUPERSEDED_BY_GENUINE_NEW_STRATEGY_SIGNAL')

    def test_future_source_rows_do_not_change_original_cached_covariance_or_hash(self):
        caches = []
        for factor in (1., 17.):
            window, rows, decisions = synthetic_source(1, .5)
            for row in rows:
                if row['close_us'] > window['start']:
                    row['close'] *= factor
            sim, _ = f.construct_case(window, rows, decisions, np.zeros((1, 5)), generated_scope=f.GENERATED)
            seed_paid(sim.account, {'BTCUSDT': '.02'}, sim.start)
            trigger(sim)
            caches.append(deepcopy(sim.account._forecast_cache))
        self.assertEqual(caches[0], caches[1])

    def test_cohort_close_does_not_resignal_duplicate_or_refresh_original_latency(self):
        sim, guard, rows = make_sim(.5)
        a = sim.account
        seed_paid(a, {'BTCUSDT': '.05'}, sim.start)
        at, original = trigger(sim)
        pending = deepcopy(sim.pending)
        # New completed observations alone do not reset attempts or signal clocks.
        for k in range(1, 4):
            mark(a, at + k * f.MINUTE)
            receipt = sim.risk_schedule(at + k * f.MINUTE)
            self.assertEqual(receipt['reason'], 'OWNED_ACTIVE_COHORT_NO_DUPLICATE_RESIGNAL')
            self.assertEqual(sim.pending, pending)
        self.assertEqual(sum(r['kind'] == 'COHORT_CREATED' for r in a.forecast_journal), 1)

    def test_native_actual_close_and_reverse_open_share_one_prior_quote_capacity(self):
        sim, guard, rows = make_sim(.5, days=2)
        a = sim.account
        seed_paid(a, {'BTCUSDT': '.02'}, sim.start)
        signal = sim.start + f.DAY
        mark(a, signal)
        set_capacity(sim, {'BTCUSDT': D('.03')})
        target = quantities(a); target['BTCUSDT'] = D('-.02')
        guard.schedule(target, signal, 'DAILY_TARGET')
        count = len(a.trades)
        mark(a, signal + f.MINUTE)
        sim.attempt(signal + f.MINUTE, market())
        paid = list(a.trades)[count:]
        self.assertEqual([r['leg'] for r in paid], ['CLOSE', 'OPEN'])
        self.assertEqual(sum((D(r['decimal_strings']['quantity']) for r in paid), D(0)), D('.03'))
        self.assertEqual(a.positions['BTCUSDT'].quantity, D('-.01'))
        self.assertTrue(all(r['event_us'] == signal + f.MINUTE + 1 for r in paid))
        self.assertFalse(a.transfer_journal)

    def test_all_32_charged_corners_preserve_real_incomplete_paid_cohort(self):
        amplitude = .5 * np.sqrt(29 / (30 * 365))
        factor = np.asarray([-amplitude if i % 2 == 0 else amplitude for i in range(30)])
        returns = factor[:, None] * np.asarray([[1., 1., 0., 0., 0.]])
        sim, guard, rows = make_sim(returns=returns)
        a = sim.account
        seed_paid(a, {'BTCUSDT': '.049', 'ETHUSDT': '.01'}, sim.start)
        set_capacity(sim, {'BTCUSDT': D(1), 'ETHUSDT': D(0)})
        at, _ = trigger(sim)
        mark(a, at + f.MINUTE)
        sim.attempt(at + f.MINUTE, market())
        self.assertIsNotNone(a._forecast_active)
        self.assertGreater(len(a.forecast_fill_journal), 0)
        target = deepcopy(a._forecast_active['targets'])
        # Every dimension changes, so the native corner enumeration really
        # visits all32 endpoints while retaining the genuine active cohort.
        target.update(BTCUSDT=D('.038'), SOLUSDT=D(1), XRPUSDT=D(100), DOGEUSDT=D(1000))
        before, pending = a.preview_state_token(), deepcopy(sim.pending)
        oracle = f.fresh_preview(a, tier_name='MID', binding=guard.source.bind(sim.start),
            prices=dict(zip(f.S, map(lambda x: D(str(x)), BASE))),
            price_available_us=dict.fromkeys(f.S, at + 2 * f.MINUTE), pending=target,
            capacity=dict.fromkeys(f.S, D(100000)), event_us=at + 2 * f.MINUTE + 1,
            signal_us=sim.start, quote_available_us=at + 2 * f.MINUTE)
        witness = oracle.evaluate(target, D(1))
        self.assertTrue(witness['allowed'], witness['reason'])
        self.assertEqual(len(witness['corners_checked']), 32)
        self.assertTrue(tree_equal(before, a.preview_state_token()))
        self.assertEqual(sim.pending, pending)

    def test_later_native_hard_cap_replaces_only_owned_forecast_reducer(self):
        sim, guard, rows = make_sim(.401)
        a = sim.account
        seed_paid(a, {'BTCUSDT': '.05'}, sim.start)
        set_capacity(sim, {'BTCUSDT': D(0)})
        at, receipt = trigger(sim)
        self.assertEqual(receipt['action'], 'NATIVE_PAID_REDUCTION_INTENT')
        old = deepcopy(sim.pending['BTCUSDT'])
        later = at + f.MINUTE
        mark(a, later, {'BTCUSDT': 70000})
        self.assertEqual(a.status, 'BOUND_BREACH_REDUCTION_REQUIRED')
        nav = a.nav()
        notionals = [abs(a.positions[s].quantity) * a._mark(s) for s in f.S]
        scale = min(D(1), a.config.max_asset_weight * D('.99') * nav / max(notionals),
                    a.config.max_gross_weight * D('.99') * nav / sum(notionals, D(0)))
        expected = a.positions['BTCUSDT'].quantity * scale
        sim.risk_schedule(later)
        current = sim.pending['BTCUSDT']
        self.assertEqual(current['kind'], 'RISK_REDUCTION')
        self.assertEqual(current['signal_us'], later)
        self.assertNotEqual(current['order_id'], old['order_id'])
        self.assertEqual(current['target'], expected)
        self.assertLess(abs(current['target']), abs(old['target']))
        self.assertIsNone(a._forecast_active)
        self.assertEqual(a.forecast_journal[-1]['kind'], 'SUPERSEDED_BY_LATE_NATIVE_HARD_CAP')

    def test_protection_only_handback_inside_funding_batch_has_no_forecast_decision(self):
        sim, guard, rows = make_sim(.401)
        a = sim.account
        seed_paid(a, {'BTCUSDT': '.05'}, sim.start)
        at, _ = trigger(sim)
        later = at + f.MINUTE
        mark(a, later)
        sim.window['events'] = [dict(symbol=s, event_us=later,
            raw_rate=1. if s == 'BTCUSDT' else 0., reported_interval_hours=8.) for s in f.S]
        observed = []
        funding = a.apply_funding
        def trace_funding(*args, **kwargs):
            observed.append((args[0], a._forecast_active is not None))
            return funding(*args, **kwargs)
        before_hook = sim.forecast_controller.before_native_risk
        finances = []
        def trace_handback(event):
            before = a._balances()
            result = before_hook(event)
            finances.append((before, a._balances()))
            return result
        a.apply_funding = trace_funding
        sim.forecast_controller.before_native_risk = trace_handback
        try:
            with patch.object(f, 'project_target', side_effect=AssertionError('NO_NEW_FORECAST_BUDGET_DECISION')) as project:
                sim.funding_through(later, True)
                project.assert_not_called()
        finally:
            del a.apply_funding
            sim.forecast_controller.before_native_risk = before_hook
        self.assertEqual([s for s, active in observed], list(f.S))
        self.assertTrue(observed[0][1])
        self.assertFalse(any(active for s, active in observed[1:]))
        self.assertTrue(all(before == after for before, after in finances))
        self.assertEqual(sim.event_cursor, 5)
        self.assertEqual(len(a.funding), 5)
        notionals = [abs(a.positions[s].quantity) * a._mark(s) for s in f.S]
        scale = min(D(1), a.config.max_asset_weight * D('.99') * a.nav() / max(notionals),
                    a.config.max_gross_weight * D('.99') * a.nav() / sum(notionals, D(0)))
        self.assertEqual(sim.pending['BTCUSDT']['target'], a.positions['BTCUSDT'].quantity * scale)
        self.assertEqual(sum(r['kind'] == 'COHORT_CREATED' for r in a.forecast_journal), 1)
        self.assertIsNone(a._forecast_active)

    def test_pending_reversal_close_and_original_guarded_open_defer_without_postponement(self):
        sim, guard, rows = make_sim(.5)
        a = sim.account
        seed_paid(a, {'BTCUSDT': '.05'}, sim.start)
        set_capacity(sim)
        reverse = quantities(a); reverse['BTCUSDT'] = D('-.01')
        guard.bindings[sim.start] = guard.source.bind(sim.start)
        guard.original_schedule(reverse, sim.start, 'DAILY_TARGET')
        pending = deepcopy(sim.pending)
        at, receipt = trigger(sim)
        self.assertIn('DEFERRED_EXISTING_ORDINARY_REDUCTION', receipt['reason'])
        self.assertEqual(sim.pending, pending)
        self.assertIsNone(a._forecast_active)
        self.assertIsNone(a._forecast_cache)
        count = len(a.trades)
        sim.attempt(at, market())
        self.assertEqual(a.positions['BTCUSDT'].quantity, D('-.01'))
        paid = list(a.trades)[count:]
        self.assertEqual([r['leg'] for r in paid], ['CLOSE', 'OPEN'])
        self.assertTrue(all(r['event_us'] == at + 1 for r in paid))
        self.assertTrue(all(r['fill_id'].startswith(pending['BTCUSDT']['order_id']) for r in paid))
        self.assertIsNone(a._forecast_active)
        self.assertFalse(a.forecast_journal)

    def test_whole_cohort_defer_preserves_same_sign_zero_and_reversal_native_lifecycle(self):
        for oldtarget in (D('.049'), D(0), D('-.01')):
            with self.subTest(oldtarget=str(oldtarget)):
                sim, guard, rows = make_sim(.5)
                a = sim.account
                control, control_guard = f.E.construct_case(sim.window, rows,
                    np.asarray([sim.start], dtype=np.int64), np.zeros((1, 5)), generated_scope=f.GENERATED)
                for native_sim, native_guard in ((sim, guard), (control, control_guard)):
                    seed_paid(native_sim.account, {'BTCUSDT': '.05'}, native_sim.start)
                    native_guard.bindings[native_sim.start] = native_guard.source.bind(native_sim.start)
                    target = quantities(native_sim.account); target.update(BTCUSDT=oldtarget, ETHUSDT=D('.1'))
                    native_guard.original_schedule(target, native_sim.start, 'DAILY_TARGET')
                    set_capacity(native_sim, dict.fromkeys(f.S, D(0)))
                    native_sim.attempt(native_sim.start + f.MINUTE, market())
                    mark(native_sim.account, native_sim.start + 2 * f.MINUTE)
                    native_sim.attempt(native_sim.start + 2 * f.MINUTE, market())
                at = sim.start + 3 * f.MINUTE
                mark(a, at)
                mark(control.account, at)
                pending, before = deepcopy(sim.pending), finance(a)
                quote = deepcopy(sim.previous_quote)
                self.assertEqual(pending['BTCUSDT']['attempts'], 2)
                with patch.object(f, 'project_target', side_effect=AssertionError('DEFER_BEFORE_PROJECTION')) as projection:
                    receipt = sim.risk_schedule(at)
                    projection.assert_not_called()
                self.assertEqual(receipt['action'], 'HOLD')
                self.assertIn('DEFERRED_EXISTING_ORDINARY_REDUCTION', receipt['reason'])
                self.assertEqual(sim.pending, pending)
                self.assertEqual(finance(a), before)
                self.assertEqual(sim.previous_quote, quote)
                control.risk_schedule(at)
                self.assertEqual(sim.pending, control.pending)
                self.assertEqual(finance(a), finance(control.account))
                self.assertIsNone(a._forecast_active)
                self.assertIsNone(a._forecast_cache)
                self.assertFalse(a.forecast_journal)
                set_capacity(sim, {'BTCUSDT': D(1), 'ETHUSDT': D(0)})
                set_capacity(control, {'BTCUSDT': D(1), 'ETHUSDT': D(0)})
                count = len(a.trades)
                sim.attempt(at, market())
                control.attempt(at, market())
                paid = list(a.trades)[count:]
                self.assertTrue(paid)
                self.assertEqual(paid[0]['event_us'], at + 1)
                self.assertTrue(paid[0]['fill_id'].startswith(pending['BTCUSDT']['order_id']))
                self.assertEqual(finance(a), finance(control.account))
                self.assertEqual(sim.pending, control.pending)
                self.assertEqual(a.positions['BTCUSDT'].quantity, control.account.positions['BTCUSDT'].quantity)
                if oldtarget >= 0:
                    self.assertEqual(a.positions['BTCUSDT'].quantity, oldtarget)
                self.assertIsNone(a._forecast_active)
                mark(a, at + f.MINUTE)
                reconsidered = sim.risk_schedule(at + f.MINUTE)
                if oldtarget == D('.049'):
                    self.assertEqual(reconsidered['action'], 'NATIVE_PAID_REDUCTION_INTENT')
                    self.assertEqual(a._forecast_active['born_us'], at + f.MINUTE)
                else:
                    self.assertEqual(reconsidered['action'], 'HOLD')
                    self.assertIsNone(a._forecast_active)

    def test_original_ordinary_expiry_precedes_next_close_forecast_reconsideration(self):
        sim, guard, rows = make_sim(.5)
        a = sim.account
        seed_paid(a, {'BTCUSDT': '.05'}, sim.start)
        target = quantities(a); target['BTCUSDT'] = D('.049')
        guard.original_schedule(target, sim.start, 'DAILY_TARGET')
        original_id = sim.pending['BTCUSDT']['order_id']
        set_capacity(sim, dict.fromkeys(f.S, D(0)))
        sim.attempt(sim.start + f.MINUTE, market())
        for k in range(2, 6):
            at = sim.start + k * f.MINUTE
            mark(a, at)
            self.assertIn('DEFERRED_EXISTING_ORDINARY_REDUCTION', sim.risk_schedule(at)['reason'])
            self.assertEqual(sim.pending['BTCUSDT']['order_id'], original_id)
            self.assertEqual(sim.pending['BTCUSDT']['signal_us'], sim.start)
            sim.attempt(at, market())
        self.assertNotIn('BTCUSDT', sim.pending)
        self.assertTrue(any(r.get('order_id') == original_id and r.get('reason') == 'FIVE_ATTEMPTS_EXPIRED'
                            for r in sim.rejections))
        self.assertIsNone(a._forecast_active)
        at = sim.start + 6 * f.MINUTE
        mark(a, at)
        receipt = sim.risk_schedule(at)
        self.assertEqual(receipt['action'], 'NATIVE_PAID_REDUCTION_INTENT')
        self.assertEqual(a._forecast_active['born_us'], at)

    def test_real_active_cohort_snapshot_and_incomplete_report_are_json_serializable(self):
        sim, guard, rows = make_sim(.5)
        a = sim.account
        seed_paid(a, {'BTCUSDT': '.05'}, sim.start)
        trigger(sim)
        self.assertIsNotNone(a._forecast_active)
        snapshot = a.snapshot()
        self.assertTrue(all(type(q) is str for q in snapshot['forecast_active']['targets'].values()))
        json.dumps(snapshot, sort_keys=True, allow_nan=False)
        result = f.case_result(sim, guard)
        result.pop('minute'); result['targets'] = result['targets'].to_dicts()
        json.dumps(f.V2.OWNED.export_tree(result), sort_keys=True, allow_nan=False)


if __name__ == '__main__':
    unittest.main()
