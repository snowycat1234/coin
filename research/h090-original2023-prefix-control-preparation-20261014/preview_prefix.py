"""Generated-only performance storage, with ordinary immutable record APIs.

No finance methods are implemented here. There is no hostile-runtime promise.
"""
from copy import deepcopy
from decimal import Decimal
from itertools import chain
from types import MappingProxyType
import math
from bounded_policy import HighRiskToyAccount

HISTORY_LISTS = ('trades', 'funding')
HISTORY_MAPS = ('fill_requests', 'funding_events', 'funding_ids')
HISTORY_FIELDS = HISTORY_LISTS + HISTORY_MAPS
ENGINE_FIELDS = frozenset(('config', '_symbols', 'cost_context', 'instrument_profiles',
    'closing_min_notional_exempt', 'free_cash', 'unpaid_liability', 'positions',
    'marks', 'clock_us', 'last_fill_us', 'status', 'halt_witness', 'trades',
    'funding', 'fill_requests', 'funding_events', 'funding_ids', 'fees',
    'execution_cost', 'funding_cash', 'realized_PnL', 'gross_fill_turnover'))


def refuse(*args, **kwargs):
    raise TypeError('IMMUTABLE_HISTORY_EXISTING_VALUE_MUTATION_REFUSED')


class FrozenList(list):
    __slots__ = ()
    __setitem__ = __delitem__ = append = extend = insert = pop = remove = clear = sort = reverse = __iadd__ = __imul__ = refuse
    def __deepcopy__(self, memo):
        result = []
        memo[id(self)] = result
        result.extend(deepcopy(value, memo) for value in self)
        return result
    def copy(self):
        return list(self)


class FrozenDict(dict):
    __slots__ = ()
    __setitem__ = __delitem__ = clear = pop = popitem = setdefault = update = __ior__ = refuse
    def __deepcopy__(self, memo):
        result = {}
        memo[id(self)] = result
        result.update((key, deepcopy(value, memo)) for key, value in self.items())
        return result
    def copy(self):
        return dict(self)


def freeze(value, active=None):
    """Copy first, freeze recursively; refuse unknown bodies or cyclic records."""
    if type(value) in (FrozenList, FrozenDict):
        # Public constructors may contain mutable children. Copy and validate
        # incoming wrappers; only stored prefixes bypass freeze during forks.
        active = set() if active is None else active
        if id(value) in active:
            raise TypeError('CYCLIC_HISTORY_RECORD_REFUSED')
        active.add(id(value))
        try:
            plain = dict(value) if type(value) is FrozenDict else list(value)
            return freeze(plain, active)
        finally:
            active.remove(id(value))
    if value is None or type(value) in (str, bool, int, Decimal):
        return value
    if type(value) is float:
        if not math.isfinite(value):
            raise TypeError('FINITE_HISTORY_RECORD_VALUE_REQUIRED')
        return value
    if type(value) not in (dict, list, tuple):
        raise TypeError('UNSUPPORTED_HISTORY_RECORD_VALUE:' + type(value).__name__)
    active = set() if active is None else active
    if id(value) in active:
        raise TypeError('CYCLIC_HISTORY_RECORD_REFUSED')
    active.add(id(value))
    try:
        if type(value) is dict:
            if any(type(key) is not str for key in value):
                raise TypeError('STRING_HISTORY_RECORD_KEYS_REQUIRED')
            return FrozenDict((key, freeze(item, active)) for key, item in value.items())
        body = [freeze(item, active) for item in value]
        return tuple(body) if type(value) is tuple else FrozenList(body)
    finally:
        active.remove(id(value))


