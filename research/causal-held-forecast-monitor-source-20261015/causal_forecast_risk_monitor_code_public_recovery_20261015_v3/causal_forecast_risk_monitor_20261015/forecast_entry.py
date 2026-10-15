"""Separate four-cell source preparation and exact external historical gate.

Import/preparation never construct or advance a historical account. Original
annual capture, covariance/target rebuild, provenance and immutable input binding
are reused by explicit local dependency bindings, never by editing old modules.
"""
from dataclasses import dataclass
from hashlib import sha256
import importlib.util
import json
from pathlib import Path
import sys
from types import FunctionType

import forecast_monitor as F

HERE, ROOT = Path(__file__).resolve().parent, Path(__file__).resolve().parent.parent
if Path(F.__file__).resolve() != HERE/'forecast_monitor.py':
    raise ValueError('EXACT_LOCAL_FORECAST_MONITOR_MODULE_REQUIRED')
OLD_ROOT = ROOT/'bounded_native_continuation_guard50_exit_expansion_20261015'
_NAME = '_causal_forecast_exact_source_entry'
if _NAME in sys.modules:
    BASE = sys.modules[_NAME]
    if Path(BASE.__file__).resolve() != OLD_ROOT/'expansion_entry.py':
        raise ValueError('CONFLICTING_DECLARED_FORECAST_SOURCE_ENTRY_IMPORT')
else:
    spec = importlib.util.spec_from_file_location(_NAME, OLD_ROOT/'expansion_entry.py')
    BASE = importlib.util.module_from_spec(spec)
    sys.modules[_NAME] = BASE
    spec.loader.exec_module(BASE)

POLICY_VARIANT = BASE.POLICY_VARIANT
POLICY_VERSION = 'CAUSAL_HELD_FORECAST_ORIGINAL_MID_FOUR_DEV_CELLS_V1'
SOURCE_SCOPE = 'EXACT_ROOT_ADMITTED_FRESH_CAUSAL_FORECAST_MID_DEV2023_2024_V1'
PREPARATION_SCHEMA = 'SOURCE_TARGET_ONLY_CAUSAL_FORECAST_FOUR_DEV_CELLS_V1'
REVIEW_SCHEMA = 'INDEPENDENT_CAUSAL_FORECAST_FOUR_CELL_SOURCE_GENERATED_REVIEW_V1'
GO_SCHEMA = 'ROOT_GO_CAUSAL_FORECAST_EXACT_ORDERED_FOUR_CELLS_V1'
ACTION = 'RUN_FRESH_EXACT_FOUR_CAUSAL_FORECAST_CELLS_ONLY'
MANIFEST_NAME = 'FROZEN_FOUR_CELL_MANIFEST.json'
MANIFEST_SHA256 = '1069e5a46b5197ce1195aaa7db1569cac3573800e526fff55039c7206f35081b'
CONTROL_NAME = 'CONTROL_REFERENCE_CATALOGUE.json'
CONTROL_SHA256 = '3b61ea88765455246acc7aa5393b7256cb915829737985e542c835579f207b79'
FIRST_TRANCHE = REMAINING_TRANCHE = 'EXACT_FOUR_CAUSAL_FORECAST_MID'
COST, MODES, SETTLEMENT_MODE, LABEL = BASE.COST, BASE.MODES, BASE.SETTLEMENT_MODE, BASE.LABEL
YEARS, SOURCE_ROOTS = BASE.YEARS, BASE.SOURCE_ROOTS
RESOURCE_LIMITS = dict(BASE.RESOURCE_LIMITS, per_case_CPU_seconds=600)
RESOURCE_EXECUTION_CONTRACT = BASE.RESOURCE_EXECUTION_CONTRACT
LAUNCH_CLAIM_CONTRACT = dict(BASE.LAUNCH_CLAIM_CONTRACT,
    launch_claim_registry_relative=HERE.name+'/EXECUTION_CLAIMS')
GLOBAL_CONTROLLER_LEASE_CONTRACT = dict(BASE.GLOBAL_CONTROLLER_LEASE_CONTRACT,
    registry_relative=HERE.name+'/EXECUTION_CLAIMS', one_controller_across_both_tranches=False,
    one_controller_across_exact_four_cells=True)
_SCOPE_SEAL = object()
_sha, _json_sha, _same = BASE._sha, BASE._json_sha, BASE._same
_object, _exact, _ordinary = BASE._object, BASE._exact, BASE._ordinary
_immutable, _plain, _canonical = BASE._immutable, BASE._plain, BASE._canonical


