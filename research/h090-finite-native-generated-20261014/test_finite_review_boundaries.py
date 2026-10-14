"""Atomic precommit regressions for the independent review's two findings."""
from copy import deepcopy
from decimal import Decimal as D
import unittest
from generated_fixtures import START,DAY,MINUTE,S
from owner_ledger import BASE,FINITE,BTC
from test_finite_candidate import prepared_two_owner,row


def signaled_add():
    sim=prepared_two_owner();stamp=START+2*MINUTE
    sim.account.update_marks(stamp,{s:dict(price=D('94') if s==BTC else D('100'),close_us=stamp,available_us=stamp) for s in S})
    sim._evaluate_program(stamp)
    order=sim.program_pending
    order['target']=sim.owners.quantity[FINITE][BTC]+sim._finite_quantity(order,94.)
    fill_id=f'{order["order_id"]}:0:INCREASE'
    sim._fill_owner[fill_id]=(FINITE,1)
    request=dict(symbol=BTC,side='BUY',quantity=D('.1'),event_us=START+3*MINUTE+1,
        signal_us=stamp,fill_id=fill_id,execution_mid_price=D('94'),quote_available_us=START+3*MINUTE,reduce_only=False)
    return sim,order,request


def owner_state(sim):
    return {'ledger':sim.owners.snapshot(),'program':deepcopy(vars(sim.program)),
        'program_budget':deepcopy(vars(sim.program_budget)),'pending':deepcopy(sim.program_pending),
        'reservations':deepcopy(vars(sim.reservations)),'events':deepcopy(sim.owner_events),
        'authorizations':deepcopy(sim._program_order_authorizations),
        'signal_marks':deepcopy(sim._program_signal_mark_evidence),
        'bindings':deepcopy(sim._fill_owner),'trade_cursor':sim._trade_cursor,'funding_cursor':sim._funding_cursor,
        'processed_receipts':deepcopy(sim.processed_native_receipts)}


