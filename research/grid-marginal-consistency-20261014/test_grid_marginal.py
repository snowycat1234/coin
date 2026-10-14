"""Nine bounded offline tests; no strategy engine or market data access."""
from copy import deepcopy
from decimal import Decimal as D
import json
from pathlib import Path
import tempfile
import unittest
import analyze_grid_marginal as a

BASE = Path(__file__).resolve().parent

class GridMarginalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.inputs = {}
        cls.results = {}
        for year in (2023, 2025):
            c = a.read_json(BASE / 'inputs' / f'{year}_cash_DAILY.json')
            g = a.read_json(BASE / 'inputs' / f'{year}_grid_DAILY.json')
            cs = a.read_json(BASE / 'inputs' / f'{year}_cash_SUMMARY_FINANCIAL.json')
            gs = a.read_json(BASE / 'inputs' / f'{year}_grid_SUMMARY_FINANCIAL.json')
            cls.inputs[year] = c, g, cs, gs
            cls.results[year] = a.analyze_pair(year, c, g, cs, gs)

    def test_01_complete_paired_calendars_and_month_telescope(self):
        for year, (result, daily) in self.results.items():
            self.assertEqual(len(daily), 365)
            self.assertEqual(daily[0]['date'], f'{year}-01-01')
            self.assertEqual(daily[-1]['date'], f'{year}-12-31')
            self.assertEqual(len(result['months']), 12)
            self.assertEqual(sum(m['days'] for m in result['months']), 365)
            self.assertEqual(sum(m['paired_increment_USDT'] for m in result['months']), result['annual_increment_USDT'])
            self.assertEqual(daily[-1]['cumulative_difference_USDT'], result['annual_increment_USDT'])

    def test_02_native_terminal_reconciliation_and_known_annual_rounding(self):
        expected = {2023: D('44.4687'), 2025: D('-35.3650')}
        for year, (result, _) in self.results.items():
            self.assertEqual(result['annual_increment_USDT'].quantize(D('0.0001')), expected[year])
            self.assertLess(abs(result['annual_increment_USDT'] - result['summary_terminal_increment_USDT']), a.TOL)
            for _, _, cs, gs in [self.inputs[year]]:
                self.assertEqual(a.validate_summary(cs), a.INITIAL)
                self.assertEqual(a.validate_summary(gs), a.INITIAL)

    def test_03_zero_days_are_in_denominator(self):
        s = a.signs([D(1), D(0), D(-1), D(0)])
        self.assertEqual((s['positive'], s['negative'], s['zero']), (1, 1, 2))
        self.assertEqual(s['positive_fraction_all'], D('0.25'))
        self.assertEqual(s['positive_fraction_nonzero'], D('0.5'))
        self.assertIsNone(a.signs([D(0)])['positive_fraction_nonzero'])
        for year, expected in [(2023, (177, 188, 0)), (2025, (182, 183, 0))]:
            d = self.results[year][0]['daily_increment_signs']
            self.assertEqual((d['positive'], d['negative'], d['zero']), expected)

    def test_04_drawdown_includes_initial_zero(self):
        r = a.difference_path_stats(['a', 'b', 'c'], [D(-2), D(1), D(-3)])
        self.assertEqual(r['maximum_drawdown_USDT'], D(4))
        self.assertEqual(r['drawdown_peak_date'], 'INITIAL_ZERO')
        self.assertEqual(r['minimum_difference_USDT'], D(-4))
        self.assertEqual(r['maximum_difference_USDT'], D(0))

    def test_05_drawdown_is_path_dependent_with_first_tie_dates(self):
        r = a.difference_path_stats(['a', 'b', 'c', 'd'], [D(2), D(-1), D(3), D(-5)])
        self.assertEqual(r['maximum_drawdown_USDT'], D(5))
        self.assertEqual((r['drawdown_peak_date'], r['drawdown_trough_date']), ('c', 'd'))
        r = a.difference_path_stats(['a', 'b'], [D(2), D(0)])
        self.assertEqual(r['maximum_date'], 'a')

    def test_06_return_correlation_not_NAV_correlation(self):
        x = list(map(D, [1, 2, 3]))
        self.assertEqual(a.pearson(x, list(map(D, [2, 4, 6]))), D(1))
        self.assertEqual(a.pearson(x, list(reversed(x))), D(-1))
        self.assertIsNone(a.pearson(x, [D(1)] * 3))
        for year, (result, daily) in self.results.items():
            self.assertEqual(daily[0]['cash_simple_return'], daily[0]['cash_increment_USDT'] / a.INITIAL)
            self.assertEqual(daily[1]['grid_simple_return'], daily[1]['grid_increment_USDT'] / daily[0]['grid_NAV_USDT'])
            self.assertGreater(result['lag_zero_daily_simple_return_correlation'], D('0.999'))
            self.assertLess(result['lag_zero_daily_simple_return_correlation'], D(1))

    def test_07_reject_missing_duplicate_incomplete_nonfinite_days(self):
        c = self.inputs[2023][0]
        bad_sets = [c[:-1]]
        duplicate = deepcopy(c); duplicate[1] = deepcopy(duplicate[0]); bad_sets.append(duplicate)
        incomplete = deepcopy(c); incomplete[0]['completed'] = False; bad_sets.append(incomplete)
        nonfinite = deepcopy(c); nonfinite[0]['net_increment_USDT'] = D('NaN'); bad_sets.append(nonfinite)
        for bad in bad_sets:
            with self.assertRaises(ValueError):
                a.validate_days(bad, 2023)

    def test_08_reject_summary_drift_and_verify_best_month_subtraction(self):
        c, g, cs, gs = self.inputs[2023]
        bad = deepcopy(gs); bad['paid_NAV_decimal'] = str(D(bad['paid_NAV_decimal']) + 1)
        with self.assertRaises(ValueError):
            a.analyze_pair(2023, c, g, cs, bad)
        bad = deepcopy(gs); bad['cost_scenario']['slippage_bps'] = 5
        with self.assertRaises(ValueError):
            a.analyze_pair(2023, c, g, cs, bad)
        bad = deepcopy(gs); bad['unexpected_metadata'] = 'reject'
        with self.assertRaises(ValueError):
            a.validate_summary(bad)
        for year, (result, _) in self.results.items():
            s = result['remove_best_month_sensitivity']
            best = max(result['months'], key=lambda x: x['paired_increment_USDT'])
            self.assertEqual(s['month'], best['month'])
            self.assertEqual(s['remaining_dollar_contribution_USDT'] + s['removed_contribution_USDT'], result['annual_increment_USDT'])

    def test_09_source_integrity_and_byte_identical_reproduction(self):
        catalog = a.read_json(BASE / 'SOURCE_CATALOG.json')
        self.assertEqual(len(catalog['sources']), 4)
        for s in catalog['sources']:
            self.assertEqual(a.git_blob_sha(BASE / s['daily_file']), s['daily_git_blob_sha'])
            self.assertEqual(a.sha256(BASE / s['daily_file']), s['daily_sha256'])
            self.assertEqual(a.sha256(BASE / s['summary_financial_file']), s['summary_financial_sha256'])
        with tempfile.TemporaryDirectory() as tmp:
            a.run(BASE, Path(tmp))
            for filename in ['RESULTS.json', 'VERIFIED_SOURCES.json', 'MONTHLY_INCREMENT.csv', '2023_PAIRED_DAILY.csv', '2025_PAIRED_DAILY.csv']:
                self.assertEqual((Path(tmp) / filename).read_bytes(), (BASE / 'results' / filename).read_bytes())

if __name__ == '__main__':
    unittest.main(verbosity=2)
