"""Synthetic finance/clock regressions; never constructs a historical wallet."""
from copy import deepcopy
from decimal import Decimal as D
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys
import unittest
import numpy as np
import polars as pl

HERE=Path(__file__).resolve().parent;ROOT=HERE.parent
WORKSPACE=Path(os.environ.get('COIN_HEADROOM_WORKSPACE',str(ROOT)))
REPO=WORKSPACE/'coin_native_half_mix_20261013/repo'
sys.path[:0]=[str(REPO),str(REPO/'src'),str(WORKSPACE/'coin_margin_protective_policy_20261013'),str(HERE)]
spec=importlib.util.spec_from_file_location('candidate_test_port',REPO/'research/static50-sma-20261013/local_native_apis.py')
port=importlib.util.module_from_spec(spec);spec.loader.exec_module(port);port.verify()
from scripts.investment.perpetual_directional import COSTS,UNITS,MINUTE,DAY
from scripts.investment.resumable_perpetual import NativeDailySimulator
from protective_policy import ProtectiveFullExitSimulator
from quant.perpetual_account import USDTLinearPerpetualAccount,InstrumentProfile
from headroom_policy import HeadroomFullExitSimulator,POLICY_ID
from feature_tape import FeatureTape
BASE=.53197408

def window(days=1,stress=None,zero_after=None,ready=True,adverse=1.4,symbols=('XRPUSDT',),events=None):
    n=days*1440;p=np.full(n,BASE)
    if stress is not None:p[10:]=stress
    q=np.full(n,1e6)
    if zero_after is not None:q[zero_after:]=0
    market={s:dict(open=p.copy(),close=p.copy(),mark=p.copy(),quote_volume=q.copy()) for s in symbols}
    daily=pl.DataFrame([dict(symbol=s,close_us=d*DAY,close=BASE if d==0 else (stress or BASE)) for d in range(days) for s in symbols])
    result=dict(start=0,end=days*DAY,symbols=symbols,daily=daily,events=events or [],market=market)
    arrays={}
    for s in symbols:
        arrays[s+'_mark']=market[s]['mark'].copy()
        arrays[s+'_ready']=np.full(n,ready,bool)
        arrays[s+'_reason_code']=np.full(n,0 if ready else 1,np.uint8)
        for k in ('a_down','g_down','g_up'):arrays[s+'_'+k]=np.full(n,0. if ready else np.nan)
        arrays[s+'_a_up']=np.full(n,np.log(adverse) if ready else np.nan)
    result['headroom_features']=FeatureTape((np.arange(n)+1)*MINUTE,symbols,arrays,{'fixture':'SYNTHETIC_ONLY'})
    return result

def account(config,*,symbols):
    return USDTLinearPerpetualAccount(config,symbols=symbols,
        instrument_profiles={s:InstrumentProfile(quantity_step=D('100')) for s in symbols},closing_min_notional_exempt=True)

def simulator(w,cls=HeadroomFullExitSimulator):
    return cls(w,'LONG_SHORT',COSTS[0],UNITS[0],account_factory=account,persist_cash_close=False,final_day_target_zero=False)

def finance_image(sim):
    image=NativeDailySimulator.snapshot(sim)
    image.pop('version')
    return image

