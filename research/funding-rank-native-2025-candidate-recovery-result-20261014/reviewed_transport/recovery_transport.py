"""Separately reviewed, candidate-only parent for the unchanged V2 worker.

The old failed ledger is evidence, never an output. Recovered financial
completion is explicitly sourced to a separate zero-advance recovery receipt.
"""
import argparse
import fcntl
import gzip
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import resource
import shutil
import signal
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent
ORIGINAL_COMMIT = '519b17f6ce94cb4b5955174d8e520765edaacfee'
ORIGINAL_FREEZE_SHA256 = 'bf5d101404745b66c1483f163ae0f01c81f5661ad53128d6d97668be464d826f'
ORIGINAL_DISPATCHER_SHA256 = '4be0422b6ff5b552268b824f1a03028a10015a9fa809f45caaaba5fc54827ea8'
ORIGINAL_REVIEW_SHA256 = '42e2ac99380c57a33defe192cd15f9d5c935343aced8365dec5f9889e62f7c7f'
ORIGINAL_GO_SHA256 = '6f248b68ec5640372b342bc59fb0247e79dc3e2a691b31e59dac38f7540780f6'
ORIGINAL_LEDGER_SHA256 = 'cdf9930cb41c197f30f74c94e3db82523d652d3f22aab77185e2cba4a3b7418b'
RECOVERY_COMMIT = '9eb7c5293f1748ac9ba9db9c7eb74be9cfa372c2'
RECOVERY_RECEIPT_SHA256 = 'fdff768b1e6a1aa0d641c0b16304e78f6a55fc633acd3d86af917d86a0878e41'
RECOVERY_RESULTS_SHA256 = '273f34f3ad2320267e1fbbb9ec8ed3178c1d6b97cda20a480c9c0d7caa15291a'
CONTROL_STATE_HASH = '123b58fba3cf8567191a0bb11bb9c50bfbceebbf6b955bf42ace71084baf581f'
CONTROL_SNAPSHOT_SHA256 = '17bc119487e5257f97fca4cc48929457b26a24bec06c8c81cc4185d4c4d95f56'
CONTROL_POINTER_SHA256 = 'e21a8e074f88e2fe17fef15e85c3f7c0704abf273a41202e2b1cca7870c33491'
CASE = '2025_candidate'
OUTPUT_NAMESPACE = 'coin_2025_candidate_recovery_transport_v1'
PRIOR_COMPLETED = ['2023_control', '2023_candidate', '2024_control', '2024_candidate']
CASE_SECONDS = 600
TOTAL_SECONDS = 3600
RSS_LIMIT = 2_000_000_000
AS_LIMIT = 4_000_000_000
START_2025 = 1_735_689_600_000_000
END_2025 = 1_767_225_600_000_000
MINUTE = 60_000_000


class GateError(ValueError):
    pass


def read(path):
    return json.loads(Path(path).read_text())


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1_048_576), b''):
            digest.update(block)
    return digest.hexdigest()


def check(path, digest):
    path = Path(path)
    if path.is_symlink() or not path.is_file() or sha(path) != digest:
        raise GateError('EXACT_BYTES_REQUIRED:' + path.name)
    return path


def safe(root, name):
    name = Path(name)
    if name.is_absolute() or '..' in name.parts:
        raise GateError('RELATIVE_ARTIFACT_REQUIRED')
    path = Path(root) / name
    if path.is_symlink() or not path.resolve().is_relative_to(Path(root).resolve()):
        raise GateError('ARTIFACT_SHADOW')
    return path


def save(path, data, *, exclusive=False):
    path = Path(path)
    if exclusive:
        with path.open('x') as stream:
            json.dump(data, stream, indent=2, sort_keys=True, allow_nan=False)
            stream.write('\n')
    else:
        temporary = path.with_suffix(path.suffix + '.tmp')
        temporary.write_text(json.dumps(data, indent=2, sort_keys=True, allow_nan=False) + '\n')
        temporary.replace(path)


