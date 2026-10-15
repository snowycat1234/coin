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
    if value['schema'] != 'PUBLIC_2023_SOURCE_RECOVERY_HANDOFF_V1':
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
        name = f'months/2023-{month:02d}.npz'
        with np.load(root / name, allow_pickle=False) as z:
            arrays = {key: z[key] for key in z.files}
            count = len(arrays['times'])
            check_month(arrays, symbols, cursor, count)
            cursor += count * MINUTE
            minutes += count
    if cursor != end or minutes != 525600:
        raise ValueError('COMPLETE_2023_CALENDAR_REQUIRED')
    daily = json.loads((root / 'DAILY.json').read_text())
    events = json.loads((root / 'EVENTS.json').read_text())
    if len(daily) != 1825 or len(events) != 5475:
        raise ValueError('EXACT_SOURCE_RECORD_COUNTS_REQUIRED')
    if any(r['symbol'] not in symbols or not start <= r['event_us'] < end for r in events):
        raise ValueError('ORIGINAL_FUNDING_SYMBOL_CALENDAR_REQUIRED')
    return dict(status='PASS_EXACT_ORIGINAL_2023_SOURCE', months=12,
                minutes_per_symbol=minutes, daily_records=len(daily),
                funding_events=len(events), derived_mark_cells=0,
                financial_runs=0, historical_account_GO=False)


def derive_source_only_warmup(original_cube, output):
    """Select only the original close/clock members, never outcomes or targets."""
    m = load_manifest()
    checked_bytes(original_cube, m['public_sources']['warmup_cube'])
    dest = Path(output)
    if dest.exists():
        raise ValueError('FRESH_WARMUP_DESTINATION_REQUIRED')
    with np.load(original_cube, allow_pickle=False) as z:
        clocks = z['close_available_us'].copy()
        prices = z['close'].copy()
    first = m['warmup_export']['first_available_us']
    last = m['warmup_export']['last_available_us']
    selected = (clocks >= first) & (clocks <= last)
    dest.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(dest, close_available_us=clocks[selected], close=prices[selected])
    checked_bytes(dest, m['warmup_export'])
    return dict(status='PASS_EXACT_SOURCE_ONLY_WARMUP_EXPORT', rows=int(selected.sum()),
                fields=['close_available_us', 'close'], outcomes_selected=[])


def verify_warmup_and_proof(warmup_path, proof_directory):
    m = load_manifest()
    checked_bytes(warmup_path, m['warmup_export'])
    proof_dir = Path(proof_directory)
    pins = m['original200']['artifacts']
    for name, pin in pins.items():
        checked_bytes(proof_dir / name, pin)
    # The pinned checker has been inspected as pure proof/source validation.
    # Compile checked text directly rather than importing a timestamp bytecode cache.
    code = checked_bytes(proof_dir / 'original200_quality.py', pins['original200_quality.py'])
    module = types.ModuleType('reviewed_original200_source_only')
    module.__file__ = str((proof_dir / 'original200_quality.py').resolve())
    exec(compile(code, module.__file__, 'exec'), module.__dict__)
    proof = module.load_original200_proof()
    with np.load(warmup_path, allow_pickle=False) as z:
        if set(z.files) != {'close_available_us', 'close'}:
            raise ValueError('SOURCE_ONLY_WARMUP_FIELDS_REQUIRED')
        clocks, prices = z['close_available_us'].copy(), z['close'].copy()
    decisions = np.arange(*m['calendar_us'], DAY, dtype=np.int64)
    ids = np.searchsorted(clocks, decisions).astype(np.int64)
    identity = proof.validate_projection(decisions, clocks, prices, ids)
    return dict(status='PASS_REVIEWED_365_BY_200_SOURCE_WINDOWS', identity=identity,
                terminal_source_row_covered_by_prior_proof=False,
                historical_account_GO=False)


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
            name = f'months/2023-{month:02d}.npz'
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
                events=json.loads((root/'EVENTS.json').read_text()), minute_blocks=blocks)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source-root')
    p.add_argument('--warmup')
    p.add_argument('--proof-directory')
    p.add_argument('--original-cube')
    p.add_argument('--derive-warmup-output')
    a = p.parse_args()
    results = {}
    if a.original_cube or a.derive_warmup_output:
        if not (a.original_cube and a.derive_warmup_output):
            p.error('Both original-cube and derive-warmup-output are required')
        results['warmup_export'] = derive_source_only_warmup(a.original_cube, a.derive_warmup_output)
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
