import hashlib,json,os
from quant.paths import ROOT
assert os.environ['COIN_TASK_ID']
names=['tests/test_donchian_daily_pool.py','scripts/investment/donchian_daily_pool_target.py','scripts/investment/public_sma_perpetual.py','scripts/investment/public_sma_daily.py','scripts/investment/research_tests.py','scripts/investment/public_pair_diagnostics.py','docs/archive/BOUNDED_RESEARCH_TEST_RUNNER_SOURCE_20261003_V1.py','environments/v8/uv.lock']
names += ['third_party/jesse_example_donchian/'+n for n in ['donchian_original.py','donchian_indicator_original.py','LICENSE','JESSE_LICENSE']]
p=dict(ready_to_execute=True,tests=[names[0]],frozen_sources={n:hashlib.sha256((ROOT/n).read_bytes()).hexdigest() for n in names},calculation_rules=dict(independent='Direct prior20 highlow/SMA200/state/ordered covariance reference',tolerance=1e-13,future_perturbation=True,market_accounts=0,models_fit=0),fee_profile=dict(source='NONE_SYNTHETIC_TARGETS_ONLY',market='NONE',risk='Existingabs30/gross60/vol10%-scale-down'))
out=ROOT/'protocols/DONCHIAN_DAILY_SEMANTICS_SYNTHETIC_20261004_V1.json'
with out.open('x') as f:json.dump(p,f,indent=2);f.write('\n')
print(str(out))
