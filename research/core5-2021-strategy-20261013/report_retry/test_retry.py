"""Pure full-shape renderer and fail-closed retry tests; no real REPORT/AUDIT."""
from __future__ import annotations
import ast
import builtins
from copy import deepcopy
from contextlib import nullcontext
import importlib.util
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import build_report as report
import retry_gate
import retry_controller


def read(path):
    return json.loads(path.read_text())


def save(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + '\n')


def full_shape_report():
    fixture = read(HERE / 'FULL_SUMMARY_RENDER_FIXTURE.json')
    rows = {}
    for item in fixture['cases']:
        case, summary, result = item['case'], item['observed_summary'], item['saved_RESULT']
        metrics = {'daily_statistics': {'annualized_daily_vol': result['annual_daily_vol'],
                                       'worst_observed_30_complete_days': result['worst_observed_30_days']},
                   'mean_minute_close_gross_weight_of_prefix': result['mean_actual_gross'],
                   'max_minute_close_gross_weight_of_prefix': result['max_actual_gross'],
                   'mean_actual_signed_net_of_prefix': result['mean_actual_signed_net'],
                   'max_actual_abs_signed_net_of_prefix': result['max_actual_abs_signed_net'],
                   'mean_l1_target_weight_gap_of_prefix': .01}
        row = report.observed_row(case, result['case_id'], deepcopy(summary), deepcopy(result), metrics,
            quantities=item['quantities'], rejections=item['rejections'], journals=item['journals'], bridge=item['bridge'])
        row.update(arm=case['arm'], year=2021, frozen_target_descriptive_statistics={
            'mean_target_gross': .5, 'max_target_gross': .5, 'mean_signed_target_net': .1,
            'max_abs_signed_target_net': .2, 'active_symbol_day_cells': 1000, 'cash_days': 91})
        rows[case['arm']] = row
    no_recovery = dict.fromkeys(report.ARMS)
    with patch.object(report, 'stream_prefix', side_effect=AssertionError('Synthetic render must not stream saved history')):
        comparisons = report.all_pairwise_comparisons(rows, no_recovery, no_recovery, start_us=report.CALENDAR[0])
    return {'kind': 'PURE_SYNTHETIC_RENDER_REGRESSION_NOT_REPORT_OUTPUT',
            'years': [{'arms': rows, 'comparisons': comparisons, 'four_way_common_observed_prefix': None}]}


