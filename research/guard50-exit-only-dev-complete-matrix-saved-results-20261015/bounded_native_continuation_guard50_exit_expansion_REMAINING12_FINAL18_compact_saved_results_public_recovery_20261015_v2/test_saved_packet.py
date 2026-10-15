"""Bounded offline mutation checks, never a financial rerun or account."""
import unittest,pathlib,copy
from verify_saved_packet import *
class SavedPacketTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.root=pathlib.Path(__file__).resolve().parent;cls.cell=CELLS[0];cls.a=load_case(cls.root,cls.cell,'ACCOUNT_FINANCIAL_AUDIT.json');cls.r=load_case(cls.root,cls.cell,'NATIVE_RESULT.json');cls.p=load_case(cls.root,cls.cell,'NATIVE40_RECONSTRUCTION_PROOF.json')
 def mutate(self,callback):
  a=copy.deepcopy(self.a);r=copy.deepcopy(self.r);p=copy.deepcopy(self.p);callback(a,r,p)
  with self.assertRaises((ValueError,KeyError,AssertionError)):validate_financial(a,r,p)
 def test_original_exact_native40_and_raw100(self):self.assertEqual(validate_financial(self.a,self.r,self.p),self.p)
 def test_cash_corruption(self):self.mutate(lambda a,r,p:a.__setitem__('free_cash',str(Decimal(a['free_cash'])+Decimal('1'))))
 def test_margin_corruption(self):self.mutate(lambda a,r,p:a['positions']['ETHUSDT'].__setitem__('isolated_balance','0.000000000000000000000000000000000000001'))
 def test_ledger_cash_delta_corruption(self):self.mutate(lambda a,r,p:a['financial_ledger'][0].__setitem__('free_cash_delta','1'))
 def test_ledger_sequence_corruption(self):self.mutate(lambda a,r,p:a['financial_ledger'][1].__setitem__('sequence',1))
 def test_trade_fee_corruption(self):self.mutate(lambda a,r,p:a['trades'][0]['decimal_strings'].__setitem__('fee_amount','0'))
 def test_trade_leg_forgery(self):self.mutate(lambda a,r,p:a['trades'][0].__setitem__('leg','CLOSE'))
 def test_duplicate_zero_funding(self):self.mutate(lambda a,r,p:a['funding'].append(copy.deepcopy(a['funding'][0])))
 def test_result_summary_forgery(self):self.mutate(lambda a,r,p:r['summary']['decimal_strings'].__setitem__('NAV','10000'))
 def test_precision100_residual_suppression(self):self.mutate(lambda a,r,p:p['raw_precision100_stored_delta_terminal_residuals']['isolated'].__setitem__('ETHUSDT','0'))
 def test_conditional_support_forgery(self):self.mutate(lambda a,r,p:r['economics'].__setitem__('conditional_insurance_overshoot_absorption_USDT','1'))
 def test_risk_breach_suppression(self):
  risk=load_case(self.root,self.cell,'ACTUAL_HELD_RISK_REPORT.json');rr=read(self.root/R/f'actual_remaining12_risk_review/{self.cell}_RISK_REVIEW.json');risk['forecast_volatility_breach_minutes']=0
  with self.assertRaises(ValueError):validate_risk_saved(risk,rr)
 def test_causal_event_prefix_forgery(self):
  a=copy.deepcopy(self.a);a['trades'][0]['decimal_strings']['fee_amount']='0'
  with self.assertRaises(ValueError):validate_prefix(a,self.cell,self.root)
 def test_compounding_claim_rejected(self):
  report=read(self.root/'RESULTS_REPORT.json');terminal=None;report['continuous_two_year_CAGR']=.25
  with self.assertRaises(ValueError):validate_report(report,terminal)
 def test_false_cold_minute_recovery_rejected(self):
  report=read(self.root/'RESULTS_REPORT.json');terminal=None;report['all_minute_risk_regeneration_is_self_contained']=True
  with self.assertRaises(ValueError):validate_report(report,terminal)
if __name__=='__main__':unittest.main()
