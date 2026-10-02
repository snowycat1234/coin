"""Freeze metadata for two fixed official read-only requests; no market IO."""
from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path('/mnt/d/codex/coin')
OUT = ROOT/'protocols/BYBIT_FUNDING_HISTORY_PILOT_20261003_V1.json'
def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

runner = 'scripts/investment/bybit_funding_history_pilot.py'
transport = 'scripts/investment/bybit_funding_windows_transport_v1.ps1'
archive = 'docs/archive/BYBIT_FUNDING_PILOT_PROTOCOL_FREEZER_20261003_V1.py'
fixed = {
    'scripts/investment/funding_semantics_probe.py': 'c433703b696e67b7a279756cee0891cf686111fed24f808e6f0c1992ce5bdf74',
    'scripts/research_v8/registry.py': '081f881f2cb1cdc84b8c098606e9f3235c92fcdd04c0120527bee0d8493068ab',
    'environments/v8/uv.lock': '97335dc3dbb04d7dbc67425f91d4e941a0cfd2c84e5f2adcd852514ec4600de6',
    'protocols/BYBIT_NONVIP_FEE_REFERENCE_20261002.json': 'd6c1e2f5b25dabf4d088edfbccbc35d7154684287ff477c2fc16a14ee5f96b3f',
    'reports/fast_research/FUNDING_SEMANTICS_PROBE_20261003_V2.json': '54febc06b7815e521715c8d70c3e930929a489c7e2a84d1ddae9507a03e4da4d',
    'reports/fast_research/FUNDING_INCOME_DIAGNOSTIC_122D_ACTUAL_20261003_V1.json': '8dc6eb125dfdb5358ba64b4600dfc38025bb08eae40b80469e6247e34442b5e2',
    'reports/fast_research/FUNDING_INCOME_DECIMAL_INDEPENDENT_AUDIT_20261003_V2.json': 'a943e7dadc42bf4ae1742745307a04fdd5ff8e64f30602f3e7009fddc1eb5b1f',
    'reports/fast_research/FUNDING_INCOME_ROOT_MODULE_ACCEPTANCE_20261003_V1.json': 'af9399c66e9c50308d27c3359810914ba501ec95ff77b751887f6c414a922d7f',
}
assert not OUT.exists()
assert Path(__file__).read_bytes() == (ROOT/archive).read_bytes()
for name, expected in fixed.items():
    assert sha(ROOT/name) == expected, name
for name in (runner, transport, archive):
    fixed[name] = sha(ROOT/name)
spec = dict(contract_id='BYBIT_FUNDING_HISTORY_PILOT_20261003_V1',
    experiment_id='BYBIT-FUNDING-HISTORY-PILOT-20261003-V1',
    created_utc=datetime.now(UTC).isoformat(),
    git_commit_at_freeze=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
    source_sha256=fixed[runner], windows_transport_sha256=fixed[transport],
    environment_lock_sha256=fixed['environments/v8/uv.lock'], frozen_sources=fixed,
    fee_reference_path='protocols/BYBIT_NONVIP_FEE_REFERENCE_20261002.json',
    fee_reference_sha256=fixed['protocols/BYBIT_NONVIP_FEE_REFERENCE_20261002.json'],
    run_dir='/home/xflops/coin-state/bybit-funding-history-pilot-20261003-v1',
    output='reports/fast_research/BYBIT_FUNDING_HISTORY_PILOT_ACTUAL_20261003_V1.json',
    endpoint='https://api.bybit.com/v5/market/funding/history', category='linear',
    symbols=['BTCUSDT','ETHUSDT'], startTime_ms=1754006400000,
    endTime_exclusive_ms=1754092800000, endTime_ms=1754092799999, limit=200,
    timeout_seconds=20, max_response_bytes=64000, maximum_requests=2,
    retry_count=0, redirects_allowed=False, stop_on_any_failure=True,
    official_documentary_sources=[
        {'url':'https://bybit-exchange.github.io/docs/v5/guide', 'claim':'api.bybit.com official mainnet host; documented regional IP restrictions; no access bypass'},
        {'url':'https://bybit-exchange.github.io/docs/v5/market/history-fund-rate', 'claim':'linear history with explicit ms start/end; limit<=200; string rate/timestamp; intervals differ'},
        {'url':'https://www.bybit.com/en/help-center/article/Funding-fee-calculation', 'claim':'fee=qty*mark*rate; positive long pays short; intervals may change; settlement vicinity does not guarantee receipt'}],
    documentary_browse_observed_by_utc='2026-10-02T17:32:44Z',
    documentary_browse_time_scope='CLOCK_READ_AFTER_PRIMARY_WEB_TOOL_READ_NOT_EXACT_RETRIEVAL_TIME',
    unit_interpretation_scope='BYBIT_DOCUMENTARY_RATIO_CONVENTION_ONLY_NO_BINANCE_OR_CASH_CERTIFICATION',
    coverage_scope='NONEMPTY_FIXED_DAY_RESPONSE_BELOW_CAP_NOT_HISTORICAL_COMPLETENESS_CERTIFICATION',
    data_role='DEVELOPMENT_SOURCE_PILOT_ONLY_NOT_FUTURE_OR_HOLDOUT',
    resource_budget={'new_owned_bytes_max':2000000,'wall_seconds_max':180,'RAM_shared_max_bytes':5000000000,
        'Windows_transport_outside_Linux_cgroup':True,'Windows_peak_measurement_separate':True,
        'GPU':0,'swap':0,'disk_combined_max_bytes':40000000000,
        'last_actual_disk_scan_bytes':19413115004,'last_actual_scan_ended_utc':'2026-10-02T17:00:09.997777+00:00',
        'last_actual_scan_is_not_current_instant':True},
    forbidden=['latest_or_locked_market_request','retry_or_alternate_host','keys_or_orders','price_arrays',
        'funding_income_calculation','net_APR_or_account_cash_certification','new_downloader_framework'])
with OUT.open('x') as writer:
    json.dump(spec,writer,indent=2,ensure_ascii=False,allow_nan=False); writer.write('\n')
print(json.dumps({'protocol_path':str(OUT),'sha256':sha(OUT),'sources':len(fixed)}))
