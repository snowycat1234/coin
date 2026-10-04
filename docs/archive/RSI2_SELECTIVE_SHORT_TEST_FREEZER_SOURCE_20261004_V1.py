"""Freeze one new synthetic signed-RSI fixture and the sources it exercises."""
import ast
from datetime import UTC, datetime
import hashlib
import json
import os
from pathlib import Path
import subprocess
from scripts.investment import rsi2_daily_pool_target as target

ROOT = Path('/mnt/d/codex/coin')
STATE = Path('/home/xflops/coin-state')
PARENT = '61316ff1865437b8cc7a286e0e2aad95bdc67340'
NAME = 'RSI2_SELECTIVE_SHORT_TARGET_SYNTHETIC_20261004_V1'
OUT = ROOT/'protocols'/f'{NAME}.json'
RUN = STATE/'d059-rsi2-selective-short-target-tests-20261004-v1'
ACTUAL = ROOT/'reports/fast_research'/f'{NAME}.json'

def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()

assert os.environ.get('COIN_TASK_ID') and not OUT.exists() and not RUN.exists() and not ACTUAL.exists()
assert subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip() == PARENT
spec = json.loads((ROOT/'protocols/RSI2_DAILY_POOL_TARGET_SYNTHETIC_20261004_V2.json').read_bytes())
sources = [p for p in spec['frozen_sources'] if not p.startswith((
    'tests/', 'reports/fast_research/RSI2_DAILY_POOL_TARGET_STARTUP_FAILURE',
    'docs/archive/RSI2_DAILY_POOL_TARGET_STARTUP_FAILURE',
    'protocols/RSI2_DAILY_POOL_TARGET_SYNTHETIC'))]
sources += ['tests/test_rsi2_selective_short_pool.py',
            'scripts/investment/multi_asset_portfolio.py',
            'scripts/investment/compare_multi_asset_portfolios.py',
            'scripts/investment/perpetual_directional.py',
            'scripts/investment/perpetual_closing_exempt_account.py',
            'src/quant/perpetual_account.py', 'src/quant/execution_contract.py',
            'docs/archive/PERPETUAL_INDEPENDENT_REFERENCE_20261003_V1.py']
sources = sorted(set(sources))
for name in sources:
    if name.endswith('.py'):
        ast.parse((ROOT/name).read_text())
spec.update(contract_id='D059_RSI2_ORIGINAL_SELECTIVE_SHORT_SHARED_POOL_SYNTHETIC_V1',
    created_utc=datetime.now(UTC).isoformat(), git_commit=PARENT,
    tests=['tests/test_rsi2_selective_short_pool.py'],
    frozen_sources={name: sha(ROOT/name) for name in sources},
    calculation_rules=target.rules_for_mode('LONG_SHORT'), rsi_parameters=dict(target.PARAMETERS),
    direction_mode='LONG_SHORT', run_dir=str(RUN),
    output_path=ACTUAL.relative_to(ROOT).as_posix(),
    test_scope='NEW_SELECTIVE_SHORT_REAL_HOOKS_SIGNED_SHARED_RISK_AND_ACCOUNT_SYNTHETIC_NOT_MARKET_RESULTS',
    pre_change_daily_adapter=dict(path='scripts/investment/rsi2_daily_pool_target.py',
        sha256='6e9aa37dad81f754543653acdfccbc75aa96750afff55e817e654debce10bd79', git_commit=PARENT))
spec.pop('prior_startup_failure', None)
spec.pop('pre_change_shared', None)
archive = ROOT/'docs/archive/RSI2_SELECTIVE_SHORT_TEST_FREEZER_SOURCE_20261004_V1.py'
assert not archive.exists()
archive.write_bytes(Path(__file__).read_bytes())
spec['frozen_sources'][archive.relative_to(ROOT).as_posix()] = sha(archive)
spec['freeze_task_id'] = os.environ['COIN_TASK_ID']
with OUT.open('x') as stream:
    json.dump(spec, stream, indent=2, allow_nan=False)
    stream.write('\n')
print(json.dumps(dict(protocol=str(OUT), sha256=sha(OUT), source_count=len(spec['frozen_sources']),
    market_arrays_read=False, tests_executed=0)))
