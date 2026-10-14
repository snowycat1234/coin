"""Independent generated-only review. No historical source adapter is imported."""
from copy import deepcopy
from decimal import Decimal, ROUND_DOWN, localcontext
import hashlib
import json
from pathlib import Path
import sys
import shutil
import subprocess
import tempfile
import unittest
import numpy as np

DESIGN = Path(__file__).resolve().parent.parent / 'coin_bounded_highrisk_design_20261014'
sys.path.insert(0, str(DESIGN))
from bounded_policy import (STAGE, SYMBOLS, RiskStage, HighRiskToyAccount,
    CapitalGuard, ReservationBook, FiniteAddsPlan, FiniteAddsState, ProgramBudget,
    validate_intent_envelope, bounded_weights)
from source_preflight import verify, original_account_module
from vendor_quant.perpetual_account import PerpetualConfig, USDTLinearPerpetualAccount
from vendor_quant.execution_contract import ExecutionContractV2

D = Decimal
M = 60_000_000
ZERO = D('0')


def fresh(cls=HighRiskToyAccount, config=None):
    a = cls(config, symbols=SYMBOLS, closing_min_notional_exempt=True)
    marks(a, 0, 100)
    return a


def marks(a, t, values):
    if not isinstance(values, dict):
        values = dict.fromkeys(SYMBOLS, values)
    return a.update_marks(t, {s: {'price': str(values[s]), 'close_us': t, 'available_us': t}
                              for s in SYMBOLS})


def execute(a, symbol='BTCUSDT', side='BUY', q='1', *, t=M+1, signal=0,
            identity='FILL', mid='100', available=None, reduce=False, guard=True):
    target = CapitalGuard(a) if guard else a
    return target.execute_fill(symbol, side, D(str(q)), t, signal, identity,
        execution_mid_price=D(str(mid)), quote_available_us=t-1,
        available_quantity=D(str(q if available is None else available)), reduce_only=reduce)


def order_quantity(margin, price):
    with localcontext() as ctx:
        ctx.prec = 40
        return (D(str(margin)) / D(str(price))).quantize(D('.00000001'), rounding=ROUND_DOWN)


def flat_actual():
    return dict.fromkeys(SYMBOLS, ZERO)


class Identities(unittest.TestCase):
    def test_exact_source_freeze(self):
        pin = json.loads((Path(__file__).parent / 'SOURCE_SNAPSHOT.json').read_text())
        for relative, expected in pin['files'].items():
            self.assertEqual(hashlib.sha256((DESIGN / relative).read_bytes()).hexdigest(), expected, relative)

    def test_only_account_validation_line_changed(self):
        self.assertTrue(verify()['original_finance_methods_unchanged'])
        original = original_account_module()
        with self.assertRaises(ValueError):
            original.PerpetualConfig(max_gross_weight='.90')
        self.assertEqual(PerpetualConfig().max_gross_weight, D('.6'))

    def test_original_execution_contract_remains_baseline(self):
        self.assertEqual(ExecutionContractV2().max_gross, .60)
        self.assertEqual(ExecutionContractV2().annual_vol_target, .10)
        with self.assertRaises(ValueError):
            ExecutionContractV2(max_gross=.90, annual_vol_target=.15)

    def test_deferred_scopes_rejected(self):
        for kwargs in ({'leverage':'2'}, {'max_gross_weight':'1.20'}, {'max_asset_weight':'.31'}):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                PerpetualConfig(**kwargs)
        with self.assertRaises(ValueError):
            HighRiskToyAccount(PerpetualConfig())

    def test_plan_rejects_scope_or_parameter_drift(self):
        for kwargs in ({'initial_order_margin':'999'}, {'margin_multiplier':'1'},
                       {'maximum_adds':0}, {'maximum_adds':4}, {'direction':-1},
                       {'symbol':'ETHUSDT'}, {'owner':'RENAMED'},
                       {'total_sleeve_investment':'2000'}, {'loss_limit_fraction':'.1'}):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                FiniteAddsPlan(**kwargs)

    def test_original_decimal_account_parity_with_mixed_finance(self):
        original = original_account_module()
        a = fresh(original.USDTLinearPerpetualAccount, original.PerpetualConfig())
        b = fresh(USDTLinearPerpetualAccount, PerpetualConfig())
        for account in (a,b):
            execute(account, q='3.12345678', identity='OPEN', guard=False)
            execute(account, 'ETHUSDT', 'SELL', '4.44444444', identity='SHORT', guard=False)
            account.apply_funding('BTCUSDT', 'DEBIT', 2*M, '.00123', 0)
            account.apply_funding('ETHUSDT', 'CREDIT', 2*M, '.00234', 0)
            marks(account, 3*M, {s: '91' if s=='BTCUSDT' else '109' if s=='ETHUSDT' else '100' for s in SYMBOLS})
            execute(account, q='1.23456789', side='SELL', t=4*M+1, signal=3*M,
                    identity='PARTIAL_CLOSE', mid='91', reduce=True, guard=False)
            execute(account, 'ETHUSDT', 'BUY', '4.44444444', t=4*M+1, signal=3*M,
                    identity='FULL_CLOSE', mid='109', reduce=True, guard=False)
        self.assertEqual(a.snapshot(), b.snapshot())


