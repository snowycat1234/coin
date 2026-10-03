"""Close only actual task/report metadata before the thin root acceptance."""
import hashlib,json,os
from datetime import UTC,datetime
from pathlib import Path
R=Path('/mnt/d/codex/coin');S=Path('/home/xflops/coin-state')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(Path(p).read_bytes())
def copy(p,q):
    with q.open('xb') as f:f.write(p.read_bytes())
    assert sha(q)==sha(p)
draft=R/'.cache/perpetual_directional_final_roles_draft_20261003_v1.json'
assert sha(draft)=='068285c1d7f1124c5235ff7045d840112d06b6c5c80a4e6210f16caada1e8bae'
plan=read(draft);assert not plan['ready_to_execute']
plan['roles']['SETTLEMENT_TEST']['path']='reports/fast_research/PERPETUAL_SETTLEMENT_TEST_ACTUAL_20261003_V1.json'
for role,item in plan['roles'].items():
    report=read(R/item['path']);h=sha(R/item['path']);identity=report['binding']['task_id']
    assert report['status']==item['required_status']
    if item.get('sha256'):assert item['sha256']==h
    if item.get('task_id'):assert item['task_id']==identity
    path=S/'task-progress'/('task-'+identity+'.json');task=read(path)
    assert task['status']=='completed' and task['exit_code']==0
    item.update(sha256=h,task_id=identity,actual_task_path=str(path),actual_task_sha256=sha(path),actual_exit_code=0,actual_status='completed')
plan['settlement_protocol']['sha256']=sha(R/plan['settlement_protocol']['path'])
assert sha(R/'scripts/investment/accept_perpetual_directional.py')==plan['helper_sha256']==sha(R/'docs/archive/PERPETUAL_DIRECTIONAL_ROOT_ACCEPTANCE_SOURCE_20261003_V1.py')
own=R/'docs/archive/PERPETUAL_DIRECTIONAL_ROOT_BINDING_FREEZER_20261003_V1.py';copy(Path(__file__),own)
extra=plan['additional_project_files'];extra[str(own.relative_to(R))]=sha(own)
for name in ('PERPETUAL_SETTLEMENT_PROTOCOL_FREEZER_20261003_V1.py','COIN_AUTONOMOUS_LONG_SHORT_PROMPT_USER_20261003.md'):
    path=R/'docs/archive'/name;extra[str(path.relative_to(R))]=sha(path)
test=read(R/plan['roles']['SETTLEMENT_TEST']['path'])
work=Path(test['run_dir']);witnesses=list(work.glob('pytest/**/settlement_evidence.json'));assert len(witnesses)==1
target=R/'reports/fast_research/PERPETUAL_SETTLEMENT_SYNTHETIC_WITNESS_20261003_V1.json';copy(witnesses[0],target)
extra[str(target.relative_to(R))]=sha(target)
# Preserve the two new audit receipts/task archives, not their large real ledgers.
for folder in ('PERPETUAL_SETTLEMENT_INDEPENDENT_USED_ACTUAL_METADATA_20261003_V1',):
    directory=R/'docs/archive'/folder;assert directory.is_dir()
    for path in directory.iterdir():
        assert path.is_file() and path.stat().st_size<2_000_000;extra[str(path.relative_to(R))]=sha(path)
for name in ('PERPETUAL_SETTLEMENT_INDEPENDENT_ACTUAL_BINDING_20261003_V1.json',
             'PERPETUAL_SETTLEMENT_INDEPENDENT_AUDITOR_20261003_V1.py',
             'PERPETUAL_SETTLEMENT_INDEPENDENT_COMPILE_ONLY_SOURCE_20261003_V1.py'):
    path=R/'docs/archive'/name;extra[str(path.relative_to(R))]=sha(path)
path=R/'reports/fast_research/PERPETUAL_SETTLEMENT_INDEPENDENT_ACTUAL_EXIT_20261003_V1.json'
extra[str(path.relative_to(R))]=sha(path)
plan.update(ready_to_execute=True,created_utc=datetime.now(UTC).isoformat(),freezer_task_id=os.environ['COIN_TASK_ID'],
    final_scope='THIRTY_ORIGINAL_FULL_CALENDARS_AND_TWO_NEW_CORRECTED_CASES_NOT_SPLICED_NAV',
    additional_project_files=extra)
target=R/'protocols/PERPETUAL_DIRECTIONAL_ROOT_BINDING_20261003_V1.json'
with target.open('x',encoding='utf-8') as f:json.dump(plan,f,ensure_ascii=False,indent=2);f.write('\n')
print(json.dumps(dict(binding=str(target),sha256=sha(target),roles=len(plan['roles']),market_arrays_read=False,task_id=os.environ['COIN_TASK_ID'])))
