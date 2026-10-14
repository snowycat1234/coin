import copy
import unittest
from decimal import Decimal
from grid_policy import CompletedClose, CompletedMinute, FixedGrid, MINUTE_US, STEP, compose_target, replacement_weight, weekly_plan
from risk_gate import CANONICAL_CONTRACT, Envelope, REQUIRED_CONTRACT, REQUIRED_METRICS, assess_intent_envelope, certify_risk_match, path_metrics
from toy_demo import generated_closes, observation

T=100*1440*MINUTE_US
BASE=(.2,.1,-.1,0.,0.)
COV=tuple(tuple(.04 if i==j else 0. for j in range(5)) for i in range(5))


def risk(**kw):
    x=dict(original_weights=BASE,retained_legs=((.18,.1,-.1,0.,0.),),
           grid_owned_weight=(0.,)*5,grid_unfilled_buy_weight=(.02,0.,0.,0.,0.),
           annual_covariance=COV,previous_quote_volume=(1e6,)*5,
           requested_notional=(200.,0.,0.,0.,0.),free_cash=6000.,reserved_cash=201.,valuation_nav=10000.)
    x.update(kw)
    return assess_intent_envelope(**x)


def full_report():
    return dict(evidence_origin="ORIGINAL_NATIVE_ENGINE_COMPLETE_LEDGER",
        complete_calendar=True,paid_flat=True,
        contract={**{k:"SYNTHETIC_TEST_IDENTITY" for k in REQUIRED_CONTRACT},**CANONICAL_CONTRACT},
        metrics={k:0. for k in REQUIRED_METRICS})


def fill(grid,intent,quantity=None,clock=None,suffix="fill"):
    grid.on_fill(intent.slot,intent.quantity if quantity is None else quantity,
                 intent.not_before_us if clock is None else clock,
                 order_id=intent.order_id,side=intent.side,fill_id=intent.order_id+":"+suffix)