class ColdLaunch(unittest.TestCase):
    def rejected(self, mutate, expected):
        with tempfile.TemporaryDirectory(prefix='negative_',dir=Path(__file__).parent) as temporary:
            root=Path(temporary); cold=root/'candidate'; cold.mkdir()
            frozen=json.loads((DESIGN/'SOURCE_FREEZE.json').read_text())
            for name in (*frozen['source_files_SHA256'], 'SOURCE_FREEZE.json'):
                target=cold/name; target.parent.mkdir(parents=True,exist_ok=True)
                shutil.copyfile(DESIGN/name,target)
            pins=json.loads((cold/'SOURCE_PINS.json').read_text())
            for pin in pins.values():
                first=Path(pin['source_path']).parts[0]
                link=root/first
                if not link.exists(): link.symlink_to(DESIGN.parent/first,target_is_directory=True)
            mutate(cold)
            result=subprocess.run([sys.executable,'run_toy.py'],cwd=cold,
                capture_output=True,text=True,timeout=15)
            self.assertNotEqual(result.returncode,0)
            self.assertIn(expected,(result.stdout+result.stderr).lower())

    def test_missing_freeze_rejects_fixed_toy_launch(self):
        self.rejected(lambda p:(p/'SOURCE_FREEZE.json').unlink(),'freeze')

    def test_changed_protocol_rejects_fixed_toy_launch(self):
        self.rejected(lambda p:(p/'PROTOCOL.json').write_text((p/'PROTOCOL.json').read_text()+'\n'),'frozen')

    def test_changed_policy_rejects_fixed_toy_launch(self):
        self.rejected(lambda p:(p/'bounded_policy.py').write_text((p/'bounded_policy.py').read_text()+'\n# drift\n'),'frozen')

    def test_historical_path_argument_rejects_without_reading(self):
        result=subprocess.run([sys.executable,str(DESIGN/'run_toy.py'),'DO_NOT_READ_MARKET_DATA'],
            capture_output=True,text=True,timeout=15)
        self.assertNotEqual(result.returncode,0)
        self.assertIn('no historical data path',result.stderr.lower())


