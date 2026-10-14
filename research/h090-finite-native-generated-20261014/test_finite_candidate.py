"""Generated ownership/candidate regressions, not historical strategy evidence."""
from copy import deepcopy
from decimal import Decimal as D,localcontext
from pathlib import Path
import hashlib,json,unittest
import numpy as np
from generated_fixtures import *
from finite_fixtures import make_candidate,demo_bundle
from finite_candidate import FiniteNativeCandidate
from owner_ledger import BASE,FINITE,BTC,Z,exact
from native_control import H090NativeControl
HERE=Path(__file__).resolve().parent


def prime(sim):
    sim._admit_decision(START,None,None,None,None)
    sim.account.update_marks(START,{s:dict(price=D('100'),close_us=START,available_us=START) for s in S})
    sim.previous_quote=dict.fromkeys(S,10000000.)


def row(price=100.):return {s:{'open':price if s==BTC else 100.,'quote_volume':10000000.} for s in S}


def prepared_two_owner():
    bundle=make_generated(weights=[.05,.05,0,0,0])
    sim=make_candidate(bundle);prime(sim)
    sim.schedule({s:D('10') if s==BTC else Z for s in S},START,'DAILY_TARGET')
    sim.attempt(START+MINUTE,row())
    return sim


class FiniteNativeTests(unittest.TestCase):
    def test_control_finance_clock_cost_and_risk_bytes_immutable(self):
        control=json.loads((HERE/'CONTROL_SOURCE_FREEZE.json').read_text())
        self.assertEqual(hashlib.sha256((HERE/'CONTROL_SOURCE_FREEZE.json').read_bytes()).hexdigest(),
            'cf886908cb2a55537c7ddc1d7e5a73a5a09ed48eff110634cbc59242240ea40f')
        for name,want in control['files_SHA256'].items():
            self.assertEqual(hashlib.sha256((HERE/name).read_bytes()).hexdigest(),want,name)

    def test_first_integrated_four_margin_orders_paid_terminal_one_wallet(self):
        sim=make_candidate(demo_bundle());finish(sim)
        self.assertEqual(sim.program.completed_opening_orders,4)
        self.assertTrue(sim.program.terminal)
        self.assertTrue(all(p.quantity==0 for p in sim.account.positions.values()))
        self.assertEqual(sim.reservations.retired_reservations[FINITE],D('1000'))
        self.assertNotIn(FINITE,sim.reservations.reservations)
        self.assertEqual(sim.reservations.available_initial_capital(),D('1000'))
        self.assertEqual(sim.program.plan.margins(),(D('150'),D('187.50'),D('234.3750'),D('292.968750')))
        total=sum(D(a['quantity'])*D(next(r['decimal_strings']['fill_price'] for r in sim.account.trades
            if r['fill_id']==a['fill_id'] and r['leg']==a['leg'])) for a in sim.owners.fill_allocations
            if a['owner']==FINITE and a['leg']=='OPEN')
        self.assertLessEqual(total,D('864.843750'))
        self.assertGreater(total,D('864.8437'))
        bridge=sim.owners.reconcile(sim.account.engine)
        self.assertFalse(bridge['owner_cash_accounts']);self.assertFalse(bridge['synthetic_cash_transfers'])
        self.assertLess(abs(D(bridge['explicit_decimal_rounding_bridge'])),D('1e-25'))
        self.assertEqual(len(sim.owners.fill_allocations),len(sim.account.trades))
        summary=sim.result()['summary']
        self.assertEqual(summary['covariance_admission'],'COMBINED_OWNER_ACTUAL_PLUS_PENDING_CORNERS_PRE_FILL')
        self.assertEqual(summary['reservation_retired_original_USDT'],{FINITE:'1000'})
        self.assertEqual(summary['total_committed_original_USDT'],'9000')

    def test_newly_fixed_8_over9_control_mapping_direct_preload_finance(self):
        bundle=make_generated(weights=[.06,-.04,.08,0,0])
        control=H090NativeControl(bundle[0],'LONG_SHORT',BASE27,UNIT,source_registry=bundle[3],source_packets=bundle[2],target_factory=bundle[1])
        a=make_candidate(bundle);b=make_candidate(bundle,preloaded=False)
        a.advance_day();b.advance_day(original_csh_weights=dict(zip(S,bundle[-1][0])))
        self.assertEqual(a.target_rows,b.target_rows)
        for item in a.target_rows:
            self.assertEqual(item['target_weight'],float(control.weights[START][item['symbol']]*(8/9)))
        self.assertEqual(a.account.snapshot(),b.account.snapshot())
        self.assertEqual(a.owners.snapshot(),b.owners.snapshot())
        self.assertEqual(a.program.processed_fill_receipts,b.program.processed_fill_receipts)
        self.assertEqual(a.reservations.reservations,b.reservations.reservations)

    def test_first_eligible_positive_decision_only_and_never_restarts(self):
        weights=[[-.05,0,0,0,0],[.05,0,0,0,0],[.05,0,0,0,0]]
        sim=make_candidate(make_generated(days=3,weights=weights))
        sim.advance_day()
        self.assertFalse(sim.program_activated)
        sim.advance_day()
        self.assertTrue(sim.program_activated)
        self.assertEqual(sim.program_activation_signal,START+DAY)
        activations=[e for e in sim.owner_events if e['kind']=='FIRST_ORIGINAL_CAUSALLY_ELIGIBLE_BTC_POSITIVE_PROGRAM_ACTIVATION']
        self.assertEqual(len(activations),1)
        sim.advance_day()
        self.assertEqual(sum(e['kind']=='FIRST_ORIGINAL_CAUSALLY_ELIGIBLE_BTC_POSITIVE_PROGRAM_ACTIVATION' for e in sim.owner_events),1)

    def test_partial_program_receipts_accumulate_one_index_and_share_capacity(self):
        sim=make_candidate(make_generated(weights=[.005,0,0,0,0]));prime(sim)
        sim.schedule({s:D('.25') if s==BTC else Z for s in S},START,'DAILY_TARGET')
        sim.previous_quote=dict.fromkeys(S,50000.) # exactly .5 BTC capacity
        before=len(sim.account.trades);sim.attempt(START+MINUTE,row())
        trades=sim.account.trades[before:]
        self.assertEqual(sum(exact(r,'quantity') for r in trades),D('.5'))
        self.assertEqual(sim.owners.quantity[BASE][BTC],D('.25'))
        self.assertEqual(sim.owners.quantity[FINITE][BTC],D('.25'))
        self.assertEqual(sim.program.completed_opening_orders,0)
        self.assertEqual(sim.program.current_order_filled_margin,D('.25')*D('100.08'))
        fill=next(r for r in trades if sim._fill_owner[r['fill_id']][0]==FINITE)
        state=deepcopy(vars(sim.program));account=sim.account.snapshot()
        request=sim.account.fill_requests[fill['fill_id']]['identity']
        sim.account.execute_fill(**request,fill_id=fill['fill_id'])
        sim.program.record_fill_receipt(sim.account.engine,fill['fill_id'],0)
        self.assertEqual(vars(sim.program),state);self.assertEqual(sim.account.snapshot(),account)
        for n in (2,3,4):sim.attempt(START+n*MINUTE,row())
        self.assertEqual(sim.program.completed_opening_orders,1)
        self.assertIsNone(sim.program_pending)

    def test_different_owner_bases_selective_partial_paid_exit_exact_bridge(self):
        sim=prepared_two_owner()
        sim.account.update_marks(START+2*MINUTE,{s:dict(price=D('90') if s==BTC else D('100'),close_us=START+2*MINUTE,available_us=START+2*MINUTE) for s in S})
        sim._evaluate_program(START+2*MINUTE)
        sim.attempt(START+3*MINUTE,row(90.))
        self.assertEqual(sim.program.completed_opening_orders,2)
        self.assertNotEqual(sim.owners.basis[BASE][BTC],sim.owners.basis[FINITE][BTC])
        base_q=sim.owners.quantity[BASE][BTC];finite_q=sim.owners.quantity[FINITE][BTC]
        sim._retire_program('GENERATED_SELECTIVE_EXIT_TEST',START+4*MINUTE,exit_inventory=True)
        sim.previous_quote=dict.fromkeys(S,50000.)
        sim.attempt(START+5*MINUTE,row(97.))
        self.assertEqual(sim.owners.quantity[BASE][BTC],base_q)
        self.assertGreater(sim.owners.quantity[FINITE][BTC],0)
        self.assertLess(sim.owners.quantity[FINITE][BTC],finite_q)
        bridge=sim.owners.reconcile(sim.account.engine)
        self.assertNotEqual(D(bridge['native_realized_classification_bridge']),0)
        with localcontext() as ctx:
            ctx.prec=40
            classification=D(bridge['native_realized_classification_bridge'])+D(bridge['native_unrealized_classification_bridge'])
            self.assertLess(abs(classification),D('1e-25'))
        self.assertLess(abs(D(bridge['explicit_decimal_rounding_bridge'])),D('1e-25'))
        self.assertTrue(all(a['owner']==FINITE for a in sim.owners.fill_allocations if a['leg']=='CLOSE'))

    def test_funding_allocates_actual_owners_and_retains_rounding_bridge(self):
        sim=prepared_two_owner()
        event=START+2*MINUTE+1
        funded=sim.account.apply_funding(BTC,'GENERATED_OWNER_FUNDING',event,D('.003'),START)
        sim._flush_account()
        allocated=[a for a in sim.owners.funding_allocations if a['event_id']=='GENERATED_OWNER_FUNDING']
        self.assertEqual(len(allocated),2)
        self.assertEqual(sum(D(a['signed_native_funding_allocated']) for a in allocated),exact(funded,'signed_funding_USDT'))
        self.assertTrue(all(D(a['signed_native_funding_allocated'])<0 for a in allocated))
        self.assertTrue(all('allocation_rounding_bridge' in a for a in allocated))
        sim.owners.reconcile(sim.account.engine)

    def test_finite_exit_paid_first_then_original_csh_short_can_open(self):
        weights=[[.05,0,0,0,0],[-.05,0,0,0,0]]
        sim=make_candidate(make_generated(days=2,weights=weights));sim.advance_day()
        self.assertGreater(sim.owners.quantity[FINITE][BTC],0)
        held=sim.owners.quantity[FINITE][BTC]
        sim.advance_day()
        day2=[r for r in sim.account.trades if START+DAY<=r['event_us']<sim.terminal_signal_us]
        finite_close=next(r for r in day2 if r['leg']=='CLOSE' and sim._fill_owner[r['fill_id']][0]==FINITE)
        short=next(r for r in day2 if r['leg']=='OPEN' and r['side']=='SELL')
        self.assertGreaterEqual(short['event_us'],finite_close['event_us'])
        self.assertEqual(exact(finite_close,'quantity'),held)
        self.assertEqual(sim.owners.quantity[FINITE][BTC],0)
        self.assertTrue(sim.program.terminal)
        self.assertTrue(any(e.get('reason')=='ORIGINAL_BTC_NONPOSITIVE' for e in sim.owner_events))

    def test_zero_capacity_collision_keeps_program_owned_blocks_short(self):
        quote=np.full(2880,10000000.);quote[1439:]=0.
        sim=make_candidate(make_generated(days=2,weights=[[.05,0,0,0,0],[-.05,0,0,0,0]],quote=quote))
        sim.advance_day();finite=sim.owners.quantity[FINITE][BTC];sim.advance_day()
        self.assertEqual(sim.owners.quantity[FINITE][BTC],finite)
        self.assertGreater(finite,0)
        self.assertFalse(any(r['side']=='SELL' and r['leg']=='OPEN' for r in sim.account.trades))
        self.assertTrue(any(e['kind']=='CSH_BTC_SHORT_HELD_UNTIL_PAID_FINITE_EXIT' for e in sim.owner_events))
        self.assertNotIn(FINITE,sim.reservations.retired_reservations)
        self.assertFalse(sim.result()['summary']['terminal_cash_realized'])

    def test_stop_gap_is_signal_not_minus200_loss_guarantee_no_restart(self):
        bundle=demo_bundle()
        bundle[0]['market'][BTC]['open'][120:]=55.;bundle[0]['market'][BTC]['mark'][120:]=55.;bundle[0]['market'][BTC]['close'][120:]=55.
        sim=make_candidate(bundle);finish(sim)
        stops=[e for e in sim.owner_events if e.get('reason')=='ACTUAL_FILL_ECONOMIC_NET_SLEEVE_PNL_LE_MINUS200']
        self.assertTrue(stops)
        self.assertLess(sim.owners.pnl(FINITE,sim.account.engine),D('-200'))
        self.assertTrue(sim.program.terminal);self.assertEqual(sim.owners.quantity[FINITE][BTC],0)
        self.assertEqual(sim.program.completed_opening_orders,4)
        self.assertEqual(sum(e['kind']=='FIRST_ORIGINAL_CAUSALLY_ELIGIBLE_BTC_POSITIVE_PROGRAM_ACTIVATION' for e in sim.owner_events),1)

    def test_funding_exhausted_buffer_blocks_adds_without_replenishment(self):
        sim=prepared_two_owner()
        q=sim.owners.quantity[FINITE][BTC]
        with localcontext() as ctx:
            ctx.prec=40;rate=D('140')/(q*D('100'))
        sim.account.apply_funding(BTC,'GENERATED_COST_RESERVE_DRAIN',START+2*MINUTE+1,rate,START)
        sim._flush_account();sim._evaluate_program(START+2*MINUTE+1)
        self.assertGreater(sim.program_budget.consumed_fee_funding_reserve,D('135.156250'))
        self.assertTrue(sim.program.terminal)
        self.assertGreater(sim.owners.quantity[FINITE][BTC],0)
        self.assertIsNone(sim.program_pending)
        before=sim.program_budget.consumed_fee_funding_reserve
        sim.account.apply_funding(BTC,'GENERATED_CREDIT_NO_REFILL',START+3*MINUTE+1,-rate,START)
        sim._flush_account();self.assertEqual(sim.program_budget.consumed_fee_funding_reserve,before)
        sim._start_margin_order(START+4*MINUTE);self.assertIsNone(sim.program_pending)

    def test_invalid_source_reduces_both_paid_or_keeps_unpaid_inventory(self):
        def delayed(source):source['daily_bars'][-1]['available_us']=START+DAY+1
        sim=make_candidate(make_generated(days=2,weights=[.05,.05,0,0,0],source_mutations={START+DAY:delayed}))
        sim.advance_day();held=sum(sim.owners.quantity[o][BTC] for o in (BASE,FINITE));self.assertGreater(held,0)
        sim.advance_day()
        self.assertTrue(all(p.quantity==0 for p in sim.account.positions.values()))
        self.assertTrue(sim.program.terminal)
        closes=[r for r in sim.account.trades if r['leg']=='CLOSE' and r['event_us']>=START+DAY]
        self.assertEqual({sim._fill_owner[r['fill_id']][0] for r in closes},{BASE,FINITE})
        self.assertTrue(all(exact(r,'fee_amount')>0 for r in closes))

    def test_program_five_partial_attempts_retains_owned_inventory_and_reservation(self):
        sim=make_candidate(make_generated(weights=[.001,0,0,0,0]));prime(sim)
        sim.schedule({s:D('.1') if s==BTC else Z for s in S},START,'DAILY_TARGET')
        # Only .2 BTC per minute is available; CSH receives .1 first, then
        # genuine partial program fills stay below the fixed150 margin.
        sim.previous_quote=dict.fromkeys(S,20000.) # .2 BTC, 20USDT partials
        for n in range(1,6):sim.attempt(START+n*MINUTE,row())
        self.assertEqual(sim.program.completed_opening_orders,0)
        self.assertTrue(sim.program.terminal)
        self.assertGreater(sim.owners.quantity[FINITE][BTC],0)
        self.assertIsNone(sim.program_pending)
        self.assertIn(FINITE,sim.reservations.reservations)
        self.assertTrue(any(r.get('owner')==FINITE and r.get('reason')=='FIVE_ATTEMPTS_EXPIRED' for r in sim.rejections))

    def test_snapshot_binds_owner_state_but_refuses_recovery(self):
        sim=make_candidate(demo_bundle());finish(sim)
        snapshot=sim.snapshot();json.dumps(snapshot,allow_nan=False)
        self.assertEqual(snapshot['version'],'h090_finite_single_program_generated_v1')
        binding=snapshot['finite_owner_binding']
        self.assertEqual(binding['program_state']['completed_opening_orders'],4)
        self.assertTrue(binding['owner_ledger']['fill_allocations'])
        self.assertEqual(binding['retired_reservations'],{FINITE:'1000'})
        self.assertEqual(binding['recovery_status'],'NO_GO_NOT_IMPLEMENTED')
        with self.assertRaisesRegex(ValueError,'NO_GO'):FiniteNativeCandidate.from_snapshot(snapshot,sim.window)

if __name__=='__main__':unittest.main(verbosity=2)
