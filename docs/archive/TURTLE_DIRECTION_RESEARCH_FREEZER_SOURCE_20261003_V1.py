"""Freeze fixed Turtle direction ablation before any new market payloads."""
import hashlib, json, os, sys
from datetime import UTC, datetime
from pathlib import Path
ROOT=Path('/mnt/d/codex/coin'); STATE=Path('/home/xflops/coin-state')
ARCHIVE='docs/archive/TURTLE_DIRECTION_RESEARCH_FREEZER_SOURCE_20261003_V1.py'

def sha(path):
    with Path(path).open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()

def read(path):return json.loads(Path(path).read_bytes())

def write(path,value):
    with Path(path).open('x') as stream:
        json.dump(value,stream,indent=2,ensure_ascii=False,allow_nan=False);stream.write('\n')

assert os.environ.get('COIN_TASK_ID') and sys.prefix==str(STATE/'v8-clean-env-20261002-v2')
assert sha(__file__)==sha(ROOT/ARCHIVE)
assert sha(ROOT/'state/dataset_lock.json')=='29d930063842e9b1666869b4e5f9e3c8cd629313e57b9dadc328c6131b92f45d'
from scripts.investment import turtle_direction_research as new
from scripts.investment import audit_turtle_direction_research as audit
prior_path='protocols/CLOSING_EXEMPT_RESEARCH_20261003_V1.json'
spec=read(ROOT/prior_path)
assert all(path!='state/dataset_lock.json' and sha(ROOT/path)==digest for path,digest in spec['frozen_sources'].items())
smoke_path='reports/fast_research/TURTLE_DIRECTION_SMOKE_20261003_V1.json'
smoke=read(ROOT/smoke_path)
task=read(STATE/'task-progress'/('task-'+smoke['binding']['task_id']+'.json'))
assert task['status']=='completed' and task['exit_code']==smoke['test_exit_code']==0 and smoke['source_bytes_unchanged']
assert smoke['junit_counts']==dict(tests=1,errors=0,failures=0,skipped=0)
pins=dict(spec['frozen_sources']); pins.update(smoke['binding']['source_hashes'])
for path,digest in new.PINS.items():assert sha(ROOT/path)==digest; pins[path]=digest
for path in [ARCHIVE,'scripts/investment/turtle_direction_research.py',
    'docs/archive/TURTLE_DIRECTION_RESEARCH_SOURCE_20261003_V1.py',
    'scripts/investment/audit_turtle_direction_research.py',
    'docs/archive/TURTLE_DIRECTION_FINANCIAL_AUDITOR_SOURCE_20261003_V1.py',
    audit.ENTRY,audit.CORRECTION,smoke_path]:pins[path]=sha(ROOT/path)
spec.update(contract_id=new.CONTRACT,rules=new.RULES,frozen_sources=pins,
    run_dir=str(STATE/'d049-turtle-direction-research-20261003-v1'),
    output_path='reports/fast_research/TURTLE_DIRECTION_ABLATION_ACTUAL_20261003_V1.json',
    required_smoke_receipt=dict(path=smoke_path,sha256=sha(ROOT/smoke_path),required_status=smoke['status']),
    budgets=dict(wall_seconds=3600,peak_RSS_bytes=3_000_000_000,new_owned_bytes=500_000_000),
    created_utc=datetime.now(UTC).isoformat(),freezer_task_id=os.environ['COIN_TASK_ID'],
    preceding_protocol_sha256=sha(ROOT/prior_path),
    original_LS_HOLD_or_CASH_accounts_replayed=False)
context=new.context(spec)
assert callable(context['main']) and callable(context['simulate']) and callable(context['load_window'])
assert new.SELECTORS==('TURTLE_LONG_ONLY','TURTLE_SHORT_ONLY')
prepared=audit.prepare()
reuse=prepared['recorded_finance']()
financial,financial_proof=reuse.prepare_financial_only(reuse.base_module())
assert callable(financial)
assert financial_proof['closing_filter_financial_journal_derivation']['every_other_financial_statement_and_guard_AST_unchanged']
assert financial_proof['additional_open_leg_direction_check'] is True
assert audit.CONTRACT==new.CONTRACT and audit.ACTUAL_STATUS==new.STATUS
write(ROOT/new.PROTOCOL_PATH,spec)
result=dict(status='PASS_D049_PROSPECTIVE_DIRECTION_METADATA_WIRING_NO_MARKET_ARRAYS',
    binding=dict(task_id=os.environ['COIN_TASK_ID'],source_hashes=pins),
    protocol_path=new.PROTOCOL_PATH,protocol_sha256=sha(ROOT/new.PROTOCOL_PATH),
    selectors=list(new.SELECTORS),planned_accounts=8,synthetic_completed_task=task,
    derivation=context['derivation'],independent_finance_metadata_preparation=financial_proof,
    market_arrays_read=False,ledger_arrays_read=False,old_QA_replayed=False,
    old_financial_cases_replayed=False,orders_sent=0,locked_consumed=False)
write(ROOT/'reports/fast_research/TURTLE_DIRECTION_BEFORE_RESULTS_20261003_V1.json',result)
print(json.dumps(dict(status=result['status'],protocol_sha256=result['protocol_sha256'])))
