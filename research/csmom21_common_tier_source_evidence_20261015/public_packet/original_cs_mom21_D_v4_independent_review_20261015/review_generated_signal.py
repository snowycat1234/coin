"""Independent generated-only V2 signal review; no source/provider APIs."""
import ast
from hashlib import sha256
import inspect
import json
from pathlib import Path
import sys
import unittest
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'original_cs_mom21_D_20261015_v4'))
import cs_signal as s
import cs_config as config
import cs_codec as codec


def fixture(days=14):
    count=260
    t=s.ANCHOR+np.arange(-230,30,dtype=np.int64)*s.DAY
    x=np.arange(count)[:,None]
    slopes=np.array([.0002,.0004,.0006,.0008,.0010])
    p=np.exp(x*slopes + .006*np.sin(x*np.array([.13,.17,.23,.29,.31]))) * np.array([50000,2000,20,.5,.05])
    return p,t,t.copy(),t[220:220+days]

class SignalReview(unittest.TestCase):
    def test_01_exact_original_source_AST_default_anchor(self):
        original=s.originals(); sig=inspect.signature(original.public_targets)
        self.assertIs(sig.parameters['short_absolute_confirmation'].default,False)
        self.assertEqual(sig.parameters['anchor_us'].default,s.ANCHOR)
        p=json.loads((s.HERE/'ORIGINAL_SIGNAL_PROVENANCE.json').read_bytes())
        for row in p['source_files']:
            path=s.HERE/'sources'/row['local_locator']
            raw=path.read_bytes();self.assertEqual(sha256(raw).hexdigest(),row['SHA256'])
            tree=ast.parse(raw)
            for name,pin in row['functions'].items():
                node=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name==name)
                self.assertEqual(sha256(ast.dump(node,include_attributes=False).encode()).hexdigest(),pin)
        p,t,a,d=fixture()
        default,diag=original.public_targets(p,a,d,s.SYMBOLS,s.SYMBOLS)
        explicit,diag2=original.public_targets(p,a,d,s.SYMBOLS,s.SYMBOLS,short_absolute_confirmation=False)
        self.assertEqual(default.tobytes(),explicit.tobytes());self.assertEqual(diag,diag2)

    def test_02_weekly_prefix_unchanged_and_distinct_arrays(self):
        p,t,a,d=fixture();raw,sized,tiers,cov,diag,proof=s.project_arrays(p,t,a,d)
        suffix=s.project_arrays(p,t,a,d[3:])
        for i,j in ((raw,suffix[0]),(sized,suffix[1]),(cov,suffix[3])):
            self.assertEqual(i[3:].tobytes(),j.tobytes())
        for tier in tiers:self.assertEqual(tiers[tier][3:].tobytes(),suffix[2][tier].tobytes())
        self.assertEqual(diag['rank_us'][3:],suffix[4]['rank_us'])
        for i,rank in enumerate(diag['rank_us']):
            self.assertEqual((rank-s.ANCHOR)%(7*s.DAY),0)
            if i and rank==diag['rank_us'][i-1]:self.assertEqual(raw[i].tobytes(),raw[i-1].tobytes())
        self.assertTrue(np.any(sized<0));self.assertEqual(raw.sum(axis=1).tobytes(),np.zeros(len(d)).tobytes())
        self.assertTrue(np.all(np.abs(raw).sum(axis=1)==.6))
        self.assertTrue(set(np.unique(raw)) <= {-.15,0.,.15})
        self.assertIsNot(raw,sized)
        for tier in tiers:self.assertIsNot(tiers[tier],sized)

    def test_03_future_price_mutation_does_not_change_prior(self):
        p,t,a,d=fixture();before=s.project_arrays(p,t,a,d)
        changed=p.copy();changed[t>d[-1]] *= np.arange(1,np.count_nonzero(t>d[-1])+1)[:,None]*3
        after=s.project_arrays(changed,t,a,d)
        for i in (0,1,3):self.assertEqual(before[i].tobytes(),after[i].tobytes())
        self.assertEqual(before[4],after[4]);self.assertEqual(before[5],after[5])
        for tier in before[2]:self.assertEqual(before[2][tier].tobytes(),after[2][tier].tobytes())

    def test_04_original_downward_only_and_common_math_exact(self):
        p,t,a,d=fixture();raw,sized,tiers,cov,diag,proof=s.project_arrays(p,t,a,d)
        for i in range(len(d)):
            self.assertLessEqual(float(np.abs(sized[i]).sum()),float(np.abs(raw[i]).sum())+1e-15)
            for tier in tiers:
                expected,meta=s.common_grid().scale_to_tier(sized[i],cov[i],tier)
                self.assertEqual(expected.tobytes(),tiers[tier][i].tobytes());self.assertEqual(meta,proof[i]['tiers'][tier])
                self.assertLessEqual(float(np.abs(expected).sum()),config.TIER_GROSS_CAPS[tier]+1e-12)
                self.assertLessEqual(float(np.max(np.abs(expected))),.3+1e-12)
                self.assertLessEqual(meta['post_sigma'],config.TIER_BUDGETS[tier]+1e-12)
        self.assertTrue(any(row['tiers']['HIGH']['factor']>1 for row in proof))
        r=np.random.default_rng(9).normal(0,.2,(30,5));w=np.array([-.8,-.4,0,.4,.8])
        clipped=np.clip(w,-.3,.3);clipped*=.6/np.abs(clipped).sum()
        c=np.cov(r,rowvar=False,ddof=1)*365;sigma=np.sqrt(clipped@c@clipped)
        got,meta=s.originals().signed_risk_weights(w,r)
        self.assertEqual(got.tobytes(),(clipped*(.1/sigma)).tobytes())

    def test_05_signal_defaults_cash_ties_and_no_short_filter(self):
        scores=np.array([[0.,0.,1.,2.,3.],[1.,1.,1.,1.,1.]])
        got=s.originals().market_neutral(scores,np.ones((2,5),dtype=bool))
        self.assertEqual(got[0].tobytes(),np.array([-.15,-.15,0.,.15,.15]).tobytes())
        self.assertFalse(got[1].any())
        p,t,a,d=fixture();p=np.exp(np.arange(len(t))[:,None]*np.array([.001,.002,.003,.004,.005]))*100
        default,diag=s.originals().public_targets(p,a,d,s.SYMBOLS,s.SYMBOLS)
        filtered,_=s.originals().public_targets(p,a,d,s.SYMBOLS,s.SYMBOLS,short_absolute_confirmation=True)
        self.assertTrue(np.any(default<0));self.assertFalse(np.any(filtered<0))
        flat=s.project_arrays(np.full_like(p,100),t,a,d)
        self.assertFalse(flat[0].any());self.assertFalse(flat[1].any())
        for tier in flat[2]:self.assertFalse(flat[2][tier].any())

    def test_06_daily_admission_and_frozen_array(self):
        p,t,a,d=fixture()
        with self.assertRaises(ValueError):s.project_arrays(p,t,a,t[198:199])
        with self.assertRaises(ValueError):s.project_arrays(p,t,a+1,d)
        changed=p.copy();changed[220,0]=np.nan
        with self.assertRaises(ValueError):s.project_arrays(changed,t,a,d)
        frozen=codec.frozen_array(p)
        self.assertFalse(frozen.flags.writeable)
        with self.assertRaises(ValueError):frozen.setflags(write=True)

    def test_07_global_fifteen_unique_calendars(self):
        cells=config.cells();self.assertEqual(len(cells),15);self.assertEqual(len({r['cell_id'] for r in cells}),15)
        for r in cells:
            self.assertEqual((r['end_exclusive_us']-r['start_us'])//s.DAY,r['calendar_days'])
            self.assertEqual(r['calendar_days'],{2021:274,2022:365,2023:365,2024:366,2025:365}[r['year']])
            self.assertEqual(r['strategy'],'CSMOM21_COMMON_TIER');self.assertTrue(r['fresh_annual_wallet'])

if __name__=='__main__':unittest.main(verbosity=2)
