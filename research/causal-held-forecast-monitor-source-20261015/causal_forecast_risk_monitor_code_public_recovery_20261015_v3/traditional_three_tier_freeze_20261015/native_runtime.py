"""Explicit offline tier binding of exact native scheduler, finance and v4 seam.

The small dependency façades below are declared transport/config adapters, not
claims that the full original repository runtime has been restored. Source
files are never rewritten. No live venue or locked-data access is implemented.
"""
from __future__ import annotations
from copy import deepcopy
from dataclasses import replace
from decimal import Decimal as D
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import sys
from types import MethodType, ModuleType

import numpy as np
import polars as pl
import frozen_grid as g

HERE = Path(__file__).resolve().parent
MINUTE, DAY, S = 60_000_000, g.DAY, g.SYMBOLS
NATIVE_SOURCE_PROVENANCE_SHA256 = 'a8a59ba72e61cab35f4bd84da1f09f5a3d0052fcaa3effba819d93f4b102f1fb'
VERSION = 'FIXED_THREE_TIER_PARTIAL_SIGNAL_AND_FRESH_REPLACEMENT_MARK_PRESERVING_TERMINAL60_V3'


def _verify_native():
    g.verify_sources()
    b = (HERE / 'NATIVE_SOURCE_PROVENANCE.json').read_bytes()
    if hashlib.sha256(b).hexdigest() != NATIVE_SOURCE_PROVENANCE_SHA256:
        raise ValueError('NATIVE_SOURCE_MANIFEST_CHANGED')
    for row in json.loads(b):
        p = HERE / row['path']
        if p.is_symlink() or not p.is_file():
            raise ValueError('ORDINARY_NATIVE_PUBLIC_SOURCE_REQUIRED')
        raw = p.read_bytes()
        if len(raw) != row['bytes'] or hashlib.sha256(raw).hexdigest() != row['SHA256']:
            raise ValueError('NATIVE_PUBLIC_SOURCE_BYTES_CHANGED')


def _load(name, filename):
    if name in sys.modules:
        module = sys.modules[name]
        if getattr(module, '__file__', None) != str(HERE / 'sources' / filename):
            raise ValueError('CONFLICTING_NATIVE_OFFLINE_IMPORT:' + name)
        return module
    spec = importlib.util.spec_from_file_location(name, HERE / 'sources' / filename)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _facade(name, **values):
    if name in sys.modules:
        raise ValueError('EXISTING_MODULE_NOT_REBOUND:' + name)
    m = ModuleType(name)
    m.__dict__.update(values)
    m.__offline_tier_binding__ = VERSION
    sys.modules[name] = m
    return m


def need(condition, message):
    if not bool(condition):
        raise ValueError(message)


def _scenario_config(cost):
    expected = {'BASE27': (4, 27), 'STRESS43': (8, 43)}
    if cost.get('id') not in expected:
        raise ValueError('FIXED_BASE27_OR_STRESS43_REQUIRED')
    friction, rt = expected[cost['id']]
    if cost != dict(id=cost['id'], half_spread_bps=friction, slippage_bps=friction, roundtrip_bps=rt):
        raise ValueError('EXACT_COMMON_COST_FIELDS_REQUIRED')
    return g._vendor().PerpetualConfig(half_spread_bps=str(friction), slippage_bps=str(friction))


def _account_for_cost(cost, symbols, factory):
    return factory(_scenario_config(cost), symbols=tuple(symbols))


_RUNTIME = None


