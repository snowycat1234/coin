"""Archive finite D070 evidence and verify its normal Git delivery; no market replay."""
import argparse, hashlib, json, os, shutil, subprocess
from datetime import UTC, datetime
from pathlib import Path
from quant.paths import ROOT, STATE
from scripts.research_v8.registry import FIELDS, append_event

PARENT = '1b3987e77854940a043b35b52e928d615ef739bc'
STEM = 'DONCHIAN_REENTRY10_20261005_V3'
parser = argparse.ArgumentParser()
parser.add_argument('action', choices=('close', 'post'))
parser.add_argument('--remote-head')
args = parser.parse_args()
assert os.environ['COIN_TASK_ID']

def read(p): return json.loads(Path(p).read_bytes())
def sha(p):
    with Path(p).open('rb') as stream: return hashlib.file_digest(stream, 'sha256').hexdigest()
def git(*a): return subprocess.check_output(['git', *a], cwd=ROOT, text=True).strip()
def save(p, value):
    with Path(p).open('x') as stream: json.dump(value, stream, indent=2, ensure_ascii=False); stream.write('\n')

proof = ROOT/'reports/GITHUB_DONCHIAN_REENTRY10_SOURCE_BINDING_20261005_V2.json'
private = sha(ROOT/'state/dataset_lock.json')
assert private == '29d930063842e9b1666869b4e5f9e3c8cd629313e57b9dadc328c6131b92f45d'
if args.action == 'post':
    binding = read(proof)
    assert git('rev-parse','HEAD') == args.remote_head and git('rev-parse','HEAD~1') == PARENT
    assert not git('status','--porcelain=v1','--untracked-files=no')
    assert sorted(git('ls-files','--others','--exclude-standard').splitlines()) == sorted(binding['prior_WIP_preserved'])
    for name, digest in binding['source_hashes'].items(): assert sha(ROOT/name) == digest, name
    gate = ROOT/'reports/GITHUB_DONCHIAN_REENTRY10_STAGED_GATE_20261005_V2.json'
    assert read(gate)['status'] == 'STAGED_MODULE_CHECKPOINT_PASS'
    tasks = [read(p) for p in (STATE/'task-progress').glob('task-*.json')]
    roles = {}
    for role, title in dict(CLOSE='D070恢复再入场实际验收与来源保存', GATE='D070提交前源码与敏感信息门槛',
            COMMIT='D070恢复再入场完整经济对照正常提交', PUSH='D070已验收恢复再入场模块推送GitHub', REMOTE='D070精确核对远端main提交').items():
        found = [t for t in tasks if t['title'] == title]; assert len(found) == 1
        t = found[0]; assert t['status'] == 'completed' and t['exit_code'] == 0 and t['ended_at']
        roles[role] = t
    output = ROOT/'reports/GITHUB_DONCHIAN_REENTRY10_SYNC_VERIFIED_20261005_V2.json'
    save(output, dict(status='PUSHED_AND_EXACT_REMOTE_MAIN_VERIFIED', local_HEAD=args.remote_head,
        remote_main=args.remote_head, parent_commit=PARENT, remote='https://github.com/snowycat1234/coin.git',
        closed_actual_roles=roles, source_binding_sha256=sha(proof), staged_gate_sha256=sha(gate),
        preserved_untracked_paths=binding['prior_WIP_preserved'], tracked_worktree_clean=True,
        private_SHA_only=private, private_body_read=False, force_push=False, orders_sent=0, locked_consumed=False,
        own_artifact_untracked_until_next_normal_module=True, created_utc=datetime.now(UTC).isoformat()))
    print(json.dumps(dict(path=str(output), sha256=sha(output), remote_main=args.remote_head)))
    raise SystemExit

assert git('rev-parse','HEAD') == PARENT
prior = ROOT/'reports/GITHUB_DONCHIAN_EXIT_WAIT_SYNC_VERIFIED_20261005_V1.json'
assert sha(prior) == '30994d75f9b47134d551166eb5d8278e2a3244ec3aaa2aa58108658488d0f2a6'
wip = read(prior)['preserved_untracked_paths']; assert len(wip) == 36
p = read(ROOT/'protocols'/(STEM+'.json'))
a = read(ROOT/'reports/fast_research'/(STEM+'.json'))
f = read(ROOT/'reports/fast_research'/(STEM+'_FINANCIAL_V6.json'))
diag = ROOT/'reports/fast_research'/(STEM+'_DIAGNOSTIC_V6.json'); d = read(diag)
assert a['completed_cases'] == a['complete_calendar_cases'] == f['financial_case_calls'] == 4
assert f['status'].startswith('PASS_CONFIGURED_N_')
assert d['status'] == 'COMPLETE_REENTRY10_SAVED_PAIRED_DIAGNOSTIC_NOT_APR' and len(d['paired_cases']) == 4
for name, digest in p['source_hashes'].items():
    archived='docs/archive/DONCHIAN_REENTRY10_PRE_COMPACT_FINANCIAL_SOURCE_20261005_V1.py' if name=='scripts/investment/multi_asset_financial_audit.py' else name
    assert sha(ROOT/archived)==digest,name
