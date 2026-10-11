import unittest
import numpy as np
import pandas as pd
from primitives import measure
from run_phase import budget


class PrimitiveTests(unittest.TestCase):
    def test_acquisition_budget_refuses_before_download(self):
        budget(51063650,35000000)
        with self.assertRaises(ValueError):budget(70000001,30000000)
        with self.assertRaises(ValueError):budget(0,35000001)

    def frame(self):
        n=3*1440;t=np.arange(n,dtype=np.int64)*60000
        close=np.exp(np.cumsum(np.sin(np.arange(n)*.23)*.001))
        return pd.DataFrame(dict(timestamp_ms=t,open=close,high=close*1.001,low=close*.999,close=close,
            volume=np.ones(n),quote_volume=np.ones(n),trades=np.ones(n)))

    def test_true_boundary_and_unknown_preserved(self):
        f=self.frame();a,t,_=measure(f,None);b,_,_=measure(f,1.)
        self.assertTrue(np.isnan(a['RV_1m'][0]) and np.isnan(a['RSplus_5m'][0]))
        self.assertTrue(np.isnan(a['max_log_up'][0]))
        np.testing.assert_array_equal(a['RV_1m'][1:],b['RV_1m'][1:])
        np.testing.assert_array_equal(t,np.array([1,2,3])*86400000000)
        for k in ('1m','5m'):
            np.testing.assert_allclose(b['RV_'+k],b['RSplus_'+k]+b['RSminus_'+k],rtol=1e-14)

    def test_future_suffix_does_not_change_past(self):
        f=self.frame();a,_,_=measure(f,1.)
        changed=f.copy();changed.loc[2880:,['open','high','low','close']]*=2
        b,_,_=measure(changed,1.)
        for k in a:
            np.testing.assert_array_equal(a[k][:2],b[k][:2])
        with self.assertRaises(ValueError):
            measure(f.drop(index=1500),1.)


if __name__=='__main__':
    unittest.main()
