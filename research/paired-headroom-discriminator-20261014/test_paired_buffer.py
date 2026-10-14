"""Synthetic-only causal/mechanical tests. No historical data or accounts."""
from __future__ import annotations
import unittest
import numpy as np
from paired_buffer import (WINDOW, HORIZON, PAIR_WIDTH, MINUTE, features,
                           pair_hurdles, paired_observations, assess, at)
from vendor import headroom_buffer as original
from run_toy import separated_extrema_toy


def flat(extra=12):
    n=WINDOW+extra
    return np.arange(n, dtype=np.int64)*MINUTE, np.ones(n)*100, np.ones(n)*100


class PairedTests(unittest.TestCase):
    def test_frozen_original_constants_and_window(self):
        self.assertEqual((WINDOW,HORIZON,PAIR_WIDTH),(43200,5,43195))
        self.assertEqual((original.MMR,original.SPREAD_SLIP,original.FEE),(.005,.0008,.00055))

    def test_independent_and_joint_differ_on_separate_synthetic_extremes(self):
        toy=separated_extrema_toy()
        self.assertTrue(toy['original_independent_trigger'])
        self.assertFalse(toy['paired_trigger'])
        self.assertGreater(toy['original_required_equity'],toy['paired_required_equity'])

    def test_same_observation_move_gap_alignment(self):
        t,p,o=flat();i=WINDOW;j=i-100
        p[j-6]=100;p[j-1]=120
        o=np.r_[p[0],p[:-1]].copy();o[j]=132
        got=features(t,p,o)
        expected=float(pair_hurdles(np.log(1.2),np.log(1.1))['short'])
        self.assertAlmostEqual(got['short_hurdle'][i],expected,places=13)

    def test_gap_uses_strict_prior_mark_not_same_bar_close(self):
        t,p,o=flat();i=WINDOW;j=i-20
        p[j]=200  # Cannot be the denominator of gap(open j).
        o[j]=120
        moves,gaps=paired_observations(p,o)
        self.assertAlmostEqual(gaps[j],np.log(1.2),places=14)
        self.assertAlmostEqual(moves[j],0,places=14)
        # Same-bar close p[j]=200 must have no effect on this observation.
        p[j]=1
        moves2,gaps2=paired_observations(p,o)
        self.assertEqual(gaps[j],gaps2[j]);self.assertEqual(moves[j],moves2[j])
        pair=pair_hurdles(moves[j],gaps[j])
        self.assertGreater(float(pair['short']),.20)

    def test_future_suffix_cannot_change_prior_features_or_signals(self):
        t,p,o=flat(30);cut=WINDOW+8
        p[100:105]=120;o[200]=110
        old=features(t,p,o)
        p2=p.copy();o2=o.copy();d=np.zeros(len(t),bool)
        p2[cut+1:]=9999;o2[cut+1:]=1;d[cut+1:]=True
        new=features(t,p2,o2,d)
        for k in old:np.testing.assert_equal(old[k][:cut+1],new[k][:cut+1])
        for i in range(WINDOW,cut+1):
            self.assertEqual(at(old,i,-1,25,p[i]),at(new,i,-1,25,p2[i]))

    def test_not_yet_completed_own_open_is_excluded(self):
        t,p,o=flat();i=WINDOW
        a=features(t,p,o);o[i+1]=1000000;b=features(t,p,o)
        self.assertEqual(a['short_hurdle'][i],b['short_hurdle'][i])
        self.assertGreater(b['short_hurdle'][i+1],a['short_hurdle'][i+1])

    def test_exact_pair_left_boundary(self):
        t,p,o=flat();i=WINDOW
        included=i-WINDOW+6;excluded=included-1
        o[excluded]=10000
        a=features(t,p,o);neutral=float(pair_hurdles(0,0)['short'])
        self.assertAlmostEqual(a['short_hurdle'][i],neutral)
        o[included]=200
        b=features(t,p,o)
        self.assertGreater(b['short_hurdle'][i],1)

    def test_direction_and_pairwise_clipping(self):
        x=pair_hurdles(.2,.1);y=pair_hurdles(-.2,-.1)
        neutral=pair_hurdles(0,0)
        self.assertEqual(float(x['long']),float(neutral['long']))
        self.assertEqual(float(y['short']),float(neutral['short']))
        self.assertGreater(float(x['short']),float(neutral['short']))
        self.assertGreater(float(y['long']),float(neutral['long']))

    def test_long_hurdles_are_not_unconditionally_ordered_at_extreme_gaps(self):
        # All prices/ratios are positive. Maintenance changes with stressed mark,
        # so constraints on pairing do not prove general coefficient dominance.
        moves=np.log(np.array([.5,1.]));gaps=np.log(np.array([1.,.0001]))
        paired=float(np.max(pair_hurdles(moves,gaps)['long']))
        old=original.assess(1,2,1,float(moves.min()),0,float(gaps.min()),0)
        independent=2-float(old['buffered_headroom'])
        self.assertGreater(paired,independent)

    def test_original_readiness_reason_and_derived_behavior_are_identical(self):
        t,p,o=flat();d=np.zeros(len(t),bool);d[WINDOW-2]=True
        a=features(t,p,o,d);b=original.features(t,p,o,d)
        np.testing.assert_equal(a['ready'],b['ready'])
        np.testing.assert_equal(a['reason'],b['reason'])
        self.assertFalse(at(a,WINDOW,-1,25,100)['trigger'])
        self.assertTrue(np.isnan(a['short_hurdle'][WINDOW]))

    def test_original_bad_open_bad_mark_and_gap_readiness_are_identical(self):
        for bad in ('open','mark','clock'):
            t,p,o=flat()
            if bad=='open':o[WINDOW-10]=0
            if bad=='mark':p[WINDOW-10]=np.nan
            if bad=='clock':t[WINDOW-10]+=1
            a=features(t,p,o);b=original.features(t,p,o)
            np.testing.assert_equal(a['ready'],b['ready'])
            np.testing.assert_equal(a['reason'],b['reason'])

    def test_current_close_mark_is_known_but_latest_pair_is_previous_open(self):
        t,p,o=flat();i=WINDOW
        p[i]=200
        a=features(t,p,o)
        self.assertAlmostEqual(a['short_hurdle'][i],float(pair_hurdles(0,0)['short']))
        self.assertFalse(at(a,i,-1,1,100)['trigger'])
        self.assertTrue(at(a,i,-1,1,200)['trigger'])
        self.assertEqual(a['aligned_independent_short_hurdle'][i],a['short_hurdle'][i])
        self.assertGreater(a['legacy_independent_short_hurdle'][i],a['aligned_independent_short_hurdle'][i])

    def test_separate_fixed_controls_decompose_alignment_and_coupling(self):
        t,p,o=flat();i=WINDOW
        p[100:105]=120;o=np.r_[p[0],p[:-1]].copy();o[200]*=1.1
        a=features(t,p,o)
        self.assertAlmostEqual(a['legacy_independent_short_hurdle'][i],a['aligned_independent_short_hurdle'][i],places=13)
        self.assertGreater(a['aligned_independent_short_hurdle'][i],a['short_hurdle'][i])
        self.assertTrue(at(a,i,-1,25,100,arm='aligned_independent')['trigger'])
        self.assertFalse(at(a,i,-1,25,100,arm='paired')['trigger'])

    def test_aligned_control_exact_marginal_extrema_over_same_population(self):
        t,p,o=flat();i=WINDOW
        p[100:105]=120;o=np.r_[p[0],p[:-1]].copy();o[200]*=1.1
        m,g=paired_observations(p,o);left=i-WINDOW+6
        a=features(t,p,o)
        old=original.assess(-1,25,100,min(0,np.min(m[left:i+1])),max(0,np.max(m[left:i+1])),min(0,np.min(g[left:i+1])),max(0,np.max(g[left:i+1])))
        self.assertAlmostEqual(a['aligned_independent_short_hurdle'][i]*100,25-float(old['buffered_headroom']),places=12)

    def test_one_pair_exactly_matches_original_financial_stress_math(self):
        for q,aa,gg in [(2,-.1,-.02),(-2,.1,.02)]:
            pairs=pair_hurdles(aa,gg)
            new=assess(q,40,100,pairs['long'],pairs['short'])
            old=original.assess(q,40,100,min(aa,0),max(aa,0),min(gg,0),max(gg,0))
            self.assertAlmostEqual(float(new['buffered_headroom']),float(old['buffered_headroom']),places=12)
            self.assertEqual(bool(new['trigger']),bool(old['trigger']))

    def test_zero_owned_quantity_never_triggers_and_inclusive_boundary(self):
        k=pair_hurdles(0,0)
        self.assertFalse(bool(assess(0,0,100,k['long'],k['short'])['trigger']))
        required=100*float(k['short'])
        self.assertTrue(bool(assess(-1,required,100,k['long'],k['short'])['trigger']))

    def test_finite_operands_required_equity_overflow_fails_closed(self):
        k=pair_hurdles(0,0)
        with self.assertRaisesRegex(ValueError,'Nonfinite required equity or headroom'):
            assess(1e308,1,10,k['long'],k['short'])

    def test_finite_required_equity_headroom_subtraction_overflow_fails_closed(self):
        k=pair_hurdles(np.log(.0001),0)
        with self.assertRaisesRegex(ValueError,'Nonfinite required equity or headroom'):
            assess(1e308,-1e308,1,k['long'],k['short'])

    def test_joint_is_not_greater_than_original_independent_on_synthetic_path(self):
        t,p,o=flat(30);rng=np.random.default_rng(814)
        p[:]=100*np.exp(np.cumsum(rng.normal(0,.001,len(p))))
        o[:]=np.r_[p[0],p[:-1]]*np.exp(rng.normal(0,.001,len(p)))
        a=features(t,p,o);b=original.features(t,p,o)
        for direction,q in [('long',1),('short',-1)]:
            old=original.assess(q,100,p,**{k:b[k] for k in ('a_down','a_up','g_down','g_up')})
            required=100-old['buffered_headroom']
            ready=a['ready']
            self.assertTrue(np.all(p[ready]*a[direction+'_hurdle'][ready]<=required[ready]+1e-10))

    def test_integer_microsecond_clock_required(self):
        t,p,o=flat()
        with self.assertRaisesRegex(ValueError,'Integer UTC'):features(t.astype(float),p,o)

    def test_sufficient_rolling_statistic_matches_independent_bruteforce(self):
        t,p,o=flat(30);rng=np.random.default_rng(901)
        p[:]=100*np.exp(np.cumsum(rng.normal(0,.001,len(p))))
        o[:]=np.r_[p[0],p[:-1]]*np.exp(rng.normal(0,.002,len(p)))
        got=features(t,p,o)
        for i in (WINDOW,WINDOW+7,WINDOW+20):
            j=np.arange(i-WINDOW+6,i+1,dtype=np.int64)
            # Independent direct clock/index arithmetic, not production helper.
            a=np.log(p[j-1]/p[j-6]);g=np.log(o[j]/p[j-1])
            self.assertEqual(len(j),43195)
            for q,equity in ((2.,25.),(-3.,50.),(.01,1.)):
                all_scenarios=original.assess(q,equity,p[i],np.minimum(a,0),np.maximum(a,0),np.minimum(g,0),np.maximum(g,0))
                worst=float(np.min(all_scenarios['buffered_headroom']))
                neutral=original.assess(q,equity,p[i],0.,0.,0.,0.)
                worst=min(worst,float(neutral['buffered_headroom']))
                compressed=at(got,i,q,equity,p[i])
                self.assertAlmostEqual(compressed['buffered_headroom'],worst,places=11)
                self.assertEqual(compressed['trigger'],worst<=0)


if __name__=='__main__':unittest.main(verbosity=2)
