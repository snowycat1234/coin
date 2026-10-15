"""Synthetic-only integration of the frozen partial allocator and native fill seam.

No published source changes. Signal inputs come from completed source rows, never
from the next market open. A signal selection is intent, not fill permission.
Native scheduling, finance, floor dust, reductions and terminal exits retain ownership.
"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from decimal import Decimal as D
import hashlib
import json
from types import MethodType
import numpy as np

from candidate import S, PRIORITY, ScheduleAdapter, vector
from native_preview import ChargedPreview
from quant.execution_contract import ExecutionContractV2

DAY = 86_400_000_000


def _stamp(value):
    if type(value) is not int or value < 0:
        raise ValueError('NONNEGATIVE_INTEGER_SOURCE_CLOCK_REQUIRED')
    return value


def _clone(account):
    """Clone financial state while removing only our transient fill interceptor."""
    result = object.__new__(type(account))
    callback = getattr(account, 'liquidation_callback', None)
    memo = {id(account.instrument_profiles): account.instrument_profiles}
    if callback is not None:
        memo[id(callback)] = None
    for name, value in vars(account).items():
        if name == 'execute_fill':
            continue
        setattr(result, name, deepcopy(value, memo))
    return result


@dataclass(frozen=True)
class SignalBinding:
    signal_us: int
    prices: tuple
    price_available_us: tuple
    covariance: tuple
    covariance_available_us: int
    source_sha256: str
    source_rows: tuple


class CompletedBarSource:
    """Source-owned daily closes with explicit observation/publication clocks.

    The source book may contain later rows. Binding uses exactly the last 31
    observed closes per CORE5 symbol at or before the decision, and rejects
    unpublished members rather than falling back to a conveniently older row.
    Covariance is the original 30 daily returns, sample ddof=1, annualized *365.
    """
    def __init__(self, rows):
        parsed = []
        for row in rows:
            if set(row) != {'symbol', 'close_us', 'available_us', 'close'}:
                raise ValueError('COMPLETED_SOURCE_BAR_SCHEMA_REQUIRED')
            symbol = row['symbol']
            close_us, available_us = _stamp(row['close_us']), _stamp(row['available_us'])
            price = D(str(row['close']))
            if symbol not in S or isinstance(row['close'], bool) or not price.is_finite() or price <= 0:
                raise ValueError('FINITE_POSITIVE_CORE5_SOURCE_CLOSE_REQUIRED')
            if close_us % DAY or available_us < close_us:
                raise ValueError('DAILY_SOURCE_CLOSURE_AND_PUBLICATION_REQUIRED')
            parsed.append((symbol, close_us, available_us, str(price)))
        if len(set((r[0], r[1]) for r in parsed)) != len(parsed):
            raise ValueError('UNIQUE_SOURCE_SYMBOL_CLOSE_REQUIRED')
        self.rows = tuple(sorted(parsed, key=lambda r: (S.index(r[0]), r[1])))

    def bind(self, signal_us):
        signal_us = _stamp(signal_us)
        selected, prices, available, calendar, returns = [], [], [], None, []
        for symbol in S:
            rows = [r for r in self.rows if r[0] == symbol and r[1] <= signal_us][-31:]
            if len(rows) != 31 or rows[-1][1] != signal_us:
                raise ValueError('EXACT_DECISION_PRICE_AND_COMPLETE_PAST30_RETURNS_REQUIRED')
            stamps = tuple(r[1] for r in rows)
            if any(b-a != DAY for a, b in zip(stamps, stamps[1:])):
                raise ValueError('COMPLETE_PAST_DAILY_SOURCE_CALENDAR_REQUIRED')
            if calendar is not None and stamps != calendar:
                raise ValueError('SHARED_CORE5_SOURCE_CALENDAR_REQUIRED')
            calendar = stamps
            if any(r[2] > signal_us for r in rows):
                raise ValueError('FUTURE_SIGNAL_PRICE_OR_COVARIANCE_SOURCE_REJECTED')
            values = np.asarray([float(D(r[3])) for r in rows], dtype=np.float64)
            daily = np.diff(values) / values[:-1]
            if not np.isfinite(daily).all():
                raise ValueError('FINITE_SOURCE_RETURNS_REQUIRED')
            returns.append(daily)
            selected.extend(rows)
            prices.append(rows[-1][3])
            available.append(rows[-1][2])
        covariance = np.cov(np.column_stack(returns), rowvar=False, ddof=1) * 365
        if not np.isfinite(covariance).all():
            raise ValueError('FINITE_SOURCE_COVARIANCE_REQUIRED')
        body = json.dumps(selected, separators=(',', ':'), ensure_ascii=True).encode()
        return SignalBinding(signal_us, tuple(prices), tuple(available),
            tuple(tuple(float(x) for x in row) for row in covariance),
            max(r[2] for r in selected), hashlib.sha256(body).hexdigest(), tuple(selected))


class FreshExecutionPreview(ChargedPreview):
    """Reuse frozen charged corners, starting from a fresh, independently marked clone."""
    def _charged(self, target, tag):
        target = dict(target)
        dust = []
        for symbol in S:
            actual = self.account.positions[symbol].quantity
            delta = target[symbol]-actual
            if delta and self.account._floor(symbol, abs(delta)) == 0:
                dust.append({'symbol': symbol, 'remaining_pending_quantity': str(delta),
                             'native_full_lot_quantity': '0', 'executed_quantity': '0'})
                target[symbol] = actual
        probe, witness = super()._charged(target, tag)
        witness['native_zero_lot_pending_dust_unexecuted'] = dust
        return probe, witness

    def __init__(self, account, *, binding, prices, price_available_us, pending,
                 capacity, event_us, signal_us, quote_available_us):
        prices, pending, capacity = vector(prices), vector(pending), vector(capacity)
        event_us, signal_us = _stamp(event_us), _stamp(signal_us)
        if binding.signal_us != signal_us or binding.covariance_available_us > signal_us:
            raise ValueError('ORDER_BOUND_PAST_COVARIANCE_REQUIRED')
        if set(price_available_us) != set(S) or any(
            type(t) is not int or t < 0 or t > event_us for t in price_available_us.values()):
            raise ValueError('FRESH_EXECUTION_PRICES_MUST_ALREADY_BE_AVAILABLE')
        if any(prices[s] <= 0 or capacity[s] < 0 for s in S):
            raise ValueError('POSITIVE_EXECUTION_PRICES_NONNEGATIVE_CAPACITY_REQUIRED')
        quote_available_us = _stamp(quote_available_us)
        if quote_available_us > event_us:
            raise ValueError('PAST_EXECUTION_CAPACITY_REQUIRED')
        if tuple(account.symbols) != S:
            raise ValueError('EXACT_CORE5_ACCOUNT_REQUIRED')
        for symbol in S:
            if not account.marks[symbol] or any(row['available_us'] > event_us or
                row['close_us'] > event_us for row in account.marks[symbol]):
                raise ValueError('CAUSAL_ACCOUNT_MARKS_REQUIRED')
        self.account = _clone(account)
        # Opens are known only here, after signal and pre-fill funding. They are
        # independent risk observations; the live account's close-mark ledger is untouched.
        self.account.update_marks(event_us, {s: {'price': prices[s],
            'close_us': event_us, 'available_us': event_us} for s in S})
        self.actual = {s: self.account.positions[s].quantity for s in S}
        self.prices, self.pending = prices, pending
        # _charged converts quote*.001/price into capacity. Use the exact remaining
        # per-symbol native attempt budget, including earlier same-minute reductions.
        self.quote = {s: capacity[s]*prices[s]/D('.001') for s in S}
        self.event_us, self.signal_us, self.quote_us = event_us, signal_us, quote_available_us
        self.price_us = dict(price_available_us)
        self.cov = np.asarray(binding.covariance, dtype=np.float64)
        if self.cov.shape != (5, 5) or not np.isfinite(self.cov).all() or not np.allclose(
            self.cov, self.cov.T, atol=1e-12, rtol=0) or np.linalg.eigvalsh(self.cov).min() < -1e-15:
            raise ValueError('FINITE_PSD_SOURCE_COVARIANCE_REQUIRED')
        self.before = self.account.snapshot()


class CausalPartialAdapter:
    """Installable schedule/attempt seam; original simulator methods are delegated.

    Install for native advance_day integration or call schedule/attempt explicitly.
    The guard intercepts every native non-reduce-only fill during an attempt, not
    just the first order. It recomputes all current actual/pending corners and native
    charged capacity from fresh state. Rejecting leaves the account byte-exact;
    original scheduler rejection journals, attempt counts and expiry still advance.
    This synthetic adapter is not a historical/recovery/fork certification.
    """
    VERSION = 'original_csh_causal_partial_execution_v4_synthetic_only'

    def __init__(self, simulator, source):
        if tuple(simulator.symbols) != S:
            raise ValueError('EXACT_CORE5_SIMULATOR_REQUIRED')
        self.simulator, self.source = simulator, source
        self.original_schedule, self.original_attempt = simulator.schedule, simulator.attempt
        self.bindings, self.execution_receipts = {}, []
        self.intent = ScheduleAdapter(self.original_schedule, self._signal_preview)
        self.installed = False

    @property
    def receipts(self):
        return self.intent.receipts

    def install(self):
        if self.installed:
            raise ValueError('ALREADY_INSTALLED')
        self.simulator.schedule, self.simulator.attempt = self.schedule, self.attempt
        self.installed = True
        return self

    def uninstall(self):
        if self.installed:
            self.simulator.schedule, self.simulator.attempt = self.original_schedule, self.original_attempt
            self.installed = False

    def _pending(self):
        sim = self.simulator
        return {s: sim.pending[s]['target'] if s in sim.pending else sim.account.positions[s].quantity for s in S}

    def _signal_preview(self, signal_us):
        sim = self.simulator
        binding = self.source.bind(signal_us)
        if sim.previous_quote is None:
            raise ValueError('PAST_SIGNAL_CAPACITY_REQUIRED')
        for s in S:
            if not sim.account.marks[s] or any(row['available_us'] > signal_us or
                row['close_us'] > signal_us for row in sim.account.marks[s]):
                raise ValueError('SIGNAL_ACCOUNT_STATE_MUST_BE_CAUSAL')
        oracle = ChargedPreview(sim.account, prices=dict(zip(S, binding.prices)),
            covariance=binding.covariance, pending=self._pending(),
            previous_quote=sim.previous_quote,
            event_us=ExecutionContractV2().earliest_execution_us(signal_us)+1,
            signal_us=signal_us, covariance_available_us=binding.covariance_available_us,
            quote_available_us=signal_us, price_available_us=dict(zip(S, binding.price_available_us)))
        self.bindings[signal_us] = binding
        return oracle

    def schedule(self, target, signal, kind, only_symbols=None):
        return self.intent.schedule(target, signal, kind, only_symbols)

    @staticmethod
    def _rejected(symbol, quantity, fill_id, reason, witness):
        return {'fill_id': fill_id, 'requested_quantity': float(quantity),
            'executed_quantity': 0., 'remaining_quantity': float(quantity),
            'decimal_strings': {'requested_quantity': str(quantity), 'executed_quantity': '0',
                                'remaining_quantity': str(quantity)},
            'status': 'REJECTED', 'reason': reason, 'fills': [], 'guard_witness': witness}

    def attempt(self, open_us, market_row):
        sim, account = self.simulator, self.simulator.account
        event = _stamp(open_us)+1
        # Read only the already available opens. Close/mark/volume for this minute
        # are not consumed by the guard. All funding at open+1 was applied by native order.
        prices = {s: D(str(market_row[s]['open'])) for s in S if s in market_row}
        capacity = {s: D(str(sim.previous_quote[s]))*D('.001')/prices[s]
            if sim.previous_quote is not None and s in prices else D(0) for s in S}
        raw_fill = account.execute_fill
        had_instance_method = 'execute_fill' in vars(account)
        previous_instance_method = vars(account).get('execute_fill')

        def guarded(_account, symbol, side, quantity, event_us, signal_us, fill_id, **kwargs):
            quantity = D(str(quantity))
            native_planned = account._floor(symbol, min(quantity, D(str(kwargs['available_quantity']))))
            if not kwargs.get('reduce_only', False) and native_planned > 0:
                before = account.snapshot()
                pending_before = deepcopy(sim.pending)
                try:
                    if event_us != event or set(prices) != set(S):
                        raise ValueError('COMPLETE_CURRENT_NATIVE_OPEN_VECTOR_REQUIRED')
                    if D(str(kwargs['execution_mid_price'])) != prices[symbol]:
                        raise ValueError('NATIVE_FILL_MIDPOINT_MUST_MATCH_CURRENT_OPEN')
                    binding = self.bindings.get(signal_us)
                    if binding is None:
                        raise ValueError('MISSING_SOURCE_BOUND_ORDER_SIGNAL')
                    live_capacity = dict(capacity)
                    live_capacity[symbol] = D(str(kwargs['available_quantity']))
                    preview = FreshExecutionPreview(account, binding=binding, prices=prices,
                        price_available_us=dict.fromkeys(S, open_us), pending=self._pending(),
                        capacity=live_capacity, event_us=event_us, signal_us=signal_us,
                        quote_available_us=kwargs['quote_available_us'])
                    witness = preview.evaluate(self._pending(), D(1))
                    witness.update(source_sha256=binding.source_sha256,
                        event_us=event_us, signal_us=signal_us, fresh_native_NAV=str(account.nav()),
                        fresh_free_cash=str(account.free_cash), fresh_funding_cash=str(account.funding_cash),
                        fresh_pending={s: str(q) for s, q in self._pending().items()},
                        current_available_opens={s: str(p) for s, p in prices.items()})
                except Exception as exc:
                    witness = {'allowed': False, 'reason': 'FRESH_GUARD_EXCEPTION:'+type(exc).__name__,
                               'detail': str(exc), 'event_us': event_us, 'signal_us': signal_us}
                if account.snapshot() != before or sim.pending != pending_before:
                    raise AssertionError('GUARD_CHANGED_LIVE_ACCOUNT_OR_PENDING')
                self.execution_receipts.append({'symbol': symbol, 'fill_id': fill_id, **witness})
                if not witness['allowed']:
                    return self._rejected(symbol, quantity, fill_id, 'FRESH_EXECUTION_RISK_GUARD', witness)
            before_trades = len(account.trades)
            receipt = raw_fill(symbol, side, quantity, event_us, signal_us, fill_id, **kwargs)
            used = sum((D(r['decimal_strings']['quantity']) for r in account.trades[before_trades:]
                        if not r.get('liquidation_takeover')), D(0))
            capacity[symbol] = max(D(0), capacity[symbol]-used)
            return receipt

        account.execute_fill = MethodType(guarded, account)
        try:
            return self.original_attempt(open_us, market_row)
        finally:
            if had_instance_method:
                account.execute_fill = previous_instance_method
            else:
                del account.execute_fill
