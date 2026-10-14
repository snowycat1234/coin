"""Material synthetic allocation/state tests only; no new historical targets."""
from datetime import datetime,timezone
import unittest
import numpy as np
from target_core import DAY,ANCHOR,WEEK,originals,replay_cs,paired_targets,match_and_scale


def fixture(start=ANCHOR,n=21):
    t=np.arange(start-230*DAY,start+(n+1)*DAY,DAY,dtype=np.int64)
    j=np.arange(len(t))[:,None];a=np.arange(1,6)[None,:]
    returns=.0003*a+.008*np.sin(j*.37+a)+.004*np.cos(j*.13-a)
    p=100*np.exp(np.cumsum(returns,axis=0))
    d=np.arange(start,start+n*DAY,DAY,dtype=np.int64)
    hold=np.full((len(d),5),.12);mask=np.ones_like(hold,bool)
    return t,p,d,hold,mask


def paired_score(at,valid,price):
    s=np.arange(5,dtype=float)
    return {'PRICE_ONLY':s,'FUNDING_ADJUSTED':s[::-1]},True,{'synthetic':True}


class TargetTests(unittest.TestCase):
    def test_exact_original_CS31_unlagged_replay_synthetic_parity(self):
        t,p,d,h,m=fixture();f=originals()
        expected,diag=f.public_targets(p,t,d,tuple(('BTCUSDT','ETHUSDT','SOLUSDT','XRPUSDT','DOGEUSDT')),
                                      tuple(('BTCUSDT','ETHUSDT','SOLUSDT','XRPUSDT','DOGEUSDT')))
        def provider(at,valid,price):
            k=int(np.searchsorted(t,at));s=p[k]/p[k-21]-1.
            return {'PRICE_ONLY':s,'FUNDING_ADJUSTED':s},True,{}
        out,proof=replay_cs(t,p,d,provider)
        np.testing.assert_array_equal(out['PRICE_ONLY'],expected)
        self.assertEqual(proof['current_eligible'],diag['current_eligible'])
        self.assertEqual(proof['owning_rank_us'],diag['rank_us'])

    def test_March29_rank_survives_inactive_HOLD_and_activates_April2(self):
        start=int(datetime(2021,3,29,tzinfo=timezone.utc).timestamp())*1_000_000
        t,p,d,h,m=fixture(start,8);m[:4,2]=False;h[:4,2]=0
        out,_,proof=paired_targets(t,p,d,h,m,paired_score)
        self.assertTrue(np.all(out['PRICE_ONLY'][:4]==0))
        self.assertTrue(np.any(out['PRICE_ONLY'][4]!=0))
        self.assertFalse(np.array_equal(out['PRICE_ONLY'][4],out['FUNDING_ADJUSTED'][4]))
        self.assertEqual(proof['CS']['owning_rank_us'][4],start)
        self.assertEqual(len(proof['CS']['rank_records']),2)

    def test_original_min4_price_eligibility_and_stable_ties(self):
        f=originals()
        w=f.market_neutral(np.array([[0,1,1,1,2.]]),np.array([[False,True,True,True,True]]),k=2,gross=.6)[0]
        np.testing.assert_array_equal(w,[0,-.15,-.15,.15,.15])

    def test_original_sticky_CS31_clear_until_next_fixed_rank(self):
        t,p,d,h,m=fixture(ANCHOR,15);missing=ANCHOR+DAY
        p[t==missing,4]=np.nan
        # Removing the current observation makes it unready for31days; a
        # separate fixture uses a source gap leaving the trailing31 window.
        start=ANCHOR;gap=start-29*DAY;p[t==missing,4]=100.;p[t==gap,4]=np.nan
        out,proof=replay_cs(t,p,d,paired_score)
        self.assertFalse(proof['current_eligible'][0][4])
        self.assertTrue(proof['current_eligible'][2][4])
        self.assertEqual(out['PRICE_ONLY'][2,4],0.)
        self.assertNotEqual(out['PRICE_ONLY'][7,4],0.)

    def test_unknown_owning_rank_blocks_later_HOLD_activation(self):
        t,p,d,h,m=fixture(ANCHOR,8);m[:4,2]=False;h[:4,2]=0
        def unknown(at,valid,price):
            scores,_,proof=paired_score(at,valid,price)
            return scores,at!=ANCHOR,proof
        out,_,proof=paired_targets(t,p,d,h,m,unknown)
        self.assertTrue(proof['daily_required_source_not_ready'][4])
        self.assertTrue(np.isnan(out['PRICE_ONLY'][4]).all())
        self.assertFalse(proof['daily_required_source_not_ready'][7])

    def test_zero_CS_common_risk_zeros_both_matched_components(self):
        t,p,d,h,m=fixture()
        def tied(at,valid,price):return {'PRICE_ONLY':np.ones(5),'FUNDING_ADJUSTED':np.ones(5)},True,{}
        out,_,proof=paired_targets(t,p,d,h,m,tied)
        self.assertTrue(np.all(out['PRICE_ONLY']==0))
        self.assertTrue(np.all(out['FUNDING_ADJUSTED']==0))
        self.assertTrue(all(r['common_sigma']==0 for r in proof['risk']['PRICE_ONLY']['match']))

    def test_signed_submatrix_covariance_final_upscale_caps(self):
        f=originals();r=np.column_stack([np.sin(np.arange(30))*.01,-np.sin(np.arange(30))*.01])
        w,_=f.signed_risk_weights([.15,-.15],r)
        self.assertGreater(float(np.sqrt(w@(np.cov(r,rowvar=False,ddof=1)*365)@w)),0.)
        enlarged,proof=f.scale(np.array([.01,-.01,0,0,0]),np.eye(5)*.01)
        self.assertGreater(proof['factor'],1)
        self.assertLessEqual(abs(enlarged).sum(),.6+1e-12)
        self.assertLessEqual(abs(enlarged).max(),.3+1e-12)

    def test_shared_original_current31_risk_and_causal_prefix(self):
        t,p,d,h,m=fixture();out,cov,proof=paired_targets(t,p,d,h,m,paired_score)
        cut=d[10];sel=t<=cut;rows=d<=cut
        alt,acov,_=paired_targets(t[sel],p[sel],d[rows],h[rows],m[rows],paired_score)
        for a in out:np.testing.assert_array_equal(alt[a],out[a][rows])
        np.testing.assert_array_equal(acov,cov[rows])
        k=int(np.searchsorted(t,d[0]));r=np.diff(p[k-30:k+1],axis=0)/p[k-30:k]
        np.testing.assert_array_equal(cov[0],np.cov(r,rowvar=False,ddof=1)*365)


if __name__=='__main__':unittest.main(verbosity=2)
