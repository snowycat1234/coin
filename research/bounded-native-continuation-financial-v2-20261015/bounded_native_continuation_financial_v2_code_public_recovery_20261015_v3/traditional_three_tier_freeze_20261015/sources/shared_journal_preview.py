"""Generated-only preview acceleration. Never install as a live account factory.

The first clone detaches and recursively freezes native journal history. Further
preview forks share only immutable history and append independent records. All
financial methods, risk gates, identity checks and corner enumeration are native.
Public snapshots remain ordinary, mutable JSON-compatible dict/list trees.

This is not an arbitrary mutable-list replacement: historical edits/deletes,
map overwrites and unsupported values fail explicitly. Native FineGrid writes
are append/new-key only. Validated from_snapshot is the recovery/rollback path.
Initial sealing, full snapshots and snapshot equality remain O(history).
"""
from __future__ import annotations

from collections.abc import Mapping, MutableMapping, MutableSequence, Sequence
from copy import deepcopy
from dataclasses import dataclass
from decimal import Decimal
from itertools import chain
from types import MappingProxyType

from fine_account import FineGridAccount

JOURNAL_LISTS = ('trades', 'funding')
JOURNAL_MAPS = ('fill_requests', 'funding_events', 'funding_ids')
JOURNALS = JOURNAL_LISTS + JOURNAL_MAPS
_NATIVE_FIELDS = frozenset(('config', '_symbols', 'cost_context', 'instrument_profiles',
    'closing_min_notional_exempt', 'free_cash', 'unpaid_liability', 'positions',
    'marks', 'clock_us', 'last_fill_us', 'status', 'halt_witness', 'fees',
    'execution_cost', 'funding_cash', 'realized_PnL', 'gross_fill_turnover', *JOURNALS))
_ATOMIC = (type(None), bool, int, float, str, Decimal)


class UnsupportedJournalMutation(TypeError):
    pass


def _deny(*args, **kwargs):
    raise UnsupportedJournalMutation('PREVIEW_JOURNAL_HISTORY_IS_READ_ONLY')


@dataclass(frozen=True, eq=False)
class _FrozenMap(Mapping):
    _data: Mapping
    def __getitem__(self, key): return self._data[key]
    def __iter__(self): return iter(self._data)
    def __len__(self): return len(self._data)
    def __deepcopy__(self, memo): return materialize(self, memo)
    __setitem__ = __delitem__ = clear = pop = popitem = setdefault = update = _deny
    __ior__ = _deny


@dataclass(frozen=True, eq=False)
class _FrozenList(Sequence):
    _items: tuple
    def __getitem__(self, key):
        return _FrozenList(self._items[key]) if isinstance(key, slice) else self._items[key]
    def __len__(self): return len(self._items)
    def __iter__(self): return iter(self._items)
    def __eq__(self, other):
        return isinstance(other, (list, tuple, _FrozenList, JournalList)) and len(self) == len(other) and all(a == b for a,b in zip(self, other))
    def __deepcopy__(self, memo): return materialize(self, memo)
    __setitem__ = __delitem__ = append = extend = insert = clear = pop = remove = reverse = sort = _deny
    __iadd__ = __imul__ = _deny


def _freeze(value, active=None):
    """Detach every mutable node; reject graphs outside native JSON journals."""
    if type(value) in _ATOMIC or isinstance(value, (_FrozenMap, _FrozenList)):
        return value
    if active is None: active = set()
    if id(value) in active:
        raise TypeError('CYCLIC_JOURNAL_GRAPH_UNSUPPORTED')
    active.add(id(value))
    try:
        if type(value) is dict:
            if any(type(k) is not str for k in value):
                raise TypeError('NATIVE_STRING_JOURNAL_KEYS_REQUIRED')
            return _FrozenMap(MappingProxyType({k: _freeze(v, active) for k,v in value.items()}))
        if type(value) is list:
            return _FrozenList(tuple(_freeze(v, active) for v in value))
        raise TypeError('UNSUPPORTED_NATIVE_JOURNAL_VALUE:'+type(value).__name__)
    finally:
        active.remove(id(value))


