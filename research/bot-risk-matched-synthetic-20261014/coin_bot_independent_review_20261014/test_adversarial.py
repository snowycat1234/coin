"""Independent generated-only adversarial checks for the frozen helper source.

This suite never imports the original financial engine or reads market data.
Run through run_review_checks.py so the candidate and original source hashes
are captured before and after testing.
"""
import copy
from dataclasses import replace
from decimal import Decimal
import sys
from pathlib import Path
import unittest

CANDIDATE = Path(__file__).resolve().parent.parent / 'coin_bot_risk_matched_synthetic_20261014'
sys.path.insert(0, str(CANDIDATE))
from grid_policy import CompletedClose, CompletedMinute, FixedGrid, MINUTE_US, STEP, compose_target, replacement_weight, weekly_plan
from risk_gate import CANONICAL_CONTRACT, Envelope, REQUIRED_CONTRACT, REQUIRED_METRICS, assess_intent_envelope, certify_risk_match, path_metrics

DAY = 1440*MINUTE_US
T = 100*DAY
BASE = (.2,.1,-.1,0.,0.)
COV = tuple(tuple(.04 if i==j else 0. for j in range(5)) for i in range(5))

def tape(t=T):
    return [CompletedClose(t-(29-i)*DAY, Decimal(90 if i%2==0 else 110), t-(29-i)*DAY) for i in range(30)]

def obs(t=T,p=100,*,available=None,end=None):
    return CompletedMinute(t if available is None else available,Decimal(str(p)),t if end is None else end)

def grid(t=T):
    return FixedGrid(tape(t),t,obs(t),200)

def fill(g,i,qty=None,t=None,**kw):
    args=dict(order_id=i.order_id,side=i.side,fill_id=i.order_id+':fill')
    args.update(kw)
    return g.on_fill(i.slot,i.quantity if qty is None else qty,i.not_before_us if t is None else t,**args)

def risk(**kw):
    x=dict(original_weights=BASE,retained_legs=((.18,.1,-.1,0.,0.),),grid_owned_weight=(0.,)*5,
           grid_unfilled_buy_weight=(.02,0.,0.,0.,0.),annual_covariance=COV,
           previous_quote_volume=(1e6,)*5,requested_notional=(200.,0.,0.,0.,0.),
           free_cash=6000.,reserved_cash=201.,valuation_nav=10000.)
    x.update(kw)
    return assess_intent_envelope(**x)

def report():
    return dict(evidence_origin='ORIGINAL_NATIVE_ENGINE_COMPLETE_LEDGER',complete_calendar=True,paid_flat=True,
        contract={**{k:'GENERATED_TEST_IDENTITY' for k in REQUIRED_CONTRACT},**CANONICAL_CONTRACT},
        metrics={k:0. for k in REQUIRED_METRICS})

