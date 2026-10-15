"""Source-target-only annual preparation and exact finite 2023 constructor.

This separate entry never changes the reviewed V3 strategy/account/guard and
does not run an account on import or preparation. Annual execution requires a
new exact external root GO. Other years and holdouts have no entry here.
"""
from __future__ import annotations
from io import BytesIO
import hashlib
import json
from pathlib import Path
from types import MappingProxyType, ModuleType

import numpy as np
import polars as pl
import frozen_grid as g
import historical_entry as h
import native_runtime as n

HERE = Path(__file__).resolve().parent
START, END = h.START, h.YEAR_END
PROTOCOL = 'ANNUAL_2023_PROTOCOL.json'


def _sha(body):
    return hashlib.sha256(body).hexdigest()


def _json_sha(value):
    return _sha(json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode())


def code_identity():
    identity = h.code_identity()
    identity['annual_entry_2023.py'] = _sha(Path(__file__).read_bytes())
    identity[PROTOCOL] = _sha((HERE / PROTOCOL).read_bytes())
    return identity


def _source(source_root):
    root, index, files, t, p, _, quality_identity, smoke_payloads = h.validate_source(source_root)
    quality_path = root / 'original200_proof/original200_quality.py'
    raw = h._read_exact(quality_path, h.QUALITY_CODE_SHA)
    module = ModuleType('_annual_exact_original200_quality')
    module.__file__ = str(quality_path)
    exec(compile(raw, str(quality_path), 'exec'), module.__dict__)
    quality = module.load_original200_proof()
    rows = []
    for i in np.flatnonzero(t < END):
        for j, symbol in enumerate(g.SYMBOLS):
            row = quality.packet_row(int(t[i]), symbol, float(p[i, j]))
            if (row['complete'] is not True or row['actual_source'] is not True
                    or row['imputed'] is not False or row['available_us'] > row['close_us']):
                raise ValueError('EXACT_ANNUAL_COMPLETED_SOURCE_QUALITY_REQUIRED')
            rows.append({key: row[key] for key in ('symbol', 'close_us', 'available_us', 'close')})
    captured = {}
    for month in index['months']:
        name = month['month']
        captured[name] = (smoke_payloads['JANUARY.npz'] if name == '2023-01' else
            h._read_exact(root / 'prepared_2023/months' / (name + '.npz'),
                month['source_NPZ_SHA256'], month['source_NPZ_bytes']))
    payloads = {'DAILY.json': smoke_payloads['DAILY.json'],
                'EVENTS.json': smoke_payloads['EVENTS.json']}
    daily = json.loads(payloads['DAILY.json'])
    events = json.loads(payloads['EVENTS.json'])
    if len(daily) != 365 * 5 or len(events) != 5475:
        raise ValueError('EXACT365_DAILY_AND5475_ORIGINAL_FUNDING_EVENTS_REQUIRED')
    for row in daily:
        k, j = int(np.searchsorted(t, row['close_us'])), g.SYMBOLS.index(row['symbol'])
        if (not START <= row['close_us'] < END or k >= len(t) or t[k] != row['close_us']
                or np.float64(row['close']).tobytes() != p[k, j].tobytes()):
            raise ValueError('NATIVE_ANNUAL_DAILY_PRICE_BITS_DIFFER_FROM_ORIGINAL200')
    if (any(not START <= row['event_us'] < END for row in events)
            or len({(row['symbol'], row['event_us']) for row in events}) != 5475):
        raise ValueError('EXACT_SIGNED_FUNDING_EVENT_IDENTITIES_REQUIRED')
    return index, files, t, p, tuple(rows), quality_identity, payloads, MappingProxyType(captured)


def _source_identity(files, quality):
    return _json_sha({'source_index_SHA256': h.INDEX_SHA,
        'warmup_SHA256': h.WARMUP_SHA, 'source_files': files, 'original200_quality': quality})


