"""Positive exact-source constructor for ONE root-approved 2023 three-day grid.

prepare_source_only creates targets/proofs and no account. make_smoke_case needs
an externally supplied exact root-GO hash and binds all source/target/code bytes.
This module has no annual execution entry point and performs no run on import.
"""
from __future__ import annotations
import hashlib
import importlib.util
from io import BytesIO
import json
from pathlib import Path
import struct
from types import ModuleType

import numpy as np
import polars as pl
import frozen_grid as g
import native_runtime as n

HERE = Path(__file__).resolve().parent
START = 1672531200000000
END = START + 3 * g.DAY
YEAR_END = 1704067200000000
INDEX_SHA = '5c88d0022fe185f966266b54c9962b1e632048817d369e00112f72b2071c7251'
WARMUP_SHA = '45a3d6dd8c788a5a721a560736c611073d41fe65648f7b5e408cb07a71e0a75f'
QUALITY_CODE_SHA = '657b96aeba85c769be63b5bf3184953244eba6fdd83d6fc95065761f8aa1b01a'
TRANSPORT_CHECK_SHA = '2b198f3d547a5f99c58a7b9ed9c2e45b74f0a9e8c892d9875382d197c6e31f6c'
CODE_FILES = ('frozen_grid.py', 'native_runtime.py', 'historical_entry.py',
              'SOURCE_PROVENANCE.json', 'NATIVE_SOURCE_PROVENANCE.json', 'FROZEN_SPEC.json')


def _sha(body):
    return hashlib.sha256(body).hexdigest()


def _read_exact(path, digest, size=None):
    path = Path(path)
    if path.is_symlink() or any(p.is_symlink() for p in path.parents) or not path.is_file():
        raise ValueError('ORDINARY_BOUND_SOURCE_FILE_REQUIRED')
    raw = path.read_bytes()
    if _sha(raw) != digest or size is not None and len(raw) != size:
        raise ValueError('EXACT_SOURCE_HASH_OR_SIZE_MISMATCH:' + path.name)
    return raw


def code_identity():
    g.verify_sources(); n._verify_native()
    return {name: _sha((HERE / name).read_bytes()) for name in CODE_FILES}


def validate_source(source_root):
    """Once-per-case exact original transport and original200 projection gate."""
    root = Path(source_root)
    index = json.loads(_read_exact(root / 'prepared_2023/SOURCE_INDEX.json', INDEX_SHA))
    check = json.loads(_read_exact(root / 'INDEPENDENT_ORIGINAL_TRANSPORT_CHECK.json', TRANSPORT_CHECK_SHA))
    if (index['calendar'] != [START, YEAR_END] or index['days'] != 365
            or tuple(index['symbol_order']) != g.SYMBOLS or len(index['months']) != 12
            or check['status'] != 'PASS_ORIGINAL_PURE_INPUT_TRANSPORT_2023'
            or check['result'] != {'source': 'PASS', 'year': 2023, 'months': 12,
                                   'funding_events': 5475, 'derived_mark_cells': 0}):
        raise ValueError('EXACT_RESTORED_ORIGINAL_2023_TRANSPORT_SCOPE')
    records, payloads = {}, {}
    for name, rec in index['files'].items():
        payloads[name] = _read_exact(root / 'prepared_2023' / name, rec['SHA256'], rec['bytes'])
        records['prepared_2023/' + name] = dict(SHA256=rec['SHA256'], bytes=rec['bytes'])
    for month in index['months']:
        rel = 'prepared_2023/months/' + month['month'] + '.npz'
        body = _read_exact(root / rel, month['source_NPZ_SHA256'], month['source_NPZ_bytes'])
        if month['month'] == '2023-01':
            payloads['JANUARY.npz'] = body
        records[rel] = dict(SHA256=month['source_NPZ_SHA256'], bytes=month['source_NPZ_bytes'])
    warm = _read_exact(root / 'SOURCE_WARMUP_CLOSE_ONLY.npz', WARMUP_SHA)
    with np.load(BytesIO(warm), allow_pickle=False) as z:
        if set(z.files) != {'close_available_us', 'close'}:
            raise ValueError('ONLY_VERIFIED_SOURCE_CLOSES_AND_CLOCKS_ALLOWED')
        t, p = z['close_available_us'].copy(), z['close'].copy()
    if t.dtype != np.dtype('int64') or p.dtype != np.dtype('float64') or p.shape != (len(t), 5):
        raise ValueError('ORIGINAL_SOURCE_CLOSE_DTYPE_ORDER_REQUIRED')
    quality_path = root / 'original200_proof/original200_quality.py'
    quality_code = _read_exact(quality_path, QUALITY_CODE_SHA)
    module = ModuleType('_three_tier_exact_original200_quality')
    module.__file__ = str(quality_path)
    exec(compile(quality_code, str(quality_path), 'exec'), module.__dict__)
    quality = module.load_original200_proof()
    year_decisions = np.arange(START, YEAR_END, g.DAY, dtype=np.int64)
    ids = np.searchsorted(t, year_decisions).astype(np.int64)
    quality_identity = quality.validate_projection(year_decisions, t, p, ids)
    # CORE5 order is the pinned source-builder/quality-consumer mapping. The
    # original source cube does not store a symbol_order member.
    mask = t < END
    source_rows = []
    for i in np.flatnonzero(mask):
        for j, symbol in enumerate(g.SYMBOLS):
            record = quality.packet_row(int(t[i]), symbol, float(p[i, j]))
            if (record['complete'] is not True or record['actual_source'] is not True
                    or record['imputed'] is not False or record['available_us'] > record['close_us']):
                raise ValueError('EXACT_COMPLETED_ACTUAL_UNIMPUTED_SOURCE_ROW')
            source_rows.append({key: record[key] for key in ('symbol', 'close_us', 'available_us', 'close')})
    return root, index, records, t, p, source_rows, quality_identity, payloads


