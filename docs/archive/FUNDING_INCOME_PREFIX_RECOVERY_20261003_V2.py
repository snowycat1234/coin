"""Prefix-only recovery. Reuse completed V1 summaries, no aggregate recomputation."""
import argparse, importlib.util, json, os, resource, sys, time
from pathlib import Path
import pyarrow as pa
ROOT=Path('/mnt/d/codex/coin'); STATE=Path('/home/xflops/coin-state')
V1=STATE/'test-funding-income-independent-audit-20261003-v1'
V2=STATE/'test-funding-income-independent-audit-20261003-v2'
FIRST=ROOT/'reports/fast_research/FUNDING_INCOME_DECIMAL_INDEPENDENT_AUDIT_20261003_V1.json'
OUTPUT=ROOT/'reports/fast_research/FUNDING_INCOME_DECIMAL_INDEPENDENT_AUDIT_20261003_V2.json'
STATUS='PASS_CONDITIONAL_RAW_FRACTION_ASSUMPTION_DECIMAL_COUPON_MATH_UNCERTIFIED_UNIT_NOT_APR'
spec=importlib.util.spec_from_file_location('frozen_funding_audit_v1',V1/'audit.py')
old=importlib.util.module_from_spec(spec); spec.loader.exec_module(old)

def verify_prefix_only(path, by_symbol):
    # The original assertion accepted one narrower physical offset width than Polars writes.
    source=(V1/'audit.py').read_text()
    first=source.index('def verify_prefix(path, by_symbol):')
    last=source.index('\n\ndef main():',first)
    function=source[first:last]
    anchor="table.schema.types == [pa.string(), pa.int64(), pa.float64(), pa.float64(), pa.float64()]"
    old.need(function.count(anchor)==1,'One known physical string assertion required')
    function=function.replace(anchor,"(pa.types.is_string(table.schema.types[0]) or pa.types.is_large_string(table.schema.types[0])) and table.schema.types[1:] == [pa.int64(), pa.float64(), pa.float64(), pa.float64()]")
    namespace=dict(old.__dict__)
    exec(compile(function,str(V2/'prefix_recovery.py')+':one_logical_string_guard','exec'),namespace)
    return namespace['verify_prefix'](path,by_symbol)

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-dir',type=Path,required=True)
    args=parser.parse_args()
    old.need(args.run_dir.resolve()==V2 and not OUTPUT.exists(),'Exclusive prefix-only recovery STATE/output')
    frozen=old.load(V2/'RECOVERY_BINDING.json')
    old.need(old.sha(__file__)==frozen['checker_sha256'],'Prebound recovery code changed')
    old.need(old.sha(V1/'audit.py')==frozen['first_checker_sha256'],'V1 frozen checker changed')
    old.need(old.sha(FIRST)==frozen['first_report_sha256'],'V1 failure report changed')
    first=old.load(FIRST)
    old.need(first['status']=='FAIL_CONDITIONAL_RAW_FRACTION_ASSUMPTION_DECIMAL_COUPON_AUDIT'
        and first['reason']=='Coupon prefix physical schema changed' and first['completed_events_verified']==732
        and first['completed_sources_verified']==8 and len(first['per_symbol'])==2,'Exact completed V1 scope required')
    first_task=old.task_evidence(first['binding']['task_id'],expected_status='failed',expected_code=1)
    actual_binding=old.load(V1/'ACTUAL_BINDING.json')
    old.need(old.sha(V1/'ACTUAL_BINDING.json')==first['binding']['ACTUAL_BINDING_sha256']==frozen['ACTUAL_BINDING_sha256'],
             'Original binding changed')
    old.need(old.sha(actual_binding['actual_report'])==actual_binding['actual_report_sha256']==frozen['actual_report_sha256'],
             'Actual producer report changed')
    actual=old.load(actual_binding['actual_report'])
    actual_task=old.task_evidence(actual_binding['actual_task_id'])
    unit_task=old.task_evidence(actual_binding['unit_task_id'],expected_status='failed',expected_code=1)
    for path,digest in first['verified_source_hashes'].items():
        old.need(old.sha(ROOT/path)==digest,'Prebound dependency changed: '+path)
    report=dict(first)
    report.update(status='FAIL_CONDITIONAL_PREFIX_ONLY_RECOVERY',composite=True,
        execution_scope='V1_COMPLETED_AGGREGATE_MONTH_COST_SCOPE_REUSED_PLUS_V2_NEW732_PREFIX_ROWS_NOT_SINGLE_FRESH_SUITE',
        independent_source=str(Path(__file__).resolve()),independent_source_sha256=old.sha(__file__),
        binding=dict(task_id=os.environ['COIN_TASK_ID'],checker_sha256=old.sha(__file__),
            actual_report=actual_binding['actual_report'],actual_report_sha256=actual_binding['actual_report_sha256'],
            ACTUAL_BINDING_sha256=old.sha(V1/'ACTUAL_BINDING.json'),RECOVERY_BINDING_sha256=old.sha(V2/'RECOVERY_BINDING.json'),
            exact_command=[sys.executable,*sys.argv]),
        first_failure=dict(path=str(FIRST),sha256=old.sha(FIRST),source_sha256=old.sha(V1/'audit.py'),
            actual_task=first_task,actual_host_session='121be0',status=first['status'],reason=first['reason']),
        actual_task_evidence=actual_task,unit_task_evidence=unit_task,
        repeated_aggregate_month_cost_checks=False,newly_verified_prefix_rows=0,
        raw_CSV_reread_scope='ONLY_UNPASSED_PREFIX_VALUES_NO_AGGREGATE_RECOMPUTATION',
        prefix_physical_string_policy='String_OR_LargeString_LOGICAL_TEXT_ALL_OTHER_TYPES_AND_VALUES_STRICT')
    report.pop('error_type',None);report.pop('reason',None)
    report['per_symbol']=json.loads(json.dumps(first['per_symbol']))
    for symbol in report['per_symbol']:
        for monthly in symbol['months']:
            monthly.pop('cost_thresholds',None)
    report['monthly_extra_cost_thresholds_removed']=True
    report['month_cost_or_producer_math_changed']=False
    started=time.monotonic()
    try:
        acceptance=old.load(old.ACCEPTANCE)
        old.need(old.sha(old.ACCEPTANCE)==old.ACCEPTANCE_SHA,'Accepted old source metadata changed')
        entries=[entry for entry in acceptance['sources'] if entry['kind']=='fundingRate']
        by_symbol={symbol:[] for symbol in old.SYMBOLS}
        for entry in sorted(entries,key=lambda e:(old.SYMBOLS.index(e['symbol']),e['month'])):
            rows,_=old.raw_funding(entry)
            by_symbol[entry['symbol']].extend(rows)
        artifact=actual['output_artifacts'][0];path=Path(artifact['path'])
        old.need(path==Path(actual['run_dir'])/'coupon_prefix.parquet' and old.sha(path)==artifact['sha256'],
                 'Exact producer prefix bytes changed')
        report['coupon_prefix']=dict(path=str(path),sha256=old.sha(path),**verify_prefix_only(path,by_symbol))
        report['newly_verified_prefix_rows']=report['coupon_prefix']['rows_verified']
        old.need(report['newly_verified_prefix_rows']==732,'Prefix-only recovery incomplete')
        old.need(old.sha(FIRST)==frozen['first_report_sha256'] and old.sha(__file__)==frozen['checker_sha256'],
                 'First report/recovery source changed during prefix-only check')
        old.need(actual['capital_net_APR']=='NOT_EVALUABLE' and not actual['fills_NAV_or_realized_funding_cash_computed']
            and not actual['mark_index_spot_arrays_read'] and not actual['locked_consumed']
            and actual['models_fit']==0 and actual['orders_sent']==0 and actual['GPU']==0
            and actual['candidate_status']=='NO_QUALIFIED_CANDIDATE', 'Pending final diagnostic scope guard failed')
        for dependency,digest in first['verified_source_hashes'].items():
            old.need(old.sha(ROOT/dependency)==digest,'Prebound source changed during prefix recovery:'+dependency)
        report['status']=STATUS
    except Exception as error:
        report.update(error_type=type(error).__name__,reason=str(error));raise
    finally:
        report.update(prefix_recovery_elapsed_seconds=time.monotonic()-started,
            prefix_recovery_peak_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024)
        old.write_new(OUTPUT,report)
    print(json.dumps(dict(status=report['status'],output=str(OUTPUT),sha256=old.sha(OUTPUT),newly_verified_prefix_rows=732)))
if __name__=='__main__': main()