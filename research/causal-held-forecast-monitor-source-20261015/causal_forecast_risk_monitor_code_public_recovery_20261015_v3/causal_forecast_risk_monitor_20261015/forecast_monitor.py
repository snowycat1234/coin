"""Separate causal MID held-forecast-risk paid-reduction adapter.

Generated/source-only admission. Exact pinned D/V2/native financial methods and
paid scheduler are reused; there is no historical account or restoration API.
"""
from collections import OrderedDict
from copy import deepcopy
from decimal import Decimal as DEC
from hashlib import sha256
import importlib.util
import math
from pathlib import Path
import sys
from types import MethodType

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
FROZEN = ROOT / 'bounded_native_continuation_guard50_exit_expansion_20261015'
PINS = {
    'expansion.py': 'd61235cc85902bb142da5812b7fe1f2368390bd76b27c7dac0943ba61b92457b',
    'expansion_entry.py': '1a0ba6f1c1a76a9a47897233012d309f4ecd81b12bca3e91e8b526c69d3e8628',
    'run_expansion.py': '085d58c293e35ab23d7eb28c70a31520f9721423d6b32c3090884adb1fbdd7de',
    'saved_native_reconciliation.py': 'd4df52de450b6c1a83801168e0bb8069bd3dd94d3058854fda971175bf6f5135',
}
for name, prefix in PINS.items():
    if sha256((FROZEN / name).read_bytes()).hexdigest() != prefix:
        raise ValueError('FROZEN_EXPANSION_SOURCE_PIN_MISMATCH:' + name)
_NAME = '_causal_forecast_exact_D_expansion'
if _NAME in sys.modules:
    E = sys.modules[_NAME]
    if Path(E.__file__).resolve() != (FROZEN / 'expansion.py').resolve():
        raise ValueError('CONFLICTING_FORECAST_D_IMPORT')
else:
    spec = importlib.util.spec_from_file_location(_NAME, FROZEN / 'expansion.py')
    E = importlib.util.module_from_spec(spec)
    sys.modules[_NAME] = E
    spec.loader.exec_module(E)
V2, S, MINUTE, GENERATED = E.V2, E.S, E.MINUTE, E.GENERATED
DAY = V2.grid.DAY
VERSION = 'SEPARATE_CAUSAL_HELD_FORECAST_MID_PAID_REDUCTION_V1'
BUDGET = .10
NEW_JOURNALS = ('forecast_journal', 'forecast_fill_journal')
PRIORITY = {'RISK_REDUCTION', 'PROTECTIVE_STOP', 'TERMINAL', 'POOL_EXIT', 'DATA_GAP_EXIT'}


def _variance(account, covariance, quantities=None):
    """Exactly native _tier_risk's marked-weight and float matrix arithmetic."""
    nav = account.nav()
    if nav <= 0:
        raise ValueError('NONPOSITIVE_NATIVE_NAV')
    q = ({s: account.positions[s].quantity for s in S}
         if quantities is None else quantities)
    w = np.asarray([float(q[s] * account._mark(s) / nav) for s in S])
    value = float(w @ covariance @ w)
    if not math.isfinite(value) or value < -1e-15:
        raise ValueError('INVALID_NATIVE_COVARIANCE_VARIANCE')
    return max(value, 0.)


def project_target(account, covariance):
    """One fixed proportional/floor projection; no optimizer or threshold grid."""
    c = V2.grid._covariance(covariance)
    current = V2.native._tier_risk(account, c, 'MID')
    sigma = current.get('sigma')
    variance = _variance(account, c)
    sigma = math.sqrt(variance) if sigma is None else float(sigma)
    actual = {s: account.positions[s].quantity for s in S}
    alpha = min(1., BUDGET / sigma) if sigma else 1.
    scale = DEC(str(alpha))
    target = {s: (DEC(1) if q >= 0 else DEC(-1)) * account._floor(s, abs(q)*scale)
              for s, q in actual.items()}
    projected = _variance(account, c, target)
    reduce_only = all(abs(target[s]) <= abs(actual[s]) and
                      (target[s] == 0 or target[s]*actual[s] > 0) for s in S)
    reason = ('BELOW_OR_AT_ORIGINAL_MID_BUDGET' if sigma <= BUDGET else
              'INFEASIBLE_COARSE_PROJECTION_NO_STRICT_VARIANCE_REDUCTION'
              if not reduce_only or not projected < variance else 'STRICT_COMPLETED_VARIANCE_REDUCTION')
    return dict(feasible=sigma > BUDGET and reduce_only and projected < variance,
                reason=reason, alpha=alpha, sigma=sigma,
                current_variance=variance, projected_variance=projected,
                target=target, actual=actual, native_current_risk=current)


