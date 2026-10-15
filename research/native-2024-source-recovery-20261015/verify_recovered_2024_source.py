"""Offline source verification/binding only. No network, finance, or account imports."""
from __future__ import annotations
import argparse
import hashlib
import json
import types
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
MANIFEST = HERE / 'RECOVERY_MANIFEST.json'
DAY = 86_400_000_000
MINUTE = 60_000_000


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def load_manifest():
    value = json.loads(MANIFEST.read_text())
    if value['schema'] != 'PUBLIC_2024_SOURCE_RECOVERY_HANDOFF_V1':
        raise ValueError('EXACT_HANDOFF_SCHEMA_REQUIRED')
    return value


def checked_bytes(path, expected):
    path = Path(path)
    if path.is_symlink() or not path.is_file():
        raise ValueError('REGULAR_SOURCE_FILE_REQUIRED:' + path.name)
    raw = path.read_bytes()
    if len(raw) != expected['bytes'] or digest(raw) != expected['SHA256']:
        raise ValueError('EXACT_SOURCE_BYTES_REQUIRED:' + path.name)
    return raw


def check_month(arrays, symbols, start, count):
    fields = {'times'} | {s + '_' + k for s in symbols for k in ('open', 'close', 'quote_volume', 'mark')}
    if set(arrays) != fields:
        raise ValueError('EXACT_MONTH_FIELDS_REQUIRED')
    times = arrays['times']
    if times.dtype != np.dtype('int64') or times.shape != (count,):
        raise ValueError('EXACT_MINUTE_CLOCK_TYPE_SHAPE_REQUIRED')
    if not np.array_equal(times, np.arange(start, start + count * MINUTE, MINUTE, dtype=np.int64)):
        raise ValueError('COMPLETE_ORIGINAL_MINUTE_GRID_REQUIRED')
    for field in sorted(fields - {'times'}):
        a = arrays[field]
        if a.dtype != np.dtype('float64') or a.shape != (count,) or not np.isfinite(a).all():
            raise ValueError('FINITE_ORIGINAL_FLOAT64_SOURCE_REQUIRED:' + field)


def verify_prepared_source(source_root):
    m = load_manifest()
    root = Path(source_root)
    for name, pin in m['prepared_files'].items():
        checked_bytes(root / name, pin)
    symbols = tuple(m['symbol_order'])
    start, end = m['calendar_us']
    cursor = start
    minutes = 0
    for month in range(1, 13):
        name = f'months/2024-{month:02d}.npz'
        with np.load(root / name, allow_pickle=False) as z:
            arrays = {key: z[key] for key in z.files}
            count = len(arrays['times'])
            check_month(arrays, symbols, cursor, count)
            cursor += count * MINUTE
            minutes += count
    if cursor != end or minutes != 527040:
        raise ValueError('COMPLETE_2024_CALENDAR_REQUIRED')
    daily = json.loads((root / 'DAILY.json').read_text())
    events = json.loads((root / 'EVENTS.json').read_text())
    if len(daily) != 1830 or len(events) != 5490:
        raise ValueError('EXACT_SOURCE_RECORD_COUNTS_REQUIRED')
    if any(r['symbol'] not in symbols or not start <= r['event_us'] < end for r in events):
        raise ValueError('ORIGINAL_FUNDING_SYMBOL_CALENDAR_REQUIRED')
    return dict(status='PASS_EXACT_ORIGINAL_2024_SOURCE', months=12,
                minutes_per_symbol=minutes, daily_records=len(daily),
                funding_events=len(events), derived_mark_cells=10,
                financial_runs=0, historical_account_GO=False)


