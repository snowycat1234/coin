"""One positive and three risk fixtures against frozen pilot parser; no network."""
import argparse, hashlib, importlib.util, json, os, resource, time
from pathlib import Path
ROOT=Path('/mnt/d/codex/coin');WORK=Path('/home/xflops/coin-state/test-bybit-funding-pilot-independent-audit-20261003-v1')
OUT=ROOT/'reports/fast_research/BYBIT_FUNDING_PILOT_INDEPENDENT_SYNTHETIC_20261003_V1.json'
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def need(ok,message):
    if not ok:raise AssertionError(message)
def main():
    parser=argparse.ArgumentParser();parser.add_argument('--run-dir',type=Path,required=True);args=parser.parse_args()
    need(args.run_dir.resolve()==WORK and not OUT.exists(),'Exclusive own STATE/output')
    frozen=json.loads((WORK/'SYNTHETIC_BINDING.json').read_bytes())
    need(sha(__file__)==frozen['source_sha256'],'Prebound synthetic helper changed')
    for path,digest in frozen['source_hashes'].items():need(sha(ROOT/path)==digest,'Frozen parser/transport changed:'+path)
    report=dict(status='FAIL_BYBIT_PILOT_INDEPENDENT_PARSER_FIXTURES',binding=dict(task_id=os.environ['COIN_TASK_ID'],
        source_sha256=sha(__file__),source_hashes=frozen['source_hashes'],SYNTHETIC_BINDING_sha256=sha(WORK/'SYNTHETIC_BINDING.json')),
        fixture_results=[],actual_HTTP_requests=0,original_history_inputs_read=0,models_fit=0,orders_sent=0,
        funding_income_calculated=False,unit_or_settlement_or_retention_certified=False)
    started=time.monotonic()
    try:
        spec=importlib.util.spec_from_file_location('frozen_bybit_pilot_parser',ROOT/'scripts/investment/bybit_funding_history_pilot.py')
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        cases=[('valid_no_8h_assumption.json',None),('bad_boolean_retcode.json','Integer retCode required'),
               ('bad_duplicate_key.json','Duplicate JSON key rejected'),('bad_wrongdate.json','Out-of-window or duplicate event')]
        for name,expected_rejection in cases:
            path=WORK/'fixtures'/name;payload=path.read_bytes()
            need(sha(path)==frozen['fixtures'][name],'Prebound fixture bytes changed')
            if expected_rejection is None:
                value=module.validate_response(payload,'BTCUSDT')
                need(value['row_count']==2 and value['interval_inferred'] is False
                     and value['full_day_event_completeness_certified'] is False,'Valid variable interval fixture mishandled')
                report['fixture_results'].append(dict(fixture=name,sha256=sha(path),result='ACCEPTED_EXPECTED_POSITIVE_4H_NOT_ASSUMED8H'))
            else:
                try:module.validate_response(payload,'BTCUSDT')
                except ValueError as error:
                    need(expected_rejection in str(error),'Wrong negative rejection cause:'+str(error))
                    report['fixture_results'].append(dict(fixture=name,sha256=sha(path),result='REJECTED_EXPECTED_INVALID',reason=str(error)))
                else:raise AssertionError('Invalid fixture was accepted:'+name)
        need(len(report['fixture_results'])==4,'All four independent parser calls required')
        for path,digest in frozen['source_hashes'].items():need(sha(ROOT/path)==digest,'Source changed during fixture audit')
        report['status']='PASS_BYBIT_PILOT_INDEPENDENT_FOUR_PARSER_FIXTURES_NO_NETWORK_NOT_MARKET_ACCEPTANCE'
    except Exception as error:
        report.update(error_type=type(error).__name__,reason=str(error));raise
    finally:
        report.update(elapsed_seconds=time.monotonic()-started,peak_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024)
        with OUT.open('x',encoding='utf-8') as stream:json.dump(report,stream,indent=2,ensure_ascii=False,allow_nan=False);stream.write('\n')
    print(json.dumps(dict(status=report['status'],output=str(OUT),sha256=sha(OUT))))
if __name__=='__main__':main()