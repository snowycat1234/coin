import unittest
import numpy as np
import verify_recovered_2023_source as v

class TestSourceSchema(unittest.TestCase):
    def fixture(self):
        symbols=('BTCUSDT','ETHUSDT','SOLUSDT','XRPUSDT','DOGEUSDT')
        a={'times':np.array([0,v.MINUTE],dtype=np.int64)}
        a.update({s+'_'+k:np.ones(2,dtype=np.float64) for s in symbols for k in ('open','close','quote_volume','mark')})
        return a,symbols
    def test_valid(self):
        a,s=self.fixture();v.check_month(a,s,0,2)
    def test_missing_field(self):
        a,s=self.fixture();del a['BTCUSDT_mark']
        with self.assertRaises(ValueError):v.check_month(a,s,0,2)
    def test_bad_clock(self):
        a,s=self.fixture();a['times'][1]+=1
        with self.assertRaises(ValueError):v.check_month(a,s,0,2)
    def test_nonfinite(self):
        a,s=self.fixture();a['ETHUSDT_open'][0]=np.nan
        with self.assertRaises(ValueError):v.check_month(a,s,0,2)
    def test_wrong_dtype(self):
        a,s=self.fixture();a['SOLUSDT_close']=np.ones(2,dtype=np.float32)
        with self.assertRaises(ValueError):v.check_month(a,s,0,2)

if __name__=='__main__':unittest.main()