def _export_cohort(active):
    if active is None:
        return None
    result = deepcopy(active)
    result['targets'] = {s: str(q) for s, q in active['targets'].items()}
    return result


class ForecastRiskAccount(E.ExpansionAccount):
    VERSION = VERSION

    def __init__(self, config=None, *, generated_scope=None, historical_scope=None,
                 tier_name='MID', **kwargs):
        if historical_scope is not None:
            raise ValueError('FORECAST_HISTORICAL_NO_GO_SOURCE_GENERATED_ONLY')
        if generated_scope != GENERATED or tier_name != 'MID':
            raise ValueError('FORECAST_GENERATED_ORIGINAL_MID_ONLY')
        super().__init__(config, generated_scope=generated_scope, tier_name='MID', **kwargs)
        for name in NEW_JOURNALS:
            object.__setattr__(self, name, V2.OWNED.PersistentList())
        self._forecast_cache = None
        self._forecast_active = None
        self._forecast_sequence = 0
        self._forecast_noops = OrderedDict()
        self._forecast_noop_watermark = -1
        self._forecast_noop_count = 0
        self._forecast_noop_commitment = '0'*64
        self._forecast_last_close = -1
        self._forecast_fill_sequence = 0
        self._forecast_infeasible_count = 0
        self._forecast_last_infeasible = None
        self._forecast_deferred_ordinary_reduction_count = 0

    def __setattr__(self, name, value):
        if name in NEW_JOURNALS and name in vars(self):
            raise TypeError('FORECAST_OWNED_HISTORY_REPLACEMENT_FORBIDDEN')
        super().__setattr__(name, value)

    def __delattr__(self, name):
        if name in NEW_JOURNALS:
            raise TypeError('FORECAST_OWNED_HISTORY_DELETION_FORBIDDEN')
        super().__delattr__(name)

    def contract_metadata(self):
        result = super().contract_metadata()
        result.update(integration_version=VERSION, continuation_policy=VERSION,
                      original_mid_forecast_budget=BUDGET,
                      no_autonomous_rerisking=True, automatic_topup=False,
                      historical_execution_admitted=False,
                      paid_partial_fills_atomic=False,
                      per_fill_variance_monotonicity_guaranteed=False)
        return result

    def preview_state_token(self):
        result = super().preview_state_token()
        for name in NEW_JOURNALS:
            result[name] = getattr(self, name).token()
        return result

    def execute_fill(self, *args, **kwargs):
        active = deepcopy(getattr(self, '_forecast_active', None))
        cache = getattr(self, '_forecast_cache', None)
        count = len(self.trades)
        before = None
        if active is not None and cache is not None and self.nav() > 0:
            before = _variance(self, V2.grid._covariance(cache['covariance']))
        result = super().execute_fill(*args, **kwargs)
        if len(self.trades) > count and active is not None:
            after = (None if cache is None or self.nav() <= 0 else
                     _variance(self, V2.grid._covariance(cache['covariance'])))
            self._forecast_fill_sequence += 1
            event = args[3] if len(args) > 3 else kwargs['event_us']
            self.forecast_fill_journal.append(dict(
                sequence=self._forecast_fill_sequence, event_us=event,
                cohort_id=active['cohort_id'],
                fill_id=args[5] if len(args) > 5 else kwargs['fill_id'],
                symbol=args[0] if args else kwargs['symbol'],
                variance_before=before, variance_after=after,
                variance_increased=(before is not None and after is not None and after > before),
                source_sha256=cache['source_sha256'] if cache else None,
                paid_fee_delta=str(sum((DEC(r['decimal_strings']['fee_amount']) for r in self.trades[count:]), DEC(0))),
                non_atomic_native_paid_execution=True))
        return result

    def _forecast_receipt(self, event_us, identity, result, *, changing=False):
        operation_id = 'FORECAST_MONITOR:' + str(event_us)
        if changing:
            self.operation_ids[operation_id] = dict(identity=V2.P._identity(identity), receipt=result)
        else:
            record = dict(identity=V2.P._identity(identity), receipt=deepcopy(result))
            self._forecast_noops[operation_id] = record
            self._forecast_noop_count += 1
            self._forecast_noop_watermark = event_us
            self._forecast_noop_commitment = sha256((self._forecast_noop_commitment +
                V2.P._identity((operation_id, record))).encode()).hexdigest()
            while len(self._forecast_noops) > 64:
                self._forecast_noops.popitem(last=False)
        return result

    def _forecast_replay(self, event_us, identity):
        operation_id = 'FORECAST_MONITOR:' + str(event_us)
        old = (self._forecast_noops.get(operation_id) or
               (self.operation_ids[operation_id] if operation_id in self.operation_ids else None))
        if old is not None:
            if old['identity'] != V2.P._identity(identity):
                raise ValueError('CONFLICTING_FORECAST_OPERATION_ID')
            return V2.OWNED.export_tree(old['receipt'])
        if event_us <= self._forecast_noop_watermark or event_us <= self._forecast_last_close:
            raise ValueError('EXPIRED_OR_REUSED_FORECAST_NOOP_REJECTED')
        return None

    def snapshot(self):
        result = super().snapshot()
        result.update(continuation_policy=VERSION,
                      forecast_journal=V2.OWNED.export_tree(self.forecast_journal),
                      forecast_fill_journal=V2.OWNED.export_tree(self.forecast_fill_journal),
                      forecast_active=_export_cohort(self._forecast_active),
                      forecast_cache=deepcopy(self._forecast_cache),
                      forecast_noop_count=self._forecast_noop_count,
                      deferred_ordinary_reduction_close_count=self._forecast_deferred_ordinary_reduction_count,
                      forecast_noop_receipts=deepcopy(list(self._forecast_noops.items())),
                      forecast_noop_rolling_SHA256=self._forecast_noop_commitment,
                      forecast_snapshot_recovery_certified=False)
        return result


