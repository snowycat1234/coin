"""Seal exact SOURCE/GENERATED evidence only. Never writes a historical GO."""
import os
for key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS','POLARS_MAX_THREADS','VECLIB_MAXIMUM_THREADS'):
    os.environ[key]='1'
os.sched_setaffinity(0,{4})
import json,sys
from pathlib import Path
from hashlib import sha256
from datetime import datetime,timezone
from decimal import Decimal as D
ROOT=Path(__file__).resolve().parents[1];OUT=Path(__file__).resolve().parent
MODULE=ROOT/'traditional_D_partial2021_20261015'
sys.path.insert(0,str(MODULE))
import partial_entry as e
import run_partial as runner
from saved_native_reconciliation import reconcile_saved_native,checker_sha256
def digest(path):return sha256(Path(path).read_bytes()).hexdigest()
def pin(path):return dict(SHA256=digest(path),bytes=Path(path).stat().st_size)
def load(path):return json.loads(Path(path).read_bytes())
prep_path=MODULE/'source_preparation_final/PREPARATION.json';prep_raw=prep_path.read_bytes();prep=e._validate_preparation(prep_raw)
assert digest(prep_path)=='40e9eda0977f2fc28c051b9f1d08c214be9b384e398ef43f166100924fde3f02'
assert prep['code_identity']==e.code_identity()
assert e.MANIFEST_SHA256=='03b8016fd98fc2bc5c60db5800672a05a558351b4cfef760dfa34014aa5be85c'
implementation_pins=load(MODULE/'SOURCE_PINS.json');implementation=load(MODULE/'IMPLEMENTATION_RECEIPT.json')
assert digest(MODULE/'SOURCE_PINS.json')=='dc216d7b31f35576d4b47bcbc561eda7da926fcc2978cba1964ae6c89289bf93'
assert digest(MODULE/'IMPLEMENTATION_RECEIPT.json')=='84f00e47e64a43b6a1fdc7ed56f8503ec17049b417fe1b5a7270cd2800755159'
assert len(implementation_pins['files'])==52
for name,value in implementation_pins['files'].items():assert pin(MODULE/name)==value
assert implementation['code_identity']==prep['code_identity']
assert not (MODULE/'EXECUTION_CLAIMS').exists()
source=load(OUT/'SOURCE_REVIEW_FINAL.json');generated=load(OUT/'GENERATED_REVIEW_FINAL.json');gates=load(OUT/'GATE_REVIEW_ATTEMPT001.json')
assert source['status']=='PASS_SOURCE_ONLY' and generated['status']=='PASS_GENERATED_ONLY'
assert gates['status']=='PASS_PORTABLE_SOURCE_AND_NEGATIVE_GATES_NO_HISTORICAL_GO'
assert gates['preparation']==pin(prep_path) and gates['code_identity']==prep['code_identity']
assert generated['tests_run']==8 and generated['failures']==generated['errors']==0
assert source['all_nine_targets_prefix_byte_equal_checks']==source['all_nine_targets_future_row_perturbation_checks']==2466
assert source['covariance_prefix_checks']==source['covariance_future_row_perturbation_checks']==274
assert gates['negative_checks']==75 and not gates['cold_private_authority_open_attempts'] and not gates['cold_private_authority_body_reads']
for record in (source,generated):
    for name,value in record['code_files'].items():
        assert (value['SHA256'] if isinstance(value,dict) else value)==digest(MODULE/name)
for record in (source,generated,gates):
    assert record['actual_2021_accounts_constructed']==record['actual_2021_financial_runs']==record['historical_market_minutes_advanced']==0
    assert record['CPU_affinity']==[4] and all(value==[4] for value in record['observed_task_affinities'].values())
for record in (source,gates):
    counts=record['prohibited_boundary_call_counts']
    assert all(value==0 for value in counts.values()) if isinstance(counts,dict) else all(x['calls']==0 for x in counts)
