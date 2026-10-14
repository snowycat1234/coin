"""Fixed finite BTC candidate on the immutable generated H090 native account.

CSH intent is newly prespecified as8/9 of the fixed CONTROL proposal. Owners are
observations of one actual wallet. Every owner fill is an actual native receipt;
no opposing virtual inventory, independent PnL wallets or synthetic transfers.
"""
from copy import deepcopy
from decimal import Decimal as D,localcontext,ROUND_DOWN,ROUND_CEILING
from itertools import product
import hashlib,json,math
import numpy as np
from native_control import H090NativeControl,DESCRIPTOR,POLICY,S,DAY,MINUTE,ZERO,HALTS,h090_weight_guard
from scripts.investment.resumable_perpetual import ExecutionContractV2
from owner_ledger import OwnerLedger,BASE,FINITE,OWNERS,BTC,Z,exact


class FiniteNativeCandidate(H090NativeControl):
    VERSION='h090_finite_single_program_generated_v1'
    CANDIDATE_ID='CSH_MART_FINITE_REPLACE10'

    def __init__(self,*args,**kwargs):
        self.owners=OwnerLedger()
        self.program=POLICY.FiniteAddsState()
        self.program_budget=POLICY.ProgramBudget()
        self.program_pending=None;self.program_activated=False
        self.program_activation_signal=None
        self.owner_events=[];self._fill_owner={}
        self._program_order_authorizations={}
        self._trade_cursor=0;self._funding_cursor=0
        super().__init__(*args,**kwargs)
        self.reservations=POLICY.ReservationBook()
        self.reservations.reserve(BASE,D('8000'))
        self.reservations.reserve(FINITE,D('1000'))
        self.account.risk_admission=self._atomic_owner_admission
        self.meta={**self.meta,'candidate_id':self.CANDIDATE_ID,
                   'newly_prespecified_csh_control_fraction':'8/9',
                   'owner_budget_definition':'CURRENT_ATTRIBUTED_MARGIN_PLUS_CUMULATIVE_COST_AND_REALIZED_LOSS_NO_CREDIT_REPLENISHMENT'}

    def _admit_decision(self,t,target_weights,original_csh_weights,source_packet,decision_kinds):
        control_target=None
        if target_weights is not None:
            h090_weight_guard(target_weights,self.descriptor)
            original=original_csh_weights if original_csh_weights is not None else self.original_weights.get(t)
            packet=source_packet if source_packet is not None else self.source_packets.get(t)
            prepared=self._prepare(t,original,packet)
            expected={s:float(prepared['weights'][s]*(8/9)) for s in S}
            if any(target_weights[s]!=expected[s] for s in S):
                raise ValueError('EXACT_CANDIDATE_8_OVER9_CONTROL_CSH_PROPOSAL_REQUIRED')
            control_target=prepared['weights']
        super()._admit_decision(t,control_target,original_csh_weights,source_packet,decision_kinds)
        control=dict(self.weights[t])
        self.weights[t]={s:float(control[s]*(8/9)) for s in S}
        self.risk_contexts[t]['candidate_csh_control_fraction']='8/9_NEWLY_PRESPECIFIED'
        self.risk_contexts[t]['candidate_csh_weights']=dict(self.weights[t])
        h090_weight_guard(self.weights[t],self.descriptor)
        ready=self.risk_contexts[t]['ready']
        if self.program_activated and self.original_weights[t][BTC]<0 and self.owners.quantity[FINITE][BTC]>0:
            self.owner_events.append({'event_us':t,'kind':'CSH_BTC_SHORT_HELD_UNTIL_PAID_FINITE_EXIT',
                'actual_finite_owned_quantity':str(self.owners.quantity[FINITE][BTC]),
                'original_negative_BTC_weight':self.original_weights[t][BTC]})
        if self.program_activated and (not ready or self.original_weights[t][BTC]<=0):
            self._retire_program('SOURCE_INVALID' if not ready else 'ORIGINAL_BTC_NONPOSITIVE',t,
                exit_inventory=True,kind='DATA_GAP_EXIT' if not ready else 'PROTECTIVE_STOP')
        elif (not self.program_activated and not self.program.terminal and ready
                and self.original_weights[t][BTC]>0 and self.decision_kinds[t][BTC]=='DAILY_TARGET'):
            self.program_activated=True;self.program_activation_signal=t
            self.owner_events.append({'event_us':t,'kind':'FIRST_ORIGINAL_CAUSALLY_ELIGIBLE_BTC_POSITIVE_PROGRAM_ACTIVATION'})
            self._start_margin_order(t)
        self._evaluate_program(t)

    def _start_margin_order(self,signal):
        margin=self.program.next_order_margin()
        if margin is None or self.program_pending is not None or not self.program_budget.allow_further_increases():return
        context=self.risk_contexts.get(self.cursor)
        if (type(signal) is not int or not self.program_activated or not context or not context['ready']
                or not self.cursor<=signal<min(self.cursor+DAY,self.end)
                or self.original_weights[self.cursor][BTC]<=0):return
        index=self.program.completed_opening_orders
        witness={'signal_us':signal,'source_decision_us':self.cursor,'order_index':index,
            'fixed_order_margin':str(margin),'original_BTC_weight':self.original_weights[self.cursor][BTC]}
        if index==0:
            if signal!=self.program_activation_signal or self.decision_kinds[self.cursor][BTC]!='DAILY_TARGET':return
            witness['authorization']='FIRST_CAUSALLY_ELIGIBLE_ORIGINAL_BTC_POSITIVE_DECISION'
        else:
            if not self.owners.quantity[FINITE][BTC] or not self.account.marks[BTC]:return
            mark=self.account.marks[BTC][-1];basis=self.owners.basis[FINITE][BTC]
            with localcontext() as ctx:
                ctx.prec=40
                trigger=self.program.plan.trigger_price(basis)
            if mark['close_us']>signal or mark['available_us']>signal or mark['price']>trigger:return
            witness.update(authorization='COMPLETED_AVAILABLE_MARK_LE_ACTUAL_FILLED_BASIS_TIMES_095',
                actual_filled_basis=str(basis),trigger_price=str(trigger),mark_price=str(mark['price']),
                mark_close_us=mark['close_us'],mark_available_us=mark['available_us'])
        self.sequence+=1
        self.program_pending={'target':self.owners.quantity[FINITE][BTC],
            'signal_us':int(signal),'kind':'FINITE_OPEN','attempts':0,
            'order_id':f'{self.CANDIDATE_ID}-{self.cost["id"]}-FINITE-{self.sequence}',
            'program_order_index':self.program.completed_opening_orders,
            'fixed_order_margin':str(margin)}
        self._program_order_authorizations[self.program_pending['order_id']]=deepcopy(witness)
        self.owner_events.append({'event_us':int(signal),'kind':'FINITE_MARGIN_ORDER_SIGNAL',
            'order_id':self.program_pending['order_id'],'order_index':index,
            'fixed_margin':str(margin),'causal_authorization':deepcopy(witness)})

    def _retire_program(self,reason,signal,*,exit_inventory,kind='PROTECTIVE_STOP'):
        first=not self.program.terminal
        self.program.begin_terminal()
        if self.program_pending is not None and self.program_pending['kind']=='FINITE_OPEN':
            old=self.program_pending;self.program_pending=None
            self.owner_events.append({'event_us':int(signal),'kind':'FINITE_NATIVE_INCREASE_CANCEL_CONFIRMED',
                'order_id':old['order_id'],'reason':reason,'actual_owned_quantity':str(self.owners.quantity[FINITE][BTC])})
        if first:self.owner_events.append({'event_us':int(signal),'kind':'FINITE_PROGRAM_PERMANENTLY_RETIRED','reason':reason,
            'actual_owned_quantity':str(self.owners.quantity[FINITE][BTC]),
            'actual_fill_economic_net_PnL_at_signal':str(self.owners.pnl(FINITE,self.account.engine))})
        q=self.owners.quantity[FINITE][BTC]
        if exit_inventory and q:
            # A paid owner-specific exit. It cannot be netted against a CSH short.
            if self.program_pending is None or self.program_pending['kind']!=kind:
                self.sequence+=1
                self.program_pending={'target':Z,'signal_us':int(signal),'kind':kind,'attempts':0,
                    'order_id':f'{self.CANDIDATE_ID}-{self.cost["id"]}-FINITE-EXIT-{self.sequence}'}
        elif not q:
            self.program_pending=None
        self._release_flat_retired()

    def _release_flat_retired(self):
        if self.program.terminal and not self.owners.quantity[FINITE][BTC] and self.program_pending is None and FINITE in self.reservations.reservations:
            self.reservations.release(FINITE,actual_quantity=0,pending_increase_count=0)
            self.owner_events.append({'event_us':int(self.account.clock_us),
                'kind':'FINITE_RESERVATION_RELEASED_TO_PERMANENT_RETIRED_CAPITAL','amount':'1000'})

    def schedule(self,target,signal,kind,only_symbols=None):
        if kind=='TERMINAL' and self.terminal and signal==self.end-6*MINUTE:
            return super().schedule(target,signal,kind,only_symbols)
        incoming={s:D(str(target[s])) for s in S}
        hard=kind if isinstance(kind,str) else None
        if hard=='RISK_REDUCTION':
            self._flush_account()
            total=self.account.positions[BTC].quantity
            fraction=incoming[BTC]/total if total else Z
            incoming[BTC]=self.owners.quantity[BASE][BTC]*fraction
            self._retire_program('ORIGINAL_HARD_RISK',signal,exit_inventory=False)
            if self.owners.quantity[FINITE][BTC]:
                self.sequence+=1
                self.program_pending={'target':self.owners.quantity[FINITE][BTC]*fraction,
                    'signal_us':int(signal),'kind':'RISK_REDUCTION','attempts':0,
                    'order_id':f'{self.CANDIDATE_ID}-FINITE-RISK-{self.sequence}'}
        if hard=='TERMINAL':
            self._retire_program('ORIGINAL_TERMINAL60',signal,exit_inventory=True,kind='TERMINAL')
        btc_kind=kind[BTC] if isinstance(kind,dict) else kind
        if btc_kind in ('POOL_EXIT','DATA_GAP_EXIT') and self.program_activated:
            self._retire_program('ORIGINAL_'+btc_kind,signal,exit_inventory=True,kind=btc_kind)
        if btc_kind=='DAILY_TARGET' and incoming[BTC]<=0 and self.program_activated:
            self._retire_program('ORIGINAL_BTC_NONPOSITIVE',signal,exit_inventory=True)
        return super().schedule(incoming,signal,kind,only_symbols)

    def _flush_account(self):
        raw=self.account.engine
        for row in raw.trades[self._trade_cursor:]:
            binding=self._fill_owner.get(row['fill_id'])
            if binding is None:raise AssertionError('NATIVE_FILL_HAS_NO_EXPLICIT_OWNER_BINDING')
            owner,index=binding
            self.owners.trade(row,owner)
            key=row['fill_id']+':'+row['leg']
            digest=hashlib.sha256(json.dumps(row,sort_keys=True,separators=(',',':')).encode()).hexdigest()
            if key in self.processed_native_receipts and self.processed_native_receipts[key]!=digest:
                raise AssertionError('CONFLICTING_NATIVE_OWNER_RECEIPT_IDENTITY')
            self.processed_native_receipts[key]=digest
            if owner==FINITE:
                with localcontext() as ctx:
                    ctx.prec=40
                    self.program_budget.record_cost_event(row['fill_id']+':'+row['leg'],actual_fee=exact(row,'fee_amount'))
                if row['leg']=='OPEN':self.program.record_fill_receipt(raw,row['fill_id'],index)
        self._trade_cursor=len(raw.trades)
        for row in raw.funding[self._funding_cursor:]:
            allocated=self.owners.funding_event(row)
            with localcontext() as ctx:
                ctx.prec=40
                self.program_budget.record_cost_event('FUNDING:'+row['event_id'],signed_funding=allocated[FINITE])
        self._funding_cursor=len(raw.funding)
        self.owners.reconcile(raw)
        self._release_flat_retired()

    def _evaluate_program(self,stamp):
        if not self.program_activated:return
        self._flush_account()
        q=self.owners.quantity[FINITE][BTC]
        if q and self.program.plan.loss_exit_due(self.owners.pnl(FINITE,self.account.engine)):
            self._retire_program('ACTUAL_FILL_ECONOMIC_NET_SLEEVE_PNL_LE_MINUS200',stamp,exit_inventory=True)
            return
        if not self.program_budget.allow_further_increases() and not self.program.terminal:
            self._retire_program('FIXED_COST_FUNDING_RESERVE_EXHAUSTED',stamp,exit_inventory=False)
        if self.terminal or self.program.terminal or self.program_pending is not None or not q:return
        context=self.risk_contexts.get(self.cursor)
        if (not context or not context['ready'] or not self.cursor<=stamp<self.cursor+DAY
                or self.original_weights[self.cursor][BTC]<=0):return
        if self.program.next_order_margin() is None:return
        mark=self.account.marks[BTC][-1]
        if mark['available_us']>stamp or mark['close_us']>stamp:return
        with localcontext() as ctx:
            ctx.prec=40
            trigger=self.program.plan.trigger_price(self.owners.basis[FINITE][BTC])
        if mark['price']<=trigger:
            self.owner_events.append({'event_us':int(stamp),'kind':'FINITE_ADD_ACTUAL_BASIS_TRIGGER',
                'actual_basis':str(self.owners.basis[FINITE][BTC]),'trigger':str(trigger),
                'completed_available_mark':str(mark['price']),'mark_close_us':mark['close_us']})
            self._start_margin_order(stamp)

    def observe(self,stamp,cause):
        value=super().observe(stamp,cause)
        if hasattr(self,'account') and hasattr(self,'risk_contexts'):
            self._flush_account()
            if cause in ('MINUTE_MARK','AFTER_FUNDING'):self._evaluate_program(int(stamp))
        return value

    def funding_through(self,limit,inclusive):
        super().funding_through(limit,inclusive)
        self._flush_account()

    def _owner_committed(self,owner,ledger,account):
        with localcontext() as ctx:
            ctx.prec=40
            return (ledger.margins(account)[owner]+ledger.fees[owner]
                +ledger.funding_debits[owner]+ledger.realized_losses[owner])

    def _finite_quantity(self,order,mid):
        with localcontext() as ctx:
            ctx.prec=40
            remaining=self.program.plan.margins()[order['program_order_index']]-self.program.current_order_filled_margin
            rate=D(str(ExecutionContractV2.execution_rate(float(self.account.config.half_spread_bps),float(self.account.config.slippage_bps))))
            price=D(str(mid))*(D(1)+rate)
            step=self.account.instrument_profiles[BTC].quantity_step
            return max(Z,(remaining/price/step).to_integral_value(rounding=ROUND_DOWN)*step)

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
                    or order is None or order['kind']!='FINITE_OPEN' or witness is None
                    or symbol!=BTC or side!='BUY' or type(index) is not int
                    or index!=self.program.completed_opening_orders or index!=order['program_order_index']
                    or signal!=order['signal_us'] or signal!=witness['signal_us']
                    or index!=witness['order_index'] or order['fixed_order_margin']!=witness['fixed_order_margin']
                    or fill_id!=f'{order["order_id"]}:{order["attempts"]}:INCREASE'):
                return {'allow_increases':False,'reason':'FINITE_CAUSAL_ORDER_TRIGGER_BINDING_REQUIRED'}
        raw=self.account.engine
        probe=deepcopy(raw,{id(raw.instrument_profiles):raw.instrument_profiles})
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

    def attempt(self,open_us,market_row):
        self._flush_account()
        event=int(open_us)+1
        if self.program_pending is not None and self.program_pending['kind']=='FINITE_OPEN' and BTC in market_row:
            self.program_pending['target']=self.owners.quantity[FINITE][BTC]+self._finite_quantity(self.program_pending,market_row[BTC]['open'])
        due=[]
        for owner,s,order in ([(BASE,s,o) for s,o in self.pending.items()]+
                              ([(FINITE,BTC,self.program_pending)] if self.program_pending is not None else [])):
            if event>=ExecutionContractV2().earliest_execution_us(order['signal_us'])+1:due.append((owner,s,order))
        capacity={s:D(str(self.previous_quote[s]))*D('.001')/D(str(market_row[s]['open']))
            if self.previous_quote is not None and s in market_row else Z for s in S}
        for phase in ('REDUCE','INCREASE'):
            # Fixed pre-output ordering: finite exits first; original CSH
            # increases first. Every leg consumes the same per-symbol capacity.
            ordering=sorted(due,key=lambda item:((0 if item[0]==FINITE else 1) if phase=='REDUCE' else (0 if item[0]==BASE else 1),S.index(item[1])))
            for owner,s,order in ordering:
                live=self.program_pending if owner==FINITE else self.pending.get(s)
                if live is not order or s not in market_row:continue
                position=self.owners.quantity[owner][s];target=order['target'];delta=target-position
                if delta==0:continue
                reducing=bool(position and position*delta<0)
                if phase=='REDUCE':
                    if not reducing:continue
                    requested=min(abs(delta),abs(position));reduce_only=True
                    if order['kind']=='RISK_REDUCTION':
                        step=self.account.instrument_profiles[s].quantity_step
                        requested=min(abs(position),(requested/step).to_integral_value(rounding=ROUND_CEILING)*step)
                else:
                    if reducing or order['kind'] in ('RISK_REDUCTION','TERMINAL','POOL_EXIT','DATA_GAP_EXIT','PROTECTIVE_STOP'):continue
                    if self.account.status!='ACTIVE':
                        self.rejections.append({'owner':owner,'symbol':s,'event_us':event,'order_id':order['order_id'],'reason':'RISK_PRIORITY_NO_INCREASE'});continue
                    if s==BTC and owner==BASE and delta<0 and self.owners.quantity[FINITE][BTC]>0:
                        self.rejections.append({'owner':owner,'symbol':s,'event_us':event,'order_id':order['order_id'],'reason':'FINITE_OWNER_MUST_PAID_FLAT_BEFORE_CSH_SHORT'});continue
                    global_q=self.account.positions[s].quantity
                    if global_q and global_q*delta<0:
                        self.rejections.append({'owner':owner,'symbol':s,'event_us':event,'order_id':order['order_id'],'reason':'UNPAID_OWNER_DIRECTION_COLLISION'});continue
                    requested=abs(delta);reduce_only=False
                if requested==0:continue
                side='BUY' if delta>0 else 'SELL'
                fill_id=f'{order["order_id"]}:{order["attempts"]}:{phase}'
                binding=(owner,order.get('program_order_index'))
                if fill_id in self._fill_owner and self._fill_owner[fill_id]!=binding:
                    raise AssertionError('CONFLICTING_NATIVE_ORDER_OWNER_IDENTITY')
                self._fill_owner[fill_id]=binding
                before=len(self.account.trades)
                receipt=self.account.execute_fill(s,side,requested,event,order['signal_us'],fill_id,
                    execution_mid_price=D(str(market_row[s]['open'])),quote_available_us=int(open_us),
                    available_quantity=capacity[s],reduce_only=reduce_only)
                used=sum((exact(r,'quantity') for r in self.account.trades[before:] if not r.get('liquidation_takeover')),Z)
                capacity[s]=max(Z,capacity[s]-used)
                self._flush_account()
                if used>0 and order['kind']=='RISK_REDUCTION':
                    witness=next(r for r in reversed(self.breaches) if r['signal_us']==order['signal_us'])
                    if 'first_reduction_fill_us' not in witness:witness.update(first_reduction_fill_us=event,reduction_latency_us=event-order['signal_us'])
                if self.account.trades[before:] and self.first_entry is None:self.first_entry=event
                if receipt['status']!='FILLED':self.rejections.append({'owner':owner,'symbol':s,'event_us':event,
                    'order_id':order['order_id'],'phase':phase,**{k:v for k,v in receipt.items() if k!='fills'}})
                self.observe(event,'AFTER_'+phase)
                if self.account.status in HALTS:
                    self.completion='NOT_EVALUABLE_ACCOUNT_HALT_NO_LIQUIDATION_SIMULATED';self.stop=event;return
        for owner,s,order in due:
            live=self.program_pending if owner==FINITE else self.pending.get(s)
            if live is not order:continue
            order['attempts']+=1
            position=self.owners.quantity[owner][s];remaining=order['target']-position
            reached=(self.program.completed_opening_orders>order['program_order_index'] if order['kind']=='FINITE_OPEN' else
                remaining==0 or order['kind'] in ('RISK_REDUCTION','TERMINAL','POOL_EXIT','DATA_GAP_EXIT') and
                (position==0 or order['target']*position>0 and abs(position)<=abs(order['target'])))
            if reached:
                if owner==FINITE:self.program_pending=None
                else:self.pending.pop(s,None)
            elif order['attempts']>=(60 if order['kind']=='TERMINAL' else 5):
                if order['kind']=='PROTECTIVE_STOP':continue
                self.rejections.append({'owner':owner,'symbol':s,'event_us':event,'order_id':order['order_id'],
                    'reason':'SIXTY_TERMINAL_ATTEMPTS_EXPIRED' if order['kind']=='TERMINAL' else 'FIVE_ATTEMPTS_EXPIRED',
                    'remaining_signed_quantity':float(remaining),'kind':order['kind']})
                if owner==FINITE:
                    self.program_pending=None
                    if order['kind']=='FINITE_OPEN':self._retire_program('FIVE_NATIVE_OPEN_ATTEMPTS_EXPIRED',event,exit_inventory=False)
                else:self.pending.pop(s,None)
                if order['kind']=='RISK_REDUCTION' and self.account.status=='BOUND_BREACH_REDUCTION_REQUIRED':
                    self.completion='NOT_EVALUABLE_UNEXECUTABLE_RISK_REDUCTION';self.stop=event;return
                if order['kind'] in ('POOL_EXIT','DATA_GAP_EXIT') and position:
                    self.completion='NOT_EVALUABLE_UNEXECUTABLE_ASSET_EXIT';self.stop=event;return
        self._flush_account()

    def snapshot(self):
        self._flush_account();result=super().snapshot()
        result['finite_owner_binding']={'candidate_id':self.CANDIDATE_ID,'owner_ledger':self.owners.snapshot(),
            'owner_reconciliation':self.owners.reconcile(self.account.engine),
            'program_activated':self.program_activated,'program_activation_signal':self.program_activation_signal,
            'program_state':{'completed_opening_orders':self.program.completed_opening_orders,'terminal':self.program.terminal,
                'current_order_filled_margin':str(self.program.current_order_filled_margin),
                'processed_fill_receipts':deepcopy(self.program.processed_fill_receipts)},
            'program_pending':{**self.program_pending,'target':str(self.program_pending['target'])} if self.program_pending else None,
            'consumed_fee_funding_reserve':str(self.program_budget.consumed_fee_funding_reserve),
            'active_reservations':{o:str(v) for o,v in self.reservations.reservations.items()},
            'retired_reservations':{o:str(v) for o,v in self.reservations.retired_reservations.items()},
            'owner_events':deepcopy(self.owner_events),'fill_owner_bindings':deepcopy(self._fill_owner),
            'program_order_authorizations':deepcopy(self._program_order_authorizations),
            'program_cost_events':{event:[str(v) for v in values] for event,values in self.program_budget.cost_events.items()},
            'recovery_status':'NO_GO_NOT_IMPLEMENTED'}
        return result

    def result(self):
        self._flush_account();result=super().result()
        result['summary'].update(candidate_id=self.CANDIDATE_ID,
            covariance_admission='COMBINED_OWNER_ACTUAL_PLUS_PENDING_CORNERS_PRE_FILL',
            reservation_retired_original_USDT={o:str(v) for o,v in self.reservations.retired_reservations.items()},
            total_committed_original_USDT=str(sum(self.reservations.reservations.values(),Z)+sum(self.reservations.retired_reservations.values(),Z)),
            owner_reconciliation=self.owners.reconcile(self.account.engine),
            program_completed_opening_orders=self.program.completed_opening_orders,
            program_activated=self.program_activated,program_terminal=self.program.terminal,
            program_pending={**self.program_pending,'target':str(self.program_pending['target'])} if self.program_pending else None,
            consumed_finite_cost_funding_reserve=str(self.program_budget.consumed_fee_funding_reserve),
            csh_actual_margin_cost_loss_committed=str(self._owner_committed(BASE,self.owners,self.account.engine)),
            finite_program_strategy='GENERATED_NATIVE_OWNER_INTEGRATION_NOT_HISTORICAL_GO',
            full_recovery='NOT_IMPLEMENTED_NOT_CERTIFIED',historical_status='NO_GO')
        result['summary']['comparison_control_id']=result['summary'].pop('control_id','CSH_H090_CONTROL')
        result['owner_fill_allocations']=deepcopy(self.owners.fill_allocations)
        result['owner_funding_allocations']=deepcopy(self.owners.funding_allocations)
        result['owner_events']=deepcopy(self.owner_events)
        return result
