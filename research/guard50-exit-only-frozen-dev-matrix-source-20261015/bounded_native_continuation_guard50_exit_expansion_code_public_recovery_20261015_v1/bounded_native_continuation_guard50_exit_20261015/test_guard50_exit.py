"""Generated-only D tests: real paid fills, immutable V2 and no margin transfer."""
from copy import deepcopy
from decimal import Decimal as D
import unittest
import numpy as np
import guard50_exit as d
from test_native_runtime import fixture,BASE

v=d.V2

def account():
    plain=v.grid.make_account('MID','BASE27')
    return d.Guard50ExitAccount(plain.config,symbols=d.S,instrument_profiles=plain.instrument_profiles,
        generated_scope=d.GENERATED,settlement_mode=d.SETTLEMENT)

def marks(a,clock,overrides=None):
    overrides=overrides or {}
    return a.update_marks(clock,{s:dict(price=str(overrides.get(s,BASE[j])),close_us=clock,available_us=clock) for j,s in enumerate(d.S)})

def fill(a,symbol='BTCUSDT',side='SELL',q='.02',signal=0,identity='INITIAL'):
    event=signal+d.MINUTE+1;marks(a,event-1)
    return a.execute_fill(symbol,side,q,event,signal,identity,execution_mid_price=str(BASE[d.S.index(symbol)]),
        quote_available_us=event-1,available_quantity=q,reduce_only=False)

def sim_fixture(intervals=()):
    window,rows,decisions=fixture(1)
    return d.construct_case(window,rows,decisions,np.zeros((1,5)),generated_scope=d.GENERATED,quality_intervals=intervals)

def finance(a):
    x=a.snapshot()
    return {k:x[k] for k in ('free_cash','unpaid_liability','positions','marks','totals','trades','funding','fill_requests','funding_events','funding_ids')}

