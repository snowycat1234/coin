"""Close the completed experiment from small metadata; no market replay."""
import hashlib
import json
import os
import subprocess
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path('/mnt/d/codex/coin')
STATE = Path('/home/xflops/coin-state')
PARENT = 'bbb2d8dd943c4830579f79e5aa01bc8799b7a904'
PREFIX = 'TURTLE_EXACT_QUANTITY_'
DEST = ROOT/'docs/archive/TURTLE_EXACT_QUANTITY_RELEASE_METADATA_20261004_V1'

def sha(p):
    with p.open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()

def read(p):
    assert p.is_file() and not p.is_symlink() and p.stat().st_size <= 2_000_000
    return json.loads(p.read_bytes())

def archive(p, name):
    read(p)
    with (DEST/name).open('xb') as f:
        f.write(p.read_bytes())
    assert sha(p) == sha(DEST/name)

assert os.environ['COIN_TASK_ID']
assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()==PARENT
spec=read(ROOT/'protocols/TURTLE_EXACT_QUANTITY_RESEARCH_20261004_V1.json')
for name,h in spec['source_hashes'].items():
    assert sha(ROOT/name)==h
DEST.mkdir()
roles={
 'SYNTHETIC':('reports/fast_research/TURTLE_EXACT_QUANTITY_SYNTHETIC_20261004_V1.json',
              'PASS_BOUNDED_RESEARCH_TESTS_SYNTHETIC_NOT_MARKET_RESULT'),
 'PAIRED':('reports/fast_research/TURTLE_EXACT_QUANTITY_PAIRED_20261004_V1.json',
           'COMPLETE_D060_SAME_LOOP_NO_ADD_ECONOMIC_COMPARISON_NOT_APR'),
 'FINAL_DISK':('reports/TURTLE_EXACT_QUANTITY_FINAL_RESOURCE_20261004_V1.json',
               'PASS_EXISTING_FINAL_PHYSICAL_FILE_GUARD_NOT_MARKET_REPLAY')}
for v in ('PYRAMID4','SINGLE_LAYER'):
    roles[v]=(f'reports/fast_research/TURTLE_EXACT_QUANTITY_{v}_303D_20261004_V1.json',
              'COMPLETE_D060_FOUR_FIXED303D_TURTLE_VARIANT_NOT_NATIVE_OR_APR')
    roles[v+'_FINANCIAL']=(f'reports/fast_research/TURTLE_EXACT_QUANTITY_{v}_FINANCIAL_20261004_V1.json',
                          'PASS_D060_FOUR_RECORDED_TURTLE_VARIANT_ACCOUNTING_NOT_NATIVE_OR_APR')
proofs={}; values={}; cash=ratio=0.
for role,(name,status) in roles.items():
    r=read(ROOT/name); assert r['status']==status
    ident=r['binding']['task_id'] if 'binding' in r else r['task_id']
    p=STATE/'task-progress'/('task-'+ident+'.json'); t=read(p)
    assert t['id']==ident and t['status']=='completed' and t['exit_code']==0 and t['ended_at']
    archive(p,role+'-TASK.json')
    proofs[role]=dict(path=name,sha256=sha(ROOT/name),task_id=ident,actual_exit_code=0,
        task_archive=str((DEST/(role+'-TASK.json')).relative_to(ROOT)),task_sha256=sha(p))
    values[role]=(r,t)
    if r.get('run_dir'):
        owner=Path(r['run_dir']); assert owner.parent==STATE and not owner.is_symlink()
        for filename in ('RUN_BINDING.json','ACTUAL_BINDING.json'):
            if (owner/filename).exists(): archive(owner/filename,role+'-'+filename)
for v in ('PYRAMID4','SINGLE_LAYER'):
    r,t=values[v]; a,at=values[v+'_FINANCIAL']
    assert r['completed_cases']==4 and r['source_bytes_unchanged'] and r['actual_calendar_days']==303
    assert r['binding']['source_hashes']==spec['source_hashes'] and r['owned_bytes']<=250000000
    assert r['peak_RSS_bytes']<=3000000000 and r['elapsed_seconds']<=1800
    assert all(c['summary']['completed_minutes']==c['summary']['required_minutes']==436320
        and c['summary']['daily_metrics']['days']==303 and c['summary']['terminal_cash_realized']
        and all(float(p['quantity'])==0 for p in c['summary']['positions'].values()) for c in r['cases'])
    assert a['completed_full_calendar_cases_verified']==a['financial_case_calls']==4
    assert a['tolerances']==dict(cash_USDT=1e-7,ratio=1e-10)
    assert a['actual_report_sha256']==proofs[v]['sha256'] and t['ended_at']<=at['started_at']
    cash=max(cash,a['maximum_errors']['cash']);ratio=max(ratio,a['maximum_errors']['ratio'])
    assert at['ended_at']<=values['PAIRED'][1]['started_at']