class GridAdversarial(unittest.TestCase):
    def rejects_without_change(self,g,f):
        before=copy.deepcopy(g.__dict__)
        with self.assertRaises(ValueError): f()
        self.assertEqual(before,g.__dict__)

    def test_paid_initial_inventory_never_appears_on_intent(self):
        g=grid();a=g.intents(T,obs())
        self.assertEqual(2,len(a));self.assertEqual(0,g.inventory())
        self.assertTrue(all(i.side=='BUY' and i.reason=='PAID_INITIAL_INVENTORY' for i in a))
        self.assertEqual([],g.intents(T,obs()))

    def test_frozen_quantity_full_budget_and_step(self):
        g=grid();q=g.quantity
        self.assertEqual(0,q%STEP)
        self.assertLessEqual(4*q*g.upper*Decimal('1.00135044'),g.budget)
        for k,p in enumerate((100,110,90,110,90,110)):
            for i in g.intents(T+2*k*MINUTE_US,obs(T+2*k*MINUTE_US,p)):fill(g,i)
        self.assertEqual(q,g.quantity)

    def test_replacement_only_after_actual_complete_fill(self):
        g=grid();a=g.intents(T,obs())[0]
        self.assertEqual([],g.intents(T+MINUTE_US,obs(T+MINUTE_US,110)))
        self.assertEqual(0,g.inventory())
        fill(g,a,t=T+MINUTE_US+1)
        b=[x for x in g.intents(T+2*MINUTE_US,obs(T+2*MINUTE_US,110)) if x.slot==a.slot][0]
        self.assertEqual('SELL',b.side);self.assertNotEqual(a.order_id,b.order_id)

    def test_same_signal_and_preeligible_fill_atomic(self):
        g=grid();a=g.intents(T,obs())[0]
        for t in (T,a.not_before_us-1):
            self.rejects_without_change(g,lambda t=t:fill(g,a,t=t))

    def test_wrong_side_order_slot_or_duplicate_atomic(self):
        for bad in ({'side':'SELL'},{'order_id':'foreign-order'},{'fill_id':''},{'fill_id':False}):
            g=grid();a=g.intents(T,obs())[0]
            self.rejects_without_change(g,lambda bad=bad:fill(g,a,**bad))
        g=grid();a=g.intents(T,obs())[0]
        self.rejects_without_change(g,lambda:g.on_fill(True,a.quantity,a.not_before_us,order_id=a.order_id,side=a.side,fill_id='bool-slot'))
        half=(a.quantity/2).quantize(STEP);fill(g,a,qty=half)
        self.rejects_without_change(g,lambda:fill(g,a,qty=half,t=a.not_before_us+1))

    def test_invalid_fill_quantities_atomic(self):
        for qty in (Decimal(0),-STEP,Decimal('0.000000001'),True,Decimal('NaN'),Decimal('1E999')):
            g=grid();a=g.intents(T,obs())[0]
            self.rejects_without_change(g,lambda qty=qty:fill(g,a,qty=qty))
        g=grid();a=g.intents(T,obs())[0]
        self.rejects_without_change(g,lambda:fill(g,a,qty=a.quantity+STEP))

    def test_old_cancel_after_full_fill_cannot_clear_new_sell(self):
        g=grid();a=g.intents(T,obs())[0];fill(g,a)
        b=[x for x in g.intents(T+2*MINUTE_US,obs(T+2*MINUTE_US,110)) if x.slot==a.slot][0]
        self.rejects_without_change(g,lambda:g.on_cancel_confirmed(a.slot,order_id=a.order_id,cancel_us=b.not_before_us))
        self.rejects_without_change(g,lambda:fill(g,a,t=b.not_before_us,fill_id='late-old-fill'))
        self.assertEqual(b.order_id,g.pending[b.slot].order_id)

    def test_partial_cancel_reissue_rejects_delayed_old_callbacks(self):
        g=grid();a=g.intents(T,obs())[0];half=(a.quantity/2).quantize(STEP)
        fill(g,a,qty=half)
        g.on_cancel_confirmed(a.slot,order_id=a.order_id,cancel_us=a.not_before_us+1)
        self.assertEqual(half,g.inventory())
        b=[x for x in g.intents(T+2*MINUTE_US,obs(T+2*MINUTE_US)) if x.slot==a.slot][0]
        self.assertEqual(a.quantity-half,b.quantity)
        self.rejects_without_change(g,lambda:g.on_cancel_confirmed(a.slot,order_id=a.order_id,cancel_us=b.not_before_us))
        self.rejects_without_change(g,lambda:fill(g,a,qty=half,t=b.not_before_us,fill_id='late-partial'))
        fill(g,b)
        self.assertEqual(a.quantity,g.inventory())

    def test_recreated_session_rejects_foreign_generation(self):
        old,new=grid(),grid()
        a,b=old.intents(T,obs())[0],new.intents(T,obs())[0]
        self.assertNotEqual(a.session_id,b.session_id)
        self.assertNotEqual(a.order_id,b.order_id)
        self.rejects_without_change(new,lambda:fill(new,a))

    def test_cancel_and_fill_clocks_cannot_rewind(self):
        g=grid();a=g.intents(T,obs())[0]
        g.intents(T+10*MINUTE_US,obs(T+10*MINUTE_US))
        self.rejects_without_change(g,lambda:fill(g,a))
        self.rejects_without_change(g,lambda:g.on_cancel_confirmed(a.slot,order_id=a.order_id,cancel_us=T+MINUTE_US))
        self.rejects_without_change(g,lambda:g.expire(T+MINUTE_US))
        self.rejects_without_change(g,lambda:g.intents(T+9*MINUTE_US,obs(T+9*MINUTE_US)))

    def test_observation_freshness_future_and_conflict_atomic(self):
        g=grid()
        for observation in (obs(T+2*MINUTE_US,available=T,end=T),obs(T+2*MINUTE_US,available=T+2*MINUTE_US+1),
                            obs(T+2*MINUTE_US,available=T+2*MINUTE_US,end=T+2*MINUTE_US+1),obs(T+2*MINUTE_US,p=0),
                            obs(T,p=101),100,CompletedMinute(True,Decimal(100),True)):
            self.rejects_without_change(g,lambda observation=observation:g.intents(T+2*MINUTE_US,observation))

    def test_initial_price_requires_completed_fresh_observation(self):
        for observation in (100,obs(T,available=T-MINUTE_US-1,end=T-MINUTE_US-1),obs(T,available=T+1),obs(T,p=0)):
            with self.assertRaises(ValueError):FixedGrid(tape(),T,observation,200)

    def test_future_stale_missing_duplicate_or_nonpositive_daily_tape(self):
        invalid=[]
        x=tape();x[-1]=replace(x[-1],available_us=T+1);invalid.append(x)
        x=tape();x[-1]=replace(x[-1],bar_end_us=T+1);invalid.append(x)
        invalid.extend((tape(T-2*DAY),tape()[:-1],tape()+[tape()[-1]]))
        x=tape();x[2]=x[1];invalid.append(x)
        x=tape();x[3]=replace(x[3],price=Decimal(0));invalid.append(x)
        for x in invalid:
            with self.assertRaises(ValueError):FixedGrid(x,T,obs(),200)

    def test_same_decision_completed_daily_close_is_allowed(self):
        g=grid();self.assertEqual(Decimal(90),g.lower);self.assertEqual(Decimal(110),g.upper)
        self.assertEqual(T,tape()[-1].available_us);self.assertEqual(T,tape()[-1].bar_end_us)

    def test_no_buy_with_too_small_budget_or_spacing(self):
        with self.assertRaises(ValueError):FixedGrid(tape(),T,obs(),10)
        narrow=[replace(x,price=Decimal('99.99') if k%2 else Decimal('100.01')) for k,x in enumerate(tape())]
        with self.assertRaises(ValueError):FixedGrid(narrow,T,obs(),200)

    def test_autoexpiry_preserves_executable_orders_inventory_and_reserve(self):
        g=grid();a=g.intents(T,obs());fill(g,a[0],qty=STEP)
        before_owned=g.inventory();pending=copy.deepcopy(g.pending)
        end=g.session_end_us
        self.assertEqual([],g.intents(end,obs(end,105)))
        self.assertTrue(g.expired);self.assertEqual(pending,g.pending)
        self.assertEqual(before_owned,g.inventory());self.assertFalse(g.settled())
        expected=g.inventory()+sum((i.quantity for i in g.pending.values() if i.side=='BUY'),Decimal(0))
        self.assertEqual(expected,g.reserve_quantity())
        remaining=g.pending[a[0].slot]
        fill(g,remaining,t=end+1,fill_id='post-expiry-fill')
        self.assertGreater(g.inventory(),before_owned);self.assertFalse(g.settled())

    def test_last_minute_intent_cannot_execute_beyond_session_end(self):
        g=grid();end=g.session_end_us
        self.assertEqual([],g.intents(end-MINUTE_US,obs(end-MINUTE_US)))
        self.assertTrue(g.expired);self.assertEqual({},g.pending)

    def test_outside_range_does_not_clear_owned_or_pending(self):
        g=grid();a=g.intents(T,obs());fill(g,a[0]);owned=g.inventory();pending=copy.deepcopy(g.pending)
        self.assertEqual([],g.intents(T+2*MINUTE_US,obs(T+2*MINUTE_US,60)))
        self.assertEqual(owned,g.inventory());self.assertEqual(pending,g.pending)

    def test_pending_sell_never_frees_owned_risk(self):
        g=grid();a=g.intents(T,obs())[0];fill(g,a)
        b=[x for x in g.intents(T+2*MINUTE_US,obs(T+2*MINUTE_US,110)) if x.slot==a.slot][0]
        owned=g.inventory();g.expire(T+2*MINUTE_US)
        self.assertGreaterEqual(g.reserve_quantity(),owned)
        self.assertEqual(owned,g.inventory());self.assertEqual('SELL',b.side)
        fill(g,b)
        self.assertLess(g.inventory(),owned)

    def test_settled_requires_no_inventory_and_no_pending(self):
        g=grid();self.assertTrue(g.settled())
        a=g.intents(T,obs());self.assertFalse(g.settled());g.expire(T)
        for i in a:g.on_cancel_confirmed(i.slot,order_id=i.order_id,cancel_us=T)
        self.assertTrue(g.settled())

    def test_weekly_gate_and_other_original_shorts_preserved(self):
        from datetime import datetime,timezone
        monday=int(datetime(2026,10,12,tzinfo=timezone.utc).timestamp())*1_000_000
        g=weekly_plan(tape(monday),monday,obs(monday),10000,BASE)
        self.assertIsNotNone(g)
        with self.assertRaises(ValueError):weekly_plan(tape(monday+MINUTE_US),monday+MINUTE_US,obs(monday+MINUTE_US),10000,BASE)
        self.assertIsNone(weekly_plan(tape(monday),monday,obs(monday),10000,(-.2,.1,-.1,0.,0.)))
        self.assertEqual(0,replacement_weight((-.2,.1,-.1,0.,0.)))
        target=compose_target(BASE,.02,1,100,10000)
        self.assertEqual(BASE[1:],target[1:]);self.assertAlmostEqual(.19,target[0])
        with self.assertRaises(ValueError):compose_target(BASE,.1,1,100,10000)