class Capital(unittest.TestCase):
    def test_retired_capital_cannot_be_reused_under_fresh_name(self):
        book = ReservationBook()
        book.reserve('CSH', 8000)
        book.reserve('MART', 1000)
        book.release('MART', actual_quantity=0, pending_increase_count=0)
        self.assertEqual(book.available_initial_capital(), D('1000'))
        with self.assertRaises(ValueError):
            book.reserve('RENAMED_MART', 1)
        with self.assertRaises(ValueError):
            book.reserve('MART', 1)

    def test_partial_or_pending_inventory_prevents_release(self):
        for quantity, pending in ((D('.00000001'),0),(0,1)):
            book = ReservationBook(); book.reserve('MART',1000)
            with self.subTest(quantity=quantity,pending=pending), self.assertRaises(ValueError):
                book.release('MART',actual_quantity=quantity,pending_increase_count=pending)
            self.assertEqual(book.reservations, {'MART':D('1000')})

    def test_cash_topup_and_overcommitted_program_rejected(self):
        with self.assertRaises(ValueError):
            ReservationBook(initial_cash=D('10001')).reserve('TOPUP',1)
        book=ReservationBook(); book.reserve('A',8999)
        with self.assertRaises(ValueError): book.reserve('B',2)

    def test_actual_margin_just_below_8500_admitted(self):
        a=fresh()
        for s in SYMBOLS[:-1]: execute(a,s,q=20,identity='OPEN:'+s)
        receipt=execute(a,SYMBOLS[-1],q='4.932',identity='BELOW')
        self.assertEqual(receipt['status'],'FILLED')
        self.assertLess(sum(p.isolated_balance for p in a.positions.values()),D('8500'))
        self.assertGreaterEqual(a.free_cash,D('1000'))

    def test_actual_margin_just_above_8500_has_no_state_change(self):
        a=fresh()
        for s in SYMBOLS[:-1]: execute(a,s,q=20,identity='OPEN:'+s)
        before=deepcopy(a.snapshot())
        receipt=execute(a,SYMBOLS[-1],q='4.9325',identity='ABOVE')
        self.assertEqual(receipt['status'],'POLICY_REJECTED')
        self.assertEqual(a.snapshot(),before)

    def test_positional_replay_after_cash_floor_breach(self):
        a=fresh(); first=execute(a,q=10,identity='REPLAY')
        a.apply_funding('BTCUSDT','CASH_DRAIN',2*M,'8.1',0)
        before=deepcopy(a.snapshot())
        self.assertLess(a.free_cash,D('1000'))
        self.assertEqual(execute(a,q=10,identity='REPLAY'),first)
        self.assertEqual(a.snapshot(),before)

    def test_conflicting_replay_is_not_hidden_by_cash_guard(self):
        a=fresh(); execute(a,q=10,identity='REPLAY')
        a.apply_funding('BTCUSDT','CASH_DRAIN',2*M,'8.1',0)
        with self.assertRaises(ValueError): execute(a,q=11,identity='REPLAY')

    def test_cash_floor_blocks_increase_but_not_reduce_only(self):
        a=fresh(); execute(a,q=10,identity='OPEN')
        a.apply_funding('BTCUSDT','CASH_DRAIN',2*M,'8.1',0)
        before=deepcopy(a.snapshot())
        r=execute(a,q=1,t=3*M+1,signal=2*M,identity='INCREASE')
        self.assertEqual(r['reason'],'INITIAL_CASH_FLOOR_BREACHED')
        self.assertEqual(a.snapshot(),before)
        r=execute(a,side='SELL',q=1,t=3*M+1,signal=2*M,identity='REDUCE',reduce=True)
        self.assertEqual(r['status'],'FILLED')


