"""Separate bounded-continuation binding of the frozen native V3 scheduler.

No historical admission on import. No old wallet restoration. Native scheduler,
terminal60, partial allocator, 32-corner charging and Decimal finance are reused
from verified immutable sources through explicit function-global seam bindings.
"""
from __future__ import annotations
from collections import OrderedDict
from collections.abc import Mapping
from contextlib import contextmanager
from copy import deepcopy
from decimal import Decimal as D, localcontext
from hashlib import sha256
import importlib.util
import json
from pathlib import Path
import sys
from types import FunctionType, MethodType, SimpleNamespace

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
FROZEN = ROOT/'traditional_three_tier_freeze_20261015'
PRIMITIVE = ROOT/'bounded_account_continuation_20261015'
if str(FROZEN) not in sys.path: sys.path.insert(0, str(FROZEN))
import native_runtime as native
import frozen_grid as grid
import causal_mark_quality as quality_module
import numpy as np

VERSION = 'SEPARATE_BOUNDED_NATIVE_CONTINUATION_V2_QUALITY_NO_NEW_EXIT'
GENERATED = 'GENERATED_FAKE_ORIGIN_ONLY'
SETTLEMENT = 'CONDITIONAL_COLLATERAL_FORFEITURE'
NOOP_RECEIPT_LIMIT = 64
MINUTE = native.MINUTE
S = grid.SYMBOLS
_PRIMITIVE = None


def _load_exact(name, path):
    if name in sys.modules:
        result = sys.modules[name]
        if Path(result.__file__).resolve() != path.resolve():
            raise ValueError('CONFLICTING_DECLARED_CONTINUATION_IMPORT:'+name)
        return result
    spec=importlib.util.spec_from_file_location(name,path)
    result=importlib.util.module_from_spec(spec);sys.modules[name]=result
    spec.loader.exec_module(result)
    return result


def primitives():
    """Declared import transport: identical finance bytes, no source rewriting."""
    global _PRIMITIVE
    if _PRIMITIVE is not None:return _PRIMITIVE
    engine,_,_,_,owned,_=native.runtime()
    if (Path(engine.__file__).read_bytes() != (PRIMITIVE/'vendor_quant/perpetual_account.py').read_bytes()
            or Path(sys.modules[engine.__package__+'.execution_contract'].__file__).read_bytes()
            != (PRIMITIVE/'vendor_quant/execution_contract.py').read_bytes()):
        raise ValueError('EXACT_SAME_NATIVE_FINANCE_AND_EXECUTION_BYTES_REQUIRED')
    if sys.modules['vendor_quant.perpetual_account'] is not engine:
        raise ValueError('EXACT_NATIVE_FINANCE_BASE_REQUIRED')
    sys.modules['vendor_quant.execution_contract']=sys.modules[engine.__package__+'.execution_contract']
    _load_exact('vendor_quant.bybit_isolated_account',PRIMITIVE/'vendor_quant/bybit_isolated_account.py')
    _load_exact('headroom_buffer',PRIMITIVE/'headroom_buffer.py')
    _PRIMITIVE=_load_exact('_bounded_native_primitive',PRIMITIVE/'continuation.py')
    _PRIMITIVE.verify_primitives()
    return _PRIMITIVE


P=primitives()
ENGINE=native.runtime()[0]
OWNED=native.runtime()[4]
LISTS=tuple(OWNED.JOURNAL_LISTS)+('transfer_journal','monitor_journal','settlement_journal','liquidations','financial_ledger','mode_journal')
MAPS=tuple(OWNED.JOURNAL_MAPS)+('operation_ids','transfer_ids','capacity_registrations')
JOURNALS=LISTS+MAPS


def _freeze_extra(value):
    if type(value) is tuple:return tuple(_freeze_extra(x) for x in value)
    if type(value) is dict:
        from types import MappingProxyType
        return OWNED._FrozenMap(MappingProxyType({k:_freeze_extra(v) for k,v in value.items()}))
    if type(value) is list:return OWNED._FrozenList(tuple(_freeze_extra(v) for v in value))
    return OWNED._freeze_owned(value)


class IdentityMap(OWNED.PersistentMap):
    """The same immutable AVL map, with explicitly admitted tuple identities."""
    def __setitem__(self,key,value):
        if type(key) is not str or key in self:
            raise TypeError('NEW_STRING_FINANCIAL_ID_REQUIRED')
        frozen=_freeze_extra(value)
        root=OWNED._put(self._root,key,frozen)
        order=OWNED._put(self._order,self._size,(key,frozen))
        self._root,self._order,self._size=root,order,self._size+1


