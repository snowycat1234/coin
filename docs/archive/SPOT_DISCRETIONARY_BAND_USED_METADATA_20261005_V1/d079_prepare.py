import hashlib,json,subprocess
from pathlib import Path
R=Path('/mnt/d/codex/coin')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
parent=subprocess.check_output(['git','rev-parse','HEAD'],cwd=R,text=True).strip()
assert parent=='6ef22565d61f0771493f2e91a8bf1bc42e00b3d6'
p=json.loads((R/'protocols/SPOT_DEFENSIVE_BLEND_20261005_V1.json').read_bytes())
oldcontrol=p['spot_control']
p.update(experiment_id='D079_SPOT_DISCRETIONARY_BAND50',module='D079',parent_commit=parent,
    question='Can a fixed50USDT discretionary rebalance band improve same Spot defensive recipe net economics without suppressing signal exits, risk reductions or raising actual risk?',
    discretionary_rebalance_min_notional=50, economic_reference=oldcontrol,
    spot_control={'path':str(R/'reports/fast_research/SPOT_DEFENSIVE_BLEND_20261005_V1.json'),
        'sha256':sha(R/'reports/fast_research/SPOT_DEFENSIVE_BLEND_20261005_V1.json')},
    hypothesis='Small optional target-chasing changes consume avoidable costs; evaluate whole new wallet rather than delete saved costs.',
    band_policy={'USDT':50,'first_target_protected':True,'any_portfolio_component_raw_vector_change_protected':True,
        'asset_eligibility_change_protected':True,'any_asset_component_risk_target_strict_decrease_protected':True,
        'first_inventory_entry_zero_target_terminal_forced_risk_cap_breach_started_partial_protected':True,
        'measurement':'FULL_REQUEST_AT_CURRENT_EXECUTION_OPEN_NAV_BEFORE_CAPACITY_NOT_FILL_AMOUNT',
        'unknown_declaration':'PROTECTED','comparison_operator':'ABS_REQUEST_STRICTLY_LESS_THAN_50'},
    comparison='Same fixed defensive targets/Spot inputs/wallet/costs/10k/caps/303 dates, only explicit discretionary band changes execution. Saved HOLD8 additional reference. No same-risk alpha assumption.',
    success_decision='Adopt development band only if net improves both costs and minute drawdown and realized daily volatility do not worsen versus original blend, with all protection/account/caps checks. Otherwise retain original. No investment qualification.',
    stop_rule='One threshold50, two complete wallets. Any source/target/account/protection mismatch or observed caps violation fails. No threshold grid, no free residual, no deleted dates/costs.',
    budget={'actual_spot_wallets':2,'saved_controls':4,'fits':0,'downloads':0,'API':0,'HPO':0,'wall_seconds':1800,'owned_bytes':100000000})
for n in ['tests/test_spot_discretionary_band.py','scripts/investment/spot_saved_economic_diagnostics.py']:
    p['source_hashes'][n]=sha(R/n)
for n in p['source_hashes']:p['source_hashes'][n]=sha(R/n)
from scripts.research_v8.registry import FIELDS,append_event
for version,identity,status in [('V1','f384d5c4e33e404b8df134bd08badb7e','FAILED_FIXTURE_ORDER_ASSUMPTION_14_PASS_1_FAIL'),
    ('V2','3b94bd6b58314007873407cb42b6e9f5','15_NECESSARY_FIXTURES_PASS')]:
    task=json.loads((Path('/home/xflops/coin-state/task-progress')/f'task-{identity}.json').read_bytes())
    assert task['exit_code']==(1 if version=='V1' else 0) and task['ended_at']
    event=dict.fromkeys(FIELDS);event.update(event_id='D079:FIXTURES:'+version,event_type='OPERATIONAL_RESEARCH_RESULT',
        experiment_id=p['experiment_id'],git_commit=parent,success_failure=status,model_family='NORMAL_SPOT_BAND_INTERFACE',
        task_id=identity,artifact_path='reports/SPOT_DISCRETIONARY_BAND_TESTS_20261005_'+version+'.xml',
        artifact_sha256=sha(R/('reports/SPOT_DISCRETIONARY_BAND_TESTS_20261005_'+version+'.xml')),
        test_source_sha256=sha(R/('.cache/d079_test_used_v1.py' if version=='V1' else 'tests/test_spot_discretionary_band.py')),
        account_source_sha256=p['source_hashes']['src/quant/backtest.py'],fits=0,
        reason_for_next_experiment='V1 test had cap restored earlier by sorted sell; only fixture order fixed, account unchanged' if version=='V1' else 'Proceed one fixed50 band whole wallet contrast')
    append_event(R/'reports/experiment_registry.jsonl',event)
with (R/'protocols/SPOT_DISCRETIONARY_BAND50_20261005_V1.json').open('x') as f:json.dump(p,f,indent=2);f.write('\n')
print(json.dumps({'status':'D079_FIXED_BEFORE_RESULTS','sha256':sha(R/'protocols/SPOT_DISCRETIONARY_BAND50_20261005_V1.json')}))
