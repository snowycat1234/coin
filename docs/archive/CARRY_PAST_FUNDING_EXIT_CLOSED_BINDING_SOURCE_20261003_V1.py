"""Close D032 actual task/code evidence; metadata only, no financial replay."""
from datetime import UTC, datetime
import hashlib, json, sys
from pathlib import Path
from scripts.research_v8.registry import FIELDS, append_event
ROOT=Path('/mnt/d/codex/coin'); STATE=Path('/home/xflops/coin-state')
ARCHIVE='docs/archive/CARRY_PAST_FUNDING_EXIT_CLOSED_BINDING_SOURCE_20261003_V1.py'
META='docs/archive/CARRY_PAST_FUNDING_EXIT_USED_ACTUAL_METADATA_20261003_V1'
AUDITDIR='docs/archive/CARRY_PAST_FUNDING_EXIT_USED_INDEPENDENT_SOURCES_20261003_V1'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def small(path):
    p=Path(path); assert p.is_file() and not p.is_symlink() and p.stat().st_size<=2_000_000
    return json.loads(p.read_bytes())
def exact(source,relative):
    p=Path(source); assert p.resolve().is_relative_to(STATE) and not p.is_symlink() and p.stat().st_size<=2_000_000
    with (ROOT/relative).open('xb') as stream:stream.write(p.read_bytes())
    assert sha(p)==sha(ROOT/relative)
    return sha(ROOT/relative)
assert Path(__file__).read_bytes()==(ROOT/ARCHIVE).read_bytes()
root_name='reports/fast_research/CARRY_PAST_FUNDING_EXIT_ROOT_ACCEPTANCE_20261003_V1.json'
root=small(ROOT/root_name)
assert root['status']=='PASS_ROOT_D032_TWO_PERIOD_CONDITIONAL_ACCOUNT_AND_COMPARISON_NOT_NATIVE_OR_LONG_TERM_APR'
identity=root['root_task_id']; root_task_path=STATE/'task-progress'/('task-'+identity+'.json'); root_task=small(root_task_path)
assert root_task['id']==identity and root_task['status']=='completed' and root_task['exit_code']==0
protocol='protocols/CARRY_PAST_FUNDING_EXIT_D032_20261003_V1.json'; spec=small(ROOT/protocol)
hashes={**spec['frozen_sources'],protocol:sha(ROOT/protocol),root_name:sha(ROOT/root_name),ARCHIVE:sha(ROOT/ARCHIVE)}
bound=small(ROOT/(AUDITDIR+'/ACTUAL_BINDING.json'))
for name,digest in bound['small_inputs'].items():
    p=Path(name); assert p.is_relative_to(ROOT) and sha(p)==digest
    relative=str(p.relative_to(ROOT)); assert relative not in hashes or hashes[relative]==digest
    hashes[relative]=digest
for p in sorted((ROOT/AUDITDIR).glob('*')):
    assert p.is_file() and p.stat().st_size<=2_000_000 and p.suffix in ('.py','.json')
    hashes[str(p.relative_to(ROOT))]=sha(p)
for name in (
    'protocols/CARRY_PAST_FUNDING_EXIT_COMPARISON_BINDING_20261003_V1.json',
    'scripts/investment/compare_carry_past_funding_exit.py',
    'docs/archive/CARRY_PAST_FUNDING_EXIT_COMPARISON_USED_SOURCE_20261003_V1.py',
    'docs/archive/CARRY_PAST_FUNDING_EXIT_COMPARISON_DRAFT_BEFORE_NUMERIC_GUARD_20261003_V1.py',
    'docs/archive/CARRY_PAST_FUNDING_EXIT_COMPARISON_BINDER_20261003_V1.ps1',
    'docs/archive/CARRY_PAST_FUNDING_EXIT_ROOT_ACCEPTANCE_SOURCE_20261003_V1.py',
    'reports/fast_research/CARRY_PAST_FUNDING_EXIT_PROTOCOL_LAUNCH_FAILURE_20261003_V1.json'):
    hashes[name]=sha(ROOT/name)
receipts=[('TINY','CARRY_PAST_FUNDING_EXIT_TINY_20261003_V1.json'),
    ('122D','CARRY_PAST_FUNDING_EXIT_122D_ACTUAL_20261003_V1.json'),
    ('90D','CARRY_PAST_FUNDING_EXIT_90D_ACTUAL_20261003_V1.json'),
    ('INDEPENDENT','CARRY_PAST_FUNDING_EXIT_TWO_PERIOD_DECIMAL_AUDIT_20261003_V1.json'),
    ('COMPARISON','CARRY_PAST_FUNDING_EXIT_ECONOMIC_COMPARISON_20261003_V1.json')]