assert cash<=1e-7 and ratio<=1e-10
assert len(values['PAIRED'][0]['pairs'])==4
for p in values['PAIRED'][0]['pairs']:
    assert p['delta']['net_PnL']<0 and p['treatment_order_diagnostic']['mapping']['UNKNOWN_legs']==0
    assert p['realized_risk_matched'] is False
failed={}
for ident in ('1691a38d820c45278aba1d3519b07c38','4516588eb9f8421782c4856476f3d28d'):
    p=STATE/'task-progress'/('task-'+ident+'.json');t=read(p)
    assert t['status']=='failed' and t['exit_code']==1 and t['ended_at']
    archive(p,'IMPORT_FAILED-'+ident+'-TASK.json')
    failed[ident]=dict(actual_exit_code=1,financial_calls=0,reason='Import failure before checker main; explicit child PYTHONPATH fixed',
        task_archive=str((DEST/('IMPORT_FAILED-'+ident+'-TASK.json')).relative_to(ROOT)))
assert sha(ROOT/'state/dataset_lock.json')=='29d930063842e9b1666869b4e5f9e3c8cd629313e57b9dadc328c6131b92f45d'
source=ROOT/'.cache/d061_release.py'
with (ROOT/'docs/archive/TURTLE_EXACT_QUANTITY_RELEASE_SOURCE_20261004_V1.py').open('xb') as f:
    f.write(source.read_bytes())
selected=set(spec['source_hashes'])
selected.update({'README.md','docs/GOALS.md','docs/PROGRESS.md','docs/RESEARCH_STATUS.md',
    'docs/MULTI_ASSET_PORTFOLIO_20261004.md','docs/RESEARCH_DECISION_LOG.md','docs/OPEN_SOURCE_REGISTRY.md','reports/experiment_registry.jsonl',
    'reports/GITHUB_TURTLE_NO_ADD_SYNC_VERIFIED_20261004_V1.json'})
for folder in ('protocols','reports/fast_research','reports','docs/archive'):
    selected.update(str(p.relative_to(ROOT)) for p in (ROOT/folder).glob(PREFIX+'*') if p.is_file())
selected.update(str(p.relative_to(ROOT)) for p in DEST.iterdir())
owned=sum(p.stat().st_size for d in STATE.glob('d061-*') if d.is_dir() for p in d.rglob('*') if p.is_file())
assert owned<=700000000
result=dict(status='CURRENT_MODULE_EXISTING_ACTUAL_ACCEPTANCE_BINDING_NOT_NEW_MARKET_REPLAY',
    parent_commit=PARENT,source_hashes={p:sha(ROOT/p) for p in sorted(selected)},selected_module_paths=sorted(selected),
    closed_actual_roles=proofs,failed_launcher_roles=failed,wrapper_argument_errors_without_task=2,
    complete_new_account_cases=8,independent_complete_financial_calls=8,paired_cases=4,calendar_days=303,
    owned_STATE_bytes=owned,maximum_cash_error_USDT=cash,maximum_ratio_error=ratio,
    market_payload_read_or_hashed=False,private_SHA_only=True,models_fit=0,HPO=0,orders_sent=0,
    locked_consumed=False,candidate='NONE',investment='CASH',long_term_APR='NOT_EVALUABLE',
    created_utc=datetime.now(UTC).isoformat())
out=ROOT/'reports/GITHUB_TURTLE_EXACT_QUANTITY_SOURCE_BINDING_20261004_V1.json'
with out.open('x') as f:
    json.dump(result,f,indent=2,allow_nan=False);f.write('\n')
print(json.dumps(dict(output=str(out),sha256=sha(out),selected_paths=len(selected),owned_STATE_bytes=owned)),flush=True)
