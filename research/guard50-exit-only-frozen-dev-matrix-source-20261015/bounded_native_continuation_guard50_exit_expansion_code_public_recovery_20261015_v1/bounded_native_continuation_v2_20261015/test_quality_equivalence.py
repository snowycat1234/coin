"""V2 correction regression: missing quality never invents a paid exit."""
from copy import deepcopy
from decimal import Decimal as D
import json
import unittest
import numpy as np
import integration as i
from test_native_runtime import fixture,BASE
from test_coupled_boundaries import known_marks,fill,sim_fixture


def finance_projection(a):
    snapshot=a.snapshot()
    return {key:snapshot[key] for key in ('free_cash','unpaid_liability','positions','marks','totals','trades','funding','fill_requests','funding_events','funding_ids')}


def make_pair(days=2,partial_existing_exit=False):
    window,rows,d=fixture(days);start=int(d[0])
    first,end=start+3*i.MINUTE,start+7*i.MINUTE
    # Funding includes a partial-bar event while the mark quality is unknown,
    # and a complete same-clock batch before genuine recovery.
    window['events']=[dict(symbol=s,event_us=at,raw_rate=.0001,reported_interval_hours=8.)
        for at in (first+30_000_000,first+i.MINUTE) for s in i.S]
    window['events'].sort(key=lambda r:(r['event_us'],i.S.index(r['symbol'])))
    if partial_existing_exit:
        # Existing actual paid reduction becomes capacity-limited across the
        # quality interval; the completed PRIOR-minute quote controls each open.
        window['market']['BTCUSDT']['quote_volume'][2:9]=50000.
    weights=np.full((days,5),.03);weights[:,0]=.10 if partial_existing_exit else .03
    old,old_guard=i.native.build_case(window,rows,d,weights,tier_name='MID',generated_scope=i.GENERATED)
    interval=i.quality_module.StaleMarkInterval(start_us=first,end_us=end,
        original_genuine_observation_us=first-i.MINUTE,symbols=i.S)
    old_quality=i.quality_module.CausalMarkQualityGuard(old_guard,intervals=(interval,),source_sidecar_sha256='d'*64).install()
    new,new_guard=i.construct_case(window,rows,d,weights,policy_variant='CONTINUE_ONLY',generated_scope=i.GENERATED,
        quality_intervals=((first,end,i.S),))
    if partial_existing_exit:
        for sim,guard in ((old,old_guard),(new,new_guard)):
            original=sim.attempt
            def scheduled(open_us,market_row,*,sim=sim,guard=guard,original=original):
                if open_us==start+2*i.MINUTE:
                    guard.original_schedule(dict.fromkeys(i.S,D(0)),open_us,'PROTECTIVE_STOP',('BTCUSDT',))
                return original(open_us,market_row)
            sim.attempt=scheduled
            # Preserve the frozen quality install invariant, already installed
            # above, while an outer generated test fixture schedules the intent.
    for sim in (old,new):
        sim.generated_pending_trace=[]
        original_risk=sim.risk_schedule
        def observed(event_us,*,sim=sim,original_risk=original_risk):
            result=original_risk(event_us)
            sim.generated_pending_trace.append((event_us,deepcopy(sim.pending)))
            return result
        sim.risk_schedule=observed
    return old,old_guard,new,new_guard,first,end


