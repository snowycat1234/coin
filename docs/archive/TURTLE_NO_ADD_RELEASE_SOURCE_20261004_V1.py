"""Save actual closed small D060 evidence and current byte pins for module Git."""
from datetime import UTC, datetime
import hashlib
import json
import os
from pathlib import Path
import subprocess

ROOT=Path('/mnt/d/codex/coin'); STATE=Path('/home/xflops/coin-state')
PARENT='8288569c4ff673ebab3161ba17782ccec69c3411'
PREFIX='TURTLE_NO_ADD_'; DEST=ROOT/'docs/archive/TURTLE_NO_ADD_RELEASE_METADATA_20261004_V1'
def sha(p):
    with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def read(p):
    assert p.is_file() and not p.is_symlink() and p.stat().st_size<=2_000_000
    return json.loads(p.read_bytes())
def copy(p,name):
    assert p.is_file() and not p.is_symlink() and p.stat().st_size<=2_000_000
    d=DEST/name
    with d.open('xb') as f:f.write(p.read_bytes())
    assert sha(p)==sha(d)
def closed(id,exit=0):
    p=STATE/'task-progress'/('task-'+id+'.json');t=read(p)
    assert t['id']==id and t['status']==('completed' if exit==0 else 'failed') and t['exit_code']==exit and t['ended_at']
    return p,t
assert os.environ['COIN_TASK_ID'] and subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()==PARENT
spec=read(ROOT/'protocols/TURTLE_NO_ADD_RESEARCH_20261004_V1.json')
for p,h in spec['source_hashes'].items(): assert sha(ROOT/p)==h
roles={
 'SYNTHETIC':('reports/fast_research/TURTLE_NO_ADD_SYNTHETIC_20261004_V1.json','PASS_BOUNDED_RESEARCH_TESTS_SYNTHETIC_NOT_MARKET_RESULT'),
 'PYRAMID4':('reports/fast_research/TURTLE_NO_ADD_PYRAMID4_303D_20261004_V1.json','COMPLETE_D060_FOUR_FIXED303D_TURTLE_VARIANT_NOT_NATIVE_OR_APR'),
 'MIGRATION':('reports/fast_research/TURTLE_NO_ADD_MIGRATION_20261004_V1.json','PASS_D060_DEFAULT_SEMANTIC_MIGRATION_NOT_NEW_ALPHA'),
 'SINGLE_LAYER_FAILED':('reports/fast_research/TURTLE_NO_ADD_SINGLE_LAYER_303D_20261004_V1.json','FAILED_D060_TURTLE_VARIANT'),
 'PYRAMID4_FINANCIAL':('reports/fast_research/TURTLE_NO_ADD_PYRAMID4_FINANCIAL_20261004_V2.json','PASS_D060_FOUR_RECORDED_TURTLE_VARIANT_ACCOUNTING_NOT_NATIVE_OR_APR'),
 'FAILED_PREFIX_FINANCIAL':('reports/fast_research/TURTLE_NO_ADD_FAILED_PREFIX_DIAGNOSIS_20261004_V1.json','PASS_D060_FAILED_PREFIX_RECORDED_FINANCE_AND_CAPACITY_DIAGNOSIS_NOT_FULL_PERIOD_COMPARE'),
 'RAW_TRACE':('reports/fast_research/TURTLE_NO_ADD_ZERO_LIQUIDITY_RAW_TRACE_20261004_V1.json','PASS_D060_FIVE_ZERO_LIQUIDITY_ROWS_RAW_NORMALIZED_SOURCE_TRACE_NOT_FULL_QA'),
 'RISK_COUNTEREXAMPLE':('reports/fast_research/TURTLE_NO_ADD_RISK_ROUNDTRIP_COUNTEREXAMPLE_20261004_V1.json','CONFIRMED_D060_SAME_WEIGHT_DECIMAL_ROUNDTRIP_SPURIOUS_RISK_REDUCTION'),
 'FINAL_DISK':('reports/TURTLE_NO_ADD_FINAL_RESOURCE_20261004_V1.json','PASS_EXISTING_FINAL_PHYSICAL_FILE_GUARD_NOT_MARKET_REPLAY')}
DEST.mkdir(); proofs={}; reports={}; cash=ratio=0.
for role,(name,status) in roles.items():
    r=read(ROOT/name);assert r['status']==status
    id=r['binding']['task_id'] if 'binding' in r else r['task_id']
    exit=1 if role=='SINGLE_LAYER_FAILED' else 0; p,t=closed(id,exit);copy(p,role+'-TASK.json')
    proof=dict(path=name,sha256=sha(ROOT/name),task_id=id,actual_exit_code=exit,
               task_archive=str((DEST/(role+'-TASK.json')).relative_to(ROOT)),task_sha256=sha(p))
    if r.get('run_dir'):
        owner=Path(r['run_dir']);assert owner.parent==STATE and not owner.is_symlink()
        for filename in ('RUN_BINDING.json','ACTUAL_BINDING.json'):
            q=owner/filename
            if q.exists():copy(q,role+'-'+filename)
    if role=='PYRAMID4':
        assert r['completed_cases']==4 and r['actual_calendar_days']==303 and r['source_bytes_unchanged']
        assert r['binding']['source_hashes']==spec['source_hashes'] and r['owned_bytes']<=250000000
        assert r['peak_RSS_bytes']<=3000000000 and r['elapsed_seconds']<=1800
        assert all(c['summary']['completed_minutes']==c['summary']['required_minutes']==436320 and
                   c['summary']['daily_metrics']['days']==303 for c in r['cases'])
    if role=='PYRAMID4_FINANCIAL':
        assert r['completed_cases_verified']==r['completed_full_calendar_cases_verified']==r['financial_case_calls']==4
        assert r['tolerances']==dict(cash_USDT=1e-7,ratio=1e-10)
        cash=max(cash,r['maximum_errors']['cash']);ratio=max(ratio,r['maximum_errors']['ratio'])
        assert cash<=1e-7 and ratio<=1e-10
    if role=='MIGRATION':assert len(r['pairs'])==4
    proofs[role]=proof;reports[role]=(r,t)