class TokenView(E.TokenView):
    pass
TokenView.__init__ = V2._rebind(E.TokenView.__init__, ContinuationAccount=ForecastRiskAccount)


class CapitalView(TokenView):
    def snapshot(self):
        return V2.ExactToken(self._owned)

    def execute_fill(self, *args, **kwargs):
        return ForecastRiskAccount.execute_fill(self._owned, *args, **kwargs)


capital_guard_fill = V2._rebind(E.capital_guard_fill, CapitalView=CapitalView)
fresh_preview = V2._rebind(E.fresh_preview, TokenView=TokenView)
signal_preview = V2._rebind(E.signal_preview, TokenView=TokenView)


class ForecastRiskGuard(E.ContinuationGuard):
    def schedule(self, target, signal, kind, only_symbols=None):
        result = self._frozen_schedule(target, signal, kind, only_symbols)
        controller = getattr(self.sim, 'forecast_controller', None)
        if controller is not None:
            controller.after_strategy_schedule(target, int(signal), kind, only_symbols)
        return result

    def attempt(self, open_us, market_row):
        result = E.ContinuationGuard.attempt(self, open_us, market_row)
        controller = getattr(self.sim, 'forecast_controller', None)
        if controller is not None:
            controller.after_attempt(int(open_us)+1)
        return result


ForecastRiskGuard._frozen_schedule = V2._rebind(E.ContinuationGuard.schedule,
                                               signal_preview=signal_preview)
ForecastRiskGuard._frozen_attempt = V2._rebind(E.ContinuationGuard._frozen_attempt,
    signal_preview=signal_preview, fresh_preview=fresh_preview, capital_guard_fill=capital_guard_fill)


class ForecastQualityGuard(E.ContinuationQualityGuard):
    pass
ForecastQualityGuard.install = V2._rebind(E.ContinuationQualityGuard.install,
                                         ContinuationGuard=ForecastRiskGuard)


