"""Small generated-only concurrent pool exercise, never historical admission."""
import argparse
from pathlib import Path
import json
import os
import resource
import sys
import time
import run_expansion as runner


def worker(path,cpu,days=3):
    runner.apply_limits(cpu)
    import numpy as np
    import expansion as e
    from test_native_runtime import fixture
    from saved_native_reconciliation import reconcile_saved_native
    began=time.monotonic();window,rows,decisions=fixture(days)
    for day in range(days):
        for key in ('open','close','mark'):
            window['market']['BTCUSDT'][key][day*1440+10:day*1440+21]=20000.
    sim,guard=e.construct_case(window,rows,decisions,np.full((days,5),.03),generated_scope=e.GENERATED)
    while sim.cursor<sim.end and sim.stop is None:sim.advance_day()
    result=e.case_result(sim,guard);result.pop('minute');result['targets']=result['targets'].to_dicts()
    audit=e.V2.OWNED.export_tree(sim.account.snapshot());result=e.V2.OWNED.export_tree(result)
    proof=reconcile_saved_native(audit,result,expected_continuation_version=e.VERSION)
    assert len(audit['trades'])>0 and audit['totals']['fees']!='0'
    runner.save(path/'GENERATED_AUDIT.json',audit);runner.save(path/'GENERATED_RESULT.json',result)
    runner.save(path/'GENERATED_PROOF.json',proof)
    receipt=dict(status='PASS_ACTIVE_GENERATED_NATIVE_CALENDAR',cell_id=path.name,PID=os.getpid(),
        generated_only=True,historical_account_objects_constructed=0,generated_minutes=sim.rows_written,
        actual_affinity=sorted(os.sched_getaffinity(0)),thread_environment={key:os.environ[key] for key in runner.THREAD_ENV},
        max_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,wall_seconds=time.monotonic()-began,
        paid_trade_rows=len(audit['trades']),conditional_settlements=len(audit['settlement_journal']),limits=runner.LIMITS,
        annual_resource_envelope_certified=False)
    runner.save(path/'CASE_RECEIPT.json',receipt)
    names=('GENERATED_AUDIT.json','GENERATED_RESULT.json','GENERATED_PROOF.json','CASE_RECEIPT.json')
    runner.save(path/'TERMINAL_CHECKPOINT.json',dict(cell_id=path.name,
        files={name:runner.sha((path/name).read_bytes()) for name in names}))


def validate(path,cell):
    from saved_native_reconciliation import reconcile_saved_native
    cp=json.loads((path/'TERMINAL_CHECKPOINT.json').read_bytes())
    if cp['cell_id']!=cell or any(runner.sha((path/name).read_bytes())!=digest for name,digest in cp['files'].items()):raise ValueError('GENERATED_CHECKPOINT_TAMPER')
    a=json.loads((path/'GENERATED_AUDIT.json').read_bytes());r=json.loads((path/'GENERATED_RESULT.json').read_bytes())
    proof=reconcile_saved_native(a,r)
    if runner.body(proof)!=(path/'GENERATED_PROOF.json').read_bytes():raise ValueError('GENERATED_PROOF_TAMPER')
    return json.loads((path/'CASE_RECEIPT.json').read_bytes())


def profile(output):
    allowed=sorted(os.sched_getaffinity(0))
    if len(allowed)<2:raise RuntimeError('TWO_DISTINCT_ALLOWED_CPUS_REQUIRED_FOR_CONCURRENCY_TEST')
    jobs=[]
    for cell in ('GENERATED_ACTIVE_A','GENERATED_ACTIVE_B'):
        jobs.append((cell,lambda path,cpu:[sys.executable,'-B',str(Path(__file__).resolve()),'--worker',str(path.resolve()),'--cpu',str(cpu)]))
    report=runner.run_pool(jobs,output,requested_workers=2,cpus=allowed[:2],validator=validate)
    report.update(runner_SHA256=runner.sha((runner.HERE/'run_expansion.py').read_bytes()),
        checker_SHA256=runner.sha((runner.HERE/'saved_native_reconciliation.py').read_bytes()),
        profile_SHA256=runner.sha(Path(__file__).read_bytes()),
        generated_only=True,historical_account_objects_constructed=0,historical_financial_runs=0,
        annual_resource_envelope_certified=False)
    return report


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--worker');p.add_argument('--cpu',type=int);p.add_argument('--output')
    a=p.parse_args()
    if a.worker:worker(Path(a.worker),a.cpu)
    else:
        result=profile(Path(a.output));runner.save(Path(a.output)/'GENERATED_POOL_PROFILE.json',result);print(json.dumps(result))