class ContinuationAccount(P.BoundedContinuationAccount):
    VERSION=VERSION
    def __init__(self,config=None,*,generated_scope=None,historical_scope=None,
                 settlement_mode=SETTLEMENT,policy_variant='TOPUP_THEN_CONTINUE',**kwargs):
        if historical_scope is None:
            super().__init__(config,generated_scope=generated_scope,
                settlement_mode=settlement_mode,policy_variant=policy_variant,**kwargs)
            self._execution_scope=None
        else:
            # New explicit historical fresh-genesis boundary. The old generated
            # constructor is NEVER called with a fake fixture flag for history.
            from continuation_entry import HistoricalExecutionScope
            if generated_scope is not None or type(historical_scope) is not HistoricalExecutionScope:
                raise ValueError('EXPLICIT_REVIEWED_HISTORICAL_SCOPE_REQUIRED')
            historical_scope.validate_current()
            if (policy_variant!=historical_scope.policy_variant or settlement_mode!=SETTLEMENT
                    or historical_scope.config!='STATIC50_MID'):
                raise ValueError('HISTORICAL_SCOPE_POLICY_MISMATCH')
            P.verify_primitives()
            expected=grid.make_account('MID','BASE27')
            if (config!=expected.config or tuple(kwargs.get('symbols',()))!=S
                    or kwargs.get('instrument_profiles')!=expected.instrument_profiles
                    or kwargs.get('closing_min_notional_exempt') is not True):
                raise ValueError('EXACT_HISTORICAL_MID_BASE27_COARSE_CORE5_GENESIS_REQUIRED')
            self.generated_scope=None;self._settlement_mode=settlement_mode
            self._policy_variant=policy_variant;self._policy_enabled=True
            self._topup_enabled=policy_variant=='TOPUP_THEN_CONTINUE'
            self.transfer_journal=[];self.monitor_journal=[];self.settlement_journal=[]
            self.operation_ids={};self.pending_exits={};self.capacity_used={}
            self.capacity_registrations={};self.transfer_ids={};self.cash_watch_reason=None
            self.liquidations=[];self.blocked_signals={};self.liquidation_callback=None
            self._exact_closing=None;self.mark_quality={}
            self.quantity_profile_binding='FROZEN_COARSE_RESEARCH_PROFILE'
            ENGINE.USDTLinearPerpetualAccount.__init__(self,config,**kwargs)
            if self.config.initial_cash!=D(10000):raise ValueError('FRESH_SHARED_10000_REQUIRED')
            self._execution_scope=historical_scope
        self.financial_ledger=[];self.mode_journal=[]
        for name in LISTS:object.__setattr__(self,name,OWNED.PersistentList(getattr(self,name)))
        for name in MAPS:object.__setattr__(self,name,IdentityMap(getattr(self,name)))
        self._noop_receipts=OrderedDict();self._noop_watermark=-1
        self._noop_count=0;self._noop_commitment='0'*64
        self._capture_depth=0;self._financial_sequence=0
        self._signal_projection_clock=None
        self._last_mode=None;self.mode_counts={}
        if self._execution_scope is None:self._quality_intervals=()
        else:
            import missing_mark_adapter_2024 as mark_adapter
            self._quality_intervals=((mark_adapter.FIRST_MISSING_KNOWN,mark_adapter.RESUME_AVAILABLE,S),)
        self._historical_scope_metadata=(None if self._execution_scope is None else dict(self._execution_scope.metadata))

    def __setattr__(self,name,value):
        if name in JOURNALS and name in vars(self) and isinstance(vars(self)[name],(OWNED.PersistentList,OWNED.PersistentMap)):
            raise TypeError('CONTINUATION_OWNED_HISTORY_REPLACEMENT_FORBIDDEN')
        object.__setattr__(self,name,value)

    def contract_metadata(self):
        result=super().contract_metadata()
        result.update(integration_version=VERSION,continuation_policy=VERSION,primitive_policy=P.POLICY_ID,generated_only=self._execution_scope is None if hasattr(self,'_execution_scope') else self.generated_scope is not None,
            scheduler_integration_certified=False,snapshot_recovery_certified=False,
            scope_binding=getattr(self,'_historical_scope_metadata',None),
            noop_receipts_retained=NOOP_RECEIPT_LIMIT,
            noop_replay_contract='RECENT_EXACT_REPLAY_FINANCIAL_IDS_PERMANENT_EVICTED_NOOP_REJECTED_NOT_REEXECUTED')
        return result

    def _balances(self):
        return (self.free_cash,tuple(self.positions[s].isolated_balance for s in self.symbols),
            self.unpaid_liability,tuple(self.positions[s].quantity for s in self.symbols),
            self.fees,self.funding_cash,self.realized_PnL,len(self.settlement_journal))

    @contextmanager
    def _capture(self,kind,event_us):
        outer=self._capture_depth==0
        before=self._balances() if outer else None
        self._capture_depth+=1
        try:yield
        finally:
            self._capture_depth-=1
            if outer:
                after=self._balances()
                if before!=after:
                    with localcontext() as ctx:
                        ctx.prec=40
                        self._financial_sequence+=1
                        self.financial_ledger.append(dict(sequence=self._financial_sequence,kind=kind,event_us=event_us,
                            free_cash_delta=str(after[0]-before[0]),
                            isolated_delta={s:str(a-b) for s,a,b in zip(self.symbols,after[1],before[1])},
                            unpaid_liability_delta=str(after[2]-before[2]),
                            quantity_delta={s:str(a-b) for s,a,b in zip(self.symbols,after[3],before[3])},
                            fee_delta=str(after[4]-before[4]),funding_delta=str(after[5]-before[5]),
                            realized_delta=str(after[6]-before[6]),conditional_settlements_delta=after[7]-before[7],
                            free_cash_after=str(after[0]),unpaid_liability_after=str(after[2])))

    def update_marks(self,observation_us,marks,*,quality=None):
        unknown={s for a,b,symbols in self._quality_intervals if a<=observation_us<b for s in symbols}
        label='DIRECT_GENERATED_OBSERVATION' if self._execution_scope is None else 'DIRECT_REVIEWED_SOURCE_OBSERVATION'
        expected_quality={s:'UNKNOWN_OR_DERIVED' if s in unknown else label for s in marks}
        if quality is None:quality=expected_quality
        if self._execution_scope is not None and quality!=expected_quality:
            raise ValueError('HISTORICAL_QUALITY_CANNOT_OVERRIDE_BOUND_SIDECAR')
        valid={'DIRECT_GENERATED_OBSERVATION','DIRECT_REVIEWED_SOURCE_OBSERVATION','UNKNOWN_OR_DERIVED'}
        if set(quality)!=set(marks) or any(x not in valid for x in quality.values()):
            raise ValueError('EXACT_EXPLICIT_QUALITY_MAPPING_REQUIRED')
        if self._execution_scope is not None and any(x=='DIRECT_GENERATED_OBSERVATION' for x in quality.values()):
            raise ValueError('GENERATED_QUALITY_CANNOT_CERTIFY_HISTORY')
        old=dict(self.mark_quality);self.mark_quality.update(quality)
        try:
            with self._capture('NATIVE_MARK_RISK',observation_us):
                return ENGINE.USDTLinearPerpetualAccount.update_marks(self,observation_us,marks)
        except BaseException:
            self.mark_quality=old;raise

    def _known_fresh(self,symbol,event_us):
        rows=self.marks[symbol]
        projection=self._signal_projection_clock
        if projection is not None and event_us==projection[1]:event_us=projection[0]
        return bool(rows and self.mark_quality.get(symbol) in {'DIRECT_GENERATED_OBSERVATION','DIRECT_REVIEWED_SOURCE_OBSERVATION'}
            and rows[-1]['available_us']<=event_us and 0<=event_us-rows[-1]['close_us']<MINUTE)

    def execute_fill(self,*args,**kwargs):
        with self._capture('NATIVE_PAID_FILL',args[3] if len(args)>3 else kwargs['event_us']):
            symbol=args[0] if args else kwargs['symbol']
            quantity=args[2] if len(args)>2 else kwargs['quantity']
            fill_id=args[5] if len(args)>5 else kwargs['fill_id']
            available=kwargs.get('available_quantity')
            available=quantity if available is None else available
            planned=(None if fill_id in self.fill_requests or kwargs.get('reduce_only',False) else
                self._floor(symbol,min(P.decimal(quantity),P.decimal(available))))
            if planned==0:
                # Match frozen quality seam: zero-executable requests own only
                # native clock/identity/attempt bookkeeping, never new risk.
                result=ENGINE.USDTLinearPerpetualAccount.execute_fill(self,*args,**kwargs)
            else:result=P.BoundedContinuationAccount.execute_fill(self,*args,**kwargs)
            for symbol in tuple(self.pending_exits):
                if not self.positions[symbol].quantity:self.pending_exits.pop(symbol,None)
            return result

    def apply_funding(self,*args,**kwargs):
        with self._capture('NATIVE_FUNDING',args[2] if len(args)>2 else kwargs['event_us']):
            return ENGINE.USDTLinearPerpetualAccount.apply_funding(self,*args,**kwargs)

    def can_increase(self,event_us):
        projection=self._signal_projection_clock
        if projection is not None and event_us==projection[1]:
            # Detached INTENT forecast, not permission for an actual fill.
            # Preserve the frozen strategy/pending lifecycle through unknown
            # quality using only already available valuation/source clocks.
            # Quality labels remain unchanged; actual execution/top-up still
            # use the strict genuine-observation predicates below.
            signal=projection[0]
            causal=all(self.marks[s] and all(row['available_us']<=signal and row['close_us']<=signal
                for row in self.marks[s]) for s in self.symbols)
            return (self.status not in P.HALTS and self.nav()>0 and not self.unpaid_liability
                and self.free_cash>=D(1000) and not self.pending_exits
                and sum((p.isolated_balance for p in self.positions.values()),D(0))<=D(8500) and causal)
        return P.BoundedContinuationAccount.can_increase(self,event_us)

    def _begin(self,operation_id,identity):
        if operation_id in self._noop_receipts:
            old=self._noop_receipts[operation_id]
            if old['identity']!=P._identity(identity):raise ValueError('CONFLICTING_OPERATION_ID')
            return deepcopy(old['receipt'])
        old=super()._begin(operation_id,identity)
        if old is not None:return old
        if identity['kind']=='MONITOR' and identity['event_us']<=self._noop_watermark:
            raise ValueError('EXPIRED_OR_REUSED_MONOTONIC_NOOP_REJECTED')
        return None

    def monitor(self,operation_id,event_us,*,headroom_features=None):
        """Frozen Guard50 arithmetic; sparse receipts and bounded no-op replay."""
        event_us=P.timestamp(event_us)
        if headroom_features is not None:raise ValueError('HEADROOM_TRIGGER_NOT_ADMITTED_FIXED_GUARD50_ONLY')
        if operation_id!='MONITOR:'+str(event_us):raise ValueError('CANONICAL_MONOTONIC_MONITOR_ID_REQUIRED')
        identity=dict(kind='MONITOR',event_us=event_us,features=None)
        replay=self._begin(operation_id,identity)
        if replay is not None:return replay
        if event_us!=self.clock_us:raise ValueError('MONITOR_MUST_FOLLOW_NATIVE_EVENT_AT_SAME_CLOCK')
        before=(self._balances(),deepcopy(self.pending_exits),self.cash_watch_reason,self._last_mode,dict(self.mark_quality))
        actions=[]
        with self._capture('INTERNAL_TRANSFER_OR_INTENT',event_us):
            if self.policy_enabled and self.status not in P.HALTS:
                ranked=[]
                for index,symbol in enumerate(self.symbols):
                    p=self.positions[symbol]
                    if not p.quantity:continue
                    if not self._known_fresh(symbol,event_us):
                        # V2 correction: unknown quality blocks top-up/new risk,
                        # as in the frozen baseline, without manufacturing a
                        # paid exit. Any already legitimate exit remains owned.
                        continue
                    mark=self._mark(symbol);equity=p.isolated_balance+p.quantity*(mark-p.entry_price)
                    mm=abs(p.quantity)*mark*self.config.maintenance_margin_rate
                    wanted=max(D(0),p.isolated_balance-equity) if equity<=p.isolated_balance/D(2) else D(0)
                    if wanted>0 and self.topup_enabled:ranked.append((equity/mm,index,symbol,wanted))
                with localcontext() as ctx:
                    ctx.prec=40
                    for _,_,symbol,wanted in sorted(ranked):
                        isolated=sum((p.isolated_balance for p in self.positions.values()),D(0))
                        budget=max(D(0),min(self.free_cash-D(1000),D(8500)-isolated))
                        amount=min(wanted,budget)
                        if amount>0:actions.append(self._transfer(symbol,amount,event_us,operation_id+':'+symbol))
                        if amount<wanted:
                            self.pending_exits.setdefault(symbol,dict(signal_us=event_us,reason='INSUFFICIENT_TOPUP_BUDGET'))
                            self.cash_watch_reason='REDUCTION_REQUIRED'
                        actions.append(dict(symbol=symbol,wanted=str(wanted),transferred=str(amount),
                            reason='LEGACY50_RESTORE_PRETRANSFER_BALANCE',full_actual_position_exit_required=symbol in self.pending_exits))
            elif self.status in P.HALTS:
                self.cash_watch_reason='UNPAID_DEBT' if self.unpaid_liability else 'UNRESOLVED_NATIVE_HALT'
        mode=self.mode(event_us);self.mode_counts[mode]=self.mode_counts.get(mode,0)+1
        if mode!=self._last_mode:
            self.mode_journal.append(dict(event_us=event_us,mode=mode));self._last_mode=mode
        result=dict(status=mode,event_us=event_us,actions=actions,pending_exits=deepcopy(self.pending_exits))
        after=(self._balances(),deepcopy(self.pending_exits),self.cash_watch_reason,self._last_mode,dict(self.mark_quality))
        if before!=after:
            self.monitor_journal.append(deepcopy(result))
            return super()._save(operation_id,identity,result)
        self._noop_count+=1
        record=dict(identity=P._identity(identity),receipt=deepcopy(result))
        self._noop_receipts[operation_id]=record
        self._noop_watermark=event_us
        self._noop_commitment=sha256((self._noop_commitment+P._identity((operation_id,record))).encode()).hexdigest()
        while len(self._noop_receipts)>NOOP_RECEIPT_LIMIT:self._noop_receipts.popitem(last=False)
        return result

    def preview_state_token(self):
        """Exact finite state plus immutable roots; no history-sized export."""
        result={}
        for name,value in vars(self).items():
            if name in {'execute_fill','liquidation_callback','_execution_scope'}:continue
            result[name]=(value.token() if name in JOURNALS else
                tuple((key,deepcopy(row)) for key,row in value.items()) if type(value) is OrderedDict else
                deepcopy(value,{id(self.instrument_profiles):self.instrument_profiles}))
        return result

    def __deepcopy__(self,memo):
        result=object.__new__(type(self));memo[id(self)]=result
        memo[id(self.instrument_profiles)]=self.instrument_profiles
        if self._execution_scope is not None:memo[id(self._execution_scope)]=self._execution_scope
        callback=self.liquidation_callback
        if callback is not None:memo[id(callback)]=None
        for name,value in vars(self).items():
            if name=='execute_fill':continue
            object.__setattr__(result,name,deepcopy(value,memo))
        result.liquidation_callback=None
        return result

    def fork_for_preview(self):return deepcopy(self)

    def snapshot(self):
        result=OWNED.export_tree(super().snapshot())
        result.update(continuation_policy=VERSION,financial_ledger=OWNED.export_tree(self.financial_ledger),mode_journal=OWNED.export_tree(self.mode_journal),
            mode_counts=dict(self.mode_counts),noop_receipt_limit=NOOP_RECEIPT_LIMIT,
            noop_receipts=deepcopy(list(self._noop_receipts.items())),noop_count=self._noop_count,
            noop_watermark=self._noop_watermark,noop_rolling_SHA256=self._noop_commitment,
            historical_execution_scope=self._historical_scope_metadata,
            scope='AUDIT_EXPORT_ONLY_NO_RESTART_OR_RESUME_CERTIFICATION')
        return result


