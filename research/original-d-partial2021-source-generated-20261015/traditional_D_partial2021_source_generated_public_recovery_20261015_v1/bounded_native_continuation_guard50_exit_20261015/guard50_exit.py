"""Separate D: fixed Guard50 warning -> native paid full-position exit.

Separate adapter over immutable financial V2. A distinct exact-reviewed root-GO
scope is required for historical construction; no top-up capability exists. Shared native scheduler, costs, caps, quality and finances
are inherited through explicit local dependency bindings, never global patches.
"""
from collections import OrderedDict
from copy import deepcopy
from decimal import Decimal as D
from hashlib import sha256
import importlib.util
import json
from pathlib import Path
import sys

HERE=Path(__file__).resolve().parent
ROOT=HERE.parent
BASE=ROOT/'bounded_native_continuation_v2_20261015'
BASE_PINS={
    'integration.py':'dd7a7f84e3e1f4422a6a66a25df99c355c290e3ef794d294666ce7d4351484fe',
    'continuation_entry.py':'4c79aca22f89bbd63dc66e20331f226c072cb81d607815e73aef5f1875eb29a0',
    'run_finite.py':'cde55d74081990486d4b337c9ce26af0661a6a6c040aa0805dbc8b14c9cb8312',
}
for name,expected in BASE_PINS.items():
    if sha256((BASE/name).read_bytes()).hexdigest()!=expected:
        raise ValueError('IMMUTABLE_FINANCIAL_V2_BASE_PIN_MISMATCH:'+name)
_NAME='_guard50_exit_exact_financial_v2_base'
if _NAME in sys.modules:
    V2=sys.modules[_NAME]
    if Path(V2.__file__).resolve()!=(BASE/'integration.py').resolve():
        raise ValueError('CONFLICTING_DECLARED_D_BASE_IMPORT')
else:
    spec=importlib.util.spec_from_file_location(_NAME,BASE/'integration.py')
    V2=importlib.util.module_from_spec(spec);sys.modules[_NAME]=V2;spec.loader.exec_module(V2)

VERSION='SEPARATE_GUARD50_EXIT_ONLY_NATIVE_V1'
POLICY_VARIANT='GUARD50_EXIT_ONLY'
GENERATED=V2.GENERATED
SETTLEMENT=V2.SETTLEMENT
S=V2.S
MINUTE=V2.MINUTE