def target_equality_receipt(decisions, targets, covariance, *, source_identity, code):
    """No returns inspected: exact whole-year identity alone permits reuse."""
    d, c = np.asarray(decisions), np.asarray(covariance)
    if (d.dtype != np.dtype('int64') or d.tobytes() !=
            np.arange(START, END, g.DAY, dtype=np.int64).tobytes()
            or c.dtype != np.dtype('float64') or c.shape != (365,5,5)
            or not np.isfinite(c).all()):
        raise ValueError('EXACT_FULL365_DECISION_AND_COVARIANCE_WITNESS_REQUIRED')
    identity = g.target_identities(decisions, targets)
    covariance_sha = _sha(np.asarray(covariance, dtype='<f8').tobytes())
    execution_identity = _json_sha({'code': code, 'covariance_raw_SHA256': covariance_sha,
        'source_identity': source_identity, 'calendar': [START, END], 'cost': 'BASE27',
        'funding': 'RAW_AS_FRACTION_CONDITIONAL_UNCERTIFIED', 'version': n.VERSION})
    groups = g.execution_reuse_groups(decisions, targets, source_identity=source_identity,
        cost_name='BASE27', execution_identity=execution_identity)
    comparisons = []
    for tier in g.TIERS:
        a, b = targets['STATIC50_' + tier.name], targets['H090_' + tier.name]
        exact = a.dtype == b.dtype and a.shape == b.shape and a.tobytes() == b.tobytes()
        difference = np.abs(a-b)
        denominator = np.maximum(np.abs(a), np.abs(b))
        relative = np.divide(difference, denominator, out=np.zeros_like(difference),
            where=denominator > 0)
        different_dates = np.any(a != b, axis=1)
        comparisons.append({'tier': tier.name, 'complete_365_decision_calendar': True,
            'same_tier_account_risk_cost_source_and_covariance': True,
            'STATIC50_raw_SHA256': _sha(a.tobytes()), 'H090_raw_SHA256': _sha(b.tobytes()),
            'entire_target_path_byte_exact': exact, 'execution_reuse_eligible': exact,
            'different_float64_cells': int(np.count_nonzero(a != b)),
            'different_decision_dates': int(np.count_nonzero(different_dates)),
            'different_decision_us': np.asarray(decisions)[different_dates].tolist(),
            'maximum_absolute_target_difference': float(np.max(difference)),
            'maximum_symmetric_relative_target_difference': float(np.max(relative)),
            'relative_difference_definition': 'abs(a-b)/max(abs(a),abs(b)); both-zero is zero',
            'interpretation': 'Floating-point order differences are not independent alpha; native lot/cap/partial thresholds can amplify them.'})
    return {'schema': 'PRE_RETURN_FULL2023_TARGET_SOURCE_EXECUTION_EQUALITY_V1',
        'requested_matrix_cells': 9, 'unique_execution_jobs': len(groups),
        'execution_groups': groups, 'canonical_representative': 'FIRST_CONFIG_IN_FROZEN_ORDER',
        'no_cross_tier_reuse': True, 'no_outcome_based_reuse': True,
        'independent_alpha_families_claimed': False, 'source_identity': source_identity,
        'execution_identity': execution_identity, 'annual_covariance_raw_SHA256': covariance_sha,
        'decision_raw_SHA256': _sha(np.asarray(decisions, dtype='<i8').tobytes()),
        'target_identity': identity, 'STATIC50_H090_comparisons': comparisons,
        'financial_accounts_created': 0, 'annual_returns_computed': False}


