"""Independent V2 generated-only missing-quality and native parity boundaries."""
from copy import deepcopy
from decimal import Decimal as D
import unittest
import numpy as np
import integration as i
from test_native_runtime import fixture, BASE
from test_coupled_boundaries import known_marks, fill, sim_fixture


def finite_finance(sim):
    a=sim.account
    return dict(cash=str(a.free_cash),debt=str(a.unpaid_liability),clock=a.clock_us,
        positions={s:(str(p.quantity),str(p.entry_price),str(p.isolated_balance),p.opened_us)
            for s,p in a.positions.items()},
        totals=tuple(str(getattr(a,key)) for key in
            ('fees','execution_cost','funding_cash','realized_PnL','gross_fill_turnover')),
        status=a.status,pending=deepcopy(sim.pending))


def pair(variant='CONTINUE_ONLY',signal_in_gap=True,partial_capacity=False,second_weight=.05,terminal_in_gap=False):
    window,rows,decisions=fixture(2);start=int(decisions[0]);decision=int(decisions[1])
    first=decision-2*i.MINUTE if signal_in_gap else start+3*i.MINUTE
    recovery=decision+3*i.MINUTE if signal_in_gap else start+7*i.MINUTE
    if terminal_in_gap:first,recovery=window['end']-65*i.MINUTE,window['end']-55*i.MINUTE
    weights=np.array([[.03]*5,[second_weight]*5])
    window['events']=[dict(symbol=s,event_us=at,raw_rate=.0001,reported_interval_hours=8.)
        for at in (first+30_000_000,recovery) for s in i.S]
    if partial_capacity:
        # Keep actual signal sizing's completed quote intact, then constrain
        # participation at the later recovery opens so parity is non-vacuous.
        window['market']['BTCUSDT']['quote_volume'][1441:1450]=50000.
    old,og=i.native.build_case(window,rows,decisions,weights,tier_name='MID',generated_scope=i.GENERATED)
    interval=i.quality_module.StaleMarkInterval(first,recovery,first-i.MINUTE,i.S)
    i.quality_module.CausalMarkQualityGuard(og,intervals=(interval,),source_sidecar_sha256='e'*64).install()
    new,ng=i.construct_case(window,rows,decisions,weights,policy_variant=variant,
        generated_scope=i.GENERATED,quality_intervals=((first,recovery,i.S),))
    for sim in (old,new):
        sim.independent_trace=[]
        # Trace actual wallet and pending order states both at native observe
        # phases and after actual opens, including partial-bar funding.
        observe=sim.observe
        def observed(event,phase,*,sim=sim,observe=observe):
            result=observe(event,phase)
            if first-i.MINUTE<=event<=recovery+5*i.MINUTE:
                sim.independent_trace.append((event,phase,finite_finance(sim)))
            return result
        sim.observe=observed
        attempt=sim.attempt
        def attempted(at,market,*,sim=sim,attempt=attempt):
            result=attempt(at,market)
            if first-i.MINUTE<=at<=recovery+5*i.MINUTE:
                sim.independent_trace.append((at+1,'AFTER_ACTUAL_ATTEMPT',finite_finance(sim)))
            return result
        sim.attempt=attempted
    return old,og,new,ng,first,recovery


