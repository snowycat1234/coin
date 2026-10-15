import copy
import json
from pathlib import Path
import tempfile
import unittest
import numpy as np
import comparison as c

class TaxonomyTests(unittest.TestCase):
 def base(self,**changes):
  kw=dict(reviewed=True,terminal=True,completed_minutes=525600,required_minutes=525600,
          nav='11000.00000000000000000001',actual_paid_market_flat=True,
          conditional_settled_flat=False,settlement_count=0,unpaid_liability='0',
          terminal_classification='FULL_CALENDAR_ACTUAL_PAID_MARKET_FLAT')
  kw.update(changes);return c.classify_return(**kw)
 def test_paid_exact_annual(self):
  x=self.base();self.assertEqual(x['comparable_paid_annual_return_fraction'],'0.100000000000000000000001')
  self.assertIsNone(x['conditional_model_annual_return_fraction'])
 def test_conditional_is_distinct(self):
  x=self.base(actual_paid_market_flat=False,conditional_settled_flat=True,settlement_count=2,terminal_classification='FULL_CALENDAR_CONDITIONAL_MODEL_SETTLED_FLAT')
  self.assertEqual(x['return_taxonomy'],'FULL_CALENDAR_CONDITIONAL_MODEL_SETTLED_FLAT')
  self.assertIsNone(x['comparable_paid_annual_return_fraction'])
  self.assertIsNotNone(x['conditional_model_annual_return_fraction'])
 def test_partial_not_annual(self):
  x=self.base(completed_minutes=12345,actual_paid_market_flat=False)
  self.assertEqual(x['return_taxonomy'],'PARTIAL_HALTED_PREFIX_NOT_ANNUAL')
  self.assertIsNone(x['annual_return_fraction']);self.assertIsNotNone(x['partial_prefix_marked_return_fraction'])
 def test_pending_does_not_invent_zero(self):
  for changes in ({'reviewed':False},{'terminal':False}):
   x=self.base(**changes)
   self.assertEqual(x['return_taxonomy'],'PENDING_UNREVIEWED')
   self.assertTrue(all(v is None for k,v in x.items() if k!='return_taxonomy'))
 def test_unresolved_debt_not_paid_annual(self):
  x=self.base(unpaid_liability='0.01')
  self.assertIsNone(x['annual_return_fraction'])
 def test_inconsistent_conditional_not_paid(self):
  x=self.base(settlement_count=1)
  self.assertIsNone(x['comparable_paid_annual_return_fraction'])
 def test_missing_nav_not_zero(self):
  self.assertEqual(self.base(nav=None)['return_taxonomy'],'TERMINAL_INCOMPLETE_EVIDENCE')
 def test_pending_classification_cannot_create_paid_annual(self):
  x=self.base(terminal_classification='PENDING')
  self.assertIsNone(x['comparable_paid_annual_return_fraction'])
 def test_outside_calendar_rejected(self):
  with self.assertRaises(c.EvidenceError):self.base(completed_minutes=525601)

