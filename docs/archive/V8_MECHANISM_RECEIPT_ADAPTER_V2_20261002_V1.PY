import hashlib,json,sys
from datetime import UTC,datetime
from pathlib import Path
root=Path('/mnt/d/codex/coin');sys.path.insert(0,str(root))
from scripts.research_v8.registry import FIELDS,append_event
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
old=root/'scripts/research_v8/nonoverlap_mechanism.py'
assert sha(old)=='40da2cde8a73904f1705b9418842396ba21bd3a723cff438a86be3b7a8d73e53'
failure=dict(status='REJECTED_PRE_START_AUDIT_RECEIPT_SCHEMA',created_utc=datetime.now(UTC).isoformat(),
 actual_unified_session_id=51503,actual_exit_code=1,
 exact_command="bash scripts/with_task_progress.sh --title 'V8 非重叠机制四fold诊断' -- /home/xflops/coin-state/v8-clean-env-20261002-v2/bin/python scripts/research_v8/nonoverlap_mechanism.py --label-audit reports/fast_research/V8_LABEL_ADVERSARIAL_AUDIT_20261002_V5_R2.json --output reports/fast_research/V8_NONOVERLAP_MECHANISM_20261002_V1.json --state-directory /home/xflops/coin-state/v8-nonoverlap-mechanism-20261002-v1",
 source_hashes={'scripts/research_v8/nonoverlap_mechanism.py':sha(old),
 'protocols/NONOVERLAP_MECHANISM_V8_V1.json':sha(root/'protocols/NONOVERLAP_MECHANISM_V8_V1.json')},
 exception='ValueError: Auditor did not bind the active label source',
 reason='Accepted R2 auditor uses verified_source_hashes, not sources_sha256. Gate correctly rejected missing field before FORMAL_START or market IO.',
 market_data_read=False,market_models_fit=0,locked_consumed=False,orders_sent=0)
fp=root/'reports/fast_research/V8_NONOVERLAP_PRESTART_FAILURE_20261002_V1.json'
with fp.open('x') as f:json.dump(failure,f,indent=2);f.write('\n')
text=old.read_text()
assert text.count("audit.get('sources_sha256',{})")==1
text=text.replace("audit.get('sources_sha256',{})","audit.get('verified_source_hashes',{})")
text=text.replace('NONOVERLAP_MECHANISM_V8_V1.json','NONOVERLAP_MECHANISM_V8_V2.json')
text=text.replace('scripts/research_v8/nonoverlap_mechanism.py','scripts/research_v8/nonoverlap_mechanism_v2.py')
text=text.replace('v8-nonoverlap-mechanism-20261002-v1','v8-nonoverlap-mechanism-20261002-v2')
new=root/'scripts/research_v8/nonoverlap_mechanism_v2.py'
with new.open('x') as f:f.write(text)
protocol=json.loads((root/'protocols/NONOVERLAP_MECHANISM_V8_V1.json').read_text())
protocol.update(version='V8_NONOVERLAP_MECHANISM_20261002_V2',
 previous_protocol_sha256=sha(root/'protocols/NONOVERLAP_MECHANISM_V8_V1.json'),
 audit_source_binding_field='verified_source_hashes',
 implementation='scripts/research_v8/nonoverlap_mechanism_v2.py',
 implementation_change='Only independent-audit receipt key and version/path bindings change; all windows/folds/metrics/thresholds are identical.')
np=root/'protocols/NONOVERLAP_MECHANISM_V8_V2.json'
with np.open('x') as f:json.dump(protocol,f,indent=2);f.write('\n')
audit=json.loads((root/'reports/fast_research/V8_LABEL_ADVERSARIAL_AUDIT_20261002_V5_R2.json').read_text())
assert audit['status']=='PASS_CONTRACT_IMPLEMENTATION'
for name,digest in audit['verified_source_hashes'].items():assert sha(root/name)==digest
assert audit['verified_source_hashes'][protocol['label_adapter']]==sha(root/protocol['label_adapter'])
event=dict.fromkeys(FIELDS)
event.update(event_id='v8-mechanism-prestart-failure-20261002-v1:RESULT',event_type='OPERATIONAL_RESULT',
 experiment_id='v8-mechanism-prestart-failure-20261002-v1',git_commit=audit['actual_HEAD_at_probe_start'],
 data_manifest_hash=sha(fp),protocol_hash=failure['source_hashes']['protocols/NONOVERLAP_MECHANISM_V8_V1.json'],
 feature_set='NO_MARKET_INPUT',labels=protocol['variants'],model_family='NONE',hyperparameters={},seed='NOT_APPLICABLE',
 thresholds='UNCHANGED',cost_assumptions='NOT_EVALUATED',all_folds=protocol['all_fold_ids'],success_failure=failure['status'],
 reason_for_next_experiment='Adapt exact receipt schema while preserving failed source/protocol and scientific design.',
 result_influenced_later_choice=True,artifact_path=str(fp.relative_to(root)),artifact_sha256=sha(fp),source_hashes=failure['source_hashes'])
append_event(root/'reports/experiment_registry.jsonl',event)
print(json.dumps(dict(status='EXACT_AUDITED_SOURCE_FIELD_VERIFIED',new_source_sha256=sha(new),new_protocol_sha256=sha(np))))
