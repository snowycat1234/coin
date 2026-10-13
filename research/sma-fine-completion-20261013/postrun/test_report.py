"""Pure synthetic streaming, daily bits, censoring and simple renderer tests."""
from copy import deepcopy
import csv
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import numpy as np
import build_report as report
import report_helpers as h


def array(n):
    x = np.zeros((n, 36), dtype=np.float64)
    x[:, 0] = 10000.
    x[:, 34] = .5
    return x


def recovery(root, arrays):
    root.mkdir()
    chunks = []
    for i, values in enumerate(arrays):
        path = root / f'day{i}.npz'
        np.savez_compressed(path, minute_chunk=values)
        chunks.append(dict(path=path.name, rows=len(values), columns=36, SHA256=h.sha(path)))
    (root / 'POINTER.json').write_text(json.dumps(dict(completed_minutes=sum(map(len, arrays)), chunks=chunks)))
    return root


def numeric(values, start=0):
    names = ('nav', 'free_cash', 'isolated_balance', 'gross_notional', 'net_signed_notional',
        'cumulative_fees', 'cumulative_execution_costs', 'cumulative_funding', 'cumulative_turnover')
    rows = [dict(name=names[i] if i < 9 else f'column{i}', dtype='<f8', rows=len(values),
        raw_SHA256=hashlib.sha256(values[:, i].tobytes()).hexdigest()) for i in range(36)]
    clocks = start + np.arange(1, len(values) + 1, dtype=np.int64) * h.MINUTE
    rows.append(dict(name='close_us', dtype='<i8', rows=len(values), raw_SHA256=hashlib.sha256(clocks.tobytes()).hexdigest()))
    return dict(columns=rows)


def summary(n=1440, quantity='0', paid=True, status='ACTIVE'):
    return dict(completed_minutes=n, net_PnL=100., completion='COMPLETE_CONDITIONAL_ACCOUNT',
        account_status=status, terminal_cash_realized=paid, positions={'X': {'quantity': quantity}})


