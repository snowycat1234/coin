"""Bind single candidate and common original-code closure without history."""
import hashlib,json
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parent
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(Path(p).read_text())
def write(p,v):
    with Path(p).open('x') as f:json.dump(v,f,indent=2,sort_keys=True,allow_nan=False);f.write('\n')
def main():
    shadow=read(ROOT/'coin_causal_headroom_shadow_20261013/INPUTS.json')
    cases=[]
    for desc in shadow['cases']:
        if desc['year']==2025:continue
        c=dict(desc['case']);c['protective_enabled']=True
        c['baseline_state_local_locator']=desc['state']
        c['baseline_files_SHA256']={name:sha(ROOT/desc['state']/name) for name in ('ACCOUNT.json','RESULT.json','BINDING.json','MINUTE_NUMERIC.json','recovery/POINTER.json')}
        c['feature_manifest_SHA256']=sha(HERE/'features'/f"Y{c['year']}.json")
        if c['year']==2021:
            c['initial_daily_sizing_cube_locator']='coin_cs_sma_recovery_20261013/inputs/Y2023.npz'
            c['initial_daily_sizing_cube_SHA256']='1c500e9d5b0244a1daaabc597d7cc5ae97a21a156cc42d8a44a1504b821e599f'
        if c['year']==2024:c['derived_csv_SHA256']=sha(ROOT/'coin_expanded_coverage_20261013/derived_mark/DERIVED_MARK_OHLC.csv')
        cases.append(c)
    plan={'case_count':3,'cases':cases,'modes':['HEADROOM'],
        'fine_profile_SHA256':sha(ROOT/'coin_quantity_resolution_20261013/FINE_PROFILE.json'),
        'new_historical_wallets_executed':0,'new_fits':0,'new_source_requests':0,
        '2025_noop_proof_SHA256':sha(HERE/'Y2025_NO_OP_PROOF.json'),
        'execution_split':{'local_serial':[2021,2023],'cloud_single':[2024]}}
    if (HERE/'CASE_BINDINGS.json').exists():
        if read(HERE/'CASE_BINDINGS.json')!=plan:raise ValueError('Archive old case binding before changing freeze')
    else:write(HERE/'CASE_BINDINGS.json',plan)
    deps={}
    portbase='coin_native_half_mix_20261013/repo/'
    for p,h in read(ROOT/portbase/'research/static50-sma-20261013/LOCAL_CODE_MANIFEST.json')['sha256'].items():deps[portbase+p]=h
    manifest_path=portbase+'research/static50-sma-20261013/LOCAL_CODE_MANIFEST.json'
    deps[manifest_path]=sha(ROOT/manifest_path)
    policy='coin_margin_protective_policy_20261013/'
    fine='coin_quantity_resolution_20261013/'
    for name in ('FREEZE.json','PROTOCOL.json','RUN_MANIFEST.json','preflight_run_plan.py','protective_policy.py','test_policy_synthetic.py'):deps[policy+name]=sha(ROOT/policy/name)
    for name in (*read(ROOT/fine/'FROZEN_CODE.json')['files_SHA256'],'freeze_bootstrap.py','FROZEN_CODE.json','REVIEW_RECEIPT.json'):deps[fine+name]=sha(ROOT/fine/name)
    for name in ('coin_margin_protective_runner_20261013/run_guard_cases.py',
                 'coin_2021_strategy_comparison_20261013/GUARD_PACK_RELEASE.json'):
        deps[name]=sha(ROOT/name)
    for name,h in deps.items():
        if sha(ROOT/name)!=h:raise ValueError('Original dependency hash changed '+name)
    files=['CASE_BINDINGS.json','PROTOCOL.json','headroom_buffer.py','headroom_policy.py','feature_tape.py',
           'source_adapter.py','run_cases.py','preflight.py','resource_gate.py','run_budget.py','worker_bounds.py',
           'prepare_features.py','prepare_freeze.py','test_synthetic.py','Y2025_NO_OP_PROOF.json','FEATURE_PREPARATION.json']
    files += [f'features/Y{y}.json' for y in (2021,2023,2024,2025)]
    write(HERE/'FROZEN_CODE.json',{'candidate':'causal_execution_headroom_full_exit_v1',
        'status':'PREPARED_ONLY_ZERO_HISTORY_PENDING_REVIEW_AND_GO',
        'bootstrap_SHA256':sha(HERE/'freeze_candidate.py'),'files_SHA256':{p:sha(HERE/p) for p in files},
        'dependencies_SHA256':deps,'new_historical_wallets_executed':0})
    print('CANDIDATE_FROZEN',sha(HERE/'FROZEN_CODE.json'),'dependencies',len(deps))
if __name__=='__main__':main()
