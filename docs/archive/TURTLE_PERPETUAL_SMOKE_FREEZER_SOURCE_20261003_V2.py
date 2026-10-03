"""Bind one synthetic Turtle/controller test before executing its fixture."""
import hashlib,json,os
from datetime import UTC,datetime
from pathlib import Path
from scripts.investment import turtle_perpetual_bridge as bridge
from scripts.investment import turtle_perpetual_research_v2 as research
ROOT=bridge.ROOT
ARCHIVE='docs/archive/TURTLE_PERPETUAL_SMOKE_FREEZER_SOURCE_20261003_V2.py'
def sha(p):
    with Path(p).open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()
def write(p,v):
    with Path(p).open('x') as f:json.dump(v,f,ensure_ascii=False,indent=2,allow_nan=False);f.write('\n')
assert os.environ.get('COIN_TASK_ID') and Path(__file__).read_bytes()==(ROOT/ARCHIVE).read_bytes()
assert sha(ROOT/'state/dataset_lock.json')=='29d930063842e9b1666869b4e5f9e3c8cd629313e57b9dadc328c6131b92f45d'
names=set(bridge.DEPENDENCY_PINS)|set(research.PINS)|{
    'scripts/investment/turtle_perpetual_bridge.py','scripts/investment/turtle_perpetual_research_v2.py',
    'scripts/investment/turtle_perpetual_smoke_v2.py','tests/test_turtle_perpetual_bridge_v2.py',
    'docs/archive/TURTLE_PERPETUAL_BRIDGE_SOURCE_20261003_V1.py',
    'docs/archive/TURTLE_PERPETUAL_RESEARCH_SOURCE_20261003_V2.py',
    'docs/archive/TURTLE_PERPETUAL_RESEARCH_SOURCE_20261003_V1.py',
    'docs/archive/TURTLE_PERPETUAL_SMOKE_SOURCE_20261003_V2.py',
    'docs/archive/TURTLE_PERPETUAL_TEST_SOURCE_20261003_V2.py',ARCHIVE,
    'docs/archive/BOUNDED_RESEARCH_TEST_RUNNER_SOURCE_20261003_V1.py',
    'docs/archive/PERPETUAL_INDEPENDENT_REFERENCE_20261003_V1.py',
    'scripts/investment/public_rsi2_indicator.py','scripts/investment/public_long_development_adapter.py',
    'scripts/investment/public_pair_diagnostics.py','scripts/investment/perpetual_directional.py',
    'scripts/investment/perpetual_303_research.py','scripts/research_v8/registry.py',
    'third_party/jesse_example_donchian/donchian_indicator_original.py',
    'third_party/jesse_example_rsi2/INSTALLED_KERNEL_BINDING_20261002_V1.json',
    'reports/fast_research/TURTLE_RULES_OFFICIAL_SOURCE_PROVENANCE_20261003_V2.json',
    'src/quant/execution_contract.py','environments/v8/uv.lock'}
names|={'third_party/jesse_example_turtle_rules/'+name for name in bridge.VENDOR_PINS}
hashes={p:sha(ROOT/p) for p in sorted(names)}
for p,h in bridge.DEPENDENCY_PINS.items():assert hashes[p]==h
for p,h in bridge.VENDOR_PINS.items():assert hashes['third_party/jesse_example_turtle_rules/'+p]==h
provenance=json.loads((ROOT/'reports/fast_research/TURTLE_RULES_OFFICIAL_SOURCE_PROVENANCE_20261003_V2.json').read_bytes())
task=json.loads((research.STATE/'task-progress'/('task-'+provenance['binding']['task_id']+'.json')).read_bytes())
assert task['status']=='completed' and task['exit_code']==0
spec=dict(created_utc=datetime.now(UTC).isoformat(),freezer_task_id=os.environ['COIN_TASK_ID'],
    tests=['tests/test_turtle_perpetual_bridge_v2.py'],frozen_sources=hashes,
    calculation_rules=dict(scope='ONE_NEW_RAW_HOOK_KERNEL_PARTIAL_RECOVERY_STOP_GAP_AND_CONTROLLER_CAUSAL_FIXTURE',old_suite_replayed=False),
    fee_profile=research.base.COSTS,data_scope='SYNTHETIC_ONLY',
    local_non_git_hash_guard={'state/dataset_lock.json':'29d930063842e9b1666869b4e5f9e3c8cd629313e57b9dadc328c6131b92f45d'})
out='protocols/TURTLE_PERPETUAL_SMOKE_20261003_V2.json'
write(ROOT/out,spec)
print(json.dumps(dict(status='FROZEN_D047_ONE_SYNTHETIC_CASE_NOT_EXECUTED',protocol=out,sha256=sha(ROOT/out),pins=len(hashes))))
