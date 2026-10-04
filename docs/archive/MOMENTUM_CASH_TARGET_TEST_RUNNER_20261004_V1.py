from pathlib import Path
import pytest
paths = ('scripts/investment/momentum_cash_pool_target.py', 'scripts/investment/multi_asset_portfolio.py', 'scripts/investment/multi_asset_financial_audit.py', 'scripts/investment/compare_multi_asset_portfolios.py', 'tests/test_momentum_cash_pool_target_20261004.py', 'tests/test_momentum_cash_independent_20261004.py')
root = Path('/mnt/d/codex/coin')
for name in paths:
    compile((root/name).read_bytes(), str(root/name), 'exec')
print('D057 current normal sources syntax accepted; only two new synthetic cases', flush=True)
raise SystemExit(pytest.main(['-q', str(root/'tests/test_momentum_cash_pool_target_20261004.py'), str(root/'tests/test_momentum_cash_independent_20261004.py'), '--basetemp=/home/xflops/coin-state/d057-momentum-target-tests-20261004-v1', '--junitxml=/mnt/d/codex/coin/reports/MOMENTUM_CASH_TARGET_TESTS_20261004_V1.xml']))
