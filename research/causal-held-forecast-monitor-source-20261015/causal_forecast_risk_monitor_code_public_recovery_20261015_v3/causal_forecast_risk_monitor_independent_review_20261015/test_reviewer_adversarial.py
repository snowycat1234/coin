"""Additional reviewer-generated native priority and identity probes only."""
from copy import deepcopy
from decimal import Decimal as D
import unittest
from unittest.mock import patch
import numpy as np
from generated_helpers import (f, make_sim, make_account, mark, seed_paid, market,
    set_capacity, trigger, quantities, finance, synthetic_source)

class ReviewerPriorityTests(unittest.TestCase):
    def test_late_actual_hard_cap_preempts_owned_forecast_before_native_planning(self):
        sim,g,_=make_sim(.401)
        a=sim.account
        seed_paid(a,{'BTCUSDT':'.05'},sim.start)
        set_capacity(sim,dict.fromkeys(f.S,D(0)))
        born,r=trigger(sim)
        self.assertEqual(a._forecast_active['targets']['BTCUSDT'],D('.049'))
        owned={s:o['order_id'] for s,o in sim.pending.items()}
        late=born+f.MINUTE
        mark(a,late,{'BTCUSDT':70000})
        self.assertEqual(a.status,'BOUND_BREACH_REDUCTION_REQUIRED')
        before=finance(a)
        sim.risk_schedule(late)
        # Exact original native hard-cap arithmetic, no new cap calculation.
        n=abs(a.positions['BTCUSDT'].quantity)*a._mark('BTCUSDT')
        scale=min(D(1),a.config.max_asset_weight*D('.99')*a.nav()/n,
                  a.config.max_gross_weight*D('.99')*a.nav()/n)
        self.assertEqual(sim.pending['BTCUSDT']['target'],a.positions['BTCUSDT'].quantity*scale)
        self.assertLess(sim.pending['BTCUSDT']['target'],D('.049'))
        self.assertIsNone(a._forecast_active)
        self.assertEqual(finance(a),before)
        self.assertTrue(all(o['order_id']!=owned[s] for s,o in sim.pending.items()))
        self.assertTrue(any(b['phase']=='ACTUAL_DRIFT_BEFORE_CAPACITY_LIMITED_REDUCTION' for b in sim.breaches))

    def test_late_D_protection_keeps_full_exit_through_partial_forecast(self):
        sim,g,_=make_sim(.8)
        a=sim.account
        seed_paid(a,{'BTCUSDT':'-.03'},sim.start)
        set_capacity(sim,{'BTCUSDT':D('.001')})
        born,_=trigger(sim)
        late=born+f.MINUTE
        mark(a,late,{'BTCUSDT':75000})
        sim.risk_schedule(late)
        self.assertEqual(sim.pending['BTCUSDT']['kind'],'PROTECTIVE_STOP')
        self.assertEqual(sim.pending['BTCUSDT']['target'],0)
        sim.attempt(late,market({'BTCUSDT':75000}))
        self.assertEqual(sim.pending['BTCUSDT']['kind'],'PROTECTIVE_STOP')
        self.assertEqual(sim.pending['BTCUSDT']['target'],0)
        self.assertEqual(a._forecast_active['targets']['BTCUSDT'],0)
        self.assertNotIn('BTCUSDT',a._forecast_active['orders'])
        self.assertFalse(a.transfer_journal)

    def test_ordinary_reduction_zero_and_reversal_keep_original_native_eligibility(self):
        for old_target in (D('.01'),D('0'),D('-.01')):
            with self.subTest(old_target=old_target):
                sim,g,_=make_sim(.8,days=2)
                a=sim.account
                seed_paid(a,{'BTCUSDT':'.02'},sim.start)
                set_capacity(sim)
                signal=sim.start+f.DAY
                mark(a,signal)
                target=quantities(a);target['BTCUSDT']=old_target
                g.schedule(target,signal,'DAILY_TARGET')
                old=deepcopy(sim.pending)
                observed=signal+f.MINUTE
                mark(a,observed,{'BTCUSDT':80000})
                before=finance(a);r=sim.risk_schedule(observed)
                self.assertEqual(r['action'],'HOLD')
                self.assertIn('DEFERRED_EXISTING_ORDINARY',r['reason'])
                self.assertEqual(sim.pending,old)
                self.assertEqual(finance(a),before)
                self.assertIsNone(a._forecast_active)
                self.assertIsNone(a._forecast_cache)
                count=len(a.trades)
                sim.attempt(observed,market({'BTCUSDT':80000}))
                paid=list(a.trades)[count:]
                self.assertTrue(paid)
                self.assertEqual(paid[0]['leg'],'CLOSE')
                self.assertEqual(paid[0]['event_us'],signal+f.MINUTE+1)
                self.assertTrue(all(x['event_us']==signal+f.MINUTE+1 for x in paid))
                self.assertEqual(a.positions['BTCUSDT'].quantity,old_target)
                self.assertFalse(a.forecast_journal)
                self.assertFalse(a.transfer_journal)
                self.assertEqual(a._forecast_deferred_ordinary_reduction_count,1)

    def test_deferred_partial_ordinary_close_keeps_id_attempts_and_shared_capacity(self):
        sim,g,_=make_sim(.8,days=2)
        a=sim.account
        seed_paid(a,{'BTCUSDT':'.02'},sim.start)
        set_capacity(sim)
        signal=sim.start+f.DAY
        mark(a,signal)
        target=quantities(a);target['BTCUSDT']=D(0)
        g.schedule(target,signal,'DAILY_TARGET')
        old=deepcopy(sim.pending['BTCUSDT'])
        # Lower genuine previous-completed quote after initial signal admission.
        set_capacity(sim,{'BTCUSDT':D('.005')})
        observed=signal+f.MINUTE
        mark(a,observed,{'BTCUSDT':80000})
        sim.risk_schedule(observed)
        count=len(a.trades)
        sim.attempt(observed,market({'BTCUSDT':80000}))
        paid=list(a.trades)[count:]
        # Frozen quote notional at50000 translates to .003 executable BTC at80000.
        self.assertEqual(sum((D(x['decimal_strings']['quantity']) for x in paid),D(0)),D('.003'))
        self.assertEqual(sim.pending['BTCUSDT']['order_id'],old['order_id'])
        self.assertEqual(sim.pending['BTCUSDT']['signal_us'],old['signal_us'])
        self.assertEqual(sim.pending['BTCUSDT']['attempts'],1)
        self.assertEqual(sim.pending['BTCUSDT']['target'],0)
        mark(a,observed+f.MINUTE,{'BTCUSDT':80000})
        again=deepcopy(sim.pending)
        r=sim.risk_schedule(observed+f.MINUTE)
        self.assertIn('DEFERRED_EXISTING_ORDINARY',r['reason'])
        self.assertEqual(sim.pending,again)
        self.assertIsNone(a._forecast_active)
        self.assertEqual(a._forecast_deferred_ordinary_reduction_count,2)

    def test_missing_owned_order_never_renews_from_unrelated_expiry(self):
        sim,g,_=make_sim(.5)
        a=sim.account
        seed_paid(a,{'BTCUSDT':'.05'},sim.start)
        set_capacity(sim,dict.fromkeys(f.S,D(0)))
        born,_=trigger(sim)
        removed=sim.pending.pop('BTCUSDT')
        sim.rejections.append(dict(order_id='UNRELATED',reason='FIVE_ATTEMPTS_EXPIRED'))
        before=deepcopy(sim.pending)
        sim.forecast_controller.after_attempt(born+f.MINUTE+1)
        self.assertEqual(sim.pending,before)
        self.assertNotIn('BTCUSDT',sim.pending)
        self.assertEqual(a._forecast_active['renewals'],0)
        self.assertEqual(a._forecast_active['orders']['BTCUSDT']['order_id'],removed['order_id'])

    def test_historical_argument_rejected_before_any_base_genesis(self):
        with patch.object(f.E.ExpansionAccount,'__init__',side_effect=AssertionError('GENESIS_CALLED')) as p:
            with self.assertRaisesRegex(ValueError,'HISTORICAL_NO_GO'):
                f.ForecastRiskAccount(historical_scope=object(),generated_scope=f.GENERATED)
            self.assertEqual(p.call_count,0)

    def test_mutated_returned_receipt_cannot_modify_permanent_identity_or_journal(self):
        sim,g,_=make_sim(.5)
        a=sim.account
        seed_paid(a,{'BTCUSDT':'.05'},sim.start)
        born,r=trigger(sim)
        expected=deepcopy(r)
        r['action']='MUTATED_CALLER_VALUE'
        r['target']['BTCUSDT']='999'
        replay=sim.forecast_controller.after_native_risk(born)
        self.assertEqual(replay,expected)
        self.assertEqual(a.forecast_journal[-1]['action'],expected['action'])
        self.assertEqual(a.forecast_journal[-1]['target']['BTCUSDT'],expected['target']['BTCUSDT'])

if __name__=='__main__':unittest.main()
