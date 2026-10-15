"""Single-process generated-only original-D transport/native equivalence."""
from copy import deepcopy
from decimal import Decimal as Q
from pathlib import Path
import sys
import unittest

import cs_generated as g
import cs_signal as signal
from cs_config import TIERS


def finance(account):
    state = account.snapshot()
    return {key: state[key] for key in ('free_cash', 'unpaid_liability', 'positions', 'marks',
        'totals', 'trades', 'funding', 'fill_requests', 'funding_events', 'funding_ids')}


def marks(account, at, price=None):
    base = (50000, 2000, 20, .5, .05)
    return account.update_marks(at, {symbol: dict(price=str(price if j == 0 and price else base[j]),
        close_us=at, available_us=at) for j, symbol in enumerate(signal.SYMBOLS)})


class GeneratedNativeEquivalenceTests(unittest.TestCase):
    def test_native_D_financial_and_guard_code_objects_unchanged(self):
        e = g.native_reference(); v = e.V2
        self.assertIs(e.ExpansionAccount.monitor, e.D.Guard50ExitAccount.monitor)
        self.assertIs(e.ExpansionAccount._transfer, e.D.Guard50ExitAccount._transfer)
        self.assertIs(e.ExpansionAccount.execute_fill, e.D.Guard50ExitAccount.execute_fill)
        self.assertIs(e.ExpansionAccount._leg, v.ENGINE.USDTLinearPerpetualAccount._leg)
        self.assertIs(e.ExpansionAccount.apply_funding, e.D.Guard50ExitAccount.apply_funding)
        self.assertIs(e.ExpansionAccount.apply_funding, v.ContinuationAccount.apply_funding)
        self.assertIs(e.ContinuationGuard.schedule.__code__, v.native.PartialTierGuard.schedule.__code__)
        self.assertIs(e.ContinuationGuard._frozen_attempt.__code__, v.native.PartialTierGuard.attempt.__code__)
        self.assertIs(e.ContinuationGuard.attempt, e.D.ContinuationGuard.attempt)

    def test_synthetic_CS_target_transport_exact_native_finance_minutes_and_pending_all_tiers(self):
        e = g.native_reference()
        with g.generated_fixture(days=1) as f:
            targets = g.project_generated(f)
            for tier in TIERS:
                with self.subTest(tier=tier):
                    new, guard = g.construct_generated_case(targets, tier)
                    window, rows, decisions = g._synthetic_window(f)
                    reference, refguard = e.V2.native.build_case(window, rows, decisions, targets.common_tier[tier],
                        tier_name=tier, generated_scope=e.GENERATED)
                    for sim in (new, reference):
                        sim.pending_trace = []
                        original = sim.risk_schedule
                        def observed(at, *, sim=sim, original=original):
                            result = original(at)
                            sim.pending_trace.append((at, deepcopy(sim.pending)))
                            return result
                        sim.risk_schedule = observed
                        while sim.cursor < sim.end and sim.stop is None:
                            sim.advance_day()
                    self.assertEqual(finance(new.account), finance(reference.account))
                    self.assertEqual(new.pending_trace, reference.pending_trace)
                    self.assertEqual(new.result()['minute'].to_numpy().tobytes(),
                                     reference.result()['minute'].to_numpy().tobytes())
                    self.assertGreater(len(new.account.trades), 0); self.assertGreater(new.account.fees, 0)
                    checker = signal.ROOT / 'bounded_native_continuation_guard50_exit_expansion_20261015'
                    if str(checker) not in sys.path:
                        sys.path.insert(0, str(checker))
                    from saved_native_reconciliation import reconcile_saved_native
                    result = e.case_result(new, guard)
                    result.pop('minute'); result['targets'] = result['targets'].to_dicts()
                    result = e.V2.OWNED.export_tree(result)
                    audit = e.V2.OWNED.export_tree(new.account.snapshot())
                    proof = reconcile_saved_native(audit, result)
                    self.assertTrue(proof['passed']); self.assertFalse(proof['tolerance_or_epsilon_used'])
                    self.assertEqual(new.account.transfer_journal, [])
                    self.assertFalse(new.account.topup_enabled)
                    self.assertIsNone(new.account._execution_scope)
                    self.assertFalse(new.account.contract_metadata()['historical_execution_admitted'])
                    self.assertEqual(new.account.contract_metadata()['bound_nominal_tier'], tier)

    def test_all_32_shared_wallet_charged_preview_corners_do_not_mutate_actual_state(self):
        e = g.native_reference(); v = e.V2
        with g.generated_fixture(days=1) as f:
            targets = g.project_generated(f)
            _, rows, decisions = g._synthetic_window(f)
            at = int(decisions[0]); base = (50000, 2000, 20, .5, .05)
            binding = v.native.runtime()[5].CompletedBarSource(rows).bind(at)
            for tier in TIERS:
                sim, guard = g.construct_generated_case(targets, tier)
                account = sim.account; marks(account, at)
                quantities = {symbol: account._floor(symbol, Q(100) / Q(str(base[j])))
                    * (-1 if targets.raw_weekly[0, j] < 0 else 1)
                    for j, symbol in enumerate(e.S)}
                before = account.preview_state_token()
                oracle = e.fresh_preview(account, tier_name=tier, binding=binding,
                    prices={symbol: Q(str(base[j])) for j, symbol in enumerate(e.S)},
                    price_available_us=dict.fromkeys(e.S, at + e.MINUTE), pending=quantities,
                    capacity=dict.fromkeys(e.S, Q(100000)), event_us=at + e.MINUTE + 1,
                    signal_us=at, quote_available_us=at + e.MINUTE)
                receipt = oracle.evaluate(quantities, Q(1))
                self.assertTrue(receipt['allowed'], receipt['reason'])
                self.assertEqual(len(receipt['corners_checked']), 32)
                self.assertTrue(v.native._exact_tree_equal(before, account.preview_state_token()))
                fork = account.fork_for_preview()
                fork.pending_exits['BTCUSDT'] = {'signal_us': at, 'reason': 'GENERATED_ONLY'}
                self.assertFalse(account.pending_exits)

    def test_fixed_guard50_warning_and_transfer_prohibition_equal_original_D_all_tiers(self):
        e = g.native_reference(); v = e.V2
        for tier in TIERS:
            plain = v.grid.make_account(tier, 'BASE27')
            kwargs = dict(symbols=e.S, instrument_profiles=plain.instrument_profiles, generated_scope=e.GENERATED)
            old = e.D.Guard50ExitAccount(plain.config, **kwargs)
            new = e.ExpansionAccount(plain.config, tier_name=tier, **kwargs)
            for account in (old, new):
                event = e.MINUTE + 1; marks(account, event - 1)
                account.execute_fill('BTCUSDT', 'SELL', '.02', event, 0, 'GENERATED_FIXED_GUARD50',
                    execution_mid_price='50000', quote_available_us=event - 1, available_quantity='.02')
                marks(account, 2 * e.MINUTE, 75000)
                account.monitor('MONITOR:' + str(2 * e.MINUTE), 2 * e.MINUTE)
            self.assertEqual(finance(old), finance(new))
            self.assertEqual(old.pending_exits, new.pending_exits)
            self.assertIn('BTCUSDT', new.pending_exits)
            self.assertEqual(new.pending_exits['BTCUSDT']['reason'], 'GUARD50_PAID_EXIT_NO_TOPUP')
            before = new.preview_state_token()
            with self.assertRaisesRegex(ValueError, 'TRANSFERS_FORBIDDEN'):
                new._transfer('BTCUSDT', Q(1), 2 * e.MINUTE, 'GENERATED_FORBIDDEN')
            self.assertTrue(v.native._exact_tree_equal(before, new.preview_state_token()))
            self.assertEqual(new.transfer_journal, []); self.assertFalse(new.topup_enabled)

    def test_no_historical_constructor_arguments_or_laundered_fake_objects(self):
        with g.generated_fixture() as f:
            targets = g.project_generated(f)
            with self.assertRaises(TypeError):
                g.construct_generated_case(targets, 'MID', historical_scope={'approved': True})
            with self.assertRaises(TypeError):
                g.construct_generated_case(targets, 'MID', window={'actual': True})
            with self.assertRaises(ValueError):
                g.construct_generated_case(targets, 'OTHER')
            native = g.native_reference()
            window, rows, decisions = g._synthetic_window(f)
            with self.assertRaisesRegex(ValueError, 'INTERNALLY_SEALED_GENERATED_NATIVE_INPUTS_REQUIRED'):
                native._construct_case(window, rows, decisions, targets.common_tier['MID'],
                    tier_name='MID', generated_scope=native.GENERATED)
            window['start'] = 1640995200000000
            with self.assertRaisesRegex(ValueError, 'INTERNALLY_SEALED_GENERATED_NATIVE_INPUTS_REQUIRED'):
                native._construct_case(window, rows, decisions, targets.common_tier['MID'],
                    tier_name='MID', generated_scope=native.GENERATED)
            self.assertFalse(g._LIVE_NATIVE_INPUTS)

    def test_unknown_source_quality_never_becomes_genuine_or_inherits_zero_impact(self):
        e = g.native_reference()
        plain = e.V2.grid.make_account('MID', 'BASE27')
        account = e.ExpansionAccount(plain.config, symbols=e.S,
            instrument_profiles=plain.instrument_profiles, generated_scope=e.GENERATED, tier_name='MID')
        event = e.MINUTE + 1; marks(account, event - 1)
        account.execute_fill('BTCUSDT', 'SELL', '.02', event, 0, 'GENERATED_UNKNOWN_QUALITY',
            execution_mid_price='50000', quote_available_us=event - 1, available_quantity='.02')
        at = 2 * e.MINUTE
        account._quality_intervals = ((at, at + e.MINUTE, e.S),)
        marks(account, at, 75000); account.monitor('MONITOR:' + str(at), at)
        self.assertFalse(account.pending_exits); self.assertFalse(account.can_increase(at))
        marks(account, at + e.MINUTE, 75000)
        account.monitor('MONITOR:' + str(at + e.MINUTE), at + e.MINUTE)
        self.assertIn('BTCUSDT', account.pending_exits)
        self.assertFalse(account.transfer_journal)

    def test_generated_native_debt_remains_debt_and_halt_cannot_resume(self):
        e = g.native_reference()
        plain = e.V2.grid.make_account('MID', 'BASE27')
        account = e.ExpansionAccount(plain.config, symbols=e.S,
            instrument_profiles=plain.instrument_profiles, generated_scope=e.GENERATED, tier_name='MID')
        event = e.MINUTE + 1; marks(account, event - 1)
        account.execute_fill('BTCUSDT', 'SELL', '.02', event, 0, 'GENERATED_DEBT',
            execution_mid_price='50000', quote_available_us=event - 1, available_quantity='.02')
        at = 2 * e.MINUTE; marks(account, at - 1)
        account.apply_funding('BTCUSDT', 'GENERATED_DEBIT', at, '-1000', at)
        self.assertGreater(account.unpaid_liability, 0)
        debt = account.unpaid_liability
        self.assertEqual(account.status, 'BANKRUPT_HALT')
        with self.assertRaisesRegex(RuntimeError, 'BANKRUPT_HALT'):
            marks(account, at + e.MINUTE)
        account.monitor('MONITOR:' + str(at), at)
        self.assertEqual(account.status, 'BANKRUPT_HALT'); self.assertEqual(account.unpaid_liability, debt)
        self.assertFalse(account.can_increase(at + e.MINUTE)); self.assertFalse(account.transfer_journal)
        with self.assertRaisesRegex(NotImplementedError, 'NOT_CERTIFIED'):
            account.from_snapshot({})