def _rebind(function,**bindings):
    """Reuse exact code objects with explicit local dependencies, no monkeypatch."""
    result=FunctionType(function.__code__,{**function.__globals__,**bindings},function.__name__,function.__defaults__,function.__closure__)
    result.__kwdefaults__=function.__kwdefaults__
    return result


class TokenView:
    def __init__(self,account):
        if type(account) is not ContinuationAccount:raise TypeError('OWNED_CONTINUATION_ACCOUNT_REQUIRED')
        self._owned=account
    def __getattr__(self,name):return getattr(self._owned,name)
    def __deepcopy__(self,memo):
        result=object.__new__(type(self));memo[id(self)]=result
        result._owned=self._owned.fork_for_preview();return result
    def snapshot(self):return self._owned.preview_state_token()


class ExactToken:
    def __init__(self,account):self.state=account.preview_state_token()
    def __eq__(self,other):return type(other) is type(self) and native._exact_tree_equal(self.state,other.state)


class CapitalView(TokenView):
    def snapshot(self):return ExactToken(self._owned)
    def execute_fill(self,*args,**kwargs):return ContinuationAccount.execute_fill(self._owned,*args,**kwargs)


def capital_guard_fill(account,*args,**kwargs):
    policy=sys.modules['_three_tier_original_capital_policy']
    return policy.CapitalGuard(CapitalView(account)).execute_fill(*args,**kwargs)