class FiniteProgram(unittest.TestCase):
    def test_fixed_margin_geometry_and_positive_reserve(self):
        p=FiniteAddsPlan()
        self.assertEqual(p.margins(),tuple(map(D,('150','187.50','234.375','292.96875'))))
        self.assertEqual(p.margin_total(),D('864.84375'))
        self.assertEqual(p.cost_funding_reserve(),D('135.15625'))
        self.assertEqual(p.trigger_price('96'),D('91.20'))

    def test_fabricated_completion_and_inflated_remainder_rejected(self):
        state=FiniteAddsState()
        with self.assertRaises(ValueError):
            state.record_complete_opening_order(1,1,quantization_remainder=149,maximum_remainder=149)
        self.assertEqual(state.completed_opening_orders,0)

    def test_actual_small_filled_child_does_not_complete_margin_order(self):
        a=fresh(); s=FiniteAddsState()
        r=execute(a,q='.1',identity='SMALL_CHILD')
        self.assertEqual(r['status'],'FILLED')
        s.record_fill_receipt(a,'SMALL_CHILD',0)
        self.assertEqual(s.completed_opening_orders,0)
        self.assertEqual(s.current_order_filled_margin,D('10.008'))
        self.assertEqual(s.next_order_margin(),D('150'))

    def test_capacity_partial_accumulates_without_extra_round_or_duplicate(self):
        a=fresh(); s=FiniteAddsState(); q=order_quantity(150,'100.08')
        r=execute(a,q=q,available='.5',identity='PARTIAL')
        self.assertEqual(r['status'],'PARTIAL')
        s.record_fill_receipt(a,'PARTIAL',0)
        first=s.current_order_filled_margin
        s.record_fill_receipt(a,'PARTIAL',0)
        self.assertEqual(s.current_order_filled_margin,first)
        self.assertEqual(s.completed_opening_orders,0)
        r=execute(a,q=q-D('.5'),t=2*M+1,signal=M,identity='REST')
        self.assertEqual(r['status'],'FILLED')
        s.record_fill_receipt(a,'REST',0)
        self.assertEqual(s.completed_opening_orders,1)
        self.assertEqual(s.next_order_margin(),D('187.50'))
        with self.assertRaises(ValueError): s.record_fill_receipt(a,'PARTIAL',1)

    def test_wrong_symbol_short_and_close_receipts_cannot_advance(self):
        for symbol,side in (('ETHUSDT','BUY'),('BTCUSDT','SELL')):
            a=fresh(); s=FiniteAddsState(); execute(a,symbol,side,1,identity='WRONG')
            with self.subTest(symbol=symbol,side=side), self.assertRaises(ValueError):
                s.record_fill_receipt(a,'WRONG',0)
        a=fresh(); s=FiniteAddsState(); execute(a,q=1,identity='OPEN')
        execute(a,side='SELL',q=1,t=2*M+1,signal=M,identity='CLOSE',reduce=True)
        with self.assertRaises(ValueError): s.record_fill_receipt(a,'CLOSE',0)

    def test_receipt_overfills_fixed_order_without_advancing(self):
        a=fresh(); s=FiniteAddsState(); execute(a,q=2,identity='OVER')
        with self.assertRaises(ValueError): s.record_fill_receipt(a,'OVER',0)
        self.assertEqual(s.completed_opening_orders,0)
        self.assertEqual(s.current_order_filled_margin,0)

    def test_terminal_prevents_actual_new_receipts_advancing(self):
        a=fresh(); s=FiniteAddsState(); execute(a,q=1,identity='OPEN'); s.begin_terminal()
        with self.assertRaises(ValueError): s.record_fill_receipt(a,'OPEN',0)
        self.assertIsNone(s.next_order_margin())

    def test_fee_funding_identity_and_nonreplenishing_credit(self):
        b=ProgramBudget(); b.record_cost_event('FEE',actual_fee=1)
        b.record_cost_event('FEE',actual_fee=1)
        self.assertEqual(b.consumed_fee_funding_reserve,D('1'))
        with self.assertRaises(ValueError): b.record_cost_event('FEE',actual_fee=2)
        b.record_cost_event('CREDIT',signed_funding=1000)
        self.assertEqual(b.consumed_fee_funding_reserve,D('1'))
        b.record_cost_event('DEBIT',signed_funding=-135)
        self.assertFalse(b.allow_further_increases())
        self.assertEqual(b.consumed_fee_funding_reserve,D('136'))