for variant in ('PYRAMID4',):
    main,t=reports[variant]; audit,at=reports[variant+'_FINANCIAL']
    assert audit['actual_report_sha256']==proofs[variant]['sha256'] and t['ended_at']<=at['started_at']
    assert audit['variant']==variant and audit['allow_pyramiding']==(variant=='PYRAMID4')
assert reports['MIGRATION'][1]['ended_at']<=reports['SINGLE_LAYER_FAILED'][1]['started_at']
assert reports['FAILED_PREFIX_FINANCIAL'][0]['binding']['actual_report_sha256']==proofs['SINGLE_LAYER_FAILED']['sha256']
assert reports['FAILED_PREFIX_FINANCIAL'][0]['complete_calendar'] is False and reports['FAILED_PREFIX_FINANCIAL'][0]['financial_calls']==1
assert sha(ROOT/'state/dataset_lock.json')=='29d930063842e9b1666869b4e5f9e3c8cd629313e57b9dadc328c6131b92f45d'
for p in (ROOT/'.cache/d060_financial_plan.py',ROOT/'.cache/d060_release.py'):
    d=ROOT/'docs/archive'/('TURTLE_NO_ADD_'+('FINANCIAL_PLAN_SOURCE_20261004_V2' if 'financial_plan' in p.name else 'RELEASE_SOURCE_20261004_V1')+'.py')
    with d.open('xb') as f:f.write(p.read_bytes())
selected=set(spec['source_hashes'])
for variant in ('PYRAMID4',):
    for p,h in reports[variant+'_FINANCIAL'][0]['binding']['source_hashes'].items():
        assert sha(ROOT/p)==h;selected.add(p)
failed=read(ROOT/'reports/fast_research/TURTLE_NO_ADD_PYRAMID4_FINANCIAL_20261004_V1.json')
assert failed['status']=='FAIL_D060_RECORDED_TURTLE_VARIANT_ACCOUNTING' and failed['completed_cases_verified']==0
ft=STATE/'task-progress'/('task-'+failed['binding']['task_id']+'.json');value=read(ft)
assert value['status']=='failed' and value['exit_code']==1 and value['ended_at']
copy(ft,'PYRAMID4_FINANCIAL_FAILED_BINDING-TASK.json')
proofs['PYRAMID4_FINANCIAL_FAILED_BINDING']=dict(task_id=value['id'],actual_exit_code=1,
    report_sha256=sha(ROOT/'reports/fast_research/TURTLE_NO_ADD_PYRAMID4_FINANCIAL_20261004_V1.json'),
    completed_financial_calls=0,task_archive=str((DEST/'PYRAMID4_FINANCIAL_FAILED_BINDING-TASK.json').relative_to(ROOT)))
selected|={'README.md','docs/GOALS.md','docs/PROGRESS.md','docs/RESEARCH_STATUS.md',
 'docs/MULTI_ASSET_PORTFOLIO_20261004.md','docs/RESEARCH_DECISION_LOG.md','docs/OPEN_SOURCE_REGISTRY.md','reports/experiment_registry.jsonl',
 'reports/GITHUB_RSI2_SELECTIVE_SHORT_SYNC_VERIFIED_20261004_V1.json'}
for folder in ('protocols','reports/fast_research','reports','docs/archive'):
    for p in (ROOT/folder).glob(PREFIX+'*'):
        if p.is_file():selected.add(str(p.relative_to(ROOT)))
selected|={str(p.relative_to(ROOT)) for p in DEST.iterdir()}
pins={p:sha(ROOT/p) for p in sorted(selected)}
owned=sum(p.stat().st_size for d in STATE.glob('d060-*') if d.is_dir() for p in d.rglob('*') if p.is_file())
assert owned<=700000000
result=dict(status='CURRENT_MODULE_EXISTING_ACTUAL_ACCEPTANCE_BINDING_NOT_NEW_MARKET_REPLAY',
 parent_commit=PARENT,source_hashes=pins,selected_module_paths=sorted(selected),closed_actual_roles=proofs,
 attempted_new_account_cases=5,complete_new_account_cases=4,incomplete_new_account_cases=1,unrun_treatment_cases=3,independent_cases=5,complete_independent_cases=4,prefix_independent_cases=1,control_calendar_days=303,full_period_treatment_delta='NOT_EVALUABLE',owned_STATE_bytes=owned,
 maximum_cash_error_USDT=cash,maximum_ratio_error=ratio,private_lock_SHA_only=True,
 market_artifacts_read_or_hashed_by_export=False,models_fit=0,HPO=0,orders_sent=0,locked_consumed=False,
 candidate='NONE',investment='CASH',long_term_APR='NOT_EVALUABLE',created_utc=datetime.now(UTC).isoformat())
out=ROOT/'reports/GITHUB_TURTLE_NO_ADD_SOURCE_BINDING_20261004_V1.json'
with out.open('x') as f:json.dump(result,f,indent=2,allow_nan=False);f.write('\n')
print(json.dumps(dict(output=str(out),sha256=sha(out),selected_paths=len(selected),owned_STATE_bytes=owned)),flush=True)