def _risk(probe,covariance,tier_name,settlement_count):
    result=native._tier_risk(probe,covariance,tier_name)
    if (probe.status in P.HALTS or probe.unpaid_liability
            or len(probe.settlement_journal)!=settlement_count):
        result.update(valid=False,reason='HYPOTHETICAL_FORCED_SETTLEMENT_OR_UNPAID_DEBT_REJECTED')
    return result


def fresh_preview(account,*,tier_name,**kwargs):
    base=native.runtime()[5].FreshExecutionPreview
    count=len(account.settlement_journal)
    class Preview(base):
        def __init__(self,*args,**values):
            actual={s:account.positions[s].quantity for s in S}
            super().__init__(*args,**values)
            # Hypothetical OPEN marks may settle a detached probe, but the
            # original partial-ladder fallback must retain REAL inventory.
            self.actual=actual
        def _risk(self,probe):return _risk(probe,self.cov,tier_name,count)
        def _charged(self,target,tag):
            try:return super()._charged(target,tag)
            except (ValueError,RuntimeError) as error:
                return None,dict(reason='CONTINUATION_CORNER_REJECTED:'+str(error))
    return Preview(TokenView(account),**kwargs)


def signal_preview(account,binding,quote,quote_us,*,tier_name,admission_us):
    clone=account.fork_for_preview()
    if not any(p.quantity for p in clone.positions.values()):
        missing={s:dict(price=D(binding.prices[i]),close_us=binding.signal_us,available_us=binding.signal_us)
            for i,s in enumerate(S) if not clone.marks[s]}
        if missing:clone.update_marks(binding.signal_us,missing)
    base=native.runtime()[5].FreshExecutionPreview
    # Intent sizing only: the exact native signal preview charges future
    # eligible execution at ORIGINAL already-known prices. Freshness remains
    # bound to that original signal, never a forged future mark timestamp.
    # This detached projection flag cannot appear on the actual account.
    clone._signal_projection_clock=(binding.signal_us,admission_us)
    count=len(account.settlement_journal)
    class SignalPreview(base):
        def __init__(self):
            self.account=TokenView(clone);self.actual={s:clone.positions[s].quantity for s in S}
            self.prices=dict(zip(S,map(D,binding.prices)));self.pending={s:account.positions[s].quantity for s in S}
            self.quote={s:D(str(quote[s])) for s in S}
            self.event_us,self.signal_us,self.quote_us=admission_us,binding.signal_us,quote_us
            self.price_us=dict(zip(S,binding.price_available_us));self.cov=grid._covariance(binding.covariance)
            self.before=self.account.snapshot()
            if (quote_us>admission_us or binding.covariance_available_us>binding.signal_us
                    or any(x>binding.signal_us for x in self.price_us.values())
                    or any(not x.is_finite() or x<0 for x in self.quote.values())):
                raise ValueError('CAUSAL_SIGNAL_AND_REAL_COMPLETED_CAPACITY_REQUIRED')
        def _risk(self,probe):return _risk(probe,self.cov,tier_name,count)
        def _charged(self,target,tag):
            try:return super()._charged(target,tag)
            except (ValueError,RuntimeError) as error:return None,dict(reason='CONTINUATION_CORNER_REJECTED:'+str(error))
    return SignalPreview()


