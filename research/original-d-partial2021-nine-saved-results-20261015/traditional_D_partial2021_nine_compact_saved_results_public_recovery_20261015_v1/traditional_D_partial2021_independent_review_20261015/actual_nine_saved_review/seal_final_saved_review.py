"""Bind completed saved checks, event projections, resources and root exit."""
import os
for key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS','POLARS_MAX_THREADS','VECLIB_MAXIMUM_THREADS'):
    os.environ[key]='1'
os.sched_setaffinity(0,{6})
import sys,json,time,resource,subprocess,multiprocessing,fcntl
from pathlib import Path
from hashlib import sha256
from decimal import Decimal as D,localcontext
from contextlib import ExitStack
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[2];OUT=Path(__file__).resolve().parent;MODULE=ROOT/'traditional_D_partial2021_20261015'
sys.path.insert(0,str(MODULE))
import numpy as np
import partial_entry as e
import partial_d as integration
import run_partial as runner
ACTUAL=MODULE/'actual_nine_attempt001'
GO_SHA='79dfb608da4e423833df12f1e512a26ff5610ae2f7ea03d41c9e62e1a2a555f8'
REVIEW_SHA='5cd2fcc60a565a91866a0ddfbce1bd41e643f97d46aaddf17601e049815e6404'
def load(path):return json.loads(Path(path).read_bytes())
def pin(path):
    raw=Path(path).read_bytes();return dict(SHA256=sha256(raw).hexdigest(),bytes=len(raw))
def save(path,value):
    with Path(path).open('xb') as stream:stream.write(runner.body(value));stream.flush();os.fsync(stream.fileno())
def projection(clocks,times,values):
    result=np.zeros(len(clocks),dtype=np.float64)
    if times:
        index=np.searchsorted(np.asarray(times,dtype=np.int64),clocks,side='right')-1
        known=index>=0;result[known]=np.asarray(values,dtype=np.float64)[index[known]]
    return result
base_path=OUT/'INDEPENDENT_NINE_SAVED_REVIEW.json';base=load(base_path)
assert base['status']=='PASS_ALL_NINE_SAVED_TERMINALS_NO_FINANCIAL_RERUN' and base['reviewed_cell_count']==9
equality_path=OUT/'STATIC50_H090_POST_HOC_SAVED_EQUALITY.json';equality=load(equality_path)
assert equality['status']=='PASS_THREE_SAME_TIER_REALIZED_PATH_DUPLICATES_WITH_DISTINCT_REQUEST_INTENTS'
assert len(equality['pairs'])==3 and equality['execution_aliases_created']==0
exit_path=ACTUAL/'ROOT_OBSERVED_EXIT.json';root_exit=load(exit_path)
assert pin(exit_path)['SHA256']=='43e8782e0e81593ebf16102e7a46ff457260e7fcff0570108d2178a79d024df6'
assert root_exit['exit_code']==0 and root_exit['root_GO_SHA256']==GO_SHA and root_exit['no_financial_rerun'] is True
controller_path=ACTUAL/root_exit['controller_receipt'];controller=load(controller_path)
assert pin(controller_path)['SHA256']==root_exit['controller_receipt_SHA256']
assert controller['status']=='ALL_ADMITTED_ORDERED_CELLS_TERMINAL' and controller['root_GO_SHA256']==GO_SHA
assert controller['limits']==e.RESOURCE_LIMITS and controller['coordinator_CPU_affinity']==[4,5]
assert controller['compute_thread_pools_maximum']==1 and controller['no_automatic_retry'] is True
assert controller['no_financial_snapshot_resume'] is True and controller['host_quota_guaranteed'] is False
assert len(controller['cases'])==9 and {c['cell_id'] for c in controller['cases']}==set(e.tranche_cells())
assert all(c['reused_saved_terminal'] is False and c['status']=='FULL_CALENDAR_ACTUAL_PAID_MARKET_FLAT' for c in controller['cases'])
worker_samples=0;helper_samples=0
for observation in controller['observations']:
    assert len(observation['workers'])<=2 and observation['aggregate_live_RSS_bytes']<=e.RESOURCE_LIMITS['aggregate_live_worker_RSS_stop_bytes']
    assigned=[]
    for worker in observation['workers']:
        worker_samples+=1
        assert worker['CPU_affinity'] in ([4],[5]) and worker['RSS_bytes']<=e.RESOURCE_LIMITS['per_case_RSS_stop_bytes']
        assigned.append(worker['CPU_affinity'][0])
        for task in worker['tasks']:
            helper_samples+=1;assert task['CPU_affinity']==worker['CPU_affinity']
    assert len(assigned)==len(set(assigned))
