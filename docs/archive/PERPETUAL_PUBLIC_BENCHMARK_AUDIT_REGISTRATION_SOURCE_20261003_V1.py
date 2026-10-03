"""Explicit late metadata registration; never invent pre-run registration."""
import hashlib,json,sys
from pathlib import Path
from scripts.research_v8.registry import FIELDS,append_event
root=Path('/mnt/d/codex/coin');state=Path('/home/xflops/coin-state')
task_path=state/'task-progress/task-5e9cf0e359624004a737680fdffc4d54.json'
task=json.loads(task_path.read_bytes());assert task['id']=='5e9cf0e359624004a737680fdffc4d54'
stage=sys.argv[1];assert stage in ('START','RESULT')
event=dict.fromkeys(FIELDS)
event.update(experiment_id='D041-INDEPENDENT-AUDIT-20261003-V1',event_id=task['id']+':'+stage,
    event_type='LATE_AUDIT_METADATA_'+stage,git_commit='09d6a7a278710a799228148b77a9b661c4b5161a',
    data_manifest_hash='bc89b62aa26681e08fb8793402613788e08c6a60ee411ab0cb7270bc3bd6a330',
    protocol_hash='4a09c87de969fa44e217b8aa4b7cac529be36543abb7bcb39bb5f22b53218f12',
    feature_set='INDEPENDENT_RAW_2H_REFERENCE_AND_ACCEPTED_FINANCIAL_AUDIT',labels='NONE',model_family='NONE',
    hyperparameters={},seed=None,thresholds={'cash_USDT':1e-7,'ratio':1e-10},
    cost_assumptions='UNCHANGED_FIXED_27_43_BP_TWO_UNCONFIRMED_FUNDING_SCALES',
    all_folds=['SEEN_122D','SEEN_90D'],success_failure=task['status'],
    reason_for_next_experiment='Verify eight newly completed accounts; no new strategy selection',
    result_influenced_later_choice=False,task_id=task['id'],actual_started_at=task['started_at'],
    registration_timing='AFTER_ACTUAL_START_NOT_PREDECLARED_REGISTRATION',
    source_hashes={'scripts/investment/audit_perpetual_public_benchmark.py':'4e30e75cc5add4664bd02aa559af1f9ec31c7c2a3fba80ce7a732530dc5c0b91'},
    exact_command=task.get('command','SEE_EXACT_TASK_METADATA'),task_path=str(task_path),
    task_metadata_sha256=hashlib.sha256(task_path.read_bytes()).hexdigest())
if stage=='RESULT':
    assert task['status']=='completed' and task['exit_code']==0
    p=root/'reports/fast_research/PERPETUAL_PUBLIC_BENCHMARK_INDEPENDENT_AUDIT_20261003_V1.json'
    r=json.loads(p.read_bytes());assert r['completed_cases_verified']==8
    event.update(artifact_path=str(p.relative_to(root)),artifact_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),success_failure=r['status'])
print(json.dumps(append_event(root/'reports/experiment_registry.jsonl',event)))
