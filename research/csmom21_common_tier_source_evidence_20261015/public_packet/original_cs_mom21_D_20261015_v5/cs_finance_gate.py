"""Additive financial wire gate, bound to the byte-frozen source graph."""
from pathlib import Path

import cs_common as c
import cs_entry as source_entry
import cs_supersession as supersession

SOURCE_CODE_SHA256 = '21e13995b6be9482ee4e20d8e63be6d63396229035f69c963901331713342fce'
REVIEW_SCHEMA = 'INDEPENDENT_CSMOM21_FINANCIAL_ADMISSION_V2'
GO_SCHEMA = 'ROOT_FINANCIAL_CSMOM21_FIRST6_ORIGINAL_D_V2'
PREPARED_REVIEW_SCHEMA = 'INDEPENDENT_CSMOM21_PREPARED_TARGET_REVIEW_V2'
NATIVE_REVIEW_SCHEMA = 'INDEPENDENT_CSMOM21_NATIVE_GENERATED_ADMISSION_V2'


def code_identity():
    here = Path(__file__).resolve().parent
    if c.HERE != here or Path(source_entry.__file__).resolve() != here / 'cs_entry.py':
        raise ValueError('EXACT_V3_SOURCE_MODULE_IDENTITIES_REQUIRED_NO_FLAT_ALIAS_REUSE')
    if source_entry.code_identity() != SOURCE_CODE_SHA256:
        raise ValueError('FROZEN_CS_SOURCE_IDENTITY_CHANGED')
    raw = (c.HERE / 'FINANCIAL_CODE_MANIFEST.json').read_bytes()
    manifest = c.exact_object(raw)
    if manifest['source_code_manifest_SHA256'] != SOURCE_CODE_SHA256:
        raise ValueError('EXACT_FROZEN_CS_SOURCE_BINDING_REQUIRED')
    for name, pin in manifest['files'].items():
        c.exact(c.HERE / c.relative(name), pin['SHA256'], pin['bytes'])
    for name, pin in manifest['dependencies'].items():
        c.exact(c.ROOT / c.relative(name), pin['SHA256'], pin['bytes'])
    return c.sha(raw)


def policy(preparation_raw, review_sha, prepared_review_sha, native_review_sha, worker_cpus):
    if type(worker_cpus) is not list or worker_cpus != [4, 5] or any(type(cpu) is not int for cpu in worker_cpus):
        raise ValueError('EXACT_ROOT_APPROVED_MAX2_DISTINCT_CPU4_5_WORKERS_REQUIRED')
    preparation = source_entry.validate_preparation_metadata(preparation_raw)
    if preparation['tranche'] != source_entry.FIRST6:
        raise ValueError('ONLY_PREDECLARED_FIRST6_FINANCIAL_SCOPE_IMPLEMENTED')
    return dict(schema=GO_SCHEMA, status='APPROVED_FRESH_EXACT_FIRST6',
        action='RUN_FRESH_CSMOM21_COMMON_TIER_FIRST6_2022_2023_ORIGINAL_D_ONLY',
        tranche=source_entry.FIRST6, ordered_cells=list(source_entry.tranche_cells(source_entry.FIRST6)),
        requested_worker_count=2, worker_CPUs=list(worker_cpus),
        resource_limits=dict(per_case_wall_seconds=600, per_case_CPU_seconds=600,
            per_case_RSS_stop_bytes=2000000000, per_case_AS_bytes=4000000000,
            per_case_output_bytes=250000000, aggregate_live_worker_RSS_stop_bytes=3500000000,
            compute_pool_threads_max=1),
        global_inherited_flock_required=True, permanent_cross_output_cell_claim_required=True,
        stable_cross_version_claim_registry=supersession.STABLE_REGISTRY_REL,
        manual_failed_pre_finance_claim_supersession_authorized=True,
        failed_claim_supersession_packet_SHA256=supersession.PACKET_SHA,
        superseded_cells=list(supersession.FAILED_CELLS), permanent_old_claim_hash_consumption_required=True,
        source_code_manifest_SHA256=SOURCE_CODE_SHA256, financial_code_manifest_SHA256=code_identity(),
        scope_manifest_SHA256=source_entry.manifest_sha(), source_contract_map_SHA256=source_entry.contract_sha(),
        preparation_SHA256=c.sha(preparation_raw), source_stage_GO_SHA256=preparation['source_stage_GO_SHA256'],
        source_independent_review_SHA256=preparation['source_review_SHA256'],
        target_financial_independent_review_SHA256=c.digest(review_sha),
        prepared_source_target_review_SHA256=c.digest(prepared_review_sha),
        native_generated_review_SHA256=c.digest(native_review_sha),
        per_cell_input_binding_SHA256={key: row['input_binding_SHA256'] for key, row in preparation['cells'].items()},
        policy_variant='GUARD50_EXIT_ONLY', cost='BASE27', initial_cash_USDT='10000',
        free_cash_floor_USDT='1000', isolated_margin_ceiling_USDT='8500',
        quantity_profile_SHA256='94b2238b25ed345a24a1fa148c6f35523b8efe9bf47496958028844432cb8ebf',
        source_recapture='EXACT_ORIGINAL_D_BOUNDED_PER_PROCESS_2022_MEMORY_NORMALIZATION_AND_2023_CANONICAL_CAPTURE_BEFORE_FINANCE_IMPORT',
        generated_resource_probe_binding='EXACT_HASH_IN_EXTERNALLY_BOUND_NATIVE_GENERATED_REVIEW',
        saved_targets_rebuilt_during_finance=False, covariance_rebuilt_during_finance=False,
        actual_provider_iteration_authorized=True, account_construction_authorized=True,
        financial_execution_authorized=True, fresh_genesis_only=True,
        automatic_retry_authorized=False, halted_snapshot_resume_authorized=False,
        internal_margin_transfers_authorized=False, topup_authorized=False, new_capital_authorized=False,
        debt_forgiveness_authorized=False, old_D_GO_reused_as_authority=False,
        other_cells_or_holdouts_authorized=False, publication_authorized=False)