def materialize(value, memo=None):
    """Return detached ordinary native containers, including duplicate receipts."""
    if memo is None: memo = {}
    if type(value) in _ATOMIC: return value
    if id(value) in memo: return memo[id(value)]
    if isinstance(value, Mapping):
        result = {}; memo[id(value)] = result
        for k,v in value.items(): result[k] = materialize(v, memo)
        return result
    if isinstance(value, (list, _FrozenList, JournalList)):
        result = []; memo[id(value)] = result
        result.extend(materialize(v, memo) for v in value)
        return result
    return deepcopy(value, memo)


class JournalList(MutableSequence):
    """Native append/slice/read protocol; forks copy only their small own tail."""
    __slots__ = ('_chunks', '_tail', '_size')
    def __init__(self, values=()):
        chunk = tuple(_freeze(v) for v in values)
        self._chunks = (chunk,) if chunk else ()
        self._tail = []; self._size = len(chunk)
    def fork(self):
        result = object.__new__(type(self))
        result._chunks = self._chunks + ((tuple(self._tail),) if self._tail else ())
        result._tail = []; result._size = self._size
        return result
    def __deepcopy__(self, memo):
        result = self.fork(); memo[id(self)] = result; return result
    def __len__(self): return self._size
    def __iter__(self): return chain(*self._chunks, self._tail)
    def __getitem__(self, index):
        if isinstance(index, slice):
            # Native preview/simulator consume newly added rows, which must stay
            # ordinary dicts in exported corner witnesses and execution receipts.
            return [materialize(self[i]) for i in range(*index.indices(len(self)))]
        if not isinstance(index, int): raise TypeError('list indices must be integers or slices')
        if index < 0: index += self._size
        if index < 0 or index >= self._size: raise IndexError('journal index out of range')
        for chunk in self._chunks:
            if index < len(chunk): return chunk[index]
            index -= len(chunk)
        return self._tail[index]
    def append(self, value):
        self._tail.append(_freeze(value)); self._size += 1
    def extend(self, values):
        # list.extend(self) duplicates a finite snapshot, not an endless iterator.
        for value in tuple(values) if values is self else values: self.append(value)
    def insert(self, index, value):
        if index < len(self): _deny()
        self.append(value)
    def __eq__(self, other):
        if self is other: return True
        if not isinstance(other, (list, tuple, JournalList, _FrozenList)): return False
        if len(self) != len(other): return False
        if isinstance(other, JournalList) and self._chunks is other._chunks and self._tail == other._tail: return True
        return all(a == b for a,b in zip(self, other))
    def __add__(self, other):
        if not isinstance(other, (list, JournalList)): return NotImplemented
        return materialize(self) + materialize(other)
    def __radd__(self, other):
        if not isinstance(other, list): return NotImplemented
        return materialize(other) + materialize(self)
    def __iadd__(self, values): self.extend(values); return self
    def copy(self): return materialize(self)
    __setitem__ = __delitem__ = clear = pop = remove = reverse = sort = __imul__ = _deny


class JournalMap(MutableMapping):
    """Immutable prefix maps with independent append-only identity-key layers."""
    __slots__ = ('_layers', '_tail', '_size')
    def __init__(self, values=()):
        values = dict(values)
        if any(type(k) is not str for k in values): raise TypeError('NATIVE_STRING_JOURNAL_KEYS_REQUIRED')
        self._layers = (MappingProxyType({k: _freeze(v) for k,v in values.items()}),) if values else ()
        self._tail = {}; self._size = len(values)
    def fork(self):
        result = object.__new__(type(self))
        result._layers = self._layers + ((MappingProxyType(dict(self._tail)),) if self._tail else ())
        result._tail = {}; result._size = self._size
        return result
    def __deepcopy__(self, memo):
        result = self.fork(); memo[id(self)] = result; return result
    def __len__(self): return self._size
    def __iter__(self): return chain(*(iter(layer) for layer in self._layers), iter(self._tail))
    def __getitem__(self, key):
        if key in self._tail: return self._tail[key]
        for layer in reversed(self._layers):
            if key in layer: return layer[key]
        raise KeyError(key)
    def __setitem__(self, key, value):
        if type(key) is not str: raise TypeError('NATIVE_STRING_JOURNAL_KEYS_REQUIRED')
        if key in self: _deny()
        self._tail[key] = _freeze(value); self._size += 1
    def copy(self): return materialize(self)
    __delitem__ = clear = pop = popitem = _deny


