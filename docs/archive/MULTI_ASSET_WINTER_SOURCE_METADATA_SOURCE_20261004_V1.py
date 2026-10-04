"""Prospective metadata for one fixed quarter using the existing source entry."""
import argparse
from datetime import UTC, datetime
import hashlib
import json
import os
from pathlib import Path
import subprocess
from scripts.investment import multi_asset_data as data

ROOT = Path('/mnt/d/codex/coin')
STATE = Path('/home/xflops/coin-state')
def sha(p):
    with Path(p).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()
def read(p):
    return json.loads(Path(p).read_bytes())
def write(p, v):
    with Path(p).open('x', encoding='utf-8') as stream:
        json.dump(v, stream, indent=2, ensure_ascii=False, allow_nan=False)
        stream.write('\n')

parser = argparse.ArgumentParser()
parser.add_argument('--expected-data', required=True)
parser.add_argument('--expected-transport', required=True)
args = parser.parse_args()
assert os.environ.get('COIN_TASK_ID')
assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip() == '1f40239706162eb92daa8a1e2fa0abb9b59299ed'
changed = {'scripts/investment/multi_asset_data.py': args.expected_data,
           'scripts/investment/multi_asset_official_transport.ps1': args.expected_transport}
assert all(sha(ROOT/p) == h for p,h in changed.items())
old = read(ROOT/'protocols/MULTI_ASSET_NOVEMBER_MARKET_SOURCE_20261004_V1.json')
pins = {}
for p,h in old['source_hashes'].items():
    expected = changed.get(p,h)
    assert sha(ROOT/p) == expected, p
    pins[p] = expected
prior_proofs = {
    'reports/fast_research/PERPETUAL_303_SOURCE_INDEPENDENT_20261003_V1.json':
        'a72c265bc821f6256600333a3fc64c9b5a738c63e3bf758e386e3a15c8287592',
    'reports/fast_research/PERPETUAL_303_SOURCE_ROOT_ACCEPTANCE_20261003_V1.json':
        '3df702c3147b10c606ba92391cff39d251247b170bea502a1b2ffc8d6a7e9ad6',
    'reports/fast_research/MULTI_ASSET_NOVEMBER_SOURCE_ACCEPTANCE_20261004_V2.json':
        '877a53523b3516f186617115128cd865eec88b17fef23490bd8d673e016b16a2',
    'reports/fast_research/MULTI_ASSET_CONTINUOUS_91D_INPUT_BINDING_20261004_V1.json':
        '218279276e924ae0e6e9eba5fc6baea15a7a4e0e687b98e2be81e91945453dd6',
}
for p,h in prior_proofs.items():
    assert sha(ROOT/p) == h, p
    pins[p] = h
warm_ref = dict(path=str(STATE/'d055-continuous-input-binding-20261004-v1/INPUT_MANIFEST.json'),
    sha256='847d8a6e561d782ae641d492697ee03fd7b3ba2eda65298e5d0f02cb0c7b1e50',
    required_status='PASS_D055_CONTINUOUS_91D_ACCEPTED_SOURCE_BINDING_NOT_ECONOMICS')
assert sha(warm_ref['path']) == warm_ref['sha256']
warm = read(warm_ref['path'])
pool = read(ROOT/old['pool_receipt']['path'])
assert pool['symbols'] == warm['selected_symbols'] and len(pool['symbols']) == 10
for ref in warm['monthly_acceptances']:
    assert sha(ROOT/ref['path']) == ref['sha256']
spec = dict(contract_id=data.WINTER_CONTRACT,
    experiment_id='d056-fixed-pool-winter-source-20261004-v1', phase='WINTER_SOURCE',
    ready_for_execution=True, capacity_registered=True, start_us=1733011200000000,
    end_us=1740787200000000, days=90, score_months=['2024-12','2025-01','2025-02'],
    rules=data.WINTER_RULES, budgets=data.WINTER_BUDGETS,
    run_dir=str(STATE/'d056-multiasset-winter-source-20261004-v1'),
    output_path='reports/fast_research/MULTI_ASSET_WINTER_MARKET_SOURCE_20261004_V1.json',
    source_hashes=pins, reuse_manifest=old['reuse_manifest'],
    pool_receipt=old['pool_receipt'], pool_receipt_sha256=old['pool_receipt_sha256'],
    symbols=sorted(set(pool['symbols'])|{'BTCUSDT','ETHUSDT'}),
    warmup_manifest=warm_ref, warmup_source_acceptances=warm['monthly_acceptances'],
    pool_reselected=False, new_market_files=72, reused_market_files=18,
    transport='DEFAULT_WINDOWS_HTTPS_SAME_OFFICIAL_URLS_WSL_PARSE',
    compatibility_reason='FINITE_DEC2024_JAN_FEB2025_DATE_AND_OWNED_PATHS_ONLY',
    child_environment=old['child_environment'], joint_disk_reservation_bytes=1_000_000_000,
    capacity_registration=dict(latest_actual_scan_bytes=24_384_593_509,
        actual_scan_utc='2026-10-04T01:03:44.459589Z', module_joint_reserve_bytes=1_000_000_000,
        expected_total_upper_bytes=25_384_593_509, warn=32_000_000_000,
        stop_new=36_000_000_000, hard=40_000_000_000,
        scan_scope='Previous actual end scan; new disk.check(1GB) required before any network'),
    funding_unit_certified=False, native_Bybit_certified=False, publication_certified=False,
    locked_consumed=False, GPU=0, model_fits=0, orders_sent=0,
    decision='D056 fixed next quarter; source-only, all unknown/missing preserved, no source-based economic selection',
    created_utc=datetime.now(UTC).isoformat())
assert spec['budgets']['market_owned_bytes'] == 300_000_000
assert spec['budgets']['source_wall_seconds'] == 1800
path = ROOT/'protocols/MULTI_ASSET_WINTER_MARKET_SOURCE_20261004_V1.json'
write(path,spec)
out = ROOT/'reports/fast_research/MULTI_ASSET_WINTER_SOURCE_METADATA_20261004_V1.json'
write(out,dict(status='READY_FIXED_WINTER_SOURCE_PROTOCOL_NOT_DOWNLOADED_OR_ACCEPTED',
    task_id=os.environ['COIN_TASK_ID'], protocol=dict(path=str(path.relative_to(ROOT)),sha256=sha(path)),
    source_hashes=pins, new_market_files=72, reused_accepted_files=18,
    warmup_old_sources=100, models_fit=0, market_accounts=0, financial_calls=0,
    new_QA_calls=0, price_payloads_read=0, metadata_source_sha256=sha(__file__)))
print(json.dumps(dict(status='READY_FIXED_WINTER_SOURCE_PROTOCOL_NOT_DOWNLOADED_OR_ACCEPTED',
    protocol=str(path), sha256=sha(path))))