# Exact frozen guard code objects, dependency bindings declared only here.
_runtime_view=lambda: (*native.runtime()[:4],SimpleNamespace(fork_owned_account=lambda a:a.fork_for_preview()),native.runtime()[5])
class ContinuationQualityGuard(quality_module.CausalMarkQualityGuard):
    def install(self):
        if (self._installed or type(self.guard) is not ContinuationGuard or not self.guard._installed
                or self.sim.attempt!=self.guard.attempt or 'execute_fill' in vars(self.sim.account)
                or getattr(self.guard.original_attempt,'__self__',None) is not self.sim
                or any(s not in self.sim.symbols for x in self.intervals for s in x.symbols)):
            raise ValueError('EXACT_INSTALLED_CONTINUATION_INNER_QUALITY_SEAM_REQUIRED')
        self.original_attempt=self.guard.original_attempt
        self.guard.original_attempt=self.attempt;self._installed=True
        return self


class ContinuationGuard(native.PartialTierGuard):pass
ContinuationGuard.schedule=_rebind(native.PartialTierGuard.schedule,signal_preview=signal_preview,runtime=_runtime_view)
ContinuationGuard._frozen_attempt=_rebind(native.PartialTierGuard.attempt,signal_preview=signal_preview,
    fresh_preview=fresh_preview,capital_guard_fill=capital_guard_fill,runtime=_runtime_view)


