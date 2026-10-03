"""Retrospective auxiliary-task record; reuse append-only registry, no science replay."""
import hashlib,json,os,subprocess
from pathlib import Path
from scripts.research_v8.registry import append_event
root=Path('/mnt/d/codex/coin');state=Path('/home/xflops/coin-state')
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
archive='docs/archive/PUBLIC_DONCHIAN_DAILY_ACCEPTANCE_REGISTRY_SOURCE_20261003_V1.py'
assert os.environ.get('COIN_TASK_ID') and sha(__file__)==sha(root/archive)
path='reports/fast_research/PUBLIC_DONCHIAN_DAILY_ROOT_ACCEPTANCE_20261003_V2.json'
v=json.loads((root/path).read_bytes());assert v['status']=='PASS_ROOT_D037_FIXED_PUBLIC_DAILY_SOURCE_BOUNDARY_THREE_LEDGER_AND_INDEPENDENT_SCOPE_SCREENING_ONLY'
task=state/'task-progress'/('task-'+v['binding']['task_id']+'.json');t=json.loads(task.read_bytes())
assert t['status']=='completed' and t['exit_code']==0
sources={archive:sha(__file__),path:sha(root/path),'scripts/research_v8/registry.py':sha(root/'scripts/research_v8/registry.py')}
event=dict(event_id='D037_ROOT_ACCEPTED_AUXILIARY_TASKS_RETROSPECTIVE_20261003_V1',event_type='RETROSPECTIVE_ACTUAL_MODULE_AUXILIARY_CLOSURE',
 experiment_id='D037_PUBLIC_DAILY_AUXILIARY_CLOSURE_20261003_V1',git_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip(),
 data_manifest_hash=v['binding']['closure_binding_sha256'],protocol_hash=v['binding']['closure_binding_sha256'],
 feature_set='NOT_APPLICABLE_METADATA_CLOSURE',labels='NOT_APPLICABLE',model_family='NONE',hyperparameters=dict(metadata_only=True,market_replayed=False),
 seed='NOT_APPLICABLE',thresholds=dict(candidate_status='NO_QUALIFIED_CANDIDATE',long_term_APR='NOT_EVALUABLE'),
 cost_assumptions=dict(venue='BybitVIP0Spot',fee_bps_per_side=10,spread_bps_RT=8,slippage_bps_per_side=4,nominal_roundtrip_bps=36,received_asset=True),
 all_folds=['CONT547','CONT122','CONT90'],success_failure='ROOT_SCOPE_ACCEPTED_FIXED_STRATEGY_INVESTMENT_PAUSED',
 reason_for_next_experiment='122-day gross loss dominates costs; different fixed public slow-trend state is higher information than Donchian tuning',
 result_influenced_later_choice=True,artifact_path=path,artifact_sha256=sha(root/path),source_hashes=sources,
 actual_root_closed0_task_sha256=sha(task),actual_role_tasks={k:r['actual_closed0_task'] for k,r in v['roles'].items()},
 actual_failed_tasks=v['preserved_initialization_failures'],not_a_pre_run_registration=True,original_scientific_registrations_preserved=True)
record=append_event(root/'reports/experiment_registry.jsonl',event)
print(json.dumps(dict(status='ACTUAL_AUXILIARY_CLOSURE_RECORDED_RETROSPECTIVELY',record_sha256=record['record_sha256'])))
