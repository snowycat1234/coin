"""Finite-only performance caller: exact owner admission copy, one clone substitution."""
from copy import deepcopy
from decimal import Decimal as D, localcontext
from itertools import product
import hashlib, json, math
import numpy as np
from native_control import S, DAY
from finite_candidate import FiniteNativeCandidate
from owner_ledger import BASE, FINITE, BTC, Z, exact
from preview_prefix import clone_preview_account

class PrefixFiniteNativeCandidate(FiniteNativeCandidate):
    def _atomic_owner_admission(self,args,kwargs):
        self._flush_account()
        fill_id=args[5] if len(args)>5 else kwargs.get('fill_id')
        binding=self._fill_owner.get(fill_id)
        if binding is None:return {'allow_increases':False,'reason':'EXPLICIT_OWNER_ORDER_BINDING_REQUIRED'}
        owner,index=binding;event=args[3] if len(args)>3 else kwargs.get('event_us')
        context=self.risk_contexts.get(self.cursor)
        if not context or not context['ready'] or type(event) is not int or not self.cursor<=event<min(self.cursor+DAY,self.end):
            return {'allow_increases':False,'reason':'SOURCE_FRESHNESS_REQUIRED_FOR_OWNER_INCREASE'}
        if owner==FINITE and (self.program.terminal or not self.program_budget.allow_further_increases()):
            return {'allow_increases':False,'reason':'FINITE_PROGRAM_RETIRED_OR_COST_RESERVE_EXHAUSTED'}
        if owner==FINITE:
            order=self.program_pending
            signal=args[4] if len(args)>4 else kwargs.get('signal_us')
            symbol=args[0] if args else kwargs.get('symbol')
            side=args[1] if len(args)>1 else kwargs.get('side')
            witness=self._program_order_authorizations.get(order['order_id']) if order else None
            if (not self.program_activated or self.original_weights[self.cursor][BTC]<=0
                    or order is None or order['kind']!='FINITE_OPEN' or type(witness) is not dict
                    or symbol!=BTC or side!='BUY' or type(index) is not int
                    or index!=self.program.completed_opening_orders or index!=order['program_order_index']
                    or signal!=order['signal_us'] or signal!=witness.get('signal_us')
                    or index!=witness.get('order_index') or order['fixed_order_margin']!=witness.get('fixed_order_margin')
                    or fill_id!=f'{order["order_id"]}:{order["attempts"]}:INCREASE'):
                return {'allow_increases':False,'reason':'FINITE_CAUSAL_ORDER_TRIGGER_BINDING_REQUIRED'}
            expected=self._expected_program_witness(order)
            try:
                exact_witness=(expected is not None and json.dumps(witness,sort_keys=True,allow_nan=False)==json.dumps(expected,sort_keys=True,allow_nan=False))
            except (TypeError,ValueError):exact_witness=False
            if not exact_witness:
                return {'allow_increases':False,'reason':'FINITE_CAUSAL_SOURCE_BASIS_MARK_WITNESS_MISMATCH'}
        raw=self.account.engine
        probe=clone_preview_account(raw)
        before=len(probe.trades);receipt=probe.execute_fill(*args,**kwargs)
        ledger=deepcopy(self.owners)
        for row in probe.trades[before:]:ledger.trade(row,owner)
        if self._owner_committed(BASE,ledger,probe)>D('8000'):
            return {'allow_increases':False,'reason':'CSH_FIXED8000_MARGIN_COST_LOSS_BUDGET'}
        if owner==FINITE:
            with localcontext() as ctx:
                ctx.prec=40
                allocated=sum((exact(row,'margin_allocated') for row in probe.trades[before:]),Z)
                remaining=self.program.plan.margins()[index]-self.program.current_order_filled_margin
                spent=self.program_budget.consumed_fee_funding_reserve+sum((exact(row,'fee_amount') for row in probe.trades[before:]),Z)
            if allocated>remaining:return {'allow_increases':False,'reason':'FINITE_FIXED_ORDER_MARGIN_EXCEEDED'}
            if spent>self.program.plan.cost_funding_reserve():
                return {'allow_increases':False,'reason':'FINITE_FIXED135_COST_FUNDING_BUFFER'}
        nav=probe.nav()
        if nav<=0:return {'allow_increases':False,'reason':'NONPOSITIVE_ACTUAL_WALLET_NAV'}
        prices=np.asarray([float(probe.marks[s][-1]['price']) if probe.marks[s] else float(self.daily_prices[s][self.cursor]) for s in S])
        endpoints=[]
        for s in S:
            actual=ledger.quantity[BASE][s]
            pending=self.pending.get(s)
            target=pending['target'] if pending is not None else actual
            endpoints.append((actual,target) if target!=actual else (actual,))
        finite_actual=ledger.quantity[FINITE][BTC]
        finite_target=self.program_pending['target'] if self.program_pending is not None else finite_actual
        finite_ends=(finite_actual,finite_target) if finite_actual!=finite_target else (finite_actual,)
        cov=context['covariance']
        for base_point in product(*endpoints):
            for finite_q in finite_ends:
                if base_point[0]*finite_q<0:
                    return {'allow_increases':False,'reason':'UNPAID_OPPOSING_OWNER_COLLISION'}
                signed=np.asarray([float(v) for v in base_point]);signed[0]+=float(finite_q)
                gross_assets=np.abs(np.asarray([float(v) for v in base_point]));gross_assets[0]+=abs(float(finite_q))
                gross_weights=gross_assets*prices/float(nav)
                w=signed*prices/float(nav);variance=float(w@cov@w)
                if not math.isfinite(variance) or variance < -1e-15:
                    return {'allow_increases':False,'reason':'OWNER_PENDING_COVARIANCE_INVALID'}
                if float(gross_weights.sum())>.90+1e-12 or float(gross_weights.max())>.30+1e-12 or math.sqrt(max(variance,0.))>.15+1e-12:
                    return {'allow_increases':False,'reason':'COMBINED_OWNER_ACTUAL_PENDING_090_030_015_CAP'}
        return {'allow_increases':True,'reason':'PASS_ATOMIC_OWNER_PROGRAM_CSH_AND_GLOBAL_CAPITAL_GATES'}