core=load(MODULE/'SOURCE_GATE_TEST_RECEIPT_FINAL.json');preprec=load(MODULE/'SOURCE_PREPARATION_RECEIPT_FINAL.json')
assert core['code_identity']==preprec['code_identity']==prep['code_identity']
assert core['preparation_SHA256']==preprec['preparation_SHA256']==digest(prep_path)
assert core['all_nine_seals_revoked'] is True and len(core['metadata_callbacks'])==9
assert [x['cell_id'] for x in core['metadata_callbacks']]==list(e.tranche_cells())
for metadata in core['metadata_callbacks']:
    cell=prep['cells'][metadata['cell_id']]
    assert metadata['scope_seal_revoked'] is True and metadata['post_revocation_validation_rejected'] is True
    assert metadata['generated_fixture_scope_used'] is False and metadata['fresh_genesis_only'] is True
    assert metadata['input_binding_SHA256']==cell['input_binding_SHA256']
    assert metadata['code_identity_SHA256']==e._json_sha(prep['code_identity'])
    assert metadata['calendar']==[e.s.START,e.s.END] and metadata['days']==274 and metadata['required_minutes']==394560
for key in ('actual_2021_accounts_constructed','actual_2021_financial_runs','historical_market_minutes_advanced','provider_iterations','process_launches','canonical_live_claims_created','real_GO_written'):
    assert core[key]==preprec[key]==0
for name in ('source_preparation_boundary_counts','actual_metadata_positive_boundary_counts'):
    assert all(x['calls']==0 for x in core[name])
assert all(x['calls']==0 for x in preprec['all_financial_native_provider_process_claim_GO_boundaries'])
assert preprec['historical_scopes_created']==0
for name,count in (('TEST_PARTIAL_FINAL.log',21),('TEST_GENERATED_FINAL.log',31)):
    log=(MODULE/name).read_text();assert f'Ran {count} tests' in log and log.endswith('OK\n') and 'skipped=' not in log
profile_dir=MODULE/'generated_profile_final';profile=load(profile_dir/'GENERATED_POOL_PROFILE.json')
assert profile['runner_SHA256']==digest(MODULE/'run_partial.py')
assert profile['profile_SHA256']==digest(MODULE/'profile_generated.py')
assert profile['checker_SHA256']==checker_sha256()=='d4df52de450b6c1a83801168e0bb8069bd3dd94d3058854fda971175bf6f5135'
assert profile['generated_only'] is True and profile['historical_account_objects_constructed']==profile['historical_financial_runs']==0
assert profile['limits']==prep['resource_limits'] and profile['coordinator_CPU_affinity']==[4,5]
assert profile['annual_resource_envelope_certified'] is False and profile['host_quota_guaranteed'] is False
overlap=[x for x in profile['observations'] if len(x['workers'])==2]
assert overlap
for observation in profile['observations']:
    assert observation['aggregate_live_RSS_bytes']<=prep['resource_limits']['aggregate_live_worker_RSS_stop_bytes']
    assert len(observation['workers'])<=2
    for worker in observation['workers']:
        assert worker['CPU_affinity'] in ([4],[5])
        assert all(task['CPU_affinity']==worker['CPU_affinity'] for task in worker['tasks'])
