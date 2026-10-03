"""Check new private independent orchestration anchors before payload IO."""
import hashlib,json,os
from pathlib import Path
from scripts.investment import audit_perpetual_303_research as a
r=Path('/mnt/d/codex/coin')
own='docs/archive/PERPETUAL_303_FINANCIAL_CONTEXT_COMPILE_SOURCE_20261003_V1.py'
assert Path(__file__).read_bytes()==(r/own).read_bytes() and os.getenv('COIN_TASK_ID')
entry,proof=a.context()
result=dict(status='COMPILED_D045_INDEPENDENT_METADATA_ONLY_NO_ARRAYS',binding=dict(task_id=os.environ['COIN_TASK_ID'],source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()),proof=proof,market_arrays_read=False,financial_functions_executed=False)
out=r/'reports/fast_research/PERPETUAL_303_FINANCIAL_CONTEXT_COMPILE_20261003_V1.json'
with out.open('x') as f:json.dump(result,f,indent=2);f.write('\n')
print(json.dumps(dict(status=result['status'],task_id=result['binding']['task_id'])))
