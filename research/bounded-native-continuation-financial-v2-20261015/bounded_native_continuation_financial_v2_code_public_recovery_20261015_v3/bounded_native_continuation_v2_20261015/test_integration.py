"""Generated-only coupled native continuation tests; never use historical source."""
from decimal import Decimal as D
import unittest
import numpy as np
import integration as i
from test_native_runtime import fixture,BASE,COST

def account(variant='TOPUP_THEN_CONTINUE',settlement=i.SETTLEMENT):
    plain=i.grid.make_account('MID','BASE27')
    return i.ContinuationAccount(plain.config,symbols=i.S,instrument_profiles=plain.instrument_profiles,
        generated_scope=i.GENERATED,settlement_mode=settlement,policy_variant=variant)

def marks(a,clock,price=100):
    a.update_marks(clock,{s:dict(price=str(price),close_us=clock,available_us=clock) for s in i.S})

def run_case(days=1,variant='CONTINUE_ONLY',weights=None):
    window,rows,d=fixture(days)
    if weights is None:weights=np.full((days,5),.03)
    sim,guard=i.construct_case(window,rows,d,weights,policy_variant=variant,generated_scope=i.GENERATED)
    while sim.cursor<sim.end and sim.stop is None:sim.advance_day()
    return sim,guard

class IntegrationTests(unittest.TestCase):
    def test_native_source_method_reuse(self):
        self.assertIs(i.ContinuationAccount._leg,i.ENGINE.USDTLinearPerpetualAccount._leg)
        self.assertIs(i.ContinuationGuard._frozen_attempt.__code__,i.native.PartialTierGuard.attempt.__code__)
        self.assertIs(i.ContinuationGuard.schedule.__code__,i.native.PartialTierGuard.schedule.__code__)
        self.assertIs(i.primitives().BoundedContinuationAccount.__mro__[1],i.ENGINE.USDTLinearPerpetualAccount)

    def test_three_modes_generated_calendar_paid_and_cashflow(self):
        for variant in ('NATIVE_STOP_REFERENCE','CONTINUE_ONLY','TOPUP_THEN_CONTINUE'):
            with self.subTest(variant=variant):
                sim,guard=run_case(variant=variant)
                result=i.case_result(sim,guard)
                self.assertIsNone(sim.stop);self.assertEqual(sim.rows_written,1440)
                self.assertTrue(result['economics']['actual_paid_market_flat'])
                self.assertTrue(result['primary_financial_reconciliation']['passed'])
                self.assertLess(len(sim.account.monitor_journal),20)
                self.assertLessEqual(len(sim.account._noop_receipts),64)
                self.assertFalse(sim.account.settlement_journal)
                self.assertGreater(len(sim.account.trades),0)
                self.assertGreater(sim.account.fees,0)
                self.assertGreater(len(sim.account.financial_ledger),0)

    def test_native_stop_reference_matches_frozen_generated(self):
        window,rows,d=fixture(1);weights=np.full((1,5),.03)
        old,g=i.native.build_case(window,rows,d,weights,tier_name='MID',generated_scope=i.GENERATED)
        while old.cursor<old.end and old.stop is None:old.advance_day()
        sim,guard=run_case(variant='NATIVE_STOP_REFERENCE')
        for key in ('free_cash','unpaid_liability','positions','marks','totals','trades','funding','fill_requests'):
            self.assertEqual(old.account.snapshot()[key],sim.account.snapshot()[key],key)
        self.assertEqual(old.result()['minute'].to_numpy().tobytes(),sim.result()['minute'].to_numpy().tobytes())

    def test_bounded_noop_cache_eviction_and_financial_id_permanence(self):
        a=account();marks(a,0);a.monitor('MONITOR:0',0);first=a.monitor('MONITOR:0',0)
        for x in range(1,90):
            marks(a,x*i.MINUTE);a.monitor('MONITOR:'+str(x*i.MINUTE),x*i.MINUTE)
        before=a.preview_state_token()
        self.assertEqual(len(a._noop_receipts),64);self.assertLess(len(a.operation_ids),5)
        self.assertEqual(a.monitor('MONITOR:0',0),first)
        with self.assertRaisesRegex(ValueError,'EXPIRED'):a.monitor('MONITOR:'+str(i.MINUTE),i.MINUTE)
        self.assertTrue(i.native._exact_tree_equal(before,a.preview_state_token()))
        with self.assertRaisesRegex(ValueError,'CANONICAL'):a.monitor('arbitrary',a.clock_us)

    def test_full32corners_isolated_and_shared_pending(self):
        window,rows,d=fixture(1);a=account();signal=int(d[0]);a.update_marks(signal,{s:dict(price=str(BASE[j]),close_us=signal,available_us=signal) for j,s in enumerate(i.S)})
        bind=i.native.runtime()[5].CompletedBarSource(rows).bind(signal)
        before=a.preview_state_token();pending={s:a._floor(s,D(100)/D(str(BASE[j]))) for j,s in enumerate(i.S)}
        oracle=i.fresh_preview(a,tier_name='MID',binding=bind,prices={s:D(str(BASE[j])) for j,s in enumerate(i.S)},
            price_available_us=dict.fromkeys(i.S,signal+i.MINUTE),pending=pending,
            capacity=dict.fromkeys(i.S,D(100000)),event_us=signal+i.MINUTE+1,
            signal_us=signal,quote_available_us=signal+i.MINUTE)
        witness=oracle.evaluate(pending,D(1))
        self.assertTrue(witness['allowed'],witness['reason']);self.assertEqual(len(witness['corners_checked']),32)
        self.assertTrue(i.native._exact_tree_equal(before,a.preview_state_token()))
        clone=a.fork_for_preview();clone.pending_exits['BTCUSDT']=dict(signal_us=signal,reason='TEST')
        clone.capacity_used[('BTCUSDT',signal)]=D(2);clone.blocked_signals['BTCUSDT']=signal
        self.assertFalse(a.pending_exits);self.assertFalse(a.capacity_used);self.assertFalse(a.blocked_signals)

    def test_historical_or_resume_gate_remains_closed(self):
        window,rows,d=fixture(1)
        with self.assertRaisesRegex(ValueError,'SCOPE_REQUIRED'):
            i.construct_case(window,rows,d,np.full((1,5),.03),policy_variant='CONTINUE_ONLY')
        with self.assertRaisesRegex(NotImplementedError,'NOT_CERTIFIED'):account().from_snapshot({})
        with self.assertRaisesRegex(ValueError,'GENERATED_ONLY'):
            i.P.BoundedContinuationAccount(generated_scope='HISTORY',settlement_mode=i.SETTLEMENT)

if __name__=='__main__':unittest.main()
