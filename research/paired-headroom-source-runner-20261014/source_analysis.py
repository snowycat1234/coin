"""Fixed whole-calendar coefficients and causal checks. No q/E or wallet inputs."""
from __future__ import annotations
import csv
import hashlib
import json
from pathlib import Path
import numpy as np

MINUTE = 60_000_000
DAY = 86_400_000_000
FIELDS = ('long_hurdle', 'short_hurdle', 'aligned_independent_long_hurdle',
          'aligned_independent_short_hurdle', 'legacy_independent_long_hurdle',
          'legacy_independent_short_hurdle')
REASONS = ('READY', 'LESS_THAN_30D', 'MISSING_OR_DUPLICATE_MINUTE',
           'NONPOSITIVE_OR_MISSING_MARK', 'NONPOSITIVE_OR_MISSING_TRADE_OPEN', 'DERIVED_MARK_IN_WINDOW')


def array_binding(array):
    a = np.ascontiguousarray(array)
    return {'dtype': a.dtype.str, 'shape': list(a.shape), 'SHA256': hashlib.sha256(a.tobytes()).hexdigest()}


def load_symbol(adapter, case, source_root, symbol):
    """Exact inherited file/schema primitives; only mark/open retained per symbol."""
    pieces = {'times': [], 'mark': [], 'open': []}
    expected = case['calendar'][0]
    for rec in case['months']:
        p = adapter.check_file(source_root, 'months/' + rec['month'] + '.npz',
                               {'SHA256': rec['source_NPZ_SHA256'], 'bytes': rec['source_NPZ_bytes']})
        with np.load(p, allow_pickle=False) as z:
            adapter.schema(z, expected, rec['minutes'], full_ohlc=False)
            pieces['times'].append(z['times'].copy())
            pieces['mark'].append(z[symbol + '_mark'].copy())
            pieces['open'].append(z[symbol + '_open'].copy())
        expected += rec['minutes'] * MINUTE
    if expected != case['calendar'][1] or len(case['months']) != 12:
        raise ValueError('FULL_YEAR_COVERAGE_REQUIRED')
    return {name: np.concatenate(parts) for name, parts in pieces.items()}


