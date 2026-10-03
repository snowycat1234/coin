"""Freeze the single preselected comparison before economic input arrays."""
import hashlib,json,os
from datetime import UTC,datetime
from pathlib import Path
from scripts.investment import perpetual_directional as market
ROOT=Path('/mnt/d/codex/coin');STATE=Path('/home/xflops/coin-state')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def load(p):return json.loads(Path(p).read_bytes())
assert sha(ROOT/'scripts/investment/perpetual_directional.py')=='547a1ca2d8e4b9278f599a1972f099bfe449910e34791e5a0e16873ce67d5ef3'
case_path='reports/fast_research/PERPETUAL_CONTROLLER_TEST_ACTUAL_20261003_V2.json'
case=load(ROOT/case_path)
assert case['status']=='PASS_BOUNDED_RESEARCH_TESTS_SYNTHETIC_NOT_MARKET_RESULT' and case['test_exit_code']==0 and case['junit_counts']==dict(tests=1,failures=0,errors=0,skipped=0)
task=load(STATE/'task-progress'/('task-'+case['binding']['task_id']+'.json'))
assert task['status']=='completed' and task['exit_code']==0
source_path='reports/fast_research/PERPETUAL_TRADE_SOURCE_ROOT_ACCEPTANCE_20261003_V4.json'
source=load(ROOT/source_path);assert sha(ROOT/source_path)=='f8f6d2e49c320ecc5f61506ffd291ac1c94af0b80803baa6b8e4210741a1f95d' and source['source_acceptance_granted'] is True
manifest_path='reports/fast_research/LONG_SHORT_USDM_INPUT_BINDING_20261003_V1.json'
assert sha(ROOT/manifest_path)=='f7b3e8eb724b8196280ef872454b36297171b5f487bea94410dc547eb846d045'
names=set(case['binding']['source_hashes'])
names.update([case_path,source_path,manifest_path,'protocols/BYBIT_NONVIP_FEE_REFERENCE_20261002.json',
 'reports/fast_research/PERPETUAL_PUBLIC_CHAIN_TEST_ACTUAL_20261003_V1.json',
 'reports/fast_research/PERPETUAL_ACCOUNT_TEST_ACTUAL_20261003_V1.json',
 'reports/fast_research/PERPETUAL_PUBLIC_SIGNAL_TEST_ACTUAL_20261003_V1.json',
 'scripts/bounded.sh','scripts/with_task_progress.sh','scripts/task_progress_run.py',
 'state/dataset_lock.json','configs/dataset_policy.json'])
pins={name:sha(ROOT/name) for name in sorted(names)}
assert pins['state/dataset_lock.json']=='29d930063842e9b1666869b4e5f9e3c8cd629313e57b9dadc328c6131b92f45d'
protocol=dict(contract_id=market.CONTRACT,created_utc=datetime.now(UTC).isoformat(),
 original_HEAD='4bf2bc1c521835c22598482900329c96a0564d4f',classification='SEEN_DEVELOPMENT_CONDITIONAL_PAIR_NOT_UNSEEN_OR_LONG_TERM_APR',
 rules=market.RULES,cost_scenarios=market.COSTS,unit_scenarios=market.UNITS,period_ids=['122D','90D'],
 input_manifest=dict(path=manifest_path,sha256=pins[manifest_path],required_status=market.MANIFEST_STATUS),
 trade_source_acceptance=dict(path=source_path,sha256=pins[source_path],required_status=source['status']),
 required_smoke_receipt=dict(path=case_path,sha256=pins[case_path],required_status=case['status']),
 frozen_sources=pins,environment=dict(sys_prefix='/home/xflops/coin-state/v8-clean-env-20261002-v2',
 lock_path='environments/v8/uv.lock',lock_sha256=pins['environments/v8/uv.lock']),
 run_dir='/home/xflops/coin-state/d040-perpetual-directional-20261003-v1',
 output_path='reports/fast_research/PERPETUAL_DIRECTIONAL_ACTUAL_20261003_V1.json',
 budgets=dict(new_owned_bytes=400_000_000,peak_RSS_bytes=1_500_000_000,wall_seconds=3600),
 comparison=dict(same_product_same_inputs_capital_risk=True,no_model_search=True,
 funding_unit_never_selected_from_result=True,signed_short_contribution_not_spot_fee_swap=True,
 incomplete_case_not_fullwindow_result=True,locked_consumed=False,orders_sent=0))
path=ROOT/'protocols/PERPETUAL_DIRECTIONAL_20261003_V1.json'
with path.open('x',encoding='utf-8') as f:json.dump(protocol,f,ensure_ascii=False,indent=2);f.write('\n')
archive=ROOT/'docs/archive/PERPETUAL_DIRECTIONAL_PROTOCOL_FREEZER_20261003_V1.py'
with archive.open('xb') as f:f.write(Path(__file__).read_bytes())
print(json.dumps(dict(protocol_sha256=sha(path),source_pins=len(pins),market_arrays_read=False,models_fit=0,task_id=os.environ['COIN_TASK_ID'])))