class SignatureTests(unittest.TestCase):
 def audit(self):
  return dict(free_cash='10000',unpaid_liability='0',positions={'BTC':{'quantity':'0.001'}},
              marks={'BTC':'60000'},totals={'fees':'0.033'},
              trades=[{'fill_id':'native1','event_us':12,'decimal_strings':{'quantity':'0.001'}}],
              funding=[{'event_id':'BTC:1','signed_funding_USDT':'-0.1'}],funding_events=1,funding_ids=['BTC:1'],
              scope={'candidate':'STATIC'},fill_requests={'requested':'0.001000000001'})
 def test_only_documented_wrapper_omissions(self):
  a=self.audit();b=copy.deepcopy(a);b['scope']={'candidate':'H090'};b['fill_requests']={'requested':'0.001000000002'}
  self.assertEqual(c.financial_projection_signature(a),c.financial_projection_signature(b))
 def test_full_trade_and_funding_ids_kept(self):
  a=self.audit()
  for key,label in [('trades','fill_id'),('funding','event_id')]:
   b=copy.deepcopy(a);b[key][0][label]+='changed'
   self.assertNotEqual(c.financial_projection_signature(a),c.financial_projection_signature(b))
 def test_exact_decimal_difference_detected(self):
  a=self.audit();b=copy.deepcopy(a);b['free_cash']='10000.00000000000000000001'
  self.assertNotEqual(c.financial_projection_signature(a),c.financial_projection_signature(b))
 def test_missing_projection_field_rejected(self):
  a=self.audit();del a['funding_ids']
  with self.assertRaises(c.EvidenceError):c.financial_projection_signature(a)
 def test_columns_dtype_values_key_order_included(self):
  values=np.array([[1.,2.],[3.,4.]],dtype='float64');cols=np.array(['nav','cash'])
  arrays=[('values',values),('columns',cols)];base=c.native_array_signature(arrays)
  self.assertEqual(base,c.native_array_signature([('values',np.asfortranarray(values)),('columns',cols)]))
  for b in [[('values',values.astype('float32')),('columns',cols)],
            [('values',values),('columns',np.array(['cash','nav']))],list(reversed(arrays))]:
   self.assertNotEqual(base,c.native_array_signature(b))
  changed=values.copy();changed[0,0]=np.nextafter(changed[0,0],2.)
  self.assertNotEqual(base,c.native_array_signature([('values',changed),('columns',cols)]))
 def test_same_stats_not_path_equality(self):
  self.assertFalse(c.validate_duplicate_proof({'status':'SAME_FINAL_NAV','NAV':'11000'},'H','S',{},{}))
 def test_duplicate_requires_every_finance_and_minute_proof(self):
  pins={'CASE_RECEIPT.json':'a','ACCOUNT_FINANCIAL_AUDIT.json':'b','MINUTE.npz':'c'}
  proof={'status':'PASS_EXACT_SAME_REALIZED_FINANCIAL_PATH','cell_id':'H',
         'full37column_minute_matrix_byte_identical':True,
         'same_financial_fields':{k:True for k in c.FINANCIAL_PROJECTION_FIELDS},
         'policy_journals_exact':{'monitor_journal':True,'settlement_journal':True,'transfer_journal':True},
         'source_file_pins':{'some/'+k:v for k,v in pins.items()}}
  self.assertTrue(c.validate_duplicate_proof(proof,'H','S',pins,pins))
  for key in c.FINANCIAL_PROJECTION_FIELDS:
   bad=copy.deepcopy(proof);bad['same_financial_fields'][key]=False
   self.assertFalse(c.validate_duplicate_proof(bad,'H','S',pins,pins))

class TerminalGuardTests(unittest.TestCase):
 def args(self):
  cell={'required_minutes':525600}
  receipt={'status':'FULL_CALENDAR_ACTUAL_PAID_MARKET_FLAT','completed_minutes':525600,'ended_UTC':'2026-10-15T09:00:00Z'}
  finance={'actual_paid_market_flat':True,'conditional_settled_flat':False,'conditional_settlement_rows':0,'exact_financials':{'unpaid_liability':'0'}}
  return receipt,finance,cell
 def test_pending_matching_full_flags_rejected(self):
  r,f,cx=self.args();r['status']='PENDING'
  with self.assertRaises(c.EvidenceError):c.validate_terminal_status(r,f,cx)
 def test_full_classification_with_partial_count_rejected(self):
  r,f,cx=self.args();r['completed_minutes']=42
  with self.assertRaises(c.EvidenceError):c.validate_terminal_status(r,f,cx)
 def test_paid_status_with_conditional_row_rejected(self):
  r,f,cx=self.args();f['conditional_settlement_rows']=1
  with self.assertRaises(c.EvidenceError):c.validate_terminal_status(r,f,cx)
 def test_reviewed_partial_terminal_can_be_reported(self):
  r,f,cx=self.args();r['status']='PARTIAL_HALTED_UNPAID';r['completed_minutes']=42;f['actual_paid_market_flat']=False
  c.validate_terminal_status(r,f,cx)
 def test_finite_nested_risk_numbers_required(self):
  for value in (float('inf'),float('-inf'),float('nan')):
   with self.assertRaises(c.EvidenceError):c.validate_finite_numbers({'nested':[value]})

class EvidenceTests(unittest.TestCase):
 def test_hash_binding_and_path_restriction(self):
  with tempfile.TemporaryDirectory() as t:
   root=Path(t);p=root/'small.json';p.write_text('{"ok":true}')
   ref={'path':'small.json','SHA256':c.file_sha256(p)}
   self.assertEqual(c.bound_json(root,ref)[0],{'ok':True})
   with self.assertRaises(c.EvidenceError):c.bound_json(root,{**ref,'SHA256':'0'*64})
   with self.assertRaises(c.EvidenceError):c.bound_json(root,{**ref,'path':'../small.json'})
 def test_pending_metrics_are_null(self):
  row=c.pending_row(dict(cell_id='2023_X_LOW',year=2023,strategy='X',tier='LOW',config='X_LOW',required_minutes=525600))
  self.assertTrue(all(row[k] is None for k in c.METRIC_KEYS))
  self.assertIsNone(row['comparable_paid_annual_return_fraction'])

if __name__=='__main__':unittest.main(verbosity=2)
