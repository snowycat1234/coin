"""Pure invented dictionaries test actual predicate, never a financial account."""
from copy import deepcopy
from pathlib import Path
import sys
import unittest
ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT/'original_cs_mom21_D_20261015_v5'))
import cs_process_runtime as r
M=60000000


def fixture(*,full=True,settled=False):
    calendar=[0,10*M];stop=None if full else 2*M;minutes=10 if full else 1
    a=dict(status='ACTIVE',unpaid_liability='0',positions={'FAKE':{'quantity':'0'}},settlement_journal=[{}] if settled else [],clock_us=10*M if full else stop)
    econ=dict(full_calendar=full,paid_flat=full and not settled,actual_paid_market_flat=full and not settled,
              conditional_settled_flat=full and settled,comparable_full_calendar_return=0. if full else None,
              paid_net_return=0. if full and not settled else None,conditional_model_net_return=0. if full and settled else None)
    result=dict(summary={'decimal_strings':{'NAV':'10000'},'completed_minutes':minutes,'stop_us':stop},economics=econ)
    return a,result,calendar,minutes,stop


def classify(f):
    a,result,calendar,minutes,stop=f
    return r.classify_terminal(a,result,calendar=calendar,completed_minutes=minutes,stop_us=stop)


class PredicateReview(unittest.TestCase):
    def test_paid_flat_full_calendar_exact(self):
        self.assertEqual(classify(fixture()),'FULL_CALENDAR_ACTUAL_PAID_MARKET_FLAT')
    def test_conditional_flat_cannot_be_called_paid(self):
        f=fixture(settled=True)
        self.assertEqual(classify(f),'FULL_CALENDAR_CONDITIONAL_SETTLED_FLAT')
        f[1]['economics']['paid_flat']=True
        with self.assertRaisesRegex(ValueError,'TAXONOMY'):classify(f)
    def test_full_unsettled_residual_pauses_queue(self):
        f=fixture();f[0]['positions']['FAKE']['quantity']='1'
        f[1]['economics'].update(paid_flat=False,actual_paid_market_flat=False,comparable_full_calendar_return=None,paid_net_return=None)
        with self.assertRaisesRegex(ValueError,'RESIDUAL_CASE'):classify(f)
    def test_partial_execution_error_cannot_be_relabelled_halt(self):
        with self.assertRaisesRegex(ValueError,'NOT_ECONOMIC_HALT'):classify(fixture(full=False))
    def test_global_debt_halt_requires_exact_witness_and_real_debt_or_nonpositive_nav(self):
        f=fixture(full=False);a,result,_,_,stop=f
        a.update(status='BANKRUPT_HALT',unpaid_liability='1',halt_witness={'event_us':stop,'NAV':'9999','unpaid_liability':'1'})
        result['summary']['decimal_strings']['NAV']='9999'
        self.assertEqual(classify(f),'NATIVE_HALT_PARTIAL_CALENDAR')
        bad=deepcopy(f);bad[0]['halt_witness']['NAV']='9998'
        with self.assertRaisesRegex(ValueError,'NAV_DEBT'):classify(bad)
        bad=deepcopy(f);bad[0]['unpaid_liability']='0';bad[0]['halt_witness'].update(NAV='10000',unpaid_liability='0');bad[1]['summary']['decimal_strings']['NAV']='10000'
        with self.assertRaisesRegex(ValueError,'BANKRUPTCY_PREDICATE'):classify(bad)
    def test_symbol_liquidation_halt_requires_exact_positive_equity_below_maintenance(self):
        f=fixture(full=False);a,result,_,_,stop=f
        a.update(status='LIQUIDATION_REQUIRED_HALT',positions={'FAKE':dict(quantity='1',entry_price='100',isolated_balance='.2')},
            marks={'FAKE':[dict(price='100')]},halt_witness=dict(event_us=stop,symbol='FAKE',quantity='1',mark_price='100',
                isolated_equity='.2',maintenance_margin='.5',NAV='10000',unpaid_liability='0'))
        self.assertEqual(classify(f),'NATIVE_HALT_PARTIAL_CALENDAR')
        for key,value in [('quantity','0'),('isolated_equity','.3'),('maintenance_margin','.6'),('event_us',stop-1)]:
            bad=deepcopy(f);bad[0]['halt_witness'][key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):classify(bad)
    def test_halt_completed_minute_clock_mismatch_denied(self):
        f=fixture(full=False);a,result,_,_,stop=f
        a.update(status='BANKRUPT_HALT',unpaid_liability='1',halt_witness=dict(event_us=stop,NAV='9999',unpaid_liability='1'))
        result['summary']['decimal_strings']['NAV']='9999'
        bad=list(f);bad[3]=2
        with self.assertRaisesRegex(ValueError,'NOT_ECONOMIC_HALT'):classify(bad)
        a['clock_us']=stop-1
        with self.assertRaisesRegex(ValueError,'NOT_ECONOMIC_HALT'):classify(f)

if __name__=='__main__':unittest.main(verbosity=2)
