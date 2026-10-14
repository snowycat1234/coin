"""Generated exact owner-budget and causal-order witnesses; no market arrays."""
from copy import deepcopy
from decimal import Decimal as D,localcontext
import unittest
from generated_fixtures import *
from finite_fixtures import make_candidate,demo_bundle
from owner_ledger import BASE,FINITE,BTC,Z,exact
from test_finite_candidate import prime,row,prepared_two_owner

CASH_TICK=D('.00000001')


def base_request(sim,symbol,side,quantity,fill_id,event,**changes):
    request=dict(symbol=symbol,side=side,quantity=D(quantity),event_us=event,
        signal_us=START,fill_id=fill_id,execution_mid_price=D('100'),
        quote_available_us=event-1,reduce_only=False)
    request.update(changes)
    # These isolate the owner admission boundary using actual charged fills.
    # Scheduled causal finite orders have separate end-to-end tests below.
    sim._fill_owner[fill_id]=(BASE,None)
    return request


def commit_base(sim,request):
    receipt=sim.account.execute_fill(**request)
    if receipt['status']!='FILLED':raise AssertionError(receipt)
    sim._flush_account()
    return receipt


def csh_boundary(cost=BASE27,extra_debit=Z):
    """Generate lawful fills/funding so a fourth fill commits exactly 8000."""
    sim=make_candidate(make_generated(weights=[0,0,0,0,0]),cost=cost);prime(sim)
    for i,(s,side) in enumerate(zip(S[:3],('BUY','SELL','BUY'))):
        commit_base(sim,base_request(sim,s,side,'20',f'CSH-PREFIX-{i}',START+MINUTE+1+i))
    request=base_request(sim,S[3],'SELL','19.9','CSH-8000-BOUNDARY',START+MINUTE+10)
    raw=sim.account.engine
    probe=deepcopy(raw,{id(raw.instrument_profiles):raw.instrument_profiles})
    before=len(probe.trades);preview=probe.execute_fill(**request)
    if preview['status']!='FILLED':raise AssertionError(preview)
    ledger=deepcopy(sim.owners)
    for trade in probe.trades[before:]:ledger.trade(trade,BASE)
    with localcontext() as ctx:
        ctx.prec=40
        needed=D('8000')-sim._owner_committed(BASE,ledger,probe)+extra_debit
        rate=needed/D('2000')
    if needed<=0:raise AssertionError('POSITIVE_LAWFUL_GENERATED_DEBIT_REQUIRED')
    funded=sim.account.apply_funding(BTC,'CSH-BUDGET-DEBIT',START+MINUTE+5,rate,START)
    if exact(funded,'signed_funding_USDT')!=-needed:raise AssertionError('EXACT_FUNDING_DEBIT_REQUIRED')
    sim._flush_account()
    return sim,request