def runtime():
    """Load an explicit, source-verified offline runtime once per process."""
    global _RUNTIME
    if _RUNTIME is not None:
        return _RUNTIME
    _verify_native()
    engine = g._vendor()
    # Exact public scheduler imports are mapped to these declared bounded
    # offline APIs. The actual account and clock classes are the exact vendor
    # classes, while unused default strategy construction is disabled.
    quant = _facade('quant', __path__=[])
    quant.execution_contract = sys.modules[engine.__package__ + '.execution_contract']
    sys.modules['quant.execution_contract'] = quant.execution_contract
    quant.perpetual_account = engine
    sys.modules['quant.perpetual_account'] = engine
    _facade('vendor_quant', __path__=[])
    sys.modules['vendor_quant.perpetual_account'] = engine
    _facade('scripts', __path__=[])
    _facade('scripts.investment', __path__=[])
    def no_default(*args, **kwargs):
        raise ValueError('EXPLICIT_FIXED_NINE_TARGET_FACTORY_REQUIRED')
    _facade('scripts.investment.public_sma_perpetual', SYMBOLS=S,
        symbol_order=g.originals().symbol_order, fixed_targets=no_default)
    _facade('scripts.investment.bybit_cost_inputs', account_for_cost=_account_for_cost)
    _facade('scripts.investment.perpetual_directional', MINUTE=MINUTE, DAY=DAY, need=need)
    scheduler = _load('scripts.investment.resumable_perpetual', 'native_scheduler.py')
    terminal = _load('_three_tier_terminal60', 'terminal_adapter.py')
    # Existing persistent journal algorithms are reused with this explicitly
    # different base class binding. No historical/native identity is inherited.
    _facade('fine_account', FineGridAccount=engine.USDTLinearPerpetualAccount)
    _load('candidate', 'candidate.py')
    _load('native_preview', 'native_preview.py')
    causal = _load('causal_adapter', 'causal_adapter.py')
    shared = _load('shared_journal_preview', 'shared_journal_preview.py')
    owned = _load('owned_journals', 'owned_journals.py')
    _load('_three_tier_original_capital_policy', 'bounded_policy.py')
    _RUNTIME = (engine, scheduler, terminal, shared, owned, causal)
    return _RUNTIME


def make_owned_account(tier_name, cost):
    tier = g.tier_named(tier_name)
    _scenario_config(cost)
    engine, _, _, _, owned, _ = runtime()
    plain = g.make_account(tier_name, cost['id'])
    return owned.OwnedFineGridAccount(plain.config, symbols=S,
        instrument_profiles=plain.instrument_profiles, closing_min_notional_exempt=True)


class _TokenView:
    def __init__(self, account):
        owned = runtime()[4]
        if type(account) is not owned.OwnedFineGridAccount:
            raise TypeError('EXPLICIT_OFFLINE_OWNED_TIER_ACCOUNT_REQUIRED')
        account.preview_state_token()
        self._owned = account
    def __getattr__(self, name):
        return getattr(object.__getattribute__(self, '_owned'), name)
    def __deepcopy__(self, memo):
        result = object.__new__(type(self)); memo[id(self)] = result
        result._owned = runtime()[4].fork_owned_account(self._owned, memo=memo)
        return result
    def snapshot(self):
        return self._owned.preview_state_token()


def _tier_risk(probe, covariance, tier_name):
    tier = g.tier_named(tier_name)
    if (probe.config.max_gross_weight != D(str(tier.gross_cap))
            or probe.config.max_asset_weight != D('.30') or probe.config.leverage != 1):
        raise ValueError('ACCOUNT_TIER_AND_PREVIEW_TIER_MUST_MATCH')
    nav = probe.nav()
    if nav <= 0:
        return {'valid': False, 'reason': 'NONPOSITIVE_CHARGED_NAV'}
    w = np.asarray([float(probe.positions[s].quantity * probe._mark(s) / nav) for s in S])
    variance = float(w @ covariance @ w)
    if not math.isfinite(variance) or variance < -1e-15:
        return {'valid': False, 'reason': 'INVALID_CHARGED_COVARIANCE_RISK'}
    gross, asset, sigma = float(abs(w).sum()), float(abs(w).max()), math.sqrt(max(variance, 0.))
    isolated = sum((p.isolated_balance for p in probe.positions.values()), D(0))
    capital_valid = probe.free_cash >= D(1000) and isolated <= D(8500)
    return {'valid': gross <= tier.gross_cap + 1e-12 and asset <= .30 + 1e-12
        and sigma <= tier.annual_vol_target + 1e-12 and capital_valid, 'gross': gross,
        'max_asset': asset, 'sigma': sigma, 'charged_NAV': str(nav),
        'free_cash': str(probe.free_cash), 'tier': tier_name,
        'isolated_margin': str(isolated), 'common_capital_guard_valid': capital_valid,
        'common_cash_floor': '1000', 'common_isolated_margin_ceiling': '8500',
        'actual_executed_positions': {s: str(probe.positions[s].quantity) for s in S}}