class ForecastRiskController:
    """Small native-scheduler intent controller, never a second backtester."""
    def __init__(self, sim, guard):
        self.sim, self.guard, self.account = sim, guard, sim.account

    def _finish(self, event_us, reason):
        a = self.account
        active = a._forecast_active
        if active is None:
            return
        a.forecast_journal.append(dict(kind=reason, event_us=event_us,
            cohort_id=active['cohort_id'], born_us=active['born_us'],
            delay_us=event_us-active['born_us'],
            remaining_quantities={s: str(a.positions[s].quantity) for s in S},
            targets={s: str(q) for s, q in active['targets'].items()}))
        a.operation_ids['FORECAST_FINISH:' + active['cohort_id'] + ':' + str(event_us)] = dict(
            identity=reason, receipt=dict(event_us=event_us, cohort_id=active['cohort_id'], reason=reason))
        a._forecast_active = None

    def after_strategy_schedule(self, target, signal, kind, only_symbols=None):
        active = self.account._forecast_active
        if active is None:
            return
        symbols = S if only_symbols is None else tuple(only_symbols)
        kinds = {s: kind[s] if isinstance(kind, dict) else kind for s in symbols}
        if any(k == 'TERMINAL' for k in kinds.values()):
            self._finish(signal, 'SUPERSEDED_BY_NATIVE_TERMINAL')
        elif signal >= active['born_us'] and any(k == 'DAILY_TARGET' for k in kinds.values()):
            self._finish(signal, 'SUPERSEDED_BY_GENUINE_NEW_STRATEGY_SIGNAL')

    def _target_reached(self, symbol, target):
        q = self.account.positions[symbol].quantity
        return q == 0 or target*q > 0 and abs(q) <= abs(target)

    def _route(self, symbols, event_us, *, renewal=False):
        a, sim, active = self.account, self.sim, self.account._forecast_active
        if not symbols or active is None or sim.terminal or sim.stop is not None:
            return
        # Native RISK_REDUCTION expects a matching breach witness for its paid
        # first-fill latency. Its financial execution method remains unchanged.
        sim.breaches.append(dict(signal_us=event_us,
            phase='CAUSAL_HELD_FORECAST_PAID_REDUCTION',
            scale=active['alpha'], cohort_id=active['cohort_id'], renewal=renewal))
        self.guard.original_schedule(active['targets'], event_us, 'RISK_REDUCTION', tuple(symbols))
        for s in symbols:
            active['orders'][s] = dict(order_id=sim.pending[s]['order_id'], signal_us=event_us)
        if renewal:
            active['renewals'] += 1
            identity = 'FORECAST_RENEW:' + active['cohort_id'] + ':' + str(event_us)
            record = dict(kind='RENEWED_AFTER_FIVE_NATIVE_OPENS', event_us=event_us,
                cohort_id=active['cohort_id'], symbols=list(symbols),
                renewals=active['renewals'], delay_us=event_us-active['born_us'],
                new_native_latency_required=True)
            a.forecast_journal.append(record)
            a.operation_ids[identity] = dict(identity=identity, receipt=record)

    def before_native_risk(self, event_us):
        """Do not let our native-kind orders mask a later native hard cap.

        The unchanged native cap reducer returns on any RISK_REDUCTION. Only
        exact owned forecast orders are cancelled here, then the original
        native/D hook is allowed to generate its stronger protection normally.
        """
        a, sim = self.account, self.sim
        active = a._forecast_active
        if active is None or a.status != 'BOUND_BREACH_REDUCTION_REQUIRED' or sim.terminal:
            return
        for symbol, owned in tuple(active['orders'].items()):
            pending = sim.pending.get(symbol)
            if (pending is not None and pending['kind'] == 'RISK_REDUCTION' and
                    pending['order_id'] == owned['order_id']):
                sim.pending.pop(symbol)
                sim.rejections.append(dict(symbol=symbol, event_us=event_us,
                    order_id=owned['order_id'], reason='FORECAST_SUPERSEDED_BY_LATE_NATIVE_HARD_CAP',
                    old_signal_us=pending['signal_us']))
        self._finish(event_us, 'SUPERSEDED_BY_LATE_NATIVE_HARD_CAP')

    def after_attempt(self, event_us):
        a, sim = self.account, self.sim
        active = a._forecast_active
        if active is None or sim.stop is not None or a.status in V2.P.HALTS:
            return
        if sim.terminal:
            self._finish(event_us, 'SUPERSEDED_BY_NATIVE_TERMINAL')
            return
        remaining, renew = [], []
        for s, target in active['targets'].items():
            if self._target_reached(s, target):
                continue
            remaining.append(s)
            order = sim.pending.get(s)
            owned = active['orders'].get(s)
            if order is None and owned is not None:
                # Only the exact native expiry record permits renewal. No new
                # close, external cancellation or fill failure resets latency.
                expired = any(r.get('order_id') == owned['order_id'] and
                              r.get('reason') == 'FIVE_ATTEMPTS_EXPIRED'
                              for r in reversed(sim.rejections))
                if expired:
                    renew.append(s)
            elif order is not None and (owned is None or order['order_id'] != owned['order_id']):
                if order['kind'] in PRIORITY:
                    # A stronger existing native/D order owns this instrument.
                    active['targets'][s] = (order['target'] if abs(order['target']) <= abs(target) else target)
                    active['orders'].pop(s, None)
        if not remaining:
            self._finish(event_us, 'COMPLETED_NATIVE_PAID_TARGET')
        else:
            self._route(renew, event_us, renewal=True)

    def _binding(self, event_us):
        a = self.account
        original_clock = event_us // DAY * DAY
        if a._forecast_cache is None or a._forecast_cache['binding_signal_us'] != original_clock:
            binding = self.guard.source.bind(original_clock)
            c = V2.grid._covariance(binding.covariance)
            if binding.covariance_available_us > original_clock or original_clock > event_us:
                raise ValueError('PAST_ORIGINAL_COVARIANCE_CLOCK_REQUIRED')
            a._forecast_cache = dict(binding_signal_us=binding.signal_us,
                covariance_available_us=binding.covariance_available_us,
                source_sha256=binding.source_sha256,
                covariance=tuple(tuple(float(x) for x in row) for row in c))
        return a._forecast_cache

    def after_native_risk(self, event_us):
        a, sim = self.account, self.sim
        event_us = V2.P.timestamp(event_us)
        if (sim.event_cursor < len(sim.window['events']) and
                sim.window['events'][sim.event_cursor]['event_us'] == event_us):
            return None
        # Funding at arbitrary microseconds and interim callbacks cannot create
        # an extra monitor tick. Only existing actual completed-close marks do.
        if (event_us % MINUTE or a.clock_us != event_us or
                not all(a.marks[s] and a.marks[s][-1]['close_us'] == event_us and
                        a.marks[s][-1]['available_us'] <= event_us for s in S)):
            return None
        identity = dict(kind='FORECAST_MONITOR', event_us=event_us)
        replay = a._forecast_replay(event_us, identity)
        if replay is not None:
            return replay
        a._forecast_last_close = event_us
        result = dict(event_us=event_us, action='HOLD', reason=None)
        if sim.terminal or sim.stop is not None:
            result['reason'] = 'NATIVE_TERMINAL_OR_STOP_PRIORITY'
        elif a.status in V2.P.HALTS or a.unpaid_liability or a.nav() <= 0:
            result['reason'] = 'GENUINE_DEBT_OR_NATIVE_HALT_NO_RESUME'
        elif not all(a._known_fresh(s, event_us) for s in S):
            result['reason'] = 'UNKNOWN_DERIVED_OR_STALE_NO_NEW_MONITOR_ACTION'
        elif a._forecast_active is not None:
            result.update(reason='OWNED_ACTIVE_COHORT_NO_DUPLICATE_RESIGNAL',
                          cohort_id=a._forecast_active['cohort_id'])
        elif any(o['kind'] in PRIORITY for o in sim.pending.values()):
            result['reason'] = 'EXISTING_NATIVE_OR_D_PRIORITY_PRESERVED'
        elif any(o['kind'] not in PRIORITY and a.positions[s].quantity != 0 and
                 a.positions[s].quantity*(o['target']-a.positions[s].quantity) < 0
                 for s,o in sim.pending.items()):
            # Preserve the original ordinary CLOSE/reduction lifecycle exactly,
            # including a reversal's legitimate CLOSE and guarded later OPEN.
            # No order is replaced/backdated/cancelled and no capacity is used.
            a._forecast_deferred_ordinary_reduction_count += 1
            result.update(reason='DEFERRED_EXISTING_ORDINARY_REDUCTION_OR_REVERSAL_CLOSE_PRESERVE_NATIVE_TIMING',
                deferred_pending=[dict(symbol=s,order_id=o['order_id'],signal_us=o['signal_us'],
                    attempts=o['attempts'],kind=o['kind'],target=str(o['target']))
                    for s,o in sim.pending.items() if o['kind'] not in PRIORITY and
                    a.positions[s].quantity != 0 and
                    a.positions[s].quantity*(o['target']-a.positions[s].quantity) < 0])
        else:
            try:
                cache = self._binding(event_us)
                projection = project_target(a, cache['covariance'])
            except (ValueError, RuntimeError) as error:
                result['reason'] = 'CAUSAL_SOURCE_OR_VARIANCE_UNAVAILABLE:' + str(error)
            else:
                result.update(reason=projection['reason'], sigma=projection['sigma'],
                    current_variance=projection['current_variance'],
                    projected_variance=projection['projected_variance'],
                    alpha=projection['alpha'], source_sha256=cache['source_sha256'],
                    binding_signal_us=cache['binding_signal_us'],
                    covariance_available_us=cache['covariance_available_us'])
                if projection['feasible']:
                    a._forecast_sequence += 1
                    cohort_id = 'FORECAST_COHORT:' + str(a._forecast_sequence) + ':' + str(event_us)
                    a._forecast_active = dict(cohort_id=cohort_id, born_us=event_us,
                        targets=projection['target'], alpha=projection['alpha'],
                        projected_variance=projection['projected_variance'],
                        current_variance=projection['current_variance'],
                        source_sha256=cache['source_sha256'], orders={}, renewals=0)
                    symbols = list(S)
                    self._route(symbols, event_us)
                    result.update(action='NATIVE_PAID_REDUCTION_INTENT', cohort_id=cohort_id,
                                  target={s: str(q) for s, q in projection['target'].items()})
                    a.forecast_journal.append(dict(kind='COHORT_CREATED', **result))
                    return a._forecast_receipt(event_us, identity, result, changing=True)
                if projection['sigma'] > BUDGET:
                    a._forecast_infeasible_count += 1
                    signature = (cache['source_sha256'],
                        tuple(str(projection['actual'][s]) for s in S),
                        tuple(str(projection['target'][s]) for s in S))
                    if signature != a._forecast_last_infeasible:
                        a._forecast_last_infeasible = signature
                        a.forecast_journal.append(dict(kind='LOT_PROJECTION_INFEASIBLE', **result))
                        return a._forecast_receipt(event_us, identity, result, changing=True)
        return a._forecast_receipt(event_us, identity, result)