for case in a['cases']:
    for item in case['artifacts'].values(): assert sha(item['path']) == item['sha256']
reviews = [ROOT/'reports/DONCHIAN_REENTRY10_INDEPENDENT_REVIEW_20261005_V1.md',
           ROOT/'reports/DONCHIAN_REENTRY10_COST_SCOPE_REVIEW_20261005_V1.md']
assert all(path.is_file() for path in reviews)
resource = read(ROOT/'reports/DONCHIAN_REENTRY10_RESOURCE_20261005_V2.json')
assert resource['status'] == 'PASS_EXISTING_PHYSICAL_DISK_GUARD_NOT_ECONOMIC_PROOF'
rejection = read(ROOT/'reports/DONCHIAN_REENTRY10_PREPARATION_BINDING_REJECTION_20261005_V1.json')
for ident, path, status in [
    ('D070-PREPARATION-V1:REJECTED', 'reports/DONCHIAN_REENTRY10_PREPARATION_BINDING_REJECTION_20261005_V1.json', 'SOURCE_BINDING_REJECTED_PROCESS_EXIT0_TESTS0_MARKET0'),
    ('D070-FINANCIAL-BINDING-V5:FAILURE', 'reports/DONCHIAN_REENTRY10_FINANCIAL_SOURCE_BINDING_FAILURE_20261005_V5.json', 'FAILED_PLANNED_CHECKER_SOURCE_BINDING_INPUTS0_FINANCIAL0'),
    ('D070-FINANCIAL-BINDING-V4:FAILURE', 'reports/DONCHIAN_REENTRY10_FINANCIAL_SOURCE_BINDING_FAILURE_20261005_V4.json', 'FAILED_OLD_CHECKER_SOURCE_BINDING_INPUTS0_FINANCIAL0'),
    ('D070-FINANCIAL-OUTPUT-V3:FAILURE', 'reports/DONCHIAN_REENTRY10_FINANCIAL_OUTPUT_FAILURE_20261005_V3.json', 'FAILED_REPORT_2MB_LIMIT_NOT_FINANCIAL_ACCEPTANCE'),
    ('D070-POOL-CLI-V2:DIAGNOSIS', 'reports/DONCHIAN_REENTRY10_POOL_INVOCATION_FAILURE_20261005_V2.json', 'OWN_MISLAUNCH_INTERRUPTED_SIGINT_EXIT_MINUS2_TWO_ASSET_NOT_TEN_RESULT')]:
    event = dict.fromkeys(FIELDS)
    event.update(event_id=ident, event_type='OPERATIONAL_FAILURE_DIAGNOSIS', experiment_id='D070-REENTRY10-20261005',
        git_commit=PARENT, data_manifest_hash='NO_NEW_DATA_OR_QA', protocol_hash=sha(ROOT/'protocols'/(STEM+'.json')),
        model_family='NONE', fits=0, all_folds='NO_VALID_TEN_ACCOUNT_RESULT_IN_THIS_EVENT', success_failure=status,
        artifact_path=path, artifact_sha256=sha(ROOT/path), reason_for_next_experiment='Preserve actual preparation/CLI errors; one unchanged scientific recipe with explicit ten-pool invocation',
        result_influenced_later_choice='INVOCATION_CORRECTION_ONLY_NOT_PARAMETER_SEARCH')
    append_event(ROOT/'reports/experiment_registry.jsonl', event)
dest = ROOT/'docs/archive/DONCHIAN_REENTRY10_TASK_METADATA_20261005_V2'; dest.mkdir()
roles = {}
for path in (STATE/'task-progress').glob('task-*.json'):
    t = read(path)
    if not t['title'].startswith('D070') or t['id'] == os.environ['COIN_TASK_ID']: continue
    assert t['ended_at'] and (t['exit_code'] == 0 and t['status'] == 'completed' or t['id'] == '31b55392af8c4ffca669683c1167cacf' and t['exit_code'] == -2 and t['status'] == 'failed' or t['id'] in ('00d746b7f6044411a289545ad33a6ca7','0d9095813e634f28bc9e31bc8a6ffa9c','057725d9898149e3a9c009fae76cc55d') and t['exit_code']==1 and t['status']=='failed')
    shutil.copyfile(path, dest/path.name)
    roles[t['id']] = dict(title=t['title'], status=t['status'], actual_exit_code=t['exit_code'],
        task_archive=(dest/path.name).relative_to(ROOT).as_posix(), sha256=sha(dest/path.name))
