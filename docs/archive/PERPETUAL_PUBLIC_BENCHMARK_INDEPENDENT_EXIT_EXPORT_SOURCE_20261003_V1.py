"""Closed D041 audit metadata export only: no finance/target/source payload read."""
from pathlib import Path
import hashlib, importlib.util, json, os
ROOT=Path('/mnt/d/codex/coin');STATE=Path('/home/xflops/coin-state')
RUN=STATE/'d041-public-benchmark-independent-20261003-v1'
GUARD=ROOT/'docs/archive/VOL_MANAGED_HOLD_547D_ROOT_CLOSE_SOURCE_20261003_V2.py'
GSH='278c9117283b88eb73b50276f37a4cd86449ffd87e747556db301dc146ce905a'
SOURCE=ROOT/'scripts/investment/audit_perpetual_public_benchmark.py'
SSH='4e30e75cc5add4664bd02aa559af1f9ec31c7c2a3fba80ce7a732530dc5c0b91'
REPORT=ROOT/'reports/fast_research/PERPETUAL_PUBLIC_BENCHMARK_INDEPENDENT_AUDIT_20261003_V1.json'
RSH='bf13af35aac4d77a2279a758d437195d6c8bfda81331d89977225c2fddb7a3bb'
OUT=ROOT/'reports/fast_research/PERPETUAL_PUBLIC_BENCHMARK_INDEPENDENT_ACTUAL_EXIT_20261003_V1.json'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
assert sha(GUARD)==GSH
spec=importlib.util.spec_from_file_location('d041_exit_guards',GUARD);g=importlib.util.module_from_spec(spec);spec.loader.exec_module(g)
r,_=g.small(REPORT,RSH);plan,plan_sha=g.small(RUN/'ACTUAL_BINDING.json');rb,rb_sha=g.small(RUN/'RUN_BINDING.json',r['run_binding_sha256'])
assert sha(SOURCE)==SSH==r['independent_source_sha256']==rb['checker_sha256']==plan['checker_sha256']
assert r['completed_cases_verified']==r['completed_full_calendar_cases_verified']==8 and r['incomplete_or_halted_cases_verified']==0
task_id=r['binding']['task_id'];task=g.closed(task_id);producer=g.closed(plan['actual_task_id'])
assert task_id=='5e9cf0e359624004a737680fdffc4d54' and plan_sha==r['binding']['ACTUAL_BINDING_sha256']
assert rb==r['binding'] and plan['actual_report_sha256']==r['actual_report_sha256']
archive=ROOT/'docs/archive';used=archive/'PERPETUAL_PUBLIC_BENCHMARK_INDEPENDENT_USED_ACTUAL_METADATA_20261003_V1'
used.mkdir(exist_ok=False)
copies={
    SOURCE:archive/'PERPETUAL_PUBLIC_BENCHMARK_INDEPENDENT_AUDITOR_20261003_V1.py',
    RUN/'ACTUAL_BINDING.json':archive/'PERPETUAL_PUBLIC_BENCHMARK_INDEPENDENT_ACTUAL_BINDING_20261003_V1.json',
    RUN/'RUN_BINDING.json':used/'RUN_BINDING.json',
    STATE/'task-progress'/f'task-{task_id}.json':used/'COMPLETED_TASK.json',
    STATE/'task-progress'/'task-78c92a5f30cc460ea0819aa226b2ee64.json':used/'AST_COMPILE_COMPLETED_TASK.json'}
bindings={}
for source,target in copies.items():
    data=g.ordinary(source).read_bytes()
    with target.open('xb') as f:f.write(data)
    assert sha(source)==sha(target)
    bindings[str(target.relative_to(ROOT))]=sha(target)
receipt=dict(status='PASS_D041_INDEPENDENT_EIGHT_AUDIT_ACTUAL_EXIT_AND_SOURCE_BYTES_ONLY',
    audit_report_path=str(REPORT.relative_to(ROOT)),audit_report_sha256=RSH,actual_independent_task=task,
    parent_actual_task=producer,host_session=45167,host_completion_chunk='a9646d',actual_exit_code=0,
    checker_path=str(SOURCE.relative_to(ROOT)),checker_sha256=SSH,run_binding_sha256=rb_sha,ACTUAL_BINDING_sha256=plan_sha,
    actual_report_sha256=r['actual_report_sha256'],archived_exact_bytes=bindings,
    maximum_errors=r['maximum_errors'],tolerances=r['tolerances'],completed_cases_verified=8,
    finance_targets_sources_replayed=False,export_scope='ONLY_ALREADY_CLOSED_SMALL_METADATA_AND_SOURCE_BYTES',
    registry_written_by_auditor=False,registry_timing_requires_root_actual_registration_not_fabricated_before_start=True,
    metadata_caller_task_id=os.environ['COIN_TASK_ID'],metadata_source_sha256=sha(__file__),
    own_completion='LIVE_METADATA_CALLER_NOT_SELF_CERTIFIED',candidate='NO_QUALIFIED_CANDIDATE',
    unit_certified=False,native_market_certified=False,long_term_APR='NOT_EVALUABLE')
digest,size=g.write(OUT,receipt)
print(json.dumps(dict(status=receipt['status'],path=str(OUT),sha256=digest,metadata_task=os.environ['COIN_TASK_ID'])),flush=True)
