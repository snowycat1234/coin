"""Generated-only semantic parity and explicit unsupported-mutation tests."""
from copy import deepcopy
from decimal import Decimal as D
import json
import unittest
import numpy as np
from candidate import S, select_partial
from causal_adapter import _clone, FreshExecutionPreview
from fine_account import FineGridAccount
from native_preview import ChargedPreview
from shared_journal_preview import (clone_preview_account, SharedChargedPreview,
    SharedFreshExecutionPreview, JournalList, JournalMap, UnsupportedJournalMutation)
from test_causal_integration import Tests as CausalFixtures, SIGNAL, MINUTE


def account():
    result = FineGridAccount()
    result.update_marks(0, {s: {'price': D(100), 'close_us': 0, 'available_us': 0} for s in S})
    return result


def fill(a, side, quantity, event, identity, symbol=S[0], **kwargs):
    return a.execute_fill(symbol, side, D(quantity), event, 0, identity,
        execution_mid_price=D(100), quote_available_us=0, **kwargs)


def generated(rounds):
    result = account()
    for i in range(rounds):
        event = 60_000_001+i*3; symbol = S[i%5]
        fill(result, 'BUY', '.10000000', event, f'GENERATED:{i}:OPEN', symbol)
        result.apply_funding(symbol, f'GENERATED:{i}:FUND', event+1, D(0), 0)
        fill(result, 'SELL', '.10000000', event+2, f'GENERATED:{i}:CLOSE', symbol, reduce_only=True)
    return result


def oracle(account, cls, pending=None, covariance=.04, quote=100_000_000):
    return cls(account, prices=dict.fromkeys(S,D(100)), covariance=np.eye(5)*covariance,
        pending=pending or dict.fromkeys(S,D(0)), previous_quote=dict.fromkeys(S,D(quote)),
        event_us=180_000_001, signal_us=120_000_000, covariance_available_us=0,
        quote_available_us=0, price_available_us=dict.fromkeys(S,0))


