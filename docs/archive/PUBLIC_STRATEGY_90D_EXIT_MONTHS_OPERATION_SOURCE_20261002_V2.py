"""Derived saved-ledger months only; ordinary reuse of the accepted MTM helper."""
import argparse, hashlib, json, os, sys
from datetime import UTC, datetime
from pathlib import Path
import numpy as np
import polars as pl
from quant.paths import ROOT
sys.path.insert(0,str(ROOT))
from scripts.research_v8.registry import append_event

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def save(path,value):
    with Path(path).open('x') as stream:json.dump(value,stream,indent=2,allow_nan=False)
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--operation-id',default='EXIT_MONTHS_V2')
parser.add_argument('--operation-directory',default='exit-monthly-attribution-v2')
parser.add_argument('--output',type=Path,default=ROOT/'reports/fast_research/PUBLIC_STRATEGY_CONTINUOUS_90D_ACTUAL_EXIT_MONTHS_20261002_V2.json')
args=parser.parse_args()
assert args.operation_id.replace('_','').isalnum() and args.operation_directory.replace('-','').isalnum()
out=args.output.resolve();assert out.is_relative_to((ROOT/'reports/fast_research').resolve()) and not out.exists()
path=ROOT/'reports/fast_research/PUBLIC_STRATEGY_CONTINUOUS_90D_ACTUAL_20261002_V2.json'
parent=json.loads(path.read_text());work=Path(parent['run_dir'])/args.operation_directory;work.mkdir()
failed_path=ROOT/'reports/fast_research/PUBLIC_STRATEGY_CONTINUOUS_90D_ACTUAL_20261002_V1.json'
failed=json.loads(failed_path.read_text())
proofs={name:sha(ROOT/name) for name in (
 'reports/fast_research/PUBLIC_STRATEGY_CONTINUOUS_90D_TINY_20261002_V1.json',
 'reports/fast_research/PUBLIC_STRATEGY_CONTINUOUS_90D_TINY_20261002_V2.json',
 'protocols/PUBLIC_STRATEGY_CONTINUOUS_90D_V1.json','protocols/PUBLIC_STRATEGY_CONTINUOUS_90D_V2.json')}
binding={'parent_report_sha256':sha(path),'operation_source_sha256':sha(__file__),'operation_command':[sys.executable,*sys.argv],
 'environment_lock_sha256':sha(ROOT/'environments/v8/uv.lock'),'git_commit':parent['binding']['git_commit'],
 'scope':'DERIVED_SAVED_15_ACCOUNT_LEDGER_ONLY_NO_MARKET_RAW_OR_MODEL_IO','source_hashes':parent['binding']['source_hashes'],
 'actual_outer_session':4852,'actual_outer_exit':0,'task_id':parent['binding']['task_id'],'run_dir':parent['run_dir'],
 'operation_task_id':os.environ['COIN_TASK_ID'],'prior_acceptance_and_protocol_hashes':proofs,
 'preserved_failure':{'report_path':str(failed_path.relative_to(ROOT)),'sha256':sha(failed_path),
  'host_session':91844,'host_exit':1,'task_id':failed['binding']['task_id'],'task_exit':1,
  'status':failed['status'],'reason':failed['reason'],'completed_CASH_ledgers':len(failed['folds'][0]['results']),
  'source_snapshot':str(Path(failed['run_dir'])/'source-snapshot'),
  'failed_runner_source_sha256':failed['binding']['source_hashes']['scripts/investment/compare_simple_strategies.py'],
  'failed_runner_snapshot_actual_sha256':sha(Path(failed['run_dir'])/'source-snapshot/scripts/investment/compare_simple_strategies.py')},
 'smoke_recovery':{'V1':'Source-calendar guard green: one case, no market price IO',
  'V2':'Only newly added final-close boundary case passed; original source-calendar case deselected',
  'V2_host_session':73427,'V2_host_exit':0,'V2_task_id':'2c8d17c787964f369ac34d0206fab56f',
  'change':'Signal closes only <=lastdecision; full calendar and execution/terminal valuation minute preserved'}}
save(work/'RUN_BINDING.json',binding)
event={**parent['registration_start'],'event_id':parent['registration_start']['experiment_id']+':'+args.operation_id+'_START',
 'event_type':'OPERATIONAL_DERIVED_EXIT_ATTRIBUTION_START','success_failure':'START',
 'source_hashes':{'operation_source_sha256':binding['operation_source_sha256']},'data_manifest_hash':binding['parent_report_sha256'],
 'exact_command':binding['operation_command'],'run_binding_sha256':sha(work/'RUN_BINDING.json')}
