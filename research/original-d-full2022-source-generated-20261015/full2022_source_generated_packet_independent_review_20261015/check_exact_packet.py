"""Independent static checks for the exact sealed source/generated packet."""
from pathlib import Path
from hashlib import sha256
from collections import Counter
import json,re,os
os.sched_setaffinity(0,{1})
HERE=Path(__file__).resolve().parent;WORK=HERE.parent;P=HERE/'cold_unpack/full2022_source_generated_packet_20261015_v1'
j=lambda p:json.loads(p.read_bytes())
h=lambda b:sha256(b).hexdigest()
def pin(p):
 b=p.read_bytes();return dict(SHA256=h(b),bytes=len(b))
m=j(P/'FILE_MANIFEST.json')['files'];mapping=j(P/'ORIGINAL_COPY_MAPPING.json');rows=mapping['files']
receipt=j(P/'traditional_D_full2022_20261015_v2/IMPLEMENTATION_RECEIPT.json');identity=receipt['code_identity']
assert len(identity)==64 and receipt['code_identity_SHA256']=='fbe6fb7dd93733931ee58c3fc3ed3061c2c754e18cb72065722901d54a7bfd9d'
assert h(json.dumps(identity,sort_keys=True,separators=(',',':')).encode())==receipt['code_identity_SHA256']
expected=set(identity)
expected.update('traditional_three_tier_freeze_20261015/'+s for s in ('test_frozen_grid.py','test_native_runtime.py'))
for folder in ('traditional_D_full2022_independent_review_20261015','traditional_D_full2022_prepared_source_independent_review_20261015'):
 expected.update(p.relative_to(WORK).as_posix() for p in (WORK/folder).iterdir() if p.is_file() and p.name!='PUBLIC_SAFE_EXACT_EVIDENCE_ALLOWLIST.json')
expected.update('traditional_D_full2022_20261015_v2/'+s for s in ('DELIVERABLE_PINS.json','IMPLEMENTATION_RECEIPT.json','GENERATED_TESTS.log','ROOT_GO_TEMPLATE_UNAPPROVED.json','SOURCE_PREP_AUTHORIZATION_TEMPLATE_UNAPPROVED.json','REMAINING_QUALIFICATION_LEDGER.json','README.md'))
expected.update('traditional_D_full2022_source_stage_handoff_20261015/'+s for s in ('source_stage_guard.py','test_source_stage_guard.py','OBSERVED_SOURCE_ONLY_GUARD_RECEIPT_attempt001.json','GUARD_GENERATED_TESTS.log'))
expected.update('traditional_D_full2022_supplementary_pure_tests_20261015/'+s for s in ('PURE_TESTS.log','test_pure_reporting_portability.py'))
expected.update('full2022_unaffected_source_restore_20261015/'+s for s in ('FINAL_RAW_SOURCE_INDEX.json','FINAL_SOURCE_QUALIFICATION_RECEIPT.json','FINAL_DELIVERABLE_PINS.json'))
expected.update('full2022_restored_source_independent_review_20261015/'+s for s in ('REVIEW_RECEIPT.json','REPORT.md','DAILY_FUNDING_METADATA_REVIEW.json','JULY_DAILY_CONFIRMATION_PROVENANCE_REVIEW.json'))
expected.update('full2022_source_metadata_plan_20261015/'+s for s in ('FULL2022_MONTHLY_SOURCE_CATALOGUE.json','FULL2022_DISTINCT_ALLOWED_RETRIEVAL_PROPOSAL.json','LOCAL_INPUT_PROJECTION_RECEIPT.json'))
expected.add('source_network_readonly_diagnosis_20261015/eth_feb_original_route_followthrough/FROZEN_ALLOWLIST.json')
projections={
'full2022_source_metadata_plan_20261015/source_only_projections/DAILY_CLOSE_SOURCE_ONLY.npz':dict(SHA256='ae81b8c2ec4f40d889ae82757bdd72f5b4c04afadd72467366e1f10371801887',bytes=16950),
'full2022_source_metadata_plan_20261015/source_only_projections/RAW_RATE_INTERVAL_EVENTS.json':dict(SHA256='4a6d644c0339facf4cc4e8607fc1379acb06c1f52c162af6cab739b4670b7c99',bytes=724500)}
expected.update(projections)
assert len(expected)==124 and expected=={r['packet_path'] for r in rows} and len(rows)==124
assert mapping['frozen_code_identity_files']==64 and mapping['fixture_modules']==2 and mapping['all_original_source_files_unchanged'] is True
for row in rows:
 name=row['packet_path'];assert row['original_workspace_relative_path']==name and row['copy_method']=='EXACT_BYTES_UNMODIFIED'
 assert pin(WORK/name)==pin(P/name)=={'SHA256':row['SHA256'],'bytes':row['bytes']}==m[name]
 if name in identity:assert row['SHA256']==identity[name]
