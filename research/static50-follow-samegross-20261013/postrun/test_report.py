"""Pure synthetic report tests: no historical runner, restore or report run."""
from __future__ import annotations

import builtins
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import build_report as report


def minute_array(n):
    import numpy as np
    data = np.zeros((n, 36), dtype=np.float64)
    data[:, 0] = 10000.0
    data[:, 34] = 0.5
    return data


def saved_recovery(root: Path, arrays):
    import numpy as np
    root.mkdir()
    chunks = []
    for day, array in enumerate(arrays):
        path = root / f'DAY_{day:04d}.npz'
        np.savez_compressed(path, minute_chunk=array)
        chunks.append({'path': path.name, 'rows': len(array), 'columns': 36, 'SHA256': report.sha(path)})
    (root / 'POINTER.json').write_text(json.dumps({'completed_minutes': sum(len(a) for a in arrays), 'chunks': chunks}))
    return root


def summary(n=1440, paid=True, quantity='0', status='ACTIVE'):
    return {'completed_minutes': n, 'net_PnL': 100.0, 'completion': 'COMPLETE_CONDITIONAL_ACCOUNT',
            'account_status': status, 'terminal_cash_realized': paid, 'positions': {'X': {'quantity': quantity}}}


def numeric_for(array, start=0):
    import numpy as np
    names = ('nav', 'free_cash', 'isolated_balance', 'gross_notional', 'net_signed_notional',
             'cumulative_fees', 'cumulative_execution_costs', 'cumulative_funding', 'cumulative_turnover')
    columns = [{'name': names[i] if i < 9 else 'column_' + str(i), 'dtype': '<f8', 'rows': len(array),
                'raw_SHA256': hashlib.sha256(array[:, i].tobytes()).hexdigest()} for i in range(36)]
    clocks = start + np.arange(1, len(array) + 1, dtype=np.int64) * report.MINUTE
    columns.append({'name': 'close_us', 'dtype': '<i8', 'rows': len(array), 'raw_SHA256': hashlib.sha256(clocks.tobytes()).hexdigest()})
    return {'columns': columns}


