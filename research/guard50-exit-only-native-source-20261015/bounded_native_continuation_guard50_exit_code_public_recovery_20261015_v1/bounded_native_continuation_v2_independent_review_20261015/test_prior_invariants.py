"""Independent coupled generated tests. No historical scope or data is used."""
from copy import deepcopy
from decimal import Decimal as D
import json
from pathlib import Path
import tempfile
import unittest

import numpy as np
import integration as i
import run_finite as runner
import test_finite as finite_fixtures
from test_native_runtime import fixture, BASE


def account(mode=i.SETTLEMENT, variant='TOPUP_THEN_CONTINUE'):
    plain = i.grid.make_account('MID', 'BASE27')
    return i.ContinuationAccount(plain.config, symbols=i.S,
        instrument_profiles=plain.instrument_profiles, generated_scope=i.GENERATED,
        settlement_mode=mode, policy_variant=variant)


def marks(a, at, prices='100'):
    a.update_marks(at, {s:dict(price=str(prices[s] if isinstance(prices, dict) else prices),
        close_us=at, available_us=at) for s in i.S})


def short(a, symbol='BTCUSDT', quantity='10', at=i.MINUTE+1, signal=0, mid='100', fill_id='open'):
    return a.execute_fill(symbol, 'SELL', quantity, at, signal, fill_id,
        execution_mid_price=mid, quote_available_us=at-1)


