"""Immutable source/target-only finite 2024 preparation for frozen nine-cell V3.

No account is constructed by preparation. Original future-looking interpolated
marks are NEVER execution-admitted. A separate causal missing-mark execution
adapter requires independent review and a new exact external root GO.
"""
from __future__ import annotations
from io import BytesIO, StringIO
import csv
import hashlib
import json
from pathlib import Path
from types import MappingProxyType

import numpy as np
import polars as pl
import frozen_grid as g
import historical_entry as h
import native_runtime as n
import missing_mark_adapter_2024 as m
import causal_mark_quality as q

HERE = Path(__file__).resolve().parent
START, END, DAYS, MINUTES = 1704067200000000, 1735689600000000, 366, 527040
PROTOCOL = 'ANNUAL_2024_PROTOCOL.json'
PROTOCOL_SHA256 = '64b4cc35ce77943d0ea5cdbf0ff882aef912bdbcd8fd990510db28bccaf329ed'
LABEL = 'OFFLINE PROXY WITH COARSE QUANTITY SENSITIVITY'
SOURCE_PINS = {
 'public_recovery_package/RECOVERY_MANIFEST.json': (75037, '0f0d3d4d6170e0cdde9c89c6913b92e567161d9b02f7fc1fe8b17378d01befc7'),
 'public_recovery_package/verify_recovered_2024_source.py': (7727, '931b3ff4e96e4c87c1d53a1d42c3adf3b588ab0d013486452ca916a97adbf146'),
 'VERIFIED_SOURCE_RECEIPT.json': (3434, 'b7a2f236f79ae8b850fc9995568bc6b7adcc4444820e316f43d3fcefe5d1dc7d'),
 'SOURCE_WARMUP_CLOSE_ONLY.npz': (16557, '84c0fbcc41f068f7b3066c942efa219625adcd58b7b45d2b7e2e395b8cd7d777'),
 'SOURCE_200DAY_WINDOW_PROOF.json': (99923, 'a7585826f901c08e01ec56505b7b3ab92d8cf7805c26ddd3e5623ba5c5ae8fc0'),
 'INITIAL_PRIOR_SOURCE.json': (1164, 'd0ecab7eb019c141ca218605f1e1e354c12c6d9be400e8eafc5f9e87b5be9ab3'),
 'derived_mark/DERIVED_MARK_OHLC.csv': (1227, '0af6d1cc66bc81afd39582ae4de2b1aa25d9e0031765ce6bce74e917a5577d0c'),
}
RESOURCE_LIMITS = dict(per_case_wall_seconds=600, CPU_threads=1,
 RSS_stop_bytes=2000000000, AS_bytes=4000000000, output_bytes=250000000, maximum_cases=9)
MISSING_OPEN_MS = (1723456920000, 1723456980000)
ARTIFACTS = ('TARGETS.npz', 'TARGET_PROOFS.json', 'EXACT_EXECUTION_EQUALITY.json', 'SOURCE_QUALIFICATION.json', 'CAUSAL_MARK_ADAPTER.json')


def _sha(body):
    return hashlib.sha256(body).hexdigest()


def _json_sha(value):
    return _sha(json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode())


def _protocol():
    return json.loads(h._read_exact(HERE/PROTOCOL, PROTOCOL_SHA256))


def code_identity():
    protocol = _protocol()
    core = h.code_identity()
    if core != protocol['frozen_V3_core_identity']:
        raise ValueError('FROZEN_V3_CORE_IDENTITY_CHANGED')
    profile = h._read_exact(HERE/'sources/QUANTITY_PROFILE.json', protocol['quantity_profile_SHA256'])
    return {**core, 'sources/QUANTITY_PROFILE.json': _sha(profile),
        'annual_entry_2024.py': _sha(Path(__file__).read_bytes()), PROTOCOL: PROTOCOL_SHA256,
        'missing_mark_adapter_2024.py': _sha((HERE/'missing_mark_adapter_2024.py').read_bytes()),
        'causal_mark_quality.py': _sha((HERE/'causal_mark_quality.py').read_bytes())}


