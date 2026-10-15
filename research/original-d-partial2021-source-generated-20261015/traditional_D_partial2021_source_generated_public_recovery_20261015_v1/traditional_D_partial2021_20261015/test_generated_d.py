"""Generated-only frozen-D multi-tier transport invariants."""
from copy import deepcopy
from decimal import Decimal as Q
from hashlib import sha256
import json
from pathlib import Path
import unittest
import numpy as np
import partial_d as e
from test_native_runtime import fixture,BASE

v=e.V2

def account(tier='MID'):
    a=v.grid.make_account(tier,'BASE27')
    return e.ExpansionAccount(a.config,symbols=e.S,instrument_profiles=a.instrument_profiles,
        generated_scope=e.GENERATED,tier_name=tier)

def marks(a,at,price=None):
    return a.update_marks(at,{s:dict(price=str(price if s=='BTCUSDT' and price is not None else BASE[j]),close_us=at,available_us=at) for j,s in enumerate(e.S)})

def fill(a,at=0):
    event=at+e.MINUTE+1;marks(a,event-1)
    return a.execute_fill('BTCUSDT','SELL','.02',event,at,'INITIAL',execution_mid_price='50000',quote_available_us=event-1,available_quantity='.02')

def finance(a):
    s=a.snapshot()
    return {k:s[k] for k in ('free_cash','unpaid_liability','positions','marks','totals','trades','funding','fill_requests','funding_events','funding_ids')}

