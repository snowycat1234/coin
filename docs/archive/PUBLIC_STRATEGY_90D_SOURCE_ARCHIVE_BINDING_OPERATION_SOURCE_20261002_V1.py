"""Archive three pure code files and bind their preserved receipts; no market IO."""
import hashlib,json,os,shutil,sys
from pathlib import Path
from datetime import UTC,datetime
from quant.paths import ROOT,STATE
sys.path.insert(0,str(ROOT))
from scripts.research_v8.registry import append_event
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def save(path,value):
    with Path(path).open('x') as stream:json.dump(value,stream,indent=2,allow_nan=False)
month_path=ROOT/'reports/fast_research/PUBLIC_STRATEGY_CONTINUOUS_90D_ACTUAL_EXIT_MONTHS_20261002_V2.json'
month=json.loads(month_path.read_text());actual=json.loads((ROOT/month['actual_report_path']).read_text())
work=STATE/'public-strategy-continuous-90d-source-archive-binding-20261002-v1';work.mkdir()
snapshot=Path(month['preserved_failure']['source_snapshot'])
copies=[(snapshot/'scripts/investment/compare_simple_strategies.py',
 ROOT/'docs/archive/PUBLIC_STRATEGY_CONTINUOUS_90D_FAILED_V1_RUNNER_20261002.py',
 '2ae031d4601833203d9709c0a29da0a603cf3a54a072fa24cd12cc3754bcfd09'),
 (snapshot/'tests/test_simple_strategy_source_scope.py',
 ROOT/'docs/archive/PUBLIC_STRATEGY_CONTINUOUS_90D_SOURCE_GUARD_BEFORE_FINAL_CLOSE_REPAIR_20261002_V1.py',
 'b2dde01489cab5e9ee198e2e97b5bc2918c35e5e2e5c81cf6b8b29231c143f75'),
 (ROOT/'.cache/public_strategy_90d_exit_months_20261002_v2.py',
 ROOT/'docs/archive/PUBLIC_STRATEGY_90D_EXIT_MONTHS_OPERATION_SOURCE_20261002_V2.py',month['operation_source_sha256'])]
binding={'source_sha256':sha(__file__),'exact_command':[sys.executable,*sys.argv],'operation_task_id':os.environ['COIN_TASK_ID'],
 'environment_lock_sha256':sha(ROOT/'environments/v8/uv.lock'),'git_commit':actual['binding']['git_commit'],
 'monthly_receipt_path':str(month_path.relative_to(ROOT)),'monthly_receipt_sha256':sha(month_path),
 'archive_plan':[{'original_source':str(src),'archive_path':str(dst.relative_to(ROOT)),'sha256':digest} for src,dst,digest in copies],
 'scope':'PURE_SMALL_CODE_ARCHIVE_ONLY_NO_PRICE_DATABASE_MODEL_OR_LEDGER_REPLAY'}
save(work/'RUN_BINDING.json',binding)
event={**actual['registration_start'],'event_id':actual['registration_start']['experiment_id']+':CODE_ARCHIVE_START',
 'event_type':'OPERATIONAL_PURE_SOURCE_ARCHIVE_START','success_failure':'START','source_hashes':{'operation_source_sha256':sha(__file__)},
 'data_manifest_hash':sha(month_path),'exact_command':binding['exact_command'],'run_binding_sha256':sha(work/'RUN_BINDING.json')}
for key in ('record_sha256','previous_record_sha256','created_utc'):event.pop(key,None)
append_event(ROOT/'reports/experiment_registry.jsonl',event)
result={**binding,'status':'FAIL_PURE_SOURCE_ARCHIVE_BINDING','archives':[],'market_models_fit':0,'market_data_read':False,
 'locked_consumed':False,'candidate_status':'NO_QUALIFIED_CANDIDATE','preserved_failure':month['preserved_failure'],
 'actual_outer_session':month['actual_outer_session'],'actual_outer_exit':month['actual_outer_exit'],
 'actual_task_id':month['task_id'],'monthly_helper_host_session':37545,'monthly_helper_host_exit':0,
 'monthly_helper_task_id':month['operation_task_id']}
out=ROOT/'reports/fast_research/PUBLIC_STRATEGY_CONTINUOUS_90D_SOURCE_ARCHIVE_BINDING_20261002_V1.json'
try:
    assert month['status']=='ACTUAL_EXIT0_FIXED90D15ACCOUNTS_MONTHLY_MTM_COMPLETE_NOT_QUALIFICATION'
    for src,dst,digest in copies:
        assert sha(src)==digest and not dst.exists()
        shutil.copyfile(src,dst);assert sha(dst)==digest
        result['archives'].append({'path':str(dst.relative_to(ROOT)),'sha256':digest,'bytes':dst.stat().st_size,'original_preserved':True})
    assert sha(ROOT/'scripts/investment/compare_simple_strategies.py')=='3079ce734610fe1fb479411974d902b0aea4450e22c3a9c1b91e0f3f94c876b1'
    assert sha(ROOT/'scripts/research_v8/public_donchian_adapter.py')=='169d7ba6ebde24be5ce4730c5e741ed281a0155e4cadc22f1bb2bedccb4093c2'
    result['status']='PASS_PURE_SOURCE_ARCHIVE_V1_FAILURE_AND_90D_MONTHLY_EXIT_BINDING'
except Exception as error:
    result.update(error_type=type(error).__name__,reason=str(error));raise
finally:
    result['created_utc']=datetime.now(UTC).isoformat();save(out,result)
    append_event(ROOT/'reports/experiment_registry.jsonl',{**event,'event_id':actual['registration_start']['experiment_id']+':CODE_ARCHIVE_RESULT',
      'event_type':'OPERATIONAL_PURE_SOURCE_ARCHIVE_RESULT','success_failure':result['status'],'artifact_path':str(out.relative_to(ROOT)),'artifact_sha256':sha(out)})
    print(json.dumps({'status':result['status'],'path':str(out),'sha256':sha(out),'archives':result['archives']}))
