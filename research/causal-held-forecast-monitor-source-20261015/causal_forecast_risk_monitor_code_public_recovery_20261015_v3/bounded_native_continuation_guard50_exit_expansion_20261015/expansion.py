"""Fixed DEV matrix transport of the exact reviewed D paid-Guard50 rule.

Only tier/calendar/source admission seams generalize. The D monitor, transfer
prohibition, native finance, latency, capacity and charged-preview rules remain
identical code objects. No historical admission or launch occurs on import.
"""
from collections import OrderedDict
from hashlib import sha256
import importlib.util
from pathlib import Path
import sys
from types import MethodType

HERE=Path(__file__).resolve().parent
ROOT=HERE.parent
FROZEN_D=ROOT/'bounded_native_continuation_guard50_exit_20261015'
FROZEN_D_PINS={
    'guard50_exit.py':'5fb0b20494269da55ea705c9f3f8aaa7270d132eb3d566eb81a29cb0466b1fc8',
    'guard50_exit_entry.py':'cf50f5c1cde1e12d8f70fb081acc49a3505252cedc3e10dd46c9463c962d0dc3',
    'run_guard50_exit.py':'8c41a6e6d93ee085530dbb5d482cc02fa6cbd34e1c2989098c3bcc9088d968f2',
}
for name,digest in FROZEN_D_PINS.items():
    if sha256((FROZEN_D/name).read_bytes()).hexdigest()!=digest:
        raise ValueError('FROZEN_D_RULE_OR_ENTRY_PIN_MISMATCH:'+name)
_NAME='_fixed_matrix_exact_guard50_exit_base'
if _NAME in sys.modules:
    D=sys.modules[_NAME]
    if Path(D.__file__).resolve()!=(FROZEN_D/'guard50_exit.py').resolve():
        raise ValueError('CONFLICTING_DECLARED_FIXED_D_IMPORT')
else:
    spec=importlib.util.spec_from_file_location(_NAME,FROZEN_D/'guard50_exit.py')
    D=importlib.util.module_from_spec(spec);sys.modules[_NAME]=D;spec.loader.exec_module(D)
V2=D.V2
DEC=V2.D
VERSION='FIXED_D_GUARD50_EXIT_DEV_2023_2024_SEVENTEEN_CELL_TRANSPORT_V1'
POLICY_VARIANT=D.POLICY_VARIANT
GENERATED=D.GENERATED
SETTLEMENT=D.SETTLEMENT
S=D.S
MINUTE=D.MINUTE
TIERS=('LOW','MID','HIGH')


