"""Seal already closed conditional-account acceptance; no financial replay."""
from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path
from scripts.research_v8.registry import FIELDS, append_event
ROOT=Path('/mnt/d/codex/coin');sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
ARCHIVE='docs/archive/CONDITIONAL_CARRY_CLOSED_ACCEPTANCE_SOURCE_20261003_V1.py'
assert Path(__file__).read_bytes()==(ROOT/ARCHIVE).read_bytes()
name='reports/fast_research/CONDITIONAL_CARRY_ROOT_ACCEPTANCE_20261003_V1.json'
assert sha(ROOT/name)=='42c499ea7f362da2518fa22ebadb6146f1a180b5cd5bc42faaa0b0a348fa3b83'
v=json.loads((ROOT/name).read_bytes());identity=v['root_task_id']
path=Path('/home/xflops/coin-state/task-progress')/('task-'+identity+'.json');task=json.loads(path.read_bytes())
assert identity=='79e5521f9e1843799d8be986c2cdac76' and task['status']=='completed' and task['exit_code']==0
hashes={**v['source_hashes'],name:sha(ROOT/name),ARCHIVE:sha(ROOT/ARCHIVE)}
for relative,digest in hashes.items():assert sha(ROOT/relative)==digest
actual=dict(path=str(path),sha256=sha(path),task=task,host_result='chunk:a0d87a',actual_exit=0)
event=dict.fromkeys(FIELDS)
event.update(experiment_id='CONDITIONAL-CARRY-ROOT-ACCEPTANCE-20261003-V1',event_id='CONDITIONAL-CARRY-ROOT-ACCEPTANCE-20261003-V1:RESULT',
    event_type='IMPORTED_OPERATIONAL_RESULT',git_commit=json.loads((ROOT/v['original_receipts'][1]['path']).read_bytes())['binding']['git_commit'],
    data_manifest_hash=hashes['reports/fast_research/BASIS_RISK_SOURCE_OPTIONS_20261003_V1.json'],
    protocol_hash=hashes['protocols/CONDITIONAL_CARRY_ACCOUNT_122D_20261003_V1.json'],feature_set='METADATA_ONLY',labels='NONE',model_family='NONE',
    hyperparameters='NO_REPLAY',seed='NONE',thresholds='SOURCE_BYTES_AND_ACTUAL_EXIT',cost_assumptions='UNCHANGED_D029_COSTS',
    all_folds='ONE_CONTINUOUS_FULL122D',success_failure=v['status'],reason_for_next_experiment='D030_SAME_CAP_COST_MATCHED_PAIR_REDUCE',
    result_influenced_later_choice=True,post_completion_registration=True,preregistered_start_record_created=False,
    artifact_path=name,artifact_sha256=sha(ROOT/name),actual_root_task=actual)
append_event(ROOT/'reports/experiment_registry.jsonl',event)
out=ROOT/'reports/GITHUB_CONDITIONAL_CARRY_SOURCE_BINDING_20261003_V1.json'
value=dict(status='PASS_EXACT_CLOSED_CONDITIONAL_CARRY_ACCOUNT_BINDING_NOT_NATIVE_OR_LONG_TERM_APR',created_utc=datetime.now(UTC).isoformat(),
    source_hashes=hashes,actual_root_closure=actual,old_QA_green_tests_or_market_math_repeated=False,
    locked_consumed=False,capital_net_APR='NOT_EVALUABLE',candidate_status='NO_QUALIFIED_CANDIDATE')
with out.open('x') as w:json.dump(value,w,indent=2,ensure_ascii=False);w.write('\n')
print(json.dumps(dict(status=value['status'],sha256=sha(out),source_files=len(hashes))))
