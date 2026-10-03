"""Close actual D048 roles and byte identities; no market/ledger replay."""
import hashlib,json,os,subprocess,sys
from datetime import UTC,datetime
from pathlib import Path
from quant import resources
ROOT=Path('/mnt/d/codex/coin');STATE=Path('/home/xflops/coin-state')
ARCHIVE='docs/archive/CLOSING_EXEMPT_ROOT_CLOSE_SOURCE_20261003_V1.py'
def sha(p):
    with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def read(p):
    p=Path(p);assert not p.is_symlink() and p.stat().st_size<2_000_000
    return json.loads(p.read_bytes())
def write(p,v):
    with Path(p).open('x') as f:json.dump(v,f,indent=2,ensure_ascii=False,allow_nan=False);f.write('\n')
def closed(identity,code=0):
    p=STATE/'task-progress'/('task-'+identity+'.json');t=read(p)
    assert t['id']==identity and t['exit_code']==code and t['status']==('completed' if code==0 else 'failed')
    return dict(path=str(p),sha256=sha(p),task=t)
assert os.environ.get('COIN_TASK_ID') and sys.prefix==str(STATE/'v8-clean-env-20261002-v2')
assert sha(__file__)==sha(ROOT/ARCHIVE)
assert sha(ROOT/'state/dataset_lock.json')=='29d930063842e9b1666869b4e5f9e3c8cd629313e57b9dadc328c6131b92f45d'
paths=dict(synthetic='reports/fast_research/PERPETUAL_CLOSING_EXEMPT_SMOKE_20261003_V1.json',
    before_results='reports/fast_research/CLOSING_EXEMPT_RESEARCH_BEFORE_RESULTS_20261003_V1.json',
    market='reports/fast_research/CLOSING_EXEMPT_RESEARCH_ACTUAL_20261003_V1.json',
    finance='reports/fast_research/CLOSING_EXEMPT_FINANCIAL_INDEPENDENT_20261003_V2.json',
    comparison='reports/fast_research/CLOSING_EXEMPT_SAVED_COMPARISON_20261003_V1.json')
values={role:read(ROOT/path) for role,path in paths.items()}
tasks={role:closed(value['binding']['task_id']) for role,value in values.items()}
market,finance,comparison=values['market'],values['finance'],values['comparison']
assert market['completed_cases']==market['completed_full_calendar_cases']==len(market['cases'])==8
assert finance['financial_case_calls']==finance['completed_cases_verified']==finance['completed_full_calendar_cases_verified']==8
assert finance['status'].startswith('PASS_D048_EIGHT_RECORDED_CLOSING_EXEMPT')
assert all(c['summary']['completed_minutes']==c['summary']['required_minutes']==436320
    and c['summary']['completion']=='COMPLETE_CONDITIONAL_ACCOUNT'
    and c['summary']['terminal_cash_realized'] for c in market['cases'])
assert values['synthetic']['test_exit_code']==0 and values['synthetic']['source_bytes_unchanged']
assert finance['maximum_errors']['cash']<=1e-7 and finance['maximum_errors']['ratio']<=1e-10
derivation=finance['financial_derivation']['closing_filter_financial_journal_derivation']
assert derivation['number_of_changed_predicates']==1 and derivation['every_other_financial_statement_and_guard_AST_unchanged']
assert comparison['compared_new_cases']==8 and comparison['prior_full_cases']==1 and comparison['prior_prefix_cases_NOT_EVALUABLE']==3
assert len(comparison['groups'])==4 and all(g['Turtle_minus_HOLD']['scope']=='FULL_SEPARATE_ACCOUNTS' for g in comparison['groups'])
pins={path:sha(ROOT/path) for path in paths.values()}
for value in values.values():
    for name,digest in value['binding'].get('source_hashes',{}).items():
        assert name!='state/dataset_lock.json'
        p=Path(name) if name.startswith('/') else ROOT/name
        if not p.is_relative_to(ROOT):continue
        rel=p.relative_to(ROOT).as_posix()
        assert rel not in pins or pins[rel]==digest,rel
        assert sha(p)==digest,rel
        pins[rel]=digest
