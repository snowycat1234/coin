#!/usr/bin/env python3
"""Saved-only negative financial, scope and mutation tests. No account imports."""
from pathlib import Path
from copy import deepcopy
from decimal import Decimal,localcontext
from unittest.mock import patch
import unittest,sys,socket,subprocess,ast
from saved_comparison import ATT,CELLS,load,build
from verify_packet import validate_financial,validate_scope,verify
ROOT=Path(__file__).resolve().parent
class SavedPacketTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.d=ROOT/ATT/(CELLS[0]+'_CAUSAL_FORECAST');cls.a=load(cls.d/'ACCOUNT_FINANCIAL_AUDIT.json');cls.r=load(cls.d/'NATIVE_RESULT.json');cls.p=load(cls.d/'NATIVE40_RECONSTRUCTION_PROOF.json')
 def test_exact_native40_and_raw100_residuals(self):validate_financial(self.a,self.r,self.p)
 def rejected(self,a=None,r=None,p=None):
  with self.assertRaises((ValueError,KeyError,AssertionError)):validate_financial(a or self.a,r or self.r,p or self.p)
 def test_one_native_decimal_digit_mutation_rejected(self):
  a=deepcopy(self.a)
  with localcontext() as c:c.prec=100;a['trades'][0]['decimal_strings']['fee_amount']=str(Decimal(a['trades'][0]['decimal_strings']['fee_amount'])+Decimal('1e-40'))
  self.rejected(a=a)
 def test_ledger_after_state_mutation_rejected(self):
  a=deepcopy(self.a);a['financial_ledger'][0]['free_cash_after']='9999';self.rejected(a=a)
 def test_raw100_residual_suppression_rejected(self):
  p=deepcopy(self.p);p['raw_precision100_stored_delta_terminal_residuals']['isolated']['BTCUSDT']='0';self.rejected(p=p)
 def test_forced_balancing_epsilon_claim_rejected(self):
  p=deepcopy(self.p);p['tolerance_or_epsilon_used']=True;self.rejected(p=p)
 def test_paid_flat_misclassification_rejected(self):
  r=deepcopy(self.r);r['economics']['actual_paid_market_flat']=False;self.rejected(r=r)
 def test_transfer_mutation_rejected(self):
  a=deepcopy(self.a);a['transfer_journal']=[{'amount':'1'}];self.rejected(a=a)
 def test_continuous_cagr_claim_rejected(self):
  s=build(ROOT)['scope'];s['continuous_two_year_CAGR']='0.2'
  with self.assertRaises(ValueError):validate_scope(s)
 def test_false_all_minute_recovery_claim_rejected(self):
  s=build(ROOT)['scope'];s['all_minute_risk_regenerated']=True
  with self.assertRaises(ValueError):validate_scope(s)
 def test_false_OOS_and_pure_normalization_claims_rejected(self):
  for key in ['OOS_or_live_performance_claim','no_pure_statistic_normalization_effect_claim']:
   s=build(ROOT)['scope'];s[key]=not s[key]
   with self.assertRaises(ValueError):validate_scope(s)
 def test_comparison_rebuild_forbids_network_process_and_financial_imports(self):
  import builtins
  orig=builtins.__import__
  def guarded(name,*a,**k):
   if any(x in name for x in ['forecast_monitor','forecast_historical','forecast_entry','perpetual_account','run_forecast','native_runtime']):raise AssertionError('FORBIDDEN_FINANCIAL_IMPORT')
   return orig(name,*a,**k)
  with patch.object(socket.socket,'connect',side_effect=AssertionError('FORBIDDEN_NETWORK')),patch.object(subprocess,'Popen',side_effect=AssertionError('FORBIDDEN_PROCESS')),patch('builtins.__import__',side_effect=guarded):
   r=build(ROOT);self.assertEqual(len(r['rows']),4);validate_scope(r['scope'])
 def test_complete_packet_rehash_and_rerender(self):self.assertEqual(verify(ROOT)['status'],'PASS_FOUR_MONITOR_COMPACT_SAVED_PACKET')
if __name__=='__main__':unittest.main(verbosity=2)