class IndependentBoundaryRegressions(unittest.TestCase):
    def assert_atomic_rejected(self,sim,request,reason):
        account=sim.account.snapshot();owners=owner_state(sim)
        receipt=sim.account.execute_fill(**request)
        self.assertEqual(receipt,{'status':'POLICY_REJECTED','reason':reason})
        self.assertEqual(sim.account.snapshot(),account)
        self.assertEqual(owner_state(sim),owners)
        return receipt

    def test_every_corrupt_stored_causal_field_rejects_before_any_state_change(self):
        changes={'source_decision_us':START+10*DAY,'authorization':'INVALID',
            'mark_available_us':START+10*DAY,'mark_close_us':START+10*DAY,
            'mark_price':'101','trigger_price':'1','actual_filled_basis':'1',
            'original_BTC_weight':-.05,'unexpected_field':True}
        for key,value in changes.items():
            with self.subTest(field=key):
                sim,order,request=signaled_add()
                sim._program_order_authorizations[order['order_id']][key]=value
                self.assert_atomic_rejected(sim,request,'FINITE_CAUSAL_SOURCE_BASIS_MARK_WITNESS_MISMATCH')

    def test_causal_field_deletion_and_equal_value_wrong_type_are_rejected(self):
        for transform in ('delete','float','joint_fabrication'):
            with self.subTest(transform=transform):
                sim,order,request=signaled_add();w=sim._program_order_authorizations[order['order_id']]
                if transform=='delete':del w['mark_price']
                elif transform=='float':w['source_decision_us']=float(w['source_decision_us'])
                else:w.update(actual_filled_basis='200',trigger_price='190',mark_price='180')
                self.assert_atomic_rejected(sim,request,'FINITE_CAUSAL_SOURCE_BASIS_MARK_WITNESS_MISMATCH')

    def test_current_owned_basis_must_match_actual_receipts_before_finance(self):
        sim,order,request=signaled_add()
        sim.owners.basis[FINITE][BTC]+=D('1')
        self.assert_atomic_rejected(sim,request,'OWNER_QUANTITY_BASIS_ACTUAL_RECEIPT_MISMATCH')

    def test_reduce_only_cannot_consume_another_owners_actual_quantity(self):
        for owner in (FINITE,BASE):
            for excess in (D('1'),D('.00000001')):
                with self.subTest(owner=owner,excess=str(excess)):
                    sim=prepared_two_owner();fill_id='OWNER-OVERCLOSE-REVIEW'
                    sim._fill_owner[fill_id]=(owner,None)
                    request=dict(symbol=BTC,side='SELL',quantity=sim.owners.quantity[owner][BTC]+excess,
                        event_us=START+2*MINUTE+1,signal_us=START,fill_id=fill_id,
                        execution_mid_price=D('100'),quote_available_us=START+2*MINUTE,reduce_only=True)
                    self.assert_atomic_rejected(sim,request,'OWNER_REDUCTION_EXCEEDS_OR_OPPOSES_ACTUAL_INVENTORY')

    def test_reduce_only_wrong_direction_and_unbound_owner_reject_atomically(self):
        for failure in ('direction','unbound'):
            with self.subTest(failure=failure):
                sim=prepared_two_owner();fill_id='OWNER-REDUCTION-GUARD'
                if failure=='direction':sim._fill_owner[fill_id]=(FINITE,None)
                request=dict(symbol=BTC,side='BUY' if failure=='direction' else 'SELL',quantity=D('.1'),
                    event_us=START+2*MINUTE+1,signal_us=START,fill_id=fill_id,
                    execution_mid_price=D('100'),quote_available_us=START+2*MINUTE,reduce_only=True)
                self.assert_atomic_rejected(sim,request,'OWNER_REDUCTION_EXCEEDS_OR_OPPOSES_ACTUAL_INVENTORY' if failure=='direction' else 'EXPLICIT_OWNER_ORDER_BINDING_REQUIRED')

    def test_exact_owner_reduction_and_duplicate_replay_precede_current_gates(self):
        sim=prepared_two_owner();fill_id='EXACT-OWNER-CLOSE'
        sim._fill_owner[fill_id]=(FINITE,None);base_before=sim.owners.quantity[BASE][BTC]
        request=dict(symbol=BTC,side='SELL',quantity=sim.owners.quantity[FINITE][BTC],
            event_us=START+2*MINUTE+1,signal_us=START,fill_id=fill_id,
            execution_mid_price=D('100'),quote_available_us=START+2*MINUTE,reduce_only=True)
        sim.risk_contexts[sim.cursor]['ready']=False
        receipt=sim.account.execute_fill(**request);self.assertEqual(receipt['status'],'FILLED');sim._flush_account()
        self.assertEqual(sim.owners.quantity[FINITE][BTC],0);self.assertEqual(sim.owners.quantity[BASE][BTC],base_before)
        account=sim.account.snapshot();owners=owner_state(sim)
        self.assertEqual(sim.account.execute_fill(**request),receipt)
        self.assertEqual(sim.account.snapshot(),account);self.assertEqual(owner_state(sim),owners)

    def test_partial_add_keeps_original_signal_basis_after_mark_history_rolls(self):
        sim=prepared_two_owner();stamp=START+2*MINUTE
        sim.account.update_marks(stamp,{s:dict(price=D('90') if s==BTC else D('100'),close_us=stamp,available_us=stamp) for s in S})
        sim._evaluate_program(stamp);order_id=sim.program_pending['order_id']
        original=deepcopy(sim._program_order_authorizations[order_id])
        sim.previous_quote=dict.fromkeys(S,40500.) # .45 BTC leaves a final fill above native 10-USDT minimum
        for n in range(3,8):
            stamp=START+n*MINUTE
            sim.account.update_marks(stamp,{s:dict(price=D('90') if s==BTC else D('100'),close_us=stamp,available_us=stamp) for s in S})
            sim.attempt(stamp,row(90.))
        self.assertEqual(sim.program.completed_opening_orders,2)
        self.assertNotEqual(sim.owners.basis[FINITE][BTC],D(original['actual_filled_basis']))
        self.assertNotIn(original['mark_close_us'],[m['close_us'] for m in sim.account.marks[BTC]])
        self.assertEqual(sim._program_order_authorizations[order_id],original)
        fills=[r for r in sim.account.trades if r['fill_id'].startswith(order_id+':')]
        self.assertEqual(len(fills),5)
        self.assertTrue(all(r['signal_us']==original['signal_us'] for r in fills))


if __name__=='__main__':unittest.main(verbosity=2)