class FiniteAtomicTests(unittest.TestCase):
    def test_csh_exact_8000_after_fees_and_funding_commits_in_both_costs(self):
        for cost in (BASE27,STRESS43):
            with self.subTest(cost=cost['id']):
                sim,request=csh_boundary(cost);commit_base(sim,request)
                self.assertEqual(sim._owner_committed(BASE,sim.owners,sim.account.engine),D('8000'))
                self.assertLess(sim.owners.margins(sim.account.engine)[BASE],D('8000'))
                self.assertGreater(sim.owners.fees[BASE],0)
                self.assertGreater(sim.owners.funding_debits[BASE],0)
                self.assertGreater(sim.account.free_cash,D('1000'))
                self.assertEqual(sim.owners.quantity[FINITE][BTC],0)

    def test_csh_8000_plus_cash_tick_is_atomic_rejection_in_both_costs(self):
        for cost in (BASE27,STRESS43):
            with self.subTest(cost=cost['id']):
                sim,request=csh_boundary(cost,CASH_TICK)
                account=sim.account.snapshot();ledger=sim.owners.snapshot()
                receipt=sim.account.execute_fill(**request)
                self.assertEqual(receipt,{'status':'POLICY_REJECTED','reason':'CSH_FIXED8000_MARGIN_COST_LOSS_BUDGET'})
                self.assertEqual(sim.account.snapshot(),account);self.assertEqual(sim.owners.snapshot(),ledger)

    def test_csh_8000_plus_native_quantity_tick_is_atomic_rejection(self):
        sim,request=csh_boundary()
        request['quantity']+=sim.account.instrument_profiles[S[3]].quantity_step
        account=sim.account.snapshot();ledger=sim.owners.snapshot()
        receipt=sim.account.execute_fill(**request)
        self.assertEqual(receipt['reason'],'CSH_FIXED8000_MARGIN_COST_LOSS_BUDGET')
        self.assertEqual(sim.account.snapshot(),account);self.assertEqual(sim.owners.snapshot(),ledger)

    def test_csh_funding_credit_does_not_replenish_consumed_budget(self):
        sim,request=csh_boundary(extra_debit=CASH_TICK)
        committed=sim._owner_committed(BASE,sim.owners,sim.account.engine)
        cash=sim.account.free_cash;debits=sim.owners.funding_debits[BASE]
        sim.account.apply_funding(BTC,'CSH-CREDIT-NO-REFILL',START+MINUTE+6,D('-.0005'),START)
        sim._flush_account()
        self.assertEqual(sim.account.free_cash,cash+D('1'))
        self.assertEqual(sim.owners.funding_debits[BASE],debits)
        self.assertEqual(sim._owner_committed(BASE,sim.owners,sim.account.engine),committed)
        self.assertEqual(sim.account.execute_fill(**request)['reason'],'CSH_FIXED8000_MARGIN_COST_LOSS_BUDGET')

    def test_csh_realized_profit_never_offsets_prior_realized_loss_or_fees(self):
        sim=make_candidate(make_generated(weights=[0,0,0,0,0]));prime(sim)
        commit_base(sim,base_request(sim,BTC,'BUY','1','CSH-LOSS-OPEN',START+MINUTE+1))
        commit_base(sim,base_request(sim,BTC,'SELL','1','CSH-LOSS-CLOSE',START+2*MINUTE+1,
            execution_mid_price=D('90'),reduce_only=True))
        loss=sim.owners.realized_losses[BASE]
        self.assertGreater(loss,0)
        commit_base(sim,base_request(sim,BTC,'BUY','1','CSH-PROFIT-OPEN',START+3*MINUTE+1))
        commit_base(sim,base_request(sim,BTC,'SELL','1','CSH-PROFIT-CLOSE',START+4*MINUTE+1,
            execution_mid_price=D('120'),reduce_only=True))
        self.assertGreater(sim.owners.realized[BASE],0)
        self.assertEqual(sim.owners.realized_losses[BASE],loss)
        self.assertEqual(sim._owner_committed(BASE,sim.owners,sim.account.engine),loss+sim.owners.fees[BASE])
        self.assertGreater(sim.account.nav(),D('10000'))

    def test_csh_reduction_remains_paid_when_budget_exceeds_8000(self):
        sim,request=csh_boundary();commit_base(sim,request)
        sim.account.apply_funding(BTC,'CSH-POST-LIMIT-DEBIT',START+MINUTE+11,D('.0005'),START)
        sim._flush_account()
        self.assertEqual(sim._owner_committed(BASE,sim.owners,sim.account.engine),D('8001'))
        receipt=commit_base(sim,base_request(sim,BTC,'SELL','1','CSH-PAID-REDUCTION',START+MINUTE+12,reduce_only=True))
        self.assertEqual(receipt['fills'][0]['leg'],'CLOSE')
        self.assertGreater(exact(receipt['fills'][0],'fee_amount'),0)

    def test_each_finite_order_has_causal_actual_basis_signal_witness(self):
        sim=make_candidate(demo_bundle());finish(sim)
        signals=[e for e in sim.owner_events if e['kind']=='FINITE_MARGIN_ORDER_SIGNAL']
        self.assertEqual(len(signals),4)
        self.assertEqual([e['order_index'] for e in signals],list(range(4)))
        for event in signals:
            w=event['causal_authorization'];index=event['order_index']
            self.assertEqual(w,sim._program_order_authorizations[event['order_id']])
            self.assertEqual(w['fixed_order_margin'],str(sim.program.plan.margins()[index]))
            fills=[r for r in sim.account.trades if r['fill_id'].startswith(event['order_id']+':')]
            self.assertTrue(fills)
            self.assertTrue(all(r['signal_us']==w['signal_us'] and r['event_us']>=w['signal_us']+MINUTE+1 for r in fills))
            if index:
                self.assertLessEqual(w['mark_close_us'],w['signal_us'])
                self.assertLessEqual(w['mark_available_us'],w['signal_us'])
                with localcontext() as ctx:
                    ctx.prec=40
                    self.assertLess(abs(D(w['trigger_price'])-D(w['actual_filled_basis'])*D('.95')),D('1e-24'))
                self.assertLessEqual(D(w['mark_price']),D(w['trigger_price']))

    def test_finite_arbitrary_owner_binding_cannot_manufacture_open_order(self):
        sim=prepared_two_owner()
        self.assertIsNone(sim.program_pending)
        request=base_request(sim,BTC,'BUY','.1','FORGED-FINITE-BINDING',START+2*MINUTE+1)
        sim._fill_owner[request['fill_id']]=(FINITE,1)
        account=sim.account.snapshot();ledger=sim.owners.snapshot()
        receipt=sim.account.execute_fill(**request)
        self.assertEqual(receipt['reason'],'FINITE_CAUSAL_ORDER_TRIGGER_BINDING_REQUIRED')
        self.assertEqual(sim.account.snapshot(),account);self.assertEqual(sim.owners.snapshot(),ledger)

    def test_finite_add_cannot_signal_above_actual_basis_trigger(self):
        sim=prepared_two_owner()
        count=len(sim.owner_events)
        sim._start_margin_order(START+2*MINUTE)
        self.assertIsNone(sim.program_pending);self.assertEqual(len(sim.owner_events),count)

    def test_finite_pending_signal_mutation_rejects_before_account_changes(self):
        sim=prepared_two_owner()
        stamp=START+2*MINUTE
        sim.account.update_marks(stamp,{s:dict(price=D('94') if s==BTC else D('100'),close_us=stamp,available_us=stamp) for s in S})
        sim._evaluate_program(stamp)
        order=sim.program_pending;self.assertIsNotNone(order)
        order['signal_us']-=MINUTE
        fill_id=f'{order["order_id"]}:0:INCREASE'
        sim._fill_owner[fill_id]=(FINITE,1)
        account=sim.account.snapshot();ledger=sim.owners.snapshot()
        receipt=sim.account.execute_fill(BTC,'BUY',D('.1'),START+3*MINUTE+1,order['signal_us'],fill_id,
            execution_mid_price=D('94'),quote_available_us=START+3*MINUTE,reduce_only=False)
        self.assertEqual(receipt['reason'],'FINITE_CAUSAL_ORDER_TRIGGER_BINDING_REQUIRED')
        self.assertEqual(sim.account.snapshot(),account);self.assertEqual(sim.owners.snapshot(),ledger)

    def test_causal_add_signal_survives_quote_rebound_without_fake_retrigger(self):
        sim=prepared_two_owner();stamp=START+2*MINUTE
        sim.account.update_marks(stamp,{s:dict(price=D('94') if s==BTC else D('100'),close_us=stamp,available_us=stamp) for s in S})
        sim._evaluate_program(stamp)
        order_id=sim.program_pending['order_id']
        sim.attempt(START+3*MINUTE,row(100.))
        self.assertEqual(sim.program.completed_opening_orders,2)
        fills=[r for r in sim.account.trades if r['fill_id'].startswith(order_id+':')]
        self.assertTrue(fills);self.assertTrue(all(r['signal_us']==stamp for r in fills))

    def test_fractional_native_funding_preserves_explicit_cumulative_rounding_bridge(self):
        sim=prepared_two_owner()
        rates=(D('.000000123456789012345678901234567890123456789'),
               D('-.0000000987654321098765432109876543210987654321'))
        saw_rounding=False
        for i in range(8):
            sim.account.apply_funding(BTC,f'FRACTIONAL-FUNDING-{i}',START+(i+2)*MINUTE+1,rates[i%2],START)
            sim._flush_account()
            bridge=sim.owners.reconcile(sim.account.engine)
            if 'explicit_cumulative_funding_rounding_bridge' in bridge:
                residue=D(bridge['explicit_cumulative_funding_rounding_bridge'])
                saw_rounding=saw_rounding or residue!=0
                self.assertLess(abs(residue),D('1e-25'))
        self.assertTrue(saw_rounding)
        with localcontext() as ctx:
            ctx.prec=40
            chronological=sum((D(r['signed_native_funding_allocated']) for r in sim.owners.funding_allocations),Z)
            grouped_by_owner=sum(sim.owners.funding.values(),Z)
            self.assertNotEqual(chronological,grouped_by_owner)
            self.assertEqual(chronological,sim.account.funding_cash)
            self.assertEqual(D(bridge['explicit_cumulative_funding_rounding_bridge']),chronological-grouped_by_owner)
            expected=Z
            for fee,funding in sim.program_budget.cost_events.values():
                expected+=fee+max(-funding,Z)
            self.assertEqual(sim.program_budget.consumed_fee_funding_reserve,expected)

    def test_minus200_exit_signal_uses_owner_pnl_exact_boundary_and_neighbors(self):
        rows=stop_boundary_witnesses()
        self.assertEqual([r['loss_exit_signal'] for r in rows],[False,True,True])
        for r in rows:
            self.assertEqual(D(r['actual_owner_PnL']),D(r['intended_owner_PnL']))
            self.assertEqual(r['owner_PnL_unchanged_by_reconciliation'],True)

    def test_actual_basis_trigger_preserves_native_decimal40_boundary(self):
        sim,witness=actual_trigger_rounding_witness()
        self.assertGreater(D(witness['Decimal40_trigger']),D(witness['legacy_ambient28_trigger']))
        self.assertFalse(witness['legacy_ambient28_would_signal'])
        self.assertTrue(witness['Decimal40_signals'])
        self.assertIsNotNone(sim.program_pending)
        self.assertEqual(sim.program_pending['program_order_index'],2)