class QualityEquivalenceTests(unittest.TestCase):
    def test_missing_gap_and_partialbar_funding_entire_trade_and_minute_path_equal(self):
        old,og,new,ng,first,end=make_pair()
        while old.cursor<old.end and old.stop is None:old.advance_day()
        while new.cursor<new.end and new.stop is None:new.advance_day()
        self.assertGreater(len(old.account.trades),0)
        self.assertEqual(finance_projection(old.account),finance_projection(new.account))
        self.assertEqual(old.generated_pending_trace,new.generated_pending_trace)
        self.assertEqual(old.result()['minute'].to_numpy().tobytes(),new.result()['minute'].to_numpy().tobytes())
        self.assertFalse(new.account.pending_exits);self.assertFalse(new.account.settlement_journal)
        self.assertFalse(any(r.get('reason')=='CANCELLED_BY_ISOLATED_LIQUIDATION' for r in new.rejections))
        self.assertFalse(any(o['kind']=='PROTECTIVE_STOP' for o in new.pending.values()))
        self.assertEqual(len(old.funding_journal),10)
        self.assertTrue(i.financial_reconciliation(new.account)['passed'])

    def test_existing_paid_partial_exit_across_gap_matches_reference(self):
        old,og,new,ng,first,end=make_pair(days=1,partial_existing_exit=True)
        while old.cursor<old.end and old.stop is None:old.advance_day()
        while new.cursor<new.end and new.stop is None:new.advance_day()
        self.assertEqual(finance_projection(old.account),finance_projection(new.account))
        self.assertEqual(old.generated_pending_trace,new.generated_pending_trace)
        self.assertEqual(old.result()['minute'].to_numpy().tobytes(),new.result()['minute'].to_numpy().tobytes())
        closes=[r for r in new.account.trades if r['symbol']=='BTCUSDT' and r['leg']=='CLOSE' and first<=r['event_us']<end]
        self.assertGreaterEqual(len(closes),2)
        self.assertTrue(all(D(r['decimal_strings']['quantity'])==D('.001') for r in closes))

    def test_daily_target_inside_gap_retains_pending_and_recovers_to_same_opens(self):
        window,rows,d=fixture(2);decision=int(d[1]);first,end=decision-2*i.MINUTE,decision+3*i.MINUTE
        weights=np.array([[.03]*5,[.05]*5])
        old,og=i.native.build_case(window,rows,d,weights,tier_name='MID',generated_scope=i.GENERATED)
        interval=i.quality_module.StaleMarkInterval(start_us=first,end_us=end,
            original_genuine_observation_us=first-i.MINUTE,symbols=i.S)
        i.quality_module.CausalMarkQualityGuard(og,intervals=(interval,),source_sidecar_sha256='d'*64).install()
        new,ng=i.construct_case(window,rows,d,weights,policy_variant='CONTINUE_ONLY',generated_scope=i.GENERATED,
            quality_intervals=((first,end,i.S),))
        for sim in (old,new):
            sim.generated_pending_trace=[];original=sim.risk_schedule
            def traced(at,*,sim=sim,original=original):
                value=original(at);sim.generated_pending_trace.append((at,deepcopy(sim.pending)));return value
            sim.risk_schedule=traced
        while old.cursor<old.end and old.stop is None:old.advance_day()
        while new.cursor<new.end and new.stop is None:new.advance_day()
        self.assertEqual(finance_projection(old.account),finance_projection(new.account))
        self.assertEqual(old.generated_pending_trace,new.generated_pending_trace)
        self.assertEqual(len(old.account.trades),15);self.assertEqual(len(new.account.trades),15)
        self.assertEqual(old.result()['minute'].to_numpy().tobytes(),new.result()['minute'].to_numpy().tobytes())
        old_signal=[r for r in og.receipts if r.get('phase')=='SIGNAL_PARTIAL' and r.get('signal_us')==decision]
        new_signal=[r for r in ng.receipts if r.get('phase')=='SIGNAL_PARTIAL' and r.get('signal_us')==decision]
        self.assertEqual(old_signal,new_signal)
        self.assertFalse(any(first<=r['event_us']<end and r['leg']=='OPEN' for r in new.account.trades))

    def test_hypothetical_open_settlement_cannot_zero_real_fallback_inventory(self):
        from test_integration import account
        window,rows,d=fixture(1);signal=int(d[0]);sim,guard=sim_fixture('CONTINUE_ONLY');a=sim.account
        known_marks(a,signal);fill(a,'BTCUSDT','SELL','.02',signal,signal+i.MINUTE+1,'SHORT')
        known_marks(a,signal+2*i.MINUTE);before=a.preview_state_token()
        binding=i.native.runtime()[5].CompletedBarSource(rows).bind(signal)
        prices={s:D(str(BASE[j])) for j,s in enumerate(i.S)};prices['BTCUSDT']=D(110000)
        actual={s:a.positions[s].quantity for s in i.S};raw=dict(actual);raw['ETHUSDT']=D('.1')
        guard.original_schedule(raw,signal,'DAILY_TARGET')
        native_pending_before=deepcopy(sim.pending)
        oracle=i.fresh_preview(a,tier_name='MID',binding=binding,prices=prices,
            price_available_us=dict.fromkeys(i.S,signal+3*i.MINUTE),pending=raw,
            capacity=dict.fromkeys(i.S,D(100000)),event_us=signal+3*i.MINUTE+1,
            signal_us=signal,quote_available_us=signal+3*i.MINUTE)
        self.assertEqual(oracle.actual,actual)
        self.assertGreater(len(oracle.account.settlement_journal),len(a.settlement_journal))
        selection=i.sys.modules['candidate'].select_partial(actual=oracle.actual,raw_target=raw,evaluate=oracle.evaluate)
        self.assertTrue(selection.all_invalid);self.assertEqual(selection.target,actual)
        self.assertEqual(sim.pending,native_pending_before)
        self.assertEqual(a.positions['BTCUSDT'].quantity,D('-.02'))
        self.assertTrue(i.native._exact_tree_equal(before,a.preview_state_token()))
        self.assertFalse(a.settlement_journal)

    def test_B_and_C_unknown_quality_create_no_exit_and_preserve_existing_intent(self):
        for variant in ('CONTINUE_ONLY','TOPUP_THEN_CONTINUE'):
            with self.subTest(variant=variant):
                sim,guard=sim_fixture(variant);a=sim.account;start=sim.start
                known_marks(a,start);fill(a,'BTCUSDT','SELL','.02',start,start+i.MINUTE+1,'SHORT')
                at=start+2*i.MINUTE;a._quality_intervals=((at,at+2*i.MINUTE,i.S),)
                legitimate=dict(signal_us=start+i.MINUTE,reason='INSUFFICIENT_TOPUP_BUDGET',renewals=2)
                a.pending_exits['BTCUSDT']=deepcopy(legitimate)
                before=deepcopy(a.pending_exits);known_marks(a,at,{'BTCUSDT':75000})
                a.monitor('MONITOR:'+str(at),at)
                self.assertEqual(a.pending_exits,before);self.assertFalse(a.transfer_journal)
                self.assertFalse(a.can_increase(at));self.assertEqual(a.mode(at),'REDUCE_ONLY_MONITOR')
                # With no preexisting intent the same observation stays a
                # quality/cash watch, and does not introduce PROTECTIVE_STOP.
                clean,clean_guard=sim_fixture(variant);b=clean.account
                known_marks(b,start);fill(b,'BTCUSDT','SELL','.02',start,start+i.MINUTE+1,'SHORT')
                b._quality_intervals=((at,at+2*i.MINUTE,i.S),);known_marks(b,at,{'BTCUSDT':75000})
                clean.risk_schedule(at)
                self.assertFalse(b.pending_exits);self.assertFalse(b.transfer_journal)
                self.assertTrue(all(o['kind']!='PROTECTIVE_STOP' for o in clean.pending.values()))

if __name__=='__main__':unittest.main()
