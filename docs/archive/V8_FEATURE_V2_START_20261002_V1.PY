import hashlib,json,subprocess,sys
from pathlib import Path
root=Path('/mnt/d/codex/coin');sys.path.insert(0,str(root))
from scripts.research_v8.registry import FIELDS,append_event
sha=lambda p:hashlib.sha256((root/p).read_bytes()).hexdigest()
contract=dict(version='FEATURE_V8_ACTIVE_IMPLEMENTATION_V2_20261002',
 definition_contract='protocols/FEATURE_CONTRACT_V8.json',definition_contract_sha256=sha('protocols/FEATURE_CONTRACT_V8.json'),
 active_adapter='scripts/research_v8/features_v2.py',active_adapter_sha256=sha('scripts/research_v8/features_v2.py'),
 preserved_definition_adapter='scripts/research_v8/features.py',preserved_definition_adapter_sha256=sha('scripts/research_v8/features.py'),
 feature_count=478,definitions_changed=False,input_guard='No float/bool decision coercion; known integral input microseconds; observed flow in [-1,1]',
 classification='SCREENING_FEATURE_IMPLEMENTATION_ONLY',candidate='NONE',locked_consumed=False,market_models_fit=0)
dest=root/'protocols/FEATURE_V8_ACTIVE_IMPLEMENTATION_V2.json'
with dest.open('x') as writer:json.dump(contract,writer,indent=2);writer.write('\n')
e=dict.fromkeys(FIELDS)
e.update(experiment_id='v8-fixed-features-active-input-guard-20261002-v2',event_id='v8-fixed-features-active-input-guard-20261002-v2:START',event_type='OPERATIONAL_START',
 git_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip(),data_manifest_hash=sha('tests/test_v8_features.py'),data_manifest_scope='invented fixture bytes; no market data',
 protocol_hash=sha('protocols/FEATURE_V8_ACTIVE_IMPLEMENTATION_V2.json'),feature_set='V8_FIXED_478_COMMON_FEATURES',labels='NONE',model_family='NONE',hyperparameters={},seed=None,
 thresholds='NONE',cost_assumptions='NOT_EVALUATED',all_folds=[],success_failure='RUNNING',reason_for_next_experiment='Preserve original definitions and reject timestamp coercion/invalid physical input before market fitting',result_influenced_later_choice=False,
 environment_hash=sha('environments/v8/uv.lock'),source_hashes={p:sha(p) for p in ['scripts/research_v8/features.py','scripts/research_v8/features_v2.py','tests/test_v8_features.py','tests/test_v8_features_v2.py']},
 exact_command="bash scripts/with_task_progress.sh --title 'V8 共同特征输入契约修正版验收' -- /home/xflops/coin-state/v8-clean-env-20261002-v2/bin/python -m pytest tests/test_v8_features.py tests/test_v8_features_v2.py -q --basetemp=/home/xflops/coin-state/test-v8-fixed-features-20261002-v2 -o cache_dir=/home/xflops/coin-state/test-v8-fixed-features-20261002-v2-cache --junitxml=reports/fast_research/V8_FIXED_FEATURE_TESTS_20261002_V2.xml",locked_consumed=False,market_models_fit=0)
record=append_event(root/'reports/experiment_registry.jsonl',e)
with (root/'reports/fast_research/V8_FIXED_FEATURE_START_20261002_V2.json').open('x') as writer:json.dump(record,writer,indent=2);writer.write('\n')
print(json.dumps({'status':record['success_failure'],'record_sha256':record['record_sha256']}))