def derived_mask(year, times, symbol, derived_csv, pins, sha):
    mask = np.zeros(len(times), dtype=bool)
    if year != 2024:
        if derived_csv is not None:
            raise ValueError('DERIVED_OVERLAY_ONLY_FOR_ORIGINAL2024')
        return mask
    rec = pins['derived_csv2024']
    if derived_csv is None or sha(derived_csv) != rec['SHA256']:
        raise ValueError('EXACT_ORIGINAL2024_DERIVED_CSV_REQUIRED')
    with Path(derived_csv).open() as f:
        rows = list(csv.DictReader(f))
    from_symbols = ('BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'XRPUSDT', 'DOGEUSDT')
    coordinates = {(r['symbol'], int(r['open_time_ms'])) for r in rows}
    wanted = {(s, t) for s in from_symbols for t in rec['open_time_ms']}
    if len(rows) != rec['cells'] or coordinates != wanted or any(r['source_missing'] != 'True' for r in rows):
        raise ValueError('ORIGINAL_DERIVED_COORDINATES_REQUIRED')
    for row in rows:
        if row['symbol'] == symbol:
            stamp = int(row['open_time_ms']) * 1000
            i = int(np.searchsorted(times, stamp))
            if i >= len(times) or int(times[i]) != stamp:
                raise ValueError('DERIVED_CLOCK_NOT_IN_SOURCE')
            mask[i] = True
    return mask


def equal_prefix(left, right, stop):
    if set(left) != set(right):
        raise ValueError('FEATURE_FIELDS_CHANGED')
    for name in left:
        a, b = left[name][:stop], right[name][:stop]
        if a.dtype.kind == 'f':
            okay = np.array_equal(a, b, equal_nan=True)
        else:
            okay = np.array_equal(a, b)
        if not okay:
            raise ValueError('CAUSAL_PREFIX_DIFFERENCE:' + name)


def causal_checks(paired, source, derived, full):
    n = len(source['times'])
    cuts = sorted({min(n, paired.WINDOW + 1440), max(1, n // 2), max(1, n - 1440)})
    checks = []
    for stop in cuts:
        prefix = paired.features(source['times'][:stop], source['mark'][:stop],
                                 source['open'][:stop], derived[:stop])
        equal_prefix(full, prefix, stop)
        clocks, marks, opens, flags = [a.copy() for a in (source['times'], source['mark'], source['open'], derived)]
        clocks[stop:] += 7 * MINUTE
        marks[stop:] *= 1.7
        opens[stop:] *= .6
        flags[stop:] = True
        changed = paired.features(clocks, marks, opens, flags)
        equal_prefix(full, changed, stop)
        checks.append({'prefix_rows': stop, 'prefix_close_us': int(source['times'][stop - 1] + MINUTE),
                       'standalone_prefix_equal': True, 'future_clock_price_mask_perturbation_equal': True})
    return checks


def finite_stats(values):
    a = np.asarray(values)
    if not len(a):
        return {'count': 0, 'minimum': None, 'maximum': None, 'mean': None}
    if not np.isfinite(a).all():
        raise ValueError('NONFINITE_READY_COEFFICIENT')
    return {'count': int(len(a)), 'minimum': float(a.min()), 'maximum': float(a.max()),
            'mean': float(np.sum(a / len(a)))}


def difference_stats(left, right):
    delta = left - right
    stats = finite_stats(delta)
    stats.update(exact_equal=int(np.count_nonzero(delta == 0)),
                 left_greater=int(np.count_nonzero(delta > 0)),
                 left_less=int(np.count_nonzero(delta < 0)),
                 max_abs=float(np.max(np.abs(delta))) if len(delta) else None)
    stats['absolute_delta_quantiles'] = ({str(q): float(np.quantile(np.abs(delta), q))
                                        for q in (.5, .95, .99)} if len(delta) else None)
    return stats


def summarize(times, feature):
    ready = feature['ready']
    observed_reasons = set(map(str, np.unique(feature['reason'])))
    # Use the original reason values verbatim, never map an unknown value to READY.
    reason_counts = {name: int(np.count_nonzero(feature['reason'] == name)) for name in sorted(observed_reasons)}
    for field in FIELDS:
        if not np.isfinite(feature[field][ready]).all() or not np.isnan(feature[field][~ready]).all():
            raise ValueError('ORIGINAL_READY_NAN_CONTRACT')
    result = {'rows': int(len(times)), 'ready_rows': int(ready.sum()), 'reason_counts': reason_counts,
              'first_open_us': int(times[0]), 'last_close_us': int(times[-1] + MINUTE),
              'coefficients': {name: finite_stats(feature[name][ready]) for name in FIELDS}, 'differences': {}}
    for direction in ('long', 'short'):
        legacy = feature['legacy_independent_' + direction + '_hurdle'][ready]
        aligned = feature['aligned_independent_' + direction + '_hurdle'][ready]
        paired = feature[direction + '_hurdle'][ready]
        result['differences'][direction] = {
            'alignment_legacy_minus_aligned': difference_stats(legacy, aligned),
            'coupling_aligned_minus_paired': difference_stats(aligned, paired),
            'combined_legacy_minus_paired': difference_stats(legacy, paired)}
    return result


def daily_summaries(times, feature):
    if len(times) % 1440:
        raise ValueError('COMPLETE_UTC_DAYS_REQUIRED')
    return [summarize(times[i:i + 1440], {k: v[i:i + 1440] for k, v in feature.items()})
            for i in range(0, len(times), 1440)]


def lossless_runs(feature):
    """Exact joint state runs; no rounding, tolerance, scenario sampling or truncation."""
    n = len(feature['ready'])
    reasons, codes = np.unique(feature['reason'], return_inverse=True)
    changed = np.zeros(n, dtype=bool)
    changed[0] = True
    changed[1:] = (feature['ready'][1:] != feature['ready'][:-1]) | (codes[1:] != codes[:-1])
    for field in FIELDS:
        a = feature[field]
        # All NOT_READY NaNs represent the same semantic missing state. Preserve
        # exact bits for READY floats, including signed zero.
        bits = a.view(np.uint64)
        changed[1:] |= feature['ready'][1:] & (bits[1:] != bits[:-1])
    starts = np.flatnonzero(changed).astype(np.int64)
    ends = np.r_[starts[1:], n].astype(np.int64)
    arrays = {'start_row': starts, 'end_row_exclusive': ends,
              'ready': feature['ready'][starts], 'reason_code': codes[starts].astype(np.uint8),
              'reason_values': reasons}
    arrays.update({field: feature[field][starts] for field in FIELDS})
    return arrays


def decode_runs(arrays, n):
    lengths = arrays['end_row_exclusive'] - arrays['start_row']
    if (int(arrays['start_row'][0]) != 0 or int(arrays['end_row_exclusive'][-1]) != n
            or np.any(lengths <= 0) or not np.array_equal(arrays['start_row'][1:], arrays['end_row_exclusive'][:-1])):
        raise ValueError('LOSSLESS_RUN_COVERAGE')
    out = {'ready': np.repeat(arrays['ready'], lengths),
           'reason': np.repeat(arrays['reason_values'][arrays['reason_code']], lengths)}
    out.update({field: np.repeat(arrays[field], lengths) for field in FIELDS})
    return out


def validate_saved_archive(path, feature, reference, expected_sha, sha):
    """Verify the actual persisted bytes, schema, coverage and READY float bits."""
    if sha(path) != expected_sha:
        raise ValueError('SAVED_ARCHIVE_HASH_CHANGED')
    with np.load(path, allow_pickle=False) as archive:
        if set(archive.files) != set(reference):
            raise ValueError('SAVED_ARCHIVE_FIELDS_CHANGED')
        saved = {name: archive[name].copy() for name in archive.files}
    for name, expected in reference.items():
        value = saved[name]
        if value.dtype != expected.dtype or value.shape != expected.shape:
            raise ValueError('SAVED_ARCHIVE_SCHEMA_CHANGED:' + name)
        if value.dtype.kind != 'f' and not np.array_equal(value, expected):
            raise ValueError('SAVED_ARCHIVE_STATE_CHANGED:' + name)
    decoded = decode_runs(saved, len(feature['ready']))
    if (not np.array_equal(decoded['ready'], feature['ready'])
            or not np.array_equal(decoded['reason'], feature['reason'])):
        raise ValueError('SAVED_ARCHIVE_MASK_REASON_CHANGED')
    ready = feature['ready']
    for field in FIELDS:
        actual, expected = decoded[field], feature[field]
        if (not np.array_equal(actual[ready].view(np.uint64), expected[ready].view(np.uint64))
                or not np.isnan(actual[~ready]).all() or not np.isnan(expected[~ready]).all()):
            raise ValueError('SAVED_ARCHIVE_COEFFICIENT_BITS_OR_MISSING_CHANGED:' + field)
    if sha(path) != expected_sha:
        raise ValueError('SAVED_ARCHIVE_HASH_CHANGED_DURING_READ')
    return True
