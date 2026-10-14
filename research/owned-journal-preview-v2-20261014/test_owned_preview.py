"""Generated-only permanent ownership and exact native economic parity tests."""
import ast
from copy import deepcopy
from decimal import Decimal as D
import json
from pathlib import Path
import random
import unittest
import numpy as np
from candidate import S
from fine_account import FineGridAccount
from causal_adapter import CausalPartialAdapter,FreshExecutionPreview
from native_preview import ChargedPreview
from native_control import NATIVE
import test_synthetic,test_causal_integration
from test_shared_journal import generated,fill,account,oracle
from shared_journal_preview import UnsupportedJournalMutation
from owned_journals import (PersistentList,PersistentMap,OwnedFineGridAccount,admit_owned_account,
    fork_owned_account,export_tree,JOURNALS,_height)
from owned_preview import BoundedChargedPreview,BoundedFreshExecutionPreview
from owned_adapter import OwnedCausalPartialAdapter
from owned_simulator import OwnedNativeSimulator


def owned_sim(native):
    result=object.__new__(OwnedNativeSimulator);vars(result).update(vars(native))
    result.account=admit_owned_account(native.account,generated_only=True);return result


class OwnedV3Tests(test_synthetic.Tests):
    def account(self):return admit_owned_account(super().account(),generated_only=True)
    def simulator(self):return owned_sim(super().simulator())
    def oracle(self,a,cov=.04,pending=None,quote=100000000):
        return BoundedChargedPreview(a,prices=self.vec(100,100,100,100,100),
            covariance=np.eye(5)*cov,pending=pending or {s:a.positions[s].quantity for s in S},
            previous_quote=self.vec(quote,quote,quote,quote,quote),event_us=180000001,signal_us=120000000,
            covariance_available_us=0,quote_available_us=60000000,price_available_us=dict.fromkeys(S,0))


class OwnedV4Tests(test_causal_integration.Tests):
    def sim(self,**kwargs):return owned_sim(super().sim(**kwargs))
    def adapter(self,sim,source=None):return OwnedCausalPartialAdapter(sim,source or self.source())