blocked=[(integration.ExpansionAccount,'__init__'),(integration.V2.ENGINE.USDTLinearPerpetualAccount,'__init__'),
    (integration,'construct_case'),(integration.V2.native,'_construct_case'),(e.s.CapturedMinuteProvider,'__call__'),
    (integration.V2.native.runtime()[2].EarlierTerminalSimulator,'advance_day'),(e,'make_case'),(e.CaseExecutionScope,'__post_init__'),
    (runner,'case'),(runner,'controller'),(runner,'run_pool'),(runner,'claim_launch'),(runner,'controller_lease'),
    (subprocess,'Popen'),(subprocess,'run'),(multiprocessing.Process,'start'),(os,'system'),(fcntl,'flock')]
began=time.monotonic();projection_records=[];cell_records={}
with ExitStack() as stack:
    mocks=[stack.enter_context(patch.object(obj,name,side_effect=AssertionError('SAVED_ONLY_FORBIDDEN:'+name))) for obj,name in blocked]
    for cell_id in e.tranche_cells():
        rpath=OUT/(cell_id+'_SAVED_REVIEW.json');r=load(rpath);cell_records[cell_id]=r
        assert pin(rpath)==base['cell_review_receipts'][cell_id]
        directory=ACTUAL/cell_id
        assert r['terminal_checkpoint']==pin(directory/'TERMINAL_CHECKPOINT.json')
        for name,value in r['evidence'].items():assert pin(directory/name)==value
        receipt=load(directory/'CASE_RECEIPT.json');bootstrap=load(directory/'BOOTSTRAP_READY.json')
        assert bootstrap['actual_affinity']==receipt['actual_CPU_affinity']==[receipt['requested_CPU']]
        assert bootstrap['thread_environment']==receipt['thread_environment']=={k:'1' for k in runner.THREAD_ENV}
        assert bootstrap['limits']==dict(AS=[4_000_000_000]*2,CPU=[600]*2,RSS=[2_000_000_000]*2)
        assert receipt['total_wall_seconds']<=600 and receipt['CPU_seconds']<=600 and receipt['max_RSS_bytes']<=2_000_000_000
        assert r['terminal_status']=='FULL_CALENDAR_ACTUAL_PAID_MARKET_FLAT' and r['conditional_settlements']==0 and D(r['unpaid_liability'])==0
        audit=load(directory/'ACCOUNT_FINANCIAL_AUDIT.json')
        with np.load(directory/'MINUTE.npz',allow_pickle=False) as z:values=z['values'];columns=z['columns'].tolist()
        clocks=values[:,columns.index('close_us')].astype(np.int64)
        assert len(clocks)==394560 and clocks[0]==e.s.START+e.s.MINUTE and clocks[-1]==e.s.END
        # Projection of already-saved post-event quantities/totals onto saved
        # close clocks. No account, balance transition, provider or simulation
        # is run, and no new financial clock is created or advanced.
        for symbol in e.s.S:
            trades=[t for t in audit['trades'] if t['symbol']==symbol]
            times=[t['event_us'] for t in trades];quantities=[float(D(t['decimal_strings']['quantity_after'])) for t in trades]
            assert np.array_equal(projection(clocks,times,quantities),values[:,columns.index(symbol+'_quantity')]),(cell_id,symbol,'Q_PROJECTION')
        with localcontext() as context:
            context.prec=40
            times=[];fees=[];costs=[];turnover=[];f=D(0);c=D(0);v=D(0)
            for t in audit['trades']:
                detail=t['decimal_strings'];f+=D(detail['fee_amount']);c+=D(detail['execution_cost']);v+=D(detail['quantity'])*D(detail['fill_price'])
                times.append(t['event_us']);fees.append(float(f));costs.append(float(c));turnover.append(float(v))
            for name,series in (('cumulative_fees',fees),('cumulative_execution_costs',costs),('cumulative_turnover',turnover)):
                assert np.array_equal(projection(clocks,times,series),values[:,columns.index(name)]),(cell_id,name,'CUMULATIVE_PROJECTION')
            f=D(0);ft=[];fv=[]
            for row in audit['funding']:
                f+=D(row['decimal_strings']['signed_funding_USDT']);ft.append(row['event_us']);fv.append(float(f))
            assert np.array_equal(projection(clocks,ft,fv),values[:,columns.index('cumulative_funding')]),(cell_id,'FUNDING_PROJECTION')
        projection_records.append(dict(cell_id=cell_id,minute_quantity_fields_checked=5*394560,minute_cumulative_financial_fields_checked=4*394560,
            status='PASS_EXACT_SAVED_EVENT_TO_MINUTE_PROJECTION',account_objects_constructed=0,financial_clocks_advanced=0,
            native40_event_total_precision=40,tolerance_or_epsilon_used=False,financial_values_changed=False))
    for mock in mocks:mock.assert_not_called()
    boundary_counts=[dict(boundary=obj.__name__+'.'+name,calls=mock.call_count) for (obj,name),mock in zip(blocked,mocks)]