def prepare_source_only(source_root, output_directory):
    """No account, market return, model fit, annual score or holdout access."""
    output = Path(output_directory)
    if output.exists():
        raise ValueError('EXCLUSIVE_NEW_SOURCE_PREPARATION_DIRECTORY_REQUIRED')
    code = code_identity()
    root, index, source_files, t, p, rows, quality, payloads = validate_source(source_root)
    d = np.arange(START, END, g.DAY, dtype=np.int64)
    decisions, targets, covariance, proofs = g.build_target_grid(p, t, t.copy(), d)
    daily = json.loads(payloads['DAILY.json'])
    for row in daily:
        if START <= row['close_us'] < END:
            i, j = int(np.searchsorted(t, row['close_us'])), g.SYMBOLS.index(row['symbol'])
            if struct.pack('<d', float(row['close'])) != struct.pack('<d', float(p[i, j])):
                raise ValueError('NATIVE_DAILY_AND_VERIFIED_WARMUP_PRICE_BITS_DIFFER')
    output.mkdir(parents=True)
    np.savez_compressed(output / 'TARGETS.npz', decision_us=decisions,
                        annual_covariance=covariance, **targets)
    (output / 'TARGET_PROOFS.json').write_text(json.dumps(proofs, indent=2, allow_nan=False) + '\n')
    target_identity = g.target_identities(decisions, targets)
    manifest = {
        'schema': 'EXACT_2023_THREE_DAY_TRADITIONAL_GRID_SOURCE_PREPARATION_V1',
        'status': 'SOURCE_TARGET_ONLY_NO_ACCOUNT_NO_ECONOMIC_RESULTS',
        'calendar': [START, END], 'configs': [s + '_' + tier for s, tier in g.CONFIGS],
        'cost': 'BASE27', 'funding_unit': 'RAW_AS_FRACTION_CONDITIONAL_UNCERTIFIED',
        'code_identity': code, 'source_index_SHA256': INDEX_SHA,
        'source_files': source_files, 'warmup_SHA256': WARMUP_SHA,
        'original200_quality': quality, 'symbol_order': list(g.SYMBOLS),
        'symbol_order_authority': 'PINNED_ORIGINAL_SOURCE_BUILDER_AND_ORIGINAL200_CONSUMER_NOT_STORED_NPZ_MEMBER',
        'target_identity': target_identity,
        'artifacts': {name: {'SHA256': _sha((output / name).read_bytes()),
                             'bytes': (output / name).stat().st_size}
                      for name in ('TARGETS.npz', 'TARGET_PROOFS.json')},
        'native_execution_version': n.VERSION, 'grid_version': g.VERSION,
        'new_fits': 0, 'accounts_created': 0, 'financial_years_run': 0,
        'holdout_outcomes_read': False, 'annual_execution_authorized': False,
        'prior_quote': 'UNKNOWN_FRESH_FLAT_DEFER_TO_FIRST_REAL_COMPLETED_MINUTE',
        'resource_limits': {'per_case_wall_seconds': 600, 'CPU_threads': 1,
            'RSS_stop_bytes': 2_000_000_000, 'AS_bytes': 4_000_000_000,
            'output_bytes': 250_000_000, 'maximum_cases': 9}}
    if code_identity() != code:
        raise ValueError('CODE_CHANGED_DURING_SOURCE_PREPARATION')
    (output / 'PREPARATION.json').write_text(json.dumps(manifest, indent=2, allow_nan=False) + '\n')
    return manifest