class CoupledSourceQualityTests(unittest.TestCase):
    def test_carry_keeps_source_clock_unknown_before_native_risk(self):
        from types import MethodType
        from cs_quality import original_quality
        e = g.native_reference()
        plain = e.V2.grid.make_account('MID', 'BASE27')
        a = e.ExpansionAccount(plain.config, symbols=e.S, instrument_profiles=plain.instrument_profiles,
                              generated_scope=e.GENERATED, tier_name='MID')
        at = 2 * e.MINUTE
        marks(a, e.MINUTE)
        a.execute_fill('BTCUSDT', 'SELL', '.02', e.MINUTE + 1, 0, 'FAKE_CARRY',
                       execution_mid_price='50000', quote_available_us=e.MINUTE, available_quantity='.02')
        marks(a, at, 75000)
        cell = original_quality().QualityCell('BTCUSDT', at, at + e.MINUTE, at + e.MINUTE,
            '75000', at - e.MINUTE, at, at, at, at, 'a' * 64, 'GENERATED_GENUINE_ROW')
        a._source_quality_cells = (cell,)
        a._quality_intervals = ((cell.completed_us, cell.completed_us + e.MINUTE, ('BTCUSDT',)),)
        seen = []; original = a._risk
        def risk(_a, phase):
            row = _a.marks['BTCUSDT'][-1]
            seen.append((_a.mark_quality['BTCUSDT'], row['close_us'], row['available_us']))
            return original(phase)
        a._risk = MethodType(risk, a)
        marks(a, cell.completed_us, 75000)
        del a._risk
        self.assertTrue(seen)
        self.assertTrue(all(row == ('UNKNOWN_OR_DERIVED', at, at) for row in seen))
        a.monitor('MONITOR:' + str(cell.completed_us), cell.completed_us)
        self.assertFalse(a.pending_exits); self.assertFalse(a.can_increase(cell.completed_us))
        self.assertFalse(a.transfer_journal)

    def test_per_asset_live_age_waits_for_installed_genuine_recovery(self):
        from cs_quality import original_quality
        e = g.native_reference()
        with g.generated_fixture(days=1) as f:
            targets = g.project_generated(f)
            sim, guard = g.construct_generated_case(targets, 'MID')
            a = sim.account; at = sim.start + 2 * e.MINUTE; marks(a, at)
            cell = original_quality().QualityCell('BTCUSDT', at, at + e.MINUTE, at + e.MINUTE,
                '50000', at - e.MINUTE, at, at, at, at, 'a' * 64, 'GENERATED_BTC_ANCHOR')
            a._source_quality_cells = (cell,)
            a._quality_intervals = ((cell.completed_us, cell.completed_us + e.MINUTE, ('BTCUSDT',)),)
            quality = guard.causal_mark_quality_guard; quality.source_quality_cells = (cell,)
            marks(a, cell.completed_us)
            witness = quality.quality_witness(cell.completed_us + 5 * e.MINUTE)
            self.assertEqual(witness['affected_source_cells'][0]['original_genuine_observation_us'], at)
            self.assertEqual(witness['affected_source_cells'][0]['original_genuine_age_us'], 6 * e.MINUTE)
            marks(a, cell.completed_us + e.MINUTE)
            self.assertIsNone(quality.quality_witness(cell.completed_us + e.MINUTE))

    def test_sameclock_funding_before_warning_and_pending_schedule(self):
        e = g.native_reference()
        with g.generated_fixture(days=1) as f:
            targets = g.project_generated(f); sim, guard = g.construct_generated_case(targets, 'HIGH')
            a = sim.account; start = sim.start; event = start + e.MINUTE + 1
            marks(a, event - 1)
            a.execute_fill('BTCUSDT', 'SELL', '.02', event, start, 'GENERATED_SAMECLOCK',
                execution_mid_price='50000', quote_available_us=event - 1, available_quantity='.02')
            at = start + 2 * e.MINUTE; marks(a, at, 75000)
            sim.window['events'] = [dict(symbol=s, event_us=at, raw_rate=.0001,
                reported_interval_hours=8.) for s in e.S]
            seen = []; original = a.apply_funding
            def funded(*args, **kwargs):
                seen.append((args[0], bool(a.pending_exits))); return original(*args, **kwargs)
            a.apply_funding = funded; sim.funding_through(at, True); del a.apply_funding
            self.assertEqual(len(seen), 5); self.assertFalse(any(flag for _, flag in seen))
            self.assertEqual(sim.pending['BTCUSDT']['kind'], 'PROTECTIVE_STOP')
            self.assertEqual(sim.pending['BTCUSDT']['signal_us'], at)
            self.assertFalse(a.transfer_journal)


if __name__ == '__main__':
    unittest.main()
