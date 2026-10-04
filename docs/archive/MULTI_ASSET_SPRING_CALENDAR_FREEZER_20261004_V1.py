"""Freeze one necessary new date/eligibility counterexample, without market rows."""
import hashlib,json,os
from pathlib import Path
from datetime import UTC,datetime
ROOT=Path('/mnt/d/codex/coin')
def sha(p):
    with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
assert os.environ['COIN_TASK_ID']
old=json.loads((ROOT/'protocols/TURTLE_EXACT_QUANTITY_SYNTHETIC_20261004_V1.json').read_bytes())
changes={'scripts/investment/multi_asset_data.py','scripts/investment/multi_asset_financial_audit.py',
         'scripts/investment/multi_asset_portfolio.py','scripts/investment/multi_asset_official_transport.ps1'}
pins={}
for name,h in old['frozen_sources'].items():
    if name.startswith('tests/') or 'TURTLE_EXACT_QUANTITY_SYNTHETIC_FREEZER' in name:continue
    now=sha(ROOT/name);assert name in changes or now==h,name;pins[name]=now
test='tests/test_spring_portfolio_causal_calendar.py'
for name in (test,'scripts/investment/multi_asset_data.py','scripts/investment/multi_asset_financial_audit.py',
    'scripts/investment/multi_asset_source_acceptance.py','docs/archive/MULTI_ASSET_SPRING_CALENDAR_FREEZER_20261004_V1.py'):
    pins[name]=sha(ROOT/name)
spec=dict(ready_to_execute=True,tests=[test],frozen_sources=pins,
    calculation_rules=dict(past_completed_days=200,no_future_score_prices=True,calendar_months=4,
        real_UTC_days=122,required_minutes=175680,missing_warm_day_is_ineligible=True),
    fee_profile=dict(scope='METADATA_ELIGIBILITY_ONLY_NO_FILLS_NO_COST_CHANGE'),
    new_owned_bytes=10000000,maximum_wall_seconds=120,maximum_shared_RAM_bytes=5000000000,
    CPU_threads=2,models_fit=0,orders_sent=0,locked_consumed=False,GPU=0,old_tests_replayed=False,
    test_scope='ONE_NEW_SPRING_COMPLETE_CALENDAR_AND_PAST200_AVAILABILITY_CASE',
    freeze_task_id=os.environ['COIN_TASK_ID'],created_utc=datetime.now(UTC).isoformat())
p=ROOT/'protocols/MULTI_ASSET_SPRING_CALENDAR_SYNTHETIC_20261004_V1.json'
with p.open('x') as f:json.dump(spec,f,indent=2);f.write('\n')
print(json.dumps(dict(protocol=str(p),sha256=sha(p),sources=len(pins))),flush=True)
