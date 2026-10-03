"""Close real D049 roles, exact sources and preserved failures; no replay."""
import hashlib,json,os,subprocess,sys
from datetime import UTC,datetime
from pathlib import Path
from quant import resources
ROOT=Path('/mnt/d/codex/coin'); STATE=Path('/home/xflops/coin-state')
ARCHIVE='docs/archive/TURTLE_DIRECTION_ROOT_CLOSE_SOURCE_20261003_V1.py'

def sha(path):
    with Path(path).open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()

def read(path):
    path=Path(path);assert not path.is_symlink() and path.stat().st_size<2_000_000
    return json.loads(path.read_bytes())

def write(path,value):
    with Path(path).open('x') as stream:
        json.dump(value,stream,indent=2,ensure_ascii=False,allow_nan=False);stream.write('\n')

def closed(identity,code=0):
    path=STATE/'task-progress'/('task-'+identity+'.json');task=read(path)
    assert task['id']==identity and task['exit_code']==code and task['status']==('completed' if code==0 else 'failed')
    return dict(path=str(path),sha256=sha(path),task=task)

assert os.environ.get('COIN_TASK_ID') and sys.prefix==str(STATE/'v8-clean-env-20261002-v2')
assert sha(__file__)==sha(ROOT/ARCHIVE)
assert sha(ROOT/'state/dataset_lock.json')=='29d930063842e9b1666869b4e5f9e3c8cd629313e57b9dadc328c6131b92f45d'
paths=dict(synthetic='reports/fast_research/TURTLE_DIRECTION_SMOKE_20261003_V2.json',
    before_results='reports/fast_research/TURTLE_DIRECTION_BEFORE_RESULTS_20261003_V1.json',
    market='reports/fast_research/TURTLE_DIRECTION_ABLATION_ACTUAL_20261003_V1.json',
    finance='reports/fast_research/TURTLE_DIRECTION_FINANCIAL_INDEPENDENT_20261003_V1.json',
    comparison='reports/fast_research/TURTLE_DIRECTION_SAVED_COMPARISON_20261003_V1.json')
values={role:read(ROOT/path) for role,path in paths.items()}
tasks={role:closed(value['binding']['task_id']) for role,value in values.items()}
market,finance,comparison=values['market'],values['finance'],values['comparison']
assert market['completed_cases']==len(market['cases'])==8
assert finance['financial_case_calls']==finance['completed_cases_verified']==8
assert finance['status']=='PASS_D049_EIGHT_RECORDED_TURTLE_DIRECTION_ACCOUNTING_NOT_NATIVE_FILTERS_OR_LONG_TERM_APR'
full=market['completed_full_calendar_cases']
assert finance['completed_full_calendar_cases_verified']==full
assert all(case['summary']['required_minutes']==436320 for case in market['cases'])
assert values['synthetic']['test_exit_code']==0 and values['synthetic']['source_bytes_unchanged']
assert finance['maximum_errors']['cash']<=1e-7 and finance['maximum_errors']['ratio']<=1e-10
proof=finance['financial_derivation']
assert proof['additional_open_leg_direction_check'] is True
assert proof['closing_filter_financial_journal_derivation']['every_other_financial_statement_and_guard_AST_unchanged']
assert comparison['new_accounts_referenced']==comparison['saved_D048_accounts_referenced']==8
assert len(comparison['groups'])==4 and comparison['market_ledger_IO'] is False and comparison['selected_direction_or_unit'] is False
assert tasks['synthetic']['task']['ended_at']<=tasks['before_results']['task']['started_at']
assert tasks['before_results']['task']['ended_at']<=tasks['market']['task']['started_at']
assert tasks['market']['task']['ended_at']<=tasks['finance']['task']['started_at']
assert tasks['finance']['task']['ended_at']<=tasks['comparison']['task']['started_at']
pins={path:sha(ROOT/path) for path in paths.values()}
for value in values.values():
    for name,digest in value['binding'].get('source_hashes',{}).items():
        assert name!='state/dataset_lock.json'
        path=Path(name) if name.startswith('/') else ROOT/name
        if not path.is_relative_to(ROOT):continue
        relative=path.relative_to(ROOT).as_posix()
        assert relative not in pins or pins[relative]==digest
        assert sha(path)==digest,relative
        pins[relative]=digest