class ExpansionAccount(D.Guard50ExitAccount):
    VERSION=VERSION
    def __init__(self,config=None,*,generated_scope=None,historical_scope=None,tier_name=None,
                 settlement_mode=SETTLEMENT,policy_variant=POLICY_VARIANT,**kwargs):
        if policy_variant!=POLICY_VARIANT:
            raise ValueError('EXACT_FROZEN_D_POLICY_REQUIRED')
        if historical_scope is None:
            tier_name='MID' if tier_name is None else tier_name
            if tier_name not in TIERS:raise ValueError('FIXED_GRID_TIER_REQUIRED')
            super().__init__(config,generated_scope=generated_scope,settlement_mode=settlement_mode,
                policy_variant=policy_variant,**kwargs)
            self._bound_tier_name=tier_name
            return
        from expansion_entry import CaseExecutionScope
        if generated_scope is not None or type(historical_scope) is not CaseExecutionScope:
            raise ValueError('EXACT_SEALED_FIXED_MATRIX_HISTORICAL_SCOPE_REQUIRED')
        historical_scope.validate_current()
        actual_tier=historical_scope.tier_name
        if (actual_tier not in TIERS or tier_name not in (None,actual_tier)
                or historical_scope.policy_variant!=POLICY_VARIANT or settlement_mode!=SETTLEMENT):
            raise ValueError('FIXED_MATRIX_D_SCOPE_POLICY_OR_TIER_MISMATCH')
        V2.P.verify_primitives()
        expected=V2.grid.make_account(actual_tier,'BASE27')
        if (config!=expected.config or tuple(kwargs.get('symbols',()))!=S
                or kwargs.get('instrument_profiles')!=expected.instrument_profiles
                or kwargs.get('closing_min_notional_exempt') is not True):
            raise ValueError('EXACT_FIXED_MATRIX_TIER_BASE27_COARSE_FRESH_GENESIS_REQUIRED')
        self.generated_scope=None;self._settlement_mode=settlement_mode
        self._policy_variant=POLICY_VARIANT;self._policy_enabled=True;self._topup_enabled=False
        self.transfer_journal=[];self.monitor_journal=[];self.settlement_journal=[]
        self.operation_ids={};self.pending_exits={};self.capacity_used={}
        self.capacity_registrations={};self.transfer_ids={};self.cash_watch_reason=None
        self.liquidations=[];self.blocked_signals={};self.liquidation_callback=None
        self._exact_closing=None;self.mark_quality={}
        self.quantity_profile_binding='FROZEN_COARSE_RESEARCH_PROFILE'
        V2.ENGINE.USDTLinearPerpetualAccount.__init__(self,config,**kwargs)
        if self.config.initial_cash!=DEC(10000):raise ValueError('FRESH_SHARED_10000_REQUIRED')
        self._execution_scope=historical_scope
        self.financial_ledger=[];self.mode_journal=[]
        for name in V2.LISTS:object.__setattr__(self,name,V2.OWNED.PersistentList(getattr(self,name)))
        for name in V2.MAPS:object.__setattr__(self,name,V2.IdentityMap(getattr(self,name)))
        self._noop_receipts=OrderedDict();self._noop_watermark=-1
        self._noop_count=0;self._noop_commitment='0'*64
        self._capture_depth=0;self._financial_sequence=0
        self._signal_projection_clock=None;self._last_mode=None;self.mode_counts={}
        self._quality_intervals=tuple(historical_scope.quality_intervals)
        self._historical_scope_metadata=dict(historical_scope.metadata)
        self._bound_tier_name=actual_tier

    def contract_metadata(self):
        result=super().contract_metadata()
        result.update(integration_version=VERSION,continuation_policy=VERSION,
            frozen_D_rule_SHA256=FROZEN_D_PINS['guard50_exit.py'],
            bound_nominal_tier=getattr(self,'_bound_tier_name',None),
            nominal_tier_is_not_exact_realized_risk_matching=True,adaptive_DEV_only=True)
        return result

    def snapshot(self):
        result=super().snapshot()
        result.update(continuation_policy=VERSION,
            frozen_D_rule_SHA256=FROZEN_D_PINS['guard50_exit.py'],
            bound_nominal_tier=self._bound_tier_name,adaptive_DEV_only=True)
        return result


class TokenView(D.TokenView):pass
TokenView.__init__=V2._rebind(D.TokenView.__init__,ContinuationAccount=ExpansionAccount)
class CapitalView(TokenView):
    def snapshot(self):return V2.ExactToken(self._owned)
    def execute_fill(self,*args,**kwargs):return ExpansionAccount.execute_fill(self._owned,*args,**kwargs)
capital_guard_fill=V2._rebind(D.capital_guard_fill,CapitalView=CapitalView)
fresh_preview=V2._rebind(D.fresh_preview,TokenView=TokenView)
signal_preview=V2._rebind(D.signal_preview,TokenView=TokenView)
class ContinuationGuard(D.ContinuationGuard):pass
ContinuationGuard.schedule=V2._rebind(D.ContinuationGuard.schedule,signal_preview=signal_preview)
ContinuationGuard._frozen_attempt=V2._rebind(D.ContinuationGuard._frozen_attempt,
    signal_preview=signal_preview,fresh_preview=fresh_preview,capital_guard_fill=capital_guard_fill)
ContinuationGuard.attempt=D.ContinuationGuard.attempt
class ContinuationQualityGuard(D.ContinuationQualityGuard):pass
ContinuationQualityGuard.install=V2._rebind(D.ContinuationQualityGuard.install,ContinuationGuard=ContinuationGuard)