def fresh_preview(account, *, tier_name, **kwargs):
    """Exact v4 corner enumeration/charged finance, explicit tier thresholds."""
    base = runtime()[5].FreshExecutionPreview
    class TierFreshPreview(base):
        def _risk(self, probe):
            return _tier_risk(probe, self.cov, tier_name)
        def evaluate(self, target, lam):
            witness = super().evaluate(target, lam)
            if witness.get('reason') == 'CHARGED_ACTUAL_PENDING_060_030_010_CAP':
                witness['reason'] = 'CHARGED_ACTUAL_PENDING_' + tier_name + '_TIER_CAP'
            return witness
        def _charged(self, target, tag):
            probe, witness = super()._charged(target, tag)
            return (probe._owned if probe is not None else None), witness
    preview = TierFreshPreview(_TokenView(account), **kwargs)
    # The public FreshExecutionPreview does not check account gross config in
    # its constructor. Bind it explicitly before evaluating ANY corner.
    tier = g.tier_named(tier_name)
    if account.config.max_gross_weight != D(str(tier.gross_cap)):
        raise ValueError('ACCOUNT_TIER_AND_PREVIEW_TIER_MUST_MATCH')
    return preview


def signal_preview(account, binding, quote, quote_us, *, tier_name, admission_us):
    """Original charged signal preview with explicit tier/capital parameters.

    At the one fresh-flat cold start only, a detached probe receives the bound
    completed-source prices as risk observations. The real mark ledger remains
    untouched, and the new capacity is only the first real completed quote.
    """
    _, _, _, _, owned, causal = runtime()
    clone = owned.fork_owned_account(account)
    if not any(clone.positions[s].quantity for s in S):
        missing = {s: dict(price=D(binding.prices[i]), close_us=binding.signal_us,
            available_us=binding.signal_us) for i, s in enumerate(S) if not clone.marks[s]}
        # Only absent fresh-flat risk observations may be seeded. Existing
        # native marks, including different same-clock trade/mark prices after
        # the wallet becomes flat again, remain exactly authoritative.
        if missing:
            clone.update_marks(binding.signal_us, missing)
    base = causal.FreshExecutionPreview
    class TierSignalPreview(base):
        def __init__(self):
            self.account = _TokenView(clone)
            self.actual = {s: clone.positions[s].quantity for s in S}
            self.prices = {s: D(binding.prices[i]) for i, s in enumerate(S)}
            self.pending = {s: account.positions[s].quantity for s in S}
            self.quote = {s: D(str(quote[s])) for s in S}
            self.event_us, self.signal_us, self.quote_us = admission_us, binding.signal_us, quote_us
            self.price_us = dict(zip(S, binding.price_available_us))
            self.cov = g._covariance(binding.covariance)
            self.before = self.account.snapshot()
            if (quote_us > admission_us or binding.covariance_available_us > binding.signal_us
                    or any(x > binding.signal_us for x in self.price_us.values())
                    or any(not x.is_finite() or x < 0 for x in self.quote.values())):
                raise ValueError('CAUSAL_SIGNAL_AND_REAL_COMPLETED_CAPACITY_REQUIRED')
        def _risk(self, probe):
            return _tier_risk(probe, self.cov, tier_name)
        def _charged(self, target, tag):
            probe, witness = super()._charged(target, tag)
            return (probe._owned if probe is not None else None), witness
        def evaluate(self, target, lam):
            witness = super().evaluate(target, lam)
            if witness.get('reason') == 'CHARGED_ACTUAL_PENDING_060_030_010_CAP':
                witness['reason'] = 'CHARGED_ACTUAL_PENDING_' + tier_name + '_TIER_CAP'
            return witness
    return TierSignalPreview()


