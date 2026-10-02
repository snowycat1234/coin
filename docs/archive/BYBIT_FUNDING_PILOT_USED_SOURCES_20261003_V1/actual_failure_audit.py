"""One failed Bybit receipt/raw-body audit; no HTTP or economic calculation."""
import json, os, resource, time
from pathlib import Path
from audit import WORK, ROOT, need, sha, load, write_new, fixed_url, strict_json, task_evidence
OUT=ROOT/'reports/fast_research/BYBIT_FUNDING_PILOT_INDEPENDENT_FAILED_RESPONSE_AUDIT_20261003_V1.json'

def main():
    bound=load(WORK/'ACTUAL_BINDING.json')
    need(not OUT.exists() and sha(__file__)==bound['checker_sha256'],'New output/prebound checker required')
    report=dict(status='FAIL_BYBIT_PILOT_FAILURE_EVIDENCE_AUDIT',
        binding=dict(task_id=os.environ['COIN_TASK_ID'],checker_sha256=sha(__file__),
            ACTUAL_BINDING_sha256=sha(WORK/'ACTUAL_BINDING.json')),
        independent_source=str(Path(__file__)),independent_source_sha256=sha(__file__),
        actual_HTTP_requests_by_auditor=0,price_arrays_read=False,raw_funding_events_read=0,
        funding_income_calculated=False,candidate_status='NO_QUALIFIED_CANDIDATE')
    started=time.monotonic()
    try:
        for path,digest in bound['inputs'].items():need(sha(path)==digest,'Prebound input changed:'+path)
        protocol=load(ROOT/bound['protocol_path']);pilot=load(ROOT/bound['pilot_report_path'])
        run=Path(protocol['run_dir']);binding=load(run/'RUN_BINDING.json')
        need(binding==pilot['binding'] and binding['protocol_sha256']==sha(ROOT/bound['protocol_path'])
             and binding['git_commit']==protocol['git_commit_at_freeze']==bound['git_commit']
             and binding['source_hashes']==protocol['frozen_sources'],'Actual source/protocol/HEAD binding differs')
        for path,digest in protocol['frozen_sources'].items():need(sha(ROOT/path)==digest,'Frozen source changed:'+path)
        report['verified_source_hashes']=protocol['frozen_sources']
        need(protocol['symbols']==['BTCUSDT','ETHUSDT'] and protocol['maximum_requests']==2
             and protocol['retry_count']==0 and protocol['redirects_allowed'] is False
             and protocol['stop_on_any_failure'] is True,'Fixed request/stop policy differs')
        need(pilot['status']=='FAIL_BYBIT_NATIVE_FUNDING_HISTORY_PILOT_UNCONFIRMED'
             and pilot['actual_operation_exit_code']==1,'Original pilot FAIL must remain')
        report['pilot_actual_task']=task_evidence(binding['task_id'],'failed',1)
        synthetic=load(ROOT/bound['synthetic_report_path'])
        report['synthetic_actual_task']=task_evidence(synthetic['binding']['task_id'],'completed',0)
        need(len(synthetic['fixture_results'])==4 and synthetic['status'].startswith('PASS_BYBIT_PILOT_INDEPENDENT_FOUR_PARSER_FIXTURES'),
             'Original four-case synthetic evidence differs')
        result=load(run/'RESULT.json')
        need(result['artifact_sha256']==sha(ROOT/bound['pilot_report_path'])
             and result['actual_task_id']==binding['task_id'] and result['actual_operation_exit_code']==1,
             'Actual RESULT/report failure binding differs')
        need(len(pilot['requests'])==1 and pilot['samples']==[],'First BTC failure must stop with no samples')
        request=pilot['requests'][0]
        need(request==load(run/'BTCUSDT-official-response.http.json'),'HTTP manifest differs')
        fixed_url(request['url'],'BTCUSDT',protocol['limit'])
        need(request['final_url']==request['url'] and request['retries']==request['redirects_followed']==0
             and request['TLS_verification']=='SYSTEM_DEFAULT_ENABLED' and request['http_status']==403
             and request['status']=='HTTP_FAILURE' and request['native_exit_code']==1,'Restriction stop differs')
        raw=run/'BTCUSDT-official-response.json';payload=raw.read_bytes()
        need(request['raw_path']==str(raw) and request['raw_sha256']==sha(raw)==bound['raw_sha256']
             and len(payload)==96==request['bytes']==request['response_body_bytes']==pilot['response_body_bytes_total'],
             'Original response SHA/length differs')
        try:strict_json(payload)
        except json.JSONDecodeError:pass
        else:raise AssertionError('Expected non-JSON restriction body accepted as business JSON')
        message='The Amazon CloudFront distribution is configured to block access from your country'
        need(message in payload.decode('utf-8'),'Raw restriction message differs')
        need(not any('ETHUSDT' in p.name for p in run.iterdir()),'ETH artifact present after BTC failure')
        for field in ('publication_or_cash_certified','full_history_coverage_certified','locked_consumed',
                      'price_arrays_read','funding_income_calculated'):need(pilot[field] is False,'Forbidden qualification:'+field)
        need(all(pilot[f]==0 for f in ('orders_sent','models_fit','GPU'))
             and pilot['funding_rate_unit']=='NOT_YET_INTERPRETED' and pilot['carry_economics']=='NOT_EVALUABLE'
             and pilot['candidate_status']=='NO_QUALIFIED_CANDIDATE','Economic/qualification scope differs')
        need(pilot['owned_bytes']<=protocol['resource_budget']['new_owned_bytes_max']==2000000
             and pilot['elapsed_seconds']<=protocol['resource_budget']['wall_seconds_max']==180
             and request['elapsed_seconds']<=protocol['timeout_seconds']==20
             and len(payload)<=protocol['max_response_bytes']==64000,'Recorded resource budget exceeded')
        need(pilot['resources']['swap_bytes']==0 and pilot['resources']['gpu_used'] is False
             and pilot['shared_simultaneous_peak_measured'] is False,'Resource measurement scope differs')
        report.update(status='PASS_BYBIT_PILOT_FAILURE_EVIDENCE_STOP_AND_NO_ECONOMICS_SCOPE',
            pilot_status=pilot['status'],pilot_actual_exit_code=1,pilot_report_path=bound['pilot_report_path'],
            pilot_report_sha256=sha(ROOT/bound['pilot_report_path']),protocol_sha256=sha(ROOT/bound['protocol_path']),
            raw_response=dict(path=str(raw),sha256=sha(raw),bytes=96,http_status=403,valid_JSON=False,
                canonical_business_retCode=None,body_error_message=message,user_location_inferred=False),
            observed_requests=1,ETH_requested=False,samples_accepted=0,native_data_or_unit_gate='NOT_PASSED',
            funding_unit_certified=False,retention_or_settlement_availability_certified=False,
            resource_evidence=dict(owned_bytes=pilot['owned_bytes'],elapsed_seconds=pilot['elapsed_seconds'],
                Windows_peak_separate_bytes=pilot['WindowsPeakWorkingSet64_max'],shared_simultaneous_peak_measured=False),
            scope='TRUE_FAILURE_PRESERVATION_STOP_BOUNDARY_ONLY_NOT_NATIVE_SOURCE_UNIT_OR_ECONOMIC_ACCEPTANCE')
        for path,digest in bound['inputs'].items():need(sha(path)==digest,'Bound input changed during audit:'+path)
    except Exception as error:
        report.update(error_type=type(error).__name__,reason=str(error));raise
    finally:
        report.update(elapsed_seconds=time.monotonic()-started,peak_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024)
        write_new(OUT,report)
    print(json.dumps(dict(status=report['status'],output=str(OUT),sha256=sha(OUT))))
if __name__=='__main__':main()