def stop_boundary_witnesses():
    rows=[]
    for epsilon in (D('1e-20'),Z,D('-1e-20')):
        sim=prepared_two_owner()
        with localcontext() as ctx:
            ctx.prec=40
            target=D('-200')+epsilon
            debit=sim.owners.pnl(FINITE,sim.account.engine)-target
            rate=debit/(sim.owners.quantity[FINITE][BTC]*D('100'))
        stamp=START+2*MINUTE+1
        sim.account.apply_funding(BTC,'NEAR-MINUS200-GENERATED',stamp,rate,START)
        sim._flush_account();pnl=sim.owners.pnl(FINITE,sim.account.engine)
        bridge=sim.owners.reconcile(sim.account.engine)
        unchanged=pnl==sim.owners.pnl(FINITE,sim.account.engine)
        sim._evaluate_program(stamp)
        rows.append({'intended_owner_PnL':str(target),'actual_owner_PnL':str(pnl),
            'generated_funding_rate':str(rate),'owner_PnL_unchanged_by_reconciliation':unchanged,
            'loss_exit_signal':any(e.get('reason')=='ACTUAL_FILL_ECONOMIC_NET_SLEEVE_PNL_LE_MINUS200' for e in sim.owner_events),
            'reconciliation':bridge})
    return rows


