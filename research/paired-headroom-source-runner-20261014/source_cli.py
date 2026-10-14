"""One fixed preflight/run CLI. Cached source reads require review and year GO."""
from __future__ import annotations
import argparse
import gc
import hashlib
import importlib.machinery
import json
import os
from pathlib import Path
import resource
import shutil
import signal
import select
import stat
import subprocess
import sys
import time
import types

HERE = Path(__file__).resolve().parent
YEARS = (2023, 2024, 2025)
BASE_COMMIT = '7a31299c0f7eb6136599d5954a206944f50b27a2'


def bootstrap_gate(expected):
    """Main .py runs directly; every imported runner source is hash-bound first."""
    data = (HERE / 'RUNNER_MANIFEST.json').read_bytes()
    if hashlib.sha256(data).hexdigest() != expected:
        raise ValueError('TRUSTED_RUNNER_MANIFEST_MISMATCH')
    manifest = json.loads(data)
    for name, digest in manifest['files_SHA256'].items():
        path = Path(name)
        if path.is_absolute() or '..' in path.parts or (HERE / path).is_symlink():
            raise ValueError('RUNNER_FILE_PATH_REFUSED')
        if hashlib.sha256((HERE / path).read_bytes()).hexdigest() != digest:
            raise ValueError('RUNNER_FILE_IDENTITY_MISMATCH:' + name)
    if 'source_gate' in sys.modules:
        raise ValueError('PRELOADED_SOURCE_GATE_REFUSED')
    path = HERE / 'source_gate.py'
    source = path.read_bytes()
    digest = manifest['files_SHA256']['source_gate.py']
    if hashlib.sha256(source).hexdigest() != digest:
        raise ValueError('BOOTSTRAP_SOURCE_CHANGED')
    gate = types.ModuleType('source_gate')
    gate.__file__ = str(path)
    gate.__spec__ = importlib.machinery.ModuleSpec('source_gate', loader=None, origin=str(path))
    gate._verified_source_SHA256 = digest
    sys.modules['source_gate'] = gate
    exec(compile(source, str(path), 'exec'), gate.__dict__)
    return gate


def save(path, obj):
    with Path(path).open('x') as f:
        json.dump(obj, f, indent=2, sort_keys=True, allow_nan=False)
        f.write('\n')


def bytes_used(path):
    return sum(p.stat().st_size for p in Path(path).rglob('*') if p.is_file())


def resource_modules(roots, pins):
    guard_path = Path(roots['resource_guard'])
    release = Path(roots['resource_release'])
    check(guard_path, pins['original_resource_guard']['SHA256'], pins['original_resource_guard']['bytes'])
    check(release, pins['original_resource_release']['SHA256'], pins['original_resource_release']['bytes'])
    guard = import_file('_paired_source_original_resource_guard', guard_path, pins['original_resource_guard']['SHA256'])
    external = import_file('_paired_source_original_resource_gate', Path(roots['input_module']) / 'original_resource_gate.py', pins['input_publication']['files']['original_resource_gate.py']['SHA256'])
    return guard, external, release


def resource_admission(guard, external, release, output):
    # Same verified path-independent release binding as the existing native dispatcher.
    base = guard.resource_admission(Path(output).parent, 0)
    task = external.task_reservation(release)
    observed = external.external_observation()
    observed.update(task)
    observed['external_reserved_bytes'] = max(task['task_reserved_bytes'], len(observed['guard_pack_processes']) * external.PACK_RESERVED_BYTES)
    observed['external_busy_cpus'] = sorted(set(task['task_busy_cpus']) |
        {cpu for p in observed['guard_pack_processes'] for cpu in p['allowed_cpus']})
    return external.check_external(base, observed, 0, guard)