def _month_arrays(raw, start, count):
    """Decode only admitted captured bytes, never a filename."""
    with np.load(BytesIO(raw), allow_pickle=False) as z:
        expected = {'times'} | {s+'_'+key for s in g.SYMBOLS for key in ('open','close','quote_volume','mark')}
        if set(z.files) != expected:
            raise ValueError('EXACT_CAPTURED_MONTH_FIELDS_REQUIRED')
        arrays = {key: z[key].copy() for key in z.files}
    t = arrays['times']
    if (t.dtype != np.dtype('int64') or t.shape != (count,) or
            not np.array_equal(t, np.arange(start,start+count*n.MINUTE,n.MINUTE,dtype=np.int64))):
        raise ValueError('EXACT_COMPLETE_2024_MINUTE_CLOCK_REQUIRED')
    for key, values in arrays.items():
        if key == 'times': continue
        if (values.dtype != np.dtype('float64') or values.shape != (count,) or
                not np.isfinite(values).all() or
                ((values < 0).any() if key.endswith('_quote_volume') else (values <= 0).any())):
            raise ValueError('FINITE_POSITIVE_CAPTURED_MARKET_SOURCE_REQUIRED')
    for values in arrays.values(): values.setflags(write=False)
    return arrays


def _validate_warmup_proof(warm_raw, proof, index_sha):
    with np.load(BytesIO(warm_raw), allow_pickle=False) as z:
        if set(z.files) != {'close_available_us','close'}:
            raise ValueError('EXACT_SOURCE_ONLY_WARMUP_FIELDS_REQUIRED')
        t, p = z['close_available_us'].copy(), z['close'].copy()
    if (t.dtype != np.dtype('int64') or t.shape != (566,) or p.dtype != np.dtype('float64')
            or p.shape != (566,5) or t[0] != 1686873600000000 or t[-1] != END
            or not np.all(np.diff(t) == g.DAY) or not np.isfinite(p).all() or (p<=0).any()):
        raise ValueError('EXACT_566_BY5_ACTUAL_CLOSE_EXPORT_REQUIRED')
    if (proof['schema'] != '2024_ACTUAL_SOURCE_ONLY_200DAY_WINDOW_BINDING_V1'
            or proof['calendar_us'] != [START,END] or tuple(proof['symbols']) != g.SYMBOLS
            or proof['source_index_2024_SHA256'] != index_sha
            or proof['actual_source_complete_nonimputed'] is not True
            or proof['derived_mark_cells_excluded_from_daily_features'] != 10
            or len(proof['windows']) != DAYS):
        raise ValueError('EXACT_ORIGINAL200_PROOF_SCOPE_REQUIRED')
    used = set()
    for at, row in zip(np.arange(START,END,g.DAY,dtype=np.int64),proof['windows']):
        k = int(np.searchsorted(t,at)); clocks = t[k-199:k+1]
        if (len(clocks) != 200 or clocks[-1] != at or row['decision_us'] != int(at)
                or row['first_available_us'] != int(clocks[0])
                or row['last_available_us'] != int(at) or row['bar_count'] != 200
                or _sha(p[k-199:k+1].tobytes()) != row['ordered_close_values_SHA256']):
            raise ValueError('EXACT_FULL366_CAUSAL_200_COMPLETED_WINDOWS_REQUIRED')
        used.update(range(k-199,k+1))
    quality = dict(schema='EXACT_2024_CAPTURED_ACTUAL_CLOSE_QUALITY_V1', decisions=366,
        completed_closes_per_window=200, exported_close_rows=566, exported_close_cells=2830,
        used_window_union_rows=len(used), used_window_union_cells=len(used)*5,
        CORE5_mapping='IMPLICIT_EXPORT_ORDER_BOUND_BY_PINNED_PROOF_SYMBOLS_AND_NATIVE_DAILY_BITS',
        imputed=False, actual_source=True, publication_arrival_certified=False,
        proof_SHA256=SOURCE_PINS['SOURCE_200DAY_WINDOW_PROOF.json'][1])
    t.setflags(write=False);p.setflags(write=False)
    return t,p,quality


