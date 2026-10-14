import unittest,json,tempfile
from pathlib import Path
from unittest.mock import patch
import numpy as np
import bindings as B
from project_inputs import project_generated_or_admitted,source_only

class PreparationTests(unittest.TestCase):
 def generated(self):
  t=np.arange(250,dtype=np.int64)*B.DAY;k=np.arange(250)[:,None];j=np.arange(5)[None,:]
  return t,(100+k*.02+2*np.sin(k*.07+j)).astype(np.float64),t[207:]

 def test_projection_exact_original_current31_np_covariance(self):
  t,p,d=self.generated();r=project_generated_or_admitted(t,p,d)
  expected=np.stack([np.cov(np.diff(p[k-30:k+1],axis=0)/p[k-30:k],rowvar=False,ddof=1)*365 for k in range(207,250)])
  self.assertEqual(expected.tobytes(),r['covariance'].tobytes());self.assertTrue(r['original_daily_admission'].all())

 def test_future_closes_do_not_change_past_covariance_or_masks(self):
  t,p,d=self.generated();a=project_generated_or_admitted(t,p,d[:4]);p[211:]*=4
  b=project_generated_or_admitted(t,p,d[:4]);self.assertEqual(a['covariance'].tobytes(),b['covariance'].tobytes())

 def test_projection_missing_or_future_current_close_fails(self):
  t,p,d=self.generated()
  for bad in (d+1,t[:2]):
   with self.assertRaises(ValueError):project_generated_or_admitted(t,p,bad)

 def test_boolean_float_or_clock_schema_refused(self):
  t,p,d=self.generated()
  for a,b,c in ((t.astype(float),p,d),(t,p.astype(bool),d),(t,p,d.astype(float))):
   with self.assertRaises(ValueError):project_generated_or_admitted(a,b,c)

 def test_warmup_mask_does_not_turn_invalid_source_into_saved_target(self):
  t,p,d=self.generated();p[30,0]=np.nan
  r=project_generated_or_admitted(t,p,d[:1]);self.assertFalse(r['original_daily_admission'][0])

 def test_weekly_owner_prefix_preserved_before_year_start(self):
  t,p,d=self.generated();r=project_generated_or_admitted(t,p,d[:1]+B.DAY)
  self.assertLess(r['owning_rank_us'][0],r['decision_us'][0]);self.assertTrue(r['owning_rank_source_known'][0])

 def test_no_source_GO_prevents_even_array_hash(self):
  with patch.object(np,'load',side_effect=AssertionError('ARRAY_OPEN')),patch.object(B,'check',side_effect=AssertionError('FILE_HASH')):
   with self.assertRaisesRegex(ValueError,'GO_REQUIRED'):source_only({},2023,None,None)

 def test_no_case_GO_prevents_runtime_or_original26_target_hash(self):
  with patch.object(B,'check',side_effect=AssertionError('FILE_HASH')):
   with self.assertRaisesRegex(ValueError,'GO_REQUIRED'):B.load_runtime(None,None,2023,'GRID')

 def test_closed_years_and_lagged_field_GO_rejected(self):
  for year in (2021,2022,2026):
   with tempfile.TemporaryDirectory() as td:
    path=Path(td)/'GO.json';path.write_text(json.dumps(dict(schema='EXPLICIT_ORIGINAL_CSH_GRID_SOURCE_OR_CASE_GO_V1',parent_GO=True,action='SOURCE_ONLY_ORIGINAL_PROJECTION',year=year,target_field='PRICE_ONLY_CSH',rank_feature_lag_hours=24,native_adapter_SHA256=B.ADAPTER_SHA,input_manifest_SHA256=B.sha(B.HERE/'INPUT_MANIFEST.json'))))
    with self.assertRaisesRegex(ValueError,'EXACT_ORIGINAL'):B.require_go(path,B.sha(path),'SOURCE_ONLY_ORIGINAL_PROJECTION',year)

 def test_strict_parent_boolean_and_wrong_scope(self):
  for value in (1,'True',False):
   with tempfile.TemporaryDirectory() as td:
    p=Path(td)/'GO.json';p.write_text(json.dumps(dict(parent_GO=value)))
    with self.assertRaises(ValueError):B.require_go(p,B.sha(p),'SOURCE_ONLY_ORIGINAL_PROJECTION',2023)

 def test_metadata_has_exact_unlagged_and_excludes_lagcontrol(self):
  m=B.metadata_manifest();self.assertEqual(m['feature_lag_hours'],0)
  self.assertIn('PRICE_ONLY_CSH',m['excluded_target_fields']);self.assertIn('FUNDING_ADJUSTED_CSH',m['excluded_target_fields'])
  for y in ('2023','2024','2025'):self.assertEqual(m['years'][y]['target_field'],'STATIC50')

if __name__=='__main__':unittest.main()
