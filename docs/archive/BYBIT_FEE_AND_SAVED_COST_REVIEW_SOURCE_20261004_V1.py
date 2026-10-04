"""Independent Decimal arithmetic on saved summaries, not a strategy replay."""
import hashlib,json,os
from pathlib import Path
from decimal import Decimal as D
from datetime import UTC,datetime
ROOT=Path('/mnt/d/codex/coin')
def sha(p):
    with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
snapshot=ROOT/'docs/input_evidence/BYBIT_USER_FEE_SNAPSHOT_20261004.json'
pair=ROOT/'reports/fast_research/TURTLE_EXACT_QUANTITY_PAIRED_20261004_V1.json'
assert os.environ['COIN_TASK_ID'] and sha(pair)=='cd71028e5274e60495fd058b658dd96e67708e69e2b3fd83b040edcc65f45244'
rates=json.loads(snapshot.read_bytes());actual=json.loads(pair.read_bytes())
assert rates['mnt_discount_enabled'] is False and rates['effective_from'] is None
checks=[]
for row in rates['product_rates']:
    for side in ('maker','taker'):
        display=D(row[side+'_percent_display'].removesuffix('%'))
        fraction=D(row[side+'_rate_fraction']);bps=D(row[side+'_bps'])
        assert display/100==fraction==bps/10000
    checks.append(dict(product=row['product_id'],maker_fraction=row['maker_rate_fraction'],taker_fraction=row['taker_rate_fraction']))
crypto=next(r for r in rates['product_rates'] if r['product_id']=='DERIVATIVES_CRYPTO_STANDARD')
assert D(crypto['taker_rate_fraction'])==D('.00055') and D(crypto['maker_rate_fraction'])==D('.0002')
arithmetic=[]
for route,fractions,expected in [('TAKER_TAKER',['.00055','.00055'],'11'),('MAKER_MAKER',['.0002','.0002'],'4'),
    ('MAKER_TAKER',['.0002','.00055'],'7.5'),('SPOT_TAKER_TAKER',['.001','.001'],'20')]:
    amount=sum(D('10000')*D(r) for r in fractions);assert amount==D(expected)
    arithmetic.append(dict(route=route,equal_filled_notional_per_leg_USDT='10000',calculated_total_fee_USDT=str(amount)))
attribution=[]
for row in actual['pairs']:
    for recipe,key in [('PYRAMID4','control_summary'),('SINGLE_LAYER','pool_summary')]:
        if key not in row:key='treatment_summary'
        s=row[key];ds=s['decimal_strings'];v=lambda n:D(ds[n])
        gross,fee,execution,funding,net=(v(n) for n in ('gross_PnL_same_quantities','fees_USDT','execution_cost_USDT','funding_USDT','net_PnL'))
        error=net-(gross-fee-execution+funding);assert abs(error)<D('0.0000001')
        extra_bps=D(str(s['cost_scenario']['half_spread_bps']))+D(str(s['cost_scenario']['slippage_bps']))
        mid_turnover=execution/(extra_bps/D(10000));pre_extra=gross-fee+funding
        attribution.append(dict(recipe=recipe,cost=row['cost_id'],funding_interpretation=row['unit_id'],
            gross_USDT=str(gross),commission_USDT=str(fee),execution_USDT=str(execution),signed_funding_USDT=str(funding),
            net_USDT=str(net),bridge_error_USDT=str(error),fixed_old_legs_no_extra_execution_USDT=str(pre_extra),
            same_old_mid_notional_break_even_extra_bps_per_side=str(pre_extra/mid_turnover*10000),
            role='FIXED_RECORDED_SUMMARY_COST_SENSITIVITY_NOT_NEW_ORDERS_OR_NAV_PATH_NOT_EXECUTABLE_CEILING'))
out=ROOT/'reports/fast_research/BYBIT_FEE_AND_D061_COST_REVIEW_20261004_V1.json'
report=dict(status='PASS_RATE_UNIT_AND_SAVED_COST_BRIDGE_NOT_NEW_ACCOUNT_OR_COST_CALIBRATION',
    task_id=os.environ['COIN_TASK_ID'],created_utc=datetime.now(UTC).isoformat(),
    input_sha256={str(snapshot.relative_to(ROOT)):sha(snapshot),str(pair.relative_to(ROOT)):sha(pair)},
    metadata_source_sha256=sha(Path(__file__)),rates=checks,equal_notional_arithmetic=arithmetic,saved_attribution=attribution,
    existing_active_standard_crypto_taker_fraction='.00055',fee_rate_change_required=False,
    BASE27=dict(commission_per_side_bp='5.5',half_spread_per_side_bp='4',slippage_per_side_bp='4',roundtrip_total_bp='27',official_commission_only=False),
    STRESS43=dict(commission_per_side_bp='5.5',half_spread_per_side_bp='8',slippage_per_side_bp='8',roundtrip_total_bp='43',official_commission_only=False),
    screenshot_images_independently_opened=False,current_account_fee_scenario_not_historical_fee_certificate=True,
    pending=['Remove account generic4+4bps lower bound with sourced scenario validation after frozen current replay closes',
             'Independent executable spread/impact evidence; current sample cannot certify past book',
             'Same-symbol same-event official funding unit check'],
    old_results_changed=False,strategy_accounts_run=0,models_fit=0,orders_sent=0,locked_consumed=False,GPU=0,
    investment='CASH',candidate='NONE',long_term_APR='NOT_EVALUABLE')
with out.open('x') as f:json.dump(report,f,indent=2,allow_nan=False);f.write('\n')
print(json.dumps(dict(status=report['status'],attribution_rows=len(attribution),output=str(out))),flush=True)