def _exact_tree_equal(left, right):
    """Exact deterministic persistent-tree equality, short-circuit shared roots."""
    if left is right:
        return True
    # Runtime was source-verified before construction. Re-reading every source
    # file for each scalar in one equality recursion would be O(nodes*source).
    node = _RUNTIME[4]._Node
    if isinstance(left, node) or isinstance(right, node):
        return (type(left) is node and type(right) is node and left.key == right.key
            and left.value == right.value and left.height == right.height
            and _exact_tree_equal(left.left, right.left)
            and _exact_tree_equal(left.right, right.right))
    if isinstance(left, dict) or isinstance(right, dict):
        return (type(left) is dict and type(right) is dict and left.keys() == right.keys()
            and all(_exact_tree_equal(left[k], right[k]) for k in left))
    if isinstance(left, (tuple, list)) or isinstance(right, (tuple, list)):
        return (type(left) is type(right) and len(left) == len(right)
            and all(_exact_tree_equal(a, b) for a, b in zip(left, right)))
    return left == right


class _ExactCapitalToken:
    def __init__(self, account):
        self.state = account.preview_state_token()
    def __eq__(self, other):
        return type(other) is type(self) and _exact_tree_equal(self.state, other.state)


class _CapitalView(_TokenView):
    """Private original-CapitalGuard view; real finances remain unchanged.

    Original CapitalGuard performs identical dry-run/commit and compares exact
    state. Persistent-tree comparison changes its comparison cost, not the
    equality predicate or public native snapshot representation.
    """
    def snapshot(self):
        return _ExactCapitalToken(self._owned)
    def execute_fill(self, *args, **kwargs):
        # Direct exact engine method avoids recursing through the live transient
        # fresh-risk interceptor; the caller already completed that check.
        return runtime()[0].USDTLinearPerpetualAccount.execute_fill(self._owned, *args, **kwargs)


def capital_guard_fill(account, *args, **kwargs):
    """Exact existing 1000/8500 CapitalGuard, common to every configuration."""
    policy = sys.modules['_three_tier_original_capital_policy']
    return policy.CapitalGuard(_CapitalView(account)).execute_fill(*args, **kwargs)