def _source(source_root):
    """Capture each exact source byte once, then validate only those bytes."""
    root = Path(source_root)
    captured = {name:h._read_exact(root/name,digest,size) for name,(size,digest) in SOURCE_PINS.items()}
    manifest = json.loads(captured['public_recovery_package/RECOVERY_MANIFEST.json'])
    if (manifest['calendar_us'] != [START,END] or tuple(manifest['symbol_order']) != g.SYMBOLS
            or manifest['coverage']['derived_mark_cells'] != 10):
        raise ValueError('EXACT_RECOVERY_MANIFEST_SCOPE_REQUIRED')
    names = {f'months/2024-{m:02d}.npz' for m in range(1,13)} | {'DAILY.json','EVENTS.json','SOURCE_INDEX.json'}
    if set(manifest['prepared_files']) != names:
        raise ValueError('EXACT_12_MONTH_DAILY_EVENT_INDEX_SOURCE_SET_REQUIRED')
    for name,pin in manifest['prepared_files'].items():
        captured['prepared_2024/'+name] = h._read_exact(root/'prepared_2024'/name,pin['SHA256'],pin['bytes'])
    files = {name:dict(SHA256=_sha(body),bytes=len(body)) for name,body in captured.items()}
    index = json.loads(captured['prepared_2024/SOURCE_INDEX.json'])
    if (index['calendar'] != [START,END] or index['days'] != DAYS
            or index['minutes_per_asset'] != MINUTES or index['funding_events'] != 5490
            or tuple(index['symbol_order']) != g.SYMBOLS or len(index['months']) != 12
            or index['derived_mark_cells'] != 10 or tuple(index['original_missing_mark_open_ms']) != MISSING_OPEN_MS
            or index['derived_mark_csv_SHA256'] != files['derived_mark/DERIVED_MARK_OHLC.csv']['SHA256']):
        raise ValueError('EXACT_2024_NATIVE_SOURCE_INDEX_REQUIRED')
    proof = json.loads(captured['SOURCE_200DAY_WINDOW_PROOF.json'])
    t,p,quality = _validate_warmup_proof(captured['SOURCE_WARMUP_CLOSE_ONLY.npz'],proof,
        files['prepared_2024/SOURCE_INDEX.json']['SHA256'])
    daily,events = (json.loads(captured['prepared_2024/'+name]) for name in ('DAILY.json','EVENTS.json'))
    expected_daily = {(s,int(at)) for s in g.SYMBOLS for at in np.arange(START,END,g.DAY,dtype=np.int64)}
    if len(daily) != 1830 or {(r['symbol'],r['close_us']) for r in daily} != expected_daily:
        raise ValueError('EXACT_1830_DAILY_IDENTITIES_REQUIRED')
    for row in daily:
        k,j = int(np.searchsorted(t,row['close_us'])),g.SYMBOLS.index(row['symbol'])
        if np.float64(row['close']).tobytes() != p[k,j].tobytes():
            raise ValueError('NATIVE_DAILY_AND_ACTUAL_CLOSE_EXPORT_BITS_DIFFER')
    if (len(events) != 5490 or len({(r['symbol'],r['event_us']) for r in events}) != 5490
            or any(r['symbol'] not in g.SYMBOLS or not START <= r['event_us'] < END for r in events)):
        raise ValueError('EXACT_5490_ORIGINAL_FUNDING_IDENTITIES_REQUIRED')
    if any(not np.isfinite(r['raw_rate']) or r['reported_interval_hours'] != 8. for r in events):
        raise ValueError('FINITE_RAW_UNCERTIFIED_FUNDING_REQUIRED')
    overlay = list(csv.DictReader(StringIO(captured['derived_mark/DERIVED_MARK_OHLC.csv'].decode())))
    expected_mask = {(s,ms*1000) for s in g.SYMBOLS for ms in MISSING_OPEN_MS}
    if (len(overlay) != 10 or {(r['symbol'],int(r['open_time_ms'])*1000) for r in overlay} != expected_mask
            or any(r['source_missing'] != 'True' or r['method'] != 'TIME_LINEAR_PRIOR_CLOSE_TO_NEXT_OPEN' for r in overlay)):
        raise ValueError('EXACT_TEN_DERIVED_MARK_MASK_AND_RULE_REQUIRED')
    overlay_map = {(r['symbol'],int(r['open_time_ms'])*1000):np.float64(r['close']) for r in overlay}
    cursor = START
    for month,record in enumerate(index['months'],1):
        name=f'months/2024-{month:02d}.npz';pin=manifest['prepared_files'][name]
        if (record['month'] != f'2024-{month:02d}' or record['source_NPZ_SHA256'] != pin['SHA256']
                or record['source_NPZ_bytes'] != pin['bytes']):
            raise ValueError('EXACT_ORDERED_MONTH_IDENTITY_REQUIRED')
        a = _month_arrays(captured['prepared_2024/'+name],cursor,record['minutes'])
        for at in np.arange(cursor+n.DAY,cursor+len(a['times'])*n.MINUTE+1,n.DAY,dtype=np.int64):
            k=int(np.searchsorted(t,at));off=(int(at)-cursor)//n.MINUTE-1
            for j,s in enumerate(g.SYMBOLS):
                if a[s+'_close'][off].tobytes() != p[k,j].tobytes():
                    raise ValueError('CAPTURED_COMPLETED_TRADE_CLOSE_BITS_DIFFER')
        for (s,at),value in overlay_map.items():
            if cursor <= at < cursor+record['minutes']*n.MINUTE:
                off=(at-cursor)//n.MINUTE
                if a[s+'_mark'][off].tobytes() != value.tobytes():
                    raise ValueError('DECLARED_DERIVED_OVERLAY_VALUE_BITS_DIFFER')
        cursor += record['minutes']*n.MINUTE
    if cursor != END: raise ValueError('EXACT_FULL366_NATIVE_CALENDAR_REQUIRED')
    rows = tuple(MappingProxyType(dict(symbol=s,close_us=int(at),available_us=int(at),close=float(p[i,j])))
        for i,at in enumerate(t) if at < END for j,s in enumerate(g.SYMBOLS))
    quality.update(derived_mark_cells=10, derived_mark_overlay_SHA256=files['derived_mark/DERIVED_MARK_OHLC.csv']['SHA256'],
        derived_mark_mask_identity=_json_sha(sorted([s,at] for s,at in expected_mask)),
        original_mark_execution_admitted=False, original_overlay_future_looking=True,
        initial_prior_captured_but_execution_ignored=True, native_venue_certified=False,
        funding_units_and_arrival_certified=False, execution_label=LABEL)
    return index,files,t,p,rows,quality,MappingProxyType(captured)