class IndependentQualityBoundaries(unittest.TestCase):
    def test_new_strategy_reduction_inside_gap_remains_paid_under_frozen_rules(self):
        for variant in ('CONTINUE_ONLY','TOPUP_THEN_CONTINUE'):
            with self.subTest(variant=variant):
                old,og,new,ng,first,recovery=pair(variant,second_weight=.01)
                for sim in (old,new):
                    while sim.cursor<sim.end and sim.stop is None:sim.advance_day()
                self.assertEqual(old.independent_trace,new.independent_trace)
                self.assertEqual(list(old.account.trades),list(new.account.trades))
                closes=[r for r in new.account.trades if first<=r['event_us']<recovery and r['leg']=='CLOSE']
                self.assertGreater(len(closes),0)
                self.assertTrue(all(r['signal_us']>=first for r in closes))
                self.assertFalse(new.account.pending_exits);self.assertFalse(new.account.transfer_journal)
                self.assertTrue(i.financial_reconciliation(new.account)['passed'])

    def test_new_terminal_exit_inside_gap_remains_paid_under_frozen_rules(self):
        for variant in ('CONTINUE_ONLY','TOPUP_THEN_CONTINUE'):
            with self.subTest(variant=variant):
                old,og,new,ng,first,recovery=pair(variant,terminal_in_gap=True)
                for sim in (old,new):
                    while sim.cursor<sim.end and sim.stop is None:sim.advance_day()
                self.assertEqual(old.independent_trace,new.independent_trace)
                self.assertEqual(list(old.account.trades),list(new.account.trades))
                closes=[r for r in new.account.trades if first<=r['event_us']<recovery and r['leg']=='CLOSE']
                self.assertEqual(len(closes),5)
                self.assertTrue(all(r['signal_us']==new.terminal_signal_us for r in closes))
                self.assertTrue(i.case_result(new,ng)['economics']['actual_paid_market_flat'])
                self.assertFalse(new.account.pending_exits);self.assertFalse(new.account.transfer_journal)

    def test_hypothetical_open_settlement_cannot_replace_real_fallback_inventory(self):
        sim,g=sim_fixture('CONTINUE_ONLY');a=sim.account;start=sim.start
        known_marks(a,start);fill(a,'BTCUSDT','SELL','.02',start,start+i.MINUTE+1,'SHORT')
        signal=start+i.MINUTE;binding=g.source.bind(start)
        actual={s:a.positions[s].quantity for s in i.S}
        target=dict(actual);target['ETHUSDT']=D('.1')
        prices={s:D(str(BASE[j])) for j,s in enumerate(i.S)};prices['BTCUSDT']=D(110000)
        token=a.preview_state_token()
        oracle=i.fresh_preview(a,tier_name='MID',binding=binding,prices=prices,
            price_available_us=dict.fromkeys(i.S,signal+i.MINUTE),pending=target,
            capacity=dict.fromkeys(i.S,D(100000)),event_us=signal+i.MINUTE+1,
            signal_us=start,quote_available_us=signal+i.MINUTE)
        self.assertEqual(oracle.actual,actual)
        choice=g._select(oracle,target,'INDEPENDENT_INVALID_OPEN_FALLBACK',start)
        self.assertTrue(choice.all_invalid);self.assertEqual(choice.target,actual)
        self.assertTrue(i.native._exact_tree_equal(token,a.preview_state_token()))
        self.assertFalse(a.settlement_journal)

    def test_daily_signal_inside_gap_retains_pending_and_full_financial_path_B(self):
        old,og,new,ng,first,recovery=pair()
        for sim in (old,new):
            while sim.cursor<sim.end and sim.stop is None:sim.advance_day()
        self.assertGreater(len(old.account.trades),10)
        self.assertEqual(old.independent_trace,new.independent_trace)
        for key in ('free_cash','unpaid_liability','positions','marks','totals','trades','funding','fill_requests'):
            self.assertEqual(old.account.snapshot()[key],new.account.snapshot()[key],key)
        self.assertEqual(old.result()['minute'].to_numpy().tobytes(),new.result()['minute'].to_numpy().tobytes())
        self.assertFalse(new.account.settlement_journal);self.assertFalse(new.account.transfer_journal)
        self.assertIsNone(new.account._signal_projection_clock)
        recovery_fills=[r for r in new.account.trades if recovery<r['event_us']<recovery+5*i.MINUTE]
        self.assertTrue(recovery_fills)
        self.assertTrue(all(r['event_us']>=recovery+1 for r in recovery_fills))

    def test_calm_C_missing_gap_keeps_reference_intent_with_partial_capacity(self):
        old,og,new,ng,first,recovery=pair('TOPUP_THEN_CONTINUE',partial_capacity=True)
        for sim in (old,new):
            while sim.cursor<sim.end and sim.stop is None:sim.advance_day()
        self.assertEqual(old.independent_trace,new.independent_trace)
        self.assertEqual(list(old.account.trades),list(new.account.trades))
        self.assertEqual(list(old.account.funding),list(new.account.funding))
        self.assertFalse(new.account.pending_exits);self.assertFalse(new.account.transfer_journal)
        self.assertTrue(any(r['symbol']=='BTCUSDT' and D(r['decimal_strings']['quantity'])==D('.001')
            and recovery<r['event_us']<recovery+5*i.MINUTE for r in new.account.trades))
        self.assertTrue(i.financial_reconciliation(new.account)['passed'])

    def test_zero_executable_native_bookkeeping_never_bypasses_positive_lot_gate(self):
        for variant in ('CONTINUE_ONLY','TOPUP_THEN_CONTINUE'):
            with self.subTest(variant=variant):
                sim,g=sim_fixture(variant);a=sim.account;start=sim.start
                known_marks(a,start);fill(a,'BTCUSDT','SELL','.02',start,start+i.MINUTE+1,'SHORT')
                at=start+2*i.MINUTE;a._quality_intervals=((at,at+3*i.MINUTE,i.S),)
                known_marks(a,at)
                a.blocked_signals['BTCUSDT']=at
                a.pending_exits['ETHUSDT']=dict(signal_us=start,reason='PREEXISTING')
                before=a.fork_for_preview();native=before.fork_for_preview()
                kwargs=dict(execution_mid_price='50000',quote_available_us=at,available_quantity='0')
                expected=i.ENGINE.USDTLinearPerpetualAccount.execute_fill(native,'BTCUSDT','SELL','.001',at+1,start,'ZERO',**kwargs)
                actual=a.execute_fill('BTCUSDT','SELL','.001',at+1,start,'ZERO',**kwargs)
                self.assertEqual(expected,actual);self.assertEqual(actual['executed_quantity'],0)
                for key in ('free_cash','unpaid_liability','positions','totals','fill_requests','clock_us','last_fill_us'):
                    self.assertEqual(a.snapshot()[key],native.snapshot()[key],key)
                token=a.preview_state_token()
                self.assertEqual(a.execute_fill('BTCUSDT','SELL','.001',at+1,start,'ZERO',**kwargs),actual)
                self.assertTrue(i.native._exact_tree_equal(token,a.preview_state_token()))
                with self.assertRaisesRegex(ValueError,'conflicting fill identity'):
                    a.execute_fill('BTCUSDT','SELL','.002',at+1,start,'ZERO',**kwargs)
                self.assertTrue(i.native._exact_tree_equal(token,a.preview_state_token()))
                # Independently isolate the quality guard from pending-exit,
                # stale-signal and latency rejection, using a valid old signal.
                a.pending_exits.clear();a.blocked_signals.clear()
                token=a.preview_state_token()
                with self.assertRaisesRegex(ValueError,'NEW_INCREASE_FAIL_CLOSED'):
                    a.execute_fill('BTCUSDT','SELL','.001',at+2,start,'POSITIVE',
                        execution_mid_price='50000',quote_available_us=at,available_quantity='.001')
                self.assertTrue(i.native._exact_tree_equal(token,a.preview_state_token()))
                self.assertFalse(a.transfer_journal);self.assertFalse(a.settlement_journal)
                self.assertTrue(i.financial_reconciliation(a)['passed'])

    def test_real_C_budget_exit_pays_actual_lots_through_unknown_interval(self):
        sim,g=sim_fixture();a=sim.account;start=sim.start
        known_marks(a,start);fill(a,'BTCUSDT','SELL','.02',start,start+i.MINUTE+1,'SHORT')
        debit=start+2*i.MINUTE;known_marks(a,debit)
        a.apply_funding('BTCUSDT','GENUINE_BUDGET_DEBIT',debit,D(-8),debit)
        at=start+3*i.MINUTE;known_marks(a,at,{'BTCUSDT':75000});sim.risk_schedule(at)
        self.assertEqual(a.pending_exits['BTCUSDT']['reason'],'INSUFFICIENT_TOPUP_BUDGET')
        transfers=len(a.transfer_journal);signal=a.pending_exits['BTCUSDT']['signal_us']
        a._quality_intervals=((at+i.MINUTE,at+9*i.MINUTE,i.S),)
        sim.previous_quote={s:75000. if s=='BTCUSDT' else 1e10 for s in i.S}
        market={s:dict(open=75000. if s=='BTCUSDT' else float(BASE[j]),
            close=75000. if s=='BTCUSDT' else float(BASE[j]),
            mark=75000. if s=='BTCUSDT' else float(BASE[j]),quote_volume=1e10) for j,s in enumerate(i.S)}
        initial=abs(a.positions['BTCUSDT'].quantity)
        for k in range(1,5):
            open_us=at+k*i.MINUTE;known_marks(a,open_us,{'BTCUSDT':75000})
            sim.risk_schedule(open_us);sim.attempt(open_us,market)
            self.assertEqual(a.pending_exits['BTCUSDT']['signal_us'],signal)
            self.assertEqual(len(a.transfer_journal),transfers)
            self.assertEqual(set(a.pending_exits),{'BTCUSDT'})
        self.assertEqual(abs(a.positions['BTCUSDT'].quantity),initial-D('.004'))
        closes=[r for r in a.trades if r['leg']=='CLOSE']
        self.assertEqual(len(closes),4);self.assertTrue(all(D(r['decimal_strings']['quantity'])==D('.001') for r in closes))
        self.assertGreater(a.fees,0);self.assertFalse(a.settlement_journal)
        self.assertTrue(i.financial_reconciliation(a)['passed'])


if __name__=='__main__':unittest.main(verbosity=2)
