import copy,json,unittest
from pathlib import Path
import numpy as np
import ranker
P=Path(__file__).parent
class DenseValidation(unittest.TestCase):
 def setUp(self):self.d=json.loads((P/'derived_inputs.json').read_text())
 def test_dense_overlap_accepted(self):
  ranker.validate(self.d)
  self.assertTrue(any(b['decision_us']<=a['label_available_us'] for a,b in zip(self.d['training'],self.d['training'][1:])))
 def test_strict_label_cutoff(self):
  self.d['training_cutoff_us']=self.d['training'][-1]['label_available_us']
  with self.assertRaises((ValueError,AssertionError)):ranker.validate(self.d)
 def test_original40_identity(self):
  self.d['training'][0]['x'][11]+=1
  with self.assertRaises(AssertionError):ranker.validate(self.d)
 def test_evaluation_identity(self):
  self.d['evaluation'][10]['prediction_state'][1]+=1
  with self.assertRaises(AssertionError):ranker.validate(self.d)
 def test_no_evaluation_leak(self):
  self.d['training'][-1]=copy.deepcopy(self.d['evaluation'][0])
  with self.assertRaises((ValueError,AssertionError)):ranker.validate(self.d)
 def test_duplicates_rejected(self):
  self.d['training'][1]=self.d['training'][0]
  with self.assertRaises(AssertionError):ranker.validate(self.d)
 def test_train_scaler_only(self):
  sc=ranker.scaler_fit([r['x'] for r in self.d['training']])
  self.d['evaluation'][0]['x']=[1e10]*60
  self.assertEqual(sc,ranker.scaler_fit([r['x'] for r in self.d['training']]))
  np.testing.assert_array_equal(sc['mean'],np.array([r['x'] for r in self.d['training']]).mean(axis=0))
 def test_fixed_cash_original_mean(self):
  old=json.loads((P/'original40_inputs.json').read_text())
  self.assertEqual(self.d['original_40_training_mean_utility'],old['training_mean_utility'])
  self.assertEqual(old['train_best'],'CASH')
if __name__=='__main__':unittest.main()