class AppendOnlyHistory(list):
    """Immutable record prefixes with independent append tails, JSON list API."""
    __slots__ = ('_prefix', '_tail', '_generation')
    def __init__(self):
        list.__init__(self)
        object.__setattr__(self, '_prefix', ())
        object.__setattr__(self, '_tail', [])
        object.__setattr__(self, '_generation', 0)
    __setattr__ = __delattr__ = refuse
    def __len__(self):
        return len(self._prefix) + len(self._tail)
    def __iter__(self):
        return chain(self._prefix, self._tail)
    def __reversed__(self):
        return chain(reversed(self._tail), reversed(self._prefix))
    def __getitem__(self, key):
        if isinstance(key, slice):
            return list(self)[key]
        if not isinstance(key, int):
            raise TypeError('list indices must be integers or slices')
        if key < 0:
            key += len(self)
        if not 0 <= key < len(self):
            raise IndexError('list index out of range')
        return self._prefix[key] if key < len(self._prefix) else self._tail[key - len(self._prefix)]
    def __contains__(self, value):
        return value in self._prefix or value in self._tail
    def __eq__(self, other):
        return list(self) == list(other) if isinstance(other, list) else NotImplemented
    def __ne__(self, other):
        answer = self.__eq__(other)
        return not answer if answer is not NotImplemented else NotImplemented
    def __repr__(self):
        return repr(list(self))
    def copy(self):
        return list(self)
    def count(self, value):
        return sum(row == value for row in self)
    def index(self, value, start=0, stop=None):
        return list(self).index(value, start, len(self) if stop is None else stop)
    def __add__(self, other):
        return list(self) + other
    def __radd__(self, other):
        return other + list(self)
    def __mul__(self, count):
        return list(self) * count
    __rmul__ = __mul__
    def append(self, value):
        frozen = freeze(value)
        self._tail.append(frozen)
        list.append(self, frozen)
        object.__setattr__(self, '_generation', self._generation + 1)
    __setitem__ = __delitem__ = extend = insert = pop = remove = clear = sort = reverse = __iadd__ = __imul__ = refuse
    def _seal(self):
        if self._tail:
            object.__setattr__(self, '_prefix', self._prefix + tuple(self._tail))
            object.__setattr__(self, '_tail', [])
        return self._prefix
    def fork(self):
        result = type(self)()
        object.__setattr__(result, '_prefix', self._seal())
        list.extend(result, self._prefix)
        object.__setattr__(result, '_generation', self._generation)
        return result
    def audit_token(self):
        return (id(self._prefix), len(self._prefix), self._generation, len(self._tail))
    def __deepcopy__(self, memo):
        result = list(self)
        memo[id(self)] = result
        return result


class InsertOnlyHistory(dict):
    """Immutable value prefixes and insert-only independent key tails."""
    __slots__ = ('_prefix', '_tail', '_generation')
    def __init__(self):
        dict.__init__(self)
        object.__setattr__(self, '_prefix', FrozenDict())
        object.__setattr__(self, '_tail', {})
        object.__setattr__(self, '_generation', 0)
    __setattr__ = __delattr__ = refuse
    def __len__(self):
        return len(self._prefix) + len(self._tail)
    def __iter__(self):
        return chain(self._prefix, self._tail)
    def __contains__(self, key):
        return key in self._prefix or key in self._tail
    def __getitem__(self, key):
        return self._prefix[key] if key in self._prefix else self._tail[key]
    def get(self, key, default=None):
        return self[key] if key in self else default
    def __reversed__(self):
        return reversed(self.copy())
    def keys(self):
        return self.copy().keys()
    def values(self):
        return self.copy().values()
    def items(self):
        return self.copy().items()
    def copy(self):
        return {key: self[key] for key in self}
    def __repr__(self):
        return repr(self.copy())
    def __eq__(self, other):
        return self.copy() == other if isinstance(other, dict) else NotImplemented
    def __ne__(self, other):
        answer = self.__eq__(other)
        return not answer if answer is not NotImplemented else NotImplemented
    def __or__(self, other):
        return self.copy() | other
    def __ror__(self, other):
        return other | self.copy()
    def __setitem__(self, key, value):
        if type(key) is not str:
            raise TypeError('STRING_HISTORY_KEY_REQUIRED')
        if key in self:
            refuse()
        frozen = freeze(value)
        self._tail[key] = frozen
        dict.__setitem__(self, key, frozen)
        object.__setattr__(self, '_generation', self._generation + 1)
    def update(self, *args, **kwargs):
        values = dict(*args, **kwargs)
        if any(type(key) is not str or key in self for key in values):
            refuse()
        frozen = {key: freeze(value) for key, value in values.items()}
        self._tail.update(frozen)
        dict.update(self, frozen)
        object.__setattr__(self, '_generation', self._generation + len(frozen))
    def setdefault(self, key, default=None):
        if key in self:
            return self[key]
        self[key] = default
        return self[key]
    def __ior__(self, other):
        self.update(other)
        return self
    __delitem__ = clear = pop = popitem = refuse
    def _seal(self):
        if self._tail:
            object.__setattr__(self, '_prefix', FrozenDict(self.items()))
            object.__setattr__(self, '_tail', {})
        return self._prefix
    def fork(self):
        result = type(self)()
        object.__setattr__(result, '_prefix', self._seal())
        dict.update(result, self._prefix)
        object.__setattr__(result, '_generation', self._generation)
        return result
    def audit_token(self):
        return (id(self._prefix), len(self._prefix), self._generation, len(self._tail))
    def __deepcopy__(self, memo):
        result = self.copy()
        memo[id(self)] = result
        return result


