import unittest,copy
from diagnostic import score,selected_rows,analyze
class TestDiagnostic(unittest.TestCase):
 def test_correct(self):
  s=score([1,2,3],[0,2,4],[True]*3,['a','b','c']);self.assertEqual(s['chosen_utility'],4);self.assertEqual(s['pairwise_accuracy'],1)
 def test_reverse(self): self.assertEqual(score([3,2,1],[0,2,4],[True]*3,['a','b','c'])['pairwise_accuracy'],0)
 def test_forecast_tie(self):
  s=score([1,1],[0,2],[True]*2,['a','b']);self.assertEqual(s['chosen_utility'],1);self.assertEqual(s['pairwise_accuracy'],.5)
 def test_actual_tie(self):
  s=score([1,2],[0,0],[True]*2,['a','b']);self.assertIsNone(s['pairwise_accuracy']);self.assertEqual(s['actual_ties_excluded'],1)
 def test_mask(self):self.assertEqual(score([1,9],[2,float('nan')],[True,False],['a','b'])['chosen'],['a'])
 def test_nonfinite(self):
  with self.assertRaises(ValueError):score([float('nan')],[1],[True],['a'])
 def test_empty(self):
  with self.assertRaises(ValueError):score([1],[1],[False],['a'])
 def test_gaps(self):
  r=[dict(decision_us=i,label_available_us=i+7,usable=True) for i in [0,1,7,8,16]];self.assertEqual([x['decision_us'] for x in selected_rows(r)],[0,8,16])
 def test_unusable(self):
  r=[dict(decision_us=i,label_available_us=i+7,usable=i!=0) for i in [0,1,8,9]];self.assertEqual([x['decision_us'] for x in selected_rows(r)],[1,9])
 def test_single_cash(self): self.assertEqual(score([0],[0],[True],['CASH'])['oracle_regret'],0)
 def test_negative_opportunity(self):self.assertEqual(score([0,1],[0,-1],[True]*2,['CASH','a'])['oracle_regret'],1)
 def test_tie_exact_not_tolerance(self):self.assertEqual(score([1,1+1e-12],[0,2],[True]*2,['a','b'])['chosen'],['b'])
class TestClockGuards(unittest.TestCase):
 def fixture(self):
  d=1000000000000;end=d+7*86400000000+120000001
  r=dict(date='fixture',decision_us=d,label_available_us=end,eligible=[True,True],utility=[0,.1],prediction_state=[0,1],prediction_market=[1,0],usable=True,reasons=[],state_and_market_fit_available_us=[d,d],market_feature_available_us=d,latest_target_available_us=d,latest_state_feedback_available_us=d-1)
  return dict(experts=['CASH','A'],rows=[r],evaluation_label_availability_cutoff_us=end)
 def test_valid_analysis(self):
  r=analyze(self.fixture());self.assertEqual(r['paired']['mean_market_minus_state_utility'],-.1)
 def test_all_actual_utilities_tied(self):
  x=self.fixture();x['rows'][0]['utility']=[0,0]
  r=analyze(x)
  self.assertIsNone(r['models']['state']['mean_block_pairwise_accuracy'])
  self.assertIsNone(r['models']['market']['pooled_pairwise_accuracy'])
 def test_only_cash_analysis(self):
  x=self.fixture();x['rows'][0]['eligible']=[True,False]
  r=analyze(x)
  self.assertIsNone(r['models']['state']['mean_block_pairwise_accuracy'])
  self.assertEqual(r['models']['market']['mean_chosen_utility'],0)
 def test_late_fit(self):
  x=self.fixture();x['rows'][0]['state_and_market_fit_available_us'][0]+=1
  with self.assertRaises(ValueError):analyze(x)
 def test_future_target(self):
  x=self.fixture();x['rows'][0]['latest_target_available_us']+=1
  with self.assertRaises(ValueError):analyze(x)
 def test_current_feedback(self):
  x=self.fixture();x['rows'][0]['latest_state_feedback_available_us']+=1
  with self.assertRaises(ValueError):analyze(x)
 def test_unmature_label(self):
  x=self.fixture();x['evaluation_label_availability_cutoff_us']-=1
  with self.assertRaises(ValueError):analyze(x)
 def test_wrong_maturity(self):
  x=self.fixture();x['rows'][0]['label_available_us']-=1
  with self.assertRaises(ValueError):analyze(x)
 def test_future_market(self):
  x=self.fixture();x['rows'][0]['market_feature_available_us']+=1
  with self.assertRaises(ValueError):analyze(x)
 def test_nonchronological(self):
  x=self.fixture();x['rows'].append(copy.deepcopy(x['rows'][0]))
  with self.assertRaises(ValueError):analyze(x)
if __name__=='__main__':unittest.main()
