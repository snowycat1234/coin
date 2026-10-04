"""Audit the saved complete calendars of an actually failed budget task; no replay."""
import hashlib,json,os,gc,resource,time
from pathlib import Path
from datetime import UTC,datetime
import polars as pl
from quant.paths import ROOT,STATE
from quant import resources
from scripts.investment import multi_asset_financial_audit as audit
from scripts.research_v8.registry import FIELDS,append_event
from scripts.research_v7.oracle_flow_ceiling import Progress
assert os.environ['COIN_TASK_ID']
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_bytes())
pp=ROOT/'protocols/CONTINUOUS_DAILY_TREND_HOLD_TEN_20261004_V1.json'
ap=ROOT/'reports/fast_research/CONTINUOUS_DAILY_TREND_HOLD_TEN_20261004_V1.json'
p,a=read(pp),read(ap)
assert sha(ROOT/'scripts/investment/multi_asset_financial_audit.py')==p['independent_reference_pre_market_sha256']
assert a['status']=='FAILED_MULTI_ASSET_DEVELOPMENT_COMPARISON' and a['reason']=='Finite output/wall research budget reached'
assert a['error_type']=='ValueError' and a['completed_cases']==a['required_cases']==4
assert a['owned_bytes']>p['budget']['owned_bytes'] and a['elapsed_seconds']<p['budget']['wall_seconds']
assert a['owned_bytes']==505969595 and a['owned_bytes']<p['research_budget']['total_new_STATE_bytes']
assert a['binding']['protocol_sha256']==sha(pp) and a['binding']['source_hashes']==p['source_hashes']
for name,digest in p['source_hashes'].items():assert sha(ROOT/name)==digest,name
symbols=tuple(a['cases'][0]['symbols']);assert len(symbols)==10
assert all(c['symbols']==list(symbols) and c['summary']['completed_minutes']==c['summary']['required_minutes']==436320 for c in a['cases'])
base,financial,derivation=audit.prepare_financial(symbols)
guard=base.module(base.GUARD,'d064_saved_failure_existing_guard',base.GUARD_SHA)
failed=guard.closed(a['binding']['task_id'],1)
run=STATE/'d064-continuous303-hold-ten-financial-20261004-v1';run.mkdir()
out=ROOT/'reports/fast_research/CONTINUOUS_DAILY_TREND_HOLD_TEN_FINANCIAL_20261004_V1.json'
binding=dict(task_id=os.environ['COIN_TASK_ID'],actual_reports={str(ap):sha(ap)},
    actual_task_id=a['binding']['task_id'],source_hashes=p['source_hashes'],recovery_source_sha256=sha(Path(__file__)),
    protocol_sha256=sha(pp),checker_sha256=sha(ROOT/'scripts/investment/multi_asset_financial_audit.py'))
guard.write(run/'RUN_BINDING.json',binding)
e=dict.fromkeys(FIELDS);e.update(event_id='D064-SAVED-BUDGET-FAILURE-AUDIT:START',experiment_id='D064-SAVED-BUDGET-FAILURE-AUDIT',event_type='SAVED_ACCOUNT_AUDIT_START',protocol_hash=sha(pp),success_failure='ORIGINAL_OUTPUT_BUDGET_FAILURE_PRESERVED',reason_for_next_experiment='Verify already saved complete calendars without raising old budget or rerunning markets')
append_event(ROOT/'reports/experiment_registry.jsonl',e)
r=dict(status='FAIL_CONFIGURED_N_SAVED_BUDGET_FAILURE_ACCOUNTING',binding=binding,run_dir=str(run),cases=[],
    actual_report_sha256=sha(ap),producer_status=a['status'],producer_task=failed,producer_budget_passed=False,
    saved_calendar_completed=True,original_result_overwritten=False,new_market_accounts=0,
    model_fits=0,orders_sent=0,locked_consumed=False,candidate='NONE',long_term_APR='NOT_EVALUABLE',
    financial_derivation=derivation,complete_period_days=303,completed_cases_verified=0)
started=time.monotonic();progress=Progress();errors=dict(cash=0.,ratio=0.)
try:
    rb=read(Path(a['run_dir'])/'RUN_BINDING.json');assert rb==a['binding']
    scope=audit.calendar_scope(p);window=audit.input_reader(p,symbols,base,guard)
    expected=audit.target_reference(window,symbols,'EQUAL',strategy_id=p['strategy'],mode='LONG_ONLY')
    reference=base.module(base.REFERENCE,'d064_saved_failure_independent_hand',base.REFERENCE_SHA)
    assert {(c['cost_id'],c['unit_id']) for c in a['cases']}=={(c,u) for c in base.COSTS for u in base.UNITS}
    for case in a['cases']:
        paths={k:base.payload(v,Path(a['run_dir'])) for k,v in case['artifacts'].items()}
        target=pl.read_parquet(paths['targets.parquet'])
        assert target.columns==expected.columns and target.height==expected.height
        for key in ['available_us','symbol','mode','eligibility_reason','raw_signed_target']:assert target[key].to_list()==expected[key].to_list(),key
        base.same(target['target_weight'],expected['target_weight'],'Independent HOLD covariance targets',errors,base.RATIO_TOL)
        progress.update('已保存失败任务的独立核账；不重跑账户',len(r['cases']),4,'账户')
        canonical=dict(case,period=scope['period_id'],mode='LONG_ONLY')
        result=financial(window,canonical,guard,reference,Path(a['run_dir']),None,[],errors)
        assert result['completed_days_verified']==303 and result['completed_months_verified']==10
        result.update(cross_month_boundary_witnesses=audit.continuous_boundary_witnesses(window,result,paths['funding.json'],base,errors),independent_HOLD_targets_verified=True)
        r['cases'].append(result);r['completed_cases_verified']=len(r['cases'])
        assert time.monotonic()-started<1800 and resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024<1500000000
        gc.collect()
    r.update(status='PASS_CONFIGURED_N_SHARED_PERPETUAL_RECORDED_ACCOUNTING_OF_SAVED_BUDGET_FAILURE_NOT_PRODUCER_SUCCESS_OR_APR',financial_case_calls=4,
        completed_full_calendar_cases_verified=4,required_scope=scope,maximum_errors=errors,
        completed_minutes_verified=4*436320,completed_days_verified=4*303,completed_months_verified=40,
        tolerances=dict(cash_USDT=1e-7,ratio=1e-10),continuous_accounting_verified=True,monthly_account_reset=False)
except Exception as err:r.update(error_type=type(err).__name__,reason=str(err));raise
finally:
    r.update(elapsed_seconds=time.monotonic()-started,peak_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,resources_after=resources.status(),created_utc=datetime.now(UTC).isoformat())
    guard.write(out,r);append_event(ROOT/'reports/experiment_registry.jsonl',{**e,'event_id':'D064-SAVED-BUDGET-FAILURE-AUDIT:RESULT','event_type':'SAVED_ACCOUNT_AUDIT_RESULT','success_failure':r['status'],'artifact_path':out.relative_to(ROOT).as_posix(),'artifact_sha256':sha(out)})
    progress.stop.set();progress.thread.join(timeout=3)
print(json.dumps(dict(status=r['status'],cases=r['completed_cases_verified'],source_task_still_failed=True)),flush=True)
