"""Separately gated original D Apr2–Dec31 partial2021 SOURCE-only entry.

Old2023/24 GO hashes are metadata, never authority or required private bodies.
Preparation has no accounts, execution scopes, provider iteration, or processes.
Only exact new independent review plus external root GO can mint a fresh scope.
"""
from dataclasses import dataclass,field
from io import BytesIO
import json
from pathlib import Path
import sys
from types import MappingProxyType
from collections.abc import Mapping
import numpy as np
import polars as pl
import partial_source as s
HERE=s.HERE;ROOT=s.ROOT
if Path(s.__file__).resolve()!=HERE/'partial_source.py':raise ValueError('EXACT_LOCAL_2021_SOURCE_ADAPTER_REQUIRED')
_sha,_json_sha,_canonical,_immutable,_plain=s.sha,s.jsha,s.canonical,s.immutable,s.plain
_same=lambda a,b:_canonical(a)==_canonical(b)
_ordinary=lambda p:Path(p).read_bytes() if Path(p).is_file() and not Path(p).is_symlink() else (_ for _ in ()).throw(ValueError('ORDINARY_BOUND_FILE_REQUIRED'))
POLICY_VARIANT='GUARD50_EXIT_ONLY';MODES=(POLICY_VARIANT,);COST='BASE27'
SETTLEMENT_MODE='CONDITIONAL_COLLATERAL_FORFEITURE'
LABEL='OFFLINE PROXY WITH COARSE QUANTITY SENSITIVITY; PARTIAL2021 DEV'
POLICY_VERSION='ORIGINAL_D_PARTIAL2021_APR2_DEC31_NINE_DEV_V1'
SOURCE_SCOPE='EXACT_ROOT_ADMITTED_FRESH_ORIGINAL_D_PARTIAL2021_APR2_DEC31_V1'
PREPARATION_SCHEMA='SOURCE_TARGET_ONLY_ORIGINAL_D_PARTIAL2021_NINE_V1'
REVIEW_SCHEMA='INDEPENDENT_ORIGINAL_D_PARTIAL2021_SOURCE_GENERATED_REVIEW_V1'
GO_SCHEMA='ROOT_GO_ORIGINAL_D_PARTIAL2021_EXACT_NINE_V1'
ACTION='RUN_FRESH_EXACT_NINE_ORIGINAL_D_PARTIAL2021_ONLY'
MANIFEST_NAME='FROZEN_NINE_CELL_MANIFEST.json'
MANIFEST_SHA256='03b8016fd98fc2bc5c60db5800672a05a558351b4cfef760dfa34014aa5be85c'
FIRST_TRANCHE=REMAINING_TRANCHE='EXACT_NINE_PARTIAL2021_D'
YEARS=(2021,);SOURCE_ROOTS={2021:s.SOURCE_ROOT}
SOURCE_TARGETS=HERE/'source_targets_attempt002'
_SCOPE_SEAL=object()
SOURCE_REVIEW_SHA='0644ba6e67e704539ad3c4240fb84c35abb24716a57e109120e8c285ac5e7bab'

# Metadata only: no runtime reads of these private historical authorizations.
OLD_EVIDENCE_HASHES={
 '2023_original_GO_pilot_SHA256':'6930d9450279f652db8f6b644ec00043a6cedb166410191859c2f666d62f37ef',
 '2023_original_GO_remaining_SHA256':'c46cc26b8039c372ec973557a9b6a2fd8b4b0f80f354612795b1da9eb60489e0',
 '2024_original_GO_pilot_SHA256':'a6a3f4b36a7fe008d99a140b32bc41a86f14c8bae281f068aac3b684c8a43851',
 '2024_original_GO_remaining_SHA256':'ab8f768beef74b0d45d8231a743fa5d25a919a6230cb166a71fd56d891e9a4b7'}

def _object(raw,error):
    if type(raw) is not bytes:raise ValueError(error)
    def pairs(values):
        out={}
        for k,v in values:
            if k in out:raise ValueError('DUPLICATE_JSON_KEY')
            out[k]=v
        return out
    try:v=json.loads(raw,object_pairs_hook=pairs,parse_constant=lambda x:(_ for _ in ()).throw(ValueError('NONFINITE_JSON')))
    except (ValueError,TypeError,UnicodeError):raise ValueError(error)
    if type(v) is not dict:raise ValueError(error)
    return v

def _exact(raw,sha,error):
    if type(raw) is not bytes or type(sha) is not str or len(sha)!=64 or _sha(raw)!=sha:raise ValueError(error)
    return raw

def frozen_manifest():
    m=_object(s.exact(HERE/MANIFEST_NAME,MANIFEST_SHA256),'EXACT_PARTIAL2021_MANIFEST_REQUIRED')
    expected=['2021_'+c+'_APR2_DEC31_D' for c in s.CONFIGS]
    if (m['years']!=[2021] or [c['cell_id'] for c in m['cells']]!=expected or m['new_cell_count']!=9
            or m['calendar']!=[s.START,s.END] or m['alias_mapping']!={} or m['partial_DEV'] is not True
            or m['financial_policy_changes_allowed'] is not False):raise ValueError('EXACT_NINE_ORIGINAL_D_PARTIAL2021_ONLY')
    return m

def cell_descriptor(cell_id):
    for c in frozen_manifest()['cells']:
        if type(cell_id) is str and c['cell_id']==cell_id:return c
    raise ValueError('EXACT_NEW_2021_ORIGINAL_D_PARTIAL_CELL_REQUIRED')

