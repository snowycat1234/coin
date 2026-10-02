import hashlib,json,subprocess,sys
from pathlib import Path
root=Path('/mnt/d/codex/coin');sys.path.insert(0,str(root))
from scripts.research_v8.registry import append_event
sha=lambda p:hashlib.sha256((root/p).read_bytes()).hexdigest()
contract=json.loads((root/'protocols/FEATURE_V8_ACTIVE_IMPLEMENTATION_V3.json').read_text())
contract.update(version='FEATURE_V8_ACTIVE_IMPLEMENTATION_V4_20261002',active_adapter='scripts/research_v8/features_v4.py',
 active_adapter_sha256=sha('scripts/research_v8/features_v4.py'),previous_active_contract_sha256=sha('protocols/FEATURE_V8_ACTIVE_IMPLEMENTATION_V3.json'),
 input_empty_masks='Known Boolean empty_bin must equal trade_count==0; integral nonnegative trade/aggregate counts agree; empty bins have zero volume, notional and interarrival count. Original definitions and legitimate missing-observation masks preserved.')
with (root/'protocols/FEATURE_V8_ACTIVE_IMPLEMENTATION_V4.json').open('x') as f:json.dump(contract,f,indent=2);f.write('\n')
event=json.loads((root/'reports/fast_research/V8_FIXED_FEATURE_START_20261002_V3.json').read_text())
for field in ['created_utc','previous_record_sha256','record_sha256']:event.pop(field,None)
event.update(experiment_id='v8-fixed-features-truthful-empty-guard-20261002-v4',event_id='v8-fixed-features-truthful-empty-guard-20261002-v4:START',
 git_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip(),protocol_hash=sha('protocols/FEATURE_V8_ACTIVE_IMPLEMENTATION_V4.json'),
 reason_for_next_experiment='Reject independently demonstrated false empty mask and integer-to-Boolean corruption before original feature computation',
 exact_command="bash scripts/with_task_progress.sh --title 'V8 共同特征空成交状态反例修复验收' -- /home/xflops/coin-state/v8-clean-env-20261002-v2/bin/python -m pytest tests/test_v8_features_v3.py tests/test_v8_features_v4.py -q --basetemp=/home/xflops/coin-state/test-v8-fixed-features-20261002-v4 -o cache_dir=/home/xflops/coin-state/test-v8-fixed-features-20261002-v4-cache --junitxml=reports/fast_research/V8_FIXED_FEATURE_TESTS_20261002_V4.xml")
event['source_hashes'].update({p:sha(p) for p in ['scripts/research_v8/features_v4.py','tests/test_v8_features_v4.py']})
record=append_event(root/'reports/experiment_registry.jsonl',event)
with (root/'reports/fast_research/V8_FIXED_FEATURE_START_20261002_V4.json').open('x') as f:json.dump(record,f,indent=2);f.write('\n')
print(json.dumps({'status':record['success_failure'],'record_sha256':record['record_sha256']}))