class ExpansionTests(unittest.TestCase):
    def test_D_financial_policy_code_objects_identical(self):
        self.assertIs(e.ExpansionAccount.monitor,e.D.Guard50ExitAccount.monitor)
        self.assertIs(e.ExpansionAccount._transfer,e.D.Guard50ExitAccount._transfer)
        self.assertIs(e.ExpansionAccount.execute_fill,e.D.Guard50ExitAccount.execute_fill)
        self.assertIs(e.ExpansionAccount._leg,v.ENGINE.USDTLinearPerpetualAccount._leg)
        self.assertIs(e.ContinuationGuard.schedule.__code__,v.native.PartialTierGuard.schedule.__code__)
        self.assertIs(e.ContinuationGuard._frozen_attempt.__code__,v.native.PartialTierGuard.attempt.__code__)
        self.assertIs(e.ContinuationGuard.attempt,e.D.ContinuationGuard.attempt)
        self.assertIs(e.ContinuationQualityGuard.attempt,v.quality_module.CausalMarkQualityGuard.attempt)

    def test_three_nominal_tiers_keep_native_configuration_and_shared_caps(self):
        for tier in e.TIERS:
            with self.subTest(tier=tier):
                a=account(tier);plain=v.grid.make_account(tier,'BASE27')
                self.assertEqual(a.config,plain.config);self.assertEqual(a.instrument_profiles,plain.instrument_profiles)
                self.assertEqual(a.free_cash,Q(10000));self.assertFalse(a.topup_enabled)
                self.assertEqual(a.policy_variant,e.POLICY_VARIANT)
                self.assertEqual(a.contract_metadata()['bound_nominal_tier'],tier)
                before=a.preview_state_token()
                with self.assertRaisesRegex(ValueError,'TRANSFERS_FORBIDDEN'):a._transfer('BTCUSDT',Q(1),0,'FORBIDDEN')
                self.assertTrue(v.native._exact_tree_equal(before,a.preview_state_token()))
        with self.assertRaisesRegex(ValueError,'TIER_REQUIRED'):account('OTHER')

    def test_calm_three_tier_whole_native_financial_paths_match_frozen_native(self):
        for tier in e.TIERS:
            window,rows,d=fixture(1);weights=np.full((1,5),.03)
            old,og=v.native.build_case(window,rows,d,weights,tier_name=tier,generated_scope=e.GENERATED)
            new,ng=e.construct_case(window,rows,d,weights,tier_name=tier,generated_scope=e.GENERATED)
            for sim in (old,new):
                while sim.cursor<sim.end and sim.stop is None:sim.advance_day()
            self.assertEqual(finance(old.account),finance(new.account),tier)
            self.assertEqual(old.result()['minute'].to_numpy().tobytes(),new.result()['minute'].to_numpy().tobytes(),tier)
            self.assertGreater(len(new.account.trades),0);self.assertGreater(new.account.fees,0)
            self.assertTrue(e.case_result(new,ng)['primary_financial_reconciliation']['passed'])
            self.assertFalse(new.account.transfer_journal)

    def test_MID_gap_signal_transport_exact_frozen_D_finance_and_pending(self):
        window,rows,d=fixture(2);decision=int(d[1]);first,end=decision-2*e.MINUTE,decision+3*e.MINUTE
        intervals=((first,end,e.S),);weights=np.array([[.03]*5,[.05]*5])
        old,og=e.D.construct_case(window,rows,d,weights,generated_scope=e.GENERATED,quality_intervals=intervals)
        new,ng=e.construct_case(window,rows,d,weights,tier_name='MID',generated_scope=e.GENERATED,quality_intervals=intervals)
        for sim in (old,new):
            sim.trace=[];original=sim.risk_schedule
            def observed(at,*,sim=sim,original=original):
                result=original(at);sim.trace.append((at,deepcopy(sim.pending)));return result
            sim.risk_schedule=observed
            while sim.cursor<sim.end and sim.stop is None:sim.advance_day()
        self.assertEqual(finance(old.account),finance(new.account));self.assertEqual(old.trace,new.trace)
        self.assertEqual(len(new.account.trades),15)
        self.assertFalse(any(first<=r['event_us']<end and r['leg']=='OPEN' for r in new.account.trades))

    def test_warning_finance_and_intent_equal_frozen_D_in_every_tier(self):
        for tier in e.TIERS:
            a=account(tier);plain=v.grid.make_account(tier,'BASE27')
            old=e.D.Guard50ExitAccount(plain.config,symbols=e.S,instrument_profiles=plain.instrument_profiles,generated_scope=e.GENERATED)
            for x in (old,a):fill(x);marks(x,2*e.MINUTE,75000);x.monitor('MONITOR:'+str(2*e.MINUTE),2*e.MINUTE)
            self.assertEqual(finance(old),finance(a));self.assertEqual(old.pending_exits,a.pending_exits)
            self.assertFalse(a.transfer_journal);self.assertFalse(a.blocked_signals)

    def test_sameclock_nonzero_funding_batch_then_warning(self):
        window,rows,d=fixture(1);sim,g=e.construct_case(window,rows,d,np.zeros((1,5)),tier_name='HIGH',generated_scope=e.GENERATED)
        a=sim.account;start=sim.start;fill(a,start);at=start+2*e.MINUTE
        marks(a,at,75000)
        sim.window['events']=[dict(symbol=s,event_us=at,raw_rate=.0001,reported_interval_hours=8.) for s in e.S]
        seen=[];original=a.apply_funding
        def funded(*args,**kw):
            seen.append((args[0],bool(a.pending_exits)));return original(*args,**kw)
        a.apply_funding=funded;sim.funding_through(at,True);del a.apply_funding
        self.assertEqual(len(seen),5);self.assertFalse(any(flag for _,flag in seen))
        self.assertEqual(sim.pending['BTCUSDT']['kind'],'PROTECTIVE_STOP')
        self.assertEqual(sim.pending['BTCUSDT']['signal_us'],at)
        self.assertFalse(a.transfer_journal)

    def test_fresh_all_32_shared_wallet_corners_all_tiers_and_forks(self):
        window,rows,d=fixture(1);signal=int(d[0]);binding=v.native.runtime()[5].CompletedBarSource(rows).bind(signal)
        for tier in e.TIERS:
            a=account(tier);marks(a,signal)
            target={s:a._floor(s,Q(100)/Q(str(BASE[j]))) for j,s in enumerate(e.S)};before=a.preview_state_token()
            oracle=e.fresh_preview(a,tier_name=tier,binding=binding,prices={s:Q(str(BASE[j])) for j,s in enumerate(e.S)},
                price_available_us=dict.fromkeys(e.S,signal+e.MINUTE),pending=target,capacity=dict.fromkeys(e.S,Q(100000)),
                event_us=signal+e.MINUTE+1,signal_us=signal,quote_available_us=signal+e.MINUTE)
            r=oracle.evaluate(target,Q(1));self.assertTrue(r['allowed'],r['reason']);self.assertEqual(len(r['corners_checked']),32)
            self.assertTrue(v.native._exact_tree_equal(before,a.preview_state_token()))
            clone=a.fork_for_preview();self.assertIs(type(clone),e.ExpansionAccount)
            clone.pending_exits['BTCUSDT']=dict(signal_us=signal,reason='TEST');self.assertFalse(a.pending_exits)

    def test_known_unknown_quality_and_terminal_rule_remain_D(self):
        a=account('LOW');fill(a);at=2*e.MINUTE
        a._quality_intervals=((at,at+e.MINUTE,e.S),);marks(a,at,75000)
        a.monitor('MONITOR:'+str(at),at);self.assertFalse(a.pending_exits);self.assertFalse(a.can_increase(at))
        marks(a,at+e.MINUTE,75000);a.monitor('MONITOR:'+str(at+e.MINUTE),at+e.MINUTE)
        self.assertIn('BTCUSDT',a.pending_exits)
        with self.assertRaisesRegex(NotImplementedError,'NOT_CERTIFIED'):a.from_snapshot({})

if __name__=='__main__':unittest.main()
