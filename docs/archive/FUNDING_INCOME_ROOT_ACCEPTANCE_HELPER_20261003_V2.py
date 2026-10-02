"""Parent-run funding audit acceptance: metadata only, no rates/prices/stat replay."""
import argparse, hashlib, json, os
from pathlib import Path
ROOT = Path('/mnt/d/codex/coin')
STATE = Path('/home/xflops/coin-state')
AUDIT_STATE = STATE / 'test-funding-income-independent-audit-20261003-v1'
AUDIT = ROOT / 'reports/fast_research/FUNDING_INCOME_DECIMAL_INDEPENDENT_AUDIT_20261003_V2.json'
STATUS = 'PASS_CONDITIONAL_RAW_FRACTION_ASSUMPTION_DECIMAL_COUPON_MATH_UNCERTIFIED_UNIT_NOT_APR'
def need(ok, message):
    if not ok: raise AssertionError(message)
def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def load(path): return json.loads(Path(path).read_bytes())
def completed(identity, expected_status="completed", expected_code=0):
    path = STATE / 'task-progress' / ('task-' + identity + '.json')
    task = load(path)
    need(task['id'] == identity and task['status'] == expected_status and task['exit_code'] == expected_code, 'Actual task explicitly required status/exit differs')
    return dict(path=str(path), sha256=sha(path), **{k:task[k] for k in ('id','status','exit_code','pid','start_ticks')})
def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--audit-sha256',required=True)
    parser.add_argument('--audit-host-session',required=True)
    parser.add_argument('--run-dir',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    need(args.run_dir.resolve().is_relative_to(STATE) and not args.run_dir.exists(), 'Exclusive metadata acceptance STATE required')
    need(args.output.resolve().is_relative_to(ROOT/'reports/fast_research') and not args.output.exists(), 'Exclusive receipt required')
    need(sha(AUDIT)==args.audit_sha256, 'Independent completed audit SHA differs')
    audit=load(AUDIT); actual_binding=load(AUDIT_STATE/'ACTUAL_BINDING.json')
    need(audit['status']==STATUS and audit['completed_sources_verified']==8 and audit['completed_events_verified']==732,
         'Complete independent raw Decimal scope not accepted')
    need(audit['binding']['ACTUAL_BINDING_sha256']==sha(AUDIT_STATE/'ACTUAL_BINDING.json') and
         audit['binding']['checker_sha256']==sha(audit['independent_source']) and actual_binding['checker_sha256']==sha(AUDIT_STATE/'audit.py'), 'Independent code/binding changed')
    tasks=[completed(audit['binding']['task_id']),completed(actual_binding['actual_task_id']),completed(actual_binding['unit_task_id'],expected_status='failed',expected_code=1),completed(audit['first_failure']['actual_task']['id'],expected_status='failed',expected_code=1)]
    need(sha(actual_binding['actual_report'])==actual_binding['actual_report_sha256']==audit['binding']['actual_report_sha256'],
         'Actual report bytes changed')
    for path,digest in audit['verified_source_hashes'].items():
        need(sha(ROOT/path)==digest,'Frozen dependency changed:'+path)
    need(audit['unit_certified'] is False and audit['sampled_API_parity_confirmed'] is False
         and audit['raw_funding_rate_unit']=='UNCONFIRMED' and audit['assumed_funding_rate_unit']=='FRACTION',
         'Conditional audit cannot certify units or genuine income')
    need(len(audit['per_symbol'])==2 and {v['symbol'] for v in audit['per_symbol']}=={'BTCUSDT','ETHUSDT'},
         'Separate two-symbol summary required')
    for row in audit['per_symbol']:
        need(row['events']==366 and len(row['months'])==4 and len(row['cost_thresholds'])==4, 'Complete scope missing')
    args.run_dir.mkdir()
    report={'status':'PASS_CONDITIONAL_FUNDING_COUPON_METADATA_ACCEPTANCE_UNIT_UNCERTIFIED_NO_NAV_OR_APR',
            'task_id':os.environ['COIN_TASK_ID'],'source_sha256':sha(__file__),
            'independent_audit_path':str(AUDIT),'independent_audit_sha256':sha(AUDIT),
            'independent_audit_host_session':args.audit_host_session,'actual_tasks':tasks,
            'actual_report_path':actual_binding['actual_report'],'actual_report_sha256':actual_binding['actual_report_sha256'],
            'checker_sha256':audit['binding']['checker_sha256'],'completed_events_verified':732,
            'candidate_status':'NO_QUALIFIED_CANDIDATE','NAV_or_APR_or_net_PnL_computed':False,
            'fraction_scope':audit['fraction_scope'],'coupon_scope':audit['coupon_scope'],'cost_scope':audit['cost_scope'],
            'unit_certified':False,'raw_funding_rate_unit':'UNCONFIRMED','assumed_funding_rate_unit':'FRACTION',
            'per_symbol':audit['per_symbol'],'finance_or_original_QA_repeated':False,'execution_scope':audit['execution_scope'],'first_failure':audit['first_failure']}
    with args.output.open('x',encoding='utf-8') as stream:
        json.dump(report,stream,indent=2,ensure_ascii=False,allow_nan=False);stream.write('\n')
    print(json.dumps({'status':report['status'],'output':str(args.output),'sha256':sha(args.output)}))
if __name__=='__main__': main()