def verify_freeze():
    freeze = read(HERE / 'TRANSPORT_FREEZE.json')
    for name, digest in freeze['files_SHA256'].items():
        check(safe(HERE, name), digest)
    policy = read(HERE / 'RESOURCE_POLICY.json')
    if policy['status'] != 'FROZEN_REQUIRES_EXTERNAL_PUBLICATION_REVIEW_AND_NEW_PARENT_GO' or policy['output_cap_bytes'] != 500_000_000:
        raise GateError('RESOURCE_POLICY_NOT_FINAL')
    if (policy['case_wall_seconds'], policy['six_case_cumulative_seconds'], policy['worker_CPU'],
        policy['worker_RSS_bytes'], policy['worker_AS_bytes']) != (600, 3600, 1, RSS_LIMIT, AS_LIMIT):
        raise GateError('UNCHANGED_COMPUTE_BUDGET_REQUIRED')
    return policy


def recovery_gate(ledger_path, receipt_path, results_path, control_case, admission_path, admission_sha, expected_binding):
    """Read saved evidence only. No account construction or calendar advancement."""
    ledger = read(check(ledger_path, ORIGINAL_LEDGER_SHA256))
    attempt = ledger.get('attempts', {}).get('2025_control', {})
    if (ledger.get('publication_commit') != ORIGINAL_COMMIT or ledger.get('completed') != PRIOR_COMPLETED
        or CASE in ledger.get('attempts', {}) or '2025_control' in ledger['completed']
        or attempt.get('exit_code') != -9 or attempt.get('stop') != 'ORIGINAL_CASE250MB_OUTPUT_CAP'):
        raise GateError('ORIGINAL_FAILED_ATTEMPT_AND_FOUR_PRIOR_CASES_REQUIRED')
    elapsed = ledger.get('elapsed_seconds')
    if type(elapsed) not in (int, float) or not math.isfinite(elapsed) or elapsed < 0 or elapsed >= TOTAL_SECONDS:
        raise GateError('CUMULATIVE_BUDGET_EXHAUSTED')
    receipt = read(check(receipt_path, RECOVERY_RECEIPT_SHA256))['control']
    if (receipt.get('status') != 'PASS_REAL_FULL_STATE_ZERO_ADVANCE' or receipt.get('advance_calls') != 0
        or receipt.get('new_economic_wallets') != 0 or receipt.get('completed_minutes') != 525600
        or receipt.get('minute_chunks') != 365 or receipt.get('state_hash') != CONTROL_STATE_HASH
        or receipt.get('snapshot_SHA256') != CONTROL_SNAPSHOT_SHA256):
        raise GateError('VALIDATED_FULL_ZERO_ADVANCE_CONTROL_REQUIRED')
    results = read(check(results_path, RECOVERY_RESULTS_SHA256))
    control = results.get('control', {})
    technical = results.get('technical_execution', {})
    if (control.get('minutes') != 525600 or control.get('daily_chunks') != 365 or control.get('halt_us') is not None
        or control.get('status') != 'PAID_FLAT' or control.get('account_status') != 'ACTIVE'
        or results.get('candidate', {}).get('status') != 'NO_ACCOUNT_CHECKPOINT'
        or technical.get('control') != attempt or technical.get('no_retry_no_ledger_edit') is not True
        or technical.get('pair_completed') is not False):
        raise GateError('RECOVERY_RESULT_ORIGINAL_FAILURE_BINDING')
    admission = read(check(admission_path, admission_sha))
    expected_admission = {
        'schema': 'VALIDATED_FULL_CONTROL_RECOVERY_ADMISSION_V1',
        'status': 'PASS_SAVED_FINANCIAL_COMPLETION_ORIGINAL_TRANSPORT_FAILED',
        'original_publication_commit': ORIGINAL_COMMIT, 'recovery_publication_commit': RECOVERY_COMMIT,
        'original_failed_ledger_SHA256': ORIGINAL_LEDGER_SHA256,
        'zero_advance_receipt_SHA256': RECOVERY_RECEIPT_SHA256, 'recovery_results_SHA256': RECOVERY_RESULTS_SHA256,
        'snapshot_SHA256': CONTROL_SNAPSHOT_SHA256, 'state_hash': CONTROL_STATE_HASH,
        'completed_minutes': 525600, 'minute_chunks': 365, 'financial_advance_calls': 0,
        'original_transport_success': False, 'original_failed_ledger_unchanged': True,
        'checkpoint_POINTER_SHA256': CONTROL_POINTER_SHA256,
        'checkpoint_binding': expected_binding, 'checkpoint_binding_validation': 'PASS_ALL8_FIELDS',
    }
    if any(admission.get(key) != value for key, value in expected_admission.items()):
        raise GateError('VALIDATED_RECOVERY_ADMISSION_RECEIPT_REQUIRED')
    checkpoint = Path(control_case) / 'checkpoint'
    pointer_digest = admission.get('checkpoint_POINTER_SHA256')
    if not isinstance(pointer_digest, str) or len(pointer_digest) != 64:
        raise GateError('PINNED_CHECKPOINT_POINTER_REQUIRED')
    pointer = read(check(checkpoint / 'POINTER.json', pointer_digest))
    if (pointer.get('binding') != expected_binding
        or pointer.get('completed_minutes') != 525600 or pointer.get('cursor') != END_2025
        or pointer.get('stop') is not None or pointer.get('state_hash') != CONTROL_STATE_HASH
        or pointer.get('snapshot_path') != 'STATE_000525600.json.gz'
        or pointer.get('snapshot_SHA256') != CONTROL_SNAPSHOT_SHA256 or len(pointer.get('chunks', [])) != 365):
        raise GateError('PARTIAL_OR_WRONG_CONTROL_CHECKPOINT')
    snapshot_path = check(safe(checkpoint, pointer['snapshot_path']), CONTROL_SNAPSHOT_SHA256)
    snapshot = json.loads(gzip.decompress(snapshot_path.read_bytes()))
    if (snapshot.get('market_range') != [START_2025, END_2025] or snapshot.get('state', {}).get('rows_written') != 525600
        or snapshot.get('state', {}).get('cursor') != END_2025 or snapshot.get('state', {}).get('stop') is not None):
        raise GateError('PARTIAL_CONTROL_SNAPSHOT')
    for index, entry in enumerate(pointer['chunks']):
        if entry.get('path') != f'DAY_{index:04d}.npz' or entry.get('rows') != 1440 or entry.get('columns') != 36:
            raise GateError('COMPLETE_365_CHUNK_SCHEMA_REQUIRED')
        check(safe(checkpoint, entry['path']), entry['SHA256'])
    return ledger, pointer


