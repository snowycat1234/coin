import unittest
import numpy as np
from tail import DAY,summarize,feature,fit_quantile,calibrate,downsize


class TailTests(unittest.TestCase):
    def test_suffix_and_initial_unknown(self):
        t=np.arange(300000000,72*DAY+300000000,300000000,dtype=np.int64)
        r=np.sin(np.arange(len(t))*.13)*.0005+.00001
        p=np.exp(np.cumsum(r))[:,None]*np.array([20000,1500,30,.5,.06])
        a=summarize(p,t)
        other=p.copy();other[45*288:]*=np.exp(np.linspace(0,1,len(other)-45*288))[:,None]
        b=summarize(other,t)
        self.assertTrue(np.isnan(a['RV'][0]).all())
        self.assertTrue(np.isnan(a['excursion'][0]).all())
        for i in range(30,45):
            for x,y in zip(feature(a,i),feature(b,i)):
                np.testing.assert_array_equal(x,y)
        with self.assertRaises(ValueError):
            summarize(p,t,('ETHUSDT','BTCUSDT','SOLUSDT','XRPUSDT','DOGEUSDT'))

    def test_immature_fails_before_solver(self):
        p={'available':np.arange(400,dtype=np.int64)*DAY}
        with self.assertRaises(ValueError):
            calibrate(p,np.arange(31,242),241*DAY)

    def test_lp_certificates_three_synthetic_calls(self):
        y=np.arange(1,11,dtype=float)
        for q in (.1,.5,.9):
            m=fit_quantile(np.ones((10,1)),y,q)
            self.assertGreaterEqual(m['coefficients'][0],q*10-1e-7)
            self.assertLessEqual(m['coefficients'][0],q*10+1+1e-7)
            self.assertLess(m['objective_error'],1e-7)

    def test_hedge_removal_rechecks_covariance(self):
        r=np.sin(np.arange(30))[:,None]*np.ones((1,5))*.15
        base=np.array([.2,-.2,0,0,0])
        w,_=downsize(base,np.zeros(5),r)
        self.assertLess(w[0],base[0])
        self.assertEqual(w[1],0)
        self.assertLessEqual(float(np.sqrt(w@(np.cov(r,rowvar=False)*365)@w)),.1+1e-12)


if __name__=='__main__':
    unittest.main()
