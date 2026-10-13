"""Synthetic-only adversarial contract tests. No historical finance advances."""
import unittest
import numpy as np
from decimal import Decimal as D
from headroom_buffer import *

class CausalBufferTests(unittest.TestCase):
    def setUp(self):
        self.n=WINDOW+12
        self.times=np.arange(self.n,dtype=np.int64)*MINUTE
        self.marks=np.full(self.n,100.)
        self.opens=np.full(self.n,100.)

    def test_exact_30_day_anchor_and_no_shortening(self):
        f=features(self.times,self.marks,self.opens)
        self.assertFalse(f['ready'][WINDOW-1]);self.assertTrue(f['ready'][WINDOW])
        self.assertEqual(f['reason'][WINDOW-1],'WARMUP_30_COMPLETE_DAYS')
        self.assertEqual(f['a_up'][WINDOW],0);self.assertEqual(f['g_down'][WINDOW],0)

    def test_future_prefix_invariance_and_current_completed_close(self):
        at=WINDOW+2
        a=features(self.times,self.marks,self.opens)
        self.marks[at+1:]=1e6;self.opens[at+1:]=1e-4
        b=features(self.times,self.marks,self.opens)
        for key in a: np.testing.assert_array_equal(a[key][:at+1],b[key][:at+1])
        self.marks[at]=110.
        c=features(self.times,self.marks,self.opens)
        self.assertAlmostEqual(c['a_up'][at],np.log(1.1))

    def test_open_basis_uses_strict_previous_mark_not_same_minute_close(self):
        at=WINDOW
        self.marks[at]=90.;self.opens[at]=110.
        f=features(self.times,self.marks,self.opens)
        self.assertAlmostEqual(f['g_up'][at],np.log(1.1))
        self.assertNotAlmostEqual(f['g_up'][at],np.log(110/90))
        # Lower included open is index1; open0 has no within-window prior mark.
        self.opens[0]=1e9;f=features(self.times,np.full(self.n,100.),self.opens)
        self.assertAlmostEqual(f['g_up'][at],np.log(1.1))

    def test_five_minute_pairs_stay_inside_window(self):
        at=WINDOW+5
        self.marks[4]=1.;f=features(self.times,self.marks,self.opens)
        self.assertEqual(f['a_up'][at],0.)
        self.marks[5]=50.;f=features(self.times,self.marks,self.opens)
        self.assertAlmostEqual(f['a_up'][at],np.log(2.))

    def test_gap_duplicate_bad_and_derived_never_nanmax_ready(self):
        cases=[]
        t=self.times.copy();t[WINDOW:]+=MINUTE;cases.append((t,self.marks,self.opens,None,'NONCONTIGUOUS_MINUTE_CLOCK'))
        t=self.times.copy();t[WINDOW]=t[WINDOW-1];cases.append((t,self.marks,self.opens,None,'NONCONTIGUOUS_MINUTE_CLOCK'))
        m=self.marks.copy();m[WINDOW]=np.nan;cases.append((self.times,m,self.opens,None,'BAD_MARK'))
        m=self.marks.copy();m[WINDOW]=0;cases.append((self.times,m,self.opens,None,'BAD_MARK'))
        o=self.opens.copy();o[WINDOW]=np.inf;cases.append((self.times,self.marks,o,None,'BAD_TRADE_OPEN'))
        d=np.zeros(self.n,bool);d[WINDOW]=True;cases.append((self.times,self.marks,self.opens,d,'DERIVED_OR_UNKNOWN_MARK'))
        for t,m,o,d,reason in cases:
            f=features(t,m,o,d);self.assertFalse(f['ready'][WINDOW]);self.assertEqual(f['reason'][WINDOW],reason)
            self.assertTrue(np.isnan(f['a_up'][WINDOW]))

    def test_long_short_direction_and_zero_ownership(self):
        r=assess(np.array([1.,-1.,0.]),np.array([100.,100.,0.]),100.,np.log(.9),np.log(1.2),np.log(.95),np.log(1.03))
        np.testing.assert_allclose(r['stressed_mark'],[90.,120.,120.])
        np.testing.assert_allclose(r['stressed_fill'][:2],[90*.95*.9992,120*1.03*1.0008])
        np.testing.assert_allclose(r['stressed_equity'][:2],[90.,80.])
        self.assertFalse(r['trigger'][2])

    def test_fee_basis_spread_slip_integrity_and_trigger_equality(self):
        q=-2.;P=100.;ad=np.log(1.1);gp=np.log(1.02)
        r=assess(q,20.,P,0,ad,0,gp)
        ps=P*np.exp(ad);fill=ps*np.exp(gp)*1.0008
        reserve=2*abs(fill-ps)+2*fill*.00055
        self.assertAlmostEqual(float(r['closecost_reserve']),reserve)
        base=assess(-1.,100.,100.,0,0,0,0)
        e=float(base['maintenance']+base['closecost_reserve'])
        self.assertTrue(bool(assess(-1.,e,100.,0,0,0,0)['trigger']))
        self.assertFalse(bool(assess(-1.,e+1e-7,100.,0,0,0,0)['trigger']))
        # Direct no-gap per-side cost is 8bp execution plus fee on actual fill.
        r=assess(1.,100.,100.,0,0,0,0)
        self.assertAlmostEqual(float(r['closecost_reserve']),100*.0008+100*.9992*.00055)

    def test_shared_capacity_floor_no_double_spend(self):
        a,cap=spend_capacity('.06','10000','100')
        b,_=spend_capacity('.06','10000','100',a)
        self.assertEqual(a,D('.06'));self.assertEqual(b,D('.04'));self.assertEqual(a+b,cap)
        x,_=spend_capacity('1','123.456789','100');self.assertEqual(x,D('.00123456'))
        self.assertEqual(spend_capacity('1','0','100')[0],0)
        for quote,price in [('-1','100'),('100','0'),('nan','100')]:
            with self.assertRaises(ValueError):spend_capacity('1',quote,price)

    def test_exact_next_open_plus_one_and_five_distinct_opens(self):
        t=np.arange(8,dtype=np.int64)*MINUTE
        o=np.full(8,100.);v=np.full(8,10000.)
        # signal close=MIN: skip open=MIN, first open=2MIN, event=2MIN+1.
        w=exit_witness('-.5',MINUTE,t,o,v)
        self.assertEqual(w['first_eligible_event_us'],2*MINUTE+1)
        self.assertEqual(w['fifth_eligible_event_us'],6*MINUTE+1)
        self.assertEqual(len(w['attempts']),5);self.assertTrue(w['capacity_complete'])
        self.assertEqual(D(w['total_fee_USDT']),D('.5')*D('100.08000')*D('.00055'))
        self.assertEqual(D(w['total_execution_cost_USDT']),D('.5')*D('.08000'))
        self.assertEqual(w['account_transitions'],0);self.assertIsNone(w['hypothetical_PnL'])
        w=exit_witness('1',MINUTE,t,o,v);self.assertFalse(w['capacity_complete']);self.assertEqual(D(w['remaining_quantity']),D('.5'))
        self.assertEqual(len({x['event_us'] for x in w['attempts']}),5)

    def test_missing_real_open_or_quote_never_fabricated(self):
        t=np.arange(8,dtype=np.int64)*MINUTE;o=np.full(8,100.);v=np.full(8,10000.)
        keep=t!=2*MINUTE
        w=exit_witness('1',MINUTE,t[keep],o[keep],v[keep])
        self.assertFalse(w['capacity_complete'])
        self.assertEqual(w['attempts'][0]['status'],'MISSING_OR_DUPLICATE_REAL_OPEN')
        self.assertEqual(w['attempts'][1]['status'],'MISSING_REAL_PRIOR_QUOTE')

    def test_future_mark_reference_not_ready_without_changing_signal(self):
        from scan_shadow import fixed_inventory_reference
        source={'times':np.arange(8,dtype=np.int64)*MINUTE,'BTCUSDT_mark':np.full(8,100.)}
        derived=np.zeros(8,bool)
        ref=fixed_inventory_reference(-1.,100.,100.,MINUTE,source,'BTCUSDT',2*MINUTE+1,derived)
        self.assertEqual(ref['status'],'READY_REFERENCE');self.assertEqual(ref['checked_real_mark_closes'],5)
        derived[2]=True
        ref=fixed_inventory_reference(-1.,100.,100.,MINUTE,source,'BTCUSDT',2*MINUTE+1,derived)
        self.assertEqual(ref['status'],'NOT_READY_REFERENCE');self.assertEqual(ref['reason'],'DERIVED_OR_UNKNOWN_FUTURE_MARK')
        self.assertIsNone(ref['cross_before_capacity_completion'])
        # A source cell after signal must never enter historical readiness.
        d=np.zeros(self.n,bool);d[WINDOW+1]=True
        f=features(self.times,self.marks,self.opens,d);self.assertTrue(f['ready'][WINDOW])
        derived[:]=False;source['BTCUSDT_mark'][2]=np.nan
        ref=fixed_inventory_reference(-1.,100.,100.,MINUTE,source,'BTCUSDT',None,derived)
        self.assertEqual(ref['reason'],'INVALID_REAL_MARK')
        source['BTCUSDT_mark'][2]=100.;source['times'][3]+=MINUTE
        ref=fixed_inventory_reference(-1.,100.,100.,MINUTE,source,'BTCUSDT',None,derived)
        self.assertEqual(ref['reason'],'MISSING_OR_DUPLICATE_REAL_MARK_CLOSE')

if __name__=='__main__':unittest.main(verbosity=2)
