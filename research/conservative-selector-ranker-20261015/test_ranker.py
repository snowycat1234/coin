"""Synthetic tests only; run before the one actual data fit."""
import unittest
import numpy as np
from scipy.optimize._numdiff import approx_derivative
from ranker import *

class TestRanker(unittest.TestCase):
 def synthetic(self):
  x=np.array([[1.,2.,1.],[-2.,.4,1.],[.2,-.5,1.]])
  y=np.array([[0.,2.,-1.],[0.,-.5,-2.],[0.,0.,0.]])
  return x,y,np.ones_like(y,dtype=bool)
 def test_analytic_gradient(self):
  x,y,m=self.synthetic();a,w,_=pair_design(x,y,m,0);theta=np.linspace(-.3,.2,6)
  numeric=approx_derivative(lambda t:objective(t,a,w)[0],theta,method='3-point').ravel()
  np.testing.assert_allclose(objective(theta,a,w)[1],numeric,atol=1e-9,rtol=1e-8)
 def test_pair_masks(self):
  x,y,m=self.synthetic();m[0,1]=False;a,w,c=pair_design(x,y,m,0);self.assertEqual(c,[1,3,0]);self.assertEqual(len(w),4)
  np.testing.assert_equal(a[0,:3],0)
 def test_exact_ties(self):
  a,w,c=pair_design([[1]],[[0,0,1e-15]],[[True]*3],0);self.assertEqual(c,[2])
 def test_equal_date_weight(self):
  x=np.ones((2,1));y=np.array([[0,0,1],[0,1,2]]);a,w,c=pair_design(x,y,np.ones_like(y,bool),0)
  self.assertEqual(c,[2,3]);self.assertAlmostEqual(sum(w[:2]),.5);self.assertAlmostEqual(sum(w[2:]),.5)
 def test_zero_pair_date_kept(self):
  x,y,m=self.synthetic();a,w,c=pair_design(x,y,m,0)
  self.assertAlmostEqual(w.sum(),2/3);self.assertAlmostEqual(objective(np.zeros(6),a,w)[0],2*np.log(2)/3)
 def test_all_tied_dates(self):
  a,w,c=pair_design(np.ones((2,2)),np.zeros((2,3)),np.ones((2,3),bool),0);t=np.arange(4.)
  f,g=objective(t,a,w);self.assertEqual(f,.5*(t@t));np.testing.assert_equal(g,t)
 def test_cash_anchor(self):
  p=predict(np.ones((4,3)),np.arange(6).reshape(2,3),1,3);np.testing.assert_equal(p[:,1],0);np.testing.assert_equal(p[0],[3,0,12])
 def test_intercept_penalized(self):
  a=np.zeros((0,6));w=np.zeros(0);t=np.array([0,0,2,0,0,-3.]);f,g=objective(t,a,w)
  self.assertEqual(f,6.5);np.testing.assert_equal(g,t)
 def test_scaler_train_only(self):
  train=np.array([[1,3],[3,3]],float);sc=scaler_fit(train);z=transform([[100,999]],sc)
  np.testing.assert_equal(sc['mean'],[2,3]);np.testing.assert_equal(sc['scale'],[1,1]);np.testing.assert_equal(z,[[98,0,1]])
  self.assertEqual(sc,scaler_fit(train))
 def test_causal_clocks(self):
  r=dict(decision_us=100,latest_target_available_us=100,latest_state_feedback_available_us=99,label_available_us=100+7*86400000000+120000001);clocks(r)
  for field,value in [('latest_target_available_us',101),('latest_state_feedback_available_us',100),('label_available_us',101)]:
   with self.assertRaises(ValueError):clocks(dict(r,**{field:value}))
  with self.assertRaises(ValueError):clocks(r,r['label_available_us'])
  clocks(r,r['label_available_us']+1)
 def test_optimizer_determinism(self):
  x,y,m=self.synthetic();a,w,c=pair_design(x,y,m,0);a1=optimize(a,w);a2=optimize(a,w)
  self.assertTrue(a1.success and a2.success);np.testing.assert_equal(a1.x,a2.x);self.assertLessEqual(max(abs(a1.jac)),1e-6)
 def test_finite_large_margins(self):
  a=np.eye(2);w=np.ones(2)/2;f,g=objective(np.array([1000.,-1000.]),a,w);self.assertTrue(np.isfinite(f));self.assertTrue(np.isfinite(g).all())
 def test_argmax_ties(self):
  s=score([1,1,0],[2,-1,0],[True]*3,['a','b','CASH']);self.assertEqual(s['chosen'],['a','b']);self.assertEqual(s['chosen_utility'],.5);self.assertEqual(s['pairwise_correct_equivalent'],1.5)
 def test_numpy_score_json_serialization(self):
  json.dumps(score(np.array([0.,1.,1.]),[0.,1.,2.],[True]*3,['CASH','a','b']),allow_nan=False)
 def test_pairwise_manual_objective(self):
  x,y,m=self.synthetic();a,w,c=pair_design(x,y,m,0);t=np.linspace(-.3,.2,6);p=predict(x,t.reshape(2,3),0,3);value=0
  for d in range(len(y)):
   losses=[np.logaddexp(0,-np.sign(y[d,i]-y[d,j])*(p[d,i]-p[d,j])) for i,j in combinations(range(3),2) if y[d,i]!=y[d,j]]
   value+=(np.mean(losses) if losses else 0)/len(y)
  self.assertAlmostEqual(objective(t,a,w)[0],value+.5*(t@t),places=14)

if __name__=='__main__':unittest.main()