def _continuation_attempt(self,open_us,market_row):
    result=self._frozen_attempt(open_us,market_row)
    if self.sim.stop is not None:return result
    event=int(open_us)+1
    for symbol,intent in tuple(self.sim.account.pending_exits.items()):
        order=self.sim.pending.get(symbol)
        if (order is not None and order['kind']=='PROTECTIVE_STOP' and order['attempts']>=5
                and self.sim.account.positions[symbol].quantity):
            identity='WARNING_RENEW:'+symbol+':'+str(event)
            intent['signal_us']=event;intent['renewals']=intent.get('renewals',0)+1
            self.sim.account.operation_ids[identity]=dict(identity=identity,receipt=dict(
                symbol=symbol,event_us=event,renewals=intent['renewals'],paid_fills_only=True))
            self.sim.account.mode_journal.append(dict(kind='PAID_WARNING_EXIT_RENEWED_AFTER_FIVE_OPENS',
                event_us=event,symbol=symbol,renewals=intent['renewals']))
            self.original_schedule(dict.fromkeys(S,D(0)),event,'PROTECTIVE_STOP',(symbol,))
    return result


ContinuationGuard.attempt=_continuation_attempt


def construct_case(window,source_rows,decisions,targets,*,policy_variant,
                   generated_scope=None,historical_scope=None,settlement_mode=SETTLEMENT,
                   quality_intervals=()):
    if historical_scope is None:
        if generated_scope!=GENERATED or window.get('fixture_scope')!=GENERATED:
            raise ValueError('GENERATED_FIXTURE_OR_EXACT_HISTORICAL_SCOPE_REQUIRED')
        scope=GENERATED
    else:
        if generated_scope is not None:raise ValueError('NO_GENERATED_FLAG_FOR_HISTORICAL_INPUTS')
        historical_scope.validate_current()
        historical_scope.validate_inputs(window,source_rows,decisions,targets)
        scope=historical_scope.source_scope
        import missing_mark_adapter_2024 as mark_adapter
        expected_quality=((mark_adapter.FIRST_MISSING_KNOWN,mark_adapter.RESUME_AVAILABLE,S),)
        if quality_intervals!=expected_quality:raise ValueError('EXACT_REVIEWED_HISTORICAL_QUALITY_INTERVAL_REQUIRED')
    def factory(tier_name,cost):
        plain=grid.make_account(tier_name,cost['id'])
        return ContinuationAccount(plain.config,symbols=S,instrument_profiles=plain.instrument_profiles,
            closing_min_notional_exempt=True,generated_scope=generated_scope,historical_scope=historical_scope,
            settlement_mode=settlement_mode,policy_variant=policy_variant)
    constructor=_rebind(native._construct_case,make_owned_account=factory,PartialTierGuard=ContinuationGuard)
    sim,guard=constructor(window,source_rows,decisions,targets,tier_name='MID',cost_name='BASE27',source_scope=scope)
    account=sim.account
    account.quantity_profile_binding='FROZEN_COARSE_RESEARCH_PROFILE'
    account._quality_intervals=tuple(quality_intervals)
    if historical_scope is not None:
        import missing_mark_adapter_2024 as mark_adapter
        original_genuine=mark_adapter.LAST_GENUINE_AVAILABLE
        sidecar=json.loads(historical_scope._preparation_raw)['artifacts']['CAUSAL_MARK_ADAPTER.json']['SHA256']
    else:
        original_genuine=None
        sidecar=sha256(P._identity(quality_intervals).encode()).hexdigest()
    intervals=tuple(quality_module.StaleMarkInterval(start_us=a,end_us=b,
        original_genuine_observation_us=original_genuine if original_genuine is not None else a-MINUTE,
        symbols=tuple(symbols)) for a,b,symbols in quality_intervals)
    quality=ContinuationQualityGuard(guard,intervals=intervals,source_sidecar_sha256=sidecar).install()
    guard.causal_mark_quality_guard=quality
    sim.meta.update(mark_quality_policy_identity=quality.policy_sha256,
        mark_quality_guard_version=quality_module.VERSION,
        original_interpolated_mark_execution_admitted=False)
    if getattr(account.liquidation_callback,'__self__',None) is not sim:
        raise AssertionError('NATIVE_PENDING_CANCELLATION_CALLBACK_REQUIRED')
    original_risk=sim.risk_schedule
    def risk_schedule(_sim,event_us):
        # Native funding calls this once per symbol. Only the last member of a
        # same-clock batch may monitor; funding keeps its strict-prior mark rule.
        sameclock_next=(_sim.event_cursor<len(_sim.window['events']) and _sim.window['events'][_sim.event_cursor]['event_us']==event_us)
        if (not sameclock_next and account.clock_us==event_us and event_us>account._noop_watermark):
            account.monitor('MONITOR:'+str(event_us),event_us)
        original_risk(event_us)
        if not _sim.terminal:
            for s,intent in tuple(account.pending_exits.items()):
                if not account.positions[s].quantity:account.pending_exits.pop(s,None);continue
                existing=_sim.pending.get(s)
                if existing is None or existing['kind'] not in {'PROTECTIVE_STOP','TERMINAL'}:
                    # Existing native PROTECTIVE_STOP is paid, reduce-only and
                    # persistent across five-open expiry, with native latency.
                    guard.original_schedule(dict.fromkeys(S,D(0)),intent['signal_us'],'PROTECTIVE_STOP',(s,))
    sim.risk_schedule=MethodType(risk_schedule,sim)
    sim.meta.update(continuation_version=VERSION,policy_variant=policy_variant,settlement_mode=settlement_mode,
        noop_receipt_limit=NOOP_RECEIPT_LIMIT,old_baselines_modified=False,
        C_minus_B_scope='WHOLE_BOUNDED_MARGIN_MANAGEMENT_PACKAGE_NOT_PURE_TOPUP')
    return sim,guard


