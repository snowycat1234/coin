"""Freeze one finite daily-rule contrast on already accepted continuous sources."""
import hashlib,json,os
from pathlib import Path
from datetime import UTC,datetime
from quant.paths import ROOT,STATE
from scripts.investment import multi_asset_data as md
from scripts.investment import donchian_daily_pool_target as dc
assert os.environ['COIN_TASK_ID']
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,v):
    with p.open('x') as f:json.dump(v,f,indent=2,allow_nan=False);f.write('\n')
run=STATE/'d064-longspan-input-binding-20261004-v1';run.mkdir()
m=md.compose_long_span_manifest(md.LONG_SPAN_MANIFEST_REFS)
mp=run/'INPUT_MANIFEST.json';write(mp,m)
assert len(m['market_records'])==300 and len(m['daily_records'])==70 and len(m['normalized_source_hashes'])==370
base=json.loads((ROOT/'protocols/MULTI_ASSET_SPRING_HOLD_TEN_20261004_V1.json').read_bytes())
pins={n:sha(ROOT/n) for n in base['source_hashes'] if 'METADATA_SOURCE' not in n}
for n in ['scripts/investment/bybit_cost_inputs.py','scripts/investment/donchian_daily_pool_target.py',
          'third_party/jesse_example_donchian/donchian_original.py','third_party/jesse_example_donchian/donchian_indicator_original.py',
          'third_party/jesse_example_donchian/LICENSE','tests/test_donchian_daily_pool.py',
          'docs/archive/CONTINUOUS_DAILY_TREND_METADATA_SOURCE_20261004_V1.py']:
    pins[n]=sha(ROOT/n)
test=ROOT/'reports/fast_research/DONCHIAN_DAILY_SEMANTICS_SYNTHETIC_20261004_V1.json'
t=json.loads(test.read_bytes());assert t['test_exit_code']==0 and t['status'].startswith('PASS_')
pins[test.relative_to(ROOT).as_posix()]=sha(test)
prepared=[]
for recipe in ['HOLD_TWO','HOLD_TEN','DONCHIAN_TEN']:
    p=dict(base);p.update(source_hashes=pins,start='2024-09-01T00:00:00+00:00',
        end_exclusive='2025-07-01T00:00:00+00:00',period_days=303,
        account_path='CONTINUOUS_SHARED_ACCOUNT_SEP_JUN_303D',
        data_role='SEEN_DEVELOPMENT_CONTINUOUS_ACCEPTED_TEN_MONTH_MANIFEST',
        data_role_note='One initial10k continuous shared wallet, no quarterly NAV concatenation or reset',
        data_manifest=dict(path=str(mp),sha256=sha(mp)),source_acceptances=m['source_acceptances'],
        experiment_id='D064-'+recipe+'-SEPJUN303-20261004',
        warmup='Accepted70 FebAug daily only; 300score sources; causal monthly-minute daily reduction',
        budget=dict(owned_bytes=400000000,wall_seconds=1800,peak_RSS_bytes=3000000000),
        research_budget=dict(total_new_STATE_bytes=1500000000,new_actual_accounts=12,
            new_independent_accounts=12,HPO=0,models_fit=0,new_recipes=1,
            financial_owned_bytes_per_run=100000,financial_wall_seconds=1800,financial_peak_RSS_bytes=1500000000),
        independent_reference_pre_market_sha256=pins['scripts/investment/multi_asset_financial_audit.py'],
        economic_comparer_pre_market_sha256=pins['scripts/investment/compare_multi_asset_portfolios.py'],
        question='Does daily prior20 breakout/SMA200 entry filtering add net value over stable HOLD on one continuous303day path?',
        success_rule='Truthfully complete or halt303day account, correct independent targets and recorded money/risk; no positive-profit gate',
        created_utc=datetime.now(UTC).isoformat())
    if recipe=='DONCHIAN_TEN':p.update(strategy=dc.STRATEGY_ID,signal='PRIOR20_DONCHIAN_SMA200_ENTRY_LONG_FLAT',strategy_rules=dc.RULES)
    stem='CONTINUOUS_DAILY_TREND_'+recipe+'_20261004_V1';pp=ROOT/'protocols'/(stem+'.json');write(pp,p)
    prepared.append(dict(recipe=recipe,protocol=str(pp),sha256=sha(pp),pool_id=base['pools'][0 if recipe=='HOLD_TWO' else 1]['id']))
write(ROOT/'reports/fast_research/CONTINUOUS_DAILY_TREND_METADATA_20261004_V1.json',dict(
    status='READY_FINITE_CONTINUOUS303_ACCOUNTS_NOT_RUN',task_id=os.environ['COIN_TASK_ID'],
    prepared=prepared,manifest_sha256=sha(mp),source_files=370,new_downloads=0,new_QA=0,accounts=0))
print(json.dumps(prepared),flush=True)
