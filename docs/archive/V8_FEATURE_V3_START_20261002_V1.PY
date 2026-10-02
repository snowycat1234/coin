import hashlib,json,subprocess,sys
from pathlib import Path
root=Path('/mnt/d/codex/coin');sys.path.insert(0,str(root))
from scripts.research_v8.registry import append_event
sha=lambda p:hashlib.sha256((root/p).read_bytes()).hexdigest()
contract=json.loads((root/'protocols/FEATURE_V8_ACTIVE_IMPLEMENTATION_V2.json').read_text())
contract.update(version='FEATURE_V8_ACTIVE_IMPLEMENTATION_V3_20261002',active_adapter='scripts/research_v8/features_v3.py',
 active_adapter_sha256=sha('scripts/research_v8/features_v3.py'),
 previous_active_contract_sha256=sha('protocols/FEATURE_V8_ACTIVE_IMPLEMENTATION_V2.json'),
 input_primitive_masks='Traded prices/sizes/ratios must be finite and physically valid; undefined return/signed-impact and interarrival retain original explicit masks; no-trade bins retain original has_trade mask.')
with (root/'protocols/FEATURE_V8_ACTIVE_IMPLEMENTATION_V3.json').open('x') as f:json.dump(contract,f,indent=2);f.write('\n')
event=json.loads((root/'reports/fast_research/V8_FIXED_FEATURE_START_20261002_V2.json').read_text())
for field in ['created_utc','previous_record_sha256','record_sha256']:event.pop(field,None)
event.update(experiment_id='v8-fixed-features-primitive-guard-20261002-v3',event_id='v8-fixed-features-primitive-guard-20261002-v3:START',
 git_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip(),protocol_hash=sha('protocols/FEATURE_V8_ACTIVE_IMPLEMENTATION_V3.json'),
 reason_for_next_experiment='Reject independently demonstrated unmasked primitive corruption without changing original definitions or legitimate masks',
 exact_command="bash scripts/with_task_progress.sh --title 'V8 共同特征primitive缺失/单位守卫验收' -- /home/xflops/coin-state/v8-clean-env-20261002-v2/bin/python -m pytest tests/test_v8_features.py tests/test_v8_features_v2.py tests/test_v8_features_v3.py -q --basetemp=/home/xflops/coin-state/test-v8-fixed-features-20261002-v3 -o cache_dir=/home/xflops/coin-state/test-v8-fixed-features-20261002-v3-cache --junitxml=reports/fast_research/V8_FIXED_FEATURE_TESTS_20261002_V3.xml")
event['source_hashes'].update({p:sha(p) for p in ['scripts/research_v8/features_v3.py','tests/test_v8_features_v3.py']})
record=append_event(root/'reports/experiment_registry.jsonl',event)
with (root/'reports/fast_research/V8_FIXED_FEATURE_START_20261002_V3.json').open('x') as f:json.dump(record,f,indent=2);f.write('\n')
print(json.dumps({'status':record['success_failure'],'record_sha256':record['record_sha256']}))
