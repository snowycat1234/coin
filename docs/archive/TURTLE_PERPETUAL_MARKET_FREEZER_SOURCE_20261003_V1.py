"""Freeze the fixed Turtle challenger after actual new compatibility/source QA."""
import hashlib,json,os,sys
from datetime import UTC,datetime
from pathlib import Path
from scripts.investment import turtle_perpetual_research_v2 as new
ROOT=new.ROOT;STATE=new.STATE
ARCHIVE='docs/archive/TURTLE_PERPETUAL_MARKET_FREEZER_SOURCE_20261003_V1.py'
def sha(p):
    with Path(p).open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()
def read(p):
    path=ROOT/p;assert not path.is_symlink() and path.stat().st_size<2_000_000
    return json.loads(path.read_bytes())
def accepted(p,status):
    value=read(p);assert value['status']==status
    task=json.loads((STATE/'task-progress'/('task-'+value['binding']['task_id']+'.json')).read_bytes())
    assert task['status']=='completed' and task['exit_code']==0
    return dict(path=p,sha256=sha(ROOT/p),required_status=status)
assert os.environ.get('COIN_TASK_ID') and Path(sys.prefix)==STATE/'v8-clean-env-20261002-v2'
assert Path(__file__).read_bytes()==(ROOT/ARCHIVE).read_bytes()
assert sha(ROOT/'state/dataset_lock.json')=='29d930063842e9b1666869b4e5f9e3c8cd629313e57b9dadc328c6131b92f45d'
parent=read('protocols/PERPETUAL_303_RESEARCH_20261003_V1.json')
smoke=accepted('reports/fast_research/TURTLE_PERPETUAL_SMOKE_20261003_V2.json','PASS_BOUNDED_RESEARCH_TESTS_SYNTHETIC_NOT_MARKET_RESULT')
warmup=accepted('reports/fast_research/TURTLE_4H_WARMUP_SOURCE_INDEPENDENT_20261003_V1.json','PASS_D047_OFFICIAL_4H_WARMUP_SOURCE_ONLY')
names=set(new.strategy.DEPENDENCY_PINS)|set(new.PINS)|{
 'scripts/investment/turtle_perpetual_research_v2.py','docs/archive/TURTLE_PERPETUAL_RESEARCH_SOURCE_20261003_V2.py',
 'docs/archive/TURTLE_PERPETUAL_RESEARCH_SOURCE_20261003_V1.py',
 'scripts/investment/turtle_perpetual_bridge.py','docs/archive/TURTLE_PERPETUAL_BRIDGE_SOURCE_20261003_V1.py',
 'scripts/investment/turtle_perpetual_smoke_v2.py','tests/test_turtle_perpetual_bridge_v2.py',
 'scripts/investment/public_long_development_adapter.py','scripts/investment/bybit_spot_adapter.py',
 'scripts/investment/public_sma_daily.py','scripts/investment/public_sma_perpetual.py',
 'scripts/investment/public_rsi2_indicator.py','scripts/investment/public_pair_diagnostics.py',
 'scripts/investment/perpetual_directional.py','scripts/investment/perpetual_303_research.py',
 'scripts/investment/perpetual_213_research.py','scripts/research_v8/registry.py',
 'scripts/research_v8/funding_price_source_v2.py','scripts/research_v7/oracle_flow_ceiling.py',
 'src/quant/paths.py','src/quant/resources.py','src/quant/disk.py','src/quant/metrics.py',
 'src/quant/execution_contract.py','environments/v8/uv.lock',
 'scripts/bounded.sh','scripts/with_task_progress.sh','scripts/task_progress_run.py',
 'protocols/BYBIT_NONVIP_FEE_REFERENCE_20261002.json',
 'protocols/TURTLE_PERPETUAL_SMOKE_20261003_V2.json',
 'reports/fast_research/TURTLE_RULES_OFFICIAL_SOURCE_PROVENANCE_20261003_V2.json',
 'reports/fast_research/TURTLE_4H_WARMUP_SOURCE_ACTUAL_20261003_V1.json',
 'third_party/jesse_example_rsi2/INSTALLED_KERNEL_BINDING_20261002_V1.json',
 'third_party/jesse_example_donchian/donchian_indicator_original.py',
 'reports/fast_research/PERPETUAL_303D_INPUT_BINDING_20261003_V1.json',
 'reports/fast_research/PERPETUAL_303_RESEARCH_ROOT_ACCEPTANCE_20261003_V1.json',
 'reports/fast_research/PERPETUAL_RISK_REDUCTION_ROOT_ACCEPTANCE_20261003_V1.json',
 'reports/fast_research/TURTLE_PERPETUAL_SMOKE_20261003_V1.json',ARCHIVE,smoke['path'],warmup['path']}
names|={'third_party/jesse_example_turtle_rules/'+name for name in new.strategy.VENDOR_PINS}
hashes={name:sha(ROOT/name) for name in sorted(names)}
for name,digest in new.strategy.DEPENDENCY_PINS.items():assert hashes[name]==digest
for name,digest in hashes.items():
    if name in parent['frozen_sources']:assert parent['frozen_sources'][name]==digest,name
spec=dict(contract_id=new.CONTRACT,rules=new.RULES,period_ids=['303D'],cost_scenarios=new.base.COSTS,
 unit_scenarios=new.base.UNITS,environment=parent['environment'],frozen_sources=hashes,
 input_manifest=parent['input_manifest'],trade_source_acceptance=parent['trade_source_acceptance'],
 required_smoke_receipt=smoke,warmup_acceptance=warmup,
 run_dir=str(STATE/'d047-turtle-perpetual-research-20261003-v2'),
 output_path='reports/fast_research/TURTLE_PERPETUAL_RESEARCH_ACTUAL_20261003_V2.json',
 budgets=dict(new_owned_bytes=500_000_000,peak_RSS_bytes=3_000_000_000,wall_seconds=3600),
 private_lock_access='STREAM_SHA_ONLY_NOT_EXPORTED',funding_rate_unit='UNCONFIRMED',
 created_utc=datetime.now(UTC).isoformat(),freezer_task_id=os.environ['COIN_TASK_ID'],
 saved_comparison_only=['D046_FIXED_SMA_LONG_SHORT','D045_PAST_VOL_MANAGED_HOLD','CASH'],
 market_accounts=4,old_controls_replayed=False,native_Jesse_intrabar_replicated=False)
context=new.context(spec);assert len(context['derivation'])==2
out='protocols/TURTLE_PERPETUAL_RESEARCH_20261003_V1.json'
with (ROOT/out).open('x') as f:json.dump(spec,f,indent=2,ensure_ascii=False,allow_nan=False);f.write('\n')
print(json.dumps(dict(status='FROZEN_D047_FOUR_CONDITIONS_ALL_AST_ANCHORS_COMPILED_NO_MARKET_ARRAYS',protocol=out,sha256=sha(ROOT/out),pins=len(hashes))))