class RiskAdversarial(unittest.TestCase):
    def test_helper_math_never_certifies_native_wallet(self):
        r=risk();self.assertTrue(r.math_valid);self.assertFalse(r.allowed)
        self.assertEqual('NOT_CERTIFIED_NEEDS_NATIVE_BINDING',r.status)
        self.assertIn('NEEDS_NATIVE_BINDING',r.reasons)

    def test_missing_other_original_legs_or_shorts_fail(self):
        for legs in ((),((.18,0.,0.,0.,0.),),((.18,.1,0.,0.,0.),)):
            r=risk(retained_legs=legs)
            self.assertFalse(r.math_valid);self.assertIn('ORIGINAL_REPLACEMENT_LINEAGE_MISMATCH',r.reasons)

    def test_unfunded_cash_and_request_inputs_fail(self):
        r=risk(free_cash=0.,reserved_cash=0.,requested_notional=(0.,)*5)
        self.assertFalse(r.math_valid)
        self.assertIn('GRID_BUY_RESERVATION_NOTIONAL_UNFUNDED',r.reasons)
        self.assertIn('OUTSTANDING_BUY_NOTIONAL_UNBOUND',r.reasons)

    def test_shared_cash_and_capacity_fail(self):
        self.assertIn('SHARED_CASH_RESERVATION_EXCEEDS_FREE_CASH',risk(free_cash=100.).reasons)
        self.assertIn('SHARED_PRIOR_MINUTE_CAPACITY',risk(previous_quote_volume=(1.,)*5).reasons)
        r=risk(requested_notional=(1200.,0.,0.,0.,0.))
        self.assertIn('SHARED_PRIOR_MINUTE_CAPACITY',r.reasons)

    def test_opposing_legs_cannot_erase_gross(self):
        r=risk(retained_legs=((.18,.1,-.1,0.,0.),(.3,0.,0.,0.,0.),(-.3,0.,0.,0.,0.)))
        self.assertFalse(r.math_valid);self.assertGreater(r.worst_reserved_gross,.6)
        self.assertIn('GROSS_CAP_OR_BASELINE_ENVELOPE',r.reasons)

    def test_all_fill_vertices_guard_absolute_net_hedge(self):
        r=risk(original_weights=(.2,-.2,0.,0.,0.),retained_legs=((.18,-.2,0.,0.,0.),))
        self.assertFalse(r.math_valid);self.assertIn('ABS_NET_BASELINE_ENVELOPE',r.reasons)

    def test_owned_plus_unfilled_buy_are_counted_together(self):
        r=risk(grid_owned_weight=(.02,0.,0.,0.,0.))
        self.assertFalse(r.math_valid);self.assertGreater(r.worst_reserved_gross,.4)
        self.assertIn('ASSET_CAP_OR_BASELINE_ENVELOPE',r.reasons)

    def test_unknown_asymmetric_singular_covariance_fails_closed(self):
        bad=[None,((0.,)*5,)*5,((float('nan'),)*5,)*5]
        x=[list(row) for row in COV];x[0][1]=.01;bad.append(x)
        for cov in bad:
            r=risk(annual_covariance=cov);self.assertFalse(r.math_valid);self.assertFalse(r.allowed)

    def test_noncanonical_envelope_and_bool_numeric_fail(self):
        for env in (Envelope(leverage=2.),Envelope(initial_capital=20000.),Envelope(gross_cap=.7)):
            self.assertFalse(risk(envelope=env).math_valid)
        for kw in ({'valuation_nav':True},{'grid_owned_weight':(False,)*5},{'free_cash':True},{'reserved_cash':True}):
            r=risk(**kw);self.assertFalse(r.math_valid);self.assertFalse(r.allowed)

    def test_favorable_arbitrary_full_report_never_certifies(self):
        a=report();r=certify_risk_match(a,a)
        self.assertEqual('NOT_CERTIFIED_NEEDS_NATIVE_BINDING',r['status'])
        self.assertFalse(r['native_snapshot_verified']);self.assertTrue(r['not_a_future_risk_guarantee'])

    def test_string_or_integer_calendar_and_paidflat_flags_fail(self):
        for field in ('complete_calendar','paid_flat'):
            for value in ('False',1,0,None,False):
                a=report();a[field]=value
                self.assertEqual('INCONCLUSIVE',certify_risk_match(a,a)['status'])

    def test_no_topup_and_contract_cannot_use_bool_coercion(self):
        a=report();a['contract']['no_topup']=1
        self.assertEqual('FAIL',certify_risk_match(a,a)['status'])
        a=report();a['contract']['leverage']=True
        self.assertEqual('FAIL',certify_risk_match(a,a)['status'])

    def test_synthetic_origin_missing_identity_or_metric_fail(self):
        for mutation in ('synthetic','identity','metric'):
            a=report()
            if mutation=='synthetic':a['evidence_origin']='SYNTHETIC_FIXTURE'
            elif mutation=='identity':a['contract']['source_identity']=' '
            else:del a['metrics']['minute_mdd']
            self.assertEqual('INCONCLUSIVE',certify_risk_match(a,a)['status'])

    def test_malformed_reports_fail_closed_instead_of_crashing(self):
        for a in (None,[],True,{}, {'metrics':None},{'contract':None}):
            self.assertEqual('INCONCLUSIVE',certify_risk_match(a,a)['status'])

    def test_each_worse_risk_endpoint_fails(self):
        for key in REQUIRED_METRICS:
            a=report();b=copy.deepcopy(a);b['metrics'][key]=.01
            r=certify_risk_match(a,b)
            self.assertEqual('FAIL',r['status']);self.assertIn('WORSE_'+key.upper(),r['reasons'])

    def test_actual_caps_apply_even_if_control_also_breaches(self):
        for key,value,reason in (('max_gross',.6233,'ACTUAL_EXPOSURE_CAP_BREACH'),
                                 ('max_asset_gross',.31,'ACTUAL_EXPOSURE_CAP_BREACH'),
                                 ('daily_annual_vol',.11,'ACTUAL_VOL_CAP_BREACH')):
            a=report();a['metrics'][key]=value;r=certify_risk_match(a,a)
            self.assertEqual('FAIL',r['status']);self.assertIn(reason,r['reasons'])

    def test_unequal_cost_funding_capital_terminal_contracts_fail(self):
        for key,value in (('initial_capital',20000.),('cost_id','SPOT'),('fee_bps',10.),
                           ('funding_convention','NONE'),('terminal_opens',0)):
            a=report();b=copy.deepcopy(a);b['contract'][key]=value
            self.assertEqual('FAIL',certify_risk_match(a,b)['status'])

    def test_residual_halt_ruin_unfilled_never_cash_return(self):
        for key in ('halt_count','ruin_count','residual_notional','unfilled_risk_count'):
            a=report();a['metrics'][key]=1
            r=certify_risk_match(a,a)
            self.assertEqual('FAIL',r['status']);self.assertIn('HALT_RUIN_RESIDUAL_OR_UNFILLED_RISK',r['reasons'])

    def test_invalid_metrics_do_not_pass(self):
        for value in (True,-.01,float('nan'),float('inf'),'0'):
            a=report();a['metrics']['minute_mdd']=value
            self.assertEqual('INCONCLUSIVE',certify_risk_match(a,a)['status'])

    def test_daily_metrics_are_descriptive_and_keep_inventory_loss(self):
        x=path_metrics([10000.-20*k for k in range(40)])
        self.assertNotIn('minute_mdd',x);self.assertGreater(x['daily_observed_mdd'],0)
        self.assertGreater(x['worst_30d_loss'],0);self.assertEqual(-35,(95-90)+(60-100))

if __name__=='__main__':unittest.main(verbosity=2)
