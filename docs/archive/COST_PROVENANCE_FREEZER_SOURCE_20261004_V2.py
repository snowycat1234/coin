import hashlib,json,os
from pathlib import Path
from quant.paths import ROOT
assert os.environ['COIN_TASK_ID']
names=['tests/test_cost_provenance_account.py','src/quant/perpetual_account.py','scripts/investment/bybit_cost_inputs.py','scripts/investment/perpetual_directional.py','src/quant/execution_contract.py','scripts/investment/public_sma_perpetual.py','scripts/investment/research_tests.py','scripts/investment/public_pair_diagnostics.py','docs/archive/BOUNDED_RESEARCH_TEST_RUNNER_SOURCE_20261003_V1.py','environments/v8/uv.lock','docs/input_evidence/BYBIT_USER_FEE_SNAPSHOT_20261004.json']
r=dict(ready_to_execute=True,tests=[names[0]],frozen_sources={n:hashlib.sha256((ROOT/n).read_bytes()).hexdigest() for n in names},calculation_rules=dict(tolerance_USDT='1e-7',synthetic_only=True,legacy_parent_commit='f895f4b32e3c2e6e61b15b022ce46736982e9865',legacy_account_SHA256='9a4223d1115add6ed2cce5b695cf6dcd89459daa6918eb61091b188e5ec05754',actual_runner_cases=2,actual_synthetic_days_each=2,models_fit=0,market_accounts=0,maximum_test_seconds=120),fee_profile=dict(source=names[-1],standard_taker_fraction='.00055',new_friction_bps_per_side='2+1 and 0+0 SYNTHETIC_ONLY',legacy_friction='4+4 and 8+8 preserved',source_market='NONE_SYNTHETIC',historical_fee_zone_certified=False,investment='CASH'))
out=ROOT/'protocols/COST_PROVENANCE_ACCOUNT_SYNTHETIC_20261004_V2.json'
with out.open('x') as f:json.dump(r,f,indent=2);f.write('\n')
print(json.dumps(dict(output=str(out),sha256=hashlib.sha256(out.read_bytes()).hexdigest())))