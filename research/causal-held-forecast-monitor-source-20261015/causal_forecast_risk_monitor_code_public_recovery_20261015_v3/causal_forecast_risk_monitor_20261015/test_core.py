"""Generated-only local core accounting and ownership checks."""
from copy import deepcopy
from decimal import Decimal as Q
import importlib.util
import math
import json
import unittest
import numpy as np
import forecast_monitor as f
from test_native_runtime import fixture, BASE


def active_fixture(days=1):
    window, rows, decisions = fixture(days)
    start = int(decisions[0])
    for row in rows:
        j = f.S.index(row['symbol'])
        day = (row['close_us']-start)//f.DAY
        row['close'] = float(BASE[j]*math.exp(.1*math.sin(day*1.1+j*.6)+.04*math.cos(day*.3+j*.8)))
    for key in ('open', 'close', 'mark'):
        window['market']['BTCUSDT'][key][100:] = 500000.
    return window, rows, decisions, np.full((days, 5), .03)


def load_checker():
    spec = importlib.util.spec_from_file_location('_forecast_native40_checker', f.FROZEN/'saved_native_reconciliation.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class CoreTests(unittest.TestCase):
    def test_active_full_calendar_and_chronological_native40_raw100(self):
        window, rows, decisions, targets = active_fixture()
        sim, guard = f.construct_case(window, rows, decisions, targets, generated_scope=f.GENERATED)
        sim.advance_day()
        a = sim.account
        self.assertIsNone(sim.stop)
        self.assertEqual(sim.rows_written, 1440)
        created = [r for r in a.forecast_journal if r['kind'] == 'COHORT_CREATED']
        self.assertTrue(created)
        self.assertGreater(len(a.forecast_fill_journal), 0)
        self.assertTrue(all(r['projected_variance'] < r['current_variance'] for r in created))
        self.assertTrue(all(Q(r['paid_fee_delta']) > 0 for r in a.forecast_fill_journal))
        self.assertTrue(any(r['kind'] == 'COMPLETED_NATIVE_PAID_TARGET' for r in a.forecast_journal))
        audit = f.V2.OWNED.export_tree(a.snapshot())
        result = f.case_result(sim, guard)
        result.pop('minute')
        result['targets'] = result['targets'].to_dicts()
        result = f.V2.OWNED.export_tree(result)
        checker = load_checker()
        proof = checker.reconcile_saved_native(audit, result, expected_continuation_version=f.VERSION)
        self.assertTrue(proof['passed'])
        self.assertEqual(proof['native_financial_precision'], 40)
        self.assertEqual(proof['raw_diagnostic_precision'], 100)
        self.assertIn('raw_precision100_stored_delta_terminal_residuals', proof)
        self.assertFalse(proof['tolerance_or_epsilon_used'])
        for key in ('free_cash', 'unpaid_liability'):
            bad = deepcopy(audit)
            bad[key] = str(Q(bad[key])+1)
            with self.assertRaises(ValueError):
                checker.reconcile_saved_native(bad, result)

    def test_original_financial_kernel_and_immutable_owned_history(self):
        window, rows, decisions = fixture(1)
        sim, guard = f.construct_case(window, rows, decisions, np.zeros((1, 5)), generated_scope=f.GENERATED)
        a = sim.account
        self.assertIs(a._leg.__func__, f.V2.ENGINE.USDTLinearPerpetualAccount._leg)
        self.assertIs(a.apply_funding.__func__, f.E.ExpansionAccount.apply_funding)
        self.assertIs(a._transfer.__func__, f.E.D.Guard50ExitAccount._transfer)
        self.assertIs(guard._frozen_attempt.__func__.__code__, f.V2.native.PartialTierGuard.attempt.__code__)
        for name in f.NEW_JOURNALS:
            journal = getattr(a, name)
            with self.assertRaises(TypeError):
                setattr(a, name, [])
            with self.assertRaises(TypeError):
                delattr(a, name)
            with self.assertRaises(Exception):
                journal.clear()
        with self.assertRaisesRegex(ValueError, 'TRANSFERS_FORBIDDEN'):
            a._transfer('BTCUSDT', Q(1), sim.start, 'NO_TOPUP')
        with self.assertRaises(NotImplementedError):
            a.from_snapshot(a.snapshot())

    def test_fresh_32_charged_corners_keep_all_owned_policy_state(self):
        window, rows, decisions = fixture(1)
        sim, guard = f.construct_case(window, rows, decisions, np.zeros((1, 5)), generated_scope=f.GENERATED)
        a, signal = sim.account, int(decisions[0])
        a.update_marks(signal, {s: dict(price=str(BASE[j]), close_us=signal, available_us=signal) for j, s in enumerate(f.S)})
        binding = guard.source.bind(signal)
        # Explicit generated nonfinancial policy state exercises every new fork
        # field while charged previews use the real original completed source.
        a._forecast_cache = dict(binding_signal_us=signal, covariance_available_us=signal,
            source_sha256=binding.source_sha256, covariance=binding.covariance)
        a._forecast_active = dict(cohort_id='GENERATED_OWNERSHIP', born_us=signal,
            targets=dict.fromkeys(f.S, Q(0)), alpha=.5, projected_variance=0.,
            current_variance=.01, source_sha256=binding.source_sha256, orders={}, renewals=0)
        a.forecast_journal.append(dict(kind='GENERATED_OWNERSHIP_SENTINEL'))
        json.dumps(a.snapshot(),allow_nan=False)
        json.dumps(f.case_result(sim,guard)['forecast_risk_monitor'],allow_nan=False)
        target = {s: a._floor(s, Q(100)/Q(str(BASE[j]))) for j, s in enumerate(f.S)}
        before, pending = a.preview_state_token(), deepcopy(sim.pending)
        oracle = f.fresh_preview(a, tier_name='MID', binding=binding,
            prices={s: Q(str(BASE[j])) for j, s in enumerate(f.S)},
            price_available_us=dict.fromkeys(f.S, signal+f.MINUTE), pending=target,
            capacity=dict.fromkeys(f.S, Q(100000)), event_us=signal+f.MINUTE+1,
            signal_us=signal, quote_available_us=signal+f.MINUTE)
        witness = oracle.evaluate(target, Q(1))
        self.assertTrue(witness['allowed'], witness['reason'])
        self.assertEqual(len(witness['corners_checked']), 32)
        self.assertTrue(f.V2.native._exact_tree_equal(before, a.preview_state_token()))
        self.assertEqual(pending, sim.pending)
        clone = a.fork_for_preview()
        self.assertIs(type(clone), f.ForecastRiskAccount)
        self.assertIsNone(clone.liquidation_callback)
        self.assertIs(clone.forecast_journal.token()[0], a.forecast_journal.token()[0])
        clone.forecast_journal.append(dict(kind='FORK_ONLY'))
        clone._forecast_active['renewals'] = 99
        clone._forecast_noops['FORK_ONLY'] = {}
        self.assertEqual(a._forecast_active['renewals'], 0)
        self.assertNotIn('FORK_ONLY', a._forecast_noops)
        self.assertEqual(len(a.forecast_journal), 1)

    def test_saved_policy_metadata_no_transfer_and_resealed_tampering(self):
        import run_forecast as runner
        window,rows,decisions,targets=active_fixture()
        sim,guard=f.construct_case(window,rows,decisions,targets,generated_scope=f.GENERATED)
        sim.advance_day()
        audit=f.V2.OWNED.export_tree(sim.account.snapshot())
        result=f.case_result(sim,guard)
        result.pop('minute');result['targets']=result['targets'].to_dicts()
        result=f.V2.OWNED.export_tree(result)
        self.assertTrue(runner.validate_policy_evidence(audit,result,historical=False))
        with self.assertRaises(ValueError):runner.validate_policy_evidence(audit,result,historical=True)
        for mutate in (
            lambda a,r:a['transfer_journal'].append({'amount':'1'}),
            lambda a,r:a['transfer_ids'].__setitem__('FORGED',{}),
            lambda a,r:r['continuation_economic_report']['transfers'].append({'amount':'1'}),
            lambda a,r:r['common_execution_policy'].__setitem__('no_autonomous_rerisking',False),
            lambda a,r:r['forecast_risk_monitor'].__setitem__('original_mid_budget',.11),
            lambda a,r:r['summary']['contract'].__setitem__('topup_enabled',True),
            lambda a,r:a['forecast_journal'][0].__setitem__('current_variance',-1),
            lambda a,r:a['forecast_journal'][0].__setitem__('sigma',float('inf')),
            lambda a,r:a['forecast_journal'][0].__setitem__('alpha',float('nan')),
        ):
            a,r=deepcopy(audit),deepcopy(result);mutate(a,r)
            with self.assertRaises(ValueError):runner.validate_policy_evidence(a,r,historical=False)

    def test_real_generated_funding_debt_never_resumes(self):
        window, rows, decisions = fixture(1)
        sim, guard = f.construct_case(window, rows, decisions, np.zeros((1, 5)), generated_scope=f.GENERATED)
        a, signal = sim.account, int(decisions[0])
        def marks(at):
            a.update_marks(at, {s: dict(price=str(BASE[j]), close_us=at, available_us=at) for j, s in enumerate(f.S)})
        marks(signal+f.MINUTE)
        a.execute_fill('BTCUSDT', 'BUY', '.02', signal+f.MINUTE+1, signal,
                       'GENERATED_DEBT_SEED', execution_mid_price='50000',
                       quote_available_us=signal+f.MINUTE, available_quantity='.02')
        at = signal+2*f.MINUTE
        marks(at-1)
        a.apply_funding('BTCUSDT', 'GENERATED_REAL_DEBT', at, '1000', at)
        self.assertGreater(a.unpaid_liability, 0)
        self.assertIn(a.status, f.V2.P.HALTS)
        with self.assertRaisesRegex(RuntimeError, 'BANKRUPT_HALT'):
            marks(at+f.MINUTE)
        self.assertIsNone(sim.risk_schedule(at+f.MINUTE))
        self.assertIsNone(a._forecast_active)
        self.assertEqual(list(a.forecast_journal), [])
        self.assertGreater(a.unpaid_liability, 0)
        self.assertTrue(load_checker().reconcile_saved_native(f.V2.OWNED.export_tree(a.snapshot()))['passed'])


if __name__ == '__main__':
    unittest.main()