def bounded_worker_guard(policy):
    if (os.environ.get('_PAIRED_SOURCE_PARENT_PID') != str(os.getppid())
            or len(os.sched_getaffinity(0)) != 1 or sys.flags.optimize):
        raise ValueError('BOUNDED_PARENT_REQUIRED_BEFORE_SOURCE_READ')
    for kind, cap in ((resource.RLIMIT_AS, policy['AS_bytes']),
                      (resource.RLIMIT_CPU, policy['CPU_seconds_per_year'])):
        soft, hard = resource.getrlimit(kind)
        # Linux RLIM_INFINITY is -1: a simple upper comparison is unsafe.
        if (soft == resource.RLIM_INFINITY or hard == resource.RLIM_INFINITY
                or soft <= 0 or hard <= 0 or soft > hard or soft > cap or hard > cap):
            raise ValueError('FINITE_SOFT_AND_HARD_RESOURCE_CAPS_REQUIRED')
    for name in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS', 'NUMEXPR_NUM_THREADS'):
        if os.environ.get(name) != '1':
            raise ValueError('EXACT_ONE_MATH_THREAD_ENV_REQUIRED')


def controller_packet(args):
    return {'schema': 'PAIRED_SOURCE_CONTROLLER_PIPE_V1', 'parent_pid': os.getpid(),
        'runner_manifest_SHA256': args.runner_manifest_sha, 'year': args.year,
        'review_SHA256': args.review_sha, 'parent_GO_SHA256': args.parent_go_sha,
        'roots_SHA256': sha(args.roots), 'scope': 'CACHED_MARK_TRADE_SOURCE_ONLY_NO_WALLETS'}


def require_controller_handoff(args):
    try:
        descriptor = int(os.environ.get('_PAIRED_SOURCE_CONTROLLER_FD', '-1'))
        if descriptor < 3 or not stat.S_ISFIFO(os.fstat(descriptor).st_mode):
            raise ValueError('INHERITED_CONTROLLER_PIPE_REQUIRED')
        if not select.select([descriptor], [], [], 2.)[0]:
            raise ValueError('CONTROLLER_PIPE_HANDSHAKE_TIMEOUT')
        raw = os.read(descriptor, 4096)
        packet = json.loads(raw)
    except (OSError, TypeError, ValueError) as error:
        raise ValueError('VERIFIED_CONTROLLER_HANDOFF_REQUIRED') from error
    finally:
        if 'descriptor' in locals() and descriptor >= 3:
            try: os.close(descriptor)
            except OSError: pass
    expected = controller_packet(args)
    expected['parent_pid'] = os.getppid()
    if packet != expected or os.environ.get('_PAIRED_SOURCE_PARENT_PID') != str(os.getppid()):
        raise ValueError('CONTROLLER_HANDOFF_BINDING_MISMATCH')
    try: os.kill(os.getppid(), 0)
    except OSError as error: raise ValueError('CONTROLLER_NOT_LIVE') from error