class IndependentIntegration(unittest.TestCase):
    def test_full_native_calendar_executes_nonzero_paid_B_and_C(self):
        for variant in ('CONTINUE_ONLY','TOPUP_THEN_CONTINUE'):
            with self.subTest(variant=variant):
                window,rows,d=fixture(1)
                sim,guard=i.construct_case(window,rows,d,np.full((1,5),.03),
                    policy_variant=variant,generated_scope=i.GENERATED)
                while sim.cursor<sim.end and sim.stop is None:sim.advance_day()
                self.assertIsNone(sim.stop);self.assertEqual(sim.rows_written,1440)
                self.assertGreater(len(sim.account.trades),0)
                self.assertGreater(sim.account.fees,0)
                self.assertGreater(sim.account.execution_cost,0)
                self.assertGreater(len(sim.account.financial_ledger),0)
                self.assertTrue(i.financial_reconciliation(sim.account)['passed'])
                result=i.case_result(sim,guard)
                self.assertTrue(result['economics']['actual_paid_market_flat'])

    def test_native_mark_wave_topup_continuation_and_terminal_taxonomy(self):
        for variant in ('CONTINUE_ONLY','TOPUP_THEN_CONTINUE'):
            with self.subTest(variant=variant):
                window,rows,d=fixture(1)
                for j,s in enumerate(i.S):
                    window['market'][s]['mark'][20]=BASE[j]*1.5
                    window['market'][s]['mark'][21]=BASE[j]*2.1
                sim,guard=i.construct_case(window,rows,d,np.full((1,5),-.03),
                    policy_variant=variant,generated_scope=i.GENERATED)
                while sim.cursor<sim.end and sim.stop is None:sim.advance_day()
                self.assertIsNone(sim.stop);self.assertEqual(sim.rows_written,1440)
                self.assertGreater(len(sim.account.trades),0)
                result=i.case_result(sim,guard);e=result['economics']
                self.assertTrue(result['primary_financial_reconciliation']['passed'])
                self.assertTrue(e['full_calendar'])
                if variant=='CONTINUE_ONLY':
                    self.assertEqual(len(sim.account.transfer_journal),0)
                    self.assertGreater(len(sim.account.settlement_journal),0)
                    self.assertFalse(e['actual_paid_market_flat'])
                    self.assertIsNone(e['paid_net_return'])
                    self.assertTrue(e['conditional_settled_flat'])
                    self.assertIsNotNone(e['conditional_model_net_return'])
                else:
                    self.assertGreater(len(sim.account.transfer_journal),0)
                    self.assertEqual(len(sim.account.settlement_journal),0)
                    self.assertTrue(e['actual_paid_market_flat'])
                    self.assertIsNotNone(e['paid_net_return'])
                self.assertEqual(e['actual_liquidation_fills'],0)
                self.assertFalse(e['native_settlement_certified'])

    def test_conditional_clearing_precedes_global_solvency_but_unknown_does_not(self):
        for mode in (i.SETTLEMENT, 'UNKNOWN_UNSETTLED'):
            with self.subTest(mode=mode):
                a=account(mode, 'CONTINUE_ONLY'); marks(a, 0); marks(a, i.MINUTE)
                short(a); cash=a.free_cash; marks(a, 2*i.MINUTE, '2000')
                self.assertEqual(a.free_cash, cash); self.assertEqual(a.unpaid_liability, 0)
                if mode == i.SETTLEMENT:
                    e=a.settlement_journal[0]['decimal_strings']
                    self.assertLess(D(e['NAV_before']), 0)
                    self.assertGreater(D(e['NAV_after']), 0)
                    self.assertGreater(D(e['conditional_insurance_value_received']), 0)
                    self.assertEqual(D(e['NAV_after'])-D(e['NAV_before']), D(e['settlement_value_cashflow']))
                    self.assertEqual(D(e['value_ledger_error']), 0)
                    self.assertEqual(a.positions['BTCUSDT'].quantity, 0)
                    self.assertNotIn(a.status, i.P.HALTS)
                else:
                    self.assertLess(a.nav(), 0); self.assertEqual(a.status, 'BANKRUPT_HALT')
                    self.assertEqual(a.positions['BTCUSDT'].quantity, -10)
                    self.assertEqual(len(a.settlement_journal), 0)
                self.assertTrue(i.financial_reconciliation(a)['passed'])

    def test_real_funding_debt_with_other_collateral_never_gets_support(self):
        a=account(variant='CONTINUE_ONLY'); marks(a, 0); marks(a, i.MINUTE)
        short(a); short(a, 'ETHUSDT', at=i.MINUTE+2, fill_id='openETH')
        a.apply_funding('BTCUSDT', 'unpaid', 2*i.MINUTE, '-20', 2*i.MINUTE)
        debt=a.unpaid_liability; self.assertGreater(debt, 0)
        self.assertGreater(a.positions['ETHUSDT'].isolated_balance, 0)
        a._risk('SECOND_CHECK')
        self.assertEqual(a.unpaid_liability, debt); self.assertEqual(a.status, 'BANKRUPT_HALT')
        self.assertEqual(len(a.settlement_journal), 0)
        self.assertTrue(i.financial_reconciliation(a)['passed'])

    def test_repeating_native_basis_keeps_exact_primary_financial_ledger(self):
        a=account();marks(a,0);marks(a,i.MINUTE);short(a)
        marks(a,2*i.MINUTE)
        a.execute_fill('BTCUSDT','SELL','3',2*i.MINUTE+1,i.MINUTE,'add',
            execution_mid_price='101',quote_available_us=2*i.MINUTE)
        marks(a,3*i.MINUTE)
        a.execute_fill('BTCUSDT','BUY','7',3*i.MINUTE+1,2*i.MINUTE,'partial',
            execution_mid_price='98',quote_available_us=3*i.MINUTE,reduce_only=True)
        reconciliation=i.financial_reconciliation(a)
        self.assertEqual(D(reconciliation['errors']['free_cash']),0)
        self.assertEqual(D(reconciliation['errors']['unpaid_liability']),0)
        self.assertTrue(all(D(x)==0 for x in reconciliation['errors']['isolated'].values()))
        self.assertEqual(D(reconciliation['errors']['NAV']),0)
        self.assertTrue(reconciliation['passed'],reconciliation)
        native=D(i.ENGINE.USDTLinearPerpetualAccount.summary(a)['decimal_strings']['accounting_bridge_error_USDT'])
        self.assertNotEqual(native,0)
        self.assertEqual(D(reconciliation['native_40digit_secondary_PnL_bridge_residual']),native)
        self.assertIs(reconciliation['exact_frozen_native_secondary_arithmetic_replay_match'],True)

    def test_noop_receipts_are_bounded_exact_and_financial_actions_permanent(self):
        a=account(); marks(a, 0); marks(a, i.MINUTE); short(a)
        marks(a, 2*i.MINUTE, '150')
        key='MONITOR:'+str(2*i.MINUTE); action=a.monitor(key, 2*i.MINUTE)
        for x in range(3, 103):
            marks(a, x*i.MINUTE, '150'); a.monitor('MONITOR:'+str(x*i.MINUTE), x*i.MINUTE)
        token=a.preview_state_token()
        self.assertEqual(len(a._noop_receipts), 64)
        self.assertEqual(len(a.transfer_journal), 1)
        self.assertEqual(a.monitor(key, 2*i.MINUTE), action)
        self.assertTrue(i.native._exact_tree_equal(token, a.preview_state_token()))
        with self.assertRaisesRegex(ValueError, 'EXPIRED'):
            a.monitor('MONITOR:'+str(3*i.MINUTE), 3*i.MINUTE)
        self.assertTrue(i.native._exact_tree_equal(token, a.preview_state_token()))
        self.assertTrue(i.financial_reconciliation(a)['passed'])

    def test_owned_fork_detaches_new_mutable_and_identity_state(self):
        a=account(); marks(a, 0); marks(a, i.MINUTE); short(a)
        marks(a, 2*i.MINUTE, '150'); a.monitor('MONITOR:'+str(2*i.MINUTE), 2*i.MINUTE)
        before=a.preview_state_token(); clone=a.fork_for_preview()
        clone.pending_exits['BTCUSDT']=dict(signal_us=2*i.MINUTE, reason='GENERATED')
        clone.capacity_used[('BTCUSDT', 3*i.MINUTE)]=D('1')
        clone.blocked_signals['ETHUSDT']=2*i.MINUTE
        clone.mark_quality['ETHUSDT']='UNKNOWN_OR_DERIVED'
        clone.operation_ids['extra']=dict(identity='generated', receipt={})
        marks(clone, 3*i.MINUTE, '300')
        self.assertGreater(len(clone.settlement_journal), len(a.settlement_journal))
        self.assertTrue(i.native._exact_tree_equal(before, a.preview_state_token()))
        self.assertTrue(i.financial_reconciliation(a)['passed'])
        self.assertTrue(i.financial_reconciliation(clone)['passed'])

    def test_preview_open_price_cannot_settle_real_inventory_or_cancel_real_orders(self):
        window, rows, d=fixture(1); signal=int(d[0]); a=account(variant='CONTINUE_ONLY')
        prices={s:D(str(v)) for s,v in zip(i.S,BASE)}
        marks(a, signal, prices); marks(a, signal+i.MINUTE, prices)
        short(a, quantity='.01', at=signal+i.MINUTE+1, signal=signal, mid=str(BASE[0]))
        external=[]; a.liquidation_callback=lambda s,t:external.append((s,t))
        binding=i.native.runtime()[5].CompletedBarSource(rows).bind(signal)
        opens=dict(prices); opens['BTCUSDT']=D('150000')
        before=a.preview_state_token(); target={s:a.positions[s].quantity for s in i.S}
        target['ETHUSDT']=D('.01')
        oracle=i.fresh_preview(a, tier_name='MID', binding=binding, prices=opens,
            price_available_us=dict.fromkeys(i.S, signal+2*i.MINUTE), pending=target,
            capacity=dict.fromkeys(i.S,D('100000')), event_us=signal+2*i.MINUTE+1,
            signal_us=signal, quote_available_us=signal+2*i.MINUTE)
        witness=oracle.evaluate(target, D(1))
        self.assertFalse(witness['allowed'])
        self.assertEqual(external, [])
        self.assertTrue(i.native._exact_tree_equal(before, a.preview_state_token()))
        self.assertEqual(len(a.settlement_journal), 0)

    def test_derived_mark_quality_is_installed_before_native_risk(self):
        a=account(); marks(a, 0); marks(a, i.MINUTE); short(a)
        a._quality_intervals=((2*i.MINUTE,3*i.MINUTE,tuple(i.S)),)
        marks(a, 2*i.MINUTE, '210')
        self.assertEqual(a.mark_quality['BTCUSDT'], 'UNKNOWN_OR_DERIVED')
        self.assertEqual(len(a.settlement_journal), 0)
        self.assertEqual(a.status, 'BANKRUPT_HALT')
        self.assertEqual(a.positions['BTCUSDT'].quantity, -10)

    def test_same_clock_monitor_waits_for_all_funding_members(self):
        window, rows, d=fixture(1); start=int(d[0]); clock=start+3*i.MINUTE
        window['events']=[dict(symbol=s,event_us=clock,raw_rate=-.001,reported_interval_hours=8.)
            for s in ('BTCUSDT','ETHUSDT')]
        sim,guard=i.construct_case(window, rows, d, np.full((1,5),-.03),
            policy_variant='TOPUP_THEN_CONTINUE',generated_scope=i.GENERATED)
        a=sim.account; prices={s:D(str(v)) for s,v in zip(i.S,BASE)}
        marks(a,start,prices); marks(a,start+i.MINUTE,prices)
        short(a, quantity='.001', at=start+i.MINUTE+1, signal=start,mid=str(BASE[0]))
        short(a,'ETHUSDT','.01',start+i.MINUTE+2,start,str(BASE[1]),'openETH')
        marks(a,clock-i.MINUTE,prices)
        marks(a,clock,{s:p*D('1.5') for s,p in prices.items()})
        self.assertEqual(len(a.transfer_journal),0)
        sim.funding_through(clock,True)
        kinds=[r['kind'] for r in a.financial_ledger if r['event_us']==clock]
        self.assertEqual(kinds[-3:],['NATIVE_FUNDING','NATIVE_FUNDING','INTERNAL_TRANSFER_OR_INTENT'])
        self.assertEqual(len(a.transfer_journal),2)
        self.assertEqual([r['symbol'] for r in a.funding],['BTCUSDT','ETHUSDT'])
        self.assertEqual(len([r for r in a.monitor_journal if r['event_us']==clock]),1)
        self.assertTrue(i.financial_reconciliation(a)['passed'])

    def test_native_takeover_cancels_only_affected_pending_and_blocks_old_signal(self):
        window,rows,d=fixture(1);start=int(d[0])
        sim,guard=i.construct_case(window,rows,d,np.full((1,5),-.03),
            policy_variant='CONTINUE_ONLY',generated_scope=i.GENERATED)
        a=sim.account; prices={s:D(str(v)) for s,v in zip(i.S,BASE)}
        marks(a,start,prices); marks(a,start+i.MINUTE,prices)
        short(a,quantity='.01',at=start+i.MINUTE+1,signal=start,mid=str(BASE[0]))
        guard.original_schedule(dict.fromkeys(i.S,D('-1')),start,'DAILY_TARGET',('BTCUSDT','ETHUSDT'))
        other=deepcopy(sim.pending['ETHUSDT'])
        marks(a,start+2*i.MINUTE,{**prices,'BTCUSDT':D('150000')})
        self.assertNotIn('BTCUSDT',sim.pending)
        self.assertEqual(sim.pending['ETHUSDT'],other)
        self.assertTrue(any(r['reason']=='CANCELLED_BY_ISOLATED_LIQUIDATION' for r in sim.rejections))
        self.assertEqual(a.blocked_signals['BTCUSDT'],start+2*i.MINUTE)
        with self.assertRaisesRegex(ValueError,'FRESH_NORMAL'):
            a.execute_fill('BTCUSDT','SELL','.001',start+3*i.MINUTE+1,start,'old',
                execution_mid_price='150000',quote_available_us=start+3*i.MINUTE)