def tranche_cells(tranche=FIRST_TRANCHE):
    if tranche!=FIRST_TRANCHE:raise ValueError('EXACT_NINE_PARTIAL2021_TRANCHE_REQUIRED')
    return tuple(c['cell_id'] for c in frozen_manifest()['cells'])

RESOURCE_LIMITS=frozen_manifest()['resource_design']
RESOURCE_EXECUTION_CONTRACT=dict(interpretation='ONE_ASSIGNED_CPU_AND_MAX_ONE_THREAD_PER_NUMERICAL_COMPUTE_POOL',
    assigned_CPUs_per_worker=1,numerical_compute_pool_threads_max=1,OS_watchdog_IO_and_runtime_helper_threads_allowed=True,
    actual_OS_task_count_and_affinities_must_be_reported=True,every_OS_task_affinity_must_equal_worker_single_assigned_CPU=True,
    affinity_is_applied_before_numerical_imports=True,two_affinity_CPUs_do_not_certify_two_full_CPU_quotas=True,
    quota_visibility='UNVERIFIED_HOST_OBSERVATIONS_ONLY',serial_fallback_before_new_launch=True)
LAUNCH_CLAIM_CONTRACT=dict(launch_claim_schema='CANONICAL_IMMUTABLE_MANIFEST_CELL_LAUNCH_CLAIM_V1',
    launch_claim_registry_relative=HERE.name+'/EXECUTION_CLAIMS',launch_claim_key='manifest_SHA256/cell_id.json',
    launch_claim_atomic_exclusive_create=True,launch_claim_never_automatically_cleared=True,existing_controller_output_refused=True,
    scheduling_resume_supported=False,cross_output_duplicate_launch_forbidden=True,
    claim_created_only_after_exact_GO_review_source_code_and_resource_validation=True,
    claim_binds='MANIFEST_CELL_YEAR_CONFIG_SOURCE_TARGET_PREPARATION_CODE_GO_REVIEW_CONTROLLER_PID_OUTPUT')
GLOBAL_CONTROLLER_LEASE_CONTRACT=dict(schema='CANONICAL_MANIFEST_GLOBAL_CONTROLLER_FLOCK_V1',registry_relative=HERE.name+'/EXECUTION_CLAIMS',
    key='manifest_SHA256/CONTROLLER_LEASE.lock',exclusive_nonblocking_flock=True,one_controller_across_exact_nine_cells=True,
    lease_held_until_all_child_processes_exit=True,lease_FD_inherited_by_workers=True,existing_lease_refuses_new_controller=True,
    real_lease_created_only_after_external_GO_review_source_code_and_resource_validation=True)

def preserved_evidence_identity():return dict(OLD_EVIDENCE_HASHES)

def code_identity():
    m=frozen_manifest();raw=s.exact(HERE/'DEPENDENCY_PINS.json',m['dependency_pins_SHA256']);pins=json.loads(raw)
    result={name:_sha(s.exact(ROOT/name,p['SHA256'],p['bytes'])) for name,p in pins.items()}
    for name in ('partial_source.py','partial_d.py','partial_entry.py','run_partial.py','test_partial.py',
                 'build_source_packet.py','profile_generated.py','test_generated_d.py','test_generated_native40.py','test_generated_runner.py',
                 'PHASE_PLAN.md',MANIFEST_NAME,'DEPENDENCY_PINS.json','SOURCE_COMPLETION_REVIEW.json'):
        result[HERE.name+'/'+name]=_sha(_ordinary(HERE/name))
    for name in ('test_native_runtime.py','test_frozen_grid.py'):
        result['traditional_three_tier_freeze_20261015/'+name]=_sha(_ordinary(s.FROZEN/name))
    s.exact(HERE/'SOURCE_COMPLETION_REVIEW.json',SOURCE_REVIEW_SHA)
    return result

def _coldstart_policy(year):
    if year!=2021:raise ValueError('ONLY_PARTIAL2021_COLDSTART_ALLOWED')
    return dict(version='UNCHANGED_NATIVE_FRESH_FLAT_UNKNOWN_PRIOR',initial_signal_us=s.START,
        available_prior_source_used=False,first_real_completed_quote_us=s.START+s.MINUTE,
        earliest_initial_increase_admission_us=s.START+s.MINUTE+1,
        all_funding_ownership_from_current_native_actual_quantity=True,old_Jan1_source_ownership_flag_used=False)

