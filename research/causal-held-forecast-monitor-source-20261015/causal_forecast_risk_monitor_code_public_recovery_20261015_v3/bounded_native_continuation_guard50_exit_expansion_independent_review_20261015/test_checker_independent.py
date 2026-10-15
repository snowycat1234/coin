"""Independent fake-origin exact native-event checker boundaries."""
from copy import deepcopy
from decimal import Decimal as Q,localcontext
import unittest
import expansion as e
import saved_native_reconciliation as checker
from test_expansion import account,marks,fill

def export(a):return e.V2.OWNED.export_tree(a.snapshot())

def rounded_account():
    a=account()
    for k,(side,quantity,mid) in enumerate((('BUY','.003','10001'),('BUY','.002','10003'),
            ('BUY','.002','10007'),('SELL','.001','10009'),('BUY','.015','10011'))):
        signal=k*3*e.MINUTE;event=signal+e.MINUTE+1
        marks(a,event-1)
        a.execute_fill('BTCUSDT',side,quantity,event,signal,'ROUND:'+str(k),execution_mid_price=mid,
            quote_available_us=event-1,available_quantity=quantity)
    return a

class IndependentChecker(unittest.TestCase):
    def test_subminute_signal_requires_exact_ceil_native_latency(self):
        a=account();at=2*e.MINUTE+30_000_001;marks(a,at-1)
        a.execute_fill('BTCUSDT','SELL','.02',at,0,'SUBMINUTE',execution_mid_price='50000',
            quote_available_us=at-1,available_quantity='.02')
        audit=export(a);checker.reconcile_saved_native(audit)
        audit['trades'][0]['signal_us']=e.MINUTE+30_000_000
        with self.assertRaises(ValueError):checker.reconcile_saved_native(audit)

    def test_mark_takeover_precedes_sameclock_zero_funding(self):
        a=account();fill(a);at=2*e.MINUTE
        marks(a,at,100000)
        self.assertEqual(len(a.settlement_journal),1)
        a.apply_funding('BTCUSDT','POST_MARK_ZERO',at,Q(0),at)
        self.assertFalse(a.funding[-1]['owned']);self.assertEqual(a.funding[-1]['quantity'],0)
        proof=checker.reconcile_saved_native(export(a),expected_continuation_version=e.VERSION)
        self.assertTrue(proof['passed']);self.assertEqual(proof['conditional_settlement_rows_checked'],1)

    def test_native40_rounding_proof_retains_nonzero_raw100_delta(self):
        a=rounded_account();proof=checker.reconcile_saved_native(export(a),expected_continuation_version=e.VERSION)
        self.assertTrue(proof['passed']);self.assertFalse(proof['tolerance_or_epsilon_used'])
        errors=proof['raw_precision100_stored_delta_terminal_residuals']
        self.assertTrue(any(Q(x)!=0 for x in errors['isolated'].values()),proof)
        self.assertTrue(proof['rounded_subtraction_rows'])

    def test_genuine_cash_margin_and_event_sequence_corruption_fails_exactly(self):
        original=export(rounded_account())
        for kind in ('cash','margin','sequence'):
            with self.subTest(kind=kind):
                audit=deepcopy(original)
                if kind=='cash':audit['financial_ledger'][0]['free_cash_after']='9000'
                elif kind=='margin':audit['financial_ledger'][0]['isolated_delta']['BTCUSDT']='999.2000000000000000000000000000000001'
                else:audit['financial_ledger'][0]['sequence']=2
                with self.assertRaises(ValueError):checker.reconcile_saved_native(audit)

    def test_native_BASE27_friction_cannot_be_rewritten_with_consistent_cost_diagnostic(self):
        a=account();fill(a);audit=export(a);row=audit['trades'][0];d=row['decimal_strings']
        with localcontext() as ctx:
            ctx.prec=40
            oldcost=Q(d['execution_cost']);mid=Q(d['execution_mid_price'])+1
            d['execution_mid_price']=d['mid_price']=str(mid)
            newcost=Q(d['quantity'])*abs(Q(d['fill_price'])-mid)
            d['execution_cost']=str(newcost);audit['totals']['execution_cost']=str(Q(audit['totals']['execution_cost'])-oldcost+newcost)
        with self.assertRaises(ValueError):checker.reconcile_saved_native(audit)

    def test_mark_risk_and_funding_cannot_fabricate_paid_execution(self):
        for kind in ('NATIVE_MARK_RISK','NATIVE_FUNDING'):
            a=account();fill(a);audit=export(a);audit['financial_ledger'][0]['kind']=kind
            with self.subTest(kind=kind),self.assertRaises(ValueError):checker.reconcile_saved_native(audit)

    def test_native_trade_leg_identity_cannot_lie(self):
        a=account();fill(a);audit=export(a);audit['trades'][0]['leg']='CLOSE'
        with self.assertRaises(ValueError):checker.reconcile_saved_native(audit)

    def test_native_zero_funding_duplicate_is_not_a_second_event(self):
        a=account();marks(a,0);marks(a,e.MINUTE)
        a.apply_funding('BTCUSDT','ZERO_UNIQUE',e.MINUTE,Q(0),e.MINUTE)
        audit=export(a);audit['funding'].append(deepcopy(audit['funding'][0]))
        with self.assertRaises(ValueError):checker.reconcile_saved_native(audit)

if __name__=='__main__':unittest.main(verbosity=2)
