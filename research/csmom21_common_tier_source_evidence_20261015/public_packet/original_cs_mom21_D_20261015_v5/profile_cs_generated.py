"""Root-approved tiny synthetic CPU4/5 probe of the unchanged D scheduler.

The temporary registry is explicitly generated-only. No actual claim is created,
and no market body, actual target, historical scope or executable authority is
read. Code pin validation reads immutable failed-claim/evidence metadata.
"""
import argparse
from io import BytesIO
import json
import os
from pathlib import Path
import resource
import sys
import time

import cs_process_runtime as r


def fake_source_guard():
    import zipfile
    import prepare_cs_source  # Exact frozen worker preguard codec graph.
    import cs_source_bridge as bridge
    import cs_signal
    import cs_quality
    from cs_source_guard import SourceOnlyGuard
    cs_signal.originals(); cs_signal.common_grid(); cs_quality.original_quality()
    at = bridge.START
    row = [str(at // 1000), '10', '11', '9', '10', '5',
           str((at + bridge.MINUTE - 1000) // 1000), '50', '1', '0', '0', '0']
    payload = b'\xef\xbb\xbf' + (','.join(row) + '\n').encode('ascii')
    stream = BytesIO(); member = zipfile.ZipInfo('BTCUSDT-1m-2022-01.csv')
    member.compress_type = zipfile.ZIP_DEFLATED
    with zipfile.ZipFile(stream, 'w') as archive: archive.writestr(member, payload)
    if member.flag_bits != 0: raise ValueError('EXACT_GENERATED_ASCII_FLAG0_ZIP_REQUIRED')
    guard = SourceOnlyGuard()
    with guard:
        rows, _ = bridge.parse_original_zip(stream.getvalue(), symbol='BTCUSDT', period='2022-01', family='klines')
        if rows != {at: tuple(row)}: raise ValueError('EXACT_INVENTED_BOM_SOURCE_ROW_REQUIRED')
        guard.checkpoint('GENERATED_WORKER_SOURCE_GRAPH_ONLY')
    return guard.receipt('PASS_GENERATED_WORKER_SOURCE_GRAPH_ONLY')


def worker(path, cpu):
    r.apply_limits(cpu)
    began = time.monotonic()
    source_guard = fake_source_guard()  # Before the first financial import.
    import cs_generated as g
    import cs_finance_gate as gate
    from saved_native_reconciliation import reconcile_saved_native
    lease = os.fstat(int(os.environ['MATRIX_CONTROLLER_LEASE_FD']))
    tier = 'LOW' if path.name.endswith('A') else 'HIGH'
    with g.generated_fixture(days=2) as fixture:
        targets = g.project_generated(fixture)
        sim, guard = g.construct_generated_case(targets, tier)
        while sim.cursor < sim.end and sim.stop is None: sim.advance_day()
        native = g.native_reference(); result = native.case_result(sim, guard)
        result.pop('minute'); result['targets'] = result['targets'].to_dicts()
        result = native.V2.OWNED.export_tree(result); audit = native.V2.OWNED.export_tree(sim.account.snapshot())
        proof = reconcile_saved_native(audit, result, expected_continuation_version=native.VERSION)
        if not proof['passed'] or not audit['trades'] or audit['totals']['fees'] == '0':
            raise ValueError('ACTIVE_GENERATED_PAID_NATIVE_PATH_REQUIRED')
        receipt = dict(status='PASS_ACTIVE_GENERATED_CS_NATIVE', cell_id=path.name, PID=os.getpid(),
            generated_only=True, historical_account_objects_constructed=0, historical_financial_runs=0,
            actual_source_bodies_read=0, generated_minutes=sim.rows_written, nominal_tier=tier,
            synthetic_calendar=[sim.start, sim.end], actual_affinity=sorted(os.sched_getaffinity(0)),
            all_TID_affinities=[sorted(os.sched_getaffinity(int(t))) for t in os.listdir('/proc/self/task')],
            thread_environment={key: os.environ[key] for key in r.THREAD_ENV},
            max_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024,
            CPU_seconds=time.process_time(), wall_seconds=time.monotonic() - began,
            paid_trade_rows=len(audit['trades']), lease_FD_inherited=True, lease_inode=lease.st_ino,
            limits=r.LIMITS, source_code_manifest_SHA256=gate.SOURCE_CODE_SHA256,
            financial_code_manifest_SHA256=gate.code_identity(), annual_resource_envelope_certified=False)
        for name, value in (('GENERATED_AUDIT.json', audit), ('GENERATED_RESULT.json', result),
                            ('GENERATED_PROOF.json', proof), ('GENERATED_SOURCE_GUARD.json', source_guard),
                            ('CASE_RECEIPT.json', receipt)):
            r.save(path / name, value)
        names = ('GENERATED_AUDIT.json', 'GENERATED_RESULT.json', 'GENERATED_PROOF.json',
                 'GENERATED_SOURCE_GUARD.json', 'CASE_RECEIPT.json')
        r.save(path / 'TERMINAL_CHECKPOINT.json', dict(cell_id=path.name,
            files={name: r.sha((path / name).read_bytes()) for name in names}))


def validate(path, cell):
    from saved_native_reconciliation import reconcile_saved_native
    checkpoint = json.loads((path / 'TERMINAL_CHECKPOINT.json').read_bytes())
    if checkpoint['cell_id'] != cell or any(r.sha((path / n).read_bytes()) != h for n, h in checkpoint['files'].items()):
        raise ValueError('EXACT_GENERATED_TERMINAL_BYTES_REQUIRED')
    audit = json.loads((path / 'GENERATED_AUDIT.json').read_bytes())
    result = json.loads((path / 'GENERATED_RESULT.json').read_bytes())
    proof = reconcile_saved_native(audit, result)
    if r.body(proof) != (path / 'GENERATED_PROOF.json').read_bytes(): raise ValueError('EXACT_GENERATED_NATIVE40_REQUIRED')
    source_guard = json.loads((path / 'GENERATED_SOURCE_GUARD.json').read_bytes())
    if any(source_guard['forbidden_attempts'].values()): raise ValueError('ZERO_GENERATED_SOURCE_BOUNDARY_ATTEMPTS_REQUIRED')
    return json.loads((path / 'CASE_RECEIPT.json').read_bytes())


def profile(output):
    if sorted(os.sched_getaffinity(0)) != [4, 5]: raise ValueError('EXACT_ROOT_APPROVED_SYNTHETIC_CPU4_5_REQUIRED')
    if output.exists(): raise ValueError('EXCLUSIVE_GENERATED_PROFILE_OUTPUT_REQUIRED')
    output.mkdir()
    jobs = [(cell, lambda path, cpu: [sys.executable, '-B', str(Path(__file__).resolve()),
             '--worker', str(path.resolve()), '--cpu', str(cpu)]) for cell in ('GENERATED_CS_ACTIVE_A', 'GENERATED_CS_ACTIVE_B')]
    with r.controller_lease(output / 'GENERATED_ONLY_TEMP_LEASE_REGISTRY') as fd:
        report = r.run_pool(jobs, output, requested_workers=2, cpus=[4, 5], validator=validate)
        inode = os.fstat(fd).st_ino
    for cell in report['cases']:
        receipt = json.loads((output / cell['cell_id'] / 'CASE_RECEIPT.json').read_bytes())
        if receipt['lease_inode'] != inode or any(row != receipt['actual_affinity'] for row in receipt['all_TID_affinities']):
            raise ValueError('EXACT_INHERITED_LEASE_AND_ALL_TID_CPU_BINDINGS_REQUIRED')
    report.update(schema='CSMOM21_V3_TINY_TWO_WORKER_GENERATED_RESOURCE_PROBE', generated_only=True,
        maximum_observed_live_workers=max(len(row['workers']) for row in report['observations']),
        source_code_manifest_SHA256='21e13995b6be9482ee4e20d8e63be6d63396229035f69c963901331713342fce',
        historical_account_objects_constructed=0, historical_financial_runs=0, actual_source_bodies_read=0,
        actual_claims_created=0, actual_targets_generated=0, annual_resource_envelope_certified=False)
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('--worker'); parser.add_argument('--cpu', type=int)
    parser.add_argument('--output'); args = parser.parse_args()
    if args.worker: worker(Path(args.worker), args.cpu)
    else:
        path = Path(args.output); report = profile(path)
        r.save(path / 'GENERATED_POOL_PROFILE.json', report)
        print(json.dumps({key: report[key] for key in ('status', 'maximum_observed_live_workers', 'historical_financial_runs')}))
