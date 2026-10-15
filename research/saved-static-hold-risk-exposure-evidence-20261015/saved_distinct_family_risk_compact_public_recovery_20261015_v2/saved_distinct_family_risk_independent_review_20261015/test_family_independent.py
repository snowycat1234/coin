import copy
import importlib.util
import json
from pathlib import Path
import unittest
import numpy as np
R=Path(__file__).resolve().parent.parent
spec=importlib.util.spec_from_file_location('review_family_module',R/'saved_distinct_family_risk_evidence_20261015/saved_family_risk.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)

class FamilyIndependentTests(unittest.TestCase):
 def minute(self):
  n=1440*4;a=np.zeros((n,37),dtype=np.float64);i=np.arange(n)
  a[:,0]=10001+20*np.sin(i/140)+i/5
  a[:,1]=a[:,0]-100;a[:,2]=100
  a[:,29]=np.where(i%3,.1,-.03);a[:,30]=-.02
  a[:,34]=np.abs(a[:,29:34]).sum(1);a[:,35]=a[:,29:34].sum(1)
  a[:,9]=np.where(i%5,1e-300,0);a[:,36]=(i+1)*m.MINUTE_US
  a[:,5]=i*.001;a[:,6]=i*.002;a[:,7]=-i*.0002;a[:,8]=i*3
  return a,np.array(m.COLUMN_NAMES)
 def test_daily_initial_denominator_and_exact_endpoint(self):
  a,c=self.minute();d,cols=m.daily_telemetry(a,c);got={x:d[:,i] for i,x in enumerate(cols)}
  nav=a[1439::1440,0];expected=np.array([nav[0]/10000-1]+[nav[i]/nav[i-1]-1 for i in range(1,4)])
  np.testing.assert_array_equal(got['daily_simple_return'],expected)
  self.assertNotEqual(expected[0],nav[0]/a[0,0]-1)
  self.assertEqual(got['daily_change_signed_funding_USDT'][0],a[1439,7])
 def test_aggregate_frozen_daily_vol_MDD_and_actual_exposure(self):
  a,c=self.minute();d,cols=m.daily_telemetry(a,c);out=m.aggregate_daily(d,cols)
  daily=a[1439::1440,0];r=daily/np.r_[10000.,daily[:-1]]-1;curve=np.r_[10000.,daily]
  self.assertEqual(out['daily_realized_annual_volatility'],float(np.std(r,ddof=1)*np.sqrt(365)))
  self.assertEqual(out['daily_close_MDD_fraction'],float(np.max(1-curve/np.maximum.accumulate(curve))))
  self.assertAlmostEqual(out['gross_weight_mean'],float(a[:,34].mean()),places=14)
  self.assertAlmostEqual(out['net_signed_weight_mean'],float(a[:,35].mean()),places=14)
  self.assertEqual(out['flat_actual_quantity_minutes'],int(np.all(a[:,9:14]==0,axis=1).sum()))
  self.assertAlmostEqual(out['asset_weights']['BTCUSDT']['signed_mean'],float(a[:,29].mean()),places=14)
 def test_column_permutation_minute_gap_nonfinite_projection_rejected(self):
  a,c=self.minute()
  for mutation in ('permutation','clock','projection','nan'):
   b=a.copy();cc=c.copy()
   if mutation=='permutation':cc[[0,1]]=cc[[1,0]]
   if mutation=='clock':b[100,36]+=m.MINUTE_US
   if mutation=='projection':b[100,34]+=1e-10
   if mutation=='nan':b[100,29]=np.nan
   with self.subTest(mutation=mutation),self.assertRaises(m.EvidenceError):m.validate_minute(b,cc,(0,len(a)*m.MINUTE_US),len(a))
 def test_funding_exact_cost_sign_and_future_denominator(self):
  self.assertEqual(m.cost_diagnostic('1.100','2.200','-3.300')['same_quantity_fee_execution_less_signed_funding_USDT'],'6.600')
  self.assertEqual(m.cost_diagnostic('1.100','2.200','3.300')['same_quantity_fee_execution_less_signed_funding_USDT'],'0.000')
  self.assertEqual(m.ratio_diagnostic('0.15',.3),'0.5');self.assertIsNone(m.ratio_diagnostic('0.15',0))
  self.assertEqual(m.exact_annual_return('10000.00000000000000000001'),'1E-24')
 def test_canonical_output_hash_bit_dtype_order(self):
  a,c=self.minute();base=m.canonical_array_signature(a,c,['values','columns'])
  changed=a.copy();changed[0,0]=np.nextafter(changed[0,0],np.inf)
  self.assertNotEqual(base['values_C_order_SHA256'],m.canonical_array_signature(changed,c)['values_C_order_SHA256'])
  reverse=m.canonical_array_signature(a,c,['columns','values'])
  self.assertNotEqual(base['original_archive_descriptor_SHA256'],reverse['original_archive_descriptor_SHA256'])
  self.assertEqual(base['values_C_order_SHA256'],m.canonical_array_signature(np.asfortranarray(a),c)['values_C_order_SHA256'])
 def test_leap_year_and_no_partial_tail(self):
  self.assertEqual((m.CALENDARS[2024][1]-m.CALENDARS[2024][0])//m.MINUTE_US,527040)
  a,c=self.minute()
  with self.assertRaises(m.EvidenceError):m.daily_telemetry(a[:-1],c)
  d,cols=m.daily_telemetry(a,c);d[2,0]+=1
  with self.assertRaises(m.EvidenceError):m.aggregate_daily(d,cols)
 def test_pair_arithmetic_excludes_conditional(self):
  cells=[]
  for year in (2023,2024):
   for tier in ('LOW','MID','HIGH'):
    for family,ret in [('STATIC50','0.10000000000000000001'),('VOL_MANAGED_HOLD','0.20000000000000000003')]:
     cells.append({'year':year,'tier':tier,'strategy':family,'cell_id':f'{year}_{family}_{tier}','native_exact_paid_annual_return_fraction':ret,'saved_float64_aggregate':{'daily_realized_annual_volatility':.1,'gross_weight_mean':.2},'all_observation_native_MDD_fraction':.03})
  p=m.paired_rows(cells);self.assertEqual(len(p),6);self.assertEqual(p[0]['HOLD_minus_STATIC_paid_return_fraction'],'0.10000000000000000002')
  cells[1]['native_exact_paid_annual_return_fraction']=None;p=m.paired_rows(cells);self.assertIsNone(p[0]['HOLD_minus_STATIC_paid_return_fraction'])
  self.assertEqual(p[0]['gap_status'],'NOT_COMPARABLE_PAID_ANNUAL')

if __name__=='__main__':unittest.main(verbosity=2)