def prepare_source_only(source_root, output_directory):
    output = Path(output_directory)
    if output.exists():
        raise ValueError('EXCLUSIVE_NEW_ANNUAL_SOURCE_PREPARATION_DIRECTORY_REQUIRED')
    code = code_identity()
    protocol = json.loads((HERE / PROTOCOL).read_bytes())
    if (protocol['calendar'] != [START, END] or protocol['execution_version'] != n.VERSION
            or protocol['frozen_V3_core_identity'] != h.code_identity()
            or protocol['riskmatched_excess_method'] != 'NOT_PREREGISTERED_NOT_CLAIMED'):
        raise ValueError('EXACT_UNCHANGED_V3_ANNUAL_PROTOCOL_REQUIRED')
    index, files, t, p, rows, quality, payloads, months = _source(source_root)
    decisions = np.arange(START, END, g.DAY, dtype=np.int64)
    d, targets, covariance, proofs = g.build_target_grid(p, t, t.copy(), decisions)
    equality = target_equality_receipt(d, targets, covariance,
        source_identity=_source_identity(files, quality), code=code)
    output.mkdir()
    np.savez_compressed(output / 'TARGETS.npz', decision_us=d, annual_covariance=covariance, **targets)
    (output / 'TARGET_PROOFS.json').write_text(json.dumps(proofs, indent=2, allow_nan=False) + '\n')
    (output / 'EXACT_EXECUTION_EQUALITY.json').write_text(json.dumps(equality, indent=2, allow_nan=False) + '\n')
    artifacts = {name: {'SHA256': _sha((output/name).read_bytes()), 'bytes': (output/name).stat().st_size}
        for name in ('TARGETS.npz', 'TARGET_PROOFS.json', 'EXACT_EXECUTION_EQUALITY.json')}
    manifest = {'schema': 'SOURCE_TARGET_ONLY_FIXED_FULL2023_NINE_GRID_PREPARATION_V1',
        'status': 'PREPARED_NO_ANNUAL_ACCOUNT_OR_RETURN', 'calendar': [START, END],
        'days': 365, 'required_minutes': 525600, 'symbol_order': list(g.SYMBOLS),
        'configs': [s+'_'+tier for s,tier in g.CONFIGS], 'cost': 'BASE27',
        'code_identity': code, 'protocol_SHA256': _sha((HERE/PROTOCOL).read_bytes()),
        'source_index_SHA256': h.INDEX_SHA, 'warmup_SHA256': h.WARMUP_SHA,
        'source_files': files, 'original200_quality': quality,
        'source_identity': equality['source_identity'], 'artifacts': artifacts,
        'target_identity': equality['target_identity'],
        'execution_identity': equality['execution_identity'],
        'execution_groups': equality['execution_groups'],
        'requested_matrix_cells': 9, 'unique_execution_jobs': equality['unique_execution_jobs'],
        'riskmatched_excess_method': 'NOT_PREREGISTERED_NOT_CLAIMED',
        'comparison_role': 'SAME_NOMINAL_BUDGET_ACCOUNT_COMPARISONS_WITH_ACTUAL_RISK_QUALIFICATION',
        'accounts_created': 0, 'annual_returns_computed': False, 'locked_or_holdout_consumed': False,
        'annual_execution_requires_new_exact_external_root_GO': True,
        'resource_limits': protocol['resource_limits']}
    if code_identity() != code:
        raise ValueError('CODE_CHANGED_DURING_ANNUAL_SOURCE_PREPARATION')
    (output/'PREPARATION.json').write_text(json.dumps(manifest, indent=2, allow_nan=False)+'\n')
    return manifest


def validate_root_go(preparation_raw, go_raw, expected_go_sha256, *, config):
    if (not isinstance(go_raw, bytes) or not isinstance(expected_go_sha256, str)
            or _sha(go_raw) != expected_go_sha256):
        raise ValueError('EXACT_EXTERNAL_ANNUAL_ROOT_GO_HASH_REQUIRED')
    prep, go = json.loads(preparation_raw), json.loads(go_raw)
    representatives = [group[0] for group in prep['execution_groups']]
    permitted = go.get('permitted_configs')
    if (go.get('schema') != 'ROOT_GO_FIXED_FINITE_FULL2023_GRID_V1'
            or go.get('action') != 'RUN_FRESH_APPROVED_2023_CANONICAL_JOBS_ONLY'
            or go.get('preparation_SHA256') != _sha(preparation_raw)
            or go.get('calendar') != [START, END] or go.get('cost') != 'BASE27'
            or go.get('resource_limits') != prep['resource_limits']
            or not isinstance(permitted, list) or not permitted or len(set(permitted)) != len(permitted)
            or any(key not in representatives for key in permitted) or config not in permitted
            or go.get('locked_or_holdout_consumed') is not False
            or go.get('other_years_authorized') is not False):
        raise ValueError('EXACT_ROOT_GO_FINITE2023_CANONICAL_JOB_SCOPE_REQUIRED')
    return prep


