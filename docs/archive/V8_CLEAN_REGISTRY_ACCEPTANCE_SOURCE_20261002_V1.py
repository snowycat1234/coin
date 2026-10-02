"""Verify completed runtime/ledger controls; never grant research qualification."""
import hashlib,json,subprocess,sys
import xml.etree.ElementTree as ET
from datetime import UTC,datetime
from pathlib import Path
root=Path('/mnt/d/codex/coin');state=Path('/home/xflops/coin-state')
sys.path.insert(0,str(root))
from scripts.research_v8.registry import FIELDS,append_event,read_verified
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip()
copies={
 state/'v8-labels-v2-failed-attempt-source-20261002-v1.py':'docs/archive/V8_LABEL_V2_FAILED_SOURCE_20261002_V1.py',
 state/'v8-labels-v2-failed-attempt-tests-20261002-v1.py':'docs/archive/V8_LABEL_V2_FAILED_TEST_SOURCE_20261002_V1.py',
 state/'test-v8-label-contract-v2-20261002-v1.xml':'reports/fast_research/V8_LABEL_V2_INITIAL_FAILURE_20261002_V1.xml',
 state/'test-v8-label-contract-v2-20261002-v2.xml':'reports/fast_research/V8_LABEL_V2_SYNTHETIC_RETEST_20261002_V2.xml',
 state/'test-v8-adversarial-20261002-v1/probe.py':'docs/archive/V8_LABEL_ADVERSARIAL_PROBE_20261002_V1.py',
 state/'test-v8-adversarial-20261002-v2/probe.py':'docs/archive/V8_LABEL_ADVERSARIAL_PROBE_20261002_V2.py',
 Path(__file__):'docs/archive/V8_CLEAN_REGISTRY_ACCEPTANCE_SOURCE_20261002_V1.py',
 root/'.cache/v8_feature_test_start_20261002_v1.py':'docs/archive/V8_FIXED_FEATURE_START_SOURCE_20261002_V1.py',
 root/'.cache/v8_feature_v2_start_20261002_v1.py':'docs/archive/V8_FIXED_FEATURE_START_SOURCE_20261002_V2.py',
}
archived={}
for src,destination in copies.items():
 dest=root/destination;payload=src.read_bytes()
 if dest.exists():assert dest.read_bytes()==payload
 else:
  with dest.open('xb') as f:f.write(payload)
 archived[destination]=sha(dest)
def task(title):
 found=[json.loads(p.read_text()) for p in (state/'task-progress').glob('task-*.json')]
 found=[x for x in found if x['title']==title]
 assert len(found)==1 and found[0]['status']=='completed' and found[0]['exit_code']==0
 return found[0]
def counts(path):
 suites=list(ET.parse(root/path).iter('testsuite'))
 result={field:sum(int(s.attrib.get(field,0)) for s in suites) for field in ('tests','errors','failures','skipped')}
 assert result['failures']==result['errors']==result['skipped']==0
 return result
ci='reports/fast_research/V8_CLEAN_CI_20261002_V1.xml'
ci_task=task('V8 独立clean CI · 因果/分割/注册不变量')
ci_sources=['scripts/research_v8/check_clean.sh','scripts/research_v8/registry.py','tests/test_v8_experiment_registry.py',
 'scripts/research_v8/labels.py','scripts/research_v8/labels_v2.py','tests/test_v8_label_contract.py','tests/test_v8_label_contract_v2.py']
ci_receipt=dict(status='PASS_ACTUAL_CLEAN_CI_EXECUTION_NOT_CAUSAL_ACCEPTANCE',created_utc=datetime.now(UTC).isoformat(),
 git_commit=head,data_hash=sha(root/'tests/test_v8_label_contract_v2.py'),data_hash_scope='invented fixture source bytes',
 protocol_hash=sha(root/'protocols/LABEL_CONTRACT_V8.json'),environment_hash=sha(root/'environments/v8/uv.lock'),seed=None,
 exact_command="bash scripts/with_task_progress.sh --title 'V8 独立clean CI · 因果/分割/注册不变量' -- bash scripts/research_v8/check_clean.sh /home/xflops/coin-state/v8-clean-env-20261002-v2 /home/xflops/coin-state/test-v8-clean-ci-20261002-v1 reports/fast_research/V8_CLEAN_CI_20261002_V1.xml",
 source_hashes={p:sha(root/p) for p in ci_sources},junit_path=ci,junit_sha256=sha(root/ci),junit_counts=counts(ci),actual_task=ci_task,
 market_models_fit=0,locked_consumed=False,orders_sent=0,P1_passed=False,
 limitations=['Unit execution is accepted; independent V2 audit found a new synthetic forbidden-date receipt path.',
 'Labels V1/V2 remain rejected; no V8 market fit until new-version independent acceptance.',
 'Missing-fee/impossible-fill and complete V8 end-to-end research integration are still pending.'])
