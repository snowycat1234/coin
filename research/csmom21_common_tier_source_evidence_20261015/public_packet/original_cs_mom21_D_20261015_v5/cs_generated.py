"""Single-process synthetic-only fixtures and native D equivalence seam.

No user arrays, paths, providers, historical scopes, GO objects or prior account
state are accepted by the public fixture or native constructor. Both fixtures
and projections are live-identity sealed and revoked on context exit.
"""
from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from hashlib import sha256
import importlib.util
import json
from pathlib import Path
import sys
from types import MappingProxyType
import weakref

import numpy as np

import cs_signal as signal
from cs_config import TIERS

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
SYNTHETIC = 'INTERNALLY_GENERATED_PURE_CS_ONLY_1971_V1'
_LIVE_FIXTURES = {}
_LIVE_TARGETS = {}
_LIVE_NATIVE_INPUTS = {}
_NATIVE = None
NATIVE_PATH = HERE / 'cs_native.py'
NATIVE_SHA256 = None  # Bound by this sibling's frozen CODE_MANIFEST.


def frozen_array(value, dtype='<f8'):
    a = np.asarray(value, dtype=dtype)
    return np.frombuffer(a.tobytes(order='C'), dtype=dtype).reshape(a.shape)


def array_digest(*arrays):
    h = sha256()
    for a in arrays:
        h.update(str(a.dtype).encode()); h.update(repr(a.shape).encode()); h.update(a.tobytes())
    return h.hexdigest()


@dataclass(frozen=True, eq=False)
class GeneratedFixture:
    scope: str
    close: np.ndarray
    close_us: np.ndarray
    available_us: np.ndarray
    decisions: np.ndarray
    digest: str

    def validate(self):
        record = _LIVE_FIXTURES.get(id(self))
        if (type(self) is not GeneratedFixture or record is None or record[0]() is not self
                or self.scope != SYNTHETIC or record[1] != self.digest
                or record[1] != array_digest(self.close, self.close_us, self.available_us, self.decisions)
                or any(a.flags.writeable for a in (self.close, self.close_us, self.available_us, self.decisions))):
            raise ValueError('LIVE_INTERNALLY_GENERATED_FIXTURE_REQUIRED')
        # Keep the generated namespace entirely outside development/holdout years.
        if self.close_us[0] < 400 * signal.DAY or self.close_us[-1] >= 800 * signal.DAY:
            raise ValueError('EXACT_SYNTHETIC_1971_CLOCK_NAMESPACE_REQUIRED')
        return self


@dataclass(frozen=True, eq=False)
class GeneratedTargets:
    fixture: GeneratedFixture
    raw_weekly: np.ndarray
    original_sized: np.ndarray
    common_tier: object
    covariance: np.ndarray
    diagnostics_json: str
    proofs_json: str
    digest: str

    def validate(self):
        self.fixture.validate()
        record = _LIVE_TARGETS.get(id(self))
        arrays = (self.raw_weekly, self.original_sized,
                  *(self.common_tier[t] for t in TIERS), self.covariance)
        identity = array_digest(*arrays) + sha256((self.diagnostics_json + self.proofs_json).encode()).hexdigest()
        if (type(self) is not GeneratedTargets or record is None or record[0]() is not self
                or record[1] != self.digest or identity != self.digest
                or tuple(self.common_tier) != TIERS or any(a.flags.writeable for a in arrays)):
            raise ValueError('LIVE_INTERNALLY_GENERATED_TARGETS_REQUIRED')
        return self

    def diagnostics(self):
        self.validate()
        return json.loads(self.diagnostics_json)

    def proofs(self):
        self.validate()
        return json.loads(self.proofs_json)


@contextmanager
def generated_fixture(*, seed=1729, days=3, future_spike=False, flat=False):
    """Mint a bounded synthetic fixture; there is no external input argument."""
    if (type(seed) is not int or not 0 <= seed <= 65535
            or type(days) is not int or not 1 <= days <= 14
            or type(future_spike) is not bool or type(flat) is not bool):
        raise ValueError('BOUNDED_GENERATED_FIXTURE_PARAMETERS_REQUIRED')
    rng = np.random.default_rng(seed)
    n = 250
    returns = rng.normal(0, .007, size=(n - 1, 5))
    returns += np.array([.004, .002, .0001, -.002, -.004])
    base = np.array([50000., 2000., 20., .5, .05])
    prices = np.vstack([base, base * np.cumprod(1 + returns, axis=0)])
    if flat:
        prices = np.tile(base, (n, 1))
    t = np.arange(400, 400 + n, dtype=np.int64) * signal.DAY
    d = t[220:220 + days]
    if future_spike:
        prices[220 + days:] *= np.array([4., .3, 2., .4, 3.])
    arrays = tuple(frozen_array(a, '<i8' if i else '<f8')
                   for i, a in enumerate((prices, t, t, d)))
    obj = GeneratedFixture(SYNTHETIC, *arrays, array_digest(*arrays))
    _LIVE_FIXTURES[id(obj)] = (weakref.ref(obj), obj.digest)
    try:
        obj.validate()
        yield obj
    finally:
        _LIVE_FIXTURES.pop(id(obj), None)
        for key, rec in tuple(_LIVE_TARGETS.items()):
            target = rec[0]()
            if target is None or target.fixture is obj:
                _LIVE_TARGETS.pop(key, None)


