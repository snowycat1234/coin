"""Save this finite saved-exit mechanism diagnostic and verify its normal Git delivery."""
import argparse
from datetime import UTC, datetime
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
from quant.paths import ROOT, STATE

PARENT = '9bfeef0808ed65f8a618310f46b57cb88e5c72c2'
STEM = 'DONCHIAN_EXIT_WAIT_20261005_V1'
parser = argparse.ArgumentParser()
parser.add_argument('action', choices=('close', 'post'))
parser.add_argument('--remote-head')
args = parser.parse_args()

def read(path): return json.loads(Path(path).read_bytes())
def sha(path):
    with Path(path).open('rb') as stream: return hashlib.file_digest(stream, 'sha256').hexdigest()
def git(*a): return subprocess.check_output(['git', *a], cwd=ROOT, text=True).strip()
def save(path, value):
    with Path(path).open('x') as stream: json.dump(value, stream, indent=2, ensure_ascii=False); stream.write('\n')
def closed(task_id):
    task = read(STATE/'task-progress'/('task-'+task_id+'.json'))
    assert task['ended_at'] and task['status']=='completed' and task['exit_code']==0
    return task

proof = ROOT/'reports/GITHUB_DONCHIAN_EXIT_WAIT_SOURCE_BINDING_20261005_V1.json'
private = sha(ROOT/'state/dataset_lock.json')
assert private == '29d930063842e9b1666869b4e5f9e3c8cd629313e57b9dadc328c6131b92f45d'
if args.action == 'post':
    binding = read(proof)
    assert git('rev-parse','HEAD')==args.remote_head and git('rev-parse','HEAD~1')==PARENT
    assert not git('status','--porcelain=v1','--untracked-files=no')
    assert sorted(git('ls-files','--others','--exclude-standard').splitlines())==sorted(binding['prior_WIP_preserved'])
    for name, digest in binding['source_hashes'].items(): assert sha(ROOT/name)==digest, name
    gate = ROOT/'reports/GITHUB_DONCHIAN_EXIT_WAIT_STAGED_GATE_20261005_V1.json'
    assert read(gate)['status']=='STAGED_MODULE_CHECKPOINT_PASS'
    tasks = [read(p) for p in (STATE/'task-progress').glob('task-*.json')]
    roles = {}
    for role, title in dict(CLOSE='D069实际机制与独立复核验收保存', GATE='D069提交前源码与敏感信息门槛',
            COMMIT='D069退出等待机制实际诊断正常提交', PUSH='D069已验收退出等待机制模块推送GitHub', REMOTE='D069精确核对远端main提交').items():
        found = [t for t in tasks if t['title']==title]; assert len(found)==1
        roles[role] = closed(found[0]['id'])
    output = ROOT/'reports/GITHUB_DONCHIAN_EXIT_WAIT_SYNC_VERIFIED_20261005_V1.json'
    save(output, dict(status='PUSHED_AND_EXACT_REMOTE_MAIN_VERIFIED', local_HEAD=args.remote_head,
        remote_main=args.remote_head, parent_commit=PARENT, remote='https://github.com/snowycat1234/coin.git',
        closed_actual_roles=roles, source_binding_sha256=sha(proof), staged_gate_sha256=sha(gate),
        preserved_untracked_paths=binding['prior_WIP_preserved'], tracked_worktree_clean=True,
        private_SHA_only=private, private_body_read=False, force_push=False, orders_sent=0,
        own_artifact_untracked_until_next_normal_module=True, created_utc=datetime.now(UTC).isoformat()))
    print(json.dumps(dict(path=str(output),sha256=sha(output),remote_main=args.remote_head)))
    raise SystemExit
assert git('rev-parse','HEAD')==PARENT
prior = ROOT/'reports/GITHUB_DONCHIAN_TIME_STABILITY_SYNC_VERIFIED_20261005_V1.json'
assert sha(prior)=='fd41686e7bdbca9ea85db128c001411463a18018e07a655675dface42a95f38a'
protocol = read(ROOT/'protocols'/(STEM+'.json'))
for name, digest in protocol['source_hashes'].items(): assert sha(ROOT/name)==digest, name
result = read(ROOT/'reports/fast_research'/(STEM+'.json'))
assert result['status']=='COMPLETE_SAVED_EXIT_WAIT_MECHANISM_NOT_CAUSAL_ALPHA' and len(result['cases'])==4
assert all(len(case['episodes'])==13 for case in result['cases'])
review = ROOT/'reports/DONCHIAN_EXIT_WAIT_INDEPENDENT_REVIEW_20261005_V1.md'
assert sha(review)=='bc903183e63bc019bf475f4edeb25908e31539dd548328378372a3d80a0e1378'
dest = ROOT/'docs/archive/DONCHIAN_EXIT_WAIT_USED_METADATA_20261005_V1'; dest.mkdir()
roles = {}
for task_id in (result['task_id'], 'f295a3d81a9042bfbfa2e4559a9bfa5d'):
    roles[task_id]=closed(task_id)
    shutil.copyfile(STATE/'task-progress'/('task-'+task_id+'.json'), dest/('task-'+task_id+'.json'))
reference = STATE/'d069-exit-wait-independent-20261005-v1/independent_review.py'
assert sha(reference)=='f99e5922a6b83d0999f78bb57342ffa4d5c246f09129ada5586408b4185724e2'
shutil.copyfile(reference, dest/'independent_review.py')
selected = ['AGENTS.md','README.md','docs/RESEARCH_STATUS.md','docs/GOALS.md','docs/PROGRESS.md',
    'docs/RESEARCH_DECISION_LOG.md','docs/FAST_RESEARCH_TASK_CHECKLIST.md','docs/MULTI_ASSET_PORTFOLIO_20261004.md',
    'reports/experiment_registry.jsonl','scripts/investment/donchian_exit_wait.py',
    'docs/DONCHIAN_EXIT_WAIT_20261005.md', 'docs/archive/DONCHIAN_EXIT_WAIT_RELEASE_SOURCE_20261005_V1.py',
    'protocols/'+STEM+'.json','reports/fast_research/'+STEM+'.json',review.relative_to(ROOT).as_posix(),prior.relative_to(ROOT).as_posix()]
selected += [p.relative_to(ROOT).as_posix() for p in dest.iterdir()]
wip = read(prior)['preserved_untracked_paths']; assert len(wip)==36 and not set(wip).intersection(selected)
save(proof, dict(status='D069_ACTUAL_EXIT_WAIT_MECHANISM_WITH_INDEPENDENT_ENDPOINTS_NOT_CAUSAL_ALPHA',
    task_id=os.environ['COIN_TASK_ID'], parent_commit=PARENT, selected_module_paths=sorted(selected),
    source_hashes={name:sha(ROOT/name) for name in sorted(selected)}, prior_WIP_preserved=wip,
    closed_actual_science_roles=roles, private_SHA_only=private, private_body_read=False,
    actual_pairs=4, actual_days=303, actual_episodes=52, actual_new_wallets=0, HPO=0, market_replays=0,
    candidate='NONE', investment='CASH', long_term_APR='NOT_EVALUABLE', created_utc=datetime.now(UTC).isoformat()))
print(json.dumps(dict(path=str(proof),sha256=sha(proof),selected_paths=len(selected))))
