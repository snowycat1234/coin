"""Exact zero-executable native ownership, never positive-risk quality bypass."""
from copy import deepcopy
from decimal import Decimal as D
import unittest
import integration as i
from test_integration import account
from test_coupled_boundaries import known_marks


class ZeroRequestTests(unittest.TestCase):
    def test_zero_request_matches_exact_native_clock_and_identity_then_replay_conflict(self):
        a=account('CONTINUE_ONLY');known_marks(a,0);known_marks(a,i.MINUTE)
        a._quality_intervals=((i.MINUTE,3*i.MINUTE,i.S),)
        known_marks(a,2*i.MINUTE)
        before=a.snapshot();native=a.fork_for_preview()
        args=('BTCUSDT','BUY','.001',2*i.MINUTE+1,i.MINUTE,'ZERO')
        kwargs=dict(execution_mid_price='50000',quote_available_us=2*i.MINUTE,available_quantity='0')
        expected=i.ENGINE.USDTLinearPerpetualAccount.execute_fill(native,*args,**kwargs)
        actual=a.execute_fill(*args,**kwargs)
        self.assertEqual(actual,expected);self.assertEqual(actual['decimal_strings']['executed_quantity'],'0')
        self.assertEqual(a.clock_us,native.clock_us);self.assertIn('ZERO',a.fill_requests)
        self.assertEqual(a.snapshot()['fill_requests'],native.snapshot()['fill_requests'])
        for key in ('free_cash','unpaid_liability','positions','totals','trades'):
            self.assertEqual(a.snapshot()[key],before[key])
        identity=a.preview_state_token();self.assertEqual(a.execute_fill(*args,**kwargs),actual)
        self.assertTrue(i.native._exact_tree_equal(identity,a.preview_state_token()))
        with self.assertRaisesRegex(ValueError,'conflicting fill identity'):
            a.execute_fill(*args,**{**kwargs,'available_quantity':'.001'})
        self.assertTrue(i.native._exact_tree_equal(identity,a.preview_state_token()))

    def test_any_positive_executable_unknown_quality_remains_rejected(self):
        a=account('CONTINUE_ONLY');known_marks(a,0);a._quality_intervals=((i.MINUTE,4*i.MINUTE,i.S),)
        known_marks(a,2*i.MINUTE);before=a.preview_state_token()
        with self.assertRaisesRegex(ValueError,'NEW_INCREASE_FAIL_CLOSED'):
            a.execute_fill('BTCUSDT','BUY','.001',2*i.MINUTE+1,i.MINUTE,'POSITIVE',
                execution_mid_price='50000',quote_available_us=2*i.MINUTE,available_quantity='.001')
        self.assertTrue(i.native._exact_tree_equal(before,a.preview_state_token()))
        self.assertFalse(a.trades);self.assertNotIn('POSITIVE',a.fill_requests)

if __name__=='__main__':unittest.main()
