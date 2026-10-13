"""Synthetic mask/rank/risk/terminal/run-budget tests; no historical accounts."""
from __future__ import annotations
import os
for k in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS'):os.environ[k]='1'
import hashlib
import json
from pathlib import Path
import shutil
import tempfile
import unittest
import numpy as np
from original_functions import DAY,SYMBOLS,load_originals
from targets_2021 import ARMS,asset_masks,build,us
from terminal_quotes import validate_terminal_rows,MINUTE,END
from run_budget import ensure_single_unstarted_batch,stop_on_worker_failure
from worker_bounds import require_worker_bounds

HERE=Path(__file__).resolve().parent

class Synthetic(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.d=np.arange(us(2021),us(2022),DAY,dtype=np.int64)
        cls.t=np.arange(us(2021)-250*DAY,us(2022)+DAY,DAY,dtype=np.int64)
        n=len(cls.t);q=np.arange(n)[:,None];j=np.arange(5)[None,:]
        cls.p=100*np.exp(.0001*(j+1)*q+.02*np.sin(q*.21+j))
        cls.p[:76,4]=np.nan;cls.p[:142,2]=np.nan
        cls.mask=asset_masks(cls.t,cls.p,cls.d)
        cls.hold=np.where(cls.mask,.12,0.)
        cls.out,cls.cov,cls.proof=build(cls.t,cls.p,cls.d,original_hold=cls.hold,original_hold_mask=cls.mask)

    def test_three_four_five_masks(self):
        np.testing.assert_array_equal(self.mask.sum(1),np.r_[np.full(25,3),np.full(66,4),np.full(274,5)])
    def test_match_keeps_original_early_cash(self):
        for a in ('STATIC50','VOL_MATCHED'):self.assertTrue((self.out[a][:91]==0).all())
        self.assertTrue(all(r['status']=='CURRENT_MEMBER_OR_PAST_RISK_UNREADY' for r in self.proof['match_proof'][:91]))
    def test_match_qualifies_after_original_mask(self):
        self.assertTrue(all(r['status']=='READY' for r in self.proof['match_proof'][91:]))
    def test_sma_cannot_enter_unready_asset(self):
        self.assertTrue((self.out['SMA200_10PCT'][~self.mask]==0).all())
    def test_exact_half_has_no_early_upscale(self):
        np.testing.assert_array_equal(self.out['EXACTHALF'][:91],.5*self.out['SMA200_10PCT'][:91])
    def test_half_exact_all_calendar(self):
        np.testing.assert_array_equal(self.out['EXACTHALF'],.5*self.out['STATIC50']+.5*self.out['SMA200_10PCT'])
    def test_365th_day_not_forced_cash(self):
        self.assertEqual(len(self.d),365);self.assertTrue(np.abs(self.out['SMA200_10PCT'][-1]).sum()>0)
    def test_future_rows_absent_at_all_mask_boundaries(self):
        for n in (24,25,90,91):
            cut=self.d[n];ids=self.d<=cut;scope=self.t<=cut
            alt,cov,_=build(self.t[scope],self.p[scope],self.d[ids],original_hold=self.hold[ids],original_hold_mask=self.mask[ids])
            for a in ARMS:np.testing.assert_array_equal(alt[a],self.out[a][ids])
            np.testing.assert_array_equal(cov,self.cov[ids])
    def test_original_hold_bytes_required(self):
        with self.assertRaisesRegex(ValueError,'explicit original HOLD'):build(self.t,self.p,self.d)
    def test_no_mask_override(self):
        with self.assertRaisesRegex(ValueError,'HOLD mask differs'):build(self.t,self.p,self.d,original_hold=self.hold,original_hold_mask=np.ones_like(self.mask))
    def test_missing_current_risk_close_stops(self):
        p=self.p.copy();p[np.searchsorted(self.t,self.d[0]),0]=np.nan
        with self.assertRaisesRegex(ValueError,'TARGET_STOP'):build(self.t,p,self.d,original_hold=self.hold,original_hold_mask=self.mask)
    def test_missing_daily_clock_stops(self):
        with self.assertRaisesRegex(ValueError,'contiguous'):build(np.delete(self.t,20),np.delete(self.p,20,axis=0),self.d,original_hold=self.hold,original_hold_mask=self.mask)
    def test_missing_rank_prefix_stops(self):
        sel=self.t>=self.d[0]-30*DAY
        with self.assertRaisesRegex(ValueError,'prior weekly rank'):build(self.t[sel],self.p[sel],self.d,original_hold=self.hold,original_hold_mask=self.mask)
    def test_zero_direction_still_counts_in_K(self):
        f=load_originals();direction=np.ones_like(self.p);direction[self.p==self.p]=1
        direction[np.searchsorted(self.t,self.d[0]),0]=0
        output=f.signed_intents(self.p,direction,self.t,SYMBOLS)[np.searchsorted(self.t,self.d[0]),0]
        self.assertEqual(output[0],0);self.assertEqual(output[2],0);self.assertEqual(output[4],0)
        # Two remaining signals retain .6/three eligible before downscale.
        k=np.searchsorted(self.t,self.d[0]);cols=np.array([0,1,3]);past=self.p[k-30:k+1,cols]
        expected,_=f.signed_risk_weights((.6/len(cols))*np.array([0.,1.,1.]),np.diff(past,axis=0)/past[:-1])
        np.testing.assert_array_equal(output[cols],expected)
    def test_terminal_exact_five_actual_minutes(self):
        t=np.arange(END-6*MINUTE,END,MINUTE);r=validate_terminal_rows(t,t+MINUTE,np.ones(6),np.ones(6),np.ones(6))
        self.assertEqual(r['attempt_count'],5);self.assertEqual(r['attempt_us'][-1],END-MINUTE+1)
    def test_terminal_missing_minute_stops(self):
        t=np.arange(END-6*MINUTE,END,MINUTE);t[-1]-=1
        with self.assertRaisesRegex(ValueError,'five attempts'):validate_terminal_rows(t,t+MINUTE,np.ones(6),np.ones(6),np.ones(6))
    def test_terminal_unknown_mark_stops(self):
        t=np.arange(END-6*MINUTE,END,MINUTE);p=np.ones(6);p[-1]=np.nan
        with self.assertRaisesRegex(ValueError,'positive actual'):validate_terminal_rows(t,t+MINUTE,np.ones(6),p,np.ones(6))
    def test_negative_capacity_stops(self):
        t=np.arange(END-6*MINUTE,END,MINUTE);v=np.ones(6);v[0]=-1
        with self.assertRaisesRegex(ValueError,'quote volume'):validate_terminal_rows(t,t+MINUTE,np.ones(6),np.ones(6),v)
    def test_finite_worker_bounds_only(self):
        require_worker_bounds({0},(4_000_000_000,4_000_000_000),(1200,1200))
        for as_,cpu in [((-1,-1),(1200,1200)),((4_000_000_000,4_000_000_000),(-1,-1))]:
            with self.assertRaises(RuntimeError):require_worker_bounds({0},as_,cpu)
    def test_new_state_root_does_not_authorize_rerun(self):
        with tempfile.TemporaryDirectory() as q:
            root=Path(q);ensure_single_unstarted_batch(root,root/'state1')
            (root/'state1').mkdir();(root/'state1/RUN_BINDING.json').write_text('{}')
            with self.assertRaisesRegex(RuntimeError,'already reserved'):ensure_single_unstarted_batch(root,root/'state2')
    def test_original_source_tamper_rejected(self):
        with tempfile.TemporaryDirectory() as q:
            root=Path(q);shutil.copytree(HERE/'reference',root/'reference');shutil.copy(HERE/'ORIGINAL_REFERENCE.json',root)
            p=root/'reference/match_core.py';p.write_text(p.read_text()+'\n# changed\n')
            with self.assertRaisesRegex(ValueError,'Original target source changed'):load_originals(root)
    def test_economic_negative_case_keeps_fixed_queue(self):
        # Economic accounting stops produce audited negative-case RESULT then
        # exit0. Their incomplete/full/paid classification is independently
        # retained; the controller must never censor the remaining fixed arms.
        for completion in ('COMPLETE_CONDITIONAL_ACCOUNT','NOT_EVALUABLE_ACCOUNT_HALT_NO_LIQUIDATION_SIMULATED','NOT_EVALUABLE_UNEXECUTABLE_RISK_REDUCTION','NOT_EVALUABLE_MISSING_HELD_ASSET_EXECUTION_OR_MARK'):
            self.assertFalse(stop_on_worker_failure(0),completion)
        for exit_code in (1,-9,-15):self.assertTrue(stop_on_worker_failure(exit_code))
        with self.assertRaises(ValueError):stop_on_worker_failure(None)

if __name__=='__main__':unittest.main(verbosity=2)