def effective_completion(ledger, pointer, admission_sha):
    """Distinct new-transport input; never an edit to the original completed ledger."""
    return {
        'schema': 'PROOF_BACKED_EFFECTIVE_COMPLETION_FOR_NEW_RECOVERY_TRANSPORT_V1',
        'completed': [*ledger['completed'], '2025_control'],
        'original_failed_ledger_SHA256': ORIGINAL_LEDGER_SHA256,
        'original_control_attempt': ledger['attempts']['2025_control'],
        'original_transport_control_success': False,
        'recovered_control': {'case': '2025_control', 'kind': 'VALIDATED_FINANCIAL_COMPLETION_ZERO_ADVANCE',
                             'publication_commit': RECOVERY_COMMIT, 'receipt_SHA256': RECOVERY_RECEIPT_SHA256,
                             'admission_receipt_SHA256': admission_sha,
                             'state_hash': pointer['state_hash'], 'completed_minutes': pointer['completed_minutes']},
    }


def transport_authorization(args, policy):
    if args.recovery_admission_sha != sha(HERE / 'RECOVERY_ADMISSION_RECEIPT.json'):
        raise GateError('EXACT_FROZEN_RECOVERY_ADMISSION_REQUIRED')
    freeze_sha = sha(HERE / 'TRANSPORT_FREEZE.json')
    review = read(check(args.transport_review, args.transport_review_sha))
    if (review.get('schema') != 'INDEPENDENT_RECOVERY_TRANSPORT_PUBLICATION_REVIEW_V1'
        or review.get('status') != 'PASS_EXACT_RECOVERY_TRANSPORT_NO_HISTORY'
        or review.get('publication_commit') != args.transport_commit
        or review.get('TRANSPORT_FREEZE_SHA256') != freeze_sha
        or review.get('recovery_receipt_SHA256') != RECOVERY_RECEIPT_SHA256
        or review.get('recovery_admission_receipt_SHA256') != args.recovery_admission_sha):
        raise GateError('INDEPENDENT_NEW_TRANSPORT_REVIEW_REQUIRED')
    go = read(check(args.transport_go, args.transport_go_sha))
    expected = {'schema': 'EXPLICIT_PARENT_RECOVERED_CONTROL_CANDIDATE_ONLY_GO_V1', 'parent_GO': True,
                'publication_commit': args.transport_commit, 'TRANSPORT_FREEZE_SHA256': freeze_sha,
                'transport_review_SHA256': args.transport_review_sha, 'original_publication_commit': ORIGINAL_COMMIT,
                'original_failed_ledger_SHA256': ORIGINAL_LEDGER_SHA256, 'recovery_publication_commit': RECOVERY_COMMIT,
                'recovery_receipt_SHA256': RECOVERY_RECEIPT_SHA256,
                'recovery_admission_receipt_SHA256': args.recovery_admission_sha,
                'roots_SHA256': sha(args.roots), 'candidate_output_namespace': OUTPUT_NAMESPACE,
                'year': 2025, 'arms': ['candidate'],
                'output_cap_bytes': policy['output_cap_bytes'], 'case_wall_seconds': 600,
                'six_case_cumulative_seconds': 3600, 'original_control_not_rerun': True,
                'original_failed_ledger_unchanged': True}
    if any(go.get(key) != value for key, value in expected.items()):
        raise GateError('EXPLICIT_NEW_CANDIDATE_ONLY_GO_REQUIRED')
    return freeze_sha