def frozen_manifest():
    raw = BASE.a24.h._read_exact(HERE/MANIFEST_NAME, MANIFEST_SHA256)
    m = _object(raw, 'EXACT_FOUR_FORECAST_MANIFEST_REQUIRED')
    expected = ['2023_STATIC50_MID_CAUSAL_FORECAST', '2023_VOL_MANAGED_HOLD_MID_CAUSAL_FORECAST',
                '2024_STATIC50_MID_CAUSAL_FORECAST', '2024_VOL_MANAGED_HOLD_MID_CAUSAL_FORECAST']
    if (m['years'] != [2023, 2024] or [c['cell_id'] for c in m['cells']] != expected
            or m['new_cell_count'] != 4 or m['original_mid_forecast_budget'] != .10
            or any(c['tier'] != 'MID' or c['strategy'] not in ('STATIC50','VOL_MANAGED_HOLD') for c in m['cells'])):
        raise ValueError('ONLY_EXACT_FOUR_NEW_ORIGINAL_MID_FORECAST_CELLS')
    return m


def cell_descriptor(cell_id):
    for cell in frozen_manifest()['cells']:
        if type(cell_id) is str and cell['cell_id'] == cell_id:
            return cell
    raise ValueError('EXACT_FOUR_NEW_MONITOR_CELL_REQUIRED_OLD_CONTROL_REFUSED')


def tranche_cells(tranche=FIRST_TRANCHE):
    if tranche != FIRST_TRANCHE:
        raise ValueError('EXACT_FOUR_CELL_TRANCHE_REQUIRED')
    return tuple(c['cell_id'] for c in frozen_manifest()['cells'])


def control_references():
    raw = BASE.a24.h._read_exact(HERE/CONTROL_NAME, CONTROL_SHA256)
    refs = _object(raw, 'EXACT_FOUR_CONTROL_REFERENCE_CATALOGUE_REQUIRED')
    if ([r['cell_id'] for r in refs['controls']] != [c['control_id'] for c in frozen_manifest()['cells']]
            or any(r['rerun_authorized'] is not False for r in refs['controls'])):
        raise ValueError('EXACT_FOUR_EXISTING_CONTROLS_REUSE_ONLY_REQUIRED')
    return refs


def preserved_evidence_identity():
    # This intentionally retains the original helper's private old-GO/review
    # dependencies as evidence only. No portability or old-gate bypass occurs.
    result = BASE.preserved_evidence_identity()
    refs = control_references()
    result[HERE.name+'/'+CONTROL_NAME] = CONTROL_SHA256
    result[refs['overall18_independent_review_relative_path']] = refs['overall18_independent_review_SHA256']
    for row in refs['controls']:
        BASE.a24.h._read_exact(ROOT/row['CASE_RECEIPT_relative_path'], row['CASE_RECEIPT_SHA256'], row['bytes'])
        result[row['CASE_RECEIPT_relative_path']] = row['CASE_RECEIPT_SHA256']
    for name, digest in result.items():
        BASE.a24.h._read_exact(ROOT/name, digest)
    return result


def code_identity():
    code = BASE.code_identity()
    for name in ('forecast_monitor.py','forecast_entry.py','forecast_historical.py','run_forecast.py',
                 'profile_generated.py','test_core.py',MANIFEST_NAME,CONTROL_NAME):
        code[HERE.name+'/'+name] = _sha(_ordinary(HERE/name))
    return code