def project_generated(fixture):
    if type(fixture) is not GeneratedFixture:
        raise ValueError('LIVE_INTERNALLY_GENERATED_FIXTURE_REQUIRED')
    fixture.validate()
    raw, original, targets, cov, diagnostics, proofs = signal.project_arrays(
        fixture.close, fixture.close_us, fixture.available_us, fixture.decisions)
    arrays = [frozen_array(raw), frozen_array(original),
              *(frozen_array(targets[tier]) for tier in TIERS), frozen_array(cov)]
    diagnostics_json = json.dumps(diagnostics, sort_keys=True, separators=(',', ':'), allow_nan=False)
    proofs_json = json.dumps(proofs, sort_keys=True, separators=(',', ':'), allow_nan=False)
    digest = array_digest(*arrays) + sha256((diagnostics_json + proofs_json).encode()).hexdigest()
    obj = GeneratedTargets(fixture, arrays[0], arrays[1],
        MappingProxyType(dict(zip(TIERS, arrays[2:5]))), arrays[5], diagnostics_json, proofs_json, digest)
    _LIVE_TARGETS[id(obj)] = (weakref.ref(obj), obj.digest)
    return obj.validate()


def native_reference():
    """Code-only import of the pinned original-D transport for fake tests."""
    global _NATIVE
    expected = json.loads((HERE / 'FINANCIAL_CODE_MANIFEST.json').read_text())['files']['cs_native.py']['SHA256']
    if NATIVE_PATH.is_symlink() or sha256(NATIVE_PATH.read_bytes()).hexdigest() != expected:
        raise ValueError('EXACT_PINNED_ORIGINAL_D_NATIVE_REFERENCE_REQUIRED')
    if _NATIVE is None:
        name = '_pure_cs_generated_exact_original_D_reference'
        spec = importlib.util.spec_from_file_location(name, NATIVE_PATH)
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        spec.loader.exec_module(module)
        _NATIVE = module
    return _NATIVE


def _synthetic_window(fixture):
    fixture.validate()
    import polars as pl
    native = native_reference()
    symbols, d = signal.SYMBOLS, fixture.decisions
    # The minute tape is internally generated constant-price data. It is not
    # sourced from a provider or read from a canonical array/container.
    base = np.array([50000., 2000., 20., .5, .05])
    start, end = int(d[0]), int(d[-1] + signal.DAY)
    count = (end - start) // native.MINUTE
    rows = [dict(symbol=s, close_us=int(at), available_us=int(at), close=float(fixture.close[i, j]))
            for i, at in enumerate(fixture.close_us) for j, s in enumerate(symbols)]
    events = [dict(symbol=s, event_us=int(at + 8 * 60 * native.MINUTE), raw_rate=.0001,
                   reported_interval_hours=8.) for at in d for s in symbols]
    window = dict(start=start, end=end, symbols=symbols, daily=pl.DataFrame(rows),
        events=events, fixture_scope=native.GENERATED,
        market={s: dict(open=np.full(count, base[j]), close=np.full(count, base[j]),
            mark=np.full(count, base[j]), quote_volume=np.full(count, 1e10)) for j, s in enumerate(symbols)})
    return window, rows, d


def construct_generated_case(targets, tier, *, quality_intervals=()):
    """Only live internally generated targets can reach the fake native seam."""
    if type(targets) is not GeneratedTargets:
        raise ValueError('LIVE_INTERNALLY_GENERATED_TARGETS_REQUIRED')
    targets.validate()
    if tier not in TIERS:
        raise ValueError('EXACT_LOW_MID_HIGH_TIER_REQUIRED')
    window, rows, decisions = _synthetic_window(targets.fixture)
    native = native_reference()
    if (type(quality_intervals) is not tuple or any(type(row) is not tuple or len(row) != 3
            or type(row[0]) is not int or type(row[1]) is not int
            or not window['start'] <= row[0] < row[1] <= window['end']
            or type(row[2]) is not tuple or not row[2] or len(set(row[2])) != len(row[2])
            or any(symbol not in signal.SYMBOLS for symbol in row[2]) for row in quality_intervals)):
        raise ValueError('BOUNDED_GENERATED_FIXTURE_ONLY_QUALITY_INTERVALS_REQUIRED')
    token = object()
    _LIVE_NATIVE_INPUTS[token] = (window, rows, decisions, targets, tier, quality_intervals)
    try:
        return native._construct_case(window, rows, decisions, targets.common_tier[tier],
            tier_name=tier, generated_scope=native.GENERATED, _generated_scope_token=token,
            quality_intervals=quality_intervals)
    finally:
        _LIVE_NATIVE_INPUTS.pop(token, None)


def _validate_native_inputs(token, window, rows, decisions, weights, tier, quality_intervals):
    record = _LIVE_NATIVE_INPUTS.get(token)
    if (record is None or window is not record[0] or rows is not record[1] or decisions is not record[2]
            or tier != record[4] or weights is not record[3].common_tier[tier] or quality_intervals != record[5]):
        raise ValueError('INTERNALLY_SEALED_GENERATED_NATIVE_INPUTS_REQUIRED')
    record[3].validate()
    return True