class Guard50ExitAccount(V2.ContinuationAccount):
    VERSION=VERSION
    def __init__(self,config=None,*,generated_scope=None,historical_scope=None,
                 settlement_mode=SETTLEMENT,policy_variant=POLICY_VARIANT,**kwargs):
        if policy_variant!=POLICY_VARIANT:
            raise ValueError('EXACT_D_GUARD50_EXIT_ONLY_VARIANT_REQUIRED')
        if historical_scope is None:
            # Initialize existing generated continuation mechanics as B. This
            # declared generated policy is never used to authorize history.
            super().__init__(config,generated_scope=generated_scope,
                settlement_mode=settlement_mode,policy_variant='CONTINUE_ONLY',**kwargs)
            self._policy_variant=POLICY_VARIANT
            self._topup_enabled=False
            return
        # Explicit new D historical fresh-genesis boundary. No generated flag,
        # old GO or prior account state is accepted as historical authority.
        from guard50_exit_entry import HistoricalExecutionScope
        if generated_scope is not None or type(historical_scope) is not HistoricalExecutionScope:
            raise ValueError('EXPLICIT_REVIEWED_D_HISTORICAL_SCOPE_REQUIRED')
        historical_scope.validate_current()
        if (historical_scope.policy_variant!=POLICY_VARIANT or settlement_mode!=SETTLEMENT
                or historical_scope.config!='STATIC50_MID'):
            raise ValueError('D_HISTORICAL_SCOPE_POLICY_MISMATCH')
        V2.P.verify_primitives()
        expected=V2.grid.make_account('MID','BASE27')
        if (config!=expected.config or tuple(kwargs.get('symbols',()))!=S
                or kwargs.get('instrument_profiles')!=expected.instrument_profiles
                or kwargs.get('closing_min_notional_exempt') is not True):
            raise ValueError('EXACT_D_HISTORICAL_MID_BASE27_COARSE_CORE5_GENESIS_REQUIRED')
        self.generated_scope=None;self._settlement_mode=settlement_mode
        self._policy_variant=POLICY_VARIANT;self._policy_enabled=True;self._topup_enabled=False
        self.transfer_journal=[];self.monitor_journal=[];self.settlement_journal=[]
        self.operation_ids={};self.pending_exits={};self.capacity_used={}
        self.capacity_registrations={};self.transfer_ids={};self.cash_watch_reason=None
        self.liquidations=[];self.blocked_signals={};self.liquidation_callback=None
        self._exact_closing=None;self.mark_quality={}
        self.quantity_profile_binding='FROZEN_COARSE_RESEARCH_PROFILE'
        V2.ENGINE.USDTLinearPerpetualAccount.__init__(self,config,**kwargs)
        if self.config.initial_cash!=D(10000):raise ValueError('FRESH_SHARED_10000_REQUIRED')
        self._execution_scope=historical_scope
        self.financial_ledger=[];self.mode_journal=[]
        for name in V2.LISTS:object.__setattr__(self,name,V2.OWNED.PersistentList(getattr(self,name)))
        for name in V2.MAPS:object.__setattr__(self,name,V2.IdentityMap(getattr(self,name)))
        self._noop_receipts=OrderedDict();self._noop_watermark=-1
        self._noop_count=0;self._noop_commitment='0'*64
        self._capture_depth=0;self._financial_sequence=0
        self._signal_projection_clock=None;self._last_mode=None;self.mode_counts={}
        import missing_mark_adapter_2024 as mark_adapter
        self._quality_intervals=((mark_adapter.FIRST_MISSING_KNOWN,mark_adapter.RESUME_AVAILABLE,S),)
        self._historical_scope_metadata=dict(historical_scope.metadata)

    def _transfer(self,*args,**kwargs):
        # Primitive _transfer does not itself check topup_enabled. D must have
        # no backdoor for a direct/internal/previews-only margin transfer.
        raise ValueError('D_GUARD50_EXIT_ONLY_INTERNAL_TRANSFERS_FORBIDDEN')

    def contract_metadata(self):
        result=super().contract_metadata()
        result.update(integration_version=VERSION,continuation_policy=VERSION,
            warning_action='NATIVE_PAID_FULL_ACTUAL_POSITION_EXIT_NO_TOPUP',
            historical_execution_admitted=self._execution_scope is not None)
        return result

    def snapshot(self):
        result=super().snapshot()
        result.update(continuation_policy=VERSION,
            warning_action='NATIVE_PAID_FULL_ACTUAL_POSITION_EXIT_NO_TOPUP',
            historical_execution_admitted=self._execution_scope is not None)
        return result

    def monitor(self,operation_id,event_us,*,headroom_features=None):
        """Same V2 receipt envelope; only the fixed known/fresh warning changes."""
        event_us=V2.P.timestamp(event_us)
        if headroom_features is not None:
            raise ValueError('HEADROOM_TRIGGER_NOT_ADMITTED_FIXED_GUARD50_ONLY')
        if operation_id!='MONITOR:'+str(event_us):
            raise ValueError('CANONICAL_MONOTONIC_MONITOR_ID_REQUIRED')
        identity=dict(kind='MONITOR',event_us=event_us,features=None)
        replay=self._begin(operation_id,identity)
        if replay is not None:return replay
        if event_us!=self.clock_us:
            raise ValueError('MONITOR_MUST_FOLLOW_NATIVE_EVENT_AT_SAME_CLOCK')
        before=(self._balances(),deepcopy(self.pending_exits),self.cash_watch_reason,self._last_mode,dict(self.mark_quality))
        actions=[]
        with self._capture('INTERNAL_TRANSFER_OR_INTENT',event_us):
            if self.policy_enabled and self.status not in V2.P.HALTS:
                # V2 C ranks transfers by E/MM. D has no wallet allocator:
                # every independently eligible warning owns a paid exit.
                for symbol in self.symbols:
                    p=self.positions[symbol]
                    if not p.quantity or not self._known_fresh(symbol,event_us):continue
                    mark=self._mark(symbol)
                    equity=p.isolated_balance+p.quantity*(mark-p.entry_price)
                    wanted=max(D(0),p.isolated_balance-equity) if equity<=p.isolated_balance/D(2) else D(0)
                    if wanted<=0:continue
                    self.pending_exits.setdefault(symbol,dict(signal_us=event_us,reason='GUARD50_PAID_EXIT_NO_TOPUP'))
                    self.cash_watch_reason='REDUCTION_REQUIRED'
                    actions.append(dict(symbol=symbol,wanted=str(wanted),transferred='0',
                        reason='GUARD50_PAID_EXIT_NO_TOPUP',full_actual_position_exit_required=True))
            elif self.status in V2.P.HALTS:
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
        record=dict(identity=V2.P._identity(identity),receipt=deepcopy(result))
        self._noop_receipts[operation_id]=record;self._noop_watermark=event_us
        self._noop_commitment=sha256((self._noop_commitment+V2.P._identity((operation_id,record))).encode()).hexdigest()
        while len(self._noop_receipts)>V2.NOOP_RECEIPT_LIMIT:self._noop_receipts.popitem(last=False)
        return result