class Guard50ExitTests(unittest.TestCase):
    def test_source_and_native_code_objects_unchanged(self):
        self.assertIs(d.Guard50ExitAccount._leg,v.ENGINE.USDTLinearPerpetualAccount._leg)
        self.assertIs(d.Guard50ExitAccount.execute_fill,v.ContinuationAccount.execute_fill)
        self.assertIs(d.ContinuationGuard._frozen_attempt.__code__,v.native.PartialTierGuard.attempt.__code__)
        self.assertIs(d.ContinuationGuard.schedule.__code__,v.native.PartialTierGuard.schedule.__code__)
        self.assertIs(d.ContinuationQualityGuard.attempt,v.quality_module.CausalMarkQualityGuard.attempt)
        self.assertIs(v.TokenView.__init__.__globals__['ContinuationAccount'],v.ContinuationAccount)
        self.assertIs(v.ContinuationGuard.schedule.__globals__['signal_preview'],v.signal_preview)

    def test_generated_only_and_readonly_d_variant(self):
        with self.assertRaisesRegex(ValueError,'GENERATED_ONLY'):d.Guard50ExitAccount(generated_scope='HISTORY')
        with self.assertRaisesRegex(ValueError,'SCOPE_REQUIRED'):d.Guard50ExitAccount(historical_scope=object())
        with self.assertRaisesRegex(ValueError,'EXACT_D'):d.Guard50ExitAccount(generated_scope=d.GENERATED,policy_variant='CONTINUE_ONLY')
        a=account();self.assertEqual(a.policy_variant,d.POLICY_VARIANT);self.assertFalse(a.topup_enabled)
        with self.assertRaises(AttributeError):a.policy_variant='TOPUP_THEN_CONTINUE'
        with self.assertRaisesRegex(NotImplementedError,'NOT_CERTIFIED'):a.from_snapshot({})

    def test_direct_transfer_forbidden_without_state_change(self):
        a=account();fill(a);before=a.preview_state_token()
        with self.assertRaisesRegex(ValueError,'TRANSFERS_FORBIDDEN'):a._transfer('BTCUSDT',D(1),a.clock_us,'DIRECT')
        self.assertTrue(v.native._exact_tree_equal(before,a.preview_state_token()))
        self.assertFalse(a.transfer_journal);self.assertFalse(a.transfer_ids)

    def test_guard50_exact_boundary_no_transfer_or_instant_fill(self):
        a=account();fill(a);p=a.positions['BTCUSDT'];clock=2*d.MINUTE
        boundary=p.entry_price+(p.isolated_balance/D(2)-p.isolated_balance)/p.quantity
        marks(a,clock,{'BTCUSDT':boundary-D('.01')})
        a.monitor('MONITOR:'+str(clock),clock);self.assertFalse(a.pending_exits)
        clock+=d.MINUTE;marks(a,clock,{'BTCUSDT':boundary})
        before=a._balances();receipt=a.monitor('MONITOR:'+str(clock),clock)
        self.assertEqual(a._balances(),before)
        self.assertEqual(a.pending_exits['BTCUSDT'],dict(signal_us=clock,reason='GUARD50_PAID_EXIT_NO_TOPUP'))
        self.assertEqual(receipt['actions'][0]['transferred'],'0');self.assertFalse(a.transfer_journal)
        self.assertEqual(a.positions['BTCUSDT'].quantity,D('-.02'))
        self.assertFalse(a.can_increase(clock));self.assertFalse(a.blocked_signals)
        self.assertTrue(v.financial_reconciliation(a)['passed'])

    def test_long_guard50_exact_boundary_and_strictly_above(self):
        a=account();fill(a,side='BUY');p=a.positions['BTCUSDT'];clock=2*d.MINUTE
        boundary=p.entry_price+(p.isolated_balance/D(2)-p.isolated_balance)/p.quantity
        marks(a,clock,{'BTCUSDT':boundary+D('.01')})
        a.monitor('MONITOR:'+str(clock),clock);self.assertFalse(a.pending_exits)
        clock+=d.MINUTE;marks(a,clock,{'BTCUSDT':boundary})
        before=a._balances();a.monitor('MONITOR:'+str(clock),clock)
        self.assertEqual(a._balances(),before);self.assertIn('BTCUSDT',a.pending_exits)
        self.assertFalse(a.transfer_journal);self.assertTrue(v.financial_reconciliation(a)['passed'])

    def test_warning_matches_C_trigger_but_not_cashflow(self):
        a=account();plain=v.grid.make_account('MID','BASE27')
        c=v.ContinuationAccount(plain.config,symbols=d.S,instrument_profiles=plain.instrument_profiles,
            generated_scope=d.GENERATED,settlement_mode=d.SETTLEMENT,policy_variant='TOPUP_THEN_CONTINUE')
        for x in (a,c):fill(x);marks(x,2*d.MINUTE,{'BTCUSDT':75000})
        self.assertEqual(finance(a),finance(c))
        for x in (a,c):x.monitor('MONITOR:'+str(2*d.MINUTE),2*d.MINUTE)
        self.assertEqual(set(a.pending_exits),{'BTCUSDT'});self.assertFalse(a.transfer_journal)
        self.assertEqual(len(c.transfer_journal),1);self.assertFalse(c.pending_exits)
        self.assertEqual(a.nav(),c.nav());self.assertEqual(a.fees,c.fees)

    def test_mark_first_gap_cannot_be_rescued_or_fake_paid_flat(self):
        a=account();fill(a);marks(a,2*d.MINUTE,{'BTCUSDT':100000})
        self.assertEqual(len(a.settlement_journal),1)
        a.monitor('MONITOR:'+str(2*d.MINUTE),2*d.MINUTE)
        self.assertFalse(a.pending_exits);self.assertFalse(a.transfer_journal)
        self.assertFalse(a.economic_report()['paid_flat'])
        self.assertTrue(v.financial_reconciliation(a)['passed'])

    def test_unknown_quality_blocks_new_warning_and_topup_keeps_existing_exit(self):
        a=account();fill(a);at=2*d.MINUTE
        a._quality_intervals=((at,at+2*d.MINUTE,d.S),)
        marks(a,at,{'BTCUSDT':75000});a.monitor('MONITOR:'+str(at),at)
        self.assertFalse(a.pending_exits);self.assertFalse(a.transfer_journal);self.assertFalse(a.can_increase(at))
        marks(a,at+2*d.MINUTE,{'BTCUSDT':75000});a.monitor('MONITOR:'+str(at+2*d.MINUTE),at+2*d.MINUTE)
        intent=deepcopy(a.pending_exits)
        a._quality_intervals=((at+3*d.MINUTE,at+4*d.MINUTE,d.S),)
        marks(a,at+3*d.MINUTE,{'BTCUSDT':75000});a.monitor('MONITOR:'+str(at+3*d.MINUTE),at+3*d.MINUTE)
        self.assertEqual(a.pending_exits,intent);self.assertFalse(a.transfer_journal)

    def test_sameclock_full_funding_batch_before_warning_and_pending_native_exit(self):
        sim,g=sim_fixture();a=sim.account;start=sim.start;fill(a,signal=start)
        at=start+2*d.MINUTE;marks(a,at,{'BTCUSDT':75000})
        sim.window['events']=[dict(symbol=s,event_us=at,raw_rate=.0001,reported_interval_hours=8.) for s in d.S]
        phases=[];original=a.apply_funding
        def trace(*args,**kw):
            phases.append((args[0],bool(a.pending_exits)));return original(*args,**kw)
        a.apply_funding=trace;sim.funding_through(at,True);del a.apply_funding
        self.assertEqual(len(phases),5);self.assertFalse(any(flag for _,flag in phases))
        self.assertEqual(sim.pending['BTCUSDT']['kind'],'PROTECTIVE_STOP')
        self.assertEqual(sim.pending['BTCUSDT']['signal_us'],at)
        self.assertFalse(a.transfer_journal);self.assertEqual(len(a.trades),1)

    def test_paid_partial_capacity_five_opens_renewal_and_latency_through_quality_gap(self):
        sim,g=sim_fixture();a=sim.account;start=sim.start;fill(a,signal=start)
        at=start+2*d.MINUTE;marks(a,at,{'BTCUSDT':75000});sim.risk_schedule(at)
        a._quality_intervals=((at+d.MINUTE,at+9*d.MINUTE,d.S),)
        sim.previous_quote={s:75000. if s=='BTCUSDT' else 1e10 for s in d.S}
        market={s:dict(open=75000. if s=='BTCUSDT' else float(BASE[j]),close=75000. if s=='BTCUSDT' else float(BASE[j]),
            mark=75000. if s=='BTCUSDT' else float(BASE[j]),quote_volume=1e10) for j,s in enumerate(d.S)}
        before=abs(a.positions['BTCUSDT'].quantity)
        for k in range(1,6):
            clock=at+k*d.MINUTE;marks(a,clock,{'BTCUSDT':75000});sim.attempt(clock,market)
            rows=[r for r in a.trades if r['event_us']==clock+1]
            self.assertEqual(sum((D(r['decimal_strings']['quantity']) for r in rows),D(0)),D('.001'))
        self.assertEqual(abs(a.positions['BTCUSDT'].quantity),before-D('.005'))
        self.assertEqual(a.pending_exits['BTCUSDT']['renewals'],1)
        self.assertEqual(sim.pending['BTCUSDT']['signal_us'],at+5*d.MINUTE+1)
        frozen=a.positions['BTCUSDT'].quantity
        marks(a,at+6*d.MINUTE,{'BTCUSDT':75000});sim.attempt(at+6*d.MINUTE,market)
        self.assertEqual(a.positions['BTCUSDT'].quantity,frozen)
        marks(a,at+7*d.MINUTE,{'BTCUSDT':75000});sim.attempt(at+7*d.MINUTE,market)
        self.assertEqual(a.positions['BTCUSDT'].quantity,frozen+D('.001'))
        self.assertFalse(a.transfer_journal);self.assertFalse(a.blocked_signals)
        self.assertGreater(a.fees,D(0));self.assertTrue(v.financial_reconciliation(a)['passed'])

    def test_preview_32_corners_preserves_D_live_state_and_cash(self):
        a=account();window,rows,decisions=fixture(1);signal=int(decisions[0]);marks(a,signal)
        binding=v.native.runtime()[5].CompletedBarSource(rows).bind(signal)
        target={s:a._floor(s,D(100)/D(str(BASE[j]))) for j,s in enumerate(d.S)}
        before=a.preview_state_token()
        oracle=d.fresh_preview(a,tier_name='MID',binding=binding,prices={s:D(str(BASE[j])) for j,s in enumerate(d.S)},
            price_available_us=dict.fromkeys(d.S,signal+d.MINUTE),pending=target,capacity=dict.fromkeys(d.S,D(100000)),
            event_us=signal+d.MINUTE+1,signal_us=signal,quote_available_us=signal+d.MINUTE)
        result=oracle.evaluate(target,D(1));self.assertTrue(result['allowed'],result['reason'])
        self.assertEqual(len(result['corners_checked']),32)
        self.assertTrue(v.native._exact_tree_equal(before,a.preview_state_token()))
        clone=a.fork_for_preview();self.assertIs(type(clone),d.Guard50ExitAccount)
        clone.pending_exits['BTCUSDT']=dict(signal_us=signal,reason='TEST')
        self.assertFalse(a.pending_exits)
        with self.assertRaisesRegex(ValueError,'TRANSFERS_FORBIDDEN'):clone._transfer('BTCUSDT',D(1),signal,'PREVIEW')

    def test_exact_noop_replay_and_pending_intent_ids_retained(self):
        a=account();fill(a);at=2*d.MINUTE;marks(a,at,{'BTCUSDT':75000})
        receipt=a.monitor('MONITOR:'+str(at),at);before=a.preview_state_token()
        self.assertEqual(a.monitor('MONITOR:'+str(at),at),receipt)
        self.assertTrue(v.native._exact_tree_equal(before,a.preview_state_token()))
        original=deepcopy(a.pending_exits['BTCUSDT'])
        for k in range(1,80):
            clock=at+k*d.MINUTE;marks(a,clock,{'BTCUSDT':75000});a.monitor('MONITOR:'+str(clock),clock)
        self.assertEqual(a.pending_exits['BTCUSDT'],original)
        self.assertIn('MONITOR:'+str(at),a.operation_ids);self.assertLessEqual(len(a._noop_receipts),64)
        with self.assertRaisesRegex(ValueError,'EXPIRED'):a.monitor('MONITOR:'+str(at+d.MINUTE),at+d.MINUTE)

    def test_full_calm_calendar_nonzero_paid_trades_matches_B(self):
        window,rows,decisions=fixture(1);weights=np.full((1,5),.03)
        b,bg=v.construct_case(window,rows,decisions,weights,policy_variant='CONTINUE_ONLY',generated_scope=d.GENERATED)
        x,xg=d.construct_case(window,rows,decisions,weights,generated_scope=d.GENERATED)
        for sim in (b,x):
            while sim.cursor<sim.end and sim.stop is None:sim.advance_day()
        self.assertEqual(finance(b.account),finance(x.account))
        self.assertEqual(b.result()['minute'].to_numpy().tobytes(),x.result()['minute'].to_numpy().tobytes())
        self.assertGreater(len(x.account.trades),0);self.assertGreater(x.account.fees,D(0))
        result=d.case_result(x,xg);self.assertTrue(result['economics']['actual_paid_market_flat'])
        self.assertFalse(result['common_execution_policy']['automatic_topup']);self.assertFalse(x.account.transfer_journal)

    def test_daily_signal_inside_gap_preserves_B_pending_trade_financial_path(self):
        window,rows,decisions=fixture(2);decision=int(decisions[1]);first,end=decision-2*d.MINUTE,decision+3*d.MINUTE
        weights=np.array([[.03]*5,[.05]*5]);interval=((first,end,d.S),)
        b,bg=v.construct_case(window,rows,decisions,weights,policy_variant='CONTINUE_ONLY',generated_scope=d.GENERATED,quality_intervals=interval)
        x,xg=d.construct_case(window,rows,decisions,weights,generated_scope=d.GENERATED,quality_intervals=interval)
        for sim in (b,x):
            sim.trace=[];original=sim.risk_schedule
            def observed(at,*,sim=sim,original=original):
                value=original(at);sim.trace.append((at,deepcopy(sim.pending)));return value
            sim.risk_schedule=observed
            while sim.cursor<sim.end and sim.stop is None:sim.advance_day()
        self.assertEqual(finance(b.account),finance(x.account));self.assertEqual(b.trace,x.trace)
        self.assertEqual(len(x.account.trades),15);self.assertFalse(x.account.pending_exits)
        self.assertFalse(any(first<=r['event_us']<end and r['leg']=='OPEN' for r in x.account.trades))

if __name__=='__main__':unittest.main()