def candidate_output(roots, supplied):
    """A GO-bound workspace has exactly one candidate namespace across invocations."""
    expected = Path(roots['workspace']).resolve() / OUTPUT_NAMESPACE
    if Path(supplied).resolve() != expected or Path(supplied).is_symlink():
        raise GateError('EXACT_SINGLE_CANDIDATE_OUTPUT_NAMESPACE_REQUIRED')
    if expected.exists():
        raise GateError('NO_DUPLICATE_CANDIDATE_OR_OUTPUT_OVERWRITE')
    return expected


def load_original(directory):
    directory = Path(directory).resolve()
    check(directory / 'V2_FREEZE.json', ORIGINAL_FREEZE_SHA256)
    check(directory / 'dispatcher.py', ORIGINAL_DISPATCHER_SHA256)
    sys.path.insert(0, str(directory))
    spec = importlib.util.spec_from_file_location('unchanged_v2_worker_dispatcher', directory / 'dispatcher.py')
    original = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(original)
    if Path(original.v.__file__).resolve() != directory / 'v2_launcher.py':
        raise GateError('ORIGINAL_LAUNCHER_IMPORT_SHADOW')
    original.v.verify_publication_files()
    return original


def remaining_seconds(original_elapsed, new_elapsed, start, now=None):
    if any(type(value) not in (int, float) or not math.isfinite(value) or value < 0
           for value in (original_elapsed, new_elapsed)):
        raise GateError('INVALID_CUMULATIVE_BUDGET')
    elapsed = (time.monotonic() if now is None else now) - start
    remaining = min(CASE_SECONDS - elapsed, TOTAL_SECONDS - original_elapsed - new_elapsed - elapsed)
    if not math.isfinite(remaining) or remaining <= 20:
        raise GateError('CASE_OR_CUMULATIVE_BUDGET_EXHAUSTED')
    return remaining


def case_bytes(path):
    total = 0
    for item in Path(path).rglob('*'):
        try:
            if item.is_file():
                total += item.stat().st_size
        except FileNotFoundError:
            # Atomic pointer replacement may remove its temporary file here.
            continue
    return total


def monitor_stop(guard, process, case, policy, original_elapsed, new_elapsed, start):
    elapsed = time.monotonic() - start
    if elapsed >= CASE_SECONDS or original_elapsed + new_elapsed + elapsed >= TOTAL_SECONDS:
        return 'HARD_WALL_BUDGET'
    if guard.process_rss(process.pid) > RSS_LIMIT:
        return 'DESCENDANT_RSS2GB'
    if shutil.disk_usage(case.parent).free < guard.DISK_RESERVE:
        return 'DISK15GIB'
    if case_bytes(case) > policy['output_cap_bytes']:
        return 'REVIEWED_RECOVERY_TRANSPORT_CASE500MB_OUTPUT_CAP'
    observation = guard.memory_observation()
    if observation['host_used'] > guard.HOST_USED_LIMIT or observation['SwapTotal'] or observation.get('cgroup_swap_current', 0):
        return 'HOST_SWAP_RESOURCE_GATE'
    if observation.get('cgroup_limit_verified') and observation['cgroup_memory_current'] > observation['cgroup_memory_max']:
        return 'CGROUP_MEMORY'
    return None