def prepared_review(preparation_raw, raw, expected_sha):
    prep = source_entry.validate_preparation_metadata(preparation_raw)
    review = c.checked_external(raw, expected_sha)
    fixed = dict(schema=PREPARED_REVIEW_SCHEMA, status='PASS',
        source_code_manifest_SHA256=SOURCE_CODE_SHA256, scope_manifest_SHA256=source_entry.manifest_sha(),
        source_contract_map_SHA256=source_entry.contract_sha(), tranche=source_entry.FIRST6,
        ordered_cells=list(source_entry.tranche_cells(source_entry.FIRST6)), years=[2022, 2023],
        preparation_SHA256=c.sha(preparation_raw), source_stage_GO_SHA256=prep['source_stage_GO_SHA256'],
        source_review_SHA256=prep['source_review_SHA256'],
        per_cell_input_binding_SHA256={key: row['input_binding_SHA256'] for key, row in prep['cells'].items()},
        per_year_array_raw_SHA256={key: row['array_raw_SHA256'] for key, row in prep['years'].items()},
        old_D_GO_reused_as_authority=False, native_financial_gate_reviewed=False,
        financial_execution_authorized=False)
    if any(c.canonical(review.get(key)) != c.canonical(value) for key, value in fixed.items()):
        raise ValueError('EXACT_SEPARATE_PREPARED_SOURCE_TARGET_REVIEW_REQUIRED')
    return c.immutable(review)


def native_review(raw, expected_sha):
    review = c.checked_external(raw, expected_sha)
    fixed = dict(schema=NATIVE_REVIEW_SCHEMA, status='PASS',
        source_code_manifest_SHA256=SOURCE_CODE_SHA256, financial_code_manifest_SHA256=code_identity(),
        scope_manifest_SHA256=source_entry.manifest_sha(), tranche=source_entry.FIRST6,
        ordered_cells=list(source_entry.tranche_cells(source_entry.FIRST6)),
        native_financial_gate_reviewed=True, financial_execution_authorized=False,
        actual_source_or_target_bodies_read=False, old_D_GO_reused_as_authority=False,
        generated_two_worker_probe_passed=True, worker_CPUs=[4, 5], maximum_observed_live_workers=2)
    if any(c.canonical(review.get(key)) != c.canonical(value) for key, value in fixed.items()):
        raise ValueError('EXACT_SEPARATE_NATIVE_GENERATED_REVIEW_REQUIRED')
    c.digest(review.get('generated_resource_probe_SHA256'))
    return c.immutable(review)


def validate(preparation_raw, go_raw, expected_go_sha, review_raw, expected_review_sha,
             prepared_review_raw, expected_prepared_review_sha, native_review_raw, expected_native_review_sha):
    preparation = source_entry.validate_preparation_metadata(preparation_raw)
    prepared_review(preparation_raw, prepared_review_raw, expected_prepared_review_sha)
    native_review(native_review_raw, expected_native_review_sha)
    review = c.checked_external(review_raw, expected_review_sha)
    fixed = dict(schema=REVIEW_SCHEMA, status='PASS', source_code_manifest_SHA256=SOURCE_CODE_SHA256,
        financial_code_manifest_SHA256=code_identity(), scope_manifest_SHA256=source_entry.manifest_sha(),
        source_contract_map_SHA256=source_entry.contract_sha(), preparation_SHA256=c.sha(preparation_raw),
        tranche=source_entry.FIRST6, ordered_cells=list(source_entry.tranche_cells(source_entry.FIRST6)),
        source_stage_GO_SHA256=preparation['source_stage_GO_SHA256'], old_D_GO_reused_as_authority=False,
        native_financial_gate_reviewed=True, financial_execution_authorized=False,
        prepared_source_target_review_SHA256=c.digest(expected_prepared_review_sha),
        native_generated_review_SHA256=c.digest(expected_native_review_sha),
        real_CLI_generated_GO_guard_integration_reviewed=True,
        failed_claim_supersession_packet_SHA256=supersession.PACKET_SHA,
        stable_cross_version_claim_registry=supersession.STABLE_REGISTRY_REL,
        permanent_one_use_failed_claim_consumption_reviewed=True)
    if any(c.canonical(review.get(key)) != c.canonical(value) for key, value in fixed.items()):
        raise ValueError('EXACT_NEW_CS_TARGET_NATIVE_FINANCIAL_REVIEW_REQUIRED')
    go = c.checked_external(go_raw, expected_go_sha)
    if c.canonical(go) != c.canonical(policy(preparation_raw, expected_review_sha, expected_prepared_review_sha, expected_native_review_sha, go.get('worker_CPUs'))):
        raise ValueError('EXACT_NEW_CS_FINANCIAL_ROOT_AUTHORITY_REQUIRED')
    return c.immutable(go)