def construct_case(window,source_rows,decisions,targets,*,policy_variant=POLICY_VARIANT,
                   tier_name=None,generated_scope=None,historical_scope=None,
                   settlement_mode=SETTLEMENT,quality_intervals=()):
    if policy_variant!=POLICY_VARIANT:raise ValueError('EXACT_FROZEN_D_POLICY_REQUIRED')
    if historical_scope is None:
        if generated_scope!=GENERATED or window.get('fixture_scope')!=GENERATED:
            raise ValueError('GENERATED_FIXTURE_OR_EXACT_FIXED_MATRIX_SCOPE_REQUIRED')
        tier_name='MID' if tier_name is None else tier_name
        if tier_name not in TIERS:raise ValueError('FIXED_GRID_TIER_REQUIRED')
        scope=GENERATED;original_genuine=None
        sidecar=sha256(V2.P._identity(quality_intervals).encode()).hexdigest()
    else:
        from expansion_entry import CaseExecutionScope
        if generated_scope is not None or type(historical_scope) is not CaseExecutionScope:
            raise ValueError('EXACT_SEALED_FIXED_MATRIX_HISTORICAL_SCOPE_REQUIRED')
        historical_scope.validate_current()
        historical_scope.validate_inputs(window,source_rows,decisions,targets)
        if tier_name not in (None,historical_scope.tier_name):
            raise ValueError('HISTORICAL_FIXED_MATRIX_TIER_CANNOT_BE_SWAPPED')
        tier_name=historical_scope.tier_name
        if quality_intervals!=historical_scope.quality_intervals:
            raise ValueError('EXACT_YEAR_BOUND_CAUSAL_QUALITY_INTERVAL_REQUIRED')
        scope=historical_scope.source_scope
        original_genuine=historical_scope.original_genuine_observation_us
        sidecar=historical_scope.quality_sidecar_sha256
    def factory(tier_name,cost):
        plain=V2.grid.make_account(tier_name,cost['id'])
        return ExpansionAccount(plain.config,symbols=S,instrument_profiles=plain.instrument_profiles,
            closing_min_notional_exempt=True,generated_scope=generated_scope,historical_scope=historical_scope,
            tier_name=tier_name,settlement_mode=settlement_mode,policy_variant=policy_variant)
    constructor=V2._rebind(V2.native._construct_case,make_owned_account=factory,PartialTierGuard=ContinuationGuard)
    sim,guard=constructor(window,source_rows,decisions,targets,tier_name=tier_name,cost_name='BASE27',source_scope=scope)
    account=sim.account
    account.quantity_profile_binding='FROZEN_COARSE_RESEARCH_PROFILE'
    account._quality_intervals=tuple(quality_intervals)
    intervals=tuple(V2.quality_module.StaleMarkInterval(start_us=a,end_us=b,
        original_genuine_observation_us=original_genuine if original_genuine is not None else a-MINUTE,
        symbols=tuple(symbols)) for a,b,symbols in quality_intervals)
    quality=ContinuationQualityGuard(guard,intervals=intervals,source_sidecar_sha256=sidecar).install()
    guard.causal_mark_quality_guard=quality
    sim.meta.update(mark_quality_policy_identity=quality.policy_sha256,
        mark_quality_guard_version=V2.quality_module.VERSION,
        original_interpolated_mark_execution_admitted=False)
    if getattr(account.liquidation_callback,'__self__',None) is not sim:
        raise AssertionError('NATIVE_AFFECTED_PENDING_CANCELLATION_CALLBACK_REQUIRED')
    original_risk=sim.risk_schedule
    def risk_schedule(_sim,event_us):
        sameclock_next=(_sim.event_cursor<len(_sim.window['events']) and _sim.window['events'][_sim.event_cursor]['event_us']==event_us)
        if not sameclock_next and account.clock_us==event_us and event_us>account._noop_watermark:
            account.monitor('MONITOR:'+str(event_us),event_us)
        original_risk(event_us)
        if not _sim.terminal:
            for symbol,intent in tuple(account.pending_exits.items()):
                if not account.positions[symbol].quantity:
                    account.pending_exits.pop(symbol,None);continue
                existing=_sim.pending.get(symbol)
                if existing is None or existing['kind'] not in {'PROTECTIVE_STOP','TERMINAL'}:
                    guard.original_schedule(dict.fromkeys(S,DEC(0)),intent['signal_us'],'PROTECTIVE_STOP',(symbol,))
    sim.risk_schedule=MethodType(risk_schedule,sim)
    sim.meta.update(continuation_version=VERSION,policy_variant=policy_variant,
        settlement_mode=settlement_mode,noop_receipt_limit=V2.NOOP_RECEIPT_LIMIT,
        old_baselines_modified=False,frozen_D_rule_unchanged=True,
        historical_execution_admitted=historical_scope is not None,adaptive_DEV_only=True,
        nominal_tier_is_not_exact_realized_risk_matching=True)
    if historical_scope is not None:
        sim.meta.update(cell_id=historical_scope.cell_id,config=historical_scope.config,
            strategy=historical_scope.strategy,year=historical_scope.year)
    return sim,guard