def make_annual_case(source_root, preparation_directory, go_raw, expected_go_sha256, *, config):
    prepared = Path(preparation_directory)
    preparation_raw = (prepared/'PREPARATION.json').read_bytes()
    prep = validate_root_go(preparation_raw, go_raw, expected_go_sha256, config=config)
    if (prep['schema'] != 'SOURCE_TARGET_ONLY_FIXED_FULL2023_NINE_GRID_PREPARATION_V1'
            or prep['code_identity'] != code_identity() or prep['calendar'] != [START, END]):
        raise ValueError('ANNUAL_PREPARATION_CODE_OR_SCOPE_CHANGED')
    for name, rec in prep['artifacts'].items():
        h._read_exact(prepared/name, rec['SHA256'], rec['bytes'])
    index, files, t, p, source_rows, quality, payloads, months = _source(source_root)
    if (files != prep['source_files'] or quality != prep['original200_quality']
            or _source_identity(files, quality) != prep['source_identity']):
        raise ValueError('ANNUAL_SOURCE_PROJECTION_CHANGED')
    with np.load(BytesIO(h._read_exact(prepared/'TARGETS.npz',
            prep['artifacts']['TARGETS.npz']['SHA256'])), allow_pickle=False) as z:
        decisions, covariance = z['decision_us'].copy(), z['annual_covariance'].copy()
        targets = {key: z[key].copy() for key in prep['configs']}
    d, rebuilt, c, _ = g.build_target_grid(p, t, t.copy(), decisions)
    if (decisions.dtype != np.dtype('int64') or decisions.tobytes() !=
            np.arange(START, END, g.DAY, dtype=np.int64).tobytes()
            or d.tobytes() != decisions.tobytes() or c.tobytes() != covariance.tobytes()
            or any(targets[key].tobytes() != rebuilt[key].tobytes() for key in targets)):
        raise ValueError('ANNUAL_CANONICAL_TARGET_OR_COVARIANCE_BITS_CHANGED')
    equality = target_equality_receipt(decisions, targets, covariance,
        source_identity=prep['source_identity'], code=prep['code_identity'])
    if (equality['execution_groups'] != prep['execution_groups']
            or equality['execution_identity'] != prep['execution_identity']
            or equality['target_identity'] != prep['target_identity']):
        raise ValueError('ANNUAL_PRE_RETURN_DEDUP_IDENTITY_CHANGED')
    def blocks():
        expected = START
        for record in index['months']:
            with np.load(BytesIO(months[record['month']]), allow_pickle=False) as z:
                stamps = z['times'].copy()
                if (stamps.dtype != np.dtype('int64') or len(stamps) != record['minutes']
                        or not np.array_equal(stamps, np.arange(expected,
                            expected+len(stamps)*n.MINUTE, n.MINUTE, dtype=np.int64))):
                    raise ValueError('EXACT_CAPTURED_MONTH_MINUTE_CALENDAR_REQUIRED')
                market = {s: {key: z[s+'_'+key].copy() for key in
                    ('open','close','quote_volume','mark')} for s in g.SYMBOLS}
                for fields in market.values():
                    for key, values in fields.items():
                        if (values.dtype != np.dtype('float64') or values.shape != stamps.shape
                                or not np.isfinite(values).all()
                                or ((values < 0).any() if key == 'quote_volume' else (values <= 0).any())):
                            raise ValueError('EXACT_FINITE_ACTUAL_MONTH_FIELDS_REQUIRED')
                        values.setflags(write=False)
            for offset in range(0,len(stamps),1440):
                yield {'times': stamps[offset:offset+1440], 'market': {
                    s: {key: values[offset:offset+1440] for key,values in fields.items()}
                    for s,fields in market.items()}}
            expected += len(stamps)*n.MINUTE
        if expected != END:
            raise ValueError('EXACT_FULL2023_PROVIDER_END_REQUIRED')
    window = {'start': START, 'end': END, 'symbols': g.SYMBOLS,
        'daily': pl.DataFrame(json.loads(payloads['DAILY.json'])),
        'events': json.loads(payloads['EVENTS.json']), 'minute_blocks': blocks}
    strategy, tier = next((s,tier) for s,tier in g.CONFIGS if s+'_'+tier == config)
    sim, guard = n._construct_case(window, source_rows, decisions, targets[config],
        tier_name=tier, cost_name='BASE27', source_scope='ROOT_ADMITTED_FINITE_SEEN_FULL2023_DEVELOPMENT')
    sim.meta.update(preparation_SHA256=_sha(preparation_raw), root_GO_SHA256=expected_go_sha256,
        config=config, source_index_SHA256=h.INDEX_SHA, original200_quality=quality,
        source_target_identity=prep['target_identity']['SHA256_by_config'][config],
        execution_identity=prep['execution_identity'], requested_matrix_cells=9,
        unique_execution_jobs=prep['unique_execution_jobs'],
        reused_matrix_cells=next(group for group in prep['execution_groups'] if group[0] == config),
        comparison_role=prep['comparison_role'], riskmatched_excess_method=prep['riskmatched_excess_method'])
    return sim, guard