def _source_identity(files,quality):
    return _json_sha(dict(source_files=files,original200_quality=quality,
        calendar=[START,END],symbols=list(g.SYMBOLS)))


def target_equality_receipt(decisions, targets, covariance, *, source_identity, code):
    """No returns inspected: exact whole-year identity alone permits reuse."""
    d, c = np.asarray(decisions), np.asarray(covariance)
    if (d.dtype != np.dtype('int64') or d.shape != (DAYS,) or d.tobytes() !=
            np.arange(START, END, g.DAY, dtype=np.int64).tobytes()
            or c.dtype != np.dtype('float64') or c.shape != (366,5,5)
            or not np.isfinite(c).all()):
        raise ValueError('EXACT_FULL366_DECISION_AND_COVARIANCE_WITNESS_REQUIRED')
    if (set(targets)!={s+'_'+tier for s,tier in g.CONFIGS}
            or any(not isinstance(v,np.ndarray) or v.dtype!=np.dtype('float64')
                or v.shape!=(DAYS,5) or not np.isfinite(v).all() for v in targets.values())):
        raise ValueError('EXACT_FULL366_NINE_FLOAT64_TARGET_WITNESS_REQUIRED')
    identity = g.target_identities(decisions, targets)
    covariance_sha = _sha(np.asarray(covariance, dtype='<f8').tobytes())
    execution_identity = _json_sha({'code': code, 'covariance_raw_SHA256': covariance_sha,
        'source_identity': source_identity, 'calendar': [START, END], 'cost': 'BASE27',
        'funding': 'RAW_AS_FRACTION_CONDITIONAL_UNCERTIFIED', 'version': n.VERSION,
        'causal_mark_feed_adapter': m.VERSION, 'causal_mark_quality_guard': q.VERSION,
        'coldstart_policy': _protocol()['coldstart_policy']})
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
        comparisons.append({'tier': tier.name, 'complete_366_decision_calendar': True,
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
    return {'schema': 'PRE_RETURN_FULL2024_TARGET_SOURCE_EXECUTION_EQUALITY_V1',
        'requested_matrix_cells': 9, 'unique_execution_jobs': len(groups),
        'execution_groups': groups, 'canonical_representative': 'FIRST_CONFIG_IN_FROZEN_ORDER',
        'no_cross_tier_reuse': True, 'no_outcome_based_reuse': True,
        'independent_alpha_families_claimed': False, 'source_identity': source_identity,
        'execution_identity': execution_identity, 'annual_covariance_raw_SHA256': covariance_sha,
        'decision_raw_SHA256': _sha(np.asarray(decisions, dtype='<i8').tobytes()),
        'target_identity': identity, 'STATIC50_H090_comparisons': comparisons,
        'financial_accounts_created': 0, 'annual_returns_computed': False}




def _mark_adapter_receipt(captured):
    arrays=_month_arrays(captured['prepared_2024/months/2024-08.npz'],1722470400000000,44640)
    projected,sidecar=m.project_month(arrays)
    return dict(schema='SEPARATE_CAUSAL_MARK_FEED_AND_STALE_QUALITY_ADAPTER_V1',
        qualification=m.qualification(),quality_guard_version=q.VERSION,
        original_august_source_SHA256=_sha(captured['prepared_2024/months/2024-08.npz']),
        original_overlay_SHA256=SOURCE_PINS['derived_mark/DERIVED_MARK_OHLC.csv'][1],
        missing_mask_identity=_json_sha(sorted([s,at] for s in g.SYMBOLS for at in m.MISSING_OPENS)),
        original_mark_array_SHA256={s:_sha(arrays[s+'_mark'].tobytes()) for s in g.SYMBOLS},
        causal_estimate_mark_array_SHA256={s:_sha(projected[s+'_mark'].tobytes()) for s in g.SYMBOLS},
        sidecar=[dict(row) for row in sidecar],original_source_files_modified=False,
        source_or_generated_tests_do_not_authorize_actual_2024_account=True)


def prepare_source_only(source_root,output_directory):
    output=Path(output_directory)
    if output.exists(): raise ValueError('EXCLUSIVE_NEW_ANNUAL_SOURCE_PREPARATION_DIRECTORY_REQUIRED')
    code=code_identity();protocol=_protocol()
    index,files,t,p,rows,quality,captured=_source(source_root)
    decisions=np.arange(START,END,g.DAY,dtype=np.int64)
    d,targets,covariance,proofs=g.build_target_grid(p,t,t.copy(),decisions)
    equality=target_equality_receipt(d,targets,covariance,
        source_identity=_source_identity(files,quality),code=code)
    output.mkdir()
    np.savez_compressed(output/'TARGETS.npz',decision_us=d,annual_covariance=covariance,**targets)
    for name,value in [('TARGET_PROOFS.json',proofs),('EXACT_EXECUTION_EQUALITY.json',equality),('SOURCE_QUALIFICATION.json',quality),('CAUSAL_MARK_ADAPTER.json',_mark_adapter_receipt(captured))]:
        (output/name).write_text(json.dumps(value,indent=2,allow_nan=False)+'\n')
    artifacts={name:dict(SHA256=_sha((output/name).read_bytes()),bytes=(output/name).stat().st_size) for name in ARTIFACTS}
    prep=dict(schema='SOURCE_TARGET_ONLY_FIXED_FULL2024_NINE_GRID_PREPARATION_V1',
        status='PREPARED_NO_ANNUAL_ACCOUNT_OR_RETURN_OR_ORIGINAL_MARK_EXECUTION_GO',
        calendar=[START,END],days=DAYS,required_minutes=MINUTES,symbol_order=list(g.SYMBOLS),
        configs=[s+'_'+tier for s,tier in g.CONFIGS],cost='BASE27',code_identity=code,
        protocol_SHA256=PROTOCOL_SHA256,source_files=files,original200_quality=quality,
        public_source_recovery=dict(repository='snowycat1234/coin',
            commit='b3de53d613489ec90f9c70874cdf712cf70db5a8',
            tree='efe3a4c16a938308bfa020c073637f8e20241f77',
            prefix='research/native-2024-source-recovery-20261015',
            publication_or_download_performed_by_this_preparation=False),
        source_identity=equality['source_identity'],artifacts=artifacts,
        target_identity=equality['target_identity'],execution_identity=equality['execution_identity'],
        execution_groups=equality['execution_groups'],requested_matrix_cells=9,
        unique_execution_jobs=equality['unique_execution_jobs'],execution_label=LABEL,
        original_interpolated_mark_execution_admitted=False,
        mark_execution_gate='REQUIRES_SEPARATE_CAUSAL_ADAPTER_INDEPENDENT_REVIEW_AND_NEW_EXACT_ROOT_GO',
        mark_feed_adapter_version=m.VERSION,mark_quality_guard_version=q.VERSION,
        coldstart_policy=protocol['coldstart_policy'],
        riskmatched_excess_method='NOT_PREREGISTERED_NOT_CLAIMED',
        comparison_role='SAME_NOMINAL_BUDGET_ACCOUNT_COMPARISONS_WITH_ACTUAL_RISK_QUALIFICATION',
        accounts_created=0,annual_returns_computed=False,locked_or_holdout_consumed=False,
        annual_execution_requires_new_exact_external_root_GO=True,
        resource_limits=RESOURCE_LIMITS)
    if code_identity()!=code:raise ValueError('CODE_CHANGED_DURING_SOURCE_PREPARATION')
    (output/'PREPARATION.json').write_text(json.dumps(prep,indent=2,allow_nan=False)+'\n')
    return prep


def validate_root_go(preparation_raw,go_raw,expected_go_sha256,*,config):
    if (not isinstance(go_raw,bytes) or not isinstance(expected_go_sha256,str)
            or _sha(go_raw)!=expected_go_sha256):
        raise ValueError('EXACT_EXTERNAL_2024_ROOT_GO_HASH_REQUIRED')
    prep,go=json.loads(preparation_raw),json.loads(go_raw)
    representatives=[group[0] for group in prep['execution_groups']]
    permitted=go.get('permitted_configs')
    if (go.get('schema')!='ROOT_GO_FIXED_FINITE_FULL2024_GRID_V1'
            or go.get('action')!='RUN_FRESH_APPROVED_2024_CANONICAL_JOBS_ONLY'
            or go.get('preparation_SHA256')!=_sha(preparation_raw)
            or go.get('calendar')!=[START,END] or go.get('cost')!='BASE27'
            or go.get('code_identity')!=prep['code_identity']
            or go.get('source_identity')!=prep['source_identity']
            or go.get('artifacts')!=prep['artifacts']
            or go.get('resource_limits')!=RESOURCE_LIMITS or prep['resource_limits']!=RESOURCE_LIMITS
            or not isinstance(permitted,list) or not permitted or len(set(permitted))!=len(permitted)
            or any(key not in representatives for key in permitted) or config not in permitted
            or go.get('locked_or_holdout_consumed') is not False
            or go.get('other_years_authorized') is not False
            or go.get('original_interpolated_mark_execution_admitted') is not False
            or go.get('coldstart_policy')!=_protocol()['coldstart_policy']
            or go.get('mark_feed_adapter_version')!=m.VERSION or go.get('mark_quality_guard_version')!=q.VERSION
            or not isinstance(go.get('independent_review_SHA256'),str)
            or len(go['independent_review_SHA256'])!=64):
        raise ValueError('EXACT_ROOT_GO_FINITE2024_CANONICAL_SCOPE_REQUIRED')
    return prep


def validate_annual_inputs(source_root,preparation_directory,go_raw,expected_go_sha256,*,config):
    """Full source-only positive admission. Returns data, never an account."""
    prepared=Path(preparation_directory);preparation_raw=(prepared/'PREPARATION.json').read_bytes()
    prep=validate_root_go(preparation_raw,go_raw,expected_go_sha256,config=config)
    if (prep['schema']!='SOURCE_TARGET_ONLY_FIXED_FULL2024_NINE_GRID_PREPARATION_V1'
            or prep['code_identity']!=code_identity() or prep['calendar']!=[START,END]
            or prep['days']!=DAYS or prep['required_minutes']!=MINUTES
            or prep['configs']!=[s+'_'+tier for s,tier in g.CONFIGS]
            or set(prep['artifacts'])!=set(ARTIFACTS)
            or prep['original_interpolated_mark_execution_admitted'] is not False
            or prep['coldstart_policy']!=_protocol()['coldstart_policy']):
        raise ValueError('ANNUAL_PREPARATION_CODE_OR_SCOPE_CHANGED')
    artifacts={name:h._read_exact(prepared/name,rec['SHA256'],rec['bytes']) for name,rec in prep['artifacts'].items()}
    index,files,t,p,source_rows,quality,captured=_source(source_root)
    if files!=prep['source_files'] or quality!=prep['original200_quality'] or _source_identity(files,quality)!=prep['source_identity']:
        raise ValueError('ANNUAL_SOURCE_PROJECTION_CHANGED')
    with np.load(BytesIO(artifacts['TARGETS.npz']),allow_pickle=False) as z:
        if set(z.files)!=set(prep['configs'])|{'decision_us','annual_covariance'}:
            raise ValueError('EXACT_NINE_TARGET_ARTIFACT_SCHEMA_REQUIRED')
        decisions,covariance=z['decision_us'].copy(),z['annual_covariance'].copy()
        targets={key:z[key].copy() for key in prep['configs']}
    d,rebuilt,c,rebuilt_proofs=g.build_target_grid(p,t,t.copy(),decisions)
    if (decisions.dtype!=np.dtype('int64') or decisions.tobytes()!=np.arange(START,END,g.DAY,dtype=np.int64).tobytes()
            or covariance.dtype!=np.dtype('float64') or covariance.shape!=(DAYS,5,5)
            or d.tobytes()!=decisions.tobytes() or c.tobytes()!=covariance.tobytes()
            or any(targets[key].dtype!=np.dtype('float64') or targets[key].shape!=(DAYS,5)
                or targets[key].tobytes()!=rebuilt[key].tobytes() for key in targets)):
        raise ValueError('ANNUAL_CANONICAL_TARGET_OR_COVARIANCE_BITS_CHANGED')
    equality=target_equality_receipt(decisions,targets,covariance,source_identity=prep['source_identity'],code=prep['code_identity'])
    if (equality['execution_groups']!=prep['execution_groups'] or equality['execution_identity']!=prep['execution_identity']
            or equality['target_identity']!=prep['target_identity']
            or json.loads(artifacts['EXACT_EXECUTION_EQUALITY.json'])!=equality
            or json.loads(artifacts['SOURCE_QUALIFICATION.json'])!=quality
            or json.loads(artifacts['TARGET_PROOFS.json'])!=rebuilt_proofs
            or json.loads(artifacts['CAUSAL_MARK_ADAPTER.json'])!=_mark_adapter_receipt(captured)):
        raise ValueError('ANNUAL_PRE_RETURN_DEDUP_OR_SOURCE_QUALIFICATION_CHANGED')
    decisions.setflags(write=False);covariance.setflags(write=False)
    for values in targets.values():values.setflags(write=False)
    def blocks():
        expected=START
        for record in index['months']:
            arrays=_month_arrays(captured['prepared_2024/months/'+record['month']+'.npz'],expected,record['minutes'])
            arrays,_=m.project_month(arrays)
            stamps=arrays['times']
            for off in range(0,len(stamps),1440):
                yield dict(times=stamps[off:off+1440],market={s:{key:arrays[s+'_'+key][off:off+1440]
                    for key in ('open','close','quote_volume','mark')} for s in g.SYMBOLS})
            expected+=len(stamps)*n.MINUTE
        if expected!=END:raise ValueError('EXACT_FULL2024_CAPTURED_PROVIDER_END_REQUIRED')
    window=dict(start=START,end=END,symbols=g.SYMBOLS,
        daily=pl.DataFrame(json.loads(captured['prepared_2024/DAILY.json'])),
        events=json.loads(captured['prepared_2024/EVENTS.json']),minute_blocks=blocks,
        derived_mark_cells=10,original_missing_mark_open_ms=MISSING_OPEN_MS,
        original_overlay_future_looking=True,original_overlay_execution_admitted=False,
        causal_mark_adapter=_mark_adapter_receipt(captured))
    return prep,window,source_rows,decisions,targets[config],captured



def _validate_independent_review(preparation_raw,prep,review_raw,expected_review_sha256,go_raw):
    if (not isinstance(review_raw,bytes) or not isinstance(expected_review_sha256,str)
            or _sha(review_raw)!=expected_review_sha256
            or json.loads(go_raw)['independent_review_SHA256']!=expected_review_sha256):
        raise ValueError('EXACT_EXTERNAL_INDEPENDENT_2024_REVIEW_HASH_REQUIRED')
    review=json.loads(review_raw)
    required=dict(schema='INDEPENDENT_FINITE2024_CAUSAL_ADAPTER_REVIEW_V1',
        status='PASS_SOURCE_ONLY_AND_GENERATED_GATES_NO_ACCOUNT_GO',
        preparation_SHA256=_sha(preparation_raw),code_identity=prep['code_identity'],
        source_identity=prep['source_identity'],artifacts=prep['artifacts'],
        execution_identity=prep['execution_identity'],mark_feed_adapter_version=m.VERSION,
        mark_quality_guard_version=q.VERSION,original_interpolated_mark_execution_admitted=False,
        actual_2024_accounts_constructed=0,actual_2024_financial_runs=0)
    if any(review.get(key)!=value for key,value in required.items()):
        raise ValueError('EXACT_INDEPENDENT_2024_REVIEW_SCOPE_REQUIRED')
    return review


def make_annual_case(source_root,preparation_directory,go_raw,expected_go_sha256,*,config,
                     review_raw=None,expected_review_sha256=None):
    """Exact finite positive constructor. NO dispatch/advance/results are called.

    Independent source/generated review is not account GO; the separately
    supplied exact external root GO must bind the same review and prep bytes.
    """
    preparation_raw=(Path(preparation_directory)/'PREPARATION.json').read_bytes()
    prep=validate_root_go(preparation_raw,go_raw,expected_go_sha256,config=config)
    _validate_independent_review(preparation_raw,prep,review_raw,expected_review_sha256,go_raw)
    prep,window,rows,decisions,targets,captured=validate_annual_inputs(source_root,preparation_directory,
        go_raw,expected_go_sha256,config=config)
    if code_identity()!=prep['code_identity']:
        raise ValueError('CODE_CHANGED_DURING_FINITE2024_ADMISSION')
    strategy,tier=next((s,tier) for s,tier in g.CONFIGS if s+'_'+tier==config)
    sim,guard=n._construct_case(window,rows,decisions,targets,tier_name=tier,cost_name='BASE27',
        source_scope='ROOT_ADMITTED_FINITE_SEEN_FULL2024_OFFLINE_PROXY_CAUSAL_MARK_ADAPTER')
    intervals=(q.StaleMarkInterval(start_us=m.FIRST_MISSING_KNOWN,end_us=m.RESUME_AVAILABLE,
        original_genuine_observation_us=m.LAST_GENUINE_AVAILABLE,symbols=g.SYMBOLS),)
    policy_identity=_json_sha(dict(execution_identity=prep['execution_identity'],
        mark_adapter_artifact=prep['artifacts']['CAUSAL_MARK_ADAPTER.json'],
        code_identity=prep['code_identity'],independent_review_SHA256=expected_review_sha256))
    quality_guard=q.CausalMarkQualityGuard(guard,intervals=intervals,
        source_sidecar_sha256=prep['artifacts']['CAUSAL_MARK_ADAPTER.json']['SHA256']).install()
    guard.causal_mark_quality_guard=quality_guard
    sim.meta.update(preparation_SHA256=_sha(preparation_raw),root_GO_SHA256=expected_go_sha256,
        independent_review_SHA256=expected_review_sha256,config=config,execution_label=LABEL,
        execution_identity=prep['execution_identity'],mark_quality_policy_identity=quality_guard.policy_sha256,
        admitted_execution_identity=_json_sha(dict(pre_return_execution_identity=prep['execution_identity'],
            review_bound_execution_identity=policy_identity,quality_guard_policy_SHA256=quality_guard.policy_sha256)),
        original_interpolated_mark_execution_admitted=False,
        coldstart_policy=prep['coldstart_policy'],initial_prior_source_used=False,
        source_target_identity=prep['target_identity']['SHA256_by_config'][config],
        requested_matrix_cells=9,unique_execution_jobs=prep['unique_execution_jobs'],
        reused_matrix_cells=next(group for group in prep['execution_groups'] if group[0]==config),
        comparison_role=prep['comparison_role'],riskmatched_excess_method=prep['riskmatched_excess_method'])
    return sim,guard
