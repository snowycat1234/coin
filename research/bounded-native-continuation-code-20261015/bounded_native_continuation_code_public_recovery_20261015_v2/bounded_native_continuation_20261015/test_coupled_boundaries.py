"""Generated coupled phase, settlement, quality, paid capacity and debt tests."""
from copy import deepcopy
from decimal import Decimal as D
import unittest
import numpy as np
import integration as i
from test_integration import account
from test_native_runtime import fixture,BASE


def known_marks(a,clock,overrides=None):
    overrides=overrides or {}
    return a.update_marks(clock,{s:dict(price=str(overrides.get(s,BASE[j])),close_us=clock,available_us=clock) for j,s in enumerate(i.S)})


def fill(a,symbol,side,q,signal,event,identity):
    price=BASE[i.S.index(symbol)]
    known_marks(a,event-1)
    return a.execute_fill(symbol,side,str(q),event,signal,identity,execution_mid_price=str(price),
        quote_available_us=event-1,available_quantity=str(q),reduce_only=False)


def sim_fixture(variant='TOPUP_THEN_CONTINUE',events=(),intervals=()):
    window,rows,d=fixture(1);window['events']=list(events)
    return i.construct_case(window,rows,d,np.zeros((1,5)),policy_variant=variant,
        generated_scope=i.GENERATED,quality_intervals=intervals)


