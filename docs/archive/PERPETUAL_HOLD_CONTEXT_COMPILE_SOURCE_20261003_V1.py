"""Validate actual frozen D044 metadata/AST without reading any market payload."""
import hashlib,json
from pathlib import Path
from scripts.investment import perpetual_hold_research as r
root=Path('/mnt/d/codex/coin')
path=root/'protocols/PERPETUAL_HOLD_RESEARCH_20261003_V1.json'
spec=json.loads(path.read_bytes());context=r.context(spec)
value=dict(status='PASS_D044_FROZEN_THREE_PERIOD_CONTEXT_COMPILED_NO_MARKET_ARRAYS',
    protocol_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),derivation=context['derivation'],
    simulate_AST_unchanged=all(x['original_AST_sha256']==x['derived_AST_sha256'] for x in context['derivation'] if x['function']=='simulate'),
    selected_periods=spec['period_ids'],planned_physical_accounts=12,market_arrays_read=False)
assert value['simulate_AST_unchanged']
with (root/'reports/fast_research/PERPETUAL_HOLD_CONTEXT_COMPILE_20261003_V1.json').open('x') as f:
    json.dump(value,f,indent=2);f.write('\n')
print(value['status'])
