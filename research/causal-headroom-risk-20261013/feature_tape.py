"""Immutable causal stress tape. Preparation reads existing sources, no account."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import numpy as np

MINUTE = 60_000_000
FIELDS = ('mark', 'ready', 'reason_code', 'a_down', 'a_up', 'g_down', 'g_up')
REASONS = ('READY', 'WARMUP_30_COMPLETE_DAYS', 'BAD_MARK',
           'DERIVED_OR_UNKNOWN_MARK', 'BAD_TRADE_OPEN', 'NONCONTIGUOUS_MINUTE_CLOCK')


def array_sha(array):
    return hashlib.sha256(np.ascontiguousarray(array).tobytes()).hexdigest()


class FeatureTape:
    def __init__(self, times, symbols, arrays, binding):
        self.times = np.asarray(times, dtype=np.int64)
        self.symbols = tuple(symbols)
        self.arrays = arrays
        self.binding = dict(binding)
        if self.times.ndim != 1 or not len(self.times):
            raise ValueError('Nonempty feature close grid required')
        if not np.all(np.diff(self.times) == MINUTE):
            raise ValueError('Exact continuous feature close grid required')
        if set(arrays) != {s+'_'+k for s in self.symbols for k in FIELDS}:
            raise ValueError('Exact feature symbol and field set required')
        for s in self.symbols:
            for k in FIELDS:
                a = arrays[s+'_'+k]
                if a.shape != self.times.shape:
                    raise ValueError('Feature shape differs from close grid')
                a.flags.writeable = False
            ready = arrays[s+'_ready']
            reason = arrays[s+'_reason_code']
            if ready.dtype != np.dtype(bool) or reason.dtype != np.dtype('uint8'):
                raise ValueError('Exact readiness/reason dtypes required')
            if np.any(reason >= len(REASONS)) or not np.array_equal(ready, reason == 0):
                raise ValueError('Readiness/reason identity mismatch')
            for k in ('a_down', 'a_up', 'g_down', 'g_up'):
                a = arrays[s+'_'+k]
                if a.dtype != np.dtype('float64') or not np.isfinite(a[ready]).all():
                    raise ValueError('Finite float64 READY stress features required')
                if not np.isnan(a[~ready]).all():
                    raise ValueError('NOT_READY features must be NaN, never shortened')
                invalid_direction = np.any(a[ready] > 0) if k.endswith('down') else np.any(a[ready] < 0)
                if invalid_direction:
                    raise ValueError('Adverse feature direction invalid')
        self.times.flags.writeable = False

    @classmethod
    def load(cls, path, manifest):
        path = Path(path)
        if hashlib.sha256(path.read_bytes()).hexdigest() != manifest['archive_SHA256']:
            raise ValueError('Feature archive bytes changed')
        with np.load(path, allow_pickle=False) as z:
            if set(z.files) != set(manifest['arrays']):
                raise ValueError('Feature archive keys changed')
            arrays = {k: z[k].copy() for k in z.files}
        for k, a in arrays.items():
            m = manifest['arrays'][k]
            if a.dtype.str != m['dtype'] or list(a.shape) != m['shape'] or array_sha(a) != m['SHA256']:
                raise ValueError('Feature array bits changed: '+k)
        times = arrays.pop('close_us')
        if [int(times[0]-MINUTE), int(times[-1])] != manifest['calendar']:
            raise ValueError('Feature calendar differs')
        return cls(times, manifest['symbols'], arrays,
                   {'archive_SHA256': manifest['archive_SHA256'],
                    'array_binding_SHA256': manifest['array_binding_SHA256'],
                    'core_SHA256': manifest['core_SHA256'],
                    'source_index_SHA256': manifest['source_index_SHA256']})

    def at(self, symbol, stamp, mark):
        delta = int(stamp)-int(self.times[0])
        if delta < 0 or delta % MINUTE:
            raise ValueError('Completed close absent from feature tape')
        i = delta // MINUTE
        if i >= len(self.times) or int(self.times[i]) != int(stamp):
            raise ValueError('Completed close absent from feature tape')
        if float(mark) != float(self.arrays[symbol+'_mark'][i]):
            raise ValueError('Current own mark differs from hash-bound feature source')
        ready = bool(self.arrays[symbol+'_ready'][i])
        return ready, REASONS[int(self.arrays[symbol+'_reason_code'][i])], {
            k: float(self.arrays[symbol+'_'+k][i]) for k in ('a_down', 'a_up', 'g_down', 'g_up')}

    def __deepcopy__(self, memo):
        # All arrays are immutable, and the tape belongs to the immutable window.
        return self