def _policy(code):
    return dict(version=POLICY_VERSION,source_scope=SOURCE_SCOPE,manifest_SHA256=MANIFEST_SHA256,code_identity=code,
        policy_variant=POLICY_VARIANT,cost=COST,settlement_mode=SETTLEMENT_MODE,ordered_cells=list(tranche_cells()),
        calendar=[s.START,s.END],partial_DEV=True,annualization_allowed=False,wallet_compounding_allowed=False,
        source_completion_independent_review_SHA256=SOURCE_REVIEW_SHA,source_completion_SHA256=s.FINAL_PINS,
        initial_shared_wallet_USDT='10000',common_free_cash_floor_USDT='1000',common_isolated_margin_ceiling_USDT='8500',leverage=1,
        D_has_no_topup_or_internal_margin_transfer=True,D_warning_action='NATIVE_PAID_FULL_ACTUAL_POSITION_EXIT_NO_TOPUP',
        D_warning_threshold='KNOWN_FRESH_ISOLATED_EQUITY_LE_HALF_ISOLATED_BALANCE',
        mark_quality_exit_policy_version='UNKNOWN_MARK_NO_NEW_EXIT_V2',unknown_or_stale_quality_itself_creates_new_warning_exit=False,
        ordinary_new_strategy_reductions_and_native_exits_preserved=True,legitimate_preexisting_pending_exit_preserved=True,
        native_risk_and_all_sameclock_funding_before_D_monitor=True,original_daily_signal_latency=True,
        terminal_signal_us=s.END-61*s.MINUTE,terminal_eligible_open_range=[s.END-60*s.MINUTE,s.END-s.MINUTE],
        source_end_plus_one_witness_is_execution_authority=False,coldstart=_coldstart_policy(2021),
        original_strategy_and_fixed_tier_definitions_unchanged=True,forecast_monitor_policy_used=False,
        nominal_tier_equality_is_realized_risk_matching=False,actual_held_exposure_and_forecast_overshoots_required=True,
        funding_units='RAW_AS_FRACTION_CONDITIONAL_UNCERTIFIED',historical_exchange_certification=False,
        native40_chronological_reconstruction_authoritative=True,raw100_delta_residual_preserved=True,
        conditional_forfeiture_is_actual_paid_flat=False,resource_limits=RESOURCE_LIMITS,
        resource_execution_contract=RESOURCE_EXECUTION_CONTRACT,launch_claim_contract=LAUNCH_CLAIM_CONTRACT,
        global_controller_lease_contract=GLOBAL_CONTROLLER_LEASE_CONTRACT,old_GO_is_new_authority=False,
        old_GO_private_runtime_bodies_required=False,fresh_genesis_only=True,automatic_retry_authorized=False,
        halted_snapshot_resume_authorized=False,all_years_seen_development=True,candidate_threshold_or_performance_selection_allowed=False,
        other_years_or_2025_authorized=False,locked_or_holdout_consumed=False,publication_authorized=False)

def _source_roots(roots):
    if not isinstance(roots,Mapping) or set(roots)!={2021} or any(type(k) is not int for k in roots):raise ValueError('EXACT2021_SOURCE_ROOT_MAPPING_REQUIRED')
    return {2021:Path(roots[2021]).resolve()}

# Same immutable native input binding schema as original expansion, with exact
# partial provider type and calendar. No original module or globals are patched.
def _input_binding(cell, window, source_rows, decisions, targets, covariance):
    days = cell['days']
    year = cell['year']
    if (not isinstance(window, MappingProxyType)
            or type(window.get('minute_blocks')) is not s.CapturedMinuteProvider
            or window['minute_blocks'].year != year or type(window.get('events')) is not tuple
            or type(source_rows) is not tuple or any(not isinstance(r, MappingProxyType) for r in source_rows)
            or not isinstance(window.get('daily'), pl.DataFrame)
            or not isinstance(decisions, np.ndarray) or decisions.dtype != np.dtype('int64')
            or decisions.shape != (days,) or decisions.flags.writeable
            or not isinstance(targets, np.ndarray) or targets.dtype != np.dtype('float64')
            or targets.shape != (days, 5) or targets.flags.writeable or not np.isfinite(targets).all()
            or not isinstance(covariance, np.ndarray) or covariance.dtype != np.dtype('float64')
            or covariance.shape != (days, 5, 5) or covariance.flags.writeable):
        raise ValueError('EXACT_IMMUTABLE_ENTRY_OWNED_CELL_INPUTS_REQUIRED')
    if (set(window) != {'start', 'end', 'symbols', 'daily', 'events', 'minute_blocks',
            'derived_mark_cells', 'original_missing_mark_open_ms', 'original_overlay_future_looking',
            'original_overlay_execution_admitted', 'causal_mark_adapter'}
            or [window['start'], window['end']] != cell['calendar']
            or tuple(window['symbols']) != s.S
            or _sha(targets.tobytes()) != cell['selected_target_raw_SHA256']):
        raise ValueError('EXACT_CELL_CALENDAR_TARGET_WINDOW_REQUIRED')
    return dict(schema='ENTRY_OWNED_EXACT_EXPANSION_CELL_INPUT_BINDING_V1',
        cell_id=cell['cell_id'], year=year, config=cell['config'], tier=cell['tier'],
        calendar=[window['start'], window['end']], symbols=list(window['symbols']),
        decision_raw_SHA256=_sha(decisions.tobytes()), selected_target_raw_SHA256=_sha(targets.tobytes()),
        covariance_raw_SHA256=_sha(covariance.tobytes()),
        daily_rows_SHA256=_json_sha(window['daily'].to_dicts()),
        daily_schema=[[name, str(dtype)] for name, dtype in window['daily'].schema.items()],
        source_rows_SHA256=_json_sha(source_rows), funding_events_SHA256=_json_sha(window['events']),
        provider_month_identity=window['minute_blocks'].identity,
        causal_mark_adapter_SHA256=_json_sha(window['causal_mark_adapter']),
        derived_mark_cells=window['derived_mark_cells'],
        original_missing_mark_open_ms=list(window['original_missing_mark_open_ms']),
        original_overlay_future_looking=window['original_overlay_future_looking'],
        original_overlay_execution_admitted=window['original_overlay_execution_admitted'])



def _artifacts():
    return {name:s.exact(SOURCE_TARGETS/name,p['SHA256'],p['bytes']) for name,p in frozen_manifest()['source_target_artifacts'].items()}