saved_profile_evidence=[];warnings_per_worker=[]
for row in profile['cases']:
    directory=profile_dir/row['cell_id'];checkpoint=load(directory/'TERMINAL_CHECKPOINT.json')
    assert checkpoint['cell_id']==row['cell_id']
    for name,value in checkpoint['files'].items():assert digest(directory/name)==value
    audit=load(directory/'GENERATED_AUDIT.json');result=load(directory/'GENERATED_RESULT.json');receipt=load(directory/'CASE_RECEIPT.json')
    proof=reconcile_saved_native(audit,result)
    assert runner.body(proof)==(directory/'GENERATED_PROOF.json').read_bytes() and proof['passed'] is True
    assert receipt['generated_minutes']==4320 and receipt['actual_affinity']==[row['CPU']]
    assert receipt['synthetic_calendar']==[205*e.s.DAY,208*e.s.DAY]
    assert receipt['thread_environment']=={name:'1' for name in runner.THREAD_ENV}
    assert all(a==[row['CPU']] for a in receipt['all_TID_affinities']) and receipt['lease_FD_inherited'] is True
    assert receipt['wall_seconds']<600 and receipt['CPU_seconds']<600 and receipt['max_RSS_bytes']<2_000_000_000
    assert not audit['transfer_journal'] and not audit['settlement_journal'] and audit['historical_execution_scope'] is None
    warnings=[a for r in audit['monitor_journal'] for a in r['actions'] if a['reason']=='GUARD50_PAID_EXIT_NO_TOPUP']
    assert len(warnings)==3 and all(a['full_actual_position_exit_required'] is True and a['transferred']=='0' for a in warnings)
    warning_signals={r['event_us'] for r in audit['monitor_journal'] if r['actions']}
    paid=[t for t in audit['trades'] if t['symbol']=='BTCUSDT' and t['leg']=='CLOSE' and t['signal_us'] in warning_signals]
    assert len(paid)==3 and all(D(t['decimal_strings']['quantity_after'])==0 for t in paid)
    warnings_per_worker.append(len(paid))
    saved_profile_evidence.extend(directory/name for name in checkpoint['files'])
    saved_profile_evidence.append(directory/'TERMINAL_CHECKPOINT.json')