def dispatch(args):
    start = time.monotonic()
    policy = verify_freeze()
    freeze_sha = transport_authorization(args, policy)
    original = load_original(args.original_module)
    roots = original.v.read(args.roots)
    published = subprocess.run(['git', 'show', args.transport_commit + ':' + policy['publication_directory'] + '/TRANSPORT_FREEZE.json'],
                               cwd=roots['publication_repo'], capture_output=True)
    if published.returncode or published.stdout != (HERE / 'TRANSPORT_FREEZE.json').read_bytes():
        raise GateError('EXACT_NEW_TRANSPORT_PUBLICATION_REQUIRED')
    original.publication_identity(roots['publication_repo'], ORIGINAL_COMMIT)
    original.v.verify_financial(roots)
    original.v.require_review(args.original_review, ORIGINAL_REVIEW_SHA256, ORIGINAL_COMMIT)
    check(args.original_go, ORIGINAL_GO_SHA256)
    expected_binding = {
        'publication_commit': ORIGINAL_COMMIT, 'year': 2025, 'arm': 'control',
        'V2_FREEZE_SHA256': ORIGINAL_FREEZE_SHA256, 'review_SHA256': ORIGINAL_REVIEW_SHA256,
        'parent_GO_SHA256': ORIGINAL_GO_SHA256,
        'source_index_SHA256': original.v.inp.registry()['years']['2025']['index']['SHA256'],
        'target_archive_SHA256': original.v.read(original.v.HERE / 'TARGET_REMOTE_BINDING.json')['files']['Y2025_TARGETS.npz']['SHA256'],
    }
    ledger, pointer = recovery_gate(args.original_ledger, args.recovery_receipt, args.recovery_results, args.control_case,
                                    args.recovery_admission, args.recovery_admission_sha, expected_binding)
    completion = effective_completion(ledger, pointer, args.recovery_admission_sha)
    original.go_identity(args.original_go, ORIGINAL_GO_SHA256, ORIGINAL_COMMIT, 2025, 'candidate', completion['completed'])
    output = candidate_output(roots, args.output)
    original.v.bind_saved_targets(2025, roots['targets'])
    original.v.source_window(2025, roots['source2025'], roots.get('derived_csv'))
    admission = original.resource_admission(roots, output)
    guard = original.original_resource_guard(roots)
    required_disk = guard.DISK_RESERVE + policy['output_cap_bytes'] + 2 * 63_204_609 + 1_048_576
    if shutil.disk_usage(output.parent).free < required_disk:
        raise GateError('NEW500MB_CASE_AND_ORIGINAL_CHECKPOINT_DISK_RESERVATION')
    remaining_seconds(ledger['elapsed_seconds'], 0.0, start)
    with Path('/tmp/coin_offline_financial_controller.lock').open('a') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise GateError('OTHER_FINANCIAL_CONTROLLER_LOCKED')
        check(args.original_ledger, ORIGINAL_LEDGER_SHA256)
        if output.exists():
            raise GateError('NO_DUPLICATE_CANDIDATE_OR_OUTPUT_OVERWRITE')
        output.mkdir(parents=True, exist_ok=False)
        save(output / 'EFFECTIVE_COMPLETION_INPUT.json', completion, exclusive=True)
        binding = {'schema': 'DISTINCT_RECOVERY_TRANSPORT_CANDIDATE_BINDING_V1', 'transport_commit': args.transport_commit,
                   'TRANSPORT_FREEZE_SHA256': freeze_sha, 'transport_review_SHA256': args.transport_review_sha,
                   'transport_GO_SHA256': args.transport_go_sha, 'original_publication_commit': ORIGINAL_COMMIT,
                   'original_failed_ledger_SHA256': ORIGINAL_LEDGER_SHA256, 'recovery_receipt_SHA256': RECOVERY_RECEIPT_SHA256,
                   'recovery_admission_receipt_SHA256': args.recovery_admission_sha,
                   'original_elapsed_seconds': ledger['elapsed_seconds'], 'output_cap_bytes': policy['output_cap_bytes']}
        save(output / 'TRANSPORT_BINDING.json', binding, exclusive=True)
        new_ledger = {'schema': 'SEPARATE_RECOVERY_TRANSPORT_LEDGER_V1', 'binding': binding, 'attempts': {CASE: {'status': 'STARTED_NO_RETRY'}},
                      'original_elapsed_seconds': ledger['elapsed_seconds'], 'elapsed_seconds': 0.0, 'completed': []}
        save(output / 'TRANSPORT_LEDGER.json', new_ledger, exclusive=True)
        remaining = remaining_seconds(ledger['elapsed_seconds'], 0.0, start)
        def limits():
            os.sched_setaffinity(0, {admission['allowed_cpus'][0]})
            resource.setrlimit(resource.RLIMIT_AS, (AS_LIMIT, AS_LIMIT))
            resource.setrlimit(resource.RLIMIT_CPU, (int(remaining), int(remaining)))
        command = [sys.executable, '-B', str(Path(args.original_module).resolve() / 'dispatcher.py'), '--worker',
                   '--roots', args.roots, '--year', '2025', '--arm', 'candidate', '--output', str(output),
                   '--publication-commit', ORIGINAL_COMMIT, '--review', args.original_review, '--review-sha', ORIGINAL_REVIEW_SHA256,
                   '--parent-go-receipt', args.original_go, '--parent-go-sha', ORIGINAL_GO_SHA256,
                   '--completed', str(output / 'EFFECTIVE_COMPLETION_INPUT.json'), '--remaining-seconds', str(remaining)]
        log = (output / (CASE + '.log')).open('x')
        process = None
        stop = None
        parent_error = None
        case = output / CASE
        try:
            process = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT, start_new_session=True, preexec_fn=limits,
                                       env=dict(os.environ, _V2_PARENT_PID=str(os.getpid()), PYTHONDONTWRITEBYTECODE='1',
                                                OPENBLAS_NUM_THREADS='1', OMP_NUM_THREADS='1', POLARS_MAX_THREADS='1'))
            while process.poll() is None:
                stop = monitor_stop(guard, process, case, policy, ledger['elapsed_seconds'], 0.0, start)
                if stop:
                    try:
                        os.killpg(process.pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
                    process.wait()
                    break
                time.sleep(.05)
        except BaseException as error:
            stop = 'PARENT_TRANSPORT_EXCEPTION:' + type(error).__name__
            parent_error = error
        finally:
            if process is not None and process.poll() is None:
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                process.wait()
            log.close()
        # The worker's last atomic output may land between monitor polls.
        if stop is None and case_bytes(case) > policy['output_cap_bytes']:
            stop = 'REVIEWED_RECOVERY_TRANSPORT_CASE500MB_OUTPUT_CAP'
        duration = time.monotonic() - start
        new_ledger['elapsed_seconds'] = duration
        new_ledger['cumulative_elapsed_seconds'] = ledger['elapsed_seconds'] + duration
        attempt = {'exit_code': process.returncode if process is not None else None, 'stop': stop, 'elapsed_seconds': duration,
                   'status': 'PRESERVED_SEPARATE_TRANSPORT_ATTEMPT_NO_RETRY'}
        new_ledger['attempts'][CASE] = attempt
        summary_path = case / 'SUMMARY.json'
        if process is not None and process.returncode == 0 and stop is None and summary_path.is_file():
            try:
                summary = read(summary_path)
                if summary.get('transport_stop_reason') is None:
                    new_ledger['completed'].append(CASE)
                    attempt['technical_completion'] = 'WORKER_EXIT_SUCCESS_PENDING_INDEPENDENT_RESULT_REVIEW'
            except (ValueError, AttributeError):
                attempt['stop'] = 'INVALID_WORKER_SUMMARY'
        save(output / 'TRANSPORT_LEDGER.json', new_ledger)
        check(args.original_ledger, ORIGINAL_LEDGER_SHA256)
        if parent_error is not None:
            raise parent_error
        return new_ledger


def main():
    parser = argparse.ArgumentParser()
    for name in ('original-module', 'roots', 'original-ledger', 'control-case', 'recovery-receipt', 'recovery-results',
                 'recovery-admission', 'recovery-admission-sha',
                 'original-review', 'original-go', 'transport-commit', 'transport-review', 'transport-review-sha',
                 'transport-go', 'transport-go-sha', 'output'):
        parser.add_argument('--' + name, required=True)
    args = parser.parse_args()
    result = dispatch(args)
    print(json.dumps(result, sort_keys=True))
    return 0 if CASE in result['completed'] else 3


if __name__ == '__main__':
    raise SystemExit(main())