class CoupledBoundaries(unittest.TestCase):
    def test_mark_first_cannot_rescue_jump_and_conditional_not_paid_flat(self):
        for variant in ('CONTINUE_ONLY','TOPUP_THEN_CONTINUE'):
            a=account(variant);known_marks(a,0)
            fill(a,'BTCUSDT','SELL','.02',0,i.MINUTE+1,'SHORT')
            known_marks(a,2*i.MINUTE,{'BTCUSDT':100000})
            self.assertEqual(len(a.settlement_journal),1)
            a.monitor('MONITOR:'+str(2*i.MINUTE),2*i.MINUTE)
            self.assertFalse(a.transfer_journal)
            self.assertEqual(a.positions['BTCUSDT'].quantity,0)
            report=a.economic_report()
            self.assertFalse(report['paid_flat']);self.assertTrue(report['settled_flat_under_declared_model'])
            self.assertTrue(i.financial_reconciliation(a)['passed'])
            self.assertGreater(D(report['conditional_insurance_overshoot_absorption_USDT']),0)

    def test_C_topup_before_trigger_restores_pretransfer_equity_B_no_warning(self):
        for variant in ('CONTINUE_ONLY','TOPUP_THEN_CONTINUE'):
            a=account(variant);known_marks(a,0);fill(a,'BTCUSDT','SELL','.02',0,i.MINUTE+1,'SHORT')
            known_marks(a,2*i.MINUTE,{'BTCUSDT':75000})
            p=a.positions['BTCUSDT'];pre_margin=p.isolated_balance
            before=(a.nav(),a.fees,a.realized_PnL,a.funding_cash,p.quantity)
            a.monitor('MONITOR:'+str(2*i.MINUTE),2*i.MINUTE)
            if variant=='CONTINUE_ONLY':
                self.assertFalse(a.transfer_journal);self.assertFalse(a.pending_exits)
            else:
                self.assertEqual(len(a.transfer_journal),1)
                self.assertEqual(p.isolated_balance+p.quantity*(D(75000)-p.entry_price),pre_margin)
                self.assertEqual(before,(a.nav(),a.fees,a.realized_PnL,a.funding_cash,p.quantity))
            self.assertTrue(i.financial_reconciliation(a)['passed'])

    def test_sameclock_funding_entire_batch_precedes_monitor(self):
        sim,guard=sim_fixture();a=sim.account;start=sim.start
        known_marks(a,start);fill(a,'BTCUSDT','SELL','.02',start,start+i.MINUTE+1,'SHORT')
        at=start+2*i.MINUTE
        known_marks(a,at,{'BTCUSDT':75000})
        events=[dict(symbol=s,event_us=at,raw_rate=0.,reported_interval_hours=8.) for s in i.S]
        sim.window['events']=events
        phases=[];old=a.apply_funding
        def traced(*args,**kwargs):
            phases.append(('funding',args[0],len(a.transfer_journal)))
            return old(*args,**kwargs)
        a.apply_funding=traced
        sim.funding_through(at,True)
        del a.apply_funding
        self.assertEqual(len(phases),5)
        self.assertTrue(all(count==0 for _,_,count in phases))
        self.assertEqual(len(a.transfer_journal),1)
        self.assertEqual(a.transfer_journal[0]['event_us'],at)
        self.assertTrue(i.financial_reconciliation(a)['passed'])

    def test_unknown_quality_blocks_settlement_topup_and_open_until_recovered(self):
        a=account();known_marks(a,0);fill(a,'BTCUSDT','SELL','.02',0,i.MINUTE+1,'SHORT')
        at=2*i.MINUTE
        a._quality_intervals=((at,at+2*i.MINUTE,i.S),)
        known_marks(a,at,{'BTCUSDT':75000})
        a.monitor('MONITOR:'+str(at),at)
        self.assertFalse(a.transfer_journal);self.assertIn('BTCUSDT',a.pending_exits)
        self.assertFalse(a.can_increase(at))
        known_marks(a,at+i.MINUTE,{'BTCUSDT':100000})
        self.assertIn(a.status,{'LIQUIDATION_REQUIRED_HALT','BANKRUPT_HALT'})
        self.assertFalse(a.settlement_journal)
        self.assertTrue(i.financial_reconciliation(a)['passed'])

    def test_affected_symbol_cancellation_only_and_new_signal_lock(self):
        sim,guard=sim_fixture('CONTINUE_ONLY');a=sim.account;start=sim.start
        known_marks(a,start);fill(a,'BTCUSDT','SELL','.02',start,start+i.MINUTE+1,'SHORT')
        raw=dict.fromkeys(i.S,D(0));raw['BTCUSDT']=D('-.03');raw['ETHUSDT']=D('.1')
        guard.original_schedule(raw,start+i.MINUTE,'DAILY_TARGET',('BTCUSDT','ETHUSDT'))
        eth=deepcopy(sim.pending['ETHUSDT'])
        at=start+2*i.MINUTE;known_marks(a,at,{'BTCUSDT':100000})
        self.assertNotIn('BTCUSDT',sim.pending);self.assertEqual(sim.pending['ETHUSDT'],eth)
        self.assertTrue(any(r.get('reason')=='CANCELLED_BY_ISOLATED_LIQUIDATION' for r in sim.rejections))
        with self.assertRaisesRegex(ValueError,'FRESH_NORMAL_SIGNAL'):
            a.execute_fill('BTCUSDT','BUY','.001',at+i.MINUTE+1,start+i.MINUTE,'STALE',
                execution_mid_price='100000',quote_available_us=at+i.MINUTE,available_quantity='.001')
        # Unaffected ETH endpoint is small and remains affordable after takeover.
        binding=guard.source.bind(start)
        cap=dict.fromkeys(i.S,D(100000));pending={s:sim.pending[s]['target'] if s in sim.pending else a.positions[s].quantity for s in i.S}
        prices={s:a._mark(s) for s in i.S}
        oracle=i.fresh_preview(a,tier_name='MID',binding=binding,prices=prices,
            price_available_us=dict.fromkeys(i.S,at),pending=pending,capacity=cap,
            event_us=at+1,signal_us=start,quote_available_us=at)
        witness=oracle.evaluate(pending,D(1));self.assertTrue(witness['allowed'],witness['reason'])
        invalid=dict(pending);invalid['ETHUSDT']=D(20)
        oracle=i.fresh_preview(a,tier_name='MID',binding=binding,prices=prices,
            price_available_us=dict.fromkeys(i.S,at),pending=invalid,capacity=cap,
            event_us=at+1,signal_us=start,quote_available_us=at)
        self.assertFalse(oracle.evaluate(invalid,D(1))['allowed'])

    def test_new_increase_rejects_hypothetical_forced_settlement_and_no_callback(self):
        a=account('CONTINUE_ONLY');known_marks(a,0);fill(a,'BTCUSDT','SELL','.02',0,i.MINUTE+1,'SHORT')
        before=a.preview_state_token();callbacks=[];a.liquidation_callback=lambda *x:callbacks.append(x)
        window,rows,d=fixture(1)
        # Binding signal0 needs a proper completed daily fixture; source bind at
        # fixture signal while mark clock remains causally earlier.
        signal=int(d[0]);known_marks(a,signal)
        binding=i.native.runtime()[5].CompletedBarSource(rows).bind(signal)
        pending={s:a.positions[s].quantity for s in i.S};pending['ETHUSDT']=D('.1')
        before=a.preview_state_token()
        prices={s:D(str(BASE[j])) for j,s in enumerate(i.S)};prices['BTCUSDT']=D(110000)
        oracle=i.fresh_preview(a,tier_name='MID',binding=binding,prices=prices,
            price_available_us=dict.fromkeys(i.S,signal+i.MINUTE),pending=pending,
            capacity=dict.fromkeys(i.S,D(100000)),event_us=signal+i.MINUTE+1,
            signal_us=signal,quote_available_us=signal+i.MINUTE)
        self.assertFalse(oracle.evaluate(pending,D(1))['allowed'])
        self.assertFalse(callbacks);self.assertTrue(i.native._exact_tree_equal(before,a.preview_state_token()))
        self.assertFalse(a.settlement_journal)

    def test_cashwatch_positive_capital_below_floor_and_debt_are_distinct(self):
        a=account();known_marks(a,0)
        # Genuine debit through unchanged funding consumes cash and then own
        # collateral; no synthetic cash mutation/forgiveness is used.
        fill(a,'BTCUSDT','BUY','.02',0,i.MINUTE+1,'LONG')
        at=2*i.MINUTE
        known_marks(a,at)
        a.apply_funding('BTCUSDT','DEBIT',at,D('8.2'),at)
        self.assertGreater(a.nav(),0);self.assertLess(a.free_cash,D(1000));self.assertFalse(a.unpaid_liability)
        a.monitor('MONITOR:'+str(at),at)
        self.assertEqual(a.mode(at),'CASH_ONLY_MONITOR')
        known_marks(a,3*i.MINUTE);self.assertEqual(a.clock_us,3*i.MINUTE)
        a.apply_funding('BTCUSDT','DEBT',4*i.MINUTE,D(100),4*i.MINUTE)
        self.assertGreater(a.unpaid_liability,0);self.assertEqual(a.status,'BANKRUPT_HALT')
        self.assertEqual(a.mode(),'DEBT_SETTLEMENT_BLOCKED');self.assertFalse(a.settlement_journal)
        self.assertTrue(i.financial_reconciliation(a)['passed'])


    def test_budget_shortage_paid_capacity_five_opens_renewal_and_latency(self):
        sim,guard=sim_fixture();a=sim.account;start=sim.start
        known_marks(a,start);fill(a,'BTCUSDT','SELL','.02',start,start+i.MINUTE+1,'SHORT')
        debit=start+2*i.MINUTE;known_marks(a,debit)
        a.apply_funding('BTCUSDT','FLOOR_DEBIT',debit,D(-8),debit)
        at=start+3*i.MINUTE;known_marks(a,at,{'BTCUSDT':75000})
        sim.risk_schedule(at)
        self.assertLessEqual(sum((D(r['decimal_strings']['amount']) for r in a.transfer_journal),D(0)),D('.25044'))
        self.assertIn('BTCUSDT',a.pending_exits)
        order=sim.pending['BTCUSDT'];self.assertEqual(order['kind'],'PROTECTIVE_STOP')
        self.assertEqual(order['signal_us'],at)
        # The only available BTC participation is .001 actual base lot/open.
        sim.previous_quote={s:75000. if s=='BTCUSDT' else 1e10 for s in i.S}
        market={s:dict(open=75000. if s=='BTCUSDT' else float(BASE[j]),
            close=75000. if s=='BTCUSDT' else float(BASE[j]),
            mark=75000. if s=='BTCUSDT' else float(BASE[j]),quote_volume=1e10) for j,s in enumerate(i.S)}
        before=abs(a.positions['BTCUSDT'].quantity)
        for k in range(1,6):
            open_us=at+k*i.MINUTE
            known_marks(a,open_us,{'BTCUSDT':75000})
            sim.attempt(open_us,market)
            rows=[r for r in a.trades if not r.get('liquidation_takeover') and r['event_us']==open_us+1]
            self.assertLessEqual(sum((D(r['decimal_strings']['quantity']) for r in rows),D(0)),D('.001'))
        self.assertEqual(abs(a.positions['BTCUSDT'].quantity),before-D('.005'))
        self.assertEqual(a.pending_exits['BTCUSDT']['renewals'],1)
        self.assertEqual(sim.pending['BTCUSDT']['attempts'],0)
        self.assertEqual(sim.pending['BTCUSDT']['signal_us'],at+5*i.MINUTE+1)
        frozen=abs(a.positions['BTCUSDT'].quantity)
        known_marks(a,at+6*i.MINUTE,{'BTCUSDT':75000});sim.attempt(at+6*i.MINUTE,market)
        self.assertEqual(abs(a.positions['BTCUSDT'].quantity),frozen)
        known_marks(a,at+7*i.MINUTE,{'BTCUSDT':75000});sim.attempt(at+7*i.MINUTE,market)
        self.assertEqual(abs(a.positions['BTCUSDT'].quantity),frozen-D('.001'))
        self.assertTrue(i.financial_reconciliation(a)['passed'])

    def test_repeating_basis_native_secondary_residual_retained_primary_exact(self):
        a=account('CONTINUE_ONLY')
        for k,(side,q,mid) in enumerate((('SELL','10','100'),('SELL','3','101'),('BUY','7','98'))):
            signal=k*2*i.MINUTE;event=signal+i.MINUTE+1
            a.update_marks(event-1,{s:dict(price='100',close_us=event-1,available_us=event-1) for s in i.S})
            a.execute_fill('BTCUSDT',side,q,event,signal,'REPEATING:'+str(k),
                execution_mid_price=mid,quote_available_us=event-1,available_quantity=q,reduce_only=side=='BUY')
        report=i.financial_reconciliation(a)
        self.assertTrue(report['passed'])
        self.assertTrue(report['exact_frozen_native_secondary_arithmetic_replay_match'])
        self.assertEqual(report['native_40digit_secondary_PnL_bridge_residual'],
            a.summary()['decimal_strings']['accounting_bridge_error_USDT'])
        self.assertTrue(all(D(v)==0 for k,v in report['errors'].items() if k!='isolated'))
        self.assertTrue(all(D(v)==0 for v in report['errors']['isolated'].values()))

    def test_installed_frozen_quality_guard_is_exact_and_blocks_new_risk(self):
        window,rows,d=fixture(1);start=int(d[0]);interval=(start+2*i.MINUTE,start+4*i.MINUTE,i.S)
        sim,guard=i.construct_case(window,rows,d,np.full((1,5),.03),policy_variant='CONTINUE_ONLY',
            generated_scope=i.GENERATED,quality_intervals=(interval,))
        self.assertIs(i.ContinuationQualityGuard.attempt,i.quality_module.CausalMarkQualityGuard.attempt)
        a=sim.account;known_marks(a,start+i.MINUTE)
        guard.original_schedule({s:D(100)/D(str(BASE[j])) for j,s in enumerate(i.S)},start+i.MINUTE,'DAILY_TARGET')
        guard.bindings[start+i.MINUTE]=guard.source.bind(start)
        at=start+2*i.MINUTE;known_marks(a,at)
        sim.previous_quote=dict.fromkeys(i.S,1e10)
        market={s:dict(open=float(BASE[j]),close=float(BASE[j]),mark=float(BASE[j]),quote_volume=1e10) for j,s in enumerate(i.S)}
        sim.attempt(at,market)
        self.assertFalse(a.trades)
        self.assertGreater(len(guard.causal_mark_quality_guard.receipts),0)
        self.assertTrue(all(a.mark_quality[s]=='UNKNOWN_OR_DERIVED' for s in i.S))

if __name__=='__main__':unittest.main()