def financial_reconciliation(account):
    """Primary cash/isolated/liability ledger, then NAV decomposition."""
    with localcontext() as ctx:
        ctx.prec=40
        free=D(10000)+sum((D(r['free_cash_delta']) for r in account.financial_ledger),D(0))
        isolated={s:sum((D(r['isolated_delta'][s]) for r in account.financial_ledger),D(0)) for s in S}
        debt=sum((D(r['unpaid_liability_delta']) for r in account.financial_ledger),D(0))
        unrealized=sum((p.quantity*(account._mark(s)-p.entry_price) for s,p in account.positions.items() if p.quantity),D(0))
        balance_nav=free+sum(isolated.values(),D(0))+unrealized-debt
        realized=account.realized_PnL
        # Preserve the exact frozen summary operation ordering. Native 40-digit
        # accumulators may leave a visible secondary PnL bridge residual after
        # repeating-basis partial closes. It is never rounded away or treated
        # as a cash/isolated/debt adjustment; exact primary balances still win.
        gross_mid=realized+unrealized+account.execution_cost
        frozen_bridge=(account.nav()-account.config.initial_cash)-(gross_mid-account.execution_cost-account.fees+account.funding_cash)
        native_bridge=D(account.summary()['decimal_strings']['accounting_bridge_error_USDT'])
        replay_match=frozen_bridge==native_bridge
        errors=dict(free_cash=str(free-account.free_cash),unpaid_liability=str(debt-account.unpaid_liability),
            isolated={s:str(isolated[s]-account.positions[s].isolated_balance) for s in S},
            NAV=str(balance_nav-account.nav()))
        passed=(all(D(v)==0 for k,v in errors.items() if k!='isolated') and all(D(v)==0 for v in errors['isolated'].values()) and replay_match)
        return dict(schema='PRIMARY_CONTINUATION_FINANCIAL_CASHFLOW_RECONCILIATION_V1',passed=passed,
            ledger_rows=len(account.financial_ledger),reconciled_free_cash=str(free),
            native_40digit_secondary_PnL_bridge_residual=str(native_bridge),
            exact_frozen_native_secondary_arithmetic_replay_match=replay_match,
            secondary_residual_is_not_cashflow_or_silently_forgiven=True,
            reconciled_isolated={s:str(v) for s,v in isolated.items()},reconciled_unpaid_liability=str(debt),
            current_unrealized=str(unrealized),reconciled_NAV=str(balance_nav),errors=errors,
            transfers_are_internal_and_not_PnL=True,conditional_support_is_explicit_value_not_free_cash=True)