class JournalTests(unittest.TestCase):
    def test_snapshot_json_restore_rollback_and_mutable_export(self):
        native=generated(12); before=native.snapshot(); preview=clone_preview_account(native,generated_only=True)
        self.assertEqual(preview.snapshot(), before)
        self.assertEqual(json.dumps(preview.snapshot(),sort_keys=True),json.dumps(before,sort_keys=True))
        restored=FineGridAccount.from_snapshot(preview.snapshot())
        self.assertEqual(restored.snapshot(),before)
        fill(preview,'BUY','3',180_000_001,'BRANCH')
        recovered=FineGridAccount.from_snapshot(before)
        self.assertEqual(recovered.snapshot(),native.snapshot())
        exported=preview.snapshot(); exported['trades'][0]['decimal_strings']['quantity']='CHANGED'
        self.assertNotEqual(preview.snapshot(),exported)
        self.assertEqual(native.snapshot(),before)

    def test_clone_and_fork_independence_and_callbacks(self):
        native=generated(4); before=native.snapshot()
        preview=clone_preview_account(native,generated_only=True)
        first=_clone(preview); second=deepcopy(preview,{id(preview.instrument_profiles):preview.instrument_profiles})
        self.assertIs(first.trades._chunks,preview.trades._chunks)
        self.assertIs(first.fill_requests._layers,preview.fill_requests._layers)
        for probe in (first,second): self.assertEqual(probe.snapshot(),before)
        fill(first,'BUY','2',180_000_001,'FIRST')
        self.assertEqual(second.snapshot(),before); self.assertEqual(preview.snapshot(),before)
        native.trades[0]['decimal_strings']['quantity']='LIVE_MUTATION'
        self.assertEqual(preview.snapshot(),before)
        preview.execute_fill=lambda *a,**k: (_ for _ in ()).throw(AssertionError())
        preview.liquidation_callback=lambda *a: None
        fresh=clone_preview_account(preview,generated_only=True)
        self.assertNotIn('execute_fill',vars(fresh)); self.assertIsNone(fresh.liquidation_callback)

    def test_list_read_slice_concatenate_reverse_and_append(self):
        values=[{'k':[1,2]},{'k':[3]}]; journal=JournalList(values)
        self.assertEqual(len(journal),2);self.assertEqual(journal[-1],values[-1])
        self.assertEqual(journal[:],values);self.assertEqual(journal[::-1],values[::-1])
        self.assertEqual(list(reversed(journal)),values[::-1]);self.assertEqual(journal+[],values)
        self.assertEqual([]+journal,values);self.assertEqual(journal.index({'k':[3]}),1)
        fork=journal.fork(); journal.append({'k':[4]}); fork.extend([{'k':[5]}])
        self.assertEqual(journal[:],values+[{'k':[4]}]);self.assertEqual(fork[:],values+[{'k':[5]}])
        exported=journal[:];exported[0]['k'].append(99);self.assertEqual(journal[0],values[0])
        values[0]['k'].append(7);self.assertEqual(journal[0],{'k':[1,2]})
        with self.assertRaises(IndexError): _=journal[99]

    def test_unsupported_mutation_rejected(self):
        preview=clone_preview_account(generated(2),generated_only=True)
        operations=[lambda:preview.trades.__setitem__(0,{}),lambda:preview.trades.pop(),
            lambda:preview.trades.clear(),lambda:preview.trades.reverse(),lambda:preview.trades.insert(0,{}),
            lambda:preview.trades[0].__setitem__('quantity',100),
            lambda:preview.trades[0]['decimal_strings'].__setitem__('quantity','100'),
            lambda:preview.fill_requests.__setitem__('GENERATED:0:OPEN',{}),
            lambda:preview.fill_requests.pop('GENERATED:0:OPEN'),
            lambda:preview.fill_requests['GENERATED:0:OPEN']['receipt']['fills'].append({})]
        before=preview.snapshot()
        for operation in operations:
            with self.assertRaises(UnsupportedJournalMutation):operation()
            self.assertEqual(preview.snapshot(),before)
        bad=[];bad.append(bad)
        with self.assertRaisesRegex(TypeError,'CYCLIC'):JournalList(bad)
        with self.assertRaisesRegex(TypeError,'UNSUPPORTED'):JournalList([object()])
        native=account();native.unreviewed_field={}
        with self.assertRaisesRegex(TypeError,'UNREVIEWED'):clone_preview_account(native,generated_only=True)
        with self.assertRaisesRegex(ValueError,'GENERATED_ONLY'):clone_preview_account(account(),generated_only=False)

    def test_duplicate_identity_receipts_and_conflicts(self):
        native=generated(3);preview=clone_preview_account(native,generated_only=True)
        for probe in (native,preview):
            receipt=fill(probe,'BUY','.10000000',60_000_001,'GENERATED:0:OPEN')
            receipt['fills'][0]['decimal_strings']['quantity']='DETACHED'
            self.assertNotEqual(probe.fill_requests['GENERATED:0:OPEN']['receipt'],receipt)
            self.assertEqual(probe.apply_funding(S[0],'GENERATED:0:FUND',60_000_002,D(0),0),native.funding[0])
            with self.assertRaisesRegex(ValueError,'conflicting fill'):fill(probe,'BUY','.2',60_000_001,'GENERATED:0:OPEN')
            with self.assertRaisesRegex(ValueError,'conflicting duplicate'):probe.apply_funding(S[0],'GENERATED:0:FUND',60_000_002,D('.1'),0)
            with self.assertRaisesRegex(ValueError,'reused'):probe.apply_funding(S[1],'GENERATED:0:FUND',180_000_002,D(0),0)
        self.assertEqual(native.snapshot(),preview.snapshot())

    def test_native_cash_margin_funding_and_every_fill_path(self):
        native=generated(7);preview=clone_preview_account(native,generated_only=True)
        cases=[('BUY','5',False,None),('SELL','7.123456789',False,None),
            ('BUY','2.12345678',True,None),('BUY','.000000001',False,None),
            ('BUY','4',False,'.1'),('BUY','1000',False,None),('SELL','8',True,None)]
        for i,(side,q,reduce,capacity) in enumerate(cases):
            kwargs={'reduce_only':reduce}
            if capacity is not None:kwargs['available_quantity']=D(capacity)
            self.assertEqual(fill(native,side,q,180_000_001+i*2,f'CASE:{i}',**kwargs),
                             fill(preview,side,q,180_000_001+i*2,f'CASE:{i}',**kwargs))
            self.assertEqual(native.snapshot(),preview.snapshot());self.assertEqual(native.summary(),preview.summary())
        for i,rate in enumerate(('.0001','-.0002','8')):
            event=180_000_030+i*2
            self.assertEqual(native.apply_funding(S[0],f'FUND:{i}',event,D(rate),0),
                             preview.apply_funding(S[0],f'FUND:{i}',event,D(rate),0))
            self.assertEqual(native.snapshot(),preview.snapshot())

    def test_charged_full_corners_pending_refusal_dust_and_live_guard(self):
        native=generated(8);before=native.snapshot()
        cases=[(dict.fromkeys(S,D('.1')),None,.04,100_000_000),
            (dict.fromkeys(S,D('20')),dict.fromkeys(S,D('25')),0,100_000_000),
            ({s:D('4.000000005') if s==S[0] else D(0) for s in S},None,0,100_000),
            ({s:D('1.000000005') if s==S[0] else D(0) for s in S},None,0,100_000_000)]
        for target,pending,cov,quote in cases:
            a=oracle(native,ChargedPreview,pending,cov,quote);b=oracle(native,SharedChargedPreview,pending,cov,quote)
            self.assertEqual(a.evaluate(target,D(1)),b.evaluate(target,D(1)))
            self.assertIs(b.account,native);self.assertEqual(native.snapshot(),before)
        a=oracle(native,SharedChargedPreview);native.free_cash-=D(1)
        with self.assertRaises(AssertionError):a.evaluate(dict.fromkeys(S,D('.1')),D(1))
        self.assertFalse(hasattr(a,'_sealed_corner_account'));self.assertIs(a.account,native)

    def test_fresh_gap_funding_pending_and_dust_parity(self):
        fixtures=CausalFixtures();sim=fixtures.sim();fixtures.seed(sim)
        sim.account.apply_funding(S[0],'FUND',SIGNAL+MINUTE,D('.001'),SIGNAL)
        binding=fixtures.source().bind(SIGNAL)
        for price,pending in ((100,'6.000000005'),(200,'15'),(100,'5.000000005')):
            kwargs=dict(binding=binding,prices=fixtures.vec(price,100,100,100,100),
                price_available_us=dict.fromkeys(S,SIGNAL+MINUTE),pending=fixtures.vec(pending,2,0,0,0),
                capacity=fixtures.vec(100,100,100,100,100),event_us=SIGNAL+MINUTE+1,
                signal_us=SIGNAL,quote_available_us=SIGNAL+MINUTE)
            before=sim.account.snapshot();a=FreshExecutionPreview(sim.account,**kwargs);b=SharedFreshExecutionPreview(sim.account,**kwargs)
            self.assertEqual(a.account.snapshot(),b.account.snapshot())
            self.assertEqual(a.evaluate(kwargs['pending'],D(1)),b.evaluate(kwargs['pending'],D(1)))
            self.assertEqual(sim.account.snapshot(),before)

    def test_native_simulator_execute_fork_and_snapshot_recovery(self):
        fixtures=CausalFixtures();native=fixtures.sim();preview=fixtures.sim()
        for sim in (native,preview):fixtures.seed(sim)
        # This test exercises native simulator methods on an isolated branch,
        # never changes the production account factory or an admission boundary.
        preview.account=clone_preview_account(preview.account,generated_only=True)
        target=fixtures.vec('-3.123456789',4,0,0,0)
        for sim in (native,preview):
            sim.schedule(target,SIGNAL,'DAILY_TARGET');sim.attempt(SIGNAL+MINUTE,fixtures.market())
        self.assertEqual(native.snapshot(),preview.snapshot());self.assertEqual(native.pending,preview.pending)
        fork=preview.fork();self.assertEqual(fork.snapshot(),preview.snapshot())
        saved=preview.snapshot();recovered=type(preview).from_snapshot(saved,preview.window,account_class=FineGridAccount)
        self.assertEqual(recovered.snapshot(),saved)
        for sim in (native,preview):
            signal=sim.terminal_signal_us;sim.schedule(fixtures.vec(),signal,'TERMINAL');sim.attempt(signal+MINUTE,fixtures.market())
        self.assertEqual(native.snapshot(),preview.snapshot())
        self.assertTrue(all(p.quantity==0 for p in preview.account.positions.values()))

    def test_direct_charged_seal_failure_restores_original(self):
        native=generated(2);before=native.snapshot();preview=oracle(native,SharedChargedPreview)
        native.unreviewed_field={}
        with self.assertRaisesRegex(TypeError,'UNREVIEWED'):
            preview._charged(dict.fromkeys(S,D('.1')),'UNSUPPORTED')
        self.assertIs(preview.account,native);self.assertFalse(hasattr(preview,'_sealed_corner_account'))
        del native.unreviewed_field
        self.assertEqual(native.snapshot(),before)
        # Verify a successful retry after the unsupported extension is removed.
        probe,witness=preview._charged(dict.fromkeys(S,D('.1')),'SUPPORTED')
        self.assertIsNotNone(probe);self.assertIs(preview.account,native)
        self.assertEqual(native.snapshot(),before)

    def test_owned_funding_debit_margin_and_bankruptcy_parity(self):
        native=account();fill(native,'BUY','5',60_000_001,'OWNED')
        preview=clone_preview_account(native,generated_only=True)
        for index,rate in enumerate(('-0.001','0.001','19','2')):
            event=60_000_002+index
            left=native.apply_funding(S[0],f'OWNED_FUND:{index}',event,D(rate),0)
            right=preview.apply_funding(S[0],f'OWNED_FUND:{index}',event,D(rate),0)
            self.assertEqual(left,right);self.assertTrue(left['owned'])
            self.assertNotEqual(D(left['decimal_strings']['signed_funding_USDT']),D(0))
            self.assertEqual(native.snapshot(),preview.snapshot())
            self.assertEqual(native.summary(),preview.summary())
            if native.status in ('BANKRUPT_HALT','LIQUIDATION_REQUIRED_HALT'):break
        self.assertEqual(native.apply_funding(S[0],f'OWNED_FUND:{index}',event,D(rate),0),right)
        self.assertEqual(preview.apply_funding(S[0],f'OWNED_FUND:{index}',event,D(rate),0),right)
        self.assertEqual(native.snapshot(),preview.snapshot())
        self.assertEqual(native.status,'BANKRUPT_HALT')
        self.assertGreater(native.unpaid_liability,D(0))
        self.assertEqual(native.free_cash,D(0));self.assertEqual(native.positions[S[0]].isolated_balance,D(0))
        for probe in (native,preview):
            with self.assertRaisesRegex(RuntimeError,'BANKRUPT_HALT'):
                fill(probe,'SELL','5',180_000_001,'HALTED',reduce_only=True)
        self.assertEqual(native.snapshot(),preview.snapshot())