def validate_engine(engine, installed=True):
    if type(engine) is not HighRiskToyAccount or set(vars(engine)) != ENGINE_FIELDS:
        raise TypeError('EXACT_REVIEWED_ENGINE_AND_FIELD_INVENTORY_REQUIRED')
    if type(engine.instrument_profiles) is not MappingProxyType:
        raise TypeError('SHARED_IMMUTABLE_PROFILE_MAP_REQUIRED')
    if installed:
        for name in HISTORY_FIELDS:
            want = AppendOnlyHistory if name in HISTORY_LISTS else InsertOnlyHistory
            if type(getattr(engine, name)) is not want:
                raise TypeError('EXACT_INSTALLED_IMMUTABLE_HISTORY_REQUIRED:' + name)
        if len({id(getattr(engine, name)) for name in HISTORY_FIELDS}) != len(HISTORY_FIELDS):
            raise TypeError('INDEPENDENT_HISTORY_CONTAINER_IDENTITIES_REQUIRED')


def install_preview_histories(engine):
    """Fresh canonical accounts only; no legacy history or wallet migration."""
    validate_engine(engine, installed=False)
    if (any(getattr(engine, name) for name in HISTORY_FIELDS) or engine.clock_us != 0
            or engine.last_fill_us is not None or engine.status != 'ACTIVE'
            or engine.free_cash != engine.config.initial_cash or engine.unpaid_liability != 0
            or any((pos.quantity or pos.entry_price or pos.isolated_balance or pos.opened_us is not None)
                   for pos in engine.positions.values()) or any(engine.marks.values())
            or engine.halt_witness is not None
            or any(getattr(engine, key) != 0 for key in ('fees', 'execution_cost', 'funding_cash', 'realized_PnL', 'gross_fill_turnover'))):
        raise TypeError('FRESH_PRE_ECONOMIC_ACCOUNT_REQUIRED_NO_HISTORY_MIGRATION')
    for name in HISTORY_FIELDS:
        setattr(engine, name, AppendOnlyHistory() if name in HISTORY_LISTS else InsertOnlyHistory())
    validate_engine(engine)
    return engine


def clone_preview_account(engine):
    """Raw-engine clone; only frozen journal prefixes/profile map are shared."""
    validate_engine(engine)
    memo = {id(engine.instrument_profiles): engine.instrument_profiles}
    for name in HISTORY_FIELDS:
        history = getattr(engine, name)
        memo[id(history)] = history.fork()
    result = deepcopy(engine, memo)
    validate_engine(result)
    return result


def prefix_tokens(engine):
    validate_engine(engine)
    return {name: getattr(engine, name).audit_token() for name in HISTORY_FIELDS}
