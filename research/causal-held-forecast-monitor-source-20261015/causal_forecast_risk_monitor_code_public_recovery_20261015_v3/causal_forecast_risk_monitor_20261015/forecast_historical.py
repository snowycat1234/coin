"""Separately sealed, fresh-genesis historical transport; never invoked on import.

Only forecast_entry.make_case can produce its scope after exact external GO and
independent review. The public generated constructor never accepts this scope.
"""
from collections import OrderedDict
from types import MethodType
from pathlib import Path
import forecast_monitor as F
import forecast_entry as entry

V2, E, S, DEC, MINUTE = F.V2, F.E, F.S, F.DEC, F.MINUTE
if (Path(F.__file__).resolve()!=Path(__file__).resolve().parent/'forecast_monitor.py'
        or Path(entry.__file__).resolve()!=Path(__file__).resolve().parent/'forecast_entry.py'):
    raise ValueError('EXACT_LOCAL_FORECAST_MONITOR_AND_ENTRY_REQUIRED')
VERSION, POLICY_VARIANT = F.VERSION, entry.POLICY_VARIANT


class HistoricalForecastRiskAccount(F.ForecastRiskAccount):
    def __init__(self, config=None, *, historical_scope, generated_scope=None, **kwargs):
        if generated_scope is not None or type(historical_scope) is not entry.ForecastExecutionScope:
            raise ValueError('EXACT_REVIEWED_FOUR_CELL_HISTORICAL_SCOPE_REQUIRED')
        historical_scope.validate_current()
        expected = V2.grid.make_account('MID','BASE27')
        if (config != expected.config or tuple(kwargs.get('symbols',())) != S
                or kwargs.get('instrument_profiles') != expected.instrument_profiles
                or kwargs.get('closing_min_notional_exempt') is not True
                or historical_scope.tier_name != 'MID'):
            raise ValueError('EXACT_FRESH_ORIGINAL_MID_BASE27_COARSE_GENESIS_REQUIRED')
        V2.P.verify_primitives()
        self.generated_scope = None
        self._settlement_mode = F.E.SETTLEMENT
        self._policy_variant = POLICY_VARIANT
        self._policy_enabled = True
        self._topup_enabled = False
        self.transfer_journal=[]; self.monitor_journal=[]; self.settlement_journal=[]
        self.operation_ids={}; self.pending_exits={}; self.capacity_used={}
        self.capacity_registrations={}; self.transfer_ids={}; self.cash_watch_reason=None
        self.liquidations=[]; self.blocked_signals={}; self.liquidation_callback=None
        self._exact_closing=None; self.mark_quality={}
        self.quantity_profile_binding='FROZEN_COARSE_RESEARCH_PROFILE'
        # Deliberately direct native fresh genesis: no generated flag, no old
        # account, no snapshot, and no historical call to a generated constructor.
        V2.ENGINE.USDTLinearPerpetualAccount.__init__(self,config,**kwargs)
        if self.config.initial_cash != DEC(10000):
            raise ValueError('FRESH_SHARED_10000_REQUIRED')
        self._execution_scope=historical_scope
        self.financial_ledger=[]; self.mode_journal=[]
        for name in V2.LISTS:
            object.__setattr__(self,name,V2.OWNED.PersistentList(getattr(self,name)))
        for name in V2.MAPS:
            object.__setattr__(self,name,V2.IdentityMap(getattr(self,name)))
        self._noop_receipts=OrderedDict(); self._noop_watermark=-1
        self._noop_count=0; self._noop_commitment='0'*64
        self._capture_depth=0; self._financial_sequence=0
        self._signal_projection_clock=None; self._last_mode=None; self.mode_counts={}
        self._quality_intervals=tuple(historical_scope.quality_intervals)
        self._historical_scope_metadata=dict(historical_scope.metadata)
        self._bound_tier_name='MID'
        for name in F.NEW_JOURNALS:
            object.__setattr__(self,name,V2.OWNED.PersistentList())
        self._forecast_cache=None; self._forecast_active=None; self._forecast_sequence=0
        self._forecast_noops=OrderedDict(); self._forecast_noop_watermark=-1
        self._forecast_noop_count=0; self._forecast_noop_commitment='0'*64
        self._forecast_last_close=-1; self._forecast_fill_sequence=0
        self._forecast_infeasible_count=0; self._forecast_last_infeasible=None
        self._forecast_deferred_ordinary_reduction_count=0

    def contract_metadata(self):
        result=super().contract_metadata()
        result.update(historical_execution_admitted=True,generated_only=False,
                      scope_binding=self._historical_scope_metadata)
        return result


class HistoricalTokenView(F.TokenView):
    pass
HistoricalTokenView.__init__=V2._rebind(F.TokenView.__init__,ContinuationAccount=HistoricalForecastRiskAccount)


class HistoricalCapitalView(HistoricalTokenView):
    def snapshot(self):
        return V2.ExactToken(self._owned)
    def execute_fill(self,*args,**kwargs):
        return HistoricalForecastRiskAccount.execute_fill(self._owned,*args,**kwargs)


capital_guard_fill=V2._rebind(F.capital_guard_fill,CapitalView=HistoricalCapitalView)
fresh_preview=V2._rebind(F.fresh_preview,TokenView=HistoricalTokenView)
signal_preview=V2._rebind(F.signal_preview,TokenView=HistoricalTokenView)