def _year_projection(year,root,artifacts):
    if year!=2021:raise ValueError('ONLY_PARTIAL2021_SOURCE_ALLOWED')
    p=s.project(root);m=frozen_manifest()
    if p['source_identity']!=m['source_identity']:raise ValueError('EXACT_PARTIAL2021_SOURCE_IDENTITY_REQUIRED')
    with np.load(BytesIO(artifacts['TARGETS.npz']),allow_pickle=False) as z:
        if set(z.files)!=set(s.CONFIGS)|{'decision_us','annual_covariance'}:raise ValueError('ALL_NINE_TARGET_BYTE_PATHS_REQUIRED')
        if (z['decision_us'].tobytes()!=p['decisions'].tobytes() or z['annual_covariance'].tobytes()!=p['covariance'].tobytes()
                or any(z[c].tobytes()!=p['targets'][c].tobytes() for c in s.CONFIGS)):
            raise ValueError('EXACT_ORIGINAL_TARGET_COVARIANCE_BYTES_REQUIRED')
    if (json.loads(artifacts['TARGET_PROOFS.json'])!=p['proofs']
            or json.loads(artifacts['DAILY_SOURCE_PROJECTION.json'])!=p['projection']
            or artifacts['MINUTE_MARK_PROVENANCE.json']!=p['sidecar_raw']):raise ValueError('EXACT_SOURCE_TARGET_PROOF_BITS_REQUIRED')
    return p

def prepare_source_only(source_roots,output_directory):
    roots=_source_roots(source_roots);out=Path(output_directory)
    if out.exists():raise ValueError('EXCLUSIVE_NEW_PARTIAL2021_PREPARATION_REQUIRED')
    code=code_identity();artifacts=_artifacts();p=_year_projection(2021,roots[2021],artifacts);m=frozen_manifest()
    info=dict(year=2021,calendar=m['calendar'],days=s.DAYS,required_minutes=s.MINUTES,coldstart_policy=_coldstart_policy(2021),
        source_identity=p['source_identity'],source_files=p['source_files'],auxiliary_source_pins={},original200_quality=p['quality'],
        quality_sidecar='2021/MINUTE_MARK_PROVENANCE.json',quality_sidecar_sha256=_sha(p['sidecar_raw']),quality_intervals=[],
        original_genuine_observation_us=None,decision_raw_SHA256=_sha(p['decisions'].tobytes()),
        covariance_raw_SHA256=_sha(p['covariance'].tobytes()),daily_source_projection=p['projection'])
    cells={}
    for c in m['cells']:
        binding=_input_binding(c,p['window'],p['source_rows'],p['decisions'],p['targets'][c['config']],p['covariance'])
        cells[c['cell_id']]=dict(descriptor=c,input_binding=binding,input_binding_SHA256=_json_sha(binding),
            selected_target_raw_SHA256=c['selected_target_raw_SHA256'],decision_raw_SHA256=info['decision_raw_SHA256'],
            covariance_raw_SHA256=info['covariance_raw_SHA256'],quality_sidecar_sha256=info['quality_sidecar_sha256'])
    policy=_policy(code)
    prep=dict(schema=PREPARATION_SCHEMA,policy_version=POLICY_VERSION,source_scope=SOURCE_SCOPE,
        status='PREPARED_SOURCE_TARGET_ONLY_NO_HISTORICAL_ACCOUNT_OR_GO',manifest_SHA256=MANIFEST_SHA256,manifest=m,
        years={'2021':info},cells=cells,ordered_cells=list(tranche_cells()),cost=COST,modes=list(MODES),settlement_mode=SETTLEMENT_MODE,
        code_identity=code,policy=policy,policy_identity=_json_sha(policy),
        artifacts={'2021/'+n:p for n,p in m['source_target_artifacts'].items()},
        resource_limits=RESOURCE_LIMITS,resource_execution_contract=RESOURCE_EXECUTION_CONTRACT,launch_claim_contract=LAUNCH_CLAIM_CONTRACT,
        global_controller_lease_contract=GLOBAL_CONTROLLER_LEASE_CONTRACT,preserved_evidence_pins=preserved_evidence_identity(),
        preserved_old_root_GO_is_new_authority=False,old_private_GO_bodies_read=0,
        all_inputs_seen_development=True,performance_selection_allowed=False,original_interpolated_mark_execution_admitted=False,
        accounts_created=0,accounts_advanced=0,historical_market_minutes_advanced=0,financial_runs=0,outcomes_inspected=False,
        provider_iterations=0,historical_scopes_created=0,process_launches=0,canonical_claims_created=0,real_GO_written=0,
        annual_returns_computed=False,locked_or_holdout_consumed=False,other_years_or_2025_authorized=False,
        publication_actions=0,historical_admission=False,execution_requires_new_exact_external_root_GO=True,execution_label=LABEL)
    if code_identity()!=code:raise ValueError('CODE_CHANGED_DURING_SOURCE_PREPARATION')
    _validate_preparation(_canonical(prep));out.mkdir(parents=True)
    for name,b in artifacts.items():
        dest=out/'2021'/name;dest.parent.mkdir(exist_ok=True)
        with dest.open('xb') as f:f.write(b)
    with (out/'PREPARATION.json').open('xb') as f:f.write(json.dumps(prep,indent=2,allow_nan=False).encode()+b'\n')
    return prep

