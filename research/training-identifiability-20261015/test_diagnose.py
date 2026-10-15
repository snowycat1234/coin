import copy,json,unittest
from pathlib import Path
import numpy as np
from diagnose import diagnose
F=json.loads((Path(__file__).parent/'training_fixture.json').read_text())
class Checks(unittest.TestCase):
 def test_scope_shape_and_rows(self):
  self.assertEqual(set(F),{'source_commit','experts','feature_names','training','coefficients'})
  r=diagnose(F); self.assertEqual(r['shape'],[40,60]);self.assertEqual([v['date'] for v in r['dates']],[v['date'] for v in F['training']]);self.assertEqual(len(set(v['date'] for v in F['training'])),40)
 def test_rank_leverage_variance(self):
  r=diagnose(F);self.assertEqual(r['numerical_rank'],39);self.assertAlmostEqual(sum(v['centered_row_leverage'] for v in r['dates']),r['centered_rank']);self.assertEqual(r['components_for_variance'],{'0.5':3,'0.8':8,'0.95':16})
 def test_exact_ties_keep_all_choices(self):
  f=copy.deepcopy(F); f['coefficients']['theta']=np.zeros((5,61)).tolist();r=diagnose(f)
  self.assertEqual(r['summary']['top_tie_dates'],40)
  for old,new in zip(f['training'],r['dates']):
   self.assertEqual(len(new['top_choices']),sum(old['eligible']));self.assertAlmostEqual(new['chosen_utility_tie_average'],np.mean(np.asarray(old['utility'])[old['eligible']]));self.assertEqual(new['top_runner_margin'],0);self.assertEqual(new['top_runner_standardized_l2_boundary_distance'],0)
 def test_analytic_boundary(self):
  c=F['coefficients'];sc=c['scaler'];x=np.array([r['x'] for r in F['training']]);z=(x-sc['mean'])/sc['scale'];z[:,sc['zero']]=0;constant=np.ptp(x,axis=0)==0;t=np.vstack([np.zeros(61),c['theta']]);r=diagnose(F)
  for i,row in enumerate(r['dates']):
   a=F['experts'].index(row['top_choices'][0]);b=F['experts'].index(row['runner_up']);w=t[a,:60]-t[b,:60];w[constant]=0;step=-row['top_runner_margin']*w/(w@w)
   self.assertAlmostEqual(np.linalg.norm(step),row['top_runner_standardized_l2_boundary_distance']);self.assertAlmostEqual((z[i]+step)@(t[a,:60]-t[b,:60])+t[a,60]-t[b,60],0,places=12)
 def test_cash_decomposition(self):
  for r in diagnose(F)['dates']:
   self.assertAlmostEqual(r['oracle_regret'],r['uncaptured_positive_utility_above_cash']+r['chosen_shortfall_below_cash'])
if __name__=='__main__':unittest.main(verbosity=2)