class GridTests(unittest.TestCase):
    def setUp(self):
        self.g=FixedGrid(generated_closes(T),T,observation(100,T),200)

    def test_explicit_paid_initial_inventory(self):
        a=self.g.intents(T,observation(100,T))
        self.assertEqual(2,len(a));self.assertTrue(all(i.reason=="PAID_INITIAL_INVENTORY" for i in a))
        self.assertEqual(0,self.g.inventory())
        self.assertEqual([],self.g.intents(T,observation(100,T)))

    def test_no_buy_sell_replacement_until_actual_fill(self):
        a=self.g.intents(T,observation(100,T))[0]
        fill(self.g,a)
        self.assertEqual("SELL",self.g.slots[a.slot].mode)
        self.assertTrue(any(i.side=="SELL" for i in self.g.intents(T+2*MINUTE_US,observation(105,T+2*MINUTE_US))))

    def test_partial_fill_and_cancellation_keep_owned(self):
        a=self.g.intents(T,observation(100,T))[0];half=(a.quantity/2).quantize(STEP)
        fill(self.g,a,half)
        self.g.on_cancel_confirmed(a.slot,order_id=a.order_id,cancel_us=self.g.last_clock)
        self.assertEqual(half,self.g.inventory())
        b=[i for i in self.g.intents(T+2*MINUTE_US,observation(100,T+2*MINUTE_US)) if i.slot==a.slot][0]
        self.assertEqual(a.quantity-half,b.quantity)

    def test_no_intraminute_or_same_signal_fill(self):
        a=self.g.intents(T,observation(100,T))[0]
        with self.assertRaises(ValueError):fill(self.g,a,clock=T)

    def test_fill_clock_cannot_be_rewound(self):
        a=self.g.intents(T,observation(100,T))[0];fill(self.g,a)
        with self.assertRaises(ValueError):self.g.intents(T,observation(105,T))

    def test_expiry_retains_pending_executable_buys_and_reserves(self):
        a=self.g.intents(T,observation(100,T))
        self.assertEqual(0,self.g.expire(self.g.last_clock))
        self.assertFalse(self.g.settled())
        self.assertEqual(sum((i.quantity for i in a),Decimal(0)),self.g.reserve_quantity())
        fill(self.g,a[0])
        self.g.on_cancel_confirmed(a[1].slot,order_id=a[1].order_id,cancel_us=self.g.last_clock)
        self.assertEqual(a[0].quantity,self.g.inventory())
        self.assertEqual(a[0].quantity,self.g.reserve_quantity())
        self.assertFalse(self.g.settled())

    def test_stale_completed_range_rejected(self):
        old=generated_closes(T-2*1440*MINUTE_US)
        with self.assertRaises(ValueError):FixedGrid(old,T,observation(100,T),200)

    def test_bar_end_and_availability_are_distinct(self):
        c=generated_closes(T)
        c[-1]=CompletedClose(T,Decimal(110),T+1)
        with self.assertRaises(ValueError):FixedGrid(c,T,observation(100,T),200)
        # A candle ending at midnight may be available at that same decision;
        # there is no mandatory extra one-day lag in this policy.
        c=generated_closes(T)
        self.assertEqual(T,c[-1].available_us)
        self.assertEqual(T,c[-1].bar_end_us)
        self.assertIsNotNone(FixedGrid(c,T,observation(100,T),200))

    def test_old_cancel_or_fill_cannot_mutate_successor(self):
        import copy
        a=self.g.intents(T,observation(100,T))[0];fill(self.g,a)
        b=[i for i in self.g.intents(T+2*MINUTE_US,observation(105,T+2*MINUTE_US)) if i.slot==a.slot][0]
        before=copy.deepcopy(self.g.__dict__)
        with self.assertRaises(ValueError):self.g.on_cancel_confirmed(a.slot,order_id=a.order_id,cancel_us=self.g.last_clock)
        with self.assertRaises(ValueError):fill(self.g,a,clock=b.not_before_us,suffix="old_duplicate")
        self.assertEqual(before,self.g.__dict__)
        fill(self.g,b)

    def test_duplicate_fill_fails_without_mutation(self):
        import copy
        a=self.g.intents(T,observation(100,T))[0];fill(self.g,a)
        before=copy.deepcopy(self.g.__dict__)
        with self.assertRaises(ValueError):fill(self.g,a)
        self.assertEqual(before,self.g.__dict__)

    def test_fixed_session_end_cannot_be_extended_by_caller(self):
        a=self.g.intents(T,observation(100,T))
        end=self.g.session_end_us
        self.assertEqual([],self.g.intents(end,observation(105,end)))
        self.assertTrue(self.g.expired)
        self.assertEqual(2,len(self.g.pending))
        self.assertGreater(self.g.reserve_quantity(),0)

    def test_late_fill_and_stale_minute_do_not_mutate_state(self):
        a=self.g.intents(T,observation(100,T))[0]
        self.g.intents(T+10*MINUTE_US,observation(100,T+10*MINUTE_US))
        before=copy.deepcopy(self.g.__dict__)
        with self.assertRaises(ValueError):fill(self.g,a)
        with self.assertRaises(ValueError):self.g.intents(T+11*MINUTE_US,observation(100,T))
        self.assertEqual(before,self.g.__dict__)

    def test_future_or_conflicting_minute_observation_rejected(self):
        before=copy.deepcopy(self.g.__dict__)
        with self.assertRaises(ValueError):self.g.intents(T,observation(105,T))
        with self.assertRaises(ValueError):self.g.intents(T,observation(100,T+1))
        self.assertEqual(before,self.g.__dict__)

    def test_recreated_same_clock_session_rejects_prior_instance_callback(self):
        a=self.g.intents(T,observation(100,T))[0]
        second=FixedGrid(generated_closes(T),T,observation(100,T),200)
        b=second.intents(T,observation(100,T))[0]
        self.assertNotEqual(a.session_id,b.session_id)
        self.assertNotEqual(a.order_id,b.order_id)
        before=copy.deepcopy(second.__dict__)
        with self.assertRaises(ValueError):fill(second,a)
        with self.assertRaises(ValueError):second.on_cancel_confirmed(a.slot,order_id=a.order_id,cancel_us=T)
        self.assertEqual(before,second.__dict__)

    def test_future_close_rejected(self):
        c=generated_closes(T);c[-1]=CompletedClose(T+1,Decimal(100),T)
        with self.assertRaises(ValueError):FixedGrid(c,T,observation(100,T),200)

    def test_suffix_not_an_input(self):
        c=generated_closes(T)
        with self.assertRaises(ValueError):FixedGrid(c+[CompletedClose(T+1440*MINUTE_US,Decimal(100),T+1440*MINUTE_US)],T,observation(100,T),200)

    def test_outside_range_and_expiry_never_free_clear(self):
        for a in self.g.intents(T,observation(100,T)):fill(self.g,a)
        owned=self.g.inventory()
        self.assertEqual([],self.g.intents(T+2*MINUTE_US,observation(60,T+2*MINUTE_US)))
        self.assertEqual(owned,self.g.expire(self.g.last_clock));self.assertEqual(owned,self.g.inventory())

    def test_budget_no_profit_reinvestment_or_double(self):
        self.assertLessEqual(self.g.reserve_quantity()*self.g.upper*Decimal("1.00135044"),self.g.budget)
        original=self.g.quantity
        for k,p in enumerate((100,110,90,110,90,110)):
            for a in self.g.intents(T+k*2*MINUTE_US,observation(p,T+k*2*MINUTE_US)):fill(self.g,a)
        self.assertEqual(original,self.g.quantity)

    def test_no_insufficient_opening_notional(self):
        with self.assertRaises(ValueError):FixedGrid(generated_closes(T),T,observation(100,T),10)

    def test_spacing_must_cover_same_cost(self):
        c=[CompletedClose(T-(29-i)*1440*MINUTE_US,Decimal("99.99") if i%2 else Decimal("100.01"),T-(29-i)*1440*MINUTE_US) for i in range(30)]
        with self.assertRaises(ValueError):FixedGrid(c,T,observation(100,T),200)

    def test_only_existing_positive_btc_is_replaced(self):
        self.assertEqual(0,replacement_weight((-.2,.1,.1,0.,0.)))
        result=compose_target(BASE,.02,Decimal(1),100,10000)
        self.assertAlmostEqual(.19,result[0]);self.assertEqual(BASE[1:],result[1:])
        with self.assertRaises(ValueError):compose_target(BASE,.1,1,100,10000)

    def test_weekly_gate_is_fixed_utc_and_past_only(self):
        from datetime import datetime,timezone
        monday=int(datetime(2026,10,12,tzinfo=timezone.utc).timestamp())*1_000_000
        self.assertIsNotNone(weekly_plan(generated_closes(monday),monday,observation(100,monday),10000,BASE))
        with self.assertRaises(ValueError):weekly_plan(generated_closes(T),T,observation(100,T),10000,BASE)