class PreviewFineGridAccount(FineGridAccount):
    """Private preview subclass; inherited native economics and recovery checks."""
    def snapshot(self):
        # Native snapshot invokes deepcopy on the journal wrappers. Those forks
        # are cheap, then this explicit export materializes full native values.
        return materialize(super().snapshot())


def clone_preview_account(account, *, generated_only):
    """Detach a live native account once, or cheaply fork a sealed preview.

    Explicit generated-only admission is required. This is not a historical
    runtime entry point and does not grant or alter public-data authorization.
    The callback and transient fill guard are removed exactly as frozen v4.
    """
    if generated_only is not True: raise ValueError('GENERATED_ONLY_PREVIEW_REQUIRED')
    if type(account) not in (FineGridAccount, PreviewFineGridAccount):
        raise TypeError('EXACT_FINEGRID_OR_SEALED_PREVIEW_REQUIRED')
    unexpected = set(vars(account)) - _NATIVE_FIELDS - {'execute_fill', 'liquidation_callback'}
    if unexpected: raise TypeError('UNREVIEWED_ACCOUNT_FIELDS:'+','.join(sorted(unexpected)))
    if not _NATIVE_FIELDS <= set(vars(account)): raise TypeError('MISSING_NATIVE_ACCOUNT_FIELDS')
    result = object.__new__(PreviewFineGridAccount)
    callback = getattr(account, 'liquidation_callback', None)
    memo = {id(account.instrument_profiles): account.instrument_profiles}
    if callback is not None: memo[id(callback)] = None
    for name, value in vars(account).items():
        if name == 'execute_fill': continue
        if name in JOURNAL_LISTS:
            if type(value) not in (list, JournalList): raise TypeError('UNSUPPORTED_JOURNAL_LIST')
            copied = value.fork() if type(value) is JournalList else JournalList(value)
        elif name in JOURNAL_MAPS:
            if type(value) not in (dict, JournalMap): raise TypeError('UNSUPPORTED_JOURNAL_MAP')
            copied = value.fork() if type(value) is JournalMap else JournalMap(value)
        else: copied = deepcopy(value, memo)
        setattr(result, name, copied)
    return result


class _SharedCornerMixin:
    """Reuse frozen corner/evaluation code, sealing once per evaluate call."""
    def evaluate(self, target, lam):
        if hasattr(self, '_sealed_corner_account'):
            raise RuntimeError('REENTRANT_PREVIEW_UNSUPPORTED')
        self._sealed_corner_account = clone_preview_account(self.account, generated_only=True)
        try:
            return super().evaluate(target, lam)
        finally:
            del self._sealed_corner_account

    def _charged(self, target, tag):
        original = self.account
        sealed = getattr(self, '_sealed_corner_account', None)
        if sealed is None:
            sealed = clone_preview_account(original, generated_only=True)
        self.account = sealed
        try:
            return super()._charged(target, tag)
        finally:
            self.account = original


from native_preview import ChargedPreview
from causal_adapter import FreshExecutionPreview


class SharedChargedPreview(_SharedCornerMixin, ChargedPreview):
    """Opt-in signal preview; original live-state snapshot assertions preserved."""
    pass


class SharedFreshExecutionPreview(_SharedCornerMixin, FreshExecutionPreview):
    """Opt-in fresh preview; same native marks, dust and full snapshots."""
    def __init__(self, account, **kwargs):
        super().__init__(clone_preview_account(account, generated_only=True), **kwargs)