class Envelope(unittest.TestCase):
    def check(self,intents,nav,actual=None,pending=None):
        return validate_intent_envelope(intents,nav,
            actual_signed_notionals=flat_actual() if actual is None else actual,
            pending_increases={} if pending is None else pending)

    def test_omitted_actual_or_pending_risk_fails_closed(self):
        with self.assertRaises((ValueError,TypeError)): validate_intent_envelope({},10000)
        with self.assertRaises((ValueError,TypeError)):
            validate_intent_envelope({},10000,actual_signed_notionals=flat_actual())

    def test_none_actual_or_pending_risk_fails_closed(self):
        for actual,pending in ((None,{}),(flat_actual(),None)):
            with self.subTest(actual=actual,pending=pending), self.assertRaises((ValueError,TypeError)):
                validate_intent_envelope({},10000,actual_signed_notionals=actual,pending_increases=pending)

    def test_actual_asset_breach_cannot_be_hidden_by_zero_intent(self):
        actual=flat_actual(); actual['BTCUSDT']=D('3100')
        r=self.check({},10000,actual)
        self.assertFalse(r['allow_increases']); self.assertIn('CONSERVATIVE_ASSET_CAP',r['reasons'])

    def test_pending_asset_breach_includes_all_owners(self):
        actual=flat_actual(); actual['BTCUSDT']=D('2500')
        r=self.check({},10000,actual,{'A':{'BTCUSDT':300},'B':{'BTCUSDT':300}})
        self.assertEqual(D(r['risk_assets_including_pending']['BTCUSDT']),D('3100'))
        self.assertFalse(r['allow_increases'])

    def test_opposing_sleeves_and_opposite_pending_do_not_net_away(self):
        r=self.check({'A':{'BTCUSDT':2000},'B':{'BTCUSDT':-2000}},10000,
                     pending={'C':{'BTCUSDT':-100}})
        self.assertEqual(D(r['net_notional']),0)
        self.assertEqual(D(r['risk_assets_including_pending']['BTCUSDT']),4100)
        self.assertFalse(r['allow_increases'])

    def test_actual_pending_gross_and_net_breaches_retained(self):
        actual=dict.fromkeys(SYMBOLS,D('1750'))
        r=self.check({},10000,actual,{'A':{'BTCUSDT':251}})
        self.assertEqual(D(r['risk_gross_including_pending']),9001)
        self.assertIn('GROSS_OR_PENDING_CAP',r['reasons']); self.assertIn('NET_CAP',r['reasons'])
        self.assertFalse(r['cap_guaranteed_after_mark'])

    def test_unknown_or_incomplete_risk_inputs_rejected(self):
        for actual,pending in (({'BTCUSDT':0},{}),(flat_actual(),{'A':{'FAKEUSDT':1}})):
            with self.subTest(actual=actual,pending=pending), self.assertRaises(ValueError):
                self.check({},10000,actual,pending)

    def test_exact_boundary_is_inclusive_but_ulp_above_not(self):
        r=self.check({'A':{'BTCUSDT':3000,'ETHUSDT':3000,'SOLUSDT':3000}},10000)
        self.assertTrue(r['allow_increases'])
        r=self.check({'A':{'BTCUSDT':D('3000.00000001'),'ETHUSDT':3000,'SOLUSDT':3000}},10000)
        self.assertFalse(r['allow_increases'])

    def test_nonpositive_equity_is_increase_block(self):
        for nav in (0,-1): self.assertFalse(self.check({},nav)['allow_increases'])