def verify_warmup_and_proof(warmup_path, proof_directory=None):
    m = load_manifest()
    checked_bytes(warmup_path, m['warmup_export'])
    proof_dir = Path(proof_directory) if proof_directory else HERE
    proof_pin = m['original200']
    proof = json.loads(checked_bytes(proof_dir / proof_pin['proof_file'], proof_pin))
    with np.load(warmup_path, allow_pickle=False) as z:
        if set(z.files) != {'close_available_us', 'close'}:
            raise ValueError('SOURCE_ONLY_WARMUP_FIELDS_REQUIRED')
        clocks, prices = z['close_available_us'].copy(), z['close'].copy()
    if clocks.dtype != np.dtype('int64') or prices.dtype != np.dtype('float64') or prices.shape != (566, 5):
        raise ValueError('EXACT_WARMUP_SCHEMA_REQUIRED')
    if clocks.shape != (566,) or clocks[0] != 1686873600000000 or clocks[-1] != 1735689600000000 or not np.all(np.diff(clocks) == DAY):
        raise ValueError('COMPLETE_ACTUAL_CLOSE_CALENDAR_REQUIRED')
    if not np.isfinite(prices).all() or not (prices > 0).all():
        raise ValueError('FINITE_POSITIVE_ACTUAL_CLOSES_REQUIRED')
    decisions = np.arange(*m['calendar_us'], DAY, dtype=np.int64)
    if len(proof['windows']) != 366:
        raise ValueError('366_DECISION_WINDOWS_REQUIRED')
    for decision, record in zip(decisions, proof['windows']):
        last = int(np.searchsorted(clocks, decision))
        window = clocks[last-199:last+1]
        if len(window) != 200 or int(window[-1]) != decision or record['decision_us'] != decision or record['first_available_us'] != int(window[0]) or record['last_available_us'] != int(window[-1]) or record['bar_count'] != 200:
            raise ValueError('EXACT_200DAY_WINDOW_REQUIRED')
        if digest(prices[last-199:last+1].tobytes()) != record['ordered_close_values_SHA256']:
            raise ValueError('EXACT_ACTUAL_CLOSE_WINDOW_VALUES_REQUIRED')
    return dict(status='PASS_EXACT_366_BY_200_SOURCE_WINDOWS', decisions=366, window_days=200,
                actual_source_close_cells=2830, historical_account_GO=False)


def verified_source_window(source_root):
    """Return the exact native data interface, without constructing an account.

    The consumer must perform its own separate authorization before calling this
    function. It verifies source values only and grants no historical/account GO.
    Each month is rehashed when the lazy block iterator is consumed.
    """
    verify_prepared_source(source_root)
    m = load_manifest()
    root = Path(source_root)
    symbols = tuple(m['symbol_order'])
    def blocks():
        cursor = m['calendar_us'][0]
        for month in range(1, 13):
            name = f'months/2024-{month:02d}.npz'
            checked_bytes(root / name, m['prepared_files'][name])
            with np.load(root / name, allow_pickle=False) as z:
                arrays = {key: z[key].copy() for key in z.files}
            check_month(arrays, symbols, cursor, len(arrays['times']))
            cursor += len(arrays['times']) * MINUTE
            for off in range(0, len(arrays['times']), 1440):
                yield dict(times=arrays['times'][off:off+1440],
                    market={s:{k:arrays[s+'_'+k][off:off+1440]
                               for k in ('open','close','quote_volume','mark')}
                            for s in symbols})
    return dict(start=m['calendar_us'][0], end=m['calendar_us'][1], symbols=symbols,
                daily=json.loads((root/'DAILY.json').read_text()),
                events=json.loads((root/'EVENTS.json').read_text()), minute_blocks=blocks,
                derived_mark_cells=10, original_missing_mark_open_ms=tuple(m['derived_marks']['original_missing_open_ms']),
                derived_mark_csv_SHA256=m['derived_marks']['exact_original_overlay_SHA256'])


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source-root')
    p.add_argument('--warmup')
    p.add_argument('--proof-directory')
    a = p.parse_args()
    results = {}
    if a.source_root:
        results['prepared_source'] = verify_prepared_source(a.source_root)
    if a.warmup or a.proof_directory:
        if not (a.warmup and a.proof_directory):
            p.error('Both warmup and proof-directory are required')
        results['source_proof'] = verify_warmup_and_proof(a.warmup, a.proof_directory)
    if not results:
        p.error('Specify a source verification or warmup export operation')
    print(json.dumps(results, indent=2, sort_keys=True))

if __name__ == '__main__':
    main()