def _validate_preparation(raw):
    p=_object(raw,'EXACT_PARTIAL2021_PREPARATION_REQUIRED');m=frozen_manifest()
    required=dict(schema=PREPARATION_SCHEMA,policy_version=POLICY_VERSION,source_scope=SOURCE_SCOPE,
        status='PREPARED_SOURCE_TARGET_ONLY_NO_HISTORICAL_ACCOUNT_OR_GO',manifest_SHA256=MANIFEST_SHA256,manifest=m,
        ordered_cells=list(tranche_cells()),cost=COST,modes=list(MODES),settlement_mode=SETTLEMENT_MODE,
        artifacts={'2021/'+n:x for n,x in m['source_target_artifacts'].items()},resource_limits=RESOURCE_LIMITS,
        resource_execution_contract=RESOURCE_EXECUTION_CONTRACT,launch_claim_contract=LAUNCH_CLAIM_CONTRACT,
        global_controller_lease_contract=GLOBAL_CONTROLLER_LEASE_CONTRACT,preserved_evidence_pins=preserved_evidence_identity(),
        preserved_old_root_GO_is_new_authority=False,old_private_GO_bodies_read=0,all_inputs_seen_development=True,
        performance_selection_allowed=False,original_interpolated_mark_execution_admitted=False,
        accounts_created=0,accounts_advanced=0,historical_market_minutes_advanced=0,financial_runs=0,outcomes_inspected=False,
        provider_iterations=0,historical_scopes_created=0,process_launches=0,canonical_claims_created=0,real_GO_written=0,
        annual_returns_computed=False,locked_or_holdout_consumed=False,other_years_or_2025_authorized=False,
        publication_actions=0,historical_admission=False,execution_requires_new_exact_external_root_GO=True,execution_label=LABEL)
    if (any(not _same(p.get(k),v) for k,v in required.items()) or set(p.get('years',{}))!={'2021'}
            or set(p.get('cells',{}))!=set(tranche_cells()) or type(p.get('code_identity')) is not dict
            or not _same(p.get('policy'),_policy(p['code_identity'])) or p.get('policy_identity')!=_json_sha(p['policy'])):
        raise ValueError('EXACT_FROZEN_PARTIAL2021_SCOPE_REQUIRED')
    info=p['years']['2021']
    fixed=dict(year=2021,calendar=m['calendar'],days=s.DAYS,required_minutes=s.MINUTES,coldstart_policy=_coldstart_policy(2021),
        source_identity=m['source_identity'],auxiliary_source_pins={},quality_sidecar='2021/MINUTE_MARK_PROVENANCE.json',
        quality_sidecar_sha256=m['source_target_artifacts']['MINUTE_MARK_PROVENANCE.json']['SHA256'],
        quality_intervals=[],original_genuine_observation_us=None,
        original200_quality=dict(fullfive200_decisions=274,warmup_only_before=s.START,derived_mark_cells=0,actual_source=True,
            imputed=False,publication_arrival_certified=False,funding_units_certified=False,native_venue_certified=False),
        daily_source_projection=json.loads(_artifacts()['DAILY_SOURCE_PROJECTION.json']))
    if any(not _same(info.get(k),v) for k,v in fixed.items()):raise ValueError('EXACT2021_CALENDAR_QUALITY_IDENTITY_REQUIRED')
    source_identity=_json_sha(dict(source_files=info.get('source_files'),calendar=[s.START,s.END],
        source_scope='ORIGINAL_FULLFIVE200_APR2_DEC31_ONLY',used_daily_projection=fixed['daily_source_projection']))
    if source_identity!=m['source_identity']:raise ValueError('EXACT2021_SOURCE_FILE_PIN_IDENTITY_REQUIRED')
    if any(type(k) is not str or type(v) is not str or len(v)!=64 or any(c not in '0123456789abcdef' for c in v)
            for k,v in p['code_identity'].items()):raise ValueError('EXACT_CODE_IDENTITY_STRING_HASH_TYPES_REQUIRED')
    equality=json.loads(_artifacts()['EXACT_EXECUTION_EQUALITY.json'])
    if (info.get('decision_raw_SHA256')!=equality['decision_raw_SHA256']
            or info.get('covariance_raw_SHA256')!=equality['annual_covariance_raw_SHA256']):raise ValueError('EXACT274_DECISION_COVARIANCE_IDENTITY_REQUIRED')
    for c in m['cells']:
        v=p['cells'][c['cell_id']];b=v.get('input_binding')
        if (not _same(v.get('descriptor'),c) or not isinstance(b,dict) or _json_sha(b)!=v.get('input_binding_SHA256')
                or b.get('calendar')!=c['calendar'] or b.get('cell_id')!=c['cell_id']
                or b.get('selected_target_raw_SHA256')!=c['selected_target_raw_SHA256']
                or b.get('decision_raw_SHA256')!=info['decision_raw_SHA256'] or b.get('covariance_raw_SHA256')!=info['covariance_raw_SHA256']
                or not _same(b.get('year'),2021) or b.get('config')!=c['config'] or b.get('tier')!=c['tier']
                or v.get('selected_target_raw_SHA256')!=c['selected_target_raw_SHA256']
                or v.get('decision_raw_SHA256')!=info['decision_raw_SHA256'] or v.get('covariance_raw_SHA256')!=info['covariance_raw_SHA256']
                or v.get('quality_sidecar_sha256')!=info['quality_sidecar_sha256']):
            raise ValueError('EXACT_NINE_CELL_BOUND_SOURCE_TARGET_REQUIRED')
    return p