class OwnershipTests(unittest.TestCase):
    def test_persistent_avl_order_balance_and_forks(self):
        values=list(range(2000));random.Random(17).shuffle(values)
        mapping=PersistentMap();sequence=PersistentList();expected={}
        for n in values:
            mapping[str(n)]={'n':n};sequence.append({'n':n});expected[str(n)]={'n':n}
        self.assertEqual(list(mapping),list(expected));self.assertEqual(export_tree(mapping),expected)
        self.assertEqual(sequence[:],[{'n':n} for n in values]);self.assertEqual(sequence[-12:],[{'n':n} for n in values[-12:]])
        self.assertLess(_height(mapping._root),20);self.assertLess(_height(mapping._order),20);self.assertLess(_height(sequence._root),20)
        branch=mapping.fork();old=mapping.token();branch['branch']={'n':-1}
        self.assertEqual(mapping.token(),old);self.assertNotIn('branch',mapping)
        for n in values:self.assertEqual(mapping[str(n)],{'n':n})
        with self.assertRaises(UnsupportedJournalMutation):mapping[str(values[0])]={'n':0}
        with self.assertRaises(UnsupportedJournalMutation):sequence[0]['n']=0
        with self.assertRaises(UnsupportedJournalMutation):sequence.pop()

    def test_exact_snapshot_token_and_atomic_history_isolation(self):
        native=generated(15);owned=admit_owned_account(native,generated_only=True)
        before=native.snapshot();self.assertEqual(owned.snapshot(),before)
        token=owned.preview_state_token();fork=fork_owned_account(owned)
        self.assertEqual(token,fork.preview_state_token());self.assertEqual(fork.snapshot(),before)
        self.assertIs(owned.trades._root,fork.trades._root)
        fill(fork,'BUY','2',180_000_001,'FORK');self.assertNotEqual(fork.preview_state_token(),token)
        self.assertEqual(owned.preview_state_token(),token)
        native.trades[0]['decimal_strings']['quantity']='MUTATED_ORIGINAL'
        self.assertEqual(owned.snapshot(),before)
        with self.assertRaises(UnsupportedJournalMutation):owned.trades=[]
        owned.free_cash=D(str(owned.free_cash)+'0')
        self.assertNotEqual(owned.preview_state_token(),token)  # exact Decimal string, not numeric-only equality

    def test_fullsnapshot_recovery_json_and_receipt_alias(self):
        native=account();owned=admit_owned_account(native,generated_only=True)
        left=fill(native,'BUY','5',60_000_001,'OPEN');right=fill(owned,'BUY','5',60_000_001,'OPEN')
        self.assertEqual(left,right);self.assertEqual(native.snapshot(),owned.snapshot())
        right['decimal_strings']['executed_quantity']='UNTRUSTED_MUTATION'
        right['fills'][0]['decimal_strings']['quantity']='UNTRUSTED_MUTATION'
        self.assertEqual(native.snapshot(),owned.snapshot())
        snap=owned.snapshot();self.assertEqual(json.dumps(snap),json.dumps(native.snapshot()))
        restored=OwnedFineGridAccount.from_snapshot(snap);self.assertEqual(restored.snapshot(),snap)
        restored.preview_state_token()
        raw=FineGridAccount.from_snapshot(snap);self.assertEqual(raw.snapshot(),snap)
        snap['trades'][0]['decimal_strings']['quantity']='DETACHED_EXPORT'
        self.assertNotEqual(owned.snapshot(),snap)

    def test_owned_nonzero_funding_halt_and_duplicate_parity(self):
        native=account();fill(native,'BUY','5',60_000_001,'SEED')
        owned=admit_owned_account(native,generated_only=True)
        for i,rate in enumerate(('-0.001','0.001','19','2')):
            event=60_000_002+i
            left=native.apply_funding(S[0],f'F:{i}',event,D(rate),0)
            right=owned.apply_funding(S[0],f'F:{i}',event,D(rate),0)
            self.assertEqual(left,right);self.assertEqual(native.snapshot(),owned.snapshot())
            self.assertEqual(owned.apply_funding(S[0],f'F:{i}',event,D(rate),0),right)
            if native.status=='BANKRUPT_HALT':break
        self.assertEqual(owned.status,'BANKRUPT_HALT');self.assertGreater(owned.unpaid_liability,0)
        for probe in (native,owned):
            with self.assertRaises(RuntimeError):fill(probe,'SELL','5',180_000_001,'HALTED',reduce_only=True)
        self.assertEqual(native.snapshot(),owned.snapshot())

    def test_32_corners_pending_all_fractions_and_stale_live_token(self):
        native=generated(10);owned=admit_owned_account(native,generated_only=True);target=dict.fromkeys(S,D('.1'))
        self.assertEqual(oracle(native,ChargedPreview).evaluate(target,D(1)),oracle(owned,BoundedChargedPreview).evaluate(target,D(1)))
        first=oracle(owned,BoundedChargedPreview);fill(owned,'BUY','.1',120_000_001,'NEW_EVENT')
        with self.assertRaises(AssertionError):first.evaluate(target,D(1))
        for q,cap in (('4.000000005',100000),('30',100000000),('0.000000001',100000000)):
            target={s:D(q) if s==S[0] else D(0) for s in S}
            pending={s:D(25) if s==S[1] else D(0) for s in S}
            baseline=FineGridAccount.from_snapshot(owned.snapshot())
            self.assertEqual(oracle(baseline,ChargedPreview,pending,0,cap).evaluate(target,D(1)),
                             oracle(owned,BoundedChargedPreview,pending,0,cap).evaluate(target,D(1)))

    def test_native_adapter_attempt_snapshot_statehash_fork_restore(self):
        fixture=test_causal_integration.Tests();native=fixture.sim();owned=owned_sim(fixture.sim())
        original=CausalPartialAdapter(native,fixture.source());candidate=OwnedCausalPartialAdapter(owned,fixture.source())
        targets=(fixture.vec(5,5,0,0,0),fixture.vec('-3.123456789',2,0,0,0))
        for i,target in enumerate(targets):
            signal=test_causal_integration.SIGNAL
            for adapter in (original,candidate):adapter.schedule(target,signal,'DAILY_TARGET')
            for adapter in (original,candidate):adapter.attempt(signal+(i+1)*test_causal_integration.MINUTE,fixture.market())
            self.assertEqual(native.snapshot(),owned.snapshot());self.assertEqual(native.state_hash(),owned.state_hash())
            self.assertEqual(original.receipts,candidate.receipts);self.assertEqual(original.execution_receipts,candidate.execution_receipts)
        branch=owned.fork();self.assertEqual(branch.snapshot(),owned.snapshot());self.assertEqual(branch.state_hash(),owned.state_hash())
        saved=owned.snapshot();restored=OwnedNativeSimulator.from_snapshot(saved,owned.window,generated_only=True)
        self.assertEqual(restored.snapshot(),saved);self.assertEqual(restored.state_hash(),owned.state_hash())
        for sim in (native,owned):
            signal=sim.terminal_signal_us;sim.schedule(fixture.vec(),signal,'TERMINAL');sim.attempt(signal+test_causal_integration.MINUTE,fixture.market())
        self.assertEqual(native.snapshot(),owned.snapshot());self.assertEqual(native.state_hash(),owned.state_hash())
        # Exercise the explicit new factory admission as well as test fixtures.
        constructed=OwnedNativeSimulator(native.window,native.mode,native.cost,native.unit,generated_only=True)
        self.assertIs(type(constructed.account),OwnedFineGridAccount)
        with self.assertRaisesRegex(ValueError,'GENERATED_ONLY'):OwnedNativeSimulator(native.window,native.mode,native.cost,native.unit)

    def test_source_delta_is_only_preview_names_and_exact_state_tokens(self):
        root=Path(__file__).resolve().parent.parent
        source=ast.parse((root/'original-csh-causal-execution-v4-20261014/causal_adapter.py').read_text())
        new=ast.parse((Path(__file__).resolve().parent/'owned_adapter.py').read_text())
        old_class=next(n for n in source.body if isinstance(n,ast.ClassDef) and n.name=='CausalPartialAdapter')
        new_class=next(n for n in new.body if isinstance(n,ast.ClassDef) and n.name=='OwnedCausalPartialAdapter')
        class AllowedDelta(ast.NodeTransformer):
            def visit_Name(self,node):
                if node.id=='ChargedPreview':node.id='BoundedChargedPreview'
                elif node.id=='FreshExecutionPreview':node.id='BoundedFreshExecutionPreview'
                return node
            def visit_Call(self,node):
                node=self.generic_visit(node)
                if isinstance(node.func,ast.Attribute) and isinstance(node.func.value,ast.Name) and node.func.value.id=='account' and node.func.attr=='snapshot':node.func.attr='preview_state_token'
                return node
        for name in ('_signal_preview','attempt'):
            old=next(n for n in old_class.body if isinstance(n,ast.FunctionDef) and n.name==name)
            actual=next(n for n in new_class.body if isinstance(n,ast.FunctionDef) and n.name==name)
            self.assertEqual(ast.dump(AllowedDelta().visit(old)),ast.dump(actual))

    def test_journal_delete_and_forged_wrapper_alias_are_blocked(self):
        from shared_journal_preview import _FrozenMap,_FrozenList
        native=generated(3);owned=admit_owned_account(native,generated_only=True)
        before=owned.snapshot();token=owned.preview_state_token()
        for name in JOURNALS:
            with self.assertRaises(UnsupportedJournalMutation):delattr(owned,name)
            self.assertEqual(owned.preview_state_token(),token)
            with self.assertRaises(UnsupportedJournalMutation):setattr(owned,name,[])
        backing={'deep':[{'v':1}]};forged=_FrozenMap(backing)
        sequence=PersistentList();sequence.append(forged)
        mapping=PersistentMap();mapping['id']=forged
        backing['deep'][0]['v']=99;backing['new']=0
        self.assertEqual(sequence[0],{'deep':[{'v':1}]})
        self.assertEqual(mapping['id'],{'deep':[{'v':1}]})
        list_backing=[{'v':2}];sequence.append(_FrozenList(list_backing))
        list_backing[0]['v']=100
        self.assertEqual(sequence[1],[{'v':2}])
        cycle={};cycle['cycle']=_FrozenMap(cycle)
        with self.assertRaisesRegex(TypeError,'CYCLIC'):sequence.append(cycle)
        self.assertEqual(owned.snapshot(),before)

    def test_installed_adapter_checkpoint_lifecycle_is_fail_closed(self):
        fixture=test_causal_integration.Tests();sim=owned_sim(fixture.sim())
        adapter=OwnedCausalPartialAdapter(sim,fixture.source()).install()
        before=sim.account.snapshot()
        # Portable native account/scheduler export remains ordinary data. It
        # deliberately does not claim to serialize live causal adapter bindings.
        json.dumps(sim.snapshot())
        with self.assertRaisesRegex(RuntimeError,'UNINSTALL_ADAPTER'):sim.fork()
        with self.assertRaisesRegex(RuntimeError,'UNINSTALL_ADAPTER'):sim.state_hash()
        self.assertEqual(sim.account.snapshot(),before)
        adapter.uninstall()
        # Native adapter.uninstall restores bound methods as instance attributes,
        # so callers must explicitly release those native aliases for bare-state
        # serialization; no installed binding is silently captured.
        del sim.schedule;del sim.attempt
        self.assertEqual(sim.fork().snapshot(),sim.snapshot());sim.state_hash()
