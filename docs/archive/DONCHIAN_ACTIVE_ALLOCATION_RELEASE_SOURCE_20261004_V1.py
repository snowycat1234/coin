"""Close D065 actual evidence and selected module sources without touching WIP."""
import hashlib, json, os, shutil, subprocess
from pathlib import Path
from datetime import UTC, datetime
from quant.paths import ROOT, STATE
from scripts.research_v8.registry import FIELDS, append_event
assert os.environ['COIN_TASK_ID']
PARENT='55798a1795b75c64b63c291a70fa5a84b357ce7f'
STEM='DONCHIAN_ACTIVE_ALLOCATION_20261004_V1'

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(Path(p).read_bytes())
assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()==PARENT
prior=ROOT/'reports/GITHUB_CONTINUOUS_DAILY_TREND_SYNC_VERIFIED_20261004_V1.json'
assert sha(prior)=='2e4b802179331e81d28077cf726d2a071e8944561675ac6b1bd25a81269e89ed'
wip=read(prior)['preserved_untracked_paths'];assert len(wip)==36
p=read(ROOT/'protocols'/(STEM+'.json'))
a=read(ROOT/'reports/fast_research'/(STEM+'.json'));f=read(ROOT/'reports/fast_research'/(STEM+'_FINANCIAL.json'))
rpath=ROOT/'reports/fast_research'/(STEM+'_DIAGNOSTIC.json');r=read(rpath)
assert a['complete_calendar_cases']==a['completed_cases']==f['financial_case_calls']==4
assert len(r['rows'])==8 and len(r['paired_cases'])==4 and r['same_signal_states_verified']
assert r['status']=='COMPLETE_ACTIVE_BUDGET_SAVED_PAIRED_DIAGNOSTIC_NOT_APR'
assert f['status'].startswith('PASS_CONFIGURED_N_')
for name,digest in p['source_hashes'].items():assert sha(ROOT/name)==digest,name
for c in a['cases']:
    for item in c['artifacts'].values():assert sha(item['path'])==item['sha256']
lock=sha(ROOT/'state/dataset_lock.json')
assert lock=='29d930063842e9b1666869b4e5f9e3c8cd629313e57b9dadc328c6131b92f45d'
dest=ROOT/'docs/archive/DONCHIAN_ACTIVE_ALLOCATION_TASK_METADATA_20261004_V1';dest.mkdir()
roles={}
for path in (STATE/'task-progress').glob('task-*.json'):
    t=read(path)
    if not t['title'].startswith('D065') or t['id']==os.environ['COIN_TASK_ID']:continue
    assert t['ended_at'] and t['exit_code'] in (0,1,2) and t['status']==('completed' if t['exit_code']==0 else 'failed')
    target=dest/path.name;shutil.copyfile(path,target)
    roles[t['id']]=dict(title=t['title'],status=t['status'],actual_exit_code=t['exit_code'],
        task_archive=target.relative_to(ROOT).as_posix(),sha256=sha(target))
assert roles['4334609c665c422c9a07116c304ac70b']['actual_exit_code']==1
failed=dict.fromkeys(FIELDS);failed.update(event_id='D065-FAILED-INLINE-FIXTURE:RESULT',
    event_type='OPERATIONAL_RESULT',experiment_id='D065-ACTIVE-ALLOCATION-INLINE-PROBE-20261004',
    git_commit=PARENT,data_manifest_hash='NONE_SYNTHETIC',protocol_hash='UNKNOWN_INLINE_NO_PROTOCOL',
    model_family='NONE',fits=0,all_folds='SYNTHETIC_ONLY',success_failure='FAILED_SYMBOL_IDENTITY_FIXTURE_NO_RETRY',
    artifact_path='reports/DONCHIAN_ACTIVE_ALLOCATION_FAILED_INLINE_PROBE_20261004_V1.md',
    artifact_sha256=sha(ROOT/'reports/DONCHIAN_ACTIVE_ALLOCATION_FAILED_INLINE_PROBE_20261004_V1.md'),
    reason_for_next_experiment='Retain actual failed inline probe; root substantive synthetic and full direct reference cover correctness',
    result_influenced_later_choice='NONE_NO_MARKET_ECONOMICS')
