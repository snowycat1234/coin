"""Seal actual closed new90d evidence; small metadata only, no finance replay."""
from datetime import UTC, datetime
import hashlib, json, sys
from pathlib import Path
from scripts.research_v8.registry import FIELDS, append_event
ROOT=Path('/mnt/d/codex/coin');STATE=Path('/home/xflops/coin-state')
ARCHIVE='docs/archive/CARRY_90D_CLOSED_BINDING_SOURCE_20261003_V1.py'
META='docs/archive/CARRY_90D_USED_ACTUAL_METADATA_20261003_V1'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def small(path):
    p=Path(path);assert p.is_file() and not p.is_symlink() and p.stat().st_size<=2_000_000
    return json.loads(p.read_bytes())
def save_exact(source,relative):
    source=Path(source);assert source.is_relative_to(STATE) and not source.is_symlink() and source.stat().st_size<=2_000_000
    dest=ROOT/relative
    with dest.open('xb') as stream:stream.write(source.read_bytes())
    assert sha(source)==sha(dest)
    return sha(dest)
assert Path(__file__).read_bytes()==(ROOT/ARCHIVE).read_bytes()
root_name='reports/fast_research/CARRY_90D_TWO_POLICY_ROOT_ACCEPTANCE_20261003_V1.json'
assert sha(ROOT/root_name)=='95dbe4da78b7c0114321756ae9e289f094fc2b1a5066f14c54f6c65b995feed4'
root=small(ROOT/root_name);identity=root['root_task_id']
root_task_path=STATE/'task-progress'/('task-'+identity+'.json');root_task=small(root_task_path)
assert root_task['id']==identity and root_task['status']=='completed' and root_task['exit_code']==0
assert root['status']=='PASS_ROOT_CARRY_90D_TWO_POLICY_CONDITIONAL_ACCOUNT_MATH_NOT_NATIVE_OR_LONG_TERM_APR'
hashes={**root['source_hashes'],**root['small_reports'],root_name:sha(ROOT/root_name),ARCHIVE:sha(ROOT/ARCHIVE)}
bound_name='docs/archive/CARRY_90D_USED_INDEPENDENT_SOURCES_20261003_V3/ACTUAL_BINDING.json'
bound=small(ROOT/bound_name)
for absolute,digest in bound['small_inputs'].items():
    path=Path(absolute);assert path.is_relative_to(ROOT) and sha(path)==digest
    relative=str(path.relative_to(ROOT));assert relative not in hashes or hashes[relative]==digest
    hashes[relative]=digest
for version in (1,2,3):
    directory=ROOT/('docs/archive/CARRY_90D_USED_INDEPENDENT_SOURCES_20261003_V'+str(version))
    for path in sorted(directory.glob('*')):
        assert path.is_file() and path.suffix in ('.py','.json') and path.stat().st_size<=2_000_000
        hashes[str(path.relative_to(ROOT))]=sha(path)
for relative in ('docs/archive/CARRY_90D_ROOT_ACCEPTANCE_SOURCE_20261003_V2.py',):hashes[relative]=sha(ROOT/relative)
(ROOT/META).mkdir(exist_ok=False)
receipts=[('TINY','reports/fast_research/CARRY_90D_PERIOD_TINY_20261003_V1.json',0),
    ('ALL_FLAT','reports/fast_research/CARRY_90D_ALL_FLAT_ACTUAL_20261003_V1.json',0),
    ('PAIR_TRIM','reports/fast_research/CARRY_90D_PAIR_TRIM_ACTUAL_20261003_V1.json',0),
    ('INDEPENDENT_V1','reports/fast_research/CARRY_90D_TWO_POLICY_DECIMAL_INDEPENDENT_AUDIT_20261003_V1.json',1),
    ('INDEPENDENT_V2','reports/fast_research/CARRY_90D_TWO_POLICY_DECIMAL_INDEPENDENT_AUDIT_20261003_V2.json',1),
    ('INDEPENDENT_V3','reports/fast_research/CARRY_90D_TWO_POLICY_DECIMAL_INDEPENDENT_AUDIT_20261003_V3.json',0)]