assert roles['94f444f5d69e4a7db85bc12e21d093de']['actual_exit_code'] == 0
for folder in STATE.glob('d070-*'):
    if not folder.is_dir(): continue
    for name in ('RUN_BINDING.json','ACTUAL_BINDING.json','junit.xml'):
        path = folder/name
        if path.is_file(): shutil.copyfile(path, dest/(folder.name+'-'+name))
independent = STATE/'d070-reentry10-independent-20261005-v1'
for name in ('independent_review.py','result.json'):
    path = independent/name
    assert path.is_file() and path.stat().st_size < 50000
    shutil.copyfile(path, dest/('independent-'+name))
independent_value = read(independent/'result.json')
assert independent_value['status']=='PASS_SAVED_REPORT_DECODE_AND_DECIMAL_BRIDGES_ONLY'
assert independent_value['logical_rows']==3030 and independent_value['repacked_exact'] is True
assert roles[independent_value['task_id']]['actual_exit_code']==0
event = dict.fromkeys(FIELDS)
event.update(event_id='D070-INDEPENDENT-DECODE:RESULT',event_type='OPERATIONAL_RESEARCH_RESULT',
    experiment_id='D070-REENTRY10-20261005',git_commit=PARENT,data_manifest_hash=p['data_manifest']['sha256'],
    protocol_hash=sha(ROOT/'protocols'/(STEM+'.json')),model_family='NONE',fits=0,
    all_folds='SAVED_REPORT_ONLY_NO_NEW_MARKET',success_failure=independent_value['status'],
    artifact_path=(dest/'independent-result.json').relative_to(ROOT).as_posix(),artifact_sha256=sha(dest/'independent-result.json'),
    reason_for_next_experiment='Confirm lossless witness output and saved monetary bridges without replay',
    result_influenced_later_choice='RETAIN_ORIGINAL_REENTRY20_PAUSE_FIXED_REENTRY10')
append_event(ROOT/'reports/experiment_registry.jsonl',event)
selected = {'scripts/investment/donchian_daily_pool_target.py','scripts/investment/public_sma_perpetual.py',
    'scripts/investment/multi_asset_portfolio.py','scripts/investment/multi_asset_financial_audit.py','tests/test_donchian_reentry_period.py',
    'README.md','AGENTS.md','docs/RESEARCH_STATUS.md','docs/RESEARCH_DECISION_LOG.md','docs/GOALS.md','docs/PROGRESS.md',
    'docs/FAST_RESEARCH_TASK_CHECKLIST.md','docs/MULTI_ASSET_PORTFOLIO_20261004.md','docs/OPEN_SOURCE_REGISTRY.md',
    'reports/experiment_registry.jsonl', prior.relative_to(ROOT).as_posix()}
for folder in ('docs','docs/archive','reports','reports/fast_research','protocols'):
    selected.update(path.relative_to(ROOT).as_posix() for path in (ROOT/folder).glob('DONCHIAN_REENTRY10_*') if path.is_file())
selected.update(path.relative_to(ROOT).as_posix() for path in dest.iterdir())
assert not set(wip).intersection(selected)
owned = sum(path.stat().st_size for run in STATE.glob('d070-*') if run.is_dir() for path in run.rglob('*') if path.is_file())
assert owned < 800000000
save(proof, dict(status='D070_FINITE_REENTRY_CHANGE_FULL_ECONOMIC_ACCEPTANCE_NOT_APR', task_id=os.environ['COIN_TASK_ID'],
    parent_commit=PARENT, created_utc=datetime.now(UTC).isoformat(), source_hashes={n:sha(ROOT/n) for n in sorted(selected)},
    selected_module_paths=sorted(selected), prior_WIP_preserved=wip, closed_actual_roles=roles, private_SHA_only=private,
    private_body_read=False, owned_d070_STATE_bytes=owned, new_market_accounts=4, saved_control_accounts=4, financial_calls=4, failed_output_attempt_account_calls=4, total_reference_calls_including_failed_output_attempt=8,
    paired_cases=4, mislaunch_saved_two_asset_accounts=2, mislaunch_interrupted_additional_account_prefix=True, total_new_completed_market_accounts_including_mislaunch=6, HPO=0, models_fit=0, new_QA=0, new_downloads=0, preparation_V1_rejected_before_any_test_or_market=True,
    preparation_V1_actual_process_exit=0, diagnostic_sha256=sha(diag), independent_review_sha256=sha(reviews[0]),
    investment='CASH', candidate='NONE', long_term_APR='NOT_EVALUABLE', orders_sent=0))
print(json.dumps(dict(output=str(proof), sha256=sha(proof), selected_paths=len(selected), owned_STATE_bytes=owned)))