assert ci_receipt['junit_counts']['tests']==42
with (root/'reports/fast_research/V8_CLEAN_CI_EXECUTION_RECEIPT_20261002_V1.json').open('x') as f:json.dump(ci_receipt,f,indent=2);f.write('\n')
for version,total,title in [('V1',9,'V8 固定共同特征合成因果验收'),('V2',12,'V8 共同特征输入契约修正版验收')]:
 start_path=f'reports/fast_research/V8_FIXED_FEATURE_START_20261002_{version}.json'
 start=json.loads((root/start_path).read_text())
 for p,h in start['source_hashes'].items():assert sha(root/p)==h
 xml=f'reports/fast_research/V8_FIXED_FEATURE_TESTS_20261002_{version}.xml'
 result=dict(status='PASS_FIXED_FEATURE_SYNTHETIC_CHECKS_PENDING_INDEPENDENT_AUDIT',created_utc=datetime.now(UTC).isoformat(),
  git_commit=head,data_hash=start['data_manifest_hash'],protocol_hash=start['protocol_hash'],environment_hash=start['environment_hash'],seed=None,
  exact_command=start['exact_command'],source_hashes=start['source_hashes'],start_receipt_sha256=sha(root/start_path),
  junit_path=xml,junit_sha256=sha(root/xml),junit_counts=counts(xml),actual_task=task(title),feature_count=478,
  market_models_fit=0,locked_consumed=False,orders_sent=0,P1_passed=False)
 assert result['junit_counts']['tests']==total
 with (root/f'reports/fast_research/V8_FIXED_FEATURE_CHECK_RECEIPT_20261002_{version}.json').open('x') as f:json.dump(result,f,indent=2);f.write('\n')
ledger=root/'reports/experiment_registry.jsonl';payload=ledger.read_bytes();rows=read_verified(payload)
prior=json.loads((root/'reports/fast_research/V8_EXPERIMENT_REGISTRY_BACKFILL_20261002_V2.json').read_text())
assert hashlib.sha256(payload[:prior['registry_prefix_bytes_at_acceptance']]).hexdigest()==prior['registry_sha256_at_acceptance']
assert sha(root/'docs/archive/V8_REGISTRY_BEFORE_DEPTH_GUARD_20261002_V1.py')==prior['source_hashes']['scripts/research_v8/registry.py']
assert len({x['event_id'] for x in rows})==len(rows)
smoke_path='reports/fast_research/V8_CLEAN_ENVIRONMENT_SMOKE_20261002_V2.json'
smoke=json.loads((root/smoke_path).read_text())
for p,h in smoke['source_hashes'].items():assert sha(root/p)==h
assert smoke['reproduction_exact_prediction_bytes_equal'] and not smoke['overlay_site_paths'] and not smoke['external_pth_links']
sources=['scripts/research_v8/registry.py','scripts/research_v8/backfill_registry.py','scripts/research_v8/register_operation_results.py',
 'scripts/research_v8/__init__.py','tests/test_v8_experiment_registry.py','environments/v8/uv.lock','environments/v8/pyproject.toml','scripts/research_v8/clean_environment_smoke.py']
prior_reports=[smoke_path,'reports/fast_research/V8_EXPERIMENT_REGISTRY_BACKFILL_20261002_V2.json',
 'reports/fast_research/V8_CLEAN_CI_EXECUTION_RECEIPT_20261002_V1.json','reports/fast_research/V8_LABEL_ADVERSARIAL_AUDIT_20261002_V1.json',
 'reports/fast_research/V8_LABEL_ADVERSARIAL_AUDIT_20261002_V2.json','reports/fast_research/V8_REGISTRY_BACKFILL_FAILURE_20261002_V1.json',
 'reports/fast_research/V8_CLEAN_ENVIRONMENT_INSTALL_FAILURE_20261002_V1.json']
receipt=dict(status='ROOT_PASS_COMPLETE_CPU_RUNTIME_AND_APPEND_ONLY_LEDGER_CONTROLS_ONLY',created_utc=datetime.now(UTC).isoformat(),
 git_commit=head,data_hash=smoke['artifacts']['inputs.npy'],protocol_hash=sha(root/'protocols/LABEL_CONTRACT_V8.json'),
 environment_hash=sha(root/'environments/v8/uv.lock'),seed=smoke['seed'],
 exact_command='bash scripts/bounded.sh /home/xflops/coin-state/v8-clean-env-20261002-v2/bin/python .cache/v8_clean_registry_acceptance_20261002_v1.py',
 source_hashes={p:sha(root/p) for p in sources},verified_prior_files={p:sha(root/p) for p in prior_reports}|archived,
 complete_lock_packages=smoke['complete_lock_package_count'],clean_imports_and_artifact_reproduction=True,
 registry_records=len(rows),registry_prefix_bytes_at_acceptance=len(payload),registry_prefix_sha256_at_acceptance=sha(ledger),
 original_621_record_prefix_unchanged=True,trial_count_complete=False,statistical_correction_eligible=False,
 candidate='NONE',candidate_status='NO_QUALIFIED_CANDIDATE',P1_gate='NOT_READY',full_P7_gate='NOT_READY',
 DSR=None,PBO_CSCV=None,Hansen_SPA=None,block_bootstrap=None,market_models_fit=0,locked_consumed=False,orders_sent=0,
 limitations=['Artifact inventory is not full reconstructed trial history. Unknown metadata is not zero.',
 'Runtime/ledger capability acceptance does not accept labels, economics, full mutation gate, or any market strategy.',
 'Registry acceptance binds a verified prefix; later append-only events are allowed and require separate receipts.'])
with (root/'reports/fast_research/V8_RUNTIME_REGISTRY_MODULE_ACCEPTANCE_20261002_V1.json').open('x') as f:json.dump(receipt,f,indent=2);f.write('\n')
print(json.dumps({k:receipt[k] for k in ['status','registry_records','P1_gate','full_P7_gate']}))