class ReportSynthetic(unittest.TestCase):
    def synthetic_audit(self):
        go = {'parent_GO': True, 'approved_stages': ['AUDIT'], 'manifest_SHA256': 'manifest',
              'state_locator': 'synthetic/state', 'run_binding_SHA256': 'run',
              'controller_receipt_SHA256': 'controller', 'historical_controller_released': True}
        text = json.dumps(go, indent=2) + '\n'
        return {'stage': 'AUDIT', 'status': 'ALL_OBSERVERS_FINISHED', 'case_ids': list(report.CASE_IDS),
                'per_observer': {key: {} for key in report.CASE_IDS}, 'unstarted_observer_ids': [],
                'financial_advances': 0, 'historical_wallets_opened': 0, 'observer_manifest_SHA256': 'manifest',
                'postrun_GO_text': text, 'postrun_GO_SHA256': hashlib.sha256(text.encode()).hexdigest()}

    def test_import_is_stdlib_only_and_reads_no_history(self):
        original = builtins.__import__
        forbidden = ('numpy', 'run_cases', 'fine_account', 'quant', 'scripts', 'original_follow_adapter', 'cold_audit')
        def guarded(name, *args, **kwargs):
            if any(name == prefix or name.startswith(prefix + '.') for prefix in forbidden):
                self.fail('Report import loaded forbidden module: ' + name)
            return original(name, *args, **kwargs)
        with patch('builtins.__import__', side_effect=guarded), patch.object(Path, 'read_text', side_effect=AssertionError('import opened history')):
            spec = importlib.util.spec_from_file_location('synthetic_report_import', HERE / 'build_report.py')
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
        self.assertEqual(len(module.CASE_IDS), 6)

    def test_worker_gate_is_first_and_blocks_inputs(self):
        with patch.object(report.gate, 'require_bounded_worker', side_effect=RuntimeError('unbounded')), \
             patch.object(report.gate, 'verify_observer_go', side_effect=AssertionError('GO called before bounds')), \
             patch.object(report, 'read_json', side_effect=AssertionError('Input opened before bounds')):
            with self.assertRaisesRegex(RuntimeError, 'unbounded'):
                report.main()

    def test_report_GO_blocks_inputs(self):
        with patch.object(report.gate, 'require_bounded_worker', return_value=None), \
             patch.object(report.gate, 'verify_observer_go', side_effect=RuntimeError('no report GO')), \
             patch.object(report, 'read_json', side_effect=AssertionError('Input opened before GO')):
            with self.assertRaisesRegex(RuntimeError, 'no report GO'):
                report.main()

    def test_audit_exact_GO_bytes_and_complete_population(self):
        audit = self.synthetic_audit()
        kwargs = dict(manifest_sha='manifest', run_binding_sha='run', controller_sha='controller', state_locator='synthetic/state')
        report.verify_audit_stage(audit, **kwargs)
        audit['postrun_GO_text'] += ' '
        with self.assertRaisesRegex(ValueError, 'bytes/hash'):
            report.verify_audit_stage(audit, **kwargs)
        audit = self.synthetic_audit()
        audit['case_ids'].pop()
        with self.assertRaisesRegex(ValueError, 'full-population'):
            report.verify_audit_stage(audit, **kwargs)
        audit = self.synthetic_audit()
        with self.assertRaisesRegex(ValueError, 'authorize'):
            report.verify_audit_stage(audit, **{**kwargs, 'run_binding_sha': 'wrong'})

    def test_cash_requires_full_exact_flat_and_official_result(self):
        self.assertTrue(report.censoring(summary(), 1440, official_result=True)['paid_flat'])
        for s, present in ((summary(quantity='0.00000001'), True), (summary(paid=False), True),
                           (summary(n=100), True), (summary(), False)):
            row = report.censoring(s, 1440, official_result=present)
            self.assertFalse(row['paid_flat'])
            self.assertIsNone(row['paid_cash_PnL_USDT'])
            self.assertIsNone(row['annual_paid_return'])
        tiny = report.censoring(summary(quantity='-1.83117484', paid=False), 1440, official_result=True)
        self.assertEqual(tiny['observation_class'], 'FULL_MARKED')
        halted = report.censoring(summary(n=100, paid=False, quantity='2', status='LIQUIDATION_REQUIRED_HALT'), 1440, official_result=True)
        self.assertEqual(halted['observation_class'], 'PARTIAL_HALTED')

    def test_contrast_refuses_cash_mark_and_vol_across_horizons(self):
        a = {'available': True, **report.censoring(summary(), 1440, official_result=True), 'marked_PnL_USDT': 100, 'annual_daily_vol': .1}
        b = {'available': True, **report.censoring({**summary(), 'net_PnL': 180}, 1440, official_result=True), 'marked_PnL_USDT': 180, 'annual_daily_vol': .2}
        self.assertEqual(report.contrast(a, b)['paid_cash_PnL_delta_USDT'], 80)
        b.update(report.censoring(summary(paid=False, quantity='1'), 1440, official_result=True))
        self.assertIsNone(report.contrast(a, b)['paid_cash_PnL_delta_USDT'])
        self.assertTrue(report.contrast(a, b)['marked_full_calendar_delta_is_not_paid_profit'])
        b.update(report.censoring(summary(n=500), 1440, official_result=True))
        answer = report.contrast(a, b)
        self.assertTrue(all(value is None for value in answer['same_full_calendar_observed_deltas'].values()))
        self.assertIsNone(answer['annual_paid_return_delta'])
        self.assertIsNone(report.contrast(a, {'available': False})['paid_cash_PnL_delta_USDT'])

    def test_daily_vol_exact_old_formula_and_no_partial_day(self):
        import numpy as np
        nav = [10100., 10000., 10300.]
        row = report.daily_stats(nav)
        returns = np.diff(np.r_[10000., nav]) / np.r_[10000., nav][:-1]
        self.assertEqual(row['annualized_daily_vol'], float(returns.std(ddof=1) * np.sqrt(365)))
        with tempfile.TemporaryDirectory() as temporary:
            first, second, partial = minute_array(1440), minute_array(1440), minute_array(3)
            first[-1, 0], second[-1, 0], partial[-1, 0] = 10100, 10000, 9000
            recovery = saved_recovery(Path(temporary) / 'r', [first, second, partial])
            observed = report.stream_prefix(recovery, 2883)
            self.assertEqual(observed['daily_statistics'], report.daily_stats([10100, 10000]))
            self.assertEqual(observed['last_completed_minute_marked_PnL_USDT'], -1000)

    def test_two_different_pairwise_prefixes_and_three_way_prefix(self):
        import numpy as np
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            arrays = {name: minute_array(n) for name, n in (('control', 5), ('pool', 8), ('old', 3))}
            arrays['control'][:, 0] = [10100, 10200, 10300, 10400, 10500]
            arrays['pool'][:, 0] = [10050, 10100, 10200, 10300, 10400, 10500, 10600, 10700]
            arrays['old'][:, 0] = [10100, 10200, 10400]
            arrays['control'][:, 29] = .1
            arrays['pool'][:, 29] = .3
            paths = {name: saved_recovery(root / name, [array]) for name, array in arrays.items()}
            rows = {name: {'completed_minutes': len(array)} for name, array in arrays.items()}
            weights = {name: np.zeros((1, 5), dtype=np.float64) for name in arrays}
            first = report.common_prefix({k: rows[k] for k in ('control', 'pool')}, paths, weights, start_us=0)
            second = report.common_prefix({k: rows[k] for k in ('old', 'pool')}, paths, weights, start_us=0)
            third = report.common_prefix(rows, paths, weights, start_us=0)
            self.assertEqual((first['common_completed_minutes'], second['common_completed_minutes'], third['common_completed_minutes']), (5, 3, 3))
            self.assertEqual(report.prefix_deltas(first, 'control', 'pool')['b_minus_a']['last_completed_minute_marked_PnL_USDT'], -100)
            self.assertEqual(report.prefix_deltas(second, 'old', 'pool')['b_minus_a']['last_completed_minute_marked_PnL_USDT'], -200)
            self.assertEqual(first['paths']['control']['minute_prefix_raw_SHA256'], hashlib.sha256(arrays['control'].tobytes()).hexdigest())
            self.assertAlmostEqual(report.prefix_deltas(first, 'control', 'pool')['b_minus_a']['mean_l1_target_weight_gap_of_prefix'], .2)
            self.assertIsNone(first['paid_cash_PnL_delta_USDT'])
            self.assertEqual(first['paths']['pool']['financial_advances'], 0)

    def test_chunk_SHA_checked_beyond_selected_prefix(self):
        with tempfile.TemporaryDirectory() as temporary:
            recovery = saved_recovery(Path(temporary) / 'r', [minute_array(1440), minute_array(1)])
            with (recovery / 'DAY_0001.npz').open('ab') as file:
                file.write(b'tamper')
            with self.assertRaisesRegex(ValueError, 'SHA'):
                report.stream_prefix(recovery, 1)

    def test_chunk_geometry_horizon_and_nonfinite_rejected(self):
        import numpy as np
        for array in (np.zeros((2, 35), dtype=np.float64), np.zeros((2, 36), dtype=np.float32), minute_array(2)):
            if array.shape == (2, 36) and array.dtype == np.float64:
                array[0, 0] = float('nan')
            with tempfile.TemporaryDirectory() as temporary:
                recovery = saved_recovery(Path(temporary) / 'r', [array])
                with self.assertRaises(ValueError):
                    report.stream_prefix(recovery, 2)
        with tempfile.TemporaryDirectory() as temporary:
            recovery = saved_recovery(Path(temporary) / 'r', [minute_array(2)])
            with self.assertRaisesRegex(ValueError, 'exceeds'):
                report.stream_prefix(recovery, 3)

    def test_complete_numeric_fingerprints_verified_without_financial_code(self):
        with tempfile.TemporaryDirectory() as temporary:
            array = minute_array(4)
            recovery = saved_recovery(Path(temporary) / 'r', [array])
            numeric = numeric_for(array)
            self.assertTrue(report.stream_prefix(recovery, 4, numeric=numeric, start_us=0)['all_saved_numeric_bits_verified'])
            numeric['columns'][30]['raw_SHA256'] = '0' * 64
            with self.assertRaisesRegex(ValueError, 'numeric minute bits'):
                report.stream_prefix(recovery, 4, numeric=numeric, start_us=0)

    def test_zero_observation_has_no_pnl_drawdown_or_vol_claim(self):
        with tempfile.TemporaryDirectory() as temporary:
            recovery = saved_recovery(Path(temporary) / 'r', [])
            row = report.stream_prefix(recovery, 0)
            self.assertIsNone(row['last_completed_minute_marked_PnL_USDT'])
            self.assertIsNone(row['max_drawdown_of_completed_minute_prefix'])
            self.assertIsNone(row['daily_statistics']['annualized_daily_vol'])

    def test_frozen_target_activity_netting_description(self):
        import numpy as np
        original = np.zeros((2, 5), dtype=np.float64)
        follow = original.copy()
        original[:, 0] = .2
        follow[0, 0] = -.1
        control = original * .5
        pool = .5 * original + .5 * follow
        result = report.target_description(control, pool, original, follow)
        self.assertEqual(result['FOLLOW_cash_days'], 1)
        self.assertEqual(result['opposite_nonzero_S_F_symbol_day_cells'], 1)
        self.assertEqual(result['new_control_downscaled_days_vs_original_S'], 2)
        self.assertAlmostEqual(result['mean_raw_pool_internal_netting_gross_reduction'], .05)
        self.assertTrue(result['equal_target_gross_is_not_equal_covariance_or_realized_risk'])

    def test_matched_volatility_uses_prefix_instead_of_full_vs_partial(self):
        a = {'available': True, **report.censoring(summary(), 1440, official_result=True), 'annual_daily_vol': .1}
        b = {'available': True, **report.censoring(summary(), 1440, official_result=True), 'annual_daily_vol': .2}
        full = report.matched_volatility(a, b, None)
        self.assertEqual(full['scope'], 'SAME_FULL_CALENDAR')
        self.assertAlmostEqual(full['b_minus_a_daily_vol_annualized'], .1)
        self.assertFalse(full['b_daily_vol_lower_than_a'])
        a.update(report.censoring(summary(n=100), 1440, official_result=True))
        prefix = {'paths': {'a': {'daily_statistics': {'annualized_daily_vol': .3}},
                            'b': {'daily_statistics': {'annualized_daily_vol': .4}}}}
        paired = report.matched_volatility(a, b, prefix)
        self.assertEqual(paired['scope'], 'OBSERVED_PREFIX_ANNUALIZED_NOT_FULL_YEAR')
        self.assertEqual(paired['b_daily_vol_annualized'], .4)
        self.assertEqual(paired['a_daily_vol_annualized'], .3)
        self.assertIsNone(report.matched_volatility(a, b, None)['b_daily_vol_lower_than_a'])

    def test_summary_explicitly_states_volatility_did_not_fall(self):
        years = []
        for year in (2023, 2024, 2025):
            comparison = {'paid_cash_PnL_delta_USDT': None, 'same_full_calendar_observed_deltas': {'marked_PnL_USDT': None},
                          'common_observed_minute_prefix': None,
                          'matched_daily_volatility': {'scope': 'OBSERVED_PREFIX_ANNUALIZED_NOT_FULL_YEAR' if year == 2024 else 'SAME_FULL_CALENDAR',
                              'b_minus_a_daily_vol_annualized': .01, 'b_daily_vol_lower_than_a': False}}
            years.append({'year': year, **{name: {'available': False} for name in ('new_control', 'pool_candidate', 'reused_original_S')},
                          'comparisons': {'pool_minus_new_control': comparison}})
        text = report.render_summary({'years': years})
        self.assertIn('Pool volatility did not fall in any of the three matched observed comparisons', text)
        self.assertIn('2024 pool full-year volatility is not directly compared', text)
        self.assertIn('same completed-minute prefix, complete UTC days only', text)
        self.assertEqual(text.count('volatility decreased=false'), 3)
        self.assertIn('Original FOLLOW cash-confidence STOP', text)

    def test_execution_components_are_fixed_existing_cost_not_new_charge(self):
        components = report.execution_components(123.45)
        self.assertEqual(components['half_spread_cost_USDT'], 61.725)
        self.assertEqual(components['slippage_cost_USDT'], 61.725)
        self.assertEqual(sum(components.values()), 123.45)
        self.assertEqual(report.execution_components(None), {'half_spread_cost_USDT': None, 'slippage_cost_USDT': None})
        a = {'available': True, **report.censoring(summary(), 1440, official_result=True), **report.execution_components(100)}
        b = {'available': True, **report.censoring(summary(), 1440, official_result=True), **report.execution_components(120)}
        self.assertEqual(report.contrast(a, b)['same_full_calendar_observed_deltas']['half_spread_cost_USDT'], 10)
        self.assertEqual(report.contrast(a, b)['same_full_calendar_observed_deltas']['slippage_cost_USDT'], 10)

    def test_locator_and_output_exclusive_create(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for locator in ('../secret', '/absolute'):
                with self.assertRaises(ValueError):
                    report.safe_path(root, locator)
            path = root / 'result.json'
            report.save_new(path, {'synthetic': True})
            with self.assertRaises(FileExistsError):
                report.save_new(path, {'synthetic': False})
            (root / 'SUMMARY.md').write_text('keep')
            with patch.object(report, 'HERE', root), patch.object(report, 'render_summary', side_effect=AssertionError('must refuse before render')):
                with self.assertRaises(FileExistsError):
                    report.write_outputs({'years': []})
            self.assertFalse((root / 'RESULTS_COMPACT.json').exists())
            self.assertEqual((root / 'SUMMARY.md').read_text(), 'keep')


if __name__ == '__main__':
    unittest.main(verbosity=2)
