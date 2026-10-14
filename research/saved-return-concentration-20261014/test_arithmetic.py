import math
import unittest
from analyze_saved_returns import DAY_US, return_metrics

def fixture(deltas):
    start = 1672531200000000
    return [{'start_us': start+i*DAY_US, 'end_us': start+(i+1)*DAY_US,
             'completed': True, 'stop_us': None, 'net_increment_USDT': d}
            for i,d in enumerate(deltas)]

class ArithmeticTests(unittest.TestCase):
    def test_flat_series(self):
        result, _ = return_metrics(fixture([0]*100),10000)
        self.assertEqual(result['annual_return'],0)
        self.assertIsNone(result['top_daily_log_returns']['5']['share_of_annual_net_log_return'])
        self.assertEqual(result['worst_rolling']['90']['complete_windows_tested'],11)
    def test_compounding_and_deletion(self):
        result, _ = return_metrics(fixture([10,-11]),100)
        self.assertAlmostEqual(result['annual_return'],-.01)
        self.assertAlmostEqual(result['annual_log_return'],math.log(.99))
        self.assertAlmostEqual(result['leave_best_month_out']['return_with_best_month_daily_returns_replaced_by_zero'],0)
    def test_month_boundary(self):
        result, _ = return_metrics(fixture([0]*30+[10]+[11]+[0]*27),100)
        self.assertEqual([x['days'] for x in result['months']],[31,28])
        self.assertAlmostEqual(result['months'][0]['compounded_return'],.1)
        self.assertAlmostEqual(result['months'][1]['compounded_return'],.1)
        self.assertAlmostEqual(sum(x['initial_capital_return_contribution_pp'] for x in result['months']),21)
    def test_worst_window_includes_first_and_last(self):
        result, _ = return_metrics(fixture([-10]+[0]*89),100)
        self.assertAlmostEqual(result['worst_rolling']['90']['return'],-.1)
        result, _ = return_metrics(fixture([0]*89+[-10]),100)
        self.assertEqual(result['worst_rolling']['30']['last_day_utc'],'2023-03-31')
        self.assertAlmostEqual(result['worst_rolling']['30']['return'],-.1)
    def test_net_share_can_exceed_one(self):
        result, _ = return_metrics(fixture([10]*10+[-9]*10),100)
        self.assertGreater(result['top_daily_log_returns']['5']['share_of_annual_net_log_return'],1)
    def test_bad_coverage(self):
        rows=fixture([1,2]);rows[1]['start_us']+=DAY_US;rows[1]['end_us']+=DAY_US
        with self.assertRaises(ValueError): return_metrics(rows,100)
    def test_nonpositive_NAV(self):
        with self.assertRaises(ValueError): return_metrics(fixture([-100]),100)
    def test_incomplete(self):
        rows=fixture([1]);rows[0]['completed']=False
        with self.assertRaises(ValueError): return_metrics(rows,100)
    def test_nonfinite(self):
        with self.assertRaises(ValueError): return_metrics(fixture([float('nan')]),100)

if __name__=='__main__': unittest.main(verbosity=2)