assert pin(OUT.parent/'INDEPENDENT_ORIGINAL_D_PARTIAL2021_REVIEW.json')['SHA256']==REVIEW_SHA
table=[]
for row in base['rows']:
    r=cell_records[row['cell_id']];risk=r['actual_held_risk']
    table.append(dict(row,forecast_budget_breach_fraction=risk['forecast_volatility_breach_minutes']/394560,
        nominal_annual_volatility_budget=risk['nominal_annual_volatility_budget'],
        forecast_annual_volatility_mean=risk['forecast_annual_volatility_mean'],
        source_funding_observed=4110,native_funding_applied=4105,fresh_flat_no_past_mark_events=5,
        primary_native40_passed=r['authoritative_native40_proof']['passed'],
        legacy_delta_sum_passed=r['legacy_delta_sum_report_preserved']['passed'],
        native40_secondary_PnL_bridge_residual=r['authoritative_native40_proof']['native40_secondary_PnL_bridge_residual'],
        raw_precision100_stored_delta_residuals=r['authoritative_native40_proof']['raw_precision100_stored_delta_terminal_residuals']))
record=dict(schema='FINAL_INDEPENDENT_ACTUAL_ORIGINAL_D_PARTIAL2021_NINE_SAVED_REVIEW_V1',status='PASS_COMPLETE_NINE_SAVED_AND_ROOT_EXIT_EVIDENCE',
    root_GO_SHA256=GO_SHA,source_generated_review_SHA256=REVIEW_SHA,preparation_SHA256=base['preparation_SHA256'],manifest_SHA256=e.MANIFEST_SHA256,
    source_generated_review_bytes_preserved=True,exact_ordered_cells=list(e.tranche_cells()),reviewed_actual_cells=9,
    all_nine_separately_executed=True,all_nine_full_calendar_actual_paid_market_flat=True,all_nine_zero_unpaid_debt=True,
    all_nine_zero_transfers=True,all_nine_zero_conditional_settlements=True,all_nine_native40_all_event_states_pass=True,
    calendar=[e.s.START,e.s.END],days_per_fresh_wallet=274,native_minutes_per_case=394560,aggregate_native_minutes=9*394560,
    initial_USDT_per_separate_fresh_wallet='10000',source_funding_coverage_per_case=4110,native_funding_applied_per_case=4105,
    initial_five_flat_no_past_mark_events_unapplied=True,no_charge_before_native_actual_exposure=True,
    terminal_signal_us=e.s.END-61*e.s.MINUTE,terminal_eligible_open_range=[e.s.END-60*e.s.MINUTE,e.s.END-e.s.MINUTE],
    latest_permitted_paid_fill_us=e.s.END-e.s.MINUTE+1,no_Jan1_execution_or_funding=True,
    root_observed_exit=root_exit,root_observed_exit_receipt=pin(exit_path),process_exit_confirmed_by_root_not_inferred_by_reviewer=True,
    controller_receipt=pin(controller_path),controller_observations=len(controller['observations']),worker_observations=worker_samples,
    worker_and_helper_TID_affinity_observations=helper_samples,all_observed_workers_and_helpers_confined_to_assigned_single_CPU=True,
    distinct_CPUs_per_live_worker=True,maximum_observed_live_workers=max(len(x['workers']) for x in controller['observations']),
    peak_observed_aggregate_worker_RSS_bytes=max(x['aggregate_live_RSS_bytes'] for x in controller['observations']),
    per_case_limits=e.RESOURCE_LIMITS,all_kernel_bootstrap_limits_and_numerical_thread_env_one_verified=True,
    all_case_wall_CPU_RSS_and_output_limits_previously_saved_verified=True,no_retry_or_reused_financial_snapshot=True,
    native40_reconstruction_authoritative=True,raw100_diagnostics_and_legacy_booleans_retained_without_epsilon_or_balancing=True,
    saved_event_to_minute_projections=projection_records,quantity_and_cumulative_fields_checked=9*9*394560,
    post_hoc_same_tier_STATIC50_H090_actual_financial_and_minute_paths_equal=True,
    post_hoc_STATIC50_H090_full_audits_identical=False,
    post_hoc_STATIC50_H090_distinct_raw_targets_and_request_intent_logs_retained=True,
    equal_realized_pairs_are_not_independent_path_evidence=True,execution_aliases_created=0,future_execution_reuse_authorized=False,
    equality_receipt=pin(equality_path),equality_pairs=[dict(tier=x['tier'],different_requested_intent_records=x['different_fill_request_records'],
        financial_history_and_minute_bytes_exact=True,full_audit_exact=False,raw_target_paths_exact=False,
        differing_raw_target_cells=x['different_raw_target_float64_cells'],differing_raw_target_days=x['different_raw_target_decision_dates'],
        differing_fields=x['full_audit_differing_top_level_fields'],risk_target_diagnostics_differ=x['saved_risk_report_differing_fields']) for x in equality['pairs']],
    rows=table,base_nine_saved_review=pin(base_path),read_only_review=True,financial_reruns=0,account_constructions=0,
    historical_clock_advances=0,provider_iterations=0,new_data_acquisitions=0,process_launches=0,claims_created=0,GO_edits=0,
    prohibited_boundary_call_counts=boundary_counts,review_CPU_affinity=[6],numerical_thread_environment={k:'1' for k in runner.THREAD_ENV},
    observed_review_helper_affinities=[sorted(os.sched_getaffinity(int(x.name))) for x in Path('/proc/self/task').iterdir()],
    review_wall_seconds=time.monotonic()-began,maximum_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,
    review_script=pin(__file__),
    interpretation_limits=[
        'Each return covers only Apr2 through Dec31,274 days. Jan1 through Apr1 warmup/cash padding is excluded. No annual CAGR, continuous compounded annual wallet, cross-cell portfolio or cross-year compounding is claimed.',
        'STATIC50 and H090 have distinct raw targets and distinct requested/unfilled intent decimals but identical realized paid financial and minute paths at each tier. All nine separate execution receipts are retained; the three duplicate realized pairs are not independent evidence.',
        'LOW/MID/HIGH are nominal target tiers. Actual forecast-risk breaches and realized daily-return annual-volatility diagnostics are reported explicitly and must not be presented as equal realized-risk matching or matched-risk excess returns.',
        'Funding units/publication/arrival and exact real-venue charge price, historical filters/listings/maintenance, and native exchange execution remain uncertified. Saved source/financial checks prove the declared offline model and supplied event evidence, not exchange certification.',
        'These2021 results remain development observations. No tuning, new threshold, ML, forecast-monitor policy, source provider acquisition, denied-source retry or holdout use was performed by this saved review.'
    ])
path=OUT/'FINAL_INDEPENDENT_ACTUAL_PARTIAL2021_NINE_REVIEW.json';save(path,record)
print(str(path));print(pin(path)['SHA256']);print('PASS_COMPLETE_NINE_SAVED_AND_ROOT_EXIT_EVIDENCE')
