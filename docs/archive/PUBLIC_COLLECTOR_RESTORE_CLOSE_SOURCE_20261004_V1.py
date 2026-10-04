"""Close actual D066 restoration evidence; do not launch or modify collectors."""
import argparse, hashlib, json, os, subprocess
from datetime import UTC, datetime
from pathlib import Path
from quant.paths import ROOT, STATE
from scripts.research_v8.registry import FIELDS, append_event

PARENT = 'b6b517710a29406bbb46e2142cba64dc1a57a38e'
PREFIX = 'PUBLIC_COLLECTOR'
parser = argparse.ArgumentParser()
parser.add_argument('action', choices=['close', 'post'])
parser.add_argument('--remote-head')
args = parser.parse_args()
assert os.environ['COIN_TASK_ID']
def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def read(path): return json.loads(Path(path).read_bytes())
def git(*parts): return subprocess.check_output(['git', *parts], cwd=ROOT, text=True).strip()
def write(path, value):
    with Path(path).open('x') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2); stream.write('\n')

source = ROOT/'reports/GITHUB_PUBLIC_COLLECTOR_RESTORE_SOURCE_BINDING_20261004_V1.json'
lock = sha(ROOT/'state/dataset_lock.json')
assert lock == '29d930063842e9b1666869b4e5f9e3c8cd629313e57b9dadc328c6131b92f45d'
if args.action == 'post':
    s = read(source); head = git('rev-parse', 'HEAD')
    assert head == args.remote_head and git('rev-parse', 'HEAD~1') == PARENT
    assert not git('status', '--porcelain=v1', '--untracked-files=no')
    assert sorted(git('ls-files', '--others', '--exclude-standard').splitlines()) == sorted(s['prior_WIP_preserved'])
    for name, digest in s['source_hashes'].items(): assert sha(ROOT/name) == digest, name
    gate = ROOT/'reports/GITHUB_PUBLIC_COLLECTOR_RESTORE_STAGED_GATE_20261004_V1.json'
    g = read(gate); assert g['status'] == 'STAGED_MODULE_CHECKPOINT_PASS'
    tasks = [read(path) for path in (STATE/'task-progress').glob('task-*.json')]
    roles = {}
    for role, title in dict(CLOSE='D066采集恢复实际验收与来源保存', GATE='D066提交前源码与敏感信息门槛', COMMIT='D066公开采集恢复正常提交', PUSH='D066已验收采集恢复推送GitHub', REMOTE='D066精确核对远端main提交').items():
        found = [t for t in tasks if t['title'] == title]; assert len(found) == 1
        task = found[0]; assert task['status'] == 'completed' and task['exit_code'] == 0 and task['ended_at']
        roles[role] = task
    out = ROOT/'reports/GITHUB_PUBLIC_COLLECTOR_RESTORE_SYNC_VERIFIED_20261004_V1.json'
    write(out, dict(status='PUSHED_AND_EXACT_REMOTE_MAIN_VERIFIED', parent_commit=PARENT, local_HEAD=head, remote_main=args.remote_head,
        remote='https://github.com/snowycat1234/coin.git', created_utc=datetime.now(UTC).isoformat(), actual_closed_roles=roles,
        source_binding_sha256=sha(source), staged_gate_sha256=sha(gate), preserved_untracked_paths=s['prior_WIP_preserved'],
        tracked_worktree_clean=True, force_push=False, private_SHA_only=lock, private_body_read=False,
        own_artifact_untracked_until_next_normal_module=True, orders_sent=0, locked_consumed=False))
    print(json.dumps(dict(path=str(out), local_HEAD=head, remote_main=args.remote_head, sha256=sha(out)))); raise SystemExit

assert git('rev-parse', 'HEAD') == PARENT
prior = ROOT/'reports/GITHUB_DONCHIAN_ACTIVE_ALLOCATION_SYNC_VERIFIED_20261004_V1.json'
assert sha(prior) == '44836b6c013d816998b8face4d876fa78e3a26fac3c57fcc00076ada95f97177'
wip = read(prior)['preserved_untracked_paths']; assert len(wip) == 36
paths = [ROOT/'reports'/f'{PREFIX}_{name}_20261004_V1.json' for name in ('PRESERVATION','MANIFEST_IDENTITIES','RESTORE_LAUNCH','RESTORE_SAMPLE1','RESTORE_SAMPLE2')]
pres, identities, launch, first, last = [read(path) for path in paths]
assert identities['status'] == 'ALL_ORIGINAL_L1_MANIFEST_PAYLOAD_IDENTITIES_EXACT_NOT_DATA_QUALIFICATION'
assert identities['exact_files'] == identities['checked_files'] == identities['required_files'] == 2008 and not identities['errors']
assert pres['exit_code'] == pres['exit_reason'] == 'UNKNOWN'
assert pres['original_source_files_stable_after_derivative_queries'] and pres['original_source_bindings_match_prior']
for name, digest in pres['source_hashes'].items(): assert sha(ROOT/name) == digest, name
assert sha(ROOT/'src/quant/microstructure.py') == pres['microstructure']['binding']['implementation_sha256']
assert launch['capacity']['total_bytes'] + launch['capacity']['reserved_bytes'] < 32_000_000_000
assert first['errors'] == last['errors'] == []
assert first['public']['session']['id'] == last['public']['session']['id'] > pres['public']['session']['id']
assert first['microstructure']['checkpoint']['session'] == last['microstructure']['checkpoint']['session'] != pres['microstructure']['checkpoint']['session']
assert last['public']['session']['heartbeat_ms'] > first['public']['session']['heartbeat_ms']
for symbol in ('BTCUSDT','ETHUSDT'):
    assert last['public']['symbols'][symbol]['websocket'] > first['public']['symbols'][symbol]['websocket']
    assert last['public']['symbols'][symbol]['last_websocket_received_ms'] > first['public']['symbols'][symbol]['last_websocket_received_ms']