def _policy(code):
    return dict(version=POLICY_VERSION, source_scope=SOURCE_SCOPE, policy_variant=POLICY_VARIANT,
        cost=COST, settlement_mode=SETTLEMENT_MODE, manifest_SHA256=MANIFEST_SHA256,
        code_identity=code, ordered_cells=list(tranche_cells()), nominal_tier='MID',
        original_forecast_budget=.10, covariance='ORIGINAL_PAST30_COMPLETED_SIMPLE_DAILY_DDOF1_X365',
        cadence='EXISTING_NATIVE_COMPLETED_MINUTE_CLOSE_AFTER_NATIVE_RISK_AND_COMPLETE_SAMECLOCK_FUNDING',
        projection='ALPHA_MIN_1_POINT10_OVER_NATIVE_SIGMA_DECIMAL_STR_SIGNED_NATIVE_FLOOR',
        completed_variance_must_strictly_fall=True, infeasible_projection_holds_state=True,
        partial_fills_atomic=False, partial_fill_variance_monotonicity_guaranteed=False,
        no_autonomous_rerisking=True, one_owned_active_trim_cohort=True,
        five_native_opens_before_expiry_renewal_with_new_native_latency=True,
        late_native_hard_cap_supersedes_only_exact_owned_forecast_pending=True,
        protection_only_native_hardcap_handback_at_existing_intrafunding_callback_allowed=True,
        new_forecast_sigma_or_target_during_incomplete_funding_batch_allowed=False,
        native_D_full_protective_and_terminal_priority=True, automatic_topup=False,
        initial_shared_wallet_USDT='10000', common_free_cash_floor_USDT='1000',
        common_isolated_margin_ceiling_USDT='8500', leverage=1,
        quantity_profile_SHA256=BASE.old.PRIMITIVE_CODE_PINS['QUANTITY_PROFILE.json'],
        frozen_D_code_SHA256=BASE.FROZEN_D_CODE_PINS['guard50_exit.py'],
        resource_limits=RESOURCE_LIMITS, resource_execution_contract=RESOURCE_EXECUTION_CONTRACT,
        launch_claim_contract=LAUNCH_CLAIM_CONTRACT,
        global_controller_lease_contract=GLOBAL_CONTROLLER_LEASE_CONTRACT,
        control_reference_catalogue_SHA256=CONTROL_SHA256, controls=control_references()['controls'],
        existing_controls_rerun_authorized=False, all_years_seen_development=True,
        candidate_threshold_or_performance_selection_allowed=False,
        original_interpolated_mark_execution_admitted=False,
        unknown_stale_derived_quality_creates_new_exit=False,
        existing_ordinary_reductions_and_native_paid_intents_preserved=True,
        ordinary_reduction_or_reversal_CLOSE_defers_entire_new_forecast_cohort=True,
        ordinary_defer_predicate='NONPRIORITY_AND_Q_NONZERO_AND_Q_TIMES_TARGET_MINUS_Q_LT_ZERO',
        ordinary_order_ID_signal_attempt_target_eligibility_and_capacity_unchanged_on_defer=True,
        old_private_GO_evidence_dependencies_retained=True, old_GO_is_new_authority=False,
        fresh_genesis_only=True, automatic_retry_authorized=False,
        halted_snapshot_resume_authorized=False, other_years_or_2025_authorized=False,
        locked_or_holdout_consumed=False, publication_authorized=False)


# Reuse pure original annual source, target, covariance, quality and provider
# transport functions. A fresh shared globals dictionary explicitly binds only
# the new policy/manifest/admission seams; no imported module is mutated.
G = dict(BASE.__dict__)
G.update({name:value for name,value in globals().copy().items() if name in (
    'HERE','ROOT','POLICY_VARIANT','POLICY_VERSION','SOURCE_SCOPE','PREPARATION_SCHEMA',
    'REVIEW_SCHEMA','GO_SCHEMA','MANIFEST_NAME','MANIFEST_SHA256','FIRST_TRANCHE','REMAINING_TRANCHE',
    'RESOURCE_LIMITS','RESOURCE_EXECUTION_CONTRACT','LAUNCH_CLAIM_CONTRACT',
    'GLOBAL_CONTROLLER_LEASE_CONTRACT','_SCOPE_SEAL','frozen_manifest','cell_descriptor',
    'tranche_cells','preserved_evidence_identity','code_identity','_policy')})


def _bind(function):
    result = FunctionType(function.__code__, G, function.__name__, function.__defaults__, function.__closure__)
    result.__kwdefaults__ = function.__kwdefaults__
    return result


for _name in ('_validate_preparation','prepare_source_only','_authorization_common'):
    globals()[_name] = G[_name] = _bind(getattr(BASE,_name))


def validate_root_go(preparation_raw, go_raw, expected_go_sha256, *, cell_id,
                     policy_variant=POLICY_VARIANT):
    cell_descriptor(cell_id)
    _exact(go_raw, expected_go_sha256, 'EXACT_NEW_EXTERNAL_FOUR_CELL_FORECAST_GO_REQUIRED')
    prep = _validate_preparation(preparation_raw)
    go = _object(go_raw, 'EXACT_FORECAST_ROOT_GO_OBJECT_REQUIRED')
    required = dict(schema=GO_SCHEMA, action=ACTION, **_authorization_common(preparation_raw,prep))
    workers, cpus = go.get('requested_worker_count'), go.get('worker_CPUs')
    review_sha = go.get('independent_review_SHA256')
    if (policy_variant != POLICY_VARIANT or go.get('tranche') != FIRST_TRANCHE
            or go.get('permitted_cells') != list(tranche_cells())
            or any(not _same(go.get(k),v) for k,v in required.items())
            or type(workers) is not int or workers not in (1,2)
            or not isinstance(cpus,list) or len(cpus)!=workers
            or any(type(c) is not int or c<0 for c in cpus) or len(set(cpus))!=workers
            or not isinstance(review_sha,str) or len(review_sha)!=64
            or any(c not in '0123456789abcdef' for c in review_sha)
            or expected_go_sha256 in prep['preserved_evidence_pins'].values()):
        raise ValueError('EXACT_NEW_FOUR_CELL_FORECAST_GO_REVIEW_RESOURCE_SCOPE_REQUIRED')
    return prep


