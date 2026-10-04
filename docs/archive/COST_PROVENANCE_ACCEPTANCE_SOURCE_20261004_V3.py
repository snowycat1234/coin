"""Summarize existing closed synthetic economic artifacts; no new account run."""
import hashlib,json,os,shutil
from datetime import UTC,datetime
from pathlib import Path
from quant.paths import ROOT,STATE
assert os.environ['COIN_TASK_ID']
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p): return json.loads(p.read_bytes())
reports=[]
for version,code,count in [('V1',1,6),('V2',0,7)]:
    p=ROOT/f'reports/fast_research/COST_PROVENANCE_ACCOUNT_SYNTHETIC_20261004_{version}.json'
    r=read(p);t=read(STATE/'task-progress'/('task-'+r['binding']['task_id']+'.json'))
    assert t['exit_code']==code and t['ended_at'] and r['junit_counts']['tests']==count
    reports.append(dict(path=p.relative_to(ROOT).as_posix(),sha256=sha(p),task_id=t['id'],exit_code=code,junit=r['junit_counts'],elapsed_seconds=r['elapsed_seconds'],peak_RSS_bytes=r['peak_RSS_bytes'],owned_bytes=r['owned_bytes']))
work=STATE/'d063-cost-provenance-synthetic-20261004-v2'
paths=sorted({p.resolve() for p in (work/'pytest').glob('test_active_runner_signed_tar*/actual_runner_synthetic_economics.json')})
assert len(paths)==1
cases=read(paths[0]);assert len(cases)==2
small=[]
for case in cases:
    s=case['summary'];assert s['completed_minutes']==s['required_minutes']==2880 and s['terminal_cash_realized']
    assert s['contract']['cost_provenance']['historical_execution_certified'] is False
    for artifact in case['artifact_hashes']['artifacts'].values():assert sha(Path(artifact['path']))==artifact['sha256']
    small.append({k:s[k] for k in ['cost_scenario','NAV','net_PnL','gross_PnL_same_quantities','fees_USDT','execution_cost_USDT','spread_cost_USDT','slippage_cost_USDT','funding_USDT','trade_legs','terminal_cash_realized','configured_nominal_roundtrip_bps','maximum_actual_gross_weight','maximum_actual_asset_weights']})
old=read(ROOT/'protocols/COST_PROVENANCE_ACCOUNT_SYNTHETIC_20261004_V1.json')['frozen_sources']
archives={
 'tests/test_cost_provenance_account.py':'docs/archive/COST_PROVENANCE_PRE_REPAIR_TEST_SOURCE_20261004_V1.py',
 'scripts/investment/perpetual_directional.py':'docs/archive/COST_PROVENANCE_PRE_CASH_FIX_RUNNER_20261004_V1.py',
 'scripts/investment/bybit_cost_inputs.py':'docs/archive/COST_PROVENANCE_PRE_CASH_FIX_INPUT_SOURCE_20261004_V1.py'}
for name,archive in archives.items():assert sha(ROOT/archive)==old[name]
probe=[]
for name in ['FUNDING_SEMANTICS_PROBE_20261003_V2','BYBIT_PUBLIC_SPEC_PROBE_20261003_V2']:
    p=ROOT/'reports/fast_research'/(name+'.json');r=read(p)
    probe.append(dict(path=p.relative_to(ROOT).as_posix(),sha256=sha(p),status=r['status'],task_id=r['binding']['task_id']))
result=dict(status='PASS_COST_IDENTITY_CASH_METADATA_AND_SYNTHETIC_ACTIVE_ACCOUNT_NOT_MARKET_CALIBRATION',created_utc=datetime.now(UTC).isoformat(),task_id=os.environ['COIN_TASK_ID'],existing_test_runs=reports,synthetic_runner_cases=small,source_recovery_archives=archives,independent_static_review=dict(path='reports/COST_PROVENANCE_INDEPENDENT_REVIEW_20261004_V1.md',sha256=sha(ROOT/'reports/COST_PROVENANCE_INDEPENDENT_REVIEW_20261004_V1.md')),preserved_access_limit_evidence=probe,new_API_requests=0,market_replays=0,model_fits=0,HPO_trials=0,orders_sent=0,locked_consumed=False,user_risk_or_capital_changed=False,hand_10k_each_leg=dict(synthetic_fixture_capital_USDT=100000,standard_taker_commission_roundtrip_USDT=11,execution_2_plus_1_bp_roundtrip_USDT=6,net_USDT=-17,not_market_cost_estimate=True),next='Reuse existing daily inputs for one low-turnover causal timeframe check and a finite continuous comparison; no new market job started',investment='CASH',candidate='NONE',long_term_APR='NOT_EVALUABLE',limitations='Source-bound declared homogeneous fee zones, TAKER only; snapshot is current account scenario on historical market, not historical fee proof. Synthetic zero/additional friction is optimistic correctness reference, not a mathematical strategy bound.')
with (ROOT/'reports/fast_research/COST_PROVENANCE_ACCOUNT_ACCEPTANCE_20261004_V1.json').open('x') as f:json.dump(result,f,indent=2);f.write('\n')
print(json.dumps(dict(status=result['status'],synthetic_cases=small),ensure_ascii=False),flush=True)