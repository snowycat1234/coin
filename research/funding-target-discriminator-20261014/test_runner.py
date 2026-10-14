"""Tiny launch/reporting/rank-lag synthetics, never historical candidate targets."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import numpy as np
import run_targets
from target_core import DAY,ANCHOR,context
from test_target_core import fixture
from inputs import frozen_funding_provider
from core import EventStream


class RunnerTests(unittest.TestCase):
    def test_plain_JSON_numpy_count_and_boolean(self):
        result=json.loads(json.dumps(run_targets.clean({'count':np.int64(4),'ready':np.bool_(True),'score':np.float64(.001)}),allow_nan=False))
        self.assertEqual(result,{'count':4,'ready':True,'score':.001})

    def test_missing_parent_GO_never_calls_source_loader(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);(root/'PREPARATION_MANIFEST.json').write_text('{"files":{}}')
            go=root/'go.json';go.write_text('{"action":"WRONG"}')
            with patch.object(run_targets,'HERE',root),patch.object(run_targets,'load') as loader:
                with self.assertRaises(AssertionError):run_targets.run(go,root/'out')
                loader.assert_not_called()
            self.assertFalse((root/'out').exists())

    def test_existing_attempt_failure_sentinel_is_never_overwritten(self):
        with tempfile.TemporaryDirectory() as temp:
            out=Path(temp);p=out/'ATTEMPT_FAILURE.json';p.write_text('SENTINEL')
            run_targets.preserve_failure(out,True,ValueError('rejected retry'))
            self.assertEqual(p.read_text(),'SENTINEL')

    def test_only_price_rank_window_lags_and_rates_sum_once(self):
        t,p,d,h,m=fixture(ANCHOR,8);at=int(d[0]);hours=3_600_000_000
        times=np.arange(at-23*DAY,at+DAY,8*hours,dtype=np.int64)
        certificates={day:times[(times>=day)&(times<day+DAY)].tolist() for day in range(at-23*DAY,at+DAY,DAY)}
        streams=[EventStream(times,np.full(len(times),.0001*(a+1)),np.full(len(times),8.),certificates) for a in range(5)]
        valid,returns,price,k=context(t,p,at)
        scores,known,proof=frozen_funding_provider(t,p,streams)(at,valid,price)
        self.assertTrue(known);np.testing.assert_array_equal(scores['PRICE_ONLY'],p[k-1]/p[k-22]-1.)
        np.testing.assert_allclose(scores['FUNDING_ADJUSTED'],scores['PRICE_ONLY']-np.arange(1,6)*.0063,rtol=0,atol=1e-14)
        self.assertEqual(proof['interval_us'],[at-22*DAY,at-DAY])
        np.testing.assert_array_equal(returns,np.diff(p[k-30:k+1],axis=0)/p[k-30:k])
        altered=[]
        for s in streams:
            r=s.rates.copy();r[s.times>=at-DAY]=1e6
            altered.append(EventStream(s.times,r,s.hours,s.complete_day_event_ids))
        other,known2,_=frozen_funding_provider(t,p,altered)(at,valid,price)
        self.assertTrue(known2);np.testing.assert_array_equal(other['FUNDING_ADJUSTED'],scores['FUNDING_ADJUSTED'])


if __name__=='__main__':unittest.main(verbosity=2)