failures={}
for role,path in dict(spec_WSL='reports/fast_research/BYBIT_PUBLIC_SPEC_PROBE_20261003_V1.json',
    spec_HTTPS='reports/fast_research/BYBIT_PUBLIC_SPEC_PROBE_20261003_V2.json',
    independent_V1='reports/fast_research/CLOSING_EXEMPT_FINANCIAL_INDEPENDENT_20261003_V1.json').items():
    value=read(ROOT/path);failures[role]=dict(report=path,sha256=sha(ROOT/path),closed_task=closed(value['binding']['task_id'],1))
    pins[path]=sha(ROOT/path)
    if role.startswith('spec_'):assert not value['confirmed_current_profiles'] and len(value['requests'])==1
    if role=='spec_HTTPS':assert value['requests'][0]['http_status']==403
for pattern in ['docs/archive/CLOSING_EXEMPT*','docs/archive/PERPETUAL_CLOSING_EXEMPT*',
    'docs/archive/BYBIT_PUBLIC_SPEC*','protocols/CLOSING_EXEMPT*','protocols/PERPETUAL_CLOSING_EXEMPT*',
    'scripts/investment/closing_exempt*','scripts/investment/audit_closing_exempt*','scripts/investment/perpetual_closing_exempt*']:
    for p in ROOT.glob(pattern):
        if p.is_file():pins[p.relative_to(ROOT).as_posix()]=sha(p)
for name in [ARCHIVE,'docs/CLOSING_EXEMPT_RESEARCH_20261003.md','tests/test_perpetual_closing_exemption.py',
    'scripts/investment/bybit_public_spec_probe.py','scripts/investment/bybit_public_spec_probe_v2.py',
    'docs/archive/APPEND_ONLY_REGISTRY_GIT_PREFLIGHT_SOURCE_20261003_V2.py']:
    pins[name]=sha(ROOT/name)
original=subprocess.check_output(['git','show','HEAD:reports/experiment_registry.jsonl'],cwd=ROOT)
current=(ROOT/'reports/experiment_registry.jsonl').read_bytes()
assert current.startswith(original) and len(current)<=8_000_000
status=resources.status();assert status['ram_limit_bytes']<=5_000_000_000 and status['swap_bytes']==0
collector=subprocess.run(['ps','-p','540','-o','pid=,stat=,etime=,comm='],capture_output=True,text=True)
result=dict(status='PASS_D048_CLOSING_EXEMPT_CONDITIONAL_COMPARISON_NOT_NATIVE_OR_LONG_TERM_APR',
    binding=dict(task_id=os.environ['COIN_TASK_ID'],source_hashes=pins),
    own_completion='LIVE_CALLER_REQUIRES_EXTERNAL_TRUE_EXIT_CHECK',source_roles=paths,closed_role_tasks=tasks,
    failed_attempts_preserved=failures,full_new_accounts=8,new_financial_case_calls=8,
    prior_Turtle_full_cases=1,prior_Turtle_prefixes_NOT_EVALUABLE=3,
    adoption='CLOSING_SEMANTICS_CAPABILITY_AND_COMPLETE_PAIRED_RESEARCH',research_anchor='PAST_COVARIANCE_HOLD',
    investment='CASH_NONE',long_term_APR='NOT_EVALUABLE',native_filters_certified=False,
    complete_strategy_state_or_intent_oracle=False,old_QA_or_finance_replayed=False,market_arrays_read=False,
    registry_append_only=dict(committed_prefix_bytes=len(original),committed_prefix_sha256=hashlib.sha256(original).hexdigest(),
        preserved_exact_prefix=True,current_bytes=len(current),registry_blob_limit=8_000_000,other_blob_limit=4_000_000),
    latest_actual_disk_scan=market['disk'],measurement_before_subsequent_outputs=True,
    collector_read_only_snapshot=dict(exit_code=collector.returncode,output=collector.stdout.strip(),process_untouched=True),
    resources=status,orders_sent=0,locked_consumed=False,GPU=0,created_utc=datetime.now(UTC).isoformat())
out=ROOT/'reports/fast_research/CLOSING_EXEMPT_ROOT_ACCEPTANCE_20261003_V1.json'
write(out,result)
print(json.dumps(dict(status=result['status'],sha256=sha(out),pins=len(pins))))
