"""Separate causal-feed increase admission; frozen native finance is untouched.

This layer consumes an already verified immutable quality policy. It does not
read market files, admit historical data, construct accounts, advance a wallet,
or certify native venue marks. A historical entry must bind this module, its
policy/sidecar identity and the feed projection before installing the guard.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal as D
import hashlib
import json
from types import MethodType

VERSION = 'CAUSAL_LAST_GENUINE_MARK_INCREASE_ADMISSION_V1'
REJECTION = 'CAUSAL_STALE_MARK_NO_NEW_RISK'


def _stamp(value):
    if type(value) is not int or value < 0:
        raise ValueError('NONNEGATIVE_INTEGER_QUALITY_CLOCK_REQUIRED')
    return value


def _sha256(value):
    if (not isinstance(value, str) or len(value) != 64
            or any(c not in '0123456789abcdef' for c in value)):
        raise ValueError('EXACT_QUALITY_SIDECAR_SHA256_REQUIRED')
    return value


@dataclass(frozen=True)
class StaleMarkInterval:
    """Known missing-mark interval, using native observation/availability clocks.

    ``start_us`` is when the first missing close becomes known, never its open.
    ``end_us`` is when the first subsequent genuine close becomes available.
    The original genuine clock remains external metadata: native carry-forward
    valuations are explicitly estimates, not newly observed genuine marks.
    """
    start_us: int
    end_us: int
    original_genuine_observation_us: int
    symbols: tuple[str, ...]

    def __post_init__(self):
        start, end, genuine = map(_stamp, (self.start_us, self.end_us,
                                         self.original_genuine_observation_us))
        if genuine >= start or start >= end:
            raise ValueError('ORDERED_GENUINE_MISSING_RECOVERY_CLOCKS_REQUIRED')
        if (type(self.symbols) is not tuple or not self.symbols
                or any(not isinstance(s, str) or not s for s in self.symbols)
                or len(set(self.symbols)) != len(self.symbols)):
            raise ValueError('IMMUTABLE_DISTINCT_QUALITY_SYMBOLS_REQUIRED')

    def as_dict(self):
        return dict(start_us=self.start_us, end_us=self.end_us,
                    original_genuine_observation_us=self.original_genuine_observation_us,
                    symbols=list(self.symbols))


class CausalMarkQualityGuard:
    """Wrap only the inner native attempt after PartialTierGuard installs fill.

    Native known-ID replay/conflict handling always wins. True reduce-only
    orders and zero-executable requests delegate unchanged. A blocked new-risk
    request changes no target/order/account state. Native owns attempt counts,
    original signals, five-attempt expiry, priority, fees, paid dust and HALTs.
    """
    def __init__(self, partial_guard, *, intervals: tuple[StaleMarkInterval, ...],
                 source_sidecar_sha256: str):
        if type(intervals) is not tuple or any(type(x) is not StaleMarkInterval for x in intervals):
            raise ValueError('IMMUTABLE_STALE_MARK_INTERVAL_TUPLE_REQUIRED')
        if any(a.end_us > b.start_us for a, b in zip(intervals, intervals[1:])):
            raise ValueError('ORDERED_NONOVERLAPPING_STALE_INTERVALS_REQUIRED')
        self.guard, self.sim = partial_guard, partial_guard.sim
        self.intervals = intervals
        self.source_sidecar_sha256 = _sha256(source_sidecar_sha256)
        self.receipts = []
        self._installed = False
        self.original_attempt = None
        self.identity = dict(version=VERSION,
            source_sidecar_sha256=self.source_sidecar_sha256,
            intervals=[x.as_dict() for x in self.intervals],
            known_fill_identity_precedes_quality=True,
            actual_installed_mark_recovery_required=True,
            reduce_only_finance_and_native_retry_unchanged=True,
            estimated_valuation_is_genuine_mark=False,
            native_venue_or_current_mark_certified=False)
        self.policy_sha256 = hashlib.sha256(json.dumps(self.identity, sort_keys=True,
            separators=(',', ':')).encode()).hexdigest()

    def install(self):
        # Do not preinstall account.execute_fill: the frozen outer guard rightly
        # rejects any unexpected instance interceptor before each attempt.
        import native_runtime as n
        if self._installed:
            raise ValueError('QUALITY_GUARD_ALREADY_INSTALLED')
        if (type(self.guard) is not n.PartialTierGuard or not self.guard._installed
                or self.sim.attempt != self.guard.attempt):
            raise ValueError('INSTALLED_FROZEN_PARTIAL_TIER_GUARD_REQUIRED')
        if any(s not in self.sim.symbols for x in self.intervals for s in x.symbols):
            raise ValueError('QUALITY_SYMBOL_OUTSIDE_BOUND_ACCOUNT')
        if 'execute_fill' in vars(self.sim.account):
            raise ValueError('QUALITY_GUARD_MUST_WRAP_INNER_ATTEMPT_ONLY')
        if getattr(self.guard.original_attempt, '__self__', None) is not self.sim:
            raise ValueError('UNMODIFIED_NATIVE_INNER_ATTEMPT_REQUIRED')
        self.original_attempt = self.guard.original_attempt
        self.guard.original_attempt = self.attempt
        self._installed = True
        return self

    def quality_witness(self, event_us):
        """Pure current-account predicate; never consult prefetched market rows."""
        event_us = _stamp(event_us)
        affected = []
        for interval in self.intervals:
            if event_us < interval.start_us:
                break
            marks = []
            recovered = event_us >= interval.end_us
            for symbol in interval.symbols:
                rows = self.sim.account.marks[symbol]
                mark = rows[-1] if rows else None
                close = mark['close_us'] if mark is not None else None
                available = mark['available_us'] if mark is not None else None
                valid = (type(close) is int and type(available) is int
                    and interval.end_us <= close <= available <= event_us)
                recovered = recovered and valid
                marks.append(dict(symbol=symbol, installed_close_us=close,
                    installed_available_us=available))
            if not recovered:
                affected.append(dict(**interval.as_dict(),
                    event_in_known_missing_interval=event_us < interval.end_us,
                    original_genuine_observation_age_us=
                        event_us - interval.original_genuine_observation_us,
                    installed_marks=marks))
        if not affected:
            return None
        return dict(allowed=False, reason=REJECTION, event_us=event_us,
            policy_sha256=self.policy_sha256,
            source_sidecar_sha256=self.source_sidecar_sha256,
            affected_intervals=affected,
            valuation_status='ESTIMATED_LAST_KNOWN_GENUINE_UNTIL_INSTALLED_RECOVERY',
            native_venue_or_current_mark_certified=False)

    @staticmethod
    def _rejected(quantity, fill_id, witness):
        return dict(fill_id=fill_id, requested_quantity=float(quantity),
            executed_quantity=0., remaining_quantity=float(quantity),
            decimal_strings=dict(requested_quantity=str(quantity),
                executed_quantity='0', remaining_quantity=str(quantity)),
            status='REJECTED', reason=REJECTION, fills=[], guard_witness=witness)

    def attempt(self, open_us, market_row):
        account = self.sim.account
        if not self._installed or 'execute_fill' not in vars(account):
            raise ValueError('QUALITY_REQUIRES_ACTIVE_OUTER_FRESH_FILL_INTERCEPTOR')
        captured_fill = vars(account)['execute_fill']
        def quality_fill(_account, symbol, side, quantity, event_us, signal_us, fill_id, **kwargs):
            if fill_id in account.fill_requests:
                return captured_fill(symbol, side, quantity, event_us, signal_us, fill_id, **kwargs)
            if account.status != 'ACTIVE' or kwargs.get('reduce_only', False):
                return captured_fill(symbol, side, quantity, event_us, signal_us, fill_id, **kwargs)
            if not kwargs.get('reduce_only', False):
                requested = D(str(quantity))
                available = kwargs.get('available_quantity')
                available = requested if available is None else D(str(available))
                planned = account._floor(symbol, min(requested, available))
                if planned > 0:
                    witness = self.quality_witness(event_us)
                    if witness is not None:
                        self.receipts.append(dict(phase='CAUSAL_MARK_QUALITY_BLOCK',
                            fill_id=fill_id, symbol=symbol, signal_us=signal_us,
                            event_us=event_us, requested_quantity=str(requested),
                            policy_sha256=self.policy_sha256, witness=witness))
                        return self._rejected(requested, fill_id, witness)
            return captured_fill(symbol, side, quantity, event_us, signal_us, fill_id, **kwargs)
        account.execute_fill = MethodType(quality_fill, account)
        try:
            return self.original_attempt(open_us, market_row)
        finally:
            # The outer PartialTierGuard will then remove its own interceptor.
            account.execute_fill = captured_fill


def install_quality_guard(sim, partial_guard, intervals, *, source_sidecar_sha256):
    """Explicit integration seam; historical binding must already be verified."""
    if partial_guard.sim is not sim:
        raise ValueError('QUALITY_CASE_AND_PARTIAL_GUARD_IDENTITY_MISMATCH')
    return CausalMarkQualityGuard(partial_guard, intervals=intervals,
        source_sidecar_sha256=source_sidecar_sha256).install()
