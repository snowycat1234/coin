"""Small generated-only concurrent pool exercise, never historical admission."""
import argparse
from pathlib import Path
import json
import os
import resource
import sys
import time
import run_partial as runner


def worker(path,cpu,days=3):
    runner.apply_limits(cpu)
    import numpy as np
    import partial_d as e
    from test_native_runtime import fixture
    from saved_native_reconciliation import reconcile_saved_native
    began=time.monotonic();window,rows,decisions=fixture(days)
    shift=window['start']-205*86400000000
    window['start']-=shift;window['end']-=shift;decisions=decisions-shift
    rows=[dict(row,close_us=row['close_us']-shift,available_us=row['available_us']-shift) for row in rows]
    window['daily']=e.V2.native.pl.DataFrame(rows)
    window['events']=[dict(row,event_us=row['event_us']-shift) for row in window['events']]
    if not (window['fixture_scope']==e.GENERATED and window['start']==205*86400000000 and window['end']-window['start']==days*86400000000):raise ValueError('ONLY_OBVIOUS_SYNTHETIC_1970_FIXTURE_ALLOWED')
    fd=int(os.environ['MATRIX_CONTROLLER_LEASE_FD']);held=os.fstat(fd)
    if not held.st_ino:raise ValueError('INHERITED_GENERATED_CONTROLLER_LEASE_REQUIRED')
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
        lease_FD_inherited=True,lease_inode=held.st_ino,all_TID_affinities=[sorted(os.sched_getaffinity(int(t))) for t in os.listdir('/proc/self/task')],
        CPU_seconds=resource.getrusage(resource.RUSAGE_SELF).ru_utime+resource.getrusage(resource.RUSAGE_SELF).ru_stime,
        synthetic_calendar=[sim.start,sim.end],paid_trade_rows=len(audit['trades']),conditional_settlements=len(audit['settlement_journal']),limits=runner.LIMITS,
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
    if allowed!=[4,5]:raise ValueError('EXACT_APPROVED_GENERATED_CPU4_5_WINDOW_REQUIRED')
    with runner.controller_lease(Path(output)/'GENERATED_ONLY_TEMP_LEASE_REGISTRY') as fd:
        report=runner.run_pool(jobs,output,requested_workers=2,cpus=allowed,validator=validate)
        lease_inode=os.fstat(fd).st_ino
    for cell in report['cases']:
        receipt=json.loads((Path(output)/cell['cell_id']/'CASE_RECEIPT.json').read_bytes())
        if receipt['lease_inode']!=lease_inode or any(a!=receipt['actual_affinity'] for a in receipt['all_TID_affinities']):raise ValueError('EXACT_GENERATED_LEASE_AND_ALL_TID_AFFINITIES_REQUIRED')
    report.update(runner_SHA256=runner.sha((runner.HERE/'run_partial.py').read_bytes()),
        checker_SHA256=runner.sha((runner.CHECKER_ROOT/'saved_native_reconciliation.py').read_bytes()),
        profile_SHA256=runner.sha(Path(__file__).read_bytes()),
        generated_only=True,historical_account_objects_constructed=0,historical_financial_runs=0,
        annual_resource_envelope_certified=False)
    return report


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--worker');p.add_argument('--cpu',type=int);p.add_argument('--output')
    a=p.parse_args()
    if a.worker:worker(Path(a.worker),a.cpu)
    else:
        Path(a.output).mkdir(exist_ok=False)
        result=profile(Path(a.output));runner.save(Path(a.output)/'GENERATED_POOL_PROFILE.json',result);print(json.dumps(result))
