"""Seal independent receipts without changing the source packet or its ZIP."""
import os
for k in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS','POLARS_MAX_THREADS','VECLIB_MAXIMUM_THREADS'):os.environ[k]='1'
os.sched_setaffinity(0,{1})
from pathlib import Path
from hashlib import sha256
import json,re
R=Path.cwd();O=Path(__file__).resolve().parent;P=R/'full2025_source_generated_packet_20261015_v1';E=O/'cold_extraction'/P.name
def pin(f):
    b=f.read_bytes();return dict(bytes=len(b),SHA256=sha256(b).hexdigest())
def read(f):return json.loads(f.read_bytes())
def save(n,v):
    with (O/n).open('x') as f:json.dump(v,f,indent=2,sort_keys=True,allow_nan=False);f.write('\n')
before=read(O/'BEFORE_ORIGINAL_INPUT_PINS.json')['files']
after={n:pin(R/n) for n in before}
assert before==after
manifest=read(P/'FILE_MANIFEST.json')['files']
expected=dict(manifest);expected['FILE_MANIFEST.json']=dict(bytes=53364,SHA256='2939fdfe4cde068fa88a524a539ace784b9d090c3eb084e50321ba4f6b10b606')
for base in (P,E):
    files={f.relative_to(base).as_posix():pin(f) for f in base.rglob('*') if f.is_file()}
    assert files==expected and not any(f.is_symlink() for f in base.rglob('*'))
assert pin(R/(P.name+'.zip'))==dict(bytes=1559883,SHA256='e2278f738d5f2a3aa2d2d71a1b81bf80f80ebe96eeeeaea27a69a39edb0beade')
omitted={r['original_workspace_relative_path']:r['original'] for r in read(P/'OMISSIONS_AND_HASH_ONLY_EVIDENCE.json')['files']}
frozen=[]
folder='full2025_selective_source_qualification_plan_20261015'
for row in read(P/folder/'FROZEN_MANIFEST.json')['files']:
    n=folder+'/'+row['file'];wanted={k:row[k] for k in ('bytes','SHA256')}
    assert expected.get(n,omitted.get(n))==wanted
    frozen.append(n)
for row in read(P/folder/'OBSERVED_METADATA_CODE_PINS.json')['observed_metadata_code_files']:
    n=row['path'];wanted={k:row[k] for k in ('bytes','SHA256')}
    assert expected.get(n,omitted.get(n))==wanted
    frozen.append(n)
for n,wanted in read(P/'traditional_D_full2025_20261015/DEPENDENCY_PINS.json').items():assert expected[n]==wanted
deps=read(P/'EXTERNAL_RAW_SOURCE_DEPENDENCIES.json')['omitted_exact_runtime_metadata_dependencies']
assert set(x['original_workspace_relative_path'] for x in deps)<=set(frozen)
code=(P/'full2025_selective_source_qualification_20261015_v2/contracts.py').read_text()
assert "for item in manifest['files']:" in code and "for item in contents['OBSERVED_METADATA_CODE_PINS.json']['observed_metadata_code_files']:" in code
source_review=P/'full2025_qualified_source_v2_independent_review_20261015/REVIEW.json'
assert pin(source_review)['SHA256']=='ed38099a903e003db750015f38cd92db0fccd2d090d96ca910f06144f90f8ee1'
sv=read(source_review);assert (sv['canonical_source_files'],sv['canonical_bytes'])==(15,46269167)
assert not sv['FAIL_count'] and not sv['financial_GO_granted'] and len(sv['inherited_proofs'])==5
v1=read(P/'full2025_qualified_source_independent_review_20261015/REVIEW.json')
assert v1['status']=='BLOCKED_ACTUAL_SOURCE_QUALIFICATION_STOPPED_NO_CANONICAL_ADMISSION'
assert v1['source_observed_counters']['opaque_objects_rehashed']==217
assert all(v1['source_observed_counters'][k]==0 for k in ('archive_reassemblies','canonical_files_written','inner_decompressed_bytes','selected_checksum_bodies','selected_inner_bodies','selected_outer_bodies'))
assert not any(v1['forbidden_attempts'].values())
fix=read(P/'full2025_selective_source_qualification_20261015_v2/NARROW_V2_FIX_AND_PRESERVATION_RECEIPT.json')
assert fix['resolver_key']==['exact_original_repository_path','exact_original_commit','bytes','SHA256','GitBlobSHA1']
assert fix['original_source_attempt_unchanged'] and not fix['authority_scope_expanded'] and not fix['source_hash_predicates_changed']
boundary=read(P/'RUNTIME_AND_EVIDENCE_BOUNDARY.json')
for n,k in [('traditional_D_full2025_20261015/CODE_MANIFEST.json','D_code_manifest_SHA256'),('traditional_D_full2025_20261015/DELIVERABLE_PINS.json','D_deliverable_SHA256'),('traditional_D_full2025_20261015_source_preparation_attempt001/PREPARATION.json','actual_saved_preparation_SHA256'),('traditional_D_full2025_independent_review_20261015/prepared_source_review_attempt001/ADMISSION_COMPATIBLE_REVIEW_RECEIPT.json','actual_saved_preparation_review_SHA256')]:assert expected[n]['SHA256']==boundary[k]
prep_review=read(P/'traditional_D_full2025_independent_review_20261015/prepared_source_review_attempt001/REVIEW_SUMMARY.json')
assert prep_review['actual_targets_compared']==9 and prep_review['decisions']==365 and not prep_review['FAIL_count']
assert prep_review['root_process_exit_evidence']['exit_code']==0 and prep_review['root_stage_exit_confirmed_by_parent']