class ReportTests(unittest.TestCase):
    def test_paid_requires_full_official_exact_zero(self):
        self.assertTrue(h.censoring(summary(), 1440, official_result=True)['paid_flat'])
        for s, present in ((summary(quantity='1e-100'), True), (summary(paid=False), True),
                          (summary(n=100), True), (summary(), False)):
            row = h.censoring(s, 1440, official_result=present)
            self.assertFalse(row['paid_flat']); self.assertIsNone(row['annual_paid_return'])
        self.assertEqual(h.censoring(summary(quantity='1', paid=False), 1440, official_result=True)['observation_class'], 'FULL_MARKED')
        self.assertEqual(h.censoring(summary(n=100, paid=False, status='LIQUIDATION_REQUIRED_HALT'), 1440, official_result=True)['observation_class'], 'PARTIAL_HALTED')

    def test_cross_horizon_paid_and_endpoint_deltas_refused(self):
        a = dict(available=True, **h.censoring(summary(), 1440, official_result=True), marked_PnL_USDT=100.)
        b = dict(available=True, **h.censoring({**summary(), 'net_PnL': 180.}, 1440, official_result=True), marked_PnL_USDT=180.)
        self.assertEqual(h.contrast(a, b)['paid_cash_PnL_delta_USDT'], 80.)
        b.update(h.censoring(summary(n=100), 1440, official_result=True))
        row = h.contrast(a, b)
        self.assertIsNone(row['paid_cash_PnL_delta_USDT'])
        self.assertTrue(all(v is None for v in row['same_full_calendar_observed_deltas'].values()))

    def test_stream_numeric_all_bits_and_daily_stats(self):
        a, b, partial = array(1440), array(1440), array(3)
        a[-1, 0], b[-1, 0], partial[-1, 0] = 10100., 10300., 9900.
        all_values = np.concatenate((a, b, partial))
        with tempfile.TemporaryDirectory(dir=h.HERE) as directory:
            root = recovery(Path(directory) / 'recovery', (a, b, partial))
            row = h.stream_prefix(root, len(all_values), np.zeros((3, 5)), numeric=numeric(all_values), start_us=0)
            self.assertEqual(row['daily_statistics']['completed_UTC_days'], 2)
            self.assertEqual(row['daily_statistics']['annualized_daily_vol'], h.daily_stats([10100., 10300.])['annualized_daily_vol'])
            self.assertTrue(row['all_saved_numeric_bits_verified'])
            wrong = numeric(all_values); wrong['columns'][15]['raw_SHA256'] = 'bad'
            with self.assertRaises(ValueError): h.stream_prefix(root, len(all_values), numeric=wrong, start_us=0)

    def test_common_prefix_excludes_halt_and_verifies_beyond_prefix(self):
        a, b = array(1440), array(1440); a[-1, 0], b[-1, 0] = 10100., 5000.
        with tempfile.TemporaryDirectory(dir=h.HERE) as directory:
            root = recovery(Path(directory) / 'recovery', (a, b))
            row = h.stream_prefix(root, 1440)
            self.assertEqual(row['last_completed_minute_NAV_USDT'], 10100.)
            self.assertTrue(row['excludes_halt_mark_after_last_completed_minute'])
            (root / 'day1.npz').write_bytes(b'tampered beyond prefix')
            with self.assertRaises(ValueError): h.stream_prefix(root, 1440)

    def test_zero_prefix_and_invalid_geometry(self):
        with tempfile.TemporaryDirectory(dir=h.HERE) as directory:
            root = recovery(Path(directory) / 'recovery', (array(2),))
            self.assertIsNone(h.stream_prefix(root, 0)['last_completed_minute_NAV_USDT'])
            with self.assertRaises(ValueError): h.stream_prefix(root, 3)

    def test_daily_csv_exact_roundtrip_including_signed_zero(self):
        a = array(1440); a[-1, 1] = -0.
        n = numeric(a)
        with tempfile.TemporaryDirectory(dir=h.HERE) as directory:
            base = Path(directory); root = recovery(base / 'recovery', (a, array(3)))
            path = base / 'DAILY.csv'; names = [r['name'] for r in n['columns']]
            with path.open('w') as file:
                writer = csv.writer(file); writer.writerow(names); writer.writerow([str(x) for x in a[-1]] + [h.DAY])
            h.verify_daily_csv(root, path, 0, n)
            path.write_text(path.read_text().replace('-0.0', '0.0'))
            with self.assertRaises(ValueError): h.verify_daily_csv(root, path, 0, n)

    def test_synthetic_zero_journal_Decimal_bridge(self):
        bridge = dict(gross_price_USDT='0', fees_USDT='0', execution_USDT='0', funding_cash_USDT='0', NAV='10000', maximum_error_USDT='0')
        account = dict(trades=[], funding=[], summary={'positions': {'X': {'decimal_strings': {'quantity': '0'}}},
            'terminal_mark_prices': {'X': 1.}, 'decimal_strings': {'NAV': '10000'}})
        result = dict(terminal_residual_quantity={'X': '0'}, independent_decimal_NAV_bridge=bridge)
        self.assertEqual(h.journal_reconciliation(account, result, ['X']), bridge)
        result['terminal_residual_quantity']['X'] = '1e-100'
        with self.assertRaises(ValueError): h.journal_reconciliation(account, result, ['X'])

    def test_renderer_retains_negative_and_unavailable_rows(self):
        unavailable = {'available': False, 'reason': 'UNSTARTED_NO_WALLET'}
        r = dict(years=[dict(year=year, cases={'SMA200_10PCT': unavailable, 'STATIC50': unavailable, 'EXACTHALF': unavailable}, comparisons={})
            for year in (2023, 2024, 2025)], interpretation='conditional only')
        text = report.render_summary(r)
        self.assertEqual(text.count('SMA200_10PCT: unavailable'), 3)
        self.assertIn('2024', text)

    def test_REPORT_gate_is_first(self):
        with patch.object(report.gate, 'require_bounded_worker', side_effect=RuntimeError('no GO')), \
             patch.object(report.p, 'read', side_effect=AssertionError('input read')):
            with self.assertRaisesRegex(RuntimeError, 'no GO'): report.main()


if __name__ == '__main__':
    unittest.main()