review=dict(schema=e.REVIEW_SCHEMA,status='PASS_SOURCE_ONLY_AND_GENERATED_NO_HISTORICAL_GO',
    **e._authorization_common(prep_raw,prep),**dict.fromkeys(e.REVIEW_FLAGS,True),
    actual_2021_accounts_constructed=0,actual_2021_financial_runs=0,historical_market_minutes_advanced=0,
    publication_actions=0,locked_source_reads=0,review_created_UTC=datetime.now(timezone.utc).isoformat(),
    reviewer='independent_original_D_partial2021_source_generated_review',historical_authorization='NO_HISTORICAL_GO',
    real_historical_GO_files_written=0,actual_2021_historical_financial_authority_granted=False,
    parent_root_only_can_admit_or_launch_actual_2021_after_this_review=True,
    scope='Exact original STATIC50/H090/VOL_MANAGED_HOLD LOW/MID/HIGH, fresh10000 Apr2 through Dec31 paid terminal calendar; SOURCE and fake-generated evidence only.',
    source_preparation=pin(prep_path),source_preparation_receipt=pin(MODULE/'SOURCE_PREPARATION_RECEIPT_FINAL.json'),
    independent_source_completion_review=pin(MODULE/'SOURCE_COMPLETION_REVIEW.json'),
    source_checks=dict(decision_count=274,source_native_minutes=394560,source_coverage_funding_marks=4110,
        source_funding_coverage_is_not_owned_charges=True,old_Jan1_not_owned_flag_removed=True,
        physically_decoded_daily_fields=['symbol_order','close_available_us','close'],physically_decoded_close_shape=[1463,5],
        permitted_daily_projection_rows=565,effective_required_past_rows=473,
        per_decision_prefix_target_byte_checks=2466,per_decision_covariance_prefix_checks=274,
        within_calendar_future_row_target_perturbation_checks=2466,within_calendar_future_covariance_perturbation_checks=274,
        outside_permitted_projection_mutated_rows=898,outside_projection_all_targets_covariance_byte_invariant=True,
        nine_unique_target_paths=True,H090_alias_mapping={},financial_accounts_created=0,provider_iterations=0),
    generated_tests=dict(author_source_and_metadata_unittests=21,author_generated_regression_unittests=31,
        independent_same_input_financial_and_AST_unittests=8,total_current_unittests=60,
        independent_additional_negative_gate_checks=75,independent_source_prefix_and_future_numeric_checks_counted_separately=True,
        all_three_tier_complete_D_financial_states_ledgers_noop_hashes_minutes_guard_receipts_byte_equal=True,
        historical_genesis_constructor_AST_identical_to_frozen_adapter_except_explicit_new_reviewed_entry_import=True,
        generated_financial_metadata_exclusions=['top-level version','contract version','integration_version','continuation_policy','partial_DEV','partial_return_annualized','annual_wallets_compounded'],
        no_frozen_module_edits_or_global_financial_monkeypatch=True),
    actual_source_metadata_tests=dict(approved_author_callbacks=9,each_manifest_cell_once_in_final_run=True,
        financial_native_provider_process_claim_GO_boundary_calls=0,all_nine_seals_revoked=True,
        post_revocation_current_validation_rejected=True,independent_reviewer_positive_callbacks=0,
        independent_reviewer_historical_scopes_created=0,all_test_GO_and_review_authority_ephemeral_in_memory_only=True),
    portability=dict(old_2023_2024_GO_hashes_metadata_only=True,new_review_and_GO_external_and_exact_required=True,
        cold_old_private_authority_body_open_attempts=0,cold_old_private_authority_body_reads=0,
        original_public_financial_and_strategy_code_dependencies_still_required=True,
        fresh_source_completion_and_quality_checks_preserved=True),
    financial_reconstruction=dict(authoritative='CHRONOLOGICAL_NATIVE40_EVENT_RECONSTRUCTION',native_precision=40,
        raw_stored_delta_precision=100,epsilon_or_forced_balancing=False,nonzero_raw100_residual_retained=True,
        legacy_false_delta_sum_boolean_never_rewritten=True,saved_fake_generated_profile_reconstruction_repeated_independently=True),
    resource_evidence=dict(per_case_limits=prep['resource_limits'],profile=pin(profile_dir/'GENERATED_POOL_PROFILE.json'),
        assigned_worker_CPUs=[4,5],generated_native_minutes_per_worker=4320,overlap_samples=len(overlap),
        peak_observed_aggregate_worker_RSS_bytes=max(x['aggregate_live_RSS_bytes'] for x in profile['observations']),
        paid_Guard50_warning_exits_per_worker=warnings_per_worker,all_worker_and_helper_TIDs_on_assigned_single_CPU=True,
        numerical_thread_environment_one_before_import=True,inherited_temporary_controller_lease_proven=True,
        sampled_RSS_output_affinity_watchdog_and_kernel_CPU_AS_limits=True,full_partial_calendar_resource_feasibility_certified=False,
        host_CPU_or_memory_quota_certified=False,no_retry_duplicate_claim_clear_or_snapshot_resume=True),
    reviewed_invariants=[
        'All nine raw target paths remain explicit. H090 differs from same-tier STATIC50; no 2023/24 duplicate inference or return-selected alias is admitted.',
        'The new historical fresh-genesis constructor consumes the exact new sealed scope and never uses a fake generated flag or old authorization scope.',
        'Frozen D monitor, transfer prohibition and native financial kernel code objects are unchanged. Known fresh E<=half B schedules the paid full actual position protective exit with no topup, transfer, capital injection or quantity increase.',
        'Native mark risk precedes full same-clock funding; only then may the D monitor create its warning intent. Unknown/stale quality blocks new risk/new warning and creates no new exit. Legitimate strategy reductions and pre-existing native risk/terminal exits retain original paid paths.',
        'BASE27 costs, fixed10000 shared wallet,1000 cash floor,8500 isolated ceiling,1x leverage, original tiers and frozen coarse lots are unchanged. Shared32-corner previews remain detached from live fallback inventory/callbacks.',
        'Original signal latency, cold-start first increase Apr2 00:01:00.000001, five-open renewal/shared capacity and affected old-signal takeover cancellation remain unchanged.',
        'Dec31 terminal signal is22:59; eligible opens23:00 through23:59 and latest paid fill23:59:00.000001. End+1 source witnesses confer no execution or Jan1 funding permission.',
        'Genuine unpaid debt is retained. Conditional collateral forfeiture and support remain separately labeled from actual paid market flat. No HALT reset, snapshot restart, epsilon or residual balancing is introduced.'
    ],
    limitations=[
        'This receipt is SOURCE/GENERATED review evidence and explicitly NO_HISTORICAL_GO. It creates no historical account, financial history, launch claim, publication or execution authority.',
        '2021 remains development data; no tuning, new threshold, ML, forecast-monitor policy, provider acquisition, denied-source retry,2025 body or2026 holdout access is authorized or performed.',
        'Raw funding units, publication/arrival, exact exchange charge pricing, historical listing/lot/filter/maintenance and native venue execution remain uncertified.4110 marks certify source coverage only; actual ownership must follow native paid fills.',
        'All Jan1 through Apr1 cash padding is excluded from274 reported trading calendar days. Partial-period return must not be annualized or represented as a continuous compounded annual account or realized-risk-matched comparison.',
        'Generated short runs prove bounded mechanisms and supplied event arithmetic, not full394560-minute runtime feasibility, exchange fills or enforceable host CPU/memory quotas.'
    ])