class ControllerAndStress(unittest.TestCase):
    def test_many_generated_covariance_cases_cap_all_three_dimensions(self):
        rng=np.random.default_rng(9010)
        for i in range(80):
            raw=rng.normal(0,1,5)
            returns=rng.normal(0,.04,(50,5))
            w,meta=bounded_weights(raw,returns)
            cov=np.cov(returns[-30:],rowvar=False,ddof=1)*365
            self.assertLessEqual(abs(w).sum(),.90+1e-13)
            self.assertLessEqual(abs(w).max(),.30+1e-13)
            self.assertLessEqual(float(np.sqrt(max(w@cov@w,0))),.15+1e-13)
            self.assertFalse(meta['historical_availability_certified'])

    def test_only_last_30_generated_rows_influence_result(self):
        rng=np.random.default_rng(99); returns=rng.normal(0,.02,(65,5)); raw=np.ones(5)
        first=bounded_weights(raw,returns)[0]; returns[:-30]*=10000
        np.testing.assert_array_equal(first,bounded_weights(raw,returns)[0])

    def test_zero_variance_does_not_upscale_or_bypass_gross(self):
        w,_=bounded_weights(np.full(5,.3),np.zeros((30,5)))
        self.assertLessEqual(abs(w).sum(),.90+1e-13)
        w,_=bounded_weights(np.full(5,.01),np.zeros((30,5)))
        np.testing.assert_array_equal(w,np.full(5,.01))

    def test_both_signed_and_covariance_shapes_reject_bad_inputs(self):
        for raw,r in (([1,2],np.zeros((30,5))),(np.ones(5),np.zeros((29,5))),
                      (np.ones(5),np.full((30,5),np.nan)),([np.inf]*5,np.zeros((30,5)))):
            with self.subTest(raw=raw),self.assertRaises(ValueError): bounded_weights(raw,r)

    def test_actual_mark_drift_exceeds_caps_and_blocks_adds(self):
        a=fresh()
        for s,side in zip(SYMBOLS,('BUY','BUY','BUY','SELL','SELL')):
            execute(a,s,side,16,identity='OPEN:'+s)
        marks(a,2*M,{s:70 if i<3 else 130 for i,s in enumerate(SYMBOLS)})
        self.assertGreater(a.summary()['gross_weight'],.90)
        self.assertEqual(a.status,'BOUND_BREACH_REDUCTION_REQUIRED')
        r=execute(a,q=1,t=3*M+1,signal=2*M,identity='FORBIDDEN')
        self.assertEqual(r['reason'],'BOUND_BREACH_REDUCTION_REQUIRED')

    def test_isolated_liquidation_halt_with_positive_wallet_and_nav(self):
        a=fresh(); execute(a,'BTCUSDT','SELL',10,identity='SHORT')
        marks(a,2*M,{s:'198.9' if s=='BTCUSDT' else '100' for s in SYMBOLS})
        self.assertEqual(a.status,'LIQUIDATION_REQUIRED_HALT')
        self.assertGreater(a.free_cash,1000); self.assertGreater(a.nav(),1000)
        self.assertFalse(a.contract_metadata()['native_liquidation_certified'])
        with self.assertRaises(RuntimeError):
            execute(a,q=10,t=3*M+1,signal=2*M,identity='NO_INVENTED_EXIT',reduce=True)

    def test_long_btc_gap_overshoots_20_percent_stop_without_exit(self):
        a=fresh(); plan=FiniteAddsPlan(); price=D('100.08')
        # Complete all four fixed budgets at a generated unchanged price.
        for i,margin in enumerate(plan.margins()):
            execute(a,q=order_quantity(margin,price),t=(i+1)*M+1,signal=i*M,identity='ADD:'+str(i))
        marks(a,6*M,{s:50 if s=='BTCUSDT' else 100 for s in SYMBOLS})
        pnl=a.nav()-D('10000')
        self.assertTrue(plan.loss_exit_due(pnl)); self.assertLess(pnl,D('-200'))
        before=a.positions['BTCUSDT'].quantity
        for i in range(60):
            r=execute(a,side='SELL',q=before,t=(7+i)*M+1,signal=6*M,
                      identity='NO_CAPACITY:'+str(i),mid=50,available=0,reduce=True)
            self.assertEqual(r['executed_quantity'],0)
        self.assertEqual(a.positions['BTCUSDT'].quantity,before)
        self.assertLess(a.nav()-D('10000'),D('-200'))

    def test_paid_close_preserves_costs_and_exact_accounting_bridge(self):
        a=fresh(); execute(a,q=10,identity='OPEN')
        r=execute(a,side='SELL',q=10,t=2*M+1,signal=M,identity='CLOSE',reduce=True)
        self.assertEqual(r['status'],'FILLED'); self.assertEqual(a.positions['BTCUSDT'].quantity,0)
        summary=a.summary(); self.assertGreater(summary['fees_USDT'],0)
        self.assertGreater(summary['execution_cost_USDT'],0)
        self.assertLess(summary['NAV'],10000); self.assertEqual(summary['accounting_bridge_error_USDT'],0)


if __name__=='__main__': unittest.main(verbosity=2)