def validate_root_go(preparation_raw, go_raw, expected_go_sha256, *, config):
    if (not isinstance(go_raw, bytes) or not isinstance(expected_go_sha256, str)
            or _sha(go_raw) != expected_go_sha256):
        raise ValueError('EXTERNAL_EXACT_ROOT_GO_HASH_REQUIRED')
    prep, go = json.loads(preparation_raw), json.loads(go_raw)
    if (go.get('schema') != 'ROOT_GO_2023_THREE_DAY_TRADITIONAL_GRID_V1'
            or go.get('action') != 'RUN_ONE_FRESH_THREE_DAY_CASE_PER_FIXED_CONFIG'
            or go.get('preparation_SHA256') != _sha(preparation_raw)
            or go.get('calendar') != [START, END]
            or go.get('permitted_configs') != prep['configs'] or config not in prep['configs']
            or go.get('resource_limits') != prep['resource_limits']
            or go.get('cost') != 'BASE27' or go.get('annual_execution_authorized') is not False
            or go.get('locked_or_holdout_consumed') is not False):
        raise ValueError('EXACT_BOUNDED_THREE_DAY_ROOT_GO_SCOPE_REQUIRED')
    return prep


def make_smoke_case(source_root, preparation_directory, go_raw, expected_go_sha256, *, config):
    """Positive real-data constructor, only after exact source/code/GO checks."""
    prepared = Path(preparation_directory)
    raw = (prepared / 'PREPARATION.json').read_bytes()
    prep = validate_root_go(raw, go_raw, expected_go_sha256, config=config)
    if (prep.get('schema') != 'EXACT_2023_THREE_DAY_TRADITIONAL_GRID_SOURCE_PREPARATION_V1'
            or prep['code_identity'] != code_identity() or prep['native_execution_version'] != n.VERSION
            or prep['grid_version'] != g.VERSION or prep['calendar'] != [START, END]):
        raise ValueError('PREPARATION_CODE_POLICY_OR_CALENDAR_CHANGED')
    for name, rec in prep['artifacts'].items():
        _read_exact(prepared / name, rec['SHA256'], rec['bytes'])
    root, index, source_files, t, p, source_rows, quality, payloads = validate_source(source_root)
    if source_files != prep['source_files'] or quality != prep['original200_quality']:
        raise ValueError('SOURCE_OR_ORIGINAL200_PROJECTION_CHANGED')
    with np.load(prepared / 'TARGETS.npz', allow_pickle=False) as z:
        decisions, covariance = z['decision_us'].copy(), z['annual_covariance'].copy()
        targets = {key: z[key].copy() for key in prep['configs']}
    rebuilt_d, rebuilt, rebuilt_c, _ = g.build_target_grid(p, t, t.copy(), decisions)
    if (not np.array_equal(rebuilt_d, decisions) or not np.array_equal(rebuilt_c, covariance)
            or any(not np.array_equal(rebuilt[key], targets[key]) for key in targets)
            or g.target_identities(decisions, targets) != prep['target_identity']):
        raise ValueError('CANONICAL_TARGET_OR_COVARIANCE_REPRODUCTION_CHANGED')
    daily = [r for r in json.loads(payloads['DAILY.json'])
             if START <= r['close_us'] < END]
    events = [r for r in json.loads(payloads['EVENTS.json'])
              if START <= r['event_us'] < END]
    month = index['months'][0]
    def blocks():
        # The entire source file was verified once at admission. Array loading
        # consumes those captured immutable bytes, never a later mutable path.
        with np.load(BytesIO(payloads['JANUARY.npz']), allow_pickle=False) as z:
            times = z['times'].copy()
            select = (times >= START) & (times < END)
            if not np.array_equal(times[select], np.arange(START, END, n.MINUTE, dtype=np.int64)):
                raise ValueError('EXACT_THREE_DAY_NATIVE_MINUTE_CALENDAR')
            market = {s: {key: z[s + '_' + key][select].copy()
                for key in ('open', 'close', 'quote_volume', 'mark')} for s in g.SYMBOLS}
        for offset in range(0, 3 * 1440, 1440):
            yield {'times': times[select][offset:offset+1440], 'market': {
                s: {key: values[offset:offset+1440] for key, values in fields.items()}
                for s, fields in market.items()}}
    window = {'start': START, 'end': END, 'symbols': g.SYMBOLS,
              'daily': pl.DataFrame(daily), 'events': events, 'minute_blocks': blocks}
    strategy, tier = next((s, tier) for s, tier in g.CONFIGS if s + '_' + tier == config)
    sim, guard = n._construct_case(window, source_rows, decisions, targets[config],
        tier_name=tier, cost_name='BASE27', source_scope='ROOT_ADMITTED_SEEN_2023_THREE_DAY_SMOKE')
    sim.meta.update(preparation_SHA256=_sha(raw), root_GO_SHA256=expected_go_sha256,
        config=config, source_index_SHA256=INDEX_SHA, original200_quality=quality,
        source_target_identity=prep['target_identity']['SHA256_by_config'][config])
    return sim, guard