def _authorization_common(raw,p):
    return dict(policy_version=POLICY_VERSION,source_scope=SOURCE_SCOPE,preparation_SHA256=_sha(raw),manifest_SHA256=MANIFEST_SHA256,
        ordered_manifest_cells=p['ordered_cells'],cost=COST,modes=list(MODES),settlement_mode=SETTLEMENT_MODE,
        code_identity=p['code_identity'],policy_identity=p['policy_identity'],artifacts=p['artifacts'],years=p['years'],cells=p['cells'],
        resource_limits=RESOURCE_LIMITS,resource_execution_contract=RESOURCE_EXECUTION_CONTRACT,launch_claim_contract=LAUNCH_CLAIM_CONTRACT,
        global_controller_lease_contract=GLOBAL_CONTROLLER_LEASE_CONTRACT,preserved_evidence_pins=preserved_evidence_identity(),
        preserved_old_root_GO_is_new_authority=False,old_private_GO_bodies_required=False,partial_DEV=True,
        annualization_allowed=False,wallet_compounding_allowed=False,all_inputs_seen_development=True,performance_selection_allowed=False,
        original_interpolated_mark_execution_admitted=False,other_years_or_2025_authorized=False,locked_or_holdout_consumed=False,
        publication_authorized=False,fresh_genesis_only=True,automatic_retry_authorized=False,halted_snapshot_resume_authorized=False)

def validate_root_go(preparation_raw,go_raw,expected_go_sha256,*,cell_id,policy_variant=POLICY_VARIANT):
    cell_descriptor(cell_id);_exact(go_raw,expected_go_sha256,'EXACT_NEW_EXTERNAL_PARTIAL2021_ROOT_GO_REQUIRED')
    p=_validate_preparation(preparation_raw);go=_object(go_raw,'EXACT2021_ROOT_GO_OBJECT_REQUIRED')
    required=dict(schema=GO_SCHEMA,action=ACTION,**_authorization_common(preparation_raw,p))
    n,cpus,rsha=go.get('requested_worker_count'),go.get('worker_CPUs'),go.get('independent_review_SHA256')
    if (policy_variant!=POLICY_VARIANT or go.get('tranche')!=FIRST_TRANCHE or go.get('permitted_cells')!=list(tranche_cells())
            or any(not _same(go.get(k),v) for k,v in required.items()) or type(n) is not int or n not in (1,2)
            or type(cpus) is not list or len(cpus)!=n or any(type(c) is not int or c<0 for c in cpus) or len(set(cpus))!=n
            or type(rsha) is not str or len(rsha)!=64 or any(c not in '0123456789abcdef' for c in rsha)
            or expected_go_sha256 in OLD_EVIDENCE_HASHES.values()):raise ValueError('EXACT_NEW2021_GO_REVIEW_RESOURCE_CELL_SCOPE_REQUIRED')
    return p

REVIEW_FLAGS=('generated_native_scheduler_phase_order_passed','generated_shared_pending_32_corner_passed',
 'generated_preview_isolation_passed','generated_causal_quality_passed','generated_terminal_taxonomy_passed',
 'generated_unknown_quality_no_new_exit_passed','generated_guard50_paid_exit_no_topup_passed',
 'generated_exact_cell_year_tier_target_quality_gates_passed','generated_frozen_manifest_and_ordered_tranche_gates_passed',
 'generated_pool_resource_and_aggregate_pressure_gates_passed','generated_canonical_launch_claim_duplicate_and_existing_output_gates_passed',
 'generated_global_controller_lease_inherited_worker_FD_gates_passed','generated_helper_thread_affinity_and_compute_pool_contract_passed',
 'generated_actual_held_exposure_forecast_overshoot_reporting_passed','generated_native40_raw100_financial_reconstruction_passed',
 'independent_actual2021_source_target_equivalence_passed','generated_partial2021_coldstart_funding_ownership_terminal60_passed',
 'generated_old_private_GO_hash_only_portability_passed')

def _validate_independent_review(preparation_raw,prep,review_raw,expected_review_sha256,go_raw):
    _exact(review_raw,expected_review_sha256,'EXACT_NEW_EXTERNAL_PARTIAL2021_REVIEW_REQUIRED')
    r=_object(review_raw,'EXACT2021_REVIEW_OBJECT_REQUIRED');go=_object(go_raw,'EXACT2021_GO_OBJECT_REQUIRED')
    required=dict(schema=REVIEW_SCHEMA,status='PASS_SOURCE_ONLY_AND_GENERATED_NO_HISTORICAL_GO',
        **_authorization_common(preparation_raw,prep),**dict.fromkeys(REVIEW_FLAGS,True),
        actual_2021_accounts_constructed=0,actual_2021_financial_runs=0,historical_market_minutes_advanced=0,
        publication_actions=0,locked_source_reads=0)
    if (go.get('independent_review_SHA256')!=expected_review_sha256 or expected_review_sha256 in OLD_EVIDENCE_HASHES.values()
            or any(not _same(r.get(k),v) for k,v in required.items())):raise ValueError('EXACT_NEW2021_INDEPENDENT_REVIEW_REQUIRED')
    return r

