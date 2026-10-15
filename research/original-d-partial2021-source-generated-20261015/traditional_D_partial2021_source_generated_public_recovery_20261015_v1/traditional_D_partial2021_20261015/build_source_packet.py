"""Explicit SOURCE-only target/manifest preparation; never historical admission."""
import os
for k in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS','POLARS_MAX_THREADS','VECLIB_MAXIMUM_THREADS'):os.environ[k]='1'
os.sched_setaffinity(0,{6})
from pathlib import Path
import json
import partial_source as s
import numpy as np
HERE=s.HERE;ROOT=s.ROOT

def write(path,v):path.write_bytes(json.dumps(v,indent=2,sort_keys=True,allow_nan=False).encode()+b'\n')
def main():
    destination=HERE/'source_targets_attempt002'
    if destination.exists():raise ValueError('EXCLUSIVE_SOURCE_PACKET_REQUIRED')
    p=s.project();destination.mkdir()
    dependencies=[]
    frozen=ROOT/'traditional_three_tier_freeze_20261015'
    for name in ('frozen_grid.py','native_runtime.py','historical_entry.py','SOURCE_PROVENANCE.json',
            'NATIVE_SOURCE_PROVENANCE.json','FROZEN_SPEC.json','causal_mark_quality.py','annual_reporting.py'):
        dependencies.append(frozen/name)
    dependencies.extend(x for x in (frozen/'sources').rglob('*') if x.is_file() and x.suffix in ('.py','.json'))
    for directory,names in (
        ('bounded_account_continuation_20261015',('continuation.py','headroom_buffer.py','POLICY.json','QUANTITY_PROFILE.json','PRIMITIVE_PINS.json','vendor_quant/perpetual_account.py','vendor_quant/execution_contract.py','vendor_quant/bybit_isolated_account.py')),
        ('bounded_native_continuation_v2_20261015',('integration.py','continuation_entry.py','run_finite.py')),
        ('bounded_native_continuation_guard50_exit_20261015',('guard50_exit.py','guard50_exit_entry.py','run_guard50_exit.py')),
        ('bounded_native_continuation_guard50_exit_expansion_20261015',('expansion.py','run_expansion.py','saved_native_reconciliation.py'))):
        dependencies.extend(ROOT/directory/name for name in names)
    pins={str(x.relative_to(ROOT)):{'SHA256':s.sha(x.read_bytes()),'bytes':x.stat().st_size} for x in sorted(set(dependencies))}
    write(HERE/'DEPENDENCY_PINS.json',pins)
    execution=s.jsha(dict(frozen_native_code=pins,partial_D_sha=s.sha((HERE/'partial_d.py').read_bytes()),
        source_identity=p['source_identity'],calendar=[s.START,s.END],cost='BASE27',wallet='FRESH10000',
        quality_sidecar_sha=s.sha(p['sidecar_raw']),covariance_raw_sha=s.sha(p['covariance'].tobytes()),
        tier_limits=[vars(t) for t in s.g.TIERS],funding='RAW_AS_FRACTION_CONDITIONAL_UNCERTIFIED',
        scheduler='UNCHANGED_NATIVE_TERMINAL60_AND_COLDSTART_LATENCY',partial_DEV=True))
    comparisons=[]
    for tier in s.g.TIERS:
        a=p['targets']['STATIC50_'+tier.name];b=p['targets']['H090_'+tier.name]
        comparisons.append(dict(tier=tier.name,STATIC50_raw_SHA256=s.sha(a.tobytes()),H090_raw_SHA256=s.sha(b.tobytes()),
            entire_target_path_byte_exact=a.tobytes()==b.tobytes(),execution_reuse_eligible=False,
            different_float64_cells=int(np.count_nonzero(a!=b)),different_decision_dates=int(np.count_nonzero(np.any(a!=b,axis=1))),
            same_tier_native_execution_inputs_and_policy_identical=True))
    if any(c['entire_target_path_byte_exact'] for c in comparisons):raise ValueError('ALIAS_REQUIRES_SEPARATE_PRIOR_REVIEW_DO_NOT_AUTO_REDUCE_MATRIX')
    equality=dict(schema='PRE_RETURN_PARTIAL2021_ORIGINAL_TARGET_EXECUTION_EQUALITY_V1',requested_matrix_cells=9,
        unique_execution_jobs=9,alias_mapping={},STATIC50_H090_comparisons=comparisons,execution_identity=execution,
        source_identity=p['source_identity'],decision_raw_SHA256=s.sha(p['decisions'].tobytes()),
        annual_covariance_raw_SHA256=s.sha(p['covariance'].tobytes()),target_identity=s.g.target_identities(p['decisions'],p['targets']),
        no_outcome_based_reuse=True,no_cross_tier_reuse=True,financial_accounts_created=0,returns_computed=False)
    np.savez_compressed(destination/'TARGETS.npz',decision_us=p['decisions'],annual_covariance=p['covariance'],**p['targets'])
    write(destination/'TARGET_PROOFS.json',p['proofs']);write(destination/'EXACT_EXECUTION_EQUALITY.json',equality)
    write(destination/'DAILY_SOURCE_PROJECTION.json',p['projection'])
    (destination/'MINUTE_MARK_PROVENANCE.json').write_bytes(p['sidecar_raw'])
    artifact_pins={x.name:{'SHA256':s.sha(x.read_bytes()),'bytes':x.stat().st_size} for x in destination.iterdir()}
    cells=[]
    for strategy,tier in s.g.CONFIGS:
        config=strategy+'_'+tier
        cells.append(dict(cell_id='2021_'+config+'_APR2_DEC31_D',year=2021,strategy=strategy,tier=tier,config=config,
            calendar=[s.START,s.END],days=s.DAYS,required_minutes=s.MINUTES,cost='BASE27',
            selected_target_raw_SHA256=s.sha(p['targets'][config].tobytes()),tranche='EXACT_NINE_PARTIAL2021_D'))
    manifest=dict(schema='FROZEN_ORIGINAL_D_PARTIAL2021_NINE_DEV_CELLS_V1',years=[2021],cells=cells,new_cell_count=9,
        nominal_cell_count=9,unique_execution_jobs=9,alias_mapping={},calendar=[s.START,s.END],warmup_only_before=s.START,
        first_fullfive200_decision_us=s.START,decision_count=s.DAYS,required_minutes=s.MINUTES,partial_DEV=True,
        partial_return_annualization_allowed=False,year_wallet_compounding_allowed=False,
        original_strategy_definitions_unchanged=True,financial_policy_changes_allowed=False,
        policy_variant='GUARD50_EXIT_ONLY',cost='BASE27',settlement_mode='CONDITIONAL_COLLATERAL_FORFEITURE',
        source_target_artifacts=artifact_pins,source_identity=p['source_identity'],execution_identity=execution,
        dependency_pins_SHA256=s.sha((HERE/'DEPENDENCY_PINS.json').read_bytes()),
        resource_design=dict(maximum_live_workers=2,threads_per_worker=1,per_case_wall_seconds=600,per_case_CPU_seconds=600,
            per_case_RSS_stop_bytes=2000000000,per_case_AS_bytes=4000000000,per_case_output_bytes=250000000,
            aggregate_live_worker_RSS_stop_bytes=3500000000),
        account_creation_authorized=False,historical_finance_authorized=False)
    write(HERE/'FROZEN_NINE_CELL_MANIFEST.json',manifest)
    print('SOURCE_ONLY_MANIFEST_SHA256',s.sha((HERE/'FROZEN_NINE_CELL_MANIFEST.json').read_bytes()),flush=True)
    print(json.dumps(comparisons,indent=2),flush=True)
if __name__=='__main__':main()