def worker(args, roots, pins, cases):
    policy = read(HERE / 'RESOURCE_POLICY.json')
    bounded_worker_guard(policy)
    require_controller_handoff(args)
    if sys.version_info[:2] != (3, 12):
        raise ValueError('VALIDATED_PYTHON3_12_REQUIRED')
    import numpy as np
    if np.__version__ != '2.3.5':
        raise ValueError('VALIDATED_NUMPY2_3_5_REQUIRED')
    analysis = import_file('source_analysis', HERE / 'source_analysis.py', read(HERE / 'RUNNER_MANIFEST.json')['files_SHA256']['source_analysis.py'])
    load_symbol, derived_mask, causal_checks, summarize = [getattr(analysis, n) for n in ('load_symbol', 'derived_mask', 'causal_checks', 'summarize')]
    daily_summaries, lossless_runs, validate_saved_archive, array_binding = [getattr(analysis, n) for n in ('daily_summaries', 'lossless_runs', 'validate_saved_archive', 'array_binding')]
    adapter = import_file('_paired_source_exact_input', Path(roots['input_module']) / 'inherited_input_binding.py', pins['input_publication']['files']['inherited_input_binding.py']['SHA256'])
    paired = load_paired(roots)
    case = cases['years'][str(args.year)]
    source_root = roots['source' + str(args.year)]
    registry = read(Path(roots['input_module']) / 'INPUT_BINDINGS.json')
    # Reuse unchanged complete source admission, including exact source index,
    # every required metadata file, all twelve NPZ schemas and funding identities.
    admitted = adapter.verify_source(args.year, source_root, bindings=registry)
    out = Path(args.output) / 'data'
    out.mkdir(exist_ok=False)
    reports = {}
    for symbol in cases['symbols']:
        started = time.monotonic()
        source = load_symbol(adapter, case, source_root, symbol)
        overlay = roots.get('derived_csv') if args.year == 2024 else None
        derived = derived_mask(args.year, source['times'], symbol, overlay, pins, sha)
        feature = paired.features(source['times'], source['mark'], source['open'], derived)
        prefix = causal_checks(paired, source, derived, feature)
        runs = lossless_runs(feature)
        path = out / (symbol + '_COEFFICIENT_RUNS.npz')
        with path.open('xb') as f:
            np.savez_compressed(f, **runs)
        archive_digest = sha(path)
        validate_saved_archive(path, feature, runs, archive_digest, sha)
        report = {'symbol': symbol, 'calendar': case['calendar'],
            'source_index_SHA256': case['index']['SHA256'],
            'summary': summarize(source['times'], feature),
            'daily': daily_summaries(source['times'], feature), 'causal_prefix_tests': prefix,
            'derived_original_cells': int(derived.sum()),
            'source_arrays': {k: array_binding(v) for k, v in source.items()},
            'features': {k: array_binding(v) for k, v in feature.items()},
            'lossless_runs': {'rows': len(runs['start_row']), 'archive_SHA256': archive_digest,
                              'archive_bytes': path.stat().st_size, 'decode_equal': True},
            'elapsed_seconds': time.monotonic() - started}
        save(out / (symbol + '_SUMMARY.json'), report)
        if bytes_used(out) > policy['data_output_bytes_max']:
            raise ValueError('FIXED_DATA_OUTPUT_CAP_NO_TRUNCATION')
        reports[symbol] = {k: report[k] for k in ('summary', 'derived_original_cells', 'lossless_runs', 'elapsed_seconds')}
        print(json.dumps({'symbol': symbol, 'ready_rows': report['summary']['ready_rows'],
                          'lossless_runs': len(runs['start_row']), 'status': 'FULL_CALENDAR_COEFFICIENTS_PASS'}), flush=True)
        del source, derived, feature, runs, report
        gc.collect()
    save(out / 'YEAR_SUMMARY.json', {'status': 'PASS_FULL_CALENDAR_SOURCE_COEFFICIENT_COMPARISON',
        'year': args.year, 'paired_publication_commit': BASE_COMMIT, 'source_admission': admitted,
        'symbols': reports, 'interpretation': 'Exact coefficient distinction only. No owned q/E, trigger, PnL or safety claim; joint scenarios can miss unseen co-occurring extremes.',
        'wallets': 0, 'financial_advances': 0, 'fits': 0, 'new_market_downloads': 0, 'wallet_GO': False})


