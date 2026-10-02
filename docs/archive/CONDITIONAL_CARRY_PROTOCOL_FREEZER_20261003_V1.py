"""Freeze one fixed account before its new synthetic or historical math."""
from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path
import subprocess
from scripts.investment import conditional_carry_account as carry

ROOT=Path('/mnt/d/codex/coin');sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
ARCHIVE='docs/archive/CONDITIONAL_CARRY_PROTOCOL_FREEZER_20261003_V1.py'
OUT=ROOT/'protocols/CONDITIONAL_CARRY_ACCOUNT_122D_20261003_V1.json'
assert not OUT.exists() and Path(__file__).read_bytes()==(ROOT/ARCHIVE).read_bytes()
basis_path='protocols/BASIS_RISK_DIAGNOSTIC_20261003_V1.json'
funding_path='protocols/FUNDING_INCOME_DIAGNOSTIC_122D_20261003_V1.json'
accepted=json.loads((ROOT/'reports/GITHUB_BASIS_RISK_SOURCE_BINDING_20261003_V1.json').read_bytes())
assert sha(ROOT/basis_path)==accepted['source_hashes'][basis_path]
basis=json.loads((ROOT/basis_path).read_bytes());funding=json.loads((ROOT/funding_path).read_bytes())
fixed={}
for previous in (basis['frozen_sources'],funding['frozen_sources'],carry.native.PINS):
    for name,digest in previous.items():
        assert name not in fixed or fixed[name]==digest,name
        assert sha(ROOT/name)==digest,name
        fixed[name]=digest
for name in (ARCHIVE,'scripts/investment/conditional_carry_account.py',carry.TEST,
             basis_path,funding_path,'scripts/investment/bybit_spot_adapter.py','src/quant/metrics.py',
             'protocols/BYBIT_SPOT_RECEIVED_ASSET_ADAPTER_V1.json'):
    fixed[name]=sha(ROOT/name)
spec=dict(contract_id='CONDITIONAL_CARRY_ACCOUNT_V1',created_utc=datetime.now(UTC).isoformat(),
    git_commit_at_freeze=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
    classification='SEEN_FIXED_FULL_PERIOD_CONDITIONAL_ACCOUNT_SCREENING_NOT_NATIVE_OR_LONG_TERM_APR',
    research_question='Under fixed conservative costs and capital, can matched net-base carry leave net account return?',
    decision='D029',rules=carry.RULES,period_start='2025-08-01',period_end_exclusive='2025-12-01',
    symbols=list(carry.SYMBOLS),source_calendar=list(carry.MONTHS),expected_price_files=24,expected_funding_files=8,
    expected_minutes_per_asset=175680,expected_funding_events=732,
    source_options_path=basis['source_options_path'],source_options_sha256=basis['source_options_sha256'],
    funding_contract_path=funding_path,funding_contract_sha256=sha(ROOT/funding_path),
    fee_reference_profile_path=carry.native.PROFILE_PATH,
    fee_reference_profile_sha256=carry.native.PINS[carry.native.PROFILE_PATH],frozen_sources=fixed,
    required_smoke_receipt='reports/fast_research/CONDITIONAL_CARRY_ACCOUNT_TINY_20261003_V1.json',
    required_smoke_scope='SAME_PROTOCOL_CODE_ACTUALLY_CLOSED_EXIT0_BEFORE_MARKET_ARRAYS',
    maximum_new_owned_bytes=50000000,maximum_wall_seconds=600,
    independent_cash_absolute_tolerance_USDT=1e-7,independent_ratio_absolute_tolerance=1e-10,
    funding_rate_unit='UNCONFIRMED',conditional_fraction_assumption=True,
    market_inputs='EXISTING_BINANCE_OFFICIAL_MINUTE_SPOT_MARK_INDEX_AND_SIGNED_FUNDING',
    funding_charge_mark_and_execution_close_proxies_certified=False,native_Bybit_settlement_proven=False,
    risk_comparison='COMMON_INITIAL_CAPITAL_AND_COST_EXPOSURE_CAPS_ONLY_OLD_VOL_CAPACITY_REAL_MMR_NOT_EQUIVALENT',
    isolated_nonpositive_equity='FAIL_WITH_WITNESS_NO_CROSS_LEG_CREDIT_OR_FICTIONAL_LIQUIDATION',
    funding_within_5s_entry_or_exit='REPORT_UNCERTAIN_WITNESSES_NO_POSTHOC_EVENT_SELECTION',
    APR_interpretation='DESCRIPTIVE_SAMPLE_COMPOUNDING_ONLY_NOT_LONG_TERM_NET_APR_EVIDENCE',
    RAM_shared_max_bytes=5000000000,swap=0,GPU=0,disk_combined_max_bytes=40000000000,
    forbidden=['API_OR_DOWNLOAD','LOCKED_PRICE_IO','MODEL_FIT_HPO','OLD_QA_OR_GREEN_REPLAY','MONTHLY_REENTRY_OR_SELECTION',
               'LOWER_COST_OR_HIGHER_LEVERAGE_AFTER_RESULTS','REAL_ORDERS_KEYS_PAID_SERVICES','OVERWRITE_FROZEN_EVIDENCE'])
carry.verify_spec(spec)
with OUT.open('x') as w:json.dump(spec,w,indent=2,ensure_ascii=False);w.write('\n')
print(json.dumps(dict(protocol=str(OUT),sha256=sha(OUT),frozen_files=len(fixed),market_arrays_read=False)))
