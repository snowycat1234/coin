"""Seal an already closed acceptance; no source QA or market replay."""
from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path
from scripts.research_v8.registry import FIELDS, append_event
ROOT=Path('/mnt/d/codex/coin');sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
ARCHIVE='docs/archive/BASIS_RISK_CLOSED_ACCEPTANCE_SOURCE_20261003_V1.py'
assert Path(__file__).read_bytes()==(ROOT/ARCHIVE).read_bytes()
name='reports/fast_research/BASIS_RISK_ROOT_ACCEPTANCE_20261003_V1.json'
assert sha(ROOT/name)=='cdd28f351f34c46c13e939289bb5545df44a0beb4a5a59de2f10717c617f4110'
v=json.loads((ROOT/name).read_bytes());identity=v['root_task_id']
path=Path('/home/xflops/coin-state/task-progress')/('task-'+identity+'.json');task=json.loads(path.read_bytes())
assert identity=='dbfaa1b56db44e929b979d67e066a6b4' and task['status']=='completed' and task['exit_code']==0
hashes={**v['source_hashes'],name:sha(ROOT/name),ARCHIVE:sha(ROOT/ARCHIVE)}
for relative,digest in hashes.items():assert sha(ROOT/relative)==digest
actual=dict(path=str(path),sha256=sha(path),task=task,host_result='chunk:2daa72',actual_exit=0)
event=dict.fromkeys(FIELDS)
event.update(experiment_id='BASIS-RISK-ROOT-ACCEPTANCE-20261003-V1',event_id='BASIS-RISK-ROOT-ACCEPTANCE-20261003-V1:RESULT',
    event_type='IMPORTED_OPERATIONAL_RESULT',git_commit=json.loads((ROOT/v['original_receipts'][1]['path']).read_bytes())['binding']['git_commit'],
    data_manifest_hash=hashes['reports/fast_research/BASIS_RISK_SOURCE_OPTIONS_20261003_V1.json'],
    protocol_hash=hashes['protocols/BASIS_RISK_DIAGNOSTIC_20261003_V1.json'],feature_set='METADATA_ONLY',labels='NONE',model_family='NONE',
    hyperparameters='NO_REPLAY',seed='NONE',thresholds='SOURCE_BYTES_AND_ACTUAL_EXIT',cost_assumptions='NO_COST_OR_CAPITAL_COMPUTATION',
    all_folds='ALL122D_AND_EACH_MONTH',success_failure=v['status'],reason_for_next_experiment='D029_CONDITIONAL_CARRY_ACCOUNT',
    result_influenced_later_choice=True,post_completion_registration=True,preregistered_start_record_created=False,
    artifact_path=name,artifact_sha256=sha(ROOT/name),actual_root_task=actual)
append_event(ROOT/'reports/experiment_registry.jsonl',event)
out=ROOT/'reports/GITHUB_BASIS_RISK_SOURCE_BINDING_20261003_V1.json'
value=dict(status='PASS_EXACT_CLOSED_BASIS_RISK_MODULE_BINDING_NOT_ACCOUNT_APR',created_utc=datetime.now(UTC).isoformat(),
    source_hashes=hashes,actual_root_closure=actual,old_QA_green_tests_or_market_statistics_repeated=False,
    locked_consumed=False,capital_net_APR='NOT_EVALUABLE',candidate_status='NO_QUALIFIED_CANDIDATE')
with out.open('x') as w:json.dump(value,w,indent=2,ensure_ascii=False);w.write('\n')
print(json.dumps(dict(status=value['status'],sha256=sha(out),source_files=len(hashes))))
