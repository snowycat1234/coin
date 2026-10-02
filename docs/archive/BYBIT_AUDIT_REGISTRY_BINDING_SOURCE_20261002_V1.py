import hashlib, json, sys
from pathlib import Path
root=Path('/mnt/d/codex/coin');sys.path.insert(0,str(root))
from scripts.research_v8.registry import FIELDS,append_event
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
prefix='reports/fast_research/'
name=prefix+'BYBIT_SPOT_NATIVE_FEE_SIX_LEDGER_AUDIT_ACTUAL_EXIT_AND_CODE_BINDING_20261002_V1.json'
assert sha(root/name)=='6dc8e0b05225bdbdefed0d69f267c3fc9fbb19dc283715223cf0791b2de477c2'
r=json.loads((root/name).read_text())
assert r['recovery_task']['status']=='completed' and r['recovery_task']['exit_code']==0
assert r['reused_122_financial_blocks']==r['fresh_90_ledgers']==3 and not r['single_fresh_six_suite']
assert r['preserved_failed_auditor']['actual_task']['exit_code']==1
source_hashes={name:sha(root/name)}
for rel in ['docs/archive/BYBIT_SPOT_NATIVE_FEE_SIX_LEDGER_CHECKER_FAILED_20261002_V1.py',
    'docs/archive/BYBIT_SPOT_NATIVE_FEE_SIX_LEDGER_RECOVERY_20261002_V2.py']:
    digest=sha(root/rel);assert digest in {i['sha256'] for i in r['code_archives']};source_hashes[rel]=digest
source_hashes[r['composite_report_path']]=r['composite_report_sha256']
source_hashes['docs/OPEN_SOURCE_REGISTRY.md']=sha(root/'docs/OPEN_SOURCE_REGISTRY.md')
archive='docs/archive/OPEN_SOURCE_REGISTRY_PRE_BYBIT_HYBRID_20261002.md'
assert sha(root/archive)=='67b1d5e77a7ba0b2d595bac50429522848c0e89053966b1585f344d5770174e0'
source_hashes[archive]=sha(root/archive)
for version,report,task_id,exit_code,scope in [
    ('V1','BYBIT_SPOT_NATIVE_FEE_SIX_LEDGER_INDEPENDENT_AUDIT_20261002_V1.json','1fe751e8ff254795bbb9805a42a3f71e',1,'CONT122_THREE_FINANCIAL_BLOCKS_BEFORE_METADATA_GUARD_FAILURE'),
    ('V2','BYBIT_SPOT_NATIVE_FEE_SIX_LEDGER_COMPOSITE_AUDIT_20261002_V1.json','aa5f64797cd149caac7496461f5e32f4',0,'ONLY_CONT90_THREE_NEW_PLUS_PRIOR_CONT122_PROOFS')]:
    p=root/(prefix+report);value=json.loads(p.read_text());task=Path('/home/xflops/coin-state/task-progress')/('task-'+task_id+'.json')
    tv=json.loads(task.read_text());assert tv['exit_code']==exit_code
    event=dict.fromkeys(FIELDS);identifier='BYBIT-NATIVE-FEE-INDEPENDENT-AUDIT-20261002-'+version
    event.update(experiment_id=identifier,git_commit='d7aaeb4b1ec5e04908c341a8ab6a569ff81bfde1',
        data_manifest_hash=sha(p),protocol_hash=sha(root/'protocols/BYBIT_SPOT_RECEIVED_ASSET_ADAPTER_V1.json'),
        feature_set='EXISTING_LEDGER_ARITHMETIC_ONLY',labels='NONE',model_family='NONE',hyperparameters={'scope':scope,'fits':0},
        seed='NOT_APPLICABLE',thresholds='NO_ECONOMIC_SELECTION_OR_SOURCE_GUARD_RELAXATION',cost_assumptions='UNCHANGED_BYBIT_NONVIP_SPOT10BP',
        all_folds=scope,success_failure=value['status'],reason_for_next_experiment='Validate already-produced accounts without oldgreen or rawQA repetition',
        result_influenced_later_choice=False,source_hashes=source_hashes,artifact_path=str(p.relative_to(root)),artifact_sha256=sha(p),
        actual_task_path=str(task),actual_task_sha256=sha(task),actual_exit_code=exit_code,
        registration_timing='POST_RECORDED_FROM_PRESERVED_PREBOUND_START_NOT_BACKDATED',new_economic_simulator_calls=0)
    append_event(root/'reports/experiment_registry.jsonl',{**event,'event_id':identifier+':START','event_type':'OPERATIONAL_START_POST_RECORDED','success_failure':'PREBOUND_START_PRESERVED'})
    append_event(root/'reports/experiment_registry.jsonl',{**event,'event_id':identifier+':RESULT','event_type':'OPERATIONAL_RESULT'})
out=root/'reports/GITHUB_BYBIT_NATIVE_FEE_AUDIT_EXIT_SOURCE_BINDING_20261002_V1.json'
value=dict(status='PASS_ACTUAL_AUDIT_EXIT_AND_CODE_ARCHIVE_BINDING_NO_NEW_MATH',source_hashes=source_hashes,
    verified_prior_files={prefix+'BYBIT_SPOT_NATIVE_FEE_ROOT_MODULE_ACCEPTANCE_20261002_V1.json':sha(root/(prefix+'BYBIT_SPOT_NATIVE_FEE_ROOT_MODULE_ACCEPTANCE_20261002_V1.json'))},
    original_failed_exit=1,recovery_exit=0,single_fresh_six_suite=False,registry_post_records_added=4,
    no_market_or_test_or_ledger_math_rerun=True,helper_source_sha256=sha(__file__))
with out.open('x') as f:json.dump(value,f,indent=2,ensure_ascii=False);f.write('\n')
for old,target in [('bybit_audit_registry_binding_20261002_v1.py','BYBIT_AUDIT_REGISTRY_BINDING_SOURCE_20261002_V1.py'),
    ('bybit_native_fee_push_verification_20261002_v1.py','BYBIT_NATIVE_FEE_PUSH_VERIFICATION_SOURCE_20261002_V1.py')]:
    with (root/'docs/archive'/target).open('xb') as f:f.write((root/'.cache'/old).read_bytes())
print(json.dumps(dict(status=value['status'],output=str(out),sha256=sha(out))))