for name,v in projections.items():assert pin(P/name)==v
support={'COLD_FAILED_ATTEMPT001_RECEIPT.json','COLD_FAILED_ATTEMPT001_SUMMARY.json','COLD_TEST.log','COLD_TEST_RECEIPT.json','EXTERNAL_RAW_SOURCE_DEPENDENCIES.json','GENERATED_FAILURE_DIAGNOSIS.json','OMISSIONS_AND_HASH_ONLY_EVIDENCE.json','ORIGINAL_COPY_MAPPING.json','PRIVACY_PORTABILITY_AUDIT.json','README.md','RECOVERY_LIMITATIONS.json','RUNTIME_AND_EVIDENCE_BOUNDARY.json','requirements.txt','verify_recovery.py'}
assert set(m)==expected|support and len(m)==138
assert {p.relative_to(P).as_posix() for p in P.rglob('*') if p.is_file()}==set(m)|{'FILE_MANIFEST.json'}
assert not any(p.is_symlink() for p in P.rglob('*'))
primary={
 'traditional_D_full2022_independent_review_20261015/INDEPENDENT_REVIEW_RECEIPT.json':'1d8d94eb352891ad9154412f48291dd734fc996289ed13e37f629c7115c0e09e',
 'traditional_D_full2022_prepared_source_independent_review_20261015/INDEPENDENT_REVIEW_RECEIPT.json':'6fe46f96a5cac8d1c8f0830448eaa1d964fc35cf882ef92ccde7817cdd47644d',
 'full2022_restored_source_independent_review_20261015/REVIEW_RECEIPT.json':'5a934063b763bd54f986a8ad8e8bb3222c737180ca03f5cafbccd4b51b521429',
 'traditional_D_full2022_source_stage_handoff_20261015/source_stage_guard.py':'868c1094cc48c45e45875d52c6e7fe7a56727c0b35971ec5ad86930b4bf91bb8'}
for name,digest in primary.items():assert m[name]['SHA256']==digest
omissions=j(P/'OMISSIONS_AND_HASH_ONLY_EVIDENCE.json');omit=omissions['files']
for row in omit:assert not (P/row['path']).exists() and row['path'] not in m
pure=next(r for r in omit if r['path'].endswith('/PURE_TEST_RECEIPT.json'))
assert pure['SHA256']=='47e8d6ea6fc857861bcdd46b27d7434d87b8e890d3bbd2f2b706a497b64a9c9a' and pure['bytes']==49039
assert 'PURE_TESTS.log' in {Path(n).name for n in m} and 'test_pure_reporting_portability.py' in {Path(n).name for n in m}
for key in ('new_source_stage_GO_required','new_source_preparation_required','new_independent_numerical_equivalence_required','new_financial_GO_required'):assert omissions[key] is True
assert omissions['full_cold_original_financial_replay_supported'] is False and omissions['snapshot_restart_supported'] is False
index=j(P/'full2022_unaffected_source_restore_20261015/FINAL_RAW_SOURCE_INDEX.json');assert len(index['monthly'])==120 and len(index['daily'])==16
external=j(P/'EXTERNAL_RAW_SOURCE_DEPENDENCIES.json');assert len(external['files'])==136 and external['raw_original_ZIP_bytes']==159122632
by_path={row['source_path']:row for row in external['files']}
for r in index['monthly']+index['daily']:
 row=by_path[r['source_path']]
 for key in ('ZIP_SHA256','ZIP_bytes','CHECKSUM_path','CHECKSUM_SHA256','CHECKSUM_bytes'):assert row[key]==r[key]
 assert not row['runtime_body_included'] and row['official_original_URL'].startswith('https://data.binance.vision/')
 assert not (P/r['source_path']).exists() and not (P/r['CHECKSUM_path']).exists()