suites=[]
for suite,counts in [('QUALIFIER',(113,109,4)),('FULL',(110,108,2))]:
    f=O/(suite+'_COLD_INDEPENDENT_RECEIPT.json');v=read(f)
    assert v['status']=='PASS_EXACT_FAKE_SUBSET_WITH_EXPLICIT_SKIPS' and (v['tests_run'],v['tests_passed'],len(v['skipped']))==counts
    assert v['failures']==v['errors']==0 and not any(v['observed'].values())
    assert not v['blocked_attempts'] and not v['foreign_project_modules'] and not v['exact_copied_Python_files_changed'] and not v['independent_io_guard_denials']
    assert v['CPU_affinity']==[1] and all(x==[1] for x in v['all_TID_affinities'].values()) and all(x=='1' for x in v['thread_environment'].values())
    assert not v['approved_actual_numeric_bytes_decoded'] and not v['two_worker_probe_rerun']
    suites.append(dict(path=f.name,pin=pin(f),tests_run=v['tests_run'],tests_passed=v['tests_passed'],skipped=v['skipped'],CPU_seconds=v['CPU_seconds'],wall_seconds=v['wall_seconds'],max_RSS_bytes=v['max_RSS_bytes']))

failed=read(O/'independent_failed_invocation001/QUALIFIER_COLD_RECEIPT.json')
assert failed['status']=='FAIL' and (failed['tests_run'],failed['tests_passed'],failed['failures'],len(failed['skipped']))==(113,107,2,4)
assert failed['observed']['original_workspace_fallback_read_attempts']==1 and failed['observed']['actual_source_or_cache_body_read_attempts']==0
rawlog=R/'full2025_source_generated_packet_independent_review_private_20261015_attempt002/QUALIFIER_COLD_INDEPENDENT.log'
raw=rawlog.read_text()
# An explicit non-authoritative derivative preserves the diagnostic while
# omitting all absolute workspace paths and the path-containing final error.
public='\n'.join('[OMITTED_PRIVATE_ABSOLUTE_PATH_LINE]' if any(x in line for x in ('/'+ 'workspace/','/'+ 'Users/','/'+ 'home/agent/')) else line for line in raw.splitlines())+'\n'
save('independent_failed_invocation001/PROVENANCE.json',dict(schema='INDEPENDENT_COLD_INVOCATION_PROVENANCE_V1',not_a_packet_failure=True,first_invocation=dict(status='FAIL_DOCUMENTED_WRONG_WORKING_DIRECTORY',receipt='QUALIFIER_COLD_RECEIPT.json',receipt_pin=pin(O/'independent_failed_invocation001/QUALIFIER_COLD_RECEIPT.json'),tests_run=113,tests_passed=107,failures=2,skips=4,finding='Invoked from workspace cwd instead of the documented extracted-packet cwd. Conservative audit interpreted a temporary symlink-cleanup dir_fd-relative open of real as an outside-packet source fallback and blocked it. No actual source/GO/process/network body action occurred.',text_log_retained=False,text_log_limitation='The text log was inadvertently overwritten by the subsequent invocation output. The exact machine-readable failed receipt above is retained.'),second_invocation=dict(status='TESTS_PASSED_BUT_EXCLUSIVE_RECEIPT_OUTPUT_ALREADY_EXISTED',tests_run=113,tests_passed=109,skips=4,raw_log_hash_only=pin(rawlog),not_original_log_bytes=True,public_log_derivative='independent_invocation002/PUBLIC_LOG_DERIVATIVE.json'),resolution='Final invocation used the documented packet cwd and fresh output paths, with no code or test changes. Final exact suites passed. The sealed archive and its two author failed attempts are unchanged.'))
save('independent_invocation002/PUBLIC_LOG_DERIVATIVE.json',dict(schema='EXPLICIT_INDEPENDENT_INVOCATION_LOG_PATH_OMISSION_DERIVATIVE_V1',original=pin(rawlog),not_exact_original_bytes=True,not_current_authority=True,transformation='Private absolute-path-containing lines replaced, without a reversible replacement map.',public_text=public))
save('PUBLICATION_SCOPE_ADDENDUM.json',dict(schema='INDEPENDENT_FULL2025_SOURCE_PACKET_PUBLICATION_SCOPE_ADDENDUM_V1',status='REQUIRED_COMPANION_FOR_ANY_FUTURE_PUBLICATION_OR_SHARED_RECOVERY_CLAIM',archive=P.name+'.zip',archive_pin=pin(R/(P.name+'.zip')),scope='Source qualification, generated-code and saved source/target-preparation evidence only.',historical_snapshots='Archived zero-finance counters, source-only reviews, invalid authority templates, pending-gate labels and generated-only manifests describe the producing stage or the historical snapshot that wrote them. They are not a global assertion that no later financial admission or run occurred.',separate_later_financial_run=dict(root_launch_report_UTC='2026-10-15T14:18:57Z',run='traditional_D_full2025_20261015_financial_attempt001',financial_GO_SHA256_metadata_only='6e461c3b47ee4318683cd94fd1e9fd8296b91d6848b5a0bfe71b252f13c8aba9',evidence='Parent supplied separate root launch confirmation to this reviewer. This reviewer did not open the GO body, inspect its financial outputs, or rerun it.',outside_this_archive=True,controller_success_or_outcome_claim=False),actual_financial_GO_bodies_or_outputs_added=False,publication_actions=0,archive_repacked=False,independent_review='Independent byte/static and documented one-CPU fake-only cold checks are complete in the companion review receipt. Sealed pending-review labels remain immutable at-sealing records.',derivative_counts=dict(primary_builder_stage=10,final_including_failed_cold_receipt_derivative=11),cold_CPU_note='Archived author receipts use CPU2. Independent replay used CPU1. The exact wrapper retains historical CPU2 text in two CPU4-incompatible skip explanations; actual final affinity and all observed thread affinities are recorded as CPU1. The same six explicit omissions/skips apply.',recovery_limits='217 raw parts, all raw archive/member bodies, 12 monthly canonical arrays, valid GO bodies, execution claims and actual financial results remain absent. Four exact private-prefix metadata/log files are genuine frozen load_plan dependencies, so fresh source GO alone does not restore raw qualification. The separate canonical-D code closure needs external canonical months, fresh scoped preparation/equivalence review and financial GO. No snapshot or full original-history cold restart is supported.',publication_gate='No publication is authorized or performed by this review. The pending 2022 source/results verified publication chain must precede new 2025 publication. The last verified parent remains d8efda159de3f9e73b91009504d850534a953e47.'))
save('AFTER_ORIGINAL_INPUT_PINS.json',dict(schema='INDEPENDENT_FULL2025_AFTER_ORIGINAL_INPUT_PINS_V1',files=after,all_before_after_equal=True,original_files_checked=len(after),archive_and_extracted_packet_file_sets_exact=True))
save('INDEPENDENT_COLD_AGGREGATE_RECEIPT.json',dict(schema='INDEPENDENT_FULL2025_COLD_AGGREGATE_V1',status='PASS_DOCUMENTED_EXACT_FAKE_SUBSET_WITH_SIX_EXPLICIT_SKIPS',tests_run=223,tests_passed=217,exact_archived_tests_declared=217,exact_archived_tests_passed=211,additional_packet_integrity_tests_passed=6,explicit_skips=6,failures=0,errors=0,suites=suites,CPU_affinity=[1],all_observed_thread_affinities=[1],numerical_pool_threads=1,actual_source_or_cache_body_reads=0,valid_GO_body_reads=0,actual_source_normalization=0,actual_targets_or_covariance_generated=0,actual_accounts_constructed=0,actual_provider_iterations=0,actual_financial_runs=0,actual_historical_scopes=0,actual_canonical_claims=0,actual_GO_issued=0,external_process_attempts_inside_cold_interpreter=0,network_attempts=0,two_worker_probe_rerun=False,approved_numeric_bytes_integrity_hashed_only=True,approved_numeric_bytes_decoded=False,archived_original_code_or_tests_modified=False,independent_invocation_provenance='independent_failed_invocation001/PROVENANCE.json',original_author_failed_attempts_in_archive=2,publication_actions=0))
save('FINAL_REVIEW_RECEIPT.json',dict(schema='INDEPENDENT_FULL2025_SOURCE_GENERATED_PACKET_FINAL_REVIEW_V1',status='PASS_BYTES_STATIC_AND_DOCUMENTED_FAKE_COLD_WITH_REQUIRED_SCOPE_ADDENDUM',archive=P.name+'.zip',archive_pin=pin(R/(P.name+'.zip')),manifest_pin=expected['FILE_MANIFEST.json'],members=270,exact_original_copies=235,current_D_code_identity_files=94,all_original_and_frozen_inputs_before_after_unchanged=True,original_files_rechecked=len(after),additional_frozen_plan_and_transitive_metadata_rows_checked=len(frozen),full_archive_allowlist='ARCHIVE_FULL_FILE_ALLOWLIST.json',static_receipt='STATIC_REVIEW_RECEIPT.json',cold_receipt='INDEPENDENT_COLD_AGGREGATE_RECEIPT.json',publication_scope_addendum='PUBLICATION_SCOPE_ADDENDUM.json',primary_builder_derivative_count=10,final_derivative_count=11,derivatives_are_separate_non_authoritative_non_original_files=True,private_prefix_literal_or_reversible_encoding_or_secret_signature_matches=0,static_scan_is_not_universal_secret_absence_proof=True,source_v1_failure_preserved=True,source_v1_217_rehashes_before_wrong_part004_path_stop=True,source_v1_selected_2025_bodies_and_canonical_writes=0,source_v1_exit_1_evidence='Parent root confirmation; reviewer did not independently observe that historical process exit.',source_v2_audit_pin=pin(source_review),source_v2_15_canonical_files_46269167_bytes=True,source_v2_365_past_only_windows_audited_in_saved_review=True,raw_normalization_and_original_warmup_equivalence_inherited_explicitly=True,actual_numeric_bodies_not_decoded_by_this_review=True,actual_source_target_financial_or_resource_probe_rerun=False,actual_saved_preparation_review_SHA256=boundary['actual_saved_preparation_review_SHA256'],actual_saved_preparation_SHA256=boundary['actual_saved_preparation_SHA256'],cold_tests_run=223,cold_tests_passed=217,explicit_skips=6,cold_failures=0,cold_errors=0,original_author_failed_attempts_preserved=2,independent_failed_invocations_transparently_recorded=True,complete_raw_qualifier_cold_runtime_metadata_closure=False,four_omitted_metadata_files_are_runtime_dependencies=True,separate_canonical_D_code_closure_complete=True,external_canonical_months_required=12,raw_transport_parts_omitted=217,fresh_source_GO_alone_restores_raw_qualification=False,snapshot_restart_or_full_original_historical_replay_supported=False,financial_GO_or_actual_financial_results_in_archive=False,global_financial_admission_never_happened_claim=False,separate_later_financial_run_outside_archive=True,separate_financial_outcomes_or_controller_success_claim=False,not_price_free=True,all2025_inputs_seen_development=True,OOS_or_holdout_claim=False,funding_units_or_arrival_or_venue_execution_certified=False,annual_resource_fit_or_two_full_CPU_host_quota_certified=False,publication_status='BLOCKED_PENDING_PRIOR_2022_VERIFIED_CHAIN_AND_AUTHORIZED_PUBLICATION_ROUTE',publication_actions=0,sealed_archive_code_reviews_or_inputs_modified=False))
print(json.dumps(dict(status='PASS_FINAL_WITH_REQUIRED_SCOPE_ADDENDUM',original_files_checked=len(after),frozen_plan_transitive_rows=len(frozen),cold_passed=217,skips=6)))
