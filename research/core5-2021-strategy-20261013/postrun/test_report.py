"""Pure synthetic report tests: no historical runner, restore or report run."""
from __future__ import annotations

import builtins
from copy import deepcopy
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
              'state_locator': 'synthetic/state', 'terminal_inputs_SHA256': 'terminal', 'run_binding_SHA256': 'run',
              'controller_receipt_SHA256': 'controller', 'historical_controller_released': True}
        text = json.dumps(go, indent=2) + '\n'
        return {'stage': 'AUDIT', 'status': 'ALL_OBSERVERS_FINISHED', 'case_ids': list(report.CASE_IDS),
                'per_observer': {key: {} for key in report.CASE_IDS}, 'unstarted_observer_ids': [],
                'financial_advances': 0, 'historical_wallets_opened': 0, 'observer_manifest_SHA256': 'manifest',
                'postrun_GO_text': text, 'postrun_GO_SHA256': hashlib.sha256(text.encode()).hexdigest()}

    def test_import_is_stdlib_only_and_reads_no_history(self):
        original = builtins.__import__
        forbidden = ('numpy', 'run_cases', 'fine_account', 'quant', 'scripts', 'original_follow_adapter', 'cold_audit', 'targets_2021', 'original_functions', 'window_2021', 'preflight_2021', 'terminal_quotes', 'prepare_targets')
        def guarded(name, *args, **kwargs):
            if any(name == prefix or name.startswith(prefix + '.') for prefix in forbidden):
                self.fail('Report import loaded forbidden module: ' + name)
            return original(name, *args, **kwargs)
        with patch('builtins.__import__', side_effect=guarded), patch.object(Path, 'read_text', side_effect=AssertionError('import opened history')):
            spec = importlib.util.spec_from_file_location('synthetic_report_import', HERE / 'build_report.py')
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
        self.assertEqual(tuple(module.CASE_IDS), tuple('Y2021_' + arm + '_FINE_ORIGINAL' for arm in report.ARMS))
        self.assertEqual(len(module.CASE_IDS), 4)

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
        kwargs = dict(manifest_sha='manifest', terminal_inputs_sha='terminal', run_binding_sha='run', controller_sha='controller', state_locator='synthetic/state')
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
        with self.assertRaisesRegex(ValueError, 'authorize'):
            report.verify_audit_stage(audit, **{**kwargs, 'terminal_inputs_sha': 'drift'})

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

    def test_two_different_pairwise_prefixes_and_four_way_prefix(self):
        import numpy as np
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            arrays = {name: minute_array(n) for name, n in (('static', 5), ('sma', 8), ('half', 3), ('vol', 6))}
            arrays['static'][:, 0] = [10100, 10200, 10300, 10400, 10500]
            arrays['sma'][:, 0] = [10050, 10100, 10200, 10300, 10400, 10500, 10600, 10700]
            arrays['half'][:, 0] = [10100, 10200, 10400]
            arrays['static'][:, 29] = .1
            arrays['sma'][:, 29] = .3
            paths = {name: saved_recovery(root / name, [array]) for name, array in arrays.items()}
            rows = {name: {'completed_minutes': len(array)} for name, array in arrays.items()}
            weights = {name: np.zeros((1, 5), dtype=np.float64) for name in arrays}
            first = report.common_prefix({k: rows[k] for k in ('static', 'sma')}, paths, weights, start_us=0)
            second = report.common_prefix({k: rows[k] for k in ('half', 'sma')}, paths, weights, start_us=0)
            third = report.common_prefix(rows, paths, weights, start_us=0)
            self.assertEqual((first['common_completed_minutes'], second['common_completed_minutes'], third['common_completed_minutes']), (5, 3, 3))
            self.assertEqual(report.prefix_deltas(first, 'static', 'sma')['b_minus_a']['last_completed_minute_marked_PnL_USDT'], -100)
            self.assertEqual(report.prefix_deltas(second, 'half', 'sma')['b_minus_a']['last_completed_minute_marked_PnL_USDT'], -200)
            self.assertEqual(first['paths']['static']['minute_prefix_raw_SHA256'], hashlib.sha256(arrays['static'].tobytes()).hexdigest())
            self.assertAlmostEqual(report.prefix_deltas(first, 'static', 'sma')['b_minus_a']['mean_l1_target_weight_gap_of_prefix'], .2)
            self.assertIsNone(first['paid_cash_PnL_delta_USDT'])
            self.assertEqual(first['paths']['sma']['financial_advances'], 0)

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

    def test_initial_zero_row_halted_day_retains_sha_geometry_and_no_endpoint(self):
        import numpy as np
        with tempfile.TemporaryDirectory() as temporary:
            array = minute_array(0)
            recovery = saved_recovery(Path(temporary) / 'r', [array])
            result = report.stream_prefix(recovery, 0, np.zeros((1, 5), dtype=np.float64),
                                          numeric=numeric_for(array), start_us=0)
            self.assertEqual(result['common_completed_minutes'], 0)
            self.assertEqual(result['chunks_sha_and_geometry_verified'], 1)
            self.assertTrue(result['all_saved_numeric_bits_verified'])
            self.assertIsNone(result['last_completed_minute_NAV_USDT'])
            self.assertIsNone(result['last_completed_minute_marked_PnL_USDT'])
            self.assertIsNone(result['max_drawdown_of_completed_minute_prefix'])
            self.assertEqual(result['daily_statistics']['completed_UTC_days'], 0)
            self.assertIsNone(result['daily_statistics']['annualized_daily_vol'])
            with (recovery / 'DAY_0000.npz').open('ab') as file:
                file.write(b'tamper')
            with self.assertRaisesRegex(ValueError, 'SHA'):
                report.stream_prefix(recovery, 0)

    def test_final_zero_row_halted_day_after_complete_day_is_retained(self):
        import numpy as np
        with tempfile.TemporaryDirectory() as temporary:
            first, empty = minute_array(1440), minute_array(0)
            first[-1, 0] = 10100.
            recovery = saved_recovery(Path(temporary) / 'r', [first, empty])
            result = report.stream_prefix(recovery, 1440, np.zeros((2, 5), dtype=np.float64),
                                          numeric=numeric_for(first), start_us=0)
            self.assertEqual(result['chunks_sha_and_geometry_verified'], 2)
            self.assertTrue(result['all_saved_numeric_bits_verified'])
            self.assertEqual(result['last_completed_minute_NAV_USDT'], 10100.)
            self.assertEqual(result['last_completed_minute_marked_PnL_USDT'], 100.)
            self.assertEqual(result['daily_statistics'], report.daily_stats([10100.]))
            self.assertEqual(result['minute_prefix_raw_SHA256'], hashlib.sha256(first.tobytes()).hexdigest())
            with (recovery / 'DAY_0001.npz').open('ab') as file:
                file.write(b'tamper')
            with self.assertRaisesRegex(ValueError, 'SHA'):
                report.stream_prefix(recovery, 1)

    def test_nonfinal_zero_row_chunks_and_empty_wrong_geometry_are_rejected(self):
        import numpy as np
        for arrays in ([minute_array(0), minute_array(1440)], [minute_array(1440), minute_array(0), minute_array(0)]):
            with tempfile.TemporaryDirectory() as temporary:
                recovery = saved_recovery(Path(temporary) / 'r', arrays)
                with self.assertRaisesRegex(ValueError, 'Non-final checkpoint day is incomplete'):
                    report.stream_prefix(recovery, 0)
        for array in (np.zeros((0, 35), dtype=np.float64), np.zeros((0, 36), dtype=np.float32)):
            with tempfile.TemporaryDirectory() as temporary:
                recovery = saved_recovery(Path(temporary) / 'r', [array])
                with self.assertRaisesRegex(ValueError, 'float64 geometry'):
                    report.stream_prefix(recovery, 0)

    def test_frozen_target_activity_gross_description(self):
        import numpy as np
        weights = np.zeros((3, 5), dtype=np.float64)
        weights[1, :2] = [.2, -.1]
        weights[2, 0] = .4
        result = report.target_description(weights)
        self.assertEqual(result['cash_days'], 1)
        self.assertEqual(result['active_symbol_day_cells'], 3)
        self.assertEqual(result['days_by_nonzero_target_symbol_count'], {'0': 1, '1': 1, '2': 1, '3': 0, '4': 0, '5': 0})
        self.assertAlmostEqual(result['mean_target_gross'], .7 / 3)
        self.assertEqual(result['max_target_gross'], .4)
        self.assertAlmostEqual(result['mean_signed_target_net'], .5 / 3)
        self.assertTrue(result['target_gross_is_not_actual_gross_or_realized_risk'])

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

    def synthetic_rows(self):
        import numpy as np
        rows = {}
        for index, arm in enumerate(report.ARMS):
            row = {'case_id': 'Y2021_' + arm + '_FINE_ORIGINAL', 'available': True,
                   **report.censoring(summary(), 1440, official_result=True),
                   'marked_PnL_USDT': 100 + index, 'completion': 'COMPLETE_CONDITIONAL_ACCOUNT', 'account_status': 'ACTIVE',
                   'stop_us': None, 'minute_drawdown': .1 + index / 100, 'halt_count': 0, 'halt_witness': None,
                   'annual_daily_vol': .1 + index / 100, 'observed_prefix_daily_vol_annualized': .1 + index / 100,
                   'worst_observed_30_complete_days': None, 'mean_actual_gross': .2, 'max_actual_gross': .3,
                   'mean_actual_signed_net': .1, 'max_actual_abs_signed_net': .2, 'mean_l1_target_weight_gap': .01,
                   'terminal_residual_quantity': {'X': '0'}, 'terminal_residual_gross_notional_USDT': 0.,
                   'terminal_residual_signed_marked_notional_USDT': 0., 'rejection_counts': {'NO_FUNDS': index},
                   'observed_journal_counts': {}, 'trade_legs': index + 1, 'gross_fill_turnover_USDT': 20.,
                   'fees_USDT': 1., 'execution_cost_USDT': 2., 'funding_USDT': -3., **report.execution_components(2.),
                   'frozen_target_descriptive_statistics': report.target_description(np.ones((365, 5), dtype=np.float64) * (.01 + index / 100))}
            row['paid_cash_PnL_USDT'] = row['marked_PnL_USDT']
            row['annual_paid_return'] = row['paid_cash_PnL_USDT'] / 10000
            rows[arm] = row
        return rows

    def test_all_six_full_pairwise_directions_and_inventory_deltas(self):
        rows = self.synthetic_rows()
        paths = dict.fromkeys(report.ARMS)
        answer = report.all_pairwise_comparisons(rows, paths, paths, start_us=0)
        expected = ['SMA200_10PCT_minus_STATIC50', 'EXACTHALF_minus_STATIC50', 'VOL_MATCHED_minus_STATIC50',
                    'EXACTHALF_minus_SMA200_10PCT', 'VOL_MATCHED_minus_SMA200_10PCT', 'VOL_MATCHED_minus_EXACTHALF']
        self.assertEqual(list(answer), expected)
        for value in answer.values():
            a, b = value['a_arm'], value['b_arm']
            self.assertEqual(value['direction'], 'b_minus_a')
            self.assertEqual(value['paid_cash_PnL_delta_USDT'], rows[b]['marked_PnL_USDT'] - rows[a]['marked_PnL_USDT'])
            self.assertEqual(value['same_full_calendar_rejection_count_b_minus_a']['NO_FUNDS'], report.ARMS.index(b) - report.ARMS.index(a))
            self.assertEqual(value['same_full_calendar_exact_terminal_quantity_b_minus_a'], {'X': '0'})
            self.assertIsNone(value['common_observed_minute_prefix'])
        rows.pop('VOL_MATCHED')
        with self.assertRaisesRegex(ValueError, 'retain all four'):
            report.all_pairwise_comparisons(rows, paths, paths, start_us=0)

    def test_full_calendar_pending_order_dictionaries_stay_per_case_evidence(self):
        required = 525600
        case = {'calendar': list(report.CALENDAR), 'symbols': ['X']}
        pending = {'X': {'target': '0.05', 'signal_us': report.CALENDAR[1] - report.MINUTE,
                         'kind': 'TERMINAL', 'attempts': 5, 'order_id': 'SYNTHETIC_TERMINAL'}}
        metrics = {'daily_statistics': {'annualized_daily_vol': .1, 'worst_observed_30_complete_days': -.01},
                   'mean_minute_close_gross_weight_of_prefix': .2, 'max_minute_close_gross_weight_of_prefix': .3,
                   'mean_actual_signed_net_of_prefix': .1, 'max_actual_abs_signed_net_of_prefix': .2,
                   'mean_l1_target_weight_gap_of_prefix': .01}
        for left_pending, right_pending in (({}, {}), ({}, pending), (pending, {}), (pending, pending)):
            with self.subTest(left=left_pending, right=right_pending):
                rows = []
                summaries = []
                for index, orders in enumerate((left_pending, right_pending)):
                    identity = 'SYNTHETIC_FULL_' + str(index)
                    observed = {**summary(n=required), 'net_PnL': 100. + index,
                                'all_observation_max_drawdown': .1, 'trade_legs': 2,
                                'pending_orders_at_stop': deepcopy(orders),
                                'terminal_marked_notional': 0., 'terminal_signed_marked_notional': {'X': 0.}}
                    result = {'case_id': identity, 'completed_minutes': required, 'required_minutes': required,
                              'full_calendar': True, 'paid_flat': True, 'paid_cash_PnL_USDT': observed['net_PnL'],
                              'marked_PnL_USDT': observed['net_PnL'], 'completion': observed['completion'],
                              'account_status': observed['account_status'], 'minute_drawdown': .1, 'trade_legs': 2}
                    rows.append(report.observed_row(case, identity, observed, result, metrics,
                        quantities={'X': '0'}, rejections={}, journals={'trades': 2, 'funding': 3}, bridge={}))
                    summaries.append(observed)
                before = deepcopy(summaries)
                comparison = report.contrast(*rows)
                self.assertTrue(comparison['same_full_calendar'])
                self.assertEqual(comparison['paid_cash_PnL_delta_USDT'], 1.)
                self.assertNotIn('pending_orders_at_stop', comparison['same_full_calendar_observed_deltas'])
                for row, orders in zip(rows, (left_pending, right_pending)):
                    self.assertEqual(row['pending_orders_at_stop'], orders)
                    self.assertEqual(row['observed_journal_counts'], {'trades': 2, 'funding': 3})
                self.assertEqual(summaries, before)

    def test_all_pairs_retain_unavailable_and_economic_halt(self):
        import numpy as np
        rows = self.synthetic_rows()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            weights = {arm: np.zeros((1, 5), dtype=np.float64) for arm in report.ARMS}
            paths = {}
            for index, arm in enumerate(report.ARMS):
                count = [5, 8, 3, 6][index]
                row = rows[arm]
                row.update(report.censoring(summary(n=count, quantity='1', paid=False, status='BANKRUPT_HALT' if arm == 'STATIC50' else 'ACTIVE'), 1440, official_result=True))
                row['marked_PnL_USDT'] = -9000 if arm == 'STATIC50' else 9999
                paths[arm] = saved_recovery(root / arm, [minute_array(count)])
            rows['VOL_MATCHED'] = {'case_id': rows['VOL_MATCHED']['case_id'], 'available': False,
                                   'reason': 'UNSTARTED_NO_WALLET', 'frozen_target_descriptive_statistics': rows['VOL_MATCHED']['frozen_target_descriptive_statistics']}
            paths['VOL_MATCHED'] = None
            answer = report.all_pairwise_comparisons(rows, paths, weights, start_us=0)
            self.assertEqual(len(answer), 6)
            for value in answer.values():
                self.assertIsNone(value['paid_cash_PnL_delta_USDT'])
                self.assertTrue(all(v is None for v in value['same_full_calendar_observed_deltas'].values()))
                if value['b_arm'] == 'VOL_MATCHED':
                    self.assertIsNone(value['common_observed_minute_prefix'])
                    self.assertEqual(value['matched_daily_volatility']['scope'], 'UNAVAILABLE_NO_MATCHED_HORIZON')
                else:
                    prefix = value['common_observed_minute_prefix']
                    self.assertEqual(prefix['common_completed_minutes'], min(rows[value['a_arm']]['completed_minutes'], rows[value['b_arm']]['completed_minutes']))
                    self.assertEqual(prefix['b_minus_a']['last_completed_minute_marked_PnL_USDT'], 0)
                    self.assertTrue(prefix['no_full_year_or_paid_profit_claim'])
            self.assertEqual(rows['STATIC50']['observation_class'], 'PARTIAL_HALTED')

    def test_summary_retains_four_rows_six_contrasts_and_qualifications(self):
        rows = self.synthetic_rows()
        rows['VOL_MATCHED'] = {**rows['VOL_MATCHED'], 'available': False, 'reason': 'UNSTARTED_NO_WALLET'}
        empty = dict.fromkeys(report.ARMS)
        comparisons = report.all_pairwise_comparisons(rows, empty, empty, start_us=0)
        text = report.render_summary({'years': [{'year': 2021, 'arms': rows, 'comparisons': comparisons, 'four_way_common_observed_prefix': None}]})
        for arm in report.ARMS:
            self.assertIn('| ' + arm + ' |', text)
        for name in comparisons:
            self.assertIn(name + ':', text)
        for phrase in ('No reused comparator', 'raw-fraction', 'Seen development replication', 'All prior strategy STOP', '25 days with 3', '66 days with 4', '274 days with 5', 'no final forced-cash', 'No free terminal flattening', 'No cross-horizon endpoint'):
            self.assertIn(phrase.lower(), text.lower())

    def synthetic_case(self, arm, *, days=365):
        return {'case_id': 'Y2021_' + arm, 'arm': arm, 'year': 2021, 'calendar': list(report.CALENDAR),
                'symbols': ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'XRPUSDT', 'DOGEUSDT'], 'protective_enabled': False,
                'source_index_SHA256': report.SOURCE_INDEX_SHA256, 'source_index_local_locator': 'synthetic/source.json',
                'target_archive_SHA256': report.TARGET_ARCHIVE_SHA256, 'target_archive_local_locator': 'synthetic/targets.npz',
                'target_dtype': '<f8', 'target_shape': [days, 5], 'target_array_SHA256': 'synthetic'}

    def test_four_arm_dispatch_rejects_wrong_population_and_identity(self):
        plan = {'case_count': 4, 'cases': [self.synthetic_case(arm) for arm in report.ARMS]}
        self.assertEqual(report.validate_four_arm_plan(plan), plan['cases'])
        for field, value in (('arm', 'FOLLOW_POOL_SAMEGROSS'), ('year', 2023), ('calendar', [0, 365 * report.DAY]),
                             ('target_archive_SHA256', 'wrong'), ('source_index_SHA256', 'wrong'), ('target_shape', [274, 5]), ('protective_enabled', True)):
            wrong = deepcopy(plan)
            wrong['cases'][0][field] = value
            with self.assertRaises(ValueError):
                report.validate_four_arm_plan(wrong)
        wrong = deepcopy(plan)
        wrong['cases'].reverse()
        with self.assertRaises(ValueError):
            report.validate_four_arm_plan(wrong)

    def test_weights_use_each_case_arm_and_archive_without_comparator_fields(self):
        import numpy as np
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            clocks = np.arange(*report.CALENDAR, report.DAY)
            arrays = {arm: np.ones((365, 5), dtype=np.float64) * (index / 100) for index, arm in enumerate(report.ARMS)}
            path = root / 'targets.npz'
            np.savez_compressed(path, decision_us=clocks, symbol_order=np.asarray(self.synthetic_case(report.ARMS[0])['symbols']), **arrays)
            with patch.object(report, 'ROOT', root):
                for arm in report.ARMS:
                    case = self.synthetic_case(arm)
                    case.update(target_archive_local_locator=path.name, target_archive_SHA256=report.sha(path),
                                target_array_SHA256=hashlib.sha256(arrays[arm].tobytes()).hexdigest())
                    np.testing.assert_array_equal(report.load_weights(case), arrays[arm])
                    case['target_array_SHA256'] = '0' * 64
                    with self.assertRaisesRegex(ValueError, 'numerical identity'):
                        report.load_weights(case)

    def test_original_dynamic_masks_early_half_and_full365_are_verified(self):
        import numpy as np
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            mask = np.ones((365, 5), dtype=np.bool_)
            mask[:91, 2], mask[:25, 4] = False, False
            static = np.zeros((365, 5), dtype=np.float64)
            static[91:] = .04
            sma = mask.astype(np.float64) * .02
            weights = {'STATIC50': static, 'SMA200_10PCT': sma, 'EXACTHALF': .5 * static + .5 * sma, 'VOL_MATCHED': static * .4}
            path = root / 'targets.npz'
            np.savez_compressed(path, SMA_mask=mask, HOLD_mask=mask)
            case = self.synthetic_case('STATIC50')
            case.update(target_archive_local_locator=path.name, target_archive_SHA256=report.sha(path))
            with patch.object(report, 'ROOT', root):
                context = report.original_dynamic_context(case, weights)
                self.assertEqual(context['decisions'], 365)
                self.assertEqual(context['STATIC50_initial_cash_decisions'], 91)
                self.assertEqual(context['SMA200_10PCT_mask_counts_by_symbol']['SOLUSDT'], 274)
                self.assertEqual(context['SMA200_10PCT_mask_counts_by_symbol']['DOGEUSDT'], 340)
                self.assertTrue(context['EXACTHALF_first_91_decisions_bit_exact_half_SMA200_10PCT'])
                self.assertTrue(context['no_final_forced_cash_target'])
                for arm in ('STATIC50', 'SMA200_10PCT', 'EXACTHALF', 'VOL_MATCHED'):
                    changed = {name: array.copy() for name, array in weights.items()}
                    changed[arm][0, 2] = .01
                    with self.assertRaisesRegex(ValueError, 'dynamic masks'):
                        report.original_dynamic_context(case, changed)

    def test_exact_terminal_delta_has_no_context_rounding(self):
        self.assertEqual(report.exact_quantity_delta('123456789012345678901234567890.0000000000000000000000000001', '123456789012345678901234567891.0000000000000000000000000002'), '1.0000000000000000000000000001')
        self.assertEqual(report.exact_quantity_delta('1E-100', '2E-100'), '1E-100')

    def test_worst_30_days_and_prefix_cost_deltas_use_complete_days(self):
        import numpy as np
        left = report.daily_stats([10100.] * 29 + [9000., 8000.])
        nav = np.r_[report.CAPITAL, [10100.] * 29 + [9000., 8000.]]
        self.assertEqual(left['worst_observed_30_complete_days'], float(np.min(nav[30:] / nav[:-30] - 1)))
        self.assertIsNone(report.daily_stats([9000.] * 29)['worst_observed_30_complete_days'])
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            a, b = minute_array(3), minute_array(5)
            a[:, 5:9] = [1., 2., -3., 20.]
            b[:, 5:9] = [4., 6., -8., 90.]
            rows = {'a': {'completed_minutes': 3}, 'b': {'completed_minutes': 5}}
            recoveries = {'a': saved_recovery(root / 'a', [a]), 'b': saved_recovery(root / 'b', [b])}
            prefix = report.common_prefix(rows, recoveries, dict.fromkeys(rows), start_us=0)
            delta = report.prefix_deltas(prefix, 'a', 'b')
            self.assertEqual(delta['saved_cumulative_b_minus_a'], {'fees_USDT': 3., 'execution_cost_USDT': 4., 'funding_USDT': -5., 'gross_fill_turnover_USDT': 70., 'half_spread_cost_USDT': 2., 'slippage_cost_USDT': 2.})
            self.assertIsNone(delta['worst_observed_30_complete_days_delta_same_completed_UTC_days'])

    def test_observed_row_exact_residue_and_halt_endpoint_stay_distinct(self):
        import numpy as np
        case = {'calendar': [0, 1440 * report.MINUTE], 'symbols': ['X']}
        with tempfile.TemporaryDirectory() as temporary:
            array = minute_array(10)
            array[:, 0] = 9500.
            recovery = saved_recovery(Path(temporary) / 'r', [array])
            metrics = report.stream_prefix(recovery, 10, np.zeros((1, 5), dtype=np.float64))
            observed = {**summary(n=10, paid=False, quantity='0.000000000000000000000000000000000001', status='LIQUIDATION_REQUIRED_HALT'),
                        'net_PnL': -9900., 'all_observation_max_drawdown': .99, 'terminal_marked_notional': 1E-34,
                        'terminal_signed_marked_notional': 1E-34, 'halt_witness': {'test': True}, 'stop_us': 11 * report.MINUTE}
            row = report.observed_row(case, 'SYNTHETIC', observed, None, metrics,
                                      quantities={'X': observed['positions']['X']['quantity']}, rejections={}, journals={}, bridge={})
            self.assertEqual(row['observation_class'], 'PARTIAL_HALTED')
            self.assertEqual(row['marked_PnL_USDT'], -9900.)
            self.assertEqual(row['minute_drawdown'], .99)
            self.assertEqual(row['completed_minute_prefix_metrics']['last_completed_minute_marked_PnL_USDT'], -500.)
            self.assertAlmostEqual(row['completed_minute_prefix_metrics']['max_drawdown_of_completed_minute_prefix'], .05)
            self.assertFalse(row['exact_terminal_flat'])
            self.assertIsNone(row['annual_daily_vol'])
            self.assertIsNone(row['paid_cash_PnL_USDT'])
            with self.assertRaisesRegex(ValueError, 'Exact terminal inventory differs'):
                report.observed_row(case, 'SYNTHETIC', observed, None, metrics, quantities={'X': '0'}, rejections={}, journals={}, bridge={})

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