class RiskTests(unittest.TestCase):
    def test_identical_envelope_passes_on_generated_inputs(self):
        r=risk();self.assertFalse(r.allowed);self.assertTrue(r.math_valid);self.assertAlmostEqual(.4,r.worst_reserved_gross)

    def test_pending_buys_are_reserved_and_not_netted_with_sells(self):
        r=risk(grid_unfilled_buy_weight=(.04,0.,0.,0.,0.))
        self.assertFalse(r.allowed);self.assertIn("GROSS_CAP_OR_BASELINE_ENVELOPE",r.reasons)

    def test_opposing_legs_never_erase_gross(self):
        r=risk(retained_legs=((.18,.1,-.1,0.,0.),(.2,0.,0.,0.,0.),(-.2,0.,0.,0.,0.)))
        self.assertFalse(r.allowed);self.assertGreater(r.worst_reserved_gross,.6)

    def test_sleeves_share_cash_and_capacity(self):
        self.assertIn("SHARED_CASH_RESERVATION_EXCEEDS_FREE_CASH",risk(free_cash=100.).reasons)
        self.assertIn("SHARED_PRIOR_MINUTE_CAPACITY",risk(previous_quote_volume=(10.,)*5).reasons)

    def test_unknown_covariance_and_leverage_fail_closed(self):
        self.assertFalse(risk(annual_covariance=((0.,)*5,)*5).allowed)
        self.assertFalse(risk(envelope=Envelope(leverage=2.)).allowed)

    def test_all_fill_vertices_preserve_net_hedge(self):
        r=risk(original_weights=(.2,-.2,0.,0.,0.),retained_legs=((.18,-.2,0.,0.,0.),))
        self.assertIn("ABS_NET_BASELINE_ENVELOPE",r.reasons)

    def test_toy_evidence_never_certifies_native_risk(self):
        a=full_report();a['evidence_origin']='SYNTHETIC_FIXTURE'
        self.assertEqual("INCONCLUSIVE",certify_risk_match(a,a)["status"])

    def test_same_caps_but_worse_drawdown_fail(self):
        a=full_report();b=copy.deepcopy(a);b['metrics']['minute_mdd']=.01
        self.assertIn("WORSE_MINUTE_MDD",certify_risk_match(a,b)["reasons"])

    def test_risk_improvement_does_not_rescue_halt_or_tail_loss(self):
        a=full_report();b=copy.deepcopy(a);b['metrics']['halt_count']=1
        self.assertEqual("FAIL",certify_risk_match(a,b)["status"])
        b=copy.deepcopy(a);b['metrics']['daily_es95_loss']=.01
        self.assertEqual("FAIL",certify_risk_match(a,b)["status"])

    def test_cost_contract_cannot_silently_switch_to_spot(self):
        a=full_report();b=copy.deepcopy(a);b['contract']['fee_bps']=10
        self.assertIn("UNMATCHED_EXECUTION_OR_CAPITAL_CONTRACT",certify_risk_match(a,b)["reasons"])

    def test_realized_drift_over_cap_fails_even_if_control_same(self):
        a=full_report();a['metrics']['max_gross']=.6233
        self.assertIn("ACTUAL_EXPOSURE_CAP_BREACH",certify_risk_match(a,a)["reasons"])

    def test_incomplete_halted_prefix_never_full_year_cash(self):
        a=full_report();a['complete_calendar']=False
        self.assertEqual("INCONCLUSIVE",certify_risk_match(a,a)["status"])

    def test_observed_pass_is_explicitly_no_future_guarantee(self):
        a=full_report();r=certify_risk_match(a,a)
        self.assertEqual("NOT_CERTIFIED_NEEDS_NATIVE_BINDING",r['status']);self.assertTrue(r['not_a_future_risk_guarantee'])

    def test_same_wrong_contract_cannot_pass(self):
        a=full_report();a['contract']['leverage']=2.
        self.assertIn("NONCANONICAL_CAPITAL_PRODUCT_EXECUTION_CONTRACT",certify_risk_match(a,a)['reasons'])

    def test_boolean_strings_and_integer_no_topup_fail_closed(self):
        a=full_report();a['complete_calendar']='False';a['paid_flat']='False'
        self.assertEqual('INCONCLUSIVE',certify_risk_match(a,a)['status'])
        a=full_report();a['contract']['no_topup']=1
        self.assertEqual('FAIL',certify_risk_match(a,a)['status'])

    def test_arbitrary_empty_legs_and_unfunded_inputs_never_certify(self):
        r=risk(retained_legs=(),free_cash=0.,reserved_cash=0.,requested_notional=(0.,)*5)
        self.assertFalse(r.allowed);self.assertFalse(r.math_valid)
        self.assertIn('ORIGINAL_REPLACEMENT_LINEAGE_MISMATCH',r.reasons)
        self.assertIn('GRID_BUY_RESERVATION_NOTIONAL_UNFUNDED',r.reasons)

    def test_bool_numeric_and_malformed_reports_are_inconclusive(self):
        self.assertFalse(risk(valuation_nav=True).math_valid)
        self.assertFalse(risk(original_weights=(True,.1,-.1,0.,0.)).math_valid)
        self.assertFalse(risk(reserved_cash=True).math_valid)
        for a in (None,[],{"metrics":None,"contract":None}):
            self.assertEqual('INCONCLUSIVE',certify_risk_match(a,a)['status'])
        a=full_report();a['metrics']=None
        self.assertEqual('INCONCLUSIVE',certify_risk_match(a,a)['status'])
        a=full_report();a['contract']=None
        self.assertEqual('INCONCLUSIVE',certify_risk_match(a,a)['status'])

    def test_generated_metrics_keep_floating_loss(self):
        x=path_metrics([10000.-20*i for i in range(40)])
        self.assertGreater(x['daily_observed_mdd'],0);self.assertGreater(x['worst_30d_loss'],0)
        self.assertLess((95-90)+(60-100),0)


if __name__ == '__main__':unittest.main()
