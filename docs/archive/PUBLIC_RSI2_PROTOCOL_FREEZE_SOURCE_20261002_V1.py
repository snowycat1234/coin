import argparse
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path('/mnt/d/codex/coin')
STATE = Path('/home/xflops/coin-state')
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
read = lambda p: json.loads((ROOT / p).read_text())
parser = argparse.ArgumentParser()
parser.add_argument('--kernel-receipt', required=True)
args = parser.parse_args()
kernel = read(args.kernel_receipt)
assert kernel['status'].startswith('PASS_'), 'Actual official kernel compatibility PASS required'
task_path = STATE / 'task-progress' / ('task-' + kernel['binding']['task_id'] + '.json')
task = json.loads(task_path.read_text())
assert task['status'] == 'completed' and task['exit_code'] == 0
prefix = 'reports/fast_research/'
strategy = 'COIN_JESSE_RSI2_1H_SPOT_ADAPTER'
extra = [
    'scripts/investment/public_rsi2_adapter.py', 'scripts/investment/public_rsi2_indicator.py',
    'tests/test_public_rsi2_native_integration.py', args.kernel_receipt,
    'docs/archive/COMPARE_SIMPLE_STRATEGIES_PRE_RSI2_20261002_V1.py',
    'docs/archive/OPEN_SOURCE_REGISTRY_PRE_RSI2_20261002.md',
    prefix + 'PUBLIC_DONCHIAN_HYBRID_NATIVE_ROOT_MODULE_ACCEPTANCE_20261002_V1.json',
    prefix + 'PUBLIC_DONCHIAN_HYBRID_BYBIT_122D_ACTUAL_20261002_V1.json',
    prefix + 'PUBLIC_DONCHIAN_HYBRID_BYBIT_90D_ACTUAL_20261002_V1.json',
]
extra += [str(p.relative_to(ROOT)) for p in (ROOT / 'third_party/jesse_example_rsi2').rglob('*') if p.is_file()]
assert all((ROOT / p).stat().st_size < 1000000 and (ROOT / p).suffix not in ('.whl', '.so', '.gz') for p in extra)
rules = {
    'PUBLIC': 'Pinned unmodified MIT RSI2 hooks; long-only1h close>SMA200 and scalarRSI2<=10 entry; held close>SMA5 exit',
    'indicator': 'Pinned official jesse-rust1.3.0 with original417f wrapper default240bar scalar truncation; no custom RSI/kernel',
    'priority': 'Held exit first at same stamp; no same-stamp reentry; next closed1h eligible',
    'causality': 'Full240 contiguous closed available1h candles; any failure denies whole paired fold, prior causal intents retained',
    'terminal': 'Common costed zero target, actual marked residuals retained',
    'adaptation': 'Signal-held context, no upstream wholebalance/short/nativeJesse-engine profitability claim',
}
for period in ('122D', '90D'):
    spec = read('protocols/PUBLIC_DONCHIAN_HYBRID_BYBIT_' + period + '_V1.json')
    spec['contract_id'] = 'PUBLIC_RSI2_BYBIT_' + period + '_V1'
    spec['created_before_new_economics_utc'] = datetime.now(UTC).isoformat()
    spec['primary_reference'] = strategy
    spec['primary_selection_reason'] = 'One fixed public trend-pullback entry information hypothesis versus accepted breakout controls; no search'
    spec['strategy_ids'] = [strategy]
    spec['strategy_rules'] = rules
    spec['smoke_test_path'] = 'tests/test_public_rsi2_native_integration.py'
    spec['required_smoke_receipt'] = prefix + 'PUBLIC_RSI2_NATIVE_PIPELINE_TINY_20261002_V1.json'
    spec['research_question'] = 'Does a fixed public trend-pullback entry provide more stable gross/net returns under unchanged ordinary Bybit Spot costs and causal risk?'
    spec['continuity_invariants']['source'] = 'Same saved Parquet as native2h/hybrid controls, fresh fixed publicRSI2 targets, immutable physicalArrow read before execution'
    spec['official_kernel_acceptance'] = dict(path=args.kernel_receipt, sha256=sha(ROOT / args.kernel_receipt), task_path=str(task_path), actual_exit=0)
    spec['additional_reference_receipts'] = {
        prefix + 'PUBLIC_DONCHIAN_HYBRID_BYBIT_' + period + '_ACTUAL_20261002_V1.json':
        sha(ROOT / (prefix + 'PUBLIC_DONCHIAN_HYBRID_BYBIT_' + period + '_ACTUAL_20261002_V1.json')),
    }
    spec['limitations'] = [v for v in spec['limitations'] if not v.startswith(('Hybrid2h', 'Faster exits', 'No new model, timeframe'))]
    spec['limitations'].extend([
        'Fixed1h long-only RSI2 is a COIN sizing/execution port, not original Jesse wholebalance or short result replication',
        'Official scalar initialization uses240 closed available bars; SMA200 is not a substitute for the full indicator window',
        'No threshold/timeframe/regime/model search; old controls read saved summaries only',
    ])
    spec['frozen_sources']['scripts/investment/compare_simple_strategies.py'] = sha(ROOT / 'scripts/investment/compare_simple_strategies.py')
    for name in extra:
        spec['frozen_sources'][name] = sha(ROOT / name)
    for name, digest in spec['frozen_sources'].items():
        assert sha(ROOT / name) == digest, name
    destination = ROOT / ('protocols/PUBLIC_RSI2_BYBIT_' + period + '_V1.json')
    with destination.open('x') as stream:
        json.dump(spec, stream, indent=2, ensure_ascii=False, allow_nan=False)
        stream.write('\n')
    print(json.dumps(dict(protocol=str(destination), sha256=sha(destination), planned_new_accounts=3)))