class IndependentSavedRecords(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        finite_fixtures.SavedTerminalTests.setUpClass()

    def corrupt_partial(self, path, *, fake_halt):
        helper=finite_fixtures.SavedTerminalTests();kw=helper.fixture(path)
        receipt=json.loads((path/'CASE_RECEIPT.json').read_bytes())
        result=json.loads((path/'NATIVE_RESULT.json').read_bytes())
        audit=json.loads((path/'ACCOUNT_FINANCIAL_AUDIT.json').read_bytes())
        stop=receipt['calendar'][1] if fake_halt else None
        receipt.update(status='NATIVE_HALT_PARTIAL_CALENDAR',completed_minutes=1439,
            account_stop_us=stop,full_calendar=False,actual_paid_market_flat=False,
            conditional_settled_flat=False,comparable_full_calendar_return=None)
        result['summary'].update(completed_minutes=1439,stop_us=stop)
        result['economics'].update(full_calendar=False,actual_paid_market_flat=False,paid_flat=False,
            conditional_settled_flat=False,paid_net_return=None,conditional_model_net_return=None,
            comparable_full_calendar_return=None)
        if fake_halt:
            witness=dict(event_us=stop,phase='GENERATED_FAKE_INVALID_HALT',
                NAV=float(audit['free_cash']),unpaid_liability=0,
                decimal_strings=dict(NAV=audit['free_cash'],unpaid_liability='0'))
            audit.update(status='BANKRUPT_HALT',halt_witness=witness)
            result['summary'].update(account_status='BANKRUPT_HALT',halt_witness=witness)
            result['economics'].update(bankruptcy_halt=True,liquidation_required_halt=False)
        for name,value in [('CASE_RECEIPT.json',receipt),('NATIVE_RESULT.json',result),
                ('ACCOUNT_FINANCIAL_AUDIT.json',audit)]:
            (path/name).write_bytes(finite_fixtures.body(value))
        helper.checkpoint(path)
        return kw

    def test_resealed_active_incomplete_calendar_cannot_claim_native_halt(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder);kw=self.corrupt_partial(path,fake_halt=False)
            with self.assertRaises(ValueError):runner.validate_saved_terminal(path,**kw)

    def test_resealed_positive_flat_no_debt_cannot_claim_bankruptcy(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder);kw=self.corrupt_partial(path,fake_halt=True)
            with self.assertRaises(ValueError):runner.validate_saved_terminal(path,**kw)


if __name__=='__main__':unittest.main(verbosity=2)
