"""Freeze a single conditional closing-rule control before any market arrays."""
import hashlib,json,os,sys
from datetime import UTC,datetime
from pathlib import Path
ROOT=Path('/mnt/d/codex/coin');STATE=Path('/home/xflops/coin-state')
ARCHIVE='docs/archive/CLOSING_EXEMPT_RESEARCH_FREEZER_SOURCE_20261003_V1.py'
def sha(p):
    with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def read(p):return json.loads(Path(p).read_bytes())
def write(p,v):
    with Path(p).open('x') as f:json.dump(v,f,indent=2,ensure_ascii=False,allow_nan=False);f.write('\n')
assert os.environ.get('COIN_TASK_ID') and sys.prefix==str(STATE/'v8-clean-env-20261002-v2')
assert sha(__file__)==sha(ROOT/ARCHIVE)
assert sha(ROOT/'state/dataset_lock.json')=='29d930063842e9b1666869b4e5f9e3c8cd629313e57b9dadc328c6131b92f45d'
from scripts.investment import closing_exempt_research as new
spec=read(ROOT/'protocols/TURTLE_PERPETUAL_RESEARCH_20261003_V1.json')
assert all(p!='state/dataset_lock.json' and sha(ROOT/p)==h for p,h in spec['frozen_sources'].items())
smoke_path='reports/fast_research/PERPETUAL_CLOSING_EXEMPT_SMOKE_20261003_V1.json'
smoke=read(ROOT/smoke_path);task=read(STATE/'task-progress'/('task-'+smoke['binding']['task_id']+'.json'))
assert task['status']=='completed' and task['exit_code']==0 and smoke['test_exit_code']==0 and smoke['source_bytes_unchanged']
assert smoke['junit_counts']==dict(tests=1,errors=0,failures=0,skipped=0)
pins=dict(spec['frozen_sources']);pins.update(smoke['binding']['source_hashes'])
for p,h in new.PINS.items():assert sha(ROOT/p)==h;pins[p]=h
for p in [ARCHIVE,'scripts/investment/closing_exempt_research.py','docs/archive/CLOSING_EXEMPT_RESEARCH_SOURCE_20261003_V1.py',smoke_path]:pins[p]=sha(ROOT/p)
assert pins['scripts/investment/closing_exempt_research.py']=='173b03ee5b2ce3bb263d695a712be694cec7a15a89025092bc6f53ced81fd98b'
spec.update(contract_id=new.CONTRACT,rules=new.RULES,frozen_sources=pins,
    run_dir=str(STATE/'d048-closing-exempt-research-20261003-v1'),
    output_path='reports/fast_research/CLOSING_EXEMPT_RESEARCH_ACTUAL_20261003_V1.json',
    required_smoke_receipt=dict(path=smoke_path,sha256=sha(ROOT/smoke_path),required_status=smoke['status']),
    budgets=dict(wall_seconds=3600,peak_RSS_bytes=3_000_000_000,new_owned_bytes=500_000_000),
    created_utc=datetime.now(UTC).isoformat(),freezer_task_id=os.environ['COIN_TASK_ID'],
    preceding_protocol_sha256=sha(ROOT/'protocols/TURTLE_PERPETUAL_RESEARCH_20261003_V1.json'),
    native_quantity_profile_available=False,historical_filters_certified=False,
    current_closing_semantics_only=True)
context=new.context(spec)
assert all(callable(context[k]) for k in ['main','simulate','simulate_TURTLE','simulate_HOLD','load_window'])
assert context['simulate_TURTLE'].__globals__['USDTLinearPerpetualAccount'] is new.closing.USDTLinearPerpetualAccount
assert context['simulate_HOLD'].__globals__['USDTLinearPerpetualAccount'] is new.closing.USDTLinearPerpetualAccount
write(ROOT/new.PROTOCOL_PATH,spec)
result=dict(status='PASS_D048_PROSPECTIVE_CLOSING_EXEMPT_METADATA_WIRING_NO_MARKET_ARRAYS',
    binding=dict(task_id=os.environ['COIN_TASK_ID'],source_hashes=pins),
    protocol_path=new.PROTOCOL_PATH,protocol_sha256=sha(ROOT/new.PROTOCOL_PATH),
    selectors=list(new.SELECTORS),planned_accounts=8,synthetic_completed_task=task,
    derivation=context['derivation'],source_QA_repeated=False,market_arrays_read=False,
    old_financial_cases_replayed=False,orders_sent=0,locked_consumed=False)
write(ROOT/'reports/fast_research/CLOSING_EXEMPT_RESEARCH_BEFORE_RESULTS_20261003_V1.json',result)
print(json.dumps(dict(status=result['status'],protocol_sha256=result['protocol_sha256'])))