class TokenView(V2.TokenView):pass
TokenView.__init__=V2._rebind(V2.TokenView.__init__,ContinuationAccount=Guard50ExitAccount)
class CapitalView(TokenView):
    def snapshot(self):return V2.ExactToken(self._owned)
    def execute_fill(self,*args,**kwargs):return Guard50ExitAccount.execute_fill(self._owned,*args,**kwargs)
capital_guard_fill=V2._rebind(V2.capital_guard_fill,CapitalView=CapitalView)
fresh_preview=V2._rebind(V2.fresh_preview,TokenView=TokenView)
signal_preview=V2._rebind(V2.signal_preview,TokenView=TokenView)

class ContinuationGuard(V2.ContinuationGuard):pass
ContinuationGuard.schedule=V2._rebind(V2.ContinuationGuard.schedule,signal_preview=signal_preview)
ContinuationGuard._frozen_attempt=V2._rebind(V2.ContinuationGuard._frozen_attempt,
    signal_preview=signal_preview,fresh_preview=fresh_preview,capital_guard_fill=capital_guard_fill)
ContinuationGuard.attempt=V2._continuation_attempt
class ContinuationQualityGuard(V2.ContinuationQualityGuard):pass
ContinuationQualityGuard.install=V2._rebind(V2.ContinuationQualityGuard.install,ContinuationGuard=ContinuationGuard)
_construct_native=V2._rebind(V2.construct_case,ContinuationAccount=Guard50ExitAccount,
    ContinuationGuard=ContinuationGuard,ContinuationQualityGuard=ContinuationQualityGuard,VERSION=VERSION)


def construct_case(window,source_rows,decisions,targets,*,policy_variant=POLICY_VARIANT,
                   generated_scope=None,historical_scope=None,settlement_mode=SETTLEMENT,
                   quality_intervals=()):
    sim,guard=_construct_native(window,source_rows,decisions,targets,policy_variant=policy_variant,
        generated_scope=generated_scope,historical_scope=historical_scope,settlement_mode=settlement_mode,quality_intervals=quality_intervals)
    sim.meta.update(comparison_scope='D_PAID_GUARD50_EXIT_VS_C_MARGIN_TOPUP_PACKAGE',
        warning_action='NATIVE_PAID_FULL_ACTUAL_POSITION_EXIT_NO_TOPUP',
        historical_execution_admitted=historical_scope is not None)
    sim.meta.pop('C_minus_B_scope',None)
    return sim,guard


def case_result(sim,guard):
    result=V2.case_result(sim,guard)
    if sim.account.transfer_journal:raise AssertionError('D_TRANSFER_JOURNAL_MUST_REMAIN_EMPTY')
    result['economics'].pop('C_minus_B_scope',None)
    result['economics']['comparison_scope']='D_PAID_GUARD50_EXIT_VS_C_MARGIN_TOPUP_PACKAGE'
    result['common_execution_policy'].update(version=VERSION,
        automatic_topup=False,policy_variant=POLICY_VARIANT,historical_execution_admitted=sim.account._execution_scope is not None)
    return result
