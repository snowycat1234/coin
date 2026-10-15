"""Short active generated coupled profile through the unchanged bounded pool."""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import resource
import sys
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
FROZEN = ROOT/'bounded_native_continuation_guard50_exit_expansion_20261015'
spec = importlib.util.spec_from_file_location('_forecast_frozen_pool', FROZEN/'run_expansion.py')
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)


def worker(path, cpu):
    runner.apply_limits(cpu)
    import forecast_monitor as f
    from test_core import active_fixture, load_checker
    began = time.monotonic()
    w, rows, decisions, targets = active_fixture()
    sim, guard = f.construct_case(w, rows, decisions, targets, generated_scope=f.GENERATED)
    while sim.cursor < sim.end and sim.stop is None:
        sim.advance_day()
    result = f.case_result(sim, guard)
    result.pop('minute')
    result['targets'] = result['targets'].to_dicts()
    result = f.V2.OWNED.export_tree(result)
    audit = f.V2.OWNED.export_tree(sim.account.snapshot())
    proof = load_checker().reconcile_saved_native(audit, result, expected_continuation_version=f.VERSION)
    assert sim.stop is None and sim.rows_written == 1440
    assert result['forecast_risk_monitor']['paid_fill_variance_journal']
    assert any(r['kind'] == 'COHORT_CREATED' for r in audit['forecast_journal'])
    assert any(r['kind'] == 'COMPLETED_NATIVE_PAID_TARGET' for r in audit['forecast_journal'])
    assert len(audit['trades']) > 0 and sim.account.fees > 0
    runner.save(path/'GENERATED_AUDIT.json', audit)
    runner.save(path/'GENERATED_RESULT.json', result)
    runner.save(path/'GENERATED_NATIVE40_PROOF.json', proof)
    receipt = dict(status='PASS_ACTIVE_GENERATED_FORECAST_NATIVE_CALENDAR',
        cell_id=path.name, PID=os.getpid(), generated_only=True,
        historical_account_objects_constructed=0, historical_financial_runs=0,
        generated_minutes=sim.rows_written, paid_trade_rows=len(audit['trades']),
        forecast_cohorts=sum(r['kind']=='COHORT_CREATED' for r in audit['forecast_journal']),
        paid_variance_rows=len(audit['forecast_fill_journal']),
        actual_affinity=sorted(os.sched_getaffinity(0)),
        thread_environment={k:os.environ[k] for k in runner.THREAD_ENV},
        max_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,
        CPU_seconds=resource.getrusage(resource.RUSAGE_SELF).ru_utime+resource.getrusage(resource.RUSAGE_SELF).ru_stime,
        wall_seconds=time.monotonic()-began, limits=runner.LIMITS,
        annual_resource_envelope_certified=False)
    runner.save(path/'CASE_RECEIPT.json', receipt)
    names = ('GENERATED_AUDIT.json','GENERATED_RESULT.json','GENERATED_NATIVE40_PROOF.json','CASE_RECEIPT.json')
    runner.save(path/'TERMINAL_CHECKPOINT.json',dict(cell_id=path.name,
        files={name:runner.sha((path/name).read_bytes()) for name in names}))


def validate(path, cell):
    import forecast_monitor as f
    from test_core import load_checker
    cp = json.loads((path/'TERMINAL_CHECKPOINT.json').read_bytes())
    if cp['cell_id'] != cell or any(runner.sha((path/name).read_bytes()) != digest for name,digest in cp['files'].items()):
        raise ValueError('GENERATED_PROFILE_CHECKPOINT_MISMATCH')
    audit = json.loads((path/'GENERATED_AUDIT.json').read_bytes())
    result = json.loads((path/'GENERATED_RESULT.json').read_bytes())
    proof = load_checker().reconcile_saved_native(audit, result, expected_continuation_version=f.VERSION)
    if runner.body(proof) != (path/'GENERATED_NATIVE40_PROOF.json').read_bytes():
        raise ValueError('GENERATED_PROFILE_NATIVE40_PROOF_MISMATCH')
    return json.loads((path/'CASE_RECEIPT.json').read_bytes())


def profile(output):
    cpus = [2, 3]
    if not set(cpus) <= os.sched_getaffinity(0):
        raise RuntimeError('TWO_REQUESTED_DISTINCT_ALLOWED_CPUS_REQUIRED')
    jobs = [(cell, lambda path, cpu: [sys.executable,'-B',str(Path(__file__).resolve()),
            '--worker',str(path.resolve()),'--cpu',str(cpu)])
            for cell in ('GENERATED_FORECAST_ACTIVE_A','GENERATED_FORECAST_ACTIVE_B')]
    report = runner.run_pool(jobs, output, requested_workers=2, cpus=cpus, validator=validate)
    report.update(generated_only=True, historical_account_objects_constructed=0,
        historical_financial_runs=0, annual_resource_envelope_certified=False,
        monitor_SHA256=runner.sha((HERE/'forecast_monitor.py').read_bytes()),
        profile_SHA256=runner.sha(Path(__file__).read_bytes()),
        frozen_pool_SHA256=runner.sha((FROZEN/'run_expansion.py').read_bytes()))
    return report


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--worker')
    p.add_argument('--cpu', type=int)
    p.add_argument('--output')
    args = p.parse_args()
    if args.worker:
        worker(Path(args.worker), args.cpu)
    else:
        result = profile(Path(args.output))
        runner.save(Path(args.output)/'GENERATED_PROFILE.json', result)
        print(json.dumps(result))
