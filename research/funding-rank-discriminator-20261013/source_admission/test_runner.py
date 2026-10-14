"""Synthetic runner checks only; never load/evaluate historical baskets."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from types import SimpleNamespace
import numpy as np
import run_baskets
from test_core import fixture
from core import score_at


class RunnerTests(unittest.TestCase):
    def test_independent_decimal_baskets_and_prefix_on_synthetic(self):
        d,t,p,m,e=fixture()
        r=score_at(t,p,m,e,d)
        proof=run_baskets.independent_check(t,p,m,e,d,r)
        self.assertEqual(proof['status'],'PASS_DIRECT_DECIMAL_EVENT_SUM_STABLE_BASKET_AND_CAUSAL_PREFIX')
        self.assertEqual(proof['checked_actual_event_counts'],[63]*5)

    def test_wrong_parent_action_cannot_reach_source_loader(self):
        with tempfile.TemporaryDirectory() as root:
            here=Path(root);(here/'FINAL_SOURCE_MANIFEST.json').write_text('{"files":{}}')
            go=here/'go.json';go.write_text(json.dumps({'action':'NOT_AUTHORIZED'}))
            with patch.object(run_baskets,'HERE',here),patch.object(run_baskets,'load',side_effect=AssertionError('SOURCE_LOADER_MUST_NOT_RUN')) as source:
                with self.assertRaises(AssertionError):run_baskets.run(go,here/'out')
                source.assert_not_called()
            self.assertFalse((here/'out').exists())

    def test_nonfinite_reporting_and_independent_stable_ties(self):
        self.assertEqual(run_baskets.clean(np.array([1.,np.nan,np.inf])),[1.,None,None])
        self.assertEqual(run_baskets.independent_basket([0,1,1,1,2],True),[-.15,-.15,0.,.15,.15])
        self.assertEqual(run_baskets.independent_basket([1]*5,True),[0.]*5)

    def test_missing_active_ownership_context_prevents_noop(self):
        ready={'status':'READY_PAIRED_BASKETS','original_admission_cash':False,'paired_basket_changed':False}
        missing={'status':'NOT_READY_PAIRED_BASKETS','original_admission_cash':False,'paired_basket_changed':False}
        self.assertEqual(run_baskets.scope_conclusion([ready],[missing]),'INCONCLUSIVE_SOURCE_NOT_READY')
        inactive=dict(missing,original_admission_cash=True)
        self.assertEqual(run_baskets.scope_conclusion([ready],[inactive]),'STOP_FUNDING_BASKET_NOOP_ON_ADMITTED_ORIGINAL_SUPPORT_CONDITIONAL')
        changed=dict(ready,paired_basket_changed=True)
        self.assertEqual(run_baskets.scope_conclusion([ready],[changed]),'FEATURE_CHANGES_BASKETS_CONDITIONAL')

    def test_runtime_wall_and_RSS_stops(self):
        with patch.object(run_baskets.time,'monotonic',return_value=121):
            with self.assertRaisesRegex(AssertionError,'WALL_TIME_STOP'):run_baskets.runtime_guard(0)
        with patch.object(run_baskets.time,'monotonic',return_value=1),patch.object(run_baskets.resource,'getrusage',return_value=SimpleNamespace(ru_maxrss=2_000_000)):
            with self.assertRaisesRegex(AssertionError,'RSS_STOP'):run_baskets.runtime_guard(0)

    def test_disk_swap_host_and_outer_timeout_guards(self):
        with patch.dict(run_baskets.os.environ,{'FUNDING_RANK_OUTER_TIMEOUT_SECONDS':'120'}),patch.object(run_baskets.os,'sched_setaffinity'),patch.object(run_baskets.resource,'setrlimit'):
            with patch.object(run_baskets.shutil,'disk_usage',return_value=SimpleNamespace(free=1)):
                with self.assertRaisesRegex(AssertionError,'DISK_RESERVE_STOP'):run_baskets.guards()
            with patch.object(run_baskets.shutil,'disk_usage',return_value=SimpleNamespace(free=20_000_000_000)):
                with patch.object(Path,'read_text',return_value='MemTotal: 10000000 kB\nMemAvailable: 9000000 kB\nSwapTotal: 1 kB\n'):
                    with self.assertRaisesRegex(AssertionError,'SWAP_STOP'):run_baskets.guards()
                with patch.object(Path,'read_text',return_value='MemTotal: 10000000 kB\nMemAvailable: 1 kB\nSwapTotal: 0 kB\n'):
                    with self.assertRaisesRegex(AssertionError,'HOST_MEMORY_STOP'):run_baskets.guards()
        with patch.dict(run_baskets.os.environ,{'FUNDING_RANK_OUTER_TIMEOUT_SECONDS':'0'}):
            with self.assertRaisesRegex(AssertionError,'MANDATORY_OUTER_TIMEOUT_WRAPPER_REQUIRED'):run_baskets.guards()


if __name__=='__main__':unittest.main(verbosity=2)