def validate_case_inputs(source_roots,preparation_directory,go_raw,expected_go_sha256,*,cell_id,policy_variant=POLICY_VARIANT):
    roots=_source_roots(source_roots);directory=Path(preparation_directory);raw=_ordinary(directory/'PREPARATION.json')
    prep=validate_root_go(raw,go_raw,expected_go_sha256,cell_id=cell_id,policy_variant=policy_variant)
    if prep['code_identity']!=code_identity():raise ValueError('PARTIAL2021_CODE_CHANGED_SINCE_PREPARATION')
    artifacts={n:s.exact(directory/n,p['SHA256'],p['bytes']) for n,p in prep['artifacts'].items()}
    c=cell_descriptor(cell_id);p=_year_projection(2021,roots[2021],{n[5:]:v for n,v in artifacts.items()})
    info=prep['years']['2021']
    if (not _same(p['source_files'],info['source_files']) or not _same(p['quality'],info['original200_quality'])
            or not _same(p['projection'],info['daily_source_projection'])):raise ValueError('EXACT2021_SOURCE_PINS_QUALITY_PROJECTION_REQUIRED')
    target=p['targets'][c['config']]
    binding=_input_binding(c,p['window'],p['source_rows'],p['decisions'],target,p['covariance'])
    if not _same(binding,prep['cells'][cell_id]['input_binding']):raise ValueError('EXACT2021_BOUND_NATIVE_INPUTS_REQUIRED')
    return prep,p['window'],p['source_rows'],p['decisions'],target,p['captured']
@dataclass(frozen=True, slots=True)
class CaseExecutionScope:
    cell_id: str
    year: int
    strategy: str
    tier_name: str
    config: str
    preparation_SHA256: str
    source_identity: str
    code_identity_SHA256: str
    policy_identity: str
    independent_review_SHA256: str
    root_GO_SHA256: str
    quality_intervals: tuple
    quality_sidecar_sha256: str
    original_genuine_observation_us: object
    policy_variant: str
    _source_root: Path = field(repr=False)
    _preparation_directory: Path = field(repr=False)
    _preparation_raw: bytes = field(repr=False)
    _review_raw: bytes = field(repr=False)
    _go_raw: bytes = field(repr=False)
    _source_pins: tuple = field(repr=False)
    _bound_window: object = field(repr=False, compare=False)
    _bound_source_rows: tuple = field(repr=False, compare=False)
    _bound_decisions: object = field(repr=False, compare=False)
    _bound_targets: object = field(repr=False, compare=False)
    _bound_covariance: object = field(repr=False, compare=False)
    _seal: object = field(repr=False)

    def __post_init__(self):
        if self._seal is not _SCOPE_SEAL:
            raise ValueError('SCOPE_ONLY_FROM_EXACT_NEW_PARTIAL2021_ADMISSION')

    def __deepcopy__(self, memo):
        memo[id(self)] = self
        return self

    @property
    def source_scope(self):
        return SOURCE_SCOPE

    @property
    def mode(self):
        return self.policy_variant

    @property
    def metadata(self):
        # Return ordinary clone-safe plaintext containers. Mutating a returned
        # metadata object does not change the sealed scope or its authority.
        cell = cell_descriptor(self.cell_id)
        return dict(source_scope=SOURCE_SCOPE, policy_version=POLICY_VERSION, cell_id=self.cell_id,
            year=self.year, strategy=self.strategy, tier_name=self.tier_name, config=self.config,
            preparation_SHA256=self.preparation_SHA256, source_identity=self.source_identity,
            code_identity_SHA256=self.code_identity_SHA256, policy_identity=self.policy_identity,
            independent_review_SHA256=self.independent_review_SHA256, root_GO_SHA256=self.root_GO_SHA256,
            policy_variant=self.policy_variant, manifest_SHA256=MANIFEST_SHA256,
            calendar=list(cell['calendar']), days=cell['days'], required_minutes=cell['required_minutes'],
            cost=COST, settlement_mode=SETTLEMENT_MODE, fresh_genesis_only=True, generated_fixture_scope_used=False,
            coldstart_policy=_coldstart_policy(self.year),
            quality_intervals=_plain(self.quality_intervals), quality_sidecar_sha256=self.quality_sidecar_sha256,
            original_genuine_observation_us=self.original_genuine_observation_us,
            input_binding_SHA256=_json_sha(_input_binding(cell, self._bound_window, self._bound_source_rows,
                self._bound_decisions, self._bound_targets, self._bound_covariance)))

    def validate_inputs(self, window, source_rows, decisions, targets):
        if (self._seal is not _SCOPE_SEAL or window is not self._bound_window
                or source_rows is not self._bound_source_rows or decisions is not self._bound_decisions
                or targets is not self._bound_targets):
            raise ValueError('EXACT_ENTRY_OWNED_CELL_INPUT_REFERENCES_REQUIRED')
        prep = _object(self._preparation_raw, 'EXACT_SCOPE_PREPARATION_REQUIRED')
        cell = cell_descriptor(self.cell_id)
        binding = _input_binding(cell, window, source_rows, decisions, targets, self._bound_covariance)
        if (not _same(binding, prep['cells'][self.cell_id]['input_binding'])
                or _json_sha(binding) != prep['cells'][self.cell_id]['input_binding_SHA256']):
            raise ValueError('BOUND_CELL_SOURCE_TARGET_PROVIDER_OR_QUALITY_CHANGED')
        return True

    def validate_current(self):
        if self._seal is not _SCOPE_SEAL:
            raise ValueError('UNSEALED_EXPANSION_CASE_SCOPE')
        raw = _ordinary(self._preparation_directory / 'PREPARATION.json')
        if raw != self._preparation_raw or _sha(raw) != self.preparation_SHA256:
            raise ValueError('BOUND_EXPANSION_PREPARATION_CHANGED')
        prep = validate_root_go(raw, self._go_raw, self.root_GO_SHA256,
            cell_id=self.cell_id, policy_variant=self.policy_variant)
        _validate_independent_review(raw, prep, self._review_raw, self.independent_review_SHA256, self._go_raw)
        cell = cell_descriptor(self.cell_id)
        info = prep['years'][str(cell['year'])]
        pins = {**info['source_files'], **info['auxiliary_source_pins']}
        if (self.year != cell['year'] or self.config != cell['config'] or self.strategy != cell['strategy']
                or self.tier_name != cell['tier'] or self.source_identity != info['source_identity']
                or self.quality_intervals != _immutable(info['quality_intervals'])
                or self.quality_sidecar_sha256 != info['quality_sidecar_sha256']
                or self.original_genuine_observation_us != info['original_genuine_observation_us']
                or self._source_pins != tuple((name, pin['SHA256'], pin['bytes']) for name, pin in sorted(pins.items()))
                or self.policy_identity != prep['policy_identity']
                or self.code_identity_SHA256 != _json_sha(prep['code_identity'])
                or prep['code_identity'] != code_identity()):
            raise ValueError('BOUND_EXPANSION_CELL_YEAR_TIER_SOURCE_QUALITY_OR_CODE_CHANGED')
        for name, digest, size in self._source_pins:
            s.exact(self._source_root / name, digest, size)
        for name, pin in prep['artifacts'].items():
            s.exact(self._preparation_directory / name, pin['SHA256'], pin['bytes'])
        self.validate_inputs(self._bound_window, self._bound_source_rows, self._bound_decisions, self._bound_targets)
        return True


