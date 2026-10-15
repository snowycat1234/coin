"""Local corrected financial-V2 source packet, no financial data or valid GO."""
from hashlib import sha256
import json
from pathlib import Path
import shutil
import zipfile

HERE=Path(__file__).resolve().parent;ROOT=HERE.parent
NAME='bounded_native_continuation_financial_v2_code_public_recovery_20261015_v3'
OUT=ROOT/NAME
if OUT.exists():raise ValueError('EXCLUSIVE_NEW_SOURCE_PACKET_DIRECTORY_REQUIRED')
OUT.mkdir()
pins=json.loads((HERE/'EXTERNAL_DEPENDENCY_PINS.json').read_bytes())
for category in ('external_code_files','preserved_evidence_files'):
    for name,row in pins[category].items():
        if '/root_go_2024_' in name:continue
        path=ROOT/name;raw=path.read_bytes()
        if len(raw)!=row['bytes'] or sha256(raw).hexdigest()!=row['SHA256']:raise ValueError('IMMUTABLE_DEPENDENCY_CHANGED:'+name)
        target=OUT/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(raw)
local=['integration.py','run_finite.py','continuation_entry.py','test_integration.py','test_coupled_boundaries.py',
 'test_finite.py','test_quality_equivalence.py','test_zero_request.py','test_continuation_entry.py',
 'profile_generated.py','README_V2.md','ROOT_GO_TEMPLATE_UNAPPROVED_V2.json','EXTERNAL_DEPENDENCY_PINS.json',
 'TEST_LOG_V2_FINAL.txt','PARITY_AND_ZERO_REQUEST_FINAL.txt','GENERATED_RESOURCE_PROFILE.json',
 'SOURCE_GATE_TEST_RECEIPT_V2.json','SOURCE_GATE_TESTS_V2.log',
 'source_only_preparation_attempt001/PREPARATION.json','FROZEN_SOURCE_PRE_GO_MANIFEST_V2.json','build_public_code_v2.py']
for name in local:
    target=OUT/HERE.name/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(HERE/name,target)
review=ROOT/'bounded_native_continuation_v2_independent_review_20261015'
review_files=['INDEPENDENT_NATIVE_CONTINUATION_V2_REVIEW.json','SOURCE_ONLY_FINAL_VERIFICATION.json','SOURCE_ONLY_VERIFICATION_LOG.txt',
 'ALL_AUTHOR_SUITE_FINAL.txt','INDEPENDENT_FINAL.txt','test_prior_invariants.py','test_quality_boundaries_independent.py','verify_source_only.py']
for name in review_files:
    target=OUT/review.name/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(review/name,target)
prior_review=ROOT/'bounded_native_continuation_independent_review_20261015'
for name in ['INDEPENDENT_NATIVE_CONTINUATION_REVIEW.json','V1_CODE_ONLY_LIMITATION_NOTE.txt']:
    target=OUT/prior_review.name/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(prior_review/name,target)
for name in ['test_native_runtime.py','test_frozen_grid.py']:
    shutil.copyfile(ROOT/'traditional_three_tier_freeze_20261015'/name,OUT/'traditional_three_tier_freeze_20261015'/name)