class HistoricalForecastGuard(F.ForecastRiskGuard):
    pass
HistoricalForecastGuard._frozen_schedule=V2._rebind(F.ForecastRiskGuard._frozen_schedule,signal_preview=signal_preview)
HistoricalForecastGuard._frozen_attempt=V2._rebind(F.ForecastRiskGuard._frozen_attempt,
    signal_preview=signal_preview,fresh_preview=fresh_preview,capital_guard_fill=capital_guard_fill)


class HistoricalQualityGuard(F.ForecastQualityGuard):
    pass
HistoricalQualityGuard.install=V2._rebind(F.ForecastQualityGuard.install,ContinuationGuard=HistoricalForecastGuard)


def construct_historical_case(window,source_rows,decisions,targets,*,historical_scope,
                              quality_intervals=(),generated_scope=None):
    if generated_scope is not None or type(historical_scope) is not entry.ForecastExecutionScope:
        raise ValueError('EXACT_SEALED_FOUR_CELL_FORECAST_HISTORICAL_SCOPE_REQUIRED')
    historical_scope.validate_current()
    historical_scope.validate_inputs(window,source_rows,decisions,targets)
    if quality_intervals != historical_scope.quality_intervals:
        raise ValueError('EXACT_YEAR_BOUND_FORECAST_CAUSAL_QUALITY_SIDECAR_REQUIRED')
    def factory(tier_name,cost):
        if tier_name!='MID' or cost['id']!='BASE27':
            raise ValueError('ONLY_ORIGINAL_MID_BASE27_ALLOWED')
        plain=V2.grid.make_account('MID','BASE27')
        return HistoricalForecastRiskAccount(plain.config,symbols=S,
            instrument_profiles=plain.instrument_profiles,closing_min_notional_exempt=True,
            historical_scope=historical_scope)
    constructor=V2._rebind(V2.native._construct_case,
        make_owned_account=factory,PartialTierGuard=HistoricalForecastGuard)
    sim,guard=constructor(window,source_rows,decisions,targets,tier_name='MID',cost_name='BASE27',
        source_scope=historical_scope.source_scope)
    a=sim.account
    intervals=tuple(V2.quality_module.StaleMarkInterval(start_us=start,end_us=end,
        original_genuine_observation_us=historical_scope.original_genuine_observation_us,
        symbols=tuple(symbols)) for start,end,symbols in quality_intervals)
    quality=HistoricalQualityGuard(guard,intervals=intervals,
        source_sidecar_sha256=historical_scope.quality_sidecar_sha256).install()
    guard.causal_mark_quality_guard=quality
    if getattr(a.liquidation_callback,'__self__',None) is not sim:
        raise AssertionError('NATIVE_AFFECTED_PENDING_CANCELLATION_CALLBACK_REQUIRED')
    native_risk=sim.risk_schedule
    controller=F.ForecastRiskController(sim,guard)
    sim.forecast_controller=controller
    def risk_schedule(_sim,event_us):
        controller.before_native_risk(event_us)
        sameclock_next=(_sim.event_cursor<len(_sim.window['events']) and
            _sim.window['events'][_sim.event_cursor]['event_us']==event_us)
        if not sameclock_next and a.clock_us==event_us and event_us>a._noop_watermark:
            a.monitor('MONITOR:'+str(event_us),event_us)
        native_risk(event_us)
        if not _sim.terminal:
            for symbol,intent in tuple(a.pending_exits.items()):
                if not a.positions[symbol].quantity:
                    a.pending_exits.pop(symbol,None);continue
                existing=_sim.pending.get(symbol)
                if existing is None or existing['kind'] not in {'PROTECTIVE_STOP','TERMINAL'}:
                    guard.original_schedule(dict.fromkeys(S,DEC(0)),intent['signal_us'],'PROTECTIVE_STOP',(symbol,))
        return controller.after_native_risk(event_us)
    sim.risk_schedule=MethodType(risk_schedule,sim)
    sim.meta.update(continuation_version=VERSION,forecast_monitor_version=VERSION,
        policy_variant=POLICY_VARIANT,settlement_mode=E.SETTLEMENT,
        mark_quality_policy_identity=quality.policy_sha256,mark_quality_guard_version=V2.quality_module.VERSION,
        original_interpolated_mark_execution_admitted=False,historical_execution_admitted=True,
        generated_fixture_scope_used=False,old_baselines_modified=False,frozen_D_rule_unchanged=True,
        adaptive_DEV_only=True,original_mid_budget=F.BUDGET,no_autonomous_rerisking=True,
        completed_projection_strict_variance_reduction_required=True,
        partial_fill_variance_monotonicity_guaranteed=False,
        cell_id=historical_scope.cell_id,config=historical_scope.config,
        strategy=historical_scope.strategy,year=historical_scope.year)
    return sim,guard


def case_result(sim,guard):
    if type(sim.account) is not HistoricalForecastRiskAccount:
        raise ValueError('EXACT_HISTORICAL_FORECAST_ACCOUNT_REPORT_REQUIRED')
    result=F.case_result(sim,guard)
    result['common_execution_policy']['historical_execution_admitted']=True
    result['forecast_risk_monitor']['historical_execution_admitted']=True
    result['forecast_risk_monitor']['generated_fixture_scope_used']=False
    return result