failure_path='reports/fast_research/TURTLE_DIRECTION_SMOKE_20261003_V1.json'
failure=read(ROOT/failure_path)
failed_task=closed(failure['binding']['task_id'],1)
assert failure['test_exit_code']==1 and failure['junit_counts']['errors']==1
for name,digest in failure['binding']['source_hashes'].items():
    assert name!='state/dataset_lock.json' and sha(ROOT/name)==digest
    assert name not in pins or pins[name]==digest
    pins[name]=digest
pins[failure_path]=sha(ROOT/failure_path)
for pattern in ['docs/archive/TURTLE_DIRECTION*','protocols/TURTLE_DIRECTION*','scripts/investment/turtle_direction*']:
    for path in ROOT.glob(pattern):
        if path.is_file():pins[path.relative_to(ROOT).as_posix()]=sha(path)
for name in [ARCHIVE,'docs/TURTLE_DIRECTION_ABLATION_20261003.md',
    'scripts/investment/audit_turtle_direction_research.py','tests/test_turtle_direction_mask.py',
    'tests/test_turtle_direction_mask_v2.py']:
    pins[name]=sha(ROOT/name)
original=subprocess.check_output(['git','show','HEAD:reports/experiment_registry.jsonl'],cwd=ROOT)
current=(ROOT/'reports/experiment_registry.jsonl').read_bytes()
assert current.startswith(original) and len(current)<=8_000_000
status=resources.status();assert status['ram_limit_bytes']<=5_000_000_000 and status['swap_bytes']==0
collector=subprocess.run(['ps','-p','540','-o','pid=,stat=,etime=,comm='],capture_output=True,text=True)
result=dict(status='PASS_D049_VERIFIABLE_DIRECTION_ABLATION_NOT_NATIVE_OR_LONG_TERM_APR',
    binding=dict(task_id=os.environ['COIN_TASK_ID'],source_hashes=pins),
    own_completion='LIVE_CALLER_REQUIRES_EXTERNAL_TRUE_EXIT_CHECK',source_roles=paths,closed_role_tasks=tasks,
    failed_attempt_preserved=dict(path=failure_path,sha256=pins[failure_path],closed_task=failed_task,
        repair='V2_ONE_ASCII_PARENTHESIS_NO_CHANGED_ASSERTIONS'),
    new_accounts=8,full_new_accounts=full,new_financial_case_calls=8,source_QA_or_old_accounts_replayed=False,
    adoption='FIXED_DIRECTION_PERMISSION_AND_ECONOMIC_COMPARISON_CAPABILITY',research_anchor='PAST_COVARIANCE_HOLD',
    investment='CASH_NONE',long_term_APR='NOT_EVALUABLE',native_filters_certified=False,
    complete_strategy_state_or_intent_oracle=False,market_arrays_read=False,
    registry_append_only=dict(committed_prefix_bytes=len(original),committed_prefix_sha256=hashlib.sha256(original).hexdigest(),
        preserved_exact_prefix=True,current_bytes=len(current),registry_blob_limit=8_000_000,other_blob_limit=4_000_000),
    latest_actual_disk_scan=market['disk'],measurement_before_subsequent_outputs=True,
    collector_read_only_snapshot=dict(exit_code=collector.returncode,output=collector.stdout.strip(),process_untouched=True),
    resources=status,orders_sent=0,locked_consumed=False,GPU=0,created_utc=datetime.now(UTC).isoformat())
out=ROOT/'reports/fast_research/TURTLE_DIRECTION_ROOT_ACCEPTANCE_20261003_V1.json'
write(out,result)
print(json.dumps(dict(status=result['status'],sha256=sha(out),pins=len(pins))))