def actual_trigger_rounding_witness():
    sim=prepared_two_owner();stamp=START+2*MINUTE
    sim.account.update_marks(stamp,{s:dict(price=D('90') if s==BTC else D('100'),close_us=stamp,available_us=stamp) for s in S})
    sim._evaluate_program(stamp);sim.attempt(START+3*MINUTE,row(90.))
    basis=sim.owners.basis[FINITE][BTC]
    with localcontext() as ctx:
        ctx.prec=28;old=sim.program.plan.trigger_price(basis)
    with localcontext() as ctx:
        ctx.prec=40;new=sim.program.plan.trigger_price(basis);difference=new-old
    stamp=START+4*MINUTE
    sim.account.update_marks(stamp,{s:dict(price=new if s==BTC else D('100'),close_us=stamp,available_us=stamp) for s in S})
    sim._evaluate_program(stamp)
    witness={'actual_owner_basis':str(basis),'legacy_ambient28_trigger':str(old),
        'Decimal40_trigger':str(new),'trigger_difference_USDT_per_BTC':str(difference),
        'generated_mark':str(new),'legacy_ambient28_would_signal':new<=old,
        'Decimal40_signals':sim.program_pending is not None,
        'scope':'Engineered sub-1e-26 price boundary; adapter context correction, no native finance or owner amount changes'}
    return sim,witness


def generated_boundary_witnesses():
    rows=[]
    for cost in (BASE27,STRESS43):
        for extra in (Z,CASH_TICK):
            sim,request=csh_boundary(cost,extra)
            before=sim.account.snapshot();receipt=sim.account.execute_fill(**request);sim._flush_account()
            rows.append({'cost':cost['id'],'excess_over_8000':str(extra),'receipt':receipt,
                'account_unchanged':sim.account.snapshot()==before,
                'csh_committed':str(sim._owner_committed(BASE,sim.owners,sim.account.engine)),
                'owner_ledger':sim.owners.snapshot(),'one_wallet_reconciliation':sim.owners.reconcile(sim.account.engine),
                'account_snapshot':sim.account.snapshot()})
    sim=prepared_two_owner();funding_rows=[]
    rates=(D('.000000123456789012345678901234567890123456789'),D('-.0000000987654321098765432109876543210987654321'))
    for i in range(8):
        sim.account.apply_funding(BTC,f'ROUNDING-WITNESS-{i}',START+(i+2)*MINUTE+1,rates[i%2],START)
        sim._flush_account();funding_rows.append(sim.owners.reconcile(sim.account.engine))
    with localcontext() as ctx:
        ctx.prec=40
        addition_order={'native_cumulative':str(sim.account.funding_cash),
            'chronological_owner_events':str(sum((D(r['signed_native_funding_allocated']) for r in sim.owners.funding_allocations),Z)),
            'independently_accumulated_then_summed_owners':str(sum(sim.owners.funding.values(),Z))}
    _,trigger=actual_trigger_rounding_witness()
    return {'scope':'GENERATED_EXACT_OWNER_BOUNDARIES_NOT_HISTORICAL_PERFORMANCE','cases':rows,
        'cumulative_fractional_funding':funding_rows,'different_funding_addition_orders':addition_order,
        'minus200_exit_boundaries':stop_boundary_witnesses(),'actual_basis_trigger_rounding_boundary':trigger,
        'historical_wallets':0,'historical_array_parses':0,'checksum_only_public_target_files':2,'historical_status':'NO_GO'}

if __name__=='__main__':unittest.main(verbosity=2)