_construct_D_generated = V2._rebind(E.construct_case, ExpansionAccount=ForecastRiskAccount,
    ContinuationGuard=ForecastRiskGuard, ContinuationQualityGuard=ForecastQualityGuard)


def construct_case(window, source_rows, decisions, targets, *, generated_scope=None,
                   historical_scope=None, quality_intervals=()):
    if historical_scope is not None:
        raise ValueError('FORECAST_HISTORICAL_NO_GO_SOURCE_GENERATED_ONLY')
    if generated_scope != GENERATED or window.get('fixture_scope') != GENERATED:
        raise ValueError('FORECAST_EXPLICIT_GENERATED_FIXTURE_REQUIRED')
    sim, guard = _construct_D_generated(window, source_rows, decisions, targets,
        tier_name='MID', generated_scope=generated_scope, quality_intervals=quality_intervals)
    controller = ForecastRiskController(sim, guard)
    sim.forecast_controller = controller
    original_risk = sim.risk_schedule
    def risk_schedule(_sim, event_us):
        controller.before_native_risk(event_us)
        original_risk(event_us)
        return controller.after_native_risk(event_us)
    sim.risk_schedule = MethodType(risk_schedule, sim)
    sim.meta.update(forecast_monitor_version=VERSION, original_mid_budget=BUDGET,
        historical_execution_admitted=False, no_autonomous_rerisking=True,
        completed_projection_strict_variance_reduction_required=True,
        partial_fill_variance_monotonicity_guaranteed=False)
    return sim, guard