paths=[OUT/'review_source_final.py',OUT/'review_generated_final.py',OUT/'review_gates.py',Path(__file__),
    OUT/'SOURCE_REVIEW_FINAL.json',OUT/'GENERATED_REVIEW_FINAL.json',OUT/'GATE_REVIEW_ATTEMPT001.json',
    OUT/'INDEPENDENT_SOURCE_GENERATED_FINAL.log',OUT/'GATE_REVIEW_ATTEMPT001.log',
    MODULE/'SOURCE_GATE_TEST_RECEIPT_FINAL.json',MODULE/'SOURCE_PREPARATION_RECEIPT_FINAL.json',
    MODULE/'SOURCE_PINS.json',MODULE/'IMPLEMENTATION_RECEIPT.json',
    MODULE/'TEST_PARTIAL_FINAL.log',MODULE/'TEST_GENERATED_FINAL.log',MODULE/'GENERATED_PROFILE_FINAL.log',
    MODULE/'ROOT_GO_TEMPLATE_UNAPPROVED.json',MODULE/'README.md',MODULE/'FUTURE_LAUNCH_TEMPLATE.txt',
    profile_dir/'GENERATED_POOL_PROFILE.json',*saved_profile_evidence]
review['evidence_files']={str(path.relative_to(ROOT)):pin(path) for path in paths}
assert prep['code_identity']==e.code_identity()
review_raw=(json.dumps(review,indent=2,sort_keys=True,allow_nan=False)+'\n').encode()
# Exact review-schema check with one ephemeral in-memory fixture GO; no scope,
# native constructor, financial loop, claim, process or GO file is created.
fixture=e._canonical(dict(schema=e.GO_SCHEMA,action=e.ACTION,**e._authorization_common(prep_raw,prep),tranche=e.FIRST_TRANCHE,
    permitted_cells=list(e.tranche_cells()),requested_worker_count=1,worker_CPUs=[4],independent_review_SHA256=e._sha(review_raw)))
admitted=e.validate_root_go(prep_raw,fixture,e._sha(fixture),cell_id=e.tranche_cells()[0])
assert e._validate_independent_review(prep_raw,admitted,review_raw,e._sha(review_raw),fixture)==review
path=OUT/'INDEPENDENT_ORIGINAL_D_PARTIAL2021_REVIEW.json'
with path.open('xb') as stream:stream.write(review_raw);stream.flush();os.fsync(stream.fileno())
print(str(path.relative_to(ROOT)));print(digest(path));print(len(review_raw));print('NO_HISTORICAL_GO')
