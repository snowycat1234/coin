import hashlib, json, shutil
from datetime import UTC, datetime
from pathlib import Path
root = Path('/mnt/d/codex/coin')
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
failure = 'reports/fast_research/BYBIT_SPOT_COMMON_PIPELINE_TINY_20261002_V1.json'
r = json.loads((root / failure).read_text())
assert r['status'] == 'FAIL_SIMPLE_STRATEGY_COMPARISON' and r['reason'] == 'At most2 Polars threads'
assert not r['market_inputs_read'] and not r['folds'] and 'test_exit_code' not in r
for period in ('122D', '90D'):
    old = 'protocols/BYBIT_SPOT_2H_' + period + '_V1.json'
    spec = json.loads((root / old).read_text())
    spec.update(contract_id='BYBIT_SPOT_2H_' + period + '_V2',
        required_smoke_receipt='reports/fast_research/BYBIT_SPOT_COMMON_PIPELINE_TINY_20261002_V2.json',
        created_before_new_economics_utc=datetime.now(UTC).isoformat(),
        preceding_failure=dict(path=failure, sha256=sha(root / failure),
            reason='Invocation did not set Polars thread limit; preflight refused before tests, disk scan or market input',
            adapter_runner_tests_economic_parameters_unchanged=True),
        required_cpu_environment=dict(POLARS_MAX_THREADS='2', OMP_NUM_THREADS='2', OPENBLAS_NUM_THREADS='2', MKL_NUM_THREADS='2'))
    spec['frozen_sources'].update({old: sha(root / old), failure: sha(root / failure)})
    new = root / old.replace('_V1.json', '_V2.json')
    with new.open('x') as f:json.dump(spec, f, indent=2, ensure_ascii=False, allow_nan=False); f.write('\n')
    print(json.dumps(dict(path=str(new),sha256=sha(new))))
archive = root / 'docs/archive/BYBIT_FEE_REPLAY_PROTOCOL_FREEZE_SOURCE_20261002_V1.py'
with archive.open('xb') as f:f.write((root / '.cache/freeze_bybit_fee_replay_20261002_v1.py').read_bytes())
