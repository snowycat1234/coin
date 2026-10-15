#!/usr/bin/env python3
"""Exact saved-only negative tests: authentic cash, debt, margin and scope corruption."""
from copy import deepcopy
from decimal import Decimal,localcontext
from pathlib import Path
from unittest.mock import patch
import unittest,socket,subprocess,os,json,sys,tempfile,shutil
from saved_report import *
from verify_packet import validate_financial,validate_identity,verify
ROOT=Path(os.environ.get('SAVED_PACKET_TEST_ROOT',str(Path(__file__).resolve().parent)))
class SavedPacketTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.d=ROOT/ATT/CELLS[0];cls.a=load(cls.d/'ACCOUNT_FINANCIAL_AUDIT.json');cls.r=load(cls.d/'NATIVE_RESULT.json');cls.p=load(cls.d/'NATIVE40_RECONSTRUCTION_PROOF.json');cls.receipt=load(cls.d/'CASE_RECEIPT.json');cls.review=load(ROOT/REV/(CELLS[0]+'_SAVED_REVIEW.json'));cls.desc=load(ROOT/'traditional_D_partial2021_20261015/FROZEN_NINE_CELL_MANIFEST.json')['cells'][0]
 def rejected(self,a=None,r=None,p=None):
  with self.assertRaises((ValueError,KeyError,AssertionError)):validate_financial(a if a is not None else self.a,r if r is not None else self.r,p if p is not None else self.p)
 def test_positive_exact_native40(self):validate_financial(self.a,self.r,self.p)
 def test_genuine_final_cash_corruption_rejected(self):
  a=deepcopy(self.a);a['free_cash']='10981.59660181968820472910000000000000000';self.rejected(a=a)
 def test_genuine_final_debt_corruption_rejected(self):
  a=deepcopy(self.a);a['unpaid_liability']='0.0000000000000000000000000000000000000001';self.rejected(a=a)
 def test_genuine_final_isolated_margin_corruption_rejected(self):
  a=deepcopy(self.a);a['positions']['BTCUSDT']['isolated_balance']='1e-40';self.rejected(a=a)
 def test_native_ledger_cash_state_corruption_rejected(self):
  a=deepcopy(self.a);a['financial_ledger'][0]['free_cash_after']='9999';self.rejected(a=a)
 def test_native_ledger_debt_state_corruption_rejected(self):
  a=deepcopy(self.a);a['financial_ledger'][0]['unpaid_liability_after']='1e-40';self.rejected(a=a)
 def test_native_ledger_margin_delta_corruption_rejected(self):
  a=deepcopy(self.a);a['financial_ledger'][0]['isolated_delta']['BTCUSDT']='1e-40';self.rejected(a=a)
 def test_one_native_decimal_fee_digit_corruption_rejected(self):
  a=deepcopy(self.a)
  with localcontext() as c:c.prec=100;a['trades'][0]['decimal_strings']['fee_amount']=str(Decimal(a['trades'][0]['decimal_strings']['fee_amount'])+Decimal('1e-40'))
  self.rejected(a=a)
 def test_forced_zero_raw100_residual_rejected(self):
  p=deepcopy(self.p);p['raw_precision100_stored_delta_terminal_residuals']['free_cash']='1e-100';self.rejected(p=p)
 def test_epsilon_permission_corruption_rejected(self):
  p=deepcopy(self.p);p['tolerance_or_epsilon_used']=True;self.rejected(p=p)
 def test_proof_bool_integer_type_confusion_rejected(self):
  p=deepcopy(self.p);p['account_objects_constructed']=False;self.rejected(p=p)
 def test_forced_paid_flat_taxonomy_rejected(self):
  r=deepcopy(self.r);r['economics']['actual_paid_market_flat']=False;self.rejected(r=r)
 def test_illegal_margin_transfer_rejected(self):
  a=deepcopy(self.a);a['transfer_journal']=[{'amount':'1'}];self.rejected(a=a)
 def test_funding_ownership_corruption_rejected(self):
  a=deepcopy(self.a);a['funding'][0]['owned']=not a['funding'][0]['owned'];self.rejected(a=a)
 def test_false_partial_annualization_rejected(self):
  r=deepcopy(self.r);r['economics']['partial_return_annualized']=True;self.rejected(r=r)
 def test_wrong_case_scope_rejected(self):
  rec=deepcopy(self.receipt);rec['cell_id']=CELLS[1]
  with self.assertRaises(ValueError):validate_identity(rec,self.a,self.r,self.review,self.desc)
 def test_typed_year_identity_corruption_rejected(self):
  rec=deepcopy(self.receipt);rec['year']=2021.0
  with self.assertRaises(ValueError):validate_identity(rec,self.a,self.r,self.review,self.desc)
 def test_scope_bool_integer_confusion_rejected(self):
  a=deepcopy(self.a);a['historical_execution_scope']['fresh_genesis_only']=1
  with self.assertRaises(ValueError):validate_identity(self.receipt,a,self.r,self.review,self.desc)
 def test_false_SCOPE_claims_rejected(self):
  for key,value in [('partial_return_annualized',True),('continuous_CAGR','0.2'),('all_minute_risk_regenerated',True),('OOS_or_live_performance_claim',True),('full_audit_byte_identity_claim',True),('period_days',365),('accounts_constructed',False)]:
   s=dict(SCOPE);s[key]=value
   with self.assertRaises(ValueError,msg=key):validate_scope(s)
 def test_original_byte_hash_corruption_rejected(self):
  with tempfile.TemporaryDirectory() as td:
   copied=Path(td)/'candidate';shutil.copytree(ROOT,copied,ignore=shutil.ignore_patterns('__pycache__'))
   target=copied/ATT/CELLS[0]/'CASE_RECEIPT.json';target.write_bytes(target.read_bytes()+b' ')
   with self.assertRaisesRegex(ValueError,'EXACT_PACKET_MEMBER'):verify(copied,require_publication=False)
 def test_lossless_gzip_byte_hash_corruption_rejected(self):
  with tempfile.TemporaryDirectory() as td:
   copied=Path(td)/'candidate';shutil.copytree(ROOT,copied,ignore=shutil.ignore_patterns('__pycache__'))
   target=copied/ATT/CELLS[0]/'ACCOUNT_FINANCIAL_AUDIT.json.gz';b=bytearray(target.read_bytes());b[len(b)//2]^=1;target.write_bytes(b)
   with self.assertRaisesRegex(ValueError,'EXACT_PACKET_MEMBER'):verify(copied,require_publication=False)
 def test_report_rebuild_has_no_network_process_or_financial_import(self):
  import builtins
  orig=builtins.__import__
  def guarded(name,*a,**kw):
   if any(n in name for n in ['partial_entry','partial_d','run_partial','perpetual_account','native_runtime','frozen_grid','forecast_monitor']):raise AssertionError('FORBIDDEN_FINANCIAL_IMPORT')
   return orig(name,*a,**kw)
  with patch.object(socket.socket,'connect',side_effect=AssertionError('FORBIDDEN_NETWORK')),patch.object(subprocess,'Popen',side_effect=AssertionError('FORBIDDEN_PROCESS')),patch('builtins.__import__',side_effect=guarded):
   r=build(ROOT);self.assertEqual(len(r['rows']),9);self.assertEqual(len(r['descriptive_period_rows']),27);validate_scope(r['scope'])
 def test_complete_packet_rehash_and_byte_exact_rerender(self):self.assertEqual(verify(ROOT,require_publication=os.environ.get('ALLOW_STAGED_SOURCE')!='1')['status'],'PASS_NINE_PARTIAL2021_COMPACT_SAVED_PACKET')
if __name__=='__main__':unittest.main(verbosity=2)