def _default_constructor_callback(*,scope,preparation,window,source_rows,decisions,targets,captured):
    import partial_d
    if Path(partial_d.__file__).resolve()!=HERE/'partial_d.py':raise ValueError('EXACT_LOCAL_PARTIAL2021_D_REQUIRED')
    return partial_d.construct_case(window,source_rows,decisions,targets,policy_variant=POLICY_VARIANT,
        historical_scope=scope,quality_intervals=scope.quality_intervals)

def make_case(source_roots, preparation_directory, go_raw, expected_go_sha256, *, cell_id,
        policy_variant=POLICY_VARIANT, review_raw=None, expected_review_sha256=None, constructor_callback=None):
    roots = _source_roots(source_roots)
    raw = _ordinary(Path(preparation_directory) / 'PREPARATION.json')
    prep = validate_root_go(raw, go_raw, expected_go_sha256, cell_id=cell_id, policy_variant=policy_variant)
    _validate_independent_review(raw, prep, review_raw, expected_review_sha256, go_raw)
    prep, window, rows, decisions, targets, captured = validate_case_inputs(roots,
        preparation_directory, go_raw, expected_go_sha256, cell_id=cell_id, policy_variant=policy_variant)
    cell = cell_descriptor(cell_id)
    info = prep['years'][str(cell['year'])]
    with np.load(BytesIO(_ordinary(Path(preparation_directory) / f"{cell['year']}/TARGETS.npz")), allow_pickle=False) as z:
        covariance = z['annual_covariance'].copy()
    covariance.setflags(write=False)
    pins = {**info['source_files'], **info['auxiliary_source_pins']}
    scope = CaseExecutionScope(cell_id=cell_id, year=cell['year'], strategy=cell['strategy'], tier_name=cell['tier'],
        config=cell['config'], preparation_SHA256=_sha(raw), source_identity=info['source_identity'],
        code_identity_SHA256=_json_sha(prep['code_identity']), policy_identity=prep['policy_identity'],
        independent_review_SHA256=expected_review_sha256, root_GO_SHA256=expected_go_sha256,
        policy_variant=policy_variant, quality_intervals=_immutable(info['quality_intervals']),
        quality_sidecar_sha256=info['quality_sidecar_sha256'], original_genuine_observation_us=info['original_genuine_observation_us'],
        _source_root=roots[cell['year']], _preparation_directory=Path(preparation_directory).resolve(),
        _preparation_raw=raw, _review_raw=review_raw, _go_raw=go_raw,
        _source_pins=tuple((name, pin['SHA256'], pin['bytes']) for name, pin in sorted(pins.items())),
        _bound_window=window, _bound_source_rows=rows, _bound_decisions=decisions,
        _bound_targets=targets, _bound_covariance=covariance, _seal=_SCOPE_SEAL)
    scope.validate_current()
    callback = constructor_callback or _default_constructor_callback
    return callback(scope=scope, preparation=prep, window=window, source_rows=rows,
        decisions=decisions, targets=targets, captured=captured)

def invalid_go_template(preparation_raw):
    p=_validate_preparation(preparation_raw)
    return dict(schema=GO_SCHEMA,action='INVALID_TEMPLATE_NOT_ROOT_AUTHORIZATION',**_authorization_common(preparation_raw,p),
        tranche=FIRST_TRANCHE,permitted_cells=list(tranche_cells()),requested_worker_count=2,worker_CPUs=[4,5],
        independent_review_SHA256='REPLACE_WITH_NEW_EXTERNAL_REVIEW_SHA256',status='INVALID_NO_HISTORICAL_GO')