cat=j(P/'full2022_source_metadata_plan_20261015/FULL2022_MONTHLY_SOURCE_CATALOGUE.json');monthly={(r['family'],r['symbol'],r['month']):r for r in cat['rows']}
prop=j(P/'full2022_source_metadata_plan_20261015/FULL2022_DISTINCT_ALLOWED_RETRIEVAL_PROPOSAL.json');proposed={r['SHA256']:r for r in prop['objects']}
for r in index['monthly']:assert by_path[r['source_path']]['official_original_URL']==monthly[(r['family'],r['symbol'],r['period'])]['official_original_URL']
for r in index['daily']:assert by_path[r['source_path']]['official_original_URL']==proposed[r['ZIP_SHA256']]['url']
assert {name for name in m if Path(name).suffix.lower() in ('.npz','.npy','.zip','.parquet','.bin','.pickle','.pkl','.pt','.pth','.safetensors')}=={next(name for name in projections if name.endswith('.npz'))}
assert not any(Path(n).name in ('PREPARATION.json','TARGETS.npz','TARGET_PROOFS.json','SOURCE_PREP_GO.json','ROOT_SOURCE_STAGE_GO_APPROVED_attempt001.json','ACCOUNT_FINANCIAL_AUDIT.json','MINUTE.npz','LAUNCH_CLAIM.json','PROCESS_OWNERSHIP.json') for n in m)
anchor=j(P/'traditional_D_full2022_prepared_source_independent_review_20261015/ACTUAL27_ANCHOR_RECOVERY_REVIEW.json');assert len(anchor['cells'])==27 and anchor['publication_arrival_installation']=='UNKNOWN_NOT_CERTIFIED' and anchor['actual_account_or_installed_recovery_claim'] is False
transport=j(P/'traditional_D_full2022_prepared_source_independent_review_20261015/NATIVE_TRANSPORT_PROOF_SCOPE.json');assert transport['normalized_monthly_containers_persisted'] is False and transport['independent_saved_all_month_all_value_comparison'] is False and len(transport['normalized_months'])==12
prep_review=j(P/'traditional_D_full2022_prepared_source_independent_review_20261015/INDEPENDENT_REVIEW_RECEIPT.json');assert prep_review['old_private_GO_bodies_required'] is False and prep_review['historical_execution_authorized'] is False and prep_review['actual_2022_financial_runs']==0
failed=j(P/'COLD_FAILED_ATTEMPT001_SUMMARY.json');assert failed['status']=='FAIL_PRESERVED_NOT_RELABELED'
assert pin(WORK/'full2022_source_generated_packaging_20261015_v1/cold_attempt001/COLD_TEST_RECEIPT.json')==failed['original_receipt']==pin(P/'COLD_FAILED_ATTEMPT001_RECEIPT.json')
assert pin(WORK/'full2022_source_generated_packaging_20261015_v1/cold_attempt001/COLD_TEST.log')==failed['original_log']
assert failed['initial_attempt_distinct_tests_passed']==101-3-2-1==95 and failed['reported_original_tests_passed_93_is_subtest_arithmetic_not_distinct_case_count'] is True
patterns={'private_workspace_prefix':('/'+'workspace'+'/').encode(),'private_agent_home':('/'+'home'+'/'+'agent'+'/').encode(),'RSA_private_key':b'BEGIN RSA PRIVATE KEY','private_key':b'BEGIN PRIVATE KEY','github_token':b'github_pat_','github_classic_token':b'ghp_','stripe_live_key':b'sk_live_','openai_project_key':b'sk-proj-'}
privacy=[]
for name in sorted(m):
 raw=(P/name).read_bytes()
 for label,pattern in patterns.items():
  if pattern in raw:privacy.append({'file':name,'pattern':label})
assert not privacy,privacy
# The exact public upstream operational defaults and obvious fake negative-test
# paths are retained as source, never asserted to be current/private paths.
public_default='traditional_three_tier_freeze_20261015/sources/reference/joint_expert_information.py'
assert m[public_default]['SHA256']==identity[public_default]
report=dict(schema='INDEPENDENT_EXACT_SOURCE_GENERATED_PACKET_STATIC_REVIEW_V1',status='PASS_EXACT_PACKET_STATIC_CHECKS',frozen_identity_files=64,exact_original_copy_files=124,fixture_modules=2,support_files=14,manifest_entries=138,total_files=139,all_manifest_pins_and_original_copy_bytes_exact=True,primary_receipts=primary,exact_source_projection_pins=projections,source_projections_decoded=False,external_raw_ZIPs=136,external_raw_ZIP_bytes=159122632,external_raw_URLs_match_original_pinned_catalogues=True,supplementary_receipt_omitted_hash_only=pure,exact_pure_test_and_log_not_substituted_for_omitted_receipt=True,raw_arrays_targets_financial_outputs_models_holdouts_or_valid_GO_bodies_included=False,private_prefix_or_secret_signature_matches=privacy,privacy_limit='Exact allowlist and static signatures do not prove absence of every conceivable secret.',normalized_month_arrays_memory_only_and_not_all_value_reread=True,source27_remains_UNKNOWN_NOT_CERTIFIED_actual_arrival=True,actual_financial_results_or_liquidation_certification_claimed=False,old_private_GO_bodies_runtime_required=False,recovery_requires_fresh_source_GO_preparation_equivalence_review_and_financial_GO=True,full_cold_history_or_snapshot_restart_claimed=False,earlier_failed_attempt_preserved=True,earlier_distinct_tests_passed=95,earlier_receipt_reported_93_is_not_distinct_case_count=True,upstream_public_path_defaults_and_obvious_generated_negative_test_paths_retained_exact=True,actual_source_normalization_accounts_financial_runs_GO_claims_or_publication=0,full_manifest=m,script_SHA256=pin(Path(__file__))['SHA256'])
(HERE/'INDEPENDENT_STATIC_REVIEW.json').write_text(json.dumps(report,sort_keys=True,indent=2)+'\n')
print(json.dumps({key:report[key] for key in ('status','total_files','exact_original_copy_files','frozen_identity_files','fixture_modules','external_raw_ZIPs')}))