for key in ('record_sha256','previous_record_sha256','created_utc'):event.pop(key,None)
append_event(ROOT/'reports/experiment_registry.jsonl',event)
result={**binding,'status':'FAIL_90D_EXIT_MONTHLY_ATTRIBUTION','monthly_accounts':[],
 'actual_report_path':str(path.relative_to(ROOT)),'candidate_status':'NO_QUALIFIED_CANDIDATE','market_models_fit':0,
 'classification':'HISTORICAL_CONTINUOUS90DAY_PREVIOUSLY_SEEN_DEVELOPMENT_SCREENING_NOT_UNSEEN','GPU_hours':0}
try:
    assert parent['status']=='COMPLETE_ACTUAL_PROXY_STRATEGY_SCREENING' and parent['completed_ledgers']==15
    assert sha(failed_path)=='87b3612321539b6fe8c408270efd8c8dee09ccae15489bef94fc5a751a7a6491'
    assert binding['preserved_failure']['completed_CASH_ledgers']==3
    assert binding['preserved_failure']['failed_runner_snapshot_actual_sha256']==binding['preserved_failure']['failed_runner_source_sha256']
    assert all(record['strategy']=='CASH' for record in failed['folds'][0]['results'])
    assert all(sha(ROOT/name)==digest for name,digest in binding['source_hashes'].items())
    for record in parent['folds'][0]['results']:
        s=record['summary'];daily_path=Path(record['directory'])/'daily_nav.parquet'
        assert sha(daily_path)==record['artifacts']['daily_nav.parquet']['sha256']
        daily=pl.read_parquet(daily_path).sort('date')
        expected=np.arange(parent['folds'][0]['start_us'],parent['folds'][0]['end_us'],86_400_000_000,dtype=np.int64)
        assert daily.height==90 and np.array_equal(daily['date'].dt.epoch(time_unit='us').to_numpy(),expected)
        daily=daily.with_columns(pl.col('date').dt.strftime('%Y-%m').alias('month'));prior=10000.;months=[]
        for month,days in (('2025-12',31),('2026-01',31),('2026-02',28)):
            rows=daily.filter(pl.col('month')==month);assert rows.height==days
            end=float(rows['nav'][-1]);fees=float(rows['fees'].sum());cost=float(rows['execution_costs'].sum())
            months.append({'month':month,'days':rows.height,'starting_nav':prior,'ending_nav':end,'net_period_return':end/prior-1,
             'net_cash_PnL':end-prior,'gross_cash_PnL_same_quantities':end-prior+fees+cost,'fees':fees,'execution_costs':cost,
             'month_end_marked_exposure_USDT':end-float(rows['cash'][-1]),'account_reset_at_boundary':False,
             'boundary_inventory_is_marked_not_liquidated':True});prior=end
        assert abs(sum(v['net_cash_PnL'] for v in months)-s['net_cash_PnL'])<1e-7
        assert abs(sum(v['gross_cash_PnL_same_quantities'] for v in months)-s['gross_cash_PnL_same_quantities'])<1e-7
        positive=sum(max(v['gross_cash_PnL_same_quantities'],0.) for v in months)
        result['monthly_accounts'].append({'strategy':record['strategy'],'spread_bps':record['spread_bps'],'period_net_return':s['total_return'],
         'daily_nav_sha256':sha(daily_path),'period_gross_cash_PnL_same_quantities':s['gross_cash_PnL_same_quantities'],
         'realized_daily_annualvol':s['annual_volatility'],'minute_MDD':s['max_observed_minute_MDD'],
         'cost_break_even_roundtrip_bps_same_quantities':s['break_even_roundtrip_cost_bps'],
         'max_minute_BTC_weight':s['max_minute_BTC_weight'],'max_minute_ETH_weight':s['max_minute_ETH_weight'],
         'max_minute_gross_weight':s['max_minute_marked_gross_weight'],'terminal_marked_notional':s['terminal_marked_notional'],
         'positive_gross_month_max_share':max(max(v['gross_cash_PnL_same_quantities'],0.) for v in months)/positive if positive else None,'months':months})
    result.update(status='ACTUAL_EXIT0_FIXED90D15ACCOUNTS_MONTHLY_MTM_COMPLETE_NOT_QUALIFICATION',completed_ledgers=15,
      source_bytes_unchanged=True,all_monthly_net_and_gross_PnL_reconcile_period=True)
except Exception as error:
    result.update(error_type=type(error).__name__,reason=str(error));raise
finally:
    result['created_utc']=datetime.now(UTC).isoformat();save(out,result)
    append_event(ROOT/'reports/experiment_registry.jsonl',{**event,'event_id':parent['registration_start']['experiment_id']+':'+args.operation_id+'_RESULT',
      'event_type':'OPERATIONAL_DERIVED_EXIT_ATTRIBUTION_RESULT','success_failure':result['status'],
      'artifact_path':str(out.relative_to(ROOT)),'artifact_sha256':sha(out)})
    print(json.dumps({'output':str(out),'sha256':sha(out),'status':result['status'],
      'public_months30bps':[r for r in result['monthly_accounts'] if 'DONCHIAN' in r['strategy'] and r['spread_bps']==2]}))
