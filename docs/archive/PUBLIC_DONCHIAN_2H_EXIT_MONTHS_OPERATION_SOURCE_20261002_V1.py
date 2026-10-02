import hashlib,json,sys
from datetime import UTC,datetime
from pathlib import Path
import numpy as np
import polars as pl
from quant.paths import ROOT
sys.path.insert(0,str(ROOT))
from scripts.research_v8.registry import append_event
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def save(path,value):
    with Path(path).open('x') as stream:json.dump(value,stream,indent=2,allow_nan=False)
path=ROOT/'reports/fast_research/PUBLIC_DONCHIAN_2H_122D_ACTUAL_20261002_V1.json'
parent=json.loads(path.read_text());work=Path(parent['run_dir'])/'exit-monthly-attribution-v1';work.mkdir()
binding={'parent_report_sha256':sha(path),'operation_source_sha256':sha(__file__),'operation_command':[sys.executable,*sys.argv],
 'environment_lock_sha256':sha(ROOT/'environments/v8/uv.lock'),'git_commit':parent['binding']['git_commit'],
 'scope':'DERIVED_SAVED_2H_ACCOUNT_LEDGER_ONLY_NO_MARKET_RAW_OR_MODEL_IO', 'source_hashes':parent['binding']['source_hashes'],
 'actual_outer_session':96916,'actual_outer_exit':0,'task_id':parent['binding']['task_id'],'run_dir':parent['run_dir']}
save(work/'RUN_BINDING.json',binding)
event={**parent['registration_start'],'event_id':parent['registration_start']['experiment_id']+':EXIT_MONTHS_START',
 'event_type':'OPERATIONAL_DERIVED_EXIT_ATTRIBUTION_START','success_failure':'START',
 'source_hashes':{'operation_source_sha256':binding['operation_source_sha256']},'data_manifest_hash':binding['parent_report_sha256'],
 'exact_command':binding['operation_command'],'run_binding_sha256':sha(work/'RUN_BINDING.json')}
for key in ('record_sha256','previous_record_sha256','created_utc'):event.pop(key,None)
append_event(ROOT/'reports/experiment_registry.jsonl',event)
result={**binding,'status':'FAIL_2H_EXIT_MONTHLY_ATTRIBUTION','monthly_accounts':[],
 'actual_report_path':str(path.relative_to(ROOT)),'candidate_status':'NO_QUALIFIED_CANDIDATE','market_models_fit':0,
 'classification':'HISTORICAL_CONTINUOUS122DAY_PROXY_SCREENING_NOT_UNSEEN','GPU_hours':0,
 'reused_reference_binding':parent['reused_reference_binding']}
out=ROOT/'reports/fast_research/PUBLIC_DONCHIAN_2H_122D_ACTUAL_EXIT_MONTHS_20261002_V1.json'
try:
    assert parent['status']=='COMPLETE_ACTUAL_PROXY_STRATEGY_SCREENING' and parent['completed_ledgers']==3
    assert all(sha(ROOT/name)==digest for name,digest in binding['source_hashes'].items())
    for record in parent['folds'][0]['results']:
        s=record['summary'];daily=pl.read_parquet(Path(record['directory'])/'daily_nav.parquet').sort('date')
        expected=np.arange(parent['folds'][0]['start_us'],parent['folds'][0]['end_us'],86_400_000_000,dtype=np.int64)
        assert daily.height==122 and np.array_equal(daily['date'].dt.epoch(time_unit='us').to_numpy(),expected)
        daily=daily.with_columns(pl.col('date').dt.strftime('%Y-%m').alias('month'));prior=10000.;months=[]
        for month in ('2025-08','2025-09','2025-10','2025-11'):
            rows=daily.filter(pl.col('month')==month);end=float(rows['nav'][-1]);fees=float(rows['fees'].sum());cost=float(rows['execution_costs'].sum())
            months.append({'month':month,'days':rows.height,'starting_nav':prior,'ending_nav':end,'net_period_return':end/prior-1,
             'net_cash_PnL':end-prior,'gross_cash_PnL_same_quantities':end-prior+fees+cost,'fees':fees,'execution_costs':cost,
             'month_end_marked_exposure_USDT':end-float(rows['cash'][-1]),'account_reset_at_boundary':False,
             'boundary_inventory_is_marked_not_liquidated':True});prior=end
        assert abs(sum(v['net_cash_PnL'] for v in months)-s['net_cash_PnL'])<1e-7
        assert abs(sum(v['gross_cash_PnL_same_quantities'] for v in months)-s['gross_cash_PnL_same_quantities'])<1e-7
        positive=sum(max(v['gross_cash_PnL_same_quantities'],0.) for v in months)
        result['monthly_accounts'].append({'strategy':record['strategy'],'spread_bps':record['spread_bps'],'period_net_return':s['total_return'],
         'period_gross_cash_PnL_same_quantities':s['gross_cash_PnL_same_quantities'],'realized_daily_annualvol':s['annual_volatility'],
         'minute_MDD':s['max_observed_minute_MDD'],'cost_break_even_roundtrip_bps_same_quantities':s['break_even_roundtrip_cost_bps'],
         'max_minute_BTC_weight':s['max_minute_BTC_weight'],'max_minute_ETH_weight':s['max_minute_ETH_weight'],
         'max_minute_gross_weight':s['max_minute_marked_gross_weight'],'terminal_marked_notional':s['terminal_marked_notional'],
         'positive_gross_month_max_share':max(max(v['gross_cash_PnL_same_quantities'],0.) for v in months)/positive if positive else None,'months':months})
    result.update(status='ACTUAL_EXIT0_FIXED2H122D_MONTHLY_MTM_COMPLETE_NOT_QUALIFICATION',completed_ledgers=3,
      source_bytes_unchanged=True,all_monthly_net_and_gross_PnL_reconcile_period=True)
except Exception as error:
    result.update(error_type=type(error).__name__,reason=str(error));raise
finally:
    result['created_utc']=datetime.now(UTC).isoformat();save(out,result)
    append_event(ROOT/'reports/experiment_registry.jsonl',{**event,'event_id':parent['registration_start']['experiment_id']+':EXIT_MONTHS_RESULT',
      'event_type':'OPERATIONAL_DERIVED_EXIT_ATTRIBUTION_RESULT','success_failure':result['status'],
      'artifact_path':str(out.relative_to(ROOT)),'artifact_sha256':sha(out)})
    print(json.dumps({'output':str(out),'sha256':sha(out),'status':result['status'],'months30bps':result['monthly_accounts'][0]['months']}))