class RenderRegression(unittest.TestCase):
    def test_financial_stream_and_censor_helpers_exact_AST_and_source(self):
        old_text = (retry_gate.ORIGINAL_HERE / 'build_report.py').read_text()
        new_text = (HERE / 'build_report.py').read_text()
        old = {node.name: node for node in ast.parse(old_text).body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))}
        new = {node.name: node for node in ast.parse(new_text).body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))}
        self.assertEqual(set(old), set(new))
        for name in sorted(set(old) - {'render_summary', 'write_outputs', 'main'}):
            self.assertEqual(ast.dump(old[name], include_attributes=False), ast.dump(new[name], include_attributes=False), name)
            self.assertEqual(ast.get_source_segment(old_text, old[name]), ast.get_source_segment(new_text, new[name]), name)

    def test_import_stdlib_only_reads_no_history(self):
        original = builtins.__import__
        forbidden = ('numpy', 'cold_audit', 'run_cases', 'fine_account', 'quant', 'targets_2021', 'original_functions')
        def guarded(name, *args, **kwargs):
            if any(name == prefix or name.startswith(prefix + '.') for prefix in forbidden):
                self.fail('Forbidden import: ' + name)
            return original(name, *args, **kwargs)
        with patch('builtins.__import__', side_effect=guarded), patch.object(Path, 'read_text', side_effect=AssertionError('Import read history')):
            spec = importlib.util.spec_from_file_location('pure_retry_report_import', HERE / 'build_report.py')
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
        self.assertEqual(module.HERE, retry_gate.ORIGINAL_HERE)
        self.assertEqual(module.OUTPUT_HERE, HERE)

    def test_full_actual_summary_shapes_observed_row_pairwise_render(self):
        fixture = read(HERE / 'FULL_SUMMARY_RENDER_FIXTURE.json')
        self.assertEqual(len(fixture['cases']), 4)
        payload = full_shape_report()
        self.assertEqual(len(payload['years'][0]['comparisons']), 6)
        for item in fixture['cases']:
            identity = item['saved_RESULT']['case_id']
            original = read(retry_gate.ORIGINAL_HERE / 'receipts' / (identity + '.json'))
            self.assertEqual(item['observed_summary'], original['observed_summary'])
            self.assertGreater(len(item['observed_summary']), 60)
            self.assertEqual(set(item['observed_summary']['terminal_signed_marked_notional']), set(item['case']['symbols']))
            self.assertIsInstance(item['observed_summary']['pending_orders_at_stop'], dict)
        text = report.render_summary(payload)
        self.assertEqual(text.count('residual signed marked USDT per symbol'), 4)
        self.assertIn('"BTCUSDT":0.0', text)
        self.assertIn('VOL_MATCHED_minus_STATIC50', text)
        self.assertIn('no full-year', report.render_summary({**payload, 'years': [{**payload['years'][0], 'four_way_common_observed_prefix': {'common_completed_minutes': 1440}}]}))
        original_spec = importlib.util.spec_from_file_location('original_renderer_regression', retry_gate.ORIGINAL_HERE / 'build_report.py')
        original = importlib.util.module_from_spec(original_spec)
        original_spec.loader.exec_module(original)
        with self.assertRaisesRegex(TypeError, 'dict.__format__'):
            original.render_summary(payload)

    def test_empty_nonempty_pending_dicts_negative_tiny_residue_halt_unavailable(self):
        fixture = read(HERE / 'FULL_SUMMARY_RENDER_FIXTURE.json')
        for pending in ({}, {'synthetic_order': {'quantity': '1.00000000', 'side': 'SELL'}}):
            item = deepcopy(fixture['cases'][0])
            summary = item['observed_summary']
            summary.update(pending_orders_at_stop=pending, account_status='LIQUIDATION_REQUIRED_HALT',
                completed_minutes=1440, completion='PARTIAL_HALTED_CONDITIONAL_ACCOUNT', terminal_cash_realized=False,
                halt_witness={'synthetic': True, 'clock_us': report.CALENDAR[0] + report.MINUTE * 1441})
            summary['terminal_signed_marked_notional'].update(BTCUSDT=-1e-12, ETHUSDT=3.25)
            summary['terminal_marked_notional'] = 3.250000000001
            summary['positions']['BTCUSDT']['quantity'] = '-0.000000000001'
            summary['positions']['BTCUSDT']['decimal_strings']['quantity'] = '-0.000000000001'
            item['quantities']['BTCUSDT'] = '-0.000000000001'
            metrics = {'daily_statistics': {'annualized_daily_vol': None, 'worst_observed_30_complete_days': None},
                       'mean_minute_close_gross_weight_of_prefix': .5, 'max_minute_close_gross_weight_of_prefix': .5,
                       'mean_actual_signed_net_of_prefix': .1, 'max_actual_abs_signed_net_of_prefix': .1,
                       'mean_l1_target_weight_gap_of_prefix': .01}
            halted = report.observed_row(item['case'], item['saved_RESULT']['case_id'], summary, None, metrics,
                quantities=item['quantities'], rejections=item['rejections'], journals=item['journals'], bridge=item['bridge'])
            self.assertEqual(halted['pending_orders_at_stop'], pending)
            self.assertIsNone(halted['paid_cash_PnL_USDT'])
            payload = full_shape_report()
            year = payload['years'][0]
            halted.update(frozen_target_descriptive_statistics=year['arms']['STATIC50']['frozen_target_descriptive_statistics'])
            year['arms']['STATIC50'] = halted
            year['arms']['VOL_MATCHED'] = {'case_id': 'Y2021_VOL_MATCHED_FINE_ORIGINAL', 'available': False,
                'reason': 'UNSTARTED_NO_WALLET', 'full_calendar': False, 'paid_flat': False,
                'annual_paid_return': None, 'paid_cash_PnL_USDT': None,
                'frozen_target_descriptive_statistics': deepcopy(halted['frozen_target_descriptive_statistics'])}
            none = dict.fromkeys(report.ARMS)
            with patch.object(report, 'stream_prefix', side_effect=AssertionError('Synthetic render streamed history')):
                year['comparisons'] = report.all_pairwise_comparisons(year['arms'], none, none, start_us=report.CALENDAR[0])
            text = report.render_summary(payload)
            self.assertIn('"BTCUSDT":-1e-12', text)
            self.assertIn('"ETHUSDT":3.25', text)
            self.assertIn('Halt witness', text)
            self.assertIn('UNAVAILABLE: UNSTARTED_NO_WALLET', text)
            self.assertIn('Common prefix unavailable', text)

    def test_new_gate_precedes_all_report_input_reads(self):
        with patch.object(report.retry_gate, 'require_bounded_worker', side_effect=RuntimeError('No retry authorization')), \
             patch.object(report.gate, 'require_bounded_worker', side_effect=AssertionError('Original gate too early')), \
             patch.object(report, 'read_json', side_effect=AssertionError('Read historical inputs')):
            with self.assertRaisesRegex(RuntimeError, 'No retry authorization'):
                report.main()

    def test_original_bounded_gate_remains_required(self):
        with patch.object(report.retry_gate, 'require_bounded_worker', return_value={}), \
             patch.object(report.gate, 'require_bounded_worker', side_effect=RuntimeError('Missing original worker bounds')), \
             patch.object(report, 'read_json', side_effect=AssertionError('Read historical inputs')):
            with self.assertRaisesRegex(RuntimeError, 'Missing original worker bounds'):
                report.main()

    def test_output_exclusively_new_directory_and_never_overwrites(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(report, 'OUTPUT_HERE', Path(tmp)):
            payload = full_shape_report()
            report.write_outputs(payload)
            self.assertEqual(read(Path(tmp) / 'RESULTS_COMPACT.json'), payload)
            with self.assertRaises(FileExistsError):
                report.write_outputs(payload)


class RetryGateSynthetic(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name)
        self.here, self.original = root / 'retry', root / 'original'
        self.here.mkdir(); self.original.mkdir()
        for name in retry_gate.FILES:
            shutil.copyfile(HERE / name, self.here / name)
        pins = {}
        for name in retry_gate.ORIGINAL_FILES:
            target = self.original / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(retry_gate.ORIGINAL_HERE / name, target)
            pins[name] = retry_gate.sha(target)
        manifest = {'kind': 'SINGLE_RENDERER_ONLY_REPORT_RETRY', 'approved_stages': ['REPORT'],
            'maximum_REPORT_attempts': 1, 'case_ids': list(report.CASE_IDS),
            'original_input_locator': 'original', 'exclusive_output_locator': 'retry',
            'historical_runs': 0, 'AUDIT_runs': 0, 'cold_restores': 0, 'financial_advances': 0,
            'files_SHA256': {name: retry_gate.sha(self.here / name) for name in retry_gate.FILES},
            'preserved_original_files_SHA256': pins}
        save(self.here / 'RETRY_MANIFEST.json', manifest)
        (self.here / 'SYNTHETIC_TEST_RESULTS.txt').write_text('pure synthetic fixture\n')
        save(self.here / 'PREPARATION_RECEIPT.json', {'status': 'PASS_PURE_SYNTHETIC_PREPARATION',
            'manifest_SHA256': retry_gate.sha(self.here / 'RETRY_MANIFEST.json'),
            'synthetic_test_results_SHA256': retry_gate.sha(self.here / 'SYNTHETIC_TEST_RESULTS.txt'),
            'tests_run': 1, 'failed_tests': 0, 'report_executions': 0, 'AUDIT_executions': 0, 'financial_advances': 0, 'cold_restores': 0})
        save(self.here / 'RETRY_REVIEW_RECEIPT.json', {'status': 'PASS_INDEPENDENT_RENDERER_ONLY_RETRY_REVIEW',
            'manifest_SHA256': retry_gate.sha(self.here / 'RETRY_MANIFEST.json'),
            'preparation_receipt_SHA256': retry_gate.sha(self.here / 'PREPARATION_RECEIPT.json'),
            'financial_and_stream_function_AST_unchanged': True, 'report_executions': 0, 'AUDIT_executions': 0,
            'financial_advances': 0, 'cold_restores': 0})
        save(self.here / 'RETRY_GO.json', {'parent_GO': True, 'approved_stages': ['REPORT'], 'maximum_REPORT_attempts': 1,
            'manifest_SHA256': retry_gate.sha(self.here / 'RETRY_MANIFEST.json'),
            'preparation_receipt_SHA256': retry_gate.sha(self.here / 'PREPARATION_RECEIPT.json'),
            'review_receipt_SHA256': retry_gate.sha(self.here / 'RETRY_REVIEW_RECEIPT.json'),
            'original_input_locator': 'original', 'exclusive_output_locator': 'retry', 'preserved_original_files_SHA256': pins})
        self.old_go = patch.object(retry_gate.gate, 'verify_observer_go', return_value={'synthetic': True})
        self.old_go.start(); self.addCleanup(self.old_go.stop)

    def verify(self, **kwargs):
        return retry_gate.verify_retry_go(self.here, self.original, **kwargs)

    def test_exact_bindings_pass_and_missing_review_GO_fail(self):
        self.assertEqual(self.verify()['maximum_REPORT_attempts'], 1)
        for name in ('RETRY_REVIEW_RECEIPT.json', 'RETRY_GO.json', 'PREPARATION_RECEIPT.json'):
            path = self.here / name; text = path.read_text(); path.unlink()
            with self.assertRaises(FileNotFoundError):
                self.verify()
            path.write_text(text)

    def test_parent_GO_review_manifest_output_and_scope_drift_fail(self):
        path = self.here / 'RETRY_GO.json'; baseline = read(path)
        for key, value in (('parent_GO', False), ('manifest_SHA256', 'drift'), ('review_receipt_SHA256', 'drift'),
                           ('approved_stages', ['AUDIT', 'REPORT']), ('maximum_REPORT_attempts', 2),
                           ('exclusive_output_locator', 'original'), ('preserved_original_files_SHA256', {})):
            save(path, {**baseline, key: value})
            with self.assertRaises(RuntimeError, msg=key):
                self.verify()
        save(path, baseline)
        path = self.here / 'RETRY_REVIEW_RECEIPT.json'; baseline = read(path)
        for key, value in (('financial_and_stream_function_AST_unchanged', False), ('manifest_SHA256', 'drift'), ('report_executions', 1)):
            save(path, {**baseline, key: value})
            with self.assertRaises(RuntimeError, msg=key):
                self.verify()

    def test_repaired_code_terminal_and_original_failure_byte_drift_fail(self):
        for root, name in ((self.here, 'build_report.py'), (self.original, 'TERMINAL_INPUTS.json'),
                           (self.original, 'REPORT_RESOURCE_RECEIPTS.json'), (self.original, 'REPORT.log'),
                           (self.original, 'receipts/Y2021_STATIC50_FINE_ORIGINAL.json')):
            path = root / name; original = path.read_bytes(); path.write_bytes(original + b' ')
            with self.assertRaisesRegex(RuntimeError, 'pinned bytes'):
                self.verify()
            path.write_bytes(original)

    def test_all_repeat_start_or_output_states_stop(self):
        for name in ('SINGLE_RETRY_STARTED.json', 'REPORT_RESOURCE_RECEIPTS.json', 'REPORT.log', 'RESULTS_COMPACT.json', 'SUMMARY.md'):
            path = self.here / name; path.write_text('{}')
            with self.assertRaises(FileExistsError):
                self.verify()
            path.unlink()

    def test_worker_requires_exact_exclusive_start_and_both_tokens(self):
        with self.assertRaises(FileNotFoundError):
            self.verify(worker=True)
        marker = {'retry_GO_SHA256': retry_gate.sha(self.here / 'RETRY_GO.json'),
            'manifest_SHA256': retry_gate.sha(self.here / 'RETRY_MANIFEST.json'),
            'review_receipt_SHA256': retry_gate.sha(self.here / 'RETRY_REVIEW_RECEIPT.json'), 'maximum_REPORT_attempts': 1}
        save(self.here / 'SINGLE_RETRY_STARTED.json', marker)
        self.assertEqual(self.verify(worker=True)['retry_GO_SHA256'], marker['retry_GO_SHA256'])
        save(self.here / 'SINGLE_RETRY_STARTED.json', {**marker, 'retry_GO_SHA256': 'drift'})
        with self.assertRaisesRegex(RuntimeError, 'start marker'):
            self.verify(worker=True)
        with patch.dict('os.environ', {}, clear=True):
            with self.assertRaisesRegex(RuntimeError, 'one-shot bounded controller'):
                retry_gate.require_bounded_worker()

    def test_controller_exactly_one_mock_worker_exclusive_log_receipts_and_repeat_stop(self):
        original_verify = retry_gate.verify_retry_go
        original_unstarted = retry_gate.ensure_unstarted
        class Shared:
            @staticmethod
            def controller_lock():
                return nullcontext()
        def verify(*args, **kwargs):
            return original_verify(self.here, self.original, **kwargs)
        def mock_worker(command, guard, shared):
            self.assertEqual(command, [sys.executable, str(self.here / 'build_report.py')])
            self.assertTrue((self.here / 'SINGLE_RETRY_STARTED.json').exists())
            self.assertTrue((self.here / 'REPORT.log').exists())
            self.assertEqual(__import__('os').environ['COIN_FULL2021_RENDERER_RETRY_GO_SHA256'], retry_gate.sha(self.here / 'RETRY_GO.json'))
            print('PURE_MOCK_WORKER_NO_REAL_REPORT')
            save(self.here / 'RESULTS_COMPACT.json', {'synthetic_mock': True})
            (self.here / 'SUMMARY.md').write_text('PURE_SYNTHETIC_MOCK_OUTPUT\n')
            return {'exit_code': 0, 'stop_reason': None}
        with patch.object(retry_controller, 'HERE', self.here), patch.object(retry_controller, 'ORIGINAL_HERE', self.original), \
             patch.object(retry_gate, 'verify_retry_go', side_effect=verify), \
             patch.object(retry_gate, 'ensure_unstarted', side_effect=lambda *args, **kwargs: original_unstarted(self.here)), \
             patch.object(retry_controller.bounded, 'load_resource_helpers', return_value=(object(), Shared())), \
             patch.object(retry_controller.bounded, 'resource_admission', return_value={'synthetic': True}), \
             patch.object(retry_controller.bounded, 'run_bounded', side_effect=mock_worker) as mock, \
             patch.dict('os.environ', {'COIN_FULL2021_RENDERER_RETRY_BOUNDED': 'prior'}, clear=False):
            retry_controller.main()
            self.assertEqual(mock.call_count, 1)
            self.assertEqual(__import__('os').environ['COIN_FULL2021_RENDERER_RETRY_BOUNDED'], 'prior')
            self.assertEqual(read(self.here / 'REPORT_RESOURCE_RECEIPTS.json')['status'], 'ALL_OBSERVERS_FINISHED')
            before = {name: (self.here / name).read_bytes() for name in ('SINGLE_RETRY_STARTED.json', 'REPORT.log', 'REPORT_RESOURCE_RECEIPTS.json', 'RESULTS_COMPACT.json', 'SUMMARY.md')}
            with self.assertRaises(FileExistsError):
                retry_controller.main()
            self.assertEqual(mock.call_count, 1)
            self.assertEqual(before, {name: (self.here / name).read_bytes() for name in before})

    def test_controller_mock_nonzero_exit_keeps_terminal_STOP_PARTIAL(self):
        original_verify = retry_gate.verify_retry_go
        original_unstarted = retry_gate.ensure_unstarted
        class Shared:
            @staticmethod
            def controller_lock():
                return nullcontext()
        with patch.object(retry_controller, 'HERE', self.here), patch.object(retry_controller, 'ORIGINAL_HERE', self.original), \
             patch.object(retry_gate, 'verify_retry_go', side_effect=lambda *args, **kwargs: original_verify(self.here, self.original, **kwargs)), \
             patch.object(retry_gate, 'ensure_unstarted', side_effect=lambda *args, **kwargs: original_unstarted(self.here)), \
             patch.object(retry_controller.bounded, 'load_resource_helpers', return_value=(object(), Shared())), \
             patch.object(retry_controller.bounded, 'resource_admission', return_value={'synthetic': True}), \
             patch.object(retry_controller.bounded, 'run_bounded', return_value={'exit_code': 1, 'stop_reason': None}) as mock:
            with self.assertRaisesRegex(RuntimeError, 'Bounded renderer retry failed'):
                retry_controller.main()
            receipt = read(self.here / 'REPORT_RESOURCE_RECEIPTS.json')
            self.assertEqual(receipt['status'], 'STOP_PARTIAL')
            self.assertEqual(receipt['per_observer']['FULL_FOUR_CASE_REPORT']['exit_code'], 1)
            self.assertEqual(mock.call_count, 1)
            with self.assertRaises(FileExistsError):
                retry_controller.main()
            self.assertEqual(mock.call_count, 1)
            self.assertEqual(receipt, read(self.here / 'REPORT_RESOURCE_RECEIPTS.json'))

    def test_original_GO_remains_required_and_no_worker_when_missing_new_GO(self):
        with patch.object(retry_gate.gate, 'verify_observer_go', side_effect=RuntimeError('Original GO revoked')):
            with self.assertRaisesRegex(RuntimeError, 'Original GO revoked'):
                self.verify()
        with patch.object(retry_controller.retry_gate, 'verify_retry_go', side_effect=RuntimeError('Missing new GO')), \
             patch.object(retry_controller.bounded, 'load_resource_helpers', side_effect=AssertionError('Started resources before GO')), \
             patch.object(retry_controller.bounded, 'run_bounded', side_effect=AssertionError('Executed forbidden real REPORT')):
            with self.assertRaisesRegex(RuntimeError, 'Missing new GO'):
                retry_controller.main()


if __name__ == '__main__':
    unittest.main(verbosity=2)