def case_result(sim,guard):
    """Economic export; chronological saved-native proof is required separately.

    Preserve the original raw delta-sum diagnostic even when it is false from
    captured Decimal subtraction rounding. It is never changed to passed=True.
    The NEW controller must verify every native40 event before admitting a
    saved terminal. No financial state or old report is altered here.
    """
    result=V2.native.case_result(sim,guard);account=sim.account
    if account.transfer_journal:raise AssertionError('FROZEN_D_TRANSFERS_FORBIDDEN')
    report=account.economic_report()
    full=sim.stop is None and sim.rows_written==(sim.end-sim.start)//MINUTE
    paid=bool(full and report['paid_flat'])
    settled=bool(full and report['settled_flat_under_declared_model'])
    net=float(account.nav()/DEC(10000)-1)
    result['economics'].update(full_calendar=full,paid_flat=paid,actual_paid_market_flat=paid,
        conditional_settled_flat=settled and bool(account.settlement_journal),
        settled_flat_under_declared_model=settled,paid_net_return=net if paid else None,
        conditional_model_net_return=net if settled and account.settlement_journal else None,
        comparable_full_calendar_return=net if settled else None,
        halted_prefix_return=net if not full else None,actual_liquidation_fills=0,
        conditional_position_settlements=len(account.settlement_journal),
        liquidation_fill_model='CONDITIONAL_COLLATERAL_FORFEITURE_NOT_PAID_MARKET_LIQUIDATION',
        conditional_insurance_overshoot_absorption_USDT=report['conditional_insurance_overshoot_absorption_USDT'],
        conditional_NAV_adjustment_USDT=report['conditional_NAV_adjustment_USDT'],
        conditional_positive_residual_forfeited_USDT=str(sum((DEC(r['decimal_strings']['conditional_positive_residual_forfeited']) for r in account.settlement_journal),DEC(0))),
        actual_remaining_isolated_collateral_forfeited_USDT=str(sum((DEC(r['isolated_margin_lost']) for r in account.liquidations),DEC(0))),
        actual_paid_market_turnover_USDT=str(sum((DEC(r['decimal_strings']['quantity'])*DEC(r['decimal_strings']['fill_price']) for r in account.trades if not r.get('liquidation_takeover')),DEC(0))),
        conditional_takeover_notional_is_not_paid_market_turnover=True,
        transfers_are_internal_not_PnL=True,
        market_and_paid_cost_net_PnL_excluding_conditional_settlement_value=report['market_and_paid_cost_net_PnL_excluding_conditional_settlement_value'],
        native_settlement_certified=False,continuation_mode=account.mode(),cashwatch_counts=dict(account.mode_counts),
        comparison_scope='FIXED_D_ACROSS_ORIGINAL_CANDIDATES_TIERS_2023_2024_DEV',
        nominal_tier_is_not_exact_realized_risk_matching=True,adaptive_DEV_only=True)
    result['common_execution_policy'].update(version=VERSION,automatic_topup=False,
        policy_variant=POLICY_VARIANT,settlement_mode=account.settlement_mode,
        frozen_D_rule_SHA256=FROZEN_D_PINS['guard50_exit.py'],adaptive_DEV_only=True,
        nominal_tier_is_not_exact_realized_risk_matching=True,
        historical_execution_admitted=account._execution_scope is not None)
    legacy=V2.financial_reconciliation(account)
    result['primary_financial_reconciliation']=legacy
    result['legacy_primary_financial_reconciliation']=legacy
    result['legacy_delta_sum_reconciliation_is_authoritative']=False
    result['chronological_native40_saved_proof_required_before_terminal_admission']=True
    result['continuation_economic_report']=report
    return result