original_author_receipt=(HERE/'SOURCE_ONLY_PREPARATION_RECEIPT_V2.json').read_bytes()
portable_receipt=json.loads(original_author_receipt)
portable_receipt['preparation_directory']='bounded_native_continuation_v2_20261015/source_only_preparation_attempt001'
portable_receipt['public_copy_status']='NON_AUTHORITY_PORTABLE_DERIVATIVE_NOT_ORIGINAL_REVIEW_PINNED_RECEIPT'
portable_receipt['original_review_pinned_receipt_SHA256']=sha256(original_author_receipt).hexdigest()
portable_receipt['changed_field_names']=['preparation_directory']
portable_raw=(json.dumps(portable_receipt,indent=2)+'\n').encode()
(OUT/'SOURCE_ONLY_PREPARATION_PORTABLE_NONAUTHORITY.json').write_bytes(portable_raw)
metadata=dict(schema='CORRECTED_FINANCIAL_V2_PUBLIC_SOURCE_COPY_SCOPE_V1',
 status='SOURCE_GENERATED_INDEPENDENT_PASS_NO_HISTORICAL_PERFORMANCE_CLAIM',
 exact_independent_review_SHA256='e1cf5cc135366b7547ded6c0e2c69bf189d03edf40d2968bf6180c0a54fa1be9',
 original_frozen_execution_or_review_bytes_changed=False,full_cold_historical_replay_claimed=False,
 omitted_original_author_receipt=dict(path='bounded_native_continuation_v2_20261015/SOURCE_ONLY_PREPARATION_RECEIPT_V2.json',
  SHA256=sha256(original_author_receipt).hexdigest(),reason='Executor-specific private launch path omitted. The original is unchanged; its review pin is not satisfied by a portable derivative.',
  portable_derivative='SOURCE_ONLY_PREPARATION_PORTABLE_NONAUTHORITY.json',portable_derivative_SHA256=sha256(portable_raw).hexdigest()),
 omitted_original_dependencies={name:row for name,row in pins['preserved_evidence_files'].items() if '/root_go_2024_' in name},
 omitted_financial_evidence_referenced_by_review=dict(
  path='bounded_native_continuation_independent_review_20261015/V1_DIAGNOSTIC_POLICY_VARIANCE_ADDENDUM.json',
  SHA256='5f146314d84f48a68199d57326c6d0037d7238d2eb06b81d804ae63227854f78',
  reason='Hash-only provenance. Historical financial-result metrics are outside this source-only packet.'),
 omission_rule='Original old-GO hashes and runtime requirements remain unchanged. Consumers require separately authorized original pinned source/target/evidence inputs. No sanitized substitute is accepted as authority.',
 source_data_arrays_included=False,historical_financial_outputs_included=False,credentials_included=False,valid_new_root_GO_included=False,
 upstream_generic_operational_reference=dict(path='traditional_three_tier_freeze_20261015/sources/reference/joint_expert_information.py',
  handling='Exact pinned public upstream bytes retain a generic operational default path. It is not this user private executor location and is not used by the offline binding.'),
 base_public_dependency_commit='cbdc3ccc55ee77f5d1773d2d72962289b59a6849')
(OUT/'PUBLIC_COPY_METADATA.json').write_text(json.dumps(metadata,indent=2)+'\n')
(OUT/'README.txt').write_text('Corrected FINANCIAL POLICY V2, source/generated evidence only.\nV1 remains diagnostic due unintended missing-quality exits; its immutable evidence is preserved.\nThis packet includes exact V2 source, tests, 68-test independent review and source-only preparation metadata.\nNo historical financial outputs, market arrays, credentials or valid root GO are included.\nGenerated-only cold checks from bounded_native_continuation_v2_20261015:\npython -B -m unittest -v test_integration test_coupled_boundaries test_finite test_quality_equivalence test_zero_request\nSource-audit tests additionally require separately restored exact pinned source/target/old-GO inputs.\nRead README_V2.md and PUBLIC_COPY_METADATA.json. Full historical cold replay and venue certification are not claimed.\n')
manifest={str(p.relative_to(OUT)):dict(bytes=p.stat().st_size,SHA256=sha256(p.read_bytes()).hexdigest()) for p in sorted(OUT.rglob('*')) if p.is_file()}
(OUT/'FILES.json').write_text(json.dumps(manifest,indent=2)+'\n')
archive=ROOT/(NAME+'.zip')
with zipfile.ZipFile(archive,'x',zipfile.ZIP_DEFLATED) as z:
    for p in sorted(OUT.rglob('*')):
        if p.is_file():z.write(p,str(p.relative_to(ROOT)))
record=dict(path=archive.name,bytes=archive.stat().st_size,SHA256=sha256(archive.read_bytes()).hexdigest(),members=len(manifest)+1,payload_pins=len(manifest))
(HERE/'PUBLIC_CODE_PACKAGE_V2.json').write_text(json.dumps(record,indent=2)+'\n')
print(json.dumps(record))