def case_result(sim,guard):
    result=native.case_result(sim,guard);account=sim.account
    report=account.economic_report();full=sim.stop is None and sim.rows_written==(sim.end-sim.start)//MINUTE
    paid=bool(full and report['paid_flat']);settled=bool(full and report['settled_flat_under_declared_model'])
    net=float(account.nav()/D(10000)-1)
    result['economics'].update(full_calendar=full,paid_flat=paid,actual_paid_market_flat=paid,
        conditional_settled_flat=settled and bool(account.settlement_journal),
        settled_flat_under_declared_model=settled,paid_net_return=net if paid else None,
        conditional_model_net_return=net if settled and account.settlement_journal else None,
        comparable_full_calendar_return=net if settled else None,
        halted_prefix_return=net if not full else None,
        actual_liquidation_fills=0,conditional_position_settlements=len(account.settlement_journal),
        liquidation_fill_model='CONDITIONAL_COLLATERAL_FORFEITURE_NOT_PAID_MARKET_LIQUIDATION',
        conditional_insurance_overshoot_absorption_USDT=report['conditional_insurance_overshoot_absorption_USDT'],
        conditional_NAV_adjustment_USDT=report['conditional_NAV_adjustment_USDT'],
        conditional_positive_residual_forfeited_USDT=str(sum((D(r['decimal_strings']['conditional_positive_residual_forfeited']) for r in account.settlement_journal),D(0))),
        actual_remaining_isolated_collateral_forfeited_USDT=str(sum((D(r['isolated_margin_lost']) for r in account.liquidations),D(0))),
        actual_paid_market_turnover_USDT=str(sum((D(r['decimal_strings']['quantity'])*D(r['decimal_strings']['fill_price']) for r in account.trades if not r.get('liquidation_takeover')),D(0))),
        conditional_takeover_notional_is_not_paid_market_turnover=True,
        transfers_are_internal_not_PnL=True,
        market_and_paid_cost_net_PnL_excluding_conditional_settlement_value=report['market_and_paid_cost_net_PnL_excluding_conditional_settlement_value'],
        C_minus_B_scope='WHOLE_BOUNDED_MARGIN_MANAGEMENT_PACKAGE_NOT_PURE_TOPUP',
        native_settlement_certified=False,continuation_mode=account.mode(),cashwatch_counts=dict(account.mode_counts))
    result['common_execution_policy'].update(version=VERSION,automatic_topup=account.topup_enabled,
        policy_variant=account.policy_variant,settlement_mode=account.settlement_mode)
    result['primary_financial_reconciliation']=financial_reconciliation(account)
    result['continuation_economic_report']=report
    if not result['primary_financial_reconciliation']['passed']:
        raise AssertionError('PRIMARY_FINANCIAL_CASHFLOW_RECONCILIATION_FAILED')
    return result


def code_identity():
    files=('integration.py','continuation_entry.py','run_finite.py')
    return {name:sha256((HERE/name).read_bytes()).hexdigest() for name in files if (HERE/name).is_file()}
