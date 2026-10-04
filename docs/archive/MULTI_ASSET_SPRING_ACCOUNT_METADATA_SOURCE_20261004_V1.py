"""Three fixed shared-capital recipes; accepted sources only, no science yet."""
import hashlib,json,os
from pathlib import Path
from datetime import UTC,datetime
ROOT=Path('/mnt/d/codex/coin');STATE=Path('/home/xflops/coin-state')
def sha(p):
    with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def small(p):
    p=Path(p);assert p.is_file() and not p.is_symlink() and p.stat().st_size<4_000_000
    return json.loads(p.read_bytes())
def write(p,v):
    with p.open('x') as f:json.dump(v,f,indent=2,allow_nan=False);f.write('\n')
assert os.environ['COIN_TASK_ID']
mp=STATE/'d062-multiasset-spring-source-acceptance-20261004-v1/INPUT_MANIFEST.json';m=small(mp)
cap_path=ROOT/'reports/fast_research/MULTI_ASSET_SPRING_SOURCE_ACCEPTANCE_20261004_V1.json';cap=small(cap_path)
assert m['status']=='PASS_D062_SELECTED_PORTFOLIO_SPRING_SOURCE_BINDING_NOT_ECONOMICS'
assert cap['status']=='PASS_D062_FIXED_POOL_SPRING_SOURCE_FORMAT_ONLY' and cap['actual_exit_code']==0
task=small(STATE/'task-progress'/('task-'+cap['binding']['task_id']+'.json'))
assert task['status']=='completed' and task['exit_code']==0
assert len(m['market_records'])==120 and len(m['normalized_source_hashes'])==250
assert (m['start_us'],m['end_us'])==(1740787200000000,1751328000000000)
common=small(ROOT/'protocols/MULTI_ASSET_WINTER_TEN_EQUAL_20261004_V3.json')
momentum=small(ROOT/'protocols/MOMENTUM_CASH_DECFEB90_20261004_V1.json')
allowed={'src/quant/data.py','scripts/investment/multi_asset_data.py','scripts/investment/multi_asset_portfolio.py'}
head_changes={'scripts/investment/public_sma_perpetual.py':'0107ce0cb410280be3435eb6b7264e2e3e3e80c76b03cfebdfd7453124126682',
              'scripts/investment/perpetual_directional.py':'a16301eb2ac70327df808884ae42f78705c5fed07273b867db82408203878138'}
pins={}
for n,h in common['source_hashes'].items():
    now=sha(ROOT/n);assert n in allowed or now==head_changes.get(n,h),n;pins[n]=now
for n in ('scripts/investment/multi_asset_financial_audit.py','scripts/investment/compare_multi_asset_portfolios.py',
          'docs/archive/MULTI_ASSET_SPRING_ACCOUNT_METADATA_SOURCE_20261004_V1.py'):
    pins[n]=sha(ROOT/n)
test_path=ROOT/'reports/fast_research/MULTI_ASSET_DECIMAL_TAIL_SYNTHETIC_20261004_V1.json'
test=small(test_path);assert test['status']=='PASS_BOUNDED_RESEARCH_TESTS_SYNTHETIC_NOT_MARKET_RESULT'
assert sha(test_path)=='83bedcdda671327d6784f0a5dd6cf9c67afc247248ff97b21d9d5b0de6a36ecc'
pins[test_path.relative_to(ROOT).as_posix()]=sha(test_path)
prepared=[]
for recipe,pool in (('HOLD_TWO',common['pools'][0]),('HOLD_TEN',common['pools'][1]),('MOMENTUM_TEN',common['pools'][1])):
    p=dict(common);p.update(source_hashes=dict(pins),pools=common['pools'],
        start='2025-03-01T00:00:00+00:00',end_exclusive='2025-07-01T00:00:00+00:00',period_days=122,
        experiment_id='D062-'+recipe+'-MARJUN122-20261004',
        account_path='CONTINUOUS_SHARED_ACCOUNT_MAR_JUN_122D',
        data_role='SEEN_DEVELOPMENT_CONTINUOUS_THIRD_WINDOW_MANIFEST',
        data_role_note='Third complete seen development window, one initial10k shared wallet per scenario; no resets/stitching.',
        data_manifest=dict(path=str(mp),sha256=sha(mp)),source_acceptances=[m['source_acceptance']],
        warmup='Accepted70daily +60SepFebminute monthly sources; causal daily reduction, no source QA repeated',
        independent_reference_pre_market_sha256=pins['scripts/investment/multi_asset_financial_audit.py'],
        economic_comparer_pre_market_sha256=pins['scripts/investment/compare_multi_asset_portfolios.py'],
        budget=dict(owned_bytes=300000000,wall_seconds=1800,peak_RSS_bytes=3000000000),
        research_budget=dict(total_new_STATE_bytes=1500000000,new_actual_accounts=12,new_independent_accounts=12,
            HPO=0,models_fit=0,new_recipes=0,financial_owned_bytes_per_run=100000,financial_wall_seconds=1800,
            financial_peak_RSS_bytes=1500000000),
        question='Does fixed pool or fixed past30 cash signal improve paired money/risk in a third complete market state?',
        success_rule='Complete or truthfully halted122day accounts, independent recorded account checks, pool and signal pair; no positive-profit gate',
        created_utc=datetime.now(UTC).isoformat())
    if recipe=='MOMENTUM_TEN':
        for key in ('strategy','signal','strategy_rules','momentum_parameters'):p[key]=momentum[key]
        n='scripts/investment/momentum_cash_pool_target.py';assert sha(ROOT/n)==momentum['source_hashes'][n]
        p['source_hashes'][n]=sha(ROOT/n)
    stem='MULTI_ASSET_SPRING_'+recipe+'_20261004_V1'
    path=ROOT/'protocols'/ (stem+'.json');write(path,p)
    prepared.append(dict(recipe=recipe,protocol=str(path),sha256=sha(path),pool_id=pool['id'],symbols=pool['symbols']))
write(ROOT/'reports/fast_research/MULTI_ASSET_SPRING_ACCOUNT_METADATA_20261004_V1.json',dict(
    status='READY_THREE_PREDECLARED_SHARED_ACCOUNT_RECIPES_NOT_RUN',task_id=os.environ['COIN_TASK_ID'],
    prepared=prepared,source_capability=cap['binding']['task_id'],manifest_sha256=sha(mp),accounts=0))
print(json.dumps(dict(status='READY_THREE_RECIPES',prepared=prepared)),flush=True)