def case_result(sim, guard):
    result = E.case_result(sim, guard)
    a = sim.account
    result['common_execution_policy'].update(version=VERSION,
        forecast_risk_monitor=True, original_mid_forecast_budget=BUDGET,
        historical_execution_admitted=False, no_autonomous_rerisking=True)
    result['economics']['comparison_scope'] = 'SEPARATE_CAUSAL_FORECAST_MID_PAID_REDUCER_DEV_ONLY'
    result['forecast_risk_monitor'] = dict(version=VERSION, original_mid_budget=BUDGET,
        no_autonomous_rerisking=True, automatic_topup=False,
        historical_execution_admitted=False,
        completed_projection_strict_variance_reduction_required=True,
        partial_fills_atomic=False, per_fill_variance_monotonicity_guaranteed=False,
        journal=V2.OWNED.export_tree(a.forecast_journal),
        paid_fill_variance_journal=V2.OWNED.export_tree(a.forecast_fill_journal),
        pending_cohort=_export_cohort(a._forecast_active),
        noop_count=a._forecast_noop_count, retained_noop_receipts=len(a._forecast_noops),
        noop_rolling_SHA256=a._forecast_noop_commitment,
        infeasible_close_count=a._forecast_infeasible_count,
        deferred_ordinary_reduction_close_count=a._forecast_deferred_ordinary_reduction_count,
        historical_control_reruns=0,
        future_control_policy='EXACT_EXISTING_OPEN_ONLY_CONTROLS_REQUIRE_IDENTITY_VERIFIED_REUSE')
    return result
