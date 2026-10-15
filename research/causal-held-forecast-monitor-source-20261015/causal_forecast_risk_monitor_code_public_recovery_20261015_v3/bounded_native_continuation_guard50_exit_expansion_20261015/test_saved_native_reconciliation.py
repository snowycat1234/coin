"""Generated-only exact arithmetic and resealed-corruption rejection gates."""
from copy import deepcopy
from decimal import Decimal as Q
import unittest
import numpy as np
import expansion as e
from test_expansion import account,marks,fill
from test_native_runtime import fixture
from saved_native_reconciliation import reconcile_saved_native


def snapshot(a):return e.V2.OWNED.export_tree(a.snapshot())


def repeating():
    a=account();at=0
    # Unequal prices/quantities create repeating weighted basis, then partial
    # margin release; all actions are generated and native40 exact.
    sequence=[('BUY','.003','10001'),('BUY','.002','10003'),('BUY','.002','10007'),
              ('SELL','.001','10009'),('BUY','.015','10011')]
    for index,(side,q,mid) in enumerate(sequence):
        signal=index*3*e.MINUTE;event=signal+e.MINUTE+1;marks(a,event-1)
        a.execute_fill('BTCUSDT',side,q,event,signal,'GENERATED'+str(index),execution_mid_price=mid,
            quote_available_us=event-1,available_quantity=q)
    return snapshot(a)


class SavedNativeTests(unittest.TestCase):
    def test_generated_repeating_fractional_basis_raw100_residual_is_retained(self):
        a=repeating();p=reconcile_saved_native(a)
        self.assertTrue(p['passed']);self.assertFalse(p['tolerance_or_epsilon_used'])
        residuals=p['raw_precision100_stored_delta_terminal_residuals']
        self.assertTrue(p['rounded_subtraction_rows'] or any(Q(x)!=0 for x in residuals['isolated'].values()) or Q(residuals['free_cash'])!=0)

    def test_true_resealed_arithmetic_corruption_rejected(self):
        original=repeating()
        mutations=[lambda a:a.__setitem__('free_cash',str(Q(a['free_cash'])+1)),
            lambda a:a.__setitem__('unpaid_liability','1'),
            lambda a:a['positions']['BTCUSDT'].__setitem__('isolated_balance','1'),
            lambda a:a['positions']['BTCUSDT'].__setitem__('entry_price','1'),
            lambda a:a['financial_ledger'][0].__setitem__('free_cash_delta','0'),
            lambda a:a['financial_ledger'][0].__setitem__('kind','NATIVE_MARK_RISK'),
            lambda a:a['trades'][0]['decimal_strings'].__setitem__('fee_amount','0'),
            lambda a:a['trades'][1]['decimal_strings'].__setitem__('entry_price_after','1'),
            lambda a:a['config'].__setitem__('fee_rate','0.001'),
            lambda a:a['totals'].__setitem__('realized_PnL','1')]
        for mutate in mutations:
            a=deepcopy(original);mutate(a)
            with self.assertRaises(ValueError):reconcile_saved_native(a)

    def test_generated_calendar_result_nav_and_all_events(self):
        w,r,d=fixture(1);sim,g=e.construct_case(w,r,d,np.full((1,5),.03),generated_scope=e.GENERATED)
        while sim.cursor<sim.end and sim.stop is None:sim.advance_day()
        result=e.case_result(sim,g);result.pop('minute');result['targets']=result['targets'].to_dicts()
        result=e.V2.OWNED.export_tree(result);audit=snapshot(sim.account)
        self.assertTrue(reconcile_saved_native(audit,result)['passed'])
        result['summary']['decimal_strings']['NAV']='10001'
        with self.assertRaises(ValueError):reconcile_saved_native(audit,result)

    def test_conditional_takeover_never_claims_paid_cash_credit(self):
        a=account();fill(a);marks(a,2*e.MINUTE,100000)
        audit=snapshot(a);p=reconcile_saved_native(audit)
        self.assertEqual(p['conditional_settlement_rows_checked'],1)
        self.assertEqual(Q(audit['settlement_journal'][0]['decimal_strings']['free_cash_credit']),0)
        bad=deepcopy(audit);bad['settlement_journal'][0]['decimal_strings']['conditional_insurance_value_received']='0'
        with self.assertRaises(ValueError):reconcile_saved_native(bad)

    def test_mark_takeover_precedes_same_clock_zero_funding(self):
        a=account();fill(a);at=2*e.MINUTE;marks(a,at,100000)
        # Funding at this clock observes the position after mark takeover.
        a.apply_funding('BTCUSDT','SAMECLOCK_ZERO',at,'.001',at)
        audit=snapshot(a)
        self.assertEqual(audit['funding'][0]['decimal_strings']['signed_funding_USDT'],'0')
        self.assertTrue(reconcile_saved_native(audit)['passed'])

    def test_real_debt_not_forgiven_or_relabelled_settlement(self):
        a=account();fill(a)
        # Honest generated funding debit exceeds free cash plus own isolated
        # margin and creates permanent native bankruptcy debt.
        at=2*e.MINUTE;marks(a,at-1)
        a.apply_funding('BTCUSDT','DEBT',at,'-1000',at)
        audit=snapshot(a);p=reconcile_saved_native(audit)
        self.assertGreater(Q(audit['unpaid_liability']),0);self.assertEqual(audit['status'],'BANKRUPT_HALT')
        self.assertTrue(p['passed']);self.assertEqual(audit['settlement_journal'],[])
        bad=deepcopy(audit);bad['unpaid_liability']='0'
        with self.assertRaises(ValueError):reconcile_saved_native(bad)


if __name__=='__main__':unittest.main()