assert last['microstructure']['checkpoint']['accepted_events'] > first['microstructure']['checkpoint']['accepted_events']
assert last['microstructure']['checkpoint']['asof_us'] > first['microstructure']['checkpoint']['asof_us']
gap = next(row for row in last['micro_restart_gap_tail'] if row['kind'] == 'RESTART_GAP')
assert json.loads(gap['payload'])['uncommitted_tail_unknown']
event = next(row for row in last['public_lifecycle_tail'] if row['kind'] == 'UNGRACEFUL_PREVIOUS_SESSION')
assert json.loads(event['payload'])['unobserved_time_not_credited']
live = []
for handle in last['processes']:
    proc = Path('/proc')/str(handle['pid'])
    argv = [v.decode() for v in (proc/'cmdline').read_bytes().split(b'\0') if v]
    ticks = int((proc/'stat').read_text().rsplit(')',1)[1].split()[19])
    cgroup = (proc/'cgroup').read_text().strip()
    assert argv == handle['argv'] and ticks == handle['start_ticks'] and 'coin-quant.slice' in cgroup
    saved = next(t['metadata'] for t in last['actual_task_receipts'] if t['metadata']['pid'] == handle['pid'])
    actual = read(STATE/'task-progress'/('task-'+saved['id']+'.json'))
    assert actual['status'] == 'running' and actual['start_ticks'] == ticks
    live.append(dict(pid=handle['pid'], start_ticks=ticks, argv=argv, cgroup=cgroup))
review = ROOT/'reports/PUBLIC_COLLECTOR_RESTORE_INDEPENDENT_REVIEW_20261004_V1.md'
assert review.is_file()
closed = {}
for path, report in zip(paths, (pres,identities,launch,first,last)):
    task = read(STATE/'task-progress'/('task-'+report['task_id']+'.json'))
    assert task['status'] == 'completed' and task['exit_code'] == 0 and task['ended_at']
    closed[task['id']] = dict(title=task['title'], actual_exit_code=0, artifact_sha256=sha(path))
    record = dict.fromkeys(FIELDS)
    record.update(event_id='D066-'+task['id']+':RESULT', event_type='OPERATIONAL_RESULT', experiment_id='D066-ORIGINAL-PUBLIC-COLLECTOR-RESTORE-20261004', git_commit=PARENT,
        data_manifest_hash=sha(paths[1]), protocol_hash=last['public']['contract_sha256'], model_family='NONE', fits=0, all_folds='NO_RESEARCH_OR_QUALIFICATION',
        success_failure='COMPLETED_EXIT0_CAPTURED_OPERATIONAL_EVIDENCE', artifact_path=path.relative_to(ROOT).as_posix(), artifact_sha256=sha(path),
        reason_for_next_experiment='Restore authorized original read-only sources; preserve gaps and unknown exit; scientific exit-window test not started', result_influenced_later_choice='FORWARD_COLLECTION_RESUMED_NOT_ALPHA_OR_HEALTH_QUALIFICATION')
    append_event(ROOT/'reports/experiment_registry.jsonl', record)
selected = {'README.md','AGENTS.md','docs/RESEARCH_STATUS.md','docs/RESEARCH_DECISION_LOG.md','docs/GOALS.md','docs/PROGRESS.md','docs/FAST_RESEARCH_TASK_CHECKLIST.md','docs/MULTI_ASSET_PORTFOLIO_20261004.md','docs/PUBLIC_COLLECTOR_RESTORE_20261004.md','reports/experiment_registry.jsonl',prior.relative_to(ROOT).as_posix()}
for folder in ('reports','docs/archive'):
    selected.update(path.relative_to(ROOT).as_posix() for path in (ROOT/folder).glob('PUBLIC_COLLECTOR_*20261004_V*.?*') if path.is_file())
selected.update(path.relative_to(ROOT).as_posix() for path in (ROOT/'docs/archive/PUBLIC_COLLECTOR_TASK_METADATA_20261004_V1').iterdir() if path.is_file())
assert not set(wip).intersection(selected)
write(source, dict(status='D066_ORIGINAL_PUBLIC_COLLECTORS_RESTORED_TWO_SAMPLES_NOT_QUALIFICATION', task_id=os.environ['COIN_TASK_ID'], parent_commit=PARENT,
    created_utc=datetime.now(UTC).isoformat(), source_hashes={name:sha(ROOT/name) for name in sorted(selected)}, selected_module_paths=sorted(selected), prior_WIP_preserved=wip,
    closed_actual_roles=closed, actual_live_processes_at_close=live, independent_review_sha256=sha(review), private_SHA_only=lock, private_body_read=False,
    exit_reason='UNKNOWN', healthy_gap_splicing=False, real_time_days_certified=0, alpha_eligible=False,
    orders_sent=0, credentials_used=False, new_services=0, microstructure_version='microstructure_l1_v1', new_market_replays=0, models_fit=0,
    latest_actual_capacity=launch['capacity'], new_capacity_scan_at_close=False))
print(json.dumps(dict(path=str(source), sha256=sha(source), selected_paths=len(selected), live_handles=live)))