(ROOT/META).mkdir(exist_ok=False);tasks=[];operational=[]
for label,base in receipts:
    name='reports/fast_research/'+base;receipt=small(ROOT/name);task_path=STATE/'task-progress'/('task-'+receipt['binding']['task_id']+'.json');task=small(task_path)
    assert task['id']==receipt['binding']['task_id'] and task['status']=='completed' and task['exit_code']==0
    relative=META+'/'+label+'_TASK_ACTUAL.json';hashes[relative]=exact(task_path,relative)
    hashes[name]=sha(ROOT/name);tasks.append(dict(label=label,task_id=task['id'],actual_exit_code=0,archived_task=relative,sha256=hashes[relative]))
    if label in ('TINY','122D','90D'): work=Path(receipt['run_dir'])
    elif label=='INDEPENDENT':work=STATE/'test-d032-past-funding-exit-independent-audit-20261003-v1'
    else:work=None
    if work is not None and (work/'RUN_BINDING.json').exists():
        relative=META+'/'+label+'_RUN_BINDING.json';hashes[relative]=exact(work/'RUN_BINDING.json',relative)
    if label in ('INDEPENDENT','COMPARISON'):operational.append((label,name,receipt,task))
relative=META+'/ROOT_TASK_ACTUAL.json';hashes[relative]=exact(root_task_path,relative)
for label,task_id,exit_code in (
    ('PROTOCOL_LAUNCH_FAILURE','886f1759a5514fc4a58077be25ae654f',1),
    ('PROTOCOL_METADATA_FREEZE','60f70a1fdc0b489784a6ee68ebdcae4a',0)):
    source=STATE/'task-progress'/('task-'+task_id+'.json');task=small(source)
    assert task['id']==task_id and task['exit_code']==exit_code and task['status']==('failed' if exit_code else 'completed')
    relative=META+'/'+label+'_TASK_ACTUAL.json';hashes[relative]=exact(source,relative)
    tasks.append(dict(label=label,task_id=task_id,actual_exit_code=exit_code,archived_task=relative,sha256=hashes[relative]))
for name,digest in hashes.items():assert sha(ROOT/name)==digest,name
for label,name,receipt,task in operational:
    event=dict.fromkeys(FIELDS)
    event.update(experiment_id='D032-'+label+'-20261003',event_id='D032-'+label+'-20261003:RESULT',
        event_type='IMPORTED_OPERATIONAL_RESULT',git_commit=spec['git_commit_at_freeze'],
        data_manifest_hash={p:v['source_options_sha256'] for p,v in spec['period_metadata'].items()},
        protocol_hash=sha(ROOT/protocol),feature_set='PAST_OWNED_FUNDING_ONLY' if label=='INDEPENDENT' else 'SAVED_FULL_PERIOD_SUMMARIES_CONDITIONAL_ATTRIBUTION',
        labels='NONE',model_family='NONE',hyperparameters='ONE_FIXED_8_7_1_GATE_NO_HPO',seed='NONE',
        thresholds=spec['adoption_criteria'],cost_assumptions='UNCHANGED_BYBIT_VIP0',all_folds='TWO_FULL_SEEN_WINDOWS_NO_SPLICE',
        success_failure=receipt['status'],reason_for_next_experiment='LONGER_FIXED_PUBLIC_REFERENCE_FALSIFICATION',
        result_influenced_later_choice=True,post_completion_registration=True,preregistered_start_record_created=False,
        artifact_path=name,artifact_sha256=sha(ROOT/name),actual_task_id=task['id'],actual_exit_code=0,
        economic_gate_passed=receipt.get('economic_adoption_criteria_passed','NOT_EVALUATED_BY_WALLET_AUDIT'))
    append_event(ROOT/'reports/experiment_registry.jsonl',event)
out=ROOT/'reports/GITHUB_CARRY_PAST_FUNDING_EXIT_SOURCE_BINDING_20261003_V1.json'
value=dict(status='PASS_EXACT_CLOSED_D032_SOURCE_BINDING_GATE_ECONOMIC_RECIPE_PAUSED_NOT_NATIVE_OR_LONG_TERM_APR',
    created_utc=datetime.now(UTC).isoformat(),source_hashes=hashes,actual_task_bindings=tasks,
    actual_root_closure=dict(path=str(root_task_path),sha256=sha(root_task_path),task=root_task,host_result=sys.argv[1],actual_exit=0),
    independent_accepted_host_result=sys.argv[2],comparison_accepted_host_result=sys.argv[3],
    economic_recipe_accepted=False,capability_preserved=True,startup_import_failure_preserved=True,
    old_QA_green_tests_control_or_market_math_repeated=False,metadata_only=True,locked_consumed=False,
    capital_net_APR='NOT_EVALUABLE',candidate_status='NO_QUALIFIED_CANDIDATE')
with out.open('x',encoding='utf-8') as stream:json.dump(value,stream,indent=2,ensure_ascii=False);stream.write('\n')
print(json.dumps(dict(status=value['status'],sha256=sha(out),frozen_ROOT_sources=len(hashes),actual_root_task_id=identity)))