class CandidateTests(unittest.TestCase):
    def test_false_gate_financial_identity_full_day_funding_terminal(self):
        w=window(adverse=1.01,events=[dict(symbol='XRPUSDT',event_us=8*MINUTE,raw_rate=.0001)])
        base=simulator(w,NativeDailySimulator);new=simulator(w)
        base.advance_day({'XRPUSDT':-.02});new.advance_day({'XRPUSDT':-.02})
        self.assertEqual(finance_image(base),finance_image(new))
        self.assertEqual(new.protective_locks,{})
        self.assertEqual(new.protective_events,[])

    def test_not_ready_keeps_path_even_where_old_guard50_would_trigger(self):
        w=window(stress=.8,ready=False)
        base=simulator(w,NativeDailySimulator);new=simulator(w)
        base.advance_day({'XRPUSDT':-.02});new.advance_day({'XRPUSDT':-.02})
        self.assertEqual(finance_image(base),finance_image(new));self.assertEqual(new.protective_events,[])
        self.assertGreater(new.headroom_coverage['XRPUSDT']['not_ready_invested_hook_evaluations'],0)

    def test_execution_methods_are_exactly_reused(self):
        for method in ('schedule','attempt','advance_day'):
            self.assertIs(getattr(HeadroomFullExitSimulator,method),getattr(ProtectiveFullExitSimulator,method))

    def test_next_open_plus1_partial_reduce_real_cost_and_direction_lock(self):
        w=window(3,stress=.8)
        w['market']['XRPUSDT']['quote_volume'][11:13]=110000
        new=simulator(w);new.advance_day({'XRPUSDT':-.02})
        signals=[r for r in new.protective_events if r['kind']=='FULL_EXIT_SIGNAL']
        closes=[r for r in new.account.trades if r['leg']=='CLOSE']
        self.assertEqual(signals[0]['event_us'],11*MINUTE)
        self.assertEqual(closes[0]['event_us'],12*MINUTE+1);self.assertEqual(closes[0]['quantity'],100)
        self.assertEqual(len(closes),3);self.assertGreater(new.account.fees,0);self.assertGreater(new.account.execution_cost,0)
        count=len(new.account.trades);new.advance_day({'XRPUSDT':-.02})
        self.assertEqual(len(new.account.trades),count);self.assertIn('XRPUSDT',new.protective_locks)
        new.advance_day({'XRPUSDT':0.});self.assertNotIn('XRPUSDT',new.protective_locks)

    def test_protection_persists_beyond_five_attempts_and_no_lot(self):
        w=window(2,stress=.8,zero_after=10)
        new=simulator(w);new.advance_day({'XRPUSDT':-.02})
        self.assertEqual(new.pending['XRPUSDT']['kind'],'PROTECTIVE_STOP')
        self.assertGreater(new.protective_locks['XRPUSDT']['deferred_no_lot_minutes'],1000)
        image=new.snapshot();restored=HeadroomFullExitSimulator.from_snapshot(image,w,account_class=USDTLinearPerpetualAccount)
        self.assertEqual(image,restored.snapshot());self.assertEqual(new.state_hash(),restored.state_hash())
        new.advance_day({'XRPUSDT':-.02});restored.advance_day({'XRPUSDT':-.02})
        self.assertEqual(new.snapshot(),restored.snapshot())
        self.assertEqual(new.completion,'NOT_EVALUABLE_PROTECTIVE_EXIT_UNFILLED_AT_HORIZON')

    def test_maintenance_halt_before_hook_never_resurrected(self):
        new=simulator(window(stress=1.06181663));new.advance_day({'XRPUSDT':-.02})
        self.assertEqual(new.account.status,'LIQUIDATION_REQUIRED_HALT');self.assertEqual(new.protective_events,[])

    def test_all_same_close_funding_precedes_trigger(self):
        events=[dict(symbol='BTCUSDT',event_us=11*MINUTE,raw_rate=0.),dict(symbol='XRPUSDT',event_us=11*MINUTE,raw_rate=-100.)]
        new=simulator(window(stress=.8,symbols=('BTCUSDT','XRPUSDT'),events=events))
        new.advance_day({'BTCUSDT':0.,'XRPUSDT':-.02})
        self.assertEqual(new.account.status,'BANKRUPT_HALT');self.assertEqual(new.protective_events,[])

    def test_cap_priority_five_attempt_stop_preserved(self):
        new=simulator(window(stress=.8,zero_after=10));new.advance_day({'XRPUSDT':-.30})
        self.assertEqual(new.completion,'NOT_EVALUABLE_UNEXECUTABLE_RISK_REDUCTION')
        self.assertEqual(new.pending.get('XRPUSDT'),None)
        self.assertLess(new.rows_written,20)

    def test_terminal_stays_end_minus6min_exact_five_opens(self):
        w=window(adverse=1.01,zero_after=1433)
        new=simulator(w);new.advance_day({'XRPUSDT':-.02})
        expires=[r for r in new.rejections if r.get('kind')=='TERMINAL' and r.get('reason')=='FIVE_ATTEMPTS_EXPIRED']
        self.assertEqual(len(expires),1);self.assertEqual(expires[0]['event_us'],DAY-MINUTE+1)
        self.assertNotEqual(new.account.positions['XRPUSDT'].quantity,0)
        self.assertFalse(new.result()['summary']['terminal_cash_realized'])

    def test_uses_own_current_equity_and_rejects_stale_mark_clock(self):
        new=simulator(window(stress=.8));new.advance_day({'XRPUSDT':-.02})
        event=next(r for r in new.protective_events if r['kind']=='FULL_EXIT_SIGNAL')
        self.assertIn('stress_assessment',event)
        quiet=simulator(window(adverse=1.01));quiet.advance_day({'XRPUSDT':-.02})
        before=deepcopy(quiet.headroom_coverage);quiet.risk_schedule(DAY+MINUTE)
        self.assertEqual(quiet.headroom_coverage,before)
        image=new.snapshot();bad=deepcopy(image);bad['protective_policy']['feature_binding']={'wrong':'hash'}
        with self.assertRaises(ValueError):HeadroomFullExitSimulator.from_snapshot(bad,new.window,account_class=USDTLinearPerpetualAccount)
        self.assertEqual(new.result()['summary']['protective_policy_id'],POLICY_ID)

if __name__=='__main__':unittest.main(verbosity=2)