def dispatch(args, roots, pins, cases):
    if sys.flags.optimize:
        raise ValueError('PYTHON_OPTIMIZATION_REFUSED')
    policy = read(HERE / 'RESOURCE_POLICY.json')
    guard, external, release = resource_modules(roots, pins)
    output = Path(args.output)
    if output.exists():
        raise FileExistsError('FRESH_ATTEMPT_OUTPUT_REQUIRED_NO_RESUME_OR_OVERWRITE')
    began = time.monotonic()
    with external.controller_lock():
        output.mkdir(parents=False, exist_ok=False)
        save(output / 'START.json', {'year': args.year, 'runner_manifest_SHA256': args.runner_manifest_sha,
            'source_index_SHA256': cases['years'][str(args.year)]['index']['SHA256'],
            'review_SHA256': args.review_sha, 'parent_GO_SHA256': args.parent_go_sha,
            'scope': 'CACHED_MARK_TRADE_SOURCE_ONLY_NO_WALLETS'})
        try:
            resource_info = resource_admission(guard, external, release, output)
        except Exception as error:
            save(output / 'ADMISSION_FAILURE.json', {'status': 'RESOURCE_ADMISSION_FAILED_NO_SOURCE_ARRAY_READ',
                'error_type': type(error).__name__, 'error': str(error), 'wallets': 0})
            save(output / 'RESOURCE_RECEIPT.json', {'status': 'FAIL_RESOURCE_ADMISSION_NO_SOURCE_ARRAY_READ',
                'error_type': type(error).__name__, 'error': str(error), 'wallets': 0,
                'runner_manifest_SHA256': args.runner_manifest_sha})
            raise
        def limits():
            os.sched_setaffinity(0, {resource_info['allowed_cpus'][0]})
            resource.setrlimit(resource.RLIMIT_AS, (policy['AS_bytes'], policy['AS_bytes']))
            resource.setrlimit(resource.RLIMIT_CPU, (policy['CPU_seconds_per_year'], policy['CPU_seconds_per_year']))
        command = [sys.executable, '-B', str(HERE / 'source_cli.py'), 'run', '--worker',
            '--runner-manifest-sha', args.runner_manifest_sha, '--roots', args.roots,
            '--year', str(args.year), '--output', args.output, '--review', args.review,
            '--review-sha', args.review_sha, '--parent-go', args.parent_go, '--parent-go-sha', args.parent_go_sha]
        env = dict(os.environ, _PAIRED_SOURCE_PARENT_PID=str(os.getpid()), PYTHONDONTWRITEBYTECODE='1',
                   OPENBLAS_NUM_THREADS='1', OMP_NUM_THREADS='1', MKL_NUM_THREADS='1', NUMEXPR_NUM_THREADS='1')
        env.pop('PYTHONOPTIMIZE', None)
        stop = None
        peak = 0
        process = None
        code = None
        monitor_error = None
        read_fd = write_fd = None
        try:
            with (output / 'WORKER.log').open('x') as log:
                read_fd, write_fd = os.pipe()
                env['_PAIRED_SOURCE_CONTROLLER_FD'] = str(read_fd)
                process = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT,
                    env=env, preexec_fn=limits, start_new_session=True, pass_fds=(read_fd,))
                os.close(read_fd); read_fd = None
                packet = json.dumps(controller_packet(args), sort_keys=True).encode()
                if len(packet) >= 4096: raise ValueError('CONTROLLER_PACKET_TOO_LARGE')
                if os.write(write_fd, packet) != len(packet): raise ValueError('CONTROLLER_HANDOFF_WRITE_INCOMPLETE')
                os.close(write_fd); write_fd = None
                while process.poll() is None:
                    rss = guard.process_rss(process.pid)
                    peak = max(peak, rss)
                    memory = guard.memory_observation()
                    if rss > policy['RSS_stop_bytes']: stop = 'RSS_LIMIT'
                    elif time.monotonic() - began > policy['wall_seconds_per_year']: stop = 'WALL_LIMIT'
                    elif bytes_used(output) > policy['output_total_bytes_max']: stop = 'OUTPUT_LIMIT'
                    elif shutil.disk_usage(output).free < policy['disk_reserve_bytes']: stop = 'DISK_RESERVE'
                    elif memory['host_used'] > policy['shared_host_limit_bytes'] or memory['SwapTotal'] or memory.get('cgroup_swap_current', 0): stop = 'HOST_SWAP_LIMIT'
                    elif memory.get('cgroup_limit_verified') and memory['cgroup_memory_current'] > memory['cgroup_memory_max']: stop = 'CGROUP_LIMIT'
                    if stop: break
                    time.sleep(policy['sample_period_seconds'])
        except BaseException as error:
            stop = 'MONITOR_OR_LAUNCH_EXCEPTION'
            monitor_error = {'type': type(error).__name__, 'message': str(error)}
        finally:
            for descriptor in (read_fd, write_fd):
                if descriptor is not None:
                    try: os.close(descriptor)
                    except OSError: pass
            if process is not None:
                if process.poll() is None:
                    try: os.killpg(process.pid, signal.SIGKILL)
                    except ProcessLookupError: pass
                code = process.wait()
        try: size = bytes_used(output)
        except OSError as error:
            size = None
            stop = 'FINAL_OUTPUT_OBSERVATION_EXCEPTION'
            monitor_error = {'type': type(error).__name__, 'message': str(error)}
        if code == 0 and size is not None and size > policy['data_output_bytes_max']: stop = 'FINAL_RECEIPT_RESERVE_EXCEEDED'
        receipt = {'status': 'PASS_BOUNDED_SOURCE_ONLY' if code == 0 and stop is None else 'FAIL_BOUNDED_SOURCE_ONLY_PRESERVED',
            'year': args.year, 'exit_code': code, 'stop_reason': stop, 'elapsed_seconds': time.monotonic() - began,
            'peak_aggregate_RSS_bytes': peak, 'output_bytes_before_receipt': size, 'resource_policy': policy,
            'monitor_or_launch_error': monitor_error,
            'runner_manifest_SHA256': args.runner_manifest_sha, 'wallets': 0, 'financial_advances': 0,
            'fits': 0, 'new_market_downloads': 0, 'wallet_GO': False}
        save(output / 'RESOURCE_RECEIPT.json', receipt)
        print(json.dumps(receipt, sort_keys=True))
        if code != 0 or stop:
            raise SystemExit(1)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=('preflight', 'run', 'synthetic-tests'))
    parser.add_argument('--runner-manifest-sha', required=True)
    parser.add_argument('--roots', required=True, help='Private local code/cache path map; never published')
    parser.add_argument('--year', type=int, choices=YEARS)
    parser.add_argument('--output')
    parser.add_argument('--review')
    parser.add_argument('--review-sha')
    parser.add_argument('--parent-go')
    parser.add_argument('--parent-go-sha')
    parser.add_argument('--worker', action='store_true', help=argparse.SUPPRESS)
    args = parser.parse_args()
    gate = bootstrap_gate(args.runner_manifest_sha)
    for name in ('sha', 'read', 'check', 'import_file', 'verify_runner', 'verify_dependencies', 'load_paired', 'authorization'):
        globals()[name] = getattr(gate, name)
    verify_runner(args.runner_manifest_sha)
    roots = read(args.roots)
    pins, cases = verify_dependencies(roots)
    if args.mode == 'synthetic-tests':
        import unittest
        hashes = read(HERE / 'RUNNER_MANIFEST.json')['files_SHA256']
        import_file('source_analysis', HERE / 'source_analysis.py', hashes['source_analysis.py'])
        module = import_file('_paired_source_tests', HERE / 'test_source_runner.py', hashes['test_source_runner.py'])
        suite = unittest.defaultTestLoader.loadTestsFromModule(module)
        result = unittest.TextTestRunner(verbosity=2).run(suite)
        if not result.wasSuccessful(): raise SystemExit(1)
        return
    if args.mode == 'preflight':
        if args.worker: parser.error('worker is only for bounded run')
        print(json.dumps({'status': 'PASS_CODE_METADATA_ONLY_NO_SOURCE_ARRAY_READ', 'paired_commit': BASE_COMMIT,
            'years': list(YEARS), 'source_indexes': {y: c['index']['SHA256'] for y, c in cases['years'].items()},
            'historical_array_reads': 0, 'wallets': 0, 'cached_data_GO': False, 'wallet_GO': False}, sort_keys=True))
        return
    if any(getattr(args, key) is None for key in ('year', 'output', 'review', 'review_sha', 'parent_go', 'parent_go_sha')):
        parser.error('run requires exact independent review, per-year source-only GO and fresh output')
    authorization(args.year, args.runner_manifest_sha, args.review, args.review_sha, args.parent_go, args.parent_go_sha)
    if args.worker: worker(args, roots, pins, cases)
    else: dispatch(args, roots, pins, cases)


if __name__ == '__main__':
    main()