REVIEW_FLAGS = (
    'generated_native_scheduler_phase_order_passed','generated_shared_pending_32_corner_passed',
    'generated_preview_isolation_passed','generated_causal_quality_passed',
    'generated_unknown_quality_no_new_exit_passed','generated_guard50_paid_exit_no_topup_passed',
    'generated_exact_four_cell_source_target_quality_gates_passed',
    'generated_minimum_proportional_projection_and_infeasible_hold_passed',
    'generated_partial_hedge_variance_increase_logged_passed',
    'generated_native_late_hardcap_D_terminal_priority_passed',
    'generated_no_old_signal_rebound_and_five_open_renewal_passed',
    'generated_ordinary_reduction_zero_and_reversal_CLOSE_timing_deferral_passed',
    'generated_pool_resource_and_aggregate_pressure_gates_passed',
    'generated_canonical_claim_and_inherited_controller_lease_gates_passed',
    'generated_native40_raw100_financial_reconstruction_passed')


def _validate_independent_review(preparation_raw, prep, review_raw, expected_review_sha256, go_raw):
    _exact(review_raw, expected_review_sha256, 'EXACT_NEW_EXTERNAL_FOUR_CELL_FORECAST_REVIEW_REQUIRED')
    review = _object(review_raw, 'EXACT_FORECAST_REVIEW_OBJECT_REQUIRED')
    go = _object(go_raw, 'EXACT_FORECAST_GO_OBJECT_REQUIRED')
    required = dict(schema=REVIEW_SCHEMA, status='PASS_SOURCE_ONLY_AND_GENERATED_NO_HISTORICAL_GO',
        **_authorization_common(preparation_raw,prep), **dict.fromkeys(REVIEW_FLAGS,True),
        actual_2023_2024_accounts_constructed=0, actual_2023_2024_financial_runs=0,
        historical_market_minutes_advanced=0, publication_actions=0, locked_source_reads=0)
    if (go.get('independent_review_SHA256') != expected_review_sha256
            or expected_review_sha256 in prep['preserved_evidence_pins'].values()
            or any(not _same(review.get(k),v) for k,v in required.items())):
        raise ValueError('EXACT_NEW_FOUR_CELL_INDEPENDENT_FORECAST_REVIEW_SCOPE_REQUIRED')
    return review


G.update(validate_root_go=validate_root_go, _validate_independent_review=_validate_independent_review)
validate_case_inputs = G['validate_case_inputs'] = _bind(BASE.validate_case_inputs)


class ForecastExecutionScope(BASE.CaseExecutionScope):
    __slots__ = ()
    def __post_init__(self):
        if self._seal is not _SCOPE_SEAL:
            raise ValueError('SCOPE_ONLY_FROM_EXACT_NEW_FOUR_CELL_FORECAST_ADMISSION')
    @property
    def source_scope(self):
        return SOURCE_SCOPE


ForecastExecutionScope.metadata = property(_bind(BASE.CaseExecutionScope.metadata.fget))
ForecastExecutionScope.validate_inputs = _bind(BASE.CaseExecutionScope.validate_inputs)
ForecastExecutionScope.validate_current = _bind(BASE.CaseExecutionScope.validate_current)


def _default_constructor_callback(*, scope, preparation, window, source_rows, decisions, targets, captured):
    import forecast_historical
    if Path(forecast_historical.__file__).resolve() != HERE/'forecast_historical.py':
        raise ValueError('EXACT_LOCAL_FORECAST_HISTORICAL_CALLBACK_MODULE_REQUIRED')
    return forecast_historical.construct_historical_case(window, source_rows, decisions, targets,
        historical_scope=scope, quality_intervals=scope.quality_intervals)


G.update(CaseExecutionScope=ForecastExecutionScope,
         _default_constructor_callback=_default_constructor_callback)
make_case = _bind(BASE.make_case)


def invalid_go_template(preparation_raw):
    prep = _validate_preparation(preparation_raw)
    return dict(schema=GO_SCHEMA, action='INVALID_TEMPLATE_NOT_ROOT_AUTHORIZATION',
        **_authorization_common(preparation_raw,prep), tranche=FIRST_TRANCHE,
        permitted_cells=list(tranche_cells()), requested_worker_count=2, worker_CPUs=[2,3],
        independent_review_SHA256='REPLACE_WITH_EXTERNAL_REVIEW_SHA256',
        status='INVALID_NO_HISTORICAL_GO')
