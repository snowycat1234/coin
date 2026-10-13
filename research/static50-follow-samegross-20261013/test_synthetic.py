"""Synthetic recipe/causality tests; never instantiate a historical wallet."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
import numpy as np
from same_gross_targets import ARMS, DAY, SYMBOLS, common_gross
from original_follow_adapter import original

HERE = Path(__file__).resolve().parent

class RecipeTests(unittest.TestCase):
    def recipe(self, s, f):
        s, f = np.atleast_2d(s).astype(np.float64), np.atleast_2d(f).astype(np.float64)
        d = np.arange(len(s), dtype=np.int64) * DAY
        return common_gross(d, SYMBOLS, s, d, SYMBOLS, f)

    def test_fixed_equations_and_equal_gross(self):
        s = [.20, .10, -.10, 0., 0.]
        f = [-.10, .10, .10, 0., 0.]
        r = self.recipe(s, f)
        c = .5*np.array(s) + .5*np.array(f)
        g = min(sum(abs(np.array(s))), sum(abs(c)))
        np.testing.assert_array_equal(r['POOL_RAW'][0], c)
        np.testing.assert_array_equal(r[ARMS[1]][0], c * g / sum(abs(c)))
        np.testing.assert_array_equal(r[ARMS[0]][0], np.array(s) * (g / sum(abs(np.array(s)))))
        self.assertAlmostEqual(np.abs(r[ARMS[0]]).sum(), np.abs(r[ARMS[1]]).sum(), places=15)

    def test_all_zero_cash_no_nan(self):
        r = self.recipe([0.]*5, [0.]*5)
        for a in ARMS:
            self.assertTrue(np.isfinite(r[a]).all())
            self.assertFalse(np.signbit(r[a]).any())
            self.assertFalse(r[a].any())

    def test_static_cash_forces_pool_cash_even_follow_active(self):
        r = self.recipe([0.]*5, [.30, -.20, .10, 0., 0.])
        for a in ARMS: self.assertFalse(r[a].any())

    def test_exact_cancellation_cash(self):
        s = np.array([.30, -.20, .10, -0., 0.])
        r = self.recipe(s, -s)
        for a in ARMS: self.assertFalse(r[a].any())

    def test_follow_cash_scales_static_half(self):
        s = np.array([.2, .1, -.1, 0., 0.])
        r = self.recipe(s, [0.]*5)
        for a in ARMS: np.testing.assert_array_equal(r[a][0], .5*s)
        self.assertFalse(np.array_equal(r[ARMS[0]][0], s))

    def test_pool_above_static_only_downscaled(self):
        s = np.array([.05, 0., 0., 0., 0.])
        f = np.array([0., .30, .30, 0., 0.])
        r = self.recipe(s, f)
        self.assertTrue((r['static_factor'] <= 1.).all())
        self.assertTrue((r['pool_factor'] <= 1.).all())
        np.testing.assert_array_equal(r[ARMS[0]][0], s)
        self.assertTrue((np.abs(r[ARMS[1]]) <= np.abs(r['POOL_RAW']) + 1e-16).all())

    def test_individual_and_gross_caps_after_downscale(self):
        i = np.arange(200).reshape(-1,1)
        s = .12*np.sin(i + np.arange(5))
        f = .12*np.cos(i + np.arange(5))
        r = self.recipe(s, f)
        for a in ARMS:
            self.assertLessEqual(np.abs(r[a]).max(), .30)
            self.assertLessEqual(np.abs(r[a]).sum(1).max(), .60)
            np.testing.assert_allclose(np.abs(r[a]).sum(1), r['common_gross'], atol=2e-16, rtol=0.)

    def test_alignment_fail_closed(self):
        t = np.arange(2,dtype=np.int64)*DAY; s=np.zeros((2,5),np.float64)
        with self.assertRaises(ValueError): common_gross(t,SYMBOLS,s,t+DAY,SYMBOLS,s)
        with self.assertRaises(ValueError): common_gross(t,SYMBOLS,s,t,SYMBOLS[::-1],s)
        with self.assertRaises(ValueError): common_gross(t,SYMBOLS,s.astype(np.float32),t,SYMBOLS,s)

    def test_invalid_weights_fail_closed(self):
        with self.assertRaises(ValueError): self.recipe([float('nan'),0.,0.,0.,0.],[0.]*5)
        with self.assertRaises(ValueError): self.recipe([.31,0.,0.,0.,0.],[0.]*5)
        with self.assertRaises(ValueError): self.recipe([.20]*5,[0.]*5)

class OriginalFormulaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.core = original()

    def candles(self):
        h=np.full(21,110.); l=np.full(21,90.); c=np.full(21,100.); r=np.ones(21,bool)
        return h,l,c,r

    def test_original_upper_follow_positive_lower_negative(self):
        h,l,c,r=self.candles(); h[-1]=111.
        self.assertEqual(self.core.rejection(h,l,c,r),(-1,'UPPER_BREAK_REJECTED'))
        h,l,c,r=self.candles(); l[-1]=89.
        self.assertEqual(self.core.rejection(h,l,c,r),(1,'LOWER_BREAK_REJECTED'))

    def test_original_dual_breach_and_strict_boundary_cash(self):
        h,l,c,r=self.candles(); h[-1]=111.;l[-1]=89.
        self.assertEqual(self.core.rejection(h,l,c,r),(0,'BOTH_SIDES_ORDER_UNKNOWN'))
        l[-1]=90.; c[-1]=110.
        self.assertEqual(self.core.rejection(h,l,c,r),(0,'NO_REJECTED_BREAK'))

    def test_unknown_real_source_never_imputed(self):
        h,l,c,r=self.candles();h[-1]=111.;r[0]=False
        self.assertEqual(self.core.rejection(h,l,c,r),(0,'UNKNOWN_SOURCE'))
        r[:]=True;l[0]=float('nan')
        self.assertEqual(self.core.rejection(h,l,c,r),(0,'UNKNOWN_SOURCE'))

    def test_original_target_prefix_is_causal(self):
        t=np.arange(80,dtype=np.int64)*DAY
        p=np.exp(.01*np.sin(np.arange(80)[:,None]*np.array([.2,.3,.4,.5,.6])))*100.
        h=p*1.01; l=p*.99; ready=np.ones_like(p,bool); d=t[31:65]
        h[40,0]=h[20:40,0].max()*1.03
        p[40,0]=(l[20:40,0].min()+h[20:40,0].max())/2
        h[40,0]=max(h[40,0],p[40,0]);l[40,0]=min(l[40,0],p[40,0])
        a,proof=self.core.targets(t,h,l,p,ready,t,p,d)
        cut=50
        hh,ll,pp=h.copy(),l.copy(),p.copy();hh[cut+1:]=np.nan;ll[cut+1:]=np.nan;pp[cut+1:]=np.nan
        b,_=self.core.targets(t,hh,ll,pp,ready,t,pp,d[d<=t[cut]])
        np.testing.assert_array_equal(a['FOLLOW'][:len(b['FOLLOW'])], b['FOLLOW'])
        np.testing.assert_array_equal(a['FOLLOW'], -a['FADE'])
        for row in proof:
            self.assertLessEqual(row['event_bar_available_us'], row['decision_us'])
            self.assertLess(row['prior_channel_last_available_us'], row['decision_us'])

    def test_original_source_tamper_rejected(self):
        m=json.loads((HERE/'ORIGINAL_REFERENCE.json').read_text())
        self.assertFalse(m['equations_modified'])
        for name,sha in m['files_SHA256'].items():
            self.assertEqual(hashlib.sha256((HERE/name).read_bytes()).hexdigest(),sha)
        import original_follow_adapter as adapter
        with tempfile.TemporaryDirectory(dir=HERE) as directory:
            root=Path(directory)
            (root/'ORIGINAL_REFERENCE.json').write_bytes((HERE/'ORIGINAL_REFERENCE.json').read_bytes())
            for name in m['files_SHA256']:
                p=root/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes((HERE/name).read_bytes())
            name=next(iter(m['files_SHA256']));p=root/name;p.write_bytes(p.read_bytes()+b'\n# synthetic tamper\n')
            saved=adapter.HERE
            try:
                adapter.HERE=root
                with self.assertRaisesRegex(ValueError,'identity changed'): adapter.original()
            finally: adapter.HERE=saved

class LaunchTests(unittest.TestCase):
    def test_multiple_roots_cannot_repeat_fixed_batch(self):
        from run_budget import ensure_single_unstarted_batch
        with tempfile.TemporaryDirectory(dir=HERE) as directory:
            root=Path(directory); new=root/'state_second'
            self.assertEqual(ensure_single_unstarted_batch(root,new)['historical_wallets_created'],0)
            first=root/'state_first';first.mkdir()
            (first/'RUN_BINDING.json').write_text('{"parent_GO":true,"fine_case_ids":[]}')
            with self.assertRaisesRegex(RuntimeError,'already reserved or started'):
                ensure_single_unstarted_batch(root,new)
            self.assertFalse(new.exists())
    def test_case_state_without_run_binding_also_blocks_repeat(self):
        from run_budget import ensure_single_unstarted_batch
        with tempfile.TemporaryDirectory(dir=HERE) as directory:
            root=Path(directory);case=root/'state_partial/Y2023_STATIC50_SAMEGROSS_FINE_ORIGINAL'
            case.mkdir(parents=True);(case/'BINDING.json').write_text('{}')
            with self.assertRaisesRegex(RuntimeError,'already reserved or started'):
                ensure_single_unstarted_batch(root,root/'state_new')

    def test_no_go_never_creates_state(self):
        if not (HERE/'run_cases.py').exists(): self.skipTest('Runner not yet prepared')
        with tempfile.TemporaryDirectory(dir=HERE) as directory:
            state=Path(directory)/'forbidden_state'
            p=subprocess.run([sys.executable,str(HERE/'run_cases.py'),'--state-root',str(state)],capture_output=True,text=True)
            self.assertNotEqual(p.returncode,0)
            self.assertFalse(state.exists())

    def test_missing_independent_review_blocks_go_before_state(self):
        if (HERE/'REVIEW_RECEIPT.json').exists(): self.skipTest('Review now exists; never launch history from a synthetic test')
        if not (HERE/'FROZEN_CODE.json').exists(): self.skipTest('Freeze not yet prepared')
        state=HERE/'state_synthetic_review_gate_must_stay_absent'
        self.assertFalse(state.exists())
        p=subprocess.run([sys.executable,str(HERE/'run_cases.py'),'--parent-go','--state-root',str(state)],capture_output=True,text=True)
        self.assertNotEqual(p.returncode,0)
        self.assertIn('Independent exact-byte review required',p.stderr)
        self.assertFalse(state.exists())

    def test_prepared_byte_tamper_rejected_before_dependencies(self):
        if not (HERE/'FROZEN_CODE.json').exists(): self.skipTest('Freeze not yet prepared')
        from samegross_freeze import verify
        m=json.loads((HERE/'FROZEN_CODE.json').read_text())
        with tempfile.TemporaryDirectory(dir=HERE) as directory:
            root=Path(directory)
            for name in (*m['files_SHA256'],'samegross_freeze.py','FROZEN_CODE.json'):
                p=root/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes((HERE/name).read_bytes())
            p=root/'run_cases.py';p.write_bytes(p.read_bytes()+b'\n# synthetic tamper\n')
            with self.assertRaisesRegex(ValueError,'Prepared bytes changed: run_cases.py'): verify(root)

class ResourceTests(unittest.TestCase):
    def test_worker_as_and_cpu_soft_hard_finite_bounds(self):
        from worker_bounds import require_worker_bounds
        self.assertEqual(require_worker_bounds({0},(4_000_000_000,4_000_000_000),(1200,1200))['wallets_created'],0)
        invalid=[({0},(-1,4_000_000_000),(1200,1200)),
                 ({0},(4_000_000_000,-1),(1200,1200)),
                 ({0},(4_000_000_001,4_000_000_001),(1200,1200)),
                 ({0},(4_000_000_000,4_000_000_000),(-1,1200)),
                 ({0},(4_000_000_000,4_000_000_000),(1200,-1)),
                 ({0},(4_000_000_000,4_000_000_000),(1201,1201)),
                 ({0},(4_000_000_000,4_000_000_000),None),
                 ({0,1},(4_000_000_000,4_000_000_000),(1200,1200))]
        for affinity,space,cpu in invalid:
            with self.assertRaises(RuntimeError): require_worker_bounds(affinity,space,cpu)
    def external(self):
        return {'prior_historical_processes':[],'external_reserved_bytes':0,'external_busy_cpus':[]}
    def base(self): return {'memory':{'host_used':1_000_000_000,'cgroup_limit_verified':False},'allowed_cpus':[0,1,2,3]}
    def test_prior_history_blocks_parallel_admission(self):
        import resource_gate
        g=SimpleNamespace(WORKER_RSS_LIMIT=2_000_000_000,HOST_USED_LIMIT=8_000_000_000)
        e=self.external();e['prior_historical_processes']=[123]
        with self.assertRaisesRegex(RuntimeError,'still active'): resource_gate.check_external(self.base(),e,0,g)
    def test_full_external_reservation_and_cpu_exclusion(self):
        import resource_gate
        g=SimpleNamespace(WORKER_RSS_LIMIT=2_000_000_000,HOST_USED_LIMIT=8_000_000_000)
        e=self.external();e['external_reserved_bytes']=4_000_000_000;e['external_busy_cpus']=[0,1]
        self.assertEqual(resource_gate.check_external(self.base(),e,0,g)['allowed_cpus'],[2,3])
        with self.assertRaisesRegex(RuntimeError,'Host cap'): resource_gate.check_external(self.base(),e,1,g)

if __name__=='__main__': unittest.main(verbosity=2)