tasks=[];operational=[]
for label,name,exit_code in receipts:
    receipt=small(ROOT/name);task_path=STATE/'task-progress'/('task-'+receipt['binding']['task_id']+'.json');task=small(task_path)
    assert task['id']==receipt['binding']['task_id'] and task['exit_code']==exit_code and task['status']==('completed' if exit_code==0 else 'failed')
    relative=META+'/'+label+'_TASK_ACTUAL.json';hashes[relative]=save_exact(task_path,relative)
    hashes[name]=sha(ROOT/name);tasks.append(dict(label=label,task_id=task['id'],actual_exit_code=exit_code,archived_task=relative,sha256=hashes[relative]))
    if label in ('TINY','ALL_FLAT','PAIR_TRIM'):work=Path(receipt['run_dir'])
    else:work=STATE/('test-carry-90d-two-controls-independent-audit-20261003-v'+label[-1])
    run=work/'RUN_BINDING.json'
    if run.exists():
        relative=META+'/'+label+'_RUN_BINDING.json';hashes[relative]=save_exact(run,relative)
    if label.startswith('INDEPENDENT'):
        operational.append((label,name,receipt,task,exit_code))
relative=META+'/ROOT_TASK_ACTUAL.json';hashes[relative]=save_exact(root_task_path,relative)
for relative,digest in hashes.items():assert sha(ROOT/relative)==digest
actual_root=dict(path=str(root_task_path),sha256=sha(root_task_path),task=root_task,host_result=sys.argv[1],actual_exit=0)
for label,name,receipt,task,exit_code in operational:
    event=dict.fromkeys(FIELDS)
    event.update(experiment_id='CARRY-90D-'+label+'-20261003',event_id='CARRY-90D-'+label+'-20261003:RESULT',
        event_type='IMPORTED_OPERATIONAL_RESULT',git_commit=root['git_commit'],
        data_manifest_hash=hashes['reports/fast_research/CARRY_90D_SOURCE_VIEW_20261003_V1.json'],
        protocol_hash=hashes['protocols/CONDITIONAL_CARRY_90D_FIXED_PERIOD_20261003_V1.json'],feature_set='INDEPENDENT_SAME_SOURCE',labels='NONE',
        model_family='NONE',hyperparameters='NO_RESEARCH_PARAMETER_CHANGE',seed='NONE',thresholds='CASH_1e-7_RATIO_1e-10',
        cost_assumptions='FIXED_BYBIT_VIP0',all_folds='TWO_FIXED_FULL90D_CONTROL_ACCOUNTS',success_failure=receipt['status'],
        reason_for_next_experiment='CORRECT_AUDIT_ADAPTER' if exit_code else 'PAST_ONLY_FUNDING_EXIT_HYPOTHESIS',
        result_influenced_later_choice=True,post_completion_registration=True,preregistered_start_record_created=False,
        artifact_path=name,artifact_sha256=sha(ROOT/name),actual_task_id=task['id'],actual_exit_code=exit_code,
        completed_financial_cases=receipt['completed_cases_verified'])
    append_event(ROOT/'reports/experiment_registry.jsonl',event)
out=ROOT/'reports/GITHUB_CARRY_90D_SOURCE_BINDING_20261003_V1.json'
value=dict(status='PASS_EXACT_CLOSED_CARRY_90D_TWO_POLICY_BINDING_NOT_NATIVE_OR_LONG_TERM_APR',created_utc=datetime.now(UTC).isoformat(),
    source_hashes=hashes,actual_root_closure=actual_root,actual_task_bindings=tasks,independent_accepted_host_result=sys.argv[2],
    failed_v1_and_v2_preserved=True,accepted_independent_version=3,old_QA_green_tests_or_market_math_repeated=False,
    metadata_only=True,locked_consumed=False,capital_net_APR='NOT_EVALUABLE',candidate_status='NO_QUALIFIED_CANDIDATE')
with out.open('x',encoding='utf-8') as stream:json.dump(value,stream,indent=2,ensure_ascii=False);stream.write('\n')
print(json.dumps(dict(status=value['status'],sha256=sha(out),frozen_ROOT_sources=len(hashes),actual_root_task_id=identity)))