append_event(ROOT/'reports/experiment_registry.jsonl',failed)
assert roles['416d6729bb5f4fec903117ad57276b65']['actual_exit_code']==2
append_event(ROOT/'reports/experiment_registry.jsonl',dict(failed,
    event_id='D065-FINANCIAL-CLI-MISSING-ARGS:RESULT',experiment_id='D065-FINANCIAL-CLI-20261004',
    success_failure='FAILED_ARGPARSE_EXIT2_BEFORE_AUDIT_NO_LEDGER_REPLAY',
    reason_for_next_experiment='Preserve actual missing protocol/output CLI failure; corrected invocation keeps same audit inputs/math'))
for run in STATE.glob('d065-*'):
    if not run.is_dir():continue
    for name in ('RUN_BINDING.json','ACTUAL_BINDING.json','junit.xml'):
        path=run/name
        if path.is_file():shutil.copyfile(path,dest/(run.name+'-'+name))
selected={'scripts/investment/public_sma_perpetual.py','scripts/investment/donchian_daily_pool_target.py',
    'scripts/investment/multi_asset_financial_audit.py','scripts/investment/multi_asset_portfolio.py',
    'tests/test_donchian_active_allocation.py','reports/experiment_registry.jsonl',prior.relative_to(ROOT).as_posix(),
    'AGENTS.md','README.md','docs/RESEARCH_STATUS.md','docs/RESEARCH_DECISION_LOG.md',
    'docs/GOALS.md','docs/PROGRESS.md','docs/FAST_RESEARCH_TASK_CHECKLIST.md',
    'docs/MULTI_ASSET_PORTFOLIO_20261004.md','docs/OPEN_SOURCE_REGISTRY.md'}
for folder in ('protocols','reports','reports/fast_research','docs/archive'):
    selected.update(path.relative_to(ROOT).as_posix() for path in (ROOT/folder).glob('DONCHIAN_ACTIVE_ALLOCATION_*') if path.is_file())
selected.update(path.relative_to(ROOT).as_posix() for path in dest.iterdir())
assert not set(wip).intersection(selected)
owned=sum(path.stat().st_size for run in STATE.glob('d065-*') if run.is_dir() for path in run.rglob('*') if path.is_file())
assert owned<800000000
value=dict(status='D065_FINITE_ACTIVE_BUDGET_FULL_ACCOUNTS_AND_INDEPENDENT_ECONOMIC_ACCEPTANCE_NOT_APR',
    task_id=os.environ['COIN_TASK_ID'],parent_commit=PARENT,created_utc=datetime.now(UTC).isoformat(),
    source_hashes={name:sha(ROOT/name) for name in sorted(selected)},selected_module_paths=sorted(selected),
    closed_actual_roles=roles,prior_WIP_preserved=wip,private_SHA_only=lock,private_body_read=False,
    owned_d065_STATE_bytes=owned,new_market_accounts=4,saved_control_accounts=4,financial_calls=4,paired_cases=4,
    models_fit=0,HPO=0,new_downloads=0,new_QA=0,orders_sent=0,investment='CASH',candidate='NONE',
    long_term_APR='NOT_EVALUABLE',diagnostic_sha256=sha(rpath),
    independent_static_review_sha256=sha(ROOT/'reports/DONCHIAN_ACTIVE_ALLOCATION_INDEPENDENT_REVIEW_20261004_V1.md'))
out=ROOT/'reports/GITHUB_DONCHIAN_ACTIVE_ALLOCATION_SOURCE_BINDING_20261004_V1.json'
with out.open('x') as stream:json.dump(value,stream,indent=2);stream.write('\n')
print(json.dumps(dict(output=str(out),sha256=sha(out),selected_paths=len(selected),owned_STATE_bytes=owned)),flush=True)