class PartialTierGuard:
    """Common frozen partial signal selection and fresh pending replacement.

    Original select_partial checks all fixed fractions independently. Native owns reductions,
    retries, funding, capacity, integer lots and paid terminal60. The initial
    signal is queued only for fresh-flat/empty pending state and admitted at
    the first actual completed-minute quote; no previous quote is fabricated.
    """
    def __init__(self, simulator, source, tier_name):
        self.sim, self.source, self.tier_name = simulator, source, tier_name
        self.original_schedule, self.original_attempt = simulator.schedule, simulator.attempt
        self.bindings, self.receipts, self.deferred = {}, [], None
        self._installed = False

    def install(self):
        if self._installed:
            raise ValueError('GUARD_ALREADY_INSTALLED')
        self.sim.schedule, self.sim.attempt = self.schedule, self.attempt
        self._installed = True
        return self

    def _pending(self):
        return {s: self.sim.pending[s]['target'] if s in self.sim.pending
                else self.sim.account.positions[s].quantity for s in S}

    def schedule(self, target, signal, kind, only_symbols=None):
        active = S if only_symbols is None else tuple(only_symbols)
        if len(set(active)) != len(active) or any(s not in S for s in active):
            raise ValueError('EXACT_ACTIVE_CORE5_SYMBOLS_REQUIRED')
        if isinstance(kind, dict) and set(kind) != set(S):
            raise ValueError('EXACT_CORE5_KIND_MAP_REQUIRED')
        kinds = {s: kind[s] if isinstance(kind, dict) else kind for s in active}
        priority = {'RISK_REDUCTION', 'TERMINAL', 'POOL_EXIT', 'DATA_GAP_EXIT', 'PROTECTIVE_STOP'}
        priority_members = tuple(s for s in active if kinds[s] in priority)
        normal_members = tuple(s for s in active if s not in priority_members)
        if not normal_members:
            return self.original_schedule(target, signal, kind, only_symbols)
        if any(kinds[s] != 'DAILY_TARGET' for s in normal_members):
            raise ValueError('NATIVE_DAILY_OR_PRIORITY_KIND_REQUIRED')
        if priority_members:
            self.original_schedule(target, signal, kind, priority_members)
        binding = self.source.bind(signal)
        self.bindings[signal] = binding
        if self.sim.previous_quote is None:
            a = self.sim.account
            if (active != S or priority_members or signal != self.sim.start
                    or self.deferred is not None or self.sim.pending
                    or self.sim.rows_written != 0 or a.free_cash != D(10000)
                    or a.unpaid_liability or any(p.quantity for p in a.positions.values())
                    or a.trades or a.fill_requests):
                raise ValueError('UNKNOWN_PRIOR_QUOTE_ONLY_FRESH_FLAT_INITIAL_INTENT')
            self.deferred = (deepcopy(target), signal, deepcopy(kind), only_symbols,
                runtime()[4].fork_owned_account(a))
            self.receipts.append({'phase': 'INITIAL_SIGNAL_DEFERRED_UNKNOWN_PRIOR_QUOTE', 'signal_us': signal})
            return None
        oracle = signal_preview(self.sim.account, binding, self.sim.previous_quote, signal,
            tier_name=self.tier_name, admission_us=signal+MINUTE+1)
        oracle.pending = self._pending()
        normal_target = {s: D(str(target[s])) if s in normal_members else oracle.actual[s] for s in S}
        chosen = self._select(oracle, normal_target, 'SIGNAL_PARTIAL', signal)
        return self.original_schedule(chosen.target, signal, kind,
            normal_members if priority_members or only_symbols is not None else None)

    def _select(self, oracle, target, phase, signal_us, evaluate=None):
        selection = sys.modules['candidate'].select_partial(actual=oracle.actual,
            raw_target=target, evaluate=evaluate or oracle.evaluate)
        self.receipts.append({'phase': phase, 'signal_us': signal_us,
            'raw_target_quantities': {s: str(q) for s, q in selection.raw_target.items()},
            'selected_target_quantities': {s: str(q) for s, q in selection.target.items()},
            'fraction': str(selection.fraction) if selection.fraction is not None else None,
            'all_invalid': selection.all_invalid,
            'evaluations': [{'fraction': str(e.fraction), 'allowed': e.allowed,
                'reason': e.witness.get('reason'),
                'corners_checked': len(e.witness.get('corners_checked', []))}
                for e in selection.evaluations]})
        return selection

    def attempt(self, open_us, market_row):
        sim, account = self.sim, self.sim.account
        if self.deferred is not None and open_us >= sim.start + MINUTE:
            if (open_us != sim.start + MINUTE or sim.rows_written != 1 or sim.previous_quote is None
                    or sim.pending or any(p.quantity for p in account.positions.values())):
                raise ValueError('EXACT_FIRST_COMPLETED_MINUTE_FRESH_FLAT_ADMISSION')
            target, signal, kind, active, frozen_account = self.deferred
            if (account.status != 'ACTIVE' or account.free_cash != frozen_account.free_cash
                    or account.unpaid_liability != frozen_account.unpaid_liability
                    or account.fees != frozen_account.fees
                    or account.execution_cost != frozen_account.execution_cost
                    or account.funding_cash != frozen_account.funding_cash
                    or account.trades or account.fill_requests):
                raise ValueError('DEFERRED_SIGNAL_ECONOMIC_STATE_CHANGED')
            binding = self.bindings[signal]
            oracle = signal_preview(frozen_account, binding, sim.previous_quote, int(open_us),
                tier_name=self.tier_name, admission_us=int(open_us)+1)
            chosen = self._select(oracle, target, 'DEFERRED_SIGNAL_PARTIAL', signal)
            self.original_schedule(chosen.target, signal, kind, active)
            self.deferred = None
            self.receipts.append({'phase': 'INITIAL_INTENT_ADMITTED_REAL_QUOTE',
                'original_signal_us': signal, 'admission_us': open_us + 1,
                'quote_available_us': open_us})
        event = int(open_us) + 1
        prices = {s: D(str(market_row[s]['open'])) for s in S if s in market_row}
        capacity = {s: D(str(sim.previous_quote[s])) * D('.001') / prices[s]
            if sim.previous_quote is not None and s in prices else D(0) for s in S}
        raw_fill = account.execute_fill
        if 'execute_fill' in vars(account):
            raise ValueError('UNEXPECTED_EXISTING_ACCOUNT_FILL_INTERCEPTOR')
        def guarded(_account, symbol, side, quantity, event_us, signal_us, fill_id, **kwargs):
            # Native duplicate identity validation precedes every current policy.
            # A replay creates no new fill; a conflict must raise natively.
            if fill_id in account.fill_requests:
                return raw_fill(symbol, side, quantity, event_us, signal_us, fill_id, **kwargs)
            quantity = D(str(quantity))
            planned = account._floor(symbol, min(quantity, D(str(kwargs['available_quantity']))))
            if not kwargs.get('reduce_only', False) and planned > 0:
                before, pending_before = account.preview_state_token(), deepcopy(sim.pending)
                try:
                    if event_us != event or set(prices) != set(S):
                        raise ValueError('COMPLETE_CURRENT_NATIVE_OPENS_REQUIRED')
                    if D(str(kwargs['execution_mid_price'])) != prices[symbol]:
                        raise ValueError('NATIVE_MIDPOINT_MISMATCH')
                    binding = self.bindings[signal_us]
                    live_capacity = dict(capacity)
                    live_capacity[symbol] = D(str(kwargs['available_quantity']))
                    old_pending = self._pending()
                    priority = {'RISK_REDUCTION', 'TERMINAL', 'POOL_EXIT', 'DATA_GAP_EXIT', 'PROTECTIVE_STOP'}
                    normal = {s for s in S if s in sim.pending and sim.pending[s]['kind'] not in priority}
                    if any(sim.pending[s]['signal_us'] != signal_us for s in normal):
                        raise ValueError('ONE_SOURCE_BOUND_NORMAL_PENDING_SIGNAL_REQUIRED')
                    # A chosen fresh replacement cancels old normal endpoints;
                    # all still-live priority endpoints remain in every corner.
                    actual = {s: account.positions[s].quantity for s in S}
                    raw_normal = {s: old_pending[s] if s in normal else actual[s] for s in S}
                    def candidate_check(candidate, lam):
                        replacement = {s: candidate[s] if s in normal else old_pending[s] for s in S}
                        oracle = fresh_preview(account, tier_name=self.tier_name, binding=binding,
                            prices=prices, price_available_us=dict.fromkeys(S, int(open_us)),
                            pending=replacement, capacity=live_capacity, event_us=event_us,
                            signal_us=signal_us, quote_available_us=kwargs['quote_available_us'])
                        return oracle.evaluate(replacement, lam)
                    oracle = fresh_preview(account, tier_name=self.tier_name, binding=binding,
                        prices=prices, price_available_us=dict.fromkeys(S, int(open_us)),
                        pending=old_pending, capacity=live_capacity, event_us=event_us,
                        signal_us=signal_us, quote_available_us=kwargs['quote_available_us'])
                    chosen = self._select(oracle, raw_normal, 'FRESH_PENDING_REPLACEMENT', signal_us,
                        evaluate=candidate_check)
                    witness = (next(e.witness for e in chosen.evaluations if e.fraction == chosen.fraction)
                        if chosen.fraction is not None else
                        {'allowed': False, 'reason': 'ALL_LADDER_CANDIDATES_INVALID_NO_INCREASE'})
                except Exception as exc:
                    witness = {'allowed': False, 'reason': type(exc).__name__ + ':' + str(exc)}
                if account.preview_state_token() != before or sim.pending != pending_before:
                    raise AssertionError('FRESH_GUARD_MUTATED_LIVE_STATE')
                self.receipts.append({'phase': 'FRESH_FILL_GUARD', 'fill_id': fill_id,
                    'signal_us': signal_us, 'event_us': event_us, 'symbol': symbol,
                    'allowed': witness['allowed'], 'reason': witness['reason'],
                    'corners_checked': len(witness.get('corners_checked', [])),
                    'source_sha256': binding.source_sha256 if 'binding' in locals() else None})
                if not witness['allowed']:
                    if 'chosen' in locals() and chosen.all_invalid:
                        # Original select_partial fallback contains only paid
                        # reductions/current inventory, never an increase.
                        for s in normal:
                            sim.pending[s]['target'] = chosen.target[s]
                    return runtime()[5].CausalPartialAdapter._rejected(symbol, quantity, fill_id,
                        'FRESH_TIER_EXECUTION_GUARD', witness)
                for s in normal:
                    sim.pending[s]['target'] = chosen.target[s]
                selected_quantity = abs(chosen.target[symbol] - account.positions[symbol].quantity)
                quantity = min(quantity, selected_quantity)
                if quantity == 0:
                    return runtime()[5].CausalPartialAdapter._rejected(symbol, D(0), fill_id,
                        'FRESH_PARTIAL_SELECTED_NO_INCREASE', witness)
            before_trades = len(account.trades)
            receipt = capital_guard_fill(account, symbol, side, quantity, event_us, signal_us, fill_id, **kwargs)
            used = sum((D(row['decimal_strings']['quantity']) for row in account.trades[before_trades:]), D(0))
            capacity[symbol] = max(D(0), capacity[symbol] - used)
            return receipt
        account.execute_fill = MethodType(guarded, account)
        try:
            return self.original_attempt(open_us, market_row)
        finally:
            del account.execute_fill


