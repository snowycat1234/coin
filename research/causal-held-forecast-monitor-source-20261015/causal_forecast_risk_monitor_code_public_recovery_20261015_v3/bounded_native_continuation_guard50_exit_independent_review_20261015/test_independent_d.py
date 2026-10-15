"""Independent generated-only D boundaries, native execution and isolation."""
from copy import deepcopy
from decimal import Decimal as D
import unittest
import numpy as np
import guard50_exit as d
from test_guard50_exit import account,marks,fill,sim_fixture,finance
from test_native_runtime import fixture,BASE
v=d.V2


class IndependentD(unittest.TestCase):
    def test_repeating_native_basis_retains_exact_primary_and_raw_secondary_residual(self):
        a=account()
        for k,(side,q,mid) in enumerate((('SELL','10','100'),('SELL','3','101'),('BUY','7','98'))):
            signal=k*2*d.MINUTE;event=signal+d.MINUTE+1
            a.update_marks(event-1,{s:dict(price='100',close_us=event-1,available_us=event-1) for s in d.S})
            a.execute_fill('BTCUSDT',side,q,event,signal,'D_REPEATING:'+str(k),execution_mid_price=mid,
                quote_available_us=event-1,available_quantity=q,reduce_only=side=='BUY')
        result=v.financial_reconciliation(a)
        self.assertTrue(result['passed']);self.assertTrue(result['exact_frozen_native_secondary_arithmetic_replay_match'])
        self.assertNotEqual(D(result['native_40digit_secondary_PnL_bridge_residual']),0)
        self.assertEqual(result['native_40digit_secondary_PnL_bridge_residual'],a.summary()['decimal_strings']['accounting_bridge_error_USDT'])
        self.assertFalse(a.transfer_journal);self.assertFalse(a.transfer_ids)

    def test_negative_equity_settlement_support_explicit_unknown_cannot_resume(self):
        for unknown in (False,True):
            with self.subTest(unknown=unknown):
                a=account();fill(a);at=2*d.MINUTE;cash=a.free_cash
                if unknown:a._quality_intervals=((at,at+2*d.MINUTE,d.S),)
                marks(a,at,{'BTCUSDT':100000})
                a.monitor('MONITOR:'+str(at),at)
                self.assertEqual(a.free_cash,cash);self.assertFalse(a.transfer_journal)
                self.assertFalse(a.pending_exits)
                if unknown:
                    self.assertIn(a.status,v.P.HALTS);self.assertFalse(a.settlement_journal)
                    with self.assertRaises(RuntimeError):marks(a,at+3*d.MINUTE)
                    self.assertFalse(a.settlement_journal)
                else:
                    row=a.settlement_journal[0]['decimal_strings']
                    self.assertLess(D(row['marked_equity_before']),0)
                    self.assertGreater(D(row['conditional_insurance_value_received']),0)
                    self.assertEqual(D(row['marked_equity_before'])+D(row['conditional_insurance_value_received'])-D(row['conditional_forfeiture_value_paid']),0)
                    self.assertEqual(D(row['free_cash_credit']),0)
                    self.assertFalse(a.economic_report()['paid_flat'])
                self.assertTrue(v.financial_reconciliation(a)['passed'])

    def test_new_native_drift_risk_reduction_inside_gap_matches_B_paid_rule(self):
        window,rows,decisions=fixture(1);start=int(decisions[0]);at=start+2*d.MINUTE
        intervals=((at,at+4*d.MINUTE,d.S),)
        b,bg=v.construct_case(window,rows,decisions,np.zeros((1,5)),policy_variant='CONTINUE_ONLY',
            generated_scope=d.GENERATED,quality_intervals=intervals)
        x,xg=d.construct_case(window,rows,decisions,np.zeros((1,5)),generated_scope=d.GENERATED,quality_intervals=intervals)
        for sim in (b,x):
            a=sim.account;fill(a,side='BUY',q='.05',signal=start)
            marks(a,at,{'BTCUSDT':100000});self.assertEqual(a.status,'BOUND_BREACH_REDUCTION_REQUIRED')
            sim.risk_schedule(at);self.assertEqual(sim.pending['BTCUSDT']['kind'],'RISK_REDUCTION')
            self.assertFalse(a.pending_exits)
            sim.previous_quote=dict.fromkeys(d.S,1e10)
            market={s:dict(open=100000. if s=='BTCUSDT' else float(BASE[j]),close=float(BASE[j]),
                mark=100000. if s=='BTCUSDT' else float(BASE[j]),quote_volume=1e10) for j,s in enumerate(d.S)}
            marks(a,at+d.MINUTE,{'BTCUSDT':100000});sim.attempt(at+d.MINUTE,market)
            self.assertTrue(any(r['leg']=='CLOSE' and r['signal_us']==at for r in a.trades))
            self.assertFalse(a.transfer_journal);self.assertFalse(a.pending_exits)
        self.assertEqual(finance(b.account),finance(x.account))
        self.assertEqual(b.pending,x.pending)

    def test_long_and_short_actual_collateral_half_boundary_and_no_cashflow(self):
        for side in ('BUY','SELL'):
            for delta,warning in ((D('.0001'),False),(D(0),True),(D('-.0001'),True)):
                with self.subTest(side=side,delta=delta):
                    a=account();fill(a,side=side);p=a.positions['BTCUSDT'];at=2*d.MINUTE
                    # Specify equity directly relative to actual remaining
                    # collateral, so both price directions exercise exact <=.
                    target_equity=p.isolated_balance/2+delta
                    mark=p.entry_price+(target_equity-p.isolated_balance)/p.quantity
                    marks(a,at,{'BTCUSDT':mark});before=a._balances()
                    a.monitor('MONITOR:'+str(at),at)
                    self.assertEqual(bool(a.pending_exits),warning)
                    self.assertEqual(a._balances(),before)
                    self.assertFalse(a.transfer_journal);self.assertFalse(a.transfer_ids)
                    self.assertFalse(a.settlement_journal)
                    token=a.preview_state_token()
                    with self.assertRaisesRegex(ValueError,'TRANSFERS_FORBIDDEN'):
                        a._transfer('BTCUSDT',D(1),at,'VALID_CURRENT_TRANSFER')
                    self.assertTrue(v.native._exact_tree_equal(token,a.preview_state_token()))

    def test_partialbar_nonzero_funding_batch_warning_uses_ceil_latency(self):
        sim,g=sim_fixture();a=sim.account;start=sim.start;fill(a,signal=start)
        markclock=start+2*d.MINUTE;at=markclock+30_000_000
        marks(a,markclock,{'BTCUSDT':75000})
        sim.window['events']=[dict(symbol=s,event_us=at,raw_rate=-.0001,reported_interval_hours=8.) for s in d.S]
        phases=[];original=a.apply_funding
        def funding(*args,**kwargs):
            phases.append((args[0],len(a.pending_exits),len(sim.pending)))
            return original(*args,**kwargs)
        a.apply_funding=funding
        sim.funding_through(at,True);del a.apply_funding
        self.assertEqual(len(phases),5);self.assertTrue(all(exits==pending==0 for _,exits,pending in phases))
        self.assertEqual(a.pending_exits['BTCUSDT']['signal_us'],at)
        self.assertEqual(sim.pending['BTCUSDT']['signal_us'],at)
        self.assertEqual(len([x for x in a.monitor_journal if x['event_us']==at]),1)
        self.assertTrue(all(x['mark_close_us']<at for x in a.funding))
        self.assertNotEqual(a.funding_cash,0)
        market={s:dict(open=75000. if s=='BTCUSDT' else float(BASE[j]),close=float(BASE[j]),
            mark=75000. if s=='BTCUSDT' else float(BASE[j]),quote_volume=1e10) for j,s in enumerate(d.S)}
        sim.previous_quote=dict.fromkeys(d.S,1e10)
        earliest=v.P.ExecutionContractV2().earliest_execution_us(at)+1
        self.assertEqual(earliest,start+4*d.MINUTE+1)
        known=abs(a.positions['BTCUSDT'].quantity)
        marks(a,start+3*d.MINUTE,{'BTCUSDT':75000});sim.attempt(start+3*d.MINUTE,market)
        self.assertEqual(abs(a.positions['BTCUSDT'].quantity),known)
        marks(a,start+4*d.MINUTE,{'BTCUSDT':75000});sim.attempt(start+4*d.MINUTE,market)
        self.assertEqual(a.positions['BTCUSDT'].quantity,0)
        self.assertFalse(a.pending_exits);self.assertNotIn('BTCUSDT',sim.pending)
        self.assertFalse(a.blocked_signals);self.assertFalse(a.transfer_journal)
        close=[x for x in a.trades if x['leg']=='CLOSE'];self.assertEqual(len(close),1)
        self.assertEqual(close[0]['event_us'],earliest);self.assertGreater(D(close[0]['decimal_strings']['fee_amount']),0)
        self.assertTrue(v.financial_reconciliation(a)['passed'])

    def test_partial_paid_warning_then_actual_full_close_and_known_id_replay(self):
        sim,g=sim_fixture();a=sim.account;start=sim.start
        initial=fill(a,signal=start);initial_id=a.trades[0]['fill_id']
        at=start+2*d.MINUTE;marks(a,at,{'BTCUSDT':75000});sim.risk_schedule(at)
        original=deepcopy(a.pending_exits['BTCUSDT'])
        market={s:dict(open=75000. if s=='BTCUSDT' else float(BASE[j]),close=float(BASE[j]),
            mark=75000. if s=='BTCUSDT' else float(BASE[j]),quote_volume=1e10) for j,s in enumerate(d.S)}
        sim.previous_quote={s:75000. if s=='BTCUSDT' else 1e10 for s in d.S}
        for k in (1,2):
            clock=at+k*d.MINUTE;marks(a,clock,{'BTCUSDT':75000});sim.risk_schedule(clock);sim.attempt(clock,market)
            self.assertEqual(a.pending_exits['BTCUSDT'],original)
        self.assertEqual(a.positions['BTCUSDT'].quantity,D('-.018'))
        sim.previous_quote=dict.fromkeys(d.S,1e10)
        clock=at+3*d.MINUTE;marks(a,clock,{'BTCUSDT':75000});sim.attempt(clock,market)
        self.assertEqual(a.positions['BTCUSDT'].quantity,0);self.assertFalse(a.pending_exits)
        self.assertNotIn('BTCUSDT',sim.pending);self.assertFalse(a.blocked_signals)
        self.assertEqual(len([x for x in a.trades if x['leg']=='CLOSE']),3)
        token=a.preview_state_token()
        replay=a.execute_fill('BTCUSDT','SELL','.02',start+d.MINUTE+1,start,initial_id,
            execution_mid_price=str(BASE[0]),quote_available_us=start+d.MINUTE,available_quantity='.02',reduce_only=False)
        self.assertEqual(replay,initial);self.assertTrue(v.native._exact_tree_equal(token,a.preview_state_token()))
        self.assertFalse(a.transfer_journal);self.assertFalse(a.transfer_ids)
        self.assertTrue(v.financial_reconciliation(a)['passed'])

    def test_new_strategy_reduction_and_terminal_in_gap_match_frozen_B(self):
        for terminal in (False,True):
            with self.subTest(terminal=terminal):
                window,rows,decisions=fixture(2);day2=int(decisions[1])
                first,end=((window['end']-65*d.MINUTE,window['end']-55*d.MINUTE) if terminal else
                    (day2-2*d.MINUTE,day2+3*d.MINUTE))
                weights=np.array([[.03]*5,[.05 if terminal else .01]*5])
                intervals=((first,end,d.S),)
                b,bg=v.construct_case(window,rows,decisions,weights,policy_variant='CONTINUE_ONLY',
                    generated_scope=d.GENERATED,quality_intervals=intervals)
                x,xg=d.construct_case(window,rows,decisions,weights,generated_scope=d.GENERATED,quality_intervals=intervals)
                for sim in (b,x):
                    while sim.cursor<sim.end and sim.stop is None:sim.advance_day()
                self.assertEqual(finance(b.account),finance(x.account))
                self.assertEqual(b.result()['minute'].to_numpy().tobytes(),x.result()['minute'].to_numpy().tobytes())
                closes=[r for r in x.account.trades if first<=r['event_us']<end and r['leg']=='CLOSE']
                self.assertTrue(closes);self.assertTrue(all(r['signal_us']>=first for r in closes))
                self.assertFalse(x.account.transfer_journal);self.assertFalse(x.account.pending_exits)

    def test_hypothetical_settlement_preserves_live_real_inventory_and_callback(self):
        sim,g=sim_fixture();a=sim.account;start=sim.start;fill(a,signal=start)
        before=a.preview_state_token();pending=deepcopy(sim.pending);callback=a.liquidation_callback
        binding=g.source.bind(start);actual={s:a.positions[s].quantity for s in d.S}
        target=dict(actual);target['ETHUSDT']=D('.1')
        prices={s:D(str(BASE[j])) for j,s in enumerate(d.S)};prices['BTCUSDT']=D(110000)
        oracle=d.fresh_preview(a,tier_name='MID',binding=binding,prices=prices,
            price_available_us=dict.fromkeys(d.S,start+2*d.MINUTE),pending=target,
            capacity=dict.fromkeys(d.S,D(100000)),event_us=start+2*d.MINUTE+1,
            signal_us=start,quote_available_us=start+2*d.MINUTE)
        self.assertEqual(oracle.actual,actual)
        selection=g._select(oracle,target,'D_INDEPENDENT_INVALID_OPEN',start)
        self.assertTrue(selection.all_invalid);self.assertEqual(selection.target,actual)
        self.assertTrue(v.native._exact_tree_equal(before,a.preview_state_token()))
        self.assertEqual(sim.pending,pending);self.assertIs(a.liquidation_callback,callback)
        fork=a.fork_for_preview();self.assertIs(type(fork),d.Guard50ExitAccount);self.assertIsNone(fork.liquidation_callback)
        self.assertFalse(a.settlement_journal);self.assertFalse(a.transfer_journal)

    def test_genuine_debt_and_old_halt_never_resume(self):
        a=account();fill(a);at=2*d.MINUTE;marks(a,at)
        a.apply_funding('BTCUSDT','UNPAID_DEBT',at,D(-100),at)
        self.assertGreater(a.unpaid_liability,0);self.assertEqual(a.status,'BANKRUPT_HALT')
        debt=a.unpaid_liability;before=a._balances();a.monitor('MONITOR:'+str(at),at)
        self.assertEqual(a._balances(),before);self.assertEqual(a.unpaid_liability,debt)
        self.assertEqual(a.mode(),'DEBT_SETTLEMENT_BLOCKED');self.assertFalse(a.transfer_journal)
        self.assertFalse(a.pending_exits);self.assertFalse(a.settlement_journal)
        with self.assertRaises(RuntimeError):marks(a,at+d.MINUTE)
        self.assertEqual(a.unpaid_liability,debt)
        self.assertTrue(v.financial_reconciliation(a)['passed'])


if __name__=='__main__':unittest.main(verbosity=2)
