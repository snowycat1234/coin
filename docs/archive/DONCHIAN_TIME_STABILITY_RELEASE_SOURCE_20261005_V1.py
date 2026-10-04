"""Save this finite saved-wallet diagnostic and verify its normal Git delivery."""
import argparse
from datetime import UTC, datetime
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
from quant.paths import ROOT, STATE

PARENT = '33fa0de74cc9fb9d86420d2f1ad0d6d48b49d998'
STEM = 'DONCHIAN_TIME_STABILITY_20261005_V1'
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

proof = ROOT/'reports/GITHUB_DONCHIAN_TIME_STABILITY_SOURCE_BINDING_20261005_V1.json'
private = sha(ROOT/'state/dataset_lock.json')
assert private == '29d930063842e9b1666869b4e5f9e3c8cd629313e57b9dadc328c6131b92f45d'
if args.action == 'post':
    binding = read(proof)
    assert git('rev-parse','HEAD')==args.remote_head and git('rev-parse','HEAD~1')==PARENT
    assert not git('status','--porcelain=v1','--untracked-files=no')
    assert sorted(git('ls-files','--others','--exclude-standard').splitlines())==sorted(binding['prior_WIP_preserved'])
    for name, digest in binding['source_hashes'].items(): assert sha(ROOT/name)==digest, name
    gate = ROOT/'reports/GITHUB_DONCHIAN_TIME_STABILITY_STAGED_GATE_20261005_V1.json'
    assert read(gate)['status']=='STAGED_MODULE_CHECKPOINT_PASS'
    tasks = [read(p) for p in (STATE/'task-progress').glob('task-*.json')]
    roles = {}
    for role, title in dict(CLOSE='D068实际诊断与独立复核验收保存', GATE='D068提交前源码与敏感信息门槛',
            COMMIT='D068时间稳定性实际诊断正常提交', PUSH='D068已验收时间诊断模块推送GitHub', REMOTE='D068精确核对远端main提交').items():
        found = [t for t in tasks if t['title']==title]; assert len(found)==1
        roles[role] = closed(found[0]['id'])
    output = ROOT/'reports/GITHUB_DONCHIAN_TIME_STABILITY_SYNC_VERIFIED_20261005_V1.json'
    save(output, dict(status='PUSHED_AND_EXACT_REMOTE_MAIN_VERIFIED', local_HEAD=args.remote_head,
        remote_main=args.remote_head, parent_commit=PARENT, remote='https://github.com/snowycat1234/coin.git',
        closed_actual_roles=roles, source_binding_sha256=sha(proof), staged_gate_sha256=sha(gate),
        preserved_untracked_paths=binding['prior_WIP_preserved'], tracked_worktree_clean=True,
        private_SHA_only=private, private_body_read=False, force_push=False, orders_sent=0,
        own_artifact_untracked_until_next_normal_module=True, created_utc=datetime.now(UTC).isoformat()))
    print(json.dumps(dict(path=str(output),sha256=sha(output),remote_main=args.remote_head)))
    raise SystemExit
assert git('rev-parse','HEAD')==PARENT
prior = ROOT/'reports/GITHUB_DONCHIAN_EXIT10_SYNC_VERIFIED_20261004_V1.json'
assert sha(prior)=='26fe768de351975db576b0826f7f60d42057c47be75a091e600c42b81c51e347'
protocol = read(ROOT/'protocols'/(STEM+'.json'))
for name, digest in protocol['source_hashes'].items(): assert sha(ROOT/name)==digest, name
result = read(ROOT/'reports/fast_research'/(STEM+'.json'))
assert result['status']=='COMPLETE_SAVED_PAIR_TIME_DIAGNOSTIC_POST_SELECTION_NOT_APR' and len(result['pairs'])==4
assert all(i['includes_zero'] for pair in result['pairs'] for i in pair['block_intervals'])
review = ROOT/'reports/DONCHIAN_TIME_STABILITY_INDEPENDENT_REVIEW_20261005_V1.md'
assert sha(review)=='ea52b07ce3b80d946655593deda46ea87521278bd826a886b1d301f9404ba2d5'
dest = ROOT/'docs/archive/DONCHIAN_TIME_STABILITY_USED_METADATA_20261005_V1'; dest.mkdir()
roles = {}
for task_id in (result['task_id'], '53d0d5303c7b445cbae54d11fea690e4'):
    roles[task_id]=closed(task_id)
    shutil.copyfile(STATE/'task-progress'/('task-'+task_id+'.json'), dest/('task-'+task_id+'.json'))
reference = STATE/'d068-time-stability-independent-20261005-v1/independent_review.py'
assert sha(reference)=='ea8adbff7a558d24ab8fb30decc599ba6c2b8bd1683827b25dfeff969efec882'
shutil.copyfile(reference, dest/'independent_review.py')
selected = ['AGENTS.md','README.md','docs/RESEARCH_STATUS.md','docs/GOALS.md','docs/PROGRESS.md',
    'docs/RESEARCH_DECISION_LOG.md','docs/FAST_RESEARCH_TASK_CHECKLIST.md','docs/MULTI_ASSET_PORTFOLIO_20261004.md',
    'reports/experiment_registry.jsonl','scripts/investment/donchian_time_stability.py',
    'docs/DONCHIAN_TIME_STABILITY_20261005.md', 'docs/archive/DONCHIAN_TIME_STABILITY_RELEASE_SOURCE_20261005_V1.py',
    'protocols/'+STEM+'.json','reports/fast_research/'+STEM+'.json',review.relative_to(ROOT).as_posix(),prior.relative_to(ROOT).as_posix()]
selected += [p.relative_to(ROOT).as_posix() for p in dest.iterdir()]
wip = read(prior)['preserved_untracked_paths']; assert len(wip)==36 and not set(wip).intersection(selected)
save(proof, dict(status='D068_ACTUAL_TIME_DIAGNOSTIC_WITH_INDEPENDENT_ARITHMETIC_NOT_STABLE_ALPHA',
    task_id=os.environ['COIN_TASK_ID'], parent_commit=PARENT, selected_module_paths=sorted(selected),
    source_hashes={name:sha(ROOT/name) for name in sorted(selected)}, prior_WIP_preserved=wip,
    closed_actual_science_roles=roles, private_SHA_only=private, private_body_read=False,
    actual_pairs=4, actual_days=303, actual_descriptive_draws=24000, HPO=0, market_replays=0,
    candidate='NONE', investment='CASH', long_term_APR='NOT_EVALUABLE', created_utc=datetime.now(UTC).isoformat()))
print(json.dumps(dict(path=str(proof),sha256=sha(proof),selected_paths=len(selected))))