def build_case(window, source_rows, decisions, targets, *, tier_name, cost_name='BASE27',
               generated_scope=None, admission=None, expected_admission_sha256=None):
    """Prepare a common native case, never dispatch it on construction.

    Historical source admission is an external exact-byte root decision. A
    generated fixture cannot grant it. No data files are opened by this API.
    """
    _verify_native()
    if (generated_scope != 'GENERATED_FAKE_ORIGIN_ONLY'
            or window.get('fixture_scope') != generated_scope):
        raise ValueError('HISTORICAL_NO_GO_PENDING_EXACT_PROVIDER_TARGET_ROOT_ADMISSION_BINDING')
    return _construct_case(window, source_rows, decisions, targets,
        tier_name=tier_name, cost_name=cost_name, source_scope='GENERATED_FAKE_ORIGIN_ONLY')


def _construct_case(window, source_rows, decisions, targets, *, tier_name,
                    cost_name, source_scope):
    """Internal constructor; historical_entry owns positive real-data admission."""
    tier = g.tier_named(tier_name)
    d, w = np.asarray(decisions), np.asarray(targets)
    expected_d = np.arange(window['start'], window['end'], DAY, dtype=np.int64)
    if (tuple(window['symbols']) != S or d.dtype != np.dtype('int64')
            or not np.array_equal(d, expected_d) or w.shape != (len(d), 5)
            or not np.isfinite(w).all() or abs(w).max() > .30 + 1e-12
            or abs(w).sum(1).max() > tier.gross_cap + 1e-12):
        raise ValueError('EXACT_TIER_CORE5_TARGET_CALENDAR_REQUIRED')
    _, _, terminal, _, _, causal = runtime()
    cost = dict(id=cost_name, half_spread_bps=4 if cost_name == 'BASE27' else 8,
        slippage_bps=4 if cost_name == 'BASE27' else 8, roundtrip_bps=27 if cost_name == 'BASE27' else 43)
    _scenario_config(cost)
    def factory(daily, clocks, mode):
        if not np.array_equal(clocks, d):
            raise ValueError('NATIVE_TARGET_CLOCK_CHANGED')
        return pl.DataFrame([{'available_us': int(at), 'symbol': s, 'target_weight': float(w[i, j])}
            for i, at in enumerate(d) for j, s in enumerate(S)]), {'grid_version': g.VERSION}
    def account_factory(config, *, symbols):
        if tuple(symbols) != S or config != _scenario_config(cost):
            raise ValueError('NATIVE_CONFIG_COST_FACTORY_MISMATCH')
        return make_owned_account(tier_name, cost)
    class NonRestartableTierSimulator(terminal.EarlierTerminalSimulator):
        VERSION = VERSION + '_NONRESTARTABLE_POLICY'
        def fork(self, *args, **kwargs):
            raise RuntimeError('NEW_TIER_GUARD_POLICY_FORK_NOT_CERTIFIED')
        def state_hash(self, *args, **kwargs):
            raise RuntimeError('NEW_TIER_GUARD_POLICY_STATE_HASH_NOT_CERTIFIED')
        def snapshot(self, *args, **kwargs):
            raise RuntimeError('NEW_TIER_GUARD_POLICY_RESTART_SNAPSHOT_NOT_CERTIFIED_USE_ACCOUNT_AUDIT')
        @classmethod
        def from_snapshot(cls, *args, **kwargs):
            raise RuntimeError('NEW_TIER_GUARD_POLICY_RECOVERY_NOT_CERTIFIED')
    sim = NonRestartableTierSimulator(window, 'LONG_SHORT', cost,
        {'id': 'RAW_AS_FRACTION', 'scale': 1.0}, target_factory=factory,
        account_factory=account_factory, persist_cash_close=False, final_day_target_zero=False)
    source = causal.CompletedBarSource(source_rows)
    sim.meta.update(tier=tier.name, gross_ceiling=tier.gross_cap,
        annual_volatility_ceiling=tier.annual_vol_target, asset_ceiling=.30,
        common_free_cash_floor='1000', common_isolated_margin_ceiling='8500',
        partial_ladder=['1', '.75', '.5', '.25', '0'], execution_version=VERSION,
        source_scope=source_scope)
    guard = PartialTierGuard(sim, source, tier_name).install()
    return sim, guard


