"""Compile only new four-account independent routing, never read price arrays."""
import hashlib,json,os
from pathlib import Path
from scripts.investment import audit_perpetual_risk_reduction as module
r=Path('/mnt/d/codex/coin')
archive='docs/archive/PERPETUAL_RISK_REDUCTION_FINANCIAL_COMPILE_SOURCE_20261003_V1.py'
assert os.getenv('COIN_TASK_ID') and Path(__file__).read_bytes()==(r/archive).read_bytes()
entry,proof=module.context()
value=dict(status='COMPILED_D046_INDEPENDENT_FOUR_ROUTE_METADATA_ONLY_NO_ARRAYS',
    binding=dict(task_id=os.environ['COIN_TASK_ID']),private_derivation=proof,
    market_arrays_read=False,financial_cases_executed=0,locked_consumed=False)
p=r/'reports/fast_research/PERPETUAL_RISK_REDUCTION_FINANCIAL_COMPILE_20261003_V1.json'
with p.open('x') as f:json.dump(value,f,indent=2);f.write('\n')
print(json.dumps(dict(status=value['status'],sha256=hashlib.sha256(p.read_bytes()).hexdigest())))