def case_result(sim, guard):
    """Native output plus explicit new-tier policy and paid/marked distinction."""
    if guard.sim is not sim:
        raise ValueError('CASE_AND_GUARD_IDENTITY_MISMATCH')
    result = sim.result()
    summary = result['summary']
    tier = g.tier_named(guard.tier_name)
    full = sim.stop is None and sim.rows_written == (sim.end - sim.start) // MINUTE
    paid = bool(full and summary['terminal_cash_realized'] and sim.account.unpaid_liability == 0)
    result['common_execution_policy'] = {
        'version': VERSION, 'tier': tier.name, 'gross_ceiling': tier.gross_cap,
        'asset_ceiling': tier.asset_cap, 'annual_covariance_volatility_ceiling': tier.annual_vol_target,
        'initial_cash': '10000', 'leverage': 1, 'margin_mode': 'ISOLATED',
        'automatic_topup': False, 'free_cash_increase_floor': '1000',
        'actual_isolated_margin_ceiling': '8500',
        'capital_reserved_twice': False, 'partial_fraction_allocator': True,
        'partial_ladder': ['1', '.75', '.5', '.25', '0'],
        'native_inherited_annual_vol_contract_text_is_legacy': True,
        'historical_or_native_venue_certified_by_generated_tests': False}
    result['economics'] = {
        'calendar': [sim.start, sim.end], 'full_calendar': full, 'paid_flat': paid,
        'marked_net_return': float(sim.account.nav() / D(10000) - 1),
        'paid_net_return': float(sim.account.nav() / D(10000) - 1) if paid else None,
        'all_observation_max_drawdown': sim.mdd,
        'liquidation_required_halt': sim.account.status == 'LIQUIDATION_REQUIRED_HALT',
        'bankruptcy_halt': sim.account.status == 'BANKRUPT_HALT',
        'actual_liquidation_fills': len(getattr(sim.account, 'liquidations', [])),
        'liquidation_fill_model': 'NOT_IMPLEMENTED_NATIVE_ACCOUNT_STOPS_WITH_WITNESS',
        'residual_marked_notional': summary['terminal_marked_notional'],
        'unpaid_liability': str(sim.account.unpaid_liability),
        'fees_USDT': str(sim.account.fees), 'execution_cost_USDT': str(sim.account.execution_cost),
        'funding_USDT': str(sim.account.funding_cash),
        'turnover_USDT': str(sim.account.gross_fill_turnover),
        'forecast_nominal_risk_matching_is_not_equal_realized_risk': True}
    result['fresh_guard_receipts'] = deepcopy(guard.receipts)
    return result